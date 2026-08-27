import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { canonicalJson, sha256File } from './receipt-format.mjs';
import { repositoryRoot, sha256 } from './scene-spec.mjs';

export const B42_SPEC_PATH = resolve(repositoryRoot, 'specs/linux-amd64-compiler-repro.v0.1.json');
export const B42_SPEC_SHA256 = '9cfc3839ef61b9e000850f2ee112e22f5e816f5b8c6f0a4b3daede9bb6265fde';
export const B42_PREREG_COMMIT = '636552dccf7502d0af8d61673f54607280a86934';

export async function readB42Spec() {
  const bytes = await readFile(B42_SPEC_PATH);
  const digest = sha256(bytes);
  if (digest !== B42_SPEC_SHA256) throw new Error(`B42 spec SHA mismatch: ${digest}`);
  return JSON.parse(bytes);
}

export function hashB42Evidence(evidence) {
  const copy = structuredClone(evidence);
  for (const key of ['analysis', 'verdict', 'nonClaims', 'evidenceHash']) delete copy[key];
  return sha256(Buffer.from(canonicalJson(copy)));
}

export async function observeSuccessfulRun(runRoot) {
  const manifestPath = resolve(runRoot, 'scene.manifest.json');
  const structurePath = resolve(runRoot, 'scene.structure.canonical.json');
  const blendPath = resolve(runRoot, 'scene.blend');
  const [manifestText, structureText] = await Promise.all([readFile(manifestPath, 'utf8'), readFile(structurePath, 'utf8')]);
  const manifest = JSON.parse(manifestText);
  return {
    manifest: { sha256: await sha256File(manifestPath), value: manifest },
    structure: { sha256: await sha256File(structurePath), bytes: Buffer.byteLength(structureText), value: JSON.parse(structureText) },
    blend: { sha256: await sha256File(blendPath), bytes: (await readFile(blendPath)).length },
  };
}

export function analyzeB42Evidence(evidence, spec) {
  const failures = [];
  const gate = (condition, code) => { if (!condition && !failures.includes(code)) failures.push(code); };
  gate(evidence?.schemaVersion === 'bfs.linuxAmd64CompilerReproEvidence.v0.1' && evidence?.experimentId === 'B42', 'EVIDENCE_SCHEMA');
  gate(evidence?.preregistration?.commit === B42_PREREG_COMMIT && evidence?.preregistration?.specSha256 === B42_SPEC_SHA256, 'PREREGISTRATION_IDENTITY');
  gate(canonicalJson(evidence?.parent) === canonicalJson(spec.parent), 'PARENT_IDENTITY');
  gate(canonicalJson(evidence?.image) === canonicalJson({ id: spec.image.id, os: spec.image.os, architecture: spec.image.architecture, sizeBytes: spec.image.dockerReportedSizeBytes }), 'IMAGE_IDENTITY');
  gate(/^[a-f0-9]{40}$/.test(evidence?.toolFreezeCommit ?? '') && Object.values(evidence?.tools ?? {}).every(item => /^[a-f0-9]{64}$/.test(item.sha256)), 'TOOL_IDENTITY');
  gate(evidence?.diskAdmission?.status === 'ACCEPTED' && BigInt(evidence.diskAdmission.freeAfterProjectedBytes) >= BigInt(spec.diskAdmission.minimumReserveBytes), 'DISK_ADMISSION');
  gate(canonicalJson(evidence?.securityBoundary) === canonicalJson(spec.containerContract), 'SECURITY_BOUNDARY');
  gate((evidence?.benchmarks ?? []).length === spec.benchmarks.length, 'BENCHMARK_COUNT');
  for (const expected of spec.benchmarks) {
    const benchmark = evidence.benchmarks?.find(item => item.id === expected.id);
    gate(benchmark?.plans?.length === 2 && benchmark.plans.every(plan => plan.fileSha256 === expected.expectedPlan.fileSha256 && plan.planHash === expected.expectedPlan.planHash) && benchmark.planFilesByteEqual === true, `${expected.id}_PLAN_REPRO`);
    gate(benchmark?.runs?.length === 2 && benchmark.runs.every(run => run.exitCode === 0 && run.timeoutTriggered === false && run.completed === true), `${expected.id}_RUNS_COMPLETE`);
    gate(benchmark?.runs?.every(run => run.observed.manifest.value.execution.planHash === expected.expectedPlan.planHash && run.observed.manifest.value.structureHash === expected.expectedStructureHash && run.observed.structure.sha256 === expected.expectedStructureHash), `${expected.id}_MANIFEST_BINDING`);
    gate(benchmark?.structureFilesByteEqual === true && benchmark?.structureHash === expected.expectedStructureHash, `${expected.id}_STRUCTURE_REPRO`);
  }
  gate(evidence?.negativeControl?.exitCode !== 0 && evidence?.negativeControl?.timeoutTriggered === false && evidence?.negativeControl?.diagnosticMatched === true && evidence?.negativeControl?.outputFiles === 0, 'TAMPER_REJECTION');
  gate(Array.isArray(evidence?.runtimeOperationsExecuted) && !evidence.runtimeOperationsExecuted.some(item => /BUILD|PULL|DOWNLOAD/.test(item)) && evidence.runtimeOperationsExecuted.filter(item => item.startsWith('DOCKER_RUN_')).length === 5, 'OPERATION_BOUNDARY');
  gate(evidence?.cleanup?.experimentContainersRunningAfter === 0, 'CLEANUP_BOUNDARY');
  gate(Array.isArray(evidence?.errors) && evidence.errors.length === 0, 'RUN_ERRORS');
  gate(evidence?.evidenceHash === hashB42Evidence(evidence), 'EVIDENCE_SELF_HASH');
  return { schemaVersion: 'bfs.linuxAmd64CompilerReproAnalysis.v0.1', passed: failures.length === 0, failures, decision: failures[0] ?? spec.acceptedVerdict };
}
