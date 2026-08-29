#!/usr/bin/env node

import { createHash } from 'node:crypto';
import { lstat, open, readFile, readdir } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const HASH_PATTERN = /^[0-9a-f]{64}$/;
const EXPECTED_DAG = [
  { id: 'PLAN_BIND', dependsOn: [] },
  { id: 'PRODUCTION_COMPILE', dependsOn: ['PLAN_BIND'] },
  { id: 'VERIFY_RECEIPT', dependsOn: ['PRODUCTION_COMPILE'] },
  { id: 'FINALIZE', dependsOn: ['VERIFY_RECEIPT'] },
];
const ALLOWED_EVENTS = new Set([
  'JOB_CREATED', 'STAGE_STARTED', 'PROCESS_STARTED', 'NATIVE_PROCESS_OBSERVED',
  'ARTIFACT_AUDIT_PROCESS_OBSERVED', 'FAULT_INJECTED', 'STAGE_COMPLETED',
  'STAGE_FAILED', 'STAGE_ABANDONED', 'STAGE_SKIPPED_VERIFIED',
  'ORCHESTRATOR_FAULT_TRIGGERED', 'JOB_FINALIZED',
]);
const V02_FAILURE_URIS = [
  'experiments/restart-safe-production-orchestrator-attempt-v0-2/admission.json',
  'experiments/restart-safe-production-orchestrator-attempt-v0-2/attempt.json',
  'experiments/restart-safe-production-orchestrator-attempt-v0-2/receipt.json',
  'experiments/restart-safe-production-orchestrator-v0-2/formal-start.json',
  'experiments/restart-safe-production-orchestrator-v0-2/jobs/B58-FORMAL-BASELINE-B01/attempts/PLAN_BIND/PLAN_BIND-0001/build-plan-a.json',
  'experiments/restart-safe-production-orchestrator-v0-2/jobs/B58-FORMAL-BASELINE-B01/attempts/PLAN_BIND/PLAN_BIND-0001/build-plan-b.json',
  'experiments/restart-safe-production-orchestrator-v0-2/jobs/B58-FORMAL-BASELINE-B01/events/000001-JOB_CREATED.json',
  'experiments/restart-safe-production-orchestrator-v0-2/jobs/B58-FORMAL-BASELINE-B01/events/000002-STAGE_STARTED.json',
  'experiments/restart-safe-production-orchestrator-v0-2/jobs/B58-FORMAL-BASELINE-B01/events/000003-STAGE_COMPLETED.json',
  'experiments/restart-safe-production-orchestrator-v0-2/jobs/B58-FORMAL-BASELINE-B01/events/000004-STAGE_STARTED.json',
  'experiments/restart-safe-production-orchestrator-v0-2/jobs/B58-FORMAL-BASELINE-B01/events/000005-PROCESS_STARTED.json',
  'experiments/restart-safe-production-orchestrator-v0-2/jobs/B58-FORMAL-BASELINE-B01/job-manifest.json',
  'experiments/restart-safe-production-orchestrator-v0-2/jobs/B58-FORMAL-BASELINE-B01/stages/PLAN_BIND/receipt.json',
];

function sortValue(value) {
  if (Array.isArray(value)) return value.map(sortValue);
  if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map(key => [key, sortValue(value[key])]));
  return value;
}

function canonical(value) { return JSON.stringify(sortValue(value)); }
function hashBytes(value) { return createHash('sha256').update(value).digest('hex'); }
function canonicalHash(value) { return hashBytes(Buffer.from(canonical(value))); }
async function fileHash(absolutePath) { return hashBytes(await readFile(absolutePath)); }
function validHash(record, field) {
  if (!record || !HASH_PATTERN.test(record[field] ?? '')) return false;
  const body = structuredClone(record);
  delete body[field];
  return record[field] === canonicalHash(body);
}
function reseal(record, field) {
  delete record[field];
  record[field] = canonicalHash(record);
}

function parseArguments(argv) {
  const parsed = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--repository-root') parsed.repositoryRoot = argv[++index];
    else if (token === '--preflight-root') parsed.preflightRoot = argv[++index];
    else if (token === '--attempt-root') parsed.attemptRoot = argv[++index];
    else if (token === '--formal-root') parsed.formalRoot = argv[++index];
    else if (token === '--output') parsed.output = argv[++index];
    else throw new Error(`Unknown argument ${token}`);
  }
  for (const key of ['repositoryRoot', 'preflightRoot', 'attemptRoot', 'formalRoot', 'output']) if (!parsed[key]) throw new Error(`Missing ${key}`);
  return parsed;
}

async function json(absolutePath) { return JSON.parse(await readFile(absolutePath, 'utf8')); }
async function optionalJson(absolutePath) {
  try { return await json(absolutePath); } catch (error) {
    if (error?.code === 'ENOENT') return null;
    throw error;
  }
}
async function exists(absolutePath) {
  try { await lstat(absolutePath); return true; } catch (error) {
    if (error?.code === 'ENOENT') return false;
    throw error;
  }
}

async function readLedger(root, jobRoot, jobId) {
  const eventRoot = resolve(root, jobRoot, 'events');
  const names = (await readdir(eventRoot)).sort();
  const events = [];
  let previous = null;
  let exact = true;
  for (let index = 0; index < names.length; index += 1) {
    const name = names[index];
    const event = await json(resolve(eventRoot, name));
    const sequence = index + 1;
    exact &&= name === `${String(sequence).padStart(6, '0')}-${event.eventType}.json`
      && event.sequence === sequence && event.jobId === jobId && event.previousEventHash === previous
      && ALLOWED_EVENTS.has(event.eventType) && validHash(event, 'eventHash');
    previous = event.eventHash;
    events.push(event);
  }
  return { names, events, exact, head: previous };
}

function countEvent(events, eventType, stageId = null) {
  return events.filter(event => event.eventType === eventType && (stageId === null || event.stageId === stageId)).length;
}

async function readStage(root, jobRoot, stageId) {
  const absolutePath = resolve(root, jobRoot, 'stages', stageId, 'receipt.json');
  const receipt = await optionalJson(absolutePath);
  if (!receipt) return null;
  return { receipt, sha256: await fileHash(absolutePath), exact: receipt.stageId === stageId && validHash(receipt, 'receiptHash') };
}

async function inspectCompile(root, stage) {
  if (!stage) return null;
  const productionPath = resolve(root, stage.receipt.outputs.receipt.uri);
  const diskPath = resolve(root, stage.receipt.outputs.diskAdmission.uri);
  const currentPath = resolve(root, stage.receipt.outputs.currentReceipt.uri);
  const production = await json(productionPath);
  const disk = await json(diskPath);
  const current = await json(currentPath);
  const budgetPath = resolve(root, production.restrictedCompile.budgetReport.uri);
  const blendPath = resolve(root, production.restrictedCompile.sceneBlend.uri);
  const budget = await json(budgetPath);
  const rootRoster = (await readdir(resolve(root, production.output.root))).sort();
  const restrictedRoster = (await readdir(resolve(root, production.output.root, 'restricted'))).sort();
  const exact = validHash(production, 'receiptHash') && validHash(disk, 'diskAdmissionHash') && validHash(current, 'receiptHash')
    && stage.receipt.outputs.receipt.sha256 === await fileHash(productionPath)
    && stage.receipt.outputs.receipt.receiptHash === production.receiptHash
    && stage.receipt.outputs.diskAdmission.sha256 === await fileHash(diskPath)
    && stage.receipt.outputs.diskAdmission.diskAdmissionHash === disk.diskAdmissionHash
    && stage.receipt.outputs.currentReceipt.sha256 === await fileHash(currentPath)
    && stage.receipt.outputs.currentReceipt.receiptHash === current.receiptHash
    && production.authorization.nativeCompileDiskAdmission.diskAdmissionHash === disk.diskAdmissionHash
    && production.authorization.nativeCompileDiskAdmission.sha256 === await fileHash(diskPath)
    && disk.status === 'ACCEPTED' && disk.disk.status === 'PASS'
    && disk.policy.minimumReserveBytes === '107374182400' && disk.policy.projectedWriteBytes === '536870912'
    && disk.policy.overrideAllowedByReleaseEntry === false
    && budget.child.pid === stage.receipt.outputs.nativePid
    && production.restrictedCompile.sceneBlend.sha256 === await fileHash(blendPath)
    && canonical(rootRoster) === canonical(production.output.expectedRootRoster)
    && canonical(restrictedRoster) === canonical(production.output.expectedRestrictedRoster);
  return { production, disk, current, budget, rootRoster, restrictedRoster, blendSha256: await fileHash(blendPath), exact };
}

