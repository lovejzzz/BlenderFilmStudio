#!/usr/bin/env node

import { createHash } from 'node:crypto';
import { open, readFile } from 'node:fs/promises';
import { dirname, relative, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const repositoryRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const SPEC_URI = 'specs/b62-camera-quality-motion-aware-search.v0.1.json';
const PROTOCOL_URI = 'research/2026-08-29-b62-d5-motion-aware-camera-search-protocol.md';
const C1_URI = 'specs/b62-camera-quality-d5-c1-probe-camera-transform-sync.v0.1.json';
const C1_PROTOCOL_URI = 'research/2026-08-29-b62-d5-c1-probe-camera-transform-sync.md';
const C2_URI = 'specs/b62-camera-quality-d5-c2-retire-contaminated-d3-baseline.v0.1.json';
const C2_PROTOCOL_URI = 'research/2026-08-29-b62-d5-c2-retire-contaminated-d3-baseline.md';
const C3_URI = 'specs/b62-camera-quality-d5-c3-v02-comparison-hash-typo.v0.1.json';
const C3_PROTOCOL_URI = 'research/2026-08-29-b62-d5-c3-v02-comparison-hash-typo.md';
const C4_URI = 'specs/b62-camera-quality-d5-c4-quaternion-record-primitive.v0.1.json';
const C4_PROTOCOL_URI = 'research/2026-08-29-b62-d5-c4-quaternion-record-primitive.md';
const ROOT_URI = 'experiments/b62-camera-quality-motion-aware-search-v0-4';
const V0_1_ROOT = 'experiments/b62-camera-quality-motion-aware-search-v0-1';
const V0_2_ROOT = 'experiments/b62-camera-quality-motion-aware-search-v0-2';
const V0_3_ROOT = 'experiments/b62-camera-quality-motion-aware-search-v0-3';
const D4_ROOT = 'experiments/b62-camera-quality-holdout-render-v0-5';
const D3_ROOT = 'experiments/b62-camera-quality-bounded-candidate-search-v0-2';
const TOOLS = [
  'blender/search_b62_q1_d5_motion_aware_camera.py',
  'blender/search_b62_q1_d5_motion_aware_camera_independent.py',
  'scripts/run-b62-q1-d5-motion-aware-search.mjs',
  'scripts/audit-b62-q1-d5-motion-aware-search.mjs',
];
const TOLERANCE = 1e-9;

function canonicalize(value) { if (Array.isArray(value)) return value.map(canonicalize); if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).sort(([a], [b]) => a.localeCompare(b)).map(([key, child]) => [key, canonicalize(child)])); return value; }
const canonicalJson = value => JSON.stringify(canonicalize(value));
const hashBytes = value => createHash('sha256').update(value).digest('hex');
const hashFile = async path => hashBytes(await readFile(path));
function requireValue(condition, message) { if (!condition) throw new Error(message); }
function localPath(uri) { requireValue(uri && !uri.startsWith('/') && !uri.split('/').includes('..'), `unsafe ${uri}`); const path = resolve(repositoryRoot, uri); requireValue(!relative(repositoryRoot, path).startsWith('../'), `escaped ${uri}`); return path; }
async function json(uri) { return JSON.parse(await readFile(localPath(uri), 'utf8')); }
function validSelfHash(value, field) { if (!value || !/^[0-9a-f]{64}$/.test(value[field] ?? '')) return false; const copy = structuredClone(value); const expected = copy[field]; delete copy[field]; return hashBytes(canonicalJson(copy)) === expected; }
async function writeHashed(path, value, field) { const body = structuredClone(value); body[field] = hashBytes(canonicalJson(body)); const handle = await open(path, 'wx', 0o600); try { await handle.writeFile(`${JSON.stringify(body, null, 2)}\n`); await handle.sync(); } finally { await handle.close(); } return body; }

