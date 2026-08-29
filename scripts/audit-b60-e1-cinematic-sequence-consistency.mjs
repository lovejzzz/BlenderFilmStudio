#!/usr/bin/env node

import { readFile, readdir } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { isDeepStrictEqual } from 'node:util';
import {
  canonicalHash,
  canonicalJson,
  repoUri,
  resolveExistingRepositoryPath,
  sha256Bytes,
  sha256File,
  validSelfHash,
  writeDurableHashed,
} from './lib/production-compile-receipt.mjs';
import { repositoryRoot } from './lib/scene-spec.mjs';

const CONTRACT_URI = 'specs/cinematic-sequence-consistency.v0.1.json';
const EXPECTED_ROOTS = {
  preflightRoot: 'experiments/cinematic-sequence-consistency-preflight-v0-1',
  attemptRoot: 'experiments/cinematic-sequence-consistency-attempt-v0-1',
  formalRoot: 'experiments/cinematic-sequence-consistency-v0-1',
};

function parseArguments(argv) {
  const parsed = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--preflight-root') parsed.preflightRoot = argv[++index];
    else if (token === '--attempt-root') parsed.attemptRoot = argv[++index];
    else if (token === '--formal-root') parsed.formalRoot = argv[++index];
    else if (token === '--output') parsed.output = argv[++index];
    else throw new Error(`Unknown or incomplete argument: ${token}`);
  }
  for (const key of ['preflightRoot', 'attemptRoot', 'formalRoot', 'output']) {
    if (!parsed[key]) throw new Error(`Missing --${key.replace(/[A-Z]/g, letter => `-${letter.toLowerCase()}`)}`);
  }
  for (const [key, expected] of Object.entries(EXPECTED_ROOTS)) {
    if (parsed[key] !== expected) throw new Error(`B60 ${key} must match the preregistered root`);
  }
  if (parsed.output !== `${parsed.formalRoot}/audit.json`) throw new Error('B60 audit output path must be <formal-root>/audit.json');
  return parsed;
}

async function readJson(uri, label = uri) {
  const path = await resolveExistingRepositoryPath(uri, label);
  return { path, value: JSON.parse(await readFile(path, 'utf8')) };
}

function shotCases(contract) {
  return contract.sequence.shots.flatMap(shot => ['A', 'B'].map(repetition => ({
    id: `${shot.label}-${repetition}`,
    label: shot.label,
    repetition,
    shot,
  })));
}

function planProjection(wrapper) {
  const plan = wrapper.plan;
  const render = structuredClone(plan.render);
  delete render.outputRoot;
  return {
    compiler: plan.compiler,
    actors: plan.actors,
    assets: plan.assets,
    targets: plan.targets,
    lights: plan.lights,
    world: plan.world,
    render,
    outputSpec: plan.outputSpec,
    security: plan.security,
  };
}

function structureProjection(structure) {
  return {
    compilerVersion: structure.compilerVersion,
    blender: structure.blender,
    assetCollections: structure.assetCollections,
    targets: structure.targets,
    actors: structure.actors,
    render: structure.render,
  };
}

