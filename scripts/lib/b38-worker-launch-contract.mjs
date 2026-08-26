import { readFile } from 'node:fs/promises';
import { posix } from 'node:path';
import { resolve } from 'node:path';
import { canonicalJson, sha256Canonical } from './receipt-format.mjs';
import { repositoryRoot, sha256 } from './scene-spec.mjs';

export const B38_SPEC_PATH = resolve(repositoryRoot, 'specs/worker-launch-contract.v0.1.json');
export const B38_SPEC_SHA256 = 'c96a6c7d9bf91c0b0f72fa2094ef6b6c0bb778d7443533f661859427715f9514';
export const B38_PREREG_COMMIT = 'a7d8311e0af46824aafafaa25d0c17be8a86cc44';
export const B38_PARENT_CANARY_KEY = 'BFS_B38_NONSECRET_PARENT_CANARY';
export const B38_PARENT_CANARY_VALUE = 'BFS_B38_NONSECRET_PARENT_CANARY_V1';

const REQUEST_KEYS = [
  'attemptId',
  'imageReference',
  'inputRootIdentity',
  'jobId',
  'outputRootIdentity',
  'projectedWriteBytes',
  'sceneUri',
  'schemaVersion',
  'scriptArgs',
  'trustedScriptUri',
];
const PLAN_KEYS = [
  'attemptId',
  'backend',
  'candidatePolicy',
  'diskAdmissionPolicy',
  'ephemeralPaths',
  'jobId',
  'mounts',
  'planHash',
  'process',
  'projectedWriteBytes',
  'recovery',
  'requestHash',
  'schemaVersion',
];
const HEX_64 = /^[a-f0-9]{64}$/;
const ID_PATTERN = /^[A-Z0-9][A-Z0-9_-]{2,63}$/;
const ROOT_ID_PATTERN = /^bfs-(input|output):[a-z0-9][a-z0-9._/-]{2,127}$/;
const IMAGE_DIGEST_PATTERN = /^[a-z0-9][a-z0-9._/-]*@sha256:[a-f0-9]{64}$/;

const exactKeys = (value, expected) => {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
  const actual = Object.keys(value).sort();
  const sortedExpected = [...expected].sort();
  return actual.length === sortedExpected.length && actual.every((key, index) => key === sortedExpected[index]);
};

const exactCanonical = (left, right) => canonicalJson(left) === canonicalJson(right);

function assertSafeUri(value, extension, label) {
  if (typeof value !== 'string' || value.length < 3 || value.length > 240) throw new Error(`${label} must be a bounded relative URI`);
  if (value.startsWith('/') || value.includes('\\') || value.includes('\0')) throw new Error(`${label} must use relative POSIX syntax`);
  if (posix.normalize(value) !== value || value.split('/').some(segment => segment === '..' || segment === '.')) throw new Error(`${label} must be normalized without traversal`);
  if (!value.endsWith(extension)) throw new Error(`${label} must end with ${extension}`);
}

function validateRequest(request) {
  if (!exactKeys(request, REQUEST_KEYS)) throw new Error('WorkerRequest key set differs');
  if (request.schemaVersion !== 'bfs.workerRequest.v0.1') throw new Error('WorkerRequest schemaVersion differs');
  if (!ID_PATTERN.test(request.jobId)) throw new Error('jobId is invalid');
  if (!ID_PATTERN.test(request.attemptId)) throw new Error('attemptId is invalid');
  if (!ROOT_ID_PATTERN.test(request.inputRootIdentity) || !request.inputRootIdentity.startsWith('bfs-input:')) throw new Error('inputRootIdentity is invalid');
  if (!ROOT_ID_PATTERN.test(request.outputRootIdentity) || !request.outputRootIdentity.startsWith('bfs-output:')) throw new Error('outputRootIdentity is invalid');
  if (!IMAGE_DIGEST_PATTERN.test(request.imageReference)) throw new Error('imageReference must be digest pinned');
  if (!/^[1-9][0-9]{0,14}$/.test(request.projectedWriteBytes)) throw new Error('projectedWriteBytes must be a positive decimal string');
  assertSafeUri(request.sceneUri, '.blend', 'sceneUri');
  assertSafeUri(request.trustedScriptUri, '.py', 'trustedScriptUri');
  if (!Array.isArray(request.scriptArgs) || request.scriptArgs.length > 16 || request.scriptArgs.some(value => typeof value !== 'string' || value.length > 256 || value.includes('\0'))) {
    throw new Error('scriptArgs must be at most 16 bounded strings');
  }
  return request;
}

