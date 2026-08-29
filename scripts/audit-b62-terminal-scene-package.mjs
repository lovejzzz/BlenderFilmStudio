#!/usr/bin/env node

import { execFile } from 'node:child_process';
import { createHash } from 'node:crypto';
import { open, readFile, realpath, readdir, statfs } from 'node:fs/promises';
import { dirname, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);
const repositoryRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const PREREGISTRATION_COMMIT = '1043af5d7b0767e87d851ea882d859bcacb61bf0';
const EXPERIMENT_URI = 'specs/b62-terminal-scene-package-compiler.v0.1.json';
const PROTOCOL_URI = 'research/2026-08-29-b62-terminal-scene-package-compiler-protocol.md';
const SCENE_SPEC_URI = 'specs/b62-terminal-proof.scene-package.v0.1.json';
const OCIO_URI = 'color/ocio/cg-config-v4.0.0_aces-v2.0_ocio-v2.5.ocio';
const OCIO_SHA256 = '24ec81841048fc5db160a7bad882263246183385c5d49d0e86e11464917ead15';
const EXPECTED_ROOT = 'experiments/b62-terminal-scene-package-v0-1';
const TOOLS = ['scripts/compile-b62-terminal-build-plan.mjs', 'blender/compile_b62_terminal_scene.py', 'blender/audit_b62_terminal_scene.py', 'scripts/run-b62-terminal-scene-package.mjs', 'scripts/audit-b62-terminal-scene-package.mjs'];

function req(condition, message) { if (!condition) throw new Error(message); }
function normalize(value) { if (typeof value === 'number' && Number.isFinite(value) && Number.isInteger(value)) return value; if (typeof value === 'number' && Number.isFinite(value)) { const bytes = Buffer.alloc(8); bytes.writeDoubleBE(value); return { $f64be: bytes.toString('hex') }; } if (Array.isArray(value)) return value.map(normalize); if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).sort(([a], [b]) => a.localeCompare(b)).map(([key, child]) => [key, normalize(child)])); return value; }
function normalizeLegacy(value) { if (typeof value === 'number' && Number.isFinite(value) && Number.isInteger(value)) return value; if (Array.isArray(value)) return value.map(normalizeLegacy); if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).sort(([a], [b]) => a.localeCompare(b)).map(([key, child]) => [key, normalizeLegacy(child)])); return value; }
const canonicalJson = value => JSON.stringify(normalize(value));
const hashBytes = value => createHash('sha256').update(value).digest('hex');
const hashFile = async path => hashBytes(await readFile(path));
function validSelf(value, field, mode = 'f64') { if (!value || !/^[0-9a-f]{64}$/.test(value[field] ?? '')) return false; const copy = structuredClone(value), expected = copy[field]; delete copy[field]; return hashBytes(mode === 'legacy' ? JSON.stringify(normalizeLegacy(copy)) : canonicalJson(copy)) === expected; }
function pathFor(uri) { req(typeof uri === 'string' && uri.length > 0 && !uri.startsWith('/') && !uri.split('/').includes('..') && !uri.includes('\\'), `unsafe ${uri}`); const path = resolve(repositoryRoot, uri); req(!relative(repositoryRoot, path).startsWith('../'), `escaped ${uri}`); return path; }
async function checkedExistingPath(uri) { const path = pathFor(uri), resolved = await realpath(path); req(path === resolved && !relative(repositoryRoot, resolved).startsWith('../'), `symlink or escape ${uri}`); return path; }
async function git(args, encoding = 'utf8') { return (await execFileAsync('/usr/bin/git', args, { cwd: repositoryRoot, encoding, timeout: 15000, maxBuffer: 32 * 1024 * 1024, env: { PATH: '/usr/bin:/bin', LANG: 'C', LC_ALL: 'C', GIT_CONFIG_NOSYSTEM: '1', GIT_TERMINAL_PROMPT: '0' } })).stdout; }
async function committedHash(commit, uri) { return hashBytes(await git(['show', `${commit}:${uri}`], null)); }
async function writeHashed(path, value, field) { const body = structuredClone(value); body[field] = hashBytes(canonicalJson(body)); const handle = await open(path, 'wx', 0o600); try { await handle.writeFile(`${JSON.stringify(body, null, 2)}\n`); await handle.sync(); } finally { await handle.close(); } return body; }
function parse() { const args = process.argv.slice(2), parsed = {}; for (let index = 0; index < args.length; index += 2) { req(args[index]?.startsWith('--') && args[index + 1], 'bad arguments'); parsed[args[index].slice(2)] = args[index + 1]; } req(parsed.root === EXPECTED_ROOT && /^[0-9a-f]{40}$/.test(parsed['tool-freeze-commit'] ?? ''), 'usage: --root exact --tool-freeze-commit sha'); return parsed; }

