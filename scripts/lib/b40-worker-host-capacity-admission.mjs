import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { canonicalJson, sha256Canonical } from './receipt-format.mjs';
import { repositoryRoot, sha256 } from './scene-spec.mjs';

export const B40_SPEC_PATH = resolve(repositoryRoot, 'specs/worker-host-capacity-admission.v0.1.json');
export const B40_SPEC_SHA256 = 'fd21c27801a83f542a4aaa498fbc61867b3116509bb6e43769d83873146850ca';
export const B40_PREREG_COMMIT = '8c39b715e7e2bacae81ca1ab9b2570472cf73fde';
const HEX_64 = /^[a-f0-9]{64}$/;
const exact = (left, right) => canonicalJson(left) === canonicalJson(right);

export async function readB40Spec() {
  const bytes = await readFile(B40_SPEC_PATH);
  const digest = sha256(bytes);
  if (digest !== B40_SPEC_SHA256) throw new Error(`B40 spec SHA mismatch: ${digest}`);
  return JSON.parse(bytes);
}

export function hashB40Evidence(evidence) {
  const copy = structuredClone(evidence);
  for (const key of ['evidenceHash', 'analysis', 'attacks', 'attacksPassed', 'verdict', 'nonClaims']) delete copy[key];
  return sha256Canonical(copy);
}

const decimal = (value, label) => {
  if (typeof value !== 'string' || !/^[0-9]+$/.test(value)) throw new Error(`${label} must be a decimal string`);
  return BigInt(value);
};

export function classifyB40Capacity(observations, spec) {
  const policy = spec.capacityPolicy;
  const ceilings = spec.frozenWorkerCeilingsFromB38;
  const hostAvailable = decimal(observations.host.availableBytes, 'host available');
  const projected = BigInt(ceilings.projectedHostWriteBytes);
  const hostReserve = BigInt(ceilings.minimumHostReserveBytes);
  const hostFreeAfterProjected = hostAvailable - projected;
  const vmMemory = decimal(observations.vm.memTotalBytes, 'VM memory');
  const vmSwap = decimal(observations.vm.swapTotalBytes, 'VM swap');
  const dockerFree = decimal(observations.vm.dockerStorage.availableBytes, 'Docker storage');
  const reasons = [];
  const gate = (id, accepted, observed, required) => {
    if (!accepted) reasons.push(id);
    return { status: accepted ? 'ACCEPTED' : 'BLOCKED', observed, required };
  };
  const gates = {
    hostDisk: gate('HOST_DISK_RESERVE', hostFreeAfterProjected >= hostReserve, observations.host.availableBytes, {
      projectedWriteBytes: String(projected), minimumReserveBytes: String(hostReserve), freeAfterProjectedBytes: String(hostFreeAfterProjected),
    }),
    vmMemory: gate('VM_MEMORY_CAPACITY', vmMemory >= BigInt(policy.requiredVmMemoryBytes), observations.vm.memTotalBytes, String(policy.requiredVmMemoryBytes)),
    vmCpu: gate('VM_CPU_CAPACITY', observations.vm.onlineCpus >= policy.requiredVmCpus, observations.vm.onlineCpus, policy.requiredVmCpus),
    dockerStorage: gate('DOCKER_STORAGE_CAPACITY', dockerFree >= BigInt(policy.minimumDockerStorageFreeBeforeBuildBytes), observations.vm.dockerStorage.availableBytes, String(policy.minimumDockerStorageFreeBeforeBuildBytes)),
    vmSwap: gate('VM_SWAP_POLICY', vmSwap === BigInt(policy.requiredVmSwapBytes), observations.vm.swapTotalBytes, String(policy.requiredVmSwapBytes)),
    x64Emulator: gate('X64_EMULATOR', observations.vm.emulator.enabled === policy.requiredEmulator.enabled
      && observations.vm.emulator.interpreter === policy.requiredEmulator.interpreter
      && observations.vm.emulator.flags.includes(policy.requiredEmulator.requiredFlags), observations.vm.emulator, policy.requiredEmulator),
    competingContainers: gate('COMPETING_CONTAINERS', observations.docker.runningContainerIds.length === policy.requiredRunningContainerCount, observations.docker.runningContainerIds.length, policy.requiredRunningContainerCount),
  };
  return {
    schemaVersion: 'bfs.workerHostCapacityDecision.v0.1',
    status: reasons.length === 0 ? 'ACCEPTED' : 'BLOCKED',
    reasons,
    gates,
  };
}

