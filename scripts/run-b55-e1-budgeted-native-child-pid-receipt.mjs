#!/opt/homebrew/Cellar/node/26.5.0/bin/node

import { spawn } from 'node:child_process';
import { lstat, mkdir, readFile, writeFile } from 'node:fs/promises';
import { relative, resolve, sep } from 'node:path';
import {
  AdmissionError,
  admitFormalRun,
  canonicalHash,
  sha256Bytes,
  sha256File,
  sortValue,
} from './lib/formal-run-admission.mjs';
import { compileBuildPlan } from './compile-build-plan.mjs';
import { canonicalJson, repositoryRoot } from './lib/scene-spec.mjs';

const SPEC_SHA256 = '8aafaad2afe90ac022e6378700d5013470c08b994515eb9cdd2b245df7a320e7';
const PREREGISTRATION_COMMIT = 'bf62f9a02dbfb966f585a4c0e634da1e3507cd72';
const NODE_EXECUTABLE = '/opt/homebrew/Cellar/node/26.5.0/bin/node';
const RESTRICTED_CLI = 'scripts/run-restricted-blender-compile.mjs';
const AUDITOR = 'scripts/audit-b55-e1-budgeted-native-child-pid-receipt.mjs';

function parseArguments(argv) {
  const parsed = { developmentProbe: false };
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--development-probe') parsed.developmentProbe = true;
    else if (token === '--spec') parsed.spec = argv[++index];
    else if (token === '--preflight-root') parsed.preflightRoot = argv[++index];
    else if (token === '--attempt-root') parsed.attemptRoot = argv[++index];
    else if (token === '--output-root') parsed.outputRoot = argv[++index];
    else if (token === '--preflight-evidence-commit') parsed.preflightEvidenceCommit = argv[++index];
    else throw new Error(`Unknown or incomplete argument: ${token}`);
  }
  return parsed;
}

async function pathState(path) {
  try { return await lstat(path); } catch (error) {
    if (error?.code === 'ENOENT') return null;
    throw error;
  }
}

function repoUri(path) {
  return relative(repositoryRoot, path).split(sep).join('/');
}

async function writeJson(path, value) {
  await writeFile(path, `${JSON.stringify(sortValue(value), null, 2)}\n`, { encoding: 'utf8', flag: 'wx' });
}

async function writeHashed(path, body, field) {
  const record = { ...body, [field]: canonicalHash(body) };
  await writeJson(path, record);
  return record;
}

function validSelfHash(record, field) {
  const body = structuredClone(record);
  delete body[field];
  return typeof record[field] === 'string' && record[field] === canonicalHash(body);
}

async function readHashed(path, field) {
  const record = JSON.parse(await readFile(path, 'utf8'));
  if (!validSelfHash(record, field)) throw new Error(`Self-hash mismatch: ${repoUri(path)}`);
  return { record, sha256: await sha256File(path) };
}

async function assertAcceptedPreflight(preflightRoot, spec) {
  const preflightPath = resolve(preflightRoot, 'preflight.json');
  const receiptPath = resolve(preflightRoot, 'receipt.json');
  const preflightRead = await readHashed(preflightPath, 'preflightHash');
  const receiptRead = await readHashed(receiptPath, 'receiptHash');
  const preflight = preflightRead.record;
  const receipt = receiptRead.record;
  const valid = preflight.schemaVersion === 'bfs.budgetedNativeChildPidReceiptPreflight.v0.1'
    && preflight.experimentId === 'B55-E1'
    && preflight.status === 'ACCEPTED'
    && preflight.specSha256 === SPEC_SHA256
    && preflight.pidProbes?.passed === true
    && Object.values(preflight.checks ?? {}).length > 0
    && Object.values(preflight.checks ?? {}).every(Boolean)
    && receipt.schemaVersion === 'bfs.budgetedNativeChildPidReceiptPreflightReceipt.v0.1'
    && receipt.experimentId === 'B55-E1'
    && receipt.status === 'ACCEPTED'
    && receipt.spec?.sha256 === SPEC_SHA256
    && receipt.preflight?.sha256 === preflightRead.sha256
    && receipt.preflight?.preflightHash === preflight.preflightHash
    && preflight.toolFreezeCommit === receipt.toolFreezeCommit;
  if (!valid) throw new Error('Accepted B55 preflight semantic binding is invalid');
  if (preflight.toolHashes?.[spec.freshness.productionInterventionPath] === spec.intervention.before.sha256) throw new Error('Accepted B55 preflight still binds the uncorrected supervisor');
  return { preflightRead, receiptRead };
}

