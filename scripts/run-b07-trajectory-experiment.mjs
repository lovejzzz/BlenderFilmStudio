import { access, mkdir, readFile, writeFile } from 'node:fs/promises';
import { constants } from 'node:fs';
import { createHash } from 'node:crypto';
import { spawn } from 'node:child_process';
import { resolve } from 'node:path';
import Ajv2020 from 'ajv/dist/2020.js';
import { repositoryRoot } from './lib/scene-spec.mjs';

const experimentRoot = resolve(repositoryRoot, 'experiments/trajectory-v0-1');
const runRoot = resolve(experimentRoot, 'runs');
const trajectoryPath = resolve(repositoryRoot, 'specs/benchmarks/B07.trajectory.json');
const schemaPath = resolve(repositoryRoot, 'specs/trajectory-spec.v0.1.schema.json');
const builder = resolve(repositoryRoot, 'blender/build_b07_trajectory_replay.py');
const evaluator = resolve(repositoryRoot, 'blender/evaluate_b07_trajectory_replay.py');
const mutator = resolve(repositoryRoot, 'blender/mutate_b07_replay.py');
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

const blender = await findBlender();
await mkdir(runRoot, { recursive: true });
const trajectoryBytes = await readFile(trajectoryPath);
const trajectorySha256 = digest(trajectoryBytes);
const trajectory = JSON.parse(trajectoryBytes.toString('utf8'));
const schema = JSON.parse(await readFile(schemaPath, 'utf8'));
const validate = new Ajv2020({ allErrors: true, strict: true }).compile(schema);
if (!validate(trajectory)) throw new Error(`B07 TrajectorySpec schema failed: ${JSON.stringify(validate.errors)}`);

async function build(label, input = trajectoryPath, expectedSha = trajectorySha256, expectSuccess = true) {
  const root = resolve(runRoot, label);
  await mkdir(root, { recursive: true });
  const blend = resolve(root, 'scene.blend');
  const manifest = resolve(root, 'manifest.json');
  const result = await run(blender, ['--background', '--factory-startup', '--python-exit-code', '1', '--python', builder, '--', '--trajectory', input, '--trajectory-sha256', expectedSha, '--repository-root', repositoryRoot, '--output', blend, '--manifest', manifest], { expectSuccess });
  return { root, blend, manifest, result };
}

async function evaluate(blend, output, expectSuccess = true) {
  return run(blender, ['--background', '--python-exit-code', '1', blend, '--python', evaluator, '--', '--trajectory', trajectoryPath, '--output', output], { expectSuccess });
}

const builds = [];
for (const label of ['positive-a', 'positive-b']) {
  const item = await build(label);
  const evaluationPath = resolve(item.root, 'evaluation.json');
  await evaluate(item.blend, evaluationPath);
  builds.push({ label, structureHash: JSON.parse(await readFile(item.manifest, 'utf8')).structureHash, blendSha256: digest(await readFile(item.blend)), evaluation: JSON.parse(await readFile(evaluationPath, 'utf8')) });
}

async function inputFixture(id, mutate) {
  const root = resolve(runRoot, id);
  await mkdir(root, { recursive: true });
  const document = structuredClone(trajectory);
  mutate(document);
  const path = resolve(root, 'fixture.trajectory.json');
  const bytes = `${JSON.stringify(document, null, 2)}\n`;
  await writeFile(path, bytes);
  return { root, path, sha: digest(bytes) };
}

async function inputNegative(id, mutate, expectedText) {
  const fixture = await inputFixture(id, mutate);
  const built = await build(id, fixture.path, fixture.sha, false);
  return { id, layer: 'REPLAY_BUILD', rejected: built.result.code !== 0 && built.result.output.includes(expectedText), expected: expectedText, observed: built.result.output.split('\n').find(line => line.includes('BFS_B07_REPLAY_BUILD_ERROR')) ?? `exit ${built.result.code}` };
}

async function runtimeNegative(id, mutation, expectedCheck) {
  const root = resolve(runRoot, id);
  await mkdir(root, { recursive: true });
  const blend = resolve(root, 'fixture.blend');
  const output = resolve(root, 'evaluation.json');
  await run(blender, ['--background', '--python-exit-code', '1', resolve(runRoot, 'positive-a/scene.blend'), '--python', mutator, '--', '--mutation', mutation, '--output', blend]);
  const evaluated = await evaluate(blend, output, false);
  const report = JSON.parse(await readFile(output, 'utf8'));
  const observed = report.checks.find(item => item.id === expectedCheck) ?? null;
  return { id, layer: 'REPLAY_EVALUATION', rejected: evaluated.code !== 0 && observed?.pass === false, expected: `${expectedCheck}=false`, observed };
}

