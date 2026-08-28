#!/usr/bin/env node

import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { lstat, readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { compileBuildPlan } from './compile-build-plan.mjs';
import { AdmissionError, admitFormalRun } from './lib/formal-run-admission.mjs';
import {
  canonicalJson,
  durableMkdir,
  repoUri,
  sha256Bytes,
  sha256File,
  validSelfHash,
  writeDurableHashed,
} from './lib/production-compile-receipt.mjs';
import { repositoryRoot } from './lib/scene-spec.mjs';

const SPEC_URI = 'specs/production-compiler-entry-promotion.v0.1.json';
const SPEC_SHA256 = '40007b388dc851a22f5e030ec5135919922a1e15e075ef56769ed3330725fd5a';
const PREREGISTRATION_COMMIT = 'b9cf983abb3e741b5a7726200e9082bc50e1a89d';
const NPM = '/opt/homebrew/bin/npm';

function parseArguments(argv) {
  const parsed = { developmentProbe: false };
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--development-probe') parsed.developmentProbe = true;
    else if (token === '--preflight-root') parsed.preflightRoot = argv[++index];
    else if (token === '--attempt-root') parsed.attemptRoot = argv[++index];
    else if (token === '--output-root') parsed.outputRoot = argv[++index];
    else if (token === '--preflight-evidence-commit') parsed.preflightEvidenceCommit = argv[++index];
    else throw new Error(`Unknown or incomplete argument: ${token}`);
  }
  return parsed;
}

async function pathState(filePath) {
  try { return await lstat(filePath); } catch (error) {
    if (error?.code === 'ENOENT') return null;
    throw error;
  }
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
  const completion = await new Promise((resolvePromise, reject) => {
    child.on('error', reject);
    child.on('close', (exitCode, signal) => resolvePromise({ exitCode, signal }));
  });
  return { command, args, pid: child.pid, ...completion, elapsedNanoseconds: Number(process.hrtime.bigint() - started), stdout: Buffer.concat(stdout).toString('utf8'), stderr: Buffer.concat(stderr).toString('utf8') };
}

async function runNpm(script, args) {
  return runChild(NPM, ['run', script, '--', ...args]);
}

async function readAcceptedPreflight(root, spec) {
  const preflightPath = resolve(root, 'preflight.json');
  const preflight = JSON.parse(await readFile(preflightPath, 'utf8'));
  if (preflight.schemaVersion !== 'bfs.productionCompilerEntryPromotionPreflight.v0.1' || preflight.experimentId !== 'B56-E1'
    || preflight.status !== 'ACCEPTED' || !validSelfHash(preflight, 'preflightHash')) throw new Error('B56 accepted preflight mismatch');
  if (preflight.specSha256 !== SPEC_SHA256 || preflight.preregistrationCommit !== PREREGISTRATION_COMMIT
    || preflight.roots?.attemptAbsent !== true || preflight.roots?.formalAbsent !== true
    || preflight.observations?.accepted?.rows?.length !== 4 || !preflight.observations.accepted.rows.every(row => row.exact)) {
    throw new Error('B56 accepted preflight semantic binding mismatch');
  }
  for (const runId of spec.inputs.formalRuns) {
    const row = preflight.observations.accepted.rows.find(value => value.runId === runId);
    if (!row) throw new Error(`B56 production preflight missing ${runId}`);
  }
  return { preflight, preflightPath };
}

async function writeAdmissionFailure(attemptRoot, attemptPath, attempt, error, gitChildren) {
  const failurePath = resolve(attemptRoot, 'failure.json');
  const failure = await writeDurableHashed(failurePath, {
    schemaVersion: 'bfs.productionCompilerEntryPromotionAdmissionFailure.v0.1', experimentId: 'B56-E1', sequence: 2,
    status: 'REJECTED', reason: error instanceof AdmissionError ? error.reason : 'ADMISSION_EXCEPTION', message: error?.message ?? String(error),
    attempt: { uri: repoUri(attemptPath), sha256: await sha256File(attemptPath), attemptHash: attempt.attemptHash }, gitChildren,
    formalRootMaterialized: false, compilerProcessesStarted: 0, scientificVerdict: null,
  }, 'failureHash');
  await writeDurableHashed(resolve(attemptRoot, 'receipt.json'), {
    schemaVersion: 'bfs.productionCompilerEntryPromotionAttemptReceipt.v0.1', experimentId: 'B56-E1', sequence: 3,
    status: 'REJECTED', scientificVerdict: null,
    attempt: { uri: repoUri(attemptPath), sha256: await sha256File(attemptPath), attemptHash: attempt.attemptHash },
    failure: { uri: repoUri(failurePath), sha256: await sha256File(failurePath), failureHash: failure.failureHash },
    formalRootMaterialized: false, sameIdRepairAndRerunForbidden: true,
  }, 'receiptHash');
}

