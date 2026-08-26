import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import Ajv2020 from 'ajv/dist/2020.js';
import { repositoryRoot } from './scene-spec.mjs';
import { semanticErrorsV02 } from './scene-spec-v02.mjs';

export const schemaV03Path = resolve(repositoryRoot, 'specs/scene-spec.v0.3.schema.json');
const readJson = async path => JSON.parse(await readFile(path, 'utf8'));
const [schemaV01, schemaV02, schemaV03] = await Promise.all([
  readJson(resolve(repositoryRoot, 'specs/scene-spec.v0.1.schema.json')),
  readJson(resolve(repositoryRoot, 'specs/scene-spec.v0.2.schema.json')),
  readJson(schemaV03Path),
]);
const ajv = new Ajv2020({ allErrors: true, strict: true });
ajv.addSchema(schemaV01);
ajv.addSchema(schemaV02);
const validateSchema = ajv.compile(schemaV03);

function v02Projection(document) {
  return {
    ...structuredClone(document),
    specVersion: '0.2.0',
    targets: document.targets.map(target => ({
      ...target,
      sockets: target.sockets.map(socket => ({ id: socket.id, transform: socket.transform })),
    })),
    security: {
      ...structuredClone(document.security),
      allowedOperations: document.security.allowedOperations.filter(operation => !['CREATE_CONSTRAINT', 'EVALUATE_GEOMETRY'].includes(operation)),
    },
    attachments: undefined,
    geometryEvaluations: undefined,
  };
}

export function semanticErrorsV03(document) {
  const projected = v02Projection(document);
  delete projected.attachments;
  delete projected.geometryEvaluations;
  const errors = semanticErrorsV02(projected);
  const add = (code, path, message) => errors.push({ code, path, message });
  const assets = new Map(document.assets.map(asset => [asset.id, asset]));
  const actors = new Map(document.actors.map(actor => [actor.id, actor]));

  for (const target of document.targets) {
    for (const socket of target.sockets) {
      if (socket.binding === 'ASSET_OBJECT' && !assets.has(socket.assetRef)) {
        add('SEM_TARGET_ASSET', `/targets/${target.id}/sockets/${socket.id}/assetRef`, `Asset-bound socket references missing asset ${socket.assetRef}`);
      }
    }
  }

  const attachmentIds = new Set();
  for (const attachment of document.attachments) {
    if (attachmentIds.has(attachment.id)) add('SEM_DUPLICATE_ATTACHMENT', `/attachments/${attachment.id}`, `Attachment ${attachment.id} is duplicated`);
    attachmentIds.add(attachment.id);
    const owner = assets.get(attachment.ownerAssetRef);
    if (!owner || owner.kind !== 'PROP') add('SEM_ATTACHMENT_OWNER', `/attachments/${attachment.id}/ownerAssetRef`, `Attachment owner must reference a PROP asset`);
    if (!actors.has(attachment.targetActorRef)) add('SEM_ATTACHMENT_ACTOR', `/attachments/${attachment.id}/targetActorRef`, `Attachment target actor is missing`);
    let previous = -1;
    for (const [index, key] of attachment.influenceKeys.entries()) {
      if (key.frame <= previous) add('SEM_INFLUENCE_ORDER', `/attachments/${attachment.id}/influenceKeys/${index}/frame`, 'Influence keys must be strictly increasing');
      if (key.frame < document.shot.frameStart || key.frame > document.shot.frameEnd) add('SEM_INFLUENCE_FRAME', `/attachments/${attachment.id}/influenceKeys/${index}/frame`, 'Influence key is outside the shot');
      previous = key.frame;
    }
    if (!attachment.influenceKeys.some(key => key.value === 0) || !attachment.influenceKeys.some(key => key.value === 1)) {
      add('SEM_INFLUENCE_STATES', `/attachments/${attachment.id}/influenceKeys`, 'Attachment must declare both detached and attached states');
    }
  }

  const geometryIds = new Set();
  for (const item of document.geometryEvaluations) {
    if (geometryIds.has(item.id)) add('SEM_DUPLICATE_GEOMETRY_EVALUATION', `/geometryEvaluations/${item.id}`, `Geometry evaluation ${item.id} is duplicated`);
    geometryIds.add(item.id);
    if (!assets.has(item.assetARef) || !assets.has(item.assetBRef)) add('SEM_GEOMETRY_ASSET', `/geometryEvaluations/${item.id}`, 'Geometry evaluation references a missing asset');
    const expected = ['APPROACH', 'ACQUIRE', 'HOLD', 'RELEASE', 'RETREAT'];
    if (item.phases.map(phase => phase.id).join(',') !== expected.join(',')) add('SEM_PHASE_ORDER', `/geometryEvaluations/${item.id}/phases`, `Phases must be ${expected.join(', ')}`);
    let previousEnd = document.shot.frameStart - 1;
    for (const [index, phase] of item.phases.entries()) {
      if (phase.frameStart !== previousEnd + 1 || phase.frameEnd < phase.frameStart) add('SEM_PHASE_RANGE', `/geometryEvaluations/${item.id}/phases/${index}`, 'Phases must be contiguous, ordered, and non-reversed');
      previousEnd = phase.frameEnd;
    }
    if (previousEnd !== document.shot.frameEnd) add('SEM_PHASE_COVERAGE', `/geometryEvaluations/${item.id}/phases`, 'Phases must cover the full shot');
  }
  return errors;
}

export function validateSceneSpecV03(document) {
  const schemaValid = validateSchema(document);
  const errors = [];
  if (!schemaValid) {
    for (const error of validateSchema.errors ?? []) errors.push({ code: 'SCHEMA', path: error.instancePath || '/', message: error.message ?? 'Schema validation failed' });
  } else {
    errors.push(...semanticErrorsV03(document));
  }
  return { valid: errors.length === 0, errors };
}
