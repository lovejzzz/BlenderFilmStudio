import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { canonicalJson, sha256Canonical } from './receipt-format.mjs';
import { repositoryRoot, sha256 } from './scene-spec.mjs';

export const B41_D3_SPEC_PATH = resolve(repositoryRoot, 'specs/linux-amd64-render-backend-control.v0.1.json');
export const B41_D3_SPEC_SHA256 = '3fd1404422ed62c44a42a8433e89b9dc70e98daaf0bc6c305d7b0aaa32d5fb3f';
export const B41_D3_PREREG_COMMIT = '294daf383b93d294ef1d66f8bf30b3913ceeda8e';
const HEX_64 = /^[a-f0-9]{64}$/;

export async function readB41D3Spec() {
  const bytes = await readFile(B41_D3_SPEC_PATH);
  const digest = sha256(bytes);
  if (digest !== B41_D3_SPEC_SHA256) throw new Error(`B41-D3 spec SHA mismatch: ${digest}`);
  return JSON.parse(bytes);
}

export function hashB41D3Evidence(evidence) {
  const copy = structuredClone(evidence);
  for (const key of ['analysis', 'verdict', 'nonClaims', 'evidenceHash']) delete copy[key];
  return sha256Canonical(copy);
}

export function classifyB41D3(controls) {
  const completed = id => controls.find(control => control.id === id)?.completed === true;
  if (completed('EEVEE_VULKAN')) return 'VULKAN_EEVEE_ROUTE_AVAILABLE';
  if (completed('CYCLES_CPU')) return 'CPU_ONLY_WORKER_CONFIRMED_EEVEE_GPU_ROUTE_ABSENT';
  return 'NO_RENDER_CONTROL_COMPLETES';
}

export function expectedB41D3Argv(control) {
  return [...control.gpuBackendArgv, '--background', '--factory-startup', '--disable-autoexec', '--offline-mode', '--python-exit-code', '1', '--python', '/inputs/render-backend-control.py'];
}

export function expectedB41D3Environment(baseSpec, control) {
  return { ...baseSpec.containerContract.environmentValues, BFS_JOB_ID: `B41-D3-${control.id}`, BFS_CONTROL_ID: control.id, BFS_ENGINE: control.engine, BFS_SAMPLES: String(control.samples ?? 0), BFS_MILESTONE_PATH: '/outputs/milestones.jsonl', BFS_REPORT_PATH: '/outputs/report.json', BFS_OUTPUT_ROOT: '/outputs', BFS_INPUT_ROOT: '/inputs' };
}

export function analyzeB41D3Evidence(evidence, spec, baseSpec) {
  const failures = [];
  const gate = (condition, code) => { if (!condition && !failures.includes(code)) failures.push(code); };
  gate(evidence?.schemaVersion === 'bfs.linuxAmd64RenderBackendControlEvidence.v0.1' && evidence?.experimentId === 'B41-D3', 'EVIDENCE_SCHEMA');
  gate(evidence?.preregistration?.commit === B41_D3_PREREG_COMMIT && evidence?.preregistration?.specSha256 === B41_D3_SPEC_SHA256, 'PREREGISTRATION_IDENTITY');
  gate(canonicalJson(evidence?.parent) === canonicalJson(spec.parent), 'PARENT_IDENTITY');
  gate(evidence?.image?.id === spec.image.id && evidence?.image?.os === spec.image.os && evidence?.image?.architecture === spec.image.architecture && evidence?.image?.sizeBytes === spec.image.dockerReportedSizeBytes, 'IMAGE_IDENTITY');
  gate(/^[a-f0-9]{40}$/.test(evidence?.toolFreezeCommit ?? '') && ['runner', 'library', 'audit', 'control'].every(key => HEX_64.test(evidence?.tools?.[key]?.sha256 ?? '')), 'TOOL_IDENTITY');
  let diskPass = false;
  try { diskPass = evidence?.diskAdmission?.status === 'ACCEPTED' && BigInt(evidence.diskAdmission.freeAfterProjectedBytes) >= BigInt(spec.diskAdmission.minimumReserveBytes); } catch {}
  gate(diskPass, 'DISK_ADMISSION');
  gate(evidence?.inputFixture?.ocioTreeManifestSha256 === baseSpec.inputFixture.ocioTreeManifestSha256, 'OCIO_IDENTITY');
  gate(canonicalJson(evidence?.securityBoundary) === canonicalJson(spec.securityBoundary), 'SECURITY_BOUNDARY');
  const controls = evidence?.controls ?? [];
  gate(controls.length === 2 && canonicalJson(controls.map(({ id, engine, device, gpuBackendArgv }) => ({ id, engine, device, gpuBackendArgv }))) === canonicalJson(spec.controls.map(({ id, engine, device, gpuBackendArgv }) => ({ id, engine, device, gpuBackendArgv }))), 'CONTROL_SET');
  for (const expected of spec.controls) {
    const control = controls.find(item => item.id === expected.id);
    const names = Array.isArray(control?.milestones) ? control.milestones.map(item => item.name) : [];
    const inventoryMilestone = control?.milestones?.find(item => item.name === 'INVENTORY_RECORDED');
    gate(control?.attempted === true && control?.imageId === spec.image.id && canonicalJson(control?.argv) === canonicalJson(expectedB41D3Argv(expected)) && canonicalJson(control?.environment) === canonicalJson(expectedB41D3Environment(baseSpec, expected)), `CONTROL_${expected.id}_LAUNCH`);
    gate(control?.promotable === false && Number.isInteger(control?.exitCode) && control?.elapsedMs > 0 && control.milestones.every((item, index) => item.sequence === index + 1) && canonicalJson(names) === canonicalJson(spec.milestonesExactOrder.slice(0, names.length)), `CONTROL_${expected.id}_RECEIPT`);
    gate(Array.isArray(inventoryMilestone?.details?.paths) && canonicalJson(inventoryMilestone.details.paths.map(item => item.path)) === canonicalJson(spec.inventoryPaths), `CONTROL_${expected.id}_INVENTORY`);
  }
  gate(evidence?.classification === classifyB41D3(controls), 'CLASSIFICATION');
  const operations = evidence?.runtimeOperationsExecuted ?? [];
  gate(Array.isArray(operations) && !operations.some(item => /BUILD|PULL|DOWNLOAD/.test(item)) && operations.filter(item => item.startsWith('DOCKER_RUN_')).length === 2 && operations[0] === 'DOCKER_IMAGE_INSPECT' && operations.at(-1) === 'DOCKER_RUNNING_CONTAINER_CHECK', 'OPERATION_BOUNDARY');
  gate(evidence?.cleanup?.experimentContainersRunningAfter === 0 && evidence?.cleanup?.temporaryInputRootRemoved === true, 'CLEANUP_BOUNDARY');
  gate(evidence?.promotable === false, 'NON_PROMOTION');
  gate(Array.isArray(evidence?.errors) && evidence.errors.length === 0, 'RUN_ERRORS');
  gate(evidence?.evidenceHash === hashB41D3Evidence(evidence), 'EVIDENCE_SELF_HASH');
  return { schemaVersion: 'bfs.linuxAmd64RenderBackendControlAnalysis.v0.1', passed: failures.length === 0, failures, decision: failures[0] ?? spec.acceptedVerdict };
}
