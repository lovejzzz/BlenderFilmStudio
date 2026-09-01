import assert from 'node:assert/strict';
import { readFile, lstat } from 'node:fs/promises';
import test from 'node:test';
import { canonicalJson, sha256 } from '../scripts/lib/scene-spec.mjs';

const preregPath = 'specs/ai-native-studio-visual-plan-typed-execution-preregistration.v0.1.json';
const correctionPath = 'specs/ai-native-studio-visual-plan-typed-execution-preregistration-c2.v0.3.json';
const contextPath = 'specs/fixtures/visual-review/PC4_ATTEMPT03.execution-context-c2.v0.3.json';
const planPath = 'experiments/visual-understanding-loop/PC4-VU1-2026-08-31-attempt-03/visual-improvement-plan.json';
const packetPath = 'specs/fixtures/visual-review/PC4_ATTEMPT03.packet.json';
const executorPath = 'scripts/execute-visual-improvement-plan.py';
const reopenPath = 'scripts/audit-visual-improvement-plan-reopen.py';
const runnerPath = 'scripts/run-visual-plan-typed-execution.mjs';
const auditorPath = 'scripts/audit-visual-plan-typed-execution.mjs';

const preregBytes = await readFile(preregPath);
const correctionBytes = await readFile(correctionPath);
const contextBytes = await readFile(contextPath);
const planBytes = await readFile(planPath);
const packetBytes = await readFile(packetPath);
const prereg = JSON.parse(preregBytes);
const correction = JSON.parse(correctionBytes);
const context = JSON.parse(contextBytes);
const plan = JSON.parse(planBytes);
const packet = JSON.parse(packetBytes);
const executor = await readFile(executorPath, 'utf8');
const reopen = await readFile(reopenPath, 'utf8');
const runner = await readFile(runnerPath, 'utf8');
const auditor = await readFile(auditorPath, 'utf8');

function selfHash(value, key) {
  const projection = structuredClone(value);
  delete projection[key];
  return sha256(canonicalJson(projection));
}

async function absent(path) {
  try { await lstat(path); return false; } catch (error) { if (error.code === 'ENOENT') return true; throw error; }
}

test('preregistration and execution context self hashes are exact', () => {
  assert.equal(prereg.specHash, selfHash(prereg, 'specHash'));
  assert.equal(correction.specHash, selfHash(correction, 'specHash'));
  assert.equal(context.contextHash, selfHash(context, 'contextHash'));
});

test('context binds the accepted visual plan and packet bytes', () => {
  assert.equal(context.plan.sha256, sha256(planBytes));
  assert.equal(context.packet.sha256, sha256(packetBytes));
  assert.equal(context.plan.planHash, plan.planHash);
});

test('plan has the exact six compiled semantic operations', () => {
  assert.equal(plan.decision, 'COMPILED');
  assert.equal(plan.operations.length, 6);
  assert.equal(prereg.inputPlan.exactOperationCount, 6);
});

test('every plan operation has one frozen typed adapter', () => {
  const adapters = new Set(prereg.typedAdapters.map(row => `${row.operationType}:${row.preset}`));
  assert.deepEqual(new Set(plan.operations.map(row => `${row.operationType}:${row.preset}`)), adapters);
});

test('plan carries no executable authority', () => {
  assert.deepEqual(plan.authority, { allowsArbitraryFilesystem: false, allowsNetwork: false, allowsPython: false, allowsShell: false, requiresTypedExecutor: true, semanticCatalogOnly: true });
});

test('shot context is contiguous and covers the real 288 frame sequence', () => {
  assert.deepEqual(context.shots.map(row => [row.frameStart, row.frameEnd, row.reviewFrame]), [[1, 96, 48], [97, 192, 144], [193, 288, 240]]);
});

test('shot cameras are packet-bound and known entities', () => {
  const packetCameras = new Set(packet.frames.map(row => row.cameraId));
  assert.ok(context.shots.every(row => packetCameras.has(row.cameraId)));
});

test('trusted geometry code contains no plan target name special cases', () => {
  const targetIds = new Set(plan.operations.flatMap(row => row.targetEntityIds));
  for (const targetId of targetIds) assert.equal(executor.includes(targetId), false, targetId);
});

test('trusted Python does not import process network or dynamic-code modules', () => {
  for (const source of [executor, reopen]) assert.doesNotMatch(source, /\b(?:subprocess|socket|urllib|requests|eval|exec)\b/);
});

test('executor implements all five typed semantic branches', () => {
  for (const token of ['apply_visibility', 'apply_framing', 'apply_joint', 'apply_face', 'apply_surface']) assert.match(executor, new RegExp(`def ${token}\\b`));
});

test('machine floors require 28 typed parts and direct visual review', () => {
  assert.equal(prereg.acceptance.minimumTotalNewTypedParts, 28);
  assert.equal(prereg.acceptance.directModelVisualReviewRequired, true);
  assert.equal(prereg.acceptance.fullSequenceRenderBeforeVisualPass, false);
});

test('lens policy is deterministically below the plan cap', () => {
  const framing = plan.operations.filter(row => row.operationType === 'APPLY_FRAMING_PRESET');
  assert.equal(framing.length, 2);
  assert.ok(framing.every(row => row.parameters.maximumLensChangePercent === 15));
  assert.match(executor, /requested = 12\.0/);
});

test('formal work and evidence roots are still fresh', async () => {
  assert.equal(await absent(context.roots.work), true);
  assert.equal(await absent(context.roots.evidence), true);
});

test('source and binary identities are live exact', async () => {
  assert.equal(sha256(await readFile(context.source.path)), context.source.sha256);
  assert.equal(sha256(await readFile(context.binary.path)), context.binary.sha256);
});

test('runner and independent auditor keep visual verdict pending', () => {
  assert.match(runner, /PENDING_DIRECT_MODEL_REVIEW/);
  assert.match(auditor, /PENDING_DIRECT_MODEL_REVIEW/);
});
