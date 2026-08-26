import { appendFile, copyFile, link, mkdir, readFile, readdir, realpath, rm, unlink, writeFile } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { relative, resolve, sep } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256Canonical, sha256File } from './lib/receipt-format.mjs';

const root = resolve(repositoryRoot, 'experiments/eevee-sampling-dose-response-v0-1');
const evidenceRoot = resolve(root, 'evidence');
const workRoot = resolve(root, 'work');
const derivedSpecRoot = resolve(workRoot, 'review-specs');
const doseSpecPath = resolve(repositoryRoot, 'specs/eevee-sampling-dose-response-spec.v0.1.json');
const baseReviewSpecPath = resolve(repositoryRoot, 'specs/review-render-spec.v0.1.json');
const renderer = resolve(repositoryRoot, 'blender/render_review_sequence.py');
const comparator = resolve(repositoryRoot, 'blender/compare_review_sequences.py');
const configurator = resolve(repositoryRoot, 'blender/configure_eevee_factorial.py');
const blender = resolve(process.env.BLENDER_BIN || '/Applications/Blender.app/Contents/MacOS/Blender');
const serialize = value => `${JSON.stringify(value, null, 2)}\n`;
const repoUri = path => relative(repositoryRoot, path).split(sep).join('/');

function run(command, args, env = process.env) {
  return new Promise((resolvePromise, reject) => {
    const child = spawn(command, args, { cwd: repositoryRoot, env, stdio: ['ignore', 'pipe', 'pipe'] });
    let output = '';
    child.stdout.on('data', chunk => { output += chunk; });
    child.stderr.on('data', chunk => { output += chunk; });
    child.on('error', reject);
    child.on('close', code => code === 0 ? resolvePromise(output) : reject(new Error(`${command} failed (${code})\n${output}`)));
  });
}

async function pngNames(dir) {
  return (await readdir(dir)).filter(name => name.endsWith('.png')).sort();
}

async function materializeReviewSpecs(doseSpec, baseReviewSpec) {
  await mkdir(derivedSpecRoot, { recursive: true });
  const paths = new Map();
  for (const samples of doseSpec.design.renderSampleLevels) {
    const derived = structuredClone(baseReviewSpec);
    derived.proxy.renderSamples = samples;
    const path = resolve(derivedSpecRoot, `review-render-spec.samples-${String(samples).padStart(2, '0')}.json`);
    await writeFile(path, serialize(derived));
    const expected = doseSpec.reviewSpecMaterialization.expectedSha256BySamples[String(samples)];
    if (await sha256File(path) !== expected) throw new Error(`Derived ReviewRenderSpec SHA mismatch for samples=${samples}`);
    const restored = structuredClone(derived);
    restored.proxy.renderSamples = baseReviewSpec.proxy.renderSamples;
    if (sha256Canonical(restored) !== sha256Canonical(baseReviewSpec)) throw new Error(`Derived ReviewRenderSpec changed more than renderSamples for samples=${samples}`);
    paths.set(samples, path);
  }
  return paths;
}

async function makeManifest({ report, doseSpecSha, cell, runId, derivedSpecSha, toolIdentities }) {
  const body = {
    documentType: 'BFS_EEVEE_SAMPLING_DOSE_SEQUENCE',
    version: '0.1.0',
    runId,
    cellId: cell.id,
    factors: { renderSamples: cell.renderSamples, ditherIntensity: 0 },
    frameCount: report.frameCount,
    frameStart: 1,
    frameEnd: 144,
    resolution: [960, 540],
    doseSpecSha256: doseSpecSha,
    derivedReviewRenderSpecSha256: derivedSpecSha,
    toolIdentities,
    frames: report.frames.map(({ frame, name, sha256, bytes }) => ({ frame, name, sha256, bytes })),
  };
  return { ...body, sequenceHash: sha256Canonical(body) };
}

