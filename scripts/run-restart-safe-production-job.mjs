#!/usr/bin/env node

import { readFile } from 'node:fs/promises';
import { relative, resolve, sep } from 'node:path';
import { pathToFileURL } from 'node:url';
import { isDeepStrictEqual } from 'node:util';
import { compileBuildPlan } from './compile-build-plan.mjs';
import {
  canonicalJson,
  validSelfHash,
  acquireWriterLease,
  appendLedgerEvent,
  createManifest,
  deriveJobState,
  releaseWriterLease,
  sha256Bytes,
  sha256File,
  writeExclusiveDurableJson,
  writeStageReceipt,
} from './lib/restart-safe-job-ledger.mjs';
import {
  resolveExistingRepositoryPath,
  resolveFreshRepositoryPath,
} from './lib/production-compile-receipt.mjs';
import { repositoryRoot } from './lib/scene-spec.mjs';

const EXPECTED_STAGE_DAG = [
  { id: 'PLAN_BIND', dependsOn: [] },
  { id: 'PRODUCTION_COMPILE', dependsOn: ['PLAN_BIND'] },
  { id: 'VERIFY_RECEIPT', dependsOn: ['PRODUCTION_COMPILE'] },
  { id: 'FINALIZE', dependsOn: ['VERIFY_RECEIPT'] },
];
const HASH_PATTERN = /^[0-9a-f]{64}$/;
const COMMIT_PATTERN = /^[0-9a-f]{40}$/;

function parseArguments(argv) {
  const parsed = { developmentStopAfterPlan: false };
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--mode') parsed.mode = argv[++index];
    else if (token === '--job-root') parsed.jobRoot = argv[++index];
    else if (token === '--request') parsed.request = argv[++index];
    else if (token === '--development-stop-after-plan') parsed.developmentStopAfterPlan = true;
    else throw new Error(`Unknown or incomplete argument: ${token}`);
  }
  if (!['start', 'resume', 'status'].includes(parsed.mode)) throw new Error('--mode must be start, resume or status');
  if (!parsed.jobRoot) throw new Error('Missing --job-root');
  if (parsed.mode === 'start' && !parsed.request) throw new Error('Start mode requires --request');
  if (parsed.mode !== 'start' && parsed.request) throw new Error('--request is accepted only in start mode');
  if (parsed.mode === 'status' && parsed.developmentStopAfterPlan) throw new Error('Status mode cannot use development flags');
  return parsed;
}

function repositoryRelative(path) {
  return relative(repositoryRoot, path).split(sep).join('/');
}

function requireString(value, label) {
  if (typeof value !== 'string' || value.length === 0) throw new Error(`${label} must be a non-empty string`);
  return value;
}

function requireHash(value, label) {
  if (!HASH_PATTERN.test(value ?? '')) throw new Error(`${label} must be a lowercase SHA-256`);
  return value;
}

function requireNormalizedRelative(value, label) {
  requireString(value, label);
  if (value.startsWith('/') || value.includes('\\') || value === '.' || value.startsWith('../') || value.includes('/../') || value.includes('//')) {
    throw new Error(`${label} must be a normalized repository-relative POSIX path`);
  }
  return value;
}

