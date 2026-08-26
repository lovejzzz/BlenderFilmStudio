import { createHash } from 'node:crypto';
import { execFile } from 'node:child_process';
import { readdir, readFile, stat } from 'node:fs/promises';
import { relative, resolve, sep } from 'node:path';
import { promisify } from 'node:util';
import { sha256Canonical, sha256File } from './receipt-format.mjs';

const execFileAsync = promisify(execFile);
const HASH = /^[0-9a-f]{64}$/;
const repoUri = (root, path) => relative(root, path).split(sep).join('/');

async function json(path) {
  return JSON.parse(await readFile(path, 'utf8'));
}

async function filesBelow(root) {
  const found = [];
  async function visit(path) {
    let entries;
    try { entries = await readdir(path, { withFileTypes: true }); } catch (error) {
      if (error.code === 'ENOENT') return;
      throw error;
    }
    for (const entry of entries) {
      const child = resolve(path, entry.name);
      if (entry.isDirectory()) await visit(child);
      else if (entry.isFile()) found.push(child);
    }
  }
  await visit(root);
  return found.sort();
}

function addHash(set, value) {
  if (typeof value !== 'string' || !HASH.test(value)) throw new Error(`B35 sensitive registry received a non-SHA value: ${String(value).slice(0, 80)}`);
  set.add(value);
}

export async function buildB35SensitiveRegistry({ privateEvidenceRoot, sealedPath, sessionRoot }) {
  const values = new Set();
  const names = await readdir(privateEvidenceRoot);
  const sourceManifestNames = names.filter(name => /^(NATURAL32|Q4_[1-4]|Q8_[1-8])\.manifest\.json$/.test(name)).sort();
  if (sourceManifestNames.length !== 13) throw new Error(`B35 sensitive registry expected 13 source manifests, observed ${sourceManifestNames.length}`);
  for (const name of sourceManifestNames) {
    const manifest = await json(resolve(privateEvidenceRoot, name));
    for (const output of manifest.outputs) addHash(values, output.sha256);
  }
  const composite = await json(resolve(privateEvidenceRoot, 'composite-display.manifest.json'));
  for (const method of Object.values(composite.methods)) for (const output of method.outputs) {
    addHash(values, output.compositeSha256);
    addHash(values, output.displaySha256);
    for (const source of output.sources) addHash(values, source.sha256);
  }
  for (const method of ['NATURAL32', 'QUADRATURE4', 'STRATIFIED8']) {
    const roundtrip = await json(resolve(privateEvidenceRoot, `${method}.roundtrip.json`));
    for (const frame of roundtrip.frames) {
      addHash(values, frame.sourceSha256);
      addHash(values, frame.decodedSha256);
    }
  }
  const packageManifest = await json(resolve(privateEvidenceRoot, 'package.manifest.json'));
  for (const carrier of packageManifest.carriers) addHash(values, carrier.sha256);
  for (const session of packageManifest.sessions) {
    addHash(values, session.mappingCommitment);
    addHash(values, session.observerHtmlSha256);
    for (const binding of session.visibleCarrierBindings) addHash(values, binding.sha256);
  }
  const sealed = await json(sealedPath);
  addHash(values, sealed.overallCommitment);
  for (const session of sealed.sessions) {
    addHash(values, session.salt);
    addHash(values, session.commitment);
  }
  for (const path of await filesBelow(sessionRoot)) {
    if (path.endsWith('.webm')) addHash(values, await sha256File(path));
    if (path.endsWith('/index.html')) addHash(values, await sha256File(path));
  }
  return [...values].sort();
}

function hashBytes(bytes) {
  return createHash('sha256').update(bytes).digest('hex');
}

async function scanFile(path, sensitiveSet) {
  const bytes = await readFile(path);
  const contentSha = hashBytes(bytes);
  const matches = new Set();
  if (sensitiveSet.has(contentSha)) matches.add(contentSha);
  for (const token of bytes.toString('latin1').match(/[0-9a-f]{64}/g) || []) if (sensitiveSet.has(token)) matches.add(token);
  return [...matches];
}

