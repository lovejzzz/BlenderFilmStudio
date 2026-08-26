import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { canonicalJson, sha256Canonical } from './receipt-format.mjs';
import { repositoryRoot, sha256 } from './scene-spec.mjs';

export const B39_SPEC_PATH = resolve(repositoryRoot, 'specs/linux-worker-architecture-preflight.v0.1.json');
export const B39_SPEC_SHA256 = '06645fda0af4778f487893a9a1881fa749d06e4774559bf975034ec49140e30f';
export const B39_PREREG_COMMIT = '59b7344b020ae98a7cdf2a6868b0a6c0365bf141';

const HEX_64 = /^[a-f0-9]{64}$/;
const exactCanonical = (left, right) => canonicalJson(left) === canonicalJson(right);

export async function readB39Spec() {
  const bytes = await readFile(B39_SPEC_PATH);
  const digest = sha256(bytes);
  if (digest !== B39_SPEC_SHA256) throw new Error(`B39 spec SHA mismatch: ${digest}`);
  return JSON.parse(bytes);
}

export function hashB39Evidence(evidence) {
  const copy = structuredClone(evidence);
  delete copy.evidenceHash;
  delete copy.analysis;
  delete copy.attacks;
  delete copy.attacksPassed;
  delete copy.verdict;
  delete copy.nonClaims;
  return sha256Canonical(copy);
}

export function evaluateB39DiskAdmission({ availableBytes, projectedWriteBytes }, spec) {
  if (typeof availableBytes !== 'string' || !/^[0-9]+$/.test(availableBytes)) throw new Error('availableBytes must be a decimal string');
  if (typeof projectedWriteBytes !== 'string' || !/^[0-9]+$/.test(projectedWriteBytes)) throw new Error('projectedWriteBytes must be a decimal string');
  const available = BigInt(availableBytes);
  const projected = BigInt(projectedWriteBytes);
  const reserve = BigInt(spec.diskAdmission.minimumReserveBytes);
  const freeAfterProjected = available - projected;
  return {
    schemaVersion: 'bfs.linuxWorkerDiskAdmission.v0.1',
    availableBytes,
    projectedWriteBytes,
    minimumReserveBytes: reserve.toString(),
    freeAfterProjectedBytes: freeAfterProjected.toString(),
    status: freeAfterProjected >= reserve ? 'ACCEPTED' : 'BLOCKED',
    reasons: freeAfterProjected >= reserve ? [] : ['DISK_RESERVE'],
  };
}

export function classifyB39Routes(observations, spec) {
  const source = observations.officialArtifacts;
  const host = observations.host;
  const nativeAvailable = source.arm64.indexOccurrences === 1 && source.arm64.checksumOccurrences === 1 && HEX_64.test(source.arm64.sha256 ?? '');
  const x64IdentityValid = source.x64.filename === spec.officialArtifactSource.linuxX64.filename
    && source.x64.indexOccurrences === 1
    && source.x64.bytes === spec.officialArtifactSource.linuxX64.bytes
    && source.x64.checksumOccurrences === 1
    && source.x64.sha256 === spec.officialArtifactSource.linuxX64.sha256;
  const architectureValid = host.hostArchitecture === spec.runtime.hostArchitecture
    && host.colima.architecture === spec.candidateHost.colimaArchitecture
    && host.docker.architecture === spec.candidateHost.dockerArchitecture;
  const securityValid = spec.candidateHost.requiredSecurityOptions.every(option => host.docker.securityOptions.includes(option));
  const imagePinned = observations.futureRuntime.workerImageDigest.startsWith('sha256:') && HEX_64.test(observations.futureRuntime.workerImageDigest.slice(7));

  let emulatedDecision = 'REJECTED_ARTIFACT_OR_HOST_IDENTITY';
  if (x64IdentityValid && architectureValid && securityValid) {
    if (observations.diskAdmission.status === 'BLOCKED') emulatedDecision = 'IDENTIFIED_BUT_RUNTIME_BLOCKED';
    else if (!imagePinned) emulatedDecision = 'IDENTIFIED_REQUIRES_PINNED_IMAGE';
    else emulatedDecision = 'ELIGIBLE_FOR_SEPARATELY_PREREGISTERED_RUNTIME_CANARY';
  }
  return {
    schemaVersion: 'bfs.linuxWorkerRouteDecision.v0.1',
    nativeArm64: {
      platform: 'linux/arm64',
      decision: nativeAvailable ? 'AVAILABLE_REQUIRES_NEW_PROTOCOL' : 'REJECTED_NO_OFFICIAL_ARTIFACT',
      officialArtifactAvailable: nativeAvailable,
    },
    x64Emulated: {
      platform: 'linux/amd64',
      executionClass: 'EXPERIMENT_ONLY_BEST_EFFORT_EMULATION',
      decision: emulatedDecision,
      officialArtifactIdentityValid: x64IdentityValid,
      hostArchitectureIdentityValid: architectureValid,
      requiredSecurityOptionsPresent: securityValid,
      workerImageDigestPinned: imagePinned,
    },
  };
}

