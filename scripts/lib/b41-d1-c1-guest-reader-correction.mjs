import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { canonicalJson } from './receipt-format.mjs';
import { repositoryRoot, sha256 } from './scene-spec.mjs';
import {
  B41_D1_PREREG_COMMIT, B41_D1_SPEC_SHA256, analyzeB41D1Evidence, hashB41D1Evidence,
} from './b41-d1-linux-binary-identity-derivation.mjs';

export const B41_D1_C1_SPEC_PATH = resolve(repositoryRoot, 'specs/linux-amd64-blender-binary-identity-guest-correction.v0.1.json');
export const B41_D1_C1_SPEC_SHA256 = 'ffbafff1368ae25a3f82c2b92dc723aff10fb6f5fcd616b7627f4a0d4fa62af1';
export const B41_D1_C1_PREREG_COMMIT = '895c506578acd161ba4c14c5e75fb59c90b216b8';

export async function readB41D1C1Spec() {
  const bytes = await readFile(B41_D1_C1_SPEC_PATH);
  const digest = sha256(bytes);
  if (digest !== B41_D1_C1_SPEC_SHA256) throw new Error(`B41-D1-C1 spec SHA mismatch: ${digest}`);
  return JSON.parse(bytes);
}

export function hashB41D1C1Evidence(evidence) {
  return hashB41D1Evidence(evidence);
}

function projectToD1(evidence) {
  const projected = structuredClone(evidence);
  for (const key of ['analysis', 'verdict', 'nonClaims', 'guestCorrection']) delete projected[key];
  projected.schemaVersion = 'bfs.linuxAmd64BlenderBinaryIdentityDerivationEvidence.v0.1';
  projected.experimentId = 'B41-D1';
  projected.preregistration = { commit: B41_D1_PREREG_COMMIT, specSha256: B41_D1_SPEC_SHA256 };
  projected.evidenceHash = hashB41D1Evidence(projected);
  return projected;
}

export function analyzeB41D1C1Evidence(evidence, correctionSpec, baseSpec) {
  const failures = [];
  const gate = (condition, code) => { if (!condition && !failures.includes(code)) failures.push(code); };
  gate(evidence?.schemaVersion === 'bfs.linuxAmd64BlenderBinaryIdentityDerivationEvidence.v0.2'
    && evidence?.experimentId === 'B41-D1-C1', 'CORRECTION_EVIDENCE_SCHEMA');
  gate(evidence?.preregistration?.commit === B41_D1_C1_PREREG_COMMIT
    && evidence?.preregistration?.specSha256 === B41_D1_C1_SPEC_SHA256, 'CORRECTION_PREREGISTRATION');
  const correction = evidence?.guestCorrection ?? {};
  gate(canonicalJson(correction.parent) === canonicalJson(correctionSpec.parent)
    && correction.changedImplementationExact === correctionSpec.guestCorrection.changedImplementationExact, 'CORRECTION_IDENTITY');
  gate(correction.pythonVersion === correctionSpec.guestCorrection.pythonVersionExact
    && correction.reader === correctionSpec.guestCorrection.reader
    && correction.shellPipeline === false && correction.installPackages === false, 'GUEST_READER_IDENTITY');
  gate(evidence?.tools?.library?.uri === 'scripts/lib/b41-d1-c1-guest-reader-correction.mjs'
    && evidence?.tools?.audit?.uri === 'scripts/audit-b41-d1-c1-guest-reader-correction.mjs', 'CORRECTION_TOOL_URIS');
  gate(evidence?.evidenceHash === hashB41D1C1Evidence(evidence), 'CORRECTION_EVIDENCE_SELF_HASH');
  const baseAnalysis = analyzeB41D1Evidence(projectToD1(evidence), baseSpec);
  for (const failure of baseAnalysis.failures) gate(false, failure);
  return {
    schemaVersion: 'bfs.linuxAmd64BlenderBinaryIdentityDerivationAnalysis.v0.2',
    passed: failures.length === 0,
    failures,
    baseAnalysis,
    decision: failures[0] ?? correctionSpec.acceptedVerdict,
  };
}

function attackBase(evidence) {
  const copy = structuredClone(evidence);
  for (const key of ['analysis', 'verdict', 'nonClaims', 'attacks']) delete copy[key];
  return copy;
}

export function buildB41D1C1Attacks(evidence, correctionSpec, baseSpec) {
  const definitions = [
    ['archive-sha', candidate => { candidate.artifact.sha256 = '0'.repeat(64); }],
    ['archive-bytes', candidate => { candidate.artifact.bytes += 1; }],
    ['member-cardinality', candidate => { candidate.member.cardinality = 2; }],
    ['guest-hash', candidate => { candidate.derivations.guest.sha256 = 'f'.repeat(64); }],
    ['guest-bytes', candidate => { candidate.derivations.guest.bytes += 1; }],
    ['elf-machine', candidate => { candidate.elf.machineCode = 183; candidate.elf.machine = 'AArch64'; }],
    ['temp-retained', candidate => { candidate.cleanup.temporaryArchiveRemoved = false; }],
    ['runtime-op', candidate => { candidate.runtimeOperationsExecuted.push('BLENDER_EXECUTION'); }],
  ];
  return definitions.map(([id, mutate]) => {
    const candidate = attackBase(evidence);
    mutate(candidate);
    candidate.evidenceHash = hashB41D1C1Evidence(candidate);
    const analysis = analyzeB41D1C1Evidence(candidate, correctionSpec, baseSpec);
    const expectedFailure = baseSpec.acceptance.attacks.find(item => item.id === id)?.expectedFailure;
    return { id, expectedFailure, observedFailure: analysis.failures[0] ?? null, rejected: !analysis.passed, passed: analysis.failures[0] === expectedFailure };
  });
}
