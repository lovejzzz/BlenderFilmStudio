import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { canonicalJson } from './receipt-format.mjs';
import { repositoryRoot, sha256 } from './scene-spec.mjs';
import { evaluateB39DiskAdmission, hashB39Evidence } from './b39-linux-worker-architecture-preflight.mjs';

export const B39_C1_SPEC_PATH = resolve(repositoryRoot, 'specs/linux-worker-architecture-preflight.v0.2.json');
export const B39_C1_SPEC_SHA256 = '775ba7436c385cf5175fc3d1e792f25d164dd50d91ff2166f4a3cc30aef4595e';
export const B39_C1_PREREG_COMMIT = '9c4260d527736f9ac5301d12d226b9be6bb080ce';
const HEX_64 = /^[a-f0-9]{64}$/;
const exact = (left, right) => canonicalJson(left) === canonicalJson(right);

export async function readB39C1Spec() {
  const bytes = await readFile(B39_C1_SPEC_PATH);
  const digest = sha256(bytes);
  if (digest !== B39_C1_SPEC_SHA256) throw new Error(`B39-C1 spec SHA mismatch: ${digest}`);
  return JSON.parse(bytes);
}

const escapeRegExp = value => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

export function parseB39C1Artifacts(indexText, checksumText, spec) {
  const parse = expected => {
    const escaped = escapeRegExp(expected.filename);
    const rawFilenameOccurrences = (indexText.match(new RegExp(escaped, 'g')) ?? []).length;
    const exactHrefTargetOccurrences = (indexText.match(new RegExp(`href=["']${escaped}["']`, 'g')) ?? []).length;
    const checksumMatches = [...checksumText.matchAll(new RegExp(`^([a-f0-9]{64})\\s+${escaped}$`, 'gm'))];
    const sizeMatches = [...indexText.matchAll(new RegExp(`${escaped}[^\\n]*?([0-9]{6,})`, 'g'))].map(match => Number(match[1]));
    return {
      filename: expected.filename,
      platform: expected.platform,
      rawFilenameOccurrences,
      exactHrefTargetOccurrences,
      checksumOccurrences: checksumMatches.length,
      bytes: sizeMatches.length === 1 ? sizeMatches[0] : null,
      sha256: checksumMatches.length === 1 ? checksumMatches[0][1] : null,
    };
  };
  return { x64: parse(spec.artifacts.x64), arm64: parse(spec.artifacts.arm64) };
}

export function classifyB39C1Routes(observations, spec) {
  const x64 = observations.officialArtifacts.x64;
  const arm64 = observations.officialArtifacts.arm64;
  const nativeAvailable = arm64.rawFilenameOccurrences > 0
    && arm64.exactHrefTargetOccurrences === 1
    && arm64.checksumOccurrences === 1
    && HEX_64.test(arm64.sha256 ?? '');
  const x64Valid = exact(x64, spec.artifacts.x64);
  const hostValid = observations.host.hostArchitecture === spec.runtime.hostArchitecture
    && observations.host.colima.architecture === spec.host.colimaArchitecture
    && observations.host.docker.architecture === spec.host.dockerArchitecture
    && spec.host.requiredSecurityOptions.every(option => observations.host.docker.securityOptions.includes(option));
  const pinned = /^sha256:[a-f0-9]{64}$/.test(observations.futureRuntime.workerImageDigest);
  let x64Decision = 'REJECTED_ARTIFACT_OR_HOST_IDENTITY';
  if (x64Valid && hostValid) {
    if (observations.diskAdmission.status === 'BLOCKED') x64Decision = 'IDENTIFIED_BUT_RUNTIME_BLOCKED';
    else if (!pinned) x64Decision = 'IDENTIFIED_REQUIRES_PINNED_IMAGE';
    else x64Decision = 'ELIGIBLE_FOR_SEPARATELY_PREREGISTERED_RUNTIME_CANARY';
  }
  return {
    schemaVersion: 'bfs.linuxWorkerRouteDecision.v0.2',
    nativeArm64: {
      platform: 'linux/arm64',
      decision: nativeAvailable ? 'AVAILABLE_REQUIRES_NEW_PROTOCOL' : 'REJECTED_NO_OFFICIAL_ARTIFACT',
      officialArtifactAvailable: nativeAvailable,
    },
    x64Emulated: {
      platform: 'linux/amd64',
      executionClass: 'EXPERIMENT_ONLY_BEST_EFFORT_EMULATION',
      decision: x64Decision,
      officialArtifactIdentityValid: x64Valid,
      hostArchitectureIdentityValid: hostValid,
      workerImageDigestPinned: pinned,
    },
  };
}

