import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import Ajv2020 from 'ajv/dist/2020.js';
import { repositoryRoot } from './scene-spec.mjs';
import { semanticErrorsV04 } from './scene-spec-v04.mjs';

export const schemaV05Path = resolve(repositoryRoot, 'specs/scene-spec.v0.5.schema.json');
const readJson = async path => JSON.parse(await readFile(path, 'utf8'));
const [schemaV01, schemaV02, schemaV03, schemaV04, schemaV05] = await Promise.all([
  readJson(resolve(repositoryRoot, 'specs/scene-spec.v0.1.schema.json')),
  readJson(resolve(repositoryRoot, 'specs/scene-spec.v0.2.schema.json')),
  readJson(resolve(repositoryRoot, 'specs/scene-spec.v0.3.schema.json')),
  readJson(resolve(repositoryRoot, 'specs/scene-spec.v0.4.schema.json')),
  readJson(schemaV05Path),
]);
const ajv = new Ajv2020({ allErrors: true, strict: true });
for (const schema of [schemaV01, schemaV02, schemaV03, schemaV04]) ajv.addSchema(schema);
const validateSchema = ajv.compile(schemaV05);

function v04Projection(document) {
  const projected = structuredClone(document);
  projected.specVersion = '0.4.0';
  delete projected.trajectories;
  projected.security.allowedOperations = projected.security.allowedOperations.filter(operation => operation !== 'CREATE_TRAJECTORY_REPLAY');
  return projected;
}

export function semanticErrorsV05(document) {
  const errors = semanticErrorsV04(v04Projection(document));
  const add = (code, path, message) => errors.push({ code, path, message });
  const assets = new Map(document.assets.map(asset => [asset.id, asset]));
  const ids = new Set();
  for (const [index, trajectory] of document.trajectories.entries()) {
    const path = `/trajectories/${index}`;
    if (ids.has(trajectory.id)) add('SEM_DUPLICATE_TRAJECTORY', `${path}/id`, `Trajectory ${trajectory.id} is duplicated`);
    ids.add(trajectory.id);
    const asset = assets.get(trajectory.assetRef);
    if (!asset || asset.kind !== 'PROP') add('SEM_TRAJECTORY_PROP_ASSET', `${path}/assetRef`, 'Trajectory assetRef must reference a PROP asset');
  }
  return errors;
}

export function validateSceneSpecV05(document) {
  const schemaValid = validateSchema(document);
  const errors = [];
  if (!schemaValid) {
    for (const error of validateSchema.errors ?? []) errors.push({ code: 'SCHEMA', path: error.instancePath || '/', message: error.message ?? 'Schema validation failed' });
  } else errors.push(...semanticErrorsV05(document));
  return { valid: errors.length === 0, errors };
}
