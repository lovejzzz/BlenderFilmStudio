import { spawn, spawnSync } from 'node:child_process';
import { createReadStream } from 'node:fs';
import { access, mkdir, readFile, realpath, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { dirname, relative, resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import {
  B36_CANARY_TOKEN,
  B36_PREREG_COMMIT,
  B36_SPEC_SHA256,
  analyzeB36,
  readB36Spec,
  runB36AnalyzerAttacks,
} from './lib/b36-autoexec-boundary.mjs';

const blender = '/Applications/Blender.app/Contents/MacOS/Blender';
const experimentRoot = resolve(repositoryRoot, 'experiments/autoexec-boundary-v0-1');
const workRoot = resolve(experimentRoot, 'work');
const runId = `run-${new Date().toISOString().replaceAll(':', '').replaceAll('.', '')}-${process.pid}`;
const runRoot = resolve(workRoot, runId);
const sourceBlend = resolve(runRoot, 'b36-registered-text-canary.blend');
const publicResultsPath = resolve(experimentRoot, 'results.json');
const buildScript = resolve(repositoryRoot, 'blender/build_b36_autoexec_canary.py');
const probeScript = resolve(repositoryRoot, 'blender/probe_b36_autoexec_state.py');
const spec = await readB36Spec();

const fileSha256 = path => new Promise((acceptPromise, rejectPromise) => {
  const hash = createHash('sha256');
  const stream = createReadStream(path);
  stream.on('data', chunk => hash.update(chunk));
  stream.on('error', rejectPromise);
  stream.on('end', () => acceptPromise(hash.digest('hex')));
});

const exists = async path => access(path).then(() => true, () => false);

function runProcess(command, args, env, timeoutMs) {
  return new Promise((acceptPromise, rejectPromise) => {
    const startedAt = Date.now();
    const child = spawn(command, args, { cwd: repositoryRoot, env, stdio: ['ignore', 'pipe', 'pipe'] });
    let output = '';
    let timedOut = false;
    child.stdout.on('data', chunk => { output += chunk; });
    child.stderr.on('data', chunk => { output += chunk; });
    child.on('error', rejectPromise);
    const timer = setTimeout(() => {
      timedOut = true;
      child.kill('SIGTERM');
    }, timeoutMs);
    child.on('close', exitCode => {
      clearTimeout(timer);
      acceptPromise({ processId: child.pid, exitCode, timedOut, durationMs: Date.now() - startedAt, output });
    });
  });
}

const preregCheck = spawnSync('git', ['merge-base', '--is-ancestor', B36_PREREG_COMMIT, 'HEAD'], { cwd: repositoryRoot });
if (preregCheck.status !== 0) throw new Error(`B36 prereg commit ${B36_PREREG_COMMIT} is not an ancestor of HEAD`);
const binarySha = await fileSha256(blender);
if (binarySha !== spec.runtime.blenderBinarySha256) throw new Error(`B36 Blender binary SHA mismatch: ${binarySha}`);

await mkdir(workRoot, { recursive: true });
await mkdir(runRoot, { recursive: false });
const canonicalWorkRoot = await realpath(workRoot);
const build = await runProcess(
  blender,
  ['--background', '--factory-startup', '--python', buildScript, '--', '--output', sourceBlend, '--allowed-root', canonicalWorkRoot],
  process.env,
  spec.runtime.timeoutSecondsPerProcess * 1000,
);
await writeFile(resolve(runRoot, 'build.log'), build.output);
if (build.exitCode !== 0 || build.timedOut || !(await exists(sourceBlend))) {
  throw new Error(`B36 canary build failed: exit=${build.exitCode} timeout=${build.timedOut}`);
}
const sourceBlendSha256Pre = await fileSha256(sourceBlend);

const cells = [];
for (const definition of spec.cells) {
  const cellRoot = resolve(runRoot, definition.id);
  const markerPath = resolve(cellRoot, 'embedded-marker.json');
  const reportPath = resolve(cellRoot, 'trusted-probe.json');
  const logPath = resolve(cellRoot, 'blender.log');
  await mkdir(cellRoot, { recursive: false });
  const canonicalCellRoot = await realpath(cellRoot);
  if (!canonicalCellRoot.startsWith(`${canonicalWorkRoot}/`)) throw new Error(`B36 cell escaped work root: ${definition.id}`);
  const markerAbsentBeforeLaunch = !(await exists(markerPath));
  const args = ['--background', '--factory-startup'];
  if (definition.autoexec === 'ENABLE') args.push('--enable-autoexec');
  if (definition.autoexec === 'DISABLE') args.push('--disable-autoexec');
  args.push(sourceBlend, '--python', probeScript);
  const processResult = await runProcess(
    blender,
    args,
    {
      ...process.env,
      BFS_B36_FAKE_SECRET: B36_CANARY_TOKEN,
      BFS_B36_MARKER_PATH: markerPath,
      BFS_B36_REPORT_PATH: reportPath,
      BFS_B36_ALLOWED_ROOT: canonicalWorkRoot,
    },
    spec.runtime.timeoutSecondsPerProcess * 1000,
  );
  await writeFile(logPath, processResult.output);
  const report = await exists(reportPath) ? JSON.parse(await readFile(reportPath, 'utf8')) : null;
  const marker = await exists(markerPath) ? JSON.parse(await readFile(markerPath, 'utf8')) : null;
  const cell = {
    id: definition.id,
    autoexec: definition.autoexec,
    expectedMarker: definition.expectedMarker,
    markerAbsentBeforeLaunch,
    processId: processResult.processId,
    exitCode: processResult.exitCode,
    timedOut: processResult.timedOut,
    durationMs: processResult.durationMs,
    report,
    marker,
  };
  cells.push(cell);
  process.stdout.write(
    `BFS_B36_CELL ${cell.id} pid=${cell.processId} exit=${cell.exitCode} `
    + `marker=${cell.marker !== null} autoexecFail=${cell.report?.autoexecFail ?? 'NO_REPORT'}\n`,
  );
}

const sourceBlendSha256Post = await fileSha256(sourceBlend);
const evidence = {
  schemaVersion: 'bfs.autoexecBoundaryEvidence.v0.1',
  experimentId: 'B36',
  status: 'REAL_BLENDER_RUN_COMPLETE',
  preregistration: { commit: B36_PREREG_COMMIT, specSha256: B36_SPEC_SHA256 },
  runtime: { blender, blenderBinarySha256: binarySha, generatorProcessId: build.processId },
  runId,
  sourceBlendPath: relative(repositoryRoot, sourceBlend),
  sourceBlendSha256Pre,
  sourceBlendSha256Post,
  cells,
};
const analysis = analyzeB36(evidence);
const attacks = analysis.passed ? runB36AnalyzerAttacks(evidence) : [];
const attacksPassed = attacks.length === 7 && attacks.every(attack => attack.passed);
const verdict = analysis.passed && attacksPassed
  ? 'REGISTERED_TEXT_AUTOEXEC_FLAG_BOUNDARY_SUPPORT'
  : analysis.decision;
const publicResult = {
  ...evidence,
  analysis,
  attacks,
  attacksPassed,
  verdict,
  nonClaims: spec.nonClaims,
};
await mkdir(dirname(publicResultsPath), { recursive: true });
await writeFile(publicResultsPath, `${JSON.stringify(publicResult, null, 2)}\n`);
process.stdout.write(
  `BFS_B36_RESULT verdict=${verdict} cells=${cells.length} uniquePids=${new Set(cells.map(cell => cell.processId)).size} `
  + `enabledMarkers=${cells.filter(cell => cell.autoexec === 'ENABLE' && cell.marker).length}/2 `
  + `blockedMarkers=${cells.filter(cell => cell.autoexec !== 'ENABLE' && !cell.marker).length}/4 attacks=${attacks.filter(attack => attack.passed).length}/7\n`,
);
if (!analysis.passed || !attacksPassed) process.exitCode = 1;
