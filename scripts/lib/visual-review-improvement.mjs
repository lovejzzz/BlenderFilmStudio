import { readFile, lstat } from 'node:fs/promises';
import { resolve, relative, isAbsolute } from 'node:path';
import Ajv2020 from 'ajv/dist/2020.js';
import { canonicalJson, canonicalize, repositoryRoot, sha256 } from './scene-spec.mjs';

const PACKET_SCHEMA_URI = 'specs/visual-review-packet.v0.1.schema.json';
const ASSESSMENT_SCHEMA_URI = 'specs/visual-assessment.v0.1.schema.json';
const PLAN_SCHEMA_URI = 'specs/visual-improvement-plan.v0.1.schema.json';
const CATALOG_URI = 'specs/visual-treatment-catalog.v0.1.json';

const severityOrder = new Map([['BLOCKER', 0], ['HIGH', 1], ['MEDIUM', 2], ['LOW', 3]]);
const categoryOrder = new Map([['COMPOSITION', 0], ['MODELING', 1], ['ANIMATION', 2], ['CONTINUITY', 3], ['LIGHTING', 4], ['MATERIAL', 5]]);
const preservationRules = {
  LIGHTING: 'PRESERVE_ACCEPTED_LIGHTING',
  CAMERA_LANGUAGE: 'PRESERVE_ACCEPTED_CAMERA_LANGUAGE',
  COLOR: 'PRESERVE_ACCEPTED_COLOR',
  ATMOSPHERE: 'PRESERVE_ACCEPTED_ATMOSPHERE',
};
const executablePattern = /(?:\bbpy\.|\bimport\s+|\bsubprocess\b|\bos\.|\bcurl\b|\bwget\b|\brm\s+-|https?:\/\/|(?:^|[\s])\/(?:Users|tmp|etc)\b|\.\.\/|`|\$\(|&&|\|\|)/i;

export class VisualReviewError extends Error {
  constructor(code, message = code) {
    super(`${code}: ${message}`);
    this.name = 'VisualReviewError';
    this.code = code;
  }
}

function requireCondition(condition, code, message) {
  if (!condition) throw new VisualReviewError(code, message);
}

function duplicates(values) {
  const seen = new Set();
  return values.filter(value => seen.has(value) || !seen.add(value));
}

export function repositoryUri(path) {
  const absolute = resolve(path);
  const uri = relative(repositoryRoot, absolute);
  requireCondition(!isAbsolute(uri) && uri !== '..' && !uri.startsWith(`..${process.platform === 'win32' ? '\\' : '/'}`), 'PATH_OUTSIDE_REPOSITORY', absolute);
  return uri.split('\\').join('/');
}

export function resolveRepositoryUri(uri) {
  requireCondition(typeof uri === 'string' && !isAbsolute(uri) && !uri.split('/').includes('..'), 'PATH_OUTSIDE_REPOSITORY', String(uri));
  const absolute = resolve(repositoryRoot, uri);
  requireCondition(repositoryUri(absolute) === uri, 'PATH_NOT_CANONICAL', uri);
  return absolute;
}

export async function sha256File(path) {
  return sha256(await readFile(path));
}

async function loadJson(uri) {
  const path = resolveRepositoryUri(uri);
  const stat = await lstat(path);
  requireCondition(stat.isFile() && !stat.isSymbolicLink(), 'INPUT_NOT_REGULAR_FILE', uri);
  const bytes = await readFile(path);
  return { uri, path, bytes, sha256: sha256(bytes), value: JSON.parse(bytes) };
}

function createValidator(schema) {
  return new Ajv2020({ allErrors: true, strict: true, allowUnionTypes: true }).compile(schema);
}

export async function loadVisualReviewCompiler() {
  const [packetSchema, assessmentSchema, planSchema, catalog] = await Promise.all([
    loadJson(PACKET_SCHEMA_URI), loadJson(ASSESSMENT_SCHEMA_URI), loadJson(PLAN_SCHEMA_URI), loadJson(CATALOG_URI),
  ]);
  return {
    catalog: catalog.value,
    validators: {
      packet: createValidator(packetSchema.value),
      assessment: createValidator(assessmentSchema.value),
      plan: createValidator(planSchema.value),
    },
    identities: {
      packetSchema: { uri: PACKET_SCHEMA_URI, sha256: packetSchema.sha256 },
      assessmentSchema: { uri: ASSESSMENT_SCHEMA_URI, sha256: assessmentSchema.sha256 },
      planSchema: { uri: PLAN_SCHEMA_URI, sha256: planSchema.sha256 },
      catalog: { uri: CATALOG_URI, sha256: catalog.sha256 },
    },
  };
}

function schemaCheck(validator, value, code) {
  requireCondition(validator(value), code, JSON.stringify(validator.errors));
}

function scanForExecutableAuthority(value, path = '$') {
  if (typeof value === 'string') {
    requireCondition(!executablePattern.test(value), 'EXECUTABLE_AUTHORITY', path);
    return;
  }
  if (Array.isArray(value)) {
    value.forEach((child, index) => scanForExecutableAuthority(child, `${path}[${index}]`));
    return;
  }
  if (value && typeof value === 'object') {
    Object.entries(value).forEach(([key, child]) => scanForExecutableAuthority(child, `${path}.${key}`));
  }
}

function treatmentParameters(treatment) {
  const parameters = { visible: null, minimumLayers: null, maximumLensChangePercent: null, minimumReadableBeats: null };
  if (treatment === 'CLEAR_FOREGROUND_OCCLUSION') parameters.visible = false;
  if (treatment === 'REFRAME_FOR_SUBJECT_READABILITY') parameters.maximumLensChangePercent = 15;
  if (treatment === 'REPLACE_PRIMITIVE_JOINT_WITH_LAYERED_ASSEMBLY') parameters.minimumLayers = 3;
  if (treatment === 'ADD_MID_SCALE_SURFACE_HIERARCHY') parameters.minimumLayers = 3;
  if (treatment === 'ADD_FACIAL_SEGMENTATION') parameters.minimumLayers = 4;
  if (treatment === 'EXPAND_PERFORMANCE_BEATS') parameters.minimumReadableBeats = 4;
  return parameters;
}

function operationInvariants(treatment) {
  const invariants = ['PRESERVE_SCENE_IDENTITY', 'NO_NEW_EXTERNAL_ASSET', 'NO_EXECUTABLE_AUTHORITY'];
  if (['REPLACE_PRIMITIVE_JOINT_WITH_LAYERED_ASSEMBLY', 'ADD_MID_SCALE_SURFACE_HIERARCHY', 'ADD_FACIAL_SEGMENTATION', 'EXPAND_PERFORMANCE_BEATS'].includes(treatment)) invariants.push('PRESERVE_ANIMATION_ANCHORS');
  if (['CLEAR_FOREGROUND_OCCLUSION', 'REFRAME_FOR_SUBJECT_READABILITY'].includes(treatment)) {
    invariants.push('PRESERVE_ACCEPTED_LIGHTING', 'PRESERVE_CAMERA_LANGUAGE');
  }
  return invariants;
}

function withoutPlanHash(plan) {
  const projection = structuredClone(plan);
  delete projection.planHash;
  return projection;
}

export function computePlanHash(plan) {
  return sha256(canonicalJson(withoutPlanHash(plan)));
}

export function compileVisualImprovementPlan({
  packet,
  assessment,
  packetUri,
  packetSha256,
  assessmentUri,
  assessmentSha256,
  catalog,
  validators,
}) {
  schemaCheck(validators.packet, packet, 'PACKET_SCHEMA');
  schemaCheck(validators.assessment, assessment, 'ASSESSMENT_SCHEMA');
  scanForExecutableAuthority(assessment);

  requireCondition(assessment.packetUri === packetUri, 'PACKET_URI_BINDING', `${assessment.packetUri} != ${packetUri}`);
  requireCondition(assessment.packetSha256 === packetSha256, 'PACKET_SHA256_BINDING', `${assessment.packetSha256} != ${packetSha256}`);

  const frameIds = packet.frames.map(item => item.frameId);
  const entityIds = packet.entities.map(item => item.entityId);
  const strengthIds = packet.strengths.map(item => item.strengthId);
  requireCondition(duplicates(frameIds).length === 0, 'DUPLICATE_FRAME_ID');
  requireCondition(duplicates(entityIds).length === 0, 'DUPLICATE_ENTITY_ID');
  requireCondition(duplicates(strengthIds).length === 0, 'DUPLICATE_STRENGTH_ID');
  requireCondition(duplicates(assessment.issues.map(item => item.issueId)).length === 0, 'DUPLICATE_ISSUE_ID');

  const frameById = new Map(packet.frames.map(item => [item.frameId, item]));
  const entitySet = new Set(entityIds);
  const strengthById = new Map(packet.strengths.map(item => [item.strengthId, item]));
  const treatmentById = new Map(catalog.treatments.map(item => [item.id, item]));
  requireCondition(duplicates(catalog.treatments.map(item => item.id)).length === 0, 'DUPLICATE_TREATMENT_ID');

  for (const frame of packet.frames) {
    requireCondition(entitySet.has(frame.cameraId), 'UNKNOWN_CAMERA_ENTITY', frame.cameraId);
    for (const entityId of frame.visibleEntityIds) requireCondition(entitySet.has(entityId), 'UNKNOWN_VISIBLE_ENTITY', `${frame.frameId}:${entityId}`);
  }
  for (const strength of packet.strengths) {
    for (const frameId of strength.evidenceFrameIds) requireCondition(frameById.has(frameId), 'UNKNOWN_STRENGTH_FRAME', `${strength.strengthId}:${frameId}`);
  }

  for (const issue of assessment.issues) {
    const treatment = treatmentById.get(issue.treatment);
    requireCondition(treatment, 'UNKNOWN_TREATMENT', issue.treatment);
    requireCondition(treatment.categories.includes(issue.category), 'TREATMENT_CATEGORY_MISMATCH', `${issue.treatment}:${issue.category}`);
    const evidenceFrames = issue.evidence.map(item => {
      const frame = frameById.get(item.frameId);
      requireCondition(frame, 'UNKNOWN_EVIDENCE_FRAME', `${issue.issueId}:${item.frameId}`);
      const region = item.region;
      requireCondition(region.x + region.width <= 1 && region.y + region.height <= 1, 'REGION_OUT_OF_BOUNDS', issue.issueId);
      return frame;
    });
    for (const entityId of issue.entityRefs) {
      requireCondition(entitySet.has(entityId), 'UNKNOWN_ISSUE_ENTITY', `${issue.issueId}:${entityId}`);
      requireCondition(evidenceFrames.some(frame => frame.visibleEntityIds.includes(entityId)), 'ENTITY_NOT_VISIBLE_IN_EVIDENCE', `${issue.issueId}:${entityId}`);
    }
  }

  requireCondition(duplicates(assessment.strengthConfirmations.map(item => item.strengthId)).length === 0, 'DUPLICATE_STRENGTH_CONFIRMATION');
  requireCondition(assessment.strengthConfirmations.length === packet.strengths.length, 'STRENGTH_CONFIRMATION_COUNT');
  for (const confirmation of assessment.strengthConfirmations) {
    const strength = strengthById.get(confirmation.strengthId);
    requireCondition(strength, 'UNKNOWN_STRENGTH_CONFIRMATION', confirmation.strengthId);
    for (const frameId of confirmation.evidenceFrameIds) {
      requireCondition(frameById.has(frameId) && strength.evidenceFrameIds.includes(frameId), 'STRENGTH_EVIDENCE_MISMATCH', `${confirmation.strengthId}:${frameId}`);
    }
  }

  const prioritized = [...assessment.issues].sort((left, right) =>
    severityOrder.get(left.severity) - severityOrder.get(right.severity)
    || categoryOrder.get(left.category) - categoryOrder.get(right.category)
    || left.issueId.localeCompare(right.issueId));
  const actionable = prioritized.filter(item => item.confidence >= packet.reviewPolicy.confidenceFloor);
  const deferred = prioritized.filter(item => item.confidence < packet.reviewPolicy.confidenceFloor);
  const frameOrder = new Map(packet.frames.map((frame, index) => [frame.frameId, index]));

  const priorities = prioritized.map((issue, index) => ({
    rank: index + 1,
    issueId: issue.issueId,
    severity: issue.severity,
    category: issue.category,
    confidence: issue.confidence,
  }));
  const operations = actionable.map(issue => {
    const rank = priorities.find(item => item.issueId === issue.issueId).rank;
    const treatment = treatmentById.get(issue.treatment);
    const evidenceFrameIds = [...new Set(issue.evidence.map(item => item.frameId))].sort((a, b) => frameOrder.get(a) - frameOrder.get(b));
    const shotIds = [...new Set(evidenceFrameIds.map(frameId => frameById.get(frameId).shotId))].sort();
    return {
      operationId: `OP_${String(rank).padStart(3, '0')}_${issue.issueId}`,
      issueId: issue.issueId,
      operationType: treatment.operationType,
      targetEntityIds: [...issue.entityRefs].sort(),
      shotIds,
      preset: treatment.preset,
      parameters: treatmentParameters(issue.treatment),
      invariants: operationInvariants(issue.treatment),
      evidenceFrameIds,
    };
  });
  const preservations = assessment.strengthConfirmations
    .map(confirmation => {
      const strength = strengthById.get(confirmation.strengthId);
      return {
        strengthId: confirmation.strengthId,
        category: strength.category,
        evidenceFrameIds: [...confirmation.evidenceFrameIds].sort((a, b) => frameOrder.get(a) - frameOrder.get(b)),
        rule: preservationRules[strength.category],
      };
    })
    .sort((left, right) => left.strengthId.localeCompare(right.strengthId));
  const rerenderSet = [...new Set(operations.flatMap(item => item.evidenceFrameIds))].sort((a, b) => frameOrder.get(a) - frameOrder.get(b));

  const plan = {
    documentType: 'BFS_VISUAL_IMPROVEMENT_PLAN',
    planVersion: '0.1.0',
    projectId: packet.project.projectId,
    iterationId: packet.project.iterationId,
    source: { packetUri, packetSha256, assessmentUri, assessmentSha256, sceneSha256: packet.scene.sha256 },
    decision: operations.length > 0 ? 'COMPILED' : 'NEEDS_MORE_EVIDENCE',
    priorities,
    operations,
    deferredIssues: deferred.map(item => ({ issueId: item.issueId, reason: 'CONFIDENCE_BELOW_PACKET_FLOOR' })),
    preservations,
    rerenderSet,
    authority: {
      semanticCatalogOnly: true,
      allowsPython: false,
      allowsShell: false,
      allowsNetwork: false,
      allowsArbitraryFilesystem: false,
      requiresTypedExecutor: true,
    },
    planHash: '',
  };
  plan.planHash = computePlanHash(plan);
  schemaCheck(validators.plan, plan, 'PLAN_SCHEMA');
  requireCondition(computePlanHash(plan) === plan.planHash, 'PLAN_SELF_HASH');
  return canonicalize(plan);
}

async function verifyPacketFiles(packet) {
  const records = [packet.scene.buildReceipt, ...packet.frames.map(item => item.beauty), ...packet.frames.flatMap(item => item.auxiliaryPasses)];
  for (const record of records) {
    const input = await loadJsonOrBytes(record.uri);
    requireCondition(input.sha256 === record.sha256, 'PACKET_FILE_HASH', `${record.uri} expected ${record.sha256} observed ${input.sha256}`);
  }
}

async function loadJsonOrBytes(uri) {
  const path = resolveRepositoryUri(uri);
  const stat = await lstat(path);
  requireCondition(stat.isFile() && !stat.isSymbolicLink(), 'INPUT_NOT_REGULAR_FILE', uri);
  const bytes = await readFile(path);
  return { path, bytes, sha256: sha256(bytes) };
}

export async function compileVisualImprovementPlanFiles(packetUri, assessmentUri) {
  const compiler = await loadVisualReviewCompiler();
  const [packetInput, assessmentInput] = await Promise.all([loadJson(packetUri), loadJson(assessmentUri)]);
  await verifyPacketFiles(packetInput.value);
  return {
    plan: compileVisualImprovementPlan({
      packet: packetInput.value,
      assessment: assessmentInput.value,
      packetUri,
      packetSha256: packetInput.sha256,
      assessmentUri,
      assessmentSha256: assessmentInput.sha256,
      catalog: compiler.catalog,
      validators: compiler.validators,
    }),
    compilerIdentities: compiler.identities,
  };
}

export function canonicalPlanBytes(plan) {
  return Buffer.from(`${JSON.stringify(canonicalize(plan), null, 2)}\n`);
}