async function runChild(command, args, role, logRoot, environment = {}) {
  const started = process.hrtime.bigint();
  const child = spawn(command, args, {
    cwd: repositoryRoot,
    env: {
      ...process.env,
      PATH: '/usr/bin:/bin:/opt/homebrew/bin',
      LANG: 'C.UTF-8',
      LC_ALL: 'C.UTF-8',
      BLENDER_BIN: '/Applications/Blender.app/Contents/MacOS/Blender',
      ...environment,
    },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  const stdout = [];
  const stderr = [];
  child.stdout.on('data', chunk => stdout.push(chunk));
  child.stderr.on('data', chunk => stderr.push(chunk));
  const exitCode = await new Promise((resolvePromise, reject) => {
    child.on('error', reject);
    child.on('close', resolvePromise);
  });
  const stdoutBytes = Buffer.concat(stdout);
  const stderrBytes = Buffer.concat(stderr);
  const safeRole = role.toLowerCase().replaceAll(/[^a-z0-9]+/g, '-');
  const stdoutPath = resolve(logRoot, `${safeRole}.stdout.log`);
  const stderrPath = resolve(logRoot, `${safeRole}.stderr.log`);
  await writeFile(stdoutPath, stdoutBytes, { flag: 'wx' });
  await writeFile(stderrPath, stderrBytes, { flag: 'wx' });
  return {
    role,
    command,
    args,
    pid: child.pid,
    exitCode,
    elapsedNanoseconds: Number(process.hrtime.bigint() - started),
    stdout: { uri: repoUri(stdoutPath), sha256: sha256Bytes(stdoutBytes), bytes: stdoutBytes.length },
    stderr: { uri: repoUri(stderrPath), sha256: sha256Bytes(stderrBytes), bytes: stderrBytes.length },
  };
}

async function planPair(spec) {
  const observations = [];
  const plans = new Map();
  for (const benchmark of spec.inputs.benchmarks) {
    const first = await compileBuildPlan(benchmark.sceneSpecUri);
    const second = await compileBuildPlan(benchmark.sceneSpecUri);
    const firstCanonical = canonicalJson(first);
    const secondCanonical = canonicalJson(second);
    observations.push({
      benchmark: benchmark.id,
      sceneSpecUri: benchmark.sceneSpecUri,
      firstPlanHash: first.planHash,
      secondPlanHash: second.planHash,
      firstCanonicalSha256: sha256Bytes(Buffer.from(firstCanonical)),
      secondCanonicalSha256: sha256Bytes(Buffer.from(secondCanonical)),
      canonicalBytesExact: firstCanonical === secondCanonical,
      frozenPlanHashExact: first.planHash === benchmark.expectedPlanHash && second.planHash === benchmark.expectedPlanHash,
    });
    plans.set(benchmark.id, first);
  }
  return { observations, plans };
}

async function runDevelopmentProbe(spec) {
  const pair = await planPair(spec);
  const rootStates = await Promise.all([spec.freshness.preflightRoot, spec.freshness.attemptRoot, spec.freshness.formalRoot]
    .map(uri => pathState(resolve(repositoryRoot, uri))));
  const rootsAbsent = rootStates.every(state => state === null);
  const passed = pair.observations.length === 2
    && pair.observations.every(row => row.canonicalBytesExact && row.frozenPlanHashExact)
    && rootsAbsent;
  process.stdout.write(`${JSON.stringify({
    status: passed ? 'PASS' : 'FAIL',
    formalRootsCreated: false,
    observations: pair.observations,
    blenderProcesses: 0,
    renderCalls: 0,
  })}\n`);
  if (!passed) process.exitCode = 1;
}

async function writeAdmissionFailure(attemptRoot, attemptRead, error, gitChildren) {
  const failurePath = resolve(attemptRoot, 'failure.json');
  const failure = await writeHashed(failurePath, {
    schemaVersion: 'bfs.budgetedNativeChildPidReceiptAdmissionFailure.v0.1',
    experimentId: 'B55-E1',
    sequence: 2,
    status: 'REJECTED',
    reason: error instanceof AdmissionError ? error.reason : 'ADMISSION_EXCEPTION',
    message: error?.message ?? String(error),
    attempt: { uri: `${repoUri(attemptRoot)}/attempt.json`, sha256: attemptRead.sha256, attemptHash: attemptRead.record.attemptHash },
    gitChildren,
    formalRootMaterialized: false,
    compilerProcessesStarted: 0,
    scientificVerdict: null,
  }, 'failureHash');
  const failureSha256 = await sha256File(failurePath);
  await writeHashed(resolve(attemptRoot, 'receipt.json'), {
    schemaVersion: 'bfs.budgetedNativeChildPidReceiptAttemptReceipt.v0.1',
    experimentId: 'B55-E1',
    sequence: 3,
    status: 'REJECTED',
    scientificVerdict: null,
    attempt: { uri: `${repoUri(attemptRoot)}/attempt.json`, sha256: attemptRead.sha256, attemptHash: attemptRead.record.attemptHash },
    failure: { uri: `${repoUri(attemptRoot)}/failure.json`, sha256: failureSha256, failureHash: failure.failureHash },
    formalRootMaterialized: false,
    sameIdRepairAndRerunForbidden: true,
  }, 'receiptHash');
}

async function writeInvalidation(root, phase, error, context = {}) {
  const path = resolve(root, 'invalidation.json');
  if (await pathState(path)) return;
  await writeHashed(path, {
    schemaVersion: 'bfs.budgetedNativeChildPidReceiptInvalidation.v0.1',
    experimentId: 'B55-E1',
    status: 'INVALIDATED',
    phase,
    error: { name: error?.name ?? 'Error', message: error?.message ?? String(error), stack: error?.stack ?? null },
    context,
    scientificVerdict: null,
    partialEvidenceRetained: true,
    sameIdRepairAndRerunForbidden: true,
  }, 'invalidationHash');
}

async function main() {
  const args = parseArguments(process.argv.slice(2));
  const specPath = resolve(repositoryRoot, args.spec ?? 'specs/budgeted-native-child-pid-receipt-correction.v0.1.json');
  if (await sha256File(specPath) !== SPEC_SHA256) throw new Error('B55-E1 spec SHA-256 mismatch');
  const spec = JSON.parse(await readFile(specPath, 'utf8'));
  if (spec.experimentId !== 'B55-E1') throw new Error('B55-E1 experiment identity mismatch');
  if (args.developmentProbe) {
    await runDevelopmentProbe(spec);
    return;
  }
  for (const required of ['preflightRoot', 'attemptRoot', 'outputRoot', 'preflightEvidenceCommit']) {
    if (!args[required]) throw new Error(`Official runner missing --${required.replace(/[A-Z]/g, letter => `-${letter.toLowerCase()}`)}`);
  }
  if (args.preflightRoot !== spec.freshness.preflightRoot
    || args.attemptRoot !== spec.freshness.attemptRoot
    || args.outputRoot !== spec.freshness.formalRoot) {
    throw new Error('Official runner requires the frozen repository-relative root spellings');
  }
  const preflightRoot = resolve(repositoryRoot, args.preflightRoot);
  const attemptRoot = resolve(repositoryRoot, args.attemptRoot);
  const formalRoot = resolve(repositoryRoot, args.outputRoot);
  if (!await pathState(preflightRoot)) throw new Error('Accepted preflight root is missing');
  if (await pathState(attemptRoot) || await pathState(formalRoot)) throw new Error('B55-E1 attempt/formal root already exists; runner is single-use');

  await mkdir(attemptRoot, { recursive: false });
  const attemptPath = resolve(attemptRoot, 'attempt.json');
  const attempt = await writeHashed(attemptPath, {
    schemaVersion: 'bfs.budgetedNativeChildPidReceiptAttempt.v0.1',
    experimentId: 'B55-E1',
    sequence: 1,
    invocation: {
      spec: args.spec ?? 'specs/budgeted-native-child-pid-receipt-correction.v0.1.json',
      preflightRoot: args.preflightRoot,
      attemptRoot: args.attemptRoot,
      outputRoot: args.outputRoot,
      preflightEvidenceCommit: args.preflightEvidenceCommit,
    },
    runnerPid: process.pid,
    preregistrationCommit: PREREGISTRATION_COMMIT,
    specSha256: SPEC_SHA256,
    formalRootAbsentBeforeAdmission: !await pathState(formalRoot),
    blenderProcessesAuthorized: 0,
    scientificVerdict: null,
  }, 'attemptHash');
  const attemptRead = { record: attempt, sha256: await sha256File(attemptPath) };
  const admissionGitChildren = [];
  let admission;
  try {
    await assertAcceptedPreflight(preflightRoot, spec);
    admission = await admitFormalRun({
      repositoryRoot,
      evidenceInput: args.preflightRoot,
      formalOutput: args.outputRoot,
      originRef: spec.runtime.git.originRef,
      gitObserver: row => admissionGitChildren.push(row),
    });
    if (admission.evidence.evidenceCommit !== args.preflightEvidenceCommit) throw new AdmissionError('EVIDENCE_COMMIT_MISMATCH', 'Admission evidence commit differs from frozen CLI binding');
  } catch (error) {
    await writeAdmissionFailure(attemptRoot, attemptRead, error, admissionGitChildren);
    process.stdout.write(`BFS_B55_E1_FORMAL_ADMISSION_REJECTED reason=${error.reason ?? 'ADMISSION_EXCEPTION'} blender=0\n`);
    process.exitCode = 1;
    return;
  }

  const admissionPath = resolve(attemptRoot, 'admission.json');
  const admissionRecord = await writeHashed(admissionPath, {
    schemaVersion: 'bfs.budgetedNativeChildPidReceiptAdmission.v0.1',
    experimentId: 'B55-E1',
    sequence: 2,
    status: admission.status,
    invocation: { evidenceInput: args.preflightRoot, formalOutput: args.outputRoot, originRef: spec.runtime.git.originRef },
    evidence: admission.evidence,
    output: {
      repositoryRelative: admission.output.repositoryRelative,
      parentRepositoryRelative: admission.output.parentRepositoryRelative,
      fresh: admission.output.fresh,
    },
    attempt: { uri: `${repoUri(attemptRoot)}/attempt.json`, sha256: attemptRead.sha256, attemptHash: attempt.attemptHash },
    gitChildren: admissionGitChildren,
    compilerProcessesStarted: 0,
    scientificVerdict: null,
  }, 'admissionHash');
  const admissionSha256 = await sha256File(admissionPath);
  const attemptReceiptPath = resolve(attemptRoot, 'receipt.json');
  const attemptReceipt = await writeHashed(attemptReceiptPath, {
    schemaVersion: 'bfs.budgetedNativeChildPidReceiptAttemptReceipt.v0.1',
    experimentId: 'B55-E1',
    sequence: 3,
    status: 'ACCEPTED',
    scientificVerdict: null,
    attempt: { uri: `${repoUri(attemptRoot)}/attempt.json`, sha256: attemptRead.sha256, attemptHash: attempt.attemptHash },
    admission: { uri: `${repoUri(attemptRoot)}/admission.json`, sha256: admissionSha256, admissionHash: admissionRecord.admissionHash },
    formalOutput: admissionRecord.output,
    formalRootMaterializationAuthorized: true,
    sameIdRepairAndRerunForbiddenOnFailure: true,
  }, 'receiptHash');
  const attemptReceiptSha256 = await sha256File(attemptReceiptPath);

  let phase = 'FORMAL_ROOT_MATERIALIZATION';
  try {
    await mkdir(formalRoot, { recursive: false });
    const formalStartPath = resolve(formalRoot, 'formal-start.json');
    const formalStart = await writeHashed(formalStartPath, {
      schemaVersion: 'bfs.budgetedNativeChildPidReceiptFormalStart.v0.1',
      experimentId: 'B55-E1',
      sequence: 4,
      runnerPid: process.pid,
      spec: { uri: repoUri(specPath), sha256: SPEC_SHA256 },
      authorization: {
        attemptReceipt: { uri: `${repoUri(attemptRoot)}/receipt.json`, sha256: attemptReceiptSha256, receiptHash: attemptReceipt.receiptHash },
        admissionIdentityHash: admission.evidence.identityHash,
        formalRoot: args.outputRoot,
      },
      prohibitedOperationCountsAtStart: { blenderProcesses: 0, renderCalls: 0, dockerProcesses: 0, modelCalls: 0, networkCalls: 0 },
      scientificVerdict: null,
    }, 'startHash');

    phase = 'BUILDPLAN_PAIR';
    const plansRoot = resolve(formalRoot, 'plans');
    const runsRoot = resolve(formalRoot, 'runs');
    const logsRoot = resolve(formalRoot, 'process-logs');
    await mkdir(plansRoot);
    await mkdir(runsRoot);
    await mkdir(logsRoot);
    const pair = await planPair(spec);
    if (!pair.observations.every(row => row.canonicalBytesExact && row.frozenPlanHashExact)) throw new Error('Formal BuildPlan pair regression');
    const planBindings = [];
    for (const benchmark of spec.inputs.benchmarks) {
      const planPath = resolve(plansRoot, `${benchmark.id}.build-plan.json`);
      await writeJson(planPath, pair.plans.get(benchmark.id));
      planBindings.push({ benchmark: benchmark.id, uri: repoUri(planPath), sha256: await sha256File(planPath), planHash: pair.plans.get(benchmark.id).planHash });
    }
    const planObservationPath = resolve(formalRoot, 'plan-observations.json');
    const planObservation = await writeHashed(planObservationPath, {
      schemaVersion: 'bfs.budgetedNativeChildPidReceiptPlanObservations.v0.1',
      experimentId: 'B55-E1',
      sequence: 5,
      observations: pair.observations,
      plans: planBindings,
      formalStart: { uri: repoUri(formalStartPath), sha256: await sha256File(formalStartPath), startHash: formalStart.startHash },
      scientificVerdict: null,
    }, 'observationHash');

    phase = 'RESTRICTED_NATIVE_COMPILES';
    const restrictedChildren = [];
    const runBindings = [];
    for (const benchmark of spec.inputs.benchmarks) {
      for (const suffix of ['A', 'B']) {
        const runId = `${benchmark.id}-${suffix}`;
        const runRoot = resolve(runsRoot, runId);
        const runUri = repoUri(runRoot);
        const planUri = planBindings.find(row => row.benchmark === benchmark.id).uri;
        const freshOutputBeforeStart = await pathState(runRoot) === null;
        if (!freshOutputBeforeStart) throw new Error(`Restricted compiler output is not fresh: ${runId}`);
        const child = await runChild(NODE_EXECUTABLE, [
          RESTRICTED_CLI,
          '--plan', planUri,
          '--output-dir', runUri,
          '--report', `${runUri}/budget.report.json`,
          '--receipt', `${runUri}/compile.receipt.json`,
        ], `RESTRICTED_COMPILE_${runId}`, logsRoot);
        restrictedChildren.push(child);
        if (child.exitCode !== 0) throw new Error(`Restricted compiler child failed: ${runId}`);
        const budgetPath = resolve(runRoot, 'budget.report.json');
        const receiptPath = resolve(runRoot, 'compile.receipt.json');
        const budget = JSON.parse(await readFile(budgetPath, 'utf8'));
        const receipt = JSON.parse(await readFile(receiptPath, 'utf8'));
        if (budget.outcome !== 'PASS') throw new Error(`Budget result did not pass: ${runId}`);
        runBindings.push({
          runId,
          benchmark: benchmark.id,
          outputUri: runUri,
          freshOutputBeforeStart,
          planHash: receipt.executionIdentity?.buildPlan?.planHash ?? null,
          structureHash: receipt.run?.sceneManifest?.structureHash ?? null,
          budget: {
            uri: `${runUri}/budget.report.json`,
            sha256: await sha256File(budgetPath),
            documentType: budget.documentType,
            version: budget.version,
            outcome: budget.outcome,
            nativeCommand: budget.command,
            nativeChildPid: budget.child?.pid ?? null,
            nativeExitCode: budget.child?.exitCode ?? null,
            nativeSignal: budget.child?.signal ?? null,
            nativeSpawnError: budget.child?.spawnError ?? null,
            terminationRequested: budget.termination?.requested ?? null,
            restrictedWrapperPid: child.pid,
          },
          receipt: { uri: `${runUri}/compile.receipt.json`, sha256: await sha256File(receiptPath), receiptHash: receipt.receiptHash },
        });
      }
    }

    phase = 'INDEPENDENT_AUDIT';
    const operationDraftPath = resolve(formalRoot, 'operation-draft.json');
    const nativePidBindingsAvailable = runBindings.every(row => row.budget.documentType === 'BFS_BUDGETED_PROCESS_RESULT'
      && row.budget.version === '0.2.0'
      && row.budget.outcome === 'PASS'
      && row.budget.nativeCommand === spec.runtime.blender.executable
      && Number.isSafeInteger(row.budget.nativeChildPid)
      && row.budget.nativeChildPid > 0
      && row.budget.nativeChildPid !== row.budget.restrictedWrapperPid
      && row.budget.nativeExitCode === 0
      && row.budget.nativeSignal === null
      && row.budget.nativeSpawnError === null
      && row.budget.terminationRequested === false);
    const operationDraft = await writeHashed(operationDraftPath, {
      schemaVersion: 'bfs.budgetedNativeChildPidReceiptOperationDraft.v0.1',
      experimentId: 'B55-E1',
      sequence: 6,
      runnerPid: process.pid,
      runnerProcesses: 1,
      restrictedCompileDirectChildren: restrictedChildren.length,
      restrictedCompileChildren: restrictedChildren,
      nativeCompileInvocations: runBindings.length,
      nativeCompilePidBindingsAvailable: nativePidBindingsAvailable,
      compileReceiptBlenderIdentityProbes: runBindings.length,
      independentAuditorProcessesPlanned: 1,
      receiptVerifierDirectChildrenPlanned: 4,
      verifierBlenderIdentityProbesPlanned: 4,
      blendArtifactAuditDirectChildrenPlanned: 4,
      blenderRenderCalls: 0,
      cyclesRayRenders: 0,
      dockerProcesses: 0,
      modelCalls: 0,
      networkCalls: 0,
      runBindings,
      admission: { uri: `${repoUri(attemptRoot)}/admission.json`, sha256: admissionSha256, admissionHash: admissionRecord.admissionHash },
      planObservations: { uri: repoUri(planObservationPath), sha256: await sha256File(planObservationPath), observationHash: planObservation.observationHash },
      scientificVerdict: null,
    }, 'operationHash');
    const auditPath = resolve(formalRoot, 'audit.json');
    const auditorChild = await runChild(NODE_EXECUTABLE, [
      AUDITOR,
      '--spec', repoUri(specPath),
      '--preflight-root', args.preflightRoot,
      '--attempt-root', args.attemptRoot,
      '--formal-root', args.outputRoot,
      '--operation-draft', repoUri(operationDraftPath),
      '--output', repoUri(auditPath),
    ], 'INDEPENDENT_AUDITOR', logsRoot);
    if (auditorChild.exitCode !== 0) throw new Error('Independent auditor process failed');
    const auditRead = await readHashed(auditPath, 'auditHash');

    phase = 'FINALIZATION';
    const operationPath = resolve(formalRoot, 'operation.json');
    const operation = await writeHashed(operationPath, {
      schemaVersion: 'bfs.budgetedNativeChildPidReceiptOperation.v0.1',
      experimentId: 'B55-E1',
      sequence: 7,
      draft: { uri: repoUri(operationDraftPath), sha256: await sha256File(operationDraftPath), operationHash: operationDraft.operationHash },
      runnerPid: process.pid,
      restrictedCompileChildren: restrictedChildren,
      independentAuditorChild: auditorChild,
      directChildCount: restrictedChildren.length + 1,
      semanticOperationCounts: {
        nativeCompileInvocations: runBindings.length,
        compileReceiptBlenderIdentityProbes: runBindings.length,
        receiptVerifierInvocations: auditRead.record.operationCounts.receiptVerifierDirectChildren,
        verifierBlenderIdentityProbes: auditRead.record.operationCounts.verifierBlenderIdentityProbes,
        blendArtifactAudits: auditRead.record.operationCounts.blendArtifactAuditDirectChildren,
      },
      nativeCompilePidBindingsAvailable: nativePidBindingsAvailable,
      prohibitedOperationCounts: { blenderRenderCalls: 0, cyclesRayRenders: 0, dockerProcesses: 0, modelCalls: 0, networkCalls: 0 },
      scientificVerdict: null,
    }, 'operationHash');
    const operationSha256 = await sha256File(operationPath);
    const allGatesPass = auditRead.record.gateNamesExact === true
      && auditRead.record.gatePassed === spec.gates.length
      && spec.gates.every(gate => auditRead.record.gates?.[gate] === true);
    const scientificVerdict = allGatesPass ? spec.decision.supportedVerdict : spec.decision.rejectedVerdict;
    if (scientificVerdict !== auditRead.record.expectedScientificVerdict) throw new Error('Outcome-neutral verdict mapping mismatch');
    const resultsPath = resolve(formalRoot, 'results.json');
    const results = await writeHashed(resultsPath, {
      schemaVersion: 'bfs.budgetedNativeChildPidReceiptIntegrationResult.v0.1',
      experimentId: 'B55-E1',
      sequence: 8,
      status: 'COMPLETE',
      scientificVerdict,
      gates: auditRead.record.gates,
      gatePassed: auditRead.record.gatePassed,
      gateTotal: auditRead.record.gateTotal,
      semanticAttacks: { passed: auditRead.record.semanticAttacksPassed, total: auditRead.record.semanticAttackCount },
      planIdentities: pair.observations,
      runBindings,
      processEvidence: {
        nativeCompilePidBindingsAvailable: nativePidBindingsAvailable,
        supervisorSchema: nativePidBindingsAvailable ? 'BFS_BUDGETED_PROCESS_RESULT@0.2.0' : null,
        childAuthoredPreflightCorroboration: nativePidBindingsAvailable,
        limitation: 'Supervisor-local spawn receipt only; not cryptographic or remote process attestation, and PID values may be recycled after exit.',
      },
      audit: { uri: repoUri(auditPath), sha256: auditRead.sha256, auditHash: auditRead.record.auditHash },
      operation: { uri: repoUri(operationPath), sha256: operationSha256, operationHash: operation.operationHash },
      nonClaims: spec.nonClaims,
    }, 'resultHash');
    const receipt = await writeHashed(resolve(formalRoot, 'receipt.json'), {
      schemaVersion: 'bfs.budgetedNativeChildPidReceiptIntegrationReceipt.v0.1',
      experimentId: 'B55-E1',
      sequence: 9,
      status: 'COMPLETE',
      scientificVerdict,
      result: { uri: repoUri(resultsPath), sha256: await sha256File(resultsPath), resultHash: results.resultHash },
      audit: { uri: repoUri(auditPath), sha256: auditRead.sha256, auditHash: auditRead.record.auditHash },
      operation: { uri: repoUri(operationPath), sha256: operationSha256, operationHash: operation.operationHash },
      attemptReceipt: { uri: `${repoUri(attemptRoot)}/receipt.json`, sha256: attemptReceiptSha256, receiptHash: attemptReceipt.receiptHash },
      sameIdClosed: true,
    }, 'receiptHash');
    process.stdout.write(`BFS_B55_E1_FORMAL_COMPLETE verdict=${scientificVerdict} gates=${results.gatePassed}/${results.gateTotal} attacks=${results.semanticAttacks.passed}/${results.semanticAttacks.total} receipt=${receipt.receiptHash}\n`);
  } catch (error) {
    await writeInvalidation(formalRoot, phase, error, {
      attemptReceipt: { uri: `${repoUri(attemptRoot)}/receipt.json`, sha256: attemptReceiptSha256, receiptHash: attemptReceipt.receiptHash },
    });
    throw error;
  }
}

main().catch(error => {
  process.stderr.write(`${error?.stack ?? error}\n`);
  process.exitCode = 1;
});
