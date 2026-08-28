#!/opt/homebrew/Cellar/node/26.5.0/bin/node

import { spawn } from 'node:child_process';
import {
  lstat,
  mkdir,
  mkdtemp,
  readFile,
  readlink,
  realpath,
  rm,
  symlink,
  writeFile,
} from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, join, relative, resolve, sep } from 'node:path';
import {
  AdmissionError,
  admitFormalRun,
  canonicalHash,
  runGit,
  sha256File,
  sortValue,
} from './lib/formal-run-admission.mjs';

const SPEC_SHA256 = 'd85c450e4f927a684a630324da3ee5281b0cd57f3fcd23cdccf5d4cfe3f2b4f5';
const PREREGISTRATION_COMMIT = 'ae7e57ff86d8a5f735e5a32d3b80755edb6b8f4d';
const NODE_SHA256 = '70851490e028b3d699a8d6d4e1de909af2a989359ae807974c92af9c6580a8e8';
const NODE_EXECUTABLE = '/opt/homebrew/Cellar/node/26.5.0/bin/node';
const TOOL_PATHS = [
  'scripts/lib/formal-run-admission.mjs',
  'scripts/run-b53-e1-formal-runner-admission-path-totality.mjs',
  'scripts/audit-b53-e1-formal-runner-admission-path-totality.mjs',
];

function parseArguments(argv) {
  const parsed = { developmentProbe: false, developmentMatrixProbe: false };
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--development-probe') parsed.developmentProbe = true;
    else if (token === '--development-matrix-probe') parsed.developmentMatrixProbe = true;
    else if (token === '--spec') parsed.spec = argv[++index];
    else if (token === '--output-root') parsed.outputRoot = argv[++index];
    else if (token === '--tool-freeze-commit') parsed.toolFreezeCommit = argv[++index];
    else throw new Error(`Unknown or incomplete argument: ${token}`);
  }
  return parsed;
}

async function writeJson(path, value) {
  await writeFile(path, `${JSON.stringify(sortValue(value), null, 2)}\n`, { encoding: 'utf8', flag: 'wx' });
}

