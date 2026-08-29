#!/usr/bin/env node

import { createHash } from 'node:crypto';
import { open, readFile } from 'node:fs/promises';
import { dirname, relative, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const repositoryRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const SPEC_URI = 'specs/b62-camera-quality-bounded-candidate-search.v0.1.json';
const PROTOCOL_URI = 'research/2026-08-29-b62-close-camera-bounded-search-protocol.md';
const ROOT_URI = 'experiments/b62-camera-quality-bounded-candidate-search-v0-1';
const TOOLS = ['blender/search_b62_q1_close_camera_candidates.py', 'blender/audit_b62_q1_close_camera_candidates.py', 'scripts/run-b62-q1-close-camera-search.mjs', 'scripts/audit-b62-q1-close-camera-search.mjs'];
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
function recomputeWinner(candidates) { const feasible = candidates.filter(row => row.feasible); feasible.sort((a, b) => a.interventionCost - b.interventionCost || b.minimumVisibleAnchorCount - a.minimumVisibleAnchorCount || a.maximumHelmetVisualBlockerShare - b.maximumHelmetVisualBlockerShare || b.minimumFaceAnchorVisibleCount - a.minimumFaceAnchorVisibleCount || a.candidateId.localeCompare(b.candidateId)); return feasible[0]?.candidateId ?? null; }
function atmosphereExact(row) { return row?.object === 'B62_ATMOSPHERE' && row.classification === 'VOLUME_ONLY_PASS_THROUGH' && row.materials?.length === 1 && row.materials[0].material === 'MAT_B62_VOLUME' && row.materials[0].surfaceLinked === false && row.materials[0].volumeLinked === true; }

export async function audit(argv) {
  const freeze = parseArgs(argv), root = localPath(ROOT_URI);
  const spec = await json(SPEC_URI), admission = await json(`${ROOT_URI}/admission.json`), primary = await json(`${ROOT_URI}/primary.json`), independent = await json(`${ROOT_URI}/independent.json`), primaryProcess = await json(`${ROOT_URI}/processes/PRIMARY.json`), independentProcess = await json(`${ROOT_URI}/processes/INDEPENDENT.json`);
  requireValue(spec.experimentId === 'B62-Q1-D3' && spec.statusBeforeToolCreation === 'PREREGISTERED', 'spec mismatch');
  requireValue(validSelfHash(admission, 'admissionHash') && admission.status === 'ADMITTED' && admission.toolFreezeCommit === freeze, 'admission mismatch');
  requireValue(admission.bindings.spec.sha256 === await hashFile(localPath(SPEC_URI)) && admission.bindings.protocol.sha256 === await hashFile(localPath(PROTOCOL_URI)), 'protocol binding mismatch');
  requireValue(canonicalJson(admission.bindings.parentTree) === canonicalJson(spec.parentEvidence.d2.tree) && admission.bindings.parentReceiptSha256 === spec.parentEvidence.d2.receipt.sha256, 'parent binding mismatch');
  for (const uri of TOOLS) requireValue(admission.bindings.tools[uri] === await hashFile(localPath(uri)), `tool mismatch ${uri}`);
  requireValue(processPass(primaryProcess, 'PRIMARY', spec) && processPass(independentProcess, 'INDEPENDENT', spec), 'process mismatch');
  for (const [document, implementation] of [[primary, 'PRIMARY'], [independent, 'INDEPENDENT']]) {
    requireValue(document.schemaVersion === 'bfs.b62CameraQualityBoundedCandidateObservation.v0.1' && document.experimentId === spec.experimentId && document.implementation === implementation && document.status === 'OBSERVED', `${implementation} identity`);
    requireValue(`Blender ${document.blender.version}` === spec.runtime.blender.version && document.blender.buildHash === spec.runtime.blender.buildHash, `${implementation} Blender`);
    requireValue(document.master.expectedSha256 === spec.parentEvidence.masterScene.sha256 && atmosphereExact(document.materialAwareAtmosphere), `${implementation} source/material`);
    requireValue(document.operations.blenderStarts === 1 && document.operations.framesSet === 288 && document.operations.renderCalls === 0 && document.operations.modelCalls === 0 && document.operations.networkCalls === 0 && document.operations.dockerProcesses === 0, `${implementation} operations`);
  }
  const primaryComparable = structuredClone(primary), independentComparable = structuredClone(independent); delete primaryComparable.implementation; delete independentComparable.implementation;
  const mismatches = []; compare(primaryComparable, independentComparable, '$', mismatches);
  const derivationExact = canonicalJson(primary.derivationFramesEvaluated) === canonicalJson(spec.design.derivationFrames);
  const sealedExact = canonicalJson(primary.sealedHoldoutFramesNotEvaluated) === canonicalJson(spec.design.sealedHoldoutFrames);
  const allFrameRows = primary.candidates.flatMap(candidate => candidate.frames.map(frame => frame.frame));
  const noHoldout = allFrameRows.every(frame => spec.design.derivationFrames.includes(frame) && !spec.design.sealedHoldoutFrames.includes(frame));
  const roster = [];
  for (const angle of spec.design.candidateGrid.azimuthDegreesAroundWorldZ) for (const scale of spec.design.candidateGrid.radialScaleFromTarget) for (const lens of spec.design.candidateGrid.lensMillimeters) roster.push(`${angle}|${scale}|${lens}`);
  const observedRoster = primary.candidates.map(row => `${row.azimuthDegrees}|${row.radialScale}|${row.lensMillimeters}`);
  const rosterExact = canonicalJson(roster) === canonicalJson(observedRoster);
  const winner = recomputeWinner(primary.candidates);
  const baseline = primary.candidates.find(row => row.azimuthDegrees === 0 && row.radialScale === 1 && row.lensMillimeters === 100);
  const feasibleCount = primary.candidates.filter(row => row.feasible).length;
  const supported = mismatches.length === 0 && baseline?.feasible === false && feasibleCount > 0 && winner === primary.selectedCandidateId;
  const scientificVerdict = supported ? spec.decision.supportedVerdict : spec.decision.rejectedVerdict;
  const comparison = await writeHashed(resolve(root, 'comparison.json'), { schemaVersion: 'bfs.b62CameraQualityBoundedSearchComparison.v0.1', experimentId: spec.experimentId, status: mismatches.length === 0 ? 'PASS' : 'FAIL', toleranceAbsolute: TOLERANCE, comparedCandidateCount: primary.candidateCount, comparedCandidateFrameCount: allFrameRows.length, mismatches, baselineCandidateId: primary.baselineCandidateId, baselineFeasible: primary.baselineFeasible, feasibleCandidateCount: feasibleCount, selectedCandidateId: winner, scientificVerdict }, 'comparisonHash');
  const checks = [
    ['SPEC_ADMISSION_PARENT_BOUND', true], ['TOOL_FREEZE_HASHES_EXACT', true], ['TWO_FRESH_BLENDER_PROCESSES_PASS', true], ['BLENDER_5_2_IDENTITY_EXACT', true], ['ZERO_RENDER_MODEL_NETWORK_DOCKER', true],
    ['DERIVATION_FRAMES_EXACT', derivationExact], ['SEALED_HOLDOUT_ROSTER_EXACT', sealedExact], ['NO_HOLDOUT_FRAME_ACCESSED', noHoldout], ['CANDIDATE_GRID_96_EXACT', primary.candidateCount === 96 && rosterExact], ['CANDIDATE_FRAME_CELLS_288_EXACT', allFrameRows.length === 288 && primary.candidates.every(row => row.frames.length === 3)],
    ['ATMOSPHERE_VOLUME_ONLY_PASS_THROUGH', atmosphereExact(primary.materialAwareAtmosphere) && atmosphereExact(independent.materialAwareAtmosphere)], ['BASELINE_INFEASIBLE', baseline?.feasible === false && primary.baselineFeasible === false], ['SELECTION_RECOMPUTED_EXACT', winner === primary.selectedCandidateId], ['PRIMARY_INDEPENDENT_AGREE', mismatches.length === 0], ['OUTCOME_NEUTRAL_VERDICT_MAPPED', [spec.decision.supportedVerdict, spec.decision.rejectedVerdict].includes(scientificVerdict)],
  ].map(([id, pass]) => ({ id, pass: Boolean(pass) }));
  const status = checks.every(row => row.pass) ? 'PASS' : 'FAIL';
  const selected = primary.candidates.find(row => row.candidateId === winner) ?? null;
  const auditRecord = await writeHashed(resolve(root, 'audit.json'), { schemaVersion: 'bfs.b62CameraQualityBoundedSearchAudit.v0.1', experimentId: spec.experimentId, status, scientificVerdict: status === 'PASS' ? scientificVerdict : null, toolFreezeCommit: freeze, checks, derivationFrames: primary.derivationFramesEvaluated, sealedHoldoutFrames: primary.sealedHoldoutFramesNotEvaluated, baseline: baseline ? { candidateId: baseline.candidateId, feasible: baseline.feasible, frames: baseline.frames } : null, feasibleCandidateCount: feasibleCount, selectedCandidateId: winner, selectedCandidate: selected, inputs: { spec: { uri: SPEC_URI, sha256: await hashFile(localPath(SPEC_URI)) }, protocol: { uri: PROTOCOL_URI, sha256: await hashFile(localPath(PROTOCOL_URI)) }, primary: { uri: `${ROOT_URI}/primary.json`, sha256: await hashFile(resolve(root, 'primary.json')) }, independent: { uri: `${ROOT_URI}/independent.json`, sha256: await hashFile(resolve(root, 'independent.json')) }, comparison: { uri: `${ROOT_URI}/comparison.json`, sha256: await hashFile(resolve(root, 'comparison.json')), comparisonHash: comparison.comparisonHash } }, nonClaims: spec.nonClaims }, 'auditHash');
  requireValue(status === 'PASS', `audit failed ${checks.filter(row => !row.pass).map(row => row.id).join(',')}`);
  process.stdout.write(`BFS_B62_Q1_D3_AUDIT PASS ${checks.length}/${checks.length} ${scientificVerdict} ${winner ?? 'NONE'} ${auditRecord.auditHash}\n`);
  return auditRecord;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) audit(process.argv.slice(2)).catch(error => { process.stderr.write(`BFS_B62_Q1_D3_AUDIT_ERROR ${error.message}\n`); process.exitCode = 1; });
