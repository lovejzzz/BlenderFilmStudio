import { appendFile, copyFile, link, mkdir, readFile, readdir, realpath, rm, unlink, writeFile } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { relative, resolve, sep } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256Canonical, sha256File } from './lib/receipt-format.mjs';

const root = resolve(repositoryRoot, 'experiments/eevee-gi-reprojection-factorial-v0-1');
const evidenceRoot = resolve(root, 'evidence');
const workRoot = resolve(root, 'work');
const factorialSpecPath = resolve(repositoryRoot, 'specs/eevee-gi-reprojection-factorial-spec.v0.1.json');
const reviewSpecPath = resolve(repositoryRoot, 'specs/review-render-spec.v0.1.json');
const renderer = resolve(repositoryRoot, 'blender/render_review_sequence.py');
const comparator = resolve(repositoryRoot, 'blender/compare_review_sequences.py');
const configurator = resolve(repositoryRoot, 'blender/configure_gi_reprojection_factorial.py');
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

async function pngNames(dir) { return (await readdir(dir)).filter(name => name.endsWith('.png')).sort(); }

async function makeManifest({ report, factorialSpecSha, cell, runId, configuratorSha }) {
  const body = {
    documentType: 'BFS_GI_REPROJECTION_FACTORIAL_SEQUENCE', version: '0.1.0', runId, cellId: cell.id,
    factors: { useFastGi: cell.useFastGi, useTaaReprojection: cell.useTaaReprojection },
    constants: { renderSamples: 32, ditherIntensity: 0 },
    frameCount: report.frameCount, frameStart: 1, frameEnd: 144, resolution: [960, 540],
    factorialSpecSha256: factorialSpecSha,
    toolIdentities: { rendererSha256: await sha256File(renderer), comparatorSha256: await sha256File(comparator), configuratorSha256: configuratorSha },
    frames: report.frames.map(({ frame, name, sha256, bytes }) => ({ frame, name, sha256, bytes })),
  };
  return { ...body, sequenceHash: sha256Canonical(body) };
}

async function validateRun({
  runRecord, cell, expectedFactorialSha, expectedReviewSpecSha, expectedRendererSha,
  expectedComparatorSha, expectedConfiguratorSha, expectedDither = 0,
  expectedFastGi = cell.useFastGi, expectedReprojection = cell.useTaaReprojection, expectedRenderSamples = 32,
}) {
  if (await sha256File(factorialSpecPath) !== expectedFactorialSha) return 'FACTORIAL_SPEC_SHA';
  if (await sha256File(reviewSpecPath) !== expectedReviewSpecSha) return 'REVIEW_SPEC_SHA';
  if (await sha256File(renderer) !== expectedRendererSha) return 'RENDERER_SHA';
  if (await sha256File(comparator) !== expectedComparatorSha) return 'COMPARATOR_SHA';
  if (await sha256File(configurator) !== expectedConfiguratorSha) return 'CONFIGURATOR_SHA';
  if (expectedDither !== 0) return 'FIXED_DITHER';

  const intervention = JSON.parse(await readFile(runRecord.interventionPath, 'utf8'));
  const expectedBefore = { ditherIntensity: 1, useFastGi: true, useTaaReprojection: true };
  const expectedAfter = { ditherIntensity: expectedDither, useFastGi: expectedFastGi, useTaaReprojection: expectedReprojection };
  if (JSON.stringify(intervention.before) !== JSON.stringify(expectedBefore)) return 'SOURCE_CONTROLS';
  if (intervention.requested.ditherIntensity !== expectedDither || intervention.after.ditherIntensity !== expectedDither) return 'FIXED_DITHER';
  if (intervention.requested.useFastGi !== expectedFastGi || intervention.after.useFastGi !== expectedFastGi) return 'FAST_GI';
  if (intervention.requested.useTaaReprojection !== expectedReprojection || intervention.after.useTaaReprojection !== expectedReprojection) return 'TAA_REPROJECTION';
  if (intervention.savedSourceBlend !== false || intervention.sceneBlendSha256 !== runRecord.sceneBlendSha256) return 'SOURCE_BLEND';

  const report = JSON.parse(await readFile(runRecord.renderReportPath, 'utf8'));
  if (report.runtime.renderSamples !== expectedRenderSamples || report.profile.renderSamples !== expectedRenderSamples) return 'RENDER_SAMPLES';
  if (report.frameCount !== 144) return 'FRAME_COUNT';
  if (report.cameraAndTimelineInvariant !== true) return 'CAMERA_TIMELINE_INVARIANT';
  if (report.source.sceneBlendSha256 !== runRecord.sceneBlendSha256) return 'RENDER_SCENE_SHA';

  const manifest = JSON.parse(await readFile(runRecord.manifestPath, 'utf8'));
  const body = structuredClone(manifest); delete body.sequenceHash;
  if (sha256Canonical(body) !== manifest.sequenceHash) return 'MANIFEST_SELF_HASH';
  if (manifest.runId !== runRecord.runId || manifest.cellId !== cell.id) return 'MANIFEST_RUN_BINDING';
  if (manifest.factors.useFastGi !== cell.useFastGi || manifest.factors.useTaaReprojection !== cell.useTaaReprojection) return 'MANIFEST_FACTORS';
  if (manifest.factorialSpecSha256 !== expectedFactorialSha) return 'MANIFEST_SPEC_BINDING';
  const expectedNames = manifest.frames.map(frame => frame.name), observedNames = await pngNames(runRecord.dir);
  if (expectedNames.some(name => !observedNames.includes(name))) return 'MISSING_FRAME';
  if (observedNames.some(name => !expectedNames.includes(name))) return 'EXTRA_FRAME';
  for (const frame of manifest.frames) if (await sha256File(resolve(runRecord.dir, frame.name)) !== frame.sha256) return 'FRAME_SHA';
  return 'OK';
}