export async function readB38Spec() {
  const bytes = await readFile(B38_SPEC_PATH);
  const digest = sha256(bytes);
  if (digest !== B38_SPEC_SHA256) throw new Error(`B38 spec SHA mismatch: ${digest}`);
  return JSON.parse(bytes);
}

export function hashB38Plan(plan) {
  const copy = structuredClone(plan);
  delete copy.planHash;
  return sha256Canonical(copy);
}

export function compileB38WorkerLaunchPlan(requestInput, spec, parentEnvironment = process.env) {
  const request = validateRequest(structuredClone(requestInput));
  const environment = {
    BFS_INPUT_ROOT: spec.contract.environmentValues.BFS_INPUT_ROOT,
    BFS_JOB_ID: request.jobId,
    BFS_OUTPUT_ROOT: spec.contract.environmentValues.BFS_OUTPUT_ROOT,
    BFS_REPORT_PATH: '/outputs/worker-report.json',
    BLENDER_USER_CONFIG: spec.contract.environmentValues.BLENDER_USER_CONFIG,
    BLENDER_USER_SCRIPTS: spec.contract.environmentValues.BLENDER_USER_SCRIPTS,
    HOME: spec.contract.environmentValues.HOME,
    LANG: spec.contract.environmentValues.LANG,
    LC_ALL: spec.contract.environmentValues.LC_ALL,
    OCIO: spec.contract.environmentValues.OCIO,
    TMPDIR: spec.contract.environmentValues.TMPDIR,
  };
  if (Object.keys(parentEnvironment).length > 0 && Object.hasOwn(environment, B38_PARENT_CANARY_KEY)) {
    throw new Error('Parent canary unexpectedly entered the allowlist');
  }
  const mounts = [
    { id: 'INPUTS', sourceIdentity: request.inputRootIdentity, target: '/inputs', readOnly: true },
    { id: 'OUTPUTS', sourceIdentity: request.outputRootIdentity, target: '/outputs', readOnly: false },
  ];
  const candidatePolicy = {
    imageReference: request.imageReference,
    pull: spec.contract.containerCandidatePolicy.pull,
    removeAfterExit: spec.contract.containerCandidatePolicy.removeAfterExit,
    rootFilesystemReadOnly: spec.contract.containerCandidatePolicy.rootFilesystemReadOnly,
    network: spec.contract.containerCandidatePolicy.network,
    privileged: spec.contract.containerCandidatePolicy.privileged,
    user: spec.contract.containerCandidatePolicy.user,
    capDrop: [...spec.contract.containerCandidatePolicy.capDrop],
    capAdd: [...spec.contract.containerCandidatePolicy.capAdd],
    noNewPrivileges: spec.contract.containerCandidatePolicy.noNewPrivileges,
    pidsLimit: spec.contract.containerCandidatePolicy.pidsLimit,
    memoryBytes: spec.contract.containerCandidatePolicy.memoryBytes,
    cpus: spec.contract.containerCandidatePolicy.cpus,
    shmBytes: spec.contract.containerCandidatePolicy.shmBytes,
  };
  const plan = {
    schemaVersion: 'bfs.workerLaunchPlan.v0.1',
    requestHash: sha256Canonical(request),
    jobId: request.jobId,
    attemptId: request.attemptId,
    backend: spec.contract.backend,
    projectedWriteBytes: request.projectedWriteBytes,
    process: {
      shell: false,
      executable: {
        uri: spec.contract.blenderExecutable,
        sha256: spec.contract.blenderExecutableSha256,
      },
      argv: [
        ...spec.contract.requiredBlenderArgvPrefix,
        `/inputs/${request.sceneUri}`,
        ...spec.contract.requiredPythonFailureArgs,
        '--python',
        `/inputs/${request.trustedScriptUri}`,
        '--',
        ...request.scriptArgs,
      ],
      cwd: '/work',
      environment,
    },
    mounts,
    ephemeralPaths: [...spec.contract.ephemeralPaths],
    candidatePolicy,
    diskAdmissionPolicy: structuredClone(spec.contract.diskAdmission),
    recovery: structuredClone(spec.contract.recovery),
  };
  plan.planHash = hashB38Plan(plan);
  return plan;
}

