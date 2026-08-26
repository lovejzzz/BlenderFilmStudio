import { spawn } from 'node:child_process';
import { access, mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { readJson, repositoryRoot } from './lib/scene-spec.mjs';

const experimentRoot = resolve(repositoryRoot, 'experiments/pixel-v0-1');
const runsRoot = resolve(experimentRoot, 'runs');
const evidenceRoot = resolve(experimentRoot, 'evidence');
const compilerRunsRoot = resolve(repositoryRoot, 'experiments/compiler-v0-1/runs');
const pixelSpecPath = resolve(repositoryRoot, 'specs/pixel-spec.v0.1.json');
const renderScript = resolve(repositoryRoot, 'blender/render_exr_sample.py');
const inspectScript = resolve(repositoryRoot, 'blender/inspect_exr.py');
const ocioConfig = resolve(repositoryRoot, 'color/ocio/cg-config-v4.0.0_aces-v2.0_ocio-v2.5.ocio');
const environment = { ...process.env, OCIO: ocioConfig };

async function findBlender() {
  const candidates = [process.env.BLENDER_BIN, '/Applications/Blender.app/Contents/MacOS/Blender', 'blender'].filter(Boolean);
  for (const candidate of candidates) {
    if (candidate === 'blender') return candidate;
    try { await access(candidate); return candidate; } catch {}
  }
  throw new Error('Blender executable not found; set BLENDER_BIN');
}

function runProcess(command, args) {
  return new Promise((resolvePromise, reject) => {
    const child = spawn(command, args, { cwd: repositoryRoot, env: environment, stdio: ['ignore', 'pipe', 'pipe'] });
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', chunk => { stdout += chunk; process.stdout.write(chunk); });
    child.stderr.on('data', chunk => { stderr += chunk; process.stderr.write(chunk); });
    child.on('error', reject);
    child.on('close', code => {
      if (code !== 0) reject(new Error(`Process failed (${code}):\n${stdout}\n${stderr}`));
      else resolvePromise({ stdout, stderr });
    });
  });
}

async function render(blender, benchmark, frame, repetition) {
  const scenePath = resolve(compilerRunsRoot, benchmark, 'run-a', 'scene.blend');
  await access(scenePath);
  const stem = `${benchmark}-f${String(frame).padStart(4, '0')}-${repetition}`;
  const output = resolve(runsRoot, `${stem}.exr`);
  const reportPath = output.replace(/\.exr$/, '.render.json');
  try {
    await access(output);
    await access(reportPath);
    process.stdout.write(`BFS_RENDER_REUSE ${stem} ${output}\n`);
    return { stem, output, renderReport: await readJson(reportPath) };
  } catch {}
  await runProcess(blender, [
    '--background', scenePath,
    '--python', renderScript,
    '--', '--frame', String(frame), '--output', output, '--pixel-spec', pixelSpecPath,
  ]);
  return { stem, output, renderReport: await readJson(reportPath) };
}

async function inspectPair(blender, benchmark, frame, first, second) {
  const output = resolve(evidenceRoot, `${benchmark}-f${String(frame).padStart(4, '0')}.inspection.json`);
  await runProcess(blender, [
    '--factory-startup', '--background',
    '--python', inspectScript,
    '--', '--input', first.output, '--compare', second.output, '--pixel-spec', pixelSpecPath, '--output', output,
  ]);
  return await readJson(output);
}

async function main() {
  const blender = await findBlender();
  const pixelSpec = await readJson(pixelSpecPath);
  await mkdir(runsRoot, { recursive: true });
  await mkdir(evidenceRoot, { recursive: true });
  const version = await runProcess(blender, ['--version']);
  const samples = [];

  for (const selected of pixelSpec.samples) {
    process.stdout.write(`BFS_PIXEL_SAMPLE_START ${selected.benchmark} frame ${selected.frame}\n`);
    const first = await render(blender, selected.benchmark, selected.frame, 'run-a');
    const second = await render(blender, selected.benchmark, selected.frame, 'run-b');
    const inspection = await inspectPair(blender, selected.benchmark, selected.frame, first, second);
    samples.push({
      benchmark: selected.benchmark,
      frame: selected.frame,
      render: { runA: first.renderReport, runB: second.renderReport },
      conformance: inspection.conformance,
      comparison: inspection.comparison,
      evidence: `evidence/${selected.benchmark}-f${String(selected.frame).padStart(4, '0')}.inspection.json`,
    });
  }

  const report = {
    documentType: 'BFS_PIXEL_EXPERIMENT',
    experimentVersion: '0.1.0',
    executedAtUtc: new Date().toISOString(),
    environment: {
      blender: version.stdout.split('\n')[0].trim(),
      platform: `${process.platform}-${process.arch}`,
      ocioConfig: pixelSpec.color.ocioConfigName,
      ocioConfigSha256: pixelSpec.color.ocioConfigSha256,
      render: pixelSpec.environment,
    },
    samples,
    acceptance: {
      allPixelComparisonsExact: samples.every(item => item.comparison.pixelExact),
      allRequiredPassesPresent: samples.every(item => item.conformance.allRequiredPassesPresent),
      allPixelsFinite: samples.every(item => item.conformance.finiteValues),
      allRequiredAttributesPresent: samples.every(item => item.conformance.allRequiredAttributesPresent),
      allResolutionsExact: samples.every(item => item.conformance.resolutionExact),
    },
    explicitNonClaims: pixelSpec.explicitNonClaims,
  };
  await writeFile(resolve(experimentRoot, 'results.json'), `${JSON.stringify(report, null, 2)}\n`);
  process.stdout.write(`BFS_PIXEL_EXPERIMENT_COMPLETE ${JSON.stringify(report.acceptance)}\n`);
}

main().catch(error => {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
});