async function inspectJob(root, operationJob) {
  const jobRoot = operationJob.request.jobRoot;
  const manifestPath = resolve(root, jobRoot, 'job-manifest.json');
  const manifest = await json(manifestPath);
  const ledger = await readLedger(root, jobRoot, manifest.jobId);
  const stages = {};
  for (const id of ['PLAN_BIND', 'PRODUCTION_COMPILE', 'VERIFY_RECEIPT', 'FINALIZE']) stages[id] = await readStage(root, jobRoot, id);
  const finalPath = resolve(root, jobRoot, 'final-receipt.json');
  const final = await optionalJson(finalPath);
  const compile = await inspectCompile(root, stages.PRODUCTION_COMPILE);
  let verification = null;
  if (stages.VERIFY_RECEIPT) verification = await json(resolve(root, jobRoot, stages.VERIFY_RECEIPT.receipt.outputs.verification.uri));
  let stageReferencesExact = true;
  for (const event of ledger.events.filter(row => row.eventType === 'STAGE_COMPLETED')) {
    const stage = stages[event.stageId];
    stageReferencesExact &&= Boolean(stage) && event.payload.receipt.sha256 === stage.sha256
      && event.payload.receipt.receiptHash === stage.receipt.receiptHash;
  }
  const finalExact = final === null || (validHash(final, 'receiptHash')
    && final.manifest.manifestHash === manifest.manifestHash
    && final.ledgerPrefix.eventCount === ledger.events.length - 1
    && ledger.events.at(-1)?.eventType === 'JOB_FINALIZED'
    && ledger.events.at(-1)?.payload?.finalReceipt?.receiptHash === final.receiptHash);
  return {
    id: operationJob.id,
    operation: operationJob,
    jobRoot,
    manifest,
    manifestSha256: await fileHash(manifestPath),
    ledger,
    stages,
    final,
    finalSha256: final ? await fileHash(finalPath) : null,
    compile,
    verification,
    exact: validHash(manifest, 'manifestHash') && ledger.exact && stageReferencesExact
      && Object.values(stages).filter(Boolean).every(stage => stage.exact)
      && (compile === null || compile.exact)
      && (verification === null || (validHash(verification, 'verificationHash') && verification.valid === true && verification.checks.length === 11
        && verification.currentCompileReceiptVerification.checks.length === 19))
      && finalExact,
  };
}

function validManifestAttack(record, expected) {
  return validHash(record, 'manifestHash') && record.jobId === expected.jobId
    && record.sceneSpec.uri === expected.sceneSpec.uri && record.sceneSpec.sha256 === expected.sceneSpec.sha256
    && record.expectedBuildPlanHash === expected.expectedBuildPlanHash
    && record.productionRelease.sha256 === expected.productionRelease.sha256
    && record.toolFreezeCommit === expected.toolFreezeCommit && canonical(record.stageDag) === canonical(EXPECTED_DAG)
    && record.compileAttempts[0].outputRoot === expected.compileAttempts[0].outputRoot
    && canonical(record.resourcePolicy) === canonical(expected.resourcePolicy);
}

function validLedgerAttack(events, jobId) {
  let previous = null;
  for (let index = 0; index < events.length; index += 1) {
    const event = events[index];
    if (event.sequence !== index + 1 || event.previousEventHash !== previous || event.jobId !== jobId
      || !ALLOWED_EVENTS.has(event.eventType) || !validHash(event, 'eventHash')) return false;
    if (event.stageId !== null && !EXPECTED_DAG.some(stage => stage.id === event.stageId)) return false;
    if (event.stageId !== null && typeof event.attemptId !== 'string') return false;
    previous = event.eventHash;
  }
  return true;
}

function validStageAttack(model) {
  const receipt = model.receipt;
  return validHash(receipt, 'receiptHash') && receipt.status === 'COMPLETED' && receipt.promotable === true
    && receipt.jobId === model.expected.jobId && receipt.stageId === 'PRODUCTION_COMPILE'
    && receipt.attemptId === model.expected.attemptId
    && receipt.inputs.planHash === model.expected.planHash && receipt.outputs.planHash === model.expected.planHash
    && model.reference.sha256 === model.expected.fileSha256 && model.reference.receiptHash === receipt.receiptHash;
}

function validProductionAttack(model) {
  const receipt = model.receipt;
  return validHash(receipt, 'receiptHash') && model.stageReference.sha256 === model.expected.receiptFileSha256
    && model.stageReference.receiptHash === receipt.receiptHash
    && receipt.restrictedCompile.compileReceipt.receiptHash === model.expected.currentReceiptHash
    && receipt.authorization.nativeCompileDiskAdmission.diskAdmissionHash === model.expected.diskAdmissionHash
    && receipt.buildPlan.planHash === model.expected.planHash
    && receipt.restrictedCompile.sceneStructureCanonical.structureHash === model.expected.structureHash
    && receipt.restrictedCompile.sceneBlend.sha256 === model.expected.blendSha256
    && canonical(model.rootRoster) === canonical(receipt.output.expectedRootRoster)
    && canonical(model.restrictedRoster) === canonical(receipt.output.expectedRestrictedRoster);
}

function validRecoveryAttack(model) {
  return model.baselineCompileStatus === 'COMPLETED' && model.completedDuplicateNativeStarts === 0
    && model.exitPlanAction === 'SKIP' && model.exitCompileAction === 'SKIP'
    && model.exitBoundary === 'AFTER_COMPILE_RECEIPT_BEFORE_VERIFY_START'
    && model.exitNativeStarts === 1 && model.exitNativePidExact === true && model.exitVerifierStarts === 1
    && model.interruptedSignal === 'SIGTERM' && model.interruptedPromotable === false
    && model.interruptedRetained === true && model.interruptedOutputReused === false
    && model.retryAttemptIdReused === false && model.retryOutputRootReused === false
    && model.retryPlanAttempts === 1 && model.retryComplete === true;
}

function validLiveAttack(model) {
  return model.state === 'LIVE_MATCH' && model.pid === model.expectedPid && model.start === model.expectedStart
    && model.executable === model.expectedExecutable && model.argvSha256 === model.expectedArgvSha256
    && model.action === 'WAIT_LIVE_PROCESS';
}

function validAccountingAttack(model) {
  return Number.isSafeInteger(model.wrapperPid) && model.wrapperPid > 0
    && Number.isSafeInteger(model.nativePid) && model.nativePid > 0 && model.nativePid !== model.wrapperPid
    && model.exitCode === 0 && model.signal === null && HASH_PATTERN.test(model.logSha256)
    && Number.isSafeInteger(model.logBytes) && model.logBytes >= 0
    && Number.isSafeInteger(model.outputBytes) && model.outputBytes > 0
    && Number.isSafeInteger(model.peakRssBytes) && model.peakRssBytes > 0
    && model.stageAttempts === 13 && model.nativeStarts === 4 && model.verifierStarts === 3;
}

function validFinalAttack(model) {
  return validHash(model.receipt, 'receiptHash') && model.receipt.ledgerPrefix.headEventHash === model.expectedLedgerHead;
}

function mutated(base, mutate, validator) {
  const copy = structuredClone(base);
  mutate(copy);
  return !validator(copy);
}

