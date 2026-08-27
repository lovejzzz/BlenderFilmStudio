import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import Ajv2020 from 'ajv/dist/2020.js';
import { canonicalJson, repositoryRoot, sha256, validateSceneSpec } from './scene-spec.mjs';

export const B43_D1_SPEC_URI = 'specs/codex-scenespec-adapter-derivation.v0.1.json';
export const B43_D1_SPEC_PATH = resolve(repositoryRoot, B43_D1_SPEC_URI);
export const B43_D1_SPEC_SHA256 = '27bd24cd964629f8653a20ffed4ab87c91246d4e8e591553582014b07f477d81';
export const B43_D1_PREREG_COMMIT = 'a80c42c338731717efe95c3c4c94c25f69ac0148';

export class B43Error extends Error {
  constructor(code, message = code) {
    super(`${code}: ${message}`);
    this.name = 'B43Error';
    this.code = code;
  }
}

export async function sha256File(path) {
  return sha256(await readFile(path));
}

export async function readB43Spec() {
  const bytes = await readFile(B43_D1_SPEC_PATH);
  const digest = sha256(bytes);
  if (digest !== B43_D1_SPEC_SHA256) throw new B43Error('DERIVATION_SPEC_HASH', digest);
  return JSON.parse(bytes);
}

function frozenRecords(value, records = []) {
  if (Array.isArray(value)) {
    for (const item of value) frozenRecords(item, records);
  } else if (value && typeof value === 'object') {
    if (typeof value.uri === 'string' && typeof value.sha256 === 'string' && !value.uri.includes('://')) records.push(value);
    for (const child of Object.values(value)) frozenRecords(child, records);
  }
  return records;
}

export async function verifyFrozenInputs(spec, expectedHashOverrides = {}) {
  const observations = [];
  for (const record of frozenRecords(spec.frozenInputs)) {
    const expectedSha256 = expectedHashOverrides[record.uri] ?? record.sha256;
    const observedSha256 = await sha256File(resolve(repositoryRoot, record.uri)).catch(() => null);
    observations.push({ uri: record.uri, expectedSha256, observedSha256, match: observedSha256 === expectedSha256 });
  }
  const mismatch = observations.find(item => !item.match);
  if (mismatch) throw new B43Error('FROZEN_INPUT_HASH', `${mismatch.uri} expected ${mismatch.expectedSha256} observed ${mismatch.observedSha256}`);
  return observations;
}

export async function createProposalValidator(spec) {
  const schemaRecord = spec.frozenInputs.proposalSchema;
  const schema = JSON.parse(await readFile(resolve(repositoryRoot, schemaRecord.uri), 'utf8'));
  return new Ajv2020({ allErrors: true, strict: true }).compile(schema);
}

const presetFields = ['shotPreset', 'assetPreset', 'cameraPreset', 'lightingPreset'];

export async function validateProposal(proposal, expectedBriefId, spec, validateSchema = null) {
  const validator = validateSchema ?? await createProposalValidator(spec);
  if (!validator(proposal)) throw new B43Error('PROPOSAL_SCHEMA', JSON.stringify(validator.errors));
  if (proposal.briefId !== expectedBriefId) throw new B43Error('PROPOSAL_BRIEF_ID', `${proposal.briefId} != ${expectedBriefId}`);
  const expected = spec.expectedProposals.find(item => item.briefId === expectedBriefId);
  if (!expected) throw new B43Error('PROPOSAL_BRIEF_ID', `unregistered brief ${expectedBriefId}`);

  if (expectedBriefId === spec.rejectionMaterialization.briefId && proposal.decision === 'ACCEPT') {
    throw new B43Error('UNAUTHORIZED_BRIEF_ACCEPTED');
  }

  if (proposal.decision === 'REJECT') {
    if (presetFields.some(field => proposal[field] !== 'NONE')) throw new B43Error('REJECT_PRESETS_NOT_NONE');
    const permittedReason = expectedBriefId === spec.rejectionMaterialization.briefId
      ? 'UNAUTHORIZED_NETWORK_OR_CODE' : 'AMBIGUOUS_INTENT';
    if (proposal.reasonCode !== permittedReason) throw new B43Error('PROPOSAL_DECISION_POLICY');
    return { valid: true, materialize: false, expected };
  }

  if (proposal.reasonCode !== 'SUPPORTED_PRESET') throw new B43Error('PROPOSAL_DECISION_POLICY');
  if (presetFields.some(field => proposal[field] !== expected[field])) throw new B43Error('PROPOSAL_COMBINATION');
  return { valid: true, materialize: true, expected };
}

export async function materializeSceneSpec(proposal, spec, validateSchema = null) {
  const proposalValidation = await validateProposal(proposal, proposal.briefId, spec, validateSchema);
  if (!proposalValidation.materialize) throw new B43Error('PROPOSAL_NOT_MATERIALIZABLE');
  const recipe = spec.materializations.find(item => item.briefId === proposal.briefId);
  if (!recipe) throw new B43Error('PROPOSAL_COMBINATION', `no materialization for ${proposal.briefId}`);
  const baseRecord = spec.frozenInputs.baseScenes.find(item => item.id === recipe.baseScene);
  if (!baseRecord) throw new B43Error('FROZEN_INPUT_HASH', `missing base scene ${recipe.baseScene}`);
  const scene = JSON.parse(await readFile(resolve(repositoryRoot, baseRecord.uri), 'utf8'));
  scene.shot = structuredClone(recipe.replace.shot);
  scene.cameras = structuredClone(recipe.replace.cameras);
  if (recipe.replace.lights) scene.lights = structuredClone(recipe.replace.lights);
  scene.render = { ...scene.render, outputRoot: recipe.replace.renderOutputRoot };
  scene.provenance = structuredClone(recipe.replace.provenance);
  const sceneValidation = validateSceneSpec(scene);
  if (!sceneValidation.valid) throw new B43Error('SCENE_SPEC_VALIDATION', JSON.stringify(sceneValidation.errors));
  return { scene, recipe, sceneValidation };
}

