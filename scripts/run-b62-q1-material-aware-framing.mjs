#!/usr/bin/env node

import { execFile } from 'node:child_process';
import { createHash } from 'node:crypto';
import { lstat, mkdir, open, readFile, readdir, statfs } from 'node:fs/promises';
import { dirname, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';
import { runBudgetedProcess } from './lib/budgeted-process.mjs';

const execFileAsync = promisify(execFile);
const repositoryRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const SPEC_URI = 'specs/b62-camera-quality-material-aware-framing-diagnostic.v0.1.json';
const PROTOCOL_URI = 'research/2026-08-29-b62-camera-quality-material-aware-framing-diagnostic-protocol.md';
const ROOT_URI = 'experiments/b62-camera-quality-material-aware-framing-v0-1';
const PREREGISTRATION_COMMIT = 'b4fdb6d';
const DERIVATION_ROOT_URI = 'experiments/b62-camera-quality-geometric-diagnostic-v0-2';
const TOOL_URIS = [
  'blender/probe_b62_q1_material_aware_framing.py',
  'blender/audit_b62_q1_material_aware_framing.py',
  'scripts/run-b62-q1-material-aware-framing.mjs',
  'scripts/audit-b62-q1-material-aware-framing.mjs',
];

function canonicalize(value) {
  if (Array.isArray(value)) return value.map(canonicalize);
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).sort(([a], [b]) => a.localeCompare(b)).map(([key, child]) => [key, canonicalize(child)]));
  return value;
}
const canonicalJson = value => JSON.stringify(canonicalize(value));
const hashBytes = value => createHash('sha256').update(value).digest('hex');
const hashFile = async path => hashBytes(await readFile(path));

function validSelfHash(value, field) {
  if (!value || !/^[0-9a-f]{64}$/.test(value[field] ?? '')) return false;
  const copy = structuredClone(value);
  const expected = copy[field];
  delete copy[field];
  return hashBytes(canonicalJson(copy)) === expected;
}

function requireValue(condition, message) {
  if (!condition) throw new Error(message);
}

function localPath(uri) {
  requireValue(typeof uri === 'string' && uri && !uri.startsWith('/') && !uri.split('/').includes('..'), `unsafe path ${uri}`);
  const path = resolve(repositoryRoot, uri);
  const rel = relative(repositoryRoot, path);
  requireValue(rel !== '..' && !rel.startsWith('../'), `escaped path ${uri}`);
  return path;
}

async function exists(path) {
  try { await lstat(path); return true; } catch (error) { if (error.code === 'ENOENT') return false; throw error; }
}

async function writeHashed(path, value, field) {
  const body = structuredClone(value);
  body[field] = hashBytes(canonicalJson(body));
  const handle = await open(path, 'wx', 0o600);
  try { await handle.writeFile(`${JSON.stringify(body, null, 2)}\n`); await handle.sync(); } finally { await handle.close(); }
  return body;
}

async function git(args, encoding = 'utf8') {
  return (await execFileAsync('/usr/bin/git', args, { cwd: repositoryRoot, encoding, timeout: 15000, maxBuffer: 32 * 1024 * 1024, env: { PATH: '/usr/bin:/bin', LANG: 'C', LC_ALL: 'C', GIT_CONFIG_NOSYSTEM: '1', GIT_TERMINAL_PROMPT: '0' } })).stdout;
}

async function committedHash(commit, uri) {
  return hashBytes(await git(['show', `${commit}:${uri}`], null));
}

async function treeIdentity(rootUri) {
  const root = localPath(rootUri);
  const files = [];
  async function walk(directory) {
    for (const entry of await readdir(directory, { withFileTypes: true })) {
      const path = resolve(directory, entry.name);
      if (entry.isDirectory()) await walk(path);
      else if (entry.isFile()) files.push(path);
      else throw new Error(`special evidence file ${path}`);
    }
  }
  await walk(root);
  files.sort();
  let bytes = 0;
  let material = '';
  for (const path of files) {
    const content = await readFile(path);
    bytes += content.length;
    material += `${relative(root, path).split('\\').join('/')}\0${hashBytes(content)}\n`;
  }
  return { files: files.length, bytes, treeSha256: hashBytes(Buffer.from(material)) };
}

function parseArgs() {
  const args = process.argv.slice(2);
  requireValue(args.length === 2 && args[0] === '--tool-freeze-commit' && /^[0-9a-f]{40}$/.test(args[1]), 'usage: --tool-freeze-commit <40-hex-sha>');
  return args[1];
}

async function processReceipt(root, processId, command, args, result) {
  return writeHashed(resolve(root, 'processes', `${processId}.json`), { schemaVersion: 'bfs.b62CameraQualityProcessReceipt.v0.1', experimentId: 'B62-Q1-D2', processId, command, args, result }, 'processHash');
}