async function writeInvalidation(formalRoot, phase, error, context = {}) {
  try {
    await writeDurableHashed(resolve(formalRoot, 'invalidation.json'), {
      schemaVersion: 'bfs.productionCompilerEntryPromotionInvalidation.v0.1', experimentId: 'B56-E1', status: 'INVALIDATED',
      phase, error: { name: error?.name ?? 'Error', message: error?.message ?? String(error) }, context,
      partialEvidenceRetained: true, sameIdRepairAndRerunForbidden: true, scientificVerdict: null,
    }, 'invalidationHash');
  } catch (writeError) {
    if (writeError?.code !== 'EEXIST') throw writeError;
  }
}

async function developmentProbe(spec) {
  const rows = [];
  for (const benchmark of spec.inputs.benchmarks) {
    const first = await compileBuildPlan(benchmark.sceneSpecUri);
    const second = await compileBuildPlan(benchmark.sceneSpecUri);
    rows.push({ id: benchmark.id, pairExact: canonicalJson(first) === canonicalJson(second), frozenHashExact: first.planHash === benchmark.expectedPlanHash });
  }
  const rootsAbsent = [spec.freshness.preflightRoot, spec.freshness.attemptRoot, spec.freshness.formalRoot].every(uri => !existsSync(resolve(repositoryRoot, uri)));
  const status = rows.every(row => row.pairExact && row.frozenHashExact) && rootsAbsent ? 'PASS' : 'FAIL';
  process.stdout.write(`${JSON.stringify({ status, rows, rootsAbsent, blenderProcesses: 0, renderCalls: 0 })}\n`);
  if (status !== 'PASS') process.exitCode = 1;
}

