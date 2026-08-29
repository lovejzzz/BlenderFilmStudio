#!/usr/bin/env node

import { createHash } from 'node:crypto';
import { open, readFile } from 'node:fs/promises';
import { dirname, relative, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const repositoryRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const SPEC_URI = 'specs/b62-camera-quality-motion-aware-holdout-validation.v0.1.json';
const PROTOCOL_URI = 'research/2026-08-29-b62-d6-motion-aware-holdout-validation-protocol.md';
const ROOT_URI = 'experiments/b62-camera-quality-motion-aware-holdout-v0-1';
const TOOLS = ['blender/build_b62_q1_d6_motion_aware_scene.py', 'blender/render_b62_q1_d6_motion_aware_holdout_pairs.py', 'blender/audit_b62_q1_d6_motion_aware_scene_and_pixels.py', 'scripts/run-b62-q1-d6-motion-aware-holdout.mjs', 'scripts/audit-b62-q1-d6-motion-aware-holdout.mjs'];
const TOLERANCE = 1e-9;

function normalize(value) { if (typeof value === 'number' && Number.isFinite(value) && Number.isInteger(value)) return value; if (typeof value === 'number' && Number.isFinite(value)) { const bytes = Buffer.alloc(8); bytes.writeDoubleBE(value); return { $f64be: bytes.toString('hex') }; } if (Array.isArray(value)) return value.map(normalize); if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).sort(([a], [b]) => a.localeCompare(b)).map(([key, child]) => [key, normalize(child)])); return value; }
const canonicalJson = value => JSON.stringify(normalize(value));
const hashBytes = value => createHash('sha256').update(value).digest('hex');
const hashFile = async path => hashBytes(await readFile(path));
function req(condition, message) { if (!condition) throw new Error(message); }
function pathFor(uri) { req(uri && !uri.startsWith('/') && !uri.split('/').includes('..'), `unsafe ${uri}`); const path = resolve(repositoryRoot, uri); req(!relative(repositoryRoot, path).startsWith('../'), `escaped ${uri}`); return path; }
async function json(uri) { return JSON.parse(await readFile(pathFor(uri), 'utf8')); }
function validSelf(value, field) { if (!value || !/^[0-9a-f]{64}$/.test(value[field] ?? '')) return false; const copy = structuredClone(value), expected = copy[field]; delete copy[field]; return hashBytes(canonicalJson(copy)) === expected; }
async function writeHashed(path, value, field) { const body = structuredClone(value); body[field] = hashBytes(canonicalJson(body)); const handle = await open(path, 'wx', 0o600); try { await handle.writeFile(`${JSON.stringify(body, null, 2)}\n`); await handle.sync(); } finally { await handle.close(); } return body; }
function parse(argv) { req(argv.length === 4 && argv[0] === '--root' && argv[1] === ROOT_URI && argv[2] === '--tool-freeze-commit' && /^[0-9a-f]{40}$/.test(argv[3]), 'argument mismatch'); return argv[3]; }
function closeNumber(left, right) { return Number.isFinite(left) && Number.isFinite(right) && Math.abs(left - right) <= TOLERANCE; }
function sameArray(left, right) { return Array.isArray(left) && Array.isArray(right) && left.length === right.length && left.every((value, index) => typeof value === 'number' ? closeNumber(value, right[index]) : value === right[index]); }
function processPass(receipt, id, spec) { const limit = id === 'BUILD' ? spec.processBudget.maximumBuildWallSeconds : id === 'RENDER' ? spec.processBudget.maximumRenderWallSeconds : spec.processBudget.maximumIndependentWallSeconds; return validSelf(receipt, 'processHash') && receipt.experimentId === spec.experimentId && receipt.processId === id && receipt.result?.outcome === 'PASS' && receipt.result?.breach === null && receipt.result?.child?.exitCode === 0 && receipt.result?.metrics?.elapsedMs <= limit * 1000 && receipt.result?.metrics?.peakSampledRssBytes <= spec.processBudget.maximumPeakResidentSetSizeBytesPerBlender && receipt.result?.metrics?.logBytes <= spec.processBudget.maximumCombinedLogBytesPerChild; }
function smoothScale(frame) { const u = (frame - 193) / 95; return 2 + 0.25 * (3 * u * u - 2 * u * u * u); }
function geometryFeasible(row, template) { const visible = new Set(row.visibleAnchors); return template.faceAnchorsExact.every(name => visible.has(name)) && row.helmetVisualBlockerShare <= template.helmetVisualBlockerShareMaximum && row.characterVisualBlockerShare >= template.characterVisualBlockerShareMinimum && row.characterVisualBlockerShare <= template.characterVisualBlockerShareMaximum && row.characterProjection.onScreenVertexFraction >= template.characterOnScreenVertexFractionMinimum && row.characterProjection.onScreenVertexFraction <= template.characterOnScreenVertexFractionMaximum && row.characterProjection.clampedUnionAreaFraction >= template.characterClampedUnionAreaFractionMinimum && row.characterProjection.clampedUnionAreaFraction <= template.characterClampedUnionAreaFractionMaximum && row.visibleAnchorCount >= template.visibleSemanticAnchorCountMinimum; }