async function validateRun({
  runRecord,
  cell,
  derivedSpecPath,
  expectedDoseSpecSha,
  expectedBaseReviewSpecSha,
  expectedDerivedSpecSha,
  expectedRendererSha,
  expectedComparatorSha,
  expectedConfiguratorSha,
  expectedRenderSamples = cell.renderSamples,
  expectedDither = 0,
}) {
  if (await sha256File(doseSpecPath) !== expectedDoseSpecSha) return 'DOSE_SPEC_SHA';
  if (await sha256File(baseReviewSpecPath) !== expectedBaseReviewSpecSha) return 'BASE_REVIEW_SPEC_SHA';
  if (await sha256File(derivedSpecPath) !== expectedDerivedSpecSha) return 'DERIVED_REVIEW_SPEC_SHA';
  if (await sha256File(renderer) !== expectedRendererSha) return 'RENDERER_SHA';
  if (await sha256File(comparator) !== expectedComparatorSha) return 'COMPARATOR_SHA';
  if (await sha256File(configurator) !== expectedConfiguratorSha) return 'CONFIGURATOR_SHA';
  if (expectedDither !== 0) return 'FIXED_DITHER';

  const intervention = JSON.parse(await readFile(runRecord.interventionPath, 'utf8'));
  if (intervention.before !== 1) return 'STARTING_DITHER';
  if (intervention.requested !== expectedDither || intervention.after !== expectedDither) return 'FIXED_DITHER';
  if (intervention.savedSourceBlend !== false) return 'SOURCE_BLEND_SAVED';
  if (intervention.sceneBlendSha256 !== runRecord.sceneBlendSha256) return 'INTERVENTION_SCENE_SHA';

  const report = JSON.parse(await readFile(runRecord.renderReportPath, 'utf8'));
  if (report.runtime.renderSamples !== expectedRenderSamples || report.profile.renderSamples !== expectedRenderSamples) return 'RENDER_SAMPLES';
  if (report.frameCount !== 144) return 'FRAME_COUNT';
  if (report.cameraAndTimelineInvariant !== true) return 'CAMERA_TIMELINE_INVARIANT';
  if (report.source.sceneBlendSha256 !== runRecord.sceneBlendSha256) return 'RENDER_SCENE_SHA';

  const manifest = JSON.parse(await readFile(runRecord.manifestPath, 'utf8'));
  const body = structuredClone(manifest);
  delete body.sequenceHash;
  if (sha256Canonical(body) !== manifest.sequenceHash) return 'MANIFEST_SELF_HASH';
  if (manifest.runId !== runRecord.runId || manifest.cellId !== cell.id) return 'MANIFEST_RUN_BINDING';
  if (manifest.factors.renderSamples !== cell.renderSamples || manifest.factors.ditherIntensity !== 0) return 'MANIFEST_FACTORS';
  if (manifest.doseSpecSha256 !== expectedDoseSpecSha || manifest.derivedReviewRenderSpecSha256 !== expectedDerivedSpecSha) return 'MANIFEST_SPEC_BINDING';
  const expectedNames = manifest.frames.map(frame => frame.name);
  const observedNames = await pngNames(runRecord.dir);
  if (expectedNames.some(name => !observedNames.includes(name))) return 'MISSING_FRAME';
  if (observedNames.some(name => !expectedNames.includes(name))) return 'EXTRA_FRAME';
  for (const frame of manifest.frames) if (await sha256File(resolve(runRecord.dir, frame.name)) !== frame.sha256) return 'FRAME_SHA';
  return 'OK';
}

