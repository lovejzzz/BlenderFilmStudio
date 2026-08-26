import { access, mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { constants } from 'node:fs';
import { createHash } from 'node:crypto';
import { spawn } from 'node:child_process';
import { resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { compileBuildPlan } from './compile-build-plan.mjs';

const experimentRoot = resolve(repositoryRoot, 'experiments/trajectory-v0-2');
const runRoot = resolve(experimentRoot, 'runs');
const sourceScenePath = resolve(repositoryRoot, 'specs/benchmarks/B08.scene.json');
const compiler = resolve(repositoryRoot, 'blender/compile_scene.py');
const evaluator = resolve(repositoryRoot, 'blender/evaluate_b08_compiled_trajectory.py');
const mutator = resolve(repositoryRoot, 'blender/mutate_b08_compiled_scene.py');
const negativeAssetMutator = resolve(repositoryRoot, 'blender/mutate_b08_negative_asset.py');
const ocio = resolve(repositoryRoot, 'color/ocio/cg-config-v4.0.0_aces-v2.0_ocio-v2.5.ocio');
const negativeAssetPath = resolve(repositoryRoot, 'library/props/B08-negative-missing-target.blend');
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
    const child = spawn(command, args, { cwd: repositoryRoot, env: { ...process.env, OCIO: ocio }, stdio: ['ignore', 'pipe', 'pipe'] });
    let output = '';
    child.stdout.on('data', chunk => { output += chunk; });
    child.stderr.on('data', chunk => { output += chunk; });
    child.on('error', reject);
    child.on('close', code => {
      const result = { code, output };
      if (expectSuccess && code !== 0) reject(new Error(output)); else resolvePromise(result);
    });
  });
}

const serialize = value => `${JSON.stringify(value, null, 2)}\n`;
const blender = await findBlender();
await rm(runRoot, { recursive: true, force: true });
await mkdir(runRoot, { recursive: true });
const sourceScene = JSON.parse(await readFile(sourceScenePath, 'utf8'));

async function emitPlan(scene, id) {
  const root = resolve(runRoot, id);
  await mkdir(root, { recursive: true });
  const scenePath = resolve(root, 'fixture.scene.json');
  await writeFile(scenePath, serialize(scene));
  const plan = await compileBuildPlan(scenePath);
  const planPath = resolve(root, 'build-plan.json');
  await writeFile(planPath, serialize(plan));
  return { root, scenePath, planPath, plan };
}

async function compileScene(planPath, root, expectSuccess = true) {
  return run(blender, ['--background', '--factory-startup', '--python-exit-code', '1', '--python', compiler, '--', '--plan', planPath, '--repository-root', repositoryRoot, '--output-dir', root], { expectSuccess });
}

async function evaluateScene(blendPath, planPath, outputPath, expectSuccess = true) {
  return run(blender, ['--background', blendPath, '--python-exit-code', '1', '--python', evaluator, '--', '--plan', planPath, '--output', outputPath], { expectSuccess });
}

async function buildPlanNegative(id, mutate, expected) {
  const scene = structuredClone(sourceScene);
  const root = resolve(runRoot, id);
  await mkdir(root, { recursive: true });
  await mutate(scene, root);
  const path = resolve(root, 'fixture.scene.json');
  await writeFile(path, serialize(scene));
  try {
    await compileBuildPlan(path);
    return { id, layer: 'BUILD_PLAN', rejected: false, expected, observed: 'BuildPlan unexpectedly emitted' };
  } catch (error) {
    return { id, layer: 'BUILD_PLAN', rejected: String(error.message).includes(expected), expected, observed: String(error.message).split('\n')[0] };
  }
}

async function trajectoryFixture(scene, root, mutate) {
  const original = JSON.parse(await readFile(resolve(repositoryRoot, scene.trajectories[0].trajectorySpecUri), 'utf8'));
  mutate(original);
  const path = resolve(root, 'fixture.trajectory.json');
  const bytes = serialize(original);
  await writeFile(path, bytes);
  scene.trajectories[0].trajectorySpecUri = path.slice(repositoryRoot.length + 1);
  scene.trajectories[0].trajectorySpecSha256 = digest(bytes);
}

