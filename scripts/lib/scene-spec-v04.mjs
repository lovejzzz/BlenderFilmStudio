import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import Ajv2020 from 'ajv/dist/2020.js';
import { repositoryRoot } from './scene-spec.mjs';
import { semanticErrorsV03 } from './scene-spec-v03.mjs';

export const schemaV04Path = resolve(repositoryRoot, 'specs/scene-spec.v0.4.schema.json');
const readJson = async path => JSON.parse(await readFile(path, 'utf8'));
const [schemaV01, schemaV02, schemaV03, schemaV04] = await Promise.all([
  readJson(resolve(repositoryRoot, 'specs/scene-spec.v0.1.schema.json')),
  readJson(resolve(repositoryRoot, 'specs/scene-spec.v0.2.schema.json')),
  readJson(resolve(repositoryRoot, 'specs/scene-spec.v0.3.schema.json')),
  readJson(schemaV04Path),
]);
const ajv = new Ajv2020({ allErrors: true, strict: true });
ajv.addSchema(schemaV01);
ajv.addSchema(schemaV02);
ajv.addSchema(schemaV03);
const validateSchema = ajv.compile(schemaV04);

function v03Projection(document) {
  const projected = structuredClone(document);
  projected.specVersion = '0.3.0';
  delete projected.grasps;
  projected.security.allowedOperations = projected.security.allowedOperations.filter(operation => operation !== 'CREATE_GRASP');
  return projected;
}

export function semanticErrorsV04(document) {
  const errors = semanticErrorsV03(v03Projection(document));
  const add = (code, path, message) => errors.push({ code, path, message });
  const assets = new Map(document.assets.map(asset => [asset.id, asset]));
  const ids = new Set();
  for (const [index, grasp] of document.grasps.entries()) {
    const path = `/grasps/${index}`;
    if (ids.has(grasp.id)) add('SEM_DUPLICATE_GRASP', `${path}/id`, `Grasp ${grasp.id} is duplicated`);
    ids.add(grasp.id);
    const actorAsset = assets.get(grasp.actorAssetRef);
    const propAsset = assets.get(grasp.propAssetRef);
    if (!actorAsset || actorAsset.kind !== 'CHARACTER') add('SEM_GRASP_ACTOR_ASSET', `${path}/actorAssetRef`, 'Grasp actorAssetRef must reference a CHARACTER asset');
    if (!propAsset || propAsset.kind !== 'PROP') add('SEM_GRASP_PROP_ASSET', `${path}/propAssetRef`, 'Grasp propAssetRef must reference a PROP asset');
    let previous = document.shot.frameStart - 1;
    for (const [keyIndex, key] of grasp.transportKeys.entries()) {
      if (key.frame <= previous) add('SEM_GRASP_TRANSPORT_ORDER', `${path}/transportKeys/${keyIndex}/frame`, 'Transport keys must be strictly increasing');
      if (key.frame < document.shot.frameStart || key.frame > document.shot.frameEnd) add('SEM_GRASP_TRANSPORT_FRAME', `${path}/transportKeys/${keyIndex}/frame`, 'Transport key is outside the shot');
      previous = key.frame;
    }
  }
  return errors;
}

export function validateSceneSpecV04(document) {
  const schemaValid = validateSchema(document);
  const errors = [];
  if (!schemaValid) {
    for (const error of validateSchema.errors ?? []) errors.push({ code: 'SCHEMA', path: error.instancePath || '/', message: error.message ?? 'Schema validation failed' });
  } else errors.push(...semanticErrorsV04(document));
  return { valid: errors.length === 0, errors };
}