async function readAndValidateRequest(requestUri, expectedJobRoot) {
  const requestPath = await resolveExistingRepositoryPath(requestUri, 'Restart-safe job request');
  const request = JSON.parse(await readFile(requestPath, 'utf8'));
  if (request.schemaVersion !== 'bfs.restartSafeProductionJobRequest.v0.1' || !validSelfHash(request, 'requestHash')) {
    throw new Error('Restart-safe job request schema or self-hash mismatch');
  }
  requireString(request.jobId, 'request.jobId');
  if (!/^[A-Z0-9][A-Z0-9_-]{2,63}$/.test(request.jobId)) throw new Error('request.jobId is not canonical');
  requireNormalizedRelative(request.jobRoot, 'request.jobRoot');
  if (request.jobRoot !== expectedJobRoot) throw new Error('Request job root does not match invocation');
  if (!isDeepStrictEqual(request.stageDag, EXPECTED_STAGE_DAG)) throw new Error('Request stage DAG mismatch');
  requireNormalizedRelative(request.sceneSpec?.uri, 'request.sceneSpec.uri');
  requireHash(request.sceneSpec?.sha256, 'request.sceneSpec.sha256');
  requireHash(request.expectedBuildPlanHash, 'request.expectedBuildPlanHash');
  requireNormalizedRelative(request.productionRelease?.uri, 'request.productionRelease.uri');
  requireHash(request.productionRelease?.sha256, 'request.productionRelease.sha256');
  if (!COMMIT_PATTERN.test(request.toolFreezeCommit ?? '')) throw new Error('request.toolFreezeCommit must be a full lowercase Git SHA-1');
  if (!Array.isArray(request.compileAttempts) || request.compileAttempts.length === 0) throw new Error('request.compileAttempts must be non-empty');
  const attemptIds = new Set();
  for (const [index, attempt] of request.compileAttempts.entries()) {
    requireString(attempt.attemptId, `compileAttempts[${index}].attemptId`);
    if (attemptIds.has(attempt.attemptId)) throw new Error(`Duplicate compile attempt ID ${attempt.attemptId}`);
    attemptIds.add(attempt.attemptId);
    for (const field of ['preflightRoot', 'productionAttemptRoot', 'outputRoot']) {
      requireNormalizedRelative(attempt[field], `compileAttempts[${index}].${field}`);
    }
    if (![null, 'INTERRUPT_NATIVE_AFTER_OBSERVED'].includes(attempt.fault ?? null)) throw new Error(`Unsupported compile fault in ${attempt.attemptId}`);
  }
  if (![null, 'EXIT_AFTER_PRODUCTION_COMPILE'].includes(request.orchestratorFault ?? null)) throw new Error('Unsupported orchestrator fault');
  const scenePath = await resolveExistingRepositoryPath(request.sceneSpec.uri, 'Job SceneSpec');
  if (await sha256File(scenePath) !== request.sceneSpec.sha256) throw new Error('Job SceneSpec hash mismatch');
  const releasePath = await resolveExistingRepositoryPath(request.productionRelease.uri, 'Production release');
  if (await sha256File(releasePath) !== request.productionRelease.sha256) throw new Error('Production release hash mismatch');
  const first = await compileBuildPlan(request.sceneSpec.uri);
  const second = await compileBuildPlan(request.sceneSpec.uri);
  if (canonicalJson(first) !== canonicalJson(second) || first.planHash !== request.expectedBuildPlanHash) {
    throw new Error('Job request BuildPlan binding mismatch');
  }
  return { requestPath, requestUri, request, requestFileSha256: await sha256File(requestPath), prevalidatedPlan: first };
}

async function initializeJob(parsed) {
  const jobRoot = await resolveFreshRepositoryPath(parsed.jobRoot, 'Restart-safe job root');
  const validated = await readAndValidateRequest(parsed.request, parsed.jobRoot);
  const manifestBody = {
    jobId: validated.request.jobId,
    request: { uri: validated.requestUri, sha256: validated.requestFileSha256, requestHash: validated.request.requestHash },
    sceneSpec: validated.request.sceneSpec,
    expectedBuildPlanHash: validated.request.expectedBuildPlanHash,
    productionRelease: validated.request.productionRelease,
    toolFreezeCommit: validated.request.toolFreezeCommit,
    stageDag: EXPECTED_STAGE_DAG,
    compileAttempts: validated.request.compileAttempts,
    orchestratorFault: validated.request.orchestratorFault ?? null,
    resourcePolicy: validated.request.resourcePolicy ?? {},
  };
  const created = await createManifest(jobRoot, manifestBody);
  await appendLedgerEvent(jobRoot, {
    eventType: 'JOB_CREATED',
    payload: {
      manifest: { uri: 'job-manifest.json', sha256: await sha256File(created.path), manifestHash: created.manifest.manifestHash },
      request: created.manifest.request,
    },
  });
  return { jobRoot, manifest: created.manifest, prevalidatedPlan: validated.prevalidatedPlan };
}

function publicState(state) {
  return {
    schemaVersion: 'bfs.restartSafeProductionJobStatus.v0.1',
    jobId: state.manifest.jobId,
    manifestHash: state.manifest.manifestHash,
    ledgerEvents: state.ledger.events.length,
    ledgerHeadEventHash: state.ledger.headEventHash,
    stages: Object.fromEntries(Object.entries(state.stages).map(([id, stage]) => [id, {
      status: stage.status,
      attempts: stage.attempts.map(attempt => ({ attemptId: attempt.attemptId, status: attempt.status })),
      completedReceiptHash: stage.completed?.receipt?.receiptHash ?? null,
    }])),
    complete: state.stages.FINALIZE.status === 'COMPLETED',
  };
}

async function completeStage(jobRoot, stageId, attemptId, receiptBody) {
  const written = await writeStageReceipt(jobRoot, stageId, attemptId, receiptBody);
  await appendLedgerEvent(jobRoot, {
    eventType: 'STAGE_COMPLETED', stageId, attemptId,
    payload: {
      receipt: {
        uri: repositoryRelative(written.path).slice(repositoryRelative(jobRoot).length + 1),
        sha256: await sha256File(written.path),
        receiptHash: written.receipt.receiptHash,
      },
    },
  });
  return written;
}

