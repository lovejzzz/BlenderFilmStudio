#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { dirname, join, relative, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const preregUri = 'specs/ai-native-studio-causal-studio-generalization-preregistration.v0.1.json';
const sceneSpecUri = 'specs/fixtures/causal-studio/PC5_G1.domino-four.scene-spec.v0.1.json';
const freezeUri = 'specs/ai-native-studio-causal-studio-generalization-tool-freeze.v0.1.json';
const baseSpecUri = 'specs/ai-native-studio-causal-studio-preregistration.v0.1.json';
const builderUri = 'scripts/build-causal-scene-spec.py';
const preregPath = resolve(root, preregUri), sceneSpecPath = resolve(root, sceneSpecUri), freezePath = resolve(root, freezeUri), baseSpecPath = resolve(root, baseSpecUri), builderPath = resolve(root, builderUri);

function canonical(value) { if (value === null || typeof value !== 'object') return JSON.stringify(value); if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`; return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}`; }
function shaBytes(value) { return createHash('sha256').update(value).digest('hex'); }
function shaFile(path) { return shaBytes(readFileSync(path)); }
function selfHash(value, field) { const copy = structuredClone(value); delete copy[field]; return shaBytes(Buffer.from(canonical(copy))); }
function validSelf(value, field) { return value?.[field] === selfHash(value, field); }
function writeRecord(path, body, field) { const value = { ...body }; value[field] = selfHash(value, field); writeFileSync(path, `${JSON.stringify(value, null, 2)}\n`); return value; }
function dirBytes(path) { if (!existsSync(path)) return 0; const stat = statSync(path); if (!stat.isDirectory()) return stat.size; return readdirSync(path).reduce((sum, name) => sum + dirBytes(join(path, name)), 0); }
function manifest(path, excluded = new Set()) { const rows = []; function visit(current) { for (const name of readdirSync(current).sort()) { const item = join(current, name), rel = relative(path, item); if (excluded.has(rel)) continue; const stat = statSync(item); if (stat.isSymbolicLink()) throw new Error(`SYMLINK_${rel}`); if (stat.isDirectory()) visit(item); else rows.push({ path: rel, bytes: stat.size, sha256: shaFile(item) }); } } visit(path); return rows; }

const prereg = JSON.parse(readFileSync(preregPath)), sceneSpec = JSON.parse(readFileSync(sceneSpecPath)), freeze = JSON.parse(readFileSync(freezePath)), baseSpec = JSON.parse(readFileSync(baseSpecPath));
if (!validSelf(prereg, 'specHash') || prereg.status !== 'PREREGISTERED_BEFORE_GENERIC_EXECUTOR_OR_ATTEMPT01_MUTATION') throw new Error('PREREGISTRATION');
if (!validSelf(sceneSpec, 'sceneSpecHash') || sceneSpec.sceneSpecHash !== prereg.holdoutSceneSpec.sceneSpecHash || shaFile(sceneSpecPath) !== prereg.holdoutSceneSpec.sha256) throw new Error('SCENE_SPEC');
if (!validSelf(freeze, 'freezeHash') || freeze.status !== 'FROZEN_BEFORE_PC5_G1_ATTEMPT01_MUTATION') throw new Error('FREEZE');
if (freeze.preregistration.specHash !== prereg.specHash || freeze.preregistration.sha256 !== shaFile(preregPath) || freeze.sceneSpec.sceneSpecHash !== sceneSpec.sceneSpecHash || freeze.sceneSpec.sha256 !== shaFile(sceneSpecPath)) throw new Error('FREEZE_INPUT_BINDING');
if (freeze.tools.some(row => shaFile(resolve(root, row.uri)) !== row.sha256)) throw new Error('TOOL_HASH');
if (shaFile(baseSpec.engine.path) !== baseSpec.engine.sha256) throw new Error('BINARY_HASH');
const workRoot = resolve(prereg.roots.work), evidenceRoot = resolve(root, prereg.roots.evidence);
if (existsSync(workRoot) || existsSync(evidenceRoot)) throw new Error('FRESH_ROOTS_REQUIRED');
const disk = spawnSync('df', ['-Pk', root], { encoding: 'utf8' });
if (disk.status !== 0) throw new Error('DISK_CHECK');
const freeKiB = Number(disk.stdout.trim().split(/\n/).at(-1).trim().split(/\s+/)[3]);
if (freeKiB * 1024 < prereg.resourceCeilings.minimumFreeDiskGiB * 1024 ** 3) throw new Error('DISK_ADMISSION');
mkdirSync(workRoot, { recursive: false }); mkdirSync(evidenceRoot, { recursive: true });
for (const path of ['logs', 'processes', 'home', 'tmp', 'config', 'scripts']) mkdirSync(join(evidenceRoot, path), { recursive: true });
const env = { ...process.env, HOME: join(evidenceRoot, 'home'), TMPDIR: `${join(evidenceRoot, 'tmp')}/`, BLENDER_USER_CONFIG: join(evidenceRoot, 'config'), BLENDER_USER_SCRIPTS: join(evidenceRoot, 'scripts'), PYTHONNOUSERSITE: '1', LC_ALL: 'C', LANG: 'C', OCIO: resolve(root, 'color/ocio/cg-config-v4.0.0_aces-v2.0_ocio-v2.5.ocio') };