async function runBlender(root, processId, toolUri, outputName, masterPath, masterSha, spec) {
  const command = spec.runtime.blender.executable;
  const args = ['--background', '--factory-startup', '--disable-autoexec', masterPath, '--python-exit-code', '1', '--python', localPath(toolUri), '--', '--output', resolve(root, outputName), '--master-sha256', masterSha];
  const result = await runBudgetedProcess({
    command, args, cwd: repositoryRoot,
    env: { PATH: '/usr/bin:/bin', LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8', OCIO: resolve(repositoryRoot, 'color/ocio/cg-config-v4.0.0_aces-v2.0_ocio-v2.5.ocio') },
    outputRoot: root,
    budgets: { wallTimeMs: spec.processBudget.maximumWallSecondsPerBlender * 1000, maxRssBytes: spec.processBudget.maximumPeakResidentSetSizeBytesPerBlender, maxLogBytes: spec.processBudget.maximumCombinedLogBytesPerChild, maxOutputFiles: 64, maxOutputBytes: spec.processBudget.projectedWriteBytes, sampleIntervalMs: 100 },
  });
  const receipt = await processReceipt(root, processId, command, args.map(value => value.startsWith(repositoryRoot) ? relative(repositoryRoot, value).split('\\').join('/') : value), result);
  requireValue(result.outcome === 'PASS' && result.child.exitCode === 0 && result.breach === null, `${processId} failed: ${result.outcome}`);
  requireValue(await exists(resolve(root, outputName)), `${outputName} missing`);
  return receipt;
}

async function main() {
  const freeze = parseArgs();
  const specPath = localPath(SPEC_URI);
  const protocolPath = localPath(PROTOCOL_URI);
  const root = localPath(ROOT_URI);
  requireValue(!await exists(root), `formal root already exists: ${ROOT_URI}`);
  const spec = JSON.parse(await readFile(specPath, 'utf8'));
  requireValue(spec.experimentId === 'B62-Q1-D2' && spec.statusBeforeToolCreation === 'PREREGISTERED', 'spec identity mismatch');
  requireValue(spec.output.formalRoot === ROOT_URI, 'formal root spec mismatch');

  const head = (await git(['rev-parse', 'HEAD'])).trim();
  const origin = (await git(['rev-parse', 'origin/main'])).trim();
  requireValue(head === freeze && origin === freeze, 'tool freeze is not synchronized HEAD/origin/main');
  requireValue((await git(['merge-base', '--is-ancestor', PREREGISTRATION_COMMIT, freeze])).trim() === '', 'preregistration not ancestor of freeze');
  requireValue(await hashFile(specPath) === await committedHash(PREREGISTRATION_COMMIT, SPEC_URI), 'spec changed after preregistration');
  requireValue(await hashFile(protocolPath) === await committedHash(PREREGISTRATION_COMMIT, PROTOCOL_URI), 'protocol changed after preregistration');
  const toolHashes = {};
  for (const uri of TOOL_URIS) {
    toolHashes[uri] = await hashFile(localPath(uri));
    requireValue(toolHashes[uri] === await committedHash(freeze, uri), `tool not frozen ${uri}`);
  }
  const scoped = [SPEC_URI, PROTOCOL_URI, DERIVATION_ROOT_URI, ...TOOL_URIS];
  requireValue((await git(['status', '--porcelain=v1', '--', ...scoped])).trim() === '', 'scoped worktree is dirty');

  const derivationTree = await treeIdentity(DERIVATION_ROOT_URI);
  requireValue(canonicalJson(derivationTree) === canonicalJson(spec.derivationDisclosure.sourceExperiment.tree), 'derivation tree mismatch');
  const derivationReceiptPath = localPath(spec.derivationDisclosure.sourceExperiment.receipt.uri);
  requireValue(await hashFile(derivationReceiptPath) === spec.derivationDisclosure.sourceExperiment.receipt.sha256, 'derivation receipt mismatch');
  const derivationReceipt = JSON.parse(await readFile(derivationReceiptPath, 'utf8'));
  requireValue(derivationReceipt.receiptHash === spec.derivationDisclosure.sourceExperiment.receipt.receiptHash, 'derivation self hash mismatch');

  const masterPath = localPath(spec.parentEvidence.masterScene.uri);
  const masterSha = await hashFile(masterPath);
  requireValue(masterSha === spec.parentEvidence.masterScene.sha256, 'master mismatch');
  const blenderSha = await hashFile(spec.runtime.blender.executable);
  requireValue(blenderSha === spec.runtime.blender.sha256, 'Blender binary mismatch');
  for (const item of spec.parentEvidence.calibrationPngs) requireValue(await hashFile(localPath(item.uri)) === item.sha256, `calibration mismatch ${item.shot}`);
  const free = await statfs(repositoryRoot);
  const availableBytes = Number(free.bavail) * Number(free.bsize);
  requireValue(availableBytes - spec.processBudget.projectedWriteBytes >= spec.processBudget.minimumFreeReserveBytes, 'disk reserve insufficient');

  await mkdir(resolve(root, 'processes'), { recursive: true, mode: 0o700 });
  const admission = await writeHashed(resolve(root, 'admission.json'), {
    schemaVersion: 'bfs.b62CameraQualityAdmission.v0.1', experimentId: 'B62-Q1-D2', status: 'ADMITTED',
    preregistrationCommit: PREREGISTRATION_COMMIT, toolFreezeCommit: freeze,
    bindings: { spec: { uri: SPEC_URI, sha256: await hashFile(specPath) }, protocol: { uri: PROTOCOL_URI, sha256: await hashFile(protocolPath) }, derivationTree, derivationReceiptSha256: await hashFile(derivationReceiptPath), master: { uri: spec.parentEvidence.masterScene.uri, sha256: masterSha }, blenderSha256: blenderSha, tools: toolHashes },
    resources: { availableBytesBefore: availableBytes, projectedWriteBytes: spec.processBudget.projectedWriteBytes, minimumFreeReserveBytes: spec.processBudget.minimumFreeReserveBytes },
    operations: { blenderStartsBeforeAdmission: 0, renderCalls: 0, modelCalls: 0, networkCalls: 0, dockerProcesses: 0 },
  }, 'admissionHash');

  try {
    const primaryProcess = await runBlender(root, 'PRIMARY', TOOL_URIS[0], 'primary.json', masterPath, masterSha, spec);
    const independentProcess = await runBlender(root, 'INDEPENDENT', TOOL_URIS[1], 'independent.json', masterPath, masterSha, spec);
    const auditorArgs = [localPath(TOOL_URIS[3]), '--root', ROOT_URI, '--tool-freeze-commit', freeze];
    const auditor = await runBudgetedProcess({ command: process.execPath, args: auditorArgs, cwd: repositoryRoot, env: { PATH: '/usr/bin:/bin', LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8' }, outputRoot: root, budgets: { wallTimeMs: 30000, maxRssBytes: 1073741824, maxLogBytes: 1048576, maxOutputFiles: 64, maxOutputBytes: spec.processBudget.projectedWriteBytes, sampleIntervalMs: 100 } });
    const auditorProcess = await processReceipt(root, 'AUDITOR', process.execPath, auditorArgs.map(value => value.startsWith(repositoryRoot) ? relative(repositoryRoot, value).split('\\').join('/') : value), auditor);
    requireValue(auditor.outcome === 'PASS' && auditor.child.exitCode === 0, 'Node auditor failed');
    const auditPath = resolve(root, 'audit.json');
    const comparisonPath = resolve(root, 'comparison.json');
    const audit = JSON.parse(await readFile(auditPath, 'utf8'));
    const comparison = JSON.parse(await readFile(comparisonPath, 'utf8'));
    requireValue(validSelfHash(audit, 'auditHash') && audit.status === 'PASS' && audit.scientificVerdict, 'audit output invalid');
    requireValue(validSelfHash(comparison, 'comparisonHash') && comparison.status === 'PASS', 'comparison output invalid');
    const receipt = await writeHashed(resolve(root, 'receipt.json'), {
      schemaVersion: 'bfs.b62CameraQualityMaterialAwareFramingReceipt.v0.1', experimentId: 'B62-Q1-D2', status: 'PASS', scientificVerdict: audit.scientificVerdict,
      admission: { uri: `${ROOT_URI}/admission.json`, sha256: await hashFile(resolve(root, 'admission.json')), admissionHash: admission.admissionHash },
      comparison: { uri: `${ROOT_URI}/comparison.json`, sha256: await hashFile(comparisonPath), comparisonHash: comparison.comparisonHash },
      audit: { uri: `${ROOT_URI}/audit.json`, sha256: await hashFile(auditPath), auditHash: audit.auditHash },
      processes: {
        primary: { uri: `${ROOT_URI}/processes/PRIMARY.json`, sha256: await hashFile(resolve(root, 'processes', 'PRIMARY.json')), processHash: primaryProcess.processHash },
        independent: { uri: `${ROOT_URI}/processes/INDEPENDENT.json`, sha256: await hashFile(resolve(root, 'processes', 'INDEPENDENT.json')), processHash: independentProcess.processHash },
        auditor: { uri: `${ROOT_URI}/processes/AUDITOR.json`, sha256: await hashFile(resolve(root, 'processes', 'AUDITOR.json')), processHash: auditorProcess.processHash },
      },
      operations: { runnerProcesses: 1, blenderStarts: 2, renderCalls: 0, nodeAuditorProcesses: 1, modelCalls: 0, networkCalls: 0, dockerProcesses: 0 },
      nonClaims: spec.nonClaims,
    }, 'receiptHash');
    console.log(`BFS_B62_Q1_D2 PASS ${receipt.scientificVerdict} ${receipt.receiptHash}`);
  } catch (error) {
    await writeHashed(resolve(root, 'failure.json'), { schemaVersion: 'bfs.b62CameraQualityFailure.v0.1', experimentId: 'B62-Q1-D2', status: 'INVALIDATED', admissionHash: admission.admissionHash, error: { name: error.name, message: error.message }, operations: { renderCalls: 0, modelCalls: 0, networkCalls: 0, dockerProcesses: 0 } }, 'failureHash');
    throw error;
  }
}

main().catch(error => { console.error(error.stack ?? error.message); process.exitCode = 1; });
