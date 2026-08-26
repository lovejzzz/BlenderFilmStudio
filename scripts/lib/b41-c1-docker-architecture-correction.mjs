import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { repositoryRoot, sha256 } from './scene-spec.mjs';
import {
  B41_PREREG_COMMIT, B41_SPEC_SHA256, analyzeB41Evidence, hashB41Evidence, readB41Spec,
} from './b41-linux-amd64-blender-runtime-canary.mjs';

export const B41_C1_SPEC_PATH = resolve(repositoryRoot, 'specs/linux-amd64-blender-runtime-canary-arch-correction.v0.1.json');
export const B41_C1_SPEC_SHA256 = '4bf1c9ff97e395246148bae972455531b596fe38b0ad864a1a591c7b54b18aa1';
export const B41_C1_PREREG_COMMIT = '4974302e48922e9ca98a7253c0e6da17f89196d7';
export async function readB41C1Spec() {
  const bytes = await readFile(B41_C1_SPEC_PATH);
  const digest = sha256(bytes);
  if (digest !== B41_C1_SPEC_SHA256) throw new Error(`B41-C1 spec SHA mismatch: ${digest}`);
  return JSON.parse(bytes);
}

export function normalizeB41DockerArchitecture(raw, correctionSpec) {
  if (raw === correctionSpec.acceptedRawDockerArchitecture) return correctionSpec.canonicalDockerArchitecture;
  return raw;
}

function projectToB41(evidence) {
  const projected = structuredClone(evidence);
  for (const key of ['analysis', 'verdict', 'nonClaims', 'architectureCorrection']) delete projected[key];
  projected.schemaVersion = 'bfs.linuxAmd64BlenderRuntimeEvidence.v0.1';
  projected.experimentId = 'B41';
  projected.preregistration = { commit: B41_PREREG_COMMIT, specSha256: B41_SPEC_SHA256 };
  projected.evidenceHash = hashB41Evidence(projected);
  return projected;
}

export function analyzeB41C1Evidence(evidence, correctionSpec, baseSpec) {
  const failures = [];
  const gate = (condition, code) => { if (!condition && !failures.includes(code)) failures.push(code); };
  gate(evidence?.schemaVersion === 'bfs.linuxAmd64BlenderRuntimeEvidence.v0.2' && evidence?.experimentId === 'B41-C1', 'ARCH_CORRECTION_EVIDENCE_SCHEMA');
  gate(evidence?.preregistration?.commit === B41_C1_PREREG_COMMIT
    && evidence?.preregistration?.specSha256 === B41_C1_SPEC_SHA256, 'ARCH_CORRECTION_PREREGISTRATION');
  gate(evidence?.architectureCorrection?.parentSpecSha256 === correctionSpec.parent.specSha256
    && evidence?.architectureCorrection?.parentPreregistrationCommit === correctionSpec.parent.preregistrationCommit
    && evidence?.architectureCorrection?.parentToolFreezeCommit === correctionSpec.parent.toolFreezeCommit
    && evidence?.architectureCorrection?.rawDockerArchitecture === correctionSpec.acceptedRawDockerArchitecture
    && evidence?.architectureCorrection?.canonicalDockerArchitecture === correctionSpec.canonicalDockerArchitecture
    && evidence?.architectureCorrection?.changedImplementationExact === correctionSpec.changedImplementationExact, 'ARCH_CORRECTION_IDENTITY');
  gate(evidence?.runtime?.dockerServerArchitecture === correctionSpec.canonicalDockerArchitecture, 'DOCKER_ARCHITECTURE_CANONICAL');
  gate(evidence?.evidenceHash === hashB41Evidence(evidence), 'ARCH_CORRECTION_EVIDENCE_SELF_HASH');
  const parentAnalysis = analyzeB41Evidence(projectToB41(evidence), baseSpec);
  for (const failure of parentAnalysis.failures) gate(false, failure);
  return {
    schemaVersion: 'bfs.linuxAmd64BlenderRuntimeAnalysis.v0.2', passed: failures.length === 0,
    failures, parentAnalysis, decision: failures[0] ?? correctionSpec.acceptedVerdict,
  };
}

export { hashB41Evidence, readB41Spec };
