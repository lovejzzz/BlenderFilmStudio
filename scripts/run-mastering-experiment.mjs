import { spawn } from 'node:child_process';
import { access, mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { readJson, repositoryRoot } from './lib/scene-spec.mjs';

const experimentRoot = resolve(repositoryRoot, 'experiments/mastering-v0-1');
const evidenceRoot = resolve(experimentRoot, 'evidence');
const pixelRunsRoot = resolve(repositoryRoot, 'experiments/pixel-v0-1/runs');
const pixelSpecPath = resolve(repositoryRoot, 'specs/pixel-spec.v0.1.json');
const masterScript = resolve(repositoryRoot, 'blender/master_exr.py');
const inspectScript = resolve(repositoryRoot, 'blender/inspect_exr.py');

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
    const child = spawn(command, args, { cwd: repositoryRoot, stdio: ['ignore', 'pipe', 'pipe'] });
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

async function main() {
  const blender = await findBlender();
  const pixelSpec = await readJson(pixelSpecPath);
  await mkdir(evidenceRoot, { recursive: true });
  const samples = [];

  for (const selected of pixelSpec.samples) {
    const frameLabel = String(selected.frame).padStart(4, '0');
    const input = resolve(pixelRunsRoot, `${selected.benchmark}-f${frameLabel}-run-a.exr`);
    const mastered = resolve(pixelRunsRoot, `${selected.benchmark}-f${frameLabel}-master.exr`);
    const inspectionPath = resolve(evidenceRoot, `${selected.benchmark}-f${frameLabel}.mastering-inspection.json`);
    await runProcess(blender, [
      '--factory-startup', '--background', '--python', masterScript, '--',
      '--input', input, '--output', mastered, '--frame', String(selected.frame),
    ]);
    await runProcess(blender, [
      '--factory-startup', '--background', '--python', inspectScript, '--',
      '--input', mastered, '--compare', input, '--pixel-spec', pixelSpecPath, '--output', inspectionPath,
    ]);
    const mastering = await readJson(mastered.replace(/\.exr$/, '.master.json'));
    const inspection = await readJson(inspectionPath);
    samples.push({
      benchmark: selected.benchmark,
      frame: selected.frame,
      inputSha256: mastering.input.sha256,
      outputSha256: mastering.output.sha256,
      outputBytes: mastering.output.bytes,
      parts: mastering.parts,
      conformance: inspection.conformance,
      comparison: inspection.comparison,
      evidence: `evidence/${selected.benchmark}-f${frameLabel}.mastering-inspection.json`,
    });
  }

  const report = {
    documentType: 'BFS_MASTERING_EXPERIMENT',
    experimentVersion: '0.1.0',
    executedAtUtc: new Date().toISOString(),
    samples,
    acceptance: {
      allRequiredAttributesPresent: samples.every(item => item.conformance.allRequiredAttributesPresent),
      allPixelsUnchanged: samples.every(item => item.comparison.pixelExact),
      allRequiredPassesPreserved: samples.every(item => item.conformance.allRequiredPassesPresent),
      allPixelsFinite: samples.every(item => item.conformance.finiteValues),
    },
    explicitNonClaims: [
      'Metadata conformance does not create a DCP or prove DCI compliance.',
      'The time-code packer currently supports integer frame rates up to 30 fps.',
      'Owner and comments are read back through OIIO canonical aliases Copyright and ImageDescription.',
    ],
  };
  await writeFile(resolve(experimentRoot, 'results.json'), `${JSON.stringify(report, null, 2)}\n`);
  process.stdout.write(`BFS_MASTERING_EXPERIMENT_COMPLETE ${JSON.stringify(report.acceptance)}\n`);
}

main().catch(error => {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
});
