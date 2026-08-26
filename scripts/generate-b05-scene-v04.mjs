import { createHash } from 'node:crypto';
import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';

const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const fileHash = async path => digest(await readFile(resolve(repositoryRoot, path)));

const characterUri = 'assets/characters/B05-gripper.blend';
const propUri = 'library/props/B05-prop.blend';
const graspUri = 'specs/benchmarks/B05.grasp.json';
const assetReportUri = 'experiments/grasp-v0-2/asset-generation.json';

const [characterHash, propHash, graspHash, assetReportHash] = await Promise.all([
  fileHash(characterUri),
  fileHash(propUri),
  fileHash(graspUri),
  fileHash(assetReportUri),
]);

const scene = {
  specVersion: '0.4.0',
  shot: {
    id: 'SHOT_107',
    title: 'B05 Compiled Two-Finger Grasp',
    frameStart: 1,
    frameEnd: 120,
    frameRate: { numerator: 24, denominator: 1 },
    unitScaleMeters: 1,
    seed: 24082605,
    activeCamera: 'CAM_B05',
  },
  assets: [
    {
      id: 'CHAR_B05', kind: 'CHARACTER', uri: characterUri, version: '0.1.0', sha256: characterHash,
      license: 'PROJECT-OWNED',
      transform: { locationM: [0, 0, 0], rotationEulerDeg: [0, 0, 0], scale: [1, 1, 1] }, visible: true,
    },
    {
      id: 'PROP_B05', kind: 'PROP', uri: propUri, version: '0.1.0', sha256: propHash,
      license: 'PROJECT-OWNED',
      transform: { locationM: [0, 0, 0], rotationEulerDeg: [0, 0, 0], scale: [1, 1, 1] }, visible: true,
    },
  ],
  actors: [],
  targets: [],
  attachments: [],
  geometryEvaluations: [],
  grasps: [{
    id: 'GRASP_B05_TWO_FINGER',
    graspSpecUri: graspUri,
    graspSpecSha256: graspHash,
    actorRef: 'ACTOR_B05',
    actorAssetRef: 'CHAR_B05',
    propAssetRef: 'PROP_B05',
    armatureObject: 'RIG_B05',
    propObject: 'PROP_BODY',
    transportKeys: [
      { frame: 49, locationM: [0, 0, 0], interpolation: 'LINEAR' },
      { frame: 108, locationM: [0, 0, 0.3], interpolation: 'LINEAR' },
    ],
  }],
  cameras: [{
    id: 'CAM_B05', lensMm: 70, sensorWidthMm: 36, apertureFStop: 8,
    focusDistanceM: 1.5, shutterAngleDeg: 180,
    transform: { locationM: [0.7, -1.4, 0.42], rotationEulerDeg: [78, 0, 27], scale: [1, 1, 1] },
  }],
  lights: [
    { id: 'KEY_B05', type: 'AREA', colorLinear: [1, 0.74, 0.55], energy: 700, sizeM: 1.1, transform: { locationM: [0.8, -0.8, 1.3], rotationEulerDeg: [25, 0, 35], scale: [1, 1, 1] } },
    { id: 'FILL_B05', type: 'AREA', colorLinear: [0.38, 0.58, 1], energy: 420, sizeM: 1.2, transform: { locationM: [-0.9, -0.5, 0.8], rotationEulerDeg: [50, 0, -55], scale: [1, 1, 1] } },
  ],
  world: { backgroundLinear: [0.004, 0.008, 0.018], strength: 0.12 },
  events: [],
  render: {
    outputProfile: 'BFS_RESEARCH_MASTER_0_1', previewEngine: 'BLENDER_EEVEE', finalEngine: 'CYCLES',
    resolution: { width: 3840, height: 2160, percentage: 100 }, samplesPreview: 32, samplesFinal: 128,
    denoise: true, fileFormat: 'OPEN_EXR_MULTILAYER', pixelType: 'HALF_16', compression: 'ZIP_LOSSLESS',
    passes: ['Combined', 'Alpha', 'Depth', 'Normal', 'Vector', 'Cryptomatte'], outputRoot: 'renders/SHOT_107/',
  },
  security: {
    networkAccess: false, arbitraryPython: false,
    allowedAssetRoots: ['assets/', 'library/', 'motion/'],
    allowedOperations: ['READ_MANIFEST', 'IMPORT_ASSET', 'CREATE_CAMERA', 'CREATE_LIGHT', 'CREATE_GRASP', 'SET_TRANSFORM', 'SET_RENDER', 'RENDER_PREVIEW', 'RENDER_FINAL'],
  },
  provenance: {
    briefId: 'BRIEF_B05_COMPILED_GRASP',
    createdBy: 'BFS SceneSpec v0.4 compiler experiment',
    createdAtUtc: '2026-08-26T18:00:00Z',
    sources: [
      { uri: graspUri, role: 'REFERENCE', license: 'PROJECT-INTERNAL', sha256: graspHash },
      { uri: assetReportUri, role: 'ASSET', license: 'PROJECT-INTERNAL', sha256: assetReportHash },
    ],
  },
};

const output = resolve(repositoryRoot, 'specs/benchmarks/B05.scene.json');
await writeFile(output, `${JSON.stringify(scene, null, 2)}\n`);
process.stdout.write(`B05_SCENE_WRITTEN ${output}\n`);
