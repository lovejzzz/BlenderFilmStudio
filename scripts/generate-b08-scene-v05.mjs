import { createHash } from 'node:crypto';
import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';

const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const fileHash = async uri => digest(await readFile(resolve(repositoryRoot, uri)));
const assetUri = 'library/props/B08-prop.blend';
const assetReportUri = 'experiments/trajectory-v0-2/asset-generation.json';
const trajectoryUri = 'specs/benchmarks/B07.trajectory.json';
const b07ResultUri = 'experiments/trajectory-v0-1/results.json';
const [assetHash, assetReportHash, trajectoryHash, b07ResultHash] = await Promise.all([
  fileHash(assetUri), fileHash(assetReportUri), fileHash(trajectoryUri), fileHash(b07ResultUri),
]);

const scene = {
  specVersion: '0.5.0',
  shot: { id: 'SHOT_108', title: 'B08 Immutable Compiled Trajectory', frameStart: 1, frameEnd: 132, frameRate: { numerator: 24, denominator: 1 }, unitScaleMeters: 1, seed: 24082608, activeCamera: 'CAM_B08' },
  assets: [{ id: 'PROP_B08', kind: 'PROP', uri: assetUri, version: '0.1.0', sha256: assetHash, license: 'PROJECT-OWNED', transform: { locationM: [0, 0, 0], rotationEulerDeg: [0, 0, 0], scale: [1, 1, 1] }, visible: true }],
  actors: [], targets: [], attachments: [], geometryEvaluations: [], grasps: [],
  trajectories: [{ id: 'TRAJECTORY_B07_CANONICAL', trajectorySpecUri: trajectoryUri, trajectorySpecSha256: trajectoryHash, assetRef: 'PROP_B08', objectRef: 'B06_PROP', applicationMode: 'BAKED_WORLD_TRANSFORM', disablePhysics: true }],
  cameras: [{ id: 'CAM_B08', lensMm: 50, sensorWidthMm: 36, apertureFStop: 8, focusDistanceM: 3, shutterAngleDeg: 180, transform: { locationM: [1.8, -4.5, 1.2], rotationEulerDeg: [76, 0, 22], scale: [1, 1, 1] } }],
  lights: [
    { id: 'KEY_B08', type: 'AREA', colorLinear: [1, 0.74, 0.55], energy: 700, sizeM: 1.1, transform: { locationM: [1.2, -1.5, 2], rotationEulerDeg: [25, 0, 35], scale: [1, 1, 1] } },
    { id: 'FILL_B08', type: 'AREA', colorLinear: [0.38, 0.58, 1], energy: 420, sizeM: 1.2, transform: { locationM: [-1.2, -1, 1], rotationEulerDeg: [50, 0, -55], scale: [1, 1, 1] } },
  ],
  world: { backgroundLinear: [0.004, 0.008, 0.018], strength: 0.12 }, events: [],
  render: { outputProfile: 'BFS_RESEARCH_MASTER_0_1', previewEngine: 'BLENDER_EEVEE', finalEngine: 'CYCLES', resolution: { width: 3840, height: 2160, percentage: 100 }, samplesPreview: 32, samplesFinal: 128, denoise: true, fileFormat: 'OPEN_EXR_MULTILAYER', pixelType: 'HALF_16', compression: 'ZIP_LOSSLESS', passes: ['Combined', 'Alpha', 'Depth', 'Normal', 'Vector', 'Cryptomatte'], outputRoot: 'renders/SHOT_108/' },
  security: { networkAccess: false, arbitraryPython: false, allowedAssetRoots: ['assets/', 'library/', 'motion/'], allowedOperations: ['READ_MANIFEST', 'IMPORT_ASSET', 'CREATE_CAMERA', 'CREATE_LIGHT', 'CREATE_TRAJECTORY_REPLAY', 'SET_TRANSFORM', 'SET_RENDER', 'RENDER_PREVIEW', 'RENDER_FINAL'] },
  provenance: { briefId: 'BRIEF_B08_COMPILED_TRAJECTORY', createdBy: 'BFS SceneSpec v0.5 compiler experiment', createdAtUtc: '2026-08-26T23:00:00Z', sources: [
    { uri: trajectoryUri, role: 'REFERENCE', license: 'PROJECT-INTERNAL', sha256: trajectoryHash },
    { uri: b07ResultUri, role: 'REFERENCE', license: 'PROJECT-INTERNAL', sha256: b07ResultHash },
    { uri: assetReportUri, role: 'ASSET', license: 'PROJECT-INTERNAL', sha256: assetReportHash },
  ] },
};
const output = resolve(repositoryRoot, 'specs/benchmarks/B08.scene.json');
await writeFile(output, `${JSON.stringify(scene, null, 2)}\n`);
process.stdout.write(`B08_SCENE_WRITTEN ${output}\n`);
