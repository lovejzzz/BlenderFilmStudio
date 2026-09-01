import { readFile, lstat } from 'node:fs/promises';
import { resolve, relative, isAbsolute } from 'node:path';
import Ajv2020 from 'ajv/dist/2020.js';
import { canonicalJson, canonicalize, repositoryRoot, sha256 } from './scene-spec.mjs';

const PACKET_SCHEMA_URI = 'specs/visual-review-packet.v0.1.schema.json';
const ASSESSMENT_SCHEMA_URI = 'specs/visual-assessment.v0.2.schema.json';
const PLAN_SCHEMA_URI = 'specs/visual-improvement-plan.v0.2.schema.json';
const CATALOG_URI = 'specs/visual-treatment-catalog.v0.2.json';
const RUBRIC_URI = 'specs/visual-film-language-rubric.v0.2.json';
const severityOrder = new Map([['BLOCKER', 0], ['HIGH', 1], ['MEDIUM', 2], ['LOW', 3]]);
const categoryOrder = new Map([['COMPOSITION', 0], ['MODELING', 1], ['ANIMATION', 2], ['CONTINUITY', 3], ['LIGHTING', 4], ['MATERIAL', 5]]);
const preservationRules = {
  LIGHTING: 'PRESERVE_ACCEPTED_LIGHTING',
  CAMERA_LANGUAGE: 'PRESERVE_ACCEPTED_CAMERA_LANGUAGE',
  COLOR: 'PRESERVE_ACCEPTED_COLOR',
  ATMOSPHERE: 'PRESERVE_ACCEPTED_ATMOSPHERE',
};
const executablePattern = /(?:\bbpy\.|\bimport\s+|\bsubprocess\b|\bos\.|\bcurl\b|\bwget\b|\brm\s+-|https?:\/\/|(?:^|[\s])\/(?:Users|tmp|etc)\b|\.\.\/|`|\$\(|&&|\|\|)/i;

export class VisualReviewV2Error extends Error {
  constructor(code, message = code) {
    super(`${code}: ${message}`);
    this.name = 'VisualReviewV2Error';
    this.code = code;
  }
}

function requireCondition(condition, code, message) {
  if (!condition) throw new VisualReviewV2Error(code, message);
}

function duplicates(values) {
  const seen = new Set();
  return values.filter(value => seen.has(value) || !seen.add(value));
}

export function repositoryUriV2(path) {
  const absolute = resolve(path);
  const uri = relative(repositoryRoot, absolute);
  requireCondition(!isAbsolute(uri) && uri !== '..' && !uri.startsWith(`..${process.platform === 'win32' ? '\\' : '/'}`), 'PATH_OUTSIDE_REPOSITORY', absolute);
  return uri.split('\\').join('/');
}

export function resolveRepositoryUriV2(uri) {
  requireCondition(typeof uri === 'string' && !isAbsolute(uri) && !uri.split('/').includes('..'), 'PATH_OUTSIDE_REPOSITORY', String(uri));
  const absolute = resolve(repositoryRoot, uri);
  requireCondition(repositoryUriV2(absolute) === uri, 'PATH_NOT_CANONICAL', uri);
  return absolute;
}

async function loadJson(uri) {
  const path = resolveRepositoryUriV2(uri);
  const stat = await lstat(path);
  requireCondition(stat.isFile() && !stat.isSymbolicLink(), 'INPUT_NOT_REGULAR_FILE', uri);
  const bytes = await readFile(path);
  return { uri, path, bytes, sha256: sha256(bytes), value: JSON.parse(bytes) };
}

function validator(schema) {
  return new Ajv2020({ allErrors: true, strict: true, allowUnionTypes: true }).compile(schema);
}

function schemaCheck(check, value, code) {
  requireCondition(check(value), code, JSON.stringify(check.errors));
}

function scan(value, path = '$') {
  if (typeof value === 'string') {
    requireCondition(!executablePattern.test(value), 'EXECUTABLE_AUTHORITY', path);
    return;
  }
  if (Array.isArray(value)) return value.forEach((child, index) => scan(child, `${path}[${index}]`));
  if (value && typeof value === 'object') Object.entries(value).forEach(([key, child]) => scan(child, `${path}.${key}`));
}

function withoutHash(plan) {
  const value = structuredClone(plan);
  delete value.planHash;
  return value;
}

export function computePlanHashV2(plan) {
  return sha256(canonicalJson(withoutHash(plan)));
}

function invariants(category) {
  const rows = ['PRESERVE_SCENE_IDENTITY', 'NO_NEW_EXTERNAL_ASSET', 'NO_EXECUTABLE_AUTHORITY', 'NO_NAMED_PROJECT_SPECIAL_CASE'];
  if (category === 'MODELING' || category === 'MATERIAL') rows.push('PRESERVE_ANIMATION_ANCHORS');
  if (category === 'COMPOSITION') rows.push('PRESERVE_ACCEPTED_LIGHTING', 'PRESERVE_CAMERA_LANGUAGE');
  return rows;
}

export async function compileVisualImprovementPlanV2Files(packetUri, assessmentUri) {
  const [packetSchema, assessmentSchema, planSchema, catalogInput, rubricInput, packetInput, assessmentInput] = await Promise.all([
    loadJson(PACKET_SCHEMA_URI), loadJson(ASSESSMENT_SCHEMA_URI), loadJson(PLAN_SCHEMA_URI), loadJson(CATALOG_URI), loadJson(RUBRIC_URI), loadJson(packetUri), loadJson(assessmentUri),
  ]);
  const checks = { packet: validator(packetSchema.value), assessment: validator(assessmentSchema.value), plan: validator(planSchema.value) };
  const packet = packetInput.value;
  const assessment = assessmentInput.value;
  schemaCheck(checks.packet, packet, 'PACKET_SCHEMA');
  schemaCheck(checks.assessment, assessment, 'ASSESSMENT_SCHEMA');
  scan(assessment);
  requireCondition(assessment.packetUri === packetUri && assessment.packetSha256 === packetInput.sha256, 'PACKET_BINDING');
  requireCondition(rubricInput.value.rubricVersion === '0.2.0' && catalogInput.value.catalogVersion === '0.2.0' && catalogInput.value.rubricUri === RUBRIC_URI, 'RUBRIC_CATALOG_BINDING');
  requireCondition(assessment.lesson.antiPatterns.every(value => rubricInput.value.antiPatterns.includes(value)), 'UNKNOWN_ANTI_PATTERN');

  const frames = new Map(packet.frames.map(frame => [frame.frameId, frame]));
  const entities = new Set(packet.entities.map(entity => entity.entityId));
  const strengths = new Map(packet.strengths.map(strength => [strength.strengthId, strength]));
  const treatments = new Map(catalogInput.value.treatments.map(item => [item.id, item]));
  requireCondition(duplicates([...frames.keys()]).length === 0 && duplicates([...entities]).length === 0 && duplicates([...strengths.keys()]).length === 0, 'DUPLICATE_PACKET_ID');
  requireCondition(duplicates(assessment.issues.map(issue => issue.issueId)).length === 0, 'DUPLICATE_ISSUE_ID');

  for (const frame of packet.frames) {
    requireCondition(entities.has(frame.cameraId), 'UNKNOWN_CAMERA', frame.cameraId);
    for (const entity of frame.visibleEntityIds) requireCondition(entities.has(entity), 'UNKNOWN_VISIBLE_ENTITY', entity);
    const records = [frame.beauty, ...frame.auxiliaryPasses];
    for (const record of records) requireCondition((await loadJsonOrBytes(record.uri)).sha256 === record.sha256, 'PACKET_FILE_HASH', record.uri);
  }
  requireCondition((await loadJsonOrBytes(packet.scene.buildReceipt.uri)).sha256 === packet.scene.buildReceipt.sha256, 'BUILD_RECEIPT_HASH');

  for (const issue of assessment.issues) {
    const treatment = treatments.get(issue.treatment);
    requireCondition(treatment && treatment.categories.includes(issue.category), 'TREATMENT_MISMATCH', issue.treatment);
    const evidenceFrames = issue.evidence.map(item => frames.get(item.frameId));
    requireCondition(evidenceFrames.every(Boolean), 'UNKNOWN_EVIDENCE_FRAME', issue.issueId);
    for (const evidence of issue.evidence) requireCondition(evidence.region.x + evidence.region.width <= 1 && evidence.region.y + evidence.region.height <= 1, 'REGION_OUT_OF_BOUNDS', issue.issueId);
    for (const entity of issue.entityRefs) requireCondition(entities.has(entity) && evidenceFrames.some(frame => frame.visibleEntityIds.includes(entity)), 'ENTITY_NOT_VISIBLE_IN_EVIDENCE', `${issue.issueId}:${entity}`);
    const p = treatment.parameters;
    requireCondition(p.targetOccupancyMin === null || p.targetOccupancyMax === null || p.targetOccupancyMin < p.targetOccupancyMax, 'OCCUPANCY_RANGE');
    requireCondition(p.requiredFacialZones.length === 0 || p.requiredFacialZones.join(',') === 'EYE_LINE,BROW,CHEEK,JAW', 'FACIAL_ZONE_ORDER');
  }

  requireCondition(assessment.strengthConfirmations.length === packet.strengths.length, 'STRENGTH_CONFIRMATION_COUNT');
  for (const confirmation of assessment.strengthConfirmations) {
    const strength = strengths.get(confirmation.strengthId);
    requireCondition(strength && confirmation.evidenceFrameIds.every(frame => strength.evidenceFrameIds.includes(frame)), 'STRENGTH_BINDING', confirmation.strengthId);
  }

  const frameOrder = new Map(packet.frames.map((frame, index) => [frame.frameId, index]));
  const prioritized = [...assessment.issues].sort((a, b) => severityOrder.get(a.severity) - severityOrder.get(b.severity) || categoryOrder.get(a.category) - categoryOrder.get(b.category) || a.issueId.localeCompare(b.issueId));
  const actionable = prioritized.filter(issue => issue.confidence >= packet.reviewPolicy.confidenceFloor);
  const priorities = prioritized.map((issue, index) => ({ rank: index + 1, issueId: issue.issueId, severity: issue.severity, category: issue.category, confidence: issue.confidence }));
  const operations = actionable.map(issue => {
    const treatment = treatments.get(issue.treatment);
    const evidenceFrameIds = [...new Set(issue.evidence.map(item => item.frameId))].sort((a, b) => frameOrder.get(a) - frameOrder.get(b));
    return {
      operationId: `OP_${String(priorities.find(row => row.issueId === issue.issueId).rank).padStart(3, '0')}_${issue.issueId}`,
      issueId: issue.issueId,
      operationType: treatment.operationType,
      targetEntityIds: [...issue.entityRefs].sort(),
      shotIds: [...new Set(evidenceFrameIds.map(frame => frames.get(frame).shotId))].sort(),
      preset: treatment.preset,
      parameters: canonicalize(treatment.parameters),
      invariants: invariants(issue.category),
      evidenceFrameIds,
      failureMechanisms: [...issue.failureMechanisms].sort(),
    };
  });
  const preservations = assessment.strengthConfirmations.map(confirmation => {
    const strength = strengths.get(confirmation.strengthId);
    return { strengthId: strength.strengthId, category: strength.category, evidenceFrameIds: [...confirmation.evidenceFrameIds].sort((a, b) => frameOrder.get(a) - frameOrder.get(b)), rule: preservationRules[strength.category] };
  }).sort((a, b) => a.strengthId.localeCompare(b.strengthId));
  const rerenderSet = [...new Set(operations.flatMap(operation => operation.evidenceFrameIds))].sort((a, b) => frameOrder.get(a) - frameOrder.get(b));
  const plan = {
    documentType: 'BFS_VISUAL_IMPROVEMENT_PLAN', planVersion: '0.2.0', projectId: packet.project.projectId, iterationId: packet.project.iterationId,
    source: { packetUri, packetSha256: packetInput.sha256, assessmentUri, assessmentSha256: assessmentInput.sha256, observedSceneSha256: packet.scene.sha256, executionBaselineSha256: assessment.executionBaseline.sceneSha256 },
    rubric: { uri: RUBRIC_URI, sha256: rubricInput.sha256, version: rubricInput.value.rubricVersion },
    decision: operations.length ? 'COMPILED' : 'NEEDS_MORE_EVIDENCE', priorities, operations, preservations, rerenderSet,
    lesson: canonicalize(assessment.lesson),
    authority: { semanticCatalogOnly: true, allowsPython: false, allowsShell: false, allowsNetwork: false, allowsArbitraryFilesystem: false, requiresTypedExecutor: true },
    planHash: '',
  };
  plan.planHash = computePlanHashV2(plan);
  schemaCheck(checks.plan, plan, 'PLAN_SCHEMA');
  requireCondition(computePlanHashV2(plan) === plan.planHash, 'PLAN_SELF_HASH');
  return { plan: canonicalize(plan), identities: { packetSchema: packetSchema.sha256, assessmentSchema: assessmentSchema.sha256, planSchema: planSchema.sha256, catalog: catalogInput.sha256, rubric: rubricInput.sha256 } };
}

async function loadJsonOrBytes(uri) {
  const path = resolveRepositoryUriV2(uri);
  const stat = await lstat(path);
  requireCondition(stat.isFile() && !stat.isSymbolicLink(), 'INPUT_NOT_REGULAR_FILE', uri);
  const bytes = await readFile(path);
  return { sha256: sha256(bytes) };
}

export function canonicalPlanBytesV2(plan) {
  return Buffer.from(`${JSON.stringify(canonicalize(plan), null, 2)}\n`);
}