export function analyzeB40Evidence(evidence, spec) {
  const failures = [];
  const gate = (condition, code) => { if (!condition && !failures.includes(code)) failures.push(code); };
  gate(evidence?.schemaVersion === 'bfs.workerHostCapacityEvidence.v0.1' && evidence?.experimentId === 'B40', 'EVIDENCE_SCHEMA');
  gate(evidence?.preregistration?.commit === B40_PREREG_COMMIT && evidence?.preregistration?.specSha256 === B40_SPEC_SHA256, 'PREREGISTRATION_IDENTITY');
  gate(exact(evidence?.ancestry, spec.ancestry), 'ANCESTRY_IDENTITY');
  gate(evidence?.runtime?.nodeVersion === spec.runtime.nodeVersion
    && evidence?.runtime?.nodeBinary === spec.runtime.nodeBinary
    && evidence?.runtime?.nodeBinarySha256 === spec.runtime.nodeBinarySha256, 'RUNTIME_IDENTITY');
  gate(['runner', 'library', 'audit'].every(key => HEX_64.test(evidence?.tools?.[key]?.sha256 ?? '')), 'TOOL_IDENTITY');
  gate(exact(evidence?.policy, {
    workerCeilings: spec.frozenWorkerCeilingsFromB38,
    capacity: spec.capacityPolicy,
  }), 'POLICY_IDENTITY');
  gate(exact(evidence?.probeTrace, spec.probeTraceExact), 'PROBE_TRACE');
  gate(Array.isArray(evidence?.runtimeOperationsExecuted) && evidence.runtimeOperationsExecuted.length === 0, 'RUNTIME_OPERATION_BOUNDARY');
  gate(evidence?.observations?.host?.architecture === spec.runtime.hostArchitecture, 'HOST_ARCHITECTURE');
  gate(typeof evidence?.observations?.host?.availableBytes === 'string', 'HOST_DISK_OBSERVATION');
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
  gate(evidence?.observations?.vm?.emulator?.registration === spec.capacityPolicy.requiredEmulator.registration, 'EMULATOR_REGISTRATION');
  gate(Array.isArray(evidence?.observations?.docker?.runningContainerIds), 'CONTAINER_OBSERVATION');
  let expectedDecision = null;
  try { expectedDecision = classifyB40Capacity(evidence.observations, spec); } catch { gate(false, 'CAPACITY_INPUT'); }
  gate(expectedDecision !== null && exact(evidence?.decision, expectedDecision), 'CAPACITY_DECISION');
  if (expectedDecision) {
    gate(expectedDecision.gates.hostDisk.status === spec.expectedCurrentGates.hostDisk, 'HOST_DISK_GATE');
    gate(expectedDecision.gates.vmMemory.status === spec.expectedCurrentGates.vmMemory, 'VM_MEMORY_GATE');
    gate(expectedDecision.gates.vmCpu.status === spec.expectedCurrentGates.vmCpu, 'VM_CPU_GATE');
    gate(expectedDecision.gates.dockerStorage.status === spec.expectedCurrentGates.dockerStorage, 'DOCKER_STORAGE_GATE');
    gate(expectedDecision.gates.vmSwap.status === spec.expectedCurrentGates.vmSwap, 'VM_SWAP_GATE');
    gate(expectedDecision.gates.x64Emulator.status === spec.expectedCurrentGates.x64Emulator, 'EMULATOR_GATE');
    gate(expectedDecision.gates.competingContainers.status === spec.expectedCurrentGates.competingContainers, 'CONTAINER_GATE');
    gate(expectedDecision.status === spec.expectedCurrentGates.overall && exact(expectedDecision.reasons, spec.expectedCurrentGates.blockedReasonsExact), 'OVERALL_GATE');
  }
  gate(evidence?.evidenceHash === hashB40Evidence(evidence), 'EVIDENCE_SELF_HASH');
  return {
    schemaVersion: 'bfs.workerHostCapacityAnalysis.v0.1',
    passed: failures.length === 0,
    failures,
    decision: failures[0] ?? spec.acceptedVerdict,
  };
}

const mutateAndHash = (evidence, mutate) => {
  const candidate = structuredClone(evidence);
  for (const key of ['analysis', 'attacks', 'attacksPassed', 'verdict', 'nonClaims']) delete candidate[key];
  mutate(candidate);
  candidate.evidenceHash = hashB40Evidence(candidate);
  return candidate;
};

