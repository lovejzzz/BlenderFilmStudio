#!/usr/bin/env node

import { spawn, execFile } from 'node:child_process';
import { lstat, open, readFile, statfs } from 'node:fs/promises';
import { dirname, relative, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { promisify } from 'node:util';
import { runBudgetedProcess, measureOutput } from './lib/budgeted-process.mjs';
import {
  acquireWriterLease,
  appendLedgerEvent,
  canonicalJson,
  compareRecordedProcess,
  createManifest,
  deriveJobState,
  durableMkdir,
  readJson,
  readProcessIdentity,
  releaseWriterLease,
  sha256Bytes,
  sha256File,
  validSelfHash,
  writeExclusiveDurableHashed,
  writeStageReceipt,
} from './lib/restart-safe-job-ledger.mjs';
import { repositoryRoot } from './lib/scene-spec.mjs';

const execFileAsync = promisify(execFile);
const BLENDER = '/Applications/Blender.app/Contents/MacOS/Blender';
const FFMPEG = '/opt/homebrew/bin/ffmpeg';
const FFPROBE = '/opt/homebrew/bin/ffprobe';
const SPEC_URI = 'specs/b62-terminal-cycles-restart.v0.1.json';
const PROTOCOL_URI = 'research/2026-08-29-b62-t3-terminal-cycles-restart-protocol.md';
const CORRECTION_URI = 'specs/b62-terminal-cycles-restart-c1-preflight-reference.v0.1.json';
const CORRECTION_PROTOCOL_URI = 'research/2026-08-29-b62-t3-c1-preflight-reference.md';
const RENDER_URI = 'blender/render_b62_terminal_cycles_shot.py';
const EXR_AUDITOR_URI = 'blender/audit_b62_terminal_cycles_exr.py';
const ORCHESTRATOR_URI = 'scripts/run-b62-terminal-cycles-restart.mjs';
const FINAL_AUDITOR_URI = 'scripts/audit-b62-terminal-cycles-restart.mjs';
const LEDGER_URI = 'scripts/lib/restart-safe-job-ledger.mjs';
const BUDGET_URI = 'scripts/lib/budgeted-process.mjs';
const SCENE_URI = 'experiments/b62-terminal-scene-package-v0-3/scene/B62_TERMINAL_PRODUCTION.blend';
const PREFLIGHT_URI = 'experiments/b62-terminal-cycles-restart-preflight-v0-2';
const JOB_URI = 'experiments/b62-terminal-cycles-restart-job-v0-2';
const FORMAL_URI = 'experiments/b62-terminal-cycles-restart-v0-2';
const JOB_ID = 'B62-TERMINAL-CYCLES-RESTART-J01';
const OCIO_URI = 'color/ocio/cg-config-v4.0.0_aces-v2.0_ocio-v2.5.ocio';
const TOOL_PATHS = [SPEC_URI, PROTOCOL_URI, CORRECTION_URI, CORRECTION_PROTOCOL_URI, RENDER_URI, EXR_AUDITOR_URI, ORCHESTRATOR_URI, FINAL_AUDITOR_URI, LEDGER_URI, BUDGET_URI];
const RESTRICTED_COMMANDS = [BLENDER, FFMPEG, FFPROBE, FINAL_AUDITOR_URI];
const MINIMUM_RESERVE = 107374182400;
const PROJECTED_WRITE = 6442450944;
const MAX_OUTPUT = 8589934592;
const SHOT_STAGE = { WIDE: 'RENDER_WIDE', MEDIUM: 'RENDER_MEDIUM', CLOSE: 'RENDER_CLOSE' };
const SHOT_ATTEMPT = { WIDE: 'WIDE-RETRY-0002', MEDIUM: 'MEDIUM-0001', CLOSE: 'CLOSE-0001' };

function require(condition, message) {
  if (!condition) throw new Error(message);
}

function parseArguments(argv) {
  const parsed = { mode: null, toolFreezeCommit: null };
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--mode') parsed.mode = argv[++index];
    else if (token === '--tool-freeze-commit') parsed.toolFreezeCommit = argv[++index];
    else throw new Error(`Unknown or incomplete argument ${token}`);
  }
  require(['start', 'resume'].includes(parsed.mode), '--mode must be start or resume');
  if (parsed.mode === 'start') require(/^[0-9a-f]{40}$/.test(parsed.toolFreezeCommit ?? ''), 'start requires full --tool-freeze-commit');
  if (parsed.mode === 'resume') require(parsed.toolFreezeCommit === null, 'resume reads freeze commit from manifest');
  return parsed;
}

async function git(args, encoding = 'utf8') {
  const result = await execFileAsync('/usr/bin/git', args, {
    cwd: repositoryRoot, encoding, timeout: 20000, maxBuffer: 64 * 1024 * 1024,
    env: { PATH: '/usr/bin:/bin', LANG: 'C', LC_ALL: 'C', GIT_CONFIG_NOSYSTEM: '1', GIT_TERMINAL_PROMPT: '0' },
  });
  return result.stdout;
}

