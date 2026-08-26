import { appendFile, copyFile, link, mkdir, readFile, readdir, realpath, rm, unlink, writeFile } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { relative, resolve, sep } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256Canonical, sha256File } from './lib/receipt-format.mjs';

const root = resolve(repositoryRoot, 'experiments/eevee-sampling-factorial-v0-1');
const evidenceRoot = resolve(root, 'evidence');
const workRoot = resolve(root, 'work');
const factorialSpecPath = resolve(repositoryRoot, 'specs/eevee-sampling-factorial-spec.v0.1.json');
const reviewSpecs = new Map([
  [1, resolve(repositoryRoot, 'specs/review-render-spec.samples1.v0.1.json')],
  [32, resolve(repositoryRoot, 'specs/review-render-spec.v0.1.json')],
]);
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

async function makeManifest({ report, factorialSpecSha, cell, runId, reviewSpecSha, toolIdentities }) {
  const body = {
    documentType: 'BFS_EEVEE_FACTORIAL_SEQUENCE',
    version: '0.1.0',
    runId,
    cellId: cell.id,
    factors: { renderSamples: cell.renderSamples, ditherIntensity: cell.ditherIntensity },
    frameCount: report.frameCount,
    frameStart: 1,
    frameEnd: 144,
    resolution: [960, 540],
    factorialSpecSha256: factorialSpecSha,
    reviewRenderSpecSha256: reviewSpecSha,
    toolIdentities,
    frames: report.frames.map(({ frame, name, sha256, bytes }) => ({ frame, name, sha256, bytes })),
  };
  return { ...body, sequenceHash: sha256Canonical(body) };
}