function parseArgs(argv) { requireValue(argv.length === 4 && argv[0] === '--root' && argv[1] === ROOT_URI && argv[2] === '--tool-freeze-commit' && /^[0-9a-f]{40}$/.test(argv[3]), 'argument mismatch'); return argv[3]; }
function compare(left, right, path, mismatches) {
  if (typeof left === 'number' && typeof right === 'number') { if (!Number.isFinite(left) || !Number.isFinite(right) || Math.abs(left - right) > TOLERANCE) mismatches.push({ path, primary: left, independent: right }); return; }
  if (Array.isArray(left) || Array.isArray(right)) { if (!Array.isArray(left) || !Array.isArray(right) || left.length !== right.length) { mismatches.push({ path, primary: left, independent: right }); return; } for (let index = 0; index < left.length; index += 1) compare(left[index], right[index], `${path}[${index}]`, mismatches); return; }
  if (left && right && typeof left === 'object' && typeof right === 'object') { const a = Object.keys(left).sort(), b = Object.keys(right).sort(); if (a.join('\0') !== b.join('\0')) { mismatches.push({ path, primaryKeys: a, independentKeys: b }); return; } for (const key of a) compare(left[key], right[key], `${path}.${key}`, mismatches); return; }
  if (left !== right) mismatches.push({ path, primary: left, independent: right });
}
function processPass(receipt, id, spec) { return validSelfHash(receipt, 'processHash') && receipt.experimentId === spec.experimentId && receipt.processId === id && receipt.result?.outcome === 'PASS' && receipt.result?.breach === null && receipt.result?.child?.exitCode === 0 && receipt.result?.metrics?.peakSampledRssBytes <= spec.processBudget.maximumPeakResidentSetSizeBytesPerBlender && receipt.result?.metrics?.logBytes <= spec.processBudget.maximumCombinedLogBytesPerChild; }
function atmosphereExact(row) { return row?.object === 'B62_ATMOSPHERE' && row.classification === 'VOLUME_ONLY_PASS_THROUGH' && row.materials?.length === 1 && row.materials[0].material === 'MAT_B62_VOLUME' && row.materials[0].surfaceLinked === false && row.materials[0].volumeLinked === true; }
function idFor(start, end) { return `RS_S${String(Math.round(start * 100)).padStart(3, '0')}_E${String(Math.round(end * 100)).padStart(3, '0')}`; }
function scaleAt(frame, start, end) { const u = (frame - 193) / 95; return start + (end - start) * (3 * u * u - 2 * u * u * u); }
function pathStatistics(start, end) { const values = Array.from({ length: 96 }, (_, index) => scaleAt(193 + index, start, end)); const deltas = values.slice(1).map((value, index) => value - values[index]); return { maximumDelta: Math.max(...deltas), monotonic: deltas.every(value => value >= 0), meanDeviation: values.reduce((sum, value) => sum + Math.abs(value - 2), 0) / values.length }; }
function frameTemplate(row) {
  const visible = new Set(row.visibleAnchors);
  return visible.has('B62_VISOR') && visible.has('B62_EYE_SLIT') && row.helmetVisualBlockerShare <= 0.70 && row.characterVisualBlockerShare >= 0.20 && row.characterVisualBlockerShare <= 0.90 && row.characterProjection.onScreenVertexFraction >= 0.10 && row.characterProjection.onScreenVertexFraction <= 0.60 && row.characterProjection.clampedUnionAreaFraction >= 0.35 && row.characterProjection.clampedUnionAreaFraction <= 0.90 && row.visibleAnchorCount >= 2;
}
function winner(candidates) { const feasible = candidates.filter(row => row.feasible); feasible.sort((a, b) => Math.abs(a.startScale - 2) - Math.abs(b.startScale - 2) || Math.abs(a.endScale - 2) - Math.abs(b.endScale - 2) || a.meanAbsoluteIntegerFrameScaleDeviationFromTwo - b.meanAbsoluteIntegerFrameScaleDeviationFromTwo || a.candidateId.localeCompare(b.candidateId)); return feasible[0]?.candidateId ?? null; }
function withoutPoseAndScale(row) { const clone = structuredClone(row); delete clone.radialScale; delete clone.evaluatedCameraLocation; delete clone.assignedCameraQuaternion; return clone; }
function d4ComparableFromD5(row) { return { objectCounts: row.objectCounts, groupCounts: row.groupCounts, helmetVisualBlockerShare: row.helmetVisualBlockerShare, characterVisualBlockerShare: row.characterVisualBlockerShare, visibleAnchors: row.visibleAnchors, visibleAnchorCount: row.visibleAnchorCount, characterProjection: row.characterProjection, feasible: row.feasible }; }
function d4Comparable(row) { return { objectCounts: row.objectCounts, groupCounts: row.groupCounts, helmetVisualBlockerShare: row.helmetVisualBlockerShare, characterVisualBlockerShare: row.characterVisualBlockerShare, visibleAnchors: row.visibleAnchors, visibleAnchorCount: row.visibleAnchorCount, characterProjection: row.characterProjection, feasible: row.feasible }; }
async function c4CorrectionOnly(uri, frozenHash, implementation) {
  let source = await readFile(localPath(uri), 'utf8');
  if (implementation === 'PRIMARY') {
    const current = '"assignedCameraQuaternion": [float(value) for value in camera.rotation_quaternion]';
    requireValue(source.split(current).length === 2, `C4 primary correction count ${uri}`);
    source = source.replace(current, '"evaluatedCameraQuaternion": [float(value) for value in evaluated_matrix.to_quaternion()]');
  } else {
    const current = '"assignedCameraQuaternion": [float(value) for value in probe_camera.rotation_quaternion]';
    requireValue(source.split(current).length === 2, `C4 independent correction count ${uri}`);
    source = source.replace(current, '"evaluatedCameraQuaternion": [float(value) for value in evaluated_transform.to_quaternion()]');
  }
  return hashBytes(source) === frozenHash;
}

