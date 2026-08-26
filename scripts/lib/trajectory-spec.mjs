import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import Ajv2020 from 'ajv/dist/2020.js';
import { repositoryRoot } from './scene-spec.mjs';

export const trajectorySchemaPath = resolve(repositoryRoot, 'specs/trajectory-spec.v0.1.schema.json');
const schema = JSON.parse(await readFile(trajectorySchemaPath, 'utf8'));
const validateSchema = new Ajv2020({ allErrors: true, strict: true }).compile(schema);

export function semanticErrorsTrajectorySpec(document) {
  const errors = [];
  const add = (code, path, message) => errors.push({ code, path, message });
  if (document.samples.length !== document.frameEnd - document.frameStart + 1) add('SEM_TRAJECTORY_COVERAGE', '/samples', 'Samples must cover the declared frame range exactly once');
  let previous = document.frameStart - 1;
  for (const [index, sample] of document.samples.entries()) {
    const expected = document.frameStart + index;
    if (sample.frame !== expected) add('SEM_TRAJECTORY_ORDER', `/samples/${index}/frame`, `Expected continuous frame ${expected}`);
    if (sample.frame <= previous) add('SEM_TRAJECTORY_UNIQUE', `/samples/${index}/frame`, 'Trajectory frames must be strictly increasing');
    previous = sample.frame;
    const magnitude = Math.hypot(...sample.rotationQuaternionWxyz);
    if (Math.abs(magnitude - 1) > 1e-6) add('SEM_TRAJECTORY_QUATERNION', `/samples/${index}/rotationQuaternionWxyz`, `Quaternion magnitude ${magnitude} exceeds 1e-6 normalization tolerance`);
  }
  return errors;
}

export function validateTrajectorySpec(document) {
  const schemaValid = validateSchema(document);
  const errors = [];
  if (!schemaValid) {
    for (const error of validateSchema.errors ?? []) errors.push({ code: 'SCHEMA', path: error.instancePath || '/', message: error.message ?? 'Schema validation failed' });
  } else errors.push(...semanticErrorsTrajectorySpec(document));
  return { valid: errors.length === 0, errors };
}