async function writeHashedJson(path, body, hashField) {
  const record = { ...body, [hashField]: canonicalHash(body) };
  await writeJson(path, record);
  return record;
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

function strictlyBelow(root, candidate) {
  const pathFromRoot = relative(root, candidate);
  return pathFromRoot !== '' && pathFromRoot !== '..' && !pathFromRoot.startsWith(`..${sep}`);
}

async function safeRemoveOwnedTemp(path) {
  const expectedParent = await realpath(tmpdir());
  const state = await pathState(path);
  const actualPath = state ? await realpath(path) : null;
  if (!actualPath
    || dirname(actualPath) !== expectedParent
    || !strictlyBelow(expectedParent, actualPath)
    || !state?.isDirectory()
    || !actualPath.split(sep).at(-1).startsWith('bfs-b53-e1-')) {
    throw new Error(`Refusing to remove non-owned temporary path: ${path}`);
  }
  await rm(actualPath, { recursive: true, force: false });
}

async function gitChecked(args, cwd, observer, phase) {
  let observed;
  const result = await runGit(args, cwd, row => {
    observed = { phase, ...row };
    observer(observed);
  });
  if (result.exitCode !== 0) {
    throw new Error(`Git failed during ${phase}: git ${args.join(' ')}\n${result.stderr}`);
  }
  return result.stdout.trim();
}

async function configureIdentity(repository, observer, phase) {
  await gitChecked(['config', 'user.name', 'BFS B53-E1 Fixture'], repository, observer, phase);
  await gitChecked(['config', 'user.email', 'b53-e1@invalid.local'], repository, observer, phase);
}

async function createFixtureBase(temporaryRoot, observer) {
  const originPath = join(temporaryRoot, 'origin.git');
  const seedPath = join(temporaryRoot, 'seed');
  await gitChecked(['init', '--bare', '--initial-branch=main', originPath], temporaryRoot, observer, 'FIXTURE_INIT_BARE');
  await mkdir(seedPath);
  await gitChecked(['init', '--initial-branch=main'], seedPath, observer, 'FIXTURE_INIT_SEED');
  await configureIdentity(seedPath, observer, 'FIXTURE_CONFIG_SEED');
  await mkdir(join(seedPath, 'tools'), { recursive: true });
  await mkdir(join(seedPath, 'fixture', 'evidence'), { recursive: true });
  const fixtureToolPath = join(seedPath, 'tools', 'admission-tool.mjs');
  await writeFile(fixtureToolPath, "export const fixtureTool = 'B53-E1';\n", { encoding: 'utf8', flag: 'wx' });
  const toolSha256 = await sha256File(fixtureToolPath);
  const preflightBody = {
    schemaVersion: 'bfs.formalRunnerAdmissionFixturePreflight.v0.1',
    experimentId: 'B53-E1',
    status: 'ACCEPTED',
    toolHashes: { 'tools/admission-tool.mjs': toolSha256 },
  };
  const preflight = await writeHashedJson(join(seedPath, 'fixture', 'evidence', 'preflight.json'), preflightBody, 'preflightHash');
  await gitChecked(['add', '--', 'tools/admission-tool.mjs', 'fixture/evidence/preflight.json'], seedPath, observer, 'FIXTURE_SEED_ADD');
  await gitChecked(['commit', '-m', 'fixture: seed accepted evidence'], seedPath, observer, 'FIXTURE_SEED_COMMIT');
  await gitChecked(['remote', 'add', 'origin', originPath], seedPath, observer, 'FIXTURE_SEED_REMOTE');
  await gitChecked(['push', '-u', 'origin', 'main'], seedPath, observer, 'FIXTURE_SEED_PUSH');
  const baselineCommit = await gitChecked(['rev-parse', 'HEAD'], seedPath, observer, 'FIXTURE_SEED_HEAD');
  return {
    originPath,
    seedPath,
    baselineCommit,
    fixtureToolSha256: toolSha256,
    preflightHash: preflight.preflightHash,
    preflightSha256: await sha256File(join(seedPath, 'fixture', 'evidence', 'preflight.json')),
  };
}

async function cloneCase(base, caseId, temporaryRoot, observer) {
  const repository = join(temporaryRoot, 'case-repositories', caseId);
  await mkdir(dirname(repository), { recursive: true });
  await gitChecked(['-c', 'protocol.file.allow=always', 'clone', '--no-local', base.originPath, repository], temporaryRoot, observer, `CLONE_${caseId}`);
  await configureIdentity(repository, observer, `CONFIG_${caseId}`);
  return repository;
}

async function commitAndPushCase(repository, caseId, observer, message) {
  const branch = `case-${caseId.toLowerCase().replaceAll('_', '-')}`;
  await gitChecked(['checkout', '-b', branch], repository, observer, `BRANCH_${caseId}`);
  await gitChecked(['add', '--all'], repository, observer, `ADD_${caseId}`);
  await gitChecked(['commit', '-m', message], repository, observer, `COMMIT_${caseId}`);
  await gitChecked(['push', '-u', 'origin', branch], repository, observer, `PUSH_${caseId}`);
  return `origin/${branch}`;
}

async function rewritePreflight(repository, mutate) {
  const path = join(repository, 'fixture', 'evidence', 'preflight.json');
  const current = JSON.parse(await readFile(path, 'utf8'));
  const next = mutate(structuredClone(current));
  await writeFile(path, `${JSON.stringify(sortValue(next), null, 2)}\n`, 'utf8');
}

async function prepareCase(caseDefinition, repository, temporaryRoot, observer) {
  const evidencePath = join(repository, 'fixture', 'evidence');
  const ordinaryOutput = join(repository, 'fixture', 'formal-negative');
  const prepared = {
    evidenceInput: 'fixture/evidence',
    formalOutput: 'fixture/formal-negative',
    originRef: 'origin/main',
  };

  switch (caseDefinition.id) {
    case 'P01_RELATIVE':
      prepared.evidenceInput = 'fixture/evidence';
      prepared.formalOutput = 'fixture/formal-relative';
      break;
    case 'P02_DOT_SEGMENTS':
      prepared.evidenceInput = 'fixture/./scratch/../evidence';
      prepared.formalOutput = 'fixture/./scratch/../formal-dot';
      break;
    case 'P03_ABSOLUTE':
      prepared.evidenceInput = evidencePath;
      prepared.formalOutput = join(repository, 'fixture', 'formal-absolute');
      break;
    case 'N01_EVIDENCE_OUTSIDE_REPOSITORY': {
      const outside = join(temporaryRoot, 'outside-evidence');
      await mkdir(outside, { recursive: true });
      prepared.evidenceInput = outside;
      break;
    }
    case 'N02_EVIDENCE_SYMLINK_ALIAS':
      await symlink('evidence', join(repository, 'fixture', 'evidence-link'));
      prepared.evidenceInput = 'fixture/evidence-link';
      break;
    case 'N03_EVIDENCE_MISSING':
      prepared.evidenceInput = 'fixture/missing-evidence';
      break;
    case 'N04_EVIDENCE_NOT_DIRECTORY':
      await writeFile(join(repository, 'fixture', 'evidence-file'), 'not a directory\n', { encoding: 'utf8', flag: 'wx' });
      prepared.evidenceInput = 'fixture/evidence-file';
      break;
    case 'N05_EVIDENCE_UNTRACKED': {
      const untracked = join(repository, 'fixture', 'untracked-evidence');
      await mkdir(untracked);
      await writeFile(join(untracked, 'preflight.json'), await readFile(join(evidencePath, 'preflight.json')));
      prepared.evidenceInput = 'fixture/untracked-evidence';
      break;
    }
    case 'N06_EVIDENCE_COMMITTED_NOT_PUSHED': {
      const unpushed = join(repository, 'fixture', 'unpushed-evidence');
      await mkdir(unpushed);
      await writeFile(join(unpushed, 'preflight.json'), await readFile(join(evidencePath, 'preflight.json')));
      await gitChecked(['add', '--', 'fixture/unpushed-evidence/preflight.json'], repository, observer, 'ADD_N06');
      await gitChecked(['commit', '-m', 'fixture: local evidence only'], repository, observer, 'COMMIT_N06');
      prepared.evidenceInput = 'fixture/unpushed-evidence';
      break;
    }
    case 'N07_PREFLIGHT_SELF_HASH':
      await rewritePreflight(repository, record => ({ ...record, preflightHash: '0'.repeat(64) }));
      prepared.originRef = await commitAndPushCase(repository, caseDefinition.id, observer, 'fixture: corrupt preflight self hash');
      break;
    case 'N08_PREFLIGHT_STATUS':
      await rewritePreflight(repository, record => {
        const body = { ...record, status: 'REJECTED' };
        delete body.preflightHash;
        return { ...body, preflightHash: canonicalHash(body) };
      });
      prepared.originRef = await commitAndPushCase(repository, caseDefinition.id, observer, 'fixture: rejected preflight status');
      break;
    case 'N09_TOOL_HASH':
      await rewritePreflight(repository, record => {
        const body = { ...record, toolHashes: { 'tools/admission-tool.mjs': 'f'.repeat(64) } };
        delete body.preflightHash;
        return { ...body, preflightHash: canonicalHash(body) };
      });
      prepared.originRef = await commitAndPushCase(repository, caseDefinition.id, observer, 'fixture: mismatched tool hash');
      break;
    case 'N10_OUTPUT_OUTSIDE_REPOSITORY':
      prepared.formalOutput = join(temporaryRoot, 'outside-formal-output');
      break;
    case 'N11_OUTPUT_SYMLINK_ALIAS':
      await symlink('evidence', join(repository, 'fixture', 'formal-link'));
      prepared.formalOutput = 'fixture/formal-link';
      break;
    case 'N12_OUTPUT_EXISTS_DIRECTORY':
      await mkdir(ordinaryOutput);
      break;
    case 'N13_OUTPUT_EXISTS_FILE':
      await writeFile(ordinaryOutput, 'pre-existing output\n', { encoding: 'utf8', flag: 'wx' });
      break;
    case 'N14_ORIGIN_BRANCH_MISSING':
      prepared.originRef = 'origin/missing-b53-e1';
      break;
    default:
      throw new Error(`Unimplemented case: ${caseDefinition.id}`);
  }
  return prepared;
}

function withoutAbsoluteOutput(admission) {
  return {
    ...admission,
    output: {
      repositoryRelative: admission.output.repositoryRelative,
      parentRepositoryRelative: admission.output.parentRepositoryRelative,
      fresh: admission.output.fresh,
    },
  };
}

async function evaluateCase({ caseDefinition, repository, prepared, ledgerRoot, gitChildren }) {
  await mkdir(ledgerRoot, { recursive: false });
  const attemptBody = {
    schemaVersion: 'bfs.formalRunnerAdmissionAttempt.v0.1',
    experimentId: 'B53-E1',
    caseId: caseDefinition.id,
    expected: caseDefinition.expected,
    expectedReason: caseDefinition.expectedReason ?? null,
    repositoryRoot: repository,
    evidenceInput: prepared.evidenceInput,
    formalOutput: prepared.formalOutput,
    originRef: prepared.originRef,
    scientificVerdict: null,
    formalWorkStarted: false,
  };
  const attemptPath = join(ledgerRoot, 'attempt.json');
  const attempt = await writeHashedJson(attemptPath, attemptBody, 'attemptHash');
  const outputAbsolute = resolve(repository, prepared.formalOutput);
  const outputBefore = await fingerprint(outputAbsolute);
  let evidenceRecord;
  let outcome;
  let reason = null;
  try {
    const admission = await admitFormalRun({
      repositoryRoot: repository,
      evidenceInput: prepared.evidenceInput,
      formalOutput: prepared.formalOutput,
      originRef: prepared.originRef,
      gitObserver: row => gitChildren.push({ phase: `ADMISSION_${caseDefinition.id}`, ...row }),
    });
    const body = {
      schemaVersion: 'bfs.formalRunnerAdmissionAccepted.v0.1',
      experimentId: 'B53-E1',
      caseId: caseDefinition.id,
      status: 'ACCEPTED',
      scientificVerdict: null,
      formalWorkStarted: false,
      admission: withoutAbsoluteOutput(admission),
      absoluteOutputMatchesResolvedCallerPath: admission.output.absolute === outputAbsolute,
      outputBefore,
      outputAfter: await fingerprint(outputAbsolute),
    };
    const path = join(ledgerRoot, 'admission.json');
    const record = await writeHashedJson(path, body, 'admissionHash');
    evidenceRecord = { kind: 'admission', path, record, selfHashField: 'admissionHash' };
    outcome = 'ACCEPT';
  } catch (error) {
    if (!(error instanceof AdmissionError)) throw error;
    reason = error.reason;
    const body = {
      schemaVersion: 'bfs.formalRunnerAdmissionFailure.v0.1',
      experimentId: 'B53-E1',
      caseId: caseDefinition.id,
      status: 'REJECTED',
      reason,
      message: error.message,
      scientificVerdict: null,
      formalWorkStarted: false,
      outputBefore,
      outputAfter: await fingerprint(outputAbsolute),
    };
    const path = join(ledgerRoot, 'failure.json');
    const record = await writeHashedJson(path, body, 'failureHash');
    evidenceRecord = { kind: 'failure', path, record, selfHashField: 'failureHash' };
    outcome = 'REJECT';
  }
  const receiptBody = {
    schemaVersion: 'bfs.formalRunnerAdmissionCaseReceipt.v0.1',
    experimentId: 'B53-E1',
    caseId: caseDefinition.id,
    outcome,
    reason,
    scientificVerdict: null,
    formalWorkStarted: false,
    attempt: {
      uri: `cases/${caseDefinition.id}/attempt.json`,
      sha256: await sha256File(attemptPath),
      attemptHash: attempt.attemptHash,
    },
    evidence: {
      kind: evidenceRecord.kind,
      uri: `cases/${caseDefinition.id}/${evidenceRecord.kind}.json`,
      sha256: await sha256File(evidenceRecord.path),
      selfHashField: evidenceRecord.selfHashField,
      selfHash: evidenceRecord.record[evidenceRecord.selfHashField],
    },
  };
  const receiptPath = join(ledgerRoot, 'receipt.json');
  const receipt = await writeHashedJson(receiptPath, receiptBody, 'receiptHash');
  return {
    caseId: caseDefinition.id,
    outcome,
    reason,
    attemptHash: attempt.attemptHash,
    evidenceSelfHash: evidenceRecord.record[evidenceRecord.selfHashField],
    receiptHash: receipt.receiptHash,
    outputBefore,
    outputAfter: await fingerprint(outputAbsolute),
  };
}

async function validateFormalToolFreeze(repository, args, spec, gitChildren) {
  if (process.execPath !== NODE_EXECUTABLE) throw new Error(`Node executable mismatch: ${process.execPath}`);
  if (await sha256File(process.execPath) !== NODE_SHA256) throw new Error('Node executable SHA-256 mismatch');
  if (process.version !== spec.runtime.node.version) throw new Error(`Node version mismatch: ${process.version}`);
  const head = await gitChecked(['rev-parse', 'HEAD'], repository, row => gitChildren.push(row), 'FORMAL_HEAD');
  const originMain = await gitChecked(['rev-parse', '--verify', 'origin/main'], repository, row => gitChildren.push(row), 'FORMAL_ORIGIN_MAIN');
  if (!args.toolFreezeCommit || head !== args.toolFreezeCommit || originMain !== args.toolFreezeCommit) {
    throw new Error(`Tool-freeze commit must equal HEAD and origin/main: head=${head} origin=${originMain} requested=${args.toolFreezeCommit}`);
  }
  const scopedPaths = ['specs/formal-runner-admission-path-totality.v0.1.json', ...TOOL_PATHS];
  const tracked = await gitChecked(['ls-files', '--', ...scopedPaths], repository, row => gitChildren.push(row), 'FORMAL_TRACKED');
  if (tracked.split('\n').filter(Boolean).length !== scopedPaths.length) throw new Error('Spec/tool paths are not all tracked');
  const dirty = await gitChecked(['status', '--porcelain=v1', '--untracked-files=all', '--', ...scopedPaths], repository, row => gitChildren.push(row), 'FORMAL_CLEAN');
  if (dirty !== '') throw new Error(`Spec/tool paths are dirty: ${dirty}`);
  const preregAncestor = await runGit(['merge-base', '--is-ancestor', PREREGISTRATION_COMMIT, args.toolFreezeCommit], repository, row => gitChildren.push({ phase: 'FORMAL_PREREG_ANCESTRY', ...row }));
  if (preregAncestor.exitCode !== 0) throw new Error('Preregistration is not an ancestor of tool-freeze commit');
  const toolHashes = {};
  for (const uri of TOOL_PATHS) toolHashes[uri] = await sha256File(join(repository, uri));
  return { head, originMain, toolHashes };
}

async function spawnAuditor(argumentsList, formalRoot) {
  const stdout = [];
  const stderr = [];
  const started = process.hrtime.bigint();
  const child = spawn(NODE_EXECUTABLE, argumentsList, {
    cwd: dirname(formalRoot),
    env: { PATH: '/usr/bin:/bin:/opt/homebrew/bin', LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8', TMPDIR: tmpdir() },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  child.stdout.on('data', chunk => stdout.push(chunk));
  child.stderr.on('data', chunk => stderr.push(chunk));
  const exitCode = await new Promise((resolvePromise, reject) => {
    child.on('error', reject);
    child.on('close', resolvePromise);
  });
  return {
    role: 'INDEPENDENT_AUDITOR',
    pid: child.pid,
    exitCode,
    stdout: Buffer.concat(stdout).toString('utf8'),
    stderr: Buffer.concat(stderr).toString('utf8'),
    elapsedNanoseconds: Number(process.hrtime.bigint() - started),
    arguments: argumentsList,
  };
}

async function runDevelopmentProbe() {
  const gitChildren = [];
  const temporaryRoot = await realpath(await mkdtemp(join(tmpdir(), 'bfs-b53-e1-')));
  try {
    const base = await createFixtureBase(temporaryRoot, row => gitChildren.push(row));
    const caseDefinition = { id: 'DEVELOPMENT_POSITIVE', expected: 'ACCEPT' };
    const caseRepository = await cloneCase(base, caseDefinition.id, temporaryRoot, row => gitChildren.push(row));
    const accepted = await admitFormalRun({
      repositoryRoot: caseRepository,
      evidenceInput: 'fixture/./scratch/../evidence',
      formalOutput: 'fixture/./scratch/../formal-probe',
      originRef: 'origin/main',
      gitObserver: row => gitChildren.push({ phase: 'DEVELOPMENT_ADMISSION', ...row }),
    });
    const outputAbsent = await pathState(join(caseRepository, 'fixture', 'formal-probe')) === null;
    if (accepted.status !== 'ACCEPTED' || !outputAbsent) throw new Error('Development positive probe failed');
    process.stdout.write(`${JSON.stringify({ status: 'PASS', formalRootCreated: false, outputAbsent, gitChildProcesses: gitChildren.length, canonicalEvidenceIdentity: accepted.evidence.identityHash })}\n`);
  } finally {
    await safeRemoveOwnedTemp(temporaryRoot);
  }
}

async function runDevelopmentMatrixProbe(repository) {
  const gitChildren = [];
  const temporaryRoot = await realpath(await mkdtemp(join(tmpdir(), 'bfs-b53-e1-')));
  try {
    const specPath = join(repository, 'specs', 'formal-runner-admission-path-totality.v0.1.json');
    const spec = JSON.parse(await readFile(specPath, 'utf8'));
    const probeRoot = join(temporaryRoot, 'matrix-probe-records');
    await mkdir(probeRoot);
    await mkdir(join(probeRoot, 'cases'));
    const head = (await runGit(['rev-parse', 'HEAD'], repository)).stdout.trim();
    const toolHashes = {};
    for (const uri of TOOL_PATHS) toolHashes[uri] = await sha256File(join(repository, uri));
    const startPath = join(probeRoot, 'formal-start.json');
    const start = await writeHashedJson(startPath, {
      schemaVersion: 'bfs.formalRunnerAdmissionFormalStart.v0.1',
      experimentId: 'B53-E1',
      scientificVerdict: null,
      runnerPid: process.pid,
      preregistrationCommit: PREREGISTRATION_COMMIT,
      toolFreezeCommit: head,
      spec: { uri: 'specs/formal-runner-admission-path-totality.v0.1.json', sha256: SPEC_SHA256 },
      toolHashes,
      prohibitedOperationCounts: { blender: 0, blenderRenderCalls: 0, cyclesRayRenders: 0, docker: 0, modelCalls: 0, networkCalls: 0 },
    }, 'startHash');
    const base = await createFixtureBase(temporaryRoot, row => gitChildren.push(row));
    const caseDefinitions = [
      ...spec.positiveCases.map(row => ({ ...row, expectedReason: null })),
      ...spec.negativeCases.map(row => ({ ...row, expected: 'REJECT' })),
    ];
    const caseRows = [];
    const repositories = {};
    for (const caseDefinition of caseDefinitions) {
      const repositoryPath = await cloneCase(base, caseDefinition.id, temporaryRoot, row => gitChildren.push(row));
      repositories[caseDefinition.id] = repositoryPath;
      const prepared = await prepareCase(caseDefinition, repositoryPath, temporaryRoot, row => gitChildren.push(row));
      caseRows.push(await evaluateCase({
        caseDefinition,
        repository: repositoryPath,
        prepared,
        ledgerRoot: join(probeRoot, 'cases', caseDefinition.id),
        gitChildren,
      }));
    }
    const fixturePath = join(probeRoot, 'fixture.json');
    const fixture = await writeHashedJson(fixturePath, {
      schemaVersion: 'bfs.formalRunnerAdmissionFixtureManifest.v0.1',
      experimentId: 'B53-E1',
      temporaryRoot,
      originPath: base.originPath,
      repositories,
      baselineCommit: base.baselineCommit,
      fixtureToolSha256: base.fixtureToolSha256,
      preflightHash: base.preflightHash,
      preflightSha256: base.preflightSha256,
      transport: 'LOCAL_FILE_PROTOCOL_BARE_ORIGIN_ONLY',
      externalRepositories: 0,
      networkCalls: 0,
    }, 'fixtureHash');
    const operationPath = join(probeRoot, 'operation-draft.json');
    const operation = await writeHashedJson(operationPath, {
      schemaVersion: 'bfs.formalRunnerAdmissionOperationDraft.v0.1',
      experimentId: 'B53-E1',
      runnerPid: process.pid,
      runnerProcesses: 1,
      auditorProcessesPlanned: 1,
      caseEvaluations: caseRows.length,
      gitChildProcesses: gitChildren,
      gitChildProcessCount: gitChildren.length,
      blenderProcesses: 0,
      blenderRenderCalls: 0,
      cyclesRayRenders: 0,
      dockerProcesses: 0,
      modelCalls: 0,
      networkCalls: 0,
    }, 'operationHash');
    const executionPath = join(probeRoot, 'execution.json');
    await writeHashedJson(executionPath, {
      schemaVersion: 'bfs.formalRunnerAdmissionExecution.v0.1',
      experimentId: 'B53-E1',
      scientificVerdict: null,
      spec: { uri: 'specs/formal-runner-admission-path-totality.v0.1.json', sha256: SPEC_SHA256 },
      preregistrationCommit: PREREGISTRATION_COMMIT,
      toolFreezeCommit: head,
      toolHashes,
      formalStart: { uri: 'formal-start.json', sha256: await sha256File(startPath), startHash: start.startHash },
      fixture: { uri: 'fixture.json', sha256: await sha256File(fixturePath), fixtureHash: fixture.fixtureHash },
      operationDraft: { uri: 'operation-draft.json', sha256: await sha256File(operationPath), operationHash: operation.operationHash },
      cases: caseRows,
      prohibitedOperationCounts: { blender: 0, blenderRenderCalls: 0, cyclesRayRenders: 0, docker: 0, modelCalls: 0, networkCalls: 0 },
    }, 'executionHash');
    const auditPath = join(probeRoot, 'audit.json');
    const auditor = await spawnAuditor([
      join(repository, 'scripts', 'audit-b53-e1-formal-runner-admission-path-totality.mjs'),
      '--spec', specPath,
      '--formal-root', probeRoot,
      '--fixture-root', temporaryRoot,
      '--execution', executionPath,
      '--operation-draft', operationPath,
      '--output', auditPath,
    ], probeRoot);
    if (auditor.exitCode !== 0) throw new Error(`Development matrix auditor failed: ${auditor.stderr}`);
    const audit = JSON.parse(await readFile(auditPath, 'utf8'));
    const expectedNonIdentityGates = spec.gates.filter(gate => gate !== 'SPEC_AND_TOOL_IDENTITIES');
    const probePassed = audit.gates.SPEC_AND_TOOL_IDENTITIES === false
      && expectedNonIdentityGates.every(gate => audit.gates[gate] === true)
      && audit.semanticAttackCount >= 32
      && audit.semanticAttacksPassed === audit.semanticAttackCount;
    if (!probePassed) throw new Error(`Development matrix gates unexpected: ${JSON.stringify(audit.gates)}`);
    process.stdout.write(`${JSON.stringify({
      status: 'PASS',
      formalRootCreated: false,
      caseEvaluations: caseRows.length,
      expectedToolFreezeGate: false,
      otherGatesPassed: expectedNonIdentityGates.length,
      semanticAttacksPassed: audit.semanticAttacksPassed,
      semanticAttackCount: audit.semanticAttackCount,
      runnerGitChildProcesses: gitChildren.length,
      auditorGitChildProcesses: audit.auditorGitChildProcessCount,
    })}\n`);
  } finally {
    await safeRemoveOwnedTemp(temporaryRoot);
  }
}

async function main() {
  const args = parseArguments(process.argv.slice(2));
  const repository = await realpath(process.cwd());
  if (args.developmentProbe) {
    await runDevelopmentProbe();
    return;
  }
  if (args.developmentMatrixProbe) {
    await runDevelopmentMatrixProbe(repository);
    return;
  }
  if (!args.spec || !args.outputRoot || !args.toolFreezeCommit) throw new Error('Formal mode requires --spec, --output-root and --tool-freeze-commit');
  const specPath = resolve(repository, args.spec);
  if (await sha256File(specPath) !== SPEC_SHA256) throw new Error('B53-E1 spec SHA-256 mismatch');
  const spec = JSON.parse(await readFile(specPath, 'utf8'));
  if (spec.experimentId !== 'B53-E1') throw new Error('B53-E1 experiment identity mismatch');
  const formalRoot = resolve(repository, args.outputRoot);
  const expectedFormalRoot = resolve(repository, spec.freshness.formalRoot);
  if (formalRoot !== expectedFormalRoot || !strictlyBelow(repository, formalRoot)) throw new Error('Formal output root does not equal the frozen repository-contained root');
  if (await pathState(formalRoot)) throw new Error('Formal output root already exists; B53-E1 is single-use');

  const gitChildren = [];
  const freeze = await validateFormalToolFreeze(repository, args, spec, gitChildren);
  await mkdir(formalRoot, { recursive: false });
  let temporaryRoot = null;
  try {
    const startPath = join(formalRoot, 'formal-start.json');
    const start = await writeHashedJson(startPath, {
      schemaVersion: 'bfs.formalRunnerAdmissionFormalStart.v0.1',
      experimentId: 'B53-E1',
      scientificVerdict: null,
      runnerPid: process.pid,
      preregistrationCommit: PREREGISTRATION_COMMIT,
      toolFreezeCommit: args.toolFreezeCommit,
      spec: { uri: args.spec, sha256: SPEC_SHA256 },
      toolHashes: freeze.toolHashes,
      prohibitedOperationCounts: { blender: 0, blenderRenderCalls: 0, cyclesRayRenders: 0, docker: 0, modelCalls: 0, networkCalls: 0 },
    }, 'startHash');

    temporaryRoot = await realpath(await mkdtemp(join(tmpdir(), 'bfs-b53-e1-')));
    await mkdir(join(formalRoot, 'cases'));
    const base = await createFixtureBase(temporaryRoot, row => gitChildren.push(row));
    const caseDefinitions = [
      ...spec.positiveCases.map(row => ({ ...row, expectedReason: null })),
      ...spec.negativeCases.map(row => ({ ...row, expected: 'REJECT' })),
    ];
    const caseRows = [];
    const repositories = {};
    for (const caseDefinition of caseDefinitions) {
      const repositoryPath = await cloneCase(base, caseDefinition.id, temporaryRoot, row => gitChildren.push(row));
      repositories[caseDefinition.id] = repositoryPath;
      const prepared = await prepareCase(caseDefinition, repositoryPath, temporaryRoot, row => gitChildren.push(row));
      const row = await evaluateCase({
        caseDefinition,
        repository: repositoryPath,
        prepared,
        ledgerRoot: join(formalRoot, 'cases', caseDefinition.id),
        gitChildren,
      });
      caseRows.push(row);
    }

    const fixtureBody = {
      schemaVersion: 'bfs.formalRunnerAdmissionFixtureManifest.v0.1',
      experimentId: 'B53-E1',
      temporaryRoot,
      originPath: base.originPath,
      repositories,
      baselineCommit: base.baselineCommit,
      fixtureToolSha256: base.fixtureToolSha256,
      preflightHash: base.preflightHash,
      preflightSha256: base.preflightSha256,
      transport: 'LOCAL_FILE_PROTOCOL_BARE_ORIGIN_ONLY',
      externalRepositories: 0,
      networkCalls: 0,
    };
    const fixturePath = join(formalRoot, 'fixture.json');
    const fixture = await writeHashedJson(fixturePath, fixtureBody, 'fixtureHash');
    const operationBody = {
      schemaVersion: 'bfs.formalRunnerAdmissionOperationDraft.v0.1',
      experimentId: 'B53-E1',
      runnerPid: process.pid,
      runnerProcesses: 1,
      auditorProcessesPlanned: 1,
      caseEvaluations: caseRows.length,
      gitChildProcesses: gitChildren,
      gitChildProcessCount: gitChildren.length,
      blenderProcesses: 0,
      blenderRenderCalls: 0,
      cyclesRayRenders: 0,
      dockerProcesses: 0,
      modelCalls: 0,
      networkCalls: 0,
    };
    const operationPath = join(formalRoot, 'operation-draft.json');
    const operation = await writeHashedJson(operationPath, operationBody, 'operationHash');
    const executionBody = {
      schemaVersion: 'bfs.formalRunnerAdmissionExecution.v0.1',
      experimentId: 'B53-E1',
      scientificVerdict: null,
      spec: { uri: args.spec, sha256: SPEC_SHA256 },
      preregistrationCommit: PREREGISTRATION_COMMIT,
      toolFreezeCommit: args.toolFreezeCommit,
      toolHashes: freeze.toolHashes,
      formalStart: { uri: 'formal-start.json', sha256: await sha256File(startPath), startHash: start.startHash },
      fixture: { uri: 'fixture.json', sha256: await sha256File(fixturePath), fixtureHash: fixture.fixtureHash },
      operationDraft: { uri: 'operation-draft.json', sha256: await sha256File(operationPath), operationHash: operation.operationHash },
      cases: caseRows,
      prohibitedOperationCounts: { blender: 0, blenderRenderCalls: 0, cyclesRayRenders: 0, docker: 0, modelCalls: 0, networkCalls: 0 },
    };
    const executionPath = join(formalRoot, 'execution.json');
    const execution = await writeHashedJson(executionPath, executionBody, 'executionHash');

    const auditPath = join(formalRoot, 'audit.json');
    const auditorArguments = [
      join(repository, 'scripts', 'audit-b53-e1-formal-runner-admission-path-totality.mjs'),
      '--spec', specPath,
      '--formal-root', formalRoot,
      '--fixture-root', temporaryRoot,
      '--execution', executionPath,
      '--operation-draft', operationPath,
      '--output', auditPath,
    ];
    const auditorProcess = await spawnAuditor(auditorArguments, formalRoot);
    if (auditorProcess.exitCode !== 0) throw new Error(`Independent auditor failed: ${auditorProcess.stderr}`);
    const audit = JSON.parse(await readFile(auditPath, 'utf8'));
    const auditBody = structuredClone(audit);
    delete auditBody.auditHash;
    if (audit.auditHash !== canonicalHash(auditBody)) throw new Error('Independent audit self-hash mismatch');

    await safeRemoveOwnedTemp(temporaryRoot);
    temporaryRoot = null;
    const cleanupPath = join(formalRoot, 'fixture-cleanup.json');
    const cleanup = await writeHashedJson(cleanupPath, {
      schemaVersion: 'bfs.formalRunnerAdmissionFixtureCleanup.v0.1',
      experimentId: 'B53-E1',
      ownedTemporaryRootRemoved: true,
      fixtureRetainedAsMachineRecords: true,
      scientificVerdict: null,
    }, 'cleanupHash');

    const allGatesPass = Object.keys(audit.gates ?? {}).length === spec.gates.length
      && spec.gates.every(gate => audit.gates[gate] === true);
    const scientificVerdict = allGatesPass ? spec.decision.supportedVerdict : spec.decision.rejectedVerdict;
    if (audit.expectedScientificVerdict !== scientificVerdict) throw new Error('Independent audit verdict mapping mismatch');
    const resultBody = {
      schemaVersion: 'bfs.formalRunnerAdmissionPathTotalityResult.v0.1',
      experimentId: 'B53-E1',
      scientificVerdict,
      supported: scientificVerdict === spec.decision.supportedVerdict,
      gates: audit.gates,
      gatePassed: Object.values(audit.gates).filter(Boolean).length,
      gateTotal: spec.gates.length,
      cases: caseRows.map(row => ({ caseId: row.caseId, outcome: row.outcome, reason: row.reason, receiptHash: row.receiptHash })),
      semanticAttacks: { passed: audit.semanticAttacksPassed, total: audit.semanticAttackCount },
      operationCounts: {
        runnerProcesses: 1,
        auditorProcesses: 1,
        caseEvaluations: caseRows.length,
        runnerGitChildProcesses: gitChildren.length,
        auditorGitChildProcesses: audit.auditorGitChildProcessCount,
        gitChildProcesses: gitChildren.length + audit.auditorGitChildProcessCount,
        blenderProcesses: 0,
        blenderRenderCalls: 0,
        cyclesRayRenders: 0,
        dockerProcesses: 0,
        modelCalls: 0,
        networkCalls: 0,
      },
      processes: { runnerPid: process.pid, auditor: auditorProcess },
      execution: { uri: 'execution.json', sha256: await sha256File(executionPath), executionHash: execution.executionHash },
      audit: { uri: 'audit.json', sha256: await sha256File(auditPath), auditHash: audit.auditHash, status: audit.status },
      cleanup: { uri: 'fixture-cleanup.json', sha256: await sha256File(cleanupPath), cleanupHash: cleanup.cleanupHash },
      nonClaims: spec.nonClaims,
    };
    const resultPath = join(formalRoot, 'results.json');
    const result = await writeHashedJson(resultPath, resultBody, 'resultHash');
    const receiptBody = {
      schemaVersion: 'bfs.formalRunnerAdmissionPathTotalityReceipt.v0.1',
      experimentId: 'B53-E1',
      scientificVerdict,
      spec: { uri: args.spec, sha256: SPEC_SHA256 },
      preregistrationCommit: PREREGISTRATION_COMMIT,
      toolFreezeCommit: args.toolFreezeCommit,
      toolHashes: freeze.toolHashes,
      execution: { uri: 'execution.json', sha256: await sha256File(executionPath), executionHash: execution.executionHash },
      audit: { uri: 'audit.json', sha256: await sha256File(auditPath), auditHash: audit.auditHash },
      result: { uri: 'results.json', sha256: await sha256File(resultPath), resultHash: result.resultHash },
      cleanup: { uri: 'fixture-cleanup.json', sha256: await sha256File(cleanupPath), cleanupHash: cleanup.cleanupHash },
      processBoundaryPassed: auditorProcess.exitCode === 0 && auditorProcess.pid !== process.pid,
      sameIdRepairAndRerunForbidden: true,
    };
    const receipt = await writeHashedJson(join(formalRoot, 'receipt.json'), receiptBody, 'receiptHash');
    process.stdout.write(`BFS_B53_E1_FORMAL_COMPLETE verdict=${scientificVerdict} gates=${result.gatePassed}/${result.gateTotal} attacks=${audit.semanticAttacksPassed}/${audit.semanticAttackCount} receipt=${receipt.receiptHash}\n`);
  } catch (error) {
    if (temporaryRoot) {
      try { await safeRemoveOwnedTemp(temporaryRoot); } catch { /* Preserve primary failure. */ }
    }
    const body = {
      schemaVersion: 'bfs.formalRunnerAdmissionPathTotalityInvalidation.v0.1',
      experimentId: 'B53-E1',
      status: 'INVALIDATED',
      scientificVerdict: null,
      reason: error?.name ?? 'Error',
      message: error?.message ?? String(error),
      sameIdRepairAndRerunForbidden: true,
      prohibitedOperationCounts: { blender: 0, blenderRenderCalls: 0, cyclesRayRenders: 0, docker: 0, modelCalls: 0, networkCalls: 0 },
    };
    const invalidationPath = join(formalRoot, 'invalidation.json');
    if (!await pathState(invalidationPath)) await writeHashedJson(invalidationPath, body, 'invalidationHash');
    throw error;
  }
}

main().catch(error => {
  process.stderr.write(`${error?.stack ?? error}\n`);
  process.exitCode = 1;
});
