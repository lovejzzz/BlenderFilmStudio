import { resolve } from 'node:path';
import { fixturePath, readJson, validateSceneSpec } from './lib/scene-spec.mjs';

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

async function runFixtureSuite() {
  const fixtureSuite = await readJson(fixturePath);
  let passed = 0;
  for (const fixture of fixtureSuite.cases) {
    const document = structuredClone(fixtureSuite.base);
    for (const mutation of fixture.mutations) applyMutation(document, mutation);
    const result = validateSceneSpec(document);
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
    const result = validateSceneSpec(await readJson(absolutePath));
    process.stdout.write(`${result.valid ? 'VALID' : 'INVALID'} ${inputPath}\n`);
    for (const error of result.errors) process.stdout.write(`  ${error.code} ${error.path}: ${error.message}\n`);
    if (!result.valid) failed = true;
  }
  if (failed) process.exitCode = 1;
}

const inputPaths = process.argv.slice(2);
if (inputPaths.length > 0) await validateFiles(inputPaths);
else await runFixtureSuite();
