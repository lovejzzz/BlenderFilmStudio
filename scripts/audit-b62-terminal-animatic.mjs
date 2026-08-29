#!/usr/bin/env node

import { execFile } from 'node:child_process';
import { createHash } from 'node:crypto';
import { open, readFile, readdir, realpath, statfs } from 'node:fs/promises';
import { dirname, relative, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);
const repositoryRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const PREREGISTRATION_COMMIT = '3de7040d607a5439d1c556a57a6eaebdae03f65d';
const CORRECTION_COMMIT = '56cda77c88cd3c6bda873cf62140053f2b258e7e';
const SPEC_URI = 'specs/b62-terminal-animatic-continuity.v0.1.json';
const PROTOCOL_URI = 'research/2026-08-29-b62-t2-terminal-animatic-continuity-protocol.md';
const CORRECTION_URI = 'specs/b62-terminal-animatic-continuity-c1-explicit-marker-routing.v0.1.json';
const CORRECTION_PROTOCOL_URI = 'research/2026-08-29-b62-t2-c1-explicit-marker-routing.md';
const RETAINED_ROOT_URI = 'experiments/b62-terminal-animatic-continuity-v0-1';
const ROOT_URI = 'experiments/b62-terminal-animatic-continuity-v0-2';
const TOOLS = ['blender/render_b62_terminal_animatic.py', 'blender/audit_b62_terminal_animatic.py', 'scripts/run-b62-terminal-animatic.mjs', 'scripts/audit-b62-terminal-animatic.mjs'];

function req(condition, message) { if (!condition) throw new Error(message); }
function normalize(value) { if (typeof value === 'number' && Number.isFinite(value) && Number.isInteger(value)) return value; if (typeof value === 'number' && Number.isFinite(value)) { const bytes = Buffer.alloc(8); bytes.writeDoubleBE(value); return { $f64be: bytes.toString('hex') }; } if (Array.isArray(value)) return value.map(normalize); if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).sort(([a], [b]) => a.localeCompare(b)).map(([key, child]) => [key, normalize(child)])); return value; }
const canonicalJson = value => JSON.stringify(normalize(value));
const hashBytes = value => createHash('sha256').update(value).digest('hex');
const hashFile = async path => hashBytes(await readFile(path));
function validSelf(value, field) { if (!value || !/^[0-9a-f]{64}$/.test(value[field] ?? '')) return false; const copy = structuredClone(value), expected = copy[field]; delete copy[field]; return hashBytes(canonicalJson(copy)) === expected; }
function pathFor(uri) { req(typeof uri === 'string' && uri && !uri.startsWith('/') && !uri.includes('\\') && !uri.split('/').includes('..'), `unsafe path ${uri}`); const path = resolve(repositoryRoot, uri); req(!relative(repositoryRoot, path).startsWith('../'), `escaped path ${uri}`); return path; }
async function checked(uri) { const path = pathFor(uri), actual = await realpath(path); req(path === actual, `symlink or alias ${uri}`); return path; }
async function git(args, encoding = 'utf8') { return (await execFileAsync('/usr/bin/git', args, { cwd: repositoryRoot, encoding, timeout: 15000, maxBuffer: 32 * 1024 * 1024, env: { PATH: '/usr/bin:/bin', LANG: 'C', LC_ALL: 'C', GIT_CONFIG_NOSYSTEM: '1', GIT_TERMINAL_PROMPT: '0' } })).stdout; }
async function committedHash(commit, uri) { return hashBytes(await git(['show', `${commit}:${uri}`], null)); }
async function writeHashed(path, value, field) { const body = structuredClone(value); body[field] = hashBytes(canonicalJson(body)); const handle = await open(path, 'wx', 0o600); try { await handle.writeFile(`${JSON.stringify(body, null, 2)}\n`); await handle.sync(); } finally { await handle.close(); } return body; }
async function collect(root) { const files = [], symlinks = []; async function walk(directory) { for (const entry of await readdir(directory, { withFileTypes: true })) { const path = resolve(directory, entry.name), uri = relative(root, path).split('\\').join('/'); if (entry.isSymbolicLink()) symlinks.push(uri); else if (entry.isDirectory()) await walk(path); else if (entry.isFile()) { const content = await readFile(path); files.push({ uri, bytes: content.length, sha256: hashBytes(content) }); } else throw new Error(`special output ${uri}`); } } await walk(root); files.sort((a, b) => a.uri.localeCompare(b.uri)); return { files, symlinks, bytes: files.reduce((sum, row) => sum + row.bytes, 0) }; }
async function treeIdentity(uri) { const root = pathFor(uri), snapshot = await collect(root); req(snapshot.symlinks.length === 0, `parent symlink ${uri}`); let material = ''; for (const row of snapshot.files) material += `${row.uri}\0${row.sha256}\n`; return { files: snapshot.files.length, bytes: snapshot.bytes, treeSha256: hashBytes(Buffer.from(material)) }; }
async function bound(binding, field, semantic) { const path = await checked(binding.uri); if (await hashFile(path) !== binding.sha256) return false; const document = JSON.parse(await readFile(path, 'utf8')); return validSelf(document, field) && document[field] === binding[field] && semantic(document); }
function processPass(row, id, spec) { return validSelf(row, 'processHash') && row.processId === id && row.result.outcome === 'PASS' && row.result.child.exitCode === 0 && row.result.breach === null && row.result.metrics.logBytes <= spec.processBudget.maximumCombinedLogBytesPerChild && row.result.metrics.output.bytes <= spec.processBudget.maximumOutputBytes; }
function geometryFeasible(row) { const p = row.characterProjection; return ['B62_VISOR', 'B62_EYE_SLIT'].every(name => row.visibleAnchors.includes(name)) && row.helmetVisualBlockerShare <= 0.7 && row.characterVisualBlockerShare >= 0.2 && row.characterVisualBlockerShare <= 0.9 && p.onScreenVertexFraction >= 0.1 && p.onScreenVertexFraction <= 0.6 && p.clampedUnionAreaFraction >= 0.35 && p.clampedUnionAreaFraction <= 0.9 && row.visibleAnchorCount >= 2; }
function parse() { const args = process.argv.slice(2); req(args.length === 2 && args[0] === '--tool-freeze-commit' && /^[0-9a-f]{40}$/.test(args[1]), 'usage: --tool-freeze-commit <sha>'); return args[1]; }

