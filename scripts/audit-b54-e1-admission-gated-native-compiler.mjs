#!/opt/homebrew/Cellar/node/26.5.0/bin/node

import { createHash } from 'node:crypto';
import { spawn } from 'node:child_process';
import { lstat, mkdir, readFile, readdir, realpath, writeFile } from 'node:fs/promises';
import { dirname, isAbsolute, relative, resolve, sep } from 'node:path';

// This auditor intentionally does not import the B54 preflight or runner.
const SPEC_SHA256 = '4453d24e7e2a36ca114435a979dc7501247b3da1f5ec0f394143356c058d30cd';
const PREREGISTRATION_COMMIT = 'ad13c0bc7400a3e43b296449d8263f10e6a974af';
const NODE_EXECUTABLE = '/opt/homebrew/Cellar/node/26.5.0/bin/node';
const BLENDER_EXECUTABLE = '/Applications/Blender.app/Contents/MacOS/Blender';
const RECEIPT_VERIFIER = 'scripts/verify-compile-receipt.mjs';
const BLEND_AUDITOR = 'blender/audit_compiled_artifact.py';
const TOOL_PATHS = [
  'scripts/lib/formal-run-admission.mjs',
  'scripts/preflight-b54-e1-admission-gated-native-compiler.mjs',
  'scripts/run-b54-e1-admission-gated-native-compiler.mjs',
  'scripts/audit-b54-e1-admission-gated-native-compiler.mjs',
  'scripts/compile-build-plan.mjs',
  'scripts/lib/scene-spec.mjs',
  'scripts/lib/scene-spec-v02.mjs',
  'scripts/lib/scene-spec-v03.mjs',
  'scripts/lib/scene-spec-v04.mjs',
  'scripts/lib/scene-spec-v05.mjs',
  'scripts/lib/actor-spec.mjs',
  'scripts/lib/grasp-spec.mjs',
  'scripts/lib/trajectory-spec.mjs',
  'scripts/run-restricted-blender-compile.mjs',
  'scripts/lib/budgeted-process.mjs',
  'scripts/lib/compile-receipt.mjs',
  'scripts/lib/receipt-format.mjs',
  RECEIPT_VERIFIER,
  'blender/compile_scene.py',
  BLEND_AUDITOR,
];
const CONFIG_PATHS = [
  'specs/restricted-compile-budget.v0.1.json',
  'specs/output-spec.v0.1.json',
  'color/ocio/cg-config-v4.0.0_aces-v2.0_ocio-v2.5.ocio',
  'specs/benchmarks/B01.scene.json',
  'specs/benchmarks/B02.scene.json',
];
const EXPECTED_RUN_FILES = [
  'budget.report.json',
  'compile.receipt.json',
  'frames',
  'scene.blend',
  'scene.manifest.json',
  'scene.structure.canonical.json',
];

function parseArguments(argv) {
  const parsed = { developmentProbe: false };
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--development-probe') parsed.developmentProbe = true;
    else if (token === '--spec') parsed.spec = argv[++index];
    else if (token === '--preflight-root') parsed.preflightRoot = argv[++index];
    else if (token === '--attempt-root') parsed.attemptRoot = argv[++index];
    else if (token === '--formal-root') parsed.formalRoot = argv[++index];
    else if (token === '--operation-draft') parsed.operationDraft = argv[++index];
    else if (token === '--output') parsed.output = argv[++index];
    else throw new Error(`Unknown or incomplete argument: ${token}`);
  }
  return parsed;
}

function sortValue(value) {
  if (Array.isArray(value)) return value.map(sortValue);
  if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map(key => [key, sortValue(value[key])]));
  return value;
}

function canonicalJson(value) {
  return JSON.stringify(sortValue(value));
}

function sha256Bytes(value) {
  return createHash('sha256').update(value).digest('hex');
}

function canonicalHash(value) {
  return sha256Bytes(Buffer.from(canonicalJson(value)));
}

async function sha256File(path) {
  return sha256Bytes(await readFile(path));
}

function validSelfHash(record, field) {
  const body = structuredClone(record);
  delete body[field];
  return typeof record[field] === 'string' && record[field] === canonicalHash(body);
}

function deepExact(left, right) {
  return canonicalJson(left) === canonicalJson(right);
}

function below(root, candidate) {
  const pathFromRoot = relative(root, candidate);
  return pathFromRoot !== '' && pathFromRoot !== '..' && !pathFromRoot.startsWith(`..${sep}`) && !isAbsolute(pathFromRoot);
}

async function pathState(path) {
  try { return await lstat(path); } catch (error) {
    if (error?.code === 'ENOENT') return null;
    throw error;
  }
}

function repoUri(repositoryRoot, path) {
  return relative(repositoryRoot, path).split(sep).join('/');
}

async function readHashed(path, field) {
  const record = JSON.parse(await readFile(path, 'utf8'));
  return { record, valid: validSelfHash(record, field), sha256: await sha256File(path) };
}