const wrongHash = await build('N01_WRONG_FILE_HASH', trajectoryPath, '0'.repeat(64), false);
const negatives = [
  { id: 'N01_WRONG_FILE_HASH', layer: 'REPLAY_BUILD', rejected: wrongHash.result.code !== 0 && wrongHash.result.output.includes('Trajectory hash mismatch'), expected: 'Trajectory hash mismatch', observed: wrongHash.result.output.split('\n').find(line => line.includes('BFS_B07_REPLAY_BUILD_ERROR')) ?? `exit ${wrongHash.result.code}` },
  await inputNegative('N02_MISSING_SAMPLE', document => { document.samples.splice(50, 1); }, 'cover frames 1-132 exactly once'),
  await inputNegative('N03_DUPLICATE_FRAME', document => { document.samples[50].frame = document.samples[49].frame; }, 'cover frames 1-132 exactly once'),
  await inputNegative('N04_BAD_QUATERNION', document => { document.samples[60].rotationQuaternionWxyz = [1, 1, 0, 0]; }, 'quaternion is not normalized'),
  await inputNegative('N05_SOURCE_HASH_MISMATCH', document => { document.source.evaluationSha256 = '0'.repeat(64); }, 'source evaluation hash mismatch'),
  await runtimeNegative('N06_RIGID_BODY_SHORTCUT', 'RIGID_BODY', 'B07_C04_NO_PHYSICS_SHORTCUT'),
  await runtimeNegative('N07_KEY_MUTATION', 'KEY_MUTATION', 'B07_C02_POSITION_REPLAY'),
  await inputNegative('N08_UNDECLARED_TARGET', document => { document.targetObject = 'OTHER_PROP'; }, 'Undeclared trajectory target or space'),
];

const structureHashesEqual = builds[0].structureHash === builds[1].structureHash;
const report = {
  documentType: 'BFS_B07_TRAJECTORY_EXPERIMENT', version: '0.1.0', executedAtUtc: new Date().toISOString(),
  environment: { blender: builds[0].evaluation.environment.blender, platform: `${process.platform}-${process.arch}`, node: process.version },
  trajectory: { uri: 'specs/benchmarks/B07.trajectory.json', sha256: trajectorySha256, selectionStatus: trajectory.selectionStatus, source: trajectory.source },
  cleanBuilds: { runs: builds.map(item => ({ label: item.label, structureHash: item.structureHash, blendSha256: item.blendSha256 })), structureHashesEqual, blendSha256Equal: builds[0].blendSha256 === builds[1].blendSha256 },
  evaluation: { passed: builds[0].evaluation.passed, measurements: builds[0].evaluation.measurements, checks: builds[0].evaluation.checks },
  negativeTests: negatives,
  allAutomatedChecksPassed: structureHashesEqual && builds.every(item => item.evaluation.passed) && negatives.every(item => item.rejected),
  formalB07Complete: false,
  remainingGates: ['immutable BuildPlan integration', 'source-solve visual and authentic human approval'],
  explicitNonClaims: builds[0].evaluation.explicitNonClaims,
};
await writeFile(resolve(experimentRoot, 'B07.manifest.json'), `${JSON.stringify(JSON.parse(await readFile(resolve(runRoot, 'positive-a/manifest.json'), 'utf8')), null, 2)}\n`);
await writeFile(resolve(experimentRoot, 'B07.evaluation.json'), `${JSON.stringify(builds[0].evaluation, null, 2)}\n`);
await writeFile(resolve(experimentRoot, 'results.json'), `${JSON.stringify(report, null, 2)}\n`);
process.stdout.write(`BFS_B07_TRAJECTORY_EXPERIMENT ${report.allAutomatedChecksPassed ? 'AUTOMATION_PASS' : 'FAIL'} ${negatives.filter(item => item.rejected).length}/${negatives.length} negatives; formal B07 ${report.formalB07Complete ? 'TRUE' : 'FALSE'}\n`);
if (!report.allAutomatedChecksPassed) process.exitCode = 1;