async function collectRoot(root) {
  const rows = [], symlinks = [];
  async function walk(directory) {
    for (const entry of await readdir(directory, { withFileTypes: true })) {
      const path = resolve(directory, entry.name), uri = relative(root, path).split('\\').join('/');
      if (entry.isSymbolicLink()) symlinks.push(uri);
      else if (entry.isDirectory()) await walk(path);
      else if (entry.isFile()) { const bytes = await readFile(path); rows.push({ uri, bytes: bytes.length, sha256: hashBytes(bytes) }); }
      else symlinks.push(uri);
    }
  }
  await walk(root);
  rows.sort((a, b) => a.uri.localeCompare(b.uri));
  return { files: rows, symlinks, fileCount: rows.length, bytes: rows.reduce((sum, row) => sum + row.bytes, 0), treeSha256: hashBytes(Buffer.from(rows.map(row => `${row.uri}\0${row.sha256}\n`).join(''))) };
}

async function readBound(binding, field, mode, semantic) {
  const path = await checkedExistingPath(binding.uri);
  req(await hashFile(path) === binding.sha256, `bound file drift ${binding.uri}`);
  const document = JSON.parse(await readFile(path, 'utf8'));
  req(validSelf(document, field, mode) && document[field] === binding[field], `bound self hash invalid ${binding.uri}`);
  semantic(document);
  return document;
}

function processPass(receipt, id, experiment) {
  if (!validSelf(receipt, 'processHash') || receipt.processId !== id || receipt.experimentId !== 'B62-T1-E1') return false;
  const result = receipt.result;
  if (result.outcome !== 'PASS' || result.child.exitCode !== 0 || result.breach !== null || result.termination.requested) return false;
  if (result.metrics.logBytes > experiment.processBudget.maximumCombinedLogBytesPerChild || result.metrics.output.bytes > experiment.processBudget.maximumOutputBytes) return false;
  if (id.startsWith('BLENDER_') && result.metrics.peakSampledRssBytes > experiment.processBudget.maximumPeakResidentSetSizeBytesPerBlender) return false;
  return true;
}

function mutationFixture({ sceneSpec, experiment, d6Build, toolHashes }) {
  return {
    masterExpected: experiment.parentEvidence.phase0.master.sha256,
    masterObserved: experiment.parentEvidence.phase0.master.sha256,
    phase0ReceiptExpected: experiment.parentEvidence.phase0.receipt.receiptHash,
    phase0ReceiptObserved: experiment.parentEvidence.phase0.receipt.receiptHash,
    d6FileExpected: experiment.parentEvidence.d6.build.sha256,
    d6FileObserved: experiment.parentEvidence.d6.build.sha256,
    d6ReportExpected: experiment.parentEvidence.d6.build.reportHash,
    d6ReportObserved: d6Build.reportHash,
    expectedSamples: d6Build.bake.map(row => ({ frame: row.frame, location: structuredClone(row.motionLocation), quaternion: structuredClone(row.motionQuaternion) })),
    samples: d6Build.bake.map(row => ({ frame: row.frame, location: structuredClone(row.motionLocation), quaternion: structuredClone(row.motionQuaternion) })),
    closeCamera: sceneSpec.timeline.cuts[2].camera,
    lens: sceneSpec.cameraIntervention.lensMillimeters,
    sourceUri: sceneSpec.sourceMaster.uri,
    rootExists: false,
    expectedToolHashes: structuredClone(toolHashes),
    observedToolHashes: structuredClone(toolHashes),
  };
}

