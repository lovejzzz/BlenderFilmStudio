import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { validateSceneSpecV04 } from './lib/scene-spec-v04.mjs';

const args = process.argv.slice(2);
const input = args[0];
if (!input) throw new Error('Usage: node scripts/validate-scene-spec-v04.mjs <SceneSpec.json>');
const path = resolve(process.cwd(), input);
const document = JSON.parse(await readFile(path, 'utf8'));
const result = validateSceneSpecV04(document);
if (!result.valid) {
  process.stderr.write(`${JSON.stringify(result, null, 2)}\n`);
  process.exitCode = 1;
} else process.stdout.write(`SCENE_SPEC_V04_OK ${path}\n`);