export async function audit(freeze) {
  const spec = JSON.parse(await readFile(await checked(SPEC_URI), 'utf8'));
  const correction = JSON.parse(await readFile(await checked(CORRECTION_URI), 'utf8'));
  req(spec.experimentId === 'B62-T2-E1' && spec.output.formalRoot === RETAINED_ROOT_URI, 'spec mismatch');
  req(correction.correctionId === 'B62-T2-E1-C1' && correction.retainedFailure.root === RETAINED_ROOT_URI && correction.authorizedChanges.retryRoot === ROOT_URI, 'correction mismatch');
  const root = await checked(ROOT_URI), snapshot = await collect(root);
  const head = (await git(['rev-parse', 'HEAD'])).trim(), origin = (await git(['rev-parse', 'origin/main'])).trim();
  const tools = Object.fromEntries(await Promise.all(TOOLS.map(async uri => [uri, await hashFile(await checked(uri))])));
  const preregExact = await hashFile(pathFor(SPEC_URI)) === await committedHash(PREREGISTRATION_COMMIT, SPEC_URI) && await hashFile(pathFor(PROTOCOL_URI)) === await committedHash(PREREGISTRATION_COMMIT, PROTOCOL_URI) && await hashFile(pathFor(CORRECTION_URI)) === await committedHash(CORRECTION_COMMIT, CORRECTION_URI) && await hashFile(pathFor(CORRECTION_PROTOCOL_URI)) === await committedHash(CORRECTION_COMMIT, CORRECTION_PROTOCOL_URI);
  const toolsExact = (await Promise.all(TOOLS.map(async uri => tools[uri] === await committedHash(freeze, uri)))).every(Boolean);
  const retainedTree = await treeIdentity(RETAINED_ROOT_URI);
  const retainedExact = canonicalJson(retainedTree) === canonicalJson(correction.retainedFailure.tree) && (await Promise.all([correction.retainedFailure.admission, correction.retainedFailure.failure, correction.retainedFailure.renderProcess, ...Object.values(correction.retainedFailure.frames).filter(value => typeof value === 'object')].map(async binding => await hashFile(await checked(binding.uri)) === binding.sha256))).every(Boolean);
  const parentTree = await treeIdentity(spec.parentEvidence.t1Root.uri);
  const parentExact = canonicalJson(parentTree) === canonicalJson({ files: spec.parentEvidence.t1Root.files, bytes: spec.parentEvidence.t1Root.bytes, treeSha256: spec.parentEvidence.t1Root.treeSha256 })
    && await bound(spec.parentEvidence.receipt, 'receiptHash', value => value.status === 'PASS' && value.scientificVerdict === spec.parentEvidence.receipt.scientificVerdict)
    && await bound(spec.parentEvidence.audit, 'auditHash', value => value.status === 'PASS' && value.gates.length === 20 && value.attacks.length === 12)
    && await bound(spec.parentEvidence.buildPlan, 'planHash', value => value.experimentId === 'B62-T1-E1')
    && await bound(spec.parentEvidence.independent, 'reportHash', value => value.status === 'PASS' && value.maximumPoseError === 0)
    && await hashFile(await checked(spec.parentEvidence.scene.uri)) === spec.parentEvidence.scene.sha256;
  const runtimeHashes = { blender: await hashFile(spec.runtime.blender.executable), ffmpeg: await hashFile(spec.runtime.ffmpeg.executable), ffprobe: await hashFile(spec.runtime.ffprobe.executable), ocio: await hashFile(pathFor(spec.runtime.ocio.uri)) };
  const runtimeExact = runtimeHashes.blender === spec.runtime.blender.sha256 && runtimeHashes.ffmpeg === spec.runtime.ffmpeg.sha256 && runtimeHashes.ffprobe === spec.runtime.ffprobe.sha256 && runtimeHashes.ocio === spec.runtime.ocio.sha256;
  const admission = JSON.parse(await readFile(resolve(root, 'admission.json'), 'utf8'));
  const render = JSON.parse(await readFile(resolve(root, 'reports/render-report.json'), 'utf8'));
  const independent = JSON.parse(await readFile(resolve(root, 'reports/independent-audit.json'), 'utf8'));
  const metadata = JSON.parse(await readFile(resolve(root, 'reports/video-metadata.json'), 'utf8'));
  const processIds = ['BLENDER_RENDER', 'BLENDER_INDEPENDENT', 'FFMPEG', 'FFPROBE'];
  const processes = Object.fromEntries(await Promise.all(processIds.map(async id => [id, JSON.parse(await readFile(resolve(root, `processes/${id}.json`), 'utf8'))])));
  const processChecks = Object.fromEntries(processIds.map(id => [id, processPass(processes[id], id, spec)]));
  const expectedFrames = Array.from({ length: 288 }, (_, index) => `frames/frame-${String(index + 1).padStart(4, '0')}.png`);
  const expectedRoster = ['admission.json', ...expectedFrames, ...processIds.map(id => `processes/${id}.json`), 'reports/independent-audit.json', 'reports/render-report.json', 'reports/video-metadata.json', 'video/B62_TERMINAL_ANIMATIC.mp4'].sort();
  const rootRosterExact = snapshot.symlinks.length === 0 && snapshot.files.map(row => row.uri).join('\0') === expectedRoster.join('\0');
  const filesByUri = new Map(snapshot.files.map(row => [row.uri, row]));
  const routeFor = frame => frame <= 96 ? ['SHOT_WIDE_APPROACH', 'CAM_WIDE_APPROACH'] : frame <= 192 ? ['SHOT_MEDIUM_CONTACT', 'CAM_MEDIUM_CONTACT'] : ['SHOT_CLOSE_REFLECTION', 'CAM_CLOSE_MOTION_TERMINAL'];
  const renderFramesExact = render.frames.length === 288 && render.frames.every((row, index) => { const frame = index + 1, uri = `frames/frame-${String(frame).padStart(4, '0')}.png`, observed = filesByUri.get(uri), [marker, camera] = routeFor(frame); return row.frame === frame && row.marker === marker && row.camera === camera && row.png.uri === `${ROOT_URI}/${uri}` && observed && observed.sha256 === row.png.sha256 && observed.bytes === row.png.bytes; });
  const settingsExact = render.settings.engine === spec.render.engine && render.settings.engineFamily === spec.render.engineFamily && canonicalJson(render.settings.resolution) === canonicalJson(spec.render.resolution) && render.settings.samples === spec.render.samples && render.settings.format === spec.render.fileFormat && render.settings.colorMode === spec.render.colorMode && render.settings.colorDepth === spec.render.colorDepth && render.settings.motionBlur === spec.render.motionBlur && canonicalJson(render.settings.color) === canonicalJson(spec.render.color);
  const routingExact = independent.routing.length === 288 && independent.routing.every((row, index) => { const [marker, camera] = routeFor(index + 1); return row.frame === index + 1 && row.marker === marker && row.camera === camera && row.expectedMarker === marker && row.expectedCamera === camera && row.exact; });
  const pixelsExact = independent.pixels.length === 288 && independent.pixels.every((row, index) => { const source = render.frames[index]; return row.frame === index + 1 && row.fileSha256 === source.png.sha256 && row.width === 640 && row.height === 360 && row.nonFiniteCount === 0 && row.rgbDynamicRange > 1 / 255 && row.meanRgb > 0.0001 && row.meanRgb < 0.9999 && /^[0-9a-f]{64}$/.test(row.decodedSha256); });
  const digest = new Map(independent.pixels.map(row => [row.frame, row.decodedSha256]));
  const expectedShotDistinct = [[1, 96], [97, 192], [193, 288]].map(([start, end]) => new Set(Array.from({ length: end - start + 1 }, (_, index) => digest.get(start + index))).size);
  const temporalExact = independent.shotDistinct.length === 3 && independent.shotDistinct.every((row, index) => row.distinctDecodedDigests === expectedShotDistinct[index] && row.distinctDecodedDigests >= 2) && new Set(digest.values()).size >= 10 && independent.outcome.wholeDistinctDecodedDigests === new Set(digest.values()).size;
  const cutsExact = [[96, 97], [192, 193]].every(([left, right], index) => digest.get(left) !== digest.get(right) && independent.cutPairs[index].different === true);
  const geometryAccounting = independent.closeGeometry.length === 96 && independent.closeGeometry.every((row, index) => row.frame === index + 193 && row.camera === 'CAM_CLOSE_MOTION_TERMINAL' && Object.values(row.groupCounts).reduce((sum, value) => sum + value, 0) === 576 && row.visibleAnchorCount === row.visibleAnchors.length && row.characterProjection.onScreenVertices / row.characterProjection.totalVertices === row.characterProjection.onScreenVertexFraction && row.feasible === geometryFeasible(row));
  const geometryPass = geometryAccounting && independent.closeGeometry.every(row => row.feasible) && independent.outcome.closeGeometryAllPass;
  const causal = independent.causalState, energies = causal.map(row => row.warmEnergy);
  const causalExact = causal.map(row => row.frame).join(',') === '138,143,144,150,288' && canonicalJson(causal.map(row => row.coreActivation)) === canonicalJson([0, 0, 0.5, 1, 1]) && causal[2].contactDistanceM <= 0.02 && energies[0] === 0 && energies[1] === 0 && energies[2] > 0 && energies[3] > energies[2] && energies[4] === energies[3] && independent.outcome.causalStatePass;
  const videoPath = resolve(root, 'video/B62_TERMINAL_ANIMATIC.mp4'), videoBytes = await readFile(videoPath), moov = videoBytes.indexOf(Buffer.from('moov')), mdat = videoBytes.indexOf(Buffer.from('mdat'));
  const stream = metadata.probe.streams?.[0], format = metadata.probe.format;
  const videoExact = validSelf(metadata, 'metadataHash') && metadata.video.sha256 === await hashFile(videoPath) && stream?.codec_name === 'h264' && stream?.width === 640 && stream?.height === 360 && stream?.pix_fmt === 'yuv420p' && stream?.r_frame_rate === '24/1' && Number(stream?.nb_read_frames) === 288 && Math.abs(Number(stream?.duration) - 12) <= 0.001 && Math.abs(Number(format?.duration) - 12) <= 0.001 && moov > 0 && mdat > 0 && moov < mdat;
  const operationsExact = render.operations.blenderStarts === 1 && render.operations.eeveeRenderCalls === 288 && render.operations.cyclesRenderCalls === 0 && independent.operations.blenderStarts === 1 && independent.operations.renderCalls === 0 && [render, independent].every(row => row.operations.modelCalls === 0 && row.operations.networkCalls === 0 && row.operations.dockerProcesses === 0);
  const filesystem = await statfs(repositoryRoot), available = Number(filesystem.bavail) * Number(filesystem.bsize);
  const admissionExact = validSelf(admission, 'admissionHash') && admission.status === 'ADMITTED' && admission.correctionCommit === CORRECTION_COMMIT && admission.toolFreezeCommit === freeze && canonicalJson(admission.parentTree) === canonicalJson(parentTree) && canonicalJson(admission.retainedFailureTree) === canonicalJson(retainedTree) && canonicalJson(admission.bindings.tools) === canonicalJson(tools) && canonicalJson(admission.bindings.runtime) === canonicalJson(runtimeHashes) && admission.bindings.scene.sha256 === spec.parentEvidence.scene.sha256;
  const technical = { preregExact, retainedExact, parentExact, toolsExact, runtimeExact, admission: admissionExact, rootRosterExact, renderSelf: validSelf(render, 'reportHash') && render.status === 'PASS', independentSelf: validSelf(independent, 'reportHash') && independent.status === 'PASS', processes: Object.values(processChecks).every(Boolean), outputBudget: snapshot.bytes <= spec.processBudget.maximumOutputBytes, reserve: available >= spec.processBudget.minimumFreeReserveBytes };
  const gates = [
    ['G01_PREREGISTRATION_AND_T1_PARENT_EXACT', preregExact && retainedExact && parentExact],
    ['G02_RUNTIME_TOOL_OCIO_AND_CAPACITY_ADMISSION_EXACT', head === freeze && origin === freeze && toolsExact && runtimeExact && technical.admission && technical.reserve],
    ['G03_FRESH_ROOT_EXCLUSIVE_WRITES_AND_NO_SYMLINKS', rootRosterExact],
    ['G04_RENDER_BLENDER_EXIT_ZERO_AND_288_EEVEE_CALLS', processChecks.BLENDER_RENDER && technical.renderSelf && settingsExact && render.operations.eeveeRenderCalls === 288 && render.operations.cyclesRenderCalls === 0],
    ['G05_FRAME_ROSTER_DIMENSIONS_AND_CAMERA_ROUTING_EXACT', renderFramesExact && routingExact],
    ['G06_ALL_288_DECODED_PIXELS_FINITE_DYNAMIC_AND_NONEMPTY', pixelsExact],
    ['G07_THREE_SHOTS_AND_WHOLE_SEQUENCE_NOT_FROZEN', temporalExact],
    ['G08_BOTH_CUT_PAIR_DIGESTS_DIFFER', cutsExact],
    ['G09_INDEPENDENT_FRESH_BLENDER_REOPEN_EXACT', processChecks.BLENDER_INDEPENDENT && technical.independentSelf && independent.source.sha256 === spec.parentEvidence.scene.sha256],
    ['G10_ALL_96_CLOSE_FRAMES_PASS_UNCHANGED_GEOMETRY_TEMPLATE', geometryPass],
    ['G11_CONTACT_CORE_AND_WARM_LIGHT_CAUSAL_STATE_EXACT', causalExact],
    ['G12_FFMPEG_AND_FFPROBE_DELIVERY_METADATA_EXACT', processChecks.FFMPEG && processChecks.FFPROBE && videoExact],
    ['G13_PROCESS_RESOURCE_AND_OUTPUT_BUDGETS_PASS', technical.processes && technical.outputBudget && technical.reserve],
    ['G14_SELF_HASHED_REPORTS_RECEIPT_AND_ZERO_FORBIDDEN_OPERATIONS', technical.renderSelf && technical.independentSelf && validSelf(metadata, 'metadataHash') && operationsExact],
  ].map(([id, pass]) => ({ id, pass: Boolean(pass) }));
  req(gates.map(row => row.id).join('\0') === spec.acceptanceGates.join('\0'), 'gate roster mismatch');
  const invalidGateIds = ['G01_PREREGISTRATION_AND_T1_PARENT_EXACT', 'G02_RUNTIME_TOOL_OCIO_AND_CAPACITY_ADMISSION_EXACT', 'G03_FRESH_ROOT_EXCLUSIVE_WRITES_AND_NO_SYMLINKS', 'G04_RENDER_BLENDER_EXIT_ZERO_AND_288_EEVEE_CALLS', 'G05_FRAME_ROSTER_DIMENSIONS_AND_CAMERA_ROUTING_EXACT', 'G09_INDEPENDENT_FRESH_BLENDER_REOPEN_EXACT', 'G12_FFMPEG_AND_FFPROBE_DELIVERY_METADATA_EXACT', 'G13_PROCESS_RESOURCE_AND_OUTPUT_BUDGETS_PASS', 'G14_SELF_HASHED_REPORTS_RECEIPT_AND_ZERO_FORBIDDEN_OPERATIONS'];
  const infrastructurePass = gates.filter(row => invalidGateIds.includes(row.id)).every(row => row.pass);
  const status = infrastructurePass ? 'PASS' : 'FAIL';
  const verdict = infrastructurePass ? (gates.every(row => row.pass) ? spec.decision.supportedVerdict : spec.decision.rejectedVerdict) : null;
  const auditRecord = await writeHashed(resolve(root, 'audit.json'), { schemaVersion: 'bfs.b62TerminalAnimaticAudit.v0.1', experimentId: spec.experimentId, status, scientificVerdict: verdict, humanReview: 'HUMAN_PENDING', preregistrationCommit: PREREGISTRATION_COMMIT, correctionCommit: CORRECTION_COMMIT, toolFreezeCommit: freeze, gates, processChecks, technical, outcomes: { pixelsExact, temporalExact, cutsExact, geometryPass, causalExact }, bindings: { retainedFailureTree: retainedTree, admission: { sha256: await hashFile(resolve(root, 'admission.json')), admissionHash: admission.admissionHash }, render: { sha256: await hashFile(resolve(root, 'reports/render-report.json')), reportHash: render.reportHash }, independent: { sha256: await hashFile(resolve(root, 'reports/independent-audit.json')), reportHash: independent.reportHash }, metadata: { sha256: await hashFile(resolve(root, 'reports/video-metadata.json')), metadataHash: metadata.metadataHash }, video: { sha256: await hashFile(videoPath), bytes: videoBytes.length } }, rootBeforeAudit: snapshot, resources: { availableBytesAtAudit: available, maximumOutputBytes: spec.processBudget.maximumOutputBytes, minimumFreeReserveBytes: spec.processBudget.minimumFreeReserveBytes }, operations: { nodeAuditorProcesses: 1, priorBlenderStarts: 2, priorEeveeRenderCalls: 288, priorCyclesRenderCalls: 0, priorFfmpegProcesses: 1, priorFfprobeProcesses: 1, modelCalls: 0, networkCalls: 0, dockerProcesses: 0 }, nonClaims: spec.nonClaims }, 'auditHash');
  req(status === 'PASS', `invalid evidence: ${gates.filter(row => invalidGateIds.includes(row.id) && !row.pass).map(row => row.id).join(',')}`);
  console.log(`BFS_B62_T2_AUDIT PASS ${gates.filter(row => row.pass).length}/${gates.length} ${verdict} HUMAN_PENDING ${auditRecord.auditHash}`);
  return auditRecord;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) audit(parse()).catch(error => { console.error(`BFS_B62_T2_AUDIT_ERROR ${error.stack ?? error.message}`); process.exitCode = 1; });