async function verifyFreeze(commit) {
  const origin = (await git(['rev-parse', 'origin/main'])).trim();
  await git(['merge-base', '--is-ancestor', commit, origin]);
  const hashes = {};
  for (const uri of TOOL_PATHS) {
    const current = await sha256File(resolve(repositoryRoot, uri));
    const frozen = sha256Bytes(await git(['show', `${commit}:${uri}`], null));
    require(current === frozen, `frozen tool mismatch ${uri}`);
    hashes[uri] = current;
  }
  return { commit, origin, hashes };
}

function pythonNormalize(value) {
  if (Array.isArray(value)) return value.map(pythonNormalize);
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).map(([key, child]) => [key, pythonNormalize(child)]));
  if (Object.is(value, -0)) return 0;
  if (typeof value === 'number' && !Number.isInteger(value)) {
    const bytes = Buffer.allocUnsafe(8); bytes.writeDoubleBE(value); return { $f64be: bytes.toString('hex') };
  }
  return value;
}

function pythonSelfHash(value, field) {
  const body = structuredClone(value); delete body[field];
  return sha256Bytes(Buffer.from(canonicalJson(pythonNormalize(body))));
}

function repoUri(path) {
  const uri = relative(repositoryRoot, path).replaceAll('\\', '/');
  require(uri && !uri.startsWith('../'), `path outside repository ${path}`);
  return uri;
}

async function durableBuffer(path, bytes) {
  await durableMkdir(dirname(path));
  const handle = await open(path, 'wx', 0o600);
  try { await handle.writeFile(bytes); await handle.sync(); } finally { await handle.close(); }
  const directory = await open(dirname(path), 'r'); try { await directory.sync(); } finally { await directory.close(); }
  return { uri: repoUri(path), sha256: sha256Bytes(bytes), bytes: bytes.length };
}

async function receiptReference(jobRoot, result) {
  return { uri: relative(jobRoot, result.path).replaceAll('\\', '/'), sha256: result.file.sha256, receiptHash: result.receipt.receiptHash };
}

async function finishStage(jobRoot, stageId, attemptId, evidence) {
  const receipt = await writeStageReceipt(jobRoot, stageId, attemptId, { status: 'COMPLETED', promotable: true, ...evidence });
  await appendLedgerEvent(jobRoot, { eventType: 'STAGE_COMPLETED', stageId, attemptId, payload: { receipt: await receiptReference(jobRoot, receipt) } });
  return receipt;
}

async function startStage(jobRoot, stageId, attemptId, payload = {}) {
  await appendLedgerEvent(jobRoot, { eventType: 'STAGE_STARTED', stageId, attemptId, payload });
}

async function requireCapacity(projected = 0) {
  const fs = await statfs(repositoryRoot);
  const freeBytes = Number(fs.bavail) * Number(fs.bsize);
  require(freeBytes - projected >= MINIMUM_RESERVE, `disk reserve gate: ${freeBytes} free, ${projected} projected`);
  return { freeBytes, projectedBytes: projected, requiredPostWriteReserveBytes: MINIMUM_RESERVE };
}

async function findCodexHostIdentity() {
  let identity = await readProcessIdentity(process.pid);
  for (let depth = 0; depth < 24 && identity.live && identity.parentPid > 1; depth += 1) {
    identity = await readProcessIdentity(identity.parentPid);
    if (identity.live && identity.argv.includes('/Applications/ChatGPT.app/Contents/Resources/codex') && identity.argv.includes('app-server')) return identity;
  }
  throw new Error('could not resolve ChatGPT/Codex app-server ancestor identity');
}

function blenderArgs(script, extra, source = SCENE_URI) {
  const initial = source ? ['--background', resolve(repositoryRoot, source)] : ['--background', '--factory-startup'];
  return [...initial, '--disable-autoexec', '--python-exit-code', '1', '--python', resolve(repositoryRoot, script), '--', '--repository-root', repositoryRoot, ...extra];
}

