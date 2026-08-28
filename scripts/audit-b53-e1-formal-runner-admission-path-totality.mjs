#!/opt/homebrew/Cellar/node/26.5.0/bin/node

import { createHash } from 'node:crypto';
import { spawn } from 'node:child_process';
import {
  lstat,
  readFile,
  readdir,
  readlink,
  realpath,
  writeFile,
} from 'node:fs/promises';
import { dirname, isAbsolute, relative, resolve, sep } from 'node:path';

// This auditor intentionally does not import the admission library or runner.
const SPEC_SHA256 = 'd85c450e4f927a684a630324da3ee5281b0cd57f3fcd23cdccf5d4cfe3f2b4f5';
const PREREGISTRATION_COMMIT = 'ae7e57ff86d8a5f735e5a32d3b80755edb6b8f4d';
const TOOL_PATHS = [
  'scripts/lib/formal-run-admission.mjs',
  'scripts/run-b53-e1-formal-runner-admission-path-totality.mjs',
  'scripts/audit-b53-e1-formal-runner-admission-path-totality.mjs',
];

class IndependentAdmissionError extends Error {
  constructor(reason, message) {
    super(message);
    this.reason = reason;
  }
}

function parseArguments(argv) {
  const parsed = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--spec') parsed.spec = argv[++index];
    else if (token === '--formal-root') parsed.formalRoot = argv[++index];
    else if (token === '--fixture-root') parsed.fixtureRoot = argv[++index];
    else if (token === '--execution') parsed.execution = argv[++index];
    else if (token === '--operation-draft') parsed.operationDraft = argv[++index];
    else if (token === '--output') parsed.output = argv[++index];
    else throw new Error(`Unknown or incomplete argument: ${token}`);
  }
  for (const required of ['spec', 'formalRoot', 'fixtureRoot', 'execution', 'operationDraft', 'output']) {
    if (!parsed[required]) throw new Error(`Missing --${required.replace(/[A-Z]/g, letter => `-${letter.toLowerCase()}`)}`);
  }
  return parsed;
}

function sortValue(value) {
  if (Array.isArray(value)) return value.map(sortValue);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.keys(value).sort().map(key => [key, sortValue(value[key])]));
  }
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

async function pathState(path) {
  try {
    return await lstat(path);
  } catch (error) {
    if (error?.code === 'ENOENT') return null;
    throw error;
  }
}

async function fingerprint(path) {
  const state = await pathState(path);
  if (!state) return { kind: 'MISSING' };
  if (state.isSymbolicLink()) return { kind: 'SYMLINK', target: await readlink(path) };
  if (state.isDirectory()) return { kind: 'DIRECTORY' };
  if (state.isFile()) return { kind: 'FILE', sha256: await sha256File(path), size: state.size };
  return { kind: 'OTHER', mode: state.mode };
}

function below(root, candidate) {
  const pathFromRoot = relative(root, candidate);
  return pathFromRoot !== '' && pathFromRoot !== '..' && !pathFromRoot.startsWith(`..${sep}`) && !isAbsolute(pathFromRoot);
}

