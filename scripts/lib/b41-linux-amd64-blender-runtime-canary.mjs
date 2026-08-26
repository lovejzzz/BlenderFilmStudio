import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { canonicalJson, sha256Canonical } from './receipt-format.mjs';
import { repositoryRoot, sha256 } from './scene-spec.mjs';

export const B41_SPEC_PATH = resolve(repositoryRoot, 'specs/linux-amd64-blender-runtime-canary.v0.1.json');
export const B41_SPEC_SHA256 = '63c5787f9566fb70dd2a250cb170d2d93ef13f5b3b426005562bd9283d308eb9';
export const B41_PREREG_COMMIT = '01502eb2ec23e113644e97436cd92b9118d5bac1';
const exact = (left, right) => canonicalJson(left) === canonicalJson(right);
const HEX_40 = /^[a-f0-9]{40}$/;
const HEX_64 = /^[a-f0-9]{64}$/;

export async function readB41Spec() {
  const bytes = await readFile(B41_SPEC_PATH);
  const digest = sha256(bytes);
  if (digest !== B41_SPEC_SHA256) throw new Error(`B41 spec SHA mismatch: ${digest}`);
  return JSON.parse(bytes);
}

export function hashB41Evidence(evidence) {
  const copy = structuredClone(evidence);
  for (const key of ['analysis', 'verdict', 'nonClaims']) delete copy[key];
  return sha256Canonical(copy);
}

export function expectedB41Argv(spec, script) {
  return [...spec.containerContract.blenderArgvPrefix, ...spec.containerContract.pythonFailureArgs, '--python', script];
}

export function expectedB41Environment(spec, jobId) {
  return Object.fromEntries(spec.containerContract.environmentKeysExact.map(key => [
    key,
    key === 'BFS_JOB_ID' ? jobId : spec.containerContract.environmentValues[key],
  ]));
}

export function analyzeB41Evidence(evidence, spec) {
  const failures = [];
  const gate = (condition, code) => { if (!condition && !failures.includes(code)) failures.push(code); };
  gate(evidence?.schemaVersion === 'bfs.linuxAmd64BlenderRuntimeEvidence.v0.1' && evidence?.experimentId === 'B41', 'EVIDENCE_SCHEMA');
  gate(evidence?.preregistration?.commit === B41_PREREG_COMMIT
    && evidence?.preregistration?.specSha256 === B41_SPEC_SHA256, 'PREREGISTRATION_IDENTITY');
  gate(exact(evidence?.ancestry, spec.ancestry), 'ANCESTRY_IDENTITY');
  gate(HEX_40.test(evidence?.toolFreezeCommit ?? ''), 'TOOL_FREEZE_IDENTITY');
  gate(evidence?.runtime?.nodeVersion === spec.runtime.nodeVersion
    && evidence?.runtime?.nodeBinary === spec.runtime.nodeBinary
    && evidence?.runtime?.nodeBinarySha256 === spec.runtime.nodeBinarySha256
    && evidence?.runtime?.dockerHost === spec.runtime.dockerHost
    && evidence?.runtime?.dockerServerArchitecture === spec.runtime.dockerServerArchitecture, 'RUNTIME_IDENTITY');
  gate(['runner', 'library', 'audit', 'dockerfile', 'runtimeCanary', 'timeoutCanary'].every(key => HEX_64.test(evidence?.tools?.[key]?.sha256 ?? '')), 'TOOL_IDENTITY');
  let diskPass = false;
  try {
    diskPass = evidence?.diskAdmission?.status === 'ACCEPTED'
      && BigInt(evidence.diskAdmission.freeAfterProjectedBytes) >= BigInt(spec.diskAdmission.minimumReserveBytes);
  } catch {}
  gate(diskPass, 'DISK_ADMISSION');
  gate(evidence?.artifact?.url === spec.artifact.url
    && evidence?.artifact?.filename === spec.artifact.filename
    && evidence?.artifact?.bytes === spec.artifact.bytes
    && evidence?.artifact?.sha256 === spec.artifact.sha256, 'ARTIFACT_IDENTITY');
  gate(evidence?.inputFixture?.ocioTreeManifestSha256 === spec.inputFixture.ocioTreeManifestSha256, 'OCIO_IDENTITY');
  gate(evidence?.image?.buildExitCode === 0 && /^sha256:[a-f0-9]{64}$/.test(evidence?.image?.id ?? '')
    && evidence?.image?.os === 'linux' && evidence?.image?.architecture === 'amd64', 'IMAGE_IDENTITY');
  gate(exact(evidence?.launchContract, spec.containerContract), 'LAUNCH_CONTRACT');
  const success = evidence?.success ?? {};
  gate(success.imageId === evidence?.image?.id && success.platform === spec.runtime.containerPlatform
    && exact(success.argv, expectedB41Argv(spec, spec.successCanary.script))
    && exact(success.environment, expectedB41Environment(spec, spec.successCanary.jobId)), 'SUCCESS_LAUNCH_IDENTITY');
  gate(success.exitCode === 0 && success.timedOut === false && success.forceKillSent === false, 'SUCCESS_PROCESS');
  gate(success.report?.passed === true
    && Object.values(success.report?.checks ?? {}).length >= spec.successCanary.requiredChecks.length
    && Object.values(success.report?.checks ?? {}).every(Boolean), 'SUCCESS_CANARIES');
  gate(success.report?.blender?.versionTuple?.join('.') === '5.2.0'
    && success.report?.blender?.executableSha256 === spec.artifact.blenderExecutableSha256
    && success.report?.blender?.renderEngine === 'BLENDER_EEVEE_NEXT', 'BLENDER_RUNTIME');
  gate(success.artifacts?.png?.valid === true && exact(success.artifacts?.png?.dimensions, [32, 32])
    && HEX_64.test(success.artifacts?.png?.sha256 ?? '')
    && success.artifacts?.blend?.bytes > 0 && HEX_64.test(success.artifacts?.blend?.sha256 ?? ''), 'SUCCESS_ARTIFACTS');
  gate(success.promotable === true, 'SUCCESS_PROMOTION');
  const timeout = evidence?.timeout ?? {};
  gate(timeout.imageId === evidence?.image?.id && timeout.platform === spec.runtime.containerPlatform
    && exact(timeout.argv, expectedB41Argv(spec, spec.timeoutCanary.script))
    && exact(timeout.environment, expectedB41Environment(spec, spec.timeoutCanary.jobId)), 'TIMEOUT_LAUNCH_IDENTITY');
  gate(timeout.timeoutTriggered === true && timeout.termSent === true && timeout.forceKillSent === true
    && timeout.exitCode === 137 && timeout.readyObserved === true && timeout.sigtermObserved === true, 'TIMEOUT_ENFORCEMENT');
  gate(timeout.promotable === false && timeout.outcome === spec.timeoutCanary.requiredOutcome, 'TIMEOUT_NON_PROMOTION');
  gate(evidence?.cleanup?.experimentContainersRunningAfter === 0 && evidence?.cleanup?.temporaryBuildRootRemoved === true, 'CLEANUP_BOUNDARY');
  gate(Array.isArray(evidence?.errors) && evidence.errors.length === 0, 'RUN_ERRORS');
  gate(evidence?.evidenceHash === hashB41Evidence(evidence), 'EVIDENCE_SELF_HASH');
  return {
    schemaVersion: 'bfs.linuxAmd64BlenderRuntimeAnalysis.v0.1',
    passed: failures.length === 0,
    failures,
    decision: failures[0] ?? spec.acceptedVerdict,
  };
}