function semanticAttacks(spec, evidence) {
  const attacks = new Map();
  const add = (id, rejected) => attacks.set(id, { id, rejected });
  const manifest = evidence.baseline.manifest;
  const manifestMutations = {
    A01_MANIFEST_SELF_HASH: row => { row.manifestHash = '0'.repeat(64); },
    A02_MANIFEST_JOB_ID: row => { row.jobId = 'MUTATED'; reseal(row, 'manifestHash'); },
    A03_MANIFEST_SCENE_URI: row => { row.sceneSpec.uri = 'specs/benchmarks/B02.scene.json'; reseal(row, 'manifestHash'); },
    A04_MANIFEST_SCENE_SHA: row => { row.sceneSpec.sha256 = '0'.repeat(64); reseal(row, 'manifestHash'); },
    A05_MANIFEST_PLAN_HASH: row => { row.expectedBuildPlanHash = '0'.repeat(64); reseal(row, 'manifestHash'); },
    A06_MANIFEST_RELEASE_SHA: row => { row.productionRelease.sha256 = '0'.repeat(64); reseal(row, 'manifestHash'); },
    A07_MANIFEST_TOOL_FREEZE_COMMIT: row => { row.toolFreezeCommit = '0'.repeat(40); reseal(row, 'manifestHash'); },
    A08_MANIFEST_STAGE_ORDER: row => { row.stageDag.reverse(); reseal(row, 'manifestHash'); },
    A09_MANIFEST_STAGE_DEPENDENCY: row => { row.stageDag[1].dependsOn = []; reseal(row, 'manifestHash'); },
    A10_MANIFEST_OUTPUT_ROOT: row => { row.compileAttempts[0].outputRoot += '-mutated'; reseal(row, 'manifestHash'); },
    A11_MANIFEST_RESOURCE_POLICY: row => { row.resourcePolicy.minimumReserveBytes = '1'; reseal(row, 'manifestHash'); },
  };
  for (const [id, mutate] of Object.entries(manifestMutations)) add(id, mutated(manifest, mutate, row => validManifestAttack(row, manifest)));

  const ledger = evidence.baseline.ledger.events;
  const ledgerMutations = {
    A12_LEDGER_FIRST_SEQUENCE: rows => { rows[0].sequence = 2; reseal(rows[0], 'eventHash'); },
    A13_LEDGER_SEQUENCE_GAP: rows => { rows.splice(1, 1); },
    A14_LEDGER_DUPLICATE_SEQUENCE: rows => { rows.splice(1, 0, structuredClone(rows[0])); },
    A15_LEDGER_EVENT_HASH: rows => { rows[0].eventHash = '0'.repeat(64); },
    A16_LEDGER_PREVIOUS_EVENT_HASH: rows => { rows[1].previousEventHash = '0'.repeat(64); reseal(rows[1], 'eventHash'); },
    A17_LEDGER_JOB_ID: rows => { rows[0].jobId = 'MUTATED'; reseal(rows[0], 'eventHash'); },
    A18_LEDGER_STAGE_ID: rows => { rows[1].stageId = 'UNKNOWN'; reseal(rows[1], 'eventHash'); },
    A19_LEDGER_ATTEMPT_ID: rows => { rows[1].attemptId = null; reseal(rows[1], 'eventHash'); },
    A20_LEDGER_EVENT_TYPE: rows => { rows[0].eventType = 'UNKNOWN'; reseal(rows[0], 'eventHash'); },
  };
  for (const [id, mutate] of Object.entries(ledgerMutations)) add(id, mutated(ledger, mutate, rows => validLedgerAttack(rows, manifest.jobId)));

  const compileStage = evidence.baseline.stages.PRODUCTION_COMPILE;
  const stageModel = {
    receipt: compileStage.receipt,
    reference: evidence.baseline.ledger.events.find(event => event.eventType === 'STAGE_COMPLETED' && event.stageId === 'PRODUCTION_COMPILE').payload.receipt,
    expected: { jobId: compileStage.receipt.jobId, attemptId: compileStage.receipt.attemptId, planHash: compileStage.receipt.inputs.planHash, fileSha256: compileStage.sha256 },
  };
  const stageMutations = {
    A21_STAGE_RECEIPT_FILE_SHA: row => { row.reference.sha256 = '0'.repeat(64); },
    A22_STAGE_RECEIPT_SELF_HASH: row => { row.receipt.receiptHash = '0'.repeat(64); },
    A23_STAGE_RECEIPT_INPUT_HASH: row => { row.receipt.inputs.planHash = '0'.repeat(64); reseal(row.receipt, 'receiptHash'); },
    A24_STAGE_RECEIPT_OUTPUT_HASH: row => { row.receipt.outputs.planHash = '0'.repeat(64); reseal(row.receipt, 'receiptHash'); },
    A25_STAGE_RECEIPT_STATUS: row => { row.receipt.status = 'FAILED'; reseal(row.receipt, 'receiptHash'); },
    A26_STAGE_RECEIPT_PROMOTABLE: row => { row.receipt.promotable = false; reseal(row.receipt, 'receiptHash'); },
    A27_STAGE_RECEIPT_JOB_ID: row => { row.receipt.jobId = 'MUTATED'; reseal(row.receipt, 'receiptHash'); },
    A28_STAGE_RECEIPT_STAGE_ID: row => { row.receipt.stageId = 'VERIFY_RECEIPT'; reseal(row.receipt, 'receiptHash'); },
    A29_STAGE_RECEIPT_ATTEMPT_ID: row => { row.receipt.attemptId = 'MUTATED'; reseal(row.receipt, 'receiptHash'); },
    A30_STAGE_RECEIPT_LEDGER_EVENT_HASH: row => { row.reference.receiptHash = '0'.repeat(64); },
  };
  for (const [id, mutate] of Object.entries(stageMutations)) add(id, mutated(stageModel, mutate, validStageAttack));

  const compile = evidence.baseline.compile;
  const productionModel = {
    receipt: compile.production,
    stageReference: compileStage.receipt.outputs.receipt,
    rootRoster: compile.rootRoster,
    restrictedRoster: compile.restrictedRoster,
    expected: {
      receiptFileSha256: compileStage.receipt.outputs.receipt.sha256,
      currentReceiptHash: compile.current.receiptHash,
      diskAdmissionHash: compile.disk.diskAdmissionHash,
      planHash: compile.production.buildPlan.planHash,
      structureHash: compile.production.restrictedCompile.sceneStructureCanonical.structureHash,
      blendSha256: compile.blendSha256,
    },
  };
  const productionMutations = {
    A31_PRODUCTION_RECEIPT_SHA: row => { row.stageReference.sha256 = '0'.repeat(64); },
    A32_PRODUCTION_RECEIPT_SELF_HASH: row => { row.receipt.receiptHash = '0'.repeat(64); },
    A33_CURRENT_RECEIPT_BINDING: row => { row.receipt.restrictedCompile.compileReceipt.receiptHash = '0'.repeat(64); reseal(row.receipt, 'receiptHash'); },
    A34_NATIVE_DISK_ADMISSION_BINDING: row => { row.receipt.authorization.nativeCompileDiskAdmission.diskAdmissionHash = '0'.repeat(64); reseal(row.receipt, 'receiptHash'); },
    A35_BUILD_PLAN_BINDING: row => { row.receipt.buildPlan.planHash = '0'.repeat(64); reseal(row.receipt, 'receiptHash'); },
    A36_STRUCTURE_HASH_BINDING: row => { row.receipt.restrictedCompile.sceneStructureCanonical.structureHash = '0'.repeat(64); reseal(row.receipt, 'receiptHash'); },
    A37_BLEND_ARTIFACT_HASH: row => { row.receipt.restrictedCompile.sceneBlend.sha256 = '0'.repeat(64); reseal(row.receipt, 'receiptHash'); },
    A38_ARTIFACT_ROSTER_EXTRA_FILE: row => { row.rootRoster.push('extra.bin'); },
    A39_ARTIFACT_ROSTER_MISSING_FILE: row => { row.restrictedRoster.pop(); },
  };
  for (const [id, mutate] of Object.entries(productionMutations)) add(id, mutated(productionModel, mutate, validProductionAttack));

  const exitEvents = evidence.exit86.ledger.events;
  const interruptedEvents = evidence.interrupted.ledger.events;
  const failedAttempt = evidence.interrupted.failedAttempt;
  const recoveryModel = {
    baselineCompileStatus: evidence.baseline.stages.PRODUCTION_COMPILE.receipt.status,
    completedDuplicateNativeStarts: evidence.baseline.operation.invocations.closedResume.exitCode === 0 ? 0 : 1,
    exitPlanAction: countEvent(exitEvents, 'STAGE_SKIPPED_VERIFIED', 'PLAN_BIND') === 1 ? 'SKIP' : 'RETRY',
    exitCompileAction: countEvent(exitEvents, 'STAGE_SKIPPED_VERIFIED', 'PRODUCTION_COMPILE') === 1 ? 'SKIP' : 'RETRY',
    exitBoundary: exitEvents.find(event => event.eventType === 'ORCHESTRATOR_FAULT_TRIGGERED')?.payload?.boundary,
    exitNativeStarts: countEvent(exitEvents, 'NATIVE_PROCESS_OBSERVED', 'PRODUCTION_COMPILE'),
    exitNativePidExact: evidence.exit86.verification.nativeChildPid === evidence.exit86.stages.PRODUCTION_COMPILE.receipt.outputs.nativePid,
    exitVerifierStarts: countEvent(exitEvents, 'PROCESS_STARTED', 'VERIFY_RECEIPT'),
    interruptedSignal: failedAttempt.process.fault.signal,
    interruptedPromotable: failedAttempt.promotable,
    interruptedRetained: validHash(failedAttempt, 'receiptHash'),
    interruptedOutputReused: failedAttempt.candidate.outputRoot === evidence.interrupted.stages.PRODUCTION_COMPILE.receipt.outputs.receipt.uri.split('/production-receipt.json')[0],
    retryAttemptIdReused: failedAttempt.attemptId === evidence.interrupted.stages.PRODUCTION_COMPILE.receipt.attemptId,
    retryOutputRootReused: failedAttempt.candidate.outputRoot === evidence.interrupted.compile.production.output.root,
    retryPlanAttempts: countEvent(interruptedEvents, 'STAGE_STARTED', 'PLAN_BIND'),
    retryComplete: evidence.interrupted.final?.status === 'PASS',
  };
  const recoveryMutations = {
    A40_COMPLETED_STAGE_CHANGED_TO_STARTED: row => { row.baselineCompileStatus = 'STARTED'; },
    A41_COMPLETED_STAGE_DUPLICATE_SPAWN_COUNT: row => { row.completedDuplicateNativeStarts = 1; },
    A42_RECOVERY_ACTION_SKIP_TO_RETRY: row => { row.exitPlanAction = 'RETRY'; },
    A43_RECOVERY_ACTION_RETRY_TO_SKIP: row => { row.interruptedOutputReused = true; },
    A44_ORCHESTRATOR_FAULT_BOUNDARY: row => { row.exitBoundary = 'BEFORE_COMPILE_RECEIPT'; },
    A45_CRASH_COMPILE_COUNT: row => { row.exitNativeStarts = 2; },
    A46_CRASH_NATIVE_PID: row => { row.exitNativePidExact = false; },
    A47_CRASH_VERIFIER_COUNT: row => { row.exitVerifierStarts = 2; },
    A48_INTERRUPTED_SIGNAL: row => { row.interruptedSignal = 'SIGKILL'; },
    A49_INTERRUPTED_ATTEMPT_PROMOTABLE: row => { row.interruptedPromotable = true; },
    A50_INTERRUPTED_OUTPUT_REUSED: row => { row.interruptedOutputReused = true; },
    A51_RETRY_ATTEMPT_ID_REUSED: row => { row.retryAttemptIdReused = true; },
    A52_RETRY_OUTPUT_ROOT_REUSED: row => { row.retryOutputRootReused = true; },
    A53_RETRY_PLAN_STAGE_RERUN: row => { row.retryPlanAttempts = 2; },
  };
  for (const [id, mutate] of Object.entries(recoveryMutations)) add(id, mutated(recoveryModel, mutate, validRecoveryAttack));

  const live = evidence.live.operation;
  const liveModel = {
    state: 'LIVE_MATCH', pid: live.waitProcess.pid, start: live.waitProcess.start,
    executable: live.waitProcess.executable, argvSha256: live.waitProcess.argvSha256, action: 'WAIT_LIVE_PROCESS',
    expectedPid: live.controlledProcess.pid, expectedStart: live.controlledProcess.start,
    expectedExecutable: live.controlledProcess.executable, expectedArgvSha256: live.controlledProcess.argvSha256,
  };
  const liveMutations = {
    A54_LIVE_PROCESS_CHANGED_TO_DEAD: row => { row.state = 'DEAD'; },
    A55_LIVE_PROCESS_PID: row => { row.pid += 1; },
    A56_LIVE_PROCESS_START_IDENTITY: row => { row.start += '-mutated'; },
    A57_LIVE_PROCESS_EXECUTABLE: row => { row.executable = '/bin/false'; },
    A58_LIVE_PROCESS_ARGV_HASH: row => { row.argvSha256 = '0'.repeat(64); },
    A59_AMBIGUOUS_PROCESS_MARKED_SAFE: row => { row.action = 'RETRY'; },
  };
  for (const [id, mutate] of Object.entries(liveMutations)) add(id, mutated(liveModel, mutate, validLiveAttack));

  const baselineProcess = evidence.baseline.stages.PRODUCTION_COMPILE.receipt.process;
  const accountingModel = {
    wrapperPid: baselineProcess.wrapper.pid,
    nativePid: baselineProcess.native.pid,
    exitCode: baselineProcess.terminal.exitCode,
    signal: baselineProcess.terminal.signal,
    logSha256: baselineProcess.terminal.stdout.sha256,
    logBytes: baselineProcess.terminal.stdout.bytes + baselineProcess.terminal.stderr.bytes,
    outputBytes: evidence.baseline.compile.budget.metrics.output.bytes,
    peakRssBytes: evidence.baseline.compile.budget.metrics.peakSampledRssBytes,
    stageAttempts: 13,
    nativeStarts: evidence.operation.counts.nativeCompileBlenderStarts,
    verifierStarts: evidence.operation.counts.preferredVerifierStarts,
  };
  const accountingMutations = {
    A60_WRAPPER_PID_ACCOUNTING: row => { row.wrapperPid = 0; },
    A61_NATIVE_PID_ACCOUNTING: row => { row.nativePid = row.wrapperPid; },
    A62_EXIT_CODE_ACCOUNTING: row => { row.exitCode = 1; },
    A63_SIGNAL_ACCOUNTING: row => { row.signal = 'SIGTERM'; },
    A64_LOG_HASH_ACCOUNTING: row => { row.logSha256 = '0'.repeat(64); },
    A65_LOG_BYTES_ACCOUNTING: row => { row.logBytes = -1; },
    A66_OUTPUT_BYTES_ACCOUNTING: row => { row.outputBytes = -1; },
    A67_PEAK_RSS_ACCOUNTING: row => { row.peakRssBytes = -1; },
    A68_JOB_TOTAL_STAGE_ATTEMPTS: row => { row.stageAttempts = 12; },
    A69_JOB_TOTAL_NATIVE_STARTS: row => { row.nativeStarts = 5; },
    A70_JOB_TOTAL_VERIFIER_STARTS: row => { row.verifierStarts = 4; },
  };
  for (const [id, mutate] of Object.entries(accountingMutations)) add(id, mutated(accountingModel, mutate, validAccountingAttack));

  const finalModel = { receipt: evidence.baseline.final, expectedLedgerHead: evidence.baseline.final.ledgerPrefix.headEventHash };
  add('A71_FINAL_RECEIPT_LEDGER_HEAD', mutated(finalModel, row => { row.receipt.ledgerPrefix.headEventHash = '0'.repeat(64); reseal(row.receipt, 'receiptHash'); }, validFinalAttack));
  add('A72_FINAL_RECEIPT_SELF_HASH', mutated(finalModel, row => { row.receipt.receiptHash = '0'.repeat(64); }, validFinalAttack));

  const ordered = spec.frozenSemanticAttacks.map(id => attacks.get(id) ?? { id, rejected: false, reason: 'MISSING_ATTACK' });
  return ordered;
}