async function validateComparison({ bindingPath, comparisonPath, aManifest, bManifest, expectedComparatorSha }) {
  if (await sha256File(comparator) !== expectedComparatorSha) return 'COMPARATOR_SHA';
  const binding = JSON.parse(await readFile(bindingPath, 'utf8'));
  const body = structuredClone(binding);
  delete body.bindingHash;
  if (sha256Canonical(body) !== binding.bindingHash) return 'COMPARISON_SELF_HASH';
  if (binding.aSequenceHash !== aManifest.sequenceHash || binding.bSequenceHash !== bManifest.sequenceHash) return 'COMPARISON_SEQUENCE_BINDING';
  if (binding.comparisonSha256 !== await sha256File(comparisonPath)) return 'COMPARISON_SHA';
  const comparison = JSON.parse(await readFile(comparisonPath, 'utf8'));
  if (comparison.frameCount !== 144 || comparison.frames.length !== 144) return 'COMPARISON_FRAME_COUNT';
  for (let index = 0; index < comparison.frames.length; index += 1) {
    if (comparison.frames[index].aSha256 !== aManifest.frames[index].sha256 || comparison.frames[index].bSha256 !== bManifest.frames[index].sha256) return 'COMPARISON_FRAME_BINDING';
  }
  return 'OK';
}

async function cloneFrames(source, target) {
  await mkdir(target, { recursive: true });
  for (const name of await pngNames(source)) await link(resolve(source, name), resolve(target, name));
}

await rm(evidenceRoot, { recursive: true, force: true });
await rm(workRoot, { recursive: true, force: true });
await mkdir(evidenceRoot, { recursive: true });

const doseSpec = JSON.parse(await readFile(doseSpecPath, 'utf8'));
const doseSpecSha = await sha256File(doseSpecPath);
if (doseSpecSha !== '8fde40cab5de4483ea8db35cbf7893e0b21705a207edd215cdeaf76eb5b4d7ee') throw new Error('Dose-response spec changed after pre-registration');
const baseReviewSpec = JSON.parse(await readFile(baseReviewSpecPath, 'utf8'));
const derivedSpecs = await materializeReviewSpecs(doseSpec, baseReviewSpec);
const cells = new Map(doseSpec.design.cells.map(cell => [cell.id, cell]));
const runToCell = new Map(doseSpec.design.cells.flatMap(cell => cell.runs.map(runId => [runId, cell])));
const frozen = doseSpec.frozenIdentity;
const toolIdentities = {
  rendererSha256: await sha256File(renderer),
  comparatorSha256: await sha256File(comparator),
  configuratorSha256: await sha256File(configurator),
};
for (const [path, expected, label] of [
  [baseReviewSpecPath, doseSpec.reviewSpecMaterialization.baseSha256, 'base ReviewRenderSpec'],
  [renderer, frozen.rendererSha256, 'renderer'],
  [comparator, frozen.comparatorSha256, 'comparator'],
  [configurator, frozen.configuratorSha256, 'configurator'],
  [blender, frozen.blenderSha256, 'Blender'],
]) if (await sha256File(path) !== expected) throw new Error(`${label} frozen SHA mismatch`);

const receiptPath = resolve(repositoryRoot, baseReviewSpec.source.receiptUri);
const receipt = JSON.parse(await readFile(receiptPath, 'utf8'));
const scenePath = resolve(repositoryRoot, receipt.run.sceneBlend.uri);
const ocioPath = resolve(repositoryRoot, receipt.executionIdentity.configuration.ocio.uri);
if (await sha256File(scenePath) !== frozen.sceneBlendSha256 || await sha256File(ocioPath) !== frozen.ocioSha256) throw new Error('Scene or OCIO frozen SHA mismatch');