async function validateRun({
  runRecord,
  cell,
  expectedFactorialSha,
  expectedReviewSpecSha,
  expectedRendererSha,
  expectedComparatorSha,
  expectedConfiguratorSha,
  expectedRenderSamples = cell.renderSamples,
  expectedDither = cell.ditherIntensity,
}) {
  if (await sha256File(factorialSpecPath) !== expectedFactorialSha) return 'FACTORIAL_SPEC_SHA';
  if (await sha256File(reviewSpecs.get(cell.renderSamples)) !== expectedReviewSpecSha) return 'REVIEW_SPEC_SHA';
  if (await sha256File(renderer) !== expectedRendererSha) return 'RENDERER_SHA';
  if (await sha256File(comparator) !== expectedComparatorSha) return 'COMPARATOR_SHA';
  if (await sha256File(configurator) !== expectedConfiguratorSha) return 'CONFIGURATOR_SHA';
  if (![0, 1].includes(expectedDither)) return 'DITHER_LEVEL';

  const intervention = JSON.parse(await readFile(runRecord.interventionPath, 'utf8'));
  if (intervention.documentType !== 'BFS_EEVEE_FACTORIAL_INTERVENTION') return 'INTERVENTION_TYPE';
  if (intervention.before !== 1) return 'STARTING_DITHER';
  if (intervention.requested !== expectedDither || intervention.after !== expectedDither) return 'DITHER_LEVEL';
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
  if (manifest.factors.renderSamples !== cell.renderSamples || manifest.factors.ditherIntensity !== cell.ditherIntensity) return 'MANIFEST_FACTORS';
  if (manifest.factorialSpecSha256 !== expectedFactorialSha || manifest.reviewRenderSpecSha256 !== expectedReviewSpecSha) return 'MANIFEST_SPEC_BINDING';
  const expectedNames = manifest.frames.map(frame => frame.name);
  const observedNames = await pngNames(runRecord.dir);
  if (expectedNames.some(name => !observedNames.includes(name))) return 'MISSING_FRAME';
  if (observedNames.some(name => !expectedNames.includes(name))) return 'EXTRA_FRAME';
  for (const frame of manifest.frames) {
    if (await sha256File(resolve(runRecord.dir, frame.name)) !== frame.sha256) return 'FRAME_SHA';
  }
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

const factorialSpec = JSON.parse(await readFile(factorialSpecPath, 'utf8'));
const factorialSpecSha = await sha256File(factorialSpecPath);
const cells = new Map(factorialSpec.design.cells.map(cell => [cell.id, cell]));
const runToCell = new Map(factorialSpec.design.cells.flatMap(cell => cell.runs.map(runId => [runId, cell])));
const frozen = factorialSpec.frozenIdentity;
const expectedReviewShas = new Map([[1, frozen.reviewRenderSpecSamples1Sha256], [32, frozen.reviewRenderSpecSamples32Sha256]]);
const toolIdentities = {
  rendererSha256: await sha256File(renderer),
  comparatorSha256: await sha256File(comparator),
  configuratorSha256: await sha256File(configurator),
};

if (factorialSpecSha !== 'ee6e32aaca0e9c9157e5f5b2955a89f348d8c0d6a85f5c4c43f79ae18ceaaaae') throw new Error('Factorial spec changed after pre-registration');
for (const [path, expected, label] of [
  [reviewSpecs.get(1), frozen.reviewRenderSpecSamples1Sha256, 'sample-1 ReviewRenderSpec'],
  [reviewSpecs.get(32), frozen.reviewRenderSpecSamples32Sha256, 'sample-32 ReviewRenderSpec'],
  [renderer, frozen.rendererSha256, 'renderer'],
  [comparator, frozen.comparatorSha256, 'comparator'],
  [blender, frozen.blenderSha256, 'Blender'],
]) if (await sha256File(path) !== expected) throw new Error(`${label} frozen SHA mismatch`);

const reviewSpec32 = JSON.parse(await readFile(reviewSpecs.get(32), 'utf8'));
const receiptPath = resolve(repositoryRoot, reviewSpec32.source.receiptUri);
const receipt = JSON.parse(await readFile(receiptPath, 'utf8'));
const scenePath = resolve(repositoryRoot, receipt.run.sceneBlend.uri);
const ocioPath = resolve(repositoryRoot, receipt.executionIdentity.configuration.ocio.uri);
if (await sha256File(scenePath) !== frozen.sceneBlendSha256 || await sha256File(ocioPath) !== frozen.ocioSha256) throw new Error('Scene or OCIO frozen SHA mismatch');

const runs = new Map();
for (const runId of factorialSpec.design.runOrder) {
  const cell = runToCell.get(runId);
  if (!cell) throw new Error(`Run order contains unknown run ${runId}`);
  const reviewSpecPath = reviewSpecs.get(cell.renderSamples);
  const reviewSpecSha = expectedReviewShas.get(cell.renderSamples);
  const dir = resolve(workRoot, runId);
  const renderReportPath = resolve(evidenceRoot, `${runId}.render.json`);
  const interventionPath = resolve(evidenceRoot, `${runId}.intervention.json`);
  const manifestPath = resolve(evidenceRoot, `${runId}.sequence.manifest.json`);
  await mkdir(dir, { recursive: true });
  await run(blender, [
    '--background', scenePath,
    '--disable-autoexec',
    '--python-exit-code', '1',
    '--python', configurator,
    '--python', renderer,
    '--',
    '--spec', reviewSpecPath,
    '--receipt', receiptPath,
    '--output-dir', dir,
    '--report', renderReportPath,
  ], {
    ...process.env,
    OCIO: ocioPath,
    BFS_FACTORIAL_DITHER_INTENSITY: String(cell.ditherIntensity),
    BFS_EXPECT_DITHER_INTENSITY: '1.0',
    BFS_FACTORIAL_DITHER_REPORT: interventionPath,
  });
  const report = JSON.parse(await readFile(renderReportPath, 'utf8'));
  const manifest = await makeManifest({ report, factorialSpecSha, cell, runId, reviewSpecSha, toolIdentities });
  await writeFile(manifestPath, serialize(manifest));
  const runRecord = { runId, dir, renderReportPath, interventionPath, manifestPath, manifest, report, sceneBlendSha256: frozen.sceneBlendSha256 };
  const reason = await validateRun({
    runRecord,
    cell,
    expectedFactorialSha: factorialSpecSha,
    expectedReviewSpecSha: reviewSpecSha,
    expectedRendererSha: frozen.rendererSha256,
    expectedComparatorSha: frozen.comparatorSha256,
    expectedConfiguratorSha: toolIdentities.configuratorSha256,
  });
  if (reason !== 'OK') throw new Error(`${runId} control failed: ${reason}`);
  runs.set(runId, runRecord);
  process.stdout.write(`BFS_B17_RUN_OK ${runId} samples=${cell.renderSamples} dither=${cell.ditherIntensity} seconds=${report.totalRenderSeconds}\n`);
}

const comparisons = new Map();
for (const cell of factorialSpec.design.cells) {
  const [aRunId, bRunId] = cell.runs;
  const a = runs.get(aRunId);
  const b = runs.get(bRunId);
  if (await realpath(a.dir) === await realpath(b.dir)) throw new Error(`${cell.id} run directories alias`);
  const comparisonPath = resolve(evidenceRoot, `${cell.id}.sequence.comparison.json`);
  const bindingPath = resolve(evidenceRoot, `${cell.id}.comparison.binding.json`);
  await run(blender, [
    '--factory-startup', '--background', '--python-exit-code', '1', '--python', comparator, '--',
    '--a-dir', a.dir, '--b-dir', b.dir, '--frame-start', '1', '--frame-end', '144', '--output', comparisonPath,
  ]);
  const comparison = JSON.parse(await readFile(comparisonPath, 'utf8'));
  const body = {
    documentType: 'BFS_EEVEE_FACTORIAL_COMPARISON_BINDING',
    version: '0.1.0',
    cellId: cell.id,
    aRunId,
    bRunId,
    aSequenceHash: a.manifest.sequenceHash,
    bSequenceHash: b.manifest.sequenceHash,
    comparatorSha256: frozen.comparatorSha256,
    comparisonSha256: await sha256File(comparisonPath),
  };
  const binding = { ...body, bindingHash: sha256Canonical(body) };
  await writeFile(bindingPath, serialize(binding));
  const reason = await validateComparison({ bindingPath, comparisonPath, aManifest: a.manifest, bManifest: b.manifest, expectedComparatorSha: frozen.comparatorSha256 });
  if (reason !== 'OK') throw new Error(`${cell.id} comparison control failed: ${reason}`);
  comparisons.set(cell.id, { comparison, comparisonPath, binding, bindingPath });
}

const attackBaseCell = cells.get('S01-D0');
const attackBaseRun = runs.get('S01-D0-A');
const validationDefaults = {
  runRecord: attackBaseRun,
  cell: attackBaseCell,
  expectedFactorialSha: factorialSpecSha,
  expectedReviewSpecSha: frozen.reviewRenderSpecSamples1Sha256,
  expectedRendererSha: frozen.rendererSha256,
  expectedComparatorSha: frozen.comparatorSha256,
  expectedConfiguratorSha: toolIdentities.configuratorSha256,
};
const attacks = [];
async function record(id, expected, observed) {
  attacks.push({ id, expectedReason: expected, observedReason: observed, pass: observed === expected });
}
await record('N_FACTORIAL_SPEC_SHA', 'FACTORIAL_SPEC_SHA', await validateRun({ ...validationDefaults, expectedFactorialSha: '0'.repeat(64) }));
await record('N_REVIEW_SPEC_SHA', 'REVIEW_SPEC_SHA', await validateRun({ ...validationDefaults, expectedReviewSpecSha: '0'.repeat(64) }));
await record('N_RENDERER_SHA', 'RENDERER_SHA', await validateRun({ ...validationDefaults, expectedRendererSha: '0'.repeat(64) }));
await record('N_COMPARATOR_SHA', 'COMPARATOR_SHA', await validateRun({ ...validationDefaults, expectedComparatorSha: '0'.repeat(64) }));
await record('N_CONFIGURATOR_SHA', 'CONFIGURATOR_SHA', await validateRun({ ...validationDefaults, expectedConfiguratorSha: '0'.repeat(64) }));
await record('N_DITHER_LEVEL', 'DITHER_LEVEL', await validateRun({ ...validationDefaults, expectedDither: 0.5 }));
await record('N_RENDER_SAMPLES', 'RENDER_SAMPLES', await validateRun({ ...validationDefaults, expectedRenderSamples: 2 }));
await record('N_ALIAS_RUNS', 'ALIAS_RUNS', await realpath(attackBaseRun.dir) === await realpath(attackBaseRun.dir) ? 'ALIAS_RUNS' : 'OK');

for (const [id, expected, mutate] of [
  ['N_MISSING_FRAME', 'MISSING_FRAME', async dir => unlink(resolve(dir, 'frame-0072.png'))],
  ['N_EXTRA_FRAME', 'EXTRA_FRAME', async dir => link(resolve(dir, 'frame-0001.png'), resolve(dir, 'frame-0145.png'))],
  ['N_FRAME_SHA', 'FRAME_SHA', async dir => {
    const target = resolve(dir, 'frame-0072.png');
    const temp = resolve(dir, 'frame-0072-copy.tmp');
    await copyFile(target, temp);
    await unlink(target);
    await copyFile(temp, target);
    await appendFile(target, Buffer.from([0]));
  }],
]) {
  const dir = resolve(workRoot, 'attacks', id);
  await cloneFrames(attackBaseRun.dir, dir);
  await mutate(dir);
  const attackedRun = { ...attackBaseRun, dir };
  await record(id, expected, await validateRun({ ...validationDefaults, runRecord: attackedRun }));
}

const attackComparison = comparisons.get('S01-D0');
const attackedBindingBody = structuredClone(attackComparison.binding);
delete attackedBindingBody.bindingHash;
attackedBindingBody.aSequenceHash = '0'.repeat(64);
const attackedBinding = { ...attackedBindingBody, bindingHash: sha256Canonical(attackedBindingBody) };
const attackedBindingPath = resolve(workRoot, 'attacks', 'N_COMPARISON_BINDING.json');
await writeFile(attackedBindingPath, serialize(attackedBinding));
await record('N_COMPARISON_BINDING', 'COMPARISON_SEQUENCE_BINDING', await validateComparison({
  bindingPath: attackedBindingPath,
  comparisonPath: attackComparison.comparisonPath,
  aManifest: runs.get('S01-D0-A').manifest,
  bManifest: runs.get('S01-D0-B').manifest,
  expectedComparatorSha: frozen.comparatorSha256,
}));

const cellResults = Object.fromEntries(factorialSpec.design.cells.map(cell => {
  const comparisonRecord = comparisons.get(cell.id);
  const comparison = comparisonRecord.comparison;
  const exact = comparison.decodedPixelExactFrames === 144 && comparison.maximumAbsoluteError === 0 && comparison.totalFailurePixels === 0;
  const [aRunId, bRunId] = cell.runs;
  return [cell.id, {
    factors: { renderSamples: cell.renderSamples, ditherIntensity: cell.ditherIntensity },
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

const validExperiment = attacks.length === 12 && attacks.every(attack => attack.pass);
const sample1BothExact = cellResults['S01-D0'].exactDecodedPixels && cellResults['S01-D1'].exactDecodedPixels;
const sample1BothNonExact = !cellResults['S01-D0'].exactDecodedPixels && !cellResults['S01-D1'].exactDecodedPixels;
const sample32BothNonExact = !cellResults['S32-D0'].exactDecodedPixels && !cellResults['S32-D1'].exactDecodedPixels;
let decision = 'MIXED_OR_BASELINE_UNSTABLE';
if (!validExperiment) decision = 'INVALID_EXPERIMENT';
else if (sample1BothExact && sample32BothNonExact) decision = 'SAMPLING_CAUSAL_SUPPORT';
else if (sample1BothNonExact && sample32BothNonExact) decision = 'SAMPLING_NOT_SUFFICIENT';

const result = {
  documentType: 'BFS_B17_EEVEE_SAMPLING_FACTORIAL_EXPERIMENT',
  version: '0.1.0',
  executedAtUtc: new Date().toISOString(),
  decision,
  validExperiment,
  design: { ...factorialSpec.design, renderedFrames: 8 * 144 },
  identities: { ...frozen, factorialSpecSha256: factorialSpecSha, configuratorSha256: toolIdentities.configuratorSha256 },
  historicalEvidence: factorialSpec.historicalEvidence,
  cells: cellResults,
  attacks,
  artifacts: Object.fromEntries(factorialSpec.design.cells.map(cell => [cell.id, {
    comparison: repoUri(comparisons.get(cell.id).comparisonPath),
    comparisonBinding: repoUri(comparisons.get(cell.id).bindingPath),
    aManifest: repoUri(runs.get(cell.runs[0]).manifestPath),
    bManifest: repoUri(runs.get(cell.runs[1]).manifestPath),
  }])),
  nonClaims: factorialSpec.explicitNonClaims,
};
await writeFile(resolve(root, 'results.json'), serialize(result));
process.stdout.write(`BFS_B17_EEVEE_FACTORIAL ${decision} ` + factorialSpec.design.cells.map(cell => `${cell.id}=${cellResults[cell.id].decodedPixelExactFrames}/144`).join(' ') + ` attacks=${attacks.filter(attack => attack.pass).length}/12\n`);
if (!validExperiment) process.exitCode = 1;