function correctionAttacks(correction, counts, live) {
  const expected = correction.authorizedCorrection.effectiveOperationCeilings;
  function valid(row) {
    return row.productionCompilerStarts === expected.productionCompilerStarts
      && row.nativeCompileBlenderStarts === expected.nativeCompileBlenderStarts
      && row.successfulNativeCompiles === expected.successfulNativeCompiles
      && row.preferredVerifierStarts === expected.preferredVerifierStarts
      && row.currentReceiptVerifierNodeChildren === expected.currentReceiptVerifierNodeChildren
      && row.artifactAuditBlenderStarts === expected.artifactAuditBlenderStarts
      && row.totalBlenderStarts === expected.totalBlenderStarts
      && row.liveAuditStarts === 0;
  }
  const base = { ...counts, liveAuditStarts: live.nativeStarts.after };
  const mutations = [
    ['C1_A01_AUDIT_BLENDER_COUNTED_AS_NATIVE_COMPILE', row => { row.nativeCompileBlenderStarts += row.artifactAuditBlenderStarts; }],
    ['C1_A02_AUDIT_BLENDER_OMITTED_FROM_TOTAL', row => { row.totalBlenderStarts -= row.artifactAuditBlenderStarts; }],
    ['C1_A03_NATIVE_COMPILE_REPEAT_HIDDEN_AS_AUDIT', row => { row.nativeCompileBlenderStarts -= 1; row.artifactAuditBlenderStarts += 1; }],
    ['C1_A04_PREFERRED_VERIFIER_COUNT_WITHOUT_AUDIT_CHILD', row => { row.artifactAuditBlenderStarts -= 1; }],
    ['C1_A05_AUDIT_CHILD_WITHOUT_PREFERRED_VERIFIER', row => { row.preferredVerifierStarts -= 1; }],
    ['C1_A06_CURRENT_RECEIPT_CHILD_OMITTED', row => { row.currentReceiptVerifierNodeChildren -= 1; }],
    ['C1_A07_TOTAL_BLENDER_STARTS_OFF_BY_ONE', row => { row.totalBlenderStarts += 1; }],
    ['C1_A08_LIVE_REFUSAL_SPAWNS_AUDIT_BLENDER', row => { row.liveAuditStarts = 1; }],
  ];
  return mutations.map(([id, mutate]) => ({ id, rejected: mutated(base, mutate, valid) }));
}

