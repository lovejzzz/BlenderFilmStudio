import { mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256File } from './lib/receipt-format.mjs';

const root = resolve(repositoryRoot, 'experiments/fixed-jitter-derivation-v0-1');
const evidence = resolve(root, 'evidence');
const work = resolve(root, 'work');
const blender = resolve('/Applications/Blender.app/Contents/MacOS/Blender');
const scene = resolve(repositoryRoot, 'experiments/compile-receipt-v0-1/evidence/B02-A/scene.blend');
const ocio = resolve(repositoryRoot, 'color/ocio/cg-config-v4.0.0_aces-v2.0_ocio-v2.5.ocio');
const configurator = resolve(repositoryRoot, 'blender/configure_eevee_threads.py');
const renderer = resolve(repositoryRoot, 'blender/explore_b30_fixed_jitter.py');
const cells = [
  { id: 'NATURAL', jitter: null },
  { id: 'CENTER', jitter: [0, 0] },
  { id: 'POS_QUARTER', jitter: [0.25, 0.25] },
  { id: 'NEG_QUARTER', jitter: [-0.25, -0.25] },
];
const run = (command, args, env = process.env) => new Promise((resolvePromise, reject) => {
  const child = spawn(command, args, { cwd: repositoryRoot, env, stdio: ['ignore', 'pipe', 'pipe'] });
  const processId = child.pid;
  let output = '';
  child.stdout.on('data', chunk => { output += chunk; }); child.stderr.on('data', chunk => { output += chunk; });
  child.on('error', reject); child.on('close', code => code === 0 ? resolvePromise({ processId, output }) : reject(new Error(`${command} failed (${code})\n${output}`)));
});

await rm(evidence, { recursive: true, force: true });
await rm(work, { recursive: true, force: true });
await mkdir(evidence, { recursive: true });
await mkdir(work, { recursive: true });
const reports = [];
for (const cell of cells) {
  const outputDir = resolve(work, cell.id);
  const reportPath = resolve(evidence, `${cell.id}.json`);
  const intervention = resolve(evidence, `${cell.id}.intervention.json`);
  await mkdir(outputDir, { recursive: true });
  const args = ['--background', scene, '--disable-autoexec', '--python-exit-code', '1', '--python', configurator, '--python', renderer, '--', '--cell', cell.id, '--output-dir', outputDir, '--report', reportPath];
  if (cell.jitter) args.push('--jitter', String(cell.jitter[0]), String(cell.jitter[1]));
  const launched = await run(blender, args, { ...process.env, OCIO: ocio, BFS_B22_THREADS_MODE: 'FIXED', BFS_B22_THREADS: '8', BFS_B22_CELL: 'T08', BFS_B22_INTERVENTION_REPORT: intervention });
  const report = JSON.parse(await readFile(reportPath, 'utf8'));
  if (report.processId !== launched.processId) throw new Error(`${cell.id} PID binding mismatch`);
  reports.push({ cell: cell.id, jitter: cell.jitter, processId: launched.processId, reportSha256: await sha256File(reportPath), uniqueDecodedRgbHashes: report.uniqueDecodedRgbHashes, frequencies: report.frequencies, totalSeconds: report.outputs.reduce((sum, item) => sum + item.seconds, 0) });
  process.stdout.write(`BFS_B30_DERIVATION_PROCESS_OK ${cell.id} pid=${launched.processId} variants=${report.uniqueDecodedRgbHashes}\n`);
}
const result = { documentType: 'BFS_B30_FIXED_JITTER_DERIVATION_RESULT', version: '0.1.0', status: 'EXPLORATORY_DERIVATION_ONLY_NOT_CONFIRMATION', executedAtUtc: new Date().toISOString(), question: 'Which preselected fixed filter-jitter positions are suitable candidates for a later natural-versus-fixed confirmatory intervention?', design: { cells, processes: 4, renderCallsPerProcess: 12, renderCalls: 48, noFormalDecision: true }, identities: { blenderSha256: await sha256File(blender), sceneBlendSha256: await sha256File(scene), ocioSha256: await sha256File(ocio), configuratorSha256: await sha256File(configurator), rendererSha256: await sha256File(renderer) }, reports, nonClaims: ['This derivation selects fixed-jitter candidates and cannot confirm a causal mechanism.', 'Fixed pixel jitter changes the sampling target and may reduce anti-aliasing quality.', 'One process per cell does not estimate process-level recurrence probability.'] };
await writeFile(resolve(root, 'results.json'), `${JSON.stringify(result, null, 2)}\n`);
process.stdout.write(`BFS_B30_DERIVATION_OK ${reports.map(item => `${item.cell}:${item.uniqueDecodedRgbHashes}`).join(' ')}\n`);
