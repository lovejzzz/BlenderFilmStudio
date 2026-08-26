import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { sha256Canonical } from './receipt-format.mjs';
import { repositoryRoot, sha256 } from './scene-spec.mjs';
import { hashB41Evidence, readB41Spec } from './b41-linux-amd64-blender-runtime-canary.mjs';
import {
  B41_C1_PREREG_COMMIT, B41_C1_SPEC_SHA256, analyzeB41C1Evidence, readB41C1Spec,
} from './b41-c1-docker-architecture-correction.mjs';

export const B41_C2_SPEC_PATH = resolve(repositoryRoot, 'specs/linux-amd64-blender-runtime-canary-tooling-correction.v0.1.json');
export const B41_C2_SPEC_SHA256 = '8875a592c9029af78f542547b8d07e2b189bc0e518fa9f693a474438c28dd38e';
export const B41_C2_PREREG_COMMIT = 'a3b401750d0f097088e269aa712d2dafb83a7b80';

export async function readB41C2Spec() {
  const bytes = await readFile(B41_C2_SPEC_PATH);
  const digest = sha256(bytes);
  if (digest !== B41_C2_SPEC_SHA256) throw new Error(`B41-C2 spec SHA mismatch: ${digest}`);
  return JSON.parse(bytes);
}

export function hashB41C2Evidence(evidence) {
  const copy = structuredClone(evidence);
  for (const key of ['evidenceHash', 'analysis', 'verdict', 'nonClaims']) delete copy[key];
  return sha256Canonical(copy);
}

function projectToC1(evidence) {
  const projected = structuredClone(evidence);
  for (const key of ['analysis', 'verdict', 'nonClaims', 'toolingCorrection']) delete projected[key];
  projected.schemaVersion = 'bfs.linuxAmd64BlenderRuntimeEvidence.v0.2';
  projected.experimentId = 'B41-C1';
  projected.preregistration = { commit: B41_C1_PREREG_COMMIT, specSha256: B41_C1_SPEC_SHA256 };
  projected.evidenceHash = hashB41Evidence(projected);
  return projected;
}

export function analyzeB41C2Evidence(evidence, c2Spec, c1Spec, baseSpec) {
  const failures = [];
  const gate = (condition, code) => { if (!condition && !failures.includes(code)) failures.push(code); };
  gate(evidence?.schemaVersion === 'bfs.linuxAmd64BlenderRuntimeEvidence.v0.3' && evidence?.experimentId === 'B41-C2', 'TOOLING_CORRECTION_EVIDENCE_SCHEMA');
  gate(evidence?.preregistration?.commit === B41_C2_PREREG_COMMIT
    && evidence?.preregistration?.specSha256 === B41_C2_SPEC_SHA256, 'TOOLING_CORRECTION_PREREGISTRATION');
  gate(evidence?.toolingCorrection?.c1SpecSha256 === c2Spec.parent.c1SpecSha256
    && evidence?.toolingCorrection?.c1PreregistrationCommit === c2Spec.parent.c1PreregistrationCommit
    && evidence?.toolingCorrection?.c1ToolFreezeCommit === c2Spec.parent.c1ToolFreezeCommit
    && evidence?.toolingCorrection?.failedResultSha256 === c2Spec.parent.failedResultSha256
    && evidence?.toolingCorrection?.failedAuditSha256 === c2Spec.parent.failedAuditSha256
    && JSON.stringify(evidence?.toolingCorrection?.changedImplementationExact) === JSON.stringify(c2Spec.changedImplementationExact), 'TOOLING_CORRECTION_IDENTITY');
  gate(evidence?.tools?.library?.uri === 'scripts/lib/b41-c2-build-receipt-tooling-correction.mjs'
    && evidence?.tools?.audit?.uri === 'scripts/audit-b41-c2-build-receipt-tooling-correction.mjs', 'CORRECTION_TOOL_URIS');
  gate(evidence?.evidenceHash === hashB41C2Evidence(evidence), 'TOOLING_CORRECTION_EVIDENCE_SELF_HASH');
  const c1Analysis = analyzeB41C1Evidence(projectToC1(evidence), c1Spec, baseSpec);
  const correctedParentFailures = c1Analysis.failures.filter(code => !['ARCH_CORRECTION_EVIDENCE_SELF_HASH', 'EVIDENCE_SELF_HASH'].includes(code));
  for (const failure of correctedParentFailures) gate(false, failure);
  return {
    schemaVersion: 'bfs.linuxAmd64BlenderRuntimeAnalysis.v0.3', passed: failures.length === 0,
    failures, c1Analysis, correctedParentFailures, decision: failures[0] ?? c2Spec.acceptedVerdict,
  };
}

export { readB41C1Spec, readB41Spec };