const runs = new Map();
for (const runId of doseSpec.design.runOrder) {
  const cell = runToCell.get(runId);
  if (!cell) throw new Error(`Run order contains unknown run ${runId}`);
  const derivedSpecPath = derivedSpecs.get(cell.renderSamples);
  const derivedSpecSha = doseSpec.reviewSpecMaterialization.expectedSha256BySamples[String(cell.renderSamples)];
  const dir = resolve(workRoot, runId);
  const renderReportPath = resolve(evidenceRoot, `${runId}.render.json`);
  const interventionPath = resolve(evidenceRoot, `${runId}.intervention.json`);
  const manifestPath = resolve(evidenceRoot, `${runId}.sequence.manifest.json`);
  await mkdir(dir, { recursive: true });
  await run(blender, [
    '--background', scenePath, '--disable-autoexec', '--python-exit-code', '1',
    '--python', configurator, '--python', renderer, '--',
    '--spec', derivedSpecPath, '--receipt', receiptPath, '--output-dir', dir, '--report', renderReportPath,
  ], {
    ...process.env,
    OCIO: ocioPath,
    BFS_FACTORIAL_DITHER_INTENSITY: '0.0',
    BFS_EXPECT_DITHER_INTENSITY: '1.0',
    BFS_FACTORIAL_DITHER_REPORT: interventionPath,
  });
  const report = JSON.parse(await readFile(renderReportPath, 'utf8'));
  const manifest = await makeManifest({ report, doseSpecSha, cell, runId, derivedSpecSha, toolIdentities });
  await writeFile(manifestPath, serialize(manifest));
  const runRecord = { runId, dir, renderReportPath, interventionPath, manifestPath, manifest, report, sceneBlendSha256: frozen.sceneBlendSha256 };
  const reason = await validateRun({
    runRecord, cell, derivedSpecPath,
    expectedDoseSpecSha: doseSpecSha,
    expectedBaseReviewSpecSha: doseSpec.reviewSpecMaterialization.baseSha256,
    expectedDerivedSpecSha: derivedSpecSha,
    expectedRendererSha: frozen.rendererSha256,
    expectedComparatorSha: frozen.comparatorSha256,
    expectedConfiguratorSha: frozen.configuratorSha256,
  });
  if (reason !== 'OK') throw new Error(`${runId} control failed: ${reason}`);
  runs.set(runId, runRecord);
  process.stdout.write(`BFS_B18_RUN_OK ${runId} samples=${cell.renderSamples} seconds=${report.totalRenderSeconds}\n`);
}

const comparisons = new Map();
for (const cell of doseSpec.design.cells) {
  const [aRunId, bRunId] = cell.runs;
  const a = runs.get(aRunId), b = runs.get(bRunId);
  if (await realpath(a.dir) === await realpath(b.dir)) throw new Error(`${cell.id} run directories alias`);
  const comparisonPath = resolve(evidenceRoot, `${cell.id}.sequence.comparison.json`);
  const bindingPath = resolve(evidenceRoot, `${cell.id}.comparison.binding.json`);
  await run(blender, ['--factory-startup', '--background', '--python-exit-code', '1', '--python', comparator, '--', '--a-dir', a.dir, '--b-dir', b.dir, '--frame-start', '1', '--frame-end', '144', '--output', comparisonPath]);
  const comparison = JSON.parse(await readFile(comparisonPath, 'utf8'));
  const body = {
    documentType: 'BFS_EEVEE_SAMPLING_DOSE_COMPARISON_BINDING', version: '0.1.0', cellId: cell.id,
    aRunId, bRunId, aSequenceHash: a.manifest.sequenceHash, bSequenceHash: b.manifest.sequenceHash,
    comparatorSha256: frozen.comparatorSha256, comparisonSha256: await sha256File(comparisonPath),
  };
  const binding = { ...body, bindingHash: sha256Canonical(body) };
  await writeFile(bindingPath, serialize(binding));
  const reason = await validateComparison({ bindingPath, comparisonPath, aManifest: a.manifest, bManifest: b.manifest, expectedComparatorSha: frozen.comparatorSha256 });
  if (reason !== 'OK') throw new Error(`${cell.id} comparison control failed: ${reason}`);
  comparisons.set(cell.id, { comparison, comparisonPath, binding, bindingPath });
}