function caughtReason(error) {
  return error instanceof B43Error ? error.code : `UNEXPECTED_${error?.name ?? 'ERROR'}`;
}

export async function runB43Attacks(spec) {
  const expectedById = new Map(spec.expectedProposals.map(item => [item.briefId, item]));
  const validator = await createProposalValidator(spec);
  const a = structuredClone(expectedById.get('BRIEF_B43_TABLETOP_PUSH'));
  const b = structuredClone(expectedById.get('BRIEF_B43_INTERIOR_STILL'));
  const rejected = structuredClone(expectedById.get('BRIEF_B43_UNAUTHORIZED_DOWNLOAD'));
  const cases = [
    ['A01_EXTRA_PROPERTY', async () => { const value = { ...a, python: 'execute' }; await validateProposal(value, a.briefId, spec, validator); }],
    ['A02_UNKNOWN_PRESET', async () => { const value = { ...a, cameraPreset: 'FREEFORM_CAMERA' }; await validateProposal(value, a.briefId, spec, validator); }],
    ['A03_BRIEF_ID_MISMATCH', async () => validateProposal(a, b.briefId, spec, validator)],
    ['A04_ACCEPT_WRONG_COMBINATION', async () => { const value = { ...a, cameraPreset: 'STATIC_70MM' }; await validateProposal(value, a.briefId, spec, validator); }],
    ['A05_ACCEPT_WRONG_REASON', async () => { const value = { ...a, reasonCode: 'AMBIGUOUS_INTENT' }; await validateProposal(value, a.briefId, spec, validator); }],
    ['A06_REJECT_WITH_PRESET', async () => { const value = { ...rejected, cameraPreset: 'STATIC_70MM' }; await validateProposal(value, rejected.briefId, spec, validator); }],
    ['A07_UNAUTHORIZED_ACCEPT', async () => { const value = { ...a, briefId: rejected.briefId }; await validateProposal(value, rejected.briefId, spec, validator); }],
    ['A08_BASE_SCENE_HASH_DRIFT', async () => verifyFrozenInputs(spec, { 'specs/benchmarks/B01.scene.json': '0'.repeat(64) })],
  ];
  const expected = new Map(spec.requiredAttacks.map(item => [item.id, item.expectedReason]));
  const attacks = [];
  for (const [id, execute] of cases) {
    let observedReason = 'NO_REJECTION';
    try { await execute(); } catch (error) { observedReason = caughtReason(error); }
    const expectedReason = expected.get(id);
    attacks.push({ id, expectedReason, observedReason, passed: observedReason === expectedReason });
  }
  return attacks;
}

export function hashB43Evidence(evidence) {
  const projection = structuredClone(evidence);
  for (const key of ['evidenceHash', 'analysis', 'attacks', 'attacksPassed', 'verdict']) delete projection[key];
  return sha256(canonicalJson(projection));
}

export function analyzeB43Evidence(evidence, spec) {
  const failures = [];
  const gate = (condition, code) => { if (!condition && !failures.includes(code)) failures.push(code); };
  gate(evidence?.schemaVersion === 'bfs.codexSceneSpecAdapterDerivationEvidence.v0.1' && evidence?.experimentId === 'B43-D1', 'EVIDENCE_SCHEMA');
  gate(evidence?.preregistration?.commit === B43_D1_PREREG_COMMIT && evidence?.preregistration?.specSha256 === B43_D1_SPEC_SHA256, 'PREREGISTRATION_IDENTITY');
  gate(evidence?.frozenInputsVerified === true && evidence?.frozenInputObservations?.every(item => item.match), 'FROZEN_INPUT_HASH');
  gate(evidence?.cases?.length === spec.expectedProposals.length, 'CASE_COUNT');
  for (const expected of spec.expectedProposals) {
    const observed = evidence?.cases?.find(item => item.briefId === expected.briefId);
    gate(observed?.proposalSchemaValid === true && observed?.proposalSemanticValid === true, `PROPOSAL_VALID_${expected.briefId}`);
    gate(observed?.proposalOracleExact === true, `PROPOSAL_ORACLE_${expected.briefId}`);
    if (expected.decision === 'ACCEPT') {
      gate(observed?.sceneSpecValid === true, `SCENE_SPEC_${expected.briefId}`);
      gate(observed?.buildPlansByteEqual === true && typeof observed?.planHash === 'string', `BUILD_PLAN_${expected.briefId}`);
    } else {
      gate(observed?.sceneSpecCount === 0 && observed?.buildPlanCount === 0, `REJECTION_OUTPUT_${expected.briefId}`);
    }
  }
  gate(evidence?.operations?.codex === 0 && evidence?.operations?.model === 0 && evidence?.operations?.blender === 0
    && evidence?.operations?.container === 0 && evidence?.operations?.network === 0, 'PROHIBITED_OPERATION');
  gate(evidence?.attacks?.length === spec.requiredAttacks.length && evidence?.attacks?.every(item => item.passed), 'ATTACKS');
  gate(evidence?.evidenceHash === hashB43Evidence(evidence), 'EVIDENCE_SELF_HASH');
  return {
    schemaVersion: 'bfs.codexSceneSpecAdapterDerivationAnalysis.v0.1',
    passed: failures.length === 0,
    failures,
    decision: failures[0] ?? spec.acceptedVerdict,
  };
}

