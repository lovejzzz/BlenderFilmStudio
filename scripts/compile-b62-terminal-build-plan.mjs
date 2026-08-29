#!/usr/bin/env node

import { createHash } from 'node:crypto';
import { open, readFile, realpath } from 'node:fs/promises';
import { dirname, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const repositoryRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const EXPERIMENT_URI = 'specs/b62-terminal-scene-package-compiler.v0.1.json';
const EXPECTED_SPEC_URI = 'specs/b62-terminal-proof.scene-package.v0.1.json';
const EXPECTED_SPEC_SHA256 = '3b82d7c84074442bbfa37793e0632c1dad194ea12fcdac7ecd4cfd6954387a7e';

function req(condition, message) {
  if (!condition) throw new Error(message);
}

function normalize(value) {
  if (typeof value === 'number' && Number.isFinite(value) && Number.isInteger(value)) return value;
  if (typeof value === 'number' && Number.isFinite(value)) {
    const bytes = Buffer.alloc(8);
    bytes.writeDoubleBE(value);
    return { $f64be: bytes.toString('hex') };
  }
  if (Array.isArray(value)) return value.map(normalize);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).sort(([left], [right]) => left.localeCompare(right)).map(([key, child]) => [key, normalize(child)]));
  }
  return value;
}

function normalizeLegacy(value) {
  if (typeof value === 'number' && Number.isFinite(value) && Number.isInteger(value)) return value;
  if (Array.isArray(value)) return value.map(normalizeLegacy);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).sort(([left], [right]) => left.localeCompare(right)).map(([key, child]) => [key, normalizeLegacy(child)]));
  }
  return value;
}

const canonicalJson = value => JSON.stringify(normalize(value));
const hashBytes = value => createHash('sha256').update(value).digest('hex');
const hashFile = async path => hashBytes(await readFile(path));

function validSelf(document, field, mode = 'f64') {
  if (!document || !/^[0-9a-f]{64}$/.test(document[field] ?? '')) return false;
  const copy = structuredClone(document);
  const expected = copy[field];
  delete copy[field];
  const encoded = mode === 'legacy' ? JSON.stringify(normalizeLegacy(copy)) : canonicalJson(copy);
  return hashBytes(encoded) === expected;
}

function repositoryPath(uri) {
  req(typeof uri === 'string' && uri.length > 0 && !uri.startsWith('/') && !uri.split('/').includes('..') && !uri.includes('\\'), `unsafe repository path ${uri}`);
  const path = resolve(repositoryRoot, uri);
  req(!relative(repositoryRoot, path).startsWith('../'), `escaped repository path ${uri}`);
  return path;
}

async function existingRepositoryPath(uri) {
  const path = repositoryPath(uri);
  const resolved = await realpath(path);
  req(resolved === path && !relative(repositoryRoot, resolved).startsWith('../'), `symlink or realpath escape ${uri}`);
  return path;
}

function parseArguments() {
  const args = process.argv.slice(2);
  const parsed = {};
  for (let index = 0; index < args.length; index += 2) {
    req(args[index]?.startsWith('--') && args[index + 1], 'arguments must be --key value pairs');
    parsed[args[index].slice(2)] = args[index + 1];
  }
  req(parsed.spec === EXPECTED_SPEC_URI, `--spec must be ${EXPECTED_SPEC_URI}`);
  req(/^[0-9a-f]{40}$/.test(parsed['tool-freeze-commit'] ?? ''), '--tool-freeze-commit must be a full SHA-1');
  req(Boolean(parsed.output) !== Boolean(parsed.verify), 'exactly one of --output or --verify is required');
  return parsed;
}

async function readBound(document, binding, selfField, semantic, mode = 'f64') {
  const path = await existingRepositoryPath(binding.uri);
  req(await hashFile(path) === binding.sha256, `file hash mismatch ${binding.uri}`);
  const value = JSON.parse(await readFile(path, 'utf8'));
  req(validSelf(value, selfField, mode), `self hash invalid ${binding.uri}`);
  req(value[selfField] === binding[selfField], `self hash binding mismatch ${binding.uri}`);
  semantic(value);
  return value;
}

function exactArray(actual, expected, message) {
  req(canonicalJson(actual) === canonicalJson(expected), message);
}

