import { spawn, spawnSync } from 'node:child_process';
import { createReadStream } from 'node:fs';
import { createServer } from 'node:net';
import { access, mkdir, readFile, realpath, writeFile } from 'node:fs/promises';
import { createHash, randomBytes } from 'node:crypto';
import { dirname, relative, resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import {
  B37_FAKE_SECRET,
  B37_PREREG_COMMIT,
  B37_SPEC_SHA256,
  analyzeB37,
  readB37Spec,
  runB37AnalyzerAttacks,
} from './lib/b37-worker-containment.mjs';

const blender = '/Applications/Blender.app/Contents/MacOS/Blender';
const sandboxExec = '/usr/bin/sandbox-exec';
const experimentRoot = resolve(repositoryRoot, 'experiments/worker-containment-v0-1');
const workRoot = resolve(experimentRoot, 'work');
const runId = `run-${new Date().toISOString().replaceAll(':', '').replaceAll('.', '')}-${process.pid}`;
const runRoot = resolve(workRoot, runId);
const publicResultsPath = resolve(experimentRoot, 'results.json');
const probeScript = resolve(repositoryRoot, 'blender/probe_b37_worker_containment.py');
const spec = await readB37Spec();

const fileSha256 = path => new Promise((acceptPromise, rejectPromise) => {
  const hash = createHash('sha256');
  const stream = createReadStream(path);
  stream.on('data', chunk => hash.update(chunk));
  stream.on('error', rejectPromise);
  stream.on('end', () => acceptPromise(hash.digest('hex')));
});
const exists = path => access(path).then(() => true, () => false);

function runProcess(command, args, env, timeoutMs) {
  return new Promise((acceptPromise, rejectPromise) => {
    const startedAt = Date.now();
    const child = spawn(command, args, { cwd: repositoryRoot, env, stdio: ['ignore', 'pipe', 'pipe'] });
    let output = '';
    let timedOut = false;
    child.stdout.on('data', chunk => { output += chunk; });
    child.stderr.on('data', chunk => { output += chunk; });
    child.on('error', rejectPromise);
    const timer = setTimeout(() => { timedOut = true; child.kill('SIGTERM'); }, timeoutMs);
    child.on('close', exitCode => {
      clearTimeout(timer);
      acceptPromise({ processId: child.pid, exitCode, timedOut, durationMs: Date.now() - startedAt, output });
    });
  });
}

function openLoopbackServer() {
  const receipts = [];
  const server = createServer(socket => {
    socket.setEncoding('utf8');
    let text = '';
    socket.on('data', chunk => { text += chunk; });
    socket.on('end', () => { if (text.trim()) receipts.push(text.trim()); });
    socket.write('OK\n');
    socket.end();
  });
  return new Promise((acceptPromise, rejectPromise) => {
    server.once('error', rejectPromise);
    server.listen(0, '127.0.0.1', () => acceptPromise({ server, receipts, port: server.address().port }));
  });
}

const sbplString = controlRoot => `
(version 1)
(allow default)
(deny network*)
(deny file-read* (subpath ${JSON.stringify(controlRoot)}))
(deny file-write* (subpath ${JSON.stringify(controlRoot)}))
(deny process-exec)
(allow process-exec (literal ${JSON.stringify(blender)}))
`.trim() + '\n';

const preregCheck = spawnSync('git', ['merge-base', '--is-ancestor', B37_PREREG_COMMIT, 'HEAD'], { cwd: repositoryRoot });
if (preregCheck.status !== 0) throw new Error(`B37 prereg commit ${B37_PREREG_COMMIT} is not an ancestor of HEAD`);
if (await fileSha256(blender) !== spec.runtime.blenderSha256) throw new Error('B37 Blender binary SHA mismatch');
if (await fileSha256(sandboxExec) !== spec.runtime.sandboxExecSha256) throw new Error('B37 sandbox-exec binary SHA mismatch');
const swVers = spawnSync('sw_vers', [], { encoding: 'utf8' });
if (swVers.status !== 0 || !swVers.stdout.includes(`ProductVersion:\t\t${spec.runtime.osVersion}`) || !swVers.stdout.includes(`BuildVersion:\t\t${spec.runtime.osBuild}`)) {
  throw new Error(`B37 OS identity mismatch: ${swVers.stdout}`);
}

await mkdir(workRoot, { recursive: true });
await mkdir(runRoot, { recursive: false });
const canonicalRunRoot = await realpath(runRoot);
const cells = [];
for (const definition of spec.cells) {
  const cellRoot = resolve(runRoot, definition.id);
  const workerRoot = resolve(cellRoot, 'worker');
  const controlRoot = resolve(cellRoot, 'control-outside-worker');
  await mkdir(workerRoot, { recursive: true });
  await mkdir(controlRoot, { recursive: true });
  const canonicalWorkerRoot = await realpath(workerRoot);
  const canonicalControlRoot = await realpath(controlRoot);
  if (!canonicalWorkerRoot.startsWith(`${canonicalRunRoot}/`) || !canonicalControlRoot.startsWith(`${canonicalRunRoot}/`)) {
    throw new Error(`B37 cell path escaped run root: ${definition.id}`);
  }
  const reportPath = resolve(workerRoot, 'probe-report.json');
  const allowedMarker = resolve(workerRoot, 'allowed-write.txt');
  const childMarker = resolve(workerRoot, 'child-touch.txt');
  const outsideReadPath = resolve(controlRoot, 'outside-read-canary.txt');
  const outsideWritePath = resolve(controlRoot, 'outside-write-canary.txt');
  const profilePath = resolve(cellRoot, 'profile.sb');
  const logPath = resolve(cellRoot, 'blender.log');
  await writeFile(outsideReadPath, `B37_OUTSIDE_READ_${definition.id}\n`);
  if (definition.sandbox) await writeFile(profilePath, sbplString(canonicalControlRoot));
  const cleanPreflight = !(await exists(reportPath)) && !(await exists(allowedMarker)) && !(await exists(childMarker)) && !(await exists(outsideWritePath));
  const loopback = await openLoopbackServer();
  const loopbackNonce = `B37_${definition.id}_${randomBytes(8).toString('hex')}`;
  const blenderArgs = ['--background', '--factory-startup', '--disable-autoexec', '--python', probeScript];
  const command = definition.sandbox ? sandboxExec : blender;
  const args = definition.sandbox ? ['-f', profilePath, blender, ...blenderArgs] : blenderArgs;
  const env = {
    ...process.env,
    BFS_B37_WORKER_ROOT: canonicalWorkerRoot,
    BFS_B37_CONTROL_ROOT: canonicalControlRoot,
    BFS_B37_REPORT_PATH: reportPath,
    BFS_B37_ALLOWED_MARKER: allowedMarker,
    BFS_B37_OUTSIDE_READ_PATH: outsideReadPath,
    BFS_B37_OUTSIDE_WRITE_PATH: outsideWritePath,
    BFS_B37_CHILD_MARKER: childMarker,
    BFS_B37_LOOPBACK_PORT: String(loopback.port),
    BFS_B37_LOOPBACK_NONCE: loopbackNonce,
  };
  if (definition.sanitizeFakeSecret) delete env.BFS_B37_FAKE_SECRET;
  else env.BFS_B37_FAKE_SECRET = B37_FAKE_SECRET;
  const processResult = await runProcess(command, args, env, spec.runtime.timeoutSecondsPerProcess * 1000);
  await new Promise(acceptPromise => setTimeout(acceptPromise, 100));
  await new Promise(acceptPromise => loopback.server.close(acceptPromise));
  await writeFile(logPath, processResult.output);
  const report = await exists(reportPath) ? JSON.parse(await readFile(reportPath, 'utf8')) : null;
  const cellClass = definition.id.startsWith('UNSANDBOXED') ? 'UNSANDBOXED'
    : definition.id.startsWith('SBPL_INHERITED') ? 'SBPL_INHERITED'
      : 'SBPL_SANITIZED';
  const cell = {
    id: definition.id,
    class: cellClass,
    sandbox: definition.sandbox,
    sanitizeFakeSecret: definition.sanitizeFakeSecret,
    cleanPreflight,
    processId: processResult.processId,
    exitCode: processResult.exitCode,
    timedOut: processResult.timedOut,
    durationMs: processResult.durationMs,
    loopbackNonce,
    loopbackReceipts: loopback.receipts,
    report,
  };
  cells.push(cell);
  const compact = report?.capabilities
    ? Object.entries(report.capabilities).map(([key, value]) => `${key}=${value.success}`).join(' ')
    : 'NO_REPORT';
  process.stdout.write(`BFS_B37_CELL ${cell.id} pid=${cell.processId} exit=${cell.exitCode} ${compact}\n`);
}

const evidence = {
  schemaVersion: 'bfs.workerContainmentEvidence.v0.1',
  experimentId: 'B37',
  status: 'REAL_BLENDER_RUN_COMPLETE',
  preregistration: { commit: B37_PREREG_COMMIT, specSha256: B37_SPEC_SHA256 },
  runtime: {
    osVersion: spec.runtime.osVersion,
    osBuild: spec.runtime.osBuild,
    sandboxExec,
    sandboxExecSha256: spec.runtime.sandboxExecSha256,
    sandboxExecStatus: spec.runtime.sandboxExecStatus,
    blender,
    blenderSha256: spec.runtime.blenderSha256,
    blenderHasAppSandboxEntitlement: false,
  },
  runId,
  runRoot: relative(repositoryRoot, runRoot),
  cells,
};
const analysis = analyzeB37(evidence);
const attacks = analysis.passed ? runB37AnalyzerAttacks(evidence) : [];
const attacksPassed = attacks.length === 9 && attacks.every(attack => attack.passed);
const verdict = analysis.passed && attacksPassed ? 'DEPRECATED_SBPL_CANARY_SUPPORT_WITH_ENV_COUNTEREXAMPLE' : analysis.decision;
const publicResult = { ...evidence, analysis, attacks, attacksPassed, verdict, nonClaims: spec.nonClaims };
await mkdir(dirname(publicResultsPath), { recursive: true });
await writeFile(publicResultsPath, `${JSON.stringify(publicResult, null, 2)}\n`);
process.stdout.write(
  `BFS_B37_RESULT verdict=${verdict} cells=${cells.length} uniquePids=${new Set(cells.map(cell => cell.processId)).size} `
  + `attacks=${attacks.filter(attack => attack.passed).length}/9\n`,
);
if (!analysis.passed || !attacksPassed) process.exitCode = 1;
