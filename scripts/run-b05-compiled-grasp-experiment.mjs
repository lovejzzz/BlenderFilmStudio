import { access, mkdir, readFile, writeFile } from 'node:fs/promises';
import { constants } from 'node:fs';
import { createHash } from 'node:crypto';
import { spawn } from 'node:child_process';
import { relative, resolve, sep } from 'node:path';
import { compileBuildPlan } from './compile-build-plan.mjs';
import { readJson, repositoryRoot } from './lib/scene-spec.mjs';
import { validateSceneSpecV04 } from './lib/scene-spec-v04.mjs';

const scenePath = resolve(repositoryRoot, 'specs/benchmarks/B05.scene.json');
const graspPath = resolve(repositoryRoot, 'specs/benchmarks/B05.grasp.json');
const experimentRoot = resolve(repositoryRoot, 'experiments/grasp-v0-2');
const runRoot = resolve(experimentRoot, 'runs/formal');
const planPath = resolve(experimentRoot, 'B05.build-plan.json');
const evaluationPath = resolve(experimentRoot, 'B05.compiled-evaluation.json');
const resultPath = resolve(experimentRoot, 'results.json');
const compilerScript = resolve(repositoryRoot, 'blender/compile_scene.py');
const evaluatorScript = resolve(repositoryRoot, 'blender/evaluate_b05_compiled_grasp.py');
const visibilityScript = resolve(repositoryRoot, 'blender/evaluate_b05_visibility.py');
const mutatorScript = resolve(repositoryRoot, 'blender/mutate_b05_negative.py');
const ocio = resolve(repositoryRoot, 'color/ocio/cg-config-v4.0.0_aces-v2.0_ocio-v2.5.ocio');
const digest = value => createHash('sha256').update(value).digest('hex');
const repoRelative = path => relative(repositoryRoot, path).split(sep).join('/');

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

const compileScene = (blender, plan, output, expectSuccess = true) => run(blender, ['--background', '--factory-startup', '--python-exit-code', '1', '--python', compilerScript, '--', '--plan', plan, '--repository-root', repositoryRoot, '--output-dir', output], { expectSuccess });
const evaluateScene = (blender, blend, plan, output, expectSuccess = true) => run(blender, ['--background', '--python-exit-code', '1', blend, '--python', evaluatorScript, '--', '--plan', plan, '--output', output], { expectSuccess });
const evaluateVisibility = (blender, blend, output, expectSuccess = true) => run(blender, ['--background', '--python-exit-code', '1', blend, '--python', visibilityScript, '--', '--output', output], { expectSuccess });

async function writeGraspFixture(baseScene, baseGrasp, id, mutate) {
  const root = resolve(runRoot, id);
  await mkdir(root, { recursive: true });
  const grasp = structuredClone(baseGrasp);
  mutate(grasp);
  const graspFile = resolve(root, 'fixture.grasp.json');
  const graspBytes = `${JSON.stringify(grasp, null, 2)}\n`;
  await writeFile(graspFile, graspBytes);
  const scene = structuredClone(baseScene);
  scene.grasps[0].graspSpecUri = repoRelative(graspFile);
  scene.grasps[0].graspSpecSha256 = digest(graspBytes);
  const sceneFile = resolve(root, 'fixture.scene.json');
  await writeFile(sceneFile, `${JSON.stringify(scene, null, 2)}\n`);
  return { root, sceneFile };
}

async function planGraspNegative(baseScene, baseGrasp, id, mutate, expectedText) {
  const fixture = await writeGraspFixture(baseScene, baseGrasp, id, mutate);
  let error = '';
  try { await compileBuildPlan(fixture.sceneFile); } catch (caught) { error = caught.message; }
  return { id, layer: 'BUILD_PLAN', rejected: error.includes(expectedText), expected: expectedText, observed: error.split('\n').find(Boolean) ?? '' };
}

async function blenderGraspNegative(blender, baseScene, baseGrasp, id, mutate, expectedText) {
  const fixture = await writeGraspFixture(baseScene, baseGrasp, id, mutate);
  const planFile = resolve(fixture.root, 'fixture.build-plan.json');
  const plan = await compileBuildPlan(fixture.sceneFile);
  await writeFile(planFile, `${JSON.stringify(plan, null, 2)}\n`);
  const result = await compileScene(blender, planFile, resolve(fixture.root, 'build'), false);
  return { id, layer: 'BLENDER_COMPILE', rejected: result.code !== 0 && result.output.includes(expectedText), expected: expectedText, observed: result.output.split('\n').find(line => line.includes('BFS_COMPILE_ERROR')) ?? `exit ${result.code}` };
}

async function permissionNegative(baseScene) {
  const root = resolve(runRoot, 'N05_UNAUTHORIZED_GRASP');
  await mkdir(root, { recursive: true });
  const scene = structuredClone(baseScene);
  scene.security.allowedOperations = scene.security.allowedOperations.filter(value => value !== 'CREATE_GRASP');
  const sceneFile = resolve(root, 'fixture.scene.json');
  await writeFile(sceneFile, `${JSON.stringify(scene, null, 2)}\n`);
  let error = '';
  try { await compileBuildPlan(sceneFile); } catch (caught) { error = caught.message; }
  const expected = 'does not authorize required operations: CREATE_GRASP';
  return { id: 'N05_UNAUTHORIZED_GRASP', layer: 'BUILD_PLAN', rejected: error.includes(expected), expected, observed: error.split('\n').find(Boolean) ?? '' };
}