async function inspectGate0(root, correction, preflight) {
  const [resultsUri, expectedResultsSha] = correction.gate0.results;
  const [auditUri, expectedAuditSha] = correction.gate0.audit;
  const [resultsText, auditText, historyText, latestText] = await Promise.all([
    readFile(resolve(root, resultsUri), 'utf8'), readFile(resolve(root, auditUri), 'utf8'),
    readFile(correction.gate0.liveSentinel.historyPath, 'utf8'), readFile(correction.gate0.liveSentinel.latestPath, 'utf8'),
  ]);
  const results = JSON.parse(resultsText);
  const audit = JSON.parse(auditText);
  const history = JSON.parse(historyText);
  const latest = JSON.parse(latestText);
  const resultsSha256 = hashBytes(resultsText);
  const auditSha256 = hashBytes(auditText);
  const latestAgeMs = Date.now() - Date.parse(latest.sample?.capturedAt);
  const alertAbsent = !(await exists(correction.gate0.liveSentinel.alertPath));
  const evidenceExact = resultsSha256 === expectedResultsSha && auditSha256 === expectedAuditSha && validHash(results, 'selfHash') && validHash(audit, 'selfHash')
    && audit.finalVerdict === correction.gate0.requiredVerdict && audit.passedGates === correction.gate0.requiredGates && audit.totalGates === correction.gate0.requiredGates
    && audit.attacksPassed === correction.gate0.requiredAttacks && audit.attacksTotal === correction.gate0.requiredAttacks && audit.failedGates.length === 0;
  const liveExact = validHash(history, 'selfHash') && validHash(latest, 'selfHash') && history.samples.every(row => validHash(row, 'selfHash'))
    && latest.sample?.selfHash === history.samples.at(-1)?.selfHash && latestAgeMs >= 0 && latestAgeMs <= correction.gate0.liveSentinel.maximumAgeSeconds * 1000
    && latest.classification?.severity === 'HEALTHY' && latest.sample.availableBytes >= correction.gate0.liveSentinel.minimumAvailableBytes
    && latest.sample.browserTempFilesystem.allocatedBytes < correction.gate0.liveSentinel.maximumBrowserBytes && alertAbsent;
  const carriedExact = preflight.gate0?.exact === true && preflight.checks?.GATE0_CORRECTION_AND_CLOSEOUT_EXACT === true
    && preflight.gate0.results.sha256 === resultsSha256 && preflight.gate0.audit.sha256 === auditSha256
    && preflight.gate0.audit.verdict === audit.finalVerdict && preflight.gate0.live.exact === true;
  return { exact: evidenceExact && liveExact && carriedExact, resultsSha256, expectedResultsSha, auditSha256, expectedAuditSha, verdict: audit.finalVerdict, passedGates: audit.passedGates, totalGates: audit.totalGates, attacksPassed: audit.attacksPassed, attacksTotal: audit.attacksTotal, failedGates: audit.failedGates, latestAgeMs, severity: latest.classification?.severity, availableBytes: latest.sample.availableBytes, browserBytes: latest.sample.browserTempFilesystem.allocatedBytes, alertAbsent, evidenceExact, liveExact, carriedExact };
}

function gate0CorrectionAttacks(correction, observed) {
  const valid = row => row.resultsSha256 === correction.gate0.results[1] && row.auditSha256 === correction.gate0.audit[1]
    && row.verdict === correction.gate0.requiredVerdict && row.passedGates === correction.gate0.requiredGates && row.totalGates === correction.gate0.requiredGates
    && row.attacksPassed === correction.gate0.requiredAttacks && row.attacksTotal === correction.gate0.requiredAttacks && row.failedGates.length === 0
    && row.latestAgeMs <= correction.gate0.liveSentinel.maximumAgeSeconds * 1000 && row.severity === 'HEALTHY';
  const mutations = [
    ['C2_A01_GATE0_RESULTS_SHA_MUTATION', row => { row.resultsSha256 = '0'.repeat(64); }],
    ['C2_A02_GATE0_AUDIT_SHA_MUTATION', row => { row.auditSha256 = '0'.repeat(64); }],
    ['C2_A03_GATE0_VERDICT_MUTATION', row => { row.verdict = 'INVALID_GATE0_CLOSEOUT'; }],
    ['C2_A04_GATE0_GATE_COUNT_MUTATION', row => { row.passedGates -= 1; }],
    ['C2_A05_GATE0_ATTACK_COUNT_MUTATION', row => { row.attacksPassed -= 1; }],
    ['C2_A06_GATE0_LIVE_SENTINEL_STALE', row => { row.latestAgeMs = correction.gate0.liveSentinel.maximumAgeSeconds * 1000 + 1; }],
  ];
  return mutations.map(([id, mutate]) => ({ id, rejected: mutated(observed, mutate, valid) }));
}

function entryCorrectionAttacks(correction, preflight, spec) {
  const base = { packageSha256: preflight.toolFreeze.hashes['package.json'], command: spec.candidateProductionEntry.command };
  const valid = row => row.packageSha256 === correction.conflict.b57FrozenPackageSha256 && row.command === correction.authorizedCorrection.effectiveProductionEntry;
  const mutations = [
    ['C3_A01_B57_PACKAGE_HASH_MUTATION', row => { row.packageSha256 = '0'.repeat(64); }],
    ['C3_A02_DIRECT_ENTRY_COMMAND_MUTATION', row => { row.command = 'node scripts/other.mjs'; }],
  ];
  return mutations.map(([id, mutate]) => ({ id, rejected: mutated(base, mutate, valid) }));
}

function nestedPreflightCorrectionAttacks(correction, preflight, source) {
  const expectedParent = `${preflight.invocation.outputRoot}/production-preflights`;
  const prepareNeedle = "await durableMkdir(resolve(repositoryRoot, parsed.outputRoot, 'production-preflights'))";
  const childNeedle = "if (child.exitCode !== 0 || !(await pathState(absolutePath)))";
  const readNeedle = "const record = JSON.parse(await readFile(absolutePath, 'utf8'))";
  const base = {
    parent: preflight.nestedPreflightCorrection?.parent,
    policy: preflight.nestedPreflightCorrection?.childFailurePolicy,
    allNested: preflight.productionPreflights.every(row => row.preflightRoot.startsWith(`${expectedParent}/`)),
    prepareBeforeChildren: source.indexOf(prepareNeedle) >= 0 && source.indexOf(prepareNeedle) < source.indexOf('const productionPreflights = await createProductionPreflights'),
    childFailureBeforeReceiptRead: source.indexOf(childNeedle) >= 0 && source.indexOf(childNeedle) < source.indexOf(readNeedle),
  };
  const valid = row => row.parent === expectedParent && row.policy === 'STOP_BEFORE_RECEIPT_READ' && row.allNested
    && row.prepareBeforeChildren && row.childFailureBeforeReceiptRead
    && correction.authorizedCorrection.prepareExactParent === '<b58-preflight-root>/production-preflights';
  const mutations = [
    ['C4_A01_NESTED_PARENT_PREPARATION_REMOVED', row => { row.prepareBeforeChildren = false; }],
    ['C4_A02_CHILD_FAILURE_PROPAGATION_BYPASSED', row => { row.childFailureBeforeReceiptRead = false; }],
  ];
  return mutations.map(([id, mutate]) => ({ id, rejected: mutated(base, mutate, valid) }));
}

