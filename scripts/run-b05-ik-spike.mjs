import { access, mkdir, readFile, writeFile } from 'node:fs/promises';
import { constants } from 'node:fs';
import { createHash } from 'node:crypto';
import { spawn } from 'node:child_process';
import { resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';

const root = resolve(repositoryRoot, 'experiments/grasp-v0-1');
const runs = resolve(root, 'runs');
const builder = resolve(repositoryRoot, 'blender/build_b05_ik_spike.py');
const evaluator = resolve(repositoryRoot, 'blender/evaluate_b05_ik_spike.py');
const ocio = resolve(repositoryRoot, 'color/ocio/cg-config-v4.0.0_aces-v2.0_ocio-v2.5.ocio');
const output = resolve(root, 'automation-summary.json');
const digest = bytes => createHash('sha256').update(bytes).digest('hex');

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
const cleanBuilds = [];
for (const label of ['run-a', 'run-b']) {
  const directory = resolve(runs, label);
  await mkdir(directory, { recursive: true });
  const blend = resolve(directory, 'scene.blend');
  const manifest = resolve(directory, 'structure.json');
  const evaluation = resolve(directory, 'evaluation.json');
  await run(blender, ['--background', '--factory-startup', '--python-exit-code', '1', '--python', builder, '--', '--output', blend, '--manifest', manifest]);
  await run(blender, ['--background', '--python-exit-code', '1', blend, '--python', evaluator, '--', '--output', evaluation]);
  cleanBuilds.push({
    label,
    blendSha256: digest(await readFile(blend)),
    manifestSha256: digest(await readFile(manifest)),
    evaluationSha256: digest(await readFile(evaluation)),
    manifest: JSON.parse(await readFile(manifest, 'utf8')),
    evaluation: JSON.parse(await readFile(evaluation, 'utf8')),
  });
}
const gates = {
  structureHashesEqual: cleanBuilds[0].manifest.structureSha256 === cleanBuilds[1].manifest.structureSha256,
  manifestsByteEqual: cleanBuilds[0].manifestSha256 === cleanBuilds[1].manifestSha256,
  evaluationsByteEqual: cleanBuilds[0].evaluationSha256 === cleanBuilds[1].evaluationSha256,
  bothEvaluationsPass: cleanBuilds.every(build => build.evaluation.passed),
  binaryBlendFilesDiffer: cleanBuilds[0].blendSha256 !== cleanBuilds[1].blendSha256,
};
const report = {
  documentType: 'BFS_B05_IK_FEASIBILITY_AUTOMATION', version: '0.1.0',
  environment: { platform: `${process.platform}-${process.arch}`, node: process.version, blender: cleanBuilds[0].evaluation.environment.blender },
  cleanBuilds: cleanBuilds.map(({ label, blendSha256, manifestSha256, evaluationSha256, manifest }) => ({ label, blendSha256, manifestSha256, evaluationSha256, structureSha256: manifest.structureSha256 })),
  measurements: cleanBuilds[0].evaluation.measurements,
  gates, passed: Object.values(gates).every(Boolean), formalB05BenchmarkPassed: false,
  explicitNonClaims: cleanBuilds[0].evaluation.explicitNonClaims,
};
await writeFile(output, `${JSON.stringify(report, null, 2)}\n`);
process.stdout.write(`BFS_B05_IK_SPIKE ${report.passed ? 'PASS' : 'FAIL'} ${report.cleanBuilds[0].structureSha256}\n`);
if (!report.passed) process.exitCode = 1;