const firstPlan = await compileBuildPlan(sourceScenePath);
const secondPlan = await compileBuildPlan(sourceScenePath);
const planDeterministic = serialize(firstPlan) === serialize(secondPlan);
const positivePlanPath = resolve(experimentRoot, 'B08.build-plan.json');
await writeFile(positivePlanPath, serialize(firstPlan));

const builds = [];
for (const label of ['positive-a', 'positive-b']) {
  const root = resolve(runRoot, label);
  await mkdir(root, { recursive: true });
  await compileScene(positivePlanPath, root);
  const blendPath = resolve(root, 'scene.blend');
  const manifestPath = resolve(root, 'scene.manifest.json');
  const evaluationPath = resolve(root, 'evaluation.json');
  await evaluateScene(blendPath, positivePlanPath, evaluationPath);
  builds.push({
    label,
    root,
    blendPath,
    manifest: JSON.parse(await readFile(manifestPath, 'utf8')),
    evaluation: JSON.parse(await readFile(evaluationPath, 'utf8')),
    blendSha256: digest(await readFile(blendPath)),
  });
}

const negatives = [
  await buildPlanNegative('N01_TRAJECTORY_HASH', scene => { scene.trajectories[0].trajectorySpecSha256 = '0'.repeat(64); }, 'TrajectorySpec TRAJECTORY_B07_CANONICAL hash mismatch'),
  await buildPlanNegative('N02_SOURCE_HASH', (scene, root) => trajectoryFixture(scene, root, trajectory => { trajectory.source.evaluationSha256 = '0'.repeat(64); }), 'source evaluation hash mismatch'),
  await buildPlanNegative('N03_MISSING_AUTHORITY', scene => { scene.security.allowedOperations = scene.security.allowedOperations.filter(item => item !== 'CREATE_TRAJECTORY_REPLAY'); }, 'does not authorize required operations: CREATE_TRAJECTORY_REPLAY'),
  await buildPlanNegative('N04_TARGET_MISMATCH', scene => { scene.trajectories[0].objectRef = 'B08_OTHER_PROP'; }, 'identity or target does not match SceneSpec binding'),
  await buildPlanNegative('N06_MISSING_SAMPLE', (scene, root) => trajectoryFixture(scene, root, trajectory => { trajectory.samples.splice(50, 1); }), 'TrajectorySpec TRAJECTORY_B07_CANONICAL validation failed'),
];

await run(blender, ['--background', resolve(repositoryRoot, 'library/props/B08-prop.blend'), '--python-exit-code', '1', '--python', negativeAssetMutator, '--', '--output', negativeAssetPath]);
const missingTargetScene = structuredClone(sourceScene);
missingTargetScene.assets[0].uri = 'library/props/B08-negative-missing-target.blend';
missingTargetScene.assets[0].sha256 = digest(await readFile(negativeAssetPath));
const missingTargetFixture = await emitPlan(missingTargetScene, 'N05_MISSING_TARGET');
const missingTargetCompile = await compileScene(missingTargetFixture.planPath, resolve(missingTargetFixture.root, 'output'), false);
negatives.splice(4, 0, {
  id: 'N05_MISSING_TARGET', layer: 'BLENDER_COMPILE',
  rejected: missingTargetCompile.code !== 0 && missingTargetCompile.output.includes('Trajectory target object is missing'),
  expected: 'Trajectory target object is missing',
  observed: missingTargetCompile.output.split('\n').find(line => line.includes('BFS_COMPILE_ERROR')) ?? `exit ${missingTargetCompile.code}`,
});
await rm(negativeAssetPath, { force: true });