export async function audit(argv) {
  const freeze = parse(argv), root = pathFor(ROOT_URI);
  const spec = await json(SPEC_URI), admission = await json(`${ROOT_URI}/admission.json`), build = await json(`${ROOT_URI}/build.json`), render = await json(`${ROOT_URI}/render.json`), independent = await json(`${ROOT_URI}/independent.json`);
  const buildProcess = await json(`${ROOT_URI}/processes/BUILD.json`), renderProcess = await json(`${ROOT_URI}/processes/RENDER.json`), independentProcess = await json(`${ROOT_URI}/processes/INDEPENDENT.json`);
  req(spec.experimentId === 'B62-Q1-D6' && spec.statusBeforeToolCreation === 'PREREGISTERED' && spec.output.formalRoot === ROOT_URI, 'spec mismatch');
  req(validSelf(admission, 'admissionHash') && admission.status === 'ADMITTED' && admission.toolFreezeCommit === freeze, 'admission mismatch');
  req(admission.bindings.spec.sha256 === await hashFile(pathFor(SPEC_URI)) && admission.bindings.protocol.sha256 === await hashFile(pathFor(PROTOCOL_URI)), 'prereg binding');
  req(canonicalJson(admission.bindings.parentTree) === canonicalJson(spec.parentEvidence.d5Formal.tree) && admission.bindings.parentReceiptSha256 === spec.parentEvidence.d5Formal.receipt.sha256 && admission.bindings.parentAuditSha256 === spec.parentEvidence.d5Formal.audit.sha256, 'parent binding');
  req(admission.bindings.master.sha256 === spec.parentEvidence.masterScene.sha256 && admission.bindings.blenderSha256 === spec.runtime.blender.sha256, 'runtime binding');
  for (const uri of TOOLS) req(admission.bindings.tools[uri] === await hashFile(pathFor(uri)), `tool ${uri}`);
  req(processPass(buildProcess, 'BUILD', spec) && processPass(renderProcess, 'RENDER', spec) && processPass(independentProcess, 'INDEPENDENT', spec), 'process receipts');
  req(validSelf(build, 'reportHash') && validSelf(render, 'reportHash') && validSelf(independent, 'reportHash'), 'report self hashes');
  req(build.experimentId === spec.experimentId && render.experimentId === spec.experimentId && independent.experimentId === spec.experimentId && build.status === 'PASS' && render.status === 'PASS' && independent.status === 'PASS', 'report identity');
  req(`Blender ${build.blender.version}` === spec.runtime.blender.version && `Blender ${render.blender.version}` === spec.runtime.blender.version && `Blender ${independent.blender.version}` === spec.runtime.blender.version && [build, render, independent].every(row => row.blender.buildHash === spec.runtime.blender.buildHash), 'Blender identity');

  const expectedFrames = spec.validation.newlyUnsealedFrames, expectedConditions = spec.validation.conditions;
  const expectedRoster = expectedFrames.flatMap(frame => expectedConditions.map(condition => `${frame}|${condition}`));
  const renderRoster = render.renders.map(row => `${row.frame}|${row.condition}`), geometryRoster = independent.geometry.map(row => `${row.frame}|${row.condition}`), pixelRoster = independent.pixels.map(row => `${row.frame}|${row.condition}`);
  const noDerivation = [...render.renders, ...independent.geometry].every(row => expectedFrames.includes(row.frame) && !spec.validation.derivationFramesForbiddenForValidationMeasurement.includes(row.frame));
  const bakeFrames = build.bake.map(row => row.frame), independentBakeFrames = independent.bake.map(row => row.frame);
  const bakeExact = bakeFrames.length === 96 && bakeFrames.every((frame, index) => frame === 193 + index) && independentBakeFrames.length === 96 && independentBakeFrames.every((frame, index) => frame === 193 + index) && build.bake.every(row => closeNumber(row.staticScale, 2) && closeNumber(row.motionScale, smoothScale(row.frame))) && independent.bake.every(row => closeNumber(row.staticScale, 2) && closeNumber(row.motionScale, smoothScale(row.frame)) && row.staticMaxLocationError <= 1e-6 && row.motionMaxLocationError <= 1e-6);
  const before = build.stateBefore, after = build.stateAfter;
  const addedObjects = after.objects.filter(name => !before.objects.includes(name)).sort(), addedCameras = after.cameras.filter(name => !before.cameras.includes(name)).sort(), addedActions = after.actions.filter(name => !before.actions.includes(name)).sort();
  const sceneInvariant = canonicalJson(before.markers) === canonicalJson(after.markers) && canonicalJson(before.sourceAnimation) === canonicalJson(after.sourceAnimation) && canonicalJson(addedObjects) === canonicalJson([spec.selectedIntervention.motionCamera, spec.selectedIntervention.staticCamera].sort()) && canonicalJson(addedCameras) === canonicalJson(['CAM_CLOSE_MOTION_D6_DATA', 'CAM_CLOSE_STATIC_D6_DATA']) && canonicalJson(addedActions) === canonicalJson(['B62_D6_MOTION_CAMERA_BAKE', 'B62_D6_STATIC_CAMERA_BAKE']);
  const settingsExact = render.settings.engine === spec.render.engine && render.settings.device === spec.render.device && sameArray(render.settings.resolution, spec.render.resolution) && render.settings.samples === spec.render.samples && render.settings.format === spec.render.fileFormat && render.settings.pixelType === 'FLOAT' && render.settings.compression === spec.render.exrCodec && render.settings.viewTransform === spec.render.viewTransform && render.settings.look === spec.render.look;

  const routingExact = render.renders.every(row => row.camera === (row.condition === 'STATIC' ? spec.selectedIntervention.staticCamera : spec.selectedIntervention.motionCamera) && row.timelineMarker === 'SHOT_CLOSE_REFLECTION' && row.timelineMarkerCamera === row.camera);
  const fileChecks = [];
  for (const row of render.renders) {
    const exr = resolve(root, row.exr.uri), png = resolve(root, row.png.uri);
    fileChecks.push(await hashFile(exr) === row.exr.sha256 && await hashFile(png) === row.png.sha256 && row.exr.bytes > 0 && row.png.bytes > 0 && row.combined.width === 960 && row.combined.height === 540 && row.combined.nonFiniteCount === 0 && row.combined.rgbDynamicRange > 1e-6);
  }
  const independentPixelsExact = independent.pixels.every(row => { const source = render.renders.find(item => item.frame === row.frame && item.condition === row.condition); return source && row.exrSha256 === source.exr.sha256 && row.combined.sha256 === source.combined.sha256 && row.combined.width === 960 && row.combined.height === 540 && row.combined.nonFiniteCount === 0 && row.combined.rgbDynamicRange > 1e-6; });
  const pairExact = render.pairs.length === 8 && render.pairs.every(pair => pair.different === true && pair.staticCombinedSha256 !== pair.motionCombinedSha256);
  const geometryAccounting = independent.geometry.every(row => row.visibleAnchorCount === row.visibleAnchors.length && row.characterProjection.totalVertices === 4716 && row.characterProjection.onScreenVertices / row.characterProjection.totalVertices === row.characterProjection.onScreenVertexFraction && Object.values(row.groupCounts).reduce((sum, value) => sum + value, 0) === 576 && row.feasible === geometryFeasible(row, spec.validation.geometryTemplate));
  const motionRows = independent.geometry.filter(row => row.condition === 'MOTION_AWARE'), staticRows = independent.geometry.filter(row => row.condition === 'STATIC');
  const motionAllPass = motionRows.length === 8 && motionRows.every(row => row.feasible), staticPassed = staticRows.filter(row => row.feasible).map(row => row.frame), staticFailed = staticRows.filter(row => !row.feasible).map(row => row.frame);
  const outcomeExact = independent.outcome.motionAllPass === motionAllPass && canonicalJson(independent.outcome.staticPassedFrames) === canonicalJson(staticPassed) && canonicalJson(independent.outcome.staticFailedFrames) === canonicalJson(staticFailed);
  const scientificVerdict = motionAllPass ? spec.decision.supportedVerdict : spec.decision.rejectedVerdict;
  const operationsExact = build.operations.blenderStarts === 1 && build.operations.sceneSaves === 1 && build.operations.renderCalls === 0 && render.operations.blenderStarts === 1 && render.operations.renderCalls === 16 && independent.operations.blenderStarts === 1 && independent.operations.renderCalls === 0 && [build, render, independent].every(row => row.operations.modelCalls === 0 && row.operations.networkCalls === 0 && row.operations.dockerProcesses === 0);
  const checks = [
    ['SPEC_ADMISSION_PARENT_BOUND', true], ['TOOL_FREEZE_HASHES_EXACT', true], ['THREE_FRESH_BLENDER_PROCESSES_PASS', true], ['BLENDER_5_2_IDENTITY_EXACT', true],
    ['ZERO_MODEL_NETWORK_DOCKER', operationsExact], ['FRESH_SCENE_STATE_INVARIANTS', sceneInvariant], ['STATIC_AND_MOTION_BAKE_96_EXACT', bakeExact],
    ['VALIDATION_ROSTER_8_BY_2_EXACT', canonicalJson(renderRoster) === canonicalJson(expectedRoster) && canonicalJson(geometryRoster) === canonicalJson(expectedRoster) && canonicalJson(pixelRoster) === canonicalJson(expectedRoster)],
    ['NO_DERIVATION_FRAME_VALIDATION_MEASURED', noDerivation], ['CYCLES_SETTINGS_EXACT', settingsExact], ['TIMELINE_MARKER_AND_SCENE_CAMERA_ROUTING_EXACT', routingExact],
    ['SIXTEEN_EXR_PNG_FILES_HASHED', fileChecks.length === 16 && fileChecks.every(Boolean)], ['INDEPENDENT_EXR_DECODE_EXACT', independentPixelsExact], ['EIGHT_PIXEL_PAIRS_DIFFER', pairExact],
    ['GEOMETRY_TEMPLATE_RECOMPUTED', geometryAccounting], ['MOTION_OUTCOME_RECOMPUTED', outcomeExact], ['OUTCOME_NEUTRAL_VERDICT_MAPPED', [spec.decision.supportedVerdict, spec.decision.rejectedVerdict].includes(scientificVerdict)],
  ].map(([id, pass]) => ({ id, pass: Boolean(pass) }));
  const status = checks.every(row => row.pass) ? 'PASS' : 'FAIL';
  const auditRecord = await writeHashed(resolve(root, 'audit.json'), { schemaVersion: 'bfs.b62CameraQualityMotionAwareHoldoutAudit.v0.1', experimentId: spec.experimentId, status, scientificVerdict: status === 'PASS' ? scientificVerdict : null, humanReview: 'PENDING', toolFreezeCommit: freeze, checks, validationFrames: expectedFrames, conditions: expectedConditions, motionAllPass, staticPassedFrames: staticPassed, staticFailedFrames: staticFailed, motionGeometry: motionRows, staticGeometry: staticRows, inputs: { spec: { uri: SPEC_URI, sha256: await hashFile(pathFor(SPEC_URI)) }, protocol: { uri: PROTOCOL_URI, sha256: await hashFile(pathFor(PROTOCOL_URI)) }, admission: { uri: `${ROOT_URI}/admission.json`, sha256: await hashFile(resolve(root, 'admission.json')), admissionHash: admission.admissionHash }, build: { uri: `${ROOT_URI}/build.json`, sha256: await hashFile(resolve(root, 'build.json')), reportHash: build.reportHash }, render: { uri: `${ROOT_URI}/render.json`, sha256: await hashFile(resolve(root, 'render.json')), reportHash: render.reportHash }, independent: { uri: `${ROOT_URI}/independent.json`, sha256: await hashFile(resolve(root, 'independent.json')), reportHash: independent.reportHash } }, nonClaims: spec.nonClaims }, 'auditHash');
  req(status === 'PASS', `audit failed ${checks.filter(row => !row.pass).map(row => row.id).join(',')}`);
  process.stdout.write(`BFS_B62_Q1_D6_AUDIT PASS ${checks.length}/${checks.length} ${scientificVerdict} HUMAN_PENDING ${auditRecord.auditHash}\n`);
  return auditRecord;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) audit(process.argv.slice(2)).catch(error => { process.stderr.write(`BFS_B62_Q1_D6_AUDIT_ERROR ${error.message}\n`); process.exitCode = 1; });
