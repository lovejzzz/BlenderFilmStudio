import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { canonicalJson } from './receipt-format.mjs';
import { repositoryRoot, sha256 } from './scene-spec.mjs';
import {
  B41_C3_PREREG_COMMIT, B41_C3_SPEC_SHA256, analyzeB41C3Evidence, hashB41C3Evidence,
} from './b41-c3-guest-buildx-correction.mjs';

export const B41_C4_SPEC_PATH = resolve(repositoryRoot, 'specs/linux-amd64-blender-runtime-canary-binary-identity-correction.v0.1.json');
export const B41_C4_SPEC_SHA256 = '8dfb22a794c0406d58b2f6b03a7a750206182cb1ff9a864653c27d77aa0f3f19';
export const B41_C4_PREREG_COMMIT = '832556390cf38e2bdb9f5a81b94001c19d580540';

export async function readB41C4Spec() {
  const bytes = await readFile(B41_C4_SPEC_PATH);
  const digest = sha256(bytes);
  if (digest !== B41_C4_SPEC_SHA256) throw new Error(`B41-C4 spec SHA mismatch: ${digest}`);
  return JSON.parse(bytes);
}

export function hashB41C4Evidence(evidence) {
  return hashB41C3Evidence(evidence);
}

function projectToC3(evidence, correctionSpec) {
  const projected = structuredClone(evidence);
  for (const key of ['analysis', 'verdict', 'nonClaims', 'binaryIdentityCorrection']) delete projected[key];
  projected.schemaVersion = 'bfs.linuxAmd64BlenderRuntimeEvidence.v0.4';
  projected.experimentId = 'B41-C3';
  projected.preregistration = { commit: B41_C3_PREREG_COMMIT, specSha256: B41_C3_SPEC_SHA256 };
  projected.tools.library.uri = 'scripts/lib/b41-c3-guest-buildx-correction.mjs';
  projected.tools.audit.uri = 'scripts/audit-b41-c3-guest-buildx-correction.mjs';
  if (projected.success?.report?.blender) {
    projected.success.report.blender.executableSha256 = correctionSpec.platformIdentity.historicalDarwinExecutableSha256;
  }
  projected.evidenceHash = hashB41C3Evidence(projected);
  return projected;
}

export function analyzeB41C4Evidence(evidence, c4Spec, c3Spec, c2Spec, c1Spec, baseSpec) {
  const failures = [];
  const gate = (condition, code) => { if (!condition && !failures.includes(code)) failures.push(code); };
  gate(evidence?.schemaVersion === 'bfs.linuxAmd64BlenderRuntimeEvidence.v0.5' && evidence?.experimentId === 'B41-C4', 'BINARY_CORRECTION_EVIDENCE_SCHEMA');
  gate(evidence?.preregistration?.commit === B41_C4_PREREG_COMMIT
    && evidence?.preregistration?.specSha256 === B41_C4_SPEC_SHA256, 'BINARY_CORRECTION_PREREGISTRATION');
  const correction = evidence?.binaryIdentityCorrection ?? {};
  gate(canonicalJson(correction.parent) === canonicalJson(c4Spec.parent)
    && canonicalJson(correction.derivation) === canonicalJson(c4Spec.derivation)
    && canonicalJson(correction.platformIdentity) === canonicalJson(c4Spec.platformIdentity)
    && canonicalJson(correction.changedImplementationExact) === canonicalJson(c4Spec.changedImplementationExact), 'BINARY_CORRECTION_IDENTITY');
  gate(evidence?.tools?.library?.uri === 'scripts/lib/b41-c4-platform-binary-identity-correction.mjs'
    && evidence?.tools?.audit?.uri === 'scripts/audit-b41-c4-platform-binary-identity-correction.mjs', 'BINARY_CORRECTION_TOOL_URIS');
  gate(evidence?.success?.report?.blender?.executableSha256 === c4Spec.platformIdentity.linuxAmd64ExecutableSha256
    && evidence?.success?.report?.checks?.blenderExecutableSha256 === true, 'LINUX_BINARY_RUNTIME_IDENTITY');
  gate(evidence?.evidenceHash === hashB41C4Evidence(evidence), 'BINARY_CORRECTION_EVIDENCE_SELF_HASH');
  const c3Analysis = analyzeB41C3Evidence(projectToC3(evidence, c4Spec), c3Spec, c2Spec, c1Spec, baseSpec);
  for (const failure of c3Analysis.failures) gate(false, failure);
  return {
    schemaVersion: 'bfs.linuxAmd64BlenderRuntimeAnalysis.v0.5', passed: failures.length === 0,
    failures, c3Analysis, decision: failures[0] ?? c4Spec.acceptedVerdict,
  };
}
