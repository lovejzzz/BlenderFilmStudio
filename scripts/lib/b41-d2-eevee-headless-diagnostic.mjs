import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { canonicalJson, sha256Canonical } from './receipt-format.mjs';
import { repositoryRoot, sha256 } from './scene-spec.mjs';

export const B41_D2_SPEC_PATH = resolve(repositoryRoot, 'specs/linux-amd64-eevee-headless-diagnostic.v0.1.json');
export const B41_D2_SPEC_SHA256 = '850d0d7b0cf9b1aa98ac203e846a3fcc7a0aa1bf5d581bad97d57411bee5369b';
export const B41_D2_PREREG_COMMIT = 'c96cb2cf8beb7c3a4525b9960e4bc5bb380c2b20';
const HEX_64 = /^[a-f0-9]{64}$/;

export async function readB41D2Spec() {
  const bytes = await readFile(B41_D2_SPEC_PATH);
  const digest = sha256(bytes);
  if (digest !== B41_D2_SPEC_SHA256) throw new Error(`B41-D2 spec SHA mismatch: ${digest}`);
  return JSON.parse(bytes);
}

export function hashB41D2Evidence(evidence) {
  const copy = structuredClone(evidence);
  for (const key of ['analysis', 'verdict', 'nonClaims', 'evidenceHash']) delete copy[key];
  return sha256Canonical(copy);
}

export function classifyB41D2(cells) {
  const completed = id => cells.find(cell => cell.id === id)?.completed === true;
  if (completed('B00')) return 'SLOW_BUT_COMPLETES_BASELINE';
  if ((completed('B01') && !completed('B00')) || (completed('B11') && !completed('B10'))) return 'SOFTWARE_SURFACELESS_REQUIRED';
  if ((completed('B10') && !completed('B00')) || (completed('B11') && !completed('B01'))) return 'EXPLICIT_OPENGL_REQUIRED';
  if (cells.some(cell => cell.completed)) return 'COMPLETES_WITHIN_DIAGNOSTIC_CEILING';
  return 'NO_COMPLETION_WITHIN_DIAGNOSTIC_CEILING';
}

export function expectedB41D2Argv(spec, cell) {
  const backend = cell.gpuBackend === 'EXPLICIT_OPENGL' ? spec.design.explicitOpenGlArgv : [];
  return [...backend, '--background', '--factory-startup', '--disable-autoexec', '--offline-mode', '--python-exit-code', '1', '--python', '/inputs/eevee-headless-diagnostic.py'];
}

export function expectedB41D2Environment(spec, baseSpec, cell) {
  const environment = {
    ...baseSpec.containerContract.environmentValues,
    BFS_JOB_ID: `B41-D2-${cell.id}`,
    BFS_CELL_ID: cell.id,
    BFS_MILESTONE_PATH: '/outputs/milestones.jsonl',
    BFS_REPORT_PATH: '/outputs/report.json',
    BFS_OUTPUT_ROOT: '/outputs',
    BFS_INPUT_ROOT: '/inputs',
  };
  if (cell.headlessEnvironment === 'MESA_SURFACELESS_SOFTWARE') Object.assign(environment, spec.design.softwareSurfacelessEnvironment);
  return environment;
}

