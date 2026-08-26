import { resolve } from 'node:path';
import { readJson } from './lib/scene-spec.mjs';
import { validateSceneSpecV02 } from './lib/scene-spec-v02.mjs';

const inputs = process.argv.slice(2);
if (inputs.length === 0) inputs.push('specs/benchmarks/B03.scene.json');
let failed = false;
for (const input of inputs) {
  const result = validateSceneSpecV02(await readJson(resolve(process.cwd(), input)));
  process.stdout.write(`${result.valid ? 'VALID' : 'INVALID'} ${input}\n`);
  for (const error of result.errors) process.stdout.write(`  ${error.code} ${error.path}: ${error.message}\n`);
  if (!result.valid) failed = true;
}
if (failed) process.exitCode = 1;