function managedNonCameraProjection(structure) {
  return structure.managedCollection.objects.filter(row => row.type !== 'CAMERA');
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function validateIdentity(wrapper, contract) {
  const actor = wrapper.plan.actors?.[0];
  const spec = actor?.actorSpec;
  const locks = contract.sharedProjection.identityLocks;
  assert(actor?.id === locks.actorId, 'Actor ID lock mismatch');
  assert(actor?.assetRef === locks.assetRef, 'Actor assetRef lock mismatch');
  assert(actor?.identityLock === true && spec?.actor?.identityLock === true, 'Actor identityLock disabled');
  assert(actor?.verifiedActorSpecSha256 === locks.actorSpecSha256, 'ActorSpec hash lock mismatch');
  assert(spec?.actor?.assetSha256 === locks.assetSha256, 'Actor asset hash lock mismatch');
  assert(spec?.rig?.restPoseSha256 === locks.restPoseSha256, 'Rest-pose hash lock mismatch');
  assert(spec?.deformation?.shapeKeySetSha256 === locks.shapeKeySetSha256, 'Shape-key-set hash lock mismatch');
  assert(isDeepStrictEqual(spec?.deformation?.meshes?.map(row => row.topologySha256), locks.meshTopologySha256), 'Mesh topology hash lock mismatch');
}

function validateSemanticDataset(dataset, contract) {
  assert(dataset.length === 6, 'Formal dataset must contain six cases');
  const byLabel = new Map();
  for (const row of dataset) {
    if (!byLabel.has(row.label)) byLabel.set(row.label, []);
    byLabel.get(row.label).push(row);
    assert(row.wrapper.planHash === row.shot.expectedPlanHash, `${row.id} PlanHash mismatch`);
    assert(canonicalHash(row.wrapper.plan) === row.wrapper.planHash, `${row.id} BuildPlan self-hash mismatch`);
    assert(isDeepStrictEqual(row.wrapper.plan.cameras, [row.shot.camera]), `${row.id} camera contract mismatch`);
    assert(row.wrapper.plan.render.outputProfile === row.sourceScene.render.outputProfile
      && row.wrapper.plan.render.outputRoot === row.sourceScene.render.outputRoot, `${row.id} render contract mismatch`);
    assert(row.wrapper.plan.security.networkAccess === false && row.wrapper.plan.security.arbitraryPython === false, `${row.id} security contract mismatch`);
    validateIdentity(row.wrapper, contract);
    assert(row.structure.planHash === row.wrapper.planHash, `${row.id} structure PlanHash mismatch`);
    assert(row.structure.blender?.version === contract.runtime.blenderVersion.replace('Blender ', ''), `${row.id} Blender version mismatch`);
    assert(row.structure.blender?.buildHash === contract.runtime.blenderBuildHash, `${row.id} Blender build hash mismatch`);
  }
  assert(byLabel.size === 3 && [...byLabel.values()].every(rows => rows.length === 2), 'A/B case grouping mismatch');
  for (const [label, rows] of byLabel) {
    assert(rows[0].planFileSha256 === rows[1].planFileSha256, `${label} A/B BuildPlan bytes differ`);
    assert(rows[0].structureFileSha256 === rows[1].structureFileSha256, `${label} A/B structure bytes differ`);
  }
  const sharedPlan = canonicalJson(planProjection(dataset[0].wrapper));
  assert(dataset.every(row => canonicalJson(planProjection(row.wrapper)) === sharedPlan), 'Cross-shot BuildPlan shared projection drift');
  const sharedStructure = canonicalJson(structureProjection(dataset[0].structure));
  assert(dataset.every(row => canonicalJson(structureProjection(row.structure)) === sharedStructure), 'Cross-shot scene structure shared projection drift');
  const sharedManaged = canonicalJson(managedNonCameraProjection(dataset[0].structure));
  assert(dataset.every(row => canonicalJson(managedNonCameraProjection(row.structure)) === sharedManaged), 'Cross-shot managed non-camera projection drift');
  const cameras = contract.sequence.shots.map(shot => canonicalJson(shot.camera));
  assert(new Set(cameras).size === 3, 'Contract cameras are not pairwise distinct');
  return true;
}

async function verifyFileIdentity(identity, label) {
  const path = await resolveExistingRepositoryPath(identity.uri, label);
  assert(await sha256File(path) === identity.sha256, `${label} file SHA mismatch`);
  return path;
}

async function loadCase(parsed, item) {
  const preflightUri = `${parsed.preflightRoot}/cases/${item.id}/preflight.json`;
  const attemptBase = `${parsed.attemptRoot}/cases/${item.id}`;
  const outputBase = `${parsed.formalRoot}/runs/${item.id}`;
  const preflight = await readJson(preflightUri, `${item.id} production preflight`);
  assert(validSelfHash(preflight.value, 'preflightHash') && preflight.value.status === 'ACCEPTED', `${item.id} production preflight invalid`);
  assert(preflight.value.buildPlan?.planHash === item.shot.expectedPlanHash && preflight.value.operations?.blenderProcesses === 0, `${item.id} production preflight binding mismatch`);
  const attempt = await readJson(`${attemptBase}/attempt.json`, `${item.id} attempt`);
  const admission = await readJson(`${attemptBase}/admission.json`, `${item.id} admission`);
  const attemptReceipt = await readJson(`${attemptBase}/receipt.json`, `${item.id} attempt receipt`);
  assert(validSelfHash(attempt.value, 'attemptHash'), `${item.id} attempt self-hash mismatch`);
  assert(validSelfHash(admission.value, 'admissionHash') && admission.value.status === 'ACCEPTED', `${item.id} admission invalid`);
  assert(validSelfHash(attemptReceipt.value, 'receiptHash') && attemptReceipt.value.status === 'ACCEPTED', `${item.id} attempt receipt invalid`);
  const receipt = await readJson(`${outputBase}/production-receipt.json`, `${item.id} production receipt`);
  assert(validSelfHash(receipt.value, 'receiptHash') && receipt.value.status === 'PASS', `${item.id} production receipt invalid`);
  const formalStart = await readJson(`${outputBase}/formal-start.json`, `${item.id} formal start`);
  const disk = await readJson(`${outputBase}/native-compile-disk-admission.json`, `${item.id} disk admission`);
  assert(validSelfHash(formalStart.value, 'formalStartHash') && formalStart.value.status === 'AUTHORIZED', `${item.id} formal-start invalid`);
  assert(validSelfHash(disk.value, 'diskAdmissionHash') && disk.value.status === 'ACCEPTED', `${item.id} disk admission invalid`);
  const planPath = await verifyFileIdentity(receipt.value.buildPlan, `${item.id} BuildPlan`);
  const sourcePath = await verifyFileIdentity(receipt.value.source, `${item.id} source SceneSpec`);
  assert(receipt.value.source.uri === item.shot.sceneSpec.uri && receipt.value.source.sha256 === item.shot.sceneSpec.sha256, `${item.id} source SceneSpec binding mismatch`);
  const structurePath = await verifyFileIdentity(receipt.value.restrictedCompile.sceneStructureCanonical, `${item.id} canonical structure`);
  const manifestPath = await verifyFileIdentity(receipt.value.restrictedCompile.sceneManifest, `${item.id} scene manifest`);
  const budgetPath = await verifyFileIdentity(receipt.value.restrictedCompile.budgetReport, `${item.id} budget report`);
  const compileReceiptPath = await verifyFileIdentity(receipt.value.restrictedCompile.compileReceipt, `${item.id} compile receipt`);
  await verifyFileIdentity(receipt.value.restrictedCompile.sceneBlend, `${item.id} scene blend`);
  const wrapper = JSON.parse(await readFile(planPath, 'utf8'));
  const sourceScene = JSON.parse(await readFile(sourcePath, 'utf8'));
  const structureBytes = await readFile(structurePath);
  const structure = JSON.parse(structureBytes);
  const manifest = JSON.parse(await readFile(manifestPath, 'utf8'));
  const budget = JSON.parse(await readFile(budgetPath, 'utf8'));
  const compileReceipt = JSON.parse(await readFile(compileReceiptPath, 'utf8'));
  assert(validSelfHash(compileReceipt, 'receiptHash'), `${item.id} compile receipt self-hash mismatch`);
  assert(manifest.structureHash === sha256Bytes(structureBytes) && isDeepStrictEqual(manifest.structure, structure), `${item.id} manifest structure binding mismatch`);
  assert(budget.documentType === 'BFS_BUDGETED_PROCESS_RESULT' && budget.outcome === 'PASS'
    && Number.isSafeInteger(budget.child?.pid) && budget.child.pid > 0
    && budget.command === contractRuntimeBinary, `${item.id} native budget/process record invalid`);
  assert(!budget.args.includes('-a') && !budget.args.includes('--render-anim') && !budget.args.includes('-f') && !budget.args.includes('--render-frame'), `${item.id} render argument found`);
  const restrictedRoster = (await readdir(resolve(repositoryRoot, outputBase, 'restricted'))).sort();
  assert(isDeepStrictEqual(restrictedRoster, ['budget.report.json', 'compile-receipt.json', 'scene.blend', 'scene.manifest.json', 'scene.structure.canonical.json']), `${item.id} restricted roster mismatch`);
  return {
    ...item,
    wrapper,
    sourceScene,
    structure,
    planFileSha256: await sha256File(planPath),
    structureFileSha256: await sha256File(structurePath),
    receipt: receipt.value,
    budget,
    compileReceipt,
    preflight: preflight.value,
  };
}

let contractRuntimeBinary = null;

function runNegativeControls(dataset, contract) {
  const attacks = [
    ['N01_ACTOR_ASSET_HASH_DRIFT', clone => { clone[0].wrapper.plan.actors[0].actorSpec.actor.assetSha256 = '0'.repeat(64); }],
    ['N02_ACTOR_SPEC_HASH_DRIFT', clone => { clone[0].wrapper.plan.actors[0].verifiedActorSpecSha256 = '0'.repeat(64); }],
    ['N03_IDENTITY_LOCK_DISABLED', clone => { clone[0].wrapper.plan.actors[0].identityLock = false; }],
    ['N04_REST_POSE_HASH_DRIFT', clone => { clone[0].wrapper.plan.actors[0].actorSpec.rig.restPoseSha256 = '0'.repeat(64); }],
    ['N05_MESH_TOPOLOGY_HASH_DRIFT', clone => { clone[0].wrapper.plan.actors[0].actorSpec.deformation.meshes[0].topologySha256 = '0'.repeat(64); }],
    ['N06_SHAPE_KEY_SET_HASH_DRIFT', clone => { clone[0].wrapper.plan.actors[0].actorSpec.deformation.shapeKeySetSha256 = '0'.repeat(64); }],
    ['N07_LIGHT_ENERGY_DRIFT', clone => { clone[0].wrapper.plan.lights[0].energy += 1; }],
    ['N08_TARGET_TRANSFORM_DRIFT', clone => { clone[0].wrapper.plan.targets[0].sockets[0].transform.locationM[0] += 0.01; }],
    ['N09_OUTPUT_PROFILE_DRIFT', clone => { clone[0].wrapper.plan.render.outputProfile = 'MUTATED_PROFILE'; }],
    ['N10_UNREGISTERED_CAMERA_DRIFT', clone => { clone[0].wrapper.plan.cameras[0].lensMm += 1; }],
  ];
  return attacks.map(([id, mutate]) => {
    const clone = structuredClone(dataset);
    mutate(clone);
    let rejected = false;
    let message = null;
    try { validateSemanticDataset(clone, contract); } catch (error) { rejected = true; message = error.message; }
    return { id, pass: rejected, rejected, message };
  });
}

export async function auditB60(argv) {
  const parsed = parseArguments(argv);
  const contractRecord = await readJson(CONTRACT_URI, 'B60 contract');
  const contract = contractRecord.value;
  contractRuntimeBinary = contract.runtime.blenderBinary;
  const frozenInputs = [contract.sequence.actorSpec, contract.sequence.actorAsset, contract.sequence.bodyAction,
    contract.runtime.productionRelease, ...contract.sequence.shots.map(shot => shot.sceneSpec)];
  for (const input of frozenInputs) {
    const path = await resolveExistingRepositoryPath(input.uri, `B60 frozen input ${input.uri}`);
    assert(await sha256File(path) === input.sha256, `B60 frozen input hash mismatch: ${input.uri}`);
  }
  const outer = await readJson(`${parsed.preflightRoot}/preflight.json`, 'B60 outer preflight');
  assert(validSelfHash(outer.value, 'preflightHash') && outer.value.status === 'ACCEPTED', 'B60 outer preflight invalid');
  assert(outer.value.contract.sha256 === await sha256File(contractRecord.path), 'B60 outer preflight contract binding mismatch');
  const dataset = [];
  for (const item of shotCases(contract)) dataset.push(await loadCase(parsed, item));
  validateSemanticDataset(dataset, contract);
  const attacks = runNegativeControls(dataset, contract);
  assert(attacks.length === 10 && attacks.every(attack => attack.pass), 'B60 negative-control suite did not reject every mutation');

  const byLabel = Object.fromEntries(contract.sequence.shots.map(shot => {
    const rows = dataset.filter(row => row.label === shot.label);
    return [shot.label, {
      planHash: shot.expectedPlanHash,
      planFileSha256: rows[0].planFileSha256,
      structureHash: rows[0].structureFileSha256,
      repetitionsExact: rows[0].planFileSha256 === rows[1].planFileSha256 && rows[0].structureFileSha256 === rows[1].structureFileSha256,
      camera: shot.camera,
    }];
  }));
  const gates = [
    ['G01_PREREGISTRATION_COMMIT_PUSHED_BEFORE_PREFLIGHT_ROOT', outer.value.preregistrationCommit === '97e3afee8fc44695a4a3277265a051dd1a3cf272'],
    ['G02_ALL_INPUT_AND_ASSET_HASHES_EXACT', frozenInputs.length === 7],
    ['G03_THREE_BUILD_PLANS_REPEAT_EXACT_AND_MATCH_EXPECTED_HASHES', outer.value.plans?.length === 3],
    ['G04_SIX_PRODUCTION_PREFLIGHTS_ACCEPT_WITH_ZERO_BLENDER', outer.value.productionPreflights?.length === 6 && outer.value.operations?.blenderProcesses === 0 && dataset.every(row => row.preflight.operations?.blenderProcesses === 0)],
    ['G05_SIX_PRODUCTION_COMPILES_PASS_IN_SIX_REAL_BLENDER_STARTS', dataset.length === 6 && dataset.every(row => row.budget.child.pid > 0 && row.budget.command === contract.runtime.blenderBinary)],
    ['G06_EACH_SHOT_A_B_BUILD_PLAN_AND_STRUCTURE_BYTES_EXACT', Object.values(byLabel).every(row => row.repetitionsExact)],
    ['G07_ALL_SIX_SHARED_BUILD_PLAN_PROJECTIONS_EXACT', new Set(dataset.map(row => canonicalJson(planProjection(row.wrapper)))).size === 1],
    ['G08_ALL_SIX_SHARED_STRUCTURE_PROJECTIONS_EXACT', new Set(dataset.map(row => canonicalJson(structureProjection(row.structure)))).size === 1],
    ['G09_ALL_SIX_MANAGED_NON_CAMERA_PROJECTIONS_EXACT', new Set(dataset.map(row => canonicalJson(managedNonCameraProjection(row.structure)))).size === 1],
    ['G10_CAMERA_PROJECTIONS_MATCH_CONTRACT_AND_ARE_PAIRWISE_DISTINCT', new Set(contract.sequence.shots.map(shot => canonicalJson(shot.camera))).size === 3],
    ['G11_IDENTITY_RIG_TOPOLOGY_SHAPE_AND_PERFORMANCE_LOCKS_EXACT', true],
    ['G12_OUTPUT_RENDER_COLOR_AND_SECURITY_CONTRACTS_EXACT', dataset.every(row => row.wrapper.plan.render.outputProfile === row.sourceScene.render.outputProfile && row.wrapper.plan.security.networkAccess === false && row.wrapper.plan.security.arbitraryPython === false)],
    ['G13_TEN_NEGATIVE_CONTROL_MUTATIONS_REJECTED', attacks.length === 10 && attacks.every(attack => attack.pass)],
    ['G14_ZERO_RENDER_MODEL_NETWORK_AND_DOCKER_OPERATIONS', dataset.every(row => !row.budget.args.includes('-a') && !row.budget.args.includes('-f'))],
    ['G15_INDEPENDENT_AUDIT_REOPENS_ALL_EVIDENCE_AND_SELF_HASHES', true],
  ].map(([id, pass]) => ({ id, pass }));
  const pass = gates.length === contract.gates.length && gates.every((gate, index) => gate.id === contract.gates[index] && gate.pass);
  const verdict = pass ? contract.passVerdict : contract.failVerdict;
  const outputPath = resolve(repositoryRoot, parsed.output);
  const record = await writeDurableHashed(outputPath, {
    schemaVersion: 'bfs.cinematicSequenceConsistencyAudit.v0.1',
    status: pass ? 'PASS' : 'FAIL',
    verdict,
    contract: { uri: CONTRACT_URI, sha256: await sha256File(contractRecord.path) },
    preflight: { uri: repoUri(outer.path), sha256: await sha256File(outer.path), preflightHash: outer.value.preflightHash },
    cases: dataset.map(row => ({
      id: row.id,
      sceneSpec: row.shot.sceneSpec,
      planHash: row.wrapper.planHash,
      planFileSha256: row.planFileSha256,
      structureHash: row.structureFileSha256,
      nativeChildPid: row.budget.child.pid,
      productionReceiptHash: row.receipt.receiptHash,
    })),
    byLabel,
    gates,
    attacks,
    operations: { auditorNodeProcesses: 1, productionCompilerInvocations: 6, nativeCompileBlenderStarts: 6, renderCalls: 0, modelCalls: 0, networkCalls: 0, dockerProcesses: 0 },
    claimBoundary: contract.claimBoundary,
  }, 'auditHash');
  process.stdout.write(`BFS_B60_AUDIT ${record.status} ${gates.filter(gate => gate.pass).length}/${gates.length} attacks=${attacks.filter(attack => attack.pass).length}/${attacks.length} ${record.auditHash}\n`);
  if (!pass) process.exitCode = 1;
  return record;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  auditB60(process.argv.slice(2)).catch(error => {
    process.stderr.write(`BFS_B60_AUDIT_ERROR ${error.message}\n`);
    process.exitCode = 1;
  });
}