async function validateComparison({ bindingPath, comparisonPath, aManifest, bManifest, expectedComparatorSha }) {
  if (await sha256File(comparator) !== expectedComparatorSha) return 'COMPARATOR_SHA';
  const binding = JSON.parse(await readFile(bindingPath, 'utf8'));
  const body = structuredClone(binding); delete body.bindingHash;
  if (sha256Canonical(body) !== binding.bindingHash) return 'COMPARISON_SELF_HASH';
  if (binding.aSequenceHash !== aManifest.sequenceHash || binding.bSequenceHash !== bManifest.sequenceHash) return 'COMPARISON_SEQUENCE_BINDING';
  if (binding.comparisonSha256 !== await sha256File(comparisonPath)) return 'COMPARISON_SHA';
  const comparison = JSON.parse(await readFile(comparisonPath, 'utf8'));
  if (comparison.frameCount !== 144 || comparison.frames.length !== 144) return 'COMPARISON_FRAME_COUNT';
  for (let index = 0; index < 144; index += 1) if (comparison.frames[index].aSha256 !== aManifest.frames[index].sha256 || comparison.frames[index].bSha256 !== bManifest.frames[index].sha256) return 'COMPARISON_FRAME_BINDING';
  return 'OK';
}

async function cloneFrames(source, target) { await mkdir(target, { recursive: true }); for (const name of await pngNames(source)) await link(resolve(source, name), resolve(target, name)); }

await rm(evidenceRoot, { recursive: true, force: true }); await rm(workRoot, { recursive: true, force: true }); await mkdir(evidenceRoot, { recursive: true });
const factorialSpec = JSON.parse(await readFile(factorialSpecPath, 'utf8'));
const factorialSpecSha = await sha256File(factorialSpecPath);
if (factorialSpecSha !== '0056dde1313c58845bc18923a31b3f99c8470a8c097924bef41992e6d137737d') throw new Error('Factorial spec changed after pre-registration');
const frozen = factorialSpec.frozenIdentity;
const cells = new Map(factorialSpec.design.cells.map(cell => [cell.id, cell]));
const runToCell = new Map(factorialSpec.design.cells.flatMap(cell => cell.runs.map(runId => [runId, cell])));
const configuratorSha = await sha256File(configurator);
for (const [path, expected, label] of [[reviewSpecPath, frozen.reviewRenderSpecSha256, 'ReviewRenderSpec'], [renderer, frozen.rendererSha256, 'renderer'], [comparator, frozen.comparatorSha256, 'comparator'], [blender, frozen.blenderSha256, 'Blender']]) if (await sha256File(path) !== expected) throw new Error(`${label} frozen SHA mismatch`);
const reviewSpec = JSON.parse(await readFile(reviewSpecPath, 'utf8'));
const receiptPath = resolve(repositoryRoot, reviewSpec.source.receiptUri), receipt = JSON.parse(await readFile(receiptPath, 'utf8'));
const scenePath = resolve(repositoryRoot, receipt.run.sceneBlend.uri), ocioPath = resolve(repositoryRoot, receipt.executionIdentity.configuration.ocio.uri);
if (await sha256File(scenePath) !== frozen.sceneBlendSha256 || await sha256File(ocioPath) !== frozen.ocioSha256) throw new Error('Scene or OCIO frozen SHA mismatch');

