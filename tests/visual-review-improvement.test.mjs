import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import {
  canonicalPlanBytes,
  compileVisualImprovementPlan,
  compileVisualImprovementPlanFiles,
  computePlanHash,
  loadVisualReviewCompiler,
} from '../scripts/lib/visual-review-improvement.mjs';
import { sha256 } from '../scripts/lib/scene-spec.mjs';

const packetUri = 'specs/fixtures/visual-review/PC4_ATTEMPT03.packet.json';
const assessmentUri = 'specs/fixtures/visual-review/PC4_ATTEMPT03.teacher-assessment.json';
const packetBytes = await readFile(packetUri);
const assessmentBytes = await readFile(assessmentUri);
const basePacket = JSON.parse(packetBytes);
const baseAssessment = JSON.parse(assessmentBytes);
const compiler = await loadVisualReviewCompiler();
const packetSha256 = sha256(packetBytes);
const assessmentSha256 = sha256(assessmentBytes);

function clone(value) {
  return structuredClone(value);
}

function compile(packet = clone(basePacket), assessment = clone(baseAssessment), overrides = {}) {
  return compileVisualImprovementPlan({
    packet,
    assessment,
    packetUri,
    packetSha256,
    assessmentUri,
    assessmentSha256,
    catalog: compiler.catalog,
    validators: compiler.validators,
    ...overrides,
  });
}

function expectCode(code, mutate) {
  const packet = clone(basePacket);
  const assessment = clone(baseAssessment);
  mutate(packet, assessment);
  assert.throws(() => compile(packet, assessment), error => error?.code === code);
}

test('teacher fixture compiles to six bounded operations and two preservations', async () => {
  const { plan } = await compileVisualImprovementPlanFiles(packetUri, assessmentUri);
  assert.equal(plan.decision, 'COMPILED');
  assert.equal(plan.operations.length, 6);
  assert.deepEqual(plan.operations.map(item => item.operationType), [
    'SET_SHOT_VISIBILITY',
    'APPLY_FRAMING_PRESET',
    'ADD_DETAIL_SYSTEM',
    'REPLACE_FORM_WITH_ASSEMBLY',
    'APPLY_FRAMING_PRESET',
    'ADD_DETAIL_SYSTEM',
  ]);
  assert.equal(plan.preservations.length, 2);
  assert.equal(plan.planHash, computePlanHash(plan));
  assert.deepEqual(plan.rerenderSet, ['PC4_F0048', 'PC4_F0144', 'PC4_F0240']);
  assert.deepEqual(plan.authority, {
    semanticCatalogOnly: true,
    allowsPython: false,
    allowsShell: false,
    allowsNetwork: false,
    allowsArbitraryFilesystem: false,
    requiresTypedExecutor: true,
  });
});

test('two compilations are canonical byte exact', () => {
  assert.deepEqual(canonicalPlanBytes(compile()), canonicalPlanBytes(compile()));
});

test('low confidence issues are deferred without operations', () => {
  const assessment = clone(baseAssessment);
  assessment.issues.forEach(item => { item.confidence = 0.1; });
  const plan = compile(clone(basePacket), assessment);
  assert.equal(plan.decision, 'NEEDS_MORE_EVIDENCE');
  assert.equal(plan.operations.length, 0);
  assert.equal(plan.deferredIssues.length, assessment.issues.length);
});

test('unknown packet property is rejected', () => expectCode('PACKET_SCHEMA', packet => { packet.python = 'none'; }));
test('unknown assessment property is rejected', () => expectCode('ASSESSMENT_SCHEMA', (_packet, assessment) => { assessment.mutation = 'none'; }));
test('unknown evidence frame is rejected', () => expectCode('UNKNOWN_EVIDENCE_FRAME', (_packet, assessment) => { assessment.issues[0].evidence[0].frameId = 'UNKNOWN_FRAME'; }));
test('unknown issue entity is rejected', () => expectCode('UNKNOWN_ISSUE_ENTITY', (_packet, assessment) => { assessment.issues[0].entityRefs[0] = 'UNKNOWN_ENTITY'; }));
test('category and treatment mismatch is rejected', () => expectCode('TREATMENT_CATEGORY_MISMATCH', (_packet, assessment) => { assessment.issues[0].category = 'ANIMATION'; }));
test('cross-field region overflow is rejected', () => expectCode('REGION_OUT_OF_BOUNDS', (_packet, assessment) => { assessment.issues[0].evidence[0].region.x = 0.5; assessment.issues[0].evidence[0].region.width = 0.6; }));
test('duplicate issue id is rejected', () => expectCode('DUPLICATE_ISSUE_ID', (_packet, assessment) => { assessment.issues[1].issueId = assessment.issues[0].issueId; }));
test('duplicate entity id is rejected', () => expectCode('DUPLICATE_ENTITY_ID', packet => { packet.entities[1].entityId = packet.entities[0].entityId; }));
test('unknown visible entity is rejected', () => expectCode('UNKNOWN_VISIBLE_ENTITY', packet => { packet.frames[0].visibleEntityIds[0] = 'UNKNOWN_VISIBLE'; }));
test('executable code language is rejected', () => expectCode('EXECUTABLE_AUTHORITY', (_packet, assessment) => { assessment.issues[0].observation = 'The response asks to import a runtime module before changing the scene.'; }));
test('network authority language is rejected', () => expectCode('EXECUTABLE_AUTHORITY', (_packet, assessment) => { assessment.issues[0].desiredOutcome = 'Fetch an external asset from https://example.invalid before the next review.'; }));
test('packet hash mismatch is rejected', () => {
  assert.throws(() => compile(clone(basePacket), clone(baseAssessment), { packetSha256: '0'.repeat(64) }), error => error?.code === 'PACKET_SHA256_BINDING');
});
test('entity not visible in cited evidence is rejected', () => expectCode('ENTITY_NOT_VISIBLE_IN_EVIDENCE', (_packet, assessment) => { assessment.issues[1].entityRefs = ['B62_COLUMN_03']; }));
test('missing preservation confirmation is rejected', () => expectCode('STRENGTH_CONFIRMATION_COUNT', (_packet, assessment) => { assessment.strengthConfirmations.pop(); }));
test('strength evidence outside the accepted frame set is rejected', () => expectCode('STRENGTH_EVIDENCE_MISMATCH', (_packet, assessment) => { assessment.strengthConfirmations[0].evidenceFrameIds = ['PC4_UNKNOWN']; }));

test('plan hash detects semantic tampering', () => {
  const plan = compile();
  plan.operations[0].targetEntityIds = ['PC4_HELMET_SHELL'];
  assert.notEqual(plan.planHash, computePlanHash(plan));
});
