import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { validateSceneSpecV05 } from './lib/scene-spec-v05.mjs';

const input = process.argv[2];
if (!input) throw new Error('Usage: node scripts/validate-scene-spec-v05.mjs <SceneSpec.json>');
const path = resolve(process.cwd(), input);
const document = JSON.parse(await readFile(path, 'utf8'));
const result = validateSceneSpecV05(document);
if (!result.valid) {
  process.stderr.write(`${JSON.stringify(result, null, 2)}\n`);
  process.exitCode = 1;
} else process.stdout.write(`SCENE_SPEC_V05_OK ${path}\n`);
