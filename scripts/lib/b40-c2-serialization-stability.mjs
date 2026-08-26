import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { canonicalJson } from './receipt-format.mjs';
import { repositoryRoot, sha256 } from './scene-spec.mjs';
import { analyzeB40Evidence, classifyB40Capacity, hashB40Evidence, readB40Spec } from './b40-worker-host-capacity-admission.mjs';

export const B40_C2_SPEC_PATH = resolve(repositoryRoot, 'specs/worker-host-capacity-serialization-correction.v0.1.json');
export const B40_C2_SPEC_SHA256 = '18d945fb9b96f5369b638b7214904ca6b3d7f110d1e544680a28dc41e8d7651a';
export const B40_C2_PREREG_COMMIT = 'a117a6ccc5631e7db382a121822a88fc76511a6f';
const exact = (left, right) => canonicalJson(left) === canonicalJson(right);
const jsonRoundTrip = value => JSON.parse(JSON.stringify(value));

export async function readB40C2Spec() {
  const bytes = await readFile(B40_C2_SPEC_PATH);
  const digest = sha256(bytes);
  if (digest !== B40_C2_SPEC_SHA256) throw new Error(`B40-C2 spec SHA mismatch: ${digest}`);
  return JSON.parse(bytes);
}

export function classifyB40C2Capacity(observations, baseSpec) {
  return jsonRoundTrip(classifyB40Capacity(observations, baseSpec));
}

function projectToBase(evidence, correctionSpec) {
  const projected = structuredClone(evidence);
  for (const key of ['analysis', 'attacks', 'attacksPassed', 'verdict', 'nonClaims', 'correctionChain', 'serializationGates']) delete projected[key];
  projected.schemaVersion = 'bfs.workerHostCapacityEvidence.v0.1';
  projected.experimentId = 'B40';
  projected.preregistration = { commit: correctionSpec.baseProtocol.preregistrationCommit, specSha256: correctionSpec.baseProtocol.specSha256 };
  projected.evidenceHash = hashB40Evidence(projected);
  return projected;
}

export async function analyzeB40C2Evidence(evidence, correctionSpec, baseSpecInput = null) {
  const baseSpec = baseSpecInput ?? await readB40Spec();
  const failures = [];
  const gate = (condition, code) => { if (!condition && !failures.includes(code)) failures.push(code); };
  gate(evidence?.schemaVersion === 'bfs.workerHostCapacityEvidence.v0.3' && evidence?.experimentId === 'B40-C2', 'SERIALIZATION_EVIDENCE_SCHEMA');
  gate(evidence?.preregistration?.commit === B40_C2_PREREG_COMMIT && evidence?.preregistration?.specSha256 === B40_C2_SPEC_SHA256, 'SERIALIZATION_PREREGISTRATION');
  gate(evidence?.correctionChain?.baseSpecSha256 === correctionSpec.baseProtocol.specSha256
    && evidence?.correctionChain?.parserCorrectionSpecSha256 === correctionSpec.parserCorrection.specSha256
    && evidence?.correctionChain?.rejectedC1ResultSha256 === correctionSpec.rejectedC1.resultSha256
    && evidence?.correctionChain?.rejectedC1AuditSha256 === correctionSpec.rejectedC1.auditSha256, 'SERIALIZATION_CORRECTION_ANCESTRY');
  gate(evidence?.observations?.vm?.emulator?.flags === 'POCF', 'CORRECTED_FLAGS_PARSE');
  gate(exact(evidence?.serializationGates, correctionSpec.requiredSerializationGates), 'SERIALIZATION_GATES_RECORDED');
  gate(evidence?.serializationPassed === true, 'SERIALIZATION_RESULT_RECORDED');
  gate(evidence?.evidenceHash === hashB40Evidence(evidence), 'SERIALIZATION_EVIDENCE_SELF_HASH');
  const projected = projectToBase(evidence, correctionSpec);
  const roundTrippedProjected = projectToBase(jsonRoundTrip(evidence), correctionSpec);
  const baseAnalysis = analyzeB40Evidence(projected, baseSpec);
  const roundTripBaseAnalysis = analyzeB40Evidence(roundTrippedProjected, baseSpec);
  gate(baseAnalysis.passed, 'BASE_ANALYSIS');
  gate(exact(baseAnalysis, roundTripBaseAnalysis), 'BASE_ANALYSIS_SERIALIZATION');
  gate(exact(projected.decision, roundTrippedProjected.decision), 'DECISION_SERIALIZATION');
  gate(projected.evidenceHash === roundTrippedProjected.evidenceHash, 'EVIDENCE_HASH_SERIALIZATION');
  return {
    schemaVersion: 'bfs.workerHostCapacityAnalysis.v0.3',
    passed: failures.length === 0,
    failures,
    baseAnalysis,
    roundTripBaseAnalysis,
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

export async function runB40C2Attacks(evidence, correctionSpec, baseSpecInput = null) {
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
    ['hide a running competing container', 'CAPACITY_DECISION', value => { value.observations.docker.runningContainerIds = ['c'.repeat(64)]; }],
    ['accept nonzero VM swap', 'VM_SWAP_GATE', value => { value.observations.vm.swapTotalBytes = '4096'; value.decision = classifyB40C2Capacity(value.observations, baseSpec); }],
    ['fabricate the x64 emulator registration', 'EMULATOR_REGISTRATION', value => { value.observations.vm.emulator.registration = 'rosetta-x86_64'; }],
    ['change an ancestry evidence hash', 'ANCESTRY_IDENTITY', value => { value.ancestry.b39C1ResultSha256 = '6'.repeat(64); }],
    ['claim a runtime operation executed', 'RUNTIME_OPERATION_BOUNDARY', value => { value.runtimeOperationsExecuted.push('CONTAINER_RUN'); }],
    ['mark overall admission accepted', 'CAPACITY_DECISION', value => { value.decision.status = 'ACCEPTED'; value.decision.reasons = []; }],
  ];
  if (!exact(cases.map(([name]) => name), baseSpec.frozenAnalyzerAttacks)) throw new Error('B40-C2 attack list differs');
  const attacks = [];
  for (const [name, expectedFailure, mutate] of cases) {
    const analysis = await analyzeB40C2Evidence(mutateAndHash(evidence, mutate), correctionSpec, baseSpec);
    attacks.push({ name, expectedFailure, observedFailures: analysis.failures, passed: !analysis.passed && analysis.failures.includes(expectedFailure) });
  }
  return attacks;
}

export function roundTripB40C2(value) {
  return jsonRoundTrip(value);
}
