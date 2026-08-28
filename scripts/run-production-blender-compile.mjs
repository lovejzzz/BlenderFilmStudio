#!/usr/bin/env node

import { createHash } from 'node:crypto';
import { spawn } from 'node:child_process';
import { readFile, readdir, rmdir, statfs } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { compileBuildPlan } from './compile-build-plan.mjs';
import { AdmissionError, admitFormalRun } from './lib/formal-run-admission.mjs';
import { evaluateDiskSpace, gibToBytes } from './lib/disk-space-guard.mjs';
import {
  canonicalJson,
  createProductionCompileReceipt,
  durableMkdir,
  repoUri,
  resolveExistingRepositoryPath,
  resolveFreshRepositoryPath,
  sha256File,
  validSelfHash,
  writeDurableHashed,
  writeDurableJson,
} from './lib/production-compile-receipt.mjs';
import { repositoryRoot } from './lib/scene-spec.mjs';

const RELEASE_MANIFEST_URI = 'specs/production-compiler-entry.v0.2.json';
const RESTRICTED_CLI_URI = 'scripts/run-restricted-blender-compile.mjs';

function parseArguments(argv) {
  const parsed = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--scene-spec') parsed.sceneSpec = argv[++index];
    else if (token === '--preflight-root') parsed.preflightRoot = argv[++index];
    else if (token === '--attempt-root') parsed.attemptRoot = argv[++index];
    else if (token === '--output-root') parsed.outputRoot = argv[++index];
    else if (token === '--preflight-evidence-commit') parsed.preflightEvidenceCommit = argv[++index];
    else throw new Error(`Unknown or incomplete argument: ${token}`);
  }
  for (const required of ['sceneSpec', 'preflightRoot', 'attemptRoot', 'outputRoot', 'preflightEvidenceCommit']) {
    if (!parsed[required]) throw new Error(`Missing --${required.replace(/[A-Z]/g, letter => `-${letter.toLowerCase()}`)}`);
  }
  if (!/^[0-9a-f]{40}$/.test(parsed.preflightEvidenceCommit)) throw new Error('Preflight evidence commit must be a full lowercase SHA-1');
  return parsed;
}