async function runGit(args, cwd, rows, phase) {
  const started = process.hrtime.bigint();
  const child = spawn('/usr/bin/git', args, {
    cwd,
    env: { PATH: '/usr/bin:/bin', LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8', GIT_CONFIG_NOSYSTEM: '1', GIT_TERMINAL_PROMPT: '0' },
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
  const row = {
    phase,
    args,
    pid: child.pid,
    exitCode,
    stdout: Buffer.concat(stdout).toString('utf8'),
    stderr: Buffer.concat(stderr).toString('utf8'),
    elapsedNanoseconds: Number(process.hrtime.bigint() - started),
  };
  rows.push(row);
  return row;
}

async function runChild(command, args, role, repositoryRoot, logRoot) {
  const started = process.hrtime.bigint();
  const child = spawn(command, args, {
    cwd: repositoryRoot,
    env: { ...process.env, PATH: '/usr/bin:/bin:/opt/homebrew/bin', LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8', BLENDER_BIN: BLENDER_EXECUTABLE },
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
    stdout: { uri: repoUri(repositoryRoot, stdoutPath), sha256: sha256Bytes(stdoutBytes), bytes: stdoutBytes.length },
    stderr: { uri: repoUri(repositoryRoot, stderrPath), sha256: sha256Bytes(stderrBytes), bytes: stderrBytes.length },
  };
}

async function processRecordExact(row, repositoryRoot) {
  if (!row || !Number.isInteger(row.pid) || !Number.isInteger(row.exitCode) || !Number.isFinite(row.elapsedNanoseconds) || row.elapsedNanoseconds < 0 || !Array.isArray(row.args)) return false;
  for (const stream of ['stdout', 'stderr']) {
    const binding = row[stream];
    if (!binding?.uri || !below(repositoryRoot, resolve(repositoryRoot, binding.uri))) return false;
    const path = resolve(repositoryRoot, binding.uri);
    const state = await pathState(path);
    if (!state?.isFile() || state.size !== binding.bytes || await sha256File(path) !== binding.sha256) return false;
  }
  return true;
}

async function collectNames(root) {
  return (await readdir(root, { withFileTypes: true })).map(entry => entry.name).sort();
}

async function findBackupFiles(root) {
  const found = [];
  async function visit(directory) {
    for (const entry of await readdir(directory, { withFileTypes: true })) {
      const path = resolve(directory, entry.name);
      if (entry.isDirectory()) await visit(path);
      else if (entry.name.endsWith('.blend1') || entry.name.endsWith('~')) found.push(path);
    }
  }
  await visit(root);
  return found;
}

function mutate(record, path, value) {
  const copy = structuredClone(record);
  let target = copy;
  for (const segment of path.slice(0, -1)) target = target[segment];
  target[path.at(-1)] = value;
  return copy;
}

function omit(record, keys) {
  const copy = { ...record };
  for (const key of keys) delete copy[key];
  return copy;
}

function receiptSelfExact(receipt) {
  if (!validSelfHash(receipt, 'receiptHash')) return false;
  return receipt.executionIdentityHash === canonicalHash(receipt.executionIdentity);
}

function manifestBindingExact(manifest, structureBytes, planHash) {
  const structureHash = sha256Bytes(structureBytes);
  let structure;
  try { structure = JSON.parse(structureBytes); } catch { return false; }
  return manifest.execution?.planHash === planHash
    && manifest.structureHash === structureHash
    && manifest.structureCanonical?.sha256 === structureHash
    && deepExact(manifest.structure, structure);
}

function blendBindingExact(report, planHash, structureHash, spec) {
  return report.scene?.planHash === planHash
    && report.scene?.structureHash === structureHash
    && report.scene?.manifestVersion === '0.2.0'
    && report.blender?.buildHash === spec.runtime.blender.buildHash;
}

async function main() {
  const args = parseArguments(process.argv.slice(2));
  const specPath = resolve(args.spec ?? 'specs/admission-gated-native-compiler-integration.v0.1.json');
  const repositoryRoot = await realpath(resolve(dirname(specPath), '..'));
  if (args.developmentProbe) {
    const passed = await sha256File(specPath) === SPEC_SHA256;
    process.stdout.write(`${JSON.stringify({ status: passed ? 'PASS' : 'FAIL', formalRootsCreated: false, blenderProcesses: 0 })}\n`);
    if (!passed) process.exitCode = 1;
    return;
  }
  for (const required of ['spec', 'preflightRoot', 'attemptRoot', 'formalRoot', 'operationDraft', 'output']) {
    if (!args[required]) throw new Error(`Missing --${required.replace(/[A-Z]/g, letter => `-${letter.toLowerCase()}`)}`);
  }
  const spec = JSON.parse(await readFile(specPath, 'utf8'));
  const preflightRoot = await realpath(resolve(repositoryRoot, args.preflightRoot));
  const attemptRoot = await realpath(resolve(repositoryRoot, args.attemptRoot));
  const formalRoot = await realpath(resolve(repositoryRoot, args.formalRoot));
  const operationDraftPath = resolve(repositoryRoot, args.operationDraft);
  const outputPath = resolve(repositoryRoot, args.output);
  if (args.preflightRoot !== spec.freshness.preflightRoot
    || args.attemptRoot !== spec.freshness.attemptRoot
    || args.formalRoot !== spec.freshness.formalRoot
    || operationDraftPath !== resolve(formalRoot, 'operation-draft.json')
    || outputPath !== resolve(formalRoot, 'audit.json')) throw new Error('Auditor root or output binding mismatch');
  if (await pathState(outputPath)) throw new Error('Audit output already exists');

  const replayRoot = resolve(formalRoot, 'audit-replay');
  const verifierRoot = resolve(replayRoot, 'verifier');
  const blendRoot = resolve(replayRoot, 'blend');
  const logRoot = resolve(replayRoot, 'process-logs');
  if (await pathState(replayRoot)) throw new Error('Audit replay root already exists');
  await mkdir(replayRoot);
  await mkdir(verifierRoot);
  await mkdir(blendRoot);
  await mkdir(logRoot);

  const preflightRead = await readHashed(resolve(preflightRoot, 'preflight.json'), 'preflightHash');
  const preflightReceiptRead = await readHashed(resolve(preflightRoot, 'receipt.json'), 'receiptHash');
  const attemptRead = await readHashed(resolve(attemptRoot, 'attempt.json'), 'attemptHash');
  const admissionRead = await readHashed(resolve(attemptRoot, 'admission.json'), 'admissionHash');
  const attemptReceiptRead = await readHashed(resolve(attemptRoot, 'receipt.json'), 'receiptHash');
  const formalStartRead = await readHashed(resolve(formalRoot, 'formal-start.json'), 'startHash');
  const planObservationRead = await readHashed(resolve(formalRoot, 'plan-observations.json'), 'observationHash');
  const operationDraftRead = await readHashed(operationDraftPath, 'operationHash');
  const preflight = preflightRead.record;
  const attempt = attemptRead.record;
  const admission = admissionRead.record;
  const attemptReceipt = attemptReceiptRead.record;
  const formalStart = formalStartRead.record;
  const planObservation = planObservationRead.record;
  const operationDraft = operationDraftRead.record;

  const gitChildren = [];
  const evidenceRelative = args.preflightRoot;
  const tracked = await runGit(['ls-files', '-z', '--', evidenceRelative], repositoryRoot, gitChildren, 'PREFLIGHT_TRACKED');
  const clean = await runGit(['status', '--porcelain=v1', '--untracked-files=all', '--', evidenceRelative], repositoryRoot, gitChildren, 'PREFLIGHT_CLEAN');
  const evidenceCommit = await runGit(['log', '-1', '--format=%H', '--', evidenceRelative], repositoryRoot, gitChildren, 'PREFLIGHT_COMMIT');
  const origin = await runGit(['rev-parse', '--verify', spec.runtime.git.originRef], repositoryRoot, gitChildren, 'ORIGIN');
  const evidenceAncestor = await runGit(['merge-base', '--is-ancestor', evidenceCommit.stdout.trim(), spec.runtime.git.originRef], repositoryRoot, gitChildren, 'PREFLIGHT_ANCESTOR');
  const preregAncestor = await runGit(['merge-base', '--is-ancestor', PREREGISTRATION_COMMIT, preflight.toolFreezeCommit], repositoryRoot, gitChildren, 'PREREGISTRATION_ANCESTOR');
  const freezeAncestor = await runGit(['merge-base', '--is-ancestor', preflight.toolFreezeCommit, evidenceCommit.stdout.trim()], repositoryRoot, gitChildren, 'TOOL_FREEZE_ANCESTOR');

  const toolChecks = [];
  for (const [uri, expected] of Object.entries(preflight.toolHashes ?? {}).sort(([left], [right]) => left.localeCompare(right))) {
    const path = resolve(repositoryRoot, uri);
    toolChecks.push({ uri, expected, observed: await sha256File(path), exact: expected === await sha256File(path) });
  }
  const toolRosterExact = deepExact(Object.keys(preflight.toolHashes ?? {}).sort(), [...TOOL_PATHS].sort());
  const configurationChecks = [];
  for (const uri of CONFIG_PATHS) {
    const observed = await sha256File(resolve(repositoryRoot, uri));
    configurationChecks.push({ uri, expected: preflight.configurationHashes?.[uri] ?? null, observed, exact: preflight.configurationHashes?.[uri] === observed });
  }
  const configurationRosterExact = deepExact(Object.keys(preflight.configurationHashes ?? {}).sort(), [...CONFIG_PATHS].sort());
  const parent = spec.parentEvidence.admissionTotality;
  const parentResultRead = await readHashed(resolve(repositoryRoot, parent.results.uri), 'resultHash');
  const parentReceiptRead = await readHashed(resolve(repositoryRoot, parent.receipt.uri), 'receiptHash');
  const parentExact = parentResultRead.valid && parentReceiptRead.valid
    && parentResultRead.sha256 === parent.results.sha256 && parentResultRead.record.resultHash === parent.results.resultHash
    && parentReceiptRead.sha256 === parent.receipt.sha256 && parentReceiptRead.record.receiptHash === parent.receipt.receiptHash
    && await sha256File(resolve(repositoryRoot, parent.admissionLibrary.uri)) === parent.admissionLibrary.sha256;
  const nodeExact = process.execPath === spec.runtime.node.executable && process.version === spec.runtime.node.version && await sha256File(process.execPath) === spec.runtime.node.sha256;
  const blenderBinaryExact = await sha256File(BLENDER_EXECUTABLE) === spec.runtime.blender.sha256;
  const specAndToolsExact = await sha256File(specPath) === SPEC_SHA256
    && parentExact && nodeExact && blenderBinaryExact
    && toolRosterExact && toolChecks.length === TOOL_PATHS.length && toolChecks.every(row => row.exact)
    && configurationRosterExact && configurationChecks.every(row => row.exact)
    && configurationChecks.find(row => row.uri === 'specs/benchmarks/B01.scene.json')?.observed === spec.inputs.benchmarks[0].sceneSpecSha256
    && configurationChecks.find(row => row.uri === 'specs/benchmarks/B02.scene.json')?.observed === spec.inputs.benchmarks[1].sceneSpecSha256
    && configurationChecks.find(row => row.uri === spec.inputs.outputSpec.uri)?.observed === spec.inputs.outputSpec.sha256
    && preregAncestor.exitCode === 0 && freezeAncestor.exitCode === 0;

  const preflightReceiptBindingExact = preflightReceiptRead.valid
    && preflightReceiptRead.record.status === 'ACCEPTED'
    && preflightReceiptRead.record.preflight?.sha256 === preflightRead.sha256
    && preflightReceiptRead.record.preflight?.preflightHash === preflight.preflightHash;
  const preflightAcceptedPushed = preflightRead.valid && preflight.status === 'ACCEPTED'
    && preflight.checkPassed === preflight.checkTotal
    && preflight.operationCounts?.blenderProcesses === 0
    && preflight.operationCounts?.blenderRenderCalls === 0
    && tracked.exitCode === 0 && tracked.stdout.length > 0 && clean.exitCode === 0 && clean.stdout === ''
    && evidenceCommit.exitCode === 0 && evidenceCommit.stdout.trim() === attempt.invocation?.preflightEvidenceCommit
    && origin.exitCode === 0 && evidenceAncestor.exitCode === 0
    && preflightReceiptBindingExact;

  const evidenceIdentityBody = structuredClone(admission.evidence ?? {});
  delete evidenceIdentityBody.identityHash;
  const admissionIdentityExact = admission.evidence?.identityHash === canonicalHash(evidenceIdentityBody)
    && admission.evidence?.evidenceCommit === evidenceCommit.stdout.trim()
    && admission.evidence?.preflight?.sha256 === preflightRead.sha256
    && admission.evidence?.preflight?.preflightHash === preflight.preflightHash
    && deepExact(admission.evidence?.toolHashes, preflight.toolHashes);
  const relativeAdmissionAccepted = admission.status === 'ACCEPTED'
    && attempt.invocation?.preflightRoot === spec.freshness.preflightRoot
    && attempt.invocation?.attemptRoot === spec.freshness.attemptRoot
    && attempt.invocation?.outputRoot === spec.freshness.formalRoot
    && admission.invocation?.evidenceInput === spec.freshness.preflightRoot
    && admission.invocation?.formalOutput === spec.freshness.formalRoot
    && admission.output?.repositoryRelative === spec.freshness.formalRoot
    && admissionIdentityExact;
  const attemptAdmissionReceiptExact = attemptRead.valid && admissionRead.valid && attemptReceiptRead.valid
    && attempt.sequence === 1 && admission.sequence === 2 && attemptReceipt.sequence === 3
    && admission.attempt?.sha256 === attemptRead.sha256 && admission.attempt?.attemptHash === attempt.attemptHash
    && attemptReceipt.attempt?.sha256 === attemptRead.sha256 && attemptReceipt.attempt?.attemptHash === attempt.attemptHash
    && attemptReceipt.admission?.sha256 === admissionRead.sha256 && attemptReceipt.admission?.admissionHash === admission.admissionHash;
  const formalAfterAdmission = formalStartRead.valid && formalStart.sequence === 4
    && attempt.formalRootAbsentBeforeAdmission === true
    && admission.compilerProcessesStarted === 0
    && attemptReceipt.formalRootMaterializationAuthorized === true
    && formalStart.authorization?.attemptReceipt?.sha256 === attemptReceiptRead.sha256
    && formalStart.authorization?.attemptReceipt?.receiptHash === attemptReceipt.receiptHash
    && formalStart.authorization?.formalRoot === spec.freshness.formalRoot;

  const planAudits = [];
  for (const benchmark of spec.inputs.benchmarks) {
    const binding = planObservation.plans?.find(row => row.benchmark === benchmark.id);
    const observation = planObservation.observations?.find(row => row.benchmark === benchmark.id);
    const path = resolve(repositoryRoot, binding?.uri ?? 'missing');
    const wrapper = JSON.parse(await readFile(path, 'utf8'));
    const observedPlanHash = sha256Bytes(Buffer.from(canonicalJson(wrapper.plan)));
    planAudits.push({
      benchmark: benchmark.id,
      uri: binding?.uri ?? null,
      fileSha256: await sha256File(path),
      fileBindingExact: binding?.sha256 === await sha256File(path),
      planSelfHashExact: wrapper.planHash === observedPlanHash,
      bindingExact: wrapper.planHash === binding?.planHash,
      frozenExact: wrapper.planHash === benchmark.expectedPlanHash,
      pairObservationExact: observation?.canonicalBytesExact === true
        && observation?.frozenPlanHashExact === true
        && observation?.firstPlanHash === benchmark.expectedPlanHash
        && observation?.secondPlanHash === benchmark.expectedPlanHash
        && observation?.firstCanonicalSha256 === observation?.secondCanonicalSha256,
      wrapper,
    });
  }
  const buildPlanPairExact = planObservationRead.valid && planAudits.length === 2 && planAudits.every(row => row.pairObservationExact && row.fileBindingExact);
  const planHashesFrozen = planAudits.every(row => row.planSelfHashExact && row.bindingExact && row.frozenExact);
  const sceneSpecSuiteExact = preflight.sceneSpecSuite?.passed === true && preflight.sceneSpecSuite?.observedCases === 22;

  const verifierChildren = [];
  const blendChildren = [];
  const runAudits = [];
  for (const benchmark of spec.inputs.benchmarks) {
    for (const suffix of ['A', 'B']) {
      const runId = `${benchmark.id}-${suffix}`;
      const runRoot = resolve(formalRoot, 'runs', runId);
      const names = await collectNames(runRoot);
      const framesEmpty = (await collectNames(resolve(runRoot, 'frames'))).length === 0;
      const budgetPath = resolve(runRoot, 'budget.report.json');
      const receiptPath = resolve(runRoot, 'compile.receipt.json');
      const manifestPath = resolve(runRoot, 'scene.manifest.json');
      const structurePath = resolve(runRoot, 'scene.structure.canonical.json');
      const blendPath = resolve(runRoot, 'scene.blend');
      const budget = JSON.parse(await readFile(budgetPath, 'utf8'));
      const receipt = JSON.parse(await readFile(receiptPath, 'utf8'));
      const manifest = JSON.parse(await readFile(manifestPath, 'utf8'));
      const structureBytes = await readFile(structurePath);
      const structureHash = sha256Bytes(structureBytes);
      const operationBinding = operationDraft.runBindings?.find(row => row.runId === runId);
      const verifierPath = resolve(verifierRoot, `${runId}.verification.json`);
      const verifierChild = await runChild(NODE_EXECUTABLE, [RECEIPT_VERIFIER, '--receipt', repoUri(repositoryRoot, receiptPath), '--report', repoUri(repositoryRoot, verifierPath)], `RECEIPT_VERIFIER_${runId}`, repositoryRoot, logRoot);
      verifierChildren.push(verifierChild);
      const verification = JSON.parse(await readFile(verifierPath, 'utf8'));
      const blendAuditPath = resolve(blendRoot, `${runId}.blend-audit.json`);
      const blendChild = await runChild(BLENDER_EXECUTABLE, ['--background', '--factory-startup', '--disable-autoexec', '--python-exit-code', '1', '--python', resolve(repositoryRoot, BLEND_AUDITOR), '--', '--input', blendPath, '--output', blendAuditPath], `BLEND_AUDIT_${runId}`, repositoryRoot, logRoot);
      blendChildren.push(blendChild);
      const blendAudit = JSON.parse(await readFile(blendAuditPath, 'utf8'));
      const planHash = benchmark.expectedPlanHash;
      runAudits.push({
        runId,
        benchmark: benchmark.id,
        outputUri: repoUri(repositoryRoot, runRoot),
        names,
        framesEmpty,
        rosterExact: deepExact(names, EXPECTED_RUN_FILES) && framesEmpty,
        budget,
        budgetSha256: await sha256File(budgetPath),
        budgetBindingExact: operationBinding?.budget?.sha256 === await sha256File(budgetPath) && operationBinding?.budget?.outcome === 'PASS',
        nativeInvocationSemanticExact: budget.outcome === 'PASS'
          && budget.command === BLENDER_EXECUTABLE
          && budget.args?.includes('--background') && budget.args?.includes('--factory-startup') && budget.args?.includes('--disable-autoexec')
          && budget.child?.exitCode === 0,
        nativeChildPid: budget.child?.pid ?? null,
        receipt,
        receiptSha256: await sha256File(receiptPath),
        receiptSelfExact: receiptSelfExact(receipt),
        receiptBindingExact: operationBinding?.receipt?.sha256 === await sha256File(receiptPath) && operationBinding?.receipt?.receiptHash === receipt.receiptHash,
        verification,
        verificationUri: repoUri(repositoryRoot, verifierPath),
        verificationSha256: await sha256File(verifierPath),
        verifierExact: verifierChild.exitCode === 0 && verification.valid === true && verification.reason === 'OK' && verification.checks?.length === 19,
        manifest,
        manifestSha256: await sha256File(manifestPath),
        structureSha256: structureHash,
        structureBytes,
        structureBindingExact: manifestBindingExact(manifest, structureBytes, planHash),
        expectedStructureExact: structureHash === benchmark.expectedStructureHash,
        blendSha256: await sha256File(blendPath),
        blendAudit,
        blendAuditUri: repoUri(repositoryRoot, blendAuditPath),
        blendAuditSha256: await sha256File(blendAuditPath),
        blendBindingExact: blendChild.exitCode === 0 && blendBindingExact(blendAudit, planHash, structureHash, spec),
      });
    }
  }

  const pairStructureBytesExact = spec.inputs.benchmarks.every(benchmark => {
    const left = runAudits.find(row => row.runId === `${benchmark.id}-A`);
    const right = runAudits.find(row => row.runId === `${benchmark.id}-B`);
    return left && right && left.structureBytes.equals(right.structureBytes);
  });
  const structureHashesFrozen = runAudits.every(row => row.expectedStructureExact && row.structureBindingExact);
  const fourCompilesPass = runAudits.length === 4 && runAudits.every(row => {
    const binding = operationDraft.runBindings?.find(item => item.runId === row.runId);
    return binding?.freshOutputBeforeStart === true
      && row.rosterExact && row.budgetBindingExact && row.nativeInvocationSemanticExact && row.receiptSelfExact && row.receiptBindingExact;
  });
  const fourVerifiersExact = runAudits.every(row => row.verifierExact);
  const fourBlendBindingsExact = runAudits.every(row => row.blendBindingExact);
  const backupFiles = await findBackupFiles(formalRoot);
  const formalTopLevelExact = deepExact(await collectNames(formalRoot), [
    'audit-replay',
    'formal-start.json',
    'operation-draft.json',
    'plan-observations.json',
    'plans',
    'process-logs',
    'runs',
  ]);
  const plansRosterExact = deepExact(await collectNames(resolve(formalRoot, 'plans')), ['B01.build-plan.json', 'B02.build-plan.json']);
  const runnerLogsRosterExact = deepExact(await collectNames(resolve(formalRoot, 'process-logs')), [
    'restricted-compile-b01-a.stderr.log',
    'restricted-compile-b01-a.stdout.log',
    'restricted-compile-b01-b.stderr.log',
    'restricted-compile-b01-b.stdout.log',
    'restricted-compile-b02-a.stderr.log',
    'restricted-compile-b02-a.stdout.log',
    'restricted-compile-b02-b.stderr.log',
    'restricted-compile-b02-b.stdout.log',
  ]);
  const replayRosterExact = deepExact(await collectNames(replayRoot), ['blend', 'process-logs', 'verifier'])
    && (await collectNames(verifierRoot)).length === 4
    && (await collectNames(blendRoot)).length === 4
    && (await collectNames(logRoot)).length === 16;
  const noUnboundOrBackupFiles = backupFiles.length === 0
    && formalTopLevelExact && plansRosterExact && runnerLogsRosterExact && replayRosterExact
    && runAudits.every(row => row.rosterExact);

  const runnerChildren = operationDraft.restrictedCompileChildren ?? [];
  const runnerChildRowsExact = runnerChildren.length === 4 && (await Promise.all(runnerChildren.map(row => processRecordExact(row, repositoryRoot)))).every(Boolean);
  const auditorChildren = [...verifierChildren, ...blendChildren];
  const auditorChildRowsExact = auditorChildren.length === 8 && (await Promise.all(auditorChildren.map(row => processRecordExact(row, repositoryRoot)))).every(Boolean);
  const processPids = [...runnerChildren, ...auditorChildren].map(row => row.pid);
  const semanticCountsExact = operationDraft.runnerProcesses === 1
    && operationDraft.restrictedCompileDirectChildren === 4
    && operationDraft.nativeCompileInvocations === 4
    && operationDraft.compileReceiptBlenderIdentityProbes === 4
    && operationDraft.independentAuditorProcessesPlanned === 1
    && operationDraft.receiptVerifierDirectChildrenPlanned === 4
    && operationDraft.verifierBlenderIdentityProbesPlanned === 4
    && operationDraft.blendArtifactAuditDirectChildrenPlanned === 4;
  const nativePidBindingsExact = operationDraft.nativeCompilePidBindingsAvailable === true
    && runAudits.every(row => Number.isInteger(row.nativeChildPid));
  const directProcessAndSemanticCountsExact = operationDraft.runnerPid === process.ppid
    && runnerChildRowsExact && auditorChildRowsExact && semanticCountsExact
    && new Set(processPids).size === processPids.length
    && nativePidBindingsExact;
  const compileSource = await readFile(resolve(repositoryRoot, 'blender/compile_scene.py'), 'utf8');
  const zeroForbidden = operationDraft.blenderRenderCalls === 0
    && operationDraft.cyclesRayRenders === 0
    && operationDraft.dockerProcesses === 0
    && operationDraft.modelCalls === 0
    && operationDraft.networkCalls === 0
    && !compileSource.includes('bpy.ops.render');

  const attacks = [];
  function selfHashAttack(id, target, record, field, path, value) {
    attacks.push({ id, target, changedField: path.join('.'), rejected: !validSelfHash(mutate(record, path, value), field) });
  }
  selfHashAttack('PREFLIGHT_STATUS', `${args.preflightRoot}/preflight.json`, preflight, 'preflightHash', ['status'], 'REJECTED');
  selfHashAttack('PREFLIGHT_TOOL_HASH', `${args.preflightRoot}/preflight.json`, preflight, 'preflightHash', ['toolHashes', 'scripts/compile-build-plan.mjs'], '0'.repeat(64));
  selfHashAttack('PREFLIGHT_RECEIPT_STATUS', `${args.preflightRoot}/receipt.json`, preflightReceiptRead.record, 'receiptHash', ['status'], 'REJECTED');
  selfHashAttack('PREFLIGHT_RECEIPT_BINDING', `${args.preflightRoot}/receipt.json`, preflightReceiptRead.record, 'receiptHash', ['preflight', 'sha256'], '0'.repeat(64));
  selfHashAttack('ATTEMPT_INVOCATION', `${args.attemptRoot}/attempt.json`, attempt, 'attemptHash', ['invocation', 'outputRoot'], 'experiments/mutated');
  selfHashAttack('ADMISSION_STATUS', `${args.attemptRoot}/admission.json`, admission, 'admissionHash', ['status'], 'REJECTED');
  selfHashAttack('ADMISSION_IDENTITY', `${args.attemptRoot}/admission.json`, admission, 'admissionHash', ['evidence', 'identityHash'], '0'.repeat(64));
  selfHashAttack('ATTEMPT_RECEIPT_STATUS', `${args.attemptRoot}/receipt.json`, attemptReceipt, 'receiptHash', ['status'], 'REJECTED');
  selfHashAttack('ATTEMPT_RECEIPT_ADMISSION', `${args.attemptRoot}/receipt.json`, attemptReceipt, 'receiptHash', ['admission', 'sha256'], '0'.repeat(64));
  selfHashAttack('FORMAL_START_AUTHORIZATION', `${args.formalRoot}/formal-start.json`, formalStart, 'startHash', ['authorization', 'admissionIdentityHash'], '0'.repeat(64));
  for (const row of planAudits) {
    const mutated = mutate(row.wrapper, ['planHash'], '0'.repeat(64));
    attacks.push({ id: `PLAN_HASH_${row.benchmark}`, target: row.uri, changedField: 'planHash', rejected: mutated.planHash !== sha256Bytes(Buffer.from(canonicalJson(mutated.plan))) });
  }
  for (const row of runAudits) {
    const receiptMutated = mutate(row.receipt, ['createdAtUtc'], '2000-01-01T00:00:00.000Z');
    attacks.push({ id: `RECEIPT_${row.runId}`, target: `${row.outputUri}/compile.receipt.json`, changedField: 'createdAtUtc', rejected: !receiptSelfExact(receiptMutated) });
    const manifestMutated = mutate(row.manifest, ['structureHash'], '0'.repeat(64));
    attacks.push({ id: `MANIFEST_${row.runId}`, target: `${row.outputUri}/scene.manifest.json`, changedField: 'structureHash', rejected: !manifestBindingExact(manifestMutated, row.structureBytes, row.receipt.executionIdentity.buildPlan.planHash) });
    const verificationMutated = mutate(row.verification, ['valid'], false);
    attacks.push({ id: `VERIFIER_${row.runId}`, target: row.verificationUri, changedField: 'valid', rejected: !(verificationMutated.valid === true && verificationMutated.checks?.length === 19) });
    const blendMutated = mutate(row.blendAudit, ['scene', 'planHash'], '0'.repeat(64));
    attacks.push({ id: `BLEND_AUDIT_${row.runId}`, target: row.blendAuditUri, changedField: 'scene.planHash', rejected: !blendBindingExact(blendMutated, row.receipt.executionIdentity.buildPlan.planHash, row.structureSha256, spec) });
    const budgetMutated = mutate(row.budget, ['outcome'], 'CHILD_FAILED');
    attacks.push({ id: `BUDGET_${row.runId}`, target: `${row.outputUri}/budget.report.json`, changedField: 'outcome', rejected: budgetMutated.outcome !== 'PASS' });
  }
  selfHashAttack('OPERATION_DRAFT_COUNT', args.operationDraft, operationDraft, 'operationHash', ['nativeCompileInvocations'], 3);
  const semanticAttacksPassed = attacks.filter(row => row.rejected).length;
  const semanticAttacksExact = attacks.length >= spec.auditContract.semanticAttacksMinimum && semanticAttacksPassed === attacks.length;
  const outcomeMapping = allPass => allPass ? spec.decision.supportedVerdict : spec.decision.rejectedVerdict;
  const verdictMappingOutcomeNeutral = outcomeMapping(true) === spec.decision.supportedVerdict
    && outcomeMapping(false) === spec.decision.rejectedVerdict
    && spec.decision.supportedVerdict !== spec.decision.rejectedVerdict;

  const gates = {
    SPEC_PARENT_RUNTIME_AND_TOOL_IDENTITIES: specAndToolsExact,
    ZERO_BLENDER_PREFLIGHT_ACCEPTED_AND_PUSHED: preflightAcceptedPushed,
    RELATIVE_PATH_FORMAL_ADMISSION_ACCEPTED: relativeAdmissionAccepted,
    ATTEMPT_ADMISSION_AND_RECEIPT_SELF_HASH_EXACT: attemptAdmissionReceiptExact,
    FORMAL_ROOT_MATERIALIZED_ONLY_AFTER_ADMISSION: formalAfterAdmission,
    SCENESPEC_SUITE_22_OF_22: sceneSpecSuiteExact,
    BUILDPLAN_PAIR_CANONICAL_BYTES_EXACT: buildPlanPairExact,
    B01_B02_PLAN_HASHES_FROZEN: planHashesFrozen,
    FOUR_FRESH_RESTRICTED_COMPILES_PASS: fourCompilesPass,
    FOUR_CURRENT_COMPILE_RECEIPTS_VERIFY_19_CHECKS: fourVerifiersExact,
    B01_B02_PAIR_STRUCTURE_BYTES_EXACT: pairStructureBytesExact,
    B01_B02_STRUCTURE_HASHES_FROZEN: structureHashesFrozen,
    FOUR_BLEND_EMBEDDED_BINDINGS_EXACT: fourBlendBindingsExact,
    NO_UNBOUND_OR_BACKUP_OUTPUT_FILES: noUnboundOrBackupFiles,
    DIRECT_PROCESS_AND_SEMANTIC_OPERATION_COUNTS_EXACT: directProcessAndSemanticCountsExact,
    MODEL_NETWORK_DOCKER_AND_RENDER_ZERO: zeroForbidden,
    INDEPENDENT_AUDIT_AND_SEMANTIC_ATTACKS_MINIMUM_24: semanticAttacksExact,
    VERDICT_MAPPING_OUTCOME_NEUTRAL: verdictMappingOutcomeNeutral,
  };
  const gateNamesExact = deepExact(Object.keys(gates).sort(), [...spec.gates].sort());
  const allGatesPass = gateNamesExact && spec.gates.every(gate => gates[gate] === true);
  const expectedScientificVerdict = outcomeMapping(allGatesPass);
  const auditBody = {
    schemaVersion: 'bfs.admissionGatedNativeCompilerIndependentAudit.v0.1',
    experimentId: 'B54-E1',
    status: 'PASS',
    auditInterpretation: 'PASS means the independent auditor completed; scientific support depends on every frozen gate.',
    expectedScientificVerdict,
    gateNamesExact,
    gates,
    gatePassed: Object.values(gates).filter(Boolean).length,
    gateTotal: spec.gates.length,
    identities: {
      specSha256: await sha256File(specPath),
      preregistrationCommit: PREREGISTRATION_COMMIT,
      parentExact,
      nodeExact,
      blenderBinaryExact,
      toolRosterExact,
      toolChecks,
      configurationRosterExact,
      configurationChecks,
      preflightSelfHashExact: preflightRead.valid,
      preflightReceiptSelfHashExact: preflightReceiptRead.valid,
      attemptSelfHashExact: attemptRead.valid,
      admissionSelfHashExact: admissionRead.valid,
      attemptReceiptSelfHashExact: attemptReceiptRead.valid,
      formalStartSelfHashExact: formalStartRead.valid,
      planObservationSelfHashExact: planObservationRead.valid,
      operationDraftSelfHashExact: operationDraftRead.valid,
    },
    admissionReplay: {
      evidenceCommit: evidenceCommit.stdout.trim(),
      originCommit: origin.stdout.trim(),
      gitChildren,
      preflightAcceptedPushed,
      relativeAdmissionAccepted,
      attemptAdmissionReceiptExact,
      formalAfterAdmission,
    },
    planAudits: planAudits.map(row => omit(row, ['wrapper'])),
    runAudits: runAudits.map(row => omit(row, ['budget', 'receipt', 'verification', 'manifest', 'structureBytes', 'blendAudit'])),
    processReplay: {
      runnerPid: operationDraft.runnerPid,
      auditorPid: process.pid,
      auditorParentPid: process.ppid,
      runnerChildRowsExact,
      auditorChildRowsExact,
      semanticCountsExact,
      nativePidBindingsExact,
      nativePidEvidenceBoundary: nativePidBindingsExact ? 'OS_PID_BOUND' : 'COMMAND_EXIT_METRICS_BOUND_WITHOUT_NATIVE_PID',
      directProcessAndSemanticCountsExact,
    },
    verifierChildren,
    blendChildren,
    operationCounts: {
      auditorProcesses: 1,
      receiptVerifierDirectChildren: verifierChildren.length,
      verifierBlenderIdentityProbes: verifierChildren.length,
      blendArtifactAuditDirectChildren: blendChildren.length,
      auditorGitChildren: gitChildren.length,
      blenderRenderCalls: 0,
      cyclesRayRenders: 0,
      dockerProcesses: 0,
      modelCalls: 0,
      networkCalls: 0,
    },
    semanticAttacks: attacks,
    semanticAttackCount: attacks.length,
    semanticAttacksPassed,
    backupFiles: backupFiles.map(path => repoUri(repositoryRoot, path)),
    scientificVerdict: null,
  };
  const audit = { ...auditBody, auditHash: canonicalHash(auditBody) };
  await writeFile(outputPath, `${JSON.stringify(sortValue(audit), null, 2)}\n`, { encoding: 'utf8', flag: 'wx' });
  process.stdout.write(`BFS_B54_E1_AUDIT PASS expected=${expectedScientificVerdict} gates=${audit.gatePassed}/${audit.gateTotal} attacks=${semanticAttacksPassed}/${attacks.length}\n`);
}

main().catch(error => {
  process.stderr.write(`${error?.stack ?? error}\n`);
  process.exitCode = 1;
});
