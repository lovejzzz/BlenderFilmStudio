import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import Ajv2020 from 'ajv/dist/2020.js';
import { canonicalize, repositoryRoot, semanticErrors as v01SemanticErrors } from './scene-spec.mjs';

export const schemaV02Path = resolve(repositoryRoot, 'specs/scene-spec.v0.2.schema.json');
const schemaV02 = JSON.parse(await readFile(schemaV02Path, 'utf8'));
const schemaV01 = JSON.parse(await readFile(resolve(repositoryRoot, 'specs/scene-spec.v0.1.schema.json'), 'utf8'));
const ajv = new Ajv2020({ allErrors: true, strict: true });
ajv.addSchema(schemaV01);
const validateSchema = ajv.compile(schemaV02);

function v01Projection(document) {
  const legacyOperations = new Set(['READ_MANIFEST', 'IMPORT_ASSET', 'CREATE_CAMERA', 'CREATE_LIGHT', 'SET_TRANSFORM', 'SET_RENDER', 'RENDER_PREVIEW', 'RENDER_FINAL']);
  return {
    ...structuredClone(document),
    specVersion: '0.1.0',
    actors: document.actors.map(({ id, assetRef, rigProfile, identityLock }) => ({ id, assetRef, rigProfile, identityLock })),
    security: {
      ...structuredClone(document.security),
      allowedAssetRoots: document.security.allowedAssetRoots.filter(root => root !== 'motion/'),
      allowedOperations: document.security.allowedOperations.filter(operation => legacyOperations.has(operation)),
    },
    targets: undefined,
  };
}

export function semanticErrorsV02(document) {
  const projected = v01Projection(document);
  delete projected.targets;
  const errors = v01SemanticErrors(projected);
  const add = (code, path, message) => errors.push({ code, path, message });
  const existingIds = new Set([
    ...document.assets.map(item => item.id),
    ...document.actors.map(item => item.id),
    ...document.cameras.map(item => item.id),
    ...document.lights.map(item => item.id),
    ...document.events.map(item => item.id),
  ]);
  for (const target of document.targets) {
    if (existingIds.has(target.id)) add('SEM_DUPLICATE_ID', `/targets/${target.id}`, `ID ${target.id} is not globally unique`);
    existingIds.add(target.id);
    const sockets = new Set();
    for (const socket of target.sockets) {
      if (sockets.has(socket.id)) add('SEM_DUPLICATE_TARGET_SOCKET', `/targets/${target.id}/sockets/${socket.id}`, `Target socket ${socket.id} is duplicated`);
      sockets.add(socket.id);
    }
  }
  for (const actor of document.actors) {
    const normalized = actor.actorSpecUri.replaceAll('\\', '/');
    if (normalized.includes('..') || normalized.includes('://') || !normalized.startsWith('specs/')) {
      add('SEC_ACTOR_SPEC_PATH', `/actors/${actor.id}/actorSpecUri`, `ActorSpec URI ${actor.actorSpecUri} escapes specs/`);
    }
  }
  return errors;
}

export function validateSceneSpecV02(document) {
  const schemaValid = validateSchema(document);
  const errors = [];
  if (!schemaValid) {
    for (const error of validateSchema.errors ?? []) errors.push({ code: 'SCHEMA', path: error.instancePath || '/', message: error.message ?? 'Schema validation failed' });
  } else {
    errors.push(...semanticErrorsV02(document));
  }
  return { valid: errors.length === 0, errors };
}

export function normalizeSceneSpecV02(document) {
  const normalized = structuredClone(document);
  normalized.targets.sort((left, right) => left.id.localeCompare(right.id));
  for (const target of normalized.targets) target.sockets.sort((left, right) => left.id.localeCompare(right.id));
  return canonicalize(normalized);
}