async function runtimeNegative(id, mutation, expectedCheck) {
  const root = resolve(runRoot, id);
  await mkdir(root, { recursive: true });
  const blendPath = resolve(root, 'fixture.blend');
  const reportPath = resolve(root, 'evaluation.json');
  await run(blender, ['--background', builds[0].blendPath, '--python-exit-code', '1', '--python', mutator, '--', '--mutation', mutation, '--output', blendPath]);
  const evaluation = await evaluateScene(blendPath, positivePlanPath, reportPath, false);
  const report = JSON.parse(await readFile(reportPath, 'utf8'));
  const observed = report.checks.find(item => item.id === expectedCheck) ?? null;
  return { id, layer: 'RUNTIME_EVALUATION', rejected: evaluation.code !== 0 && observed?.pass === false, expected: `${expectedCheck}=false with non-zero exit`, observed };
}

negatives.push(await runtimeNegative('N07_KEY_MUTATION', 'KEY_MUTATION', 'B08_C04_POSITION_REPLAY'));
negatives.push(await runtimeNegative('N08_RIGID_BODY', 'RIGID_BODY', 'B08_C06_NO_RUNTIME_SHORTCUT'));

const structureHashesEqual = builds[0].manifest.structureHash === builds[1].manifest.structureHash;
const evaluationReportsEqual = serialize(builds[0].evaluation) === serialize(builds[1].evaluation);
const automatedPassed = planDeterministic && structureHashesEqual && evaluationReportsEqual && builds.every(item => item.evaluation.passed) && negatives.length === 8 && negatives.every(item => item.rejected);
const result = {
  documentType: 'BFS_B08_TRAJECTORY_COMPILER_EXPERIMENT', version: '0.1.0', executedAtUtc: new Date().toISOString(),
  environment: { blender: builds[0].evaluation.environment.blender, buildHash: builds[0].evaluation.environment.buildHash, platform: `${process.platform}-${process.arch}`, node: process.version },
  buildPlan: { uri: 'experiments/trajectory-v0-2/B08.build-plan.json', planHash: firstPlan.planHash, deterministic: planDeterministic, compilerVersion: firstPlan.plan.compiler.version },
  trajectory: { uri: firstPlan.plan.trajectories[0].trajectorySpecUri, sha256: firstPlan.plan.trajectories[0].verifiedTrajectorySpecSha256, sourceEvaluationSha256: firstPlan.plan.trajectories[0].verifiedSourceEvaluationSha256, selectionStatus: firstPlan.plan.trajectories[0].trajectorySpec.selectionStatus },
  cleanBuilds: { runs: builds.map(item => ({ label: item.label, structureHash: item.manifest.structureHash, blendSha256: item.blendSha256 })), structureHashesEqual, blendSha256Equal: builds[0].blendSha256 === builds[1].blendSha256, evaluationReportsEqual },
  evaluation: { passed: builds[0].evaluation.passed, measurements: builds[0].evaluation.measurements, checks: builds[0].evaluation.checks },
  negativeTests: negatives,
  allAutomatedChecksPassed: automatedPassed,
  formalB08Complete: automatedPassed,
  sourceSolveHumanApproved: false,
  remainingDependency: 'source-solve visual and authentic human approval',
  explicitNonClaims: builds[0].evaluation.explicitNonClaims,
};
await writeFile(resolve(experimentRoot, 'B08.manifest.json'), serialize(builds[0].manifest));
await writeFile(resolve(experimentRoot, 'B08.evaluation.json'), serialize(builds[0].evaluation));
await writeFile(resolve(experimentRoot, 'results.json'), serialize(result));
process.stdout.write(`BFS_B08_TRAJECTORY_COMPILER ${automatedPassed ? 'AUTOMATION_PASS' : 'FAIL'} ${negatives.filter(item => item.rejected).length}/${negatives.length} negatives; formal B08 ${result.formalB08Complete ? 'TRUE' : 'FALSE'}\n`);
if (!automatedPassed) process.exitCode = 1;
