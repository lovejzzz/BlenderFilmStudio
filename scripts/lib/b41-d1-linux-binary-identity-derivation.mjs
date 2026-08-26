import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { canonicalJson, sha256Canonical } from './receipt-format.mjs';
import { repositoryRoot, sha256 } from './scene-spec.mjs';

export const B41_D1_SPEC_PATH = resolve(repositoryRoot, 'specs/linux-amd64-blender-binary-identity-derivation.v0.1.json');
export const B41_D1_SPEC_SHA256 = 'a6b9c0ef025d8e4394726b09250404f54e15ca1d2f795c3aaa70df606bd24ca8';
export const B41_D1_PREREG_COMMIT = 'bbef07079be510e1ccb1d77dab452d543fd30928';
const HEX_64 = /^[a-f0-9]{64}$/;

export async function readB41D1Spec() {
  const bytes = await readFile(B41_D1_SPEC_PATH);
  const digest = sha256(bytes);
  if (digest !== B41_D1_SPEC_SHA256) throw new Error(`B41-D1 spec SHA mismatch: ${digest}`);
  return JSON.parse(bytes);
}

export function hashB41D1Evidence(evidence) {
  const copy = structuredClone(evidence);
  for (const key of ['analysis', 'verdict', 'nonClaims', 'evidenceHash']) delete copy[key];
  return sha256Canonical(copy);
}

export function analyzeB41D1Evidence(evidence, spec) {
  const failures = [];
  const gate = (condition, code) => { if (!condition && !failures.includes(code)) failures.push(code); };
  gate(evidence?.schemaVersion === 'bfs.linuxAmd64BlenderBinaryIdentityDerivationEvidence.v0.1'
    && evidence?.experimentId === 'B41-D1', 'EVIDENCE_SCHEMA');
  gate(evidence?.preregistration?.commit === B41_D1_PREREG_COMMIT
    && evidence?.preregistration?.specSha256 === B41_D1_SPEC_SHA256, 'PREREGISTRATION_IDENTITY');
  gate(canonicalJson(evidence?.parent) === canonicalJson(spec.parent), 'PARENT_IDENTITY');
  gate(/^[a-f0-9]{40}$/.test(evidence?.toolFreezeCommit ?? '')
    && ['runner', 'library', 'audit'].every(key => HEX_64.test(evidence?.tools?.[key]?.sha256 ?? '')), 'TOOL_IDENTITY');
  let diskPass = false;
  try {
    diskPass = evidence?.diskAdmission?.status === 'ACCEPTED'
      && BigInt(evidence.diskAdmission.freeAfterProjectedBytes) >= BigInt(spec.diskAdmission.minimumReserveBytes);
  } catch {}
  gate(diskPass, 'DISK_ADMISSION');
  gate(evidence?.artifact?.url === spec.artifact.url
    && evidence?.artifact?.filename === spec.artifact.filename
    && evidence?.artifact?.bytes === spec.artifact.bytes
    && evidence?.artifact?.sha256 === spec.artifact.sha256, 'ARCHIVE_IDENTITY');
  gate(evidence?.member?.path === spec.artifact.member && evidence?.member?.cardinality === 1, 'MEMBER_IDENTITY');
  const host = evidence?.derivations?.host ?? {};
  const guest = evidence?.derivations?.guest ?? {};
  gate(HEX_64.test(host.sha256 ?? '') && Number.isSafeInteger(host.bytes) && host.bytes > 0
    && host.sha256 === guest.sha256 && host.bytes === guest.bytes, 'DERIVATION_AGREEMENT');
  gate(evidence?.elf?.magicHex === spec.derivation.requiredElf.magicHex
    && evidence?.elf?.class === spec.derivation.requiredElf.class
    && evidence?.elf?.endianness === spec.derivation.requiredElf.endianness
    && evidence?.elf?.machine === spec.derivation.requiredElf.machine
    && evidence?.elf?.machineCode === spec.derivation.requiredElf.machineCode, 'ELF_IDENTITY');
  gate(evidence?.cleanup?.temporaryArchiveRemoved === true, 'CLEANUP_BOUNDARY');
  gate(canonicalJson(evidence?.runtimeOperationsExecuted) === canonicalJson(spec.acceptance.runtimeOperationsExecutedExact), 'OPERATION_BOUNDARY');
  gate(Array.isArray(evidence?.errors) && evidence.errors.length === 0, 'RUN_ERRORS');
  gate(evidence?.evidenceHash === hashB41D1Evidence(evidence), 'EVIDENCE_SELF_HASH');
  return {
    schemaVersion: 'bfs.linuxAmd64BlenderBinaryIdentityDerivationAnalysis.v0.1',
    passed: failures.length === 0,
    failures,
    decision: failures[0] ?? spec.acceptedVerdict,
  };
}

function attackBase(evidence) {
  const copy = structuredClone(evidence);
  for (const key of ['analysis', 'verdict', 'nonClaims', 'attacks']) delete copy[key];
  return copy;
}

export function buildB41D1Attacks(evidence, spec) {
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
    candidate.evidenceHash = hashB41D1Evidence(candidate);
    const analysis = analyzeB41D1Evidence(candidate, spec);
    const expectedFailure = spec.acceptance.attacks.find(item => item.id === id)?.expectedFailure;
    return { id, expectedFailure, observedFailure: analysis.failures[0] ?? null, rejected: !analysis.passed, passed: analysis.failures[0] === expectedFailure };
  });
}
