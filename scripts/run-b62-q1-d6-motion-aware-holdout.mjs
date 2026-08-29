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
const SPEC_URI = 'specs/b62-camera-quality-motion-aware-holdout-validation.v0.1.json';
const PROTOCOL_URI = 'research/2026-08-29-b62-d6-motion-aware-holdout-validation-protocol.md';
const CORRECTION_URI = 'specs/b62-camera-quality-d6-c1-native-ocio-runtime.v0.1.json';
const CORRECTION_PROTOCOL_URI = 'research/2026-08-29-b62-d6-c1-native-ocio-runtime.md';
const ROOT_URI = 'experiments/b62-camera-quality-motion-aware-holdout-v0-2';
const RETAINED_ROOT = 'experiments/b62-camera-quality-motion-aware-holdout-v0-1';
const PARENT_ROOT = 'experiments/b62-camera-quality-motion-aware-search-v0-4';
const PREREGISTRATION_COMMIT = 'd33b0144e231e663303848167e1758af4b9022bc';
const CORRECTION_COMMIT = '3d1c1f0c92c53fbf833612028353cd0693a74298';
const TOOLS = ['blender/build_b62_q1_d6_motion_aware_scene.py', 'blender/render_b62_q1_d6_motion_aware_holdout_pairs.py', 'blender/audit_b62_q1_d6_motion_aware_scene_and_pixels.py', 'scripts/run-b62-q1-d6-motion-aware-holdout.mjs', 'scripts/audit-b62-q1-d6-motion-aware-holdout.mjs'];

function normalize(value) { if (typeof value === 'number' && Number.isFinite(value) && Number.isInteger(value)) return value; if (typeof value === 'number' && Number.isFinite(value)) { const bytes = Buffer.alloc(8); bytes.writeDoubleBE(value); return { $f64be: bytes.toString('hex') }; } if (Array.isArray(value)) return value.map(normalize); if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).sort(([a], [b]) => a.localeCompare(b)).map(([key, child]) => [key, normalize(child)])); return value; }
const canonicalJson = value => JSON.stringify(normalize(value));
const hashBytes = value => createHash('sha256').update(value).digest('hex');
const hashFile = async path => hashBytes(await readFile(path));
function req(condition, message) { if (!condition) throw new Error(message); }
function pathFor(uri) { req(uri && !uri.startsWith('/') && !uri.split('/').includes('..'), `unsafe ${uri}`); const path = resolve(repositoryRoot, uri); req(!relative(repositoryRoot, path).startsWith('../'), `escaped ${uri}`); return path; }
async function exists(path) { try { await lstat(path); return true; } catch (error) { if (error.code === 'ENOENT') return false; throw error; } }
async function git(args, encoding = 'utf8') { return (await execFileAsync('/usr/bin/git', args, { cwd: repositoryRoot, encoding, timeout: 15000, maxBuffer: 32 * 1024 * 1024, env: { PATH: '/usr/bin:/bin', LANG: 'C', LC_ALL: 'C', GIT_CONFIG_NOSYSTEM: '1', GIT_TERMINAL_PROMPT: '0' } })).stdout; }
async function committedHash(commit, uri) { return hashBytes(await git(['show', `${commit}:${uri}`], null)); }
async function writeHashed(path, value, field) { const body = structuredClone(value); body[field] = hashBytes(canonicalJson(body)); const handle = await open(path, 'wx', 0o600); try { await handle.writeFile(`${JSON.stringify(body, null, 2)}\n`); await handle.sync(); } finally { await handle.close(); } return body; }
function validSelf(value, field) { if (!value || !/^[0-9a-f]{64}$/.test(value[field] ?? '')) return false; const copy = structuredClone(value), expected = copy[field]; delete copy[field]; return hashBytes(canonicalJson(copy)) === expected; }
async function treeIdentity(uri) { const root = pathFor(uri), files = []; async function walk(directory) { for (const entry of await readdir(directory, { withFileTypes: true })) { const path = resolve(directory, entry.name); if (entry.isDirectory()) await walk(path); else if (entry.isFile()) files.push(path); else throw new Error(`special file ${path}`); } } await walk(root); files.sort(); let bytes = 0, material = ''; for (const path of files) { const content = await readFile(path); bytes += content.length; material += `${relative(root, path).split('\\').join('/')}\0${hashBytes(content)}\n`; } return { files: files.length, bytes, treeSha256: hashBytes(Buffer.from(material)) }; }
function parse() { const args = process.argv.slice(2); req(args.length === 2 && args[0] === '--tool-freeze-commit' && /^[0-9a-f]{40}$/.test(args[1]), 'usage: --tool-freeze-commit <sha>'); return args[1]; }
async function processReceipt(root, id, command, args, result) { return writeHashed(resolve(root, 'processes', `${id}.json`), { schemaVersion: 'bfs.b62CameraQualityProcessReceipt.v0.1', experimentId: 'B62-Q1-D6', processId: id, command, args, result }, 'processHash'); }

