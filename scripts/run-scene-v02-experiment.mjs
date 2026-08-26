import { access, mkdir, readFile, writeFile } from 'node:fs/promises';
import { constants } from 'node:fs';
import { createHash } from 'node:crypto';
import { spawn } from 'node:child_process';
import { resolve } from 'node:path';
import { compileBuildPlan } from './compile-build-plan.mjs';
import { readJson, repositoryRoot } from './lib/scene-spec.mjs';
import { validateSceneSpecV02 } from './lib/scene-spec-v02.mjs';

const scenePath = resolve(repositoryRoot, 'specs/benchmarks/B03.scene.json');
const planPath = resolve(repositoryRoot, 'experiments/actor-v0-1/B03.build-plan.json');
const outputPath = resolve(repositoryRoot, 'experiments/actor-v0-1/B03.integration-results.json');
const runRoot = resolve(repositoryRoot, 'experiments/actor-v0-1/runs/B03-v02');
const compilerScript = resolve(repositoryRoot, 'blender/compile_scene.py');
const evaluatorScript = resolve(repositoryRoot, 'blender/evaluate_compiled_actor_scene.py');
const evaluationPath = resolve(repositoryRoot, 'experiments/actor-v0-1/B03.scene-evaluation.json');
const ocio = resolve(repositoryRoot, 'color/ocio/cg-config-v4.0.0_aces-v2.0_ocio-v2.5.ocio');

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
    const child = spawn(command, args, { cwd: repositoryRoot, env: { ...process.env, OCIO: ocio }, stdio: ['ignore', 'pipe', 'pipe'] });
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', chunk => { stdout += chunk; process.stdout.write(chunk); });
    child.stderr.on('data', chunk => { stderr += chunk; process.stderr.write(chunk); });
    child.on('error', reject);
    child.on('close', code => code === 0 ? resolvePromise({ stdout, stderr }) : reject(new Error(`${command} exited ${code}: ${stderr || stdout}`)));
  });
}

const digest = value => createHash('sha256').update(value).digest('hex');

async function expectCompileRejected(base, id, mutate, expectedText) {
  const document = structuredClone(base);
  mutate(document);
  const path = resolve(runRoot, `${id}.scene.json`);
  await writeFile(path, `${JSON.stringify(document, null, 2)}\n`);
  const validation = validateSceneSpecV02(document);
  let error = '';
  try { await compileBuildPlan(path); } catch (caught) { error = caught.message; }
  return { id, schemaValid: validation.valid, rejected: error.includes(expectedText), expectedText, error: error.split('\n')[0] };
}

const blender = await findBlender();
await mkdir(runRoot, { recursive: true });
const scene = await readJson(scenePath);
const validation = validateSceneSpecV02(scene);
if (!validation.valid) throw new Error(`B03 SceneSpec v0.2 is invalid: ${JSON.stringify(validation.errors)}`);

const plan = await compileBuildPlan(scenePath);
await writeFile(planPath, `${JSON.stringify(plan, null, 2)}\n`);
const manifests = [];
const blendHashes = [];
for (const label of ['run-a', 'run-b']) {
  const outputDir = resolve(runRoot, label);
  await run(blender, ['--background', '--factory-startup', '--python', compilerScript, '--', '--plan', planPath, '--repository-root', repositoryRoot, '--output-dir', outputDir]);
  manifests.push(await readJson(resolve(outputDir, 'scene.manifest.json')));
  blendHashes.push(digest(await readFile(resolve(outputDir, 'scene.blend'))));
}
await run(blender, ['--background', resolve(runRoot, 'run-a/scene.blend'), '--python', evaluatorScript, '--', '--plan', planPath, '--repository-root', repositoryRoot, '--output', evaluationPath]);
const evaluation = await readJson(evaluationPath);

const duplicateSocket = structuredClone(scene);
duplicateSocket.targets[0].sockets.push(structuredClone(duplicateSocket.targets[0].sockets[0]));
const duplicateSocketValidation = validateSceneSpecV02(duplicateSocket);
const negatives = [
  {
    id: 'N01_DUPLICATE_TARGET_SOCKET',
    schemaValid: duplicateSocketValidation.valid,
    rejected: duplicateSocketValidation.errors.some(error => error.code === 'SEM_DUPLICATE_TARGET_SOCKET'),
    expectedText: 'SEM_DUPLICATE_TARGET_SOCKET',
    error: duplicateSocketValidation.errors.map(error => error.code).join(','),
  },
  await expectCompileRejected(scene, 'N02_ACTOR_SPEC_HASH', document => { document.actors[0].actorSpecSha256 = 'a'.repeat(64); }, 'ActorSpec ACTOR_LEAD hash mismatch'),
  await expectCompileRejected(scene, 'N03_MISSING_GAZE_TARGET', document => { document.targets = document.targets.filter(target => target.id !== 'PROP_MARK'); }, 'gaze target PROP_MARK.GAZE_MARK is missing'),
  await expectCompileRejected(scene, 'N04_MISSING_OPERATION', document => { document.security.allowedOperations = document.security.allowedOperations.filter(value => value !== 'APPLY_PERFORMANCE'); }, 'does not authorize required operations: APPLY_PERFORMANCE'),
];

const summary = {
  documentType: 'BFS_SCENE_V02_EXPERIMENT',
  experimentVersion: '0.1.0',
  executedAtUtc: new Date().toISOString(),
  environment: { blender: evaluation.blender.version, platform: `${process.platform}-${process.arch}`, node: process.version },
  sceneSpec: { version: scene.specVersion, valid: validation.valid, shot: scene.shot.id },
  buildPlan: { version: plan.planVersion, hash: plan.planHash },
  cleanBuilds: {
    structureHashes: manifests.map(item => item.structureHash),
    structureHashesEqual: manifests[0].structureHash === manifests[1].structureHash,
    blendSha256: blendHashes,
    blendSha256Equal: blendHashes[0] === blendHashes[1],
  },
  evaluation: {
    allChecksPassed: evaluation.allChecksPassed,
    checks: evaluation.checks,
  },
  negativeTests: negatives,
  allAcceptanceChecksPassed: manifests[0].structureHash === manifests[1].structureHash
    && evaluation.allChecksPassed && negatives.every(item => item.rejected),
  explicitNonClaims: evaluation.explicitNonClaims,
};
await writeFile(outputPath, `${JSON.stringify(summary, null, 2)}\n`);
console.log(`BFS_SCENE_V02_EXPERIMENT_COMPLETE ${JSON.stringify({ allAcceptanceChecksPassed: summary.allAcceptanceChecksPassed, structureHash: manifests[0].structureHash })}`);
if (!summary.allAcceptanceChecksPassed) process.exitCode = 1;
