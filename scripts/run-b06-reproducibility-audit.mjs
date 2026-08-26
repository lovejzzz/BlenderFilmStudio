import { access, mkdir, readFile, writeFile } from 'node:fs/promises';
import { constants } from 'node:fs';
import { spawn } from 'node:child_process';
import { resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';

const experimentRoot = resolve(repositoryRoot, 'experiments/physics-v0-1');
const runRoot = resolve(experimentRoot, 'runs/repro-audit');
const builder = resolve(repositoryRoot, 'blender/build_b06_physics_spike.py');
const evaluator = resolve(repositoryRoot, 'blender/evaluate_b06_physics_spike.py');

async function findBlender() {
  const candidates = [process.env.BLENDER_BIN, '/Applications/Blender.app/Contents/MacOS/Blender', 'blender'].filter(Boolean);
  for (const candidate of candidates) {
    if (candidate === 'blender') return candidate;
    try { await access(candidate, constants.X_OK); return candidate; } catch {}
  }
  throw new Error('Blender executable not found; set BLENDER_BIN');
}

function run(command, args) {
  return new Promise((resolvePromise, reject) => {
    const child = spawn(command, args, { cwd: repositoryRoot, stdio: ['ignore', 'pipe', 'pipe'] });
    let output = '';
    child.stdout.on('data', chunk => { output += chunk; });
    child.stderr.on('data', chunk => { output += chunk; });
    child.on('error', reject);
    child.on('close', code => code === 0 ? resolvePromise(output) : reject(new Error(output)));
  });
}

function divergence(left, right, frameStart = 1, frameEnd = 132) {
  let maximumM = 0;
  let frame = 0;
  for (let index = frameStart - 1; index < frameEnd; index += 1) {
    const distance = Math.hypot(...left[index].propCentreWorldM.map((value, axis) => value - right[index].propCentreWorldM[axis]));
    if (distance > maximumM) { maximumM = distance; frame = index + 1; }
  }
  return { maximumM, frame };
}

const blender = await findBlender();
await mkdir(runRoot, { recursive: true });
const runs = [];
for (let index = 1; index <= 10; index += 1) {
  const label = `run-${String(index).padStart(2, '0')}`;
  const root = resolve(runRoot, label);
  await mkdir(root, { recursive: true });
  const blend = resolve(root, 'scene.blend');
  const manifestPath = resolve(root, 'manifest.json');
  const evaluationPath = resolve(root, 'evaluation.json');
  await run(blender, ['--background', '--factory-startup', '--python-exit-code', '1', '--python', builder, '--', '--output', blend, '--manifest', manifestPath, '--variant', 'POSITIVE']);
  await run(blender, ['--background', '--python-exit-code', '1', blend, '--python', evaluator, '--', '--output', evaluationPath]);
  runs.push({ label, manifest: JSON.parse(await readFile(manifestPath, 'utf8')), evaluation: JSON.parse(await readFile(evaluationPath, 'utf8')) });
}

const comparisons = [];
for (let left = 0; left < runs.length; left += 1) for (let right = left + 1; right < runs.length; right += 1) {
  comparisons.push({
    left: runs[left].label, right: runs[right].label,
    full: divergence(runs[left].evaluation.trajectory, runs[right].evaluation.trajectory),
    hold: divergence(runs[left].evaluation.trajectory, runs[right].evaluation.trajectory, 49, 108),
    release: divergence(runs[left].evaluation.trajectory, runs[right].evaluation.trajectory, 109, 132),
  });
}
const maximum = (field) => comparisons.reduce((best, item) => item[field].maximumM > best.maximumM ? { ...item[field], pair: [item.left, item.right] } : best, { maximumM: 0, frame: 0, pair: [] });
const structureHashes = [...new Set(runs.map(item => item.manifest.structureHash))];
const report = {
  documentType: 'BFS_B06_REPRODUCIBILITY_AUDIT', version: '0.1.0', executedAtUtc: new Date().toISOString(),
  independentRuns: runs.length, pairwiseComparisons: comparisons.length,
  allIndividualPositiveGatesPassed: runs.every(item => item.evaluation.passed),
  uniqueStructureHashes: structureHashes,
  maximumFullTrajectoryDivergence: maximum('full'),
  maximumHoldDivergence: maximum('hold'),
  maximumReleaseDivergence: maximum('release'),
  trajectoryThresholdM: 0.001,
  reproducibilityGatePassed: structureHashes.length === 1 && maximum('full').maximumM <= 0.001,
  comparisons,
  explicitNonClaims: ['A finite repeated-run audit cannot prove determinism for every platform, thread schedule, or Blender build.'],
};
await writeFile(resolve(experimentRoot, 'B06.reproducibility-audit.json'), `${JSON.stringify(report, null, 2)}\n`);
const resultsPath = resolve(experimentRoot, 'results.json');
const results = JSON.parse(await readFile(resultsPath, 'utf8'));
results.repeatedReproducibilityAudit = {
  independentRuns: report.independentRuns, pairwiseComparisons: report.pairwiseComparisons,
  maximumFullTrajectoryDivergence: report.maximumFullTrajectoryDivergence,
  maximumHoldDivergence: report.maximumHoldDivergence,
  maximumReleaseDivergence: report.maximumReleaseDivergence,
  reproducibilityGatePassed: report.reproducibilityGatePassed,
};
results.allAutomatedChecksPassed = results.allAutomatedChecksPassed && report.reproducibilityGatePassed;
await writeFile(resultsPath, `${JSON.stringify(results, null, 2)}\n`);
process.stdout.write(`BFS_B06_REPRO_AUDIT ${report.reproducibilityGatePassed ? 'PASS' : 'FAIL'} ${runs.length} runs ${comparisons.length} pairs max=${report.maximumFullTrajectoryDivergence.maximumM}\n`);
if (!report.reproducibilityGatePassed) process.exitCode = 1;
