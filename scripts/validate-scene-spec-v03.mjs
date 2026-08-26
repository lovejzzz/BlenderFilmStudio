import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { validateSceneSpecV03 } from './lib/scene-spec-v03.mjs';

const input = process.argv[2];
if (!input) throw new Error('Usage: node scripts/validate-scene-spec-v03.mjs <SceneSpec.json>');
const document = JSON.parse(await readFile(resolve(process.cwd(), input), 'utf8'));
const result = validateSceneSpecV03(document);
if (!result.valid) {
  process.stderr.write(`${JSON.stringify(result, null, 2)}\n`);
  process.exitCode = 1;
} else {
  process.stdout.write(`SCENE_SPEC_V03_OK ${input}\n`);
}
