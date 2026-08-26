import { copyFile, mkdir, mkdtemp, readFile, rm, symlink, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { spawn } from 'node:child_process';
import { join, resolve } from 'node:path';
import { tmpdir } from 'node:os';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { compileBuildPlan } from './compile-build-plan.mjs';

const finalMode = process.argv.includes('--final');
const experimentRoot = resolve(repositoryRoot, 'experiments/security-v0-1');
const workRoot = resolve(experimentRoot, 'work');
const externalRoot = await mkdtemp(join(tmpdir(), 'bfs-b10-'));
const sourceScenePath = resolve(repositoryRoot, 'specs/benchmarks/B08.scene.json');
const sourceScene = JSON.parse(await readFile(sourceScenePath, 'utf8'));
const digest = value => createHash('sha256').update(value).digest('hex');
const serialize = value => `${JSON.stringify(value, null, 2)}\n`;
await rm(workRoot, { recursive: true, force: true });
await mkdir(workRoot, { recursive: true });

function run(command, args) {
  return new Promise((resolvePromise, reject) => {
    const child = spawn(command, args, { cwd: repositoryRoot, stdio: ['ignore', 'pipe', 'pipe'] });
    let output = '';
    child.stdout.on('data', chunk => { output += chunk; }); child.stderr.on('data', chunk => { output += chunk; }); child.on('error', reject);
    child.on('close', code => resolvePromise({ code, output }));
  });
}

async function sceneCase(id, mutate) {
  const scene = structuredClone(sourceScene);
  const path = resolve(workRoot, `${id}.scene.json`);
  await mutate(scene, path);
  if (!await readFile(path).catch(() => null)) await writeFile(path, serialize(scene));
  try {
    const plan = await compileBuildPlan(path);
    return { id, rejected: false, planHash: plan.planHash, observed: 'BUILD_PLAN_EMITTED' };
  } catch (error) { return { id, rejected: true, observed: String(error.message).split('\n')[0] }; }
}

const createdLinks = [];
async function link(target, path, type) {
  await rm(path, { recursive: true, force: true });
  await symlink(target, path, type);
  createdLinks.push(path);
}

try {
  const externalAsset = resolve(externalRoot, 'external-asset.blend');
  await copyFile(resolve(repositoryRoot, 'library/props/B08-prop.blend'), externalAsset);
  const assetLink = resolve(repositoryRoot, 'library/props/B10-external-asset.blend');
  await link(externalAsset, assetLink, 'file');

  const externalScene = resolve(externalRoot, 'external.scene.json');
  await writeFile(externalScene, serialize(sourceScene));
  const sceneLink = resolve(workRoot, 'N02_SCENE_SYMLINK.scene.json');
  await link(externalScene, sceneLink, 'file');

  const externalProvenance = resolve(externalRoot, 'external-source.json');
  await copyFile(resolve(repositoryRoot, 'experiments/trajectory-v0-1/results.json'), externalProvenance);
  const provenanceLink = resolve(workRoot, 'external-source.json');
  await link(externalProvenance, provenanceLink, 'file');

  const externalTrajectory = resolve(externalRoot, 'external.trajectory.json');
  await copyFile(resolve(repositoryRoot, 'specs/benchmarks/B07.trajectory.json'), externalTrajectory);
  const trajectoryLink = resolve(repositoryRoot, 'specs/benchmarks/B10-external.trajectory.json');
  await link(externalTrajectory, trajectoryLink, 'file');

  const externalOutput = resolve(externalRoot, 'render-output');
  await mkdir(externalOutput);
  const outputLink = resolve(repositoryRoot, 'renders/B10-external');
  await mkdir(resolve(repositoryRoot, 'renders'), { recursive: true });
  await link(externalOutput, outputLink, 'dir');

  const negatives = [];
  negatives.push(await sceneCase('N01_ASSET_SYMLINK', async scene => {
    scene.assets[0].uri = 'library/props/B10-external-asset.blend';
    scene.assets[0].sha256 = digest(await readFile(externalAsset));
  }));
  negatives.push(await sceneCase('N02_SCENE_SYMLINK', async (_scene, path) => {
    if (path !== sceneLink) throw new Error('Unexpected N02 path');
  }));
  negatives.push(await sceneCase('N03_PROVENANCE_SYMLINK', async scene => {
    scene.provenance.sources[1] = { uri: 'experiments/security-v0-1/work/external-source.json', role: 'REFERENCE', license: 'PROJECT-INTERNAL', sha256: digest(await readFile(externalProvenance)) };
  }));
  negatives.push(await sceneCase('N04_TRAJECTORY_SYMLINK', async scene => {
    scene.trajectories[0].trajectorySpecUri = 'specs/benchmarks/B10-external.trajectory.json';
    scene.trajectories[0].trajectorySpecSha256 = digest(await readFile(externalTrajectory));
  }));
  negatives.push(await sceneCase('N05_OUTPUT_ROOT_SYMLINK', async scene => { scene.render.outputRoot = 'renders/B10-external/'; }));

  const cliOutside = resolve(externalRoot, 'outside-build-plan.json');
  const cli = await run(process.execPath, ['scripts/compile-build-plan.mjs', '--input', 'specs/benchmarks/B08.scene.json', '--output', cliOutside]);
  negatives.push({ id: 'N06_CLI_OUTPUT_OUTSIDE', rejected: cli.code !== 0, observed: cli.output.trim().split('\n').at(-1) || `exit ${cli.code}` });
  negatives.push(await sceneCase('N07_LEXICAL_TRAVERSAL', async scene => { scene.assets[0].uri = 'library/../props/B08-prop.blend'; }));
  negatives.push(await sceneCase('N08_NETWORK_ACCESS', async scene => { scene.security.networkAccess = true; }));
  const positive = await compileBuildPlan(sourceScenePath);
  const vulnerableIds = negatives.filter(item => !item.rejected).map(item => item.id);
  const baselineExpected = ['N01_ASSET_SYMLINK', 'N02_SCENE_SYMLINK', 'N03_PROVENANCE_SYMLINK', 'N04_TRAJECTORY_SYMLINK', 'N05_OUTPUT_ROOT_SYMLINK', 'N06_CLI_OUTPUT_OUTSIDE'];
  const passed = finalMode
    ? negatives.every(item => item.rejected) && positive.planHash === '7a4bccb640130db2dbf5c315907f81d5462605b6939b00a9df672c362d544dd9'
    : serialize(vulnerableIds) === serialize(baselineExpected) && negatives.filter(item => ['N07_LEXICAL_TRAVERSAL', 'N08_NETWORK_ACCESS'].includes(item.id)).every(item => item.rejected);
  const report = {
    documentType: 'BFS_B10_PATH_SECURITY_EXPERIMENT', version: '0.1.0', phase: finalMode ? 'POST_REMEDIATION' : 'FIRST_RUN_FALSIFICATION', executedAtUtc: new Date().toISOString(),
    harmlessExternalFixture: true, negativeTests: negatives, vulnerableIds, positiveControl: { planHash: positive.planHash, pass: positive.planHash === '7a4bccb640130db2dbf5c315907f81d5462605b6939b00a9df672c362d544dd9' }, passed,
    formalB10Complete: finalMode && passed,
    ...(finalMode ? { firstRunFalsification: { uri: 'experiments/security-v0-1/first-run-falsified.json', observedVulnerableCases: 6 } } : {}),
  };
  await mkdir(experimentRoot, { recursive: true });
  const output = resolve(experimentRoot, finalMode ? 'results.json' : 'first-run-falsified.json');
  await writeFile(output, serialize(report));
  process.stdout.write(`BFS_B10_PATH_SECURITY ${report.phase} ${passed ? 'EXPECTED' : 'UNEXPECTED'} vulnerable ${vulnerableIds.length}/${negatives.length}\n`);
  if (!passed) process.exitCode = 1;
} finally {
  for (const path of createdLinks.reverse()) await rm(path, { recursive: true, force: true });
  await rm(externalRoot, { recursive: true, force: true });
}
