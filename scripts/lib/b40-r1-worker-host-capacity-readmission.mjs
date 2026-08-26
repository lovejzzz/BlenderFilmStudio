import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { canonicalJson } from './receipt-format.mjs';
import { repositoryRoot, sha256 } from './scene-spec.mjs';
import { classifyB40Capacity, hashB40Evidence, readB40Spec } from './b40-worker-host-capacity-admission.mjs';

export const B40_R1_SPEC_PATH = resolve(repositoryRoot, 'specs/worker-host-capacity-readmission.v0.1.json');
export const B40_R1_SPEC_SHA256 = '29ca949f6d9172a36df321b469050e7f7189b42ada790aa4f9bd2f6a97a131c1';
export const B40_R1_PREREG_COMMIT = '0e52704ec2e61e0868c8f44e85b0ba24333d3145';
const HEX_40 = /^[a-f0-9]{40}$/;
const HEX_64 = /^[a-f0-9]{64}$/;
const exact = (left, right) => canonicalJson(left) === canonicalJson(right);

export async function readB40R1Spec() {
  const bytes = await readFile(B40_R1_SPEC_PATH);
  const digest = sha256(bytes);
  if (digest !== B40_R1_SPEC_SHA256) throw new Error(`B40-R1 spec SHA mismatch: ${digest}`);
  return JSON.parse(bytes);
}

export function roundTripB40R1(value) {
  return JSON.parse(JSON.stringify(value));
}