function admitsFixture(value) {
  const safeUri = typeof value.sourceUri === 'string' && !value.sourceUri.startsWith('/') && !value.sourceUri.split('/').includes('..') && !value.sourceUri.includes('\\');
  const frames = value.samples.map(row => row.frame);
  const vectors = value.samples.every(row => row.location.length === 3 && row.quaternion.length === 4 && [...row.location, ...row.quaternion].every(Number.isFinite));
  return value.masterObserved === value.masterExpected && value.phase0ReceiptObserved === value.phase0ReceiptExpected && value.d6FileObserved === value.d6FileExpected && value.d6ReportObserved === value.d6ReportExpected && value.samples.length === 96 && frames.every((frame, index) => frame === 193 + index) && vectors && canonicalJson(value.samples) === canonicalJson(value.expectedSamples) && value.closeCamera === 'CAM_CLOSE_MOTION_TERMINAL' && value.lens === 65 && safeUri && value.rootExists === false && canonicalJson(value.observedToolHashes) === canonicalJson(value.expectedToolHashes);
}

function runAttacks(base, ids) {
  req(admitsFixture(base), 'base mutation fixture is not admitted');
  const attacks = [];
  function attack(id, mutate) { const value = structuredClone(base); mutate(value); attacks.push({ id, rejectedBeforeNativeSpawn: !admitsFixture(value) }); }
  attack('A01_SOURCE_MASTER_SHA_MUTATION', value => { value.masterObserved = '0'.repeat(64); });
  attack('A02_PHASE0_RECEIPT_SELF_HASH_MUTATION', value => { value.phase0ReceiptObserved = '1'.repeat(64); });
  attack('A03_D6_BUILD_FILE_SHA_MUTATION', value => { value.d6FileObserved = '2'.repeat(64); });
  attack('A04_D6_BUILD_REPORT_HASH_MUTATION', value => { value.d6ReportObserved = '3'.repeat(64); });
  attack('A05_D6_SAMPLE_FRAME_MUTATION', value => { value.samples[10].frame += 1; });
  attack('A06_D6_SAMPLE_LOCATION_MUTATION', value => { value.samples[20].location[0] += 0.01; });
  attack('A07_D6_SAMPLE_QUATERNION_MUTATION', value => { value.samples[30].quaternion[0] += 0.01; });
  attack('A08_CLOSE_CUT_CAMERA_MUTATION', value => { value.closeCamera = 'CAM_CLOSE_REFLECTION'; });
  attack('A09_TERMINAL_LENS_MUTATION', value => { value.lens = 100; });
  attack('A10_INPUT_PATH_TRAVERSAL', value => { value.sourceUri = '../outside.blend'; });
  attack('A11_EXISTING_OUTPUT_ROOT', value => { value.rootExists = true; });
  attack('A12_TOOL_IDENTITY_MUTATION', value => { value.observedToolHashes[TOOLS[0]] = 'f'.repeat(64); });
  req(attacks.map(row => row.id).join('\0') === ids.join('\0'), 'attack roster mismatch');
  return attacks;
}

