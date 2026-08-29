#!/usr/bin/env node

import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { AdmissionError, admitFormalRun } from './lib/formal-run-admission.mjs';
import {
  appendLedgerEvent,
  durableMkdir,
  readProcessIdentity,
  sha256File,
  validSelfHash,
  writeExclusiveDurableHashed,
} from './lib/restart-safe-job-ledger.mjs';
import { repositoryRoot } from './lib/scene-spec.mjs';

const NODE = '/opt/homebrew/Cellar/node/26.5.0/bin/node';
const ORCHESTRATOR = 'scripts/run-restart-safe-production-job.mjs';
const AUDITOR = 'scripts/audit-b58-e1-restart-safe-production-orchestrator.mjs';
const GATE0_CORRECTION = 'specs/restart-safe-production-orchestrator-gate0-binding-correction.v0.1.json';

async function verifyGate0Binding(preflight) {
  const correctionPath = resolve(repositoryRoot, GATE0_CORRECTION);
  const correction = JSON.parse(await readFile(correctionPath, 'utf8'));
  const resultsPath = resolve(repositoryRoot, correction.gate0.results[0]);
  const auditPath = resolve(repositoryRoot, correction.gate0.audit[0]);
  const [results, audit] = await Promise.all([readFile(resultsPath, 'utf8').then(JSON.parse), readFile(auditPath, 'utf8').then(JSON.parse)]);
  const exact = preflight.gate0Correction?.uri === GATE0_CORRECTION
    && preflight.gate0Correction.sha256 === await sha256File(correctionPath)
    && preflight.checks?.GATE0_CORRECTION_AND_CLOSEOUT_EXACT === true && preflight.gate0?.exact === true
    && preflight.gate0.results.sha256 === await sha256File(resultsPath) && preflight.gate0.results.sha256 === correction.gate0.results[1]
    && preflight.gate0.audit.sha256 === await sha256File(auditPath) && preflight.gate0.audit.sha256 === correction.gate0.audit[1]
    && validSelfHash(results, 'selfHash') && validSelfHash(audit, 'selfHash') && audit.finalVerdict === correction.gate0.requiredVerdict
    && audit.passedGates === correction.gate0.requiredGates && audit.totalGates === correction.gate0.requiredGates
    && audit.attacksPassed === correction.gate0.requiredAttacks && audit.attacksTotal === correction.gate0.requiredAttacks && audit.failedGates.length === 0;
  if (!exact) throw new Error('B58 Gate 0 binding mismatch');
  return preflight.gate0;
}

function parseArguments(argv) {
  const parsed = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--preflight-root') parsed.preflightRoot = argv[++index];
    else if (token === '--attempt-root') parsed.attemptRoot = argv[++index];
    else if (token === '--formal-root') parsed.formalRoot = argv[++index];
    else if (token === '--preflight-evidence-commit') parsed.preflightEvidenceCommit = argv[++index];
    else throw new Error(`Unknown or incomplete argument: ${token}`);
  }
  for (const key of ['preflightRoot', 'attemptRoot', 'formalRoot', 'preflightEvidenceCommit']) {
    if (!parsed[key]) throw new Error(`Missing --${key.replace(/[A-Z]/g, letter => `-${letter.toLowerCase()}`)}`);
  }
  if (!/^[0-9a-f]{40}$/.test(parsed.preflightEvidenceCommit)) throw new Error('Evidence commit must be a full lowercase SHA-1');
  return parsed;
}