export async function audit(argv) {
  const freeze = parseArgs(argv), root = localPath(ROOT_URI);
  const spec = await json(SPEC_URI), c1 = await json(C1_URI), c2 = await json(C2_URI), c3 = await json(C3_URI), c4 = await json(C4_URI), admission = await json(`${ROOT_URI}/admission.json`), primary = await json(`${ROOT_URI}/primary.json`), independent = await json(`${ROOT_URI}/independent.json`);
  const primaryProcess = await json(`${ROOT_URI}/processes/PRIMARY.json`), independentProcess = await json(`${ROOT_URI}/processes/INDEPENDENT.json`);
  const d3Primary = await json(`${D3_ROOT}/primary.json`), d4Independent = await json(`${D4_ROOT}/independent.json`), d4Build = await json(c2.authoritativeBaseline.d4BuildReport.uri);
  requireValue(spec.experimentId === 'B62-Q1-D5' && spec.statusBeforeToolCreation === 'PREREGISTERED' && spec.output.formalRoot === V0_1_ROOT, 'spec mismatch');
  requireValue(c1.correctionId === 'B62-Q1-D5-C1' && c1.statusBeforeToolChange === 'PREREGISTERED' && c1.retainedFailure.root === V0_1_ROOT && c1.authorizedChanges.retryRoot === V0_2_ROOT, 'C1 mismatch');
  requireValue(c2.correctionId === 'B62-Q1-D5-C2' && c2.statusBeforeToolChange === 'PREREGISTERED' && c2.retainedFailures.v0_1.root === V0_1_ROOT && c2.retainedFailures.v0_2.root === V0_2_ROOT && c2.authorizedChanges.retryRoot === V0_3_ROOT, 'C2 mismatch');
  requireValue(c3.correctionId === 'B62-Q1-D5-C3' && c3.statusBeforeNodeToolChange === 'PREREGISTERED' && c3.preAdmissionRejection.formalRootCreated === false && c3.authorizedChanges.retryRoot === V0_3_ROOT, 'C3 mismatch');
  requireValue(c4.correctionId === 'B62-Q1-D5-C4' && c4.statusBeforeToolChange === 'PREREGISTERED' && c4.retainedFailure.root === V0_3_ROOT && c4.authorizedChanges.retryRoot === ROOT_URI, 'C4 mismatch');
  requireValue(validSelfHash(admission, 'admissionHash') && admission.status === 'ADMITTED' && admission.toolFreezeCommit === freeze, 'admission mismatch');
  requireValue(admission.bindings.spec.sha256 === await hashFile(localPath(SPEC_URI)) && admission.bindings.protocol.sha256 === await hashFile(localPath(PROTOCOL_URI)), 'protocol binding mismatch');
  requireValue(admission.bindings.c1.sha256 === await hashFile(localPath(C1_URI)) && admission.bindings.c1Protocol.sha256 === await hashFile(localPath(C1_PROTOCOL_URI)) && admission.bindings.c2.sha256 === await hashFile(localPath(C2_URI)) && admission.bindings.c2Protocol.sha256 === await hashFile(localPath(C2_PROTOCOL_URI)) && admission.bindings.c3.sha256 === await hashFile(localPath(C3_URI)) && admission.bindings.c3Protocol.sha256 === await hashFile(localPath(C3_PROTOCOL_URI)) && admission.bindings.c4.sha256 === await hashFile(localPath(C4_URI)) && admission.bindings.c4Protocol.sha256 === await hashFile(localPath(C4_PROTOCOL_URI)), 'correction binding mismatch');
  requireValue(canonicalJson(admission.bindings.retainedV01Tree) === canonicalJson(c2.retainedFailures.v0_1.tree) && canonicalJson(admission.bindings.retainedV02Tree) === canonicalJson(c2.retainedFailures.v0_2.tree) && canonicalJson(admission.bindings.retainedV03Tree) === canonicalJson(c4.retainedFailure.tree) && admission.bindings.retainedV02FailureSha256 === c2.retainedFailures.v0_2.failure.sha256 && admission.bindings.retainedV02AuditSha256 === c2.retainedFailures.v0_2.audit.sha256 && admission.bindings.retainedV02ComparisonSha256 === c3.correctValue.sha256 && admission.bindings.retainedV03FailureSha256 === c4.retainedFailure.failure.sha256 && admission.bindings.retainedV03AuditSha256 === c4.retainedFailure.audit.sha256 && admission.bindings.retainedV03ComparisonSha256 === c4.retainedFailure.comparison.sha256 && await hashFile(localPath(c3.correctValue.uri)) === c3.correctValue.sha256, 'retained failure binding mismatch');
  requireValue(admission.bindings.correctionScopeExact === true && admission.bindings.c4FrozenToolHashes[TOOLS[0]] === c4.frozenBeforeCorrection.primaryBlenderToolSha256 && admission.bindings.c4FrozenToolHashes[TOOLS[1]] === c4.frozenBeforeCorrection.independentBlenderToolSha256, 'C4 scope binding mismatch');
  requireValue(await c4CorrectionOnly(TOOLS[0], c4.frozenBeforeCorrection.primaryBlenderToolSha256, 'PRIMARY') && await c4CorrectionOnly(TOOLS[1], c4.frozenBeforeCorrection.independentBlenderToolSha256, 'INDEPENDENT'), 'C4 Blender correction scope exceeded');
  requireValue(canonicalJson(admission.bindings.d4Tree) === canonicalJson(spec.parentEvidence.d4Formal.tree) && canonicalJson(admission.bindings.d3Tree) === canonicalJson(spec.parentEvidence.d3Search.tree), 'parent tree binding mismatch');
  requireValue(admission.bindings.d4ReceiptSha256 === spec.parentEvidence.d4Formal.receipt.sha256 && admission.bindings.d4AuditSha256 === spec.parentEvidence.d4Formal.audit.sha256, 'D4 binding mismatch');
  requireValue(admission.bindings.d4BuildSha256 === c2.authoritativeBaseline.d4BuildReport.sha256 && await hashFile(localPath(c2.authoritativeBaseline.d4BuildReport.uri)) === c2.authoritativeBaseline.d4BuildReport.sha256 && d4Build.reportHash === c2.authoritativeBaseline.d4BuildReport.reportHash, 'D4 build binding mismatch');
  requireValue(admission.bindings.master.sha256 === spec.parentEvidence.masterScene.sha256 && admission.bindings.blenderSha256 === spec.runtime.blender.sha256, 'runtime binding mismatch');
  for (const uri of TOOLS) requireValue(admission.bindings.tools[uri] === await hashFile(localPath(uri)), `tool mismatch ${uri}`);
  requireValue(processPass(primaryProcess, 'PRIMARY', spec) && processPass(independentProcess, 'INDEPENDENT', spec), 'process mismatch');
  for (const [document, implementation] of [[primary, 'PRIMARY'], [independent, 'INDEPENDENT']]) {
    requireValue(document.schemaVersion === 'bfs.b62CameraQualityMotionAwareSearchObservation.v0.1' && document.experimentId === spec.experimentId && document.implementation === implementation && document.status === 'OBSERVED', `${implementation} identity`);
    requireValue(`Blender ${document.blender.version}` === spec.runtime.blender.version && document.blender.buildHash === spec.runtime.blender.buildHash, `${implementation} Blender`);
    requireValue(document.master.expectedSha256 === spec.parentEvidence.masterScene.sha256 && atmosphereExact(document.materialAwareAtmosphere), `${implementation} source/material`);
    requireValue(document.operations.blenderStarts === 1 && document.operations.framesSet === 126 && document.operations.renderCalls === 0 && document.operations.modelCalls === 0 && document.operations.networkCalls === 0 && document.operations.dockerProcesses === 0 && document.operations.sceneSaves === 0, `${implementation} operations`);
  }

  const primaryComparable = structuredClone(primary), independentComparable = structuredClone(independent);
  delete primaryComparable.implementation; delete independentComparable.implementation;
  const implementationMismatches = [];
  compare(primaryComparable, independentComparable, '$', implementationMismatches);

  const derivationExact = canonicalJson(primary.derivationFramesEvaluated) === canonicalJson(spec.derivation.frames);
  const sealedExact = canonicalJson(primary.sealedValidationFramesNotEvaluated) === canonicalJson(spec.sealedValidation.frames);
  const allFrameRows = primary.candidates.flatMap(candidate => candidate.frames.map(frame => frame.frame));
  const noSealed = allFrameRows.every(frame => spec.derivation.frames.includes(frame) && !spec.sealedValidation.frames.includes(frame));
  const expectedRoster = [];
  for (const start of spec.cameraFamily.startScaleGrid) for (const end of spec.cameraFamily.endScaleGrid) if (end >= start) expectedRoster.push({ id: idFor(start, end), start, end });
  const rosterExact = expectedRoster.length === primary.candidates.length && expectedRoster.every((expected, index) => {
    const observed = primary.candidates[index];
    return observed.candidateId === expected.id && observed.startScale === expected.start && observed.endScale === expected.end && observed.azimuthDegrees === spec.cameraFamily.azimuthDegreesAroundWorldZ && observed.lensMillimeters === spec.cameraFamily.lensMillimeters;
  });
  const pathMismatches = [], feasibilityMismatches = [];
  for (const candidate of primary.candidates) {
    const stats = pathStatistics(candidate.startScale, candidate.endScale);
    compare(candidate.maximumAdjacentIntegerFrameScaleDelta, stats.maximumDelta, `${candidate.candidateId}.maximumDelta`, pathMismatches);
    compare(candidate.meanAbsoluteIntegerFrameScaleDeviationFromTwo, stats.meanDeviation, `${candidate.candidateId}.meanDeviation`, pathMismatches);
    if (candidate.monotonicNondecreasing !== stats.monotonic || stats.maximumDelta > spec.cameraFamily.maximumPerIntegerFrameScaleDelta) pathMismatches.push({ path: candidate.candidateId, reason: 'path contract' });
    if (canonicalJson(candidate.frames.map(row => row.frame)) !== canonicalJson(spec.derivation.frames)) pathMismatches.push({ path: candidate.candidateId, reason: 'frame roster' });
    for (const frame of candidate.frames) {
      compare(frame.radialScale, scaleAt(frame.frame, candidate.startScale, candidate.endScale), `${candidate.candidateId}.frame${frame.frame}.scale`, pathMismatches);
      const expectedVisible = frame.anchors.filter(row => row.exactTargetVisible).map(row => row.anchor);
      if (canonicalJson(expectedVisible) !== canonicalJson(frame.visibleAnchors) || frame.visibleAnchorCount !== expectedVisible.length || frame.faceAnchorVisibleCount !== expectedVisible.filter(name => ['B62_VISOR', 'B62_EYE_SLIT'].includes(name)).length || frame.feasible !== frameTemplate(frame)) feasibilityMismatches.push({ candidateId: candidate.candidateId, frame: frame.frame });
    }
    const expectedFeasible = stats.monotonic && stats.maximumDelta <= spec.cameraFamily.maximumPerIntegerFrameScaleDelta && candidate.frames.every(frameTemplate);
    if (candidate.feasible !== expectedFeasible) feasibilityMismatches.push({ candidateId: candidate.candidateId, reason: 'candidate aggregate' });
  }

  const baseline = primary.candidates.find(row => row.candidateId === spec.cameraFamily.baselineCandidate);
  const d3ContaminationMismatches = [], d4PoseMismatches = [], d4GeometryMismatches = [];
  const d3Selected = d3Primary.candidates.find(row => row.candidateId === spec.parentEvidence.d3Search.selectedCandidateId);
  for (const retained of d3Selected.frames) {
    const observed = baseline.frames.find(row => row.frame === retained.frame);
    compare(withoutPoseAndScale(observed), retained, `D3.frame${retained.frame}`, d3ContaminationMismatches);
  }
  for (const frame of c2.authoritativeBaseline.poseFramesAllowedForD5) {
    const observed = baseline.frames.find(row => row.frame === frame);
    const retained = d4Build.bake.find(row => row.frame === frame);
    compare(observed.evaluatedCameraLocation, retained.correctedLocation, `D4_POSE.frame${frame}.location`, d4PoseMismatches);
    compare(observed.assignedCameraQuaternion, retained.correctedQuaternion, `D4_POSE.frame${frame}.quaternion`, d4PoseMismatches);
  }
  for (const retained of d4Independent.geometry.filter(row => row.condition === 'CORRECTED')) {
    const observed = baseline.frames.find(row => row.frame === retained.frame);
    compare(d4ComparableFromD5(observed), d4Comparable(retained), `D4_GEOMETRY.frame${retained.frame}`, d4GeometryMismatches);
  }

  const selected = winner(primary.candidates), feasibleCount = primary.candidates.filter(row => row.feasible).length;
  const scientificVerdict = feasibleCount > 0 ? spec.decision.supportedVerdict : spec.decision.rejectedVerdict;
  const comparison = await writeHashed(resolve(root, 'comparison.json'), {
    schemaVersion: 'bfs.b62CameraQualityMotionAwareComparison.v0.1', experimentId: spec.experimentId,
    status: implementationMismatches.length === 0 ? 'PASS' : 'FAIL', toleranceAbsolute: TOLERANCE,
    comparedCandidateCount: primary.candidateCount, comparedCandidateFrameCount: allFrameRows.length,
    implementationMismatches, d3ContaminationMismatches, d4PoseMismatches, d4GeometryMismatches,
    pathMismatches, feasibilityMismatches, feasibleCandidateCount: feasibleCount,
    baselineCandidateId: baseline?.candidateId ?? null, baselineFeasible: baseline?.feasible ?? null,
    selectedCandidateId: selected, scientificVerdict,
  }, 'comparisonHash');

  const checks = [
    ['SPEC_C1_C2_C3_C4_ADMISSION_PARENTS_BOUND', true], ['RETAINED_V0_1_V0_2_V0_3_FAILURES_BOUND', true],
    ['C4_SCOPE_EXACT_QUATERNION_PRIMITIVE_ONLY', true], ['TOOL_FREEZE_HASHES_EXACT', true],
    ['TWO_FRESH_BLENDER_PROCESSES_PASS', true], ['BLENDER_5_2_IDENTITY_EXACT', true],
    ['ZERO_RENDER_MODEL_NETWORK_DOCKER_SCENE_SAVE', true], ['DERIVATION_FRAMES_9_EXACT', derivationExact],
    ['SEALED_VALIDATION_ROSTER_8_EXACT', sealedExact], ['NO_SEALED_FRAME_ACCESSED', noSealed],
    ['CANDIDATE_GRID_14_EXACT', primary.candidateCount === 14 && rosterExact],
    ['CANDIDATE_FRAME_CELLS_126_EXACT', allFrameRows.length === 126 && primary.candidates.every(row => row.frames.length === 9)],
    ['SMOOTHSTEP_PATH_RECOMPUTED', pathMismatches.length === 0],
    ['GEOMETRY_TEMPLATE_RECOMPUTED', feasibilityMismatches.length === 0],
    ['ATMOSPHERE_VOLUME_ONLY_PASS_THROUGH', atmosphereExact(primary.materialAwareAtmosphere) && atmosphereExact(independent.materialAwareAtmosphere)],
    ['D3_CONTAMINATION_RETAINED_EXPLICIT', d3ContaminationMismatches.length === c2.retainedFailures.v0_2.comparison.d3GeometryMismatchCount && d3ContaminationMismatches.every(row => row.path.startsWith('D3.'))],
    ['STATIC_BASELINE_POSE_REPRODUCES_D4_BAKE_9', d4PoseMismatches.length === 0],
    ['STATIC_BASELINE_GEOMETRY_REPRODUCES_D4_6', d4GeometryMismatches.length === 0],
    ['STATIC_BASELINE_FAILS', baseline?.feasible === false && primary.baselineFeasible === false],
    ['PRIMARY_INDEPENDENT_AGREE', implementationMismatches.length === 0],
    ['FEASIBLE_COUNT_RECOMPUTED', primary.feasibleCandidateCount === feasibleCount],
    ['SELECTION_RECOMPUTED_EXACT', primary.selectedCandidateId === selected],
    ['OUTCOME_NEUTRAL_VERDICT_MAPPED', [spec.decision.supportedVerdict, spec.decision.rejectedVerdict].includes(scientificVerdict)],
  ].map(([id, pass]) => ({ id, pass: Boolean(pass) }));
  const status = checks.every(row => row.pass) ? 'PASS' : 'FAIL';
  const selectedCandidate = primary.candidates.find(row => row.candidateId === selected) ?? null;
  const auditRecord = await writeHashed(resolve(root, 'audit.json'), {
    schemaVersion: 'bfs.b62CameraQualityMotionAwareSearchAudit.v0.1', experimentId: spec.experimentId,
    status, scientificVerdict: status === 'PASS' ? scientificVerdict : null, toolFreezeCommit: freeze,
    checks, derivationFrames: primary.derivationFramesEvaluated, sealedValidationFrames: primary.sealedValidationFramesNotEvaluated,
    baseline: baseline ? { candidateId: baseline.candidateId, feasible: baseline.feasible, frames: baseline.frames } : null,
    feasibleCandidateCount: feasibleCount, selectedCandidateId: selected, selectedCandidate,
    inputs: {
      spec: { uri: SPEC_URI, sha256: await hashFile(localPath(SPEC_URI)) },
      protocol: { uri: PROTOCOL_URI, sha256: await hashFile(localPath(PROTOCOL_URI)) },
      c1: { uri: C1_URI, sha256: await hashFile(localPath(C1_URI)) },
      c1Protocol: { uri: C1_PROTOCOL_URI, sha256: await hashFile(localPath(C1_PROTOCOL_URI)) },
      c2: { uri: C2_URI, sha256: await hashFile(localPath(C2_URI)) },
      c2Protocol: { uri: C2_PROTOCOL_URI, sha256: await hashFile(localPath(C2_PROTOCOL_URI)) },
      c3: { uri: C3_URI, sha256: await hashFile(localPath(C3_URI)) },
      c3Protocol: { uri: C3_PROTOCOL_URI, sha256: await hashFile(localPath(C3_PROTOCOL_URI)) },
      c4: { uri: C4_URI, sha256: await hashFile(localPath(C4_URI)) },
      c4Protocol: { uri: C4_PROTOCOL_URI, sha256: await hashFile(localPath(C4_PROTOCOL_URI)) },
      retainedV01Failure: { uri: c1.retainedFailure.failure.uri, sha256: await hashFile(localPath(c1.retainedFailure.failure.uri)), failureHash: c1.retainedFailure.failure.failureHash },
      retainedV02Failure: { uri: c2.retainedFailures.v0_2.failure.uri, sha256: await hashFile(localPath(c2.retainedFailures.v0_2.failure.uri)), failureHash: c2.retainedFailures.v0_2.failure.failureHash },
      retainedV03Failure: { uri: c4.retainedFailure.failure.uri, sha256: await hashFile(localPath(c4.retainedFailure.failure.uri)), failureHash: c4.retainedFailure.failure.failureHash },
      admission: { uri: `${ROOT_URI}/admission.json`, sha256: await hashFile(resolve(root, 'admission.json')), admissionHash: admission.admissionHash },
      d3Primary: { uri: `${D3_ROOT}/primary.json`, sha256: await hashFile(localPath(`${D3_ROOT}/primary.json`)) },
      d4Independent: { uri: `${D4_ROOT}/independent.json`, sha256: await hashFile(localPath(`${D4_ROOT}/independent.json`)) },
      d4Build: { uri: c2.authoritativeBaseline.d4BuildReport.uri, sha256: await hashFile(localPath(c2.authoritativeBaseline.d4BuildReport.uri)), reportHash: c2.authoritativeBaseline.d4BuildReport.reportHash },
      primary: { uri: `${ROOT_URI}/primary.json`, sha256: await hashFile(resolve(root, 'primary.json')) },
      independent: { uri: `${ROOT_URI}/independent.json`, sha256: await hashFile(resolve(root, 'independent.json')) },
      comparison: { uri: `${ROOT_URI}/comparison.json`, sha256: await hashFile(resolve(root, 'comparison.json')), comparisonHash: comparison.comparisonHash },
    },
    nonClaims: spec.nonClaims,
  }, 'auditHash');
  requireValue(status === 'PASS', `audit failed ${checks.filter(row => !row.pass).map(row => row.id).join(',')}`);
  process.stdout.write(`BFS_B62_Q1_D5_AUDIT PASS ${checks.length}/${checks.length} ${scientificVerdict} ${selected ?? 'NONE'} ${auditRecord.auditHash}\n`);
  return auditRecord;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) audit(process.argv.slice(2)).catch(error => { process.stderr.write(`BFS_B62_Q1_D5_AUDIT_ERROR ${error.message}\n`); process.exitCode = 1; });
