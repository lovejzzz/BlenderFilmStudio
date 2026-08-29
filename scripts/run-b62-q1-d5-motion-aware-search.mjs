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
const SPEC_URI = 'specs/b62-camera-quality-motion-aware-search.v0.1.json';
const PROTOCOL_URI = 'research/2026-08-29-b62-d5-motion-aware-camera-search-protocol.md';
const C1_URI = 'specs/b62-camera-quality-d5-c1-probe-camera-transform-sync.v0.1.json';
const C1_PROTOCOL_URI = 'research/2026-08-29-b62-d5-c1-probe-camera-transform-sync.md';
const C2_URI = 'specs/b62-camera-quality-d5-c2-retire-contaminated-d3-baseline.v0.1.json';
const C2_PROTOCOL_URI = 'research/2026-08-29-b62-d5-c2-retire-contaminated-d3-baseline.md';
const C3_URI = 'specs/b62-camera-quality-d5-c3-v02-comparison-hash-typo.v0.1.json';
const C3_PROTOCOL_URI = 'research/2026-08-29-b62-d5-c3-v02-comparison-hash-typo.md';
const ROOT_URI = 'experiments/b62-camera-quality-motion-aware-search-v0-3';
const V0_1_ROOT = 'experiments/b62-camera-quality-motion-aware-search-v0-1';
const V0_2_ROOT = 'experiments/b62-camera-quality-motion-aware-search-v0-2';
const D4_ROOT = 'experiments/b62-camera-quality-holdout-render-v0-5';
const D3_ROOT = 'experiments/b62-camera-quality-bounded-candidate-search-v0-2';
const PREREGISTRATION_COMMIT = '4011fb8bcb231931d495052ea213fdf044ddc3b1';
const C1_COMMIT = 'f341fec5b215d9f66dbfcdacbd963ab1a9340178';
const C2_COMMIT = '3ca15d0af78bc646db1837f7358f5416d245cefb';
const C3_COMMIT = 'c1fbf375d3fe81b67fc1ab9014142f76606b33e8';
const C1_TOOL_FREEZE_COMMIT = '65e72d7f3c1454b01a7f6d52724c12a8d569f171';
const TOOLS = [
  'blender/search_b62_q1_d5_motion_aware_camera.py',
  'blender/search_b62_q1_d5_motion_aware_camera_independent.py',
  'scripts/run-b62-q1-d5-motion-aware-search.mjs',
  'scripts/audit-b62-q1-d5-motion-aware-search.mjs',
];

function canonicalize(value) { if (Array.isArray(value)) return value.map(canonicalize); if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).sort(([a], [b]) => a.localeCompare(b)).map(([key, child]) => [key, canonicalize(child)])); return value; }
const canonicalJson = value => JSON.stringify(canonicalize(value));
const hashBytes = value => createHash('sha256').update(value).digest('hex');
const hashFile = async path => hashBytes(await readFile(path));
function requireValue(condition, message) { if (!condition) throw new Error(message); }
function localPath(uri) { requireValue(uri && !uri.startsWith('/') && !uri.split('/').includes('..'), `unsafe ${uri}`); const path = resolve(repositoryRoot, uri); requireValue(!relative(repositoryRoot, path).startsWith('../'), `escaped ${uri}`); return path; }
async function exists(path) { try { await lstat(path); return true; } catch (error) { if (error.code === 'ENOENT') return false; throw error; } }
async function git(args, encoding = 'utf8') { return (await execFileAsync('/usr/bin/git', args, { cwd: repositoryRoot, encoding, timeout: 15000, maxBuffer: 32 * 1024 * 1024, env: { PATH: '/usr/bin:/bin', LANG: 'C', LC_ALL: 'C', GIT_CONFIG_NOSYSTEM: '1', GIT_TERMINAL_PROMPT: '0' } })).stdout; }
async function committedHash(commit, uri) { return hashBytes(await git(['show', `${commit}:${uri}`], null)); }
async function committedBytes(commit, uri) { return git(['show', `${commit}:${uri}`], null); }
async function writeHashed(path, value, field) { const body = structuredClone(value); body[field] = hashBytes(canonicalJson(body)); const handle = await open(path, 'wx', 0o600); try { await handle.writeFile(`${JSON.stringify(body, null, 2)}\n`); await handle.sync(); } finally { await handle.close(); } return body; }
function validSelfHash(value, field) { if (!value || !/^[0-9a-f]{64}$/.test(value[field] ?? '')) return false; const copy = structuredClone(value); const expected = copy[field]; delete copy[field]; return hashBytes(canonicalJson(copy)) === expected; }