const expectedProbeIds = [
  'HOST_UNAME',
  'COLIMA_STATUS',
  'DOCKER_SERVER_VERSION',
  'DOCKER_ARCH_SECURITY',
  'DOCKER_EXISTING_IMAGE_INSPECT',
  'BLENDER_RELEASE_INDEX_HTTPS',
  'BLENDER_SHA256_MANIFEST_HTTPS',
  'HOST_STATFS',
];

export function analyzeB39Evidence(evidence, spec) {
  const failures = [];
  const requireGate = (condition, code) => {
    if (!condition && !failures.includes(code)) failures.push(code);
  };
  requireGate(evidence?.schemaVersion === 'bfs.linuxWorkerArchitecturePreflightEvidence.v0.1' && evidence?.experimentId === 'B39', 'EVIDENCE_SCHEMA');
  requireGate(evidence?.preregistration?.commit === B39_PREREG_COMMIT && evidence?.preregistration?.specSha256 === B39_SPEC_SHA256, 'PREREGISTRATION_IDENTITY');
  requireGate(evidence?.runtime?.nodeVersion === spec.runtime.nodeVersion
    && evidence?.runtime?.nodeBinary === spec.runtime.nodeBinary
    && evidence?.runtime?.nodeBinarySha256 === spec.runtime.nodeBinarySha256, 'RUNTIME_IDENTITY');
  requireGate(['runner', 'library', 'audit'].every(key => HEX_64.test(evidence?.tools?.[key]?.sha256 ?? '')), 'TOOL_IDENTITY');
  requireGate(evidence?.sources?.releaseIndexUrl === spec.officialArtifactSource.releaseIndexUrl
    && evidence?.sources?.checksumUrl === spec.officialArtifactSource.checksumUrl, 'SOURCE_IDENTITY');

  const artifacts = evidence?.observations?.officialArtifacts ?? {};
  requireGate(artifacts?.x64?.filename === spec.officialArtifactSource.linuxX64.filename
    && artifacts?.x64?.indexOccurrences === 1
    && artifacts?.x64?.bytes === spec.officialArtifactSource.linuxX64.bytes, 'X64_INDEX_IDENTITY');
  requireGate(artifacts?.x64?.checksumOccurrences === 1
    && artifacts?.x64?.sha256 === spec.officialArtifactSource.linuxX64.sha256, 'X64_CHECKSUM_IDENTITY');
  requireGate(artifacts?.arm64?.filename === spec.officialArtifactSource.linuxArm64ExpectedFilename
    && artifacts?.arm64?.indexOccurrences === 0
    && artifacts?.arm64?.checksumOccurrences === 0
    && artifacts?.arm64?.sha256 === null, 'ARM64_ARTIFACT_ABSENCE');

  const host = evidence?.observations?.host ?? {};
  requireGate(host.hostArchitecture === spec.runtime.hostArchitecture, 'HOST_ARCHITECTURE');
  requireGate(host?.colima?.driver === spec.candidateHost.colimaDriver
    && host?.colima?.architecture === spec.candidateHost.colimaArchitecture
    && host?.colima?.runtime === spec.candidateHost.colimaRuntime
    && host?.colima?.mountType === spec.candidateHost.colimaMountType, 'COLIMA_IDENTITY');
  requireGate(host?.docker?.serverVersion === spec.candidateHost.dockerServerVersion
    && host?.docker?.architecture === spec.candidateHost.dockerArchitecture, 'DOCKER_IDENTITY');
  requireGate(spec.candidateHost.requiredSecurityOptions.every(option => host?.docker?.securityOptions?.includes(option)), 'DOCKER_SECURITY_OPTIONS');
  requireGate(Array.isArray(host.existingImages)
    && host.existingImages.length === 2
    && host.existingImages.every(image => image.os === 'linux' && image.architecture === 'arm64' && HEX_64.test(image.id.replace(/^sha256:/, ''))), 'EXISTING_IMAGE_METADATA');

  requireGate(exactCanonical(evidence?.probeTrace, expectedProbeIds), 'PROBE_TRACE');
  requireGate(Array.isArray(evidence?.runtimeOperationsExecuted) && evidence.runtimeOperationsExecuted.length === 0, 'RUNTIME_OPERATION_BOUNDARY');
  requireGate(evidence?.observations?.futureRuntime?.state === 'PENDING_SEPARATE_PREREGISTRATION'
    && evidence?.observations?.futureRuntime?.workerImageDigest === spec.futureRuntimeCanary.workerImageDigest, 'FUTURE_RUNTIME_STATE');

  let expectedAdmission = null;
  try {
    expectedAdmission = evaluateB39DiskAdmission({
      availableBytes: evidence?.observations?.diskAdmission?.availableBytes,
      projectedWriteBytes: String(spec.diskAdmission.projectedRuntimeWriteBytes),
    }, spec);
  } catch {
    requireGate(false, 'DISK_ADMISSION_INPUT');
  }
  requireGate(expectedAdmission !== null && exactCanonical(evidence.observations.diskAdmission, expectedAdmission), 'DISK_ADMISSION_DECISION');
  requireGate(evidence?.observations?.diskAdmission?.status === spec.diskAdmission.expectedCurrentStatus, 'DISK_ADMISSION_EXPECTED_STATE');

  let expectedRoutes = null;
  try {
    expectedRoutes = classifyB39Routes(evidence.observations, spec);
  } catch {
    requireGate(false, 'ROUTE_INPUT');
  }
  requireGate(expectedRoutes !== null && exactCanonical(evidence?.routes, expectedRoutes), 'ROUTE_DECISION');
  requireGate(evidence?.routes?.nativeArm64?.decision === spec.routes.officialNativeArm64.expectedDecision, 'NATIVE_ROUTE_DECISION');
  requireGate(evidence?.routes?.x64Emulated?.decision === spec.routes.officialX64Emulated.expectedDecisionBeforeRuntime
    && evidence?.routes?.x64Emulated?.executionClass === spec.routes.officialX64Emulated.executionClass, 'EMULATED_ROUTE_DECISION');
  requireGate(typeof evidence?.evidenceHash === 'string' && evidence.evidenceHash === hashB39Evidence(evidence), 'EVIDENCE_SELF_HASH');

  return {
    schemaVersion: 'bfs.linuxWorkerArchitecturePreflightAnalysis.v0.1',
    passed: failures.length === 0,
    failures,
    decision: failures[0] ?? 'ARCHITECTURE_PREFLIGHT_SUPPORT_RUNTIME_BLOCKED',
  };
}