async function main() {
  const args = parseArguments(process.argv.slice(2));
  if (await sha256File(resolve(repositoryRoot, SPEC_URI)) !== SPEC_SHA256) throw new Error('B56-E1 spec SHA-256 mismatch');
  const spec = JSON.parse(await readFile(resolve(repositoryRoot, SPEC_URI), 'utf8'));
  if (args.developmentProbe) return developmentProbe(spec);
  for (const field of ['preflightRoot', 'attemptRoot', 'outputRoot', 'preflightEvidenceCommit']) if (!args[field]) throw new Error(`Missing ${field}`);
  if (args.preflightRoot !== spec.freshness.preflightRoot || args.attemptRoot !== spec.freshness.attemptRoot || args.outputRoot !== spec.freshness.formalRoot) throw new Error('B56 frozen root spelling mismatch');
  if (!/^[0-9a-f]{40}$/.test(args.preflightEvidenceCommit)) throw new Error('B56 preflight evidence commit must be a full SHA-1');
  const preflightRoot = resolve(repositoryRoot, args.preflightRoot);
  const attemptRoot = resolve(repositoryRoot, args.attemptRoot);
  const formalRoot = resolve(repositoryRoot, args.outputRoot);
  if (!await pathState(preflightRoot) || await pathState(attemptRoot) || await pathState(formalRoot)) throw new Error('B56 root freshness mismatch');
  const { preflight, preflightPath } = await readAcceptedPreflight(preflightRoot, spec);

  await durableMkdir(attemptRoot);
  const attemptPath = resolve(attemptRoot, 'attempt.json');
  const attempt = await writeDurableHashed(attemptPath, {
    schemaVersion: 'bfs.productionCompilerEntryPromotionAttempt.v0.1', experimentId: 'B56-E1', sequence: 1,
    invocation: args, runnerPid: process.pid, preregistrationCommit: PREREGISTRATION_COMMIT, specSha256: SPEC_SHA256,
    preflight: { uri: repoUri(preflightPath), sha256: await sha256File(preflightPath), preflightHash: preflight.preflightHash },
    formalRootAbsentBeforeAdmission: true, blenderProcessesAuthorized: 0, scientificVerdict: null,
  }, 'attemptHash');

  const gitChildren = [];
  let admission;
  try {
    admission = await admitFormalRun({ repositoryRoot, evidenceInput: args.preflightRoot, formalOutput: args.outputRoot, originRef: 'origin/main', gitObserver: row => gitChildren.push(row) });
    if (admission.evidence.evidenceCommit !== args.preflightEvidenceCommit) throw new AdmissionError('EVIDENCE_COMMIT_MISMATCH', 'B56 preflight evidence commit mismatch');
  } catch (error) {
    await writeAdmissionFailure(attemptRoot, attemptPath, attempt, error, gitChildren);
    process.stdout.write(`BFS_B56_E1_FORMAL_ADMISSION_REJECTED ${error.reason ?? 'ADMISSION_EXCEPTION'} blender=0\n`);
    process.exitCode = 1;
    return;
  }

  const admissionPath = resolve(attemptRoot, 'admission.json');
  const admissionRecord = await writeDurableHashed(admissionPath, {
    schemaVersion: 'bfs.productionCompilerEntryPromotionAdmission.v0.1', experimentId: 'B56-E1', sequence: 2, status: 'ACCEPTED',
    evidence: admission.evidence, output: { repositoryRelative: admission.output.repositoryRelative, parentRepositoryRelative: admission.output.parentRepositoryRelative, fresh: admission.output.fresh },
    attempt: { uri: repoUri(attemptPath), sha256: await sha256File(attemptPath), attemptHash: attempt.attemptHash }, gitChildren,
    compilerProcessesStarted: 0, scientificVerdict: null,
  }, 'admissionHash');
  const attemptReceiptPath = resolve(attemptRoot, 'receipt.json');
  const attemptReceipt = await writeDurableHashed(attemptReceiptPath, {
    schemaVersion: 'bfs.productionCompilerEntryPromotionAttemptReceipt.v0.1', experimentId: 'B56-E1', sequence: 3, status: 'ACCEPTED', scientificVerdict: null,
    attempt: { uri: repoUri(attemptPath), sha256: await sha256File(attemptPath), attemptHash: attempt.attemptHash },
    admission: { uri: repoUri(admissionPath), sha256: await sha256File(admissionPath), admissionHash: admissionRecord.admissionHash },
    formalOutput: admissionRecord.output, formalRootMaterializationAuthorized: true, sameIdRepairAndRerunForbiddenOnFailure: true,
  }, 'receiptHash');

  let phase = 'FORMAL_START';
  try {
    await durableMkdir(formalRoot);
    const formalStart = await writeDurableHashed(resolve(formalRoot, 'formal-start.json'), {
      schemaVersion: 'bfs.productionCompilerEntryPromotionFormalStart.v0.1', experimentId: 'B56-E1', sequence: 4, status: 'AUTHORIZED',
      attemptReceipt: { uri: repoUri(attemptReceiptPath), sha256: await sha256File(attemptReceiptPath), receiptHash: attemptReceipt.receiptHash },
      compilerProcessesStarted: 0, scientificVerdict: null,
    }, 'formalStartHash');
    const productionAttempts = resolve(attemptRoot, 'production-attempts');
    const runsRoot = resolve(formalRoot, 'runs');
    await durableMkdir(productionAttempts);
    await durableMkdir(runsRoot);

    phase = 'PRODUCTION_RUNS';
    const runs = [];
    for (const runId of spec.inputs.formalRuns) {
      const benchmark = spec.inputs.benchmarks.find(row => runId.startsWith(row.id));
      const preflightRow = preflight.observations.accepted.rows.find(row => row.runId === runId);
      const productionAttempt = `${repoUri(productionAttempts)}/${runId}`;
      const productionOutput = `${repoUri(runsRoot)}/${runId}`;
      const compileChild = await runNpm('compile:production', [
        '--scene-spec', benchmark.sceneSpecUri,
        '--preflight-root', preflightRow.record.uri.replace(/\/preflight\.json$/, ''),
        '--attempt-root', productionAttempt,
        '--output-root', productionOutput,
        '--preflight-evidence-commit', args.preflightEvidenceCommit,
      ]);
      if (compileChild.exitCode !== 0 || compileChild.signal !== null) throw new Error(`Production alias failed for ${runId}: ${compileChild.stderr || compileChild.stdout}`);
      const receiptPath = resolve(repositoryRoot, productionOutput, 'production-receipt.json');
      const receipt = JSON.parse(await readFile(receiptPath, 'utf8'));
      if (!validSelfHash(receipt, 'receiptHash')) throw new Error(`Production receipt self-hash failed for ${runId}`);
      const verifyChild = await runNpm('verify:production-receipt', ['--receipt', repoUri(receiptPath)]);
      const jsonLine = verifyChild.stdout.split('\n').find(line => line.startsWith('BFS_PRODUCTION_RECEIPT_VERIFICATION_JSON '));
      if (verifyChild.exitCode !== 0 || verifyChild.signal !== null || !jsonLine) throw new Error(`Production verifier alias failed for ${runId}: ${verifyChild.stderr || verifyChild.stdout}`);
      const verification = JSON.parse(jsonLine.slice('BFS_PRODUCTION_RECEIPT_VERIFICATION_JSON '.length));
      if (!verification.valid || verification.checks.length !== 10) throw new Error(`Production verification did not pass ten checks for ${runId}`);
      runs.push({
        runId, benchmarkId: benchmark.id,
        compileAlias: { pid: compileChild.pid, exitCode: compileChild.exitCode, signal: compileChild.signal, elapsedNanoseconds: compileChild.elapsedNanoseconds, stdoutSha256: sha256Bytes(Buffer.from(compileChild.stdout)), stderrSha256: sha256Bytes(Buffer.from(compileChild.stderr)) },
        verifyAlias: { pid: verifyChild.pid, exitCode: verifyChild.exitCode, signal: verifyChild.signal, elapsedNanoseconds: verifyChild.elapsedNanoseconds, stdoutSha256: sha256Bytes(Buffer.from(verifyChild.stdout)), stderrSha256: sha256Bytes(Buffer.from(verifyChild.stderr)) },
        attempt: { uri: productionAttempt, attemptHash: (JSON.parse(await readFile(resolve(repositoryRoot, productionAttempt, 'attempt.json'), 'utf8'))).attemptHash },
        receipt: { uri: repoUri(receiptPath), sha256: await sha256File(receiptPath), receiptHash: receipt.receiptHash },
        verification,
        planHash: receipt.buildPlan.planHash,
        structureHash: receipt.restrictedCompile.sceneStructureCanonical.structureHash,
        wrapperPid: receipt.restrictedCompile.wrapperProcess.pid,
        nativePid: receipt.restrictedCompile.budgetReport.nativeChildPid,
      });
    }

    const pairIdentity = spec.inputs.benchmarks.map(benchmark => {
      const pair = runs.filter(row => row.benchmarkId === benchmark.id);
      return {
        id: benchmark.id,
        count: pair.length,
        planHash: pair[0]?.planHash ?? null,
        structureHash: pair[0]?.structureHash ?? null,
        planPairExact: pair.length === 2 && pair.every(row => row.planHash === benchmark.expectedPlanHash),
        structurePairExact: pair.length === 2 && pair.every(row => row.structureHash === benchmark.expectedStructureHash),
      };
    });
    const operationDraft = await writeDurableHashed(resolve(formalRoot, 'operation-draft.json'), {
      schemaVersion: 'bfs.productionCompilerEntryPromotionOperationDraft.v0.1', experimentId: 'B56-E1',
      formalStartHash: formalStart.formalStartHash, runs, pairIdentity,
      operationCounts: {
        metaRunnerProcesses: 1, preferredCompileAliasInvocations: 4, productionWrapperProcesses: 4, restrictedCompileDirectChildren: 4,
        nativeCompileInvocations: 4, compileReceiptBlenderIdentityProbes: 4, preferredVerifierAliasInvocations: 4,
        currentReceiptVerifierProcesses: 4, verifierBlenderIdentityProbes: 4, blendArtifactAuditProcesses: 4,
        caseCompilations: 4, blenderRenderCalls: 0, cyclesRayRenders: 0, modelCalls: 0, networkCalls: 0, dockerProcesses: 0,
      },
      scientificVerdict: null,
    }, 'operationDraftHash');

    phase = 'INDEPENDENT_AUDIT';
    const auditPath = resolve(formalRoot, 'audit.json');
    const auditChild = await runChild(process.execPath, [
      resolve(repositoryRoot, 'scripts/audit-b56-e1-production-compiler-entry-promotion.mjs'),
      '--spec', SPEC_URI, '--preflight-root', args.preflightRoot, '--attempt-root', args.attemptRoot,
      '--formal-root', args.outputRoot, '--output', repoUri(auditPath),
    ]);
    if (auditChild.exitCode !== 0 || auditChild.signal !== null) throw new Error(`B56 independent audit process failed: ${auditChild.stderr || auditChild.stdout}`);
    const audit = JSON.parse(await readFile(auditPath, 'utf8'));
    if (!validSelfHash(audit, 'auditHash')) throw new Error('B56 audit self-hash mismatch');
    const allGatesPass = Object.keys(audit.gates ?? {}).length === spec.gates.length && Object.values(audit.gates ?? {}).every(Boolean);
    const verdict = allGatesPass && audit.attackSummary?.rejected >= spec.auditContract.semanticAttacksMinimum
      ? spec.decision.supportedVerdict : spec.decision.rejectedVerdict;
    const results = await writeDurableHashed(resolve(formalRoot, 'results.json'), {
      schemaVersion: 'bfs.productionCompilerEntryPromotionResult.v0.1', experimentId: 'B56-E1', scientificVerdict: verdict,
      preregistrationCommit: PREREGISTRATION_COMMIT, specSha256: SPEC_SHA256,
      preflight: { uri: repoUri(preflightPath), sha256: await sha256File(preflightPath), preflightHash: preflight.preflightHash, evidenceCommit: args.preflightEvidenceCommit },
      metaAuthorization: { attemptHash: attempt.attemptHash, admissionHash: admissionRecord.admissionHash, attemptReceiptHash: attemptReceipt.receiptHash, formalStartHash: formalStart.formalStartHash },
      runs, pairIdentity, gates: audit.gates, attackSummary: audit.attackSummary,
      operationCounts: operationDraft.operationCounts,
      claims: { preferredProductionEntryPromoted: verdict === spec.decision.supportedVerdict, renderedPixels: false, cinematicQuality: false, signed: false, remotelyAttested: false },
    }, 'resultHash');
    const operation = await writeDurableHashed(resolve(formalRoot, 'operation.json'), {
      schemaVersion: 'bfs.productionCompilerEntryPromotionOperation.v0.1', experimentId: 'B56-E1',
      draft: { uri: `${repoUri(formalRoot)}/operation-draft.json`, sha256: await sha256File(resolve(formalRoot, 'operation-draft.json')), operationDraftHash: operationDraft.operationDraftHash },
      auditor: { pid: auditChild.pid, exitCode: auditChild.exitCode, signal: auditChild.signal, stdoutSha256: sha256Bytes(Buffer.from(auditChild.stdout)), stderrSha256: sha256Bytes(Buffer.from(auditChild.stderr)) },
      finalCounts: { ...operationDraft.operationCounts, independentAuditorProcesses: 1 }, scientificVerdict: verdict,
    }, 'operationHash');
    await writeDurableHashed(resolve(formalRoot, 'receipt.json'), {
      schemaVersion: 'bfs.productionCompilerEntryPromotionReceipt.v0.1', experimentId: 'B56-E1', scientificVerdict: verdict,
      results: { uri: `${repoUri(formalRoot)}/results.json`, sha256: await sha256File(resolve(formalRoot, 'results.json')), resultHash: results.resultHash },
      audit: { uri: repoUri(auditPath), sha256: await sha256File(auditPath), auditHash: audit.auditHash },
      operation: { uri: `${repoUri(formalRoot)}/operation.json`, sha256: await sha256File(resolve(formalRoot, 'operation.json')), operationHash: operation.operationHash },
      allEvidenceRetained: true, sameIdRepairAndRerunForbidden: true,
    }, 'receiptHash');
    process.stdout.write(`BFS_B56_E1_FORMAL_${verdict} gates=${Object.values(audit.gates).filter(Boolean).length}/${Object.keys(audit.gates).length} attacks=${audit.attackSummary.rejected}/${audit.attackSummary.total}\n`);
    if (verdict !== spec.decision.supportedVerdict) process.exitCode = 1;
  } catch (error) {
    await writeInvalidation(formalRoot, phase, error, { attemptHash: attempt.attemptHash, admissionHash: admissionRecord.admissionHash });
    process.stderr.write(`BFS_B56_E1_INVALIDATED ${phase} ${error.message}\n`);
    process.exitCode = 1;
  }
}

main().catch(error => {
  process.stderr.write(`${error?.stack ?? error}\n`);
  process.exitCode = 1;
});
