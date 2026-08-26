import { access, mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { constants } from 'node:fs';
import { createHash } from 'node:crypto';
import { spawn } from 'node:child_process';
import { resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { compileBuildPlan } from './compile-build-plan.mjs';

const finalMode = process.argv.includes('--final');
const experimentRoot = resolve(repositoryRoot, 'experiments/asset-security-v0-1');
const workRoot = resolve(experimentRoot, 'work');
const assetWorkRoot = resolve(repositoryRoot, 'assets/sets/B11-work');
const generator = resolve(repositoryRoot, 'blender/generate_b11_adversarial_asset.py');
const compiler = resolve(repositoryRoot, 'blender/compile_scene.py');
const ocio = resolve(repositoryRoot, 'color/ocio/cg-config-v4.0.0_aces-v2.0_ocio-v2.5.ocio');
const digest = value => createHash('sha256').update(value).digest('hex');
const serialize = value => `${JSON.stringify(value, null, 2)}\n`;

async function findBlender() {
  const candidates = [process.env.BLENDER_BIN, '/Applications/Blender.app/Contents/MacOS/Blender', 'blender'].filter(Boolean);
  for (const candidate of candidates) { if (candidate === 'blender') return candidate; try { await access(candidate, constants.X_OK); return candidate; } catch {} }
  throw new Error('Blender executable not found; set BLENDER_BIN');
}
function run(command, args, expectSuccess = true, extraEnv = {}) {
  return new Promise((resolvePromise, reject) => {
    const child = spawn(command, args, { cwd: repositoryRoot, env: { ...process.env, ...extraEnv }, stdio: ['ignore', 'pipe', 'pipe'] });
    let output = ''; child.stdout.on('data', chunk => { output += chunk; }); child.stderr.on('data', chunk => { output += chunk; }); child.on('error', reject);
    child.on('close', code => expectSuccess && code !== 0 ? reject(new Error(output)) : resolvePromise({ code, output }));
  });
}
const blender = await findBlender();
await rm(workRoot, { recursive: true, force: true });
await rm(assetWorkRoot, { recursive: true, force: true });
await mkdir(workRoot, { recursive: true });
await mkdir(assetWorkRoot, { recursive: true });
const sourceScene = JSON.parse(await readFile(resolve(repositoryRoot, 'specs/benchmarks/B01.scene.json'), 'utf8'));
const baseAsset = resolve(repositoryRoot, sourceScene.assets[0].uri);
const dependency = resolve(assetWorkRoot, 'B11-dependency.blend');
await run(blender, ['--background','--factory-startup','--disable-autoexec','--python-exit-code','1','--python',generator,'--','--variant','DEPENDENCY','--output',dependency,'--report',resolve(workRoot,'DEPENDENCY.report.json')]);
const variants = finalMode ? ['DRIVER','SHAPE_KEY_DRIVER','CONSTRAINT','RIGID_BODY','ACTION','LINKED_LIBRARY','LIBRARY_OVERRIDE','COMBINED'] : ['COMBINED'];
const tests = [];
for (const variant of variants) {
  const asset = resolve(assetWorkRoot, `${variant}.blend`);
  const generation = resolve(workRoot, `${variant}.report.json`);
  const args = ['--background','--factory-startup','--disable-autoexec','--python-exit-code','1','--python',generator,'--','--base',baseAsset,'--variant',variant,'--output',asset,'--report',generation];
  if (variant === 'LINKED_LIBRARY' || variant === 'LIBRARY_OVERRIDE') args.push('--dependency', dependency);
  await run(blender, args);
  const scene = structuredClone(sourceScene);
  scene.assets[0].uri = `assets/sets/B11-work/${variant}.blend`;
  scene.assets[0].sha256 = digest(await readFile(asset));
  scene.render.outputRoot = `renders/B11_${variant}/`;
  const scenePath = resolve(workRoot, `${variant}.scene.json`);
  const planPath = resolve(workRoot, `${variant}.build-plan.json`);
  await writeFile(scenePath, serialize(scene));
  const plan = await compileBuildPlan(scenePath);
  await writeFile(planPath, serialize(plan));
  const outputRoot = resolve(workRoot, `${variant}-output`);
  const compile = await run(blender, ['--background','--factory-startup','--disable-autoexec','--python-exit-code','1','--python',compiler,'--','--plan',planPath,'--repository-root',repositoryRoot,'--output-dir',outputRoot], false, { OCIO: ocio });
  tests.push({ id: `N_${variant}`, rejected: compile.code !== 0, observed: compile.output.split('\n').find(line => line.includes('BFS_COMPILE_')) ?? `exit ${compile.code}` });
}
let positiveControl = null;
if (finalMode) {
  const cleanPlan = await compileBuildPlan(resolve(repositoryRoot, 'specs/benchmarks/B01.scene.json'));
  const cleanPlanPath = resolve(workRoot, 'B01.clean.build-plan.json');
  await writeFile(cleanPlanPath, serialize(cleanPlan));
  const autoexec = await run(blender, ['--background','--factory-startup','--enable-autoexec','--python-exit-code','1','--python',compiler,'--','--plan',cleanPlanPath,'--repository-root',repositoryRoot,'--output-dir',resolve(workRoot,'AUTOEXEC-output')], false, { OCIO: ocio });
  tests.push({ id: 'N_AUTOEXEC_ENABLED', rejected: autoexec.code !== 0, observed: autoexec.output.split('\n').find(line => line.includes('BFS_COMPILE_')) ?? `exit ${autoexec.code}` });
  const cleanOutput = resolve(workRoot, 'B01-clean-output');
  const clean = await run(blender, ['--background','--factory-startup','--disable-autoexec','--python-exit-code','1','--python',compiler,'--','--plan',cleanPlanPath,'--repository-root',repositoryRoot,'--output-dir',cleanOutput], false, { OCIO: ocio });
  const manifest = clean.code === 0 ? JSON.parse(await readFile(resolve(cleanOutput, 'scene.manifest.json'), 'utf8')) : null;
  positiveControl = { accepted: clean.code === 0, planHash: cleanPlan.planHash, structureHash: manifest?.structureHash ?? null, pass: clean.code === 0 && manifest?.structureHash === 'c699fc27230d8dc378a9d4e6aa23a6425cc7007c0ee33a3172b6928f8e1b7f0b' };
}
const expected = finalMode ? tests.every(item => item.rejected) && positiveControl?.pass : tests.every(item => !item.rejected);
const report = {
  documentType: 'BFS_B11_ASSET_SECURITY_EXPERIMENT', version: '0.1.0',
  phase: finalMode ? 'POST_REMEDIATION' : 'FIRST_RUN_FALSIFICATION', executedAtUtc: new Date().toISOString(), harmlessExecutableCode: false,
  tests, positiveControl, experimentOutcomeAsExpected: expected, securityGatePassed: finalMode && expected,
  passed: finalMode && expected, formalB11Complete: finalMode && expected, firstRunExpectedToFalsify: !finalMode,
};
await mkdir(experimentRoot, { recursive: true });
await writeFile(resolve(experimentRoot, finalMode ? 'results.json' : 'first-run-falsified.json'), serialize(report));
process.stdout.write(`BFS_B11_ASSET_SECURITY ${report.phase} ${expected ? 'EXPECTED' : 'UNEXPECTED'} ${tests.filter(item => item.rejected).length}/${tests.length} rejected\n`);
if (!expected) process.exitCode = 1;
