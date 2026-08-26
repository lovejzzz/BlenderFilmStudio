import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { canonicalJson } from './receipt-format.mjs';
import { repositoryRoot, sha256 } from './scene-spec.mjs';
import { hashB40Evidence, readB40Spec } from './b40-worker-host-capacity-admission.mjs';
import { classifyB40C2Capacity, readB40C2Spec, roundTripB40C2 } from './b40-c2-serialization-stability.mjs';
import {
  B40_C4_PREREG_COMMIT, B40_C4_SPEC_SHA256, analyzeB40C4Evidence, readB40C4Spec,
} from './b40-c4-projection-identity.mjs';

export const B40_C5_SPEC_PATH = resolve(repositoryRoot, 'specs/worker-host-capacity-result-field-correction.v0.1.json');
export const B40_C5_SPEC_SHA256 = 'a87c3290d6512815b8912789e8a517c9009584c45b69aaf01618c7c26693021c';
export const B40_C5_PREREG_COMMIT = '1869f679bd6486192a6f0cc4f354c07022135e06';
const exact = (left, right) => canonicalJson(left) === canonicalJson(right);

export async function readB40C5Spec() {
  const bytes = await readFile(B40_C5_SPEC_PATH);
  const digest = sha256(bytes);
  if (digest !== B40_C5_SPEC_SHA256) throw new Error(`B40-C5 spec SHA mismatch: ${digest}`);
  return JSON.parse(bytes);
}

function projectToC4(evidence) {
  const projected = structuredClone(evidence);
  for (const key of ['analysis', 'attacks', 'attacksPassed', 'verdict', 'nonClaims', 'resultFieldCorrection']) delete projected[key];
  projected.schemaVersion = 'bfs.workerHostCapacityEvidence.v0.5';
  projected.experimentId = 'B40-C4';
  projected.preregistration = { commit: B40_C4_PREREG_COMMIT, specSha256: B40_C4_SPEC_SHA256 };
  projected.evidenceHash = hashB40Evidence(projected);
  return projected;
}

export async function analyzeB40C5Evidence(evidence, c5Spec, c4SpecInput = null, c2SpecInput = null, baseSpecInput = null) {
  const c4Spec = c4SpecInput ?? await readB40C4Spec();
  const c2Spec = c2SpecInput ?? await readB40C2Spec();
  const baseSpec = baseSpecInput ?? await readB40Spec();
  const failures = [];
  const gate = (condition, code) => { if (!condition && !failures.includes(code)) failures.push(code); };
  gate(evidence?.schemaVersion === 'bfs.workerHostCapacityEvidence.v0.6' && evidence?.experimentId === 'B40-C5', 'RESULT_FIELD_EVIDENCE_SCHEMA');
  gate(evidence?.preregistration?.commit === B40_C5_PREREG_COMMIT && evidence?.preregistration?.specSha256 === B40_C5_SPEC_SHA256, 'RESULT_FIELD_PREREGISTRATION');
  gate(evidence?.resultFieldCorrection?.c4SpecSha256 === c5Spec.c4.specSha256
    && evidence?.resultFieldCorrection?.c4ResultSha256 === c5Spec.c4.resultSha256
    && evidence?.resultFieldCorrection?.c4AuditSha256 === c5Spec.c4.auditSha256
    && exact(evidence?.resultFieldCorrection?.changedImplementationExact, c5Spec.changedImplementationExact), 'RESULT_FIELD_CORRECTION_ANCESTRY');
  gate(evidence?.replayPassed === true, 'REPLAY_RESULT_RECORDED');
  gate(evidence?.evidenceHash === hashB40Evidence(evidence), 'RESULT_FIELD_EVIDENCE_SELF_HASH');
  const c4Analysis = await analyzeB40C4Evidence(projectToC4(evidence), c4Spec, c2Spec, baseSpec);
  for (const failure of c4Analysis.failures) gate(false, failure);
  return { schemaVersion: 'bfs.workerHostCapacityAnalysis.v0.6', passed: failures.length === 0, failures, c4Analysis, decision: failures[0] ?? c5Spec.acceptedVerdict };
}

const mutateAndHash = (evidence, mutate) => {
  const candidate = structuredClone(evidence);
  for (const key of ['analysis', 'attacks', 'attacksPassed', 'verdict', 'nonClaims']) delete candidate[key];
  mutate(candidate);
  candidate.evidenceHash = hashB40Evidence(candidate);
  return candidate;
};

export async function runB40C5Attacks(evidence, c5Spec, c4SpecInput = null, c2SpecInput = null, baseSpecInput = null) {
  const c4Spec = c4SpecInput ?? await readB40C4Spec();
  const c2Spec = c2SpecInput ?? await readB40C2Spec();
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
    ['hide a running competing container', 'CAPACITY_DECISION', value => { value.observations.docker.runningContainerIds = ['f'.repeat(64)]; }],
    ['accept nonzero VM swap', 'VM_SWAP_GATE', value => { value.observations.vm.swapTotalBytes = '4096'; value.decision = classifyB40C2Capacity(value.observations, baseSpec); }],
    ['fabricate the x64 emulator registration', 'EMULATOR_REGISTRATION', value => { value.observations.vm.emulator.registration = 'rosetta-x86_64'; }],
    ['change an ancestry evidence hash', 'ANCESTRY_IDENTITY', value => { value.ancestry.b39C1ResultSha256 = '9'.repeat(64); }],
    ['claim a runtime operation executed', 'RUNTIME_OPERATION_BOUNDARY', value => { value.runtimeOperationsExecuted.push('CONTAINER_RUN'); }],
    ['mark overall admission accepted', 'CAPACITY_DECISION', value => { value.decision.status = 'ACCEPTED'; value.decision.reasons = []; }],
  ];
  if (!exact(cases.map(([name]) => name), baseSpec.frozenAnalyzerAttacks)) throw new Error('B40-C5 attack list differs');
  const attacks = [];
  for (const [name, expectedFailure, mutate] of cases) {
    const analysis = await analyzeB40C5Evidence(mutateAndHash(evidence, mutate), c5Spec, c4Spec, c2Spec, baseSpec);
    attacks.push({ name, expectedFailure, observedFailures: analysis.failures, passed: !analysis.passed && analysis.failures.includes(expectedFailure) });
  }
  return attacks;
}

export { classifyB40C2Capacity, roundTripB40C2 };
