#!/usr/bin/env node
import { execFileSync, spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { existsSync, readFileSync, statfsSync, statSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

const repository = resolve(process.argv[2]);
const evidenceRelative = process.argv[3];
if (!repository || !evidenceRelative) throw new Error('Usage: run-f05.mjs <repository-root> <evidence-root-relative>');
const evidence = resolve(repository, evidenceRelative);
const product = '/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-F0-workspace/build-f0.6-merge-drill/bin/Film Studio Engine F0.app/Contents/MacOS/Blender';
const ocio = resolve(repository, 'color/ocio/cg-config-v4.0.0_aces-v2.0_ocio-v2.5.ocio');
const source = resolve(repository, 'experiments/ai-native-studio-f0/F0.6-2026-08-30-mac-m2max-attempt-02/regression/f04/b01/artifacts/scene.blend');
const renderScript = resolve(repository, 'experiments/ai-native-studio-f0/F0.6-2026-08-30-mac-m2max-attempt-03/tools/render-stage.py');
const auditScript = resolve(repository, 'experiments/ai-native-studio-f0/F0.6-2026-08-30-mac-m2max-attempt-03/tools/audit-f05.py');
const requiredFree = 160n * 1024n ** 3n;
const reserve = 100n * 1024n ** 3n;
const positiveProjection = 512n * 1024n ** 2n;
const insufficientProjection = 80n * 1024n ** 3n;
const maxSeconds = 120;
const maxRss = 8 * 1024 ** 3;
let formalProductStarts = 0;
let rendererStarts = 0;

const shaBytes = value => createHash('sha256').update(value).digest('hex');
const shaFile = path => shaBytes(readFileSync(path));
const prettyHash = value => shaBytes(`${JSON.stringify(value, null, 2)}\n`);
const now = () => new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
const freeBytes = () => { const value = statfsSync(evidence, { bigint: true }); return value.bavail * value.bsize; };
const runningBlender = () => {
  try { return execFileSync('/usr/bin/pgrep', ['-x', 'Blender'], { encoding: 'utf8' }).trim().split(/\s+/).filter(Boolean); } catch { return []; }
};
function writeHashed(path, body, field) {
  const record = { ...body, [field]: prettyHash(body) };
  writeFileSync(path, `${JSON.stringify(record, null, 2)}\n`, { flag: 'wx' });
  return record;
}
function validSelf(path, field) {
  const value = JSON.parse(readFileSync(path));
  const expected = value[field];
  delete value[field];
  return expected === prettyHash(value);
}
function parseTiming(text) {
  const number = label => Number(text.match(new RegExp(`^${label}\\s+([0-9.]+)`, 'm'))?.[1] ?? Number.NaN);
  return {
    realSeconds: number('real'),
    userSeconds: number('user'),
    systemSeconds: number('sys'),
    maximumResidentSetSizeBytes: Number(text.match(/^\s*([0-9]+)\s+maximum resident set size/m)?.[1] ?? Number.NaN),
  };
}
function admission({ sequence, id, output, report, renderer }) {
  const free = freeBytes();
  const running = runningBlender();
  const body = {
    schemaVersion: 'bfs.f0.5.nativeStartAdmission.v0.1',
    id,
    formalProductStart: sequence,
    observedAt: now(),
    status: free >= requiredFree && free - positiveProjection >= reserve && running.length === 0 && !existsSync(output) && !existsSync(report) ? 'ACCEPTED' : 'REJECTED',
    freeBytes: String(free),
    requiredFreeBytes: String(requiredFree),
    reserveBytes: String(reserve),
    projectedWriteBytes: String(positiveProjection),
    projectedFreeAfterWriteBytes: String(free - positiveProjection),
    runningBlenderPidsBefore: running,
    output,
    outputAbsentBefore: !existsSync(output),
    report,
    reportAbsentBefore: !existsSync(report),
    maximumConcurrentNativeProcesses: 1,
    renderer,
  };
  const record = writeHashed(resolve(evidence, 'admissions', `${String(sequence).padStart(2, '0')}-${id}.json`), body, 'admissionHash');
  if (record.status !== 'ACCEPTED') throw new Error(`Admission rejected: ${id}`);
  return record;
}
async function runProduct({ sequence, id, script, scriptArgs, interruptMarker = null, renderer, expectedRenderCalls }) {
  formalProductStarts += 1;
  if (renderer) rendererStarts += 1;
  const prefix = resolve(evidence, 'processes', `${String(sequence).padStart(2, '0')}-${id}`);
  const stdoutPath = `${prefix}.stdout.log`;
  const stderrPath = `${prefix}.stderr.log`;
  const timingPath = `${prefix}.timing.log`;
  const args = ['-lp', '-o', timingPath, product, '--background', '--factory-startup', '--python-exit-code', '1', '--python', script, '--', ...scriptArgs];
  const startedAt = now();
  const started = process.hrtime.bigint();
  const child = spawn('/usr/bin/time', args, {
    cwd: repository,
    detached: true,
    env: { ...process.env, OCIO: ocio, LANG: 'C', LC_ALL: 'C', F06_SOURCE_SHA: sourceSha, F06_JOB_HASH: jobHash },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  const stdout = [];
  const stderr = [];
  let markerObserved = false;
  let interruptionDelivered = false;
  let interruptionError = null;
  let timeout = false;
  child.stdout.on('data', chunk => {
    stdout.push(chunk);
    const text = Buffer.concat(stdout).toString('utf8');
    if (interruptMarker && !interruptionDelivered && text.includes(interruptMarker)) {
      markerObserved = true;
      let descendants = [];
      try { descendants = execFileSync('/usr/bin/pgrep', ['-P', String(child.pid)], { encoding: 'utf8' }).trim().split(/\s+/).filter(Boolean).map(Number); } catch {}
      if (descendants.length !== 1) {
        interruptionError = `Expected one Blender child for interruption, observed ${descendants}`;
        try { process.kill(-child.pid, 'SIGKILL'); } catch {}
        return;
      }
      process.kill(descendants[0], 'SIGTERM');
      interruptionDelivered = true;
    }
  });
  child.stderr.on('data', chunk => stderr.push(chunk));
  const timer = setTimeout(() => {
    timeout = true;
    try { process.kill(-child.pid, 'SIGKILL'); } catch {}
  }, maxSeconds * 1000);
  const result = await new Promise((resolveResult, reject) => {
    child.on('error', reject);
    child.on('close', (exitCode, signal) => resolveResult({ exitCode, signal }));
  });
  clearTimeout(timer);
  const elapsedSeconds = Number(process.hrtime.bigint() - started) / 1e9;
  writeFileSync(stdoutPath, Buffer.concat(stdout), { flag: 'wx' });
  writeFileSync(stderrPath, Buffer.concat(stderr), { flag: 'wx' });
  const timingText = readFileSync(timingPath, 'utf8');
  const timing = parseTiming(timingText);
  const interrupted = Boolean(interruptMarker);
  const stdoutText = Buffer.concat(stdout).toString('utf8');
  const observedRenderCalls = stdoutText.match(/^F05_RENDER_CALL_BEGIN\b/gm)?.length ?? 0;
  const status = interrupted
    ? markerObserved && interruptionDelivered && !interruptionError && observedRenderCalls === 0 && result.exitCode !== 0 && !timeout ? 'INTERRUPTED' : 'FAIL'
    : observedRenderCalls === expectedRenderCalls && result.exitCode === 0 && !timeout ? 'PASS' : 'FAIL';
  const body = {
    schemaVersion: 'bfs.f0.5.processReceipt.v0.1',
    id: id.toUpperCase(),
    formalProductStart: sequence,
    status,
    startedAt,
    command: product,
    args: args.slice(4),
    exitCode: result.exitCode,
    signal: result.signal,
    timeout,
    timing: { ...timing, observedElapsedSeconds: elapsedSeconds },
    renderer,
    expectedRenderCalls,
    observedRenderCalls,
    controlledInterruption: interrupted ? { marker: interruptMarker, markerObserved, delivered: interruptionDelivered, error: interruptionError } : null,
    logs: {
      stdout: { uri: stdoutPath.slice(evidence.length + 1), bytes: statSync(stdoutPath).size, sha256: shaFile(stdoutPath) },
      stderr: { uri: stderrPath.slice(evidence.length + 1), bytes: statSync(stderrPath).size, sha256: shaFile(stderrPath) },
      timing: { uri: timingPath.slice(evidence.length + 1), bytes: statSync(timingPath).size, sha256: shaFile(timingPath) },
    },
  };
  const receipt = writeHashed(`${prefix}.json`, body, 'processHash');
  if (status === 'FAIL') throw new Error(`Product process failed: ${id}`);
  if (![timing.realSeconds, timing.userSeconds, timing.systemSeconds, timing.maximumResidentSetSizeBytes].every(Number.isFinite)) throw new Error(`Invalid timing receipt: ${id}`);
  if (timing.realSeconds > maxSeconds || timing.maximumResidentSetSizeBytes > maxRss) throw new Error(`Process budget exceeded: ${id}`);
  return receipt;
}
function makeStageReceipt(stage, processReceipt, reportPath, outputPath) {
  const report = JSON.parse(readFileSync(reportPath));
  if (!validSelf(reportPath, 'stageReportHash') || report.status !== 'PASS' || report.output.sha256 !== shaFile(outputPath)) throw new Error(`${stage} stage report invalid`);
  const body = {
    schemaVersion: 'bfs.f0.5.stageReceipt.v0.1',
    jobId: 'F05-B01-RENDER-001',
    stage,
    status: 'PASS',
    process: { uri: `processes/${String(processReceipt.formalProductStart).padStart(2, '0')}-${processReceipt.id.toLowerCase()}.json`, processHash: processReceipt.processHash },
    stageReport: { uri: reportPath.slice(evidence.length + 1), fileSha256: shaFile(reportPath), stageReportHash: report.stageReportHash },
    output: { uri: outputPath.slice(evidence.length + 1), bytes: statSync(outputPath).size, sha256: shaFile(outputPath) },
    timing: processReceipt.timing,
    expectedRenderCalls: 1,
    observedRenderCalls: processReceipt.observedRenderCalls,
    sourceBlendSha256After: shaFile(source),
  };
  return writeHashed(resolve(evidence, stage.toLowerCase(), 'receipt.json'), body, 'receiptHash');
}

const sourceSha = shaFile(source);
const jobHash = JSON.parse(readFileSync(resolve(evidence, 'job-manifest.json'))).manifestHash;
for (const [path, expected] of [[product, '58d5c984c58d986d3cf44622ad5876052a67890d0b077dafd4977f6e2b24a71d'], [source, sourceSha], [ocio, '24ec81841048fc5db160a7bad882263246183385c5d49d0e86e11464917ead15']]) {
  if (shaFile(path) !== expected) throw new Error(`Frozen identity mismatch: ${path}`);
}
if (!validSelf(resolve(evidence, 'job-manifest.json'), 'manifestHash') || !validSelf(resolve(evidence, 'approval.json'), 'approvalHash')) throw new Error('Job approval identity invalid');
const formalStart = JSON.parse(readFileSync(resolve(evidence, 'formal-start.json')));
if (formalStart.status !== 'FROZEN_BEFORE_FORMAL_PRODUCT_START') throw new Error('Formal start not frozen');
if (runningBlender().length) throw new Error('Blender already running before F0.5');

const negativeFree = freeBytes();
const negativeBody = {
  schemaVersion: 'bfs.f0.5.insufficientDiskAdmission.v0.1',
  id: 'N1_INSUFFICIENT_DISK',
  observedAt: now(),
  status: negativeFree - insufficientProjection < reserve ? 'REJECTED' : 'UNEXPECTED_ACCEPT',
  freeBytes: String(negativeFree),
  projectedWriteBytes: String(insufficientProjection),
  reserveBytes: String(reserve),
  projectedFreeAfterWriteBytes: String(negativeFree - insufficientProjection),
  runningBlenderPidsBeforeAndAfter: runningBlender(),
  productStarts: 0,
  rendererStarts: 0,
  outputCreated: false,
};
writeHashed(resolve(evidence, 'admissions/00-insufficient-disk.json'), negativeBody, 'admissionHash');
if (negativeBody.status !== 'REJECTED' || runningBlender().length) throw new Error('Insufficient disk negative did not reject safely');

const previewOutput = resolve(evidence, 'preview/preview.png');
const previewReport = resolve(evidence, 'preview/stage-report.json');
admission({ sequence: 1, id: 'preview', output: previewOutput, report: previewReport, renderer: true });
const previewProcess = await runProduct({
  sequence: 1,
  id: 'preview',
  script: renderScript,
  scriptArgs: ['--repository-root', repository, '--evidence-root', evidenceRelative, '--stage', 'preview', '--output', `${evidenceRelative}/preview/preview.png`, '--report', `${evidenceRelative}/preview/stage-report.json`],
  renderer: true,
  expectedRenderCalls: 1,
});
const previewReceipt = makeStageReceipt('PREVIEW', previewProcess, previewReport, previewOutput);

const interruptedOutput = resolve(evidence, 'interrupted-final/final.exr');
const interruptedReport = resolve(evidence, 'interrupted-final/stage-report.json');
admission({ sequence: 2, id: 'final-interrupted', output: interruptedOutput, report: interruptedReport, renderer: true });
const interruptedProcess = await runProduct({
  sequence: 2,
  id: 'final-interrupted',
  script: renderScript,
  scriptArgs: ['--repository-root', repository, '--evidence-root', evidenceRelative, '--stage', 'final', '--output', `${evidenceRelative}/interrupted-final/final.exr`, '--report', `${evidenceRelative}/interrupted-final/stage-report.json`, '--pause-before-render'],
  interruptMarker: 'F05_READY_FOR_CONTROLLED_INTERRUPT',
  renderer: true,
  expectedRenderCalls: 0,
});
if (existsSync(interruptedOutput) || existsSync(interruptedReport)) throw new Error('Interrupted final wrote a formal artifact');

const tampered = structuredClone(previewReceipt);
tampered.output.sha256 = '0'.repeat(64);
const startsBeforeTamper = formalProductStarts;
const tamperedRejected = tampered.receiptHash !== prettyHash(Object.fromEntries(Object.entries(tampered).filter(([key]) => key !== 'receiptHash')));
const tamperedBody = {
  schemaVersion: 'bfs.f0.5.tamperedReceiptNegative.v0.1',
  status: tamperedRejected ? 'REJECTED' : 'UNEXPECTED_ACCEPT',
  mutation: 'preview.output.sha256',
  expectedReason: 'RECEIPT_SELF_HASH_MISMATCH',
  observedReason: tamperedRejected ? 'RECEIPT_SELF_HASH_MISMATCH' : null,
  productStartsBefore: startsBeforeTamper,
  productStartsAfter: formalProductStarts,
  additionalProductStarts: formalProductStarts - startsBeforeTamper,
};
writeHashed(resolve(evidence, 'tampered-receipt.json'), tamperedBody, 'negativeHash');
if (!tamperedRejected || formalProductStarts !== startsBeforeTamper) throw new Error('Tampered receipt was not rejected before product start');

if (!validSelf(resolve(evidence, 'preview/receipt.json'), 'receiptHash') || previewReceipt.output.sha256 !== shaFile(previewOutput)) throw new Error('Immutable preview verification failed before recovery');
const interruptedReceiptPath = resolve(evidence, 'processes/02-final-interrupted.json');
if (!validSelf(interruptedReceiptPath, 'processHash') || interruptedProcess.status !== 'INTERRUPTED') throw new Error('Interruption receipt invalid before recovery');

const finalOutput = resolve(evidence, 'final/final.exr');
const finalReport = resolve(evidence, 'final/stage-report.json');
admission({ sequence: 3, id: 'final-recovery', output: finalOutput, report: finalReport, renderer: true });
const finalProcess = await runProduct({
  sequence: 3,
  id: 'final-recovery',
  script: renderScript,
  scriptArgs: ['--repository-root', repository, '--evidence-root', evidenceRelative, '--stage', 'final', '--output', `${evidenceRelative}/final/final.exr`, '--report', `${evidenceRelative}/final/stage-report.json`],
  renderer: true,
  expectedRenderCalls: 1,
});
const finalReceipt = makeStageReceipt('FINAL', finalProcess, finalReport, finalOutput);

const recoveryBody = {
  schemaVersion: 'bfs.f0.5.recoveryReceipt.v0.1',
  status: 'PASS',
  jobId: 'F05-B01-RENDER-001',
  previewReceiptVerified: true,
  previewReceiptHash: previewReceipt.receiptHash,
  previewRerenderCount: 0,
  interruptionVerified: true,
  interruptionProcessHash: interruptedProcess.processHash,
  interruptedRenderCalls: interruptedProcess.observedRenderCalls,
  interruptedFinalArtifactAbsent: !existsSync(interruptedOutput),
  tamperedReceiptRejected: tamperedRejected,
  recoveredStages: ['FINAL'],
  finalReceiptHash: finalReceipt.receiptHash,
  finalRenderCalls: finalProcess.observedRenderCalls,
};
writeHashed(resolve(evidence, 'recovery.json'), recoveryBody, 'recoveryHash');

const auditOutput = resolve(evidence, 'audit.json');
const auditSentinel = resolve(evidence, 'processes/04-audit.json');
admission({ sequence: 4, id: 'audit', output: auditOutput, report: auditSentinel, renderer: false });
const renderProcesses = [previewProcess, interruptedProcess, finalProcess];
const observedRenderCalls = renderProcesses.reduce((sum, row) => sum + row.observedRenderCalls, 0);
const formalOutputBytesBeforeAudit = [previewOutput, previewReport, finalOutput, finalReport, resolve(evidence, 'preview/receipt.json'), resolve(evidence, 'final/receipt.json'), resolve(evidence, 'recovery.json')].reduce((sum, path) => sum + statSync(path).size, 0);
const costBody = {
  schemaVersion: 'bfs.f0.5.costReceipt.v0.1',
  status: 'PASS',
  jobId: 'F05-B01-RENDER-001',
  monetaryCostUsd: 0,
  monetaryCostBasis: 'Local owned-host execution; no paid API, model, network render or cloud worker was used.',
  energyCostMeasured: false,
  renderProcessRealSeconds: renderProcesses.reduce((sum, row) => sum + row.timing.realSeconds, 0),
  renderProcessUserSeconds: renderProcesses.reduce((sum, row) => sum + row.timing.userSeconds, 0),
  renderProcessSystemSeconds: renderProcesses.reduce((sum, row) => sum + row.timing.systemSeconds, 0),
  peakResidentSetSizeBytes: Math.max(...renderProcesses.map(row => row.timing.maximumResidentSetSizeBytes)),
  formalOutputBytes: formalOutputBytesBeforeAudit,
  maximumFormalOutputBytes: 268435456,
  maximumConcurrentNativeProcesses: 1,
  formalProductStarts: 4,
  rendererStarts: 3,
  expectedRenderCalls: 2,
  observedRenderCalls,
  modelCalls: 0,
  networkCalls: 0,
  timingCoverage: 'All three renderer starts; the zero-render independent audit process receipt is written after the audit.',
};
writeHashed(resolve(evidence, 'cost-receipt.json'), costBody, 'costHash');

const auditProcess = await runProduct({
  sequence: 4,
  id: 'audit',
  script: auditScript,
  scriptArgs: ['--repository-root', repository, '--evidence-root', evidenceRelative],
  renderer: false,
  expectedRenderCalls: 0,
});
const audit = JSON.parse(readFileSync(auditOutput));
if (audit.status !== 'PASS') throw new Error('Independent audit did not pass');
const totalFormalBytes = execFileSync('/usr/bin/du', ['-sk', evidence], { encoding: 'utf8' }).trim().split(/\s+/)[0] * 1024;
const completionBody = {
  schemaVersion: 'bfs.f0.5.completionReceipt.v0.1',
  status: totalFormalBytes <= 268435456 && shaFile(source) === sourceSha ? 'PASS' : 'FAIL',
  jobId: 'F05-B01-RENDER-001',
  formalProductStarts,
  rendererStarts,
  expectedRenderCalls: 2,
  observedRenderCalls,
  processHashes: [previewProcess.processHash, interruptedProcess.processHash, finalProcess.processHash, auditProcess.processHash],
  previewReceiptHash: previewReceipt.receiptHash,
  finalReceiptHash: finalReceipt.receiptHash,
  recoveryHash: JSON.parse(readFileSync(resolve(evidence, 'recovery.json'))).recoveryHash,
  costHash: JSON.parse(readFileSync(resolve(evidence, 'cost-receipt.json'))).costHash,
  auditHash: audit.auditHash,
  totalFormalBytes,
  sourceBlendUnchanged: shaFile(source) === sourceSha,
  runningBlenderPidsAfter: runningBlender(),
};
const completion = writeHashed(resolve(evidence, 'completion.json'), completionBody, 'completionHash');
if (completion.status !== 'PASS' || completion.runningBlenderPidsAfter.length) throw new Error('F0.5 completion failed');
console.log(`F05_RUN PASS starts=${formalProductStarts} renderers=${rendererStarts} renders=${observedRenderCalls} bytes=${totalFormalBytes}`);