const attackCell = cells.get('S01');
const attackRun = runs.get('S01-A');
const attackDerivedSpecPath = derivedSpecs.get(1);
const validationDefaults = {
  runRecord: attackRun, cell: attackCell, derivedSpecPath: attackDerivedSpecPath,
  expectedDoseSpecSha: doseSpecSha,
  expectedBaseReviewSpecSha: doseSpec.reviewSpecMaterialization.baseSha256,
  expectedDerivedSpecSha: doseSpec.reviewSpecMaterialization.expectedSha256BySamples['1'],
  expectedRendererSha: frozen.rendererSha256,
  expectedComparatorSha: frozen.comparatorSha256,
  expectedConfiguratorSha: frozen.configuratorSha256,
};
const attacks = [];
async function record(id, expected, observed) { attacks.push({ id, expectedReason: expected, observedReason: observed, pass: observed === expected }); }
await record('N_DOSE_SPEC_SHA', 'DOSE_SPEC_SHA', await validateRun({ ...validationDefaults, expectedDoseSpecSha: '0'.repeat(64) }));
await record('N_BASE_REVIEW_SPEC_SHA', 'BASE_REVIEW_SPEC_SHA', await validateRun({ ...validationDefaults, expectedBaseReviewSpecSha: '0'.repeat(64) }));
await record('N_DERIVED_REVIEW_SPEC_SHA', 'DERIVED_REVIEW_SPEC_SHA', await validateRun({ ...validationDefaults, expectedDerivedSpecSha: '0'.repeat(64) }));
await record('N_RENDERER_SHA', 'RENDERER_SHA', await validateRun({ ...validationDefaults, expectedRendererSha: '0'.repeat(64) }));
await record('N_COMPARATOR_SHA', 'COMPARATOR_SHA', await validateRun({ ...validationDefaults, expectedComparatorSha: '0'.repeat(64) }));
await record('N_CONFIGURATOR_SHA', 'CONFIGURATOR_SHA', await validateRun({ ...validationDefaults, expectedConfiguratorSha: '0'.repeat(64) }));
await record('N_FIXED_DITHER', 'FIXED_DITHER', await validateRun({ ...validationDefaults, expectedDither: 1 }));
await record('N_RENDER_SAMPLES', 'RENDER_SAMPLES', await validateRun({ ...validationDefaults, expectedRenderSamples: 3 }));
await record('N_ALIAS_RUNS', 'ALIAS_RUNS', await realpath(attackRun.dir) === await realpath(attackRun.dir) ? 'ALIAS_RUNS' : 'OK');
for (const [id, expected, mutate] of [
  ['N_MISSING_FRAME', 'MISSING_FRAME', async dir => unlink(resolve(dir, 'frame-0072.png'))],
  ['N_EXTRA_FRAME', 'EXTRA_FRAME', async dir => link(resolve(dir, 'frame-0001.png'), resolve(dir, 'frame-0145.png'))],
  ['N_FRAME_SHA', 'FRAME_SHA', async dir => {
    const target = resolve(dir, 'frame-0072.png'), temp = resolve(dir, 'frame-0072-copy.tmp');
    await copyFile(target, temp); await unlink(target); await copyFile(temp, target); await appendFile(target, Buffer.from([0]));
  }],
]) {
  const dir = resolve(workRoot, 'attacks', id);
  await cloneFrames(attackRun.dir, dir); await mutate(dir);
  await record(id, expected, await validateRun({ ...validationDefaults, runRecord: { ...attackRun, dir } }));
}
const comparisonAttackBase = comparisons.get('S01');
const attackedBindingBody = structuredClone(comparisonAttackBase.binding); delete attackedBindingBody.bindingHash;
attackedBindingBody.aSequenceHash = '0'.repeat(64);
const attackedBinding = { ...attackedBindingBody, bindingHash: sha256Canonical(attackedBindingBody) };
const attackedBindingPath = resolve(workRoot, 'attacks', 'N_COMPARISON_BINDING.json');
await writeFile(attackedBindingPath, serialize(attackedBinding));
await record('N_COMPARISON_BINDING', 'COMPARISON_SEQUENCE_BINDING', await validateComparison({
  bindingPath: attackedBindingPath, comparisonPath: comparisonAttackBase.comparisonPath,
  aManifest: runs.get('S01-A').manifest, bManifest: runs.get('S01-B').manifest,
  expectedComparatorSha: frozen.comparatorSha256,
}));

