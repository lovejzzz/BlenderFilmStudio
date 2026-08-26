import { spawn } from 'node:child_process';
import { access, mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { canonicalJson, readJson, repositoryRoot, sha256 } from './lib/scene-spec.mjs';
import { compileBuildPlan } from './compile-build-plan.mjs';

const experimentRoot = resolve(repositoryRoot, 'experiments/compiler-v0-1');
const plansRoot = resolve(experimentRoot, 'plans');
const evidenceRoot = resolve(experimentRoot, 'evidence');
const runsRoot = resolve(experimentRoot, 'runs');
const blenderScript = resolve(repositoryRoot, 'blender/compile_scene.py');
const ocioConfig = resolve(repositoryRoot, 'color/ocio/cg-config-v4.0.0_aces-v2.0_ocio-v2.5.ocio');
const blenderEnvironment = { ...process.env, OCIO: ocioConfig };

async function findBlender() {
  const candidates = [
    process.env.BLENDER_BIN,
    '/Applications/Blender.app/Contents/MacOS/Blender',
    'blender',
  ].filter(Boolean);
  for (const candidate of candidates) {
    if (candidate === 'blender') return candidate;
    try {
      await access(candidate);
      return candidate;
    } catch {}
  }
  throw new Error('Blender executable not found; set BLENDER_BIN');
}

function runProcess(command, args, { expectSuccess = true, env = process.env } = {}) {
  return new Promise((resolvePromise, reject) => {
    const child = spawn(command, args, { cwd: repositoryRoot, env, stdio: ['ignore', 'pipe', 'pipe'] });
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', chunk => { stdout += chunk; });
    child.stderr.on('data', chunk => { stderr += chunk; });
    child.on('error', reject);
    child.on('close', code => {
      const result = { code, stdout, stderr };
      if (expectSuccess && code !== 0) reject(new Error(`Process failed (${code}):\n${stdout}\n${stderr}`));
      else resolvePromise(result);
    });
  });
}

async function writePlan(benchmark) {
  const sceneSpecPath = `specs/benchmarks/${benchmark}.scene.json`;
  const first = await compileBuildPlan(sceneSpecPath);
  const second = await compileBuildPlan(sceneSpecPath);
  const firstCanonical = canonicalJson(first);
  const secondCanonical = canonicalJson(second);
  if (firstCanonical !== secondCanonical) throw new Error(`${benchmark} BuildPlan is not deterministic`);
  const planPath = resolve(plansRoot, `${benchmark}.build-plan.json`);
  await writeFile(planPath, `${JSON.stringify(first, null, 2)}\n`);
  return { plan: first, planPath, deterministic: true };
}

async function compileRun(blender, benchmark, label, planPath) {
  const outputDir = resolve(runsRoot, benchmark, label);
  await rm(outputDir, { recursive: true, force: true });
  await mkdir(outputDir, { recursive: true });
  const processResult = await runProcess(blender, [
    '--factory-startup',
    '--background',
    '--python', blenderScript,
    '--',
    '--plan', planPath,
    '--repository-root', repositoryRoot,
    '--output-dir', outputDir,
  ], { env: blenderEnvironment });
  const manifest = await readJson(resolve(outputDir, 'scene.manifest.json'));
  const blendBytes = await readFile(resolve(outputDir, 'scene.blend'));
  const evidencePath = resolve(evidenceRoot, `${benchmark}-${label}.manifest.json`);
  await writeFile(evidencePath, `${JSON.stringify(manifest, null, 2)}\n`);
  return {
    manifest,
    blendSha256: sha256(blendBytes),
    compilerMarker: processResult.stdout.split('\n').find(line => line.startsWith('BFS_COMPILE_OK')),
  };
}

async function verifyTamperRejected(blender, benchmark, plan) {
  const tampered = structuredClone(plan);
  tampered.plan.cameras[0].lensMm += 1;
  const tamperedPath = resolve(runsRoot, benchmark, 'tampered.build-plan.json');
  await mkdir(resolve(runsRoot, benchmark), { recursive: true });
  await writeFile(tamperedPath, `${JSON.stringify(tampered, null, 2)}\n`);
  const result = await runProcess(blender, [
    '--factory-startup',
    '--background',
    '--python', blenderScript,
    '--',
    '--plan', tamperedPath,
    '--repository-root', repositoryRoot,
    '--output-dir', resolve(runsRoot, benchmark, 'tampered-output'),
  ], { expectSuccess: false, env: blenderEnvironment });
  return result.code !== 0 && `${result.stdout}\n${result.stderr}`.includes('BuildPlan hash mismatch');
}

async function main() {
  const blender = await findBlender();
  await mkdir(plansRoot, { recursive: true });
  await mkdir(evidenceRoot, { recursive: true });
  await mkdir(runsRoot, { recursive: true });
  const version = await runProcess(blender, ['--version']);
  const blenderVersion = version.stdout.split('\n')[0].trim();
  const results = [];

  for (const benchmark of ['B01', 'B02']) {
    const { plan, planPath, deterministic } = await writePlan(benchmark);
    const first = await compileRun(blender, benchmark, 'run-a', planPath);
    const second = await compileRun(blender, benchmark, 'run-b', planPath);
    const structureEqual = canonicalJson(first.manifest.structure) === canonicalJson(second.manifest.structure);
    const structureHashEqual = first.manifest.structureHash === second.manifest.structureHash;
    const tamperRejected = await verifyTamperRejected(blender, benchmark, plan);
    results.push({
      benchmark,
      shotId: plan.plan.shot.id,
      planHash: plan.planHash,
      buildPlanDeterministic: deterministic,
      structureHash: first.manifest.structureHash,
      cleanBuildStructureEqual: structureEqual && structureHashEqual,
      blendByteIdentical: first.blendSha256 === second.blendSha256,
      blendSha256: { runA: first.blendSha256, runB: second.blendSha256 },
      tamperedPlanRejected: tamperRejected,
      warnings: first.manifest.warnings,
    });
  }

  const report = {
    documentType: 'BFS_COMPILER_EXPERIMENT',
    experimentVersion: '0.1.0',
    executedAtUtc: new Date().toISOString(),
    environment: { blender: blenderVersion, platform: `${process.platform}-${process.arch}`, node: process.version },
    results,
    allStructuralChecksPassed: results.every(result => result.buildPlanDeterministic && result.cleanBuildStructureEqual && result.tamperedPlanRejected),
    explicitNonClaims: [
      'No final pixels were rendered in this structural experiment.',
      'Binary .blend byte identity is recorded but is not the acceptance criterion.',
      'The ACES 2 OCIO config is pinned; physical display calibration and pixel reproducibility are outside this structural experiment.',
    ],
  };
  await writeFile(resolve(experimentRoot, 'results.json'), `${JSON.stringify(report, null, 2)}\n`);
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
  if (!report.allStructuralChecksPassed) process.exitCode = 1;
}

main().catch(error => {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
});
