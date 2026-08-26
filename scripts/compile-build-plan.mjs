import { readFile, writeFile } from 'node:fs/promises';
import { relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { canonicalJson, canonicalize, readJson, repositoryRoot, sha256, validateSceneSpec } from './lib/scene-spec.mjs';
import { validateSceneSpecV02 } from './lib/scene-spec-v02.mjs';
import { validateSceneSpecV03 } from './lib/scene-spec-v03.mjs';
import { validateSceneSpecV04 } from './lib/scene-spec-v04.mjs';
import { validateSceneSpecV05 } from './lib/scene-spec-v05.mjs';
import { validateActorSpec } from './lib/actor-spec.mjs';
import { validateGraspSpec } from './lib/grasp-spec.mjs';
import { validateTrajectorySpec } from './lib/trajectory-spec.mjs';

const COMPILER_VERSIONS = { '0.1.0': '0.1.0', '0.2.0': '0.2.0', '0.3.0': '0.3.0', '0.4.0': '0.4.1', '0.5.0': '0.5.0' };
const TARGET_BLENDER = '5.2.0';
const outputSpecPath = resolve(repositoryRoot, 'specs/output-spec.v0.1.json');

function repoRelative(absolutePath) {
  return relative(repositoryRoot, absolutePath).split(sep).join('/');
}

function assertBelowRepository(absolutePath, label) {
  const pathFromRoot = relative(repositoryRoot, absolutePath);
  if (pathFromRoot === '' || pathFromRoot.startsWith(`..${sep}`) || pathFromRoot === '..') {
    throw new Error(`${label} must resolve below the repository root`);
  }
}

async function digestFile(absolutePath) {
  return sha256(await readFile(absolutePath));
}

function requireOperations(document) {
  const requested = new Set(document.security.allowedOperations);
  const required = new Set(['SET_RENDER']);
  if (document.assets.length > 0) required.add('IMPORT_ASSET');
  if (document.cameras.length > 0) required.add('CREATE_CAMERA');
  if (document.lights.length > 0) required.add('CREATE_LIGHT');
  if ((document.targets ?? []).length > 0) required.add('CREATE_TARGET');
  if (document.actors.length > 0 && ['0.2.0', '0.3.0', '0.4.0', '0.5.0'].includes(document.specVersion)) {
    required.add('IMPORT_ACTOR_SPEC');
    required.add('IMPORT_ACTION');
    required.add('APPLY_PERFORMANCE');
  }
  if ((document.attachments ?? []).length > 0) required.add('CREATE_CONSTRAINT');
  if ((document.geometryEvaluations ?? []).length > 0) required.add('EVALUATE_GEOMETRY');
  if ((document.grasps ?? []).length > 0) required.add('CREATE_GRASP');
  if ((document.trajectories ?? []).length > 0) required.add('CREATE_TRAJECTORY_REPLAY');
  if (document.assets.length + document.cameras.length + document.lights.length > 0) required.add('SET_TRANSFORM');
  const missing = [...required].filter(operation => !requested.has(operation));
  if (missing.length > 0) throw new Error(`SceneSpec does not authorize required operations: ${missing.join(', ')}`);
  return [...required].sort();
}

function sortById(items) {
  return structuredClone(items).sort((left, right) => left.id.localeCompare(right.id));
}

async function resolveAssets(document) {
  const assets = [];
  for (const asset of sortById(document.assets)) {
    const absolutePath = resolve(repositoryRoot, asset.uri);
    assertBelowRepository(absolutePath, `Asset ${asset.id}`);
    const actualSha256 = await digestFile(absolutePath).catch(() => {
      throw new Error(`Asset ${asset.id} is missing: ${asset.uri}`);
    });
    if (actualSha256 !== asset.sha256) {
      throw new Error(`Asset ${asset.id} hash mismatch: expected ${asset.sha256}, received ${actualSha256}`);
    }
    assets.push({ ...asset, uri: repoRelative(absolutePath), verifiedSha256: actualSha256 });
  }
  return assets;
}

async function resolveActors(document, assets) {
  if (!['0.2.0', '0.3.0', '0.4.0', '0.5.0'].includes(document.specVersion)) return sortById(document.actors);
  const assetMap = new Map(assets.map(asset => [asset.id, asset]));
  const targetSockets = new Map((document.targets ?? []).map(target => [target.id, new Set(target.sockets.map(socket => socket.id))]));
  const actors = [];
  for (const actor of sortById(document.actors)) {
    const actorSpecPath = resolve(repositoryRoot, actor.actorSpecUri);
    assertBelowRepository(actorSpecPath, `ActorSpec ${actor.id}`);
    const actorSpecBytes = await readFile(actorSpecPath).catch(() => {
      throw new Error(`ActorSpec ${actor.id} is missing: ${actor.actorSpecUri}`);
    });
    const actualActorSpecSha256 = sha256(actorSpecBytes);
    if (actualActorSpecSha256 !== actor.actorSpecSha256) {
      throw new Error(`ActorSpec ${actor.id} hash mismatch: expected ${actor.actorSpecSha256}, received ${actualActorSpecSha256}`);
    }
    const actorSpec = JSON.parse(actorSpecBytes.toString('utf8'));
    const validation = validateActorSpec(actorSpec);
    if (!validation.valid) {
      const details = validation.errors.map(error => `${error.code} ${error.path}: ${error.message}`).join('\n');
      throw new Error(`ActorSpec ${actor.id} validation failed:\n${details}`);
    }
    const actorSpecCanonicalSha256 = sha256(canonicalJson(actorSpec));
    if (actorSpec.actor.id !== actor.id || actorSpec.actor.assetRef !== actor.assetRef || actorSpec.actor.rigProfile !== actor.rigProfile || actorSpec.actor.identityLock !== actor.identityLock) {
      throw new Error(`ActorSpec ${actor.id} identity fields do not match SceneSpec`);
    }
    const asset = assetMap.get(actor.assetRef);
    if (!asset || asset.kind !== 'CHARACTER' || asset.uri !== actorSpec.actor.assetUri || asset.sha256 !== actorSpec.actor.assetSha256) {
      throw new Error(`ActorSpec ${actor.id} asset does not match the verified SceneSpec CHARACTER asset`);
    }
    if (actorSpec.performance.frameStart !== document.shot.frameStart || actorSpec.performance.frameEnd !== document.shot.frameEnd
      || actorSpec.performance.frameRate.numerator !== document.shot.frameRate.numerator || actorSpec.performance.frameRate.denominator !== document.shot.frameRate.denominator) {
      throw new Error(`ActorSpec ${actor.id} performance range or frame rate does not match the shot`);
    }
    for (const gaze of actorSpec.performance.gazeKeys) {
      if (!targetSockets.get(gaze.targetRef)?.has(gaze.targetSocket)) throw new Error(`Actor ${actor.id} gaze target ${gaze.targetRef}.${gaze.targetSocket} is missing from SceneSpec targets`);
    }
    for (const contact of actorSpec.performance.contacts) {
      if (!targetSockets.get(contact.targetRef)?.has(contact.targetSocket)) throw new Error(`Actor ${actor.id} contact target ${contact.targetRef}.${contact.targetSocket} is missing from SceneSpec targets`);
    }
    const resolvedActions = [];
    for (const action of actorSpec.performance.bodyActions) {
      const actionPath = resolve(repositoryRoot, action.uri);
      assertBelowRepository(actionPath, `Actor action ${action.id}`);
      const actualSha256 = await digestFile(actionPath).catch(() => {
        throw new Error(`Actor action ${action.id} is missing: ${action.uri}`);
      });
      if (actualSha256 !== action.sha256) throw new Error(`Actor action ${action.id} hash mismatch: expected ${action.sha256}, received ${actualSha256}`);
      resolvedActions.push({ ...action, uri: repoRelative(actionPath), verifiedSha256: actualSha256 });
    }
    actorSpec.performance.bodyActions = resolvedActions;
    actors.push({
      ...actor,
      actorSpecUri: repoRelative(actorSpecPath),
      verifiedActorSpecSha256: actualActorSpecSha256,
      actorSpecCanonicalSha256,
      actorSpec: canonicalize(actorSpec),
    });
  }
  return actors;
}

async function resolveGrasps(document, assets) {
  if (!['0.4.0', '0.5.0'].includes(document.specVersion)) return [];
  const assetMap = new Map(assets.map(asset => [asset.id, asset]));
  const grasps = [];
  for (const binding of sortById(document.grasps)) {
    const graspPath = resolve(repositoryRoot, binding.graspSpecUri);
    assertBelowRepository(graspPath, `GraspSpec ${binding.id}`);
    const bytes = await readFile(graspPath).catch(() => { throw new Error(`GraspSpec ${binding.id} is missing: ${binding.graspSpecUri}`); });
    const actualSha256 = sha256(bytes);
    if (actualSha256 !== binding.graspSpecSha256) throw new Error(`GraspSpec ${binding.id} hash mismatch: expected ${binding.graspSpecSha256}, received ${actualSha256}`);
    const graspSpec = JSON.parse(bytes.toString('utf8'));
    const validation = validateGraspSpec(graspSpec);
    if (!validation.valid) {
      const details = validation.errors.map(error => `${error.code} ${error.path}: ${error.message}`).join('\n');
      throw new Error(`GraspSpec ${binding.id} validation failed:\n${details}`);
    }
    if (graspSpec.id !== binding.id || graspSpec.actorRef !== binding.actorRef || graspSpec.propRef !== binding.propAssetRef) throw new Error(`GraspSpec ${binding.id} identity references do not match SceneSpec binding`);
    if (!assetMap.has(binding.actorAssetRef) || !assetMap.has(binding.propAssetRef)) throw new Error(`GraspSpec ${binding.id} references unresolved assets`);
    if (graspSpec.phases.approach.start !== document.shot.frameStart || graspSpec.phases.release.end > document.shot.frameEnd) throw new Error(`GraspSpec ${binding.id} phase range does not fit the shot`);
    if (binding.transportKeys[0].frame !== graspSpec.phases.hold.start || binding.transportKeys.at(-1).frame !== graspSpec.phases.hold.end) throw new Error(`Grasp ${binding.id} transport keys must span the exact HOLD window`);
    grasps.push({
      ...binding,
      graspSpecUri: repoRelative(graspPath),
      verifiedGraspSpecSha256: actualSha256,
      graspSpecCanonicalSha256: sha256(canonicalJson(graspSpec)),
      graspSpec: canonicalize(graspSpec),
    });
  }
  return grasps;
}

async function resolveTrajectories(document, assets) {
  if (document.specVersion !== '0.5.0') return [];
  const assetMap = new Map(assets.map(asset => [asset.id, asset]));
  const trajectories = [];
  for (const binding of sortById(document.trajectories)) {
    const trajectoryPath = resolve(repositoryRoot, binding.trajectorySpecUri);
    assertBelowRepository(trajectoryPath, `TrajectorySpec ${binding.id}`);
    const bytes = await readFile(trajectoryPath).catch(() => { throw new Error(`TrajectorySpec ${binding.id} is missing: ${binding.trajectorySpecUri}`); });
    const actualSha256 = sha256(bytes);
    if (actualSha256 !== binding.trajectorySpecSha256) throw new Error(`TrajectorySpec ${binding.id} hash mismatch: expected ${binding.trajectorySpecSha256}, received ${actualSha256}`);
    const trajectorySpec = JSON.parse(bytes.toString('utf8'));
    const validation = validateTrajectorySpec(trajectorySpec);
    if (!validation.valid) {
      const details = validation.errors.map(error => `${error.code} ${error.path}: ${error.message}`).join('\n');
      throw new Error(`TrajectorySpec ${binding.id} validation failed:\n${details}`);
    }
    if (trajectorySpec.id !== binding.id || trajectorySpec.targetObject !== binding.objectRef) throw new Error(`TrajectorySpec ${binding.id} identity or target does not match SceneSpec binding`);
    const asset = assetMap.get(binding.assetRef);
    if (!asset || asset.kind !== 'PROP') throw new Error(`TrajectorySpec ${binding.id} does not reference a verified PROP asset`);
    if (trajectorySpec.frameStart !== document.shot.frameStart || trajectorySpec.frameEnd !== document.shot.frameEnd
      || trajectorySpec.frameRate.numerator !== document.shot.frameRate.numerator || trajectorySpec.frameRate.denominator !== document.shot.frameRate.denominator) {
      throw new Error(`TrajectorySpec ${binding.id} range or frame rate does not match the shot`);
    }
    const evaluationPath = resolve(repositoryRoot, trajectorySpec.source.evaluationUri);
    assertBelowRepository(evaluationPath, `TrajectorySpec source ${binding.id}`);
    const evaluationBytes = await readFile(evaluationPath).catch(() => { throw new Error(`TrajectorySpec source evaluation is missing: ${trajectorySpec.source.evaluationUri}`); });
    const evaluationSha256 = sha256(evaluationBytes);
    if (evaluationSha256 !== trajectorySpec.source.evaluationSha256) throw new Error(`TrajectorySpec ${binding.id} source evaluation hash mismatch: expected ${trajectorySpec.source.evaluationSha256}, received ${evaluationSha256}`);
    const sourceEvaluation = JSON.parse(evaluationBytes.toString('utf8'));
    if (sourceEvaluation.passed !== true || !Array.isArray(sourceEvaluation.trajectory) || sourceEvaluation.trajectory.length !== trajectorySpec.samples.length) {
      throw new Error(`TrajectorySpec ${binding.id} source evaluation is not an individually passing solve with a complete trajectory`);
    }
    for (let index = 0; index < trajectorySpec.samples.length; index += 1) {
      const sample = trajectorySpec.samples[index];
      const source = sourceEvaluation.trajectory[index];
      if (sample.frame !== source.frame
        || canonicalJson(sample.locationM) !== canonicalJson(source.propCentreWorldM)
        || canonicalJson(sample.rotationQuaternionWxyz) !== canonicalJson(source.propRotationQuaternion)) {
        throw new Error(`TrajectorySpec ${binding.id} sample ${sample.frame} does not match the pinned source evaluation`);
      }
    }
    trajectories.push({
      ...binding,
      trajectorySpecUri: repoRelative(trajectoryPath),
      verifiedTrajectorySpecSha256: actualSha256,
      trajectorySpecCanonicalSha256: sha256(canonicalJson(trajectorySpec)),
      verifiedSourceEvaluationSha256: evaluationSha256,
      trajectorySpec: canonicalize(trajectorySpec),
    });
  }
  return trajectories;
}

async function verifyLocalSources(document) {
  const sources = [];
  for (const source of document.provenance.sources) {
    const normalized = source.uri.replaceAll('\\', '/');
    if (normalized.includes('://')) {
      sources.push({ ...source, verification: 'DECLARED_EXTERNAL' });
      continue;
    }
    const absolutePath = resolve(repositoryRoot, normalized);
    assertBelowRepository(absolutePath, `Provenance source ${source.uri}`);
    const actualSha256 = await digestFile(absolutePath).catch(() => {
      throw new Error(`Local provenance source is missing: ${source.uri}`);
    });
    if (actualSha256 !== source.sha256) {
      throw new Error(`Provenance hash mismatch for ${source.uri}: expected ${source.sha256}, received ${actualSha256}`);
    }
    sources.push({ ...source, uri: repoRelative(absolutePath), verification: 'HASH_VERIFIED' });
  }
  return sources.sort((left, right) => left.uri.localeCompare(right.uri));
}

function normalizeDocument(document) {
  const normalized = structuredClone(document);
  normalized.assets = sortById(normalized.assets);
  normalized.actors = sortById(normalized.actors);
  normalized.cameras = sortById(normalized.cameras).map(camera => ({
    ...camera,
    ...(camera.transformKeys ? { transformKeys: [...camera.transformKeys].sort((left, right) => left.frame - right.frame) } : {}),
  }));
  normalized.lights = sortById(normalized.lights);
  normalized.events = sortById(normalized.events);
  if (normalized.targets) normalized.targets = sortById(normalized.targets).map(target => ({ ...target, sockets: sortById(target.sockets) }));
  if (normalized.attachments) normalized.attachments = sortById(normalized.attachments).map(attachment => ({
    ...attachment,
    influenceKeys: [...attachment.influenceKeys].sort((left, right) => left.frame - right.frame),
  }));
  if (normalized.geometryEvaluations) normalized.geometryEvaluations = sortById(normalized.geometryEvaluations);
  if (normalized.grasps) normalized.grasps = sortById(normalized.grasps).map(grasp => ({ ...grasp, transportKeys: [...grasp.transportKeys].sort((left, right) => left.frame - right.frame) }));
  if (normalized.trajectories) normalized.trajectories = sortById(normalized.trajectories);
  normalized.render.passes = [...normalized.render.passes].sort();
  normalized.security.allowedAssetRoots = [...normalized.security.allowedAssetRoots].sort();
  normalized.security.allowedOperations = [...normalized.security.allowedOperations].sort();
  normalized.provenance.sources = [...normalized.provenance.sources].sort((left, right) => left.uri.localeCompare(right.uri));
  return canonicalize(normalized);
}

export async function compileBuildPlan(inputPath) {
  const absoluteInputPath = resolve(process.cwd(), inputPath);
  assertBelowRepository(absoluteInputPath, 'SceneSpec');
  const document = await readJson(absoluteInputPath);
  const validator = document.specVersion === '0.5.0'
    ? validateSceneSpecV05
    : document.specVersion === '0.4.0' ? validateSceneSpecV04
    : document.specVersion === '0.3.0' ? validateSceneSpecV03
    : document.specVersion === '0.2.0' ? validateSceneSpecV02 : validateSceneSpec;
  const validation = validator(document);
  if (!validation.valid) {
    const details = validation.errors.map(error => `${error.code} ${error.path}: ${error.message}`).join('\n');
    throw new Error(`SceneSpec validation failed before BuildPlan generation:\n${details}`);
  }

  const normalizedDocument = normalizeDocument(document);
  const compilerVersion = COMPILER_VERSIONS[normalizedDocument.specVersion];
  if (!compilerVersion) throw new Error(`Unsupported SceneSpec version: ${normalizedDocument.specVersion}`);
  const outputSpec = await readJson(outputSpecPath);
  if (outputSpec.id !== normalizedDocument.render.outputProfile) {
    throw new Error(`Output profile ${normalizedDocument.render.outputProfile} does not match ${outputSpec.id}`);
  }
  const ocioConfigPath = resolve(repositoryRoot, outputSpec.color.ocioConfigUri);
  assertBelowRepository(ocioConfigPath, 'OCIO config');
  const ocioConfigSha256 = await digestFile(ocioConfigPath).catch(() => {
    throw new Error(`Pinned OCIO config is missing: ${outputSpec.color.ocioConfigUri}`);
  });
  if (ocioConfigSha256 !== outputSpec.color.ocioConfigSha256) {
    throw new Error(`OCIO config hash mismatch: expected ${outputSpec.color.ocioConfigSha256}, received ${ocioConfigSha256}`);
  }
  const verifiedAssets = await resolveAssets(normalizedDocument);
  const verifiedActors = await resolveActors(normalizedDocument, verifiedAssets);
  const verifiedGrasps = await resolveGrasps(normalizedDocument, verifiedAssets);
  const verifiedTrajectories = await resolveTrajectories(normalizedDocument, verifiedAssets);
  const verifiedSources = await verifyLocalSources(normalizedDocument);
  const authorizedOperations = requireOperations(normalizedDocument);
  const outputRoot = resolve(repositoryRoot, normalizedDocument.render.outputRoot);
  assertBelowRepository(outputRoot, 'Render output');

  const plan = canonicalize({
    compiler: {
      name: 'BFS_SCENE_COMPILER',
      version: compilerVersion,
      targetApplication: 'Blender',
      targetVersion: TARGET_BLENDER,
    },
    source: {
      sceneSpecPath: repoRelative(absoluteInputPath),
      sceneSpecVersion: normalizedDocument.specVersion,
      canonicalSha256: sha256(canonicalJson(normalizedDocument)),
    },
    shot: normalizedDocument.shot,
    assets: verifiedAssets,
    actors: verifiedActors,
    ...(normalizedDocument.targets ? { targets: normalizedDocument.targets } : {}),
    ...(normalizedDocument.attachments ? { attachments: normalizedDocument.attachments } : {}),
    ...(normalizedDocument.geometryEvaluations ? { geometryEvaluations: normalizedDocument.geometryEvaluations } : {}),
    ...(normalizedDocument.grasps ? { grasps: verifiedGrasps } : {}),
    ...(normalizedDocument.trajectories ? { trajectories: verifiedTrajectories } : {}),
    cameras: normalizedDocument.cameras,
    lights: normalizedDocument.lights,
    world: normalizedDocument.world,
    events: normalizedDocument.events,
    render: normalizedDocument.render,
    outputSpec: {
      id: outputSpec.id,
      specVersion: outputSpec.specVersion,
      canonicalSha256: sha256(canonicalJson(outputSpec)),
      picture: outputSpec.picture,
      color: { ...outputSpec.color, verifiedOcioConfigSha256: ocioConfigSha256 },
      master: outputSpec.master,
      acceptance: outputSpec.acceptance,
    },
    security: {
      networkAccess: false,
      arbitraryPython: false,
      authorizedOperations,
      compilerInternalOperations: ['RESET_SCENE', 'SET_WORLD', 'SET_ACTIVE_CAMERA', 'WRITE_MANIFEST', 'SAVE_BLEND'],
    },
    provenance: { ...normalizedDocument.provenance, sources: verifiedSources },
    outputs: {
      root: repoRelative(outputRoot),
      blend: `${repoRelative(outputRoot)}scene.blend`,
      manifest: `${repoRelative(outputRoot)}scene.manifest.json`,
    },
  });

  return canonicalize({
    documentType: 'BFS_BUILD_PLAN',
    planVersion: compilerVersion,
    planHash: sha256(canonicalJson(plan)),
    plan,
  });
}

async function main() {
  const args = process.argv.slice(2);
  const inputIndex = args.indexOf('--input');
  const outputIndex = args.indexOf('--output');
  if (inputIndex < 0 || !args[inputIndex + 1]) {
    throw new Error('Usage: node scripts/compile-build-plan.mjs --input <SceneSpec.json> [--output <BuildPlan.json>]');
  }
  const buildPlan = await compileBuildPlan(args[inputIndex + 1]);
  const serialized = `${JSON.stringify(buildPlan, null, 2)}\n`;
  if (outputIndex >= 0 && args[outputIndex + 1]) {
    const outputPath = resolve(process.cwd(), args[outputIndex + 1]);
    await writeFile(outputPath, serialized);
    process.stdout.write(`BUILD_PLAN ${buildPlan.plan.shot.id} ${buildPlan.planHash} ${outputPath}\n`);
  } else {
    process.stdout.write(serialized);
  }
}

const isDirectRun = process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (isDirectRun) main().catch(error => {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
});
