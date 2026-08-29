#!/usr/bin/env node

import { createHash } from 'node:crypto';
import { open, readFile } from 'node:fs/promises';
import { dirname, relative, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const repositoryRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const SPEC_URI = 'specs/b62-camera-quality-geometric-diagnostic.v0.1.json';
const PROTOCOL_URI = 'research/2026-08-29-b62-camera-quality-geometric-diagnostic-protocol.md';
const CORRECTION_URI = 'specs/b62-camera-quality-c1-version-normalization.v0.1.json';
const TOOL_URIS = [
  'blender/probe_b62_q1_geometric_visibility.py',
  'blender/audit_b62_q1_geometric_visibility.py',
  'scripts/run-b62-q1-geometric-diagnostic.mjs',
  'scripts/audit-b62-q1-geometric-diagnostic.mjs',
];

function canonicalize(value) {
  if (Array.isArray(value)) return value.map(canonicalize);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).sort(([left], [right]) => left.localeCompare(right)).map(([key, child]) => [key, canonicalize(child)]));
  }
  return value;
}

const canonicalJson = value => JSON.stringify(canonicalize(value));
const sha256Bytes = value => createHash('sha256').update(value).digest('hex');

async function sha256File(path) {
  return sha256Bytes(await readFile(path));
}

function validSelfHash(value, field) {
  if (!value || typeof value !== 'object' || !/^[0-9a-f]{64}$/.test(value[field] ?? '')) return false;
  const copy = structuredClone(value);
  const expected = copy[field];
  delete copy[field];
  return sha256Bytes(canonicalJson(copy)) === expected;
}

async function durableHashed(path, value, hashField) {
  const body = structuredClone(value);
  body[hashField] = sha256Bytes(canonicalJson(body));
  const handle = await open(path, 'wx', 0o600);
  try {
    await handle.writeFile(`${JSON.stringify(body, null, 2)}\n`);
    await handle.sync();
  } finally {
    await handle.close();
  }
  return body;
}

function requireValue(condition, message) {
  if (!condition) throw new Error(message);
}

function parseArgs(argv) {
  const parsed = {};
  for (let index = 0; index < argv.length; index += 2) {
    requireValue(argv[index]?.startsWith('--') && argv[index + 1], 'invalid arguments');
    parsed[argv[index].slice(2)] = argv[index + 1];
  }
  requireValue(parsed.root && /^[0-9a-f]{40}$/.test(parsed['tool-freeze-commit'] ?? ''), 'usage: --root <repo-relative-root> --tool-freeze-commit <sha>');
  return { rootUri: parsed.root, freeze: parsed['tool-freeze-commit'] };
}

function containedPath(uri) {
  requireValue(typeof uri === 'string' && uri.length > 0 && !uri.startsWith('/') && !uri.split('/').includes('..'), `unsafe path ${uri}`);
  const path = resolve(repositoryRoot, uri);
  requireValue(relative(repositoryRoot, path) !== '..' && !relative(repositoryRoot, path).startsWith(`..${process.platform === 'win32' ? '\\' : '/'}`), `path escapes repository ${uri}`);
  return path;
}

async function readJson(uri) {
  return JSON.parse(await readFile(containedPath(uri), 'utf8'));
}

function compareValues(primary, independent, path = '$', mismatches = []) {
  if (typeof primary === 'number' && typeof independent === 'number') {
    if (!Number.isFinite(primary) || !Number.isFinite(independent) || Math.abs(primary - independent) > 1e-9) {
      mismatches.push({ path, primary, independent, kind: 'NUMBER_TOLERANCE' });
    }
    return mismatches;
  }
  if (Array.isArray(primary) || Array.isArray(independent)) {
    if (!Array.isArray(primary) || !Array.isArray(independent) || primary.length !== independent.length) {
      mismatches.push({ path, primaryType: Array.isArray(primary) ? `array:${primary.length}` : typeof primary, independentType: Array.isArray(independent) ? `array:${independent.length}` : typeof independent, kind: 'ARRAY_SHAPE' });
      return mismatches;
    }
    primary.forEach((value, index) => compareValues(value, independent[index], `${path}[${index}]`, mismatches));
    return mismatches;
  }
  if (primary && typeof primary === 'object' || independent && typeof independent === 'object') {
    if (!primary || !independent || typeof primary !== 'object' || typeof independent !== 'object') {
      mismatches.push({ path, primary, independent, kind: 'OBJECT_TYPE' });
      return mismatches;
    }
    const primaryKeys = Object.keys(primary).sort();
    const independentKeys = Object.keys(independent).sort();
    if (canonicalJson(primaryKeys) !== canonicalJson(independentKeys)) {
      mismatches.push({ path, primaryKeys, independentKeys, kind: 'OBJECT_KEYS' });
      return mismatches;
    }
    for (const key of primaryKeys) compareValues(primary[key], independent[key], `${path}.${key}`, mismatches);
    return mismatches;
  }
  if (primary !== independent) mismatches.push({ path, primary, independent, kind: 'VALUE' });
  return mismatches;
}