async function compilePlan(args) {
  const experiment = JSON.parse(await readFile(await existingRepositoryPath(EXPERIMENT_URI), 'utf8'));
  req(experiment.schemaVersion === 'bfs.b62TerminalScenePackageCompilerExperiment.v0.1' && experiment.experimentId === 'B62-T1-E1' && experiment.statusBeforeToolCreation === 'PREREGISTERED', 'experiment contract mismatch');
  req(experiment.inputSceneSpec.uri === EXPECTED_SPEC_URI && experiment.inputSceneSpec.sha256 === EXPECTED_SPEC_SHA256, 'experiment input binding mismatch');
  const specPath = await existingRepositoryPath(args.spec);
  req(await hashFile(specPath) === EXPECTED_SPEC_SHA256, 'ScenePackageSpec hash mismatch');
  const sceneSpec = JSON.parse(await readFile(specPath, 'utf8'));
  req(sceneSpec.schemaVersion === 'bfs.b62TerminalScenePackageSpec.v0.1' && sceneSpec.packageId === 'B62-TERMINAL-PROOF' && sceneSpec.scope === 'NARROW_PRECOMPILED_SCENE_PACKAGE_DIALECT', 'ScenePackageSpec identity mismatch');
  req(sceneSpec.sourceMaster.uri === experiment.parentEvidence.phase0.master.uri && sceneSpec.sourceMaster.sha256 === experiment.parentEvidence.phase0.master.sha256, 'source master binding mismatch');
  const sourceMasterPath = await existingRepositoryPath(sceneSpec.sourceMaster.uri);
  req(await hashFile(sourceMasterPath) === sceneSpec.sourceMaster.sha256, 'source master drift');

  const phase0Generation = await readBound(sceneSpec, experiment.parentEvidence.phase0.generation, 'reportHash', value => {
    req(value.status === 'PASS' && value.experimentId === 'B62-P0-E1', 'Phase 0 generation invalid');
  }, 'legacy');
  await readBound(sceneSpec, experiment.parentEvidence.phase0.audit, 'auditHash', value => {
    req(value.status === 'PASS' && value.verdict === experiment.parentEvidence.phase0.audit.verdict, 'Phase 0 audit invalid');
  }, 'legacy');
  await readBound(sceneSpec, experiment.parentEvidence.phase0.receipt, 'receiptHash', value => {
    req(value.status === 'PASS' && value.verdict === experiment.parentEvidence.phase0.audit.verdict, 'Phase 0 receipt invalid');
  }, 'legacy');
  const d6Build = await readBound(sceneSpec, experiment.parentEvidence.d6.build, 'reportHash', value => {
    req(value.status === 'PASS' && value.experimentId === 'B62-Q1-D6', 'D6 build invalid');
  });
  await readBound(sceneSpec, experiment.parentEvidence.d6.audit, 'auditHash', value => {
    req(value.status === 'PASS' && value.scientificVerdict === experiment.parentEvidence.d6.audit.scientificVerdict, 'D6 audit invalid');
  });
  await readBound(sceneSpec, experiment.parentEvidence.d6.receipt, 'receiptHash', value => {
    req(value.status === 'PASS' && value.scientificVerdict === experiment.parentEvidence.d6.audit.scientificVerdict, 'D6 receipt invalid');
  });
  await readBound(sceneSpec, experiment.parentEvidence.d6.humanReview, 'reviewHash', value => {
    req(value.status === 'PASS' && value.scope === experiment.parentEvidence.d6.humanReview.scope, 'D6 human review invalid');
  });

  req(phase0Generation.reportHash === sceneSpec.preservation.phase0GenerationReport.reportHash, 'generation self binding mismatch');
  exactArray(phase0Generation.timeline, {
    fps: 24,
    frameEnd: 288,
    frameStart: 1,
    markers: [
      { camera: 'CAM_WIDE_APPROACH', frame: 1, name: 'SHOT_WIDE_APPROACH' },
      { camera: 'CAM_MEDIUM_CONTACT', frame: 97, name: 'SHOT_MEDIUM_CONTACT' },
      { camera: 'CAM_CLOSE_REFLECTION', frame: 193, name: 'SHOT_CLOSE_REFLECTION' },
    ],
  }, 'Phase 0 timeline drift');
  exactArray(sceneSpec.timeline.cuts, experiment.buildPlanContract.timeline.cuts, 'ScenePackageSpec cut contract mismatch');
  req(d6Build.source?.sha256 === sceneSpec.sourceMaster.sha256 && d6Build.cameras?.source === sceneSpec.cameraIntervention.sourceCamera && d6Build.cameras?.motion === 'CAM_CLOSE_MOTION_D6' && d6Build.cameras?.lensMillimeters === 65, 'D6 camera binding mismatch');
  req(Array.isArray(d6Build.bake) && d6Build.bake.length === 96, 'D6 bake count mismatch');
  const samples = d6Build.bake.map((row, index) => {
    const expectedFrame = 193 + index;
    req(row.frame === expectedFrame, `D6 frame roster mismatch ${expectedFrame}`);
    req(Array.isArray(row.motionLocation) && row.motionLocation.length === 3 && row.motionLocation.every(Number.isFinite), `invalid motionLocation ${expectedFrame}`);
    req(Array.isArray(row.motionQuaternion) && row.motionQuaternion.length === 4 && row.motionQuaternion.every(Number.isFinite), `invalid motionQuaternion ${expectedFrame}`);
    const norm = Math.hypot(...row.motionQuaternion);
    req(Math.abs(norm - 1) <= 1e-5, `non-unit motionQuaternion ${expectedFrame}`);
    return { frame: row.frame, location: row.motionLocation, quaternion: row.motionQuaternion };
  });
  req(sceneSpec.cameraIntervention.expectedSampleCount === samples.length && sceneSpec.cameraIntervention.lensMillimeters === 65 && sceneSpec.cameraIntervention.interpolation === 'LINEAR', 'camera intervention contract mismatch');

  const planBody = {
    schemaVersion: 'bfs.b62TerminalScenePackageBuildPlan.v0.1',
    experimentId: 'B62-T1-E1',
    packageId: sceneSpec.packageId,
    status: 'COMPILED',
    toolFreezeCommit: args['tool-freeze-commit'],
    inputSceneSpec: { uri: args.spec, sha256: EXPECTED_SPEC_SHA256 },
    sourceMaster: structuredClone(sceneSpec.sourceMaster),
    evidence: {
      phase0: structuredClone(experiment.parentEvidence.phase0),
      d6: structuredClone(experiment.parentEvidence.d6),
    },
    timeline: structuredClone(sceneSpec.timeline),
    camera: {
      sourceCamera: sceneSpec.cameraIntervention.sourceCamera,
      objectName: sceneSpec.cameraIntervention.outputCamera,
      dataName: sceneSpec.authorizedMutation.addCameraData[0],
      actionName: sceneSpec.cameraIntervention.outputAction,
      lensMillimeters: sceneSpec.cameraIntervention.lensMillimeters,
      clipStart: sceneSpec.cameraIntervention.clipStart,
      clipEnd: sceneSpec.cameraIntervention.clipEnd,
      rotationMode: sceneSpec.cameraIntervention.rotationMode,
      interpolation: sceneSpec.cameraIntervention.interpolation,
      framesInclusive: sceneSpec.cameraIntervention.framesInclusive,
      curves: 7,
      keysPerCurve: 96,
      samples,
    },
    preservation: structuredClone(sceneSpec.preservation),
    authorizedMutation: structuredClone(sceneSpec.authorizedMutation),
    forbiddenMutation: structuredClone(sceneSpec.forbiddenMutation),
    operations: { buildPlanCompilerProcesses: 2, blenderStarts: 0, renderCalls: 0, modelCalls: 0, networkCalls: 0, dockerProcesses: 0 },
  };
  return { ...planBody, planHash: hashBytes(canonicalJson(planBody)) };
}

async function main() {
  const args = parseArguments();
  const plan = await compilePlan(args);
  const serialized = `${JSON.stringify(plan, null, 2)}\n`;
  if (args.output) {
    const output = repositoryPath(args.output);
    const handle = await open(output, 'wx', 0o600);
    try {
      await handle.writeFile(serialized);
      await handle.sync();
    } finally {
      await handle.close();
    }
    process.stdout.write(`BFS_B62_T1_BUILDPLAN_WRITE PASS ${plan.camera.samples.length} ${plan.planHash}\n`);
    return;
  }
  const verificationPath = await existingRepositoryPath(args.verify);
  const observed = await readFile(verificationPath, 'utf8');
  req(observed === serialized, 'independent BuildPlan bytes differ');
  process.stdout.write(`BFS_B62_T1_BUILDPLAN_VERIFY PASS ${plan.camera.samples.length} ${plan.planHash}\n`);
}

main().catch(error => {
  process.stderr.write(`${error.stack ?? error.message}\n`);
  process.exitCode = 1;
});
