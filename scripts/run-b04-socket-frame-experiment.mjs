import { access, mkdir, readFile, writeFile } from 'node:fs/promises';
import { constants } from 'node:fs';
import { createHash } from 'node:crypto';
import { spawn } from 'node:child_process';
import { resolve } from 'node:path';
import { compileBuildPlan } from './compile-build-plan.mjs';
import { canonicalJson, readJson, repositoryRoot } from './lib/scene-spec.mjs';
import { validateActorSpec } from './lib/actor-spec.mjs';
import { validateSceneSpecV03 } from './lib/scene-spec-v03.mjs';

const root = resolve(repositoryRoot, 'experiments/contact-v0-3');
const runs = resolve(root, 'runs');
const actorPath = resolve(repositoryRoot, 'specs/benchmarks/B04.socket-frame.actor.json');
const scenePath = resolve(repositoryRoot, 'specs/benchmarks/B04.socket-frame.scene.json');
const planPath = resolve(root, 'B04.socket-frame.build-plan.json');
const contactPath = resolve(root, 'B04.socket-frame.contact-evaluation.json');
const geometryPath = resolve(root, 'B04.socket-frame.geometry.json');
const geometryRunBPath = resolve(runs, 'run-b/geometry.json');
const resultPath = resolve(root, 'results.json');
const compiler = resolve(repositoryRoot, 'blender/compile_scene.py');
const contactEvaluator = resolve(repositoryRoot, 'blender/evaluate_b04_contact_scene.py');
const geometryEvaluator = resolve(repositoryRoot, 'blender/evaluate_b04_geometry_v02.py');
const generator = resolve(repositoryRoot, 'scripts/generate-b04-socket-frame-scene.mjs');
const ocio = resolve(repositoryRoot, 'color/ocio/cg-config-v4.0.0_aces-v2.0_ocio-v2.5.ocio');
const digest = value => createHash('sha256').update(value).digest('hex');

async function findBlender() {
  for (const candidate of [process.env.BLENDER_BIN, '/Applications/Blender.app/Contents/MacOS/Blender', 'blender'].filter(Boolean)) {
    if (candidate === 'blender') return candidate;
    try { await access(candidate, constants.X_OK); return candidate; } catch {}
  }
  throw new Error('Blender executable not found; set BLENDER_BIN');
}

function run(command, args) {
  return new Promise((resolvePromise, reject) => {
    const child = spawn(command, args, { cwd: repositoryRoot, env: { ...process.env, OCIO: ocio }, stdio: ['ignore', 'pipe', 'pipe'] });
    let stdout = '', stderr = '';
    child.stdout.on('data', chunk => { stdout += chunk; });
    child.stderr.on('data', chunk => { stderr += chunk; });
    child.on('error', reject);
    child.on('close', code => code === 0 ? resolvePromise({ stdout, stderr }) : reject(new Error(`${stdout}\n${stderr}`)));
  });
}

const blender = await findBlender();
await mkdir(runs, { recursive: true });
await run(process.execPath, [generator]);
const actor = await readJson(actorPath);
const scene = await readJson(scenePath);
const actorValidation = validateActorSpec(actor);
const sceneValidation = validateSceneSpecV03(scene);
if (!actorValidation.valid || !sceneValidation.valid) throw new Error(`Generated fixture invalid: ${JSON.stringify({ actor: actorValidation.errors, scene: sceneValidation.errors })}`);
const firstPlan = await compileBuildPlan(scenePath);
const secondPlan = await compileBuildPlan(scenePath);
if (canonicalJson(firstPlan) !== canonicalJson(secondPlan)) throw new Error('BuildPlan generation is not deterministic');
await writeFile(planPath, `${JSON.stringify(firstPlan, null, 2)}\n`);

const cleanBuilds = [];
for (const label of ['run-a', 'run-b']) {
  const output = resolve(runs, label);
  await mkdir(output, { recursive: true });
  await run(blender, ['--background', '--factory-startup', '--python-exit-code', '1', '--python', compiler, '--', '--plan', planPath, '--repository-root', repositoryRoot, '--output-dir', output]);
  const manifest = await readJson(resolve(output, 'scene.manifest.json'));
  cleanBuilds.push({ label, structureHash: manifest.structureHash, blendSha256: digest(await readFile(resolve(output, 'scene.blend'))) });
}
await run(blender, ['--background', '--python-exit-code', '1', resolve(runs, 'run-a/scene.blend'), '--python', contactEvaluator, '--', '--plan', planPath, '--output', contactPath]);
await run(blender, ['--background', '--python-exit-code', '1', resolve(runs, 'run-a/scene.blend'), '--python', geometryEvaluator, '--', '--plan', planPath, '--output', geometryPath]);
await run(blender, ['--background', '--python-exit-code', '1', resolve(runs, 'run-b/scene.blend'), '--python', geometryEvaluator, '--', '--plan', planPath, '--output', geometryRunBPath]);
const contact = await readJson(contactPath);
const geometry = await readJson(geometryPath);
const geometryRunB = await readJson(geometryRunBPath);
const hold = geometry.phaseSummaries.find(item => item.phase === 'HOLD');
const original = await readJson(resolve(repositoryRoot, 'experiments/contact-v0-1/results.json'));
const gates = {
  actorSpecValid: actorValidation.valid,
  sceneSpecValid: sceneValidation.valid,
  buildPlanDeterministic: true,
  structureHashesEqual: cleanBuilds[0].structureHash === cleanBuilds[1].structureHash,
  originalTenChecksPass: contact.allMachineChecksPassed,
  originalEightNegativesStillRejected: original.negativeTests.length === 8 && original.negativeTests.every(item => item.rejected),
  holdOverlapFramesZero: hold.framesWithSurfaceOverlap === 0,
  holdInsideDepthZero: hold.maximumInsideVertexDepthM === 0,
  holdSeparationInPreregisteredRange: hold.minimumExactUnsignedSurfaceDistanceM >= 0.001 && hold.minimumExactUnsignedSurfaceDistanceM <= 0.003,
  geometryReportsEqual: canonicalJson(geometry) === canonicalJson(geometryRunB),
};
const report = {
  documentType: 'BFS_B04_SOCKET_FRAME_EXPERIMENT', experimentVersion: '0.3.0', executedAtUtc: new Date().toISOString(),
  environment: { blender: geometry.blender.version, platform: `${process.platform}-${process.arch}`, node: process.version },
  fixtures: { actorSpecSha256: firstPlan.plan.actors[0].verifiedActorSpecSha256, buildPlanSha256: firstPlan.planHash },
  cleanBuilds, contactChecks: contact.checks, geometry: { phaseSummaries: geometry.phaseSummaries, finding: geometry.finding, reportSha256: digest(await readFile(geometryPath)) },
  inheritedNegativeTests: original.negativeTests.map(item => ({ id: item.id, rejected: item.rejected })), gates,
  allAutomatedGatesPassed: Object.values(gates).every(Boolean), humanReview: { status: 'PENDING_NEW_CLIP', required: true }, experimentComplete: false,
  explicitNonClaims: geometry.explicitNonClaims,
};
await writeFile(resultPath, `${JSON.stringify(report, null, 2)}\n`);
process.stdout.write(`BFS_B04_SOCKET_FRAME ${report.allAutomatedGatesPassed ? 'AUTOMATION_PASS' : 'FAIL'} ${cleanBuilds[0].structureHash}\n`);
if (!report.allAutomatedGatesPassed) process.exitCode = 1;
