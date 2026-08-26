import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { repositoryRoot, sha256 } from './scene-spec.mjs';
import { readB41Spec } from './b41-linux-amd64-blender-runtime-canary.mjs';
import { readB41C1Spec } from './b41-c1-docker-architecture-correction.mjs';
import {
  B41_C2_PREREG_COMMIT, B41_C2_SPEC_SHA256, analyzeB41C2Evidence, hashB41C2Evidence, readB41C2Spec,
} from './b41-c2-build-receipt-tooling-correction.mjs';

export const B41_C3_SPEC_PATH = resolve(repositoryRoot, 'specs/linux-amd64-blender-runtime-canary-buildx-correction.v0.1.json');
export const B41_C3_SPEC_SHA256 = 'd8f3ebca7c181bdced580f3bd588825a246fc80dcd94a352dc536738e3adad9f';
export const B41_C3_PREREG_COMMIT = '5ceb0e79b9b4afcc96fccd55212394334ca71a77';

export async function readB41C3Spec() {
  const bytes = await readFile(B41_C3_SPEC_PATH);
  const digest = sha256(bytes);
  if (digest !== B41_C3_SPEC_SHA256) throw new Error(`B41-C3 spec SHA mismatch: ${digest}`);
  return JSON.parse(bytes);
}

export function hashB41C3Evidence(evidence) {
  return hashB41C2Evidence(evidence);
}

function projectToC2(evidence) {
  const projected = structuredClone(evidence);
  for (const key of ['analysis', 'verdict', 'nonClaims', 'buildxCorrection', 'buildTransport']) delete projected[key];
  projected.schemaVersion = 'bfs.linuxAmd64BlenderRuntimeEvidence.v0.3';
  projected.experimentId = 'B41-C2';
  projected.preregistration = { commit: B41_C2_PREREG_COMMIT, specSha256: B41_C2_SPEC_SHA256 };
  projected.tools.library.uri = 'scripts/lib/b41-c2-build-receipt-tooling-correction.mjs';
  projected.tools.audit.uri = 'scripts/audit-b41-c2-build-receipt-tooling-correction.mjs';
  projected.evidenceHash = hashB41C2Evidence(projected);
  return projected;
}

export function analyzeB41C3Evidence(evidence, c3Spec, c2Spec, c1Spec, baseSpec) {
  const failures = [];
  const gate = (condition, code) => { if (!condition && !failures.includes(code)) failures.push(code); };
  gate(evidence?.schemaVersion === 'bfs.linuxAmd64BlenderRuntimeEvidence.v0.4' && evidence?.experimentId === 'B41-C3', 'BUILDX_CORRECTION_EVIDENCE_SCHEMA');
  gate(evidence?.preregistration?.commit === B41_C3_PREREG_COMMIT
    && evidence?.preregistration?.specSha256 === B41_C3_SPEC_SHA256, 'BUILDX_CORRECTION_PREREGISTRATION');
  gate(evidence?.buildxCorrection?.c2SpecSha256 === c3Spec.parent.c2SpecSha256
    && evidence?.buildxCorrection?.c2PreregistrationCommit === c3Spec.parent.c2PreregistrationCommit
    && evidence?.buildxCorrection?.c2ToolFreezeCommit === c3Spec.parent.c2ToolFreezeCommit
    && evidence?.buildxCorrection?.failedResultSha256 === c3Spec.parent.failedResultSha256
    && evidence?.buildxCorrection?.failedAuditSha256 === c3Spec.parent.failedAuditSha256
    && evidence?.buildxCorrection?.changedImplementationExact === c3Spec.changedImplementationExact, 'BUILDX_CORRECTION_IDENTITY');
  const transport = evidence?.buildTransport ?? {};
  gate(transport.buildxVersion === c3Spec.buildTransport.buildxVersion
    && transport.builderName === c3Spec.buildTransport.builderName
    && transport.driver === c3Spec.buildTransport.driver
    && transport.buildkitVersion === c3Spec.buildTransport.buildkitVersion
    && Array.isArray(transport.platforms) && transport.platforms.includes(c3Spec.buildTransport.requiredPlatform), 'BUILDX_TRANSPORT_IDENTITY');
  gate(Array.isArray(transport.command)
    && JSON.stringify(transport.command.slice(0, 4 + c3Spec.buildTransport.innerArgsPrefix.length))
      === JSON.stringify(['colima', 'ssh', '--', 'docker', ...c3Spec.buildTransport.innerArgsPrefix]), 'BUILDX_COMMAND_IDENTITY');
  gate(evidence?.tools?.library?.uri === 'scripts/lib/b41-c3-guest-buildx-correction.mjs'
    && evidence?.tools?.audit?.uri === 'scripts/audit-b41-c3-guest-buildx-correction.mjs', 'BUILDX_CORRECTION_TOOL_URIS');
  gate(evidence?.evidenceHash === hashB41C3Evidence(evidence), 'BUILDX_CORRECTION_EVIDENCE_SELF_HASH');
  const c2Analysis = analyzeB41C2Evidence(projectToC2(evidence), c2Spec, c1Spec, baseSpec);
  for (const failure of c2Analysis.failures) gate(false, failure);
  return {
    schemaVersion: 'bfs.linuxAmd64BlenderRuntimeAnalysis.v0.4', passed: failures.length === 0,
    failures, c2Analysis, decision: failures[0] ?? c3Spec.acceptedVerdict,
  };
}

export { readB41C2Spec, readB41C1Spec, readB41Spec };
