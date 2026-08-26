import { access, mkdir, readFile, writeFile } from 'node:fs/promises';
import { constants } from 'node:fs';
import { createHash } from 'node:crypto';
import { spawn } from 'node:child_process';
import { resolve } from 'node:path';
import { compileBuildPlan } from './compile-build-plan.mjs';
import { readJson, repositoryRoot } from './lib/scene-spec.mjs';
import { validateSceneSpecV03 } from './lib/scene-spec-v03.mjs';

const scenePath = resolve(repositoryRoot, 'specs/benchmarks/B04.scene.json');
const experimentRoot = resolve(repositoryRoot, 'experiments/contact-v0-1');
const runRoot = resolve(experimentRoot, 'runs');
const planPath = resolve(experimentRoot, 'B04.build-plan.json');
const evaluationPath = resolve(experimentRoot, 'B04.contact-evaluation.json');
const resultPath = resolve(experimentRoot, 'results.json');
const compilerScript = resolve(repositoryRoot, 'blender/compile_scene.py');
const evaluatorScript = resolve(repositoryRoot, 'blender/evaluate_b04_contact_scene.py');
const ocio = resolve(repositoryRoot, 'color/ocio/cg-config-v4.0.0_aces-v2.0_ocio-v2.5.ocio');

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

const digest = value => createHash('sha256').update(value).digest('hex');

async function compileScene(blender, plan, outputDir, expectSuccess = true) {
  return run(blender, ['--background', '--factory-startup', '--python-exit-code', '1', '--python', compilerScript, '--', '--plan', plan, '--repository-root', repositoryRoot, '--output-dir', outputDir], { expectSuccess });
}

async function evaluateScene(blender, blend, plan, output, expectSuccess = true) {
  return run(blender, ['--background', '--python-exit-code', '1', blend, '--python', evaluatorScript, '--', '--plan', plan, '--output', output], { expectSuccess });
}

async function schemaNegative(base, id, mutate, expectedCode) {
  const document = structuredClone(base);
  mutate(document);
  const validation = validateSceneSpecV03(document);
  return { id, layer: 'SCHEMA', rejected: validation.errors.some(error => error.code === expectedCode), expected: expectedCode, observed: validation.errors.map(error => error.code) };
}

async function planNegative(base, id, mutate, expectedText) {
  const document = structuredClone(base);
  mutate(document);
  const scene = resolve(runRoot, id, 'fixture.scene.json');
  await mkdir(resolve(runRoot, id), { recursive: true });
  await writeFile(scene, `${JSON.stringify(document, null, 2)}\n`);
  let error = '';
  try { await compileBuildPlan(scene); } catch (caught) { error = caught.message; }
  return { id, layer: 'BUILD_PLAN', rejected: error.includes(expectedText), expected: expectedText, observed: error.split('\n')[0] };
}

async function blenderCompileNegative(blender, base, id, mutate, expectedText) {
  const document = structuredClone(base);
  mutate(document);
  const root = resolve(runRoot, id);
  await mkdir(root, { recursive: true });
  const scene = resolve(root, 'fixture.scene.json');
  const planFile = resolve(root, 'fixture.build-plan.json');
  await writeFile(scene, `${JSON.stringify(document, null, 2)}\n`);
  const plan = await compileBuildPlan(scene);
  await writeFile(planFile, `${JSON.stringify(plan, null, 2)}\n`);
  const result = await compileScene(blender, planFile, resolve(root, 'build'), false);
  return { id, layer: 'BLENDER_COMPILE', rejected: result.code !== 0 && result.output.includes(expectedText), expected: expectedText, observed: result.output.split('\n').find(line => line.includes('BFS_COMPILE_ERROR')) ?? `exit ${result.code}` };
}

async function evaluationNegative(blender, base, id, mutate, failedCheck) {
  const document = structuredClone(base);
  mutate(document);
  const root = resolve(runRoot, id);
  await mkdir(root, { recursive: true });
  const scene = resolve(root, 'fixture.scene.json');
  const planFile = resolve(root, 'fixture.build-plan.json');
  const evaluationFile = resolve(root, 'evaluation.json');
  await writeFile(scene, `${JSON.stringify(document, null, 2)}\n`);
  const plan = await compileBuildPlan(scene);
  await writeFile(planFile, `${JSON.stringify(plan, null, 2)}\n`);
  await compileScene(blender, planFile, resolve(root, 'build'));
  await evaluateScene(blender, resolve(root, 'build/scene.blend'), planFile, evaluationFile, false);
  const evaluation = await readJson(evaluationFile);
  const target = evaluation.checks.find(item => item.id === failedCheck);
  return { id, layer: 'EVALUATION', rejected: target?.pass === false, expected: `${failedCheck}=false`, observed: target ?? null };
}

