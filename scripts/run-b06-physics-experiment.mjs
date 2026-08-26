import { access, mkdir, readFile, writeFile } from 'node:fs/promises';
import { constants } from 'node:fs';
import { createHash } from 'node:crypto';
import { spawn } from 'node:child_process';
import { resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';

const experimentRoot = resolve(repositoryRoot, 'experiments/physics-v0-1');
const runRoot = resolve(experimentRoot, 'runs');
const builder = resolve(repositoryRoot, 'blender/build_b06_physics_spike.py');
const evaluator = resolve(repositoryRoot, 'blender/evaluate_b06_physics_spike.py');
const digest = value => createHash('sha256').update(value).digest('hex');

async function findBlender() {
  const candidates = [process.env.BLENDER_BIN, '/Applications/Blender.app/Contents/MacOS/Blender', 'blender'].filter(Boolean);
  for (const candidate of candidates) {
    if (candidate === 'blender') return candidate;
    try { await access(candidate, constants.X_OK); return candidate; } catch {}
  }
  throw new Error('Blender executable not found; set BLENDER_BIN');
}

function run(command, args, { expectSuccess = true } = {}) {
  return new Promise((resolvePromise, reject) => {
    const child = spawn(command, args, { cwd: repositoryRoot, stdio: ['ignore', 'pipe', 'pipe'] });
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', chunk => { stdout += chunk; });
    child.stderr.on('data', chunk => { stderr += chunk; });
    child.on('error', reject);
    child.on('close', code => {
      const result = { code, stdout, stderr, output: `${stdout}\n${stderr}` };
      if (expectSuccess && code !== 0) reject(new Error(result.output));
      else resolvePromise(result);
    });
  });
}

async function buildAndEvaluate(blender, label, variant, expectEvaluationSuccess) {
  const root = resolve(runRoot, label);
  await mkdir(root, { recursive: true });
  const blend = resolve(root, 'scene.blend');
  const manifestPath = resolve(root, 'manifest.json');
  const evaluationPath = resolve(root, 'evaluation.json');
  await run(blender, ['--background', '--factory-startup', '--python-exit-code', '1', '--python', builder, '--', '--output', blend, '--manifest', manifestPath, '--variant', variant]);
  const evaluationRun = await run(blender, ['--background', '--python-exit-code', '1', blend, '--python', evaluator, '--', '--output', evaluationPath], { expectSuccess: expectEvaluationSuccess });
  return {
    label, variant, blend, manifestPath, evaluationPath, evaluationRun,
    manifest: JSON.parse(await readFile(manifestPath, 'utf8')),
    evaluation: JSON.parse(await readFile(evaluationPath, 'utf8')),
    blendSha256: digest(await readFile(blend)),
  };
}

function trajectoryDivergence(left, right) {
  let maximum = 0;
  let frame = 0;
  for (let index = 0; index < left.length; index += 1) {
    const distance = Math.hypot(...left[index].propCentreWorldM.map((value, axis) => value - right[index].propCentreWorldM[axis]));
    if (distance > maximum) { maximum = distance; frame = left[index].frame; }
  }
  return { maximumM: maximum, frame };
}

function trajectoryDivergenceWindow(left, right, frameStart, frameEnd) {
  return trajectoryDivergence(left.filter(item => item.frame >= frameStart && item.frame <= frameEnd), right.filter(item => item.frame >= frameStart && item.frame <= frameEnd));
}

const blender = await findBlender();
await mkdir(runRoot, { recursive: true });
const positiveA = await buildAndEvaluate(blender, 'positive-a', 'POSITIVE', true);
const positiveB = await buildAndEvaluate(blender, 'positive-b', 'POSITIVE', true);
const divergence = trajectoryDivergence(positiveA.evaluation.trajectory, positiveB.evaluation.trajectory);
const divergenceWindows = {
  closure: trajectoryDivergenceWindow(positiveA.evaluation.trajectory, positiveB.evaluation.trajectory, 1, 48),
  hold: trajectoryDivergenceWindow(positiveA.evaluation.trajectory, positiveB.evaluation.trajectory, 49, 108),
  release: trajectoryDivergenceWindow(positiveA.evaluation.trajectory, positiveB.evaluation.trajectory, 109, 132),
};

const negativeDefinitions = [
  ['N01_ZERO_FRICTION', 'B06_C04_VERTICAL_TRANSPORT'],
  ['N02_ONE_COLLIDER', 'B06_C04_VERTICAL_TRANSPORT'],
  ['N03_INSUFFICIENT_CLOSURE', 'B06_C04_VERTICAL_TRANSPORT'],
  ['N04_PROP_KINEMATIC', 'B06_C02_PROP_DYNAMIC'],
  ['N05_FORBIDDEN_PARENT', 'B06_C01_NO_SHORTCUT'],
  ['N06_FAST_TRANSPORT', 'B06_C11_COLLIDER_STEP'],
  ['N07_LARGE_MARGIN', 'B06_C10_COLLISION_MARGIN'],
  ['N08_LOW_SUBSTEPS', 'B06_C09_SOLVER_BUDGET'],
];
const negatives = [];
for (const [variant, expectedCheck] of negativeDefinitions) {
  const result = await buildAndEvaluate(blender, variant, variant, false);
  const observed = result.evaluation.checks.find(item => item.id === expectedCheck) ?? null;
  negatives.push({ id: variant, expectedCheck, rejected: result.evaluationRun.code !== 0 && observed?.pass === false, observed, allFailedChecks: result.evaluation.checks.filter(item => !item.pass).map(item => item.id) });
}

await writeFile(resolve(experimentRoot, 'B06.final-manifest.json'), `${JSON.stringify(positiveA.manifest, null, 2)}\n`);
await writeFile(resolve(experimentRoot, 'B06.final-evaluation.json'), `${JSON.stringify(positiveA.evaluation, null, 2)}\n`);
const structureHashesEqual = positiveA.manifest.structureHash === positiveB.manifest.structureHash;
const trajectoryReproducible = divergence.maximumM <= 0.001;
const report = {
  documentType: 'BFS_B06_PHYSICS_EXPERIMENT', version: '0.1.0', executedAtUtc: new Date().toISOString(),
  environment: { blender: positiveA.evaluation.environment.blender, platform: `${process.platform}-${process.arch}`, node: process.version },
  cleanBuilds: {
    runs: [positiveA, positiveB].map(item => ({ label: item.label, structureHash: item.manifest.structureHash, blendSha256: item.blendSha256, passed: item.evaluation.passed, measurements: item.evaluation.measurements })),
    structureHashesEqual, blendSha256Equal: positiveA.blendSha256 === positiveB.blendSha256,
    trajectoryMaximumDivergenceM: divergence.maximumM, trajectoryMaximumDivergenceFrame: divergence.frame, trajectoryDivergenceWindows: divergenceWindows, trajectoryReproducible,
  },
  firstRunFalsification: {
    evaluation: 'experiments/physics-v0-1/B06.evaluation.json',
    cause: '2 mm initial overlap and narrow equal-depth faces injected energy and allowed immediate edge escape.',
    observed: { verticalTransportM: -14.601222029, maximumHoldMidpointDriftM: 15.941267728, holdRotationChangeDeg: 162.96157903 },
  },
  intermediateReproducibilityFailure: {
    cause: 'A floor impact after release produced chaotic trajectory divergence despite identical structures and two individually passing trajectories.',
    maximumTrajectoryDivergenceM: 0.138790659,
    correction: 'The floor was moved outside the observation window and declared damping was increased; the protocol thresholds were unchanged.',
  },
  evaluation: { passed: positiveA.evaluation.passed, measurements: positiveA.evaluation.measurements, checks: positiveA.evaluation.checks },
  negativeTests: negatives,
  allAutomatedChecksPassed: positiveA.evaluation.passed && positiveB.evaluation.passed && structureHashesEqual && trajectoryReproducible && negatives.every(item => item.rejected),
  formalB06Complete: false,
  remainingGates: ['PhysicsSpec/SceneSpec/immutable BuildPlan integration', 'active-camera visibility', 'authentic independent human review'],
  explicitNonClaims: positiveA.evaluation.explicitNonClaims,
};
await writeFile(resolve(experimentRoot, 'results.json'), `${JSON.stringify(report, null, 2)}\n`);
process.stdout.write(`BFS_B06_PHYSICS_EXPERIMENT ${report.allAutomatedChecksPassed ? 'AUTOMATION_PASS' : 'FAIL'} ${negatives.filter(item => item.rejected).length}/${negatives.length} negatives; formal B06 ${report.formalB06Complete ? 'TRUE' : 'FALSE'}\n`);
if (!report.allAutomatedChecksPassed) process.exitCode = 1;
