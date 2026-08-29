#!/usr/bin/env node

import { createHash } from 'node:crypto';
import { open, readFile } from 'node:fs/promises';
import { dirname, relative, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const repositoryRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const SPEC_URI = 'specs/b62-camera-quality-material-aware-framing-diagnostic.v0.1.json';
const PROTOCOL_URI = 'research/2026-08-29-b62-camera-quality-material-aware-framing-diagnostic-protocol.md';
const EXPECTED_ROOT = 'experiments/b62-camera-quality-material-aware-framing-v0-1';
const TOOL_URIS = [
  'blender/probe_b62_q1_material_aware_framing.py',
  'blender/audit_b62_q1_material_aware_framing.py',
  'scripts/run-b62-q1-material-aware-framing.mjs',
  'scripts/audit-b62-q1-material-aware-framing.mjs',
];
const TOLERANCE = 1e-9;

function canonicalize(value) {
  if (Array.isArray(value)) return value.map(canonicalize);
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).sort(([a], [b]) => a.localeCompare(b)).map(([key, child]) => [key, canonicalize(child)]));
  return value;
}
const canonicalJson = value => JSON.stringify(canonicalize(value));
const hashBytes = value => createHash('sha256').update(value).digest('hex');
const hashFile = async path => hashBytes(await readFile(path));

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

async function json(uri) {
  return JSON.parse(await readFile(localPath(uri), 'utf8'));
}

function validSelfHash(value, field) {
  if (!value || !/^[0-9a-f]{64}$/.test(value[field] ?? '')) return false;
  const copy = structuredClone(value);
  const expected = copy[field];
  delete copy[field];
  return hashBytes(canonicalJson(copy)) === expected;
}

async function writeHashed(path, value, field) {
  const body = structuredClone(value);
  body[field] = hashBytes(canonicalJson(body));
  const handle = await open(path, 'wx', 0o600);
  try { await handle.writeFile(`${JSON.stringify(body, null, 2)}\n`); await handle.sync(); } finally { await handle.close(); }
  return body;
}

function parseArgs(argv) {
  requireValue(argv.length === 4 && argv[0] === '--root' && argv[2] === '--tool-freeze-commit', 'usage: --root <uri> --tool-freeze-commit <sha>');
  requireValue(argv[1] === EXPECTED_ROOT && /^[0-9a-f]{40}$/.test(argv[3]), 'argument identity mismatch');
  return { rootUri: argv[1], freeze: argv[3] };
}

function compareValues(left, right, path, mismatches) {
  if (typeof left === 'number' && typeof right === 'number') {
    if (!Number.isFinite(left) || !Number.isFinite(right) || Math.abs(left - right) > TOLERANCE) mismatches.push({ path, primary: left, independent: right });
    return;
  }
  if (Array.isArray(left) || Array.isArray(right)) {
    if (!Array.isArray(left) || !Array.isArray(right) || left.length !== right.length) { mismatches.push({ path, primary: left, independent: right }); return; }
    for (let index = 0; index < left.length; index += 1) compareValues(left[index], right[index], `${path}[${index}]`, mismatches);
    return;
  }
  if (left && right && typeof left === 'object' && typeof right === 'object') {
    const keysLeft = Object.keys(left).sort();
    const keysRight = Object.keys(right).sort();
    if (keysLeft.join('\0') !== keysRight.join('\0')) { mismatches.push({ path, primaryKeys: keysLeft, independentKeys: keysRight }); return; }
    for (const key of keysLeft) compareValues(left[key], right[key], `${path}.${key}`, mismatches);
    return;
  }
  if (left !== right) mismatches.push({ path, primary: left, independent: right });
}

function processPass(receipt, id, spec) {
  return validSelfHash(receipt, 'processHash')
    && receipt.experimentId === spec.experimentId
    && receipt.processId === id
    && receipt.result?.outcome === 'PASS'
    && receipt.result?.breach === null
    && receipt.result?.child?.exitCode === 0
    && receipt.result?.metrics?.peakSampledRssBytes <= spec.processBudget.maximumPeakResidentSetSizeBytesPerBlender
    && receipt.result?.metrics?.logBytes <= spec.processBudget.maximumCombinedLogBytesPerChild;
}