export function analyzeB38Plan(plan, request, spec) {
  const failures = [];
  const requireGate = (condition, code) => {
    if (!condition && !failures.includes(code)) failures.push(code);
    return Boolean(condition);
  };
  let expected = null;
  try {
    expected = compileB38WorkerLaunchPlan(request, spec, { [B38_PARENT_CANARY_KEY]: B38_PARENT_CANARY_VALUE });
  } catch {
    requireGate(false, 'REQUEST');
  }
  requireGate(exactKeys(plan, PLAN_KEYS), 'PLAN_KEY_SET');
  requireGate(typeof plan?.planHash === 'string' && plan.planHash === hashB38Plan(plan), 'PLAN_SELF_HASH');
  requireGate(plan?.process?.shell === false, 'SHELL');
  requireGate(
    plan?.process?.executable?.uri === spec.contract.blenderExecutable
      && plan?.process?.executable?.sha256 === spec.contract.blenderExecutableSha256,
    'EXECUTABLE_IDENTITY',
  );
  const argv = plan?.process?.argv ?? [];
  requireGate(spec.contract.requiredBlenderArgvPrefix.every((value, index) => argv[index] === value), 'ARGV_PREFIX');
  requireGate(argv.includes('--disable-autoexec'), 'DISABLE_AUTOEXEC');
  requireGate(argv.includes('--offline-mode'), 'OFFLINE_MODE');
  requireGate(spec.contract.forbiddenBlenderArgs.every(value => !argv.includes(value)), 'FORBIDDEN_ARGV');
  const pythonExitIndex = argv.indexOf('--python-exit-code');
  requireGate(pythonExitIndex >= 0 && argv[pythonExitIndex + 1] === '1', 'PYTHON_EXIT_CODE');
  const environment = plan?.process?.environment ?? {};
  requireGate(exactKeys(environment, spec.contract.environmentKeysExact), 'ENVIRONMENT_KEYS');
  const expectedEnvironment = expected?.process?.environment;
  requireGate(expectedEnvironment !== undefined && exactCanonical(environment, expectedEnvironment), 'ENVIRONMENT_VALUES');
  requireGate(!Object.hasOwn(environment, B38_PARENT_CANARY_KEY), 'PARENT_ENVIRONMENT');
  const mounts = plan?.mounts ?? [];
  const input = mounts.find(mount => mount.id === 'INPUTS');
  const output = mounts.find(mount => mount.id === 'OUTPUTS');
  requireGate(mounts.length === 2 && input && output, 'MOUNT_SET');
  requireGate(input?.target === '/inputs' && input?.readOnly === true, 'INPUT_MOUNT');
  requireGate(output?.target === '/outputs' && output?.readOnly === false, 'OUTPUT_MOUNT');
  requireGate(mounts.filter(mount => mount.readOnly === false).length === 1, 'WRITABLE_MOUNT_SET');
  requireGate(!mounts.some(mount => mount.target === '/var/run/docker.sock' || mount.target === '/run/docker.sock'), 'DOCKER_SOCKET_MOUNT');
  const policy = plan?.candidatePolicy ?? {};
  requireGate(IMAGE_DIGEST_PATTERN.test(policy.imageReference ?? ''), 'IMAGE_DIGEST');
  requireGate(policy.pull === 'never', 'PULL_POLICY');
  requireGate(policy.rootFilesystemReadOnly === true, 'READ_ONLY_ROOTFS');
  requireGate(policy.network === 'none', 'NETWORK');
  requireGate(policy.privileged === false, 'PRIVILEGED');
  requireGate(policy.user === '65532:65532', 'NON_ROOT_USER');
  requireGate(exactCanonical(policy.capDrop, ['ALL']) && exactCanonical(policy.capAdd, []), 'CAPABILITIES');
  requireGate(policy.noNewPrivileges === true, 'NO_NEW_PRIVILEGES');
  requireGate(Number.isInteger(policy.pidsLimit) && policy.pidsLimit > 0
    && Number.isInteger(policy.memoryBytes) && policy.memoryBytes > 0
    && Number.isFinite(policy.cpus) && policy.cpus > 0, 'RESOURCE_LIMITS');
  if (expected) requireGate(exactCanonical(plan, expected), 'PLAN_CANONICAL');
  return {
    schemaVersion: 'bfs.workerLaunchPlanAnalysis.v0.1',
    passed: failures.length === 0,
    failures,
  };
}

