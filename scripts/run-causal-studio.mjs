#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { dirname, join, relative, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const specUri = 'specs/ai-native-studio-causal-studio-preregistration.v0.1.json';
const contextUri = 'specs/ai-native-studio-causal-studio-execution-context-c2.v0.3.json';
const freezeUri = 'specs/ai-native-studio-causal-studio-tool-freeze-c2.v0.3.json';
const scriptUri = 'scripts/build-causal-studio.py';
const specPath = resolve(root, specUri);
const contextPath = resolve(root, contextUri);
const freezePath = resolve(root, freezeUri);
const scriptPath = resolve(root, scriptUri);

function canonical(value) {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}`;
}
function shaBytes(value) { return createHash('sha256').update(value).digest('hex'); }
function shaFile(path) { return shaBytes(readFileSync(path)); }
function selfHash(value, field) { const copy = structuredClone(value); delete copy[field]; return shaBytes(Buffer.from(canonical(copy))); }
function validSelf(value, field) { return value?.[field] === selfHash(value, field); }
function writeRecord(path, body, field) { const value = { ...body }; value[field] = selfHash(value, field); writeFileSync(path, `${JSON.stringify(value, null, 2)}\n`); return value; }
function dirBytes(path) { if (!existsSync(path)) return 0; const stat = statSync(path, { throwIfNoEntry: false }); if (!stat) return 0; if (!stat.isDirectory()) return stat.size; return readdirSync(path).reduce((sum, name) => sum + dirBytes(join(path, name)), 0); }
function manifest(path, excluded = new Set()) {
  const rows = [];
  function visit(current) {
    for (const name of readdirSync(current).sort()) {
      const item = join(current, name);
      const rel = relative(path, item);
      if (excluded.has(rel)) continue;
      const stat = statSync(item);
      if (stat.isSymbolicLink()) throw new Error(`SYMLINK_${rel}`);
      if (stat.isDirectory()) visit(item);
      else rows.push({ path: rel, bytes: stat.size, sha256: shaFile(item) });
    }
  }
  visit(path);
  return rows;
}

const spec = JSON.parse(readFileSync(specPath, 'utf8'));
const context = JSON.parse(readFileSync(contextPath, 'utf8'));
const freeze = JSON.parse(readFileSync(freezePath, 'utf8'));
if (!validSelf(spec, 'specHash') || spec.status !== 'PREREGISTERED_BEFORE_ATTEMPT01_SCENE_MUTATION') throw new Error('SPEC');
if (!validSelf(context, 'contextHash') || context.status !== 'PREREGISTERED_C2_BEFORE_ATTEMPT03_SCENE_MUTATION') throw new Error('CONTEXT');
if (!validSelf(freeze, 'freezeHash') || freeze.status !== 'FROZEN_C2_BEFORE_ATTEMPT03_SCENE_MUTATION') throw new Error('FREEZE');
if (context.base.specHash !== spec.specHash || context.base.sha256 !== shaFile(specPath)) throw new Error('CONTEXT_SPEC_BINDING');
if (freeze.context.contextHash !== context.contextHash || freeze.context.sha256 !== shaFile(contextPath)) throw new Error('FREEZE_CONTEXT_BINDING');
if (freeze.tools.some(row => shaFile(resolve(root, row.uri)) !== row.sha256)) throw new Error('TOOL_HASH');

const workRoot = resolve(context.roots.work);
const evidenceRoot = resolve(root, context.roots.evidence);
if (existsSync(workRoot) || existsSync(evidenceRoot)) throw new Error('FRESH_ROOTS_REQUIRED');
if (shaFile(spec.engine.path) !== spec.engine.sha256) throw new Error('BINARY_HASH');
const disk = spawnSync('df', ['-Pk', root], { encoding: 'utf8' });
if (disk.status !== 0) throw new Error('DISK_CHECK');
const freeKiB = Number(disk.stdout.trim().split(/\n/).at(-1).trim().split(/\s+/)[3]);
if (freeKiB * 1024 < spec.resourceCeilings.minimumFreeDiskGiBBeforeStart * 1024 ** 3) throw new Error('DISK_ADMISSION');

mkdirSync(workRoot, { recursive: false });
mkdirSync(evidenceRoot, { recursive: true });
for (const path of ['logs', 'processes', 'home', 'tmp', 'config', 'scripts']) mkdirSync(join(evidenceRoot, path), { recursive: true });
const env = {
  ...process.env,
  HOME: join(evidenceRoot, 'home'),
  TMPDIR: `${join(evidenceRoot, 'tmp')}/`,
  BLENDER_USER_CONFIG: join(evidenceRoot, 'config'),
  BLENDER_USER_SCRIPTS: join(evidenceRoot, 'scripts'),
  PYTHONNOUSERSITE: '1',
  LC_ALL: 'C',
  LANG: 'C',
  OCIO: resolve(root, 'color/ocio/cg-config-v4.0.0_aces-v2.0_ocio-v2.5.ocio'),
};

function runBlender(index, mode) {
  const blendPath = join(workRoot, 'PC5_CAUSAL_STUDIO.blend');
  const blenderArgv = mode === 'build'
    ? ['--background', '--factory-startup', '--python', scriptPath, '--', '--mode', mode, '--spec', specPath, '--context', contextPath, '--work', workRoot, '--evidence', evidenceRoot]
    : ['--background', '--factory-startup', blendPath, '--python', scriptPath, '--', '--mode', mode, '--spec', specPath, '--context', contextPath, '--work', workRoot, '--evidence', evidenceRoot];
  const started = Date.now();
  const result = spawnSync('/usr/bin/caffeinate', ['-dimsu', spec.engine.path, ...blenderArgv], { cwd: root, env, encoding: 'buffer', timeout: 600000, maxBuffer: 64 * 1024 * 1024 });
  const wallSeconds = (Date.now() - started) / 1000;
  const stdout = result.stdout ?? Buffer.alloc(0);
  const stderr = result.stderr ?? Buffer.alloc(0);
  const prefix = `${String(index).padStart(2, '0')}-${mode}`;
  const stdoutPath = join(evidenceRoot, 'logs', `${prefix}.stdout.log`);
  const stderrPath = join(evidenceRoot, 'logs', `${prefix}.stderr.log`);
  writeFileSync(stdoutPath, stdout);
  writeFileSync(stderrPath, stderr);
  const process = writeRecord(join(evidenceRoot, 'processes', `${prefix}.json`), {
    schemaVersion: 'bfs.causalStudioProcess.v0.1',
    index,
    mode,
    executable: '/usr/bin/caffeinate',
    argv: ['-dimsu', spec.engine.path, ...blenderArgv],
    blenderArgv: [spec.engine.path, ...blenderArgv],
    cwd: root,
    environment: { HOME: env.HOME, TMPDIR: env.TMPDIR, BLENDER_USER_CONFIG: env.BLENDER_USER_CONFIG, BLENDER_USER_SCRIPTS: env.BLENDER_USER_SCRIPTS, PYTHONNOUSERSITE: env.PYTHONNOUSERSITE, LC_ALL: env.LC_ALL, LANG: env.LANG, OCIO: env.OCIO },
    exitCode: result.status,
    signal: result.signal,
    timedOut: result.error?.code === 'ETIMEDOUT',
    wallSeconds,
    stdout: { uri: `${context.roots.evidence}/logs/${prefix}.stdout.log`, sha256: shaBytes(stdout), bytes: stdout.length },
    stderr: { uri: `${context.roots.evidence}/logs/${prefix}.stderr.log`, sha256: shaBytes(stderr), bytes: stderr.length },
  }, 'processHash');
  const expectedArtifact = join(evidenceRoot, mode === 'build' ? 'build.json' : 'reopen.json');
  const successMarker = mode === 'build' ? 'BFS_CAUSAL_STUDIO_BUILD COMPLETE' : 'BFS_CAUSAL_STUDIO_REOPEN COMPLETE';
  const semanticSuccess = result.status === 0 && existsSync(expectedArtifact) && stdout.toString('utf8').includes(successMarker) && !stderr.toString('utf8').includes('Traceback (most recent call last)');
  if (!semanticSuccess) throw Object.assign(new Error(`BLENDER_${mode.toUpperCase()}_SEMANTIC_FAILURE_${result.status}`), { process });
  return process;
}

try {
  const processes = [runBlender(1, 'build'), runBlender(2, 'reopen')];
  const buildPath = join(evidenceRoot, 'build.json');
  const reopenPath = join(evidenceRoot, 'reopen.json');
  const build = JSON.parse(readFileSync(buildPath, 'utf8'));
  const reopen = JSON.parse(readFileSync(reopenPath, 'utf8'));
  const workBytes = dirBytes(workRoot);
  const evidenceBytes = dirBytes(evidenceRoot);
  const receipt = writeRecord(join(evidenceRoot, 'receipt.json'), {
    schemaVersion: 'bfs.causalStudioReceipt.v0.1',
    status: 'EXECUTION_COMPLETE_PENDING_INDEPENDENT_AUDIT_AND_DIRECT_REVIEW',
    preregistration: { uri: specUri, sha256: shaFile(specPath), specHash: spec.specHash },
    context: { uri: contextUri, sha256: shaFile(contextPath), contextHash: context.contextHash },
    toolFreeze: { uri: freezeUri, sha256: shaFile(freezePath), freezeHash: freeze.freezeHash },
    build: { uri: `${context.roots.evidence}/build.json`, sha256: shaFile(buildPath), buildHash: build.buildHash },
    reopen: { uri: `${context.roots.evidence}/reopen.json`, sha256: shaFile(reopenPath), reopenHash: reopen.reopenHash },
    processes: processes.map(row => ({ mode: row.mode, processHash: row.processHash })),
    operations: { blenderStarts: 2, renderCalls: build.reviews.length, retainedReviewPngs: build.reviews.length, networkCalls: 0, externalAssetDownloads: 0, engineMutations: 0, engineRemoteWrites: 0 },
    resources: { freeBytesBefore: freeKiB * 1024, workBytes, evidenceBytesBeforeReceipt: evidenceBytes, workCeiling: spec.resourceCeilings.workRootBytes, evidenceCeiling: spec.resourceCeilings.evidenceRootBytes },
  }, 'receiptHash');
  const rootManifest = writeRecord(join(evidenceRoot, 'root-manifest.json'), {
    schemaVersion: 'bfs.causalStudioRootManifest.v0.1',
    work: manifest(workRoot),
    evidence: manifest(evidenceRoot, new Set(['root-manifest.json'])),
  }, 'manifestHash');
  console.log(`BFS_CAUSAL_STUDIO_EXECUTION_COMPLETE ${receipt.receiptHash} ${rootManifest.manifestHash}`);
} catch (error) {
  const body = {
    schemaVersion: 'bfs.causalStudioFailure.v0.1',
    status: 'FAIL',
    error: String(error?.stack ?? error),
    operationsObserved: { blenderStartsMaximum: readdirSync(join(evidenceRoot, 'processes')).filter(name => name.endsWith('.json')).length, networkCalls: 0, engineMutations: 0, engineRemoteWrites: 0 },
  };
  writeRecord(join(evidenceRoot, 'failure.json'), body, 'failureHash');
  console.error(error);
  process.exitCode = 1;
}