const runs = new Map();
for (const runId of factorialSpec.design.runOrder) {
  const cell = runToCell.get(runId); if (!cell) throw new Error(`Unknown run ${runId}`);
  const dir = resolve(workRoot, runId), renderReportPath = resolve(evidenceRoot, `${runId}.render.json`), interventionPath = resolve(evidenceRoot, `${runId}.intervention.json`), manifestPath = resolve(evidenceRoot, `${runId}.sequence.manifest.json`);
  await mkdir(dir, { recursive: true });
  await run(blender, ['--background', scenePath, '--disable-autoexec', '--python-exit-code', '1', '--python', configurator, '--python', renderer, '--', '--spec', reviewSpecPath, '--receipt', receiptPath, '--output-dir', dir, '--report', renderReportPath], {
    ...process.env, OCIO: ocioPath,
    BFS_B19_DITHER: '0.0', BFS_B19_FAST_GI: cell.useFastGi ? '1' : '0', BFS_B19_REPROJECTION: cell.useTaaReprojection ? '1' : '0', BFS_B19_INTERVENTION_REPORT: interventionPath,
  });
  const report = JSON.parse(await readFile(renderReportPath, 'utf8'));
  const manifest = await makeManifest({ report, factorialSpecSha, cell, runId, configuratorSha }); await writeFile(manifestPath, serialize(manifest));
  const runRecord = { runId, dir, renderReportPath, interventionPath, manifestPath, manifest, report, sceneBlendSha256: frozen.sceneBlendSha256 };
  const reason = await validateRun({ runRecord, cell, expectedFactorialSha: factorialSpecSha, expectedReviewSpecSha: frozen.reviewRenderSpecSha256, expectedRendererSha: frozen.rendererSha256, expectedComparatorSha: frozen.comparatorSha256, expectedConfiguratorSha: configuratorSha });
  if (reason !== 'OK') throw new Error(`${runId} control failed: ${reason}`);
  runs.set(runId, runRecord); process.stdout.write(`BFS_B19_RUN_OK ${runId} gi=${cell.useFastGi} reprojection=${cell.useTaaReprojection} seconds=${report.totalRenderSeconds}\n`);
}

const comparisons = new Map();
for (const cell of factorialSpec.design.cells) {
  const [aRunId, bRunId] = cell.runs, a = runs.get(aRunId), b = runs.get(bRunId);
  if (await realpath(a.dir) === await realpath(b.dir)) throw new Error(`${cell.id} run directories alias`);
  const comparisonPath = resolve(evidenceRoot, `${cell.id}.sequence.comparison.json`), bindingPath = resolve(evidenceRoot, `${cell.id}.comparison.binding.json`);
  await run(blender, ['--factory-startup', '--background', '--python-exit-code', '1', '--python', comparator, '--', '--a-dir', a.dir, '--b-dir', b.dir, '--frame-start', '1', '--frame-end', '144', '--output', comparisonPath]);
  const comparison = JSON.parse(await readFile(comparisonPath, 'utf8'));
  const body = { documentType: 'BFS_GI_REPROJECTION_COMPARISON_BINDING', version: '0.1.0', cellId: cell.id, aRunId, bRunId, aSequenceHash: a.manifest.sequenceHash, bSequenceHash: b.manifest.sequenceHash, comparatorSha256: frozen.comparatorSha256, comparisonSha256: await sha256File(comparisonPath) };
  const binding = { ...body, bindingHash: sha256Canonical(body) }; await writeFile(bindingPath, serialize(binding));
  const reason = await validateComparison({ bindingPath, comparisonPath, aManifest: a.manifest, bManifest: b.manifest, expectedComparatorSha: frozen.comparatorSha256 }); if (reason !== 'OK') throw new Error(`${cell.id} comparison failed: ${reason}`);
  comparisons.set(cell.id, { comparison, comparisonPath, binding, bindingPath });
}