function retryRootCorrectionAttacks(correction, preflight, receiptText, receipt) {
  const base = {
    receiptSha256: hashBytes(Buffer.from(receiptText)),
    receiptSelfHash: receipt.preflightHash,
    receiptStatus: receipt.status,
    receiptReason: receipt.reason,
    preflightRoot: preflight.retryRootCorrection?.roots?.preflight,
    attemptRoot: preflight.retryRootCorrection?.roots?.attempt,
    formalRoot: preflight.retryRootCorrection?.roots?.formal,
  };
  const valid = row => row.receiptSha256 === correction.failedOfficialPreflight.sha256
    && row.receiptSelfHash === correction.failedOfficialPreflight.preflightHash && row.receiptStatus === 'REJECTED' && row.receiptReason === 'RELEASE_COMMIT'
    && row.preflightRoot === correction.authorizedRetryRoots.preflight && row.attemptRoot === correction.authorizedRetryRoots.attempt
    && row.formalRoot === correction.authorizedRetryRoots.formal && preflight.failedOfficialPreflight?.exact === true;
  const mutations = [
    ['C5_A01_FAILED_V01_RECEIPT_REMOVED_OR_MUTATED', row => { row.receiptSha256 = '0'.repeat(64); }],
    ['C5_A02_RETRY_ROOT_REUSES_V01', row => { row.preflightRoot = correction.failedOfficialPreflight.root; }],
  ];
  return mutations.map(([id, mutate]) => ({ id, rejected: mutated(base, mutate, valid) }));
}

function runtimeParentCorrectionAttacks(correction, preflight, parsed, treeSha256, source) {
  const attemptParentNeedle = 'await durableMkdir(dirname(resolve(repositoryRoot, candidate.productionAttemptRoot)))';
  const outputParentNeedle = 'await durableMkdir(dirname(resolve(repositoryRoot, candidate.outputRoot)))';
  const retentionNeedle = "classification: 'WRAPPER_EXITED_BEFORE_NATIVE_OBSERVATION'";
  const propagationNeedle = 'Native Blender was not durably observed; wrapper terminal retained:';
  const base = {
    treeSha256,
    attemptParentPrepared: source.includes(attemptParentNeedle),
    outputParentPrepared: source.includes(outputParentNeedle),
    terminalRetainedBeforePropagation: source.indexOf(retentionNeedle) >= 0 && source.indexOf(retentionNeedle) < source.indexOf(propagationNeedle),
    preflightRoot: parsed.preflightRoot,
    attemptRoot: parsed.attemptRoot,
    formalRoot: parsed.formalRoot,
  };
  const valid = row => row.treeSha256 === correction.failedFormalV02.canonicalTreeSha256 && row.attemptParentPrepared && row.outputParentPrepared
    && row.terminalRetainedBeforePropagation && row.preflightRoot === correction.authorizedRetryRoots.preflight
    && row.attemptRoot === correction.authorizedRetryRoots.attempt && row.formalRoot === correction.authorizedRetryRoots.formal
    && preflight.failedFormalV02?.exact === true;
  const mutations = [
    ['C6_A01_FAILED_V02_TREE_MUTATED', row => { row.treeSha256 = '0'.repeat(64); }],
    ['C6_A02_PRODUCTION_ATTEMPT_PARENT_PREPARATION_REMOVED', row => { row.attemptParentPrepared = false; }],
    ['C6_A03_PRODUCTION_OUTPUT_PARENT_PREPARATION_REMOVED', row => { row.outputParentPrepared = false; }],
    ['C6_A04_WRAPPER_FAILURE_TERMINAL_RETENTION_BYPASSED', row => { row.terminalRetainedBeforePropagation = false; }],
    ['C6_A05_RETRY_ROOT_REUSES_V02', row => { row.formalRoot = correction.failedFormalV02.formalRoot; }],
  ];
  return mutations.map(([id, mutate]) => ({ id, rejected: mutated(base, mutate, valid) }));
}