function normalizedShot(shot) {
  const copy = structuredClone(shot);
  delete copy.grid.rays;
  return copy;
}

function signature(shot, thresholds) {
  const conditions = {
    dominantFirstHitObjectShare: shot.grid.dominantFirstHitShare >= thresholds.dominantFirstHitObjectShareMinimum,
    nearFieldFirstHitShare: shot.grid.nearFieldHitShare >= thresholds.nearFieldFirstHitShareMinimum,
    semanticAnchorExactVisibility: shot.visibleAnchorCount <= thresholds.semanticAnchorExactVisibilityMaximum,
  };
  return { conditions, complete: Object.values(conditions).every(Boolean) };
}

function processExact(processReceipt, expectedId, spec) {
  return validSelfHash(processReceipt, 'processHash')
    && processReceipt.processId === expectedId
    && processReceipt.result?.outcome === 'PASS'
    && processReceipt.result?.breach === null
    && processReceipt.result?.child?.exitCode === 0
    && processReceipt.result?.metrics?.peakSampledRssBytes <= spec.processBudget.maximumPeakResidentSetSizeBytesPerBlender
    && processReceipt.result?.metrics?.logBytes <= spec.processBudget.maximumCombinedLogBytesPerChild;
}

export async function audit(argv) {
  const { rootUri, freeze } = parseArgs(argv);
  const rootPath = containedPath(rootUri);
  const spec = await readJson(SPEC_URI);
  const correction = await readJson(CORRECTION_URI);
  const admission = await readJson(`${rootUri}/admission.json`);
  const primary = await readJson(`${rootUri}/primary.json`);
  const independent = await readJson(`${rootUri}/independent.json`);
  const primaryProcess = await readJson(`${rootUri}/processes/PRIMARY.json`);
  const independentProcess = await readJson(`${rootUri}/processes/INDEPENDENT.json`);
  requireValue(spec.experimentId === 'B62-Q1-D1' && spec.statusBeforeToolCreation === 'PREREGISTERED', 'spec identity mismatch');
  requireValue(correction.correctionId === 'B62-Q1-D1-C1' && correction.statusBeforeToolChange === 'PREREGISTERED' && correction.authorizedChanges.retryRoot === rootUri, 'C1 correction mismatch');
  requireValue(validSelfHash(admission, 'admissionHash') && admission.status === 'ACCEPTED', 'admission invalid');
  requireValue(admission.toolFreezeCommit === freeze && admission.spec.sha256 === await sha256File(containedPath(SPEC_URI)), 'admission freeze/spec mismatch');
  requireValue(admission.correction.uri === CORRECTION_URI && admission.correction.sha256 === await sha256File(containedPath(CORRECTION_URI)), 'admission correction mismatch');
  for (const uri of TOOL_URIS) requireValue(admission.toolHashes[uri] === await sha256File(containedPath(uri)), `tool hash mismatch ${uri}`);
  requireValue(admission.protocol.sha256 === await sha256File(containedPath(PROTOCOL_URI)), 'protocol hash mismatch');
  for (const row of [spec.parentEvidence.phase0Receipt, spec.parentEvidence.masterScene, ...spec.parentEvidence.calibrationPngs]) {
    requireValue(await sha256File(containedPath(row.uri)) === row.sha256, `parent evidence mismatch ${row.uri}`);
  }
  const parentReceipt = await readJson(spec.parentEvidence.phase0Receipt.uri);
  requireValue(validSelfHash(parentReceipt, 'receiptHash') && parentReceipt.receiptHash === spec.parentEvidence.phase0Receipt.receiptHash, 'parent receipt self hash mismatch');
  requireValue(processExact(primaryProcess, 'PRIMARY', spec) && processExact(independentProcess, 'INDEPENDENT', spec), 'Blender process receipt invalid');
  for (const [document, implementation] of [[primary, 'PRIMARY'], [independent, 'INDEPENDENT']]) {
    requireValue(document.schemaVersion === 'bfs.b62CameraQualityGeometricObservation.v0.1' && document.experimentId === spec.experimentId && document.implementation === implementation && document.status === 'OBSERVED', `${implementation} observation identity mismatch`);
    requireValue(document.master.expectedSha256 === spec.parentEvidence.masterScene.sha256, `${implementation} master binding mismatch`);
    requireValue(`Blender ${document.blender.version}` === spec.runtime.blender.version && document.blender.buildHash === spec.runtime.blender.buildHash, `${implementation} Blender identity mismatch`);
    requireValue(document.operations.blenderStarts === 1 && document.operations.renderCalls === 0 && document.operations.modelCalls === 0 && document.operations.networkCalls === 0 && document.operations.dockerProcesses === 0, `${implementation} operation mismatch`);
    requireValue(document.shots.length === spec.design.shots.length, `${implementation} shot count mismatch`);
  }
  const mismatches = [];
  for (let index = 0; index < primary.shots.length; index += 1) compareValues(normalizedShot(primary.shots[index]), normalizedShot(independent.shots[index]), `$.shots[${index}]`, mismatches);
  const thresholds = spec.design.diagnosticSignature.closeRequired;
  const signatures = primary.shots.map(shot => ({ shot: shot.shot, frame: shot.frame, ...signature(shot, thresholds) }));
  const close = signatures.find(row => row.shot === 'CLOSE_REFLECTION');
  const controls = signatures.filter(row => row.shot !== 'CLOSE_REFLECTION');
  const supported = mismatches.length === 0 && close?.complete === true && controls.every(row => !row.complete);
  const scientificVerdict = supported ? spec.decision.supportedVerdict : spec.decision.rejectedVerdict;
  const comparison = await durableHashed(resolve(rootPath, 'comparison.json'), {
    schemaVersion: 'bfs.b62CameraQualityGeometricComparison.v0.1',
    experimentId: spec.experimentId,
    status: mismatches.length === 0 ? 'PASS' : 'FAIL',
    toleranceAbsolute: 1e-9,
    comparedShots: primary.shots.map(row => ({ shot: row.shot, frame: row.frame })),
    mismatches,
    signatures,
    scientificVerdict,
  }, 'comparisonHash');
  const checks = [
    ['SPEC_AND_ADMISSION_BOUND', true],
    ['PARENT_RECEIPT_AND_MASTER_BOUND', true],
    ['CALIBRATION_PNGS_BOUND', true],
    ['TOOL_FREEZE_HASHES_EXACT', true],
    ['TWO_FRESH_BLENDER_PROCESSES_PASS', true],
    ['BLENDER_IDENTITY_EXACT', true],
    ['ZERO_RENDER_MODEL_NETWORK_DOCKER', true],
    ['THREE_SHOT_ROSTER_EXACT', primary.shots.map(row => `${row.shot}:${row.frame}`).join(',') === 'WIDE_APPROACH:48,MEDIUM_CONTACT:144,CLOSE_REFLECTION:240'],
    ['GRID_64_BY_36_EXACT', primary.shots.every(row => row.grid.width === 64 && row.grid.height === 36 && row.grid.totalRays === 2304)],
    ['SEMANTIC_ANCHOR_ROSTER_EXACT', primary.shots.every(row => row.anchors.map(anchor => anchor.anchor).join(',') === spec.design.semanticAnchors.join(','))],
    ['PRIMARY_INDEPENDENT_AGREE', mismatches.length === 0],
    ['OUTCOME_NEUTRAL_VERDICT_MAPPED', scientificVerdict === spec.decision.supportedVerdict || scientificVerdict === spec.decision.rejectedVerdict],
  ].map(([id, pass]) => ({ id, pass }));
  const status = checks.every(row => row.pass) ? 'PASS' : 'FAIL';
  const auditRecord = await durableHashed(resolve(rootPath, 'audit.json'), {
    schemaVersion: 'bfs.b62CameraQualityGeometricAudit.v0.1',
    experimentId: spec.experimentId,
    status,
    scientificVerdict: status === 'PASS' ? scientificVerdict : null,
    toolFreezeCommit: freeze,
    inputs: {
      spec: { uri: SPEC_URI, sha256: await sha256File(containedPath(SPEC_URI)) },
      protocol: { uri: PROTOCOL_URI, sha256: await sha256File(containedPath(PROTOCOL_URI)) },
      correction: { uri: CORRECTION_URI, sha256: await sha256File(containedPath(CORRECTION_URI)) },
      primary: { uri: `${rootUri}/primary.json`, sha256: await sha256File(resolve(rootPath, 'primary.json')) },
      independent: { uri: `${rootUri}/independent.json`, sha256: await sha256File(resolve(rootPath, 'independent.json')) },
      comparison: { uri: `${rootUri}/comparison.json`, sha256: await sha256File(resolve(rootPath, 'comparison.json')), comparisonHash: comparison.comparisonHash },
    },
    checks,
    signatures,
    nonClaims: spec.nonClaims,
  }, 'auditHash');
  requireValue(status === 'PASS', `audit checks failed: ${checks.filter(row => !row.pass).map(row => row.id).join(',')}`);
  process.stdout.write(`BFS_B62_Q1_AUDIT PASS ${checks.length}/${checks.length} ${auditRecord.scientificVerdict} ${auditRecord.auditHash}\n`);
  return auditRecord;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  audit(process.argv.slice(2)).catch(error => {
    process.stderr.write(`BFS_B62_Q1_AUDIT_ERROR ${error.message}\n`);
    process.exitCode = 1;
  });
}