const attackCell = cells.get('G1-R1'), attackRun = runs.get('G1-R1-A');
const defaults = { runRecord: attackRun, cell: attackCell, expectedFactorialSha: factorialSpecSha, expectedReviewSpecSha: frozen.reviewRenderSpecSha256, expectedRendererSha: frozen.rendererSha256, expectedComparatorSha: frozen.comparatorSha256, expectedConfiguratorSha: configuratorSha };
const attacks = []; async function record(id, expected, observed) { attacks.push({ id, expectedReason: expected, observedReason: observed, pass: observed === expected }); }
await record('N_FACTORIAL_SPEC_SHA', 'FACTORIAL_SPEC_SHA', await validateRun({ ...defaults, expectedFactorialSha: '0'.repeat(64) }));
await record('N_REVIEW_SPEC_SHA', 'REVIEW_SPEC_SHA', await validateRun({ ...defaults, expectedReviewSpecSha: '0'.repeat(64) }));
await record('N_RENDERER_SHA', 'RENDERER_SHA', await validateRun({ ...defaults, expectedRendererSha: '0'.repeat(64) }));
await record('N_COMPARATOR_SHA', 'COMPARATOR_SHA', await validateRun({ ...defaults, expectedComparatorSha: '0'.repeat(64) }));
await record('N_CONFIGURATOR_SHA', 'CONFIGURATOR_SHA', await validateRun({ ...defaults, expectedConfiguratorSha: '0'.repeat(64) }));
await record('N_FIXED_DITHER', 'FIXED_DITHER', await validateRun({ ...defaults, expectedDither: 1 }));
await record('N_FAST_GI', 'FAST_GI', await validateRun({ ...defaults, expectedFastGi: false }));
await record('N_TAA_REPROJECTION', 'TAA_REPROJECTION', await validateRun({ ...defaults, expectedReprojection: false }));
await record('N_RENDER_SAMPLES', 'RENDER_SAMPLES', await validateRun({ ...defaults, expectedRenderSamples: 31 }));
await record('N_ALIAS_RUNS', 'ALIAS_RUNS', await realpath(attackRun.dir) === await realpath(attackRun.dir) ? 'ALIAS_RUNS' : 'OK');
for (const [id, expected, mutate] of [
  ['N_MISSING_FRAME', 'MISSING_FRAME', async dir => unlink(resolve(dir, 'frame-0072.png'))],
  ['N_EXTRA_FRAME', 'EXTRA_FRAME', async dir => link(resolve(dir, 'frame-0001.png'), resolve(dir, 'frame-0145.png'))],
  ['N_FRAME_SHA', 'FRAME_SHA', async dir => { const target = resolve(dir, 'frame-0072.png'), temp = resolve(dir, 'frame-copy.tmp'); await copyFile(target, temp); await unlink(target); await copyFile(temp, target); await appendFile(target, Buffer.from([0])); }],
]) { const dir = resolve(workRoot, 'attacks', id); await cloneFrames(attackRun.dir, dir); await mutate(dir); await record(id, expected, await validateRun({ ...defaults, runRecord: { ...attackRun, dir } })); }
const baseComparison = comparisons.get('G1-R1');
const attackedBody = structuredClone(baseComparison.binding); delete attackedBody.bindingHash; attackedBody.aSequenceHash = '0'.repeat(64);
const attackedBinding = { ...attackedBody, bindingHash: sha256Canonical(attackedBody) }, attackedBindingPath = resolve(workRoot, 'attacks', 'N_COMPARISON_BINDING.json'); await writeFile(attackedBindingPath, serialize(attackedBinding));
await record('N_COMPARISON_BINDING', 'COMPARISON_SEQUENCE_BINDING', await validateComparison({ bindingPath: attackedBindingPath, comparisonPath: baseComparison.comparisonPath, aManifest: runs.get('G1-R1-A').manifest, bManifest: runs.get('G1-R1-B').manifest, expectedComparatorSha: frozen.comparatorSha256 }));