export function analyzeB41D2Evidence(evidence, spec, baseSpec) {
  const failures = [];
  const gate = (condition, code) => { if (!condition && !failures.includes(code)) failures.push(code); };
  gate(evidence?.schemaVersion === 'bfs.linuxAmd64EeveeHeadlessDiagnosticEvidence.v0.1' && evidence?.experimentId === 'B41-D2', 'EVIDENCE_SCHEMA');
  gate(evidence?.preregistration?.commit === B41_D2_PREREG_COMMIT && evidence?.preregistration?.specSha256 === B41_D2_SPEC_SHA256, 'PREREGISTRATION_IDENTITY');
  gate(canonicalJson(evidence?.parent) === canonicalJson(spec.parent), 'PARENT_IDENTITY');
  gate(evidence?.image?.id === spec.image.id && evidence?.image?.os === spec.image.os && evidence?.image?.architecture === spec.image.architecture && evidence?.image?.sizeBytes === spec.image.dockerReportedSizeBytes, 'IMAGE_IDENTITY');
  gate(/^[a-f0-9]{40}$/.test(evidence?.toolFreezeCommit ?? '') && ['runner', 'library', 'audit', 'diagnostic'].every(key => HEX_64.test(evidence?.tools?.[key]?.sha256 ?? '')), 'TOOL_IDENTITY');
  let diskPass = false;
  try { diskPass = evidence?.diskAdmission?.status === 'ACCEPTED' && BigInt(evidence.diskAdmission.freeAfterProjectedBytes) >= BigInt(spec.diskAdmission.minimumReserveBytes); } catch {}
  gate(diskPass, 'DISK_ADMISSION');
  gate(canonicalJson(evidence?.design) === canonicalJson(spec.design), 'DESIGN_IDENTITY');
  gate(canonicalJson(evidence?.launchBoundary) === canonicalJson(spec.frozenLaunchBoundary), 'LAUNCH_BOUNDARY');
  gate(evidence?.inputFixture?.ocioTreeManifestSha256 === baseSpec.inputFixture.ocioTreeManifestSha256, 'OCIO_IDENTITY');
  const cells = evidence?.cells ?? [];
  gate(cells.length === 4 && canonicalJson(cells.map(({ id, gpuBackend, headlessEnvironment }) => ({ id, gpuBackend, headlessEnvironment }))) === canonicalJson(spec.design.cells), 'CELL_SET');
  for (const expected of spec.design.cells) {
    const cell = cells.find(item => item.id === expected.id);
    gate(cell?.attempted === true && cell?.imageId === spec.image.id && canonicalJson(cell?.argv) === canonicalJson(expectedB41D2Argv(spec, expected))
      && canonicalJson(cell?.environment) === canonicalJson(expectedB41D2Environment(spec, baseSpec, expected)), `CELL_${expected.id}_LAUNCH`);
    const milestoneNames = Array.isArray(cell?.milestones) ? cell.milestones.map(item => item.name) : [];
    gate(cell?.promotable === false && Number.isInteger(cell?.exitCode) && cell?.elapsedMs > 0
      && Array.isArray(cell?.milestones) && cell.milestones.every((item, index) => item.sequence === index + 1)
      && canonicalJson(milestoneNames) === canonicalJson(spec.design.milestonesExactOrder.slice(0, milestoneNames.length)), `CELL_${expected.id}_RECEIPT`);
  }
  gate(evidence?.classification === classifyB41D2(cells), 'CLASSIFICATION');
  const operations = evidence?.runtimeOperationsExecuted ?? [];
  gate(Array.isArray(operations) && !operations.some(item => /BUILD|PULL|DOWNLOAD/.test(item))
    && operations.filter(item => item.startsWith('DOCKER_RUN_')).length === 4
    && operations[0] === 'DOCKER_IMAGE_INSPECT' && operations.at(-1) === 'DOCKER_RUNNING_CONTAINER_CHECK', 'OPERATION_BOUNDARY');
  gate(evidence?.cleanup?.experimentContainersRunningAfter === 0 && evidence?.cleanup?.temporaryInputRootRemoved === true, 'CLEANUP_BOUNDARY');
  gate(evidence?.promotable === false, 'NON_PROMOTION');
  gate(Array.isArray(evidence?.errors) && evidence.errors.length === 0, 'RUN_ERRORS');
  gate(evidence?.evidenceHash === hashB41D2Evidence(evidence), 'EVIDENCE_SELF_HASH');
  return { schemaVersion: 'bfs.linuxAmd64EeveeHeadlessDiagnosticAnalysis.v0.1', passed: failures.length === 0, failures, decision: failures[0] ?? spec.acceptedVerdict };
}
