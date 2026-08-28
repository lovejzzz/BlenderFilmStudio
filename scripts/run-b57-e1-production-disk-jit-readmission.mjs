#!/usr/bin/env node

import { spawn } from 'node:child_process';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { AdmissionError, admitFormalRun } from './lib/formal-run-admission.mjs';
import {
  durableMkdir,
  repoUri,
  sha256File,
  validSelfHash,
  writeDurableHashed,
} from './lib/production-compile-receipt.mjs';
import { repositoryRoot } from './lib/scene-spec.mjs';

const NPM = '/opt/homebrew/bin/npm';
const NODE = '/opt/homebrew/Cellar/node/26.5.0/bin/node';
const AUDITOR = 'scripts/audit-b57-e1-production-disk-jit-readmission.mjs';
const LOW_CEILING = '107911053311';

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

async function runChild(command, args, env = {}) {
  const started = process.hrtime.bigint();
  const child = spawn(command, args, {
    cwd: repositoryRoot,
    env: { PATH: '/opt/homebrew/bin:/usr/bin:/bin', LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8', ...env },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  const stdout = [];
  const stderr = [];
  child.stdout.on('data', chunk => stdout.push(chunk));
  child.stderr.on('data', chunk => stderr.push(chunk));
  const completion = await new Promise((resolvePromise, reject) => {
    child.on('error', reject);
    child.on('close', (exitCode, signal) => resolvePromise({ exitCode, signal }));
  });
  return { pid: child.pid, ...completion, elapsedNanoseconds: Number(process.hrtime.bigint() - started), stdout: Buffer.concat(stdout).toString('utf8'), stderr: Buffer.concat(stderr).toString('utf8') };
}

async function runNpm(script, args, env = {}) { return runChild(NPM, ['run', script, '--', ...args], env); }

async function textHash(text) {
  const { createHash } = await import('node:crypto');
  return createHash('sha256').update(text).digest('hex');
}

async function compactAsync(child) {
  return { pid: child.pid, exitCode: child.exitCode, signal: child.signal, elapsedNanoseconds: child.elapsedNanoseconds, stdoutSha256: await textHash(child.stdout), stderrSha256: await textHash(child.stderr) };
}

function parseVerification(stdout) {
  const line = stdout.split('\n').find(row => row.startsWith('BFS_PRODUCTION_RECEIPT_VERIFICATION_JSON '));
  if (!line) throw new Error('Preferred verifier JSON line missing');
  return JSON.parse(line.slice('BFS_PRODUCTION_RECEIPT_VERIFICATION_JSON '.length));
}

async function writeAdmissionFailure(attemptRoot, attemptPath, attempt, error, gitChildren) {
  const failurePath = resolve(attemptRoot, 'failure.json');
  const failure = await writeDurableHashed(failurePath, {
    schemaVersion: 'bfs.productionDiskJitReadmissionAdmissionFailure.v0.1', sequence: 2, status: 'REJECTED',
    reason: error instanceof AdmissionError ? error.reason : 'ADMISSION_EXCEPTION', message: error?.message ?? String(error),
    attempt: { uri: repoUri(attemptPath), sha256: await sha256File(attemptPath), attemptHash: attempt.attemptHash }, gitChildren,
    formalOutputMaterialized: false, blenderProcessesStarted: 0, scientificVerdict: null,
  }, 'failureHash');
  await writeDurableHashed(resolve(attemptRoot, 'receipt.json'), {
    schemaVersion: 'bfs.productionDiskJitReadmissionAttemptReceipt.v0.1', sequence: 3, status: 'REJECTED',
    attempt: { uri: repoUri(attemptPath), sha256: await sha256File(attemptPath), attemptHash: attempt.attemptHash },
    failure: { uri: repoUri(failurePath), sha256: await sha256File(failurePath), failureHash: failure.failureHash },
    formalOutputMaterialized: false, blenderProcessesStarted: 0, scientificVerdict: null,
  }, 'receiptHash');
}

export async function runB57Formal(argv) {
  const parsed = parseArguments(argv);
  const preflightPath = resolve(repositoryRoot, parsed.preflightRoot, 'preflight.json');
  const preflight = JSON.parse(await readFile(preflightPath, 'utf8'));
  if (preflight.schemaVersion !== 'bfs.productionDiskJitReadmissionPreflight.v0.1' || preflight.status !== 'ACCEPTED' || !validSelfHash(preflight, 'preflightHash')) throw new Error('B57 preflight is not accepted and exact');
  if (preflight.invocation.attemptRoot !== parsed.attemptRoot || preflight.invocation.formalRoot !== parsed.formalRoot) throw new Error('B57 root binding mismatch');
  await durableMkdir(resolve(repositoryRoot, parsed.attemptRoot));
  const attemptPath = resolve(repositoryRoot, parsed.attemptRoot, 'attempt.json');
  const attempt = await writeDurableHashed(attemptPath, {
    schemaVersion: 'bfs.productionDiskJitReadmissionAttempt.v0.1', sequence: 1, invocation: parsed,
    preflight: { uri: repoUri(preflightPath), sha256: await sha256File(preflightPath), preflightHash: preflight.preflightHash },
    runnerPid: process.pid, formalOutputAbsent: true, blenderProcessesAuthorized: 0, scientificVerdict: null,
  }, 'attemptHash');
  const gitChildren = [];
  let admission;
  try {
    admission = await admitFormalRun({ repositoryRoot, evidenceInput: parsed.preflightRoot, formalOutput: parsed.formalRoot, originRef: 'origin/main', gitObserver: row => gitChildren.push(row) });
    if (admission.evidence.evidenceCommit !== parsed.preflightEvidenceCommit) throw new AdmissionError('EVIDENCE_COMMIT_MISMATCH', 'B57 preflight evidence commit mismatch');
  } catch (error) {
    await writeAdmissionFailure(resolve(repositoryRoot, parsed.attemptRoot), attemptPath, attempt, error, gitChildren);
    process.stdout.write(`BFS_B57_FORMAL REJECTED ${error.reason ?? 'ADMISSION_EXCEPTION'} blender=0\n`);
    process.exitCode = 1;
    return { status: 'REJECTED' };
  }
  const admissionPath = resolve(repositoryRoot, parsed.attemptRoot, 'admission.json');
  const admissionRecord = await writeDurableHashed(admissionPath, {
    schemaVersion: 'bfs.productionDiskJitReadmissionAdmission.v0.1', sequence: 2, status: 'ACCEPTED', evidence: admission.evidence, output: admission.output,
    attempt: { uri: repoUri(attemptPath), sha256: await sha256File(attemptPath), attemptHash: attempt.attemptHash }, gitChildren, blenderProcessesStarted: 0, scientificVerdict: null,
  }, 'admissionHash');
  const attemptReceiptPath = resolve(repositoryRoot, parsed.attemptRoot, 'receipt.json');
  const attemptReceipt = await writeDurableHashed(attemptReceiptPath, {
    schemaVersion: 'bfs.productionDiskJitReadmissionAttemptReceipt.v0.1', sequence: 3, status: 'ACCEPTED',
    attempt: { uri: repoUri(attemptPath), sha256: await sha256File(attemptPath), attemptHash: attempt.attemptHash },
    admission: { uri: repoUri(admissionPath), sha256: await sha256File(admissionPath), admissionHash: admissionRecord.admissionHash },
    formalOutput: admission.output, outputMaterializationAuthorized: true, scientificVerdict: null,
  }, 'receiptHash');
  await durableMkdir(resolve(repositoryRoot, parsed.formalRoot));
  const formalStartPath = resolve(repositoryRoot, parsed.formalRoot, 'formal-start.json');
  await writeDurableHashed(formalStartPath, {
    schemaVersion: 'bfs.productionDiskJitReadmissionFormalStart.v0.1', sequence: 4, status: 'AUTHORIZED',
    attemptReceipt: { uri: repoUri(attemptReceiptPath), sha256: await sha256File(attemptReceiptPath), receiptHash: attemptReceipt.receiptHash },
    formalRoot: parsed.formalRoot, blenderProcessesStarted: 0,
  }, 'formalStartHash');
  await durableMkdir(resolve(repositoryRoot, parsed.attemptRoot, 'production-attempts'));
  await durableMkdir(resolve(repositoryRoot, parsed.formalRoot, 'runs'));

  const low = preflight.productionPreflights.find(row => row.runId === 'LOW-DISK');
  const lowAttempt = `${parsed.attemptRoot}/production-attempts/LOW-DISK`;
  const lowCompile = await runNpm('compile:production', ['--scene-spec', 'specs/benchmarks/B01.scene.json', '--preflight-root', low.preflightRoot, '--attempt-root', lowAttempt, '--output-root', low.output, '--preflight-evidence-commit', parsed.preflightEvidenceCommit], { BFS_PRODUCTION_COMPILE_AVAILABLE_BYTES_CEILING: LOW_CEILING });
  const lowDisk = JSON.parse(await readFile(resolve(repositoryRoot, low.output, 'native-compile-disk-admission.json'), 'utf8'));
  const lowInvalidation = JSON.parse(await readFile(resolve(repositoryRoot, low.output, 'invalidation.json'), 'utf8'));
  if (lowCompile.exitCode !== 1 || lowDisk.status !== 'REJECTED' || lowInvalidation.phase !== 'NATIVE_COMPILE_DISK_ADMISSION') throw new Error('B57 low-disk case did not fail at the frozen boundary');

  const runs = [];
  for (const row of preflight.productionPreflights.filter(item => item.runId !== 'LOW-DISK')) {
    const attemptRoot = `${parsed.attemptRoot}/production-attempts/${row.runId}`;
    const scene = `specs/benchmarks/${row.benchmarkId}.scene.json`;
    const compile = await runNpm('compile:production', ['--scene-spec', scene, '--preflight-root', row.preflightRoot, '--attempt-root', attemptRoot, '--output-root', row.output, '--preflight-evidence-commit', parsed.preflightEvidenceCommit]);
    if (compile.exitCode !== 0 || compile.signal !== null) throw new Error(`${row.runId} preferred compile failed: ${compile.stderr || compile.stdout}`);
    const receiptUri = `${row.output}/production-receipt.json`;
    const verify = await runNpm('verify:production-receipt', ['--receipt', receiptUri]);
    const verification = parseVerification(verify.stdout);
    if (verify.exitCode !== 0 || !verification.valid || verification.checks.length !== 11) throw new Error(`${row.runId} preferred verifier failed`);
    const receipt = JSON.parse(await readFile(resolve(repositoryRoot, receiptUri), 'utf8'));
    runs.push({ runId: row.runId, benchmarkId: row.benchmarkId, attemptRoot, outputRoot: row.output, receipt: { uri: receiptUri, sha256: await sha256File(resolve(repositoryRoot, receiptUri)), receiptHash: receipt.receiptHash }, compile: await compactAsync(compile), verify: await compactAsync(verify), verification });
  }
  const operationBody = {
    schemaVersion: 'bfs.productionDiskJitReadmissionOperationDraft.v0.1', experimentId: 'B57-E1',
    lowDisk: { preflightRoot: low.preflightRoot, attemptRoot: lowAttempt, outputRoot: low.output, compile: await compactAsync(lowCompile), diskAdmissionHash: lowDisk.diskAdmissionHash, invalidationHash: lowInvalidation.invalidationHash },
    runs,
    counts: { productionCompiles: 4, nativeCompiles: 4, preferredVerifiers: 4, lowDiskRestrictedCompiles: 0 },
    semanticOperations: { renderCalls: 0, modelCalls: 0, networkCalls: 0, dockerProcesses: 0 },
  };
  const operationDraft = await writeDurableHashed(resolve(repositoryRoot, parsed.formalRoot, 'operation-draft.json'), operationBody, 'operationHash');
  const auditPath = resolve(repositoryRoot, parsed.formalRoot, 'audit.json');
  const auditor = await runChild(NODE, [AUDITOR, '--repository-root', repositoryRoot, '--preflight-root', parsed.preflightRoot, '--attempt-root', parsed.attemptRoot, '--formal-root', parsed.formalRoot, '--output', auditPath]);
  if (auditor.exitCode !== 0 || auditor.signal !== null) throw new Error(`B57 auditor failed: ${auditor.stderr || auditor.stdout}`);
  const audit = JSON.parse(await readFile(auditPath, 'utf8'));
  if (!validSelfHash(audit, 'auditHash')) throw new Error('B57 audit self-hash mismatch');
  const resultBody = {
    schemaVersion: 'bfs.productionDiskJitReadmissionResult.v0.1', experimentId: 'B57-E1',
    specSha256: preflight.specSha256, preflight: { uri: repoUri(preflightPath), sha256: await sha256File(preflightPath), preflightHash: preflight.preflightHash },
    operation: { uri: `${parsed.formalRoot}/operation-draft.json`, sha256: await sha256File(resolve(repositoryRoot, parsed.formalRoot, 'operation-draft.json')), operationHash: operationDraft.operationHash },
    audit: { uri: `${parsed.formalRoot}/audit.json`, sha256: await sha256File(auditPath), auditHash: audit.auditHash },
    gates: audit.gates, attackSummary: audit.attackSummary, scientificVerdict: audit.scientificVerdict,
  };
  const results = await writeDurableHashed(resolve(repositoryRoot, parsed.formalRoot, 'results.json'), resultBody, 'resultHash');
  const receiptBody = {
    schemaVersion: 'bfs.productionDiskJitReadmissionFormalReceipt.v0.1', experimentId: 'B57-E1', allEvidenceRetained: true,
    results: { uri: `${parsed.formalRoot}/results.json`, sha256: await sha256File(resolve(repositoryRoot, parsed.formalRoot, 'results.json')), resultHash: results.resultHash },
    audit: { uri: `${parsed.formalRoot}/audit.json`, sha256: await sha256File(auditPath), auditHash: audit.auditHash },
    scientificVerdict: audit.scientificVerdict, sameIdRepairAndRerunForbidden: true,
  };
  const receipt = await writeDurableHashed(resolve(repositoryRoot, parsed.formalRoot, 'receipt.json'), receiptBody, 'receiptHash');
  process.stdout.write(`BFS_B57_FORMAL ${audit.scientificVerdict} gates=${audit.gatePassed}/${audit.gateTotal} attacks=${audit.attackSummary.rejected}/${audit.attackSummary.total} ${receipt.receiptHash}\n`);
  return { status: 'COMPLETE', scientificVerdict: audit.scientificVerdict, receipt };
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  runB57Formal(process.argv.slice(2)).catch(error => { process.stderr.write(`BFS_B57_FORMAL_ERROR ${error.message}\n`); process.exitCode = 1; });
}