function signature(shot, thresholds) {
  const conditions = {
    dominantVisualBlockerObject: shot.grid.dominantVisualBlockerObject === thresholds.dominantVisualBlockerObject,
    dominantVisualBlockerShare: shot.grid.dominantVisualBlockerShare >= thresholds.dominantVisualBlockerShareMinimum,
    characterVisualBlockerShare: shot.grid.characterVisualBlockerShare >= thresholds.characterVisualBlockerShareMinimum,
    characterOnScreenVertexFraction: shot.characterProjection.onScreenVertexFraction <= thresholds.characterOnScreenVertexFractionMaximum,
    characterClampedUnionAreaFraction: shot.characterProjection.clampedUnionAreaFraction >= thresholds.characterClampedUnionAreaFractionMinimum,
    semanticAnchorExactVisibility: shot.visibleAnchorCount <= thresholds.semanticAnchorExactVisibilityMaximum,
  };
  return { conditions, complete: Object.values(conditions).every(Boolean) };
}

function atmosphereExact(row) {
  return row?.object === 'B62_ATMOSPHERE'
    && row.classification === 'VOLUME_ONLY_PASS_THROUGH'
    && Array.isArray(row.materials)
    && row.materials.length === 1
    && row.materials[0].material === 'MAT_B62_VOLUME'
    && row.materials[0].usesNodes === true
    && row.materials[0].outputCount >= 1
    && row.materials[0].surfaceLinked === false
    && row.materials[0].volumeLinked === true;
}

