import test from 'node:test';
import assert from 'node:assert/strict';
import { access, readFile } from 'node:fs/promises';
import { constants } from 'node:fs';
import { canonicalJson, sha256 } from '../scripts/lib/scene-spec.mjs';

const contextPath = 'specs/fixtures/visual-review/PC4_VX2.execution-context.v0.1.json';
const planPath = 'experiments/visual-film-language-loop/PC4-VFL2-2026-08-31-attempt-01/visual-improvement-plan.v0.2.json';
const executorPath = 'scripts/execute-film-language-plan-v2.py';
const context = JSON.parse(await readFile(contextPath));
const plan = JSON.parse(await readFile(planPath));
const executor = await readFile(executorPath, 'utf8');

function selfHash(value, field) { const copy = structuredClone(value); delete copy[field]; return sha256(canonicalJson(copy)); }

test('context and plan identities are exact and self bound', async () => {
  assert.equal(context.contextHash, selfHash(context, 'contextHash'));
  assert.equal(plan.planHash, context.plan.planHash);
  assert.equal(sha256(await readFile(planPath)), context.plan.sha256);
});

test('executor accepts exactly the five film-language typed adapters', () => {
  assert.equal(plan.operations.length, 5);
  for (const operation of plan.operations) assert.ok(executor.includes(`("${operation.operationType}", "${operation.preset}")`));
});

test('trusted geometry contains no exact project object or collection special case', () => {
  for (const forbidden of ['PC4_', 'B62_', 'AI_NATIVE_STUDIO_REAL_PROJECT_01', 'SET_B62_OBSERVATORY', 'PC4_HERO_REDESIGN']) assert.equal(executor.includes(forbidden), false);
});

test('executor derives roles from packet semantics', () => {
  for (const phrase of ['semanticRole', '"hero" in roles', '"foreground" in roles', '"faceplate" in row[0]', '"joint" in role', '"cap" in role']) assert.ok(executor.includes(phrase));
});

test('composition is measured in screen space rather than fixed lens percentage', () => {
  for (const phrase of ['world_to_camera_view', 'intersection_ratio', 'maximumOcclusionRatio', 'targetOccupancyMin', 'targetOccupancyMax', 'minimumNegativeSpaceMargin']) assert.ok(executor.includes(phrase));
  assert.equal(executor.includes('requested = 12.0'), false);
});

test('detail generation enforces relief coverage and scale-band constraints', () => {
  for (const phrase of ['maximumReliefDepthRatio', 'maximumDetailCoverageRatio', 'requiredScaleBands', 'maximumSameScalePeers', 'bfs_film_language_scale_band']) assert.ok(executor.includes(phrase));
  assert.equal('minimumLayers' in plan.operations[1].parameters, false);
});

test('face is an ordered landmark hierarchy rather than a part floor', () => {
  const face = plan.operations.find(row => row.preset === 'LANDMARK_DRIVEN_FACEPLATE');
  assert.deepEqual(face.parameters.requiredFacialZones, ['EYE_LINE', 'BROW', 'CHEEK', 'JAW']);
  for (const zone of face.parameters.requiredFacialZones) assert.ok(executor.includes(`"${zone}"`));
});

test('trusted Python has no process network or dynamic-code authority', () => {
  for (const forbidden of ['import subprocess', 'import socket', 'import requests', 'urllib', 'eval(', 'exec(', 'os.system', 'Popen(']) assert.equal(executor.includes(forbidden), false);
});

test('formal roots remain fresh and external identities are readable', async () => {
  await assert.rejects(access(context.roots.work, constants.F_OK));
  await assert.rejects(access(context.roots.evidence, constants.F_OK));
  await access(context.source.path, constants.R_OK);
  await access(context.binary.path, constants.X_OK);
  assert.equal(sha256(await readFile(context.source.path)), context.source.sha256);
  assert.equal(sha256(await readFile(context.binary.path)), context.binary.sha256);
});

test('visual verdict remains pending after machine execution', async () => {
  const runner = await readFile('scripts/run-film-language-plan-v2-execution.mjs', 'utf8');
  assert.ok(runner.includes("visualVerdict: 'PENDING_DIRECT_MODEL_REVIEW'"));
  assert.equal(runner.includes("visualVerdict: 'PASS'"), false);
});