async function main() {
  const args = parse(), freeze = args['tool-freeze-commit'];
  const experiment = JSON.parse(await readFile(await checkedExistingPath(EXPERIMENT_URI), 'utf8'));
  const sceneSpec = JSON.parse(await readFile(await checkedExistingPath(SCENE_SPEC_URI), 'utf8'));
  req(experiment.experimentId === 'B62-T1-E1' && experiment.output.formalRoot === EXPECTED_ROOT, 'experiment mismatch');
  const head = (await git(['rev-parse', 'HEAD'])).trim(), origin = (await git(['rev-parse', 'origin/main'])).trim();
  const preregExact = (await Promise.all([EXPERIMENT_URI, PROTOCOL_URI, SCENE_SPEC_URI].map(async uri => await hashFile(pathFor(uri)) === await committedHash(PREREGISTRATION_COMMIT, uri)))).every(Boolean);
  await git(['merge-base', '--is-ancestor', PREREGISTRATION_COMMIT, freeze]);
  const toolHashes = {};
  for (const uri of TOOLS) { toolHashes[uri] = await hashFile(await checkedExistingPath(uri)); req(toolHashes[uri] === await committedHash(freeze, uri), `tool drift ${uri}`); }
  const phase0Generation = await readBound(experiment.parentEvidence.phase0.generation, 'reportHash', 'legacy', value => req(value.status === 'PASS', 'Phase 0 generation invalid'));
  const phase0Audit = await readBound(experiment.parentEvidence.phase0.audit, 'auditHash', 'legacy', value => req(value.status === 'PASS', 'Phase 0 audit invalid'));
  const phase0Receipt = await readBound(experiment.parentEvidence.phase0.receipt, 'receiptHash', 'legacy', value => req(value.status === 'PASS', 'Phase 0 receipt invalid'));
  const d6Build = await readBound(experiment.parentEvidence.d6.build, 'reportHash', 'f64', value => req(value.status === 'PASS' && value.bake.length === 96, 'D6 build invalid'));
  const d6Audit = await readBound(experiment.parentEvidence.d6.audit, 'auditHash', 'f64', value => req(value.status === 'PASS' && value.scientificVerdict === experiment.parentEvidence.d6.audit.scientificVerdict, 'D6 audit invalid'));
  const d6Receipt = await readBound(experiment.parentEvidence.d6.receipt, 'receiptHash', 'f64', value => req(value.status === 'PASS', 'D6 receipt invalid'));
  const d6Human = await readBound(experiment.parentEvidence.d6.humanReview, 'reviewHash', 'f64', value => req(value.status === 'PASS' && value.scope === 'LABELED_CAMERA_ENGINEERING_REVIEW', 'D6 human review invalid'));
  const masterPath = await checkedExistingPath(experiment.parentEvidence.phase0.master.uri), masterExact = await hashFile(masterPath) === experiment.parentEvidence.phase0.master.sha256;
  const runtimeExact = await hashFile(experiment.runtime.blender.executable) === experiment.runtime.blender.sha256 && await hashFile(await checkedExistingPath(OCIO_URI)) === OCIO_SHA256;
  const root = pathFor(EXPECTED_ROOT), rootSnapshot = await collectRoot(root);
  const expectedPreAuditRoster = ['admission.json', 'build-plan.json', 'processes/BLENDER_COMPILE.json', 'processes/BLENDER_INDEPENDENT.json', 'processes/BUILDPLAN_A.json', 'processes/BUILDPLAN_B.json', 'reports/compile-report.json', 'reports/independent-audit.json', 'scene/B62_TERMINAL_PRODUCTION.blend'].sort();
  const rootRosterExact = rootSnapshot.symlinks.length === 0 && rootSnapshot.files.map(row => row.uri).join('\0') === expectedPreAuditRoster.join('\0');
  const admission = JSON.parse(await readFile(resolve(root, 'admission.json'), 'utf8'));
  const plan = JSON.parse(await readFile(resolve(root, 'build-plan.json'), 'utf8'));
  const compile = JSON.parse(await readFile(resolve(root, 'reports/compile-report.json'), 'utf8'));
  const independent = JSON.parse(await readFile(resolve(root, 'reports/independent-audit.json'), 'utf8'));
  const processIds = ['BUILDPLAN_A', 'BUILDPLAN_B', 'BLENDER_COMPILE', 'BLENDER_INDEPENDENT'];
  const processes = Object.fromEntries(await Promise.all(processIds.map(async id => [id, JSON.parse(await readFile(resolve(root, 'processes', `${id}.json`), 'utf8'))])));
  const processChecks = Object.fromEntries(processIds.map(id => [id, processPass(processes[id], id, experiment)]));
  const planSamplesExact = plan.camera.samples.length === 96 && plan.camera.samples.every((row, index) => row.frame === d6Build.bake[index].frame && canonicalJson(row.location) === canonicalJson(d6Build.bake[index].motionLocation) && canonicalJson(row.quaternion) === canonicalJson(d6Build.bake[index].motionQuaternion));
  const planDeterminismExact = processes.BUILDPLAN_A.result.outputPreview.includes(`PASS 96 ${plan.planHash}`) && processes.BUILDPLAN_B.result.outputPreview.includes(`PASS 96 ${plan.planHash}`);
  const before = compile.stateBefore, after = compile.stateAfter;
  const idDeltaExact = after.rosters.objects.join('\0') === [...before.rosters.objects, plan.camera.objectName].sort().join('\0') && after.rosters.cameras.join('\0') === [...before.rosters.cameras, plan.camera.dataName].sort().join('\0') && independent.terminalAction.name === plan.camera.actionName && independent.terminalAction.slots.flatMap(slot => slot.curves).length === 7;
  const markerRoutingExact = canonicalJson(after.markers) === canonicalJson(plan.timeline.cuts.map(row => ({ name: row.marker, frame: row.frame, camera: row.camera }))) && after.markers[0].camera === before.markers[0].camera && after.markers[1].camera === before.markers[1].camera && before.markers[2].camera === 'CAM_CLOSE_REFLECTION';
  const preservationExact = canonicalJson(before.assets) === canonicalJson(after.assets) && canonicalJson(before.actions) === canonicalJson(after.actions) && canonicalJson(before.states) === canonicalJson(after.states);
  const attacks = runAttacks(mutationFixture({ sceneSpec, experiment, d6Build, toolHashes }), experiment.mutationAttacks);
  const filesystem = await statfs(repositoryRoot), availableNow = Number(filesystem.bavail) * Number(filesystem.bsize);
  const pathsSafe = [EXPERIMENT_URI, PROTOCOL_URI, SCENE_SPEC_URI, OCIO_URI, EXPECTED_ROOT, ...Object.values(experiment.parentEvidence.phase0).map(value => value.uri), ...Object.values(experiment.parentEvidence.d6).map(value => value.uri), ...TOOLS].every(uri => { try { pathFor(uri); return true; } catch { return false; } });
  const gates = [
    ['G01_PREREGISTRATION_COMMIT_PUSHED_BEFORE_TOOL_CREATION_OR_FORMAL_ROOT', head === freeze && origin === freeze && Boolean(preregExact)],
    ['G02_INPUT_SCENE_PACKAGE_SPEC_EXACT_AND_SCHEMA_SUPPORTED', await hashFile(pathFor(SCENE_SPEC_URI)) === experiment.inputSceneSpec.sha256 && sceneSpec.schemaVersion === experiment.inputSceneSpec.schemaVersion],
    ['G03_PHASE0_PARENT_FILES_AND_SELF_HASHES_EXACT_PASS', phase0Generation.status === 'PASS' && phase0Audit.status === 'PASS' && phase0Receipt.status === 'PASS' && masterExact],
    ['G04_D6_PARENT_FILES_SELF_HASHES_MACHINE_VERDICT_AND_HUMAN_SCOPE_EXACT_PASS', d6Build.status === 'PASS' && d6Audit.scientificVerdict === experiment.parentEvidence.d6.audit.scientificVerdict && d6Receipt.scientificVerdict === d6Audit.scientificVerdict && d6Human.scope === experiment.parentEvidence.d6.humanReview.scope],
    ['G05_ALL_INPUT_AND_OUTPUT_PATHS_REPOSITORY_RELATIVE_NORMALIZED_NO_SYMLINK_ESCAPE', pathsSafe && rootSnapshot.symlinks.length === 0],
    ['G06_FRESH_OUTPUT_ROOT_AND_EXCLUSIVE_WRITES', admission.status === 'ADMITTED' && admission.operations.nativeProcessesBeforeAdmission === 0 && rootRosterExact],
    ['G07_CAPACITY_RESERVE_AND_PROJECTED_WRITES_ADMITTED_BEFORE_NATIVE_SPAWN', admission.resources.availableBytesBefore - admission.resources.projectedWriteBytes >= admission.resources.minimumFreeReserveBytes && availableNow >= experiment.processBudget.minimumFreeReserveBytes],
    ['G08_TOOL_AND_RUNTIME_IDENTITIES_EXACT', runtimeExact && canonicalJson(admission.bindings.tools) === canonicalJson(toolHashes) && admission.toolFreezeCommit === freeze],
    ['G09_TWO_INDEPENDENT_BUILDPLAN_COMPILATIONS_CANONICAL_BYTE_EXACT', validSelf(plan, 'planHash') && planDeterminismExact && processChecks.BUILDPLAN_A && processChecks.BUILDPLAN_B],
    ['G10_BUILDPLAN_COPIES_EXACT_D6_96_FRAME_MOTION_BAKE', planSamplesExact && plan.camera.curves === 7 && plan.camera.keysPerCurve === 96],
    ['G11_REAL_BLENDER_COMPILE_EXIT_ZERO_WITH_ZERO_RENDER_CALLS', processChecks.BLENDER_COMPILE && compile.status === 'PASS' && compile.operations.renderCalls === 0],
    ['G12_DERIVED_BLEND_EXISTS_FINITE_SIZE_AND_SOURCE_MASTER_UNCHANGED', masterExact && compile.derived.bytes > 0 && await hashFile(resolve(root, 'scene/B62_TERMINAL_PRODUCTION.blend')) === compile.derived.sha256],
    ['G13_ONLY_ONE_CAMERA_OBJECT_ONE_CAMERA_DATA_ONE_ACTION_ADDED', idDeltaExact],
    ['G14_THREE_MARKERS_EXACT_AND_ONLY_CLOSE_CAMERA_REROUTED', markerRoutingExact],
    ['G15_96_FRAME_LOCATION_AND_QUATERNION_BAKE_MATCHES_BUILDPLAN_WITHIN_1E_6', independent.poseRows.length === 96 && independent.maximumPoseError <= 1e-6 && independent.checks.all96PosesWithinTolerance],
    ['G16_PHASE0_ASSET_IDENTITY_MOTION_CONTACT_CORE_AND_LIGHT_STATE_PRESERVED', preservationExact && independent.checks.assetIdentityPreserved && independent.checks.contactCoreAndLightStatePreserved],
    ['G17_TIMELINE_RENDER_EXR_MOTION_BLUR_AND_COLOR_CONTRACT_PRESERVED', canonicalJson(before.timeline) === canonicalJson(after.timeline) && canonicalJson(before.render) === canonicalJson(after.render) && independent.checks.timelineRenderAndColorContractPreserved],
    ['G18_INDEPENDENT_FRESH_BLENDER_REOPEN_AGREES', processChecks.BLENDER_INDEPENDENT && independent.status === 'PASS' && Object.values(independent.checks).every(Boolean)],
    ['G19_TWELVE_SEMANTIC_MUTATION_ATTACKS_REJECTED_BEFORE_NATIVE_SPAWN', attacks.length === 12 && attacks.every(row => row.rejectedBeforeNativeSpawn)],
    ['G20_PROCESS_RESOURCE_ROOT_ROSTER_AND_SELF_HASHED_RECEIPTS_EXACT_WITH_ZERO_MODEL_NETWORK_DOCKER', Object.values(processChecks).every(Boolean) && rootSnapshot.bytes <= experiment.processBudget.maximumOutputBytes && compile.operations.modelCalls === 0 && compile.operations.networkCalls === 0 && compile.operations.dockerProcesses === 0 && independent.operations.renderCalls === 0 && independent.operations.modelCalls === 0 && independent.operations.networkCalls === 0 && independent.operations.dockerProcesses === 0],
  ].map(([id, pass]) => ({ id, pass: Boolean(pass) }));
  req(gates.map(row => row.id).join('\0') === experiment.acceptanceGates.join('\0'), 'gate roster mismatch');
  const pass = gates.every(row => row.pass) && attacks.every(row => row.rejectedBeforeNativeSpawn);
  const audit = await writeHashed(resolve(root, experiment.output.audit), {
    schemaVersion: 'bfs.b62TerminalScenePackageAudit.v0.1', experimentId: 'B62-T1-E1', status: pass ? 'PASS' : 'FAIL', scientificVerdict: pass ? experiment.decision.supportedVerdict : null,
    preregistrationCommit: PREREGISTRATION_COMMIT, toolFreezeCommit: freeze, gates, attacks,
    bindings: { admission: { sha256: await hashFile(resolve(root, 'admission.json')), admissionHash: admission.admissionHash }, buildPlan: { sha256: await hashFile(resolve(root, 'build-plan.json')), planHash: plan.planHash }, compile: { sha256: await hashFile(resolve(root, 'reports/compile-report.json')), reportHash: compile.reportHash }, independent: { sha256: await hashFile(resolve(root, 'reports/independent-audit.json')), reportHash: independent.reportHash }, sourceMaster: { sha256: await hashFile(masterPath) }, derived: { sha256: await hashFile(resolve(root, 'scene/B62_TERMINAL_PRODUCTION.blend')) } },
    processChecks, rootBeforeAudit: rootSnapshot, resources: { availableBytesAtAudit: availableNow, maximumOutputBytes: experiment.processBudget.maximumOutputBytes, minimumFreeReserveBytes: experiment.processBudget.minimumFreeReserveBytes },
    operations: { nodeAuditorProcesses: 1, priorBuildPlanCompilerProcesses: 2, priorBlenderStarts: 2, totalRenderCalls: 0, modelCalls: 0, networkCalls: 0, dockerProcesses: 0 }, nonClaims: experiment.nonClaims,
  }, 'auditHash');
  if (!pass) throw new Error(`audit gates failed: ${gates.filter(row => !row.pass).map(row => row.id).join(',')}`);
  console.log(`BFS_B62_T1_AUDIT PASS ${gates.length}/${gates.length} ${attacks.length}/${attacks.length} ${audit.auditHash}`);
}

main().catch(error => { console.error(error.stack ?? error.message); process.exitCode = 1; });