let spec;
async function blenderChild({ root, id, scene, tool, args, wallSeconds }) {
  const command = spec.runtime.blender.executable;
  const full = ['--background', '--factory-startup', '--disable-autoexec', scene, '--python-exit-code', '1', '--python', pathFor(tool), '--', ...args];
  const result = await runBudgetedProcess({ command, args: full, cwd: repositoryRoot, env: { PATH: '/usr/bin:/bin', LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8' }, outputRoot: root, budgets: { wallTimeMs: wallSeconds * 1000, maxRssBytes: spec.processBudget.maximumPeakResidentSetSizeBytesPerBlender, maxLogBytes: spec.processBudget.maximumCombinedLogBytesPerChild, maxOutputFiles: 256, maxOutputBytes: spec.processBudget.projectedWriteBytes, sampleIntervalMs: 100 } });
  const receipt = await processReceipt(root, id, command, full.map(value => value.startsWith(repositoryRoot) ? relative(repositoryRoot, value).split('\\').join('/') : value), result);
  req(result.outcome === 'PASS' && result.child.exitCode === 0 && result.breach === null, `${id} failed`);
  return receipt;
}

async function main() {
  const freeze = parse();
  spec = JSON.parse(await readFile(pathFor(SPEC_URI), 'utf8'));
  const correction = JSON.parse(await readFile(pathFor(CORRECTION_URI), 'utf8'));
  req(spec.experimentId === 'B62-Q1-D6' && spec.statusBeforeToolCreation === 'PREREGISTERED' && spec.output.formalRoot === RETAINED_ROOT, 'spec mismatch');
  req(correction.correctionId === 'B62-Q1-D6-C1' && correction.statusBeforeToolChange === 'PREREGISTERED' && correction.retainedFailure.root === RETAINED_ROOT && correction.authorizedChanges.retryRoot === ROOT_URI, 'correction mismatch');
  req(!await exists(pathFor(ROOT_URI)), 'formal root exists');
  const head = (await git(['rev-parse', 'HEAD'])).trim(), origin = (await git(['rev-parse', 'origin/main'])).trim();
  req(head === freeze && origin === freeze, 'freeze not pushed HEAD');
  await git(['merge-base', '--is-ancestor', PREREGISTRATION_COMMIT, freeze]);
  await git(['merge-base', '--is-ancestor', CORRECTION_COMMIT, freeze]);
  req(await hashFile(pathFor(SPEC_URI)) === await committedHash(PREREGISTRATION_COMMIT, SPEC_URI) && await hashFile(pathFor(PROTOCOL_URI)) === await committedHash(PREREGISTRATION_COMMIT, PROTOCOL_URI), 'preregistration drift');
  req(await hashFile(pathFor(CORRECTION_URI)) === await committedHash(CORRECTION_COMMIT, CORRECTION_URI) && await hashFile(pathFor(CORRECTION_PROTOCOL_URI)) === await committedHash(CORRECTION_COMMIT, CORRECTION_PROTOCOL_URI), 'correction drift');
  const toolHashes = {};
  for (const uri of TOOLS) { toolHashes[uri] = await hashFile(pathFor(uri)); req(toolHashes[uri] === await committedHash(freeze, uri), `tool drift ${uri}`); }
  req(toolHashes[TOOLS[0]] === correction.frozenBeforeCorrection.builderSha256 && toolHashes[TOOLS[1]] === correction.frozenBeforeCorrection.renderSha256 && toolHashes[TOOLS[2]] === correction.frozenBeforeCorrection.independentSha256, 'frozen Blender tools changed');
  req((await git(['status', '--porcelain=v1', '--', SPEC_URI, PROTOCOL_URI, CORRECTION_URI, CORRECTION_PROTOCOL_URI, RETAINED_ROOT, PARENT_ROOT, ...TOOLS])).trim() === '', 'scoped dirty');
  const retainedTree = await treeIdentity(RETAINED_ROOT);
  req(canonicalJson(retainedTree) === canonicalJson(correction.retainedFailure.tree) && await hashFile(pathFor(correction.retainedFailure.failure.uri)) === correction.retainedFailure.failure.sha256 && await hashFile(pathFor(correction.retainedFailure.build.uri)) === correction.retainedFailure.build.sha256, 'retained v0.1 drift');
  const parentTree = await treeIdentity(PARENT_ROOT);
  req(canonicalJson(parentTree) === canonicalJson(spec.parentEvidence.d5Formal.tree), 'D5 tree drift');
  const parentReceiptPath = pathFor(spec.parentEvidence.d5Formal.receipt.uri), parentAuditPath = pathFor(spec.parentEvidence.d5Formal.audit.uri);
  req(await hashFile(parentReceiptPath) === spec.parentEvidence.d5Formal.receipt.sha256 && await hashFile(parentAuditPath) === spec.parentEvidence.d5Formal.audit.sha256, 'D5 evidence drift');
  const parentReceipt = JSON.parse(await readFile(parentReceiptPath, 'utf8')), parentAudit = JSON.parse(await readFile(parentAuditPath, 'utf8'));
  req(parentReceipt.receiptHash === spec.parentEvidence.d5Formal.receipt.receiptHash && parentAudit.auditHash === spec.parentEvidence.d5Formal.audit.auditHash && parentAudit.status === 'PASS' && parentAudit.scientificVerdict === spec.parentEvidence.d5Formal.audit.scientificVerdict && parentAudit.selectedCandidateId === spec.parentEvidence.d5Formal.audit.selectedCandidateId, 'D5 evidence invalid');
  const master = pathFor(spec.parentEvidence.masterScene.uri), masterSha = await hashFile(master);
  req(masterSha === spec.parentEvidence.masterScene.sha256 && await hashFile(spec.runtime.blender.executable) === spec.runtime.blender.sha256, 'runtime/source drift');
  const filesystem = await statfs(repositoryRoot), available = Number(filesystem.bavail) * Number(filesystem.bsize);
  req(available - spec.processBudget.projectedWriteBytes >= spec.processBudget.minimumFreeReserveBytes, 'disk reserve');
  const root = pathFor(ROOT_URI);
  await mkdir(resolve(root, 'processes'), { recursive: true, mode: 0o700 });
  const admission = await writeHashed(resolve(root, 'admission.json'), { schemaVersion: 'bfs.b62CameraQualityMotionAwareHoldoutAdmission.v0.1', experimentId: spec.experimentId, status: 'ADMITTED', preregistrationCommit: PREREGISTRATION_COMMIT, correctionCommit: CORRECTION_COMMIT, toolFreezeCommit: freeze, bindings: { spec: { uri: SPEC_URI, sha256: await hashFile(pathFor(SPEC_URI)) }, protocol: { uri: PROTOCOL_URI, sha256: await hashFile(pathFor(PROTOCOL_URI)) }, correction: { uri: CORRECTION_URI, sha256: await hashFile(pathFor(CORRECTION_URI)) }, correctionProtocol: { uri: CORRECTION_PROTOCOL_URI, sha256: await hashFile(pathFor(CORRECTION_PROTOCOL_URI)) }, retainedFailureTree: retainedTree, retainedFailureSha256: await hashFile(pathFor(correction.retainedFailure.failure.uri)), retainedBuildSha256: await hashFile(pathFor(correction.retainedFailure.build.uri)), parentTree, parentReceiptSha256: await hashFile(parentReceiptPath), parentAuditSha256: await hashFile(parentAuditPath), master: { uri: spec.parentEvidence.masterScene.uri, sha256: masterSha }, blenderSha256: await hashFile(spec.runtime.blender.executable), tools: toolHashes }, resources: { availableBytesBefore: available, projectedWriteBytes: spec.processBudget.projectedWriteBytes, minimumFreeReserveBytes: spec.processBudget.minimumFreeReserveBytes }, operations: { blenderStartsBeforeAdmission: 0, renderCalls: 0, modelCalls: 0, networkCalls: 0, dockerProcesses: 0 } }, 'admissionHash');
  try {
    const derived = resolve(root, 'scene/B62_PHASE0_D6_MOTION_AWARE.blend'), buildPath = resolve(root, 'build.json');
    const build = await blenderChild({ root, id: 'BUILD', scene: master, tool: TOOLS[0], args: ['--output-scene', derived, '--report', buildPath, '--master-sha256', masterSha], wallSeconds: spec.processBudget.maximumBuildWallSeconds });
    const buildDoc = JSON.parse(await readFile(buildPath, 'utf8'));
    req(validSelf(buildDoc, 'reportHash') && buildDoc.status === 'PASS' && buildDoc.bake.length === 96 && await hashFile(derived) === buildDoc.derived.sha256, 'build output invalid');
    const renderPath = resolve(root, 'render.json');
    const render = await blenderChild({ root, id: 'RENDER', scene: derived, tool: TOOLS[1], args: ['--output-dir', resolve(root, 'renders'), '--report', renderPath, '--derived-sha256', buildDoc.derived.sha256], wallSeconds: spec.processBudget.maximumRenderWallSeconds });
    const renderDoc = JSON.parse(await readFile(renderPath, 'utf8'));
    req(validSelf(renderDoc, 'reportHash') && renderDoc.status === 'PASS' && renderDoc.renders.length === 16, 'render output invalid');
    const independentPath = resolve(root, 'independent.json');
    const independent = await blenderChild({ root, id: 'INDEPENDENT', scene: derived, tool: TOOLS[2], args: ['--output', independentPath, '--build-report', buildPath, '--render-report', renderPath, '--derived-sha256', buildDoc.derived.sha256], wallSeconds: spec.processBudget.maximumIndependentWallSeconds });
    const independentDoc = JSON.parse(await readFile(independentPath, 'utf8'));
    req(validSelf(independentDoc, 'reportHash') && independentDoc.status === 'PASS', 'independent output invalid');
    const auditorArgs = [pathFor(TOOLS[4]), '--root', ROOT_URI, '--tool-freeze-commit', freeze];
    const auditorResult = await runBudgetedProcess({ command: process.execPath, args: auditorArgs, cwd: repositoryRoot, env: { PATH: '/usr/bin:/bin', LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8' }, outputRoot: root, budgets: { wallTimeMs: 60000, maxRssBytes: 1073741824, maxLogBytes: 1048576, maxOutputFiles: 256, maxOutputBytes: spec.processBudget.projectedWriteBytes, sampleIntervalMs: 100 } });
    const auditor = await processReceipt(root, 'AUDITOR', process.execPath, auditorArgs.map(value => value.startsWith(repositoryRoot) ? relative(repositoryRoot, value).split('\\').join('/') : value), auditorResult);
    req(auditorResult.outcome === 'PASS' && auditorResult.child.exitCode === 0 && auditorResult.breach === null, 'auditor failed');
    const auditPath = resolve(root, 'audit.json'), audit = JSON.parse(await readFile(auditPath, 'utf8'));
    req(validSelf(audit, 'auditHash') && audit.status === 'PASS', 'audit invalid');
    const receipt = await writeHashed(resolve(root, 'receipt.json'), { schemaVersion: 'bfs.b62CameraQualityMotionAwareHoldoutReceipt.v0.1', experimentId: spec.experimentId, status: 'PASS', scientificVerdict: audit.scientificVerdict, humanReview: 'PENDING', admission: { uri: `${ROOT_URI}/admission.json`, sha256: await hashFile(resolve(root, 'admission.json')), admissionHash: admission.admissionHash }, build: { uri: `${ROOT_URI}/build.json`, sha256: await hashFile(buildPath), reportHash: buildDoc.reportHash }, render: { uri: `${ROOT_URI}/render.json`, sha256: await hashFile(renderPath), reportHash: renderDoc.reportHash }, independent: { uri: `${ROOT_URI}/independent.json`, sha256: await hashFile(independentPath), reportHash: independentDoc.reportHash }, audit: { uri: `${ROOT_URI}/audit.json`, sha256: await hashFile(auditPath), auditHash: audit.auditHash }, processes: { build: { uri: `${ROOT_URI}/processes/BUILD.json`, sha256: await hashFile(resolve(root, 'processes/BUILD.json')), processHash: build.processHash }, render: { uri: `${ROOT_URI}/processes/RENDER.json`, sha256: await hashFile(resolve(root, 'processes/RENDER.json')), processHash: render.processHash }, independent: { uri: `${ROOT_URI}/processes/INDEPENDENT.json`, sha256: await hashFile(resolve(root, 'processes/INDEPENDENT.json')), processHash: independent.processHash }, auditor: { uri: `${ROOT_URI}/processes/AUDITOR.json`, sha256: await hashFile(resolve(root, 'processes/AUDITOR.json')), processHash: auditor.processHash } }, operations: { runnerProcesses: 1, blenderStarts: 3, renderCalls: 16, nodeAuditorProcesses: 1, modelCalls: 0, networkCalls: 0, dockerProcesses: 0 }, nonClaims: spec.nonClaims }, 'receiptHash');
    console.log(`BFS_B62_Q1_D6 PASS ${receipt.scientificVerdict} HUMAN_PENDING ${receipt.receiptHash}`);
  } catch (error) {
    if (!await exists(resolve(root, 'failure.json'))) await writeHashed(resolve(root, 'failure.json'), { schemaVersion: 'bfs.b62CameraQualityFailure.v0.1', experimentId: spec.experimentId, status: 'INVALIDATED', scientificVerdict: null, toolFreezeCommit: freeze, reason: error.message }, 'failureHash');
    throw error;
  }
}

main().catch(error => { console.error(error.stack ?? error.message); process.exitCode = 1; });