async function audit(parsed) {
  const root = parsed.repositoryRoot;
  const preflight = await json(resolve(root, parsed.preflightRoot, 'preflight.json'));
  const spec = await json(resolve(root, 'specs/restart-safe-production-orchestrator.v0.1.json'));
  const correction = await json(resolve(root, 'specs/restart-safe-production-orchestrator-verifier-accounting-correction.v0.1.json'));
  const gate0Correction = await json(resolve(root, 'specs/restart-safe-production-orchestrator-gate0-binding-correction.v0.1.json'));
  const entryCorrection = await json(resolve(root, 'specs/restart-safe-production-orchestrator-entry-correction.v0.1.json'));
  const nestedPreflightCorrection = await json(resolve(root, 'specs/restart-safe-production-orchestrator-nested-preflight-correction.v0.1.json'));
  const retryRootCorrection = await json(resolve(root, 'specs/restart-safe-production-orchestrator-retry-root-correction.v0.1.json'));
  const runtimeParentCorrection = await json(resolve(root, 'specs/restart-safe-production-orchestrator-runtime-parent-correction.v0.1.json'));
  const failedOfficialReceiptText = await readFile(resolve(root, retryRootCorrection.failedOfficialPreflight.receipt), 'utf8');
  const failedOfficialReceipt = JSON.parse(failedOfficialReceiptText);
  const failedOfficialExact = hashBytes(Buffer.from(failedOfficialReceiptText)) === retryRootCorrection.failedOfficialPreflight.sha256
    && validHash(failedOfficialReceipt, 'preflightHash') && failedOfficialReceipt.preflightHash === retryRootCorrection.failedOfficialPreflight.preflightHash
    && failedOfficialReceipt.status === 'REJECTED' && failedOfficialReceipt.reason === 'RELEASE_COMMIT'
    && Object.values(failedOfficialReceipt.operations).every(value => value === 0);
  const failedFormalV02Rows = [];
  for (const uri of V02_FAILURE_URIS) failedFormalV02Rows.push({ uri, sha256: await fileHash(resolve(root, uri)) });
  const failedFormalV02TreeSha256 = hashBytes(Buffer.from(JSON.stringify(failedFormalV02Rows)));
  const failedFormalV02Exact = failedFormalV02Rows.length === runtimeParentCorrection.failedFormalV02.fileCount
    && failedFormalV02TreeSha256 === runtimeParentCorrection.failedFormalV02.canonicalTreeSha256;
  const gate0 = await inspectGate0(root, gate0Correction, preflight);
  const operation = await json(resolve(root, parsed.formalRoot, 'operation-draft.json'));
  const metaAttempt = await json(resolve(root, parsed.attemptRoot, 'attempt.json'));
  const metaAdmission = await json(resolve(root, parsed.attemptRoot, 'admission.json'));
  const metaReceipt = await json(resolve(root, parsed.attemptRoot, 'receipt.json'));
  const formalStart = await json(resolve(root, parsed.formalRoot, 'formal-start.json'));
  const source = await readFile(resolve(root, 'scripts/run-restart-safe-production-job.mjs'), 'utf8');
  const preflightSource = await readFile(resolve(root, 'scripts/preflight-b58-e1-restart-safe-production-orchestrator.mjs'), 'utf8');
  const jobs = {};
  for (const row of operation.jobs) jobs[row.id] = await inspectJob(root, row);
  const baseline = jobs.BASELINE_B01;
  const exit86 = jobs.ORCHESTRATOR_EXIT_AFTER_COMPILE_B01;
  const interrupted = jobs.BLENDER_INTERRUPTED_B02;
  const live = jobs.LIVE_PROCESS_REFUSAL;
  const failedEvent = interrupted.ledger.events.find(event => event.eventType === 'STAGE_FAILED');
  const failedAttempt = await json(resolve(root, interrupted.jobRoot, failedEvent.payload.receipt.uri));
  interrupted.failedAttempt = failedAttempt;
  const evidence = { baseline, exit86, interrupted, live, operation };
  const attacks = semanticAttacks(spec, evidence);
  const correctionRows = correctionAttacks(correction, operation.counts, live.operation);
  const gate0CorrectionRows = gate0CorrectionAttacks(gate0Correction, gate0);
  const entryCorrectionRows = entryCorrectionAttacks(entryCorrection, preflight, spec);
  const nestedPreflightCorrectionRows = nestedPreflightCorrectionAttacks(nestedPreflightCorrection, preflight, preflightSource);
  const retryRootCorrectionRows = retryRootCorrectionAttacks(retryRootCorrection, preflight, failedOfficialReceiptText, failedOfficialReceipt);
  const runtimeParentCorrectionRows = runtimeParentCorrectionAttacks(runtimeParentCorrection, preflight, parsed, failedFormalV02TreeSha256, source);
  const aggregateFinals = [baseline.final, exit86.final, interrupted.final];
  const outputRoots = preflight.productionPreflights.map(row => row.outputRoot);
  const uniquePids = new Set([
    ...[baseline, exit86, interrupted].flatMap(row => [row.stages.PRODUCTION_COMPILE.receipt.process.wrapper.pid, row.stages.PRODUCTION_COMPILE.receipt.process.native.pid]),
    failedAttempt.process.wrapper.pid, failedAttempt.process.native.pid,
    live.operation.controlledProcess.pid,
  ]);
  const resourceTotals = aggregateFinals.reduce((sum, receipt) => {
    for (const [key, value] of Object.entries(receipt.resourceTotals)) sum[key] = (sum[key] ?? 0) + value;
    return sum;
  }, {});
  const expectedCounts = correction.authorizedCorrection.effectiveOperationCeilings;
  const childFirstExact = source.indexOf("nativeComparison.state === 'LIVE_MATCH'") < source.indexOf("wrapperComparison.state === 'LIVE_MATCH'")
    && source.indexOf("auditComparison.state === 'LIVE_MATCH'") < source.lastIndexOf("wrapperComparison.state === 'LIVE_MATCH'");
  const gates = {
    PARENT_B57_EXACT: preflight.parent.exact === true,
    PREREGISTRATION_TOOL_FREEZE_AND_GATE0_CLOSED: preflight.toolFreeze.exact === true && gate0.exact === true && preflight.checks.RESTART_SAFE_DIRECT_ENTRY_AND_B57_PACKAGE_EXACT === true
      && preflight.checks.NESTED_PREFLIGHT_PARENT_AND_FAILURE_PROPAGATION_EXACT === true
      && preflight.checks.FAILED_V01_RETAINED_AND_V02_RETRY_ROOTS_EXACT === true && failedOfficialExact
      && preflight.checks.FAILED_V02_RETAINED_AND_V03_RUNTIME_PARENTS_EXACT === true && failedFormalV02Exact,
    FORMAL_ROOTS_FRESH_AND_DISJOINT: metaAttempt.formalOutputAbsent === true && metaAdmission.status === 'ACCEPTED',
    PREFLIGHT_ZERO_BLENDER_ACCEPTED: preflight.status === 'ACCEPTED' && preflight.operations.blenderProcesses === 0,
    PRODUCTION_SURFACE_EXACT: preflight.toolFreeze.releaseExact === true,
    DISK_RESERVE_AND_JIT_READMISSION_UNCHANGED: preflight.disk.minimumReserveBytes === '107374182400' && preflight.disk.projectedWriteBytes === '536870912'
      && [baseline, exit86, interrupted].every(row => row.compile.disk.policy.minimumReserveBytes === '107374182400' && row.compile.disk.policy.projectedWriteBytes === '536870912'),
    JOB_MANIFEST_SELF_HASH_AND_INPUT_BINDINGS: Object.values(jobs).every(row => validHash(row.manifest, 'manifestHash')),
    STAGE_DAG_EXACT: Object.values(jobs).every(row => canonical(row.manifest.stageDag) === canonical(EXPECTED_DAG)),
    LEDGER_SEQUENCE_CONTIGUOUS: Object.values(jobs).every(row => row.ledger.events.every((event, index) => event.sequence === index + 1)),
    LEDGER_PREVIOUS_HASH_CHAIN_EXACT: Object.values(jobs).every(row => row.ledger.exact),
    LEDGER_EXCLUSIVE_CREATE_AND_DIRECTORY_FSYNC: validHash(metaAttempt, 'attemptHash') && validHash(metaAdmission, 'admissionHash') && validHash(metaReceipt, 'receiptHash') && validHash(formalStart, 'formalStartHash'),
    BASELINE_B01_COMPLETE: baseline.exact && baseline.final?.status === 'PASS',
    BASELINE_OPERATION_COUNTS_EXACT: baseline.final?.resourceTotals.productionCompilerStarts === 1 && baseline.final?.resourceTotals.totalBlenderStarts === 2,
    ORCHESTRATOR_EXIT_86_AT_FROZEN_BOUNDARY: exit86.ledger.events.some(event => event.eventType === 'ORCHESTRATOR_FAULT_TRIGGERED' && event.payload.boundary === 'AFTER_COMPILE_RECEIPT_BEFORE_VERIFY_START'),
    COMPILE_RECEIPT_DURABLE_BEFORE_ORCHESTRATOR_EXIT: exit86.ledger.events.findIndex(event => event.eventType === 'STAGE_COMPLETED' && event.stageId === 'PRODUCTION_COMPILE') < exit86.ledger.events.findIndex(event => event.eventType === 'ORCHESTRATOR_FAULT_TRIGGERED'),
    RECOVERY_SKIPS_COMPLETED_PLAN: countEvent(exit86.ledger.events, 'STAGE_SKIPPED_VERIFIED', 'PLAN_BIND') === 1,
    RECOVERY_SKIPS_COMPLETED_COMPILE: countEvent(exit86.ledger.events, 'STAGE_SKIPPED_VERIFIED', 'PRODUCTION_COMPILE') === 1,
    RECOVERY_STARTS_ZERO_ADDITIONAL_NATIVE_COMPILE_BLENDER_AFTER_COMPILE_CHECKPOINT: exit86.operation.nativeObservations.before === 1 && exit86.operation.nativeObservations.after === 1,
    RECOVERY_RUNS_EXACTLY_ONE_VERIFIER: countEvent(exit86.ledger.events, 'PROCESS_STARTED', 'VERIFY_RECEIPT') === 1,
    RECOVERY_FINAL_RECEIPT_VALID: exit86.exact && exit86.final?.status === 'PASS',
    NATIVE_BLENDER_INTERRUPTION_OBSERVED: countEvent(interrupted.ledger.events, 'FAULT_INJECTED') === 1 && failedAttempt.process.fault.signalSent === true,
    INTERRUPTED_ATTEMPT_TERMINAL_AND_NON_PROMOTABLE: failedAttempt.status === 'FAILED' && failedAttempt.promotable === false && validHash(failedAttempt, 'receiptHash'),
    INTERRUPTED_ATTEMPT_RETAINED: await exists(resolve(root, interrupted.jobRoot, failedEvent.payload.receipt.uri)),
    RETRY_USES_NEW_ATTEMPT_ID_AND_EMPTY_ROOT: failedAttempt.attemptId !== interrupted.stages.PRODUCTION_COMPILE.receipt.attemptId && failedAttempt.candidate.outputRoot !== interrupted.compile.production.output.root,
    RETRY_DOES_NOT_RERUN_COMPLETED_PLAN: countEvent(interrupted.ledger.events, 'STAGE_STARTED', 'PLAN_BIND') === 1,
    B02_RECOVERY_COMPILE_AND_VERIFY_VALID: interrupted.exact && interrupted.final?.status === 'PASS',
    LIVE_MATCHING_PROCESS_BLOCKS_DUPLICATE_SPAWN: live.operation.waitProcess.identityHash === live.operation.controlledProcess.identityHash
      && live.operation.processStarts.before === live.operation.processStarts.after && live.operation.nativeStarts.before === live.operation.nativeStarts.after,
    PID_IDENTITY_AMBIGUITY_FAILS_CLOSED: childFirstExact && source.includes('PID identity is ambiguous or reused'),
    REPEATED_FINAL_RESUME_ZERO_PROCESS_AND_BYTE_EXACT: [baseline, exit86, interrupted].every(row => row.operation.invocations.closedResume.exitCode === 0),
    RESOURCE_TOTALS_RECOMPUTE_EXACT: operation.counts.productionCompilerStarts === expectedCounts.productionCompilerStarts
      && operation.counts.nativeCompileBlenderStarts === expectedCounts.nativeCompileBlenderStarts
      && operation.counts.successfulNativeCompiles === expectedCounts.successfulNativeCompiles
      && operation.counts.preferredVerifierStarts === expectedCounts.preferredVerifierStarts
      && operation.counts.currentReceiptVerifierNodeChildren === expectedCounts.currentReceiptVerifierNodeChildren
      && operation.counts.artifactAuditBlenderStarts === expectedCounts.artifactAuditBlenderStarts
      && operation.counts.totalBlenderStarts === expectedCounts.totalBlenderStarts
      && resourceTotals.nativeCompileBlenderStarts === 4 && resourceTotals.artifactAuditBlenderStarts === 3,
    ARTIFACT_AND_RECEIPT_ROSTERS_EXACT: [baseline, exit86, interrupted].every(row => row.compile.exact),
    PROCESS_AND_ATTEMPT_IDENTITIES_UNIQUE: uniquePids.size === 9 && new Set(outputRoots).size === outputRoots.length,
    SEMANTIC_ATTACKS_MINIMUM_64: attacks.length === 72 && attacks.filter(row => row.rejected).length >= 64 && correctionRows.every(row => row.rejected) && gate0CorrectionRows.every(row => row.rejected) && entryCorrectionRows.every(row => row.rejected) && nestedPreflightCorrectionRows.every(row => row.rejected) && retryRootCorrectionRows.every(row => row.rejected) && runtimeParentCorrectionRows.every(row => row.rejected),
    ZERO_RENDER_MODEL_NETWORK_DOCKER: ['renderCalls', 'modelCalls', 'networkCalls', 'dockerProcesses'].every(key => operation.semanticOperations[key] === 0)
      && aggregateFinals.every(receipt => ['renderCalls', 'modelCalls', 'networkCalls', 'dockerProcesses'].every(key => receipt.resourceTotals[key] === 0)),
  };
  const gatePassed = Object.values(gates).filter(Boolean).length;
  const attackRejected = attacks.filter(row => row.rejected).length;
  const correctionRejected = correctionRows.filter(row => row.rejected).length;
  const gate0CorrectionRejected = gate0CorrectionRows.filter(row => row.rejected).length;
  const entryCorrectionRejected = entryCorrectionRows.filter(row => row.rejected).length;
  const nestedPreflightCorrectionRejected = nestedPreflightCorrectionRows.filter(row => row.rejected).length;
  const retryRootCorrectionRejected = retryRootCorrectionRows.filter(row => row.rejected).length;
  const runtimeParentCorrectionRejected = runtimeParentCorrectionRows.filter(row => row.rejected).length;
  const critical = [
    gates.LIVE_MATCHING_PROCESS_BLOCKS_DUPLICATE_SPAWN,
    gates.INTERRUPTED_ATTEMPT_TERMINAL_AND_NON_PROMOTABLE,
    gates.RECOVERY_STARTS_ZERO_ADDITIONAL_NATIVE_COMPILE_BLENDER_AFTER_COMPILE_CHECKPOINT,
    gates.DISK_RESERVE_AND_JIT_READMISSION_UNCHANGED,
  ].every(Boolean);
  const scientificVerdict = gatePassed === 34 && attackRejected >= 64 && correctionRejected === 8 && gate0CorrectionRejected === 6 && entryCorrectionRejected === 2 && nestedPreflightCorrectionRejected === 2 && retryRootCorrectionRejected === 2 && runtimeParentCorrectionRejected === 5
    ? 'RESTART_SAFE_PRODUCTION_ORCHESTRATOR_SUPPORTED'
    : critical ? 'RESTART_SAFE_PRODUCTION_ORCHESTRATOR_BOUNDED' : 'RESTART_SAFE_PRODUCTION_ORCHESTRATOR_REJECTED';
  const body = {
    schemaVersion: 'bfs.restartSafeProductionOrchestratorAudit.v0.1',
    experimentId: 'B58-E1',
    status: 'COMPLETE',
    independence: { importedExecutionModules: false, importedNodeBuiltinsOnly: true, sourceReopenedDirectly: true },
    meta: { attemptExact: validHash(metaAttempt, 'attemptHash'), admissionExact: validHash(metaAdmission, 'admissionHash'), receiptExact: validHash(metaReceipt, 'receiptHash'), formalStartExact: validHash(formalStart, 'formalStartHash') },
    jobInspections: Object.values(jobs).map(row => ({ id: row.id, jobRoot: row.jobRoot, exact: row.exact, manifestHash: row.manifest.manifestHash, ledgerEvents: row.ledger.events.length, ledgerHead: row.ledger.head, finalReceiptHash: row.final?.receiptHash ?? null })),
    recomputedResourceTotals: resourceTotals,
    attacks,
    attackSummary: { total: attacks.length, rejected: attackRejected },
    correctionAttacks: correctionRows,
    correctionAttackSummary: { total: correctionRows.length, rejected: correctionRejected },
    gate0,
    gate0CorrectionAttacks: gate0CorrectionRows,
    gate0CorrectionAttackSummary: { total: gate0CorrectionRows.length, rejected: gate0CorrectionRejected },
    entryCorrectionAttacks: entryCorrectionRows,
    entryCorrectionAttackSummary: { total: entryCorrectionRows.length, rejected: entryCorrectionRejected },
    nestedPreflightCorrectionAttacks: nestedPreflightCorrectionRows,
    nestedPreflightCorrectionAttackSummary: { total: nestedPreflightCorrectionRows.length, rejected: nestedPreflightCorrectionRejected },
    failedOfficialPreflight: { uri: retryRootCorrection.failedOfficialPreflight.receipt, exact: failedOfficialExact, sha256: hashBytes(Buffer.from(failedOfficialReceiptText)), preflightHash: failedOfficialReceipt.preflightHash, status: failedOfficialReceipt.status, reason: failedOfficialReceipt.reason },
    retryRootCorrectionAttacks: retryRootCorrectionRows,
    retryRootCorrectionAttackSummary: { total: retryRootCorrectionRows.length, rejected: retryRootCorrectionRejected },
    failedFormalV02: { exact: failedFormalV02Exact, fileCount: failedFormalV02Rows.length, treeSha256: failedFormalV02TreeSha256 },
    runtimeParentCorrectionAttacks: runtimeParentCorrectionRows,
    runtimeParentCorrectionAttackSummary: { total: runtimeParentCorrectionRows.length, rejected: runtimeParentCorrectionRejected },
    gates,
    gatePassed,
    gateTotal: Object.keys(gates).length,
    derivedVerdict: scientificVerdict,
    scientificVerdict,
  };
  return { ...body, auditHash: canonicalHash(body) };
}