const decimalBigInt = (value, label) => {
  if (typeof value !== 'string' || !/^(0|[1-9][0-9]*)$/.test(value)) throw new Error(`${label} must be a decimal string`);
  return BigInt(value);
};

export function evaluateB38Admission({ availableBytes, projectedWriteBytes, outputRootEmpty }, spec) {
  const available = decimalBigInt(availableBytes, 'availableBytes');
  const projected = decimalBigInt(projectedWriteBytes, 'projectedWriteBytes');
  const reserve = BigInt(spec.contract.diskAdmission.minimumReserveBytes);
  const freeAfterProjected = available - projected;
  const reasons = [];
  if (!outputRootEmpty) reasons.push('OUTPUT_ROOT_NOT_EMPTY');
  if (freeAfterProjected < reserve) reasons.push('DISK_RESERVE');
  return {
    schemaVersion: 'bfs.workerAdmission.v0.1',
    availableBytes,
    projectedWriteBytes,
    minimumReserveBytes: reserve.toString(),
    freeAfterProjectedBytes: freeAfterProjected.toString(),
    outputRootEmpty,
    status: reasons.length === 0 ? 'ACCEPTED' : 'BLOCKED',
    reasons,
  };
}

export function analyzeB38Admission(admission, spec) {
  const failures = [];
  let expected;
  try {
    expected = evaluateB38Admission(admission, spec);
  } catch {
    return { schemaVersion: 'bfs.workerAdmissionAnalysis.v0.1', passed: false, failures: ['ADMISSION_INPUT'] };
  }
  if (!exactCanonical(admission, expected)) failures.push('ADMISSION_DECISION');
  return { schemaVersion: 'bfs.workerAdmissionAnalysis.v0.1', passed: failures.length === 0, failures };
}

function hashReceipt(receipt) {
  const copy = structuredClone(receipt);
  delete copy.receiptHash;
  return sha256Canonical(copy);
}

