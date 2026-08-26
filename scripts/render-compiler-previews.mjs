import { spawn } from 'node:child_process';
import { mkdir } from 'node:fs/promises';
import { resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';

const blender = process.env.BLENDER_BIN || '/Applications/Blender.app/Contents/MacOS/Blender';
const renderer = resolve(repositoryRoot, 'blender/render_preview.py');
const publicRoot = resolve(repositoryRoot, 'public/compiler-v0-1');
const ocioConfig = resolve(repositoryRoot, 'color/ocio/cg-config-v4.0.0_aces-v2.0_ocio-v2.5.ocio');

const previews = [
  { benchmark: 'B01', frame: 1 },
  { benchmark: 'B02', frame: 1 },
  { benchmark: 'B02', frame: 72 },
  { benchmark: 'B02', frame: 144 },
];

function run(command, args) {
  return new Promise((resolvePromise, reject) => {
    const child = spawn(command, args, { cwd: repositoryRoot, env: { ...process.env, OCIO: ocioConfig }, stdio: 'inherit' });
    child.on('error', reject);
    child.on('close', code => code === 0 ? resolvePromise() : reject(new Error(`Preview process failed with exit code ${code}`)));
  });
}

await mkdir(publicRoot, { recursive: true });
for (const preview of previews) {
  const frameLabel = String(preview.frame).padStart(4, '0');
  const blendPath = resolve(repositoryRoot, `experiments/compiler-v0-1/runs/${preview.benchmark}/run-a/scene.blend`);
  const outputPath = resolve(publicRoot, `${preview.benchmark}-frame-${frameLabel}.png`);
  await run(blender, [
    '--background', blendPath,
    '--python', renderer,
    '--',
    '--frame', String(preview.frame),
    '--output', outputPath,
  ]);
}
