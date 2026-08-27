import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { canonicalJson, repositoryRoot, sha256 } from './scene-spec.mjs';

export const B44_SPEC_URI = 'specs/codex-to-blender-worker-promotion.v0.1.json';
export const B44_SPEC_PATH = resolve(repositoryRoot, B44_SPEC_URI);
export const B44_SPEC_SHA256 = '5c07d0b1f9b29f6791bc19c75ebe2311012b78e3fd51ed2294fc9c137124a88c';
export const B44_PREREG_COMMIT = 'f44e16404df18af67f46533778b4cce367b5fc91';

export async function readB44Spec() {
  const bytes = await readFile(B44_SPEC_PATH);
  const digest = sha256(bytes);
  if (digest !== B44_SPEC_SHA256) throw new Error(`B44 spec SHA mismatch: ${digest}`);
  return JSON.parse(bytes);
}

export function hashB44Evidence(evidence) {
  const copy = structuredClone(evidence);
  for (const key of ['evidenceHash', 'analysis', 'attacks', 'attacksPassed', 'verdict', 'nonClaims']) delete copy[key];
  return sha256(Buffer.from(canonicalJson(copy)));
}

export function analyzeB44Evidence(evidence, spec, { requireAttacks = true } = {}) {
  const failures = [];
  const gate = (condition, code) => { if (!condition && !failures.includes(code)) failures.push(code); };
  gate(evidence?.schemaVersion === 'bfs.codexToBlenderWorkerPromotionEvidence.v0.1' && evidence?.experimentId === 'B44', 'EVIDENCE_SCHEMA');
  gate(evidence?.preregistration?.commit === B44_PREREG_COMMIT && evidence?.preregistration?.specSha256 === B44_SPEC_SHA256, 'PREREGISTRATION_IDENTITY');
  gate(canonicalJson(evidence?.parents) === canonicalJson(spec.parents), 'PARENT_IDENTITY');
  gate(evidence?.parentObservations?.length === 6 && evidence.parentObservations.every(item => item.match), 'PARENT_HASH');
  gate(evidence?.inputObservations?.every(item => item.match) && evidence?.inputObservations?.length >= 7, 'FROZEN_INPUT_HASH');
  gate(/^[a-f0-9]{40}$/.test(evidence?.toolFreezeCommit ?? '') && Object.values(evidence?.tools ?? {}).every(item => /^[a-f0-9]{64}$/.test(item.sha256 ?? '')), 'TOOL_IDENTITY');
  gate(canonicalJson(evidence?.image) === canonicalJson({ id: spec.image.id, os: spec.image.os, architecture: spec.image.architecture, sizeBytes: spec.image.dockerReportedSizeBytes }), 'IMAGE_IDENTITY');
  gate(evidence?.diskAdmission?.status === 'ACCEPTED' && BigInt(evidence.diskAdmission.freeAfterProjectedBytes) >= BigInt(spec.diskAdmission.minimumReserveBytes), 'DISK_ADMISSION');
  gate(canonicalJson(evidence?.securityBoundary) === canonicalJson(spec.containerContract), 'SECURITY_BOUNDARY');
  gate(evidence?.proposals?.length === spec.selectedProposals.length, 'PROPOSAL_COUNT');

  for (const expected of spec.selectedProposals) {
    const observed = evidence?.proposals?.find(item => item.id === expected.id);
    gate(observed?.fileSha256 === expected.fileSha256 && observed?.canonicalSha256 === expected.canonicalSha256, `PROPOSAL_IDENTITY_${expected.id}`);
    gate(observed?.schemaValid === true && observed?.semanticValid === true && observed?.decision === expected.decision, `PROPOSAL_SEMANTICS_${expected.id}`);
    if (expected.decision === 'ACCEPT') {
      gate(observed?.materialize === true && observed?.sceneSpecCount === 1 && observed?.buildPlanCount === 1, `MATERIALIZATION_${expected.id}`);
      gate(observed?.sceneSpec?.fileSha256 === expected.sceneSpec.fileSha256 && observed?.sceneSpec?.canonicalSha256 === expected.sceneSpec.canonicalSha256 && observed?.sceneSpec?.materializedCanonicalSha256 === expected.sceneSpec.canonicalSha256, `SCENE_IDENTITY_${expected.id}`);
      gate(observed?.buildPlan?.fileSha256 === expected.buildPlan.fileSha256 && observed?.buildPlan?.planHash === expected.buildPlan.planHash, `PLAN_IDENTITY_${expected.id}`);
      gate(observed?.runs?.length === 2 && observed.runs.every(run => run.exitCode === 0 && run.timeoutTriggered === false && run.completed === true), `RUNS_COMPLETE_${expected.id}`);
      gate(observed?.runs?.every(run => run.observed?.manifest?.value?.execution?.planHash === expected.buildPlan.planHash
        && run.observed.manifest.value.execution.sourceSceneCanonicalSha256 === observed.buildPlan.sourceSceneCanonicalSha256
        && run.observed.manifest.value.structureHash === run.observed.structure.sha256), `MANIFEST_BINDING_${expected.id}`);
      gate(observed?.structureFilesByteEqual === true && observed?.runs?.[0]?.observed?.structure?.sha256 === observed?.runs?.[1]?.observed?.structure?.sha256 && observed?.structureHash === observed?.runs?.[0]?.observed?.structure?.sha256, `STRUCTURE_REPRO_${expected.id}`);
    } else {
      gate(observed?.materialize === false && observed?.sceneSpecCount === 0 && observed?.buildPlanCount === 0 && observed?.containerLaunchCount === 0, `PRE_CONTAINER_REJECTION_${expected.id}`);
    }
  }

  const operations = evidence?.runtimeOperationsExecuted ?? [];
  gate(Array.isArray(operations) && operations[0] === 'DOCKER_IMAGE_INSPECT' && operations.at(-1) === 'DOCKER_RUNNING_CONTAINER_CHECK'
    && operations.filter(item => item.startsWith('DOCKER_RUN_')).length === 4
    && !operations.some(item => /BUILD|PULL|DOWNLOAD/.test(item)), 'OPERATION_BOUNDARY');
  gate(evidence?.cleanup?.experimentContainersRunningAfter === 0, 'CLEANUP_BOUNDARY');
  gate(Array.isArray(evidence?.errors) && evidence.errors.length === 0, 'RUN_ERRORS');
  if (requireAttacks) gate(evidence?.attacks?.length === spec.attacks.length && evidence.attacks.every(item => item.passed), 'ATTACKS');
  gate(evidence?.evidenceHash === hashB44Evidence(evidence), 'EVIDENCE_SELF_HASH');
  return {
    schemaVersion: 'bfs.codexToBlenderWorkerPromotionAnalysis.v0.1',
    passed: failures.length === 0,
    failures,
    decision: failures[0] ?? spec.acceptedVerdict,
  };
}

