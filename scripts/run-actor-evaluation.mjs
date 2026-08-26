import { access } from 'node:fs/promises';
import { constants } from 'node:fs';
import { spawn } from 'node:child_process';
import { resolve } from 'node:path';

const repositoryRoot = resolve(import.meta.dirname, '..');
const evaluator = resolve(repositoryRoot, 'blender/evaluate_actor_performance.py');

async function findBlender() {
  const candidates = [process.env.BLENDER_BIN, '/Applications/Blender.app/Contents/MacOS/Blender', 'blender'].filter(Boolean);
  for (const candidate of candidates) {
    if (candidate === 'blender') return candidate;
    try {
      await access(candidate, constants.X_OK);
      return candidate;
    } catch {}
  }
  throw new Error('Blender executable not found; set BLENDER_BIN');
}

const blender = await findBlender();
const child = spawn(blender, [
  '--background', '--factory-startup', '--python', evaluator, '--',
  '--spec', 'specs/benchmarks/B03.actor.json',
  '--repository-root', repositoryRoot,
  '--output', 'experiments/actor-v0-1/performance-evaluation.json',
], { cwd: repositoryRoot, stdio: 'inherit' });

child.on('error', error => {
  console.error(error);
  process.exitCode = 1;
});
child.on('close', code => {
  process.exitCode = code ?? 1;
});