export function createB38SyntheticReceipt(plan, status, spec) {
  if (!['SUCCEEDED', 'FAILED', 'TIMED_OUT', 'CANCELLED'].includes(status)) throw new Error(`Unknown receipt status ${status}`);
  const succeeded = status === 'SUCCEEDED';
  const timedOut = status === 'TIMED_OUT';
  const cancelled = status === 'CANCELLED';
  const receipt = {
    schemaVersion: 'bfs.workerTerminalReceipt.v0.1',
    planHash: plan.planHash,
    jobId: plan.jobId,
    attemptId: plan.attemptId,
    status,
    exitCode: succeeded ? 0 : status === 'FAILED' ? 7 : null,
    timedOut,
    cancelled,
    termination: timedOut ? {
      requestedSignal: spec.contract.recovery.terminateSignal,
      graceMs: spec.contract.recovery.terminateGraceMs,
      forceSignal: spec.contract.recovery.forceSignal,
    } : null,
    reportSha256: succeeded ? '1'.repeat(64) : null,
    outputManifestSha256: succeeded ? '2'.repeat(64) : null,
    promotable: succeeded,
  };
  receipt.receiptHash = hashReceipt(receipt);
  return receipt;
}

export function analyzeB38Receipt(receipt, plan, spec) {
  const failures = [];
  const requireGate = (condition, code) => {
    if (!condition && !failures.includes(code)) failures.push(code);
  };
  requireGate(receipt?.receiptHash === hashReceipt(receipt), 'RECEIPT_SELF_HASH');
  requireGate(receipt?.planHash === plan.planHash && receipt?.jobId === plan.jobId && receipt?.attemptId === plan.attemptId, 'RECEIPT_PLAN_BINDING');
  const shouldPromote = receipt?.status === 'SUCCEEDED' && receipt.exitCode === 0
    && receipt.timedOut === false && receipt.cancelled === false
    && HEX_64.test(receipt.reportSha256 ?? '') && HEX_64.test(receipt.outputManifestSha256 ?? '');
  requireGate(receipt?.promotable === shouldPromote, 'RECEIPT_PROMOTION');
  if (receipt?.status === 'TIMED_OUT') {
    requireGate(receipt.timedOut === true && exactCanonical(receipt.termination, {
      requestedSignal: spec.contract.recovery.terminateSignal,
      graceMs: spec.contract.recovery.terminateGraceMs,
      forceSignal: spec.contract.recovery.forceSignal,
    }), 'TIMEOUT_RECOVERY');
  }
  if (receipt?.status !== 'SUCCEEDED') requireGate(receipt?.promotable === false, 'FAILURE_NOT_PROMOTABLE');
  return { schemaVersion: 'bfs.workerTerminalReceiptAnalysis.v0.1', passed: failures.length === 0, failures };
}

