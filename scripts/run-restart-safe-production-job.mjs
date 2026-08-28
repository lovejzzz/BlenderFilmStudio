#!/usr/bin/env node

import { createHash } from 'node:crypto';
import { execFile } from 'node:child_process';
import { spawn } from 'node:child_process';
import { readFile, readdir } from 'node:fs/promises';
import { relative, resolve, sep } from 'node:path';
import { pathToFileURL } from 'node:url';
import { isDeepStrictEqual, promisify } from 'node:util';
import { setTimeout as delay } from 'node:timers/promises';
import { compileBuildPlan } from './compile-build-plan.mjs';
import {
  canonicalJson,
  validSelfHash,
  acquireWriterLease,
  appendLedgerEvent,
  compareRecordedProcess,
  createManifest,
  deriveJobState,
  readJson,
  readProcessIdentity,
  releaseWriterLease,
  sha256Bytes,
  sha256File,
  writeExclusiveDurableHashed,
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
const NPM = '/opt/homebrew/bin/npm';
const MAXIMUM_CAPTURE_BYTES = 4 * 1024 * 1024;
const execFileAsync = promisify(execFile);

function parseArguments(argv) {
  const parsed = { developmentStopAfterPlan: false, developmentStopAfterCompile: false };
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--mode') parsed.mode = argv[++index];
    else if (token === '--job-root') parsed.jobRoot = argv[++index];
    else if (token === '--request') parsed.request = argv[++index];
    else if (token === '--preflight-evidence-commit') parsed.preflightEvidenceCommit = argv[++index];
    else if (token === '--development-stop-after-plan') parsed.developmentStopAfterPlan = true;
    else if (token === '--development-stop-after-compile') parsed.developmentStopAfterCompile = true;
    else throw new Error(`Unknown or incomplete argument: ${token}`);
  }
  if (!['start', 'resume', 'status'].includes(parsed.mode)) throw new Error('--mode must be start, resume or status');
  if (!parsed.jobRoot) throw new Error('Missing --job-root');
  if (parsed.mode === 'start' && !parsed.request) throw new Error('Start mode requires --request');
  if (parsed.mode !== 'start' && parsed.request) throw new Error('--request is accepted only in start mode');
  if (parsed.mode === 'start' && !COMMIT_PATTERN.test(parsed.preflightEvidenceCommit ?? '')) throw new Error('Start mode requires a full --preflight-evidence-commit');
  if (parsed.mode !== 'start' && parsed.preflightEvidenceCommit) throw new Error('--preflight-evidence-commit is accepted only in start mode');
  if (parsed.developmentStopAfterPlan && parsed.developmentStopAfterCompile) throw new Error('Development stop flags are mutually exclusive');
  if (parsed.mode === 'status' && (parsed.developmentStopAfterPlan || parsed.developmentStopAfterCompile)) throw new Error('Status mode cannot use development flags');
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

function pathsOverlap(left, right) {
  return left === right || left.startsWith(`${right}/`) || right.startsWith(`${left}/`);
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
  const registeredRoots = [{ label: 'jobRoot', path: request.jobRoot }];
  for (const [index, attempt] of request.compileAttempts.entries()) {
    requireString(attempt.attemptId, `compileAttempts[${index}].attemptId`);
    if (attemptIds.has(attempt.attemptId)) throw new Error(`Duplicate compile attempt ID ${attempt.attemptId}`);
    attemptIds.add(attempt.attemptId);
    for (const field of ['preflightRoot', 'productionAttemptRoot', 'outputRoot']) {
      requireNormalizedRelative(attempt[field], `compileAttempts[${index}].${field}`);
      registeredRoots.push({ label: `compileAttempts[${index}].${field}`, path: attempt[field] });
    }
    if (![null, 'INTERRUPT_NATIVE_AFTER_OBSERVED'].includes(attempt.fault ?? null)) throw new Error(`Unsupported compile fault in ${attempt.attemptId}`);
  }
  for (let left = 0; left < registeredRoots.length; left += 1) {
    for (let right = left + 1; right < registeredRoots.length; right += 1) {
      if (pathsOverlap(registeredRoots[left].path, registeredRoots[right].path)) {
        throw new Error(`Registered roots overlap: ${registeredRoots[left].label} and ${registeredRoots[right].label}`);
      }
    }
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
    preflightEvidenceCommit: parsed.preflightEvidenceCommit,
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

function jobRelative(jobRoot, path) {
  const rootUri = repositoryRelative(jobRoot);
  const pathUri = repositoryRelative(path);
  if (!pathUri.startsWith(`${rootUri}/`)) throw new Error(`Path is outside job root: ${pathUri}`);
  return pathUri.slice(rootUri.length + 1);
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
        uri: jobRelative(jobRoot, written.path),
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
      buildPlanA: { uri: jobRelative(jobRoot, firstPath), sha256: await sha256File(firstPath) },
      buildPlanB: { uri: jobRelative(jobRoot, secondPath), sha256: await sha256File(secondPath) },
      planHash: first.planHash,
      canonicalBytesSha256: sha256Bytes(Buffer.from(canonicalJson(first))),
      byteIdentical: true,
    },
    process: { orchestratorPid: process.pid, childProcesses: 0 },
    resources: { compilerWrappers: 0, nativeCompileBlenderStarts: 0, preferredVerifierStarts: 0, artifactAuditBlenderStarts: 0, renderCalls: 0, modelCalls: 0, networkCalls: 0, dockerProcesses: 0 },
  });
}