const cellResults = Object.fromEntries(factorialSpec.design.cells.map(cell => {
  const record = comparisons.get(cell.id), c = record.comparison, [aRunId, bRunId] = cell.runs;
  const exact = c.decodedPixelExactFrames === 144 && c.maximumAbsoluteError === 0 && c.totalFailurePixels === 0;
  return [cell.id, { factors: { useFastGi: cell.useFastGi, useTaaReprojection: cell.useTaaReprojection }, exactDecodedPixels: exact, containerExactFrames: c.containerExactFrames, decodedPixelExactFrames: c.decodedPixelExactFrames, maximumAbsoluteError: c.maximumAbsoluteError, totalFailurePixels: c.totalFailurePixels, worstFrame: c.worstFrame.frame, aSequenceHash: runs.get(aRunId).manifest.sequenceHash, bSequenceHash: runs.get(bRunId).manifest.sequenceHash, aRenderSeconds: runs.get(aRunId).report.totalRenderSeconds, bRenderSeconds: runs.get(bRunId).report.totalRenderSeconds, comparisonBindingHash: record.binding.bindingHash }];
}));
const e11 = cellResults['G1-R1'].exactDecodedPixels, e01 = cellResults['G0-R1'].exactDecodedPixels, e10 = cellResults['G1-R0'].exactDecodedPixels, e00 = cellResults['G0-R0'].exactDecodedPixels;
const validExperiment = attacks.length === 14 && attacks.every(attack => attack.pass);
let decision = 'BASELINE_UNSTABLE_OR_MIXED';
if (!validExperiment) decision = 'INVALID_EXPERIMENT';
else if (e01 && e00 && !e11 && !e10) decision = 'FAST_GI_CAUSAL_SUPPORT';
else if (e10 && e00 && !e11 && !e01) decision = 'REPROJECTION_CAUSAL_SUPPORT';
else if (e00 && !e11 && !e01 && !e10) decision = 'JOINT_DISABLE_SUPPORT';
else if (!e11 && e01 && e10 && e00) decision = 'EITHER_DISABLE_SUPPORT';
else if (!e11 && !e01 && !e10 && !e00) decision = 'NO_SUFFICIENT_INTERVENTION';
const result = { documentType: 'BFS_B19_GI_REPROJECTION_FACTORIAL_EXPERIMENT', version: '0.1.0', executedAtUtc: new Date().toISOString(), decision, validExperiment, exactnessPattern: { 'G1-R1': e11, 'G0-R1': e01, 'G1-R0': e10, 'G0-R0': e00 }, design: { ...factorialSpec.design, renderedFrames: 8 * 144 }, identities: { ...frozen, factorialSpecSha256: factorialSpecSha, configuratorSha256: configuratorSha }, evidenceBasis: factorialSpec.evidenceBasis, cells: cellResults, attacks, artifacts: Object.fromEntries(factorialSpec.design.cells.map(cell => [cell.id, { comparison: repoUri(comparisons.get(cell.id).comparisonPath), comparisonBinding: repoUri(comparisons.get(cell.id).bindingPath), aManifest: repoUri(runs.get(cell.runs[0]).manifestPath), bManifest: repoUri(runs.get(cell.runs[1]).manifestPath) }])), nonClaims: factorialSpec.explicitNonClaims };
await writeFile(resolve(root, 'results.json'), serialize(result));
process.stdout.write(`BFS_B19_GI_REPROJECTION ${decision} ` + factorialSpec.design.cells.map(cell => `${cell.id}=${cellResults[cell.id].decodedPixelExactFrames}/144`).join(' ') + ` attacks=${attacks.filter(attack => attack.pass).length}/14\n`);
if (!validExperiment) process.exitCode = 1;
