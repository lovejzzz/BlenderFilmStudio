import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { canonicalJson } from './receipt-format.mjs';
import { repositoryRoot, sha256 } from './scene-spec.mjs';
import {
  B41_C4_PREREG_COMMIT, B41_C4_SPEC_SHA256, analyzeB41C4Evidence, hashB41C4Evidence,
} from './b41-c4-platform-binary-identity-correction.mjs';

export const B41_C5_SPEC_PATH = resolve(repositoryRoot, 'specs/linux-amd64-blender-runtime-canary-eevee-enum-correction.v0.1.json');
export const B41_C5_SPEC_SHA256 = '96f7d6ab2e802667ebd168a2acd3a8e578e0f7b48135bd132edc73d9ae202919';
export const B41_C5_PREREG_COMMIT = '53746d9fd484e8e9e8f01f3334acff51f4f8ecce';

export async function readB41C5Spec() {
  const bytes = await readFile(B41_C5_SPEC_PATH);
  const digest = sha256(bytes);
  if (digest !== B41_C5_SPEC_SHA256) throw new Error(`B41-C5 spec SHA mismatch: ${digest}`);
  return JSON.parse(bytes);
}

export function hashB41C5Evidence(evidence) {
  return hashB41C4Evidence(evidence);
}

function projectToC4(evidence, correctionSpec) {
  const projected = structuredClone(evidence);
  for (const key of ['analysis', 'verdict', 'nonClaims', 'eeveeEnumCorrection']) delete projected[key];
  projected.schemaVersion = 'bfs.linuxAmd64BlenderRuntimeEvidence.v0.5';
  projected.experimentId = 'B41-C4';
  projected.preregistration = { commit: B41_C4_PREREG_COMMIT, specSha256: B41_C4_SPEC_SHA256 };
  projected.tools.library.uri = 'scripts/lib/b41-c4-platform-binary-identity-correction.mjs';
  projected.tools.audit.uri = 'scripts/audit-b41-c4-platform-binary-identity-correction.mjs';
  if (projected.success?.report?.blender) projected.success.report.blender.renderEngine = correctionSpec.observedRuntime.rejectedIdentifier;
  projected.evidenceHash = hashB41C4Evidence(projected);
  return projected;
}

export function analyzeB41C5Evidence(evidence, c5Spec, c4Spec, c3Spec, c2Spec, c1Spec, baseSpec) {
  const failures = [];
  const gate = (condition, code) => { if (!condition && !failures.includes(code)) failures.push(code); };
  gate(evidence?.schemaVersion === 'bfs.linuxAmd64BlenderRuntimeEvidence.v0.6' && evidence?.experimentId === 'B41-C5', 'EEVEE_ENUM_CORRECTION_EVIDENCE_SCHEMA');
  gate(evidence?.preregistration?.commit === B41_C5_PREREG_COMMIT
    && evidence?.preregistration?.specSha256 === B41_C5_SPEC_SHA256, 'EEVEE_ENUM_CORRECTION_PREREGISTRATION');
  const correction = evidence?.eeveeEnumCorrection ?? {};
  gate(canonicalJson(correction.parent) === canonicalJson(c5Spec.parent)
    && canonicalJson(correction.observedRuntime) === canonicalJson(c5Spec.observedRuntime)
    && canonicalJson(correction.changedImplementationExact) === canonicalJson(c5Spec.changedImplementationExact), 'EEVEE_ENUM_CORRECTION_IDENTITY');
  gate(evidence?.tools?.library?.uri === 'scripts/lib/b41-c5-eevee-enum-correction.mjs'
    && evidence?.tools?.audit?.uri === 'scripts/audit-b41-c5-eevee-enum-correction.mjs', 'EEVEE_ENUM_CORRECTION_TOOL_URIS');
  gate(evidence?.success?.report?.blender?.renderEngine === c5Spec.observedRuntime.acceptedIdentifier, 'EEVEE_RUNTIME_IDENTITY');
  gate(evidence?.evidenceHash === hashB41C5Evidence(evidence), 'EEVEE_ENUM_CORRECTION_EVIDENCE_SELF_HASH');
  const c4Analysis = analyzeB41C4Evidence(projectToC4(evidence, c5Spec), c4Spec, c3Spec, c2Spec, c1Spec, baseSpec);
  for (const failure of c4Analysis.failures) gate(false, failure);
  return { schemaVersion: 'bfs.linuxAmd64BlenderRuntimeAnalysis.v0.6', passed: failures.length === 0, failures, c4Analysis, decision: failures[0] ?? c5Spec.acceptedVerdict };
}