export function runB44Attacks(evidence, spec) {
  const attacks = [
    ['A01_PROPOSAL_FILE', 'PROPOSAL_IDENTITY_TABLETOP-A', value => { value.proposals.find(item => item.id === 'TABLETOP-A').fileSha256 = '0'.repeat(64); }],
    ['A02_PROPOSAL_SEMANTICS', 'PROPOSAL_SEMANTICS_TABLETOP-A', value => { value.proposals.find(item => item.id === 'TABLETOP-A').decision = 'REJECT'; }],
    ['A03_ADAPTER_IDENTITY', 'FROZEN_INPUT_HASH', value => { value.inputObservations.find(item => item.uri === spec.inputs.adapter.uri).match = false; }],
    ['A04_SCENE_IDENTITY', 'SCENE_IDENTITY_TABLETOP-A', value => { value.proposals.find(item => item.id === 'TABLETOP-A').sceneSpec.fileSha256 = '0'.repeat(64); }],
    ['A05_PLAN_IDENTITY', 'PLAN_IDENTITY_TABLETOP-A', value => { value.proposals.find(item => item.id === 'TABLETOP-A').buildPlan.planHash = '0'.repeat(64); }],
    ['A06_IMAGE_IDENTITY', 'IMAGE_IDENTITY', value => { value.image.id = `sha256:${'0'.repeat(64)}`; }],
    ['A07_SECURITY_BOUNDARY', 'SECURITY_BOUNDARY', value => { value.securityBoundary.network = 'bridge'; }],
    ['A08_REJECTED_CONTAINER', 'PRE_CONTAINER_REJECTION_UNAUTHORIZED-A', value => { value.proposals.find(item => item.id === 'UNAUTHORIZED-A').containerLaunchCount = 1; }],
    ['A09_MANIFEST_PLAN', 'MANIFEST_BINDING_TABLETOP-A', value => { value.proposals.find(item => item.id === 'TABLETOP-A').runs[0].observed.manifest.value.execution.planHash = '0'.repeat(64); }],
    ['A10_STRUCTURE_REPLICATE', 'STRUCTURE_REPRO_TABLETOP-A', value => { value.proposals.find(item => item.id === 'TABLETOP-A').structureFilesByteEqual = false; }],
    ['A11_PROHIBITED_OPERATION', 'OPERATION_BOUNDARY', value => { value.runtimeOperationsExecuted.splice(-1, 0, 'DOCKER_PULL'); }],
    ['A12_EVIDENCE_HASH', 'EVIDENCE_SELF_HASH', value => { value.evidenceHash = '0'.repeat(64); }],
  ];
  return attacks.map(([id, expectedReason, mutate]) => {
    const value = structuredClone(evidence);
    mutate(value);
    const analysis = analyzeB44Evidence(value, spec, { requireAttacks: false });
    const observedReason = analysis.failures[0] ?? 'NO_REJECTION';
    return { id, expectedReason, observedReason, passed: observedReason === expectedReason };
  });
}