export function analyzeB39C1Evidence(evidence, spec) {
  const failures = [];
  const gate = (condition, code) => { if (!condition && !failures.includes(code)) failures.push(code); };
  gate(evidence?.schemaVersion === 'bfs.linuxWorkerArchitecturePreflightEvidence.v0.2' && evidence?.experimentId === 'B39-C1', 'EVIDENCE_SCHEMA');
  gate(evidence?.preregistration?.commit === B39_C1_PREREG_COMMIT && evidence?.preregistration?.specSha256 === B39_C1_SPEC_SHA256, 'PREREGISTRATION_IDENTITY');
  gate(evidence?.correctionFrom?.resultSha256 === spec.correctionFrom.resultSha256
    && evidence?.correctionFrom?.auditSha256 === spec.correctionFrom.auditSha256
    && evidence?.correctionFrom?.changedAssumptionExact === spec.correctionFrom.changedAssumptionExact, 'CORRECTION_ANCESTRY');
  gate(evidence?.runtime?.nodeVersion === spec.runtime.nodeVersion
    && evidence?.runtime?.nodeBinary === spec.runtime.nodeBinary
    && evidence?.runtime?.nodeBinarySha256 === spec.runtime.nodeBinarySha256, 'RUNTIME_IDENTITY');
  gate(['runner', 'library', 'audit'].every(key => HEX_64.test(evidence?.tools?.[key]?.sha256 ?? '')), 'TOOL_IDENTITY');
  gate(evidence?.sources?.releaseIndexUrl === spec.sources.releaseIndexUrl && evidence?.sources?.checksumUrl === spec.sources.checksumUrl, 'SOURCE_IDENTITY');
  gate(exact(evidence?.observations?.officialArtifacts?.x64, spec.artifacts.x64), 'X64_CORRECTED_IDENTITY');
  gate(exact(evidence?.observations?.officialArtifacts?.arm64, { ...spec.artifacts.arm64, bytes: null }), 'ARM64_ARTIFACT_ABSENCE');
  const host = evidence?.observations?.host ?? {};
  gate(host.hostArchitecture === spec.runtime.hostArchitecture, 'HOST_ARCHITECTURE');
  gate(host?.colima?.driver === spec.host.colimaDriver && host?.colima?.architecture === spec.host.colimaArchitecture, 'COLIMA_IDENTITY');
  gate(host?.docker?.serverVersion === spec.host.dockerServerVersion && host?.docker?.architecture === spec.host.dockerArchitecture, 'DOCKER_IDENTITY');
  gate(spec.host.requiredSecurityOptions.every(option => host?.docker?.securityOptions?.includes(option)), 'DOCKER_SECURITY_OPTIONS');
  gate(Array.isArray(host.existingImages) && host.existingImages.length === 2
    && host.existingImages.every(image => image.os === 'linux' && image.architecture === 'arm64' && /^sha256:[a-f0-9]{64}$/.test(image.id)), 'EXISTING_IMAGE_METADATA');
  gate(exact(evidence?.probeTrace, spec.probeTraceExact), 'PROBE_TRACE');
  gate(exact(evidence?.runtimeOperationsExecuted, spec.runtimeOperationsExecutedExact), 'RUNTIME_OPERATION_BOUNDARY');
  gate(evidence?.observations?.futureRuntime?.experimentId === spec.futureRuntime.experimentId
    && evidence?.observations?.futureRuntime?.state === spec.futureRuntime.state
    && evidence?.observations?.futureRuntime?.workerImageDigest === spec.futureRuntime.workerImageDigest, 'FUTURE_RUNTIME_STATE');
  let admission = null;
  try {
    admission = evaluateB39DiskAdmission({
      availableBytes: evidence?.observations?.diskAdmission?.availableBytes,
      projectedWriteBytes: String(spec.diskAdmission.projectedRuntimeWriteBytes),
    }, { diskAdmission: spec.diskAdmission });
  } catch {
    gate(false, 'DISK_ADMISSION_INPUT');
  }
  gate(admission !== null && exact(evidence?.observations?.diskAdmission, admission), 'DISK_ADMISSION_DECISION');
  gate(evidence?.observations?.diskAdmission?.status === spec.diskAdmission.expectedCurrentStatus, 'DISK_ADMISSION_EXPECTED_STATE');
  let routes = null;
  try { routes = classifyB39C1Routes(evidence.observations, spec); } catch { gate(false, 'ROUTE_INPUT'); }
  gate(routes !== null && exact(evidence?.routes, routes), 'ROUTE_DECISION');
  gate(evidence?.routes?.nativeArm64?.decision === spec.routes.nativeArm64Decision, 'NATIVE_ROUTE_DECISION');
  gate(evidence?.routes?.x64Emulated?.decision === spec.routes.x64Decision
    && evidence?.routes?.x64Emulated?.executionClass === spec.routes.x64ExecutionClass, 'X64_ROUTE_DECISION');
  gate(evidence?.evidenceHash === hashB39Evidence(evidence), 'EVIDENCE_SELF_HASH');
  return {
    schemaVersion: 'bfs.linuxWorkerArchitecturePreflightAnalysis.v0.2',
    passed: failures.length === 0,
    failures,
    decision: failures[0] ?? spec.acceptedVerdict,
  };
}