const blender = await findBlender();
await mkdir(runRoot, { recursive: true });
const scene = await readJson(scenePath);
const validation = validateSceneSpecV03(scene);
if (!validation.valid) throw new Error(`B04 SceneSpec v0.3 is invalid: ${JSON.stringify(validation.errors)}`);
const plan = await compileBuildPlan(scenePath);
await writeFile(planPath, `${JSON.stringify(plan, null, 2)}\n`);

const cleanBuilds = [];
for (const label of ['run-a', 'run-b']) {
  const outputDir = resolve(runRoot, label);
  await compileScene(blender, planPath, outputDir);
  const manifest = await readJson(resolve(outputDir, 'scene.manifest.json'));
  cleanBuilds.push({ label, structureHash: manifest.structureHash, blendSha256: digest(await readFile(resolve(outputDir, 'scene.blend'))) });
}
await evaluateScene(blender, resolve(runRoot, 'run-a/scene.blend'), planPath, evaluationPath);
const evaluation = await readJson(evaluationPath);

const negatives = [
  await blenderCompileNegative(blender, scene, 'N01_MISSING_PROP_OBJECT', document => { document.targets[0].sockets[0].objectRef = 'MISSING_PROP_OBJECT'; }, 'Target socket object is missing'),
  await blenderCompileNegative(blender, scene, 'N02_MISSING_TARGET_SOCKET', document => { document.attachments[0].targetEffectorSocket = 'MISSING_PALM'; }, 'Attachment socket is missing'),
  await planNegative(scene, 'N03_MISSING_CONSTRAINT_PERMISSION', document => { document.security.allowedOperations = document.security.allowedOperations.filter(value => value !== 'CREATE_CONSTRAINT'); }, 'does not authorize required operations: CREATE_CONSTRAINT'),
  await schemaNegative(scene, 'N04_INFLUENCE_STUCK_ZERO', document => { document.attachments[0].influenceKeys.forEach(key => { key.value = 0; }); }, 'SEM_INFLUENCE_STATES'),
  await evaluationNegative(blender, scene, 'N05_RELEASE_POP', document => { document.attachments[0].releaseTransform.locationM[0] += 1; }, 'B04_C08_SWITCH_POP'),
  await evaluationNegative(blender, scene, 'N06_APPROACH_OVERLAP', document => { document.assets.find(asset => asset.id === 'PROP_B04').transform.locationM = [-0.579999924, 0, 1.100000024]; }, 'B04_C09_CLEAR_PHASE_OVERLAP'),
  await evaluationNegative(blender, scene, 'N07_FAKE_STATIC_TARGET', document => { const socket = document.targets[0].sockets[0]; socket.binding = 'WORLD'; delete socket.assetRef; delete socket.objectRef; }, 'B04_C04_HOLD_POSITION'),
  await schemaNegative(scene, 'N08_ORIGINAL_GEOMETRY', document => { document.geometryEvaluations[0].space = 'ORIGINAL'; }, 'SCHEMA'),
];

const structureHashesEqual = cleanBuilds[0].structureHash === cleanBuilds[1].structureHash;
const report = {
  documentType: 'BFS_B04_CONTACT_EXPERIMENT',
  experimentVersion: '0.1.0',
  executedAtUtc: new Date().toISOString(),
  environment: { blender: evaluation.blender.version, platform: `${process.platform}-${process.arch}`, node: process.version },
  sceneSpec: { version: scene.specVersion, valid: validation.valid, shot: scene.shot.id },
  buildPlan: { version: plan.planVersion, hash: plan.planHash },
  cleanBuilds: { runs: cleanBuilds, structureHashesEqual, blendSha256Equal: cleanBuilds[0].blendSha256 === cleanBuilds[1].blendSha256 },
  evaluation: { allMachineChecksPassed: evaluation.allMachineChecksPassed, checks: evaluation.checks, geometry: evaluation.geometry },
  negativeTests: negatives,
  allAutomatedChecksPassed: structureHashesEqual && evaluation.allMachineChecksPassed && negatives.every(item => item.rejected),
  humanReview: evaluation.humanReview,
  experimentComplete: false,
  explicitNonClaims: evaluation.explicitNonClaims,
};
await writeFile(resultPath, `${JSON.stringify(report, null, 2)}\n`);
process.stdout.write(`BFS_B04_EXPERIMENT ${report.allAutomatedChecksPassed ? 'AUTOMATION_PASS' : 'FAIL'} ${negatives.filter(item => item.rejected).length}/${negatives.length} negatives; human review ${report.humanReview.status}\n`);
if (!report.allAutomatedChecksPassed) process.exitCode = 1;