export function analyzeB38Evidence(record, spec) {
  const failures = [];
  const requireGate = (condition, code) => {
    if (!condition) failures.push(code);
    return Boolean(condition);
  };
  requireGate(record?.preregistration?.commit === B38_PREREG_COMMIT && record?.preregistration?.specSha256 === B38_SPEC_SHA256, 'PREREGISTRATION');
  requireGate(record?.runtime?.nodeVersion === spec.runtime.nodeVersion
    && record?.runtime?.nodeBinary === spec.runtime.nodeBinary
    && record?.runtime?.nodeBinarySha256 === spec.runtime.nodeBinarySha256, 'RUNTIME_IDENTITY');
  const fixtures = record?.fixtures ?? [];
  requireGate(fixtures.length === spec.frozenPositiveGates.acceptedRequests, 'FIXTURE_COUNT');
  for (const fixture of fixtures) {
    requireGate(fixture.requestHash === fixture.reorderedRequestHash, `REQUEST_HASH_${fixture.id}`);
    requireGate(fixture.plan.planHash === fixture.reorderedPlan.planHash, `PLAN_HASH_${fixture.id}`);
    requireGate(fixture.analysis.passed && fixture.reorderedAnalysis.passed, `PLAN_ANALYSIS_${fixture.id}`);
    requireGate(exactKeys(fixture.plan.process.environment, spec.contract.environmentKeysExact), `ENV_KEYS_${fixture.id}`);
    requireGate(!Object.hasOwn(fixture.plan.process.environment, B38_PARENT_CANARY_KEY), `PARENT_ENV_${fixture.id}`);
  }
  const admissions = record?.admissions ?? {};
  requireGate(admissions.accepted?.status === 'ACCEPTED' && admissions.acceptedAnalysis?.passed, 'ADMISSION_ACCEPTED');
  requireGate(admissions.dirty?.status === 'BLOCKED' && admissions.dirty?.reasons?.includes('OUTPUT_ROOT_NOT_EMPTY') && admissions.dirtyAnalysis?.passed, 'ADMISSION_DIRTY');
  requireGate(admissions.belowReserve?.status === 'BLOCKED' && admissions.belowReserve?.reasons?.includes('DISK_RESERVE') && admissions.belowReserveAnalysis?.passed, 'ADMISSION_BELOW_RESERVE');
  requireGate(admissions.hostObserved?.status === 'BLOCKED' && admissions.hostObserved?.reasons?.includes('DISK_RESERVE') && admissions.hostObservedAnalysis?.passed, 'HOST_DISK_BLOCKED');
  const receipts = record?.receipts ?? {};
  for (const status of ['SUCCEEDED', 'FAILED', 'TIMED_OUT', 'CANCELLED']) {
    const key = status.toLowerCase();
    requireGate(receipts[key]?.status === status && receipts[`${key}Analysis`]?.passed, `RECEIPT_${status}`);
  }
  requireGate(receipts.succeeded?.promotable === true, 'SUCCESS_PROMOTABLE');
  requireGate(['failed', 'timed_out', 'cancelled'].every(key => receipts[key]?.promotable === false), 'FAILURES_NOT_PROMOTABLE');
  return {
    schemaVersion: 'bfs.workerLaunchContractAnalysis.v0.1',
    decision: failures.length === 0 ? 'WORKER_LAUNCH_CONTRACT_LOGIC_SUPPORT_ONLY' : 'LAUNCH_CONTRACT_FAILED',
    passed: failures.length === 0,
    failures,
  };
}

const clone = value => structuredClone(value);