const mutateAndHash = (evidence, mutate) => {
  const candidate = structuredClone(evidence);
  for (const key of ['analysis', 'attacks', 'attacksPassed', 'verdict', 'nonClaims']) delete candidate[key];
  mutate(candidate);
  candidate.evidenceHash = hashB39Evidence(candidate);
  return candidate;
};

export function runB39C1Attacks(evidence, spec) {
  const cases = [
    ['restore the rejected raw occurrence assumption', 'X64_CORRECTED_IDENTITY', value => { value.observations.officialArtifacts.x64.rawFilenameOccurrences = 1; }],
    ['remove the unique exact href target', 'X64_CORRECTED_IDENTITY', value => { value.observations.officialArtifacts.x64.exactHrefTargetOccurrences = 0; }],
    ['fabricate an official Linux arm64 href target', 'ARM64_ARTIFACT_ABSENCE', value => { value.observations.officialArtifacts.arm64.exactHrefTargetOccurrences = 1; value.observations.officialArtifacts.arm64.rawFilenameOccurrences = 2; }],
    ['change the official x64 byte count', 'X64_CORRECTED_IDENTITY', value => { value.observations.officialArtifacts.x64.bytes += 1; }],
    ['change the official x64 SHA-256', 'X64_CORRECTED_IDENTITY', value => { value.observations.officialArtifacts.x64.sha256 = '3'.repeat(64); }],
    ['label linux/amd64 as native arm64', 'ROUTE_DECISION', value => { value.routes.x64Emulated.platform = 'linux/arm64'; }],
    ['promote best-effort emulation to production', 'ROUTE_DECISION', value => { value.routes.x64Emulated.executionClass = 'PRODUCTION_NATIVE'; }],
    ['change the observed host architecture', 'HOST_ARCHITECTURE', value => { value.observations.host.hostArchitecture = 'x86_64'; }],
    ['change the observed Colima architecture', 'COLIMA_IDENTITY', value => { value.observations.host.colima.architecture = 'x86_64'; }],
    ['change the observed Docker architecture', 'DOCKER_IDENTITY', value => { value.observations.host.docker.architecture = 'x86_64'; }],
    ['remove a required Docker security option', 'DOCKER_SECURITY_OPTIONS', value => { value.observations.host.docker.securityOptions = value.observations.host.docker.securityOptions.slice(1); }],
    ['mark below-reserve disk admission accepted', 'DISK_ADMISSION_DECISION', value => { value.observations.diskAdmission.status = 'ACCEPTED'; value.observations.diskAdmission.reasons = []; }],
    ['claim that a runtime operation executed', 'RUNTIME_OPERATION_BOUNDARY', value => { value.runtimeOperationsExecuted.push('CONTAINER_RUN'); }],
    ['materialize an unpinned worker image', 'FUTURE_RUNTIME_STATE', value => { value.observations.futureRuntime.workerImageDigest = 'bfs/blender-worker:latest'; }],
    ['mark B40 complete before separate preregistration', 'FUTURE_RUNTIME_STATE', value => { value.observations.futureRuntime.state = 'COMPLETE'; }],
  ];
  if (!exact(cases.map(([name]) => name), spec.frozenAnalyzerAttacks)) throw new Error('B39-C1 attack list differs');
  return cases.map(([name, expectedFailure, mutate]) => {
    const analysis = analyzeB39C1Evidence(mutateAndHash(evidence, mutate), spec);
    return { name, expectedFailure, observedFailures: analysis.failures, passed: !analysis.passed && analysis.failures.includes(expectedFailure) };
  });
}