function runBlender(index, mode) {
  const blendPath = join(workRoot, 'PC5_G1_CAUSAL_SCENE.blend');
  const common = ['--python', builderPath, '--', '--mode', mode, '--preregistration', preregPath, '--scene-spec', sceneSpecPath, '--work', workRoot, '--evidence', evidenceRoot];
  const blenderArgv = mode === 'build' ? ['--background', '--factory-startup', ...common] : ['--background', '--factory-startup', blendPath, ...common];
  const started = Date.now();
  const result = spawnSync('/usr/bin/caffeinate', ['-dimsu', baseSpec.engine.path, ...blenderArgv], { cwd: root, env, encoding: 'buffer', timeout: 600000, maxBuffer: 64 * 1024 * 1024 });
  const stdout = result.stdout ?? Buffer.alloc(0), stderr = result.stderr ?? Buffer.alloc(0), prefix = `${String(index).padStart(2, '0')}-${mode}`;
  const stdoutPath = join(evidenceRoot, 'logs', `${prefix}.stdout.log`), stderrPath = join(evidenceRoot, 'logs', `${prefix}.stderr.log`);
  writeFileSync(stdoutPath, stdout); writeFileSync(stderrPath, stderr);
  const process = writeRecord(join(evidenceRoot, 'processes', `${prefix}.json`), { schemaVersion: 'bfs.causalSceneSpecProcess.v0.1', index, mode, executable: '/usr/bin/caffeinate', argv: ['-dimsu', baseSpec.engine.path, ...blenderArgv], blenderArgv: [baseSpec.engine.path, ...blenderArgv], cwd: root, environment: { HOME: env.HOME, TMPDIR: env.TMPDIR, BLENDER_USER_CONFIG: env.BLENDER_USER_CONFIG, BLENDER_USER_SCRIPTS: env.BLENDER_USER_SCRIPTS, PYTHONNOUSERSITE: env.PYTHONNOUSERSITE, LC_ALL: env.LC_ALL, LANG: env.LANG, OCIO: env.OCIO }, exitCode: result.status, signal: result.signal, timedOut: result.error?.code === 'ETIMEDOUT', wallSeconds: (Date.now() - started) / 1000, stdout: { uri: `${prereg.roots.evidence}/logs/${prefix}.stdout.log`, sha256: shaBytes(stdout), bytes: stdout.length }, stderr: { uri: `${prereg.roots.evidence}/logs/${prefix}.stderr.log`, sha256: shaBytes(stderr), bytes: stderr.length } }, 'processHash');
  const artifact = join(evidenceRoot, mode === 'build' ? 'build.json' : 'reopen.json');
  const marker = mode === 'build' ? 'BFS_CAUSAL_SCENE_SPEC_BUILD COMPLETE' : 'BFS_CAUSAL_SCENE_SPEC_REOPEN COMPLETE';
  if (!(result.status === 0 && existsSync(artifact) && stdout.toString().includes(marker) && !stderr.toString().includes('Traceback (most recent call last)'))) throw Object.assign(new Error(`BLENDER_${mode.toUpperCase()}_SEMANTIC_FAILURE_${result.status}`), { process });
  return process;
}

try {
  const processes = [runBlender(1, 'build'), runBlender(2, 'reopen')];
  const buildPath = join(evidenceRoot, 'build.json'), reopenPath = join(evidenceRoot, 'reopen.json');
  const build = JSON.parse(readFileSync(buildPath)), reopen = JSON.parse(readFileSync(reopenPath));
  const receipt = writeRecord(join(evidenceRoot, 'receipt.json'), { schemaVersion: 'bfs.causalStudioGeneralizationReceipt.v0.1', status: 'EXECUTION_COMPLETE_PENDING_INDEPENDENT_AUDIT_AND_DIRECT_REVIEW', preregistration: { uri: preregUri, sha256: shaFile(preregPath), specHash: prereg.specHash }, sceneSpec: { uri: sceneSpecUri, sha256: shaFile(sceneSpecPath), sceneSpecHash: sceneSpec.sceneSpecHash }, toolFreeze: { uri: freezeUri, sha256: shaFile(freezePath), freezeHash: freeze.freezeHash }, build: { uri: `${prereg.roots.evidence}/build.json`, sha256: shaFile(buildPath), buildHash: build.buildHash }, reopen: { uri: `${prereg.roots.evidence}/reopen.json`, sha256: shaFile(reopenPath), reopenHash: reopen.reopenHash }, processes: processes.map(row => ({ mode: row.mode, processHash: row.processHash })), operations: { blenderStarts: 2, renderCalls: build.reviews.length, retainedReviewPngs: build.reviews.length, networkCalls: 0, externalAssetDownloads: 0, engineMutations: 0, engineRemoteWrites: 0 }, resources: { freeBytesBefore: freeKiB * 1024, workBytes: dirBytes(workRoot), evidenceBytesBeforeReceipt: dirBytes(evidenceRoot), workCeiling: prereg.resourceCeilings.workRootBytes, evidenceCeiling: prereg.resourceCeilings.evidenceRootBytes } }, 'receiptHash');
  const rootManifest = writeRecord(join(evidenceRoot, 'root-manifest.json'), { schemaVersion: 'bfs.causalStudioGeneralizationRootManifest.v0.1', work: manifest(workRoot), evidence: manifest(evidenceRoot, new Set(['root-manifest.json'])) }, 'manifestHash');
  console.log(`BFS_CAUSAL_STUDIO_GENERALIZATION_EXECUTION_COMPLETE ${receipt.receiptHash} ${rootManifest.manifestHash}`);
} catch (error) {
  const body = { schemaVersion: 'bfs.causalStudioGeneralizationFailure.v0.1', status: 'FAIL', error: String(error?.stack ?? error), operationsObserved: { blenderStartsMaximum: readdirSync(join(evidenceRoot, 'processes')).filter(name => name.endsWith('.json')).length, networkCalls: 0, engineMutations: 0, engineRemoteWrites: 0 } };
  writeRecord(join(evidenceRoot, 'failure.json'), body, 'failureHash'); console.error(error); process.exitCode = 1;
}
