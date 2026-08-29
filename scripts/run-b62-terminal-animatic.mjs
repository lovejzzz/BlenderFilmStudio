#!/usr/bin/env node

import { execFile } from 'node:child_process';
import { createHash } from 'node:crypto';
import { lstat, mkdir, open, readFile, readdir, realpath, stat, statfs } from 'node:fs/promises';
import { dirname, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';
import { runBudgetedProcess } from './lib/budgeted-process.mjs';

const execFileAsync = promisify(execFile);
const repositoryRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const PREREGISTRATION_COMMIT = '3de7040d607a5439d1c556a57a6eaebdae03f65d';
const CORRECTION_COMMIT = '56cda77c88cd3c6bda873cf62140053f2b258e7e';
const CORRECTION_C2_COMMIT = '79bf37fe3771fff8eafd0a060866d9ad84e6a916';
const CORRECTION_C3_COMMIT = 'ff58742e60d607038ac3fd2d4a5bf2b85f8b30b2';
const SPEC_URI = 'specs/b62-terminal-animatic-continuity.v0.1.json';
const PROTOCOL_URI = 'research/2026-08-29-b62-t2-terminal-animatic-continuity-protocol.md';
const CORRECTION_URI = 'specs/b62-terminal-animatic-continuity-c1-explicit-marker-routing.v0.1.json';
const CORRECTION_PROTOCOL_URI = 'research/2026-08-29-b62-t2-c1-explicit-marker-routing.md';
const CORRECTION_C2_URI = 'specs/b62-terminal-animatic-continuity-c2-post-render-camera-state.v0.1.json';
const CORRECTION_C2_PROTOCOL_URI = 'research/2026-08-29-b62-t2-c2-post-render-camera-state.md';
const CORRECTION_C3_URI = 'specs/b62-terminal-animatic-continuity-c3-active-scene-render-context.v0.1.json';
const CORRECTION_C3_PROTOCOL_URI = 'research/2026-08-29-b62-t2-c3-active-scene-render-context.md';
const RETAINED_ROOT_URI = 'experiments/b62-terminal-animatic-continuity-v0-1';
const RETAINED_C2_ROOT_URI = 'experiments/b62-terminal-animatic-continuity-v0-2';
const RETAINED_C3_ROOT_URI = 'experiments/b62-terminal-animatic-continuity-v0-3';
const ROOT_URI = 'experiments/b62-terminal-animatic-continuity-v0-4';
const OCIO_URI = 'color/ocio/cg-config-v4.0.0_aces-v2.0_ocio-v2.5.ocio';
const TOOLS = [
  'blender/render_b62_terminal_animatic.py',
  'blender/audit_b62_terminal_animatic.py',
  'scripts/run-b62-terminal-animatic.mjs',
  'scripts/audit-b62-terminal-animatic.mjs',
];

function req(condition, message) { if (!condition) throw new Error(message); }
function normalize(value) { if (typeof value === 'number' && Number.isFinite(value) && Number.isInteger(value)) return value; if (typeof value === 'number' && Number.isFinite(value)) { const bytes = Buffer.alloc(8); bytes.writeDoubleBE(value); return { $f64be: bytes.toString('hex') }; } if (Array.isArray(value)) return value.map(normalize); if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).sort(([a], [b]) => a.localeCompare(b)).map(([key, child]) => [key, normalize(child)])); return value; }
const canonicalJson = value => JSON.stringify(normalize(value));
const hashBytes = value => createHash('sha256').update(value).digest('hex');
const hashFile = async path => hashBytes(await readFile(path));
function validSelf(value, field) { if (!value || !/^[0-9a-f]{64}$/.test(value[field] ?? '')) return false; const copy = structuredClone(value), expected = copy[field]; delete copy[field]; return hashBytes(canonicalJson(copy)) === expected; }
function pathFor(uri) { req(typeof uri === 'string' && uri && !uri.startsWith('/') && !uri.includes('\\') && !uri.split('/').includes('..'), `unsafe path ${uri}`); const path = resolve(repositoryRoot, uri); req(!relative(repositoryRoot, path).startsWith('../'), `escaped path ${uri}`); return path; }
async function exists(path) { try { await lstat(path); return true; } catch (error) { if (error.code === 'ENOENT') return false; throw error; } }
async function checkedExisting(uri) { const path = pathFor(uri), actual = await realpath(path); req(path === actual, `symlink or alias ${uri}`); return path; }
async function git(args, encoding = 'utf8') { return (await execFileAsync('/usr/bin/git', args, { cwd: repositoryRoot, encoding, timeout: 15000, maxBuffer: 32 * 1024 * 1024, env: { PATH: '/usr/bin:/bin', LANG: 'C', LC_ALL: 'C', GIT_CONFIG_NOSYSTEM: '1', GIT_TERMINAL_PROMPT: '0' } })).stdout; }
async function committedHash(commit, uri) { return hashBytes(await git(['show', `${commit}:${uri}`], null)); }
async function writeHashed(path, value, field) { const body = structuredClone(value); body[field] = hashBytes(canonicalJson(body)); const handle = await open(path, 'wx', 0o600); try { await handle.writeFile(`${JSON.stringify(body, null, 2)}\n`); await handle.sync(); } finally { await handle.close(); } return body; }
async function treeIdentity(uri) { const root = pathFor(uri), files = []; async function walk(directory) { for (const entry of await readdir(directory, { withFileTypes: true })) { const path = resolve(directory, entry.name); if (entry.isDirectory()) await walk(path); else if (entry.isFile()) files.push(path); else throw new Error(`special parent entry ${path}`); } } await walk(root); files.sort(); let bytes = 0, material = ''; for (const path of files) { const content = await readFile(path); bytes += content.length; material += `${relative(root, path).split('\\').join('/')}\0${hashBytes(content)}\n`; } return { files: files.length, bytes, treeSha256: hashBytes(Buffer.from(material)) }; }
function parse() { const args = process.argv.slice(2); req(args.length === 2 && args[0] === '--tool-freeze-commit' && /^[0-9a-f]{40}$/.test(args[1]), 'usage: --tool-freeze-commit <sha>'); return args[1]; }