async function runGit(args, cwd, rows, phase) {
  const started = process.hrtime.bigint();
  const child = spawn('/usr/bin/git', args, {
    cwd,
    env: { PATH: '/usr/bin:/bin', LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8', GIT_CONFIG_NOSYSTEM: '1', GIT_TERMINAL_PROMPT: '0', GIT_ALLOW_PROTOCOL: 'file' },
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
  const result = {
    phase,
    args,
    pid: child.pid,
    exitCode,
    stdout: Buffer.concat(stdout).toString('utf8'),
    stderr: Buffer.concat(stderr).toString('utf8'),
    elapsedNanoseconds: Number(process.hrtime.bigint() - started),
  };
  rows.push(result);
  return result;
}

async function gitRequired(args, cwd, rows, phase, reason) {
  const result = await runGit(args, cwd, rows, phase);
  if (result.exitCode !== 0) throw new IndependentAdmissionError(reason, result.stderr.trim());
  return result.stdout.trim();
}

async function independentAdmission({ repositoryRoot, evidenceInput, formalOutput, originRef }, gitRows, phasePrefix) {
  const repositoryLexical = resolve(repositoryRoot);
  const repositoryActual = await realpath(repositoryLexical);
  if (repositoryLexical !== repositoryActual) throw new IndependentAdmissionError('REPOSITORY_SYMLINK_ALIAS', 'Repository symlink alias');

  const evidenceAbsolute = resolve(repositoryLexical, evidenceInput);
  if (!below(repositoryLexical, evidenceAbsolute)) throw new IndependentAdmissionError('EVIDENCE_OUTSIDE_REPOSITORY', 'Evidence outside repository');
  const evidenceState = await pathState(evidenceAbsolute);
  if (!evidenceState) throw new IndependentAdmissionError('EVIDENCE_MISSING', 'Evidence missing');
  if (evidenceState.isSymbolicLink()) throw new IndependentAdmissionError('EVIDENCE_SYMLINK_ALIAS', 'Evidence target symbolic link');
  const evidenceActual = await realpath(evidenceAbsolute);
  if (evidenceActual !== evidenceAbsolute) throw new IndependentAdmissionError('EVIDENCE_SYMLINK_ALIAS', 'Evidence traverses symbolic link');
  if (!below(repositoryActual, evidenceActual)) throw new IndependentAdmissionError('EVIDENCE_OUTSIDE_REPOSITORY', 'Evidence realpath escape');
  if (!evidenceState.isDirectory()) throw new IndependentAdmissionError('EVIDENCE_NOT_DIRECTORY', 'Evidence not directory');
  const evidenceRelative = relative(repositoryLexical, evidenceAbsolute).split(sep).join('/');

  const tracked = await runGit(['ls-files', '-z', '--', evidenceRelative], repositoryLexical, gitRows, `${phasePrefix}_TRACKED`);
  const dirty = await runGit(['status', '--porcelain=v1', '--untracked-files=all', '--', evidenceRelative], repositoryLexical, gitRows, `${phasePrefix}_CLEAN`);
  if (tracked.exitCode !== 0 || tracked.stdout.length === 0 || dirty.exitCode !== 0 || dirty.stdout.length !== 0) {
    throw new IndependentAdmissionError('EVIDENCE_NOT_TRACKED_CLEAN', 'Evidence not tracked clean');
  }
  const evidenceCommit = await gitRequired(['log', '-1', '--format=%H', '--', evidenceRelative], repositoryLexical, gitRows, `${phasePrefix}_EVIDENCE_COMMIT`, 'EVIDENCE_NOT_TRACKED_CLEAN');
  const origin = await runGit(['rev-parse', '--verify', originRef], repositoryLexical, gitRows, `${phasePrefix}_ORIGIN`);
  if (origin.exitCode !== 0) throw new IndependentAdmissionError('ORIGIN_BRANCH_MISSING', 'Origin branch missing');
  const ancestor = await runGit(['merge-base', '--is-ancestor', evidenceCommit, originRef], repositoryLexical, gitRows, `${phasePrefix}_ANCESTRY`);
  if (ancestor.exitCode !== 0) throw new IndependentAdmissionError('EVIDENCE_COMMIT_NOT_PUSHED', 'Evidence commit not pushed');

  const preflightPath = resolve(evidenceAbsolute, 'preflight.json');
  const preflightState = await pathState(preflightPath);
  if (!preflightState?.isFile()) throw new IndependentAdmissionError('PREFLIGHT_SELF_HASH', 'Preflight missing');
  const preflight = JSON.parse(await readFile(preflightPath, 'utf8'));
  if (!validSelfHash(preflight, 'preflightHash')) throw new IndependentAdmissionError('PREFLIGHT_SELF_HASH', 'Preflight self-hash mismatch');
  if (preflight.status !== 'ACCEPTED') throw new IndependentAdmissionError('PREFLIGHT_STATUS', 'Preflight status mismatch');
  const toolHashes = {};
  for (const [uri, expected] of Object.entries(preflight.toolHashes ?? {}).sort(([left], [right]) => left.localeCompare(right))) {
    const path = resolve(repositoryLexical, uri);
    if (!below(repositoryLexical, path) || !await pathState(path)) throw new IndependentAdmissionError('TOOL_HASH', 'Tool missing/outside');
    const observed = await sha256File(path);
    toolHashes[uri] = observed;
    if (observed !== expected) throw new IndependentAdmissionError('TOOL_HASH', 'Tool mismatch');
  }
  if (Object.keys(toolHashes).length === 0) throw new IndependentAdmissionError('TOOL_HASH', 'No tool hashes');

  const outputAbsolute = resolve(repositoryLexical, formalOutput);
  if (!below(repositoryLexical, outputAbsolute)) throw new IndependentAdmissionError('OUTPUT_OUTSIDE_REPOSITORY', 'Output outside repository');
  const targetState = await pathState(outputAbsolute);
  if (targetState?.isSymbolicLink()) throw new IndependentAdmissionError('OUTPUT_SYMLINK_ALIAS', 'Output target symbolic link');
  if (targetState) throw new IndependentAdmissionError('OUTPUT_EXISTS', 'Output exists');
  let ancestorPath = dirname(outputAbsolute);
  let ancestorState = await pathState(ancestorPath);
  while (!ancestorState) {
    const parent = dirname(ancestorPath);
    if (parent === ancestorPath) throw new IndependentAdmissionError('OUTPUT_OUTSIDE_REPOSITORY', 'No contained output ancestor');
    ancestorPath = parent;
    ancestorState = await pathState(ancestorPath);
  }
  if (ancestorState.isSymbolicLink()) throw new IndependentAdmissionError('OUTPUT_SYMLINK_ALIAS', 'Output ancestor symbolic link');
  const ancestorActual = await realpath(ancestorPath);
  if (ancestorPath !== ancestorActual) throw new IndependentAdmissionError('OUTPUT_SYMLINK_ALIAS', 'Output ancestor traverses symbolic link');
  if (!below(repositoryActual, ancestorActual)) throw new IndependentAdmissionError('OUTPUT_OUTSIDE_REPOSITORY', 'Output ancestor escape');

  const evidenceIdentityBody = {
    repositoryRelative: evidenceRelative,
    evidenceCommit,
    originRef,
    originCommit: origin.stdout.trim(),
    preflight: {
      uri: `${evidenceRelative}/preflight.json`,
      sha256: await sha256File(preflightPath),
      preflightHash: preflight.preflightHash,
    },
    toolHashes,
  };
  return {
    status: 'ACCEPTED',
    evidence: { ...evidenceIdentityBody, identityHash: canonicalHash(evidenceIdentityBody) },
    output: {
      repositoryRelative: relative(repositoryLexical, outputAbsolute).split(sep).join('/'),
      parentRepositoryRelative: relative(repositoryLexical, dirname(outputAbsolute)).split(sep).join('/'),
      fresh: true,
    },
  };
}

async function readHashed(path, field) {
  const record = JSON.parse(await readFile(path, 'utf8'));
  return { record, valid: validSelfHash(record, field), sha256: await sha256File(path) };
}

function mutateOneField(record, field, value) {
  const copy = structuredClone(record);
  copy[field] = value;
  return copy;
}

async function main() {
  const args = parseArguments(process.argv.slice(2));
  const specPath = resolve(args.spec);
  const formalRoot = await realpath(resolve(args.formalRoot));
  const fixtureRoot = await realpath(resolve(args.fixtureRoot));
  const outputPath = resolve(args.output);
  if (!below(formalRoot, outputPath)) throw new Error('Audit output must be strictly below formal root');
  if (await pathState(outputPath)) throw new Error('Audit output already exists');
  const repository = await realpath(resolve(dirname(specPath), '..'));
  const specShaExact = await sha256File(specPath) === SPEC_SHA256;
  const spec = JSON.parse(await readFile(specPath, 'utf8'));
  const startPath = resolve(formalRoot, 'formal-start.json');
  const fixturePath = resolve(formalRoot, 'fixture.json');
  const startRead = await readHashed(startPath, 'startHash');
  const fixtureRead = await readHashed(fixturePath, 'fixtureHash');
  const executionRead = await readHashed(resolve(args.execution), 'executionHash');
  const operationRead = await readHashed(resolve(args.operationDraft), 'operationHash');
  const fixture = fixtureRead.record;
  const start = startRead.record;
  const execution = executionRead.record;
  const operation = operationRead.record;
  const auditorGitChildren = [];

  const fixtureRootExact = fixture.temporaryRoot === fixtureRoot && await realpath(fixture.temporaryRoot) === fixtureRoot;
  const originActual = await realpath(fixture.originPath);
  const originBelowFixture = below(fixtureRoot, originActual);
  const bare = await runGit(['rev-parse', '--is-bare-repository'], originActual, auditorGitChildren, 'AUDIT_ORIGIN_BARE');
  const originBareExact = bare.exitCode === 0 && bare.stdout.trim() === 'true';
  const originHead = await runGit(['rev-parse', 'refs/heads/main'], originActual, auditorGitChildren, 'AUDIT_ORIGIN_MAIN');
  const baselineExact = originHead.exitCode === 0 && originHead.stdout.trim() === fixture.baselineCommit;

  const head = await runGit(['rev-parse', 'HEAD'], repository, auditorGitChildren, 'AUDIT_MAIN_HEAD');
  const originMain = await runGit(['rev-parse', '--verify', 'origin/main'], repository, auditorGitChildren, 'AUDIT_MAIN_ORIGIN');
  const preregAncestor = await runGit(['merge-base', '--is-ancestor', PREREGISTRATION_COMMIT, execution.toolFreezeCommit], repository, auditorGitChildren, 'AUDIT_PREREG_ANCESTRY');
  const toolChecks = [];
  for (const uri of TOOL_PATHS) {
    const observed = await sha256File(resolve(repository, uri));
    toolChecks.push({ uri, expected: execution.toolHashes?.[uri] ?? null, observed, exact: observed === execution.toolHashes?.[uri] });
  }
  const scopedStatus = await runGit(['status', '--porcelain=v1', '--untracked-files=all', '--', 'specs/formal-runner-admission-path-totality.v0.1.json', ...TOOL_PATHS], repository, auditorGitChildren, 'AUDIT_MAIN_CLEAN');
  const identitiesExact = specShaExact
    && spec.experimentId === 'B53-E1'
    && executionRead.valid
    && startRead.valid
    && fixtureRead.valid
    && operationRead.valid
    && execution.formalStart?.sha256 === startRead.sha256
    && execution.formalStart?.startHash === start.startHash
    && execution.fixture?.sha256 === fixtureRead.sha256
    && execution.fixture?.fixtureHash === fixture.fixtureHash
    && execution.operationDraft?.sha256 === operationRead.sha256
    && execution.operationDraft?.operationHash === operation.operationHash
    && start.preregistrationCommit === PREREGISTRATION_COMMIT
    && start.toolFreezeCommit === execution.toolFreezeCommit
    && start.runnerPid === operation.runnerPid
    && deepExact(start.toolHashes, execution.toolHashes)
    && execution.preregistrationCommit === PREREGISTRATION_COMMIT
    && head.exitCode === 0
    && originMain.exitCode === 0
    && head.stdout.trim() === execution.toolFreezeCommit
    && originMain.stdout.trim() === execution.toolFreezeCommit
    && preregAncestor.exitCode === 0
    && scopedStatus.exitCode === 0
    && scopedStatus.stdout === ''
    && toolChecks.length === TOOL_PATHS.length
    && toolChecks.every(row => row.exact);

  const expectedCases = new Map([
    ...spec.positiveCases.map(row => [row.id, { outcome: 'ACCEPT', reason: null }]),
    ...spec.negativeCases.map(row => [row.id, { outcome: 'REJECT', reason: row.expectedReason }]),
  ]);
  const caseAudits = [];
  const receiptsForAttacks = [];
  const failuresForAttacks = [];
  const admissionsForAttacks = [];
  for (const [caseId, expected] of expectedCases) {
    const caseRoot = resolve(formalRoot, 'cases', caseId);
    const attemptRead = await readHashed(resolve(caseRoot, 'attempt.json'), 'attemptHash');
    const receiptRead = await readHashed(resolve(caseRoot, 'receipt.json'), 'receiptHash');
    const attempt = attemptRead.record;
    const receipt = receiptRead.record;
    const evidenceName = receipt.evidence?.kind === 'admission' ? 'admission.json' : 'failure.json';
    const evidenceField = receipt.evidence?.kind === 'admission' ? 'admissionHash' : 'failureHash';
    const evidenceRead = await readHashed(resolve(caseRoot, evidenceName), evidenceField);
    const directoryEntries = (await readdir(caseRoot)).sort();
    const expectedEntries = ['attempt.json', evidenceName, 'receipt.json'].sort();
    const repositoryRoot = await realpath(attempt.repositoryRoot);
    const repositoryMatchesManifest = fixture.repositories?.[caseId] === repositoryRoot && below(fixtureRoot, repositoryRoot);
    const remote = await runGit(['remote', 'get-url', 'origin'], repositoryRoot, auditorGitChildren, `AUDIT_REMOTE_${caseId}`);
    let remoteExact = false;
    if (remote.exitCode === 0) {
      try { remoteExact = await realpath(remote.stdout.trim()) === originActual; } catch { remoteExact = false; }
    }
    let replayOutcome = 'ACCEPT';
    let replayReason = null;
    let replayAdmission = null;
    try {
      replayAdmission = await independentAdmission({
        repositoryRoot,
        evidenceInput: attempt.evidenceInput,
        formalOutput: attempt.formalOutput,
        originRef: attempt.originRef,
      }, auditorGitChildren, `AUDIT_CASE_${caseId}`);
    } catch (error) {
      if (!(error instanceof IndependentAdmissionError)) throw error;
      replayOutcome = 'REJECT';
      replayReason = error.reason;
    }
    const outputAbsolute = resolve(repositoryRoot, attempt.formalOutput);
    const actualOutput = await fingerprint(outputAbsolute);
    const evidenceRecord = evidenceRead.record;
    const executionRow = execution.cases?.find(row => row.caseId === caseId);
    const expectedExecutionRow = {
      caseId,
      outcome: receipt.outcome,
      reason: receipt.reason,
      attemptHash: attempt.attemptHash,
      evidenceSelfHash: evidenceRecord[evidenceField],
      receiptHash: receipt.receiptHash,
      outputBefore: evidenceRecord.outputBefore,
      outputAfter: evidenceRecord.outputAfter,
    };
    const executionRowExact = deepExact(executionRow, expectedExecutionRow);
    const bindingExact = attemptRead.valid
      && receiptRead.valid
      && evidenceRead.valid
      && receipt.attempt?.sha256 === attemptRead.sha256
      && receipt.attempt?.attemptHash === attempt.attemptHash
      && receipt.evidence?.sha256 === evidenceRead.sha256
      && receipt.evidence?.selfHash === evidenceRecord[evidenceField]
      && receipt.caseId === caseId
      && attempt.caseId === caseId
      && evidenceRecord.caseId === caseId
      && receipt.scientificVerdict === null
      && evidenceRecord.scientificVerdict === null
      && attempt.scientificVerdict === null
      && deepExact(directoryEntries, expectedEntries);
    const expectedExact = receipt.outcome === expected.outcome
      && receipt.reason === expected.reason
      && replayOutcome === expected.outcome
      && replayReason === expected.reason;
    const replayExact = replayOutcome === 'ACCEPT'
      ? evidenceRecord.status === 'ACCEPTED' && deepExact(evidenceRecord.admission, replayAdmission)
      : evidenceRecord.status === 'REJECTED' && evidenceRecord.reason === replayReason;
    const outputUnchanged = deepExact(evidenceRecord.outputBefore, evidenceRecord.outputAfter)
      && deepExact(evidenceRecord.outputAfter, actualOutput);
    const shouldBePreExisting = ['N11_OUTPUT_SYMLINK_ALIAS', 'N12_OUTPUT_EXISTS_DIRECTORY', 'N13_OUTPUT_EXISTS_FILE'].includes(caseId);
    const declaredOutputCreationAbsent = shouldBePreExisting ? actualOutput.kind !== 'MISSING' && outputUnchanged : actualOutput.kind === 'MISSING' && outputUnchanged;
    caseAudits.push({
      caseId,
      expected,
      observed: { outcome: receipt.outcome, reason: receipt.reason },
      replay: { outcome: replayOutcome, reason: replayReason },
      bindingExact,
      expectedExact,
      replayExact,
      executionRowExact,
      repositoryMatchesManifest,
      remoteExact,
      outputUnchanged,
      declaredOutputCreationAbsent,
      outputFingerprint: actualOutput,
      evidenceIdentity: replayAdmission?.evidence ?? null,
      outputIdentity: replayAdmission?.output ?? null,
    });
    receiptsForAttacks.push({ caseId, record: receipt });
    if (evidenceField === 'failureHash') failuresForAttacks.push({ caseId, record: evidenceRecord });
    else admissionsForAttacks.push({ caseId, record: evidenceRecord });
  }

  const positiveRows = caseAudits.filter(row => row.expected.outcome === 'ACCEPT');
  const negativeRows = caseAudits.filter(row => row.expected.outcome === 'REJECT');
  const positiveAccept = positiveRows.length === 3 && positiveRows.every(row => row.expectedExact && row.bindingExact && row.replayExact);
  const positiveEvidenceExact = positiveAccept
    && positiveRows.every(row => deepExact(row.evidenceIdentity, positiveRows[0].evidenceIdentity));
  const fixtureBaselineBindingsExact = positiveEvidenceExact
    && positiveRows.every(row => row.evidenceIdentity?.evidenceCommit === fixture.baselineCommit
      && row.evidenceIdentity?.originCommit === fixture.baselineCommit
      && row.evidenceIdentity?.preflight?.sha256 === fixture.preflightSha256
      && row.evidenceIdentity?.preflight?.preflightHash === fixture.preflightHash
      && row.evidenceIdentity?.toolHashes?.['tools/admission-tool.mjs'] === fixture.fixtureToolSha256);
  const positiveOutputParentExact = positiveAccept
    && positiveRows.every(row => row.outputIdentity?.parentRepositoryRelative === 'fixture' && row.outputIdentity?.fresh === true)
    && new Set(positiveRows.map(row => row.outputIdentity?.repositoryRelative)).size === 3;
  const negativesExact = negativeRows.length === 14 && negativeRows.every(row => row.expectedExact && row.replayExact);
  const everyReceipt = caseAudits.length === 17 && caseAudits.every(row => row.bindingExact);
  const everyFailureSelfHashed = failuresForAttacks.length === 14 && negativeRows.every(row => row.bindingExact);
  const noDeclaredOutputCreated = caseAudits.every(row => row.declaredOutputCreationAbsent);
  const noSymlinkOrOutsideWrite = caseAudits.every(row => row.outputUnchanged)
    && caseAudits.find(row => row.caseId === 'N10_OUTPUT_OUTSIDE_REPOSITORY')?.outputFingerprint.kind === 'MISSING'
    && caseAudits.find(row => row.caseId === 'N11_OUTPUT_SYMLINK_ALIAS')?.outputFingerprint.kind === 'SYMLINK';
  const localBareOriginOnly = fixtureRootExact
    && originBelowFixture
    && originBareExact
    && baselineExact
    && fixture.transport === 'LOCAL_FILE_PROTOCOL_BARE_ORIGIN_ONLY'
    && fixture.externalRepositories === 0
    && fixture.networkCalls === 0
    && fixtureBaselineBindingsExact
    && caseAudits.every(row => row.repositoryMatchesManifest && row.remoteExact);

  const runnerGitRowsWellFormed = Array.isArray(operation.gitChildProcesses)
    && operation.gitChildProcesses.length === operation.gitChildProcessCount
    && operation.gitChildProcesses.every(row => Array.isArray(row.args)
      && Number.isInteger(row.pid)
      && Number.isInteger(row.exitCode)
      && typeof row.stdout === 'string'
      && typeof row.stderr === 'string'
      && Number.isFinite(row.elapsedNanoseconds)
      && row.elapsedNanoseconds >= 0);
  const auditorGitRowsWellFormed = auditorGitChildren.every(row => Array.isArray(row.args)
    && Number.isInteger(row.pid)
    && Number.isInteger(row.exitCode)
    && typeof row.stdout === 'string'
    && typeof row.stderr === 'string'
    && Number.isFinite(row.elapsedNanoseconds)
    && row.elapsedNanoseconds >= 0);
  const allGitPids = [...operation.gitChildProcesses.map(row => row.pid), ...auditorGitChildren.map(row => row.pid)];
  const processRosterExact = operation.runnerProcesses === 1
    && operation.auditorProcessesPlanned === 1
    && operation.caseEvaluations === 17
    && Number.isInteger(operation.runnerPid)
    && operation.runnerPid === process.ppid
    && process.pid !== operation.runnerPid
    && runnerGitRowsWellFormed
    && auditorGitRowsWellFormed
    && new Set(allGitPids).size === allGitPids.length;
  const zeroCounts = ['blenderProcesses', 'blenderRenderCalls', 'cyclesRayRenders', 'dockerProcesses', 'modelCalls', 'networkCalls']
    .every(field => operation[field] === 0)
    && Object.values(execution.prohibitedOperationCounts ?? {}).every(value => value === 0)
    && Object.values(start.prohibitedOperationCounts ?? {}).every(value => value === 0);

  const attacks = [];
  for (const { caseId, record } of receiptsForAttacks) {
    const mutated = mutateOneField(record, 'outcome', record.outcome === 'ACCEPT' ? 'REJECT' : 'ACCEPT');
    attacks.push({ id: `RECEIPT_OUTCOME_${caseId}`, target: `cases/${caseId}/receipt.json`, changedField: 'outcome', rejected: !validSelfHash(mutated, 'receiptHash') });
  }
  for (const { caseId, record } of failuresForAttacks) {
    const mutated = mutateOneField(record, 'reason', `${record.reason}_MUTATED`);
    attacks.push({ id: `FAILURE_REASON_${caseId}`, target: `cases/${caseId}/failure.json`, changedField: 'reason', rejected: !validSelfHash(mutated, 'failureHash') });
  }
  for (const { caseId, record } of admissionsForAttacks) {
    const mutated = mutateOneField(record, 'status', 'REJECTED');
    attacks.push({ id: `ADMISSION_STATUS_${caseId}`, target: `cases/${caseId}/admission.json`, changedField: 'status', rejected: !validSelfHash(mutated, 'admissionHash') });
  }
  const semanticAttacksPassed = attacks.filter(row => row.rejected).length;
  const semanticAttacksExact = attacks.length >= 32 && semanticAttacksPassed === attacks.length;
  const auditReplayExact = execution.cases?.length === 17
    && deepExact(execution.cases.map(row => row.caseId), [...expectedCases.keys()])
    && caseAudits.every(row => row.bindingExact && row.expectedExact && row.replayExact && row.executionRowExact)
    && startRead.valid
    && fixtureRead.valid
    && executionRead.valid
    && operationRead.valid;

  const gates = {
    SPEC_AND_TOOL_IDENTITIES: identitiesExact,
    THREE_POSITIVES_ACCEPT: positiveAccept,
    POSITIVE_EVIDENCE_CANONICAL_IDENTITY_EXACT: positiveEvidenceExact,
    POSITIVE_OUTPUT_PARENT_IDENTITY_EXACT: positiveOutputParentExact,
    FOURTEEN_NEGATIVES_REJECT_WITH_EXACT_REASON: negativesExact,
    EVERY_CASE_WRITES_ONE_RECEIPT: everyReceipt,
    EVERY_REJECTION_WRITES_SELF_HASHED_FAILURE: everyFailureSelfHashed,
    NO_CASE_CREATES_DECLARED_FORMAL_OUTPUT: noDeclaredOutputCreated,
    NO_SYMLINK_OR_OUTSIDE_WRITE: Boolean(noSymlinkOrOutsideWrite),
    LOCAL_BARE_ORIGIN_ONLY: localBareOriginOnly,
    PROCESS_ROSTER_EXACT: processRosterExact,
    MODEL_NETWORK_BLENDER_RENDER_ZERO: zeroCounts,
    AUDIT_REPLAY_EXACT: auditReplayExact,
    SEMANTIC_ATTACKS_MINIMUM_32: semanticAttacksExact,
  };
  const gateNamesExact = deepExact(Object.keys(gates).sort(), [...spec.gates].sort());
  const allGatesPass = gateNamesExact && spec.gates.every(gate => gates[gate] === true);
  const expectedScientificVerdict = allGatesPass ? spec.decision.supportedVerdict : spec.decision.rejectedVerdict;
  const auditBody = {
    schemaVersion: 'bfs.formalRunnerAdmissionPathTotalityAudit.v0.1',
    experimentId: 'B53-E1',
    status: 'PASS',
    auditInterpretation: 'PASS means the independent audit completed; scientific support depends on all frozen gates.',
    expectedScientificVerdict,
    gateNamesExact,
    gates,
    gatePassed: Object.values(gates).filter(Boolean).length,
    gateTotal: spec.gates.length,
    caseAudits,
    semanticAttacks: attacks,
    semanticAttackCount: attacks.length,
    semanticAttacksPassed,
    identities: {
      specSha256: await sha256File(specPath),
      specShaExact,
      preregistrationCommit: PREREGISTRATION_COMMIT,
      toolFreezeCommit: execution.toolFreezeCommit,
      toolChecks,
      formalStartSelfHashExact: startRead.valid,
      fixtureSelfHashExact: fixtureRead.valid,
      executionSelfHashExact: executionRead.valid,
      operationSelfHashExact: operationRead.valid,
    },
    fixtureReplay: {
      fixtureRootExact,
      originBelowFixture,
      originBareExact,
      baselineExact,
      fixtureBaselineBindingsExact,
      localBareOriginOnly,
    },
    processReplay: {
      runnerPid: operation.runnerPid,
      auditorPid: process.pid,
      auditorParentPid: process.ppid,
      runnerGitChildProcessCount: operation.gitChildProcessCount,
      auditorGitChildProcessCount: auditorGitChildren.length,
      runnerGitRowsWellFormed,
      auditorGitRowsWellFormed,
      processRosterExact,
      prohibitedCountsExact: zeroCounts,
    },
    auditorGitChildren,
    auditorGitChildProcessCount: auditorGitChildren.length,
    scientificVerdict: null,
  };
  const audit = { ...auditBody, auditHash: canonicalHash(auditBody) };
  await writeFile(outputPath, `${JSON.stringify(sortValue(audit), null, 2)}\n`, { encoding: 'utf8', flag: 'wx' });
  process.stdout.write(`BFS_B53_E1_AUDIT PASS expected=${expectedScientificVerdict} gates=${audit.gatePassed}/${audit.gateTotal} attacks=${semanticAttacksPassed}/${attacks.length}\n`);
}

main().catch(error => {
  process.stderr.write(`${error?.stack ?? error}\n`);
  process.exitCode = 1;
});