export async function analyzeB40R1Evidence(evidence, readmissionSpecInput = null, baseSpecInput = null) {
  const spec = readmissionSpecInput ?? await readB40R1Spec();
  const baseSpec = baseSpecInput ?? await readB40Spec();
  const failures = [];
  const gate = (condition, code) => { if (!condition && !failures.includes(code)) failures.push(code); };
  gate(evidence?.schemaVersion === 'bfs.workerHostCapacityReadmissionEvidence.v0.1'
    && evidence?.experimentId === 'B40-R1', 'EVIDENCE_SCHEMA');
  gate(evidence?.preregistration?.commit === B40_R1_PREREG_COMMIT
    && evidence?.preregistration?.specSha256 === B40_R1_SPEC_SHA256, 'PREREGISTRATION_IDENTITY');
  gate(exact(evidence?.ancestry, spec.ancestry), 'ANCESTRY_IDENTITY');
  gate(HEX_40.test(evidence?.toolFreezeCommit ?? ''), 'TOOL_FREEZE_IDENTITY');
  gate(evidence?.runtime?.nodeVersion === spec.runtime.nodeVersion
    && evidence?.runtime?.nodeBinary === spec.runtime.nodeBinary
    && evidence?.runtime?.nodeBinarySha256 === spec.runtime.nodeBinarySha256, 'RUNTIME_IDENTITY');
  gate(['runner', 'library', 'audit'].every(key => HEX_64.test(evidence?.tools?.[key]?.sha256 ?? '')), 'TOOL_IDENTITY');
  gate(exact(evidence?.policy, {
    workerCeilings: baseSpec.frozenWorkerCeilingsFromB38,
    capacity: baseSpec.capacityPolicy,
  }), 'POLICY_IDENTITY');
  gate(exact(evidence?.probeTrace, spec.probeTraceExact), 'PROBE_TRACE');
  gate(Array.isArray(evidence?.runtimeOperationsExecuted) && evidence.runtimeOperationsExecuted.length === 0, 'RUNTIME_OPERATION_BOUNDARY');
  gate(evidence?.observations?.host?.architecture === spec.runtime.hostArchitecture, 'HOST_ARCHITECTURE');
  gate(/^[0-9]+$/.test(evidence?.observations?.host?.availableBytes ?? ''), 'HOST_DISK_OBSERVATION');
  const colima = evidence?.observations?.colima ?? {};
  gate(colima?.status?.driver === 'macOS Virtualization.Framework'
    && colima?.status?.arch === 'aarch64'
    && colima?.status?.runtime === 'docker'
    && colima?.config?.arch === 'aarch64'
    && colima?.config?.vmType === 'vz'
    && colima?.config?.rosetta === false, 'COLIMA_IDENTITY');
  gate(Number.isInteger(evidence?.observations?.vm?.onlineCpus) && evidence.observations.vm.onlineCpus > 0, 'VM_CPU_OBSERVATION');
  gate(/^[0-9]+$/.test(evidence?.observations?.vm?.memTotalBytes ?? '')
    && /^[0-9]+$/.test(evidence?.observations?.vm?.swapTotalBytes ?? ''), 'VM_MEMORY_OBSERVATION');
  gate(['totalBytes', 'usedBytes', 'availableBytes'].every(key => /^[0-9]+$/.test(evidence?.observations?.vm?.dockerStorage?.[key] ?? '')), 'DOCKER_STORAGE_OBSERVATION');
  gate(evidence?.observations?.vm?.emulator?.registration === baseSpec.capacityPolicy.requiredEmulator.registration, 'EMULATOR_REGISTRATION');
  gate(Array.isArray(evidence?.observations?.docker?.runningContainerIds), 'CONTAINER_OBSERVATION');
  let expectedDecision = null;
  try { expectedDecision = classifyB40Capacity(evidence.observations, baseSpec); } catch { gate(false, 'CAPACITY_INPUT'); }
  gate(expectedDecision !== null && exact(evidence?.decision, expectedDecision), 'CAPACITY_DECISION');
  if (expectedDecision) {
    for (const key of ['hostDisk', 'vmMemory', 'vmCpu', 'dockerStorage', 'vmSwap', 'x64Emulator', 'competingContainers']) {
      const code = `${key.replace(/([A-Z])/g, '_$1').toUpperCase()}_GATE`;
      gate(expectedDecision.gates[key].status === spec.expectedCurrentGates[key], code);
    }
    gate(expectedDecision.status === spec.expectedCurrentGates.overall
      && exact(expectedDecision.reasons, spec.expectedCurrentGates.blockedReasonsExact), 'OVERALL_GATE');
  }
  gate(evidence?.replayPassed === true, 'REPLAY_RESULT_RECORDED');
  gate(evidence?.evidenceHash === hashB40Evidence(evidence), 'EVIDENCE_SELF_HASH');
  return {
    schemaVersion: 'bfs.workerHostCapacityReadmissionAnalysis.v0.1',
    passed: failures.length === 0,
    failures,
    decision: failures[0] ?? spec.acceptedVerdict,
  };
}

const mutateEvidence = (evidence, mutate, rehash = true) => {
  const candidate = structuredClone(evidence);
  for (const key of ['analysis', 'attacks', 'attacksPassed', 'verdict', 'nonClaims']) delete candidate[key];
  mutate(candidate);
  if (rehash) candidate.evidenceHash = hashB40Evidence(candidate);
  return candidate;
};

export async function runB40R1Attacks(evidence, readmissionSpecInput = null, baseSpecInput = null) {
  const spec = readmissionSpecInput ?? await readB40R1Spec();
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
    ['mark replay failed after hashing', 'REPLAY_RESULT_RECORDED', value => { value.replayPassed = false; }, false],
  ];
  if (!exact(cases.map(([name]) => name), spec.frozenAnalyzerAttacks)) throw new Error('B40-R1 attack list differs');
  const attacks = [];
  for (const [name, expectedFailure, mutate, rehash] of cases) {
    const analysis = await analyzeB40R1Evidence(mutateEvidence(evidence, mutate, rehash !== false), spec, baseSpec);
    attacks.push({ name, expectedFailure, observedFailures: analysis.failures, passed: !analysis.passed && analysis.failures.includes(expectedFailure) });
  }
  return attacks;
}

export { classifyB40Capacity, hashB40Evidence };