const cellResults = Object.fromEntries(doseSpec.design.cells.map(cell => {
  const comparisonRecord = comparisons.get(cell.id), comparison = comparisonRecord.comparison;
  const exact = comparison.decodedPixelExactFrames === 144 && comparison.maximumAbsoluteError === 0 && comparison.totalFailurePixels === 0;
  const [aRunId, bRunId] = cell.runs;
  return [cell.id, {
    renderSamples: cell.renderSamples,
    exactDecodedPixels: exact,
    containerExactFrames: comparison.containerExactFrames,
    decodedPixelExactFrames: comparison.decodedPixelExactFrames,
    maximumAbsoluteError: comparison.maximumAbsoluteError,
    totalFailurePixels: comparison.totalFailurePixels,
    worstFrame: comparison.worstFrame.frame,
    aSequenceHash: runs.get(aRunId).manifest.sequenceHash,
    bSequenceHash: runs.get(bRunId).manifest.sequenceHash,
    aRenderSeconds: runs.get(aRunId).report.totalRenderSeconds,
    bRenderSeconds: runs.get(bRunId).report.totalRenderSeconds,
    comparisonBindingHash: comparisonRecord.binding.bindingHash,
  }];
}));

const exactnessVector = doseSpec.design.cells.map(cell => cellResults[cell.id].exactDecodedPixels);
const validExperiment = attacks.length === 13 && attacks.every(attack => attack.pass);
const allExact = exactnessVector.every(Boolean);
const onlySingleExact = exactnessVector[0] && exactnessVector.slice(1).every(value => !value);
const firstNonExactIndex = exactnessVector.indexOf(false);
const monotonicBoundary = firstNonExactIndex >= 2 && exactnessVector.slice(0, firstNonExactIndex).every(Boolean) && exactnessVector.slice(firstNonExactIndex).every(value => !value);
let decision = 'NON_MONOTONIC_OR_UNSTABLE';
if (!validExperiment) decision = 'INVALID_EXPERIMENT';
else if (onlySingleExact) decision = 'ONLY_SINGLE_SAMPLE_EXACT';
else if (monotonicBoundary) decision = 'MONOTONIC_BOUNDARY_FOUND';
else if (allExact) decision = 'ALL_LEVELS_EXACT_BASELINE_UNSTABLE';
const boundary = monotonicBoundary ? {
  lastExactSamples: doseSpec.design.renderSampleLevels[firstNonExactIndex - 1],
  firstNonExactSamples: doseSpec.design.renderSampleLevels[firstNonExactIndex],
} : onlySingleExact ? { lastExactSamples: 1, firstNonExactSamples: 2 } : null;

const result = {
  documentType: 'BFS_B18_EEVEE_SAMPLING_DOSE_RESPONSE_EXPERIMENT', version: '0.1.0', executedAtUtc: new Date().toISOString(),
  decision, validExperiment, exactnessVector, boundary,
  design: { ...doseSpec.design, renderedFrames: 12 * 144 },
  identities: { ...frozen, doseSpecSha256: doseSpecSha, baseReviewSpecSha256: doseSpec.reviewSpecMaterialization.baseSha256 },
  historicalEvidence: doseSpec.historicalEvidence,
  cells: cellResults,
  attacks,
  artifacts: Object.fromEntries(doseSpec.design.cells.map(cell => [cell.id, {
    comparison: repoUri(comparisons.get(cell.id).comparisonPath), comparisonBinding: repoUri(comparisons.get(cell.id).bindingPath),
    aManifest: repoUri(runs.get(cell.runs[0]).manifestPath), bManifest: repoUri(runs.get(cell.runs[1]).manifestPath),
  }])),
  nonClaims: doseSpec.explicitNonClaims,
};
await writeFile(resolve(root, 'results.json'), serialize(result));
process.stdout.write(`BFS_B18_EEVEE_DOSE ${decision} vector=${exactnessVector.map(value => value ? 'T' : 'F').join('')} ` + doseSpec.design.cells.map(cell => `${cell.id}=${cellResults[cell.id].decodedPixelExactFrames}/144`).join(' ') + ` attacks=${attacks.filter(attack => attack.pass).length}/13\n`);
if (!validExperiment) process.exitCode = 1;
