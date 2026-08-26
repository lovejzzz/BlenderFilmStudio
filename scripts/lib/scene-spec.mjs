import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import Ajv2020 from 'ajv/dist/2020.js';

export const repositoryRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
export const schemaPath = resolve(repositoryRoot, 'specs/scene-spec.v0.1.schema.json');
export const fixturePath = resolve(repositoryRoot, 'specs/fixtures/scene-spec-fixtures.v0.1.json');

export const readJson = async (path) => JSON.parse(await readFile(path, 'utf8'));

const schema = await readJson(schemaPath);
const ajv = new Ajv2020({ allErrors: true, strict: true });
const validateSchema = ajv.compile(schema);

export function canonicalize(value) {
  if (Array.isArray(value)) return value.map(canonicalize);
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value)
        .sort(([left], [right]) => left < right ? -1 : left > right ? 1 : 0)
        .map(([key, child]) => [key, canonicalize(child)]),
    );
  }
  return value;
}

export function canonicalJson(value) {
  return JSON.stringify(canonicalize(value));
}

export function sha256(value) {
  return createHash('sha256').update(value).digest('hex');
}

export function semanticErrors(document) {
  const errors = [];
  const add = (code, path, message) => errors.push({ code, path, message });

  if (document.shot.frameEnd < document.shot.frameStart) {
    add('SEM_FRAME_RANGE', '/shot/frameEnd', 'frameEnd must be greater than or equal to frameStart');
  }

  const collections = [document.assets, document.actors, document.cameras, document.lights, document.events];
  const ids = new Set();
  for (const item of collections.flat()) {
    if (ids.has(item.id)) add('SEM_DUPLICATE_ID', `/${item.id}`, `ID ${item.id} is not globally unique`);
    ids.add(item.id);
  }

  const cameras = new Set(document.cameras.map(camera => camera.id));
  if (!cameras.has(document.shot.activeCamera)) {
    add('SEM_ACTIVE_CAMERA', '/shot/activeCamera', `Camera ${document.shot.activeCamera} does not exist`);
  }

  for (const camera of document.cameras) {
    let previousFrame = -1;
    for (const [index, key] of (camera.transformKeys ?? []).entries()) {
      const keyPath = `/cameras/${camera.id}/transformKeys/${index}/frame`;
      if (key.frame < document.shot.frameStart || key.frame > document.shot.frameEnd) {
        add('SEM_CAMERA_KEY_FRAME', keyPath, `Camera key ${key.frame} is outside the shot frame range`);
      }
      if (key.frame <= previousFrame) {
        add('SEM_CAMERA_KEY_ORDER', keyPath, 'Camera transform keys must be strictly increasing');
      }
      previousFrame = key.frame;
    }
  }

  const assets = new Map(document.assets.map(asset => [asset.id, asset]));
  for (const actor of document.actors) {
    const asset = assets.get(actor.assetRef);
    if (!asset || asset.kind !== 'CHARACTER') {
      add('SEM_ACTOR_ASSET', `/actors/${actor.id}/assetRef`, `Actor ${actor.id} must reference a CHARACTER asset`);
    }
  }

  const eventSubjects = new Set([...document.assets.map(item => item.id), ...document.actors.map(item => item.id)]);
  for (const event of document.events) {
    if (event.frame < document.shot.frameStart || event.frame > document.shot.frameEnd) {
      add('SEM_EVENT_FRAME', `/events/${event.id}/frame`, `Event ${event.id} is outside the shot frame range`);
    }
    for (const subject of event.subjects) {
      if (!eventSubjects.has(subject)) add('SEM_EVENT_SUBJECT', `/events/${event.id}/subjects`, `Subject ${subject} does not exist`);
    }
  }

  for (const asset of document.assets) {
    const normalized = asset.uri.replaceAll('\\', '/');
    if (normalized.startsWith('/') || normalized.includes('://') || normalized.split('/').includes('..')) {
      add('SEC_PATH_TRAVERSAL', `/assets/${asset.id}/uri`, `Asset URI ${asset.uri} escapes the restricted workspace`);
      continue;
    }
    if (!document.security.allowedAssetRoots.some(root => normalized.startsWith(root))) {
      add('SEC_ASSET_ROOT', `/assets/${asset.id}/uri`, `Asset URI ${asset.uri} is outside allowedAssetRoots`);
    }
  }

  const outputRoot = document.render.outputRoot.replaceAll('\\', '/');
  if (!outputRoot.startsWith('renders/') || outputRoot.split('/').includes('..')) {
    add('SEC_OUTPUT_ROOT', '/render/outputRoot', 'outputRoot must remain below renders/');
  }

  return errors;
}

export function validateSceneSpec(document) {
  const schemaValid = validateSchema(document);
  const errors = [];
  if (!schemaValid) {
    for (const error of validateSchema.errors ?? []) {
      errors.push({ code: 'SCHEMA', path: error.instancePath || '/', message: error.message ?? 'Schema validation failed' });
    }
  } else {
    errors.push(...semanticErrors(document));
  }
  return { valid: errors.length === 0, errors };
}
