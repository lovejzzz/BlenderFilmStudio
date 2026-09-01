import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { canonicalJson } from '../scripts/lib/scene-spec.mjs';
import { compileVisualImprovementPlanV2Files, computePlanHashV2 } from '../scripts/lib/visual-review-improvement-v2.mjs';

const packet = 'specs/fixtures/visual-review/PC4_VX1_ATTEMPT03.packet.v0.2.json';
const assessment = 'specs/fixtures/visual-review/PC4_VX1_ATTEMPT03.teacher-assessment.v0.2.json';
const compile = () => compileVisualImprovementPlanV2Files(packet, assessment);

test('rejected screenshots compile deterministically into five relationship operations', async () => {
  const first = (await compile()).plan;
  const second = (await compile()).plan;
  assert.equal(canonicalJson(first), canonicalJson(second));
  assert.equal(first.operations.length, 5);
  assert.equal(first.planHash, computePlanHashV2(first));
});

test('plan binds rejected observation and clean accepted baseline separately', async () => {
  const { plan } = await compile();
  assert.equal(plan.source.observedSceneSha256, 'dbfb99177fef2835f468a055fb39a0d8cd999c84f31afbccfc4143fa45c2087e');
  assert.equal(plan.source.executionBaselineSha256, '339de0032c8598ba5811bc06668ecdf7924e3c49434c8824094508adccc9d940');
  assert.notEqual(plan.source.observedSceneSha256, plan.source.executionBaselineSha256);
});

test('composition operations use measured occlusion and fit constraints', async () => {
  const { plan } = await compile();
  const occlusion = plan.operations.find(row => row.preset === 'HIDE_NEAREST_NONSTORY_OCCLUDER');
  const fit = plan.operations.find(row => row.preset === 'FIT_BOUND_SUBJECT_WITH_MARGIN');
  assert.equal(occlusion.parameters.maximumOcclusionRatio, 0.08);
  assert.deepEqual([fit.parameters.targetOccupancyMin, fit.parameters.targetOccupancyMax, fit.parameters.minimumNegativeSpaceMargin], [0.48, 0.78, 0.08]);
});

test('modeling operations carry contour depth coverage and scale hierarchy caps', async () => {
  const { plan } = await compile();
  for (const operation of plan.operations.filter(row => row.operationType.includes('CONTOUR'))) {
    assert.ok(operation.parameters.maximumReliefDepthRatio > 0);
    assert.ok(operation.parameters.maximumDetailCoverageRatio > 0);
    assert.equal(operation.parameters.requiredScaleBands, 3);
  }
});

test('facial operation encodes ordered landmarks rather than part count', async () => {
  const { plan } = await compile();
  const face = plan.operations.find(row => row.preset === 'LANDMARK_DRIVEN_FACEPLATE');
  assert.deepEqual(face.parameters.requiredFacialZones, ['EYE_LINE', 'BROW', 'CHEEK', 'JAW']);
  assert.equal('minimumLayers' in face.parameters, false);
});

test('lesson explicitly rejects the failed executor anti patterns', async () => {
  const { plan } = await compile();
  assert.ok(plan.lesson.antiPatterns.includes('PART_COUNT_AS_QUALITY'));
  assert.ok(plan.lesson.antiPatterns.includes('FLOATING_RECTANGULAR_OVERLAYS'));
  assert.ok(plan.operations.every(row => row.invariants.includes('NO_NAMED_PROJECT_SPECIAL_CASE')));
});

test('plan remains semantic and carries no executable authority', async () => {
  const { plan } = await compile();
  assert.deepEqual(plan.authority, { allowsArbitraryFilesystem: false, allowsNetwork: false, allowsPython: false, allowsShell: false, requiresTypedExecutor: true, semanticCatalogOnly: true });
});

test('generic compiler and catalog contain no exact project entity special cases', async () => {
  const source = await readFile('scripts/lib/visual-review-improvement-v2.mjs', 'utf8');
  const catalog = await readFile('specs/visual-treatment-catalog.v0.2.json', 'utf8');
  for (const forbidden of ['PC4_', 'B62_', 'AI_NATIVE_STUDIO_REAL_PROJECT_01']) {
    assert.equal(source.includes(forbidden), false);
    assert.equal(catalog.includes(forbidden), false);
  }
});