export async function audit(argv) {
  const { rootUri, freeze } = parseArgs(argv);
  const root = localPath(rootUri);
  const spec = await json(SPEC_URI);
  const admission = await json(`${rootUri}/admission.json`);
  const primary = await json(`${rootUri}/primary.json`);
  const independent = await json(`${rootUri}/independent.json`);
  const primaryProcess = await json(`${rootUri}/processes/PRIMARY.json`);
  const independentProcess = await json(`${rootUri}/processes/INDEPENDENT.json`);
  requireValue(spec.experimentId === 'B62-Q1-D2' && spec.statusBeforeToolCreation === 'PREREGISTERED', 'spec identity mismatch');
  requireValue(validSelfHash(admission, 'admissionHash') && admission.status === 'ADMITTED' && admission.toolFreezeCommit === freeze, 'admission mismatch');
  requireValue(admission.bindings.spec.sha256 === await hashFile(localPath(SPEC_URI)) && admission.bindings.protocol.sha256 === await hashFile(localPath(PROTOCOL_URI)), 'spec/protocol binding mismatch');
  requireValue(canonicalJson(admission.bindings.derivationTree) === canonicalJson(spec.derivationDisclosure.sourceExperiment.tree), 'derivation binding mismatch');
  requireValue(admission.bindings.derivationReceiptSha256 === spec.derivationDisclosure.sourceExperiment.receipt.sha256, 'derivation receipt binding mismatch');
  for (const uri of TOOL_URIS) requireValue(admission.bindings.tools[uri] === await hashFile(localPath(uri)), `tool hash mismatch ${uri}`);
  requireValue(processPass(primaryProcess, 'PRIMARY', spec) && processPass(independentProcess, 'INDEPENDENT', spec), 'Blender process receipt mismatch');

  for (const [document, implementation] of [[primary, 'PRIMARY'], [independent, 'INDEPENDENT']]) {
    requireValue(document.schemaVersion === 'bfs.b62CameraQualityMaterialAwareFramingObservation.v0.1' && document.experimentId === spec.experimentId && document.implementation === implementation && document.status === 'OBSERVED', `${implementation} identity mismatch`);
    requireValue(document.master.expectedSha256 === spec.parentEvidence.masterScene.sha256, `${implementation} master mismatch`);
    requireValue(`Blender ${document.blender.version}` === spec.runtime.blender.version && document.blender.buildHash === spec.runtime.blender.buildHash, `${implementation} Blender mismatch`);
    requireValue(document.operations.blenderStarts === 1 && document.operations.renderCalls === 0 && document.operations.modelCalls === 0 && document.operations.networkCalls === 0 && document.operations.dockerProcesses === 0, `${implementation} operations mismatch`);
    requireValue(atmosphereExact(document.materialClassifications.B62_ATMOSPHERE), `${implementation} atmosphere mismatch`);
  }

  const primaryComparable = structuredClone(primary);
  const independentComparable = structuredClone(independent);
  delete primaryComparable.implementation;
  delete independentComparable.implementation;
  const mismatches = [];
  compareValues(primaryComparable, independentComparable, '$', mismatches);
  const thresholds = spec.design.diagnosticSignature.closeRequired;
  const signatures = primary.shots.map(shot => ({ shot: shot.shot, frame: shot.frame, ...signature(shot, thresholds) }));
  const close = signatures.find(row => row.shot === 'CLOSE_REFLECTION');
  const controls = signatures.filter(row => row.shot !== 'CLOSE_REFLECTION');
  const supported = mismatches.length === 0 && close?.complete === true && controls.every(row => !row.complete);
  const scientificVerdict = supported ? spec.decision.supportedVerdict : spec.decision.rejectedVerdict;
  const comparison = await writeHashed(resolve(root, 'comparison.json'), {
    schemaVersion: 'bfs.b62CameraQualityMaterialAwareFramingComparison.v0.1', experimentId: spec.experimentId,
    status: mismatches.length === 0 ? 'PASS' : 'FAIL', toleranceAbsolute: TOLERANCE,
    comparedShots: primary.shots.map(row => ({ shot: row.shot, frame: row.frame })), mismatches, signatures, scientificVerdict,
  }, 'comparisonHash');

  const roster = primary.shots.map(row => `${row.shot}:${row.frame}`).join(',');
  const checks = [
    ['SPEC_ADMISSION_AND_DERIVATION_BOUND', true],
    ['MASTER_AND_CALIBRATION_IDENTITIES_BOUND', admission.bindings.master.sha256 === spec.parentEvidence.masterScene.sha256],
    ['TOOL_FREEZE_HASHES_EXACT', true],
    ['TWO_FRESH_BLENDER_PROCESSES_PASS', true],
    ['BLENDER_5_2_IDENTITY_EXACT', true],
    ['ZERO_RENDER_MODEL_NETWORK_DOCKER', true],
    ['SHOT_ROSTER_EXACT', roster === 'WIDE_APPROACH:48,MEDIUM_CONTACT:144,CLOSE_REFLECTION:240'],
    ['GRID_64_BY_36_EXACT', primary.shots.every(row => row.grid.width === 64 && row.grid.height === 36 && row.grid.totalRays === 2304 && row.grid.rays.length === 2304)],
    ['NO_TRAVERSAL_EXHAUSTION', primary.shots.every(row => row.grid.rays.every(ray => ray.exhausted === false) && row.centerRay.exhausted === false && row.anchors.every(anchor => anchor.firstVisualBlocker.exhausted === false))],
    ['ATMOSPHERE_VOLUME_ONLY_PASS_THROUGH_PROVEN', atmosphereExact(primary.materialClassifications.B62_ATMOSPHERE) && atmosphereExact(independent.materialClassifications.B62_ATMOSPHERE)],
    ['SEMANTIC_ANCHOR_ROSTER_EXACT', primary.shots.every(row => row.anchors.map(anchor => anchor.anchor).join(',') === spec.design.semanticAnchors.join(','))],
    ['PRIMARY_INDEPENDENT_AGREE', mismatches.length === 0],
    ['OUTCOME_NEUTRAL_VERDICT_MAPPED', [spec.decision.supportedVerdict, spec.decision.rejectedVerdict].includes(scientificVerdict)],
  ].map(([id, pass]) => ({ id, pass: Boolean(pass) }));
  const status = checks.every(row => row.pass) ? 'PASS' : 'FAIL';
  const auditRecord = await writeHashed(resolve(root, 'audit.json'), {
    schemaVersion: 'bfs.b62CameraQualityMaterialAwareFramingAudit.v0.1', experimentId: spec.experimentId,
    status, scientificVerdict: status === 'PASS' ? scientificVerdict : null, toolFreezeCommit: freeze,
    inputs: {
      spec: { uri: SPEC_URI, sha256: await hashFile(localPath(SPEC_URI)) },
      protocol: { uri: PROTOCOL_URI, sha256: await hashFile(localPath(PROTOCOL_URI)) },
      primary: { uri: `${rootUri}/primary.json`, sha256: await hashFile(resolve(root, 'primary.json')) },
      independent: { uri: `${rootUri}/independent.json`, sha256: await hashFile(resolve(root, 'independent.json')) },
      comparison: { uri: `${rootUri}/comparison.json`, sha256: await hashFile(resolve(root, 'comparison.json')), comparisonHash: comparison.comparisonHash },
    },
    checks, materialAwareAtmosphere: primary.materialClassifications.B62_ATMOSPHERE, signatures, nonClaims: spec.nonClaims,
  }, 'auditHash');
  requireValue(status === 'PASS', `audit failed: ${checks.filter(row => !row.pass).map(row => row.id).join(',')}`);
  process.stdout.write(`BFS_B62_Q1_D2_AUDIT PASS ${checks.length}/${checks.length} ${scientificVerdict} ${auditRecord.auditHash}\n`);
  return auditRecord;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  audit(process.argv.slice(2)).catch(error => { process.stderr.write(`BFS_B62_Q1_D2_AUDIT_ERROR ${error.message}\n`); process.exitCode = 1; });
}