async function writeExclusive(absolutePath, value) {
  const handle = await open(absolutePath, 'wx', 0o600);
  try { await handle.writeFile(`${JSON.stringify(sortValue(value), null, 2)}\n`); await handle.sync(); } finally { await handle.close(); }
  const directory = await open(dirname(absolutePath), 'r');
  try { await directory.sync(); } finally { await directory.close(); }
}

export async function runAudit(argv) {
  const parsed = parseArguments(argv);
  const result = await audit(parsed);
  await writeExclusive(parsed.output, result);
  process.stdout.write(`BFS_B58_AUDIT ${result.gatePassed}/${result.gateTotal} attacks=${result.attackSummary.rejected}/${result.attackSummary.total} correction=${result.correctionAttackSummary.rejected}/${result.correctionAttackSummary.total} gate0=${result.gate0CorrectionAttackSummary.rejected}/${result.gate0CorrectionAttackSummary.total} entry=${result.entryCorrectionAttackSummary.rejected}/${result.entryCorrectionAttackSummary.total} nested=${result.nestedPreflightCorrectionAttackSummary.rejected}/${result.nestedPreflightCorrectionAttackSummary.total} retry=${result.retryRootCorrectionAttackSummary.rejected}/${result.retryRootCorrectionAttackSummary.total} runtime=${result.runtimeParentCorrectionAttackSummary.rejected}/${result.runtimeParentCorrectionAttackSummary.total} ${result.scientificVerdict}\n`);
  return result;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  runAudit(process.argv.slice(2)).catch(error => {
    process.stderr.write(`BFS_B58_AUDIT_ERROR ${error.message}\n`);
    process.exitCode = 1;
  });
}
