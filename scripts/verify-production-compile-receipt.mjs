#!/usr/bin/env node

import { spawn } from 'node:child_process';
import { mkdtemp, readFile, readdir, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { isDeepStrictEqual } from 'node:util';
import { runGit } from './lib/formal-run-admission.mjs';
import {
  canonicalHash,
  canonicalJson,
  repoUri,
  resolveExistingRepositoryPath,
  sha256Bytes,
  sha256File,
  sortValue,
  validSelfHash,
} from './lib/production-compile-receipt.mjs';
import { repositoryRoot } from './lib/scene-spec.mjs';

const BLENDER = '/Applications/Blender.app/Contents/MacOS/Blender';

function parseArguments(argv) {
  if (argv.length !== 2 || argv[0] !== '--receipt') throw new Error('Usage: --receipt RELATIVE_PRODUCTION_RECEIPT');
  return { receipt: argv[1] };
}

async function runChild(command, args) {
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
  return { pid: child.pid, ...completion, stdout: Buffer.concat(stdout).toString('utf8'), stderr: Buffer.concat(stderr).toString('utf8') };
}

async function requireIdentity(identity, label) {
  const filePath = await resolveExistingRepositoryPath(identity?.uri, label);
  const observed = await sha256File(filePath);
  if (observed !== identity.sha256) throw new Error(`${label} file hash mismatch`);
  return filePath;
}

function requireRecord(record, schemaVersion, hashField, label) {
  if (record?.schemaVersion !== schemaVersion) throw new Error(`${label} schema mismatch`);
  if (!validSelfHash(record, hashField)) throw new Error(`${label} self-hash mismatch`);
  return record;
}

async function verifyGitEvidence(admission, checks) {
  const commit = admission.evidence?.evidenceCommit;
  if (!/^[0-9a-f]{40}$/.test(commit ?? '')) throw new Error('Admission evidence commit is invalid');
  const ancestor = await runGit(['merge-base', '--is-ancestor', commit, 'origin/main'], repositoryRoot);
  if (ancestor.exitCode !== 0) throw new Error('Admission evidence commit is not pushed to origin/main');
  checks.push('PREFLIGHT_EVIDENCE_PUSHED');
}

async function invokeCurrentReceiptVerifier(compileReceiptPath) {
  const moduleUri = pathToFileURL(resolve(repositoryRoot, 'scripts/verify-compile-receipt.mjs')).href;
  const source = `const moduleValue=await import(${JSON.stringify(moduleUri)});const result=await moduleValue.verifyCompileReceipt(process.argv[1]);process.stdout.write(JSON.stringify(result));`;
  const child = await runChild(process.execPath, ['--input-type=module', '-e', source, compileReceiptPath]);
  if (child.exitCode !== 0 || child.signal !== null) throw new Error(`Current CompileReceipt verifier process failed: ${child.stderr}`);
  const result = JSON.parse(child.stdout);
  if (!result.valid || result.reason !== 'OK' || result.checks?.length !== 19) throw new Error('Current CompileReceipt verifier did not pass exactly 19 checks');
  return { child: { pid: child.pid, exitCode: child.exitCode, signal: child.signal }, result };
}

async function invokeBlendAudit(blendPath) {
  const scratch = await mkdtemp(join(tmpdir(), 'bfs-production-verifier-'));
  const reportPath = join(scratch, 'blend-audit.json');
  try {
    const child = await runChild(BLENDER, [
      '--background', '--factory-startup', '--disable-autoexec', '--python-exit-code', '1',
      '--python', resolve(repositoryRoot, 'blender/audit_compiled_artifact.py'), '--',
      '--input', blendPath, '--output', reportPath,
    ]);
    if (child.exitCode !== 0 || child.signal !== null) throw new Error(`Compiled .blend audit failed: ${child.stderr || child.stdout}`);
    return { child: { pid: child.pid, exitCode: child.exitCode, signal: child.signal }, result: JSON.parse(await readFile(reportPath, 'utf8')) };
  } finally {
    await rm(scratch, { recursive: true, force: true });
  }
}

async function verify(receiptUri) {
  const checks = [];
  const receiptPath = await resolveExistingRepositoryPath(receiptUri, 'Production receipt');
  const outputRoot = dirname(receiptPath);
  const receipt = JSON.parse(await readFile(receiptPath, 'utf8'));
  if (receipt.schemaVersion !== 'bfs.productionCompileReceipt.v0.2' || receipt.status !== 'PASS') throw new Error('Production receipt schema or status mismatch');
  if (!validSelfHash(receipt, 'receiptHash')) throw new Error('Production receipt self-hash mismatch');
  checks.push('PRODUCTION_RECEIPT_SELF_HASH');

  const releasePath = await requireIdentity(receipt.release, 'Release manifest');
  const release = JSON.parse(await readFile(releasePath, 'utf8'));
  if (release.schemaVersion !== 'bfs.productionCompilerEntry.v0.2' || release.releaseId !== receipt.release.releaseId) throw new Error('Release manifest binding mismatch');
  for (const [uri, expectedSha256] of Object.entries(release.frozenFiles).sort(([left], [right]) => left.localeCompare(right))) {
    const filePath = await resolveExistingRepositoryPath(uri, `Frozen release file ${uri}`);
    if (await sha256File(filePath) !== expectedSha256) throw new Error(`Frozen release file mismatch: ${uri}`);
  }
  const packageDocument = JSON.parse(await readFile(resolve(repositoryRoot, 'package.json'), 'utf8'));
  for (const [key, value] of Object.entries(release.packageAliases)) {
    if (packageDocument.scripts?.[key] !== value) throw new Error(`Preferred package alias mismatch: ${key}`);
  }
  checks.push('RELEASE_AND_PACKAGE_BINDINGS');

  const preflightPath = await requireIdentity(receipt.authorization.preflight, 'Production preflight');
  const attemptPath = await requireIdentity(receipt.authorization.attempt, 'Production attempt');
  const admissionPath = await requireIdentity(receipt.authorization.admission, 'Production admission');
  const attemptReceiptPath = await requireIdentity(receipt.authorization.attemptReceipt, 'Production attempt receipt');
  const formalStartPath = await requireIdentity(receipt.authorization.formalStart, 'Production formal start');
  const preflight = requireRecord(JSON.parse(await readFile(preflightPath, 'utf8')), 'bfs.productionCompilePreflight.v0.1', 'preflightHash', 'Production preflight');
  const attempt = requireRecord(JSON.parse(await readFile(attemptPath, 'utf8')), 'bfs.productionCompileAttempt.v0.1', 'attemptHash', 'Production attempt');
  const admission = requireRecord(JSON.parse(await readFile(admissionPath, 'utf8')), 'bfs.productionCompileAdmission.v0.1', 'admissionHash', 'Production admission');
  const attemptReceipt = requireRecord(JSON.parse(await readFile(attemptReceiptPath, 'utf8')), 'bfs.productionCompileAttemptReceipt.v0.1', 'receiptHash', 'Production attempt receipt');
  const formalStart = requireRecord(JSON.parse(await readFile(formalStartPath, 'utf8')), 'bfs.productionCompileFormalStart.v0.1', 'formalStartHash', 'Production formal start');
  if (preflight.status !== 'ACCEPTED' || admission.status !== 'ACCEPTED' || attemptReceipt.status !== 'ACCEPTED' || formalStart.status !== 'AUTHORIZED') throw new Error('Authorization status mismatch');
  if (attempt.sequence !== 1 || admission.sequence !== 2 || attemptReceipt.sequence !== 3 || formalStart.sequence !== 4) throw new Error('Authorization sequence mismatch');
  if (attempt.preflight.sha256 !== receipt.authorization.preflight.sha256 || admission.evidence?.preflight?.preflightHash !== preflight.preflightHash
    || admission.attempt.attemptHash !== attempt.attemptHash || attemptReceipt.attempt.attemptHash !== attempt.attemptHash || attemptReceipt.admission.admissionHash !== admission.admissionHash
    || formalStart.attemptReceipt.receiptHash !== attemptReceipt.receiptHash) throw new Error('Authorization cross-binding mismatch');
  if (preflight.invocation.outputRoot !== receipt.output.root || admission.output.repositoryRelative !== receipt.output.root
    || formalStart.outputRoot !== receipt.output.root || repoUri(outputRoot) !== receipt.output.root) throw new Error('Authorization output binding mismatch');
  await verifyGitEvidence(admission, checks);
  checks.push('AUTHORIZATION_SEQUENCE_AND_BINDINGS');

  const sceneSpecPath = await requireIdentity(receipt.source, 'Production SceneSpec');
  if (repoUri(sceneSpecPath) !== preflight.source.uri || receipt.source.sha256 !== preflight.source.sha256) throw new Error('SceneSpec preflight binding mismatch');
  const planPath = await requireIdentity(receipt.buildPlan, 'Production BuildPlan');
  const wrapper = JSON.parse(await readFile(planPath, 'utf8'));
  if (sha256Bytes(Buffer.from(canonicalJson(wrapper.plan))) !== wrapper.planHash || wrapper.planHash !== receipt.buildPlan.planHash
    || wrapper.planHash !== preflight.buildPlan.planHash) throw new Error('BuildPlan binding mismatch');
  checks.push('SCENE_AND_BUILD_PLAN_BINDINGS');

  const diskAdmissionPath = await requireIdentity(receipt.authorization.nativeCompileDiskAdmission, 'Native compile disk admission');
  const diskAdmission = requireRecord(JSON.parse(await readFile(diskAdmissionPath, 'utf8')), 'bfs.productionNativeCompileDiskAdmission.v0.1', 'diskAdmissionHash', 'Native compile disk admission');
  if (diskAdmission.sequence !== 5 || diskAdmission.status !== 'ACCEPTED' || diskAdmission.disk?.status !== 'PASS'
    || diskAdmission.policy?.minimumReserveBytes !== '107374182400' || diskAdmission.policy?.projectedWriteBytes !== '536870912'
    || diskAdmission.policy?.overrideAllowedByReleaseEntry !== false
    || BigInt(diskAdmission.effectiveAvailableBytes) > BigInt(diskAdmission.filesystemAvailableBytesObserved)
    || diskAdmission.restrictedCompilerProcessesStarted !== 0 || diskAdmission.nativeBlenderProcessesStarted !== 0) {
    throw new Error('Native compile disk readmission mismatch');
  }
  const receiptDisk = receipt.authorization.nativeCompileDiskAdmission;
  if (receiptDisk.diskAdmissionHash !== diskAdmission.diskAdmissionHash || receiptDisk.sequence !== diskAdmission.sequence
    || receiptDisk.status !== diskAdmission.status || receiptDisk.filesystemAvailableBytesObserved !== diskAdmission.filesystemAvailableBytesObserved
    || receiptDisk.effectiveAvailableBytes !== diskAdmission.effectiveAvailableBytes || receiptDisk.testCeilingApplied !== diskAdmission.testCeilingApplied
    || !isDeepStrictEqual(receiptDisk.policy, diskAdmission.policy)) throw new Error('Production receipt disk cross-binding mismatch');
  checks.push('NATIVE_COMPILE_DISK_READMISSION');

  const budgetPath = await requireIdentity(receipt.restrictedCompile.budgetReport, 'Budget report');
  const compileReceiptPath = await requireIdentity(receipt.restrictedCompile.compileReceipt, 'Current CompileReceipt');
  const manifestPath = await requireIdentity(receipt.restrictedCompile.sceneManifest, 'Scene manifest');
  const structurePath = await requireIdentity(receipt.restrictedCompile.sceneStructureCanonical, 'Canonical scene structure');
  const blendPath = await requireIdentity(receipt.restrictedCompile.sceneBlend, 'Compiled .blend');
  const budget = JSON.parse(await readFile(budgetPath, 'utf8'));
  if (budget.documentType !== 'BFS_BUDGETED_PROCESS_RESULT' || budget.version !== '0.2.0' || budget.outcome !== 'PASS'
    || budget.command !== BLENDER || budget.child?.exitCode !== 0 || budget.child?.signal !== null || budget.child?.spawnError !== null
    || !Number.isSafeInteger(budget.child?.pid) || budget.child.pid <= 0 || budget.child.pid === receipt.restrictedCompile.wrapperProcess.pid) {
    throw new Error('Native budget/PID receipt mismatch');
  }
  checks.push('NATIVE_BUDGET_PID_BINDING');

  const currentVerification = await invokeCurrentReceiptVerifier(compileReceiptPath);
  if (currentVerification.result.planHash !== wrapper.planHash) throw new Error('Current verifier plan binding mismatch');
  checks.push('CURRENT_COMPILE_RECEIPT_19_CHECKS');

  const manifest = JSON.parse(await readFile(manifestPath, 'utf8'));
  const structureBytes = await readFile(structurePath);
  const structureHash = sha256Bytes(structureBytes);
  if (structureHash !== manifest.structureHash || structureHash !== receipt.restrictedCompile.sceneStructureCanonical.structureHash
    || !isDeepStrictEqual(JSON.parse(structureBytes), manifest.structure)) throw new Error('Canonical structure binding mismatch');
  checks.push('MANIFEST_AND_STRUCTURE_BINDINGS');

  const blendAudit = await invokeBlendAudit(blendPath);
  if (blendAudit.result.documentType !== 'BFS_COMPILED_BLEND_AUDIT' || blendAudit.result.version !== '0.1.0'
    || blendAudit.result.scene?.planHash !== wrapper.planHash || blendAudit.result.scene?.structureHash !== structureHash
    || blendAudit.result.scene?.manifestVersion !== manifest.manifestVersion || blendAudit.result.blender?.buildHash !== release.runtime.blender.buildHash) {
    throw new Error('Compiled .blend embedded binding mismatch');
  }
  checks.push('BLEND_EMBEDDED_BINDINGS');

  const rootRoster = (await readdir(outputRoot)).sort();
  const restrictedRoot = dirname(budgetPath);
  const restrictedRoster = (await readdir(restrictedRoot)).sort();
  if (!isDeepStrictEqual(rootRoster, receipt.output.expectedRootRoster) || !isDeepStrictEqual(restrictedRoster, receipt.output.expectedRestrictedRoster)) {
    throw new Error('Production output roster mismatch');
  }
  checks.push('OUTPUT_ROSTER_EXACT');

  const body = {
    schemaVersion: 'bfs.productionCompileVerification.v0.1',
    valid: true,
    reason: 'OK',
    receipt: { uri: receiptUri, sha256: await sha256File(receiptPath), receiptHash: receipt.receiptHash },
    planHash: wrapper.planHash,
    structureHash,
    nativeChildPid: budget.child.pid,
    checks,
    verifierPid: process.pid,
    currentCompileReceiptVerification: currentVerification.result,
    blendAudit: blendAudit.result,
    children: { currentReceiptVerifier: currentVerification.child, blendArtifactAudit: blendAudit.child },
    operations: { renderCalls: 0, modelCalls: 0, networkCalls: 0, dockerProcesses: 0 },
  };
  return { ...body, verificationHash: canonicalHash(body) };
}

export async function verifyProductionCompileReceipt(argv) {
  let result;
  try {
    const parsed = parseArguments(argv);
    result = await verify(parsed.receipt);
  } catch (error) {
    const body = {
      schemaVersion: 'bfs.productionCompileVerification.v0.1',
      valid: false,
      reason: error?.message ?? String(error),
      checks: [],
      operations: { renderCalls: 0, modelCalls: 0, networkCalls: 0, dockerProcesses: 0 },
    };
    result = { ...body, verificationHash: canonicalHash(body) };
  }
  process.stdout.write(`BFS_PRODUCTION_RECEIPT_VERIFICATION_JSON ${JSON.stringify(sortValue(result))}\n`);
  process.stdout.write(`BFS_PRODUCTION_RECEIPT_VERIFY ${result.valid ? 'PASS' : 'FAIL'} ${result.reason}\n`);
  if (!result.valid) process.exitCode = 1;
  return result;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  verifyProductionCompileReceipt(process.argv.slice(2)).catch(error => {
    process.stderr.write(`BFS_PRODUCTION_RECEIPT_VERIFY_ERROR ${error.message}\n`);
    process.exitCode = 1;
  });
}