async function treeIdentity(uri) {
  const root = localPath(uri), files = [];
  async function walk(directory) { for (const entry of await readdir(directory, { withFileTypes: true })) { const path = resolve(directory, entry.name); if (entry.isDirectory()) await walk(path); else if (entry.isFile()) files.push(path); else throw new Error(`special file ${path}`); } }
  await walk(root); files.sort(); let bytes = 0, material = '';
  for (const path of files) { const content = await readFile(path); bytes += content.length; material += `${relative(root, path).split('\\').join('/')}\0${hashBytes(content)}\n`; }
  return { files: files.length, bytes, treeSha256: hashBytes(Buffer.from(material)) };
}

function parseArgs() { const args = process.argv.slice(2); requireValue(args.length === 2 && args[0] === '--tool-freeze-commit' && /^[0-9a-f]{40}$/.test(args[1]), 'usage: --tool-freeze-commit <sha>'); return args[1]; }
async function processReceipt(root, id, command, args, result) { return writeHashed(resolve(root, 'processes', `${id}.json`), { schemaVersion: 'bfs.b62CameraQualityProcessReceipt.v0.1', experimentId: 'B62-Q1-D5', processId: id, command, args, result }, 'processHash'); }

async function blenderChild(root, id, tool, output, master, masterSha, spec) {
  const command = spec.runtime.blender.executable;
  const args = ['--background', '--factory-startup', '--disable-autoexec', master, '--python-exit-code', '1', '--python', localPath(tool), '--', '--output', resolve(root, output), '--master-sha256', masterSha];
  const result = await runBudgetedProcess({
    command, args, cwd: repositoryRoot,
    env: { PATH: '/usr/bin:/bin', LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8', OCIO: resolve(repositoryRoot, 'color/ocio/cg-config-v4.0.0_aces-v2.0_ocio-v2.5.ocio') },
    outputRoot: root,
    budgets: { wallTimeMs: spec.processBudget.maximumWallSecondsPerBlender * 1000, maxRssBytes: spec.processBudget.maximumPeakResidentSetSizeBytesPerBlender, maxLogBytes: spec.processBudget.maximumCombinedLogBytesPerChild, maxOutputFiles: 64, maxOutputBytes: spec.processBudget.projectedWriteBytes, sampleIntervalMs: 100 },
  });
  const receipt = await processReceipt(root, id, command, args.map(value => value.startsWith(repositoryRoot) ? relative(repositoryRoot, value).split('\\').join('/') : value), result);
  requireValue(result.outcome === 'PASS' && result.child.exitCode === 0 && result.breach === null && await exists(resolve(root, output)), `${id} failed`);
  return receipt;
}

async function main() {
  const freeze = parseArgs();
  const spec = JSON.parse(await readFile(localPath(SPEC_URI), 'utf8'));
  const c1 = JSON.parse(await readFile(localPath(C1_URI), 'utf8'));
  const c2 = JSON.parse(await readFile(localPath(C2_URI), 'utf8'));
  const c3 = JSON.parse(await readFile(localPath(C3_URI), 'utf8'));
  requireValue(spec.experimentId === 'B62-Q1-D5' && spec.statusBeforeToolCreation === 'PREREGISTERED' && spec.output.formalRoot === V0_1_ROOT, 'spec mismatch');
  requireValue(c1.correctionId === 'B62-Q1-D5-C1' && c1.statusBeforeToolChange === 'PREREGISTERED' && c1.retainedFailure.root === V0_1_ROOT && c1.authorizedChanges.retryRoot === V0_2_ROOT, 'C1 mismatch');
  requireValue(c2.correctionId === 'B62-Q1-D5-C2' && c2.statusBeforeToolChange === 'PREREGISTERED' && c2.retainedFailures.v0_1.root === V0_1_ROOT && c2.retainedFailures.v0_2.root === V0_2_ROOT && c2.authorizedChanges.retryRoot === ROOT_URI, 'C2 mismatch');
  requireValue(c3.correctionId === 'B62-Q1-D5-C3' && c3.statusBeforeNodeToolChange === 'PREREGISTERED' && c3.preAdmissionRejection.formalRootCreated === false && c3.authorizedChanges.retryRoot === ROOT_URI, 'C3 mismatch');
  requireValue(!await exists(localPath(ROOT_URI)), 'formal root exists');
  const head = (await git(['rev-parse', 'HEAD'])).trim(), origin = (await git(['rev-parse', 'origin/main'])).trim();
  requireValue(head === freeze && origin === freeze, 'freeze not pushed HEAD');
  await git(['merge-base', '--is-ancestor', PREREGISTRATION_COMMIT, freeze]);
  await git(['merge-base', '--is-ancestor', C1_COMMIT, freeze]);
  await git(['merge-base', '--is-ancestor', C2_COMMIT, freeze]);
  await git(['merge-base', '--is-ancestor', C3_COMMIT, freeze]);
  requireValue(await hashFile(localPath(SPEC_URI)) === await committedHash(PREREGISTRATION_COMMIT, SPEC_URI), 'spec drift');
  requireValue(await hashFile(localPath(PROTOCOL_URI)) === await committedHash(PREREGISTRATION_COMMIT, PROTOCOL_URI), 'protocol drift');
  requireValue(await hashFile(localPath(C1_URI)) === await committedHash(C1_COMMIT, C1_URI) && await hashFile(localPath(C1_PROTOCOL_URI)) === await committedHash(C1_COMMIT, C1_PROTOCOL_URI), 'C1 drift');
  requireValue(await hashFile(localPath(C2_URI)) === await committedHash(C2_COMMIT, C2_URI) && await hashFile(localPath(C2_PROTOCOL_URI)) === await committedHash(C2_COMMIT, C2_PROTOCOL_URI), 'C2 drift');
  requireValue(await hashFile(localPath(C3_URI)) === await committedHash(C3_COMMIT, C3_URI) && await hashFile(localPath(C3_PROTOCOL_URI)) === await committedHash(C3_COMMIT, C3_PROTOCOL_URI), 'C3 drift');
  const toolHashes = {};
  for (const uri of TOOLS) { toolHashes[uri] = await hashFile(localPath(uri)); requireValue(toolHashes[uri] === await committedHash(freeze, uri), `tool drift ${uri}`); }
  requireValue(c2.frozenBeforeCorrection.toolFreezeCommit === C1_TOOL_FREEZE_COMMIT, 'C2 tool freeze mismatch');
  requireValue(await committedHash(C1_TOOL_FREEZE_COMMIT, TOOLS[0]) === c2.frozenBeforeCorrection.primaryBlenderToolSha256 && await committedHash(C1_TOOL_FREEZE_COMMIT, TOOLS[1]) === c2.frozenBeforeCorrection.independentBlenderToolSha256, 'C2 frozen Blender tools mismatch');
  const oldPrimary = (await committedBytes(C1_TOOL_FREEZE_COMMIT, TOOLS[0])).toString('utf8');
  const oldIndependent = (await committedBytes(C1_TOOL_FREEZE_COMMIT, TOOLS[1])).toString('utf8');
  const expectedPrimary = oldPrimary.replace('                    bpy.context.view_layer.update()\n                    frames.append({"frame": frame, "radialScale": scale, **measure', '                    bpy.context.view_layer.update()\n                    evaluated_matrix = camera.matrix_world.copy()\n                    frames.append({"frame": frame, "radialScale": scale, "evaluatedCameraLocation": [float(value) for value in evaluated_matrix.translation], "evaluatedCameraQuaternion": [float(value) for value in evaluated_matrix.to_quaternion()], **measure');
  const expectedIndependent = oldIndependent.replace('                    bpy.context.view_layer.update()\n                    frame_rows.append({"frame": frame, "radialScale": current_scale, **observe_candidate_frame', '                    bpy.context.view_layer.update()\n                    evaluated_transform = probe_camera.matrix_world.copy()\n                    frame_rows.append({"frame": frame, "radialScale": current_scale, "evaluatedCameraLocation": [float(value) for value in evaluated_transform.translation], "evaluatedCameraQuaternion": [float(value) for value in evaluated_transform.to_quaternion()], **observe_candidate_frame');
  requireValue(expectedPrimary !== oldPrimary && expectedIndependent !== oldIndependent, 'C2 insertion anchor missing');
  requireValue((await readFile(localPath(TOOLS[0]), 'utf8')) === expectedPrimary && (await readFile(localPath(TOOLS[1]), 'utf8')) === expectedIndependent, 'C2 Blender correction scope exceeded');
  requireValue((await git(['status', '--porcelain=v1', '--', SPEC_URI, PROTOCOL_URI, C1_URI, C1_PROTOCOL_URI, C2_URI, C2_PROTOCOL_URI, C3_URI, C3_PROTOCOL_URI, V0_1_ROOT, V0_2_ROOT, D4_ROOT, D3_ROOT, ...TOOLS])).trim() === '', 'scoped dirty');

  const retainedV01Tree = await treeIdentity(V0_1_ROOT), retainedV02Tree = await treeIdentity(V0_2_ROOT);
  requireValue(canonicalJson(retainedV01Tree) === canonicalJson(c2.retainedFailures.v0_1.tree) && canonicalJson(retainedV02Tree) === canonicalJson(c2.retainedFailures.v0_2.tree), 'retained D5 tree drift');
  requireValue(await hashFile(localPath(c2.retainedFailures.v0_2.failure.uri)) === c2.retainedFailures.v0_2.failure.sha256 && await hashFile(localPath(c2.retainedFailures.v0_2.audit.uri)) === c2.retainedFailures.v0_2.audit.sha256 && await hashFile(localPath(c3.correctValue.uri)) === c3.correctValue.sha256, 'retained D5 v0.2 evidence drift');

  const d4Tree = await treeIdentity(D4_ROOT);
  requireValue(canonicalJson(d4Tree) === canonicalJson(spec.parentEvidence.d4Formal.tree), 'D4 tree drift');
  const d4ReceiptPath = localPath(spec.parentEvidence.d4Formal.receipt.uri);
  const d4AuditPath = localPath(spec.parentEvidence.d4Formal.audit.uri);
  requireValue(await hashFile(d4ReceiptPath) === spec.parentEvidence.d4Formal.receipt.sha256 && await hashFile(d4AuditPath) === spec.parentEvidence.d4Formal.audit.sha256, 'D4 receipt/audit drift');
  const d4Receipt = JSON.parse(await readFile(d4ReceiptPath, 'utf8'));
  const d4Audit = JSON.parse(await readFile(d4AuditPath, 'utf8'));
  requireValue(d4Receipt.receiptHash === spec.parentEvidence.d4Formal.receipt.receiptHash && d4Audit.auditHash === spec.parentEvidence.d4Formal.audit.auditHash && d4Audit.scientificVerdict === spec.parentEvidence.d4Formal.audit.scientificVerdict, 'D4 evidence invalid');
  const d4BuildPath = localPath(c2.authoritativeBaseline.d4BuildReport.uri);
  const d4Build = JSON.parse(await readFile(d4BuildPath, 'utf8'));
  requireValue(await hashFile(d4BuildPath) === c2.authoritativeBaseline.d4BuildReport.sha256 && d4Build.reportHash === c2.authoritativeBaseline.d4BuildReport.reportHash && d4Build.candidateId === c2.authoritativeBaseline.d4BuildReport.candidateId && d4Build.bake.length === c2.authoritativeBaseline.d4BuildReport.bakeFrameCount, 'D4 build baseline drift');
  const d3Tree = await treeIdentity(D3_ROOT);
  requireValue(canonicalJson(d3Tree) === canonicalJson(spec.parentEvidence.d3Search.tree), 'D3 tree drift');
  const d3Primary = JSON.parse(await readFile(localPath(`${D3_ROOT}/primary.json`), 'utf8'));
  requireValue(d3Primary.selectedCandidateId === spec.parentEvidence.d3Search.selectedCandidateId, 'D3 selection drift');
  const master = localPath(spec.parentEvidence.masterScene.uri), masterSha = await hashFile(master);
  requireValue(masterSha === spec.parentEvidence.masterScene.sha256, 'master drift');
  requireValue(await hashFile(spec.runtime.blender.executable) === spec.runtime.blender.sha256, 'Blender drift');
  const filesystem = await statfs(repositoryRoot), available = Number(filesystem.bavail) * Number(filesystem.bsize);
  requireValue(available - spec.processBudget.projectedWriteBytes >= spec.processBudget.minimumFreeReserveBytes, 'disk reserve');

  const root = localPath(ROOT_URI);
  await mkdir(resolve(root, 'processes'), { recursive: true, mode: 0o700 });
  const admission = await writeHashed(resolve(root, 'admission.json'), {
    schemaVersion: 'bfs.b62CameraQualityMotionAwareAdmission.v0.1', experimentId: spec.experimentId, status: 'ADMITTED',
    preregistrationCommit: PREREGISTRATION_COMMIT, correctionCommits: [C1_COMMIT, C2_COMMIT, C3_COMMIT], toolFreezeCommit: freeze,
    bindings: {
      spec: { uri: SPEC_URI, sha256: await hashFile(localPath(SPEC_URI)) },
      protocol: { uri: PROTOCOL_URI, sha256: await hashFile(localPath(PROTOCOL_URI)) },
      c1: { uri: C1_URI, sha256: await hashFile(localPath(C1_URI)) },
      c1Protocol: { uri: C1_PROTOCOL_URI, sha256: await hashFile(localPath(C1_PROTOCOL_URI)) },
      c2: { uri: C2_URI, sha256: await hashFile(localPath(C2_URI)) },
      c2Protocol: { uri: C2_PROTOCOL_URI, sha256: await hashFile(localPath(C2_PROTOCOL_URI)) },
      c3: { uri: C3_URI, sha256: await hashFile(localPath(C3_URI)) },
      c3Protocol: { uri: C3_PROTOCOL_URI, sha256: await hashFile(localPath(C3_PROTOCOL_URI)) },
      retainedV01Tree, retainedV02Tree,
      retainedV02FailureSha256: await hashFile(localPath(c2.retainedFailures.v0_2.failure.uri)),
      retainedV02AuditSha256: await hashFile(localPath(c2.retainedFailures.v0_2.audit.uri)),
      retainedV02ComparisonSha256: await hashFile(localPath(c3.correctValue.uri)),
      correctionScopeExact: true, c2FrozenToolHashes: {
        [TOOLS[0]]: c2.frozenBeforeCorrection.primaryBlenderToolSha256,
        [TOOLS[1]]: c2.frozenBeforeCorrection.independentBlenderToolSha256,
        [TOOLS[2]]: c2.frozenBeforeCorrection.runnerSha256,
        [TOOLS[3]]: c2.frozenBeforeCorrection.auditorSha256,
      },
      d4Tree, d4ReceiptSha256: await hashFile(d4ReceiptPath), d4AuditSha256: await hashFile(d4AuditPath), d4BuildSha256: await hashFile(d4BuildPath),
      d3Tree, d3PrimarySha256: await hashFile(localPath(`${D3_ROOT}/primary.json`)),
      master: { uri: spec.parentEvidence.masterScene.uri, sha256: masterSha },
      blenderSha256: await hashFile(spec.runtime.blender.executable), tools: toolHashes,
    },
    resources: { availableBytesBefore: available, projectedWriteBytes: spec.processBudget.projectedWriteBytes, minimumFreeReserveBytes: spec.processBudget.minimumFreeReserveBytes },
    operations: { blenderStartsBeforeAdmission: 0, renderCalls: 0, modelCalls: 0, networkCalls: 0, dockerProcesses: 0 },
  }, 'admissionHash');

  try {
    const primaryProcess = await blenderChild(root, 'PRIMARY', TOOLS[0], 'primary.json', master, masterSha, spec);
    const independentProcess = await blenderChild(root, 'INDEPENDENT', TOOLS[1], 'independent.json', master, masterSha, spec);
    const auditorArgs = [localPath(TOOLS[3]), '--root', ROOT_URI, '--tool-freeze-commit', freeze];
    const result = await runBudgetedProcess({
      command: process.execPath, args: auditorArgs, cwd: repositoryRoot,
      env: { PATH: '/usr/bin:/bin', LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8' }, outputRoot: root,
      budgets: { wallTimeMs: 60000, maxRssBytes: 1073741824, maxLogBytes: 1048576, maxOutputFiles: 64, maxOutputBytes: spec.processBudget.projectedWriteBytes, sampleIntervalMs: 100 },
    });
    const auditorProcess = await processReceipt(root, 'AUDITOR', process.execPath, auditorArgs.map(value => value.startsWith(repositoryRoot) ? relative(repositoryRoot, value).split('\\').join('/') : value), result);
    requireValue(result.outcome === 'PASS' && result.child.exitCode === 0 && result.breach === null, 'auditor failed');
    const auditPath = resolve(root, 'audit.json'), comparisonPath = resolve(root, 'comparison.json');
    const audit = JSON.parse(await readFile(auditPath, 'utf8')), comparison = JSON.parse(await readFile(comparisonPath, 'utf8'));
    requireValue(validSelfHash(audit, 'auditHash') && audit.status === 'PASS' && validSelfHash(comparison, 'comparisonHash') && comparison.status === 'PASS', 'audit outputs invalid');
    const receipt = await writeHashed(resolve(root, 'receipt.json'), {
      schemaVersion: 'bfs.b62CameraQualityMotionAwareSearchReceipt.v0.1', experimentId: spec.experimentId,
      status: 'PASS', scientificVerdict: audit.scientificVerdict, selectedCandidateId: audit.selectedCandidateId,
      admission: { uri: `${ROOT_URI}/admission.json`, sha256: await hashFile(resolve(root, 'admission.json')), admissionHash: admission.admissionHash },
      comparison: { uri: `${ROOT_URI}/comparison.json`, sha256: await hashFile(comparisonPath), comparisonHash: comparison.comparisonHash },
      audit: { uri: `${ROOT_URI}/audit.json`, sha256: await hashFile(auditPath), auditHash: audit.auditHash },
      processes: {
        primary: { uri: `${ROOT_URI}/processes/PRIMARY.json`, sha256: await hashFile(resolve(root, 'processes/PRIMARY.json')), processHash: primaryProcess.processHash },
        independent: { uri: `${ROOT_URI}/processes/INDEPENDENT.json`, sha256: await hashFile(resolve(root, 'processes/INDEPENDENT.json')), processHash: independentProcess.processHash },
        auditor: { uri: `${ROOT_URI}/processes/AUDITOR.json`, sha256: await hashFile(resolve(root, 'processes/AUDITOR.json')), processHash: auditorProcess.processHash },
      },
      operations: { runnerProcesses: 1, blenderStarts: 2, renderCalls: 0, nodeAuditorProcesses: 1, modelCalls: 0, networkCalls: 0, dockerProcesses: 0 },
      nonClaims: spec.nonClaims,
    }, 'receiptHash');
    console.log(`BFS_B62_Q1_D5 PASS ${receipt.scientificVerdict} ${receipt.selectedCandidateId ?? 'NONE'} ${receipt.receiptHash}`);
  } catch (error) {
    if (!await exists(resolve(root, 'failure.json'))) await writeHashed(resolve(root, 'failure.json'), { schemaVersion: 'bfs.b62CameraQualityFailure.v0.1', experimentId: spec.experimentId, status: 'INVALIDATED', scientificVerdict: null, toolFreezeCommit: freeze, reason: error.message }, 'failureHash');
    throw error;
  }
}

main().catch(error => { console.error(error.stack ?? error.message); process.exitCode = 1; });