function frozenEnv() {
  return { PATH: '/opt/homebrew/bin:/usr/bin:/bin', LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8', OCIO: resolve(repositoryRoot, OCIO_URI) };
}

async function controlledInterruption(jobRoot) {
  const stageId = 'INTERRUPT_WIDE_PROBE';
  const attemptId = 'WIDE-INTERRUPTED-0001';
  await startStage(jobRoot, stageId, attemptId, { purpose: 'controlled native Blender interruption before first render' });
  const attemptRoot = resolve(jobRoot, 'attempts', stageId, attemptId);
  await durableMkdir(attemptRoot);
  const report = resolve(attemptRoot, 'shot-report.json');
  const goFile = resolve(attemptRoot, 'GO');
  const args = blenderArgs(RENDER_URI, ['--attempt-root', attemptRoot, '--mode', 'interrupt-probe', '--shot', 'WIDE', '--go-file', goFile, '--report', report]);
  const child = spawn(BLENDER, args, { cwd: repositoryRoot, env: frozenEnv(), detached: true, stdio: ['ignore', 'pipe', 'pipe'] });
  const stdout = []; const stderr = []; let combined = ''; let markerResolve; let markerReject;
  const marker = new Promise((resolvePromise, reject) => { markerResolve = resolvePromise; markerReject = reject; });
  const timeout = setTimeout(() => markerReject(new Error('controlled interruption marker timeout')), 60000);
  child.stdout.on('data', chunk => { stdout.push(chunk); combined += chunk.toString('utf8'); if (combined.includes('BFS_T3_READY_FOR_CONTROLLED_INTERRUPT')) markerResolve(); });
  child.stderr.on('data', chunk => stderr.push(chunk));
  const closed = new Promise((resolvePromise, reject) => { child.on('error', reject); child.on('close', (exitCode, signal) => resolvePromise({ exitCode, signal })); });
  let processIdentity;
  try {
    await marker;
    clearTimeout(timeout);
    processIdentity = await readProcessIdentity(child.pid);
    require(processIdentity.live, 'interrupted Blender identity unavailable');
    const pre = await measureOutput(attemptRoot);
    require(pre.fileCount === 0 && pre.bytes === 0, 'interrupt probe wrote accepted output before termination');
    process.kill(-child.pid, 'SIGTERM');
  } catch (error) {
    clearTimeout(timeout);
    try { process.kill(-child.pid, 'SIGKILL'); } catch {}
    await closed.catch(() => {});
    throw error;
  }
  const terminal = await closed;
  const stdoutFile = await durableBuffer(resolve(attemptRoot, 'stdout.log'), Buffer.concat(stdout));
  const stderrFile = await durableBuffer(resolve(attemptRoot, 'stderr.log'), Buffer.concat(stderr));
  const reportState = await lstat(report).catch(error => error.code === 'ENOENT' ? null : Promise.reject(error));
  require(terminal.signal === 'SIGTERM' && reportState === null && !(await measureOutput(attemptRoot)).symlinkCount, 'controlled Blender did not terminate by SIGTERM');
  const failed = await writeExclusiveDurableHashed(resolve(attemptRoot, 'receipt.json'), {
    schemaVersion: 'bfs.restartSafeProductionAttemptReceipt.v0.1', jobId: JOB_ID, stageId, attemptId,
    status: 'FAILED', promotable: false, reason: 'CONTROLLED_SIGTERM_BEFORE_RENDER', process: processIdentity,
    terminal, marker: 'BFS_T3_READY_FOR_CONTROLLED_INTERRUPT', acceptedRenderCalls: 0,
    outputsBeforeLogs: { fileCount: 0, bytes: 0 }, logs: { stdout: stdoutFile, stderr: stderrFile },
  }, 'receiptHash');
  await appendLedgerEvent(jobRoot, { eventType: 'STAGE_FAILED', stageId, attemptId, payload: { receipt: { uri: relative(jobRoot, failed.path).replaceAll('\\', '/'), sha256: failed.file.sha256, receiptHash: failed.record.receiptHash } } });
  const verifyAttempt = 'WIDE-INTERRUPTION-VERIFIED-0002';
  await startStage(jobRoot, stageId, verifyAttempt, { failedAttemptId: attemptId });
  return finishStage(jobRoot, stageId, verifyAttempt, {
    controlledInterruption: { failedReceipt: { uri: repoUri(failed.path), sha256: failed.file.sha256, receiptHash: failed.record.receiptHash }, process: processIdentity, terminal, acceptedRenderCalls: 0 },
    operations: { blenderStarts: 1, renderCalls: 0, modelCalls: 0, videoModelCalls: 0, networkCalls: 0, dockerProcesses: 0, colimaProcesses: 0 },
  });
}

function parseTiming(text) {
  const seconds = label => Number(text.match(new RegExp(`^${label}\\s+([0-9.]+)`, 'm'))?.[1] ?? NaN);
  const maximumResidentSetSizeBytes = Number(text.match(/^\s*([0-9]+)\s+maximum resident set size/m)?.[1] ?? NaN);
  const timing = { realSeconds: seconds('real'), userSeconds: seconds('user'), systemSeconds: seconds('sys'), maximumResidentSetSizeBytes };
  require(Object.values(timing).every(Number.isFinite), `invalid /usr/bin/time output: ${text}`);
  return timing;
}

async function renderShot(jobRoot, shot) {
  const stageId = SHOT_STAGE[shot]; const attemptId = SHOT_ATTEMPT[shot];
  await startStage(jobRoot, stageId, attemptId, { shot });
  const attemptRoot = resolve(jobRoot, 'attempts', stageId, attemptId);
  await durableMkdir(attemptRoot);
  const report = resolve(attemptRoot, 'shot-report.json');
  const timingPath = resolve(attemptRoot, 'time.txt');
  const capacityBefore = await requireCapacity(PROJECTED_WRITE);
  const args = ['-lp', '-o', timingPath, BLENDER, ...blenderArgs(RENDER_URI, ['--attempt-root', attemptRoot, '--mode', 'render-shot', '--shot', shot, '--report', report])];
  process.stdout.write(`BFS_T3_SHOT_START shot=${shot} attempt=${attemptId}\n`);
  const result = await runBudgetedProcess({
    command: '/usr/bin/time', args, cwd: repositoryRoot, env: frozenEnv(), outputRoot: jobRoot,
    budgets: { wallTimeMs: 7200000, maxRssBytes: 6442450944, maxLogBytes: 16777216, maxOutputFiles: 1200, maxOutputBytes: MAX_OUTPUT, sampleIntervalMs: 1000 },
  });
  require(result.outcome === 'PASS' && result.child.exitCode === 0 && result.child.signal === null, `${shot} Blender failed: ${JSON.stringify(result)}`);
  const timingBytes = await readFile(timingPath);
  const timing = parseTiming(timingBytes.toString('utf8'));
  require(timing.maximumResidentSetSizeBytes <= 6442450944, `${shot} Blender RSS budget exceeded`);
  const reportBytes = await readFile(report);
  const shotReport = JSON.parse(reportBytes);
  require(shotReport.schemaVersion === 'bfs.b62TerminalCyclesShotReport.v0.1' && shotReport.status === 'PASS' && shotReport.shot === shot && shotReport.frameCount === 96, `${shot} shot report invalid`);
  require(shotReport.reportHash === pythonSelfHash(shotReport, 'reportHash'), `${shot} shot report self-hash mismatch`);
  const capacityAfter = await requireCapacity(0);
  process.stdout.write(`BFS_T3_SHOT_COMPLETE shot=${shot} seconds=${timing.realSeconds} rss=${timing.maximumResidentSetSizeBytes}\n`);
  return finishStage(jobRoot, stageId, attemptId, {
    shot, shotReport: { uri: repoUri(report), sha256: sha256Bytes(reportBytes), reportHash: shotReport.reportHash },
    process: result, timing, timingFile: { uri: repoUri(timingPath), sha256: sha256Bytes(timingBytes), bytes: timingBytes.length },
    capacityBefore, capacityAfter,
    artifactCounts: { exr: 96, png: 96, frameReports: 96 },
    operations: shotReport.operations,
  });
}

async function acceptedManifest(jobRoot, spec) {
  const frames = [];
  for (const shot of ['WIDE', 'MEDIUM', 'CLOSE']) {
    const stageId = SHOT_STAGE[shot];
    const state = await deriveJobState(jobRoot);
    const stage = state.stages[stageId];
    require(stage.status === 'COMPLETED', `${stageId} incomplete`);
    const reference = stage.completed.receipt.shotReport;
    const reportPath = resolve(repositoryRoot, reference.uri);
    require(await sha256File(reportPath) === reference.sha256, `${shot} shot report file mismatch`);
    const report = JSON.parse(await readFile(reportPath, 'utf8'));
    require(report.reportHash === reference.reportHash && report.reportHash === pythonSelfHash(report, 'reportHash'), `${shot} report binding mismatch`);
    for (const binding of report.frameBindings) frames.push({ frame: binding.frame, shot, report: binding.report, exr: binding.exr, png: binding.png, decodedCombinedSha256: binding.decodedCombinedSha256 });
  }
  require(frames.length === 288 && frames.every((row, index) => row.frame === index + 1), 'accepted frame roster is not contiguous');
  const path = resolve(jobRoot, 'accepted-frames.json');
  const body = { schemaVersion: 'bfs.b62TerminalAcceptedFrameManifest.v0.1', experimentId: spec.experimentId, source: spec.parents.sceneCompilation.scene, frames };
  const result = await writeExclusiveDurableHashed(path, body, 'manifestHash');
  require(result.record.manifestHash === sha256Bytes(Buffer.from(canonicalJson(pythonNormalize(body)))), 'manifest canonical mismatch');
  return { path, record: result.record, file: result.file };
}

async function independentExrAudit(jobRoot, spec) {
  const stageId = 'INDEPENDENT_EXR_AUDIT'; const attemptId = 'EXR-AUDIT-0001';
  await startStage(jobRoot, stageId, attemptId);
  const manifest = await acceptedManifest(jobRoot, spec);
  const attemptRoot = resolve(jobRoot, 'attempts', stageId, attemptId); await durableMkdir(attemptRoot);
  const output = resolve(attemptRoot, 'exr-audit.json');
  const result = await runBudgetedProcess({ command: BLENDER, args: blenderArgs(EXR_AUDITOR_URI, ['--manifest', manifest.path, '--output', output], null), cwd: repositoryRoot, env: frozenEnv(), outputRoot: jobRoot,
    budgets: { wallTimeMs: 1800000, maxRssBytes: 6442450944, maxLogBytes: 16777216, maxOutputFiles: 1300, maxOutputBytes: MAX_OUTPUT, sampleIntervalMs: 1000 } });
  require(result.outcome === 'PASS' && result.child.exitCode === 0, `independent EXR audit failed: ${JSON.stringify(result)}`);
  const auditBytes = await readFile(output); const audit = JSON.parse(auditBytes);
  require(audit.status === 'PASS' && audit.rows.length === 288 && audit.auditHash === pythonSelfHash(audit, 'auditHash'), 'independent EXR audit receipt invalid');
  return finishStage(jobRoot, stageId, attemptId, { manifest: { uri: repoUri(manifest.path), sha256: manifest.file.sha256, manifestHash: manifest.record.manifestHash }, audit: { uri: repoUri(output), sha256: sha256Bytes(auditBytes), auditHash: audit.auditHash }, process: result, operations: audit.operations });
}

async function delivery(jobRoot) {
  const stageId = 'DELIVERY'; const attemptId = 'DELIVERY-0001'; await startStage(jobRoot, stageId, attemptId);
  const attemptRoot = resolve(jobRoot, 'attempts', stageId, attemptId); await durableMkdir(attemptRoot);
  const output = resolve(attemptRoot, 'b62-terminal-final.mp4');
  const roots = ['WIDE', 'MEDIUM', 'CLOSE'].map(shot => resolve(jobRoot, 'attempts', SHOT_STAGE[shot], SHOT_ATTEMPT[shot], 'png', 'frame-%04d.png'));
  const args = ['-hide_banner', '-loglevel', 'error', '-framerate', '24', '-start_number', '1', '-i', roots[0], '-framerate', '24', '-start_number', '97', '-i', roots[1], '-framerate', '24', '-start_number', '193', '-i', roots[2], '-filter_complex', '[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]', '-map', '[v]', '-frames:v', '288', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', output];
  const result = await runBudgetedProcess({ command: FFMPEG, args, cwd: repositoryRoot, env: frozenEnv(), outputRoot: jobRoot, budgets: { wallTimeMs: 600000, maxRssBytes: 2147483648, maxLogBytes: 16777216, maxOutputFiles: 1300, maxOutputBytes: MAX_OUTPUT, sampleIntervalMs: 500 } });
  require(result.outcome === 'PASS' && result.child.exitCode === 0, `delivery failed ${JSON.stringify(result)}`);
  const probeResult = await execFileAsync(FFPROBE, ['-v', 'error', '-count_frames', '-show_entries', 'stream=codec_name,pix_fmt,width,height,r_frame_rate,nb_read_frames:format=duration', '-of', 'json', output], { encoding: 'utf8', timeout: 120000, env: frozenEnv() });
  const probe = JSON.parse(probeResult.stdout); const stream = probe.streams[0];
  require(stream.codec_name === 'h264' && stream.pix_fmt === 'yuv420p' && stream.width === 1920 && stream.height === 1080 && stream.r_frame_rate === '24/1' && Number(stream.nb_read_frames) === 288 && Math.abs(Number(probe.format.duration) - 12) < 0.001, 'delivery ffprobe mismatch');
  const video = { uri: repoUri(output), sha256: await sha256File(output), bytes: (await readFile(output)).length };
  return finishStage(jobRoot, stageId, attemptId, { video, ffmpeg: result, ffprobe: probe, operations: { ffmpegStarts: 1, ffprobeStarts: 1, modelCalls: 0, videoModelCalls: 0, networkCalls: 0 } });
}

async function finalAudit(jobRoot) {
  const stageId = 'FINAL_AUDIT'; const attemptId = 'FINAL-AUDIT-0001'; await startStage(jobRoot, stageId, attemptId);
  await durableMkdir(resolve(repositoryRoot, FORMAL_URI));
  const output = resolve(repositoryRoot, FORMAL_URI, 'audit.json');
  const { auditB62 } = await import('./audit-b62-terminal-cycles-restart.mjs');
  const result = await auditB62({ jobRootUri: JOB_URI, formalRootUri: FORMAL_URI, outputUri: repoUri(output) });
  const bytes = await readFile(output); const audit = JSON.parse(bytes); require(validSelfHash(audit, 'auditHash') && audit.status === 'PASS', 'final audit output invalid');
  return finishStage(jobRoot, stageId, attemptId, { audit: { uri: repoUri(output), sha256: sha256Bytes(bytes), auditHash: audit.auditHash }, inProcess: true, restrictedChildProcessesSpawned: 0, summary: result.summary });
}

async function finalize(jobRoot, spec) {
  const stageId = 'FINALIZE'; const attemptId = 'FINALIZE-0001'; await startStage(jobRoot, stageId, attemptId);
  const state = await deriveJobState(jobRoot); const audit = state.stages.FINAL_AUDIT.completed.receipt.audit; const deliveryReceipt = state.stages.DELIVERY.completed.receipt;
  const resultPath = resolve(repositoryRoot, FORMAL_URI, 'results.json');
  const boundary = await readJson(resolve(jobRoot, 'final-receipt.json'));
  const repeat = await readJson(resolve(jobRoot, 'repeated-completed-resume.json'));
  const results = await writeExclusiveDurableHashed(resultPath, { schemaVersion: 'bfs.b62TerminalCyclesRestartResults.v0.1', status: 'PASS', machineVerdict: spec.decision.supportedVerdict, humanReviewStatus: 'PENDING', audit, completionBoundary: { uri: `${JOB_URI}/final-receipt.json`, sha256: boundary.sha256, receiptHash: boundary.value.receiptHash }, repeatedResume: { uri: `${JOB_URI}/repeated-completed-resume.json`, sha256: repeat.sha256, proofHash: repeat.value.proofHash }, delivery: deliveryReceipt.video, claimBoundary: spec.nonClaims }, 'resultsHash');
  const stage = await finishStage(jobRoot, stageId, attemptId, { results: { uri: repoUri(resultPath), sha256: results.file.sha256, resultsHash: results.record.resultsHash }, completionBoundaryReceiptHash: boundary.value.receiptHash, humanReviewStatus: 'PENDING' });
  await appendLedgerEvent(jobRoot, { eventType: 'JOB_FINALIZED', payload: { completionBoundary: { uri: 'final-receipt.json', sha256: boundary.sha256, receiptHash: boundary.value.receiptHash }, results: { uri: repoUri(resultPath), sha256: results.file.sha256, resultsHash: results.record.resultsHash }, finalStageReceipt: await receiptReference(jobRoot, stage) } });
  process.stdout.write(`BFS_T3_COMPLETE ${JSON.stringify({ receipt: boundary.value.receiptHash, results: results.record.resultsHash, video: deliveryReceipt.video.uri, humanReviewStatus: 'PENDING' })}\n`);
  return results;
}

async function createCompletionBoundary(jobRoot, spec) {
  const state = await deriveJobState(jobRoot);
  require(state.stages.DELIVERY.status === 'COMPLETED' && state.stages.FINAL_AUDIT.status === 'PENDING', 'completion boundary stage mismatch');
  const deliveryReceipt = state.stages.DELIVERY.completed.receipt;
  const completedStages = Object.fromEntries(Object.entries(state.stages).filter(([, row]) => row.status === 'COMPLETED').map(([id, row]) => [id, { attemptId: row.completed.attemptId, receiptHash: row.completed.receipt.receiptHash }]));
  const receipt = await writeExclusiveDurableHashed(resolve(jobRoot, 'final-receipt.json'), {
    schemaVersion: 'bfs.b62TerminalCyclesRestartCompletionBoundaryReceipt.v0.1', status: 'COMPLETION_CANDIDATE',
    experimentId: spec.experimentId, machineVerdict: null, humanReviewStatus: 'PENDING', completedStages,
    delivery: deliveryReceipt.video, nextRequiredAction: 'REPEATED_COMPLETED_RESUME_AND_IN_PROCESS_FINAL_AUDIT',
  }, 'receiptHash');
  process.stdout.write(`BFS_T3_COMPLETION_BOUNDARY ${JSON.stringify({ exitCode: 87, receiptHash: receipt.record.receiptHash, sha256: receipt.file.sha256, restrictedChildProcessesAfterBoundary: 0 })}\n`);
  process.exitCode = 87;
  return receipt;
}

async function ensureRepeatedResumeProof(jobRoot) {
  const proofPath = resolve(jobRoot, 'repeated-completed-resume.json');
  const existing = await readJson(proofPath).catch(error => error.reason === 'REQUIRED_FILE_MISSING' ? null : Promise.reject(error));
  if (existing) {
    require(validSelfHash(existing.value, 'proofHash'), 'repeated-resume proof invalid');
    return existing;
  }
  const before = await readJson(resolve(jobRoot, 'final-receipt.json'));
  require(validSelfHash(before.value, 'receiptHash') && before.value.status === 'COMPLETION_CANDIDATE', 'completion boundary invalid');
  const after = await readJson(resolve(jobRoot, 'final-receipt.json'));
  require(before.sha256 === after.sha256 && before.value.receiptHash === after.value.receiptHash, 'completion receipt was not byte exact');
  return writeExclusiveDurableHashed(proofPath, {
    schemaVersion: 'bfs.b62TerminalRepeatedCompletedResumeProof.v0.1', status: 'PASS',
    receiptBefore: { uri: 'final-receipt.json', sha256: before.sha256, receiptHash: before.value.receiptHash, bytes: before.bytes.length },
    receiptAfter: { uri: 'final-receipt.json', sha256: after.sha256, receiptHash: after.value.receiptHash, bytes: after.bytes.length },
    byteExact: true, childProcessesSpawnedBeforeProof: 0, restrictedProcessesSpawnedBeforeProof: 0,
  }, 'proofHash');
}

async function createStart(parsed, spec) {
  for (const uri of [PREFLIGHT_URI, JOB_URI, FORMAL_URI]) {
    const rootState = await lstat(resolve(repositoryRoot, uri)).catch(error => error.code === 'ENOENT' ? null : Promise.reject(error));
    require(rootState === null, `formal root already exists ${uri}`);
  }
  const freeze = await verifyFreeze(parsed.toolFreezeCommit);
  const capacity = await requireCapacity(PROJECTED_WRITE);
  await durableMkdir(resolve(repositoryRoot, PREFLIGHT_URI));
  const preflightPath = resolve(repositoryRoot, PREFLIGHT_URI, 'preflight.json');
  const correctionPath = resolve(repositoryRoot, CORRECTION_URI); const correction = JSON.parse(await readFile(correctionPath, 'utf8'));
  require(correction.statusBeforeToolModification === 'PREREGISTERED' && correction.authorizedRetryRoots.preflight === PREFLIGHT_URI && correction.authorizedRetryRoots.job === JOB_URI && correction.authorizedRetryRoots.formal === FORMAL_URI, 'C1 correction binding mismatch');
  const retainedPreflight = await readJson(resolve(repositoryRoot, correction.retainedFailure.preflight.uri));
  const retainedFailure = await readJson(resolve(repositoryRoot, correction.retainedFailure.failure.uri));
  require(retainedPreflight.sha256 === correction.retainedFailure.preflight.sha256 && retainedPreflight.value.preflightHash === correction.retainedFailure.preflight.preflightHash && validSelfHash(retainedPreflight.value, 'preflightHash'), 'retained v0.1 preflight mismatch');
  require(retainedFailure.sha256 === correction.retainedFailure.failure.sha256 && retainedFailure.value.failureHash === correction.retainedFailure.failure.failureHash && validSelfHash(retainedFailure.value, 'failureHash'), 'retained v0.1 failure mismatch');
  const preflight = await writeExclusiveDurableHashed(preflightPath, { schemaVersion: 'bfs.b62TerminalCyclesRestartPreflight.v0.2', status: 'ACCEPTED', toolFreezeCommit: freeze.commit, originMain: freeze.origin, toolHashes: freeze.hashes, correction: { uri: CORRECTION_URI, sha256: await sha256File(correctionPath) }, retainedFailure: { preflight: correction.retainedFailure.preflight, failure: correction.retainedFailure.failure }, capacity, source: spec.parents.sceneCompilation.scene, stageDag: spec.stageDag }, 'preflightHash');
  const jobRoot = resolve(repositoryRoot, JOB_URI);
  await createManifest(jobRoot, { jobId: JOB_ID, experimentId: spec.experimentId, toolFreezeCommit: freeze.commit, preflight: { uri: repoUri(preflightPath), sha256: preflight.file.sha256, preflightHash: preflight.record.preflightHash }, source: spec.parents.sceneCompilation.scene, spec: { uri: SPEC_URI, sha256: await sha256File(resolve(repositoryRoot, SPEC_URI)) }, correction: { uri: CORRECTION_URI, sha256: await sha256File(correctionPath) }, stageDag: spec.stageDag });
  await appendLedgerEvent(jobRoot, { eventType: 'JOB_CREATED', payload: { mode: 'start' } });
  return jobRoot;
}

async function runB62(argv) {
  const parsed = parseArguments(argv); const spec = JSON.parse(await readFile(resolve(repositoryRoot, SPEC_URI), 'utf8'));
  let jobRoot;
  if (parsed.mode === 'start') jobRoot = await createStart(parsed, spec);
  else {
    jobRoot = resolve(repositoryRoot, JOB_URI);
    const state = await deriveJobState(jobRoot);
    const finalPath = resolve(jobRoot, 'final-receipt.json');
    const final = await readJson(finalPath).catch(error => error.reason === 'REQUIRED_FILE_MISSING' ? null : Promise.reject(error));
    const finalized = state.ledger.events.some(row => row.event.eventType === 'JOB_FINALIZED');
    if (final && finalized) {
      require(validSelfHash(final.value, 'receiptHash'), 'existing final receipt invalid');
      process.stdout.write(`BFS_T3_ALREADY_FINALIZED ${JSON.stringify({ receiptHash: final.value.receiptHash, sha256: final.sha256, restrictedProcessesSpawned: 0 })}\n`);
      return final.value;
    }
    if (final) {
      const lock = await lstat(resolve(jobRoot, '.writer-lock')).catch(error => error.code === 'ENOENT' ? null : Promise.reject(error));
      require(lock === null, 'completion-boundary resume requires no pre-existing writer lease');
      await ensureRepeatedResumeProof(jobRoot);
    } else {
      await verifyFreeze(state.manifest.toolFreezeCommit);
    }
  }

  const lease = await acquireWriterLease(jobRoot, { allowReclaimDead: parsed.mode === 'resume' });
  try {
    let state = await deriveJobState(jobRoot);
    if (state.stages.ADMIT_PLAN.status !== 'COMPLETED') {
      await startStage(jobRoot, 'ADMIT_PLAN', 'ADMIT-0001');
      await finishStage(jobRoot, 'ADMIT_PLAN', 'ADMIT-0001', { spec: state.manifest.spec, preflight: state.manifest.preflight, source: state.manifest.source, operations: { restrictedProcesses: 0 } });
    }
    state = await deriveJobState(jobRoot);
    if (state.stages.INTERRUPT_WIDE_PROBE.status !== 'COMPLETED') await controlledInterruption(jobRoot);
    state = await deriveJobState(jobRoot);
    if (state.stages.RENDER_WIDE.status !== 'COMPLETED') await renderShot(jobRoot, 'WIDE');
    state = await deriveJobState(jobRoot);
    if (state.stages.CODEX_RESTART_CHECKPOINT.status !== 'COMPLETED') {
      const stageId = 'CODEX_RESTART_CHECKPOINT'; const attemptId = 'CHECKPOINT-0001'; await startStage(jobRoot, stageId, attemptId);
      const host = await findCodexHostIdentity();
      const checkpoint = await writeExclusiveDurableHashed(resolve(jobRoot, 'codex-restart-checkpoint.json'), { schemaVersion: 'bfs.b62TerminalCodexRestartCheckpoint.v0.1', status: 'AWAITING_REAL_RESTART', host, wideReceiptHash: state.stages.RENDER_WIDE.completed.receipt.receiptHash }, 'checkpointHash');
      await finishStage(jobRoot, stageId, attemptId, { checkpoint: { uri: 'codex-restart-checkpoint.json', sha256: checkpoint.file.sha256, checkpointHash: checkpoint.record.checkpointHash }, host, operations: { restrictedProcesses: 0 } });
      process.stdout.write(`BFS_T3_RESTART_CHECKPOINT ${JSON.stringify({ exitCode: 86, hostIdentityHash: host.identityHash, wideFramesComplete: 96 })}\n`);
      process.exitCode = 86; return null;
    }
    state = await deriveJobState(jobRoot);
    if (state.stages.POST_RESTART_ATTEST.status !== 'COMPLETED') {
      const checkpoint = (await readJson(resolve(jobRoot, 'codex-restart-checkpoint.json'))).value;
      require(validSelfHash(checkpoint, 'checkpointHash'), 'restart checkpoint self-hash mismatch');
      const comparison = await compareRecordedProcess(checkpoint.host);
      const current = await findCodexHostIdentity();
      if (comparison.state !== 'DEAD' || current.identityHash === checkpoint.host.identityHash) {
        process.stdout.write(`BFS_T3_CODEX_RESTART_REQUIRED ${JSON.stringify({ oldHostState: comparison.state, currentHostIdentityHash: current.identityHash, restrictedProcessesSpawned: 0 })}\n`);
        process.exitCode = 86; return null;
      }
      const stageId = 'POST_RESTART_ATTEST'; const attemptId = 'POST-RESTART-0001'; await startStage(jobRoot, stageId, attemptId);
      for (const skipped of ['ADMIT_PLAN', 'INTERRUPT_WIDE_PROBE', 'RENDER_WIDE']) await appendLedgerEvent(jobRoot, { eventType: 'STAGE_SKIPPED_VERIFIED', stageId: skipped, attemptId: state.stages[skipped].completed.attemptId, payload: { receiptHash: state.stages[skipped].completed.receipt.receiptHash, reason: 'durable verified resume after real Codex host restart' } });
      await finishStage(jobRoot, stageId, attemptId, { previousHost: checkpoint.host, comparison, currentHost: current, skippedStages: ['ADMIT_PLAN', 'INTERRUPT_WIDE_PROBE', 'RENDER_WIDE'], wideRerenderCalls: 0, operations: { restrictedProcessesBeforeAttestation: 0 } });
    }
    state = await deriveJobState(jobRoot); if (state.stages.RENDER_MEDIUM.status !== 'COMPLETED') await renderShot(jobRoot, 'MEDIUM');
    state = await deriveJobState(jobRoot); if (state.stages.RENDER_CLOSE.status !== 'COMPLETED') await renderShot(jobRoot, 'CLOSE');
    state = await deriveJobState(jobRoot); if (state.stages.INDEPENDENT_EXR_AUDIT.status !== 'COMPLETED') await independentExrAudit(jobRoot, spec);
    state = await deriveJobState(jobRoot); if (state.stages.DELIVERY.status !== 'COMPLETED') await delivery(jobRoot);
    state = await deriveJobState(jobRoot);
    if (state.stages.DELIVERY.status === 'COMPLETED' && state.stages.FINAL_AUDIT.status !== 'COMPLETED' && !(await readJson(resolve(jobRoot, 'final-receipt.json')).catch(error => error.reason === 'REQUIRED_FILE_MISSING' ? null : Promise.reject(error)))) return createCompletionBoundary(jobRoot, spec);
    state = await deriveJobState(jobRoot); if (state.stages.FINAL_AUDIT.status !== 'COMPLETED') await finalAudit(jobRoot);
    state = await deriveJobState(jobRoot); if (state.stages.FINALIZE.status !== 'COMPLETED') return finalize(jobRoot, spec);
    throw new Error('FINALIZE completed without final receipt');
  } finally {
    await releaseWriterLease(lease);
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  runB62(process.argv.slice(2)).catch(error => { process.stderr.write(`BFS_T3_ERROR ${error.stack ?? error.message}\n`); process.exitCode = 1; });
}

export { RESTRICTED_COMMANDS, runB62 };