async function runChild(command, args) {
  const started = process.hrtime.bigint();
  const child = spawn(command, args, {
    cwd: repositoryRoot,
    env: {
      PATH: '/opt/homebrew/bin:/usr/bin:/bin',
      LANG: 'C.UTF-8',
      LC_ALL: 'C.UTF-8',
      BLENDER_BIN: '/Applications/Blender.app/Contents/MacOS/Blender',
    },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  const stdout = [];
  const stderr = [];
  let stdoutBytes = 0;
  let stderrBytes = 0;
  const maximumLogBytes = 4 * 1024 * 1024;
  child.stdout.on('data', chunk => {
    stdoutBytes += chunk.length;
    if (stdoutBytes <= maximumLogBytes) stdout.push(chunk);
  });
  child.stderr.on('data', chunk => {
    stderrBytes += chunk.length;
    if (stderrBytes <= maximumLogBytes) stderr.push(chunk);
  });
  const completion = await new Promise((resolvePromise, reject) => {
    child.on('error', reject);
    child.on('close', (exitCode, signal) => resolvePromise({ exitCode, signal }));
  });
  const stdoutBuffer = Buffer.concat(stdout);
  const stderrBuffer = Buffer.concat(stderr);
  return {
    pid: child.pid,
    ...completion,
    elapsedNanoseconds: Number(process.hrtime.bigint() - started),
    stdout: { bytes: stdoutBytes, capturedBytes: stdoutBuffer.length, sha256: createHash('sha256').update(stdoutBuffer).digest('hex') },
    stderr: { bytes: stderrBytes, capturedBytes: stderrBuffer.length, sha256: createHash('sha256').update(stderrBuffer).digest('hex') },
    stdoutText: stdoutBuffer.toString('utf8'),
    stderrText: stderrBuffer.toString('utf8'),
  };
}

async function readAcceptedPreflight(preflightRoot, parsed) {
  const preflightPath = resolve(preflightRoot, 'preflight.json');
  const preflight = JSON.parse(await readFile(preflightPath, 'utf8'));
  if (!validSelfHash(preflight, 'preflightHash')) throw new Error('Production preflight self-hash mismatch');
  if (preflight.schemaVersion !== 'bfs.productionCompilePreflight.v0.1' || preflight.status !== 'ACCEPTED') throw new Error('Production preflight is not accepted');
  if (preflight.invocation?.sceneSpec !== parsed.sceneSpec || preflight.invocation?.preflightRoot !== parsed.preflightRoot
    || preflight.invocation?.outputRoot !== parsed.outputRoot || preflight.output?.repositoryRelative !== parsed.outputRoot) {
    throw new Error('Production preflight invocation binding mismatch');
  }
  return { preflightPath, preflight };
}

async function writeAdmissionFailure(attemptRoot, attemptPath, attempt, error, gitChildren) {
  const failurePath = resolve(attemptRoot, 'failure.json');
  const failure = await writeDurableHashed(failurePath, {
    schemaVersion: 'bfs.productionCompileAdmissionFailure.v0.1',
    sequence: 2,
    status: 'REJECTED',
    reason: error instanceof AdmissionError ? error.reason : 'ADMISSION_EXCEPTION',
    message: error?.message ?? String(error),
    attempt: { uri: repoUri(attemptPath), sha256: await sha256File(attemptPath), attemptHash: attempt.attemptHash },
    gitChildren,
    outputMaterialized: false,
    blenderProcessesStarted: 0,
    scientificVerdict: null,
  }, 'failureHash');
  await writeDurableHashed(resolve(attemptRoot, 'receipt.json'), {
    schemaVersion: 'bfs.productionCompileAttemptReceipt.v0.1',
    sequence: 3,
    status: 'REJECTED',
    scientificVerdict: null,
    attempt: { uri: repoUri(attemptPath), sha256: await sha256File(attemptPath), attemptHash: attempt.attemptHash },
    failure: { uri: repoUri(failurePath), sha256: await sha256File(failurePath), failureHash: failure.failureHash },
    outputMaterialized: false,
    compilerProcessesStarted: 0,
  }, 'receiptHash');
}

async function writeInvalidation(outputRoot, phase, error, context = {}) {
  const invalidationPath = resolve(outputRoot, 'invalidation.json');
  try {
    await writeDurableHashed(invalidationPath, {
      schemaVersion: 'bfs.productionCompileInvalidation.v0.1',
      status: 'INVALIDATED',
      phase,
      error: { name: error?.name ?? 'Error', message: error?.message ?? String(error) },
      context,
      partialEvidenceRetained: true,
      scientificVerdict: null,
    }, 'invalidationHash');
  } catch (writeError) {
    if (writeError?.code !== 'EEXIST') throw writeError;
  }
}

async function writeNativeCompileDiskAdmission(outputRoot) {
  const filesystem = await statfs(repositoryRoot, { bigint: true });
  const observedAvailableBytes = filesystem.bavail * filesystem.bsize;
  const ceilingText = process.env.BFS_PRODUCTION_COMPILE_AVAILABLE_BYTES_CEILING;
  let ceilingBytes = null;
  let invalidCeiling = false;
  if (ceilingText !== undefined) {
    if (!/^[0-9]+$/.test(ceilingText)) invalidCeiling = true;
    else {
      ceilingBytes = BigInt(ceilingText);
      if (ceilingBytes > observedAvailableBytes) invalidCeiling = true;
    }
  }
  const effectiveAvailableBytes = invalidCeiling || ceilingBytes === null ? observedAvailableBytes : ceilingBytes;
  const disk = evaluateDiskSpace({
    availableBytes: effectiveAvailableBytes,
    capacityBytes: filesystem.blocks * filesystem.bsize,
    reserveBytes: gibToBytes(100),
    projectedWriteBytes: gibToBytes(0.5),
    target: repositoryRoot,
  });
  const accepted = !invalidCeiling && disk.status === 'PASS';
  return writeDurableHashed(resolve(outputRoot, 'native-compile-disk-admission.json'), {
    schemaVersion: 'bfs.productionNativeCompileDiskAdmission.v0.1',
    sequence: 5,
    status: accepted ? 'ACCEPTED' : 'REJECTED',
    reason: invalidCeiling ? 'TEST_CEILING_MAY_ONLY_LOWER_REAL_OBSERVATION' : disk.reason,
    filesystemAvailableBytesObserved: observedAvailableBytes.toString(),
    effectiveAvailableBytes: effectiveAvailableBytes.toString(),
    testCeilingApplied: ceilingBytes !== null && !invalidCeiling,
    disk,
    policy: { minimumReserveBytes: gibToBytes(100).toString(), projectedWriteBytes: gibToBytes(0.5).toString(), overrideAllowedByReleaseEntry: false },
    restrictedCompilerProcessesStarted: 0,
    nativeBlenderProcessesStarted: 0,
  }, 'diskAdmissionHash');
}

export async function runProductionCompile(argv) {
  const parsed = parseArguments(argv);
  const sceneSpecPath = await resolveExistingRepositoryPath(parsed.sceneSpec, 'Production SceneSpec');
  const preflightRoot = await resolveExistingRepositoryPath(parsed.preflightRoot, 'Production preflight root', 'directory');
  const attemptRoot = await resolveFreshRepositoryPath(parsed.attemptRoot, 'Production attempt root');
  const outputRoot = await resolveFreshRepositoryPath(parsed.outputRoot, 'Production output root');
  const releaseManifestPath = await resolveExistingRepositoryPath(RELEASE_MANIFEST_URI, 'Production release manifest');
  const rootSpellings = [parsed.preflightRoot, parsed.attemptRoot, parsed.outputRoot];
  if (rootSpellings.some((left, index) => rootSpellings.some((right, other) => index !== other && (left === right || left.startsWith(`${right}/`) || right.startsWith(`${left}/`))))) {
    throw new Error('Production preflight, attempt and output roots must be disjoint');
  }
  const preflightPath = await resolveExistingRepositoryPath(`${parsed.preflightRoot}/preflight.json`, 'Production preflight record');

  await durableMkdir(attemptRoot);
  const attemptPath = resolve(attemptRoot, 'attempt.json');
  const attempt = await writeDurableHashed(attemptPath, {
    schemaVersion: 'bfs.productionCompileAttempt.v0.1',
    sequence: 1,
    invocation: parsed,
    preflight: { uri: repoUri(preflightPath), sha256: await sha256File(preflightPath) },
    runnerPid: process.pid,
    outputAbsentBeforeAdmission: true,
    blenderProcessesAuthorized: 0,
    scientificVerdict: null,
  }, 'attemptHash');

  const gitChildren = [];
  let admission;
  let preflight;
  try {
    ({ preflight } = await readAcceptedPreflight(preflightRoot, parsed));
    if (await sha256File(sceneSpecPath) !== preflight.source.sha256) throw new AdmissionError('SCENE_BINDING', 'Production SceneSpec changed after preflight');
    if (await sha256File(releaseManifestPath) !== preflight.release.sha256) throw new AdmissionError('RELEASE_BINDING', 'Production release manifest changed after preflight');
    admission = await admitFormalRun({
      repositoryRoot,
      evidenceInput: parsed.preflightRoot,
      formalOutput: parsed.outputRoot,
      originRef: 'origin/main',
      gitObserver: row => gitChildren.push(row),
    });
    if (admission.evidence.evidenceCommit !== parsed.preflightEvidenceCommit) {
      throw new AdmissionError('EVIDENCE_COMMIT_MISMATCH', 'Preflight evidence commit differs from the CLI binding');
    }
    if (admission.output.repositoryRelative !== parsed.outputRoot) throw new AdmissionError('PREFLIGHT_BINDING', 'Production preflight output binding mismatch');
  } catch (error) {
    await writeAdmissionFailure(attemptRoot, attemptPath, attempt, error, gitChildren);
    process.stdout.write(`BFS_PRODUCTION_COMPILE REJECTED ${error.reason ?? 'ADMISSION_EXCEPTION'} blender=0\n`);
    process.exitCode = 1;
    return { status: 'REJECTED', reason: error.reason ?? 'ADMISSION_EXCEPTION' };
  }

  const admissionPath = resolve(attemptRoot, 'admission.json');
  const admissionRecord = await writeDurableHashed(admissionPath, {
    schemaVersion: 'bfs.productionCompileAdmission.v0.1',
    sequence: 2,
    status: 'ACCEPTED',
    evidence: admission.evidence,
    output: { repositoryRelative: admission.output.repositoryRelative, parentRepositoryRelative: admission.output.parentRepositoryRelative, fresh: admission.output.fresh },
    attempt: { uri: repoUri(attemptPath), sha256: await sha256File(attemptPath), attemptHash: attempt.attemptHash },
    gitChildren,
    compilerProcessesStarted: 0,
    scientificVerdict: null,
  }, 'admissionHash');
  const attemptReceiptPath = resolve(attemptRoot, 'receipt.json');
  const attemptReceipt = await writeDurableHashed(attemptReceiptPath, {
    schemaVersion: 'bfs.productionCompileAttemptReceipt.v0.1',
    sequence: 3,
    status: 'ACCEPTED',
    attempt: { uri: repoUri(attemptPath), sha256: await sha256File(attemptPath), attemptHash: attempt.attemptHash },
    admission: { uri: repoUri(admissionPath), sha256: await sha256File(admissionPath), admissionHash: admissionRecord.admissionHash },
    formalOutput: admissionRecord.output,
    outputMaterializationAuthorized: true,
    scientificVerdict: null,
  }, 'receiptHash');

  let phase = 'OUTPUT_MATERIALIZATION';
  try {
    await durableMkdir(outputRoot);
    const formalStartPath = resolve(outputRoot, 'formal-start.json');
    await writeDurableHashed(formalStartPath, {
      schemaVersion: 'bfs.productionCompileFormalStart.v0.1',
      sequence: 4,
      status: 'AUTHORIZED',
      attemptReceipt: { uri: repoUri(attemptReceiptPath), sha256: await sha256File(attemptReceiptPath), receiptHash: attemptReceipt.receiptHash },
      outputRoot: parsed.outputRoot,
      compilerProcessesStarted: 0,
    }, 'formalStartHash');

    phase = 'BUILD_PLAN';
    const first = await compileBuildPlan(parsed.sceneSpec);
    const second = await compileBuildPlan(parsed.sceneSpec);
    if (canonicalJson(first) !== canonicalJson(second) || first.planHash !== preflight.buildPlan.planHash) {
      throw new Error('Production BuildPlan no longer matches accepted preflight');
    }
    const planPath = resolve(outputRoot, 'build-plan.json');
    await writeDurableJson(planPath, first);

    phase = 'NATIVE_COMPILE_DISK_ADMISSION';
    const diskAdmissionPath = resolve(outputRoot, 'native-compile-disk-admission.json');
    const diskAdmission = await writeNativeCompileDiskAdmission(outputRoot);
    if (diskAdmission.status !== 'ACCEPTED') throw new Error(`Native compile disk admission rejected: ${diskAdmission.reason}`);

    phase = 'RESTRICTED_COMPILE';
    const restrictedRoot = resolve(outputRoot, 'restricted');
    const wrapper = await runChild(process.execPath, [
      resolve(repositoryRoot, RESTRICTED_CLI_URI),
      '--plan', planPath,
      '--output-dir', restrictedRoot,
      '--report', resolve(restrictedRoot, 'budget.report.json'),
      '--receipt', resolve(restrictedRoot, 'compile-receipt.json'),
    ]);
    const wrapperProcess = {
      pid: wrapper.pid,
      exitCode: wrapper.exitCode,
      signal: wrapper.signal,
      elapsedNanoseconds: wrapper.elapsedNanoseconds,
      stdout: wrapper.stdout,
      stderr: wrapper.stderr,
    };
    if (wrapper.exitCode !== 0 || wrapper.signal !== null) {
      throw new Error(`Restricted compiler failed: ${wrapper.stderrText || wrapper.stdoutText}`);
    }
    const emptyFramesPath = resolve(restrictedRoot, 'frames');
    const frameEntries = await readdir(emptyFramesPath).catch(error => {
      if (error?.code === 'ENOENT') return null;
      throw error;
    });
    if (frameEntries && frameEntries.length > 0) throw new Error('Zero-render production compile emitted frame files');
    if (frameEntries) await rmdir(emptyFramesPath);
    wrapperProcess.emptyFramesDirectoryRemoved = frameEntries !== null;

    phase = 'PRODUCTION_RECEIPT';
    const productionReceipt = await createProductionCompileReceipt({
      releaseManifestPath,
      releaseCommit: preflight.release.releaseCommit,
      preflightPath,
      attemptPath,
      admissionPath,
      attemptReceiptPath,
      formalStartPath,
      diskAdmissionPath,
      sceneSpecPath,
      planPath,
      restrictedRoot,
      wrapperProcess,
    });
    await writeDurableJson(resolve(outputRoot, 'production-receipt.json'), productionReceipt);
    process.stdout.write(`BFS_PRODUCTION_COMPILE PASS ${productionReceipt.buildPlan.planHash} ${productionReceipt.restrictedCompile.sceneStructureCanonical.structureHash} ${productionReceipt.receiptHash}\n`);
    return { status: 'PASS', receipt: productionReceipt };
  } catch (error) {
    await writeInvalidation(outputRoot, phase, error, { attemptHash: attempt.attemptHash, admissionHash: admissionRecord.admissionHash });
    process.stderr.write(`BFS_PRODUCTION_COMPILE_INVALIDATED ${phase} ${error.message}\n`);
    process.exitCode = 1;
    return { status: 'INVALIDATED', phase, reason: error.message };
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  runProductionCompile(process.argv.slice(2)).catch(error => {
    process.stderr.write(`BFS_PRODUCTION_COMPILE_ERROR ${error.message}\n`);
    process.exitCode = 1;
  });
}
