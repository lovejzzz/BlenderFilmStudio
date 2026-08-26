import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import Ajv2020 from 'ajv/dist/2020.js';
import { repositoryRoot } from './scene-spec.mjs';

export const graspSchemaPath = resolve(repositoryRoot, 'specs/grasp-spec.v0.1.schema.json');
const schema = JSON.parse(await readFile(graspSchemaPath, 'utf8'));
const ajv = new Ajv2020({ allErrors: true, strict: true, formats: { 'date-time': true } });
const validateSchema = ajv.compile(schema);

export function graspSemanticErrors(document) {
  const errors = [];
  const add = (code, path, message) => errors.push({ code, path, message });
  const fingerIds = new Set();
  const roles = new Set();
  const tipByFinger = new Map();
  for (const [fingerIndex, finger] of document.fingerChains.entries()) {
    if (fingerIds.has(finger.id)) add('SEM_DUPLICATE_FINGER', `/fingerChains/${fingerIndex}/id`, `Duplicate finger id ${finger.id}`);
    if (roles.has(finger.role)) add('SEM_DUPLICATE_FINGER_ROLE', `/fingerChains/${fingerIndex}/role`, `Duplicate finger role ${finger.role}`);
    fingerIds.add(finger.id);
    roles.add(finger.role);
    tipByFinger.set(finger.id, finger.tipSocket);
    for (const [boneIndex, bone] of finger.bones.entries()) {
      if (bone.minimumDeg > bone.maximumDeg) add('SEM_JOINT_RANGE', `/fingerChains/${fingerIndex}/bones/${boneIndex}`, `${finger.id}.${bone.boneSemantic} minimumDeg exceeds maximumDeg`);
      if (bone.restDeg < bone.minimumDeg || bone.restDeg > bone.maximumDeg) add('SEM_JOINT_REST', `/fingerChains/${fingerIndex}/bones/${boneIndex}/restDeg`, `${finger.id}.${bone.boneSemantic} restDeg is outside joint limits`);
    }
  }
  const contactIds = new Set();
  for (const [patchIndex, item] of document.contactPatches.entries()) {
    if (contactIds.has(item.id)) add('SEM_DUPLICATE_CONTACT_PATCH', `/contactPatches/${patchIndex}/id`, `Duplicate contact id ${item.id}`);
    contactIds.add(item.id);
    if (!fingerIds.has(item.fingerRef)) add('SEM_CONTACT_FINGER', `/contactPatches/${patchIndex}/fingerRef`, `${item.id} references missing finger ${item.fingerRef}`);
    if (tipByFinger.get(item.fingerRef) !== item.tipSocket) add('SEM_CONTACT_TIP', `/contactPatches/${patchIndex}/tipSocket`, `${item.id} tipSocket does not match ${item.fingerRef}`);
    const length = Math.hypot(...item.targetNormalLocal);
    if (Math.abs(length - 1) > 1e-6) add('SEM_CONTACT_NORMAL', `/contactPatches/${patchIndex}/targetNormalLocal`, `${item.id} targetNormalLocal is not unit length`);
    if (item.separationRangeM.minimum > item.separationRangeM.maximum) add('SEM_CONTACT_SEPARATION', `/contactPatches/${patchIndex}/separationRangeM`, `${item.id} separation minimum exceeds maximum`);
  }
  const phaseIds = ['approach', 'closure', 'hold', 'release'];
  const phases = phaseIds.map(id => ({ id, ...document.phases[id] }));
  for (const phase of phases) if (phase.start > phase.end) add('SEM_GRASP_PHASE_RANGE', `/phases/${phase.id}`, `${phase.id} phase start exceeds end`);
  for (let index = 1; index < phases.length; index += 1) if (phases[index].start !== phases[index - 1].end + 1) add('SEM_GRASP_PHASE_ORDER', `/phases/${phases[index].id}`, `${phases[index].id} must begin immediately after ${phases[index - 1].id}`);
  if (document.acceptance.minimumActiveContacts > document.contactPatches.length) add('SEM_ACTIVE_CONTACT_COUNT', '/acceptance/minimumActiveContacts', 'minimumActiveContacts exceeds declared contact patch count');
  let maximumAngle = 0;
  for (let left = 0; left < document.contactPatches.length; left += 1) for (let right = left + 1; right < document.contactPatches.length; right += 1) {
    const a = document.contactPatches[left].targetNormalLocal;
    const b = document.contactPatches[right].targetNormalLocal;
    const dot = Math.max(-1, Math.min(1, a.reduce((sum, value, axis) => sum + value * b[axis], 0)));
    maximumAngle = Math.max(maximumAngle, Math.acos(dot) * 180 / Math.PI);
  }
  if (maximumAngle < document.acceptance.minimumOpposingNormalAngleDeg) add('SEM_OPPOSING_NORMALS', '/contactPatches', `Maximum opposing-normal angle ${maximumAngle.toFixed(6)} deg is below threshold`);
  return errors;
}

export function validateGraspSpec(document) {
  const schemaValid = validateSchema(document);
  const errors = [];
  if (!schemaValid) {
    for (const error of validateSchema.errors ?? []) errors.push({ code: 'SCHEMA', path: error.instancePath || '/', message: error.message ?? 'Schema validation failed' });
  } else errors.push(...graspSemanticErrors(document));
  return { valid: errors.length === 0, errors };
}