async function runtimeNegative(blender, id, mutation, expectedCheck, positiveBlend) {
  const root = resolve(runRoot, id);
  await mkdir(root, { recursive: true });
  const blend = resolve(root, 'fixture.blend');
  const output = resolve(root, 'evaluation.json');
  await run(blender, ['--background', '--python-exit-code', '1', positiveBlend, '--python', mutatorScript, '--', '--plan', planPath, '--mutation', mutation, '--output', blend]);
  const result = await evaluateScene(blender, blend, planPath, output, false);
  const evaluation = await readJson(output);
  const observed = evaluation.checks.find(item => item.id === expectedCheck) ?? null;
  return { id, layer: 'RUNTIME_EVALUATION', rejected: result.code !== 0 && observed?.pass === false, expected: `${expectedCheck}=false`, observed };
}

const blender = await findBlender();
await mkdir(runRoot, { recursive: true });
const [scene, grasp] = await Promise.all([readJson(scenePath), readJson(graspPath)]);
const validation = validateSceneSpecV04(scene);
if (!validation.valid) throw new Error(`B05 SceneSpec v0.4 is invalid: ${JSON.stringify(validation.errors)}`);
const plan = await compileBuildPlan(scenePath);
await writeFile(planPath, `${JSON.stringify(plan, null, 2)}\n`);

const cleanBuilds = [];
for (const label of ['run-a', 'run-b']) {
  const root = resolve(runRoot, label);
  await compileScene(blender, planPath, root);
  const manifest = await readJson(resolve(root, 'scene.manifest.json'));
  cleanBuilds.push({ label, structureHash: manifest.structureHash, blendSha256: digest(await readFile(resolve(root, 'scene.blend'))) });
}
const positiveBlend = resolve(runRoot, 'run-a/scene.blend');
await evaluateScene(blender, positiveBlend, planPath, evaluationPath);
const evaluation = await readJson(evaluationPath);
const visibilityPath = resolve(experimentRoot, 'B05.visibility.json');
await evaluateVisibility(blender, positiveBlend, visibilityPath);
const visibility = await readJson(visibilityPath);

const negatives = [
  await planGraspNegative(scene, grasp, 'N01_GENERIC_LIMIT_SOURCE', document => { document.solverPolicy.jointLimitSource = 'GENERIC_LIMITS'; }, 'GraspSpec GRASP_B05_TWO_FINGER validation failed'),
  await planGraspNegative(scene, grasp, 'N02_INVALID_JOINT_RANGE', document => { document.fingerChains[0].bones[0].minimumDeg = 66; }, 'SEM_JOINT_RANGE'),
  await planGraspNegative(scene, grasp, 'N03_PARALLEL_NORMALS', document => { document.contactPatches[1].targetNormalLocal = [-1, 0, 0]; }, 'SEM_OPPOSING_NORMALS'),
  await blenderGraspNegative(blender, scene, grasp, 'N04_MISSING_FINGER_BONE', document => { document.fingerChains[1].bones[1].boneSemantic = 'MISSING_DISTAL'; }, 'Grasp finger bone is missing'),
  await permissionNegative(scene),
  await runtimeNegative(blender, 'N06_STRETCH_ENABLED', 'STRETCH', 'B05_C02_IK_CONTRACT', positiveBlend),
  await runtimeNegative(blender, 'N07_CONTACT_DISABLED', 'CONTACT_DISABLED', 'B05_C07_ACTIVE_CONTACTS', positiveBlend),
  await runtimeNegative(blender, 'N08_TARGET_DRIFT', 'TARGET_DRIFT', 'B05_C10_HOLD_DRIFT', positiveBlend),
];

const firstRun = await readJson(resolve(experimentRoot, 'B05.first-run-falsified-evaluation.json'));
const structureHashesEqual = cleanBuilds[0].structureHash === cleanBuilds[1].structureHash;
const report = {
  documentType: 'BFS_B05_COMPILED_GRASP_EXPERIMENT',
  version: '0.1.0',
  executedAtUtc: new Date().toISOString(),
  environment: { blender: evaluation.environment.blender, platform: `${process.platform}-${process.arch}`, node: process.version },
  sceneSpec: { version: scene.specVersion, valid: validation.valid, shot: scene.shot.id },
  buildPlan: { version: plan.planVersion, hash: plan.planHash },
  firstRunFalsification: {
    buildPlanHash: firstRun.buildPlan.hash,
    maximumSeparationM: firstRun.measurements.holdSurfaceSeparationMaximumM,
    failedChecks: firstRun.checks.filter(item => !item.pass).map(item => item.id),
    correction: 'Technical finger chain length increased from 0.12 m to 0.18 m; acceptance thresholds were unchanged.',
  },
  cleanBuilds: { runs: cleanBuilds, structureHashesEqual, blendSha256Equal: cleanBuilds[0].blendSha256 === cleanBuilds[1].blendSha256 },
  evaluation: { allMachineChecksPassed: evaluation.allMachineChecksPassed, measurements: evaluation.measurements, checks: evaluation.checks },
  negativeTests: negatives,
  allAutomatedChecksPassed: structureHashesEqual && evaluation.allMachineChecksPassed && visibility.visibilityGatePassed && negatives.every(item => item.rejected),
  visibility: { status: visibility.visibilityGatePassed ? 'PASS' : 'FAIL', summaries: visibility.summaries, method: visibility.method },
  humanReview: evaluation.humanReview,
  experimentComplete: false,
  explicitNonClaims: evaluation.explicitNonClaims,
};
await writeFile(resultPath, `${JSON.stringify(report, null, 2)}\n`);
process.stdout.write(`BFS_B05_COMPILED_EXPERIMENT ${report.allAutomatedChecksPassed ? 'AUTOMATION_PASS' : 'FAIL'} ${negatives.filter(item => item.rejected).length}/${negatives.length} negatives; visibility ${report.visibility.status}; human ${report.humanReview.status}\n`);
if (!report.allAutomatedChecksPassed) process.exitCode = 1;