export function runB38AnalyzerAttacks(record, spec) {
  const baseFixture = record.fixtures[0];
  const planAttacks = [
    ['INHERITED_PARENT_ENV', 'ENVIRONMENT_KEYS', draft => { draft.process.environment[B38_PARENT_CANARY_KEY] = B38_PARENT_CANARY_VALUE; }],
    ['MISSING_ENV_KEY', 'ENVIRONMENT_KEYS', draft => { delete draft.process.environment.LANG; }],
    ['ENV_PATH_ESCAPE', 'ENVIRONMENT_VALUES', draft => { draft.process.environment.HOME = '/host/home'; }],
    ['SHELL_TRUE', 'SHELL', draft => { draft.process.shell = true; }],
    ['EXECUTABLE_IDENTITY', 'EXECUTABLE_IDENTITY', draft => { draft.process.executable.sha256 = '0'.repeat(64); }],
    ['MISSING_DISABLE_AUTOEXEC', 'DISABLE_AUTOEXEC', draft => { draft.process.argv = draft.process.argv.filter(value => value !== '--disable-autoexec'); }],
    ['ENABLE_AUTOEXEC', 'FORBIDDEN_ARGV', draft => { draft.process.argv.splice(2, 0, '--enable-autoexec'); }],
    ['MISSING_OFFLINE_MODE', 'OFFLINE_MODE', draft => { draft.process.argv = draft.process.argv.filter(value => value !== '--offline-mode'); }],
    ['ONLINE_MODE', 'FORBIDDEN_ARGV', draft => { draft.process.argv.splice(3, 0, '--online-mode'); }],
    ['PYTHON_EXIT_ZERO', 'PYTHON_EXIT_CODE', draft => { draft.process.argv[draft.process.argv.indexOf('--python-exit-code') + 1] = '0'; }],
    ['IMAGE_TAG_NOT_DIGEST', 'IMAGE_DIGEST', draft => { draft.candidatePolicy.imageReference = 'bfs/blender-worker:latest'; }],
    ['PULL_ALWAYS', 'PULL_POLICY', draft => { draft.candidatePolicy.pull = 'always'; }],
    ['INPUT_WRITABLE', 'INPUT_MOUNT', draft => { draft.mounts.find(mount => mount.id === 'INPUTS').readOnly = false; }],
    ['SECOND_WRITABLE_MOUNT', 'MOUNT_SET', draft => { draft.mounts.push({ id: 'EXTRA', sourceIdentity: 'bfs-output:extra', target: '/extra', readOnly: false }); }],
    ['DOCKER_SOCKET_MOUNT', 'DOCKER_SOCKET_MOUNT', draft => { draft.mounts.push({ id: 'SOCKET', sourceIdentity: 'bfs-input:socket', target: '/var/run/docker.sock', readOnly: false }); }],
    ['NETWORK_BRIDGE', 'NETWORK', draft => { draft.candidatePolicy.network = 'bridge'; }],
    ['PRIVILEGED', 'PRIVILEGED', draft => { draft.candidatePolicy.privileged = true; }],
    ['CAPABILITY_ADDED', 'CAPABILITIES', draft => { draft.candidatePolicy.capAdd = ['SYS_ADMIN']; }],
    ['NO_NEW_PRIVILEGES_REMOVED', 'NO_NEW_PRIVILEGES', draft => { draft.candidatePolicy.noNewPrivileges = false; }],
    ['ROOT_USER', 'NON_ROOT_USER', draft => { draft.candidatePolicy.user = '0:0'; }],
    ['WRITABLE_ROOTFS', 'READ_ONLY_ROOTFS', draft => { draft.candidatePolicy.rootFilesystemReadOnly = false; }],
    ['RESOURCE_LIMIT_REMOVED', 'RESOURCE_LIMITS', draft => { draft.candidatePolicy.memoryBytes = null; }],
  ];
  const attacks = planAttacks.map(([id, expectedFailure, mutate]) => {
    const draft = clone(baseFixture.plan);
    mutate(draft);
    const analysis = analyzeB38Plan(draft, baseFixture.request, spec);
    return { id, expectedFailure, passed: analysis.passed === false && analysis.failures.includes(expectedFailure), failures: analysis.failures };
  });
  const admissionDraft = clone(record.admissions.belowReserve);
  admissionDraft.status = 'ACCEPTED';
  admissionDraft.reasons = [];
  const admissionAnalysis = analyzeB38Admission(admissionDraft, spec);
  attacks.push({
    id: 'BELOW_RESERVE_ACCEPTED', expectedFailure: 'ADMISSION_DECISION',
    passed: admissionAnalysis.passed === false && admissionAnalysis.failures.includes('ADMISSION_DECISION'), failures: admissionAnalysis.failures,
  });
  const receiptDraft = clone(record.receipts.timed_out);
  receiptDraft.promotable = true;
  const receiptAnalysis = analyzeB38Receipt(receiptDraft, baseFixture.plan, spec);
  attacks.push({
    id: 'TIMEOUT_PROMOTABLE', expectedFailure: 'RECEIPT_PROMOTION',
    passed: receiptAnalysis.passed === false && receiptAnalysis.failures.includes('RECEIPT_PROMOTION'), failures: receiptAnalysis.failures,
  });
  const hashDraft = clone(baseFixture.plan);
  hashDraft.planHash = '0'.repeat(64);
  const hashAnalysis = analyzeB38Plan(hashDraft, baseFixture.request, spec);
  attacks.push({
    id: 'PLAN_SELF_HASH', expectedFailure: 'PLAN_SELF_HASH',
    passed: hashAnalysis.passed === false && hashAnalysis.failures.includes('PLAN_SELF_HASH'), failures: hashAnalysis.failures,
  });
  return attacks;
}

export function reverseObjectOrderDeep(value) {
  if (Array.isArray(value)) return value.map(reverseObjectOrderDeep);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).reverse().map(([key, child]) => [key, reverseObjectOrderDeep(child)]));
  }
  return value;
}
