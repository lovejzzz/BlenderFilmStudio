import { readFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import Ajv2020 from 'ajv/dist/2020.js';

const repositoryRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const schemaPath = resolve(repositoryRoot, 'specs/scene-spec.v0.1.schema.json');
const fixturePath = resolve(repositoryRoot, 'specs/fixtures/scene-spec-fixtures.v0.1.json');

const readJson = async (path) => JSON.parse(await readFile(path, 'utf8'));
const schema = await readJson(schemaPath);
const ajv = new Ajv2020({ allErrors: true, strict: true });
const validateSchema = ajv.compile(schema);

function decodePointer(path) {
  if (!path.startsWith('/')) throw new Error(`Mutation path must be a JSON Pointer: ${path}`);
  return path.slice(1).split('/').map(part => part.replaceAll('~1', '/').replaceAll('~0', '~'));
}

function resolveParent(document, path) {
  const segments = decodePointer(path);
  const key = segments.pop();
  let parent = document;
  for (const segment of segments) {
    if (parent?.[segment] === undefined) throw new Error(`Mutation path does not exist: ${path}`);
    parent = parent[segment];
  }
  return { parent, key };
}

function applyMutation(document, mutation) {
  const { parent, key } = resolveParent(document, mutation.path);
  if (mutation.op === 'set') parent[key] = structuredClone(mutation.value);
  else if (mutation.op === 'delete') delete parent[key];
  else if (mutation.op === 'append') {
    const target = parent[key];
    if (!Array.isArray(target)) throw new Error(`Append target is not an array: ${mutation.path}`);
    target.push(structuredClone(mutation.value));
  } else throw new Error(`Unsupported mutation: ${mutation.op}`);
}

function semanticErrors(document) {
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

function validateDocument(document) {
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

async function runFixtureSuite() {
  const fixtureSuite = await readJson(fixturePath);
  let passed = 0;
  for (const fixture of fixtureSuite.cases) {
    const document = structuredClone(fixtureSuite.base);
    for (const mutation of fixture.mutations) applyMutation(document, mutation);
    const result = validateDocument(document);
    const codeMatched = fixture.expectedCode === undefined || result.errors.some(error => error.code === fixture.expectedCode);
    const fixturePassed = result.valid === fixture.expectedValid && codeMatched;
    if (fixturePassed) passed += 1;
    const marker = fixturePassed ? 'PASS' : 'FAIL';
    const codes = result.errors.map(error => error.code).join(',') || 'NONE';
    process.stdout.write(`${marker} ${fixture.id} expected=${fixture.expectedValid} actual=${result.valid} codes=${codes}\n`);
  }
  process.stdout.write(`\n${passed}/${fixtureSuite.cases.length} fixtures passed\n`);
  if (passed !== fixtureSuite.cases.length) process.exitCode = 1;
}

async function validateFiles(paths) {
  let failed = false;
  for (const inputPath of paths) {
    const absolutePath = resolve(process.cwd(), inputPath);
    const result = validateDocument(await readJson(absolutePath));
    process.stdout.write(`${result.valid ? 'VALID' : 'INVALID'} ${inputPath}\n`);
    for (const error of result.errors) process.stdout.write(`  ${error.code} ${error.path}: ${error.message}\n`);
    if (!result.valid) failed = true;
  }
  if (failed) process.exitCode = 1;
}

const inputPaths = process.argv.slice(2);
if (inputPaths.length > 0) await validateFiles(inputPaths);
else await runFixtureSuite();
