import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { canonicalJson } from './receipt-format.mjs';
import { repositoryRoot, sha256 } from './scene-spec.mjs';
import { hashB40Evidence, readB40Spec } from './b40-worker-host-capacity-admission.mjs';
import {
  B40_C2_PREREG_COMMIT, B40_C2_SPEC_SHA256, analyzeB40C2Evidence,
  classifyB40C2Capacity, readB40C2Spec, roundTripB40C2,
} from './b40-c2-serialization-stability.mjs';

export const B40_C4_SPEC_PATH = resolve(repositoryRoot, 'specs/worker-host-capacity-projection-identity-correction.v0.1.json');
export const B40_C4_SPEC_SHA256 = '33940601ecd966741054d33bc3b68ba2555750b7993e6c7b6fa3e776964ef434';
export const B40_C4_PREREG_COMMIT = '78fc415e52b885bbd31ef79336f7cc17b9d7badc';
const exact = (left, right) => canonicalJson(left) === canonicalJson(right);

export async function readB40C4Spec() {
  const bytes = await readFile(B40_C4_SPEC_PATH);
  const digest = sha256(bytes);
  if (digest !== B40_C4_SPEC_SHA256) throw new Error(`B40-C4 spec SHA mismatch: ${digest}`);
  return JSON.parse(bytes);
}

function projectToC2(evidence) {
  const projected = structuredClone(evidence);
  for (const key of ['analysis', 'attacks', 'attacksPassed', 'verdict', 'nonClaims', 'failureProjectionCorrection', 'projectionIdentityCorrection']) delete projected[key];
  projected.schemaVersion = 'bfs.workerHostCapacityEvidence.v0.3';
  projected.experimentId = 'B40-C2';
  projected.preregistration = { commit: B40_C2_PREREG_COMMIT, specSha256: B40_C2_SPEC_SHA256 };
  projected.evidenceHash = hashB40Evidence(projected);
  return projected;
}

export async function analyzeB40C4Evidence(evidence, c4Spec, c2SpecInput = null, baseSpecInput = null) {
  const c2Spec = c2SpecInput ?? await readB40C2Spec();
  const baseSpec = baseSpecInput ?? await readB40Spec();
  const failures = [];
  const gate = (condition, code) => { if (!condition && !failures.includes(code)) failures.push(code); };
  gate(evidence?.schemaVersion === 'bfs.workerHostCapacityEvidence.v0.5' && evidence?.experimentId === 'B40-C4', 'IDENTITY_EVIDENCE_SCHEMA');
  gate(evidence?.preregistration?.commit === B40_C4_PREREG_COMMIT && evidence?.preregistration?.specSha256 === B40_C4_SPEC_SHA256, 'IDENTITY_PREREGISTRATION');
  gate(evidence?.projectionIdentityCorrection?.c3SpecSha256 === c4Spec.c3Protocol.specSha256
    && evidence?.projectionIdentityCorrection?.c3ToolFreezeCommit === c4Spec.c3Protocol.toolFreezeCommit
    && exact(evidence?.projectionIdentityCorrection?.changedImplementationExact, c4Spec.changedImplementationExact), 'IDENTITY_CORRECTION_ANCESTRY');
  gate(evidence?.evidenceHash === hashB40Evidence(evidence), 'IDENTITY_EVIDENCE_SELF_HASH');
  const c2Analysis = await analyzeB40C2Evidence(projectToC2(evidence), c2Spec, baseSpec);
  for (const failure of c2Analysis.failures.filter(code => code !== 'BASE_ANALYSIS')) gate(false, failure);
  if (!c2Analysis.baseAnalysis.passed) {
    for (const failure of c2Analysis.baseAnalysis.failures) gate(false, failure);
    gate(false, 'BASE_ANALYSIS');
  }
  return { schemaVersion: 'bfs.workerHostCapacityAnalysis.v0.5', passed: failures.length === 0, failures, c2Analysis, decision: failures[0] ?? c4Spec.acceptedVerdict };
}

const mutateAndHash = (evidence, mutate) => {
  const candidate = structuredClone(evidence);
  for (const key of ['analysis', 'attacks', 'attacksPassed', 'verdict', 'nonClaims']) delete candidate[key];
  mutate(candidate);
  candidate.evidenceHash = hashB40Evidence(candidate);
  return candidate;
};

export async function runB40C4Attacks(evidence, c4Spec, c2SpecInput = null, baseSpecInput = null) {
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
    ['hide a running competing container', 'CAPACITY_DECISION', value => { value.observations.docker.runningContainerIds = ['e'.repeat(64)]; }],
    ['accept nonzero VM swap', 'VM_SWAP_GATE', value => { value.observations.vm.swapTotalBytes = '4096'; value.decision = classifyB40C2Capacity(value.observations, baseSpec); }],
    ['fabricate the x64 emulator registration', 'EMULATOR_REGISTRATION', value => { value.observations.vm.emulator.registration = 'rosetta-x86_64'; }],
    ['change an ancestry evidence hash', 'ANCESTRY_IDENTITY', value => { value.ancestry.b39C1ResultSha256 = '8'.repeat(64); }],
    ['claim a runtime operation executed', 'RUNTIME_OPERATION_BOUNDARY', value => { value.runtimeOperationsExecuted.push('CONTAINER_RUN'); }],
    ['mark overall admission accepted', 'CAPACITY_DECISION', value => { value.decision.status = 'ACCEPTED'; value.decision.reasons = []; }],
  ];
  if (!exact(cases.map(([name]) => name), baseSpec.frozenAnalyzerAttacks)) throw new Error('B40-C4 attack list differs');
  const attacks = [];
  for (const [name, expectedFailure, mutate] of cases) {
    const analysis = await analyzeB40C4Evidence(mutateAndHash(evidence, mutate), c4Spec, c2Spec, baseSpec);
    attacks.push({ name, expectedFailure, observedFailures: analysis.failures, passed: !analysis.passed && analysis.failures.includes(expectedFailure) });
  }
  return attacks;
}

export { classifyB40C2Capacity, roundTripB40C2 };