let experiment;
async function processReceipt(root, id, command, args, result) {
  return writeHashed(resolve(root, 'processes', `${id}.json`), { schemaVersion: 'bfs.b62TerminalAnimaticProcessReceipt.v0.1', experimentId: 'B62-T2-E1', processId: id, command, args, result }, 'processHash');
}
async function runChild({ root, id, command, args, wallSeconds, maxRssBytes, env = {} }) {
  const result = await runBudgetedProcess({ command, args, cwd: repositoryRoot, env: { PATH: '/opt/homebrew/bin:/usr/bin:/bin', LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8', ...env }, outputRoot: root, budgets: { wallTimeMs: wallSeconds * 1000, maxRssBytes, maxLogBytes: experiment.processBudget.maximumCombinedLogBytesPerChild, maxOutputFiles: 320, maxOutputBytes: experiment.processBudget.maximumOutputBytes, sampleIntervalMs: 100 } });
  const displayArgs = args.map(value => typeof value === 'string' && value.startsWith(repositoryRoot) ? relative(repositoryRoot, value).split('\\').join('/') : value);
  const receipt = await processReceipt(root, id, command, displayArgs, result);
  req(result.outcome === 'PASS' && result.child.exitCode === 0 && result.breach === null, `${id} failed`);
  return receipt;
}
async function runBlender({ root, id, tool, args, wallSeconds }) {
  const scene = pathFor(experiment.parentEvidence.scene.uri);
  const full = ['--background', '--factory-startup', '--disable-autoexec', scene, '--python-exit-code', '1', '--python', pathFor(tool), '--', ...args];
  return runChild({ root, id, command: experiment.runtime.blender.executable, args: full, wallSeconds, maxRssBytes: experiment.processBudget.maximumPeakResidentSetSizeBytesPerBlender, env: { OCIO: pathFor(OCIO_URI) } });
}
async function bound(binding, field, semantic) {
  const path = await checkedExisting(binding.uri);
  req(await hashFile(path) === binding.sha256, `parent file drift ${binding.uri}`);
  const document = JSON.parse(await readFile(path, 'utf8'));
  req(validSelf(document, field) && document[field] === binding[field], `parent self hash invalid ${binding.uri}`);
  semantic(document);
  return document;
}

async function main() {
  const freeze = parse();
  experiment = JSON.parse(await readFile(await checkedExisting(SPEC_URI), 'utf8'));
  const correction = JSON.parse(await readFile(await checkedExisting(CORRECTION_URI), 'utf8'));
  const correctionC2 = JSON.parse(await readFile(await checkedExisting(CORRECTION_C2_URI), 'utf8'));
  const correctionC3 = JSON.parse(await readFile(await checkedExisting(CORRECTION_C3_URI), 'utf8'));
  req(experiment.experimentId === 'B62-T2-E1' && experiment.statusBeforeToolCreation === 'PREREGISTERED' && experiment.output.formalRoot === RETAINED_ROOT_URI, 'experiment mismatch');
  req(correction.correctionId === 'B62-T2-E1-C1' && correction.statusBeforeToolChange === 'PREREGISTERED' && correction.retainedFailure.root === RETAINED_ROOT_URI && correction.authorizedChanges.retryRoot === RETAINED_C2_ROOT_URI, 'correction mismatch');
  req(correction.authorizedChanges.retryRoot === RETAINED_C2_ROOT_URI && correctionC2.correctionId === 'B62-T2-E1-C2' && correctionC2.statusBeforeToolChange === 'PREREGISTERED' && correctionC2.retainedFailure.root === RETAINED_C2_ROOT_URI && correctionC2.authorizedChanges.retryRoot === RETAINED_C3_ROOT_URI, 'C2 mismatch');
  req(correctionC3.correctionId === 'B62-T2-E1-C3' && correctionC3.statusBeforeToolChange === 'PREREGISTERED' && correctionC3.retainedResult.root === RETAINED_C3_ROOT_URI && correctionC3.authorizedChanges.retryRoot === ROOT_URI, 'C3 mismatch');
  const head = (await git(['rev-parse', 'HEAD'])).trim(), origin = (await git(['rev-parse', 'origin/main'])).trim();
  req(head === freeze && origin === freeze, 'tool freeze commit is not pushed HEAD');
  await git(['merge-base', '--is-ancestor', PREREGISTRATION_COMMIT, freeze]);
  req(await hashFile(pathFor(SPEC_URI)) === await committedHash(PREREGISTRATION_COMMIT, SPEC_URI), 'preregistered spec drift');
  req(await hashFile(pathFor(PROTOCOL_URI)) === await committedHash(PREREGISTRATION_COMMIT, PROTOCOL_URI), 'preregistered protocol drift');
  req(await hashFile(pathFor(CORRECTION_URI)) === await committedHash(CORRECTION_COMMIT, CORRECTION_URI), 'correction spec drift');
  req(await hashFile(pathFor(CORRECTION_PROTOCOL_URI)) === await committedHash(CORRECTION_COMMIT, CORRECTION_PROTOCOL_URI), 'correction protocol drift');
  req(await hashFile(pathFor(CORRECTION_C2_URI)) === await committedHash(CORRECTION_C2_COMMIT, CORRECTION_C2_URI), 'C2 spec drift');
  req(await hashFile(pathFor(CORRECTION_C2_PROTOCOL_URI)) === await committedHash(CORRECTION_C2_COMMIT, CORRECTION_C2_PROTOCOL_URI), 'C2 protocol drift');
  req(await hashFile(pathFor(CORRECTION_C3_URI)) === await committedHash(CORRECTION_C3_COMMIT, CORRECTION_C3_URI), 'C3 spec drift');
  req(await hashFile(pathFor(CORRECTION_C3_PROTOCOL_URI)) === await committedHash(CORRECTION_C3_COMMIT, CORRECTION_C3_PROTOCOL_URI), 'C3 protocol drift');
  const scoped = await git(['status', '--porcelain=v1', '--', SPEC_URI, PROTOCOL_URI, CORRECTION_URI, CORRECTION_PROTOCOL_URI, CORRECTION_C2_URI, CORRECTION_C2_PROTOCOL_URI, CORRECTION_C3_URI, CORRECTION_C3_PROTOCOL_URI, ...TOOLS]);
  req(scoped.trim() === '', 'release-scoped files dirty');
  const root = pathFor(ROOT_URI);
  req(!await exists(root), 'formal root already exists');
  const retainedTree = await treeIdentity(RETAINED_ROOT_URI);
  req(canonicalJson(retainedTree) === canonicalJson(correction.retainedFailure.tree), 'retained v0.1 tree drift');
  for (const binding of [correction.retainedFailure.admission, correction.retainedFailure.failure, correction.retainedFailure.renderProcess, ...Object.values(correction.retainedFailure.frames).filter(value => typeof value === 'object')]) req(await hashFile(await checkedExisting(binding.uri)) === binding.sha256, `retained evidence drift ${binding.uri}`);
  const retainedC2Tree = await treeIdentity(RETAINED_C2_ROOT_URI);
  req(canonicalJson(retainedC2Tree) === canonicalJson(correctionC2.retainedFailure.tree), 'retained v0.2 tree drift');
  for (const binding of [correctionC2.retainedFailure.admission, correctionC2.retainedFailure.failure, correctionC2.retainedFailure.renderProcess, ...Object.values(correctionC2.retainedFailure.frames).filter(value => typeof value === 'object')]) req(await hashFile(await checkedExisting(binding.uri)) === binding.sha256, `retained C2 evidence drift ${binding.uri}`);
  const retainedC3Tree = await treeIdentity(RETAINED_C3_ROOT_URI);
  req(canonicalJson(retainedC3Tree) === canonicalJson(correctionC3.retainedResult.tree), 'retained v0.3 tree drift');
  for (const binding of [correctionC3.retainedResult.audit, correctionC3.retainedResult.receipt, correctionC3.retainedResult.renderReport, correctionC3.retainedResult.independentReport, correctionC3.retainedResult.video]) req(await hashFile(await checkedExisting(binding.uri)) === binding.sha256, `retained C3 evidence drift ${binding.uri}`);

  const parentTree = await treeIdentity(experiment.parentEvidence.t1Root.uri);
  req(canonicalJson(parentTree) === canonicalJson({ files: experiment.parentEvidence.t1Root.files, bytes: experiment.parentEvidence.t1Root.bytes, treeSha256: experiment.parentEvidence.t1Root.treeSha256 }), 'T1 tree drift');
  await bound(experiment.parentEvidence.receipt, 'receiptHash', value => req(value.status === 'PASS' && value.scientificVerdict === experiment.parentEvidence.receipt.scientificVerdict, 'T1 receipt invalid'));
  await bound(experiment.parentEvidence.audit, 'auditHash', value => req(value.status === 'PASS' && value.gates.length === 20 && value.attacks.length === 12, 'T1 audit invalid'));
  await bound(experiment.parentEvidence.buildPlan, 'planHash', value => req(value.experimentId === 'B62-T1-E1', 'T1 plan invalid'));
  await bound(experiment.parentEvidence.independent, 'reportHash', value => req(value.status === 'PASS' && value.maximumPoseError === 0, 'T1 independent invalid'));
  const scene = await checkedExisting(experiment.parentEvidence.scene.uri);
  req(await hashFile(scene) === experiment.parentEvidence.scene.sha256, 'T1 scene drift');

  const toolHashes = {};
  for (const uri of TOOLS) { toolHashes[uri] = await hashFile(await checkedExisting(uri)); req(toolHashes[uri] === await committedHash(freeze, uri), `tool drift ${uri}`); }
  req(await hashFile(experiment.runtime.blender.executable) === experiment.runtime.blender.sha256, 'Blender binary drift');
  req(await hashFile(experiment.runtime.ffmpeg.executable) === experiment.runtime.ffmpeg.sha256, 'ffmpeg binary drift');
  req(await hashFile(experiment.runtime.ffprobe.executable) === experiment.runtime.ffprobe.sha256, 'ffprobe binary drift');
  req(await hashFile(await checkedExisting(OCIO_URI)) === experiment.runtime.ocio.sha256, 'OCIO drift');
  const filesystem = await statfs(repositoryRoot), available = Number(filesystem.bavail) * Number(filesystem.bsize);
  req(available - experiment.processBudget.projectedWriteBytes >= experiment.processBudget.minimumFreeReserveBytes, 'capacity admission failed');

  await mkdir(root, { recursive: false });
  await mkdir(resolve(root, 'processes'));
  await mkdir(resolve(root, 'reports'));
  await mkdir(resolve(root, 'video'));
  const admission = await writeHashed(resolve(root, 'admission.json'), {
    schemaVersion: 'bfs.b62TerminalAnimaticAdmission.v0.1', experimentId: experiment.experimentId, status: 'ADMITTED', preregistrationCommit: PREREGISTRATION_COMMIT, correctionCommit: CORRECTION_COMMIT, correctionC2Commit: CORRECTION_C2_COMMIT, correctionC3Commit: CORRECTION_C3_COMMIT, toolFreezeCommit: freeze,
    parentTree, retainedFailureTree: retainedTree, retainedC2FailureTree: retainedC2Tree, retainedC3ResultTree: retainedC3Tree, bindings: { tools: toolHashes, scene: { uri: experiment.parentEvidence.scene.uri, sha256: await hashFile(scene) }, runtime: { blender: await hashFile(experiment.runtime.blender.executable), ffmpeg: await hashFile(experiment.runtime.ffmpeg.executable), ffprobe: await hashFile(experiment.runtime.ffprobe.executable), ocio: await hashFile(pathFor(OCIO_URI)) } },
    resources: { availableBytesBefore: available, projectedWriteBytes: experiment.processBudget.projectedWriteBytes, minimumFreeReserveBytes: experiment.processBudget.minimumFreeReserveBytes },
    operations: { restrictedProcessesBeforeAdmission: 0, modelCalls: 0, networkCalls: 0, dockerProcesses: 0 },
  }, 'admissionHash');

  const renderReport = resolve(root, 'reports/render-report.json');
  await runBlender({ root, id: 'BLENDER_RENDER', tool: TOOLS[0], wallSeconds: experiment.processBudget.maximumRenderWallSeconds, args: ['--repository-root', repositoryRoot, '--formal-root', root, '--report', renderReport] });
  const independentReport = resolve(root, 'reports/independent-audit.json');
  await runBlender({ root, id: 'BLENDER_INDEPENDENT', tool: TOOLS[1], wallSeconds: experiment.processBudget.maximumIndependentWallSeconds, args: ['--repository-root', repositoryRoot, '--formal-root', root, '--render-report', renderReport, '--output', independentReport, '--source-sha256', experiment.parentEvidence.scene.sha256] });

  const video = resolve(root, 'video/B62_TERMINAL_ANIMATIC.mp4');
  await runChild({ root, id: 'FFMPEG', command: experiment.runtime.ffmpeg.executable, wallSeconds: 180, maxRssBytes: 1073741824, args: ['-nostdin', '-hide_banner', '-loglevel', 'error', '-framerate', '24', '-start_number', '1', '-i', resolve(root, 'frames/frame-%04d.png'), '-frames:v', '288', '-an', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', video] });
  const probeReceipt = await runChild({ root, id: 'FFPROBE', command: experiment.runtime.ffprobe.executable, wallSeconds: 60, maxRssBytes: 536870912, args: ['-v', 'error', '-count_frames', '-select_streams', 'v:0', '-show_entries', 'format=duration,format_name:stream=codec_type,codec_name,width,height,pix_fmt,r_frame_rate,avg_frame_rate,nb_read_frames,duration', '-of', 'json', video] });
  const probe = JSON.parse(probeReceipt.result.outputPreview);
  await writeHashed(resolve(root, 'reports/video-metadata.json'), { schemaVersion: 'bfs.b62TerminalAnimaticVideoMetadata.v0.1', experimentId: experiment.experimentId, status: 'PASS', video: { uri: relative(repositoryRoot, video).split('\\').join('/'), sha256: await hashFile(video), bytes: (await stat(video)).size }, probe }, 'metadataHash');

  await runChild({ root, id: 'NODE_AUDIT', command: process.execPath, wallSeconds: 120, maxRssBytes: 536870912, args: [pathFor(TOOLS[3]), '--tool-freeze-commit', freeze] });
  const auditPath = resolve(root, 'audit.json'), audit = JSON.parse(await readFile(auditPath, 'utf8'));
  req(validSelf(audit, 'auditHash') && audit.status === 'PASS' && audit.scientificVerdict, 'final audit invalid');
  const receipt = await writeHashed(resolve(root, 'receipt.json'), {
    schemaVersion: 'bfs.b62TerminalAnimaticReceipt.v0.1', experimentId: experiment.experimentId, status: 'PASS', scientificVerdict: audit.scientificVerdict, humanReview: 'HUMAN_PENDING', preregistrationCommit: PREREGISTRATION_COMMIT, correctionCommit: CORRECTION_COMMIT, correctionC2Commit: CORRECTION_C2_COMMIT, correctionC3Commit: CORRECTION_C3_COMMIT, toolFreezeCommit: freeze,
    admission: { uri: `${ROOT_URI}/admission.json`, sha256: await hashFile(resolve(root, 'admission.json')), admissionHash: admission.admissionHash },
    audit: { uri: `${ROOT_URI}/audit.json`, sha256: await hashFile(auditPath), auditHash: audit.auditHash },
    renderReport: { uri: `${ROOT_URI}/reports/render-report.json`, sha256: await hashFile(renderReport) }, independentReport: { uri: `${ROOT_URI}/reports/independent-audit.json`, sha256: await hashFile(independentReport) },
    video: { uri: `${ROOT_URI}/video/B62_TERMINAL_ANIMATIC.mp4`, sha256: await hashFile(video), bytes: (await stat(video)).size },
    operations: { runnerProcesses: 1, freshBlenderProcesses: 2, eeveeRenderCalls: 288, cyclesRenderCalls: 0, ffmpegProcesses: 1, ffprobeProcesses: 1, nodeAuditorProcesses: 1, modelCalls: 0, networkCalls: 0, dockerProcesses: 0 }, nonClaims: experiment.nonClaims,
  }, 'receiptHash');
  console.log(`BFS_B62_T2 PASS ${receipt.scientificVerdict} HUMAN_PENDING ${receipt.receiptHash}`);
}

main().catch(async error => {
  try { const root = pathFor(ROOT_URI); if (await exists(root) && !await exists(resolve(root, 'failure.json'))) await writeHashed(resolve(root, 'failure.json'), { schemaVersion: 'bfs.b62TerminalAnimaticFailure.v0.1', experimentId: 'B62-T2-E1', status: 'INVALIDATED', scientificVerdict: null, error: error.message }, 'failureHash'); } catch {}
  console.error(`BFS_B62_T2_ERROR ${error.stack ?? error.message}`); process.exitCode = 1;
});