const mutatedAndRehashed = (evidence, mutate) => {
  const candidate = structuredClone(evidence);
  delete candidate.analysis;
  delete candidate.attacks;
  delete candidate.attacksPassed;
  delete candidate.verdict;
  delete candidate.nonClaims;
  mutate(candidate);
  candidate.evidenceHash = hashB39Evidence(candidate);
  return candidate;
};

export function runB39AnalyzerAttacks(evidence, spec) {
  const cases = [
    ['fabricate an official Linux arm64 artifact', 'ARM64_ARTIFACT_ABSENCE', value => { value.observations.officialArtifacts.arm64.indexOccurrences = 1; value.observations.officialArtifacts.arm64.checksumOccurrences = 1; value.observations.officialArtifacts.arm64.sha256 = '1'.repeat(64); }],
    ['change the official x64 filename', 'X64_INDEX_IDENTITY', value => { value.observations.officialArtifacts.x64.filename = 'blender-5.2.0-linux-x86.tar.xz'; }],
    ['change the official x64 byte count', 'X64_INDEX_IDENTITY', value => { value.observations.officialArtifacts.x64.bytes += 1; }],
    ['change the official x64 SHA-256', 'X64_CHECKSUM_IDENTITY', value => { value.observations.officialArtifacts.x64.sha256 = '2'.repeat(64); }],
    ['label linux/amd64 as native arm64', 'ROUTE_DECISION', value => { value.routes.x64Emulated.platform = 'linux/arm64'; }],
    ['promote best-effort emulation to production', 'ROUTE_DECISION', value => { value.routes.x64Emulated.executionClass = 'PRODUCTION_NATIVE'; }],
    ['change the observed host architecture', 'HOST_ARCHITECTURE', value => { value.observations.host.hostArchitecture = 'x86_64'; }],
    ['change the observed Colima architecture', 'COLIMA_IDENTITY', value => { value.observations.host.colima.architecture = 'x86_64'; }],
    ['change the observed Docker architecture', 'DOCKER_IDENTITY', value => { value.observations.host.docker.architecture = 'x86_64'; }],
    ['remove a required Docker security option', 'DOCKER_SECURITY_OPTIONS', value => { value.observations.host.docker.securityOptions = value.observations.host.docker.securityOptions.slice(1); }],
    ['mark below-reserve disk admission accepted', 'DISK_ADMISSION_DECISION', value => { value.observations.diskAdmission.status = 'ACCEPTED'; value.observations.diskAdmission.reasons = []; }],
    ['claim that a container or Blender process executed', 'RUNTIME_OPERATION_BOUNDARY', value => { value.runtimeOperationsExecuted.push('CONTAINER_RUN'); }],
    ['insert a forbidden runtime operation', 'PROBE_TRACE', value => { value.probeTrace.push('DOCKER_PULL'); }],
    ['materialize an unpinned worker image', 'FUTURE_RUNTIME_STATE', value => { value.observations.futureRuntime.workerImageDigest = 'bfs/blender-worker:latest'; }],
    ['mark B40 complete before a separate preregistration', 'FUTURE_RUNTIME_STATE', value => { value.observations.futureRuntime.state = 'COMPLETE'; }],
  ];
  if (!exactCanonical(cases.map(([name]) => name), spec.frozenAnalyzerAttacks)) throw new Error('B39 attack list differs from preregistration');
  return cases.map(([name, expectedFailure, mutate]) => {
    const analysis = analyzeB39Evidence(mutatedAndRehashed(evidence, mutate), spec);
    return {
      name,
      expectedFailure,
      observedFailures: analysis.failures,
      passed: !analysis.passed && analysis.failures.includes(expectedFailure),
    };
  });
}

export function parseB39OfficialArtifacts(indexText, checksumText, spec) {
  const parse = filename => {
    const escaped = filename.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const indexOccurrences = (indexText.match(new RegExp(escaped, 'g')) ?? []).length;
    const checksumPattern = new RegExp(`^([a-f0-9]{64})\\s+${escaped}$`, 'gm');
    const checksumMatches = [...checksumText.matchAll(checksumPattern)];
    const sizePattern = new RegExp(`${escaped}[^\\n]*?([0-9]{6,})`, 'g');
    const sizes = [...indexText.matchAll(sizePattern)].map(match => Number(match[1]));
    return {
      filename,
      indexOccurrences,
      checksumOccurrences: checksumMatches.length,
      sha256: checksumMatches.length === 1 ? checksumMatches[0][1] : null,
      bytes: sizes.length === 1 ? sizes[0] : null,
    };
  };
  return {
    x64: parse(spec.officialArtifactSource.linuxX64.filename),
    arm64: parse(spec.officialArtifactSource.linuxArm64ExpectedFilename),
  };
}
