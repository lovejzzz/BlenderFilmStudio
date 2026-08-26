import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { canonicalJson } from './receipt-format.mjs';
import { repositoryRoot, sha256 } from './scene-spec.mjs';
import { classifyB40Capacity, hashB40Evidence, readB40Spec } from './b40-worker-host-capacity-admission.mjs';
import {
  B40_R1_PREREG_COMMIT, B40_R1_SPEC_SHA256, analyzeB40R1Evidence, readB40R1Spec, roundTripB40R1,
} from './b40-r1-worker-host-capacity-readmission.mjs';

export const B40_R2_SPEC_PATH = resolve(repositoryRoot, 'specs/worker-host-capacity-readmission-replay-correction.v0.1.json');
export const B40_R2_SPEC_SHA256 = 'c8c4f3e5cbe79c2b070fc52d8e65f01faf5bc9c6d5ff30f41a7d79f29735d732';
export const B40_R2_PREREG_COMMIT = '47fdbeb95c77786369b85a7ed56b993a11127e31';
const exact = (left, right) => canonicalJson(left) === canonicalJson(right);

export async function readB40R2Spec() {
  const bytes = await readFile(B40_R2_SPEC_PATH);
  const digest = sha256(bytes);
  if (digest !== B40_R2_SPEC_SHA256) throw new Error(`B40-R2 spec SHA mismatch: ${digest}`);
  return JSON.parse(bytes);
}

function projectToR1(evidence) {
  const projected = structuredClone(evidence);
  for (const key of ['analysis', 'attacks', 'attacksPassed', 'verdict', 'nonClaims', 'replayCorrection', 'replayDiagnostics']) delete projected[key];
  projected.schemaVersion = 'bfs.workerHostCapacityReadmissionEvidence.v0.1';
  projected.experimentId = 'B40-R1';
  projected.preregistration = { commit: B40_R1_PREREG_COMMIT, specSha256: B40_R1_SPEC_SHA256 };
  projected.evidenceHash = hashB40Evidence(projected);
  return projected;
}

export async function analyzeB40R2Evidence(evidence, r2SpecInput = null, r1SpecInput = null, baseSpecInput = null) {
  const r2Spec = r2SpecInput ?? await readB40R2Spec();
  const r1Spec = r1SpecInput ?? await readB40R1Spec();
  const baseSpec = baseSpecInput ?? await readB40Spec();
  const failures = [];
  const gate = (condition, code) => { if (!condition && !failures.includes(code)) failures.push(code); };
  gate(evidence?.schemaVersion === 'bfs.workerHostCapacityReadmissionEvidence.v0.2'
    && evidence?.experimentId === 'B40-R2', 'REPLAY_CORRECTION_EVIDENCE_SCHEMA');
  gate(evidence?.preregistration?.commit === B40_R2_PREREG_COMMIT
    && evidence?.preregistration?.specSha256 === B40_R2_SPEC_SHA256, 'REPLAY_CORRECTION_PREREGISTRATION');
  gate(evidence?.replayCorrection?.r1SpecSha256 === r2Spec.r1.specSha256
    && evidence?.replayCorrection?.r1PreregistrationCommit === r2Spec.r1.preregistrationCommit
    && evidence?.replayCorrection?.r1ToolFreezeCommit === r2Spec.r1.toolFreezeCommit
    && evidence?.replayCorrection?.failedResultSha256 === r2Spec.r1.failedResultSha256
    && evidence?.replayCorrection?.failedAuditSha256 === r2Spec.r1.failedAuditSha256
    && exact(evidence?.replayCorrection?.changedImplementationExact, r2Spec.changedImplementationExact), 'REPLAY_CORRECTION_ANCESTRY');
  const diagnostics = evidence?.replayDiagnostics ?? {};
  gate(exact(Object.keys(diagnostics), r2Spec.requiredReplayDiagnostics), 'REPLAY_DIAGNOSTIC_SCHEMA');
  gate(diagnostics.evidenceCanonicalEqual === true, 'EVIDENCE_CANONICAL_REPLAY');
  gate(diagnostics.analysisEqual === true, 'ANALYSIS_REPLAY');
  gate(diagnostics.attackVectorEqual === true, 'ATTACK_VECTOR_REPLAY');
  gate(evidence?.replayPassed === true
    && diagnostics.evidenceCanonicalEqual === true
    && diagnostics.analysisEqual === true
    && diagnostics.attackVectorEqual === true, 'REPLAY_RESULT_RECORDED');
  gate(evidence?.evidenceHash === hashB40Evidence(evidence), 'REPLAY_CORRECTION_EVIDENCE_SELF_HASH');
  const r1Analysis = await analyzeB40R1Evidence(projectToR1(evidence), r1Spec, baseSpec);
  for (const failure of r1Analysis.failures) gate(false, failure);
  return {
    schemaVersion: 'bfs.workerHostCapacityReadmissionAnalysis.v0.2', passed: failures.length === 0,
    failures, r1Analysis, decision: failures[0] ?? r2Spec.acceptedVerdict,
  };
}