async function runChild(command, args) {
  const started = process.hrtime.bigint();
  const child = spawn(command, args, {
    cwd: repositoryRoot,
    env: { PATH: '/opt/homebrew/bin:/usr/bin:/bin', LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8' },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  const stdout = [];
  const stderr = [];
  child.stdout.on('data', chunk => stdout.push(chunk));
  child.stderr.on('data', chunk => stderr.push(chunk));
  const terminal = await new Promise((resolvePromise, reject) => {
    child.on('error', reject);
    child.on('close', (exitCode, signal) => resolvePromise({ exitCode, signal }));
  });
  const stdoutBuffer = Buffer.concat(stdout);
  const stderrBuffer = Buffer.concat(stderr);
  return {
    pid: child.pid,
    ...terminal,
    elapsedNanoseconds: Number(process.hrtime.bigint() - started),
    stdout: stdoutBuffer.toString('utf8'),
    stderr: stderrBuffer.toString('utf8'),
    stdoutBytes: stdoutBuffer.length,
    stderrBytes: stderrBuffer.length,
    stdoutSha256: createHash('sha256').update(stdoutBuffer).digest('hex'),
    stderrSha256: createHash('sha256').update(stderrBuffer).digest('hex'),
  };
}

function compactChild(child) {
  return {
    pid: child.pid,
    exitCode: child.exitCode,
    signal: child.signal,
    elapsedNanoseconds: child.elapsedNanoseconds,
    stdoutBytes: child.stdoutBytes,
    stderrBytes: child.stderrBytes,
    stdoutSha256: child.stdoutSha256,
    stderrSha256: child.stderrSha256,
  };
}

function parseJobOutput(child, expectedOutcome) {
  const prefix = `BFS_RESTART_SAFE_JOB ${expectedOutcome} `;
  const line = child.stdout.split('\n').find(row => row.startsWith(prefix));
  if (!line) throw new Error(`Missing ${expectedOutcome} output: ${child.stderr || child.stdout}`);
  return JSON.parse(line.slice(prefix.length));
}

function countEvent(events, eventType, stageId = null) {
  return events.filter(event => event.eventType === eventType && (stageId === null || event.stageId === stageId)).length;
}

async function readEvents(jobRoot) {
  const { readdir } = await import('node:fs/promises');
  const names = (await readdir(resolve(repositoryRoot, jobRoot, 'events'))).sort();
  const events = [];
  for (const name of names) events.push(JSON.parse(await readFile(resolve(repositoryRoot, jobRoot, 'events', name), 'utf8')));
  return events;
}

async function runJobStart(preflight, id, extra = []) {
  const request = preflight.jobRequests.find(row => row.id === id);
  if (!request) throw new Error(`Missing job request ${id}`);
  const child = await runChild(NODE, [ORCHESTRATOR, '--mode', 'start', '--job-root', request.jobRoot, '--request', request.uri, '--preflight-evidence-commit', preflight.evidenceCommit, ...extra]);
  return { request, child };
}

async function runResume(jobRoot) {
  return runChild(NODE, [ORCHESTRATOR, '--mode', 'resume', '--job-root', jobRoot]);
}

async function finalReference(jobRoot) {
  const absolutePath = resolve(repositoryRoot, jobRoot, 'final-receipt.json');
  const value = JSON.parse(await readFile(absolutePath, 'utf8'));
  if (!validSelfHash(value, 'receiptHash')) throw new Error(`Invalid final receipt ${jobRoot}`);
  return { uri: `${jobRoot}/final-receipt.json`, sha256: await sha256File(absolutePath), receiptHash: value.receiptHash, value };
}

async function runBaseline(preflight) {
  const { request, child: start } = await runJobStart(preflight, 'BASELINE_B01');
  const startState = parseJobOutput(start, 'COMPLETE');
  if (start.exitCode !== 0 || !startState.complete) throw new Error('Baseline job did not complete');
  const before = await readEvents(request.jobRoot);
  const beforeFinal = await finalReference(request.jobRoot);
  const closed = await runResume(request.jobRoot);
  const closedState = parseJobOutput(closed, 'ALREADY_FINALIZED');
  const after = await readEvents(request.jobRoot);
  const afterFinal = await finalReference(request.jobRoot);
  if (closed.exitCode !== 0 || !closedState.complete || before.length !== after.length || beforeFinal.sha256 !== afterFinal.sha256) throw new Error('Baseline closed resume was not byte exact');
  return { id: 'BASELINE_B01', request, invocations: { start: compactChild(start), closedResume: compactChild(closed) }, eventCount: after.length, finalReceipt: afterFinal };
}

async function runExit86(preflight) {
  const { request, child: first } = await runJobStart(preflight, 'ORCHESTRATOR_EXIT_AFTER_COMPILE_B01');
  const checkpoint = parseJobOutput(first, 'ORCHESTRATOR_EXIT_AFTER_COMPILE');
  if (first.exitCode !== 86 || checkpoint.complete) throw new Error('Exit-86 job did not stop at checkpoint');
  const before = await readEvents(request.jobRoot);
  if (countEvent(before, 'NATIVE_PROCESS_OBSERVED', 'PRODUCTION_COMPILE') !== 1 || countEvent(before, 'STAGE_STARTED', 'VERIFY_RECEIPT') !== 0) throw new Error('Exit-86 checkpoint boundary mismatch');
  const resume = await runResume(request.jobRoot);
  const resumed = parseJobOutput(resume, 'COMPLETE');
  if (resume.exitCode !== 0 || !resumed.complete) throw new Error('Exit-86 recovery did not complete');
  const after = await readEvents(request.jobRoot);
  if (countEvent(after, 'NATIVE_PROCESS_OBSERVED', 'PRODUCTION_COMPILE') !== 1) throw new Error('Exit-86 recovery repeated native compile');
  const final = await finalReference(request.jobRoot);
  const closed = await runResume(request.jobRoot);
  parseJobOutput(closed, 'ALREADY_FINALIZED');
  if ((await finalReference(request.jobRoot)).sha256 !== final.sha256) throw new Error('Exit-86 closed resume changed final receipt');
  return {
    id: 'ORCHESTRATOR_EXIT_AFTER_COMPILE_B01', request,
    invocations: { checkpoint: compactChild(first), recovery: compactChild(resume), closedResume: compactChild(closed) },
    eventCounts: { before: before.length, after: after.length },
    nativeObservations: { before: countEvent(before, 'NATIVE_PROCESS_OBSERVED'), after: countEvent(after, 'NATIVE_PROCESS_OBSERVED') },
    finalReceipt: final,
  };
}

async function runInterrupted(preflight) {
  const { request, child: first } = await runJobStart(preflight, 'BLENDER_INTERRUPTED_B02');
  const failed = parseJobOutput(first, 'COMPILE_FAILED_NEEDS_RESUME');
  if (first.exitCode !== 0 || failed.stages.PRODUCTION_COMPILE.status !== 'FAILED') throw new Error('Interrupted B02 did not retain failed attempt');
  const before = await readEvents(request.jobRoot);
  const resume = await runResume(request.jobRoot);
  const resumed = parseJobOutput(resume, 'COMPLETE');
  if (resume.exitCode !== 0 || !resumed.complete) throw new Error('Interrupted B02 recovery did not complete');
  const after = await readEvents(request.jobRoot);
  if (countEvent(after, 'FAULT_INJECTED') !== 1 || countEvent(after, 'NATIVE_PROCESS_OBSERVED') !== 2) throw new Error('Interrupted B02 process counts mismatch');
  const final = await finalReference(request.jobRoot);
  const closed = await runResume(request.jobRoot);
  parseJobOutput(closed, 'ALREADY_FINALIZED');
  if ((await finalReference(request.jobRoot)).sha256 !== final.sha256) throw new Error('Interrupted B02 closed resume changed final receipt');
  return {
    id: 'BLENDER_INTERRUPTED_B02', request,
    invocations: { interrupted: compactChild(first), recovery: compactChild(resume), closedResume: compactChild(closed) },
    eventCounts: { before: before.length, after: after.length },
    nativeObservations: { before: countEvent(before, 'NATIVE_PROCESS_OBSERVED'), after: countEvent(after, 'NATIVE_PROCESS_OBSERVED') },
    finalReceipt: final,
  };
}

async function runLive(preflight) {
  const { request, child: plan } = await runJobStart(preflight, 'LIVE_PROCESS_REFUSAL', ['--development-stop-after-plan']);
  const planState = parseJobOutput(plan, 'DEVELOPMENT_PLAN_CHECKPOINT');
  if (plan.exitCode !== 0 || planState.stages.PLAN_BIND.status !== 'COMPLETED') throw new Error('Live-process PLAN checkpoint failed');
  const controlled = spawn(NODE, ['-e', 'setInterval(() => {}, 1000)'], {
    cwd: repositoryRoot,
    env: { PATH: '/opt/homebrew/bin:/usr/bin:/bin', LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8' },
    stdio: 'ignore',
  });
  let identity = null;
  try {
    identity = await readProcessIdentity(controlled.pid);
    if (!identity.live) throw new Error('Controlled live child exited before identity observation');
    const attemptId = 'LIVE-COMPILE-0001';
    const manifest = JSON.parse(await readFile(resolve(repositoryRoot, request.jobRoot, 'job-manifest.json'), 'utf8'));
    const candidate = manifest.compileAttempts[0];
    await appendLedgerEvent(resolve(repositoryRoot, request.jobRoot), {
      eventType: 'STAGE_STARTED', stageId: 'PRODUCTION_COMPILE', attemptId,
      payload: { candidate: { ...candidate }, controlledLiveProbe: true },
    });
    await appendLedgerEvent(resolve(repositoryRoot, request.jobRoot), {
      eventType: 'PROCESS_STARTED', stageId: 'PRODUCTION_COMPILE', attemptId,
      payload: { role: 'CONTROLLED_LIVE_PROCESS', process: identity },
    });
    const before = await readEvents(request.jobRoot);
    const resume = await runResume(request.jobRoot);
    const waited = parseJobOutput(resume, 'WAIT_LIVE_PROCESS');
    const after = await readEvents(request.jobRoot);
    if (resume.exitCode !== 0 || waited.waitProcess?.pid !== controlled.pid || waited.waitProcess?.identityHash !== identity.identityHash
      || countEvent(before, 'PROCESS_STARTED') !== countEvent(after, 'PROCESS_STARTED')
      || countEvent(before, 'NATIVE_PROCESS_OBSERVED') !== countEvent(after, 'NATIVE_PROCESS_OBSERVED')) {
      throw new Error('Live-process recovery did not wait on the exact child');
    }
    return {
      id: 'LIVE_PROCESS_REFUSAL', request,
      invocations: { plan: compactChild(plan), wait: compactChild(resume) },
      controlledProcess: identity,
      waitProcess: waited.waitProcess,
      eventCounts: { before: before.length, after: after.length },
      processStarts: { before: countEvent(before, 'PROCESS_STARTED'), after: countEvent(after, 'PROCESS_STARTED') },
      nativeStarts: { before: countEvent(before, 'NATIVE_PROCESS_OBSERVED'), after: countEvent(after, 'NATIVE_PROCESS_OBSERVED') },
      outputMaterialized: false,
    };
  } finally {
    if (controlled.exitCode === null && controlled.signalCode === null) controlled.kill('SIGTERM');
    await new Promise(resolvePromise => controlled.once('close', resolvePromise));
  }
}

async function writeAdmissionFailure(parsed, attemptPath, attempt, error, gitChildren) {
  const failurePath = resolve(repositoryRoot, parsed.attemptRoot, 'failure.json');
  const { record: failure } = await writeExclusiveDurableHashed(failurePath, {
    schemaVersion: 'bfs.restartSafeProductionOrchestratorAdmissionFailure.v0.1',
    sequence: 2, status: 'REJECTED', reason: error instanceof AdmissionError ? error.reason : 'ADMISSION_EXCEPTION',
    message: error?.message ?? String(error), attempt: { uri: `${parsed.attemptRoot}/attempt.json`, sha256: await sha256File(attemptPath), attemptHash: attempt.attemptHash },
    gitChildren, formalOutputMaterialized: false, blenderProcessesStarted: 0, scientificVerdict: null,
  }, 'failureHash');
  await writeExclusiveDurableHashed(resolve(repositoryRoot, parsed.attemptRoot, 'receipt.json'), {
    schemaVersion: 'bfs.restartSafeProductionOrchestratorAttemptReceipt.v0.1', sequence: 3, status: 'REJECTED',
    attempt: { uri: `${parsed.attemptRoot}/attempt.json`, sha256: await sha256File(attemptPath), attemptHash: attempt.attemptHash },
    failure: { uri: `${parsed.attemptRoot}/failure.json`, sha256: await sha256File(failurePath), failureHash: failure.failureHash },
    formalOutputMaterialized: false, blenderProcessesStarted: 0, scientificVerdict: null,
  }, 'receiptHash');
}

export async function runB58Formal(argv) {
  const parsed = parseArguments(argv);
  const preflightPath = resolve(repositoryRoot, parsed.preflightRoot, 'preflight.json');
  const preflight = JSON.parse(await readFile(preflightPath, 'utf8'));
  if (preflight.schemaVersion !== 'bfs.restartSafeProductionOrchestratorPreflight.v0.1' || preflight.status !== 'ACCEPTED' || !validSelfHash(preflight, 'preflightHash')) throw new Error('B58 preflight is not accepted and exact');
  if (preflight.invocation.attemptRoot !== parsed.attemptRoot || preflight.invocation.formalRoot !== parsed.formalRoot) throw new Error('B58 root binding mismatch');
  const gate0 = await verifyGate0Binding(preflight);
  preflight.evidenceCommit = parsed.preflightEvidenceCommit;
  await durableMkdir(resolve(repositoryRoot, parsed.attemptRoot));
  const attemptPath = resolve(repositoryRoot, parsed.attemptRoot, 'attempt.json');
  const { record: attempt } = await writeExclusiveDurableHashed(attemptPath, {
    schemaVersion: 'bfs.restartSafeProductionOrchestratorAttempt.v0.1', sequence: 1, invocation: parsed,
    preflight: { uri: `${parsed.preflightRoot}/preflight.json`, sha256: await sha256File(preflightPath), preflightHash: preflight.preflightHash },
    runnerPid: process.pid, formalOutputAbsent: true, blenderProcessesAuthorized: 0, scientificVerdict: null,
  }, 'attemptHash');
  const gitChildren = [];
  let admission;
  try {
    admission = await admitFormalRun({ repositoryRoot, evidenceInput: parsed.preflightRoot, formalOutput: parsed.formalRoot, originRef: 'origin/main', gitObserver: row => gitChildren.push(row) });
    if (admission.evidence.evidenceCommit !== parsed.preflightEvidenceCommit) throw new AdmissionError('EVIDENCE_COMMIT_MISMATCH', 'B58 preflight evidence commit mismatch');
  } catch (error) {
    await writeAdmissionFailure(parsed, attemptPath, attempt, error, gitChildren);
    process.stdout.write(`BFS_B58_FORMAL REJECTED ${error.reason ?? 'ADMISSION_EXCEPTION'} blender=0\n`);
    process.exitCode = 1;
    return { status: 'REJECTED' };
  }
  const admissionPath = resolve(repositoryRoot, parsed.attemptRoot, 'admission.json');
  const { record: admissionRecord } = await writeExclusiveDurableHashed(admissionPath, {
    schemaVersion: 'bfs.restartSafeProductionOrchestratorAdmission.v0.1', sequence: 2, status: 'ACCEPTED',
    evidence: admission.evidence, output: admission.output,
    attempt: { uri: `${parsed.attemptRoot}/attempt.json`, sha256: await sha256File(attemptPath), attemptHash: attempt.attemptHash },
    gitChildren, blenderProcessesStarted: 0, scientificVerdict: null,
  }, 'admissionHash');
  const attemptReceiptPath = resolve(repositoryRoot, parsed.attemptRoot, 'receipt.json');
  const { record: attemptReceipt } = await writeExclusiveDurableHashed(attemptReceiptPath, {
    schemaVersion: 'bfs.restartSafeProductionOrchestratorAttemptReceipt.v0.1', sequence: 3, status: 'ACCEPTED',
    attempt: { uri: `${parsed.attemptRoot}/attempt.json`, sha256: await sha256File(attemptPath), attemptHash: attempt.attemptHash },
    admission: { uri: `${parsed.attemptRoot}/admission.json`, sha256: await sha256File(admissionPath), admissionHash: admissionRecord.admissionHash },
    formalOutput: admission.output, outputMaterializationAuthorized: true, scientificVerdict: null,
  }, 'receiptHash');
  await durableMkdir(resolve(repositoryRoot, parsed.formalRoot));
  const formalStartPath = resolve(repositoryRoot, parsed.formalRoot, 'formal-start.json');
  await writeExclusiveDurableHashed(formalStartPath, {
    schemaVersion: 'bfs.restartSafeProductionOrchestratorFormalStart.v0.1', sequence: 4, status: 'AUTHORIZED',
    attemptReceipt: { uri: `${parsed.attemptRoot}/receipt.json`, sha256: await sha256File(attemptReceiptPath), receiptHash: attemptReceipt.receiptHash },
    gate0, formalRoot: parsed.formalRoot, blenderProcessesStarted: 0,
  }, 'formalStartHash');

  const jobs = [];
  jobs.push(await runBaseline(preflight));
  jobs.push(await runExit86(preflight));
  jobs.push(await runInterrupted(preflight));
  jobs.push(await runLive(preflight));
  const operationPath = resolve(repositoryRoot, parsed.formalRoot, 'operation-draft.json');
  const { record: operation } = await writeExclusiveDurableHashed(operationPath, {
    schemaVersion: 'bfs.restartSafeProductionOrchestratorOperationDraft.v0.1',
    experimentId: 'B58-E1',
    jobs,
    counts: {
      productionCompilerStarts: 4,
      nativeCompileBlenderStarts: 4,
      successfulNativeCompiles: 3,
      controlledInterruptedNativeCompiles: 1,
      preferredVerifierStarts: 3,
      currentReceiptVerifierNodeChildren: 3,
      artifactAuditBlenderStarts: 3,
      totalBlenderStarts: 7,
      controlledLiveNodeStarts: 1,
    },
    semanticOperations: { renderCalls: 0, modelCalls: 0, networkCalls: 0, dockerProcesses: 0 },
  }, 'operationHash');
  const auditPath = resolve(repositoryRoot, parsed.formalRoot, 'audit.json');
  const auditor = await runChild(NODE, [AUDITOR, '--repository-root', repositoryRoot, '--preflight-root', parsed.preflightRoot, '--attempt-root', parsed.attemptRoot, '--formal-root', parsed.formalRoot, '--output', auditPath]);
  if (auditor.exitCode !== 0 || auditor.signal !== null) throw new Error(`B58 auditor failed: ${auditor.stderr || auditor.stdout}`);
  const audit = JSON.parse(await readFile(auditPath, 'utf8'));
  if (!validSelfHash(audit, 'auditHash')) throw new Error('B58 audit self-hash mismatch');
  const resultsPath = resolve(repositoryRoot, parsed.formalRoot, 'results.json');
  const { record: results } = await writeExclusiveDurableHashed(resultsPath, {
    schemaVersion: 'bfs.restartSafeProductionOrchestratorResult.v0.1', experimentId: 'B58-E1',
    spec: preflight.spec, correction: preflight.correction, gate0Correction: preflight.gate0Correction, gate0,
    preflight: { uri: `${parsed.preflightRoot}/preflight.json`, sha256: await sha256File(preflightPath), preflightHash: preflight.preflightHash },
    operation: { uri: `${parsed.formalRoot}/operation-draft.json`, sha256: await sha256File(operationPath), operationHash: operation.operationHash },
    audit: { uri: `${parsed.formalRoot}/audit.json`, sha256: await sha256File(auditPath), auditHash: audit.auditHash },
    gates: audit.gates, attackSummary: audit.attackSummary, correctionAttackSummary: audit.correctionAttackSummary, gate0CorrectionAttackSummary: audit.gate0CorrectionAttackSummary,
    scientificVerdict: audit.scientificVerdict,
  }, 'resultHash');
  const receiptPath = resolve(repositoryRoot, parsed.formalRoot, 'receipt.json');
  const { record: receipt } = await writeExclusiveDurableHashed(receiptPath, {
    schemaVersion: 'bfs.restartSafeProductionOrchestratorFormalReceipt.v0.1', experimentId: 'B58-E1', allEvidenceRetained: true,
    results: { uri: `${parsed.formalRoot}/results.json`, sha256: await sha256File(resultsPath), resultHash: results.resultHash },
    audit: { uri: `${parsed.formalRoot}/audit.json`, sha256: await sha256File(auditPath), auditHash: audit.auditHash },
    scientificVerdict: audit.scientificVerdict, sameIdRepairAndRerunForbidden: true,
  }, 'receiptHash');
  process.stdout.write(`BFS_B58_FORMAL ${audit.scientificVerdict} gates=${audit.gatePassed}/${audit.gateTotal} attacks=${audit.attackSummary.rejected}/${audit.attackSummary.total} correction=${audit.correctionAttackSummary.rejected}/${audit.correctionAttackSummary.total} gate0=${audit.gate0CorrectionAttackSummary.rejected}/${audit.gate0CorrectionAttackSummary.total} ${receipt.receiptHash}\n`);
  return { status: 'COMPLETE', scientificVerdict: audit.scientificVerdict, receipt };
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  runB58Formal(process.argv.slice(2)).catch(error => {
    process.stderr.write(`BFS_B58_FORMAL_ERROR ${error.message}\n`);
    process.exitCode = 1;
  });
}
