import { mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256File } from './lib/receipt-format.mjs';

const experimentRoot = resolve(repositoryRoot, 'experiments/sampling-quality-derivation-v0-1');
const evidenceRoot = resolve(experimentRoot, 'evidence');
const workRoot = resolve(experimentRoot, 'work');
const reviewPath = resolve(repositoryRoot, 'specs/review-render-spec.v0.1.json');
const configurator = resolve(repositoryRoot, 'blender/configure_eevee_threads.py');
const renderer = resolve(repositoryRoot, 'blender/render_b31_sampling_quality_derivation.py');
const analyzer = resolve(repositoryRoot, 'blender/analyze_b31_sampling_quality_derivation.py');
const blender = resolve(process.env.BLENDER_BIN || '/Applications/Blender.app/Contents/MacOS/Blender');
const serialize = value => `${JSON.stringify(value, null, 2)}\n`;

function run(command, args, env = process.env) {
  return new Promise((resolvePromise, reject) => {
    const child = spawn(command, args, { cwd: repositoryRoot, env, stdio: ['ignore', 'pipe', 'pipe'] });
    const processId = child.pid;
    let output = '';
    child.stdout.on('data', chunk => { output += chunk; });
    child.stderr.on('data', chunk => { output += chunk; });
    child.on('error', reject);
    child.on('close', code => code === 0 ? resolvePromise({ processId, output })
      : reject(new Error(`${command} failed (${code}) pid=${processId}\n${output}`)));
  });
}

await rm(evidenceRoot, { recursive: true, force: true });
await rm(workRoot, { recursive: true, force: true });
await mkdir(evidenceRoot, { recursive: true });
await mkdir(workRoot, { recursive: true });
const review = JSON.parse(await readFile(reviewPath, 'utf8'));
const receiptPath = resolve(repositoryRoot, review.source.receiptUri);
const receipt = JSON.parse(await readFile(receiptPath, 'utf8'));
const scenePath = resolve(repositoryRoot, receipt.run.sceneBlend.uri);
const ocioPath = resolve(repositoryRoot, receipt.executionIdentity.configuration.ocio.uri);
const frames = [37, 72, 103];
const schedule = [
  ['NATURAL32', 'A'], ['CENTER32', 'A'], ['REFERENCE1024', 'A'],
  ['NATURAL32', 'B'], ['CENTER32', 'B'], ['REFERENCE1024', 'B'],
];
const reports = [];
for (const [cell, replicate] of schedule) {
  const id = `${cell}_${replicate}`;
  const outputDir = resolve(workRoot, id);
  const reportPath = resolve(evidenceRoot, `${id}.json`);
  const interventionPath = resolve(evidenceRoot, `${id}.threads.json`);
  await mkdir(outputDir, { recursive: true });
  const launched = await run(blender, [
    '--background', scenePath, '--disable-autoexec', '--python-exit-code', '1',
    '--python', configurator, '--python', renderer, '--',
    '--review-spec', reviewPath, '--receipt', receiptPath, '--output-dir', outputDir,
    '--report', reportPath, '--cell', cell, '--replicate', replicate, '--frames', ...frames.map(String),
  ], { ...process.env, OCIO: ocioPath, BFS_B22_THREADS_MODE: 'FIXED', BFS_B22_THREADS: '8',
    BFS_B22_CELL: 'T08', BFS_B22_INTERVENTION_REPORT: interventionPath });
  const report = JSON.parse(await readFile(reportPath, 'utf8'));
  if (report.processId !== launched.processId) throw new Error(`${id} PID binding mismatch`);
  reports.push({ id, cell, replicate, processId: launched.processId, reportSha256: await sha256File(reportPath),
    totalRenderSeconds: report.totalRenderSeconds, outputHashes: report.outputs.map(item => item.sha256) });
  process.stdout.write(`BFS_B31_DERIVATION_PROCESS_OK ${id} pid=${launched.processId} seconds=${report.totalRenderSeconds}\n`);
}
const result = {
  documentType: 'BFS_B31_SAMPLING_QUALITY_DERIVATION_RESULT', version: '0.1.0',
  status: 'EXPLORATORY_DERIVATION_ONLY_NOT_CONFIRMATION', executedAtUtc: new Date().toISOString(),
  question: 'How does CENTER32 scene-linear error compare with NATURAL32 against a dual independent NATURAL1024 reference proxy?',
  design: { frames, schedule: schedule.map(([cell, replicate]) => `${cell}_${replicate}`),
    processes: 6, renderCalls: 18, referenceDefinition: 'mean of two independent NATURAL1024 EXR renders' },
  identities: { blenderSha256: await sha256File(blender), sceneBlendSha256: await sha256File(scenePath),
    ocioSha256: await sha256File(ocioPath), configuratorSha256: await sha256File(configurator),
    rendererSha256: await sha256File(renderer), analyzerSha256: await sha256File(analyzer),
    reviewRenderSpecSha256: await sha256File(reviewPath) },
  reports,
  nonClaims: ['Derivation only; no confirmatory quality threshold is defined.',
    'The 1024-sample mean is a reference proxy, not ground truth.',
    'Numerical error cannot replace temporal or human quality review.'],
};
const resultPath = resolve(experimentRoot, 'results.json');
await writeFile(resultPath, serialize(result));
const analysisPath = resolve(experimentRoot, 'analysis.json');
const analysisRun = await run(blender, ['--factory-startup', '--background', '--disable-autoexec', '--python-exit-code', '1',
  '--python', analyzer, '--', '--work-dir', workRoot, '--results', resultPath, '--output', analysisPath]);
process.stdout.write(analysisRun.output);
process.stdout.write(`BFS_B31_DERIVATION_OK processes=${reports.length} renders=${result.design.renderCalls}\n`);