const mutateEvidence = (evidence, mutate, rehash = true) => {
  const candidate = structuredClone(evidence);
  for (const key of ['analysis', 'attacks', 'attacksPassed', 'verdict', 'nonClaims']) delete candidate[key];
  mutate(candidate);
  if (rehash) candidate.evidenceHash = hashB40Evidence(candidate);
  return candidate;
};

export async function runB40R2Attacks(evidence, r2SpecInput = null, r1SpecInput = null, baseSpecInput = null) {
  const r2Spec = r2SpecInput ?? await readB40R2Spec();
  const r1Spec = r1SpecInput ?? await readB40R1Spec();
  const baseSpec = baseSpecInput ?? await readB40Spec();
  const worker = baseSpec.frozenWorkerCeilingsFromB38;
  const policy = baseSpec.capacityPolicy;
  const belowHostFloor = String(BigInt(worker.projectedHostWriteBytes) + BigInt(worker.minimumHostReserveBytes) - 1n);
  const belowMemoryFloor = String(BigInt(policy.requiredVmMemoryBytes) - 1n);
  const belowDockerFloor = String(BigInt(policy.minimumDockerStorageFreeBeforeBuildBytes) - 1n);
  const cases = [
    ['lower the host disk reserve', 'POLICY_IDENTITY', value => { value.policy.workerCeilings.minimumHostReserveBytes = 0; }],
    ['lower the projected host write', 'POLICY_IDENTITY', value => { value.policy.workerCeilings.projectedHostWriteBytes = 0; }],
    ['lower host free space without recomputing the decision', 'CAPACITY_DECISION', value => { value.observations.host.availableBytes = belowHostFloor; }],
    ['lower host free space and recompute the decision', 'HOST_DISK_GATE', value => { value.observations.host.availableBytes = belowHostFloor; value.decision = classifyB40Capacity(value.observations, baseSpec); }],
    ['lower VM memory without recomputing the decision', 'CAPACITY_DECISION', value => { value.observations.vm.memTotalBytes = belowMemoryFloor; }],
    ['lower VM memory and recompute the decision', 'VM_MEMORY_GATE', value => { value.observations.vm.memTotalBytes = belowMemoryFloor; value.decision = classifyB40Capacity(value.observations, baseSpec); }],
    ['lower VM CPUs without recomputing the decision', 'CAPACITY_DECISION', value => { value.observations.vm.onlineCpus = policy.requiredVmCpus - 1; }],
    ['lower VM CPUs and recompute the decision', 'VM_CPU_GATE', value => { value.observations.vm.onlineCpus = policy.requiredVmCpus - 1; value.decision = classifyB40Capacity(value.observations, baseSpec); }],
    ['lower Docker free space without recomputing the decision', 'CAPACITY_DECISION', value => { value.observations.vm.dockerStorage.availableBytes = belowDockerFloor; }],
    ['lower Docker free space and recompute the decision', 'DOCKER_STORAGE_GATE', value => { value.observations.vm.dockerStorage.availableBytes = belowDockerFloor; value.decision = classifyB40Capacity(value.observations, baseSpec); }],
    ['add a running container and recompute the decision', 'COMPETING_CONTAINERS_GATE', value => { value.observations.docker.runningContainerIds = ['a'.repeat(64)]; value.decision = classifyB40Capacity(value.observations, baseSpec); }],
    ['add nonzero swap and recompute the decision', 'VM_SWAP_GATE', value => { value.observations.vm.swapTotalBytes = '4096'; value.decision = classifyB40Capacity(value.observations, baseSpec); }],
    ['fabricate the x64 emulator registration', 'EMULATOR_REGISTRATION', value => { value.observations.vm.emulator.registration = 'rosetta-x86_64'; }],
    ['change the B40-C5 evidence hash', 'ANCESTRY_IDENTITY', value => { value.ancestry.b40C5ResultSha256 = '9'.repeat(64); }],
    ['claim a runtime operation executed', 'RUNTIME_OPERATION_BOUNDARY', value => { value.runtimeOperationsExecuted.push('CONTAINER_RUN'); }],
    ['mark replay failed after hashing', 'REPLAY_RESULT_RECORDED', value => { value.replayPassed = false; value.replayDiagnostics.attackVectorEqual = false; }, false],
  ];
  if (!exact(cases.map(([name]) => name), r1Spec.frozenAnalyzerAttacks)) throw new Error('B40-R2 attack list differs from R1');
  const attacks = [];
  for (const [name, expectedFailure, mutate, rehash] of cases) {
    const analysis = await analyzeB40R2Evidence(mutateEvidence(evidence, mutate, rehash !== false), r2Spec, r1Spec, baseSpec);
    attacks.push({ name, expectedFailure, observedFailures: analysis.failures, passed: !analysis.passed && analysis.failures.includes(expectedFailure) });
  }
  return attacks;
}

export { hashB40Evidence, roundTripB40R1 as roundTripB40R2 };
