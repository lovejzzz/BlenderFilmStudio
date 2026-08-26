import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { canonicalJson } from './receipt-format.mjs';
import { repositoryRoot, sha256 } from './scene-spec.mjs';
import {
  analyzeB40Evidence,
  classifyB40Capacity,
  hashB40Evidence,
  readB40Spec,
} from './b40-worker-host-capacity-admission.mjs';

export const B40_C1_SPEC_PATH = resolve(repositoryRoot, 'specs/worker-host-capacity-admission-correction.v0.1.json');
export const B40_C1_SPEC_SHA256 = '00f50c7ee250de2d78c9643be552b5aa5b1339463ff5d8c1c276acbc7fd0882a';
export const B40_C1_PREREG_COMMIT = 'f679c0a73d6b3cce53556452bfdf950caaf26f98';
const exact = (left, right) => canonicalJson(left) === canonicalJson(right);

export async function readB40C1Spec() {
  const bytes = await readFile(B40_C1_SPEC_PATH);
  const digest = sha256(bytes);
  if (digest !== B40_C1_SPEC_SHA256) throw new Error(`B40-C1 spec SHA mismatch: ${digest}`);
  return JSON.parse(bytes);
}

export function parseB40C1Binfmt(text, registration) {
  const value = pattern => text.match(pattern)?.[1] ?? null;
  return {
    registration,
    enabled: text.split('\n')[0]?.trim() === 'enabled',
    interpreter: value(/^interpreter\s+(.+)$/m),
    flags: value(/^flags:\s+(.+)$/m) ?? '',
  };
}

function projectB40C1ToBase(evidence, correctionSpec) {
  const projected = structuredClone(evidence);
  for (const key of ['analysis', 'attacks', 'attacksPassed', 'verdict', 'nonClaims', 'correction']) delete projected[key];
  projected.schemaVersion = 'bfs.workerHostCapacityEvidence.v0.1';
  projected.experimentId = 'B40';
  projected.preregistration = {
    commit: correctionSpec.baseProtocol.preregistrationCommit,
    specSha256: correctionSpec.baseProtocol.specSha256,
  };
  projected.evidenceHash = hashB40Evidence(projected);
  return projected;
}

export async function analyzeB40C1Evidence(evidence, correctionSpec, baseSpecInput = null) {
  const baseSpec = baseSpecInput ?? await readB40Spec();
  const failures = [];
  const gate = (condition, code) => { if (!condition && !failures.includes(code)) failures.push(code); };
  gate(evidence?.schemaVersion === 'bfs.workerHostCapacityEvidence.v0.2' && evidence?.experimentId === 'B40-C1', 'CORRECTION_EVIDENCE_SCHEMA');
  gate(evidence?.preregistration?.commit === B40_C1_PREREG_COMMIT && evidence?.preregistration?.specSha256 === B40_C1_SPEC_SHA256, 'CORRECTION_PREREGISTRATION');
  gate(evidence?.correction?.baseSpecSha256 === correctionSpec.baseProtocol.specSha256
    && evidence?.correction?.invalidResultSha256 === correctionSpec.invalidAttempt.resultSha256
    && evidence?.correction?.invalidAuditSha256 === correctionSpec.invalidAttempt.auditSha256
    && exact(evidence?.correction?.changedImplementationExact, correctionSpec.changedImplementationExact), 'CORRECTION_ANCESTRY');
  gate(evidence?.observations?.vm?.emulator?.flags === correctionSpec.changedImplementationExact.expectedParsedFlags, 'CORRECTED_FLAGS_PARSE');
  gate(evidence?.evidenceHash === hashB40Evidence(evidence), 'CORRECTION_EVIDENCE_SELF_HASH');
  const baseAnalysis = analyzeB40Evidence(projectB40C1ToBase(evidence, correctionSpec), baseSpec);
  for (const failure of baseAnalysis.failures) gate(false, failure);
  return {
    schemaVersion: 'bfs.workerHostCapacityAnalysis.v0.2',
    passed: failures.length === 0,
    failures,
    baseAnalysis,
    decision: failures[0] ?? correctionSpec.acceptedVerdict,
  };
}

const mutateAndHash = (evidence, mutate) => {
  const candidate = structuredClone(evidence);
  for (const key of ['analysis', 'attacks', 'attacksPassed', 'verdict', 'nonClaims']) delete candidate[key];
  mutate(candidate);
  candidate.evidenceHash = hashB40Evidence(candidate);
  return candidate;
};

export async function runB40C1Attacks(evidence, correctionSpec, baseSpecInput = null) {
  const baseSpec = baseSpecInput ?? await readB40Spec();
  const cases = [
    ['lower the host disk reserve', 'POLICY_IDENTITY', value => { value.policy.workerCeilings.minimumHostReserveBytes = 0; }],
    ['lower the projected host write', 'POLICY_IDENTITY', value => { value.policy.workerCeilings.projectedHostWriteBytes = 0; }],
    ['remove the infrastructure memory reserve', 'POLICY_IDENTITY', value => { value.policy.capacity.infrastructureMemoryReserveBytes = 0; value.policy.capacity.requiredVmMemoryBytes = value.policy.workerCeilings.memoryBytes; }],
    ['mark six-GiB VM memory accepted', 'CAPACITY_DECISION', value => { value.decision.gates.vmMemory.status = 'ACCEPTED'; }],
    ['remove the infrastructure CPU reserve', 'POLICY_IDENTITY', value => { value.policy.capacity.infrastructureCpuReserve = 0; value.policy.capacity.requiredVmCpus = value.policy.workerCeilings.cpus; }],
    ['mark four-CPU VM capacity accepted', 'CAPACITY_DECISION', value => { value.decision.gates.vmCpu.status = 'ACCEPTED'; }],
    ['lower the Docker storage safety floor', 'POLICY_IDENTITY', value => { value.policy.capacity.minimumDockerStorageFreeBeforeBuildBytes = 1; }],
    ['mark below-floor Docker storage accepted', 'CAPACITY_DECISION', value => { value.decision.gates.dockerStorage.status = 'ACCEPTED'; }],
    ['hide a running competing container', 'CAPACITY_DECISION', value => { value.observations.docker.runningContainerIds = ['b'.repeat(64)]; }],
    ['accept nonzero VM swap', 'VM_SWAP_GATE', value => { value.observations.vm.swapTotalBytes = '4096'; value.decision = classifyB40Capacity(value.observations, baseSpec); }],
    ['fabricate the x64 emulator registration', 'EMULATOR_REGISTRATION', value => { value.observations.vm.emulator.registration = 'rosetta-x86_64'; }],
    ['change an ancestry evidence hash', 'ANCESTRY_IDENTITY', value => { value.ancestry.b39C1ResultSha256 = '5'.repeat(64); }],
    ['claim a runtime operation executed', 'RUNTIME_OPERATION_BOUNDARY', value => { value.runtimeOperationsExecuted.push('CONTAINER_RUN'); }],
    ['mark overall admission accepted', 'CAPACITY_DECISION', value => { value.decision.status = 'ACCEPTED'; value.decision.reasons = []; }],
  ];
  if (!exact(cases.map(([name]) => name), baseSpec.frozenAnalyzerAttacks)) throw new Error('B40-C1 attack list differs from base protocol');
  return Promise.all(cases.map(async ([name, expectedFailure, mutate]) => {
    const analysis = await analyzeB40C1Evidence(mutateAndHash(evidence, mutate), correctionSpec, baseSpec);
    return { name, expectedFailure, observedFailures: analysis.failures, passed: !analysis.passed && analysis.failures.includes(expectedFailure) };
  }));
}
