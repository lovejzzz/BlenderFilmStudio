#!/usr/bin/env node
import { strict as assert } from 'node:assert';
import { inventoryChecks } from './audit-ai-native-studio-pc0.mjs';

const frames = [1, 48, 96, 97, 144, 192, 193, 240, 288];
const cameraSample = { camera: { lens: 50 } };
const lightSample = { light: { energy: 100 } };
const fixture = {
  schemaVersion: 'bfs.pc0HeroAssetActionInventory.v0.1',
  status: 'PASS',
  counts: { objects: 3, meshes: 1, vertices: 8, polygons: 6, materials: 1, actions: 1, fcurves: 1, keyframes: 2, animatedTargets: 1, heroCandidates: 1 },
  objects: [
    { name: 'CHAR_B62_GUARDIAN', type: 'MESH', mesh: { vertices: 8, polygons: 6 } },
    { name: 'CAM_WIDE_APPROACH', type: 'CAMERA' },
    { name: 'KEY_LIGHT', type: 'LIGHT' },
  ],
  heroCandidates: ['CHAR_B62_GUARDIAN'],
  materials: [{ name: 'MAT' }],
  actions: [{ name: 'ACT', fcurveCount: 1, keyframeCount: 2 }],
  animationBindings: [{}, {}, {}],
  animatedTargets: ['CHAR_B62_GUARDIAN'],
  sentinels: frames.map(frame => ({ frame, objects: { CHAR_B62_GUARDIAN: {}, CAM_WIDE_APPROACH: cameraSample, KEY_LIGHT: lightSample } })),
  operations: { renderCalls: 0, sceneSaves: 0, dataMutations: 0, networkCalls: 0, modelCalls: 0 },
};

const baseline = inventoryChecks(fixture);
for (const [id, pass] of Object.entries(baseline)) assert.equal(pass, true, id);
const noHero = structuredClone(fixture); noHero.heroCandidates = []; noHero.counts.heroCandidates = 0;
assert.equal(inventoryChecks(noHero).heroRoster, false);
const wrongFrames = structuredClone(fixture); wrongFrames.sentinels.pop();
assert.equal(inventoryChecks(wrongFrames).sentinelRoster, false);
const rendered = structuredClone(fixture); rendered.operations.renderCalls = 1;
assert.equal(inventoryChecks(rendered).zeroOperations, false);
process.stdout.write('BFS_PC0_TOOL_TEST PASS 14/14\n');