function spawnCaptured(command, args) {
  const started = process.hrtime.bigint();
  const child = spawn(command, args, {
    cwd: repositoryRoot,
    env: { PATH: '/opt/homebrew/bin:/usr/bin:/bin', LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8' },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  let closed = false;
  let spawnError = null;
  let stdoutBytes = 0;
  let stderrBytes = 0;
  const stdoutChunks = [];
  const stderrChunks = [];
  let stdoutCaptured = 0;
  let stderrCaptured = 0;
  const stdoutHash = createHash('sha256');
  const stderrHash = createHash('sha256');
  function capture(chunk, kind) {
    const isStdout = kind === 'stdout';
    if (isStdout) {
      stdoutBytes += chunk.length;
      stdoutHash.update(chunk);
      if (stdoutCaptured < MAXIMUM_CAPTURE_BYTES) {
        const slice = chunk.subarray(0, MAXIMUM_CAPTURE_BYTES - stdoutCaptured);
        stdoutChunks.push(slice);
        stdoutCaptured += slice.length;
      }
    } else {
      stderrBytes += chunk.length;
      stderrHash.update(chunk);
      if (stderrCaptured < MAXIMUM_CAPTURE_BYTES) {
        const slice = chunk.subarray(0, MAXIMUM_CAPTURE_BYTES - stderrCaptured);
        stderrChunks.push(slice);
        stderrCaptured += slice.length;
      }
    }
  }
  child.stdout.on('data', chunk => capture(chunk, 'stdout'));
  child.stderr.on('data', chunk => capture(chunk, 'stderr'));
  child.on('error', error => { spawnError = error; });
  const completion = new Promise(resolveCompletion => {
    child.on('close', (exitCode, signal) => {
      closed = true;
      const stdout = Buffer.concat(stdoutChunks);
      const stderr = Buffer.concat(stderrChunks);
      resolveCompletion({
        pid: child.pid,
        exitCode,
        signal,
        spawnError: spawnError?.message ?? null,
        elapsedNanoseconds: Number(process.hrtime.bigint() - started),
        stdout: { bytes: stdoutBytes, capturedBytes: stdout.length, sha256: stdoutHash.digest('hex'), truncated: stdoutBytes > stdout.length },
        stderr: { bytes: stderrBytes, capturedBytes: stderr.length, sha256: stderrHash.digest('hex'), truncated: stderrBytes > stderr.length },
        stdoutText: stdout.toString('utf8'),
        stderrText: stderr.toString('utf8'),
      });
    });
  });
  return { child, completion, isClosed: () => closed };
}

async function processParentPairs() {
  const { stdout } = await execFileAsync('/bin/ps', ['-axo', 'pid=,ppid='], {
    encoding: 'utf8', timeout: 2000, env: { PATH: '/usr/bin:/bin', LANG: 'C', LC_ALL: 'C' },
  });
  return stdout.split('\n').map(line => line.trim().split(/\s+/).map(Number)).filter(row => row.length === 2 && row.every(Number.isSafeInteger));
}

function descendantPids(rootPid, pairs) {
  const children = new Map();
  for (const [pid, parentPid] of pairs) {
    if (!children.has(parentPid)) children.set(parentPid, []);
    children.get(parentPid).push(pid);
  }
  const found = [];
  const queue = [rootPid];
  const seen = new Set(queue);
  while (queue.length > 0) {
    const current = queue.shift();
    for (const pid of children.get(current) ?? []) {
      if (seen.has(pid)) continue;
      seen.add(pid);
      found.push(pid);
      queue.push(pid);
    }
  }
  return found;
}

async function observeNativeCompileProcess(rootPid, isClosed, timeoutMs = 10000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline && !isClosed()) {
    const descendants = descendantPids(rootPid, await processParentPairs());
    for (const pid of descendants) {
      const identity = await readProcessIdentity(pid).catch(() => null);
      if (identity?.live && identity.executable.includes('Blender') && identity.argv.includes('compile_scene.py')) return identity;
    }
    await delay(10);
  }
  return null;
}

async function writeAttemptTerminal(jobRoot, stageId, attemptId, status, body) {
  const path = resolve(jobRoot, 'attempts', stageId, attemptId, 'receipt.json');
  const state = await deriveJobState(jobRoot);
  const { record } = await writeExclusiveDurableHashed(path, {
    schemaVersion: 'bfs.restartSafeProductionAttemptReceipt.v0.1',
    jobId: state.manifest.jobId,
    stageId,
    attemptId,
    status,
    promotable: false,
    ...structuredClone(body),
  }, 'receiptHash');
  const eventType = status === 'FAILED' ? 'STAGE_FAILED' : 'STAGE_ABANDONED';
  await appendLedgerEvent(jobRoot, {
    eventType, stageId, attemptId,
    payload: { receipt: { uri: jobRelative(jobRoot, path), sha256: await sha256File(path), receiptHash: record.receiptHash } },
  });
  return { path, receipt: record };
}

async function readOptionalJson(path) {
  try {
    return await readJson(path);
  } catch (error) {
    if (error?.reason === 'REQUIRED_FILE_MISSING') return null;
    throw error;
  }
}

async function readProductionCompileSuccess(manifest, candidate) {
  const receiptPath = await resolveExistingRepositoryPath(`${candidate.outputRoot}/production-receipt.json`, 'Restart-safe production receipt');
  const production = await readJson(receiptPath);
  const receipt = production.value;
  if (receipt.schemaVersion !== 'bfs.productionCompileReceipt.v0.2' || receipt.status !== 'PASS' || !validSelfHash(receipt, 'receiptHash')) {
    throw new Error('Production compile receipt schema, status or self-hash mismatch');
  }
  if (receipt.output?.root !== candidate.outputRoot || receipt.buildPlan?.planHash !== manifest.expectedBuildPlanHash) {
    throw new Error('Production compile output or BuildPlan binding mismatch');
  }
  const diskPath = await resolveExistingRepositoryPath(receipt.authorization?.nativeCompileDiskAdmission?.uri, 'Native compile disk admission');
  const disk = await readJson(diskPath);
  if (disk.sha256 !== receipt.authorization.nativeCompileDiskAdmission.sha256
    || disk.value.diskAdmissionHash !== receipt.authorization.nativeCompileDiskAdmission.diskAdmissionHash
    || !validSelfHash(disk.value, 'diskAdmissionHash') || disk.value.status !== 'ACCEPTED' || disk.value.disk?.status !== 'PASS') {
    throw new Error('Native compile disk admission binding mismatch');
  }
  const currentPath = await resolveExistingRepositoryPath(receipt.restrictedCompile?.compileReceipt?.uri, 'Current CompileReceipt');
  const current = await readJson(currentPath);
  if (current.sha256 !== receipt.restrictedCompile.compileReceipt.sha256 || !validSelfHash(current.value, 'receiptHash')) {
    throw new Error('Current CompileReceipt binding mismatch');
  }
  const nativePid = receipt.restrictedCompile?.budget?.child?.pid ?? receipt.restrictedCompile?.nativeChildPid;
  const budgetPath = await resolveExistingRepositoryPath(receipt.restrictedCompile?.budgetReport?.uri, 'Native compile budget report');
  const budget = await readJson(budgetPath);
  const observedNativePid = budget.value.child?.pid;
  if (!Number.isSafeInteger(observedNativePid) || observedNativePid <= 0 || (nativePid !== undefined && nativePid !== observedNativePid)) {
    throw new Error('Native compile PID accounting mismatch');
  }
  return {
    receipt: { uri: repositoryRelative(receiptPath), sha256: production.sha256, receiptHash: receipt.receiptHash },
    diskAdmission: { uri: repositoryRelative(diskPath), sha256: disk.sha256, diskAdmissionHash: disk.value.diskAdmissionHash },
    currentReceipt: { uri: repositoryRelative(currentPath), sha256: current.sha256, receiptHash: current.value.receiptHash },
    planHash: receipt.buildPlan.planHash,
    structureHash: receipt.restrictedCompile.sceneStructureCanonical.structureHash,
    nativePid: observedNativePid,
  };
}

async function outputRoster(repositoryRelativeRoot) {
  const absolute = resolve(repositoryRoot, repositoryRelativeRoot);
  return readdir(absolute).then(entries => entries.sort()).catch(error => {
    if (error?.code === 'ENOENT') return [];
    throw error;
  });
}

async function validateCompileCandidateForSpawn(jobRoot, manifest, candidate) {
  const preflightRoot = await resolveExistingRepositoryPath(candidate.preflightRoot, 'Production compile preflight root', 'directory');
  const preflight = await readJson(resolve(preflightRoot, 'preflight.json'));
  if (preflight.value.schemaVersion !== 'bfs.productionCompilePreflight.v0.1' || preflight.value.status !== 'ACCEPTED'
    || !validSelfHash(preflight.value, 'preflightHash')) {
    throw new Error(`Production compile preflight is not accepted and exact: ${candidate.preflightRoot}`);
  }
  if (preflight.value.invocation?.sceneSpec !== manifest.sceneSpec.uri
    || preflight.value.invocation?.preflightRoot !== candidate.preflightRoot
    || preflight.value.invocation?.outputRoot !== candidate.outputRoot
    || preflight.value.buildPlan?.planHash !== manifest.expectedBuildPlanHash) {
    throw new Error(`Production compile preflight binding mismatch: ${candidate.attemptId}`);
  }
  await resolveFreshRepositoryPath(candidate.productionAttemptRoot, `Production attempt root ${candidate.attemptId}`);
  await resolveFreshRepositoryPath(candidate.outputRoot, `Production output root ${candidate.attemptId}`);
  const jobRootUri = repositoryRelative(jobRoot);
  for (const [label, path] of Object.entries({ preflightRoot: candidate.preflightRoot, productionAttemptRoot: candidate.productionAttemptRoot, outputRoot: candidate.outputRoot })) {
    if (pathsOverlap(jobRootUri, path)) throw new Error(`${label} overlaps restart-safe job root for ${candidate.attemptId}`);
  }
  return { preflight: { uri: `${candidate.preflightRoot}/preflight.json`, sha256: preflight.sha256, preflightHash: preflight.value.preflightHash } };
}

async function runProductionCompileStage(jobRoot, manifest, candidate) {
  const stageId = 'PRODUCTION_COMPILE';
  const attemptId = candidate.attemptId;
  const candidateAdmission = await validateCompileCandidateForSpawn(jobRoot, manifest, candidate);
  await appendLedgerEvent(jobRoot, {
    eventType: 'STAGE_STARTED', stageId, attemptId,
    payload: { candidate: { preflightRoot: candidate.preflightRoot, productionAttemptRoot: candidate.productionAttemptRoot, outputRoot: candidate.outputRoot, fault: candidate.fault ?? null }, candidateAdmission },
  });
  const launched = spawnCaptured(NPM, [
    'run', 'compile:production', '--',
    '--scene-spec', manifest.sceneSpec.uri,
    '--preflight-root', candidate.preflightRoot,
    '--attempt-root', candidate.productionAttemptRoot,
    '--output-root', candidate.outputRoot,
    '--preflight-evidence-commit', manifest.preflightEvidenceCommit,
  ]);
  const wrapperIdentity = await readProcessIdentity(launched.child.pid);
  if (!wrapperIdentity.live) throw new Error('Production compiler wrapper exited before its identity could be recorded');
  await appendLedgerEvent(jobRoot, {
    eventType: 'PROCESS_STARTED', stageId, attemptId,
    payload: { role: 'PRODUCTION_COMPILER_WRAPPER', process: wrapperIdentity },
  });
  const nativeObserved = await observeNativeCompileProcess(launched.child.pid, launched.isClosed);
  if (nativeObserved) {
    await appendLedgerEvent(jobRoot, {
      eventType: 'NATIVE_PROCESS_OBSERVED', stageId, attemptId,
      payload: { role: 'NATIVE_COMPILE_BLENDER', process: nativeObserved },
    });
  }
  let faultRecord = null;
  if (candidate.fault === 'INTERRUPT_NATIVE_AFTER_OBSERVED') {
    if (!nativeObserved) throw new Error('Controlled interruption could not observe native Blender before wrapper completion');
    let signalSent = false;
    try {
      process.kill(-nativeObserved.pid, 'SIGTERM');
      signalSent = true;
    } catch (error) {
      if (error?.code !== 'ESRCH') throw error;
    }
    faultRecord = { type: candidate.fault, nativeProcess: nativeObserved, signal: 'SIGTERM', signalSent };
    await appendLedgerEvent(jobRoot, {
      eventType: 'FAULT_INJECTED', stageId, attemptId,
      payload: faultRecord,
    });
  }
  const wrapper = await launched.completion;
  if (!nativeObserved) throw new Error('Native Blender completed or failed before durable process identity observation; recovery must fail closed');
  const processRecord = {
    wrapper: wrapperIdentity,
    native: nativeObserved,
    terminal: {
      exitCode: wrapper.exitCode,
      signal: wrapper.signal,
      spawnError: wrapper.spawnError,
      elapsedNanoseconds: wrapper.elapsedNanoseconds,
      stdout: wrapper.stdout,
      stderr: wrapper.stderr,
    },
    fault: faultRecord,
  };
  if (wrapper.exitCode !== 0 || wrapper.signal !== null || wrapper.spawnError !== null) {
    const invalidationPath = resolve(repositoryRoot, candidate.outputRoot, 'invalidation.json');
    const invalidation = await readOptionalJson(invalidationPath);
    if (invalidation && !validSelfHash(invalidation.value, 'invalidationHash')) throw new Error('Failed compile invalidation self-hash mismatch');
    const forbiddenSuccess = await readOptionalJson(resolve(repositoryRoot, candidate.outputRoot, 'production-receipt.json'));
    if (forbiddenSuccess) throw new Error('Failed compile unexpectedly produced a production receipt');
    const terminal = await writeAttemptTerminal(jobRoot, stageId, attemptId, 'FAILED', {
      reason: faultRecord ? 'CONTROLLED_NATIVE_INTERRUPTION' : 'PRODUCTION_COMPILER_FAILED',
      candidate,
      process: processRecord,
      evidence: {
        invalidation: invalidation ? { uri: `${candidate.outputRoot}/invalidation.json`, sha256: invalidation.sha256, invalidationHash: invalidation.value.invalidationHash } : null,
        productionAttemptRoster: await outputRoster(candidate.productionAttemptRoot),
        outputRoster: await outputRoster(candidate.outputRoot),
      },
      resources: {
        productionCompilerStarts: 1,
        nativeCompileBlenderStarts: 1,
        successfulNativeCompiles: 0,
        preferredVerifierStarts: 0,
        artifactAuditBlenderStarts: 0,
        renderCalls: 0, modelCalls: 0, networkCalls: 0, dockerProcesses: 0,
      },
    });
    return { status: 'FAILED', attempt: terminal.receipt };
  }
  if (candidate.fault !== null && candidate.fault !== undefined) throw new Error('Faulted compile unexpectedly completed successfully');
  const output = await readProductionCompileSuccess(manifest, candidate);
  if (output.nativePid !== nativeObserved.pid) throw new Error('Observed native Blender PID does not match the production budget receipt');
  const completed = await completeStage(jobRoot, stageId, attemptId, {
    status: 'COMPLETED',
    promotable: true,
    inputs: {
      sceneSpec: manifest.sceneSpec,
      planHash: manifest.expectedBuildPlanHash,
      productionRelease: manifest.productionRelease,
      preflightRoot: candidate.preflightRoot,
      preflightEvidenceCommit: manifest.preflightEvidenceCommit,
    },
    outputs: output,
    process: processRecord,
    resources: {
      productionCompilerStarts: 1,
      nativeCompileBlenderStarts: 1,
      successfulNativeCompiles: 1,
      preferredVerifierStarts: 0,
      artifactAuditBlenderStarts: 0,
      renderCalls: 0, modelCalls: 0, networkCalls: 0, dockerProcesses: 0,
    },
  });
  return { status: 'COMPLETED', stage: completed.receipt };
}

async function recoverStartedCompile(jobRoot, state) {
  const stage = state.stages.PRODUCTION_COMPILE;
  const started = [...stage.attempts].reverse().find(attempt => attempt.status === 'STARTED');
  if (!started) throw new Error('Started compile stage has no started attempt');
  const processEvent = [...state.ledger.events].reverse().find(row => row.event.eventType === 'PROCESS_STARTED'
    && row.event.stageId === 'PRODUCTION_COMPILE' && row.event.attemptId === started.attemptId);
  if (!processEvent?.event.payload?.process) throw new Error('REFUSE_RECOVERY: started compile has no recorded process identity');
  const nativeEvent = [...state.ledger.events].reverse().find(row => row.event.eventType === 'NATIVE_PROCESS_OBSERVED'
    && row.event.stageId === 'PRODUCTION_COMPILE' && row.event.attemptId === started.attemptId);
  const wrapperComparison = await compareRecordedProcess(processEvent.event.payload.process);
  if (wrapperComparison.state === 'LIVE_MATCH') return { status: 'WAIT_LIVE_PROCESS', process: wrapperComparison.observed };
  if (wrapperComparison.state !== 'DEAD') throw new Error('REFUSE_RECOVERY: compiler wrapper PID identity is ambiguous or reused');
  if (!nativeEvent?.event.payload?.process) {
    throw new Error('REFUSE_RECOVERY: dead wrapper has no durable native Blender identity; orphan state is ambiguous');
  }
  const nativeComparison = await compareRecordedProcess(nativeEvent.event.payload.process);
  if (nativeComparison.state === 'LIVE_MATCH') return { status: 'WAIT_LIVE_PROCESS', process: nativeComparison.observed };
  if (nativeComparison.state !== 'DEAD') throw new Error('REFUSE_RECOVERY: native Blender PID identity is ambiguous or reused');
  const terminal = await writeAttemptTerminal(jobRoot, 'PRODUCTION_COMPILE', started.attemptId, 'ABANDONED', {
    reason: 'RECORDED_WRAPPER_DEAD_WITHOUT_TERMINAL_STAGE_RECEIPT',
    process: {
      wrapper: { recorded: processEvent.event.payload.process, observed: wrapperComparison.observed },
      native: { recorded: nativeEvent.event.payload.process, observed: nativeComparison.observed },
    },
    evidence: { outputPromoted: false },
    resources: { productionCompilerStarts: 1, nativeCompileBlenderStarts: 0, successfulNativeCompiles: 0, preferredVerifierStarts: 0, artifactAuditBlenderStarts: 0, renderCalls: 0, modelCalls: 0, networkCalls: 0, dockerProcesses: 0 },
  });
  return { status: 'ABANDONED', attempt: terminal.receipt };
}

function nextCompileCandidate(manifest, state) {
  const used = new Set(state.stages.PRODUCTION_COMPILE.attempts.map(attempt => attempt.attemptId));
  const candidate = manifest.compileAttempts.find(item => !used.has(item.attemptId));
  if (!candidate) throw new Error('No fresh registered compile attempt remains');
  return candidate;
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
  if (state.stages.PRODUCTION_COMPILE.status === 'COMPLETED') {
    await appendLedgerEvent(jobRoot, {
      eventType: 'STAGE_SKIPPED_VERIFIED', stageId: 'PRODUCTION_COMPILE', attemptId: state.stages.PRODUCTION_COMPILE.completed.attemptId,
      payload: { receiptHash: state.stages.PRODUCTION_COMPILE.completed.receipt.receiptHash },
    });
  } else {
    if (state.stages.PRODUCTION_COMPILE.status === 'STARTED') {
      const recovered = await recoverStartedCompile(jobRoot, state);
      if (recovered.status === 'WAIT_LIVE_PROCESS') {
        return { outcome: 'WAIT_LIVE_PROCESS', state: publicState(await deriveJobState(jobRoot)), process: recovered.process };
      }
      state = await deriveJobState(jobRoot);
    }
    if (!['PENDING', 'FAILED', 'ABANDONED'].includes(state.stages.PRODUCTION_COMPILE.status)) {
      throw new Error(`PRODUCTION_COMPILE is not recoverable from status ${state.stages.PRODUCTION_COMPILE.status}`);
    }
    const compile = await runProductionCompileStage(jobRoot, state.manifest, nextCompileCandidate(state.manifest, state));
    state = await deriveJobState(jobRoot);
    if (compile.status === 'FAILED') return { outcome: 'COMPILE_FAILED_NEEDS_RESUME', state: publicState(state) };
    if (state.manifest.orchestratorFault === 'EXIT_AFTER_PRODUCTION_COMPILE') {
      await appendLedgerEvent(jobRoot, {
        eventType: 'ORCHESTRATOR_FAULT_TRIGGERED', stageId: 'PRODUCTION_COMPILE', attemptId: state.stages.PRODUCTION_COMPILE.completed.attemptId,
        payload: { exitCode: 86, boundary: 'AFTER_COMPILE_RECEIPT_BEFORE_VERIFY_START' },
      });
      return { outcome: 'ORCHESTRATOR_EXIT_AFTER_COMPILE', exitCode: 86, state: publicState(await deriveJobState(jobRoot)) };
    }
  }
  state = await deriveJobState(jobRoot);
  if (parsed.developmentStopAfterCompile) return { outcome: 'DEVELOPMENT_COMPILE_CHECKPOINT', state: publicState(state) };
  throw new Error('VERIFY_RECEIPT implementation is intentionally unavailable in this unfrozen checkpoint');
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
    if (result.exitCode) process.exitCode = result.exitCode;
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