export async function auditB35PublicState({ repositoryRoot, privateEvidenceRoot, sealedPath, sessionRoot, registryPath, publicRoots = [], requireCleanTrackedTree = true }) {
  const registry = await json(registryPath);
  const sensitiveValues = await buildB35SensitiveRegistry({ privateEvidenceRoot, sealedPath, sessionRoot });
  const expectedCommitment = sha256Canonical({ salt: registry.salt, values: sensitiveValues });
  if (registry.documentType !== 'BFS_B35_SENSITIVE_HASH_REGISTRY' || registry.values.length !== sensitiveValues.length || JSON.stringify(registry.values) !== JSON.stringify(sensitiveValues) || registry.commitment !== expectedCommitment) throw new Error('B35 sensitive registry binding mismatch');

  const [{ stdout: headText }, { stdout: trackedText }, { stdout: statusText }] = await Promise.all([
    execFileAsync('git', ['rev-parse', 'HEAD'], { cwd: repositoryRoot }),
    execFileAsync('git', ['ls-files', '-z'], { cwd: repositoryRoot, encoding: 'buffer', maxBuffer: 64 * 1024 * 1024 }),
    execFileAsync('git', ['status', '--porcelain', '--untracked-files=no'], { cwd: repositoryRoot }),
  ]);
  const head = String(headText).trim();
  const trackedNames = Buffer.from(trackedText).toString('utf8').split('\0').filter(Boolean).sort();
  const privatePrefix = 'experiments/human-quadrature-review-v0-2/work/';
  const trackedPrivatePaths = trackedNames.filter(name => name.startsWith(privatePrefix));
  const sensitiveSet = new Set(sensitiveValues), matches = [];
  for (const name of trackedNames) {
    const path = resolve(repositoryRoot, name);
    for (const value of await scanFile(path, sensitiveSet)) matches.push({ surface: 'git-tracked', path: name, value });
  }
  let publicFileCount = 0;
  for (const root of publicRoots) for (const path of await filesBelow(root)) {
    if (!(await stat(path)).isFile()) continue;
    publicFileCount += 1;
    for (const value of await scanFile(path, sensitiveSet)) matches.push({ surface: 'public-build', path: repoUri(repositoryRoot, path), value });
  }
  const trackedDirty = String(statusText).trim();
  const pass = trackedPrivatePaths.length === 0 && matches.length === 0 && (!requireCleanTrackedTree || trackedDirty === '');
  return {
    documentType: 'BFS_B35_PUBLIC_STATE_LEAK_AUDIT',
    version: '0.2.0',
    auditedAtUtc: new Date().toISOString(),
    status: pass ? 'PUBLIC_STATE_LEAK_AUDIT_PASS' : 'PUBLIC_STATE_LEAK_AUDIT_FAIL',
    gitHead: head,
    trackedTreeClean: trackedDirty === '',
    trackedFileCount: trackedNames.length,
    publicBuildFileCount: publicFileCount,
    sensitiveRegistryCount: sensitiveValues.length,
    sensitiveRegistryCommitment: registry.commitment,
    trackedPrivatePathCount: trackedPrivatePaths.length,
    sensitiveMatchCount: matches.length,
    privateDetails: { trackedPrivatePaths, matches },
    publicSummary: {
      gitHead: head,
      trackedTreeClean: trackedDirty === '',
      trackedFileCount: trackedNames.length,
      publicBuildFileCount: publicFileCount,
      sensitiveRegistryCount: sensitiveValues.length,
      sensitiveRegistryCommitment: registry.commitment,
      trackedPrivatePathCount: trackedPrivatePaths.length,
      sensitiveMatchCount: matches.length,
    },
  };
}