async function runPlanStage(jobRoot, manifest, prevalidatedPlan = null) {
  const attemptId = 'PLAN_BIND-0001';
  await appendLedgerEvent(jobRoot, { eventType: 'STAGE_STARTED', stageId: 'PLAN_BIND', attemptId, payload: {} });
  const first = prevalidatedPlan ?? await compileBuildPlan(manifest.sceneSpec.uri);
  const second = await compileBuildPlan(manifest.sceneSpec.uri);
  if (canonicalJson(first) !== canonicalJson(second) || first.planHash !== manifest.expectedBuildPlanHash) {
    throw new Error('PLAN_BIND repeated BuildPlan mismatch');
  }
  const attemptRoot = resolve(jobRoot, 'attempts', 'PLAN_BIND', attemptId);
  const firstPath = resolve(attemptRoot, 'build-plan-a.json');
  const secondPath = resolve(attemptRoot, 'build-plan-b.json');
  await writeExclusiveDurableJson(firstPath, first);
  await writeExclusiveDurableJson(secondPath, second);
  return completeStage(jobRoot, 'PLAN_BIND', attemptId, {
    status: 'COMPLETED',
    promotable: true,
    inputs: { sceneSpec: manifest.sceneSpec, expectedBuildPlanHash: manifest.expectedBuildPlanHash },
    outputs: {
      buildPlanA: { uri: repositoryRelative(firstPath).slice(repositoryRelative(jobRoot).length + 1), sha256: await sha256File(firstPath) },
      buildPlanB: { uri: repositoryRelative(secondPath).slice(repositoryRelative(jobRoot).length + 1), sha256: await sha256File(secondPath) },
      planHash: first.planHash,
      canonicalBytesSha256: sha256Bytes(Buffer.from(canonicalJson(first))),
      byteIdentical: true,
    },
    process: { orchestratorPid: process.pid, childProcesses: 0 },
    resources: { compilerWrappers: 0, nativeCompileBlenderStarts: 0, preferredVerifierStarts: 0, artifactAuditBlenderStarts: 0, renderCalls: 0, modelCalls: 0, networkCalls: 0, dockerProcesses: 0 },
  });
}

async function runAvailableStages(jobRoot, prevalidatedPlan, parsed) {
  let state = await deriveJobState(jobRoot);
  if (state.stages.PLAN_BIND.status === 'COMPLETED') {
    await appendLedgerEvent(jobRoot, {
      eventType: 'STAGE_SKIPPED_VERIFIED', stageId: 'PLAN_BIND', attemptId: state.stages.PLAN_BIND.completed.attemptId,
      payload: { receiptHash: state.stages.PLAN_BIND.completed.receipt.receiptHash },
    });
  } else if (state.stages.PLAN_BIND.status === 'PENDING') {
    await runPlanStage(jobRoot, state.manifest, prevalidatedPlan);
  } else {
    throw new Error(`PLAN_BIND is not recoverable from status ${state.stages.PLAN_BIND.status}`);
  }
  state = await deriveJobState(jobRoot);
  if (parsed.developmentStopAfterPlan) {
    return { outcome: 'DEVELOPMENT_PLAN_CHECKPOINT', state: publicState(state) };
  }
  throw new Error('PRODUCTION_COMPILE implementation is intentionally unavailable in this unfrozen checkpoint');
}

export async function runRestartSafeProductionJob(argv) {
  const parsed = parseArguments(argv);
  let initialized = null;
  let jobRoot;
  if (parsed.mode === 'start') {
    initialized = await initializeJob(parsed);
    jobRoot = initialized.jobRoot;
  } else {
    jobRoot = await resolveExistingRepositoryPath(parsed.jobRoot, 'Restart-safe job root', 'directory');
  }
  if (parsed.mode === 'status') {
    const state = await deriveJobState(jobRoot);
    const result = publicState(state);
    process.stdout.write(`BFS_RESTART_SAFE_JOB_STATUS ${JSON.stringify(result)}\n`);
    return result;
  }
  const lease = await acquireWriterLease(jobRoot, { allowReclaimDead: parsed.mode === 'resume' });
  try {
    const result = await runAvailableStages(jobRoot, initialized?.prevalidatedPlan ?? null, parsed);
    process.stdout.write(`BFS_RESTART_SAFE_JOB ${result.outcome} ${JSON.stringify(result.state)}\n`);
    return result;
  } finally {
    await releaseWriterLease(lease);
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  runRestartSafeProductionJob(process.argv.slice(2)).catch(error => {
    process.stderr.write(`BFS_RESTART_SAFE_JOB_ERROR ${error.message}\n`);
    process.exitCode = 1;
  });
}