export function runB40Attacks(evidence, spec) {
  const cases = [
    ['lower the host disk reserve', 'POLICY_IDENTITY', value => { value.policy.workerCeilings.minimumHostReserveBytes = 0; }],
    ['lower the projected host write', 'POLICY_IDENTITY', value => { value.policy.workerCeilings.projectedHostWriteBytes = 0; }],
    ['remove the infrastructure memory reserve', 'POLICY_IDENTITY', value => { value.policy.capacity.infrastructureMemoryReserveBytes = 0; value.policy.capacity.requiredVmMemoryBytes = value.policy.workerCeilings.memoryBytes; }],
    ['mark six-GiB VM memory accepted', 'CAPACITY_DECISION', value => { value.decision.gates.vmMemory.status = 'ACCEPTED'; }],
    ['remove the infrastructure CPU reserve', 'POLICY_IDENTITY', value => { value.policy.capacity.infrastructureCpuReserve = 0; value.policy.capacity.requiredVmCpus = value.policy.workerCeilings.cpus; }],
    ['mark four-CPU VM capacity accepted', 'CAPACITY_DECISION', value => { value.decision.gates.vmCpu.status = 'ACCEPTED'; }],
    ['lower the Docker storage safety floor', 'POLICY_IDENTITY', value => { value.policy.capacity.minimumDockerStorageFreeBeforeBuildBytes = 1; }],
    ['mark below-floor Docker storage accepted', 'CAPACITY_DECISION', value => { value.decision.gates.dockerStorage.status = 'ACCEPTED'; }],
    ['hide a running competing container', 'CAPACITY_DECISION', value => { value.observations.docker.runningContainerIds = ['a'.repeat(64)]; }],
    ['accept nonzero VM swap', 'VM_SWAP_GATE', value => { value.observations.vm.swapTotalBytes = '4096'; value.decision = classifyB40Capacity(value.observations, spec); }],
    ['fabricate the x64 emulator registration', 'EMULATOR_REGISTRATION', value => { value.observations.vm.emulator.registration = 'rosetta-x86_64'; }],
    ['change an ancestry evidence hash', 'ANCESTRY_IDENTITY', value => { value.ancestry.b39C1ResultSha256 = '4'.repeat(64); }],
    ['claim a runtime operation executed', 'RUNTIME_OPERATION_BOUNDARY', value => { value.runtimeOperationsExecuted.push('CONTAINER_RUN'); }],
    ['mark overall admission accepted', 'CAPACITY_DECISION', value => { value.decision.status = 'ACCEPTED'; value.decision.reasons = []; }],
  ];
  if (!exact(cases.map(([name]) => name), spec.frozenAnalyzerAttacks)) throw new Error('B40 attack list differs');
  return cases.map(([name, expectedFailure, mutate]) => {
    const analysis = analyzeB40Evidence(mutateAndHash(evidence, mutate), spec);
    return { name, expectedFailure, observedFailures: analysis.failures, passed: !analysis.passed && analysis.failures.includes(expectedFailure) };
  });
}

export function parseB40ColimaConfig(text) {
  const scalar = key => text.match(new RegExp(`^${key}:\\s*(\\S+)`, 'm'))?.[1];
  const number = key => Number(scalar(key));
  return {
    cpu: number('cpu'),
    diskGiB: number('disk'),
    memoryGiB: number('memory'),
    arch: scalar('arch'),
    vmType: scalar('vmType'),
    rosetta: scalar('rosetta') === 'true',
    mountType: scalar('mountType'),
  };
}

export function parseB40Meminfo(text) {
  const bytes = key => {
    const match = text.match(new RegExp(`^${key}:\\s+([0-9]+)\\s+kB$`, 'm'));
    if (!match) throw new Error(`Missing ${key}`);
    return String(BigInt(match[1]) * 1024n);
  };
  return { memTotalBytes: bytes('MemTotal'), swapTotalBytes: bytes('SwapTotal') };
}

export function parseB40Df(text) {
  const lines = text.trim().split('\n');
  const fields = lines.at(-1).trim().split(/\s+/);
  if (fields.length < 6) throw new Error('Unexpected df output');
  return { totalBytes: fields[1], usedBytes: fields[2], availableBytes: fields[3], usePercent: fields[4] };
}

export function parseB40Binfmt(text, registration) {
  const line = key => text.match(new RegExp(`^${key}\\s+(.+)$`, 'm'))?.[1] ?? null;
  return {
    registration,
    enabled: text.split('\n')[0]?.trim() === 'enabled',
    interpreter: line('interpreter'),
    flags: line('flags') ?? '',
  };
}
