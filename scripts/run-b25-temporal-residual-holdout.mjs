import { mkdir, readFile, readdir, rm, writeFile } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { relative, resolve, sep } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256Canonical, sha256File } from './lib/receipt-format.mjs';

const root = resolve(repositoryRoot, 'experiments/temporal-residual-holdout-v0-1');
const evidenceRoot = resolve(root, 'evidence');
const workRoot = resolve(root, 'work');
const specPath = resolve(repositoryRoot, 'specs/temporal-residual-holdout-spec.v0.1.json');
const derivationPath = resolve(repositoryRoot, 'experiments/temporal-residual-derivation-v0-1/results.json');
const b24Path = resolve(repositoryRoot, 'experiments/production-tolerance-holdout-v0-1/results.json');
const reviewSpecPath = resolve(repositoryRoot, 'specs/review-render-spec.v0.1.json');
const configurator = resolve(repositoryRoot, 'blender/configure_eevee_threads.py');
const renderer = resolve(repositoryRoot, 'blender/render_review_sequence.py');
const comparator = resolve(repositoryRoot, 'blender/compare_b25_temporal_residual.py');
const runner = fileURLToPath(import.meta.url);
const blender = resolve(process.env.BLENDER_BIN || '/Applications/Blender.app/Contents/MacOS/Blender');
const serialize = value => `${JSON.stringify(value, null, 2)}\n`;
const repoUri = path => relative(repositoryRoot, path).split(sep).join('/');

function run(command, args, env = process.env) {
  return new Promise((resolvePromise, reject) => {
    const child = spawn(command, args, { cwd: repositoryRoot, env, stdio: ['ignore', 'pipe', 'pipe'] });
    const processId = child.pid;
    let output = '';
    child.stdout.on('data', chunk => { output += chunk; });
    child.stderr.on('data', chunk => { output += chunk; });
    child.on('error', reject);
    child.on('close', code => code === 0
      ? resolvePromise({ processId, output })
      : reject(new Error(`${command} failed (${code}) pid=${processId}\n${output}`)));
  });
}

async function pngNames(dir) { return (await readdir(dir)).filter(name => name.endsWith('.png')).sort(); }

async function makeManifest({ replicate, processId, report, specSha, tools }) {
  const body = {
    documentType: 'BFS_B25_TEMPORAL_HOLDOUT_SEQUENCE', version: '0.1.0', replicate, processId,
    b25SpecSha256: specSha, frameStart: 1, frameEnd: 144, frameCount: report.frameCount,
    constants: { renderSamples: 32, ditherIntensity: 0, useFastGi: true, useTaaReprojection: true, threadsMode: 'FIXED', threads: 8 },
    source: report.source, runtime: report.runtime, toolIdentities: tools,
    frames: report.frames.map(({ frame, name, sha256, bytes }) => ({ frame, name, sha256, bytes })),
  };
  return { ...body, sequenceHash: sha256Canonical(body) };
}

async function validateRun({
  record, spec, expectedSpecSha, expectedDerivationSha, expectedB24Sha, expectedReviewSpecSha,
  expectedBlenderSha, expectedOcioSha, expectedSceneSha, expectedPlanHash, expectedStructureHash,
  expectedConfiguratorSha, expectedRendererSha, expectedReplicate = record.replicate,
  expectedProcessId = record.processId, expectedFrameCount = 144, expectedWidth = 960,
  expectedAfterDither = 0, expectedFirstFrameSha = record.manifest.frames[0].sha256,
}) {
  if (await sha256File(specPath) !== expectedSpecSha) return 'B25_SPEC_SHA';
  if (await sha256File(derivationPath) !== expectedDerivationSha) return 'DERIVATION_SHA';
  if (await sha256File(b24Path) !== expectedB24Sha) return 'B24_RESULT_SHA';
  if (await sha256File(reviewSpecPath) !== expectedReviewSpecSha) return 'REVIEW_SPEC_SHA';
  if (await sha256File(blender) !== expectedBlenderSha) return 'BLENDER_SHA';
  if (await sha256File(record.ocioPath) !== expectedOcioSha) return 'OCIO_SHA';
  if (await sha256File(record.scenePath) !== expectedSceneSha) return 'SCENE_SHA';
  if (await sha256File(configurator) !== expectedConfiguratorSha) return 'CONFIGURATOR_SHA';
  if (await sha256File(renderer) !== expectedRendererSha) return 'RENDERER_SHA';

  const report = JSON.parse(await readFile(record.reportPath, 'utf8'));
  if (report.source.planHash !== expectedPlanHash || report.source.structureHash !== expectedStructureHash) return 'PLAN_OR_STRUCTURE_HASH';
  const intervention = JSON.parse(await readFile(record.interventionPath, 'utf8'));
  if (intervention.before.threadsMode !== 'FIXED' || intervention.before.threads !== 8 || intervention.before.ditherIntensity !== 1
      || intervention.before.useFastGi !== true || intervention.before.useTaaReprojection !== true
      || intervention.after.threadsMode !== 'FIXED' || intervention.after.threads !== 8 || intervention.after.ditherIntensity !== expectedAfterDither
      || intervention.after.useFastGi !== true || intervention.after.useTaaReprojection !== true
      || intervention.savedSourceBlend !== false) return 'SOURCE_OR_FIXED_CONTROLS';

  const manifest = JSON.parse(await readFile(record.manifestPath, 'utf8'));
  const body = structuredClone(manifest); delete body.sequenceHash;
  if (sha256Canonical(body) !== manifest.sequenceHash) return 'MANIFEST_SELF_HASH';
  if (manifest.replicate !== expectedReplicate || manifest.processId !== expectedProcessId) return 'PROCESS_REPLICATE_BINDING';
  if (manifest.b25SpecSha256 !== expectedSpecSha || JSON.stringify(manifest.toolIdentities) !== JSON.stringify(record.tools)) return 'MANIFEST_TOOL_BINDING';
  if (report.frameCount !== expectedFrameCount || manifest.frameCount !== expectedFrameCount || report.frames.length !== expectedFrameCount) return 'FRAME_ORDER_OR_COUNT';
  const expectedFrames = Array.from({ length: expectedFrameCount }, (_, index) => index + 1);
  if (JSON.stringify(report.frames.map(frame => frame.frame)) !== JSON.stringify(expectedFrames)
      || JSON.stringify(manifest.frames.map(frame => frame.frame)) !== JSON.stringify(expectedFrames)) return 'FRAME_ORDER_OR_COUNT';
  if (report.runtime.renderSamples !== 32 || report.profile.renderSamples !== 32 || report.cameraAndTimelineInvariant !== true
      || report.source.sceneBlendSha256 !== expectedSceneSha) return 'SOURCE_OR_FIXED_CONTROLS';
  if (report.profile.width !== expectedWidth || report.profile.height !== 540 || report.profile.imageFormat !== 'PNG'
      || report.profile.colorDepth !== '8' || report.profile.colorMode !== 'RGBA') return 'PNG_LAYOUT';
  const names = await pngNames(record.dir);
  if (names.length !== 144) return 'MISSING_OR_MUTATED_OUTPUT';
  for (const frame of manifest.frames) {
    if (!names.includes(frame.name)) return 'MISSING_OR_MUTATED_OUTPUT';
    try { if (await sha256File(resolve(record.dir, frame.name)) !== frame.sha256) return 'MISSING_OR_MUTATED_OUTPUT'; }
    catch { return 'MISSING_OR_MUTATED_OUTPUT'; }
  }
  if (manifest.frames[0].sha256 !== expectedFirstFrameSha) return 'MISSING_OR_MUTATED_OUTPUT';
  if (spec.executionContract.humanReviewMustRemainPending !== true) return 'HUMAN_REVIEW_STATUS';
  return 'OK';
}

async function validateComparison({ item, aManifest, bManifest, expectedComparatorSha, expectedStaticEnvelope, expectedTemporalEnvelope }) {
  if (await sha256File(comparator) !== expectedComparatorSha) return 'COMPARATOR_SHA';
  const binding = JSON.parse(await readFile(item.bindingPath, 'utf8'));
  const body = structuredClone(binding); delete body.bindingHash;
  if (sha256Canonical(body) !== binding.bindingHash) return 'COMPARISON_SELF_HASH';
  if (binding.aSequenceHash !== aManifest.sequenceHash || binding.bSequenceHash !== bManifest.sequenceHash
      || binding.comparisonSha256 !== await sha256File(item.comparisonPath)) return 'COMPARISON_BINDING';
  const comparison = JSON.parse(await readFile(item.comparisonPath, 'utf8'));
  if (comparison.frameCount !== 144 || comparison.transitionCount !== 143) return 'FRAME_ORDER_OR_COUNT';
  if (sha256Canonical(comparison.frozenStaticEnvelope) !== sha256Canonical(expectedStaticEnvelope)
      || sha256Canonical(comparison.frozenTemporalEnvelope) !== sha256Canonical(expectedTemporalEnvelope)) return 'ENVELOPE_MUTATION';
  for (let index = 0; index < 144; index += 1) {
    if (comparison.frames[index].frame !== index + 1 || comparison.frames[index].aSha256 !== aManifest.frames[index].sha256
        || comparison.frames[index].bSha256 !== bManifest.frames[index].sha256) return 'COMPARISON_BINDING';
  }
  return 'OK';
}

await rm(evidenceRoot, { recursive: true, force: true });
await rm(workRoot, { recursive: true, force: true });
await mkdir(evidenceRoot, { recursive: true });
const spec = JSON.parse(await readFile(specPath, 'utf8'));
const specSha = await sha256File(specPath);
if (specSha !== 'b94c70418d1453162c4eb07ee54912358212f6e3bee7ef0c30e2f78a0f214368') throw new Error('B25 spec changed after pre-registration');
const derivation = JSON.parse(await readFile(derivationPath, 'utf8'));
const b24 = JSON.parse(await readFile(b24Path, 'utf8'));
if (derivation.status !== 'DERIVATION_ONLY_NOT_VALIDATION' || b24.decision !== spec.evidenceBasis.b24Decision) throw new Error('Evidence basis mismatch');
const reviewSpec = JSON.parse(await readFile(reviewSpecPath, 'utf8'));
const receiptPath = resolve(repositoryRoot, reviewSpec.source.receiptUri);
const receipt = JSON.parse(await readFile(receiptPath, 'utf8'));
const scenePath = resolve(repositoryRoot, receipt.run.sceneBlend.uri);
const ocioPath = resolve(repositoryRoot, receipt.executionIdentity.configuration.ocio.uri);
const frozen = spec.frozenIdentity;
for (const [path, expected, label] of [
  [derivationPath, spec.evidenceBasis.derivationResultSha256, 'derivation'], [b24Path, spec.evidenceBasis.b24ResultsSha256, 'B24'],
  [reviewSpecPath, frozen.reviewRenderSpecSha256, 'ReviewRenderSpec'], [blender, frozen.blenderSha256, 'Blender'],
  [ocioPath, frozen.ocioSha256, 'OCIO'], [scenePath, frozen.sceneBlendSha256, 'scene'],
  [configurator, frozen.configuratorSha256, 'configurator'], [renderer, frozen.rendererSha256, 'renderer'],
]) if (await sha256File(path) !== expected) throw new Error(`${label} frozen SHA mismatch`);
const tools = { configuratorSha256: await sha256File(configurator), rendererSha256: await sha256File(renderer), comparatorSha256: await sha256File(comparator), runnerSha256: await sha256File(runner) };
const runs = new Map();
for (const replicate of spec.design.processOrder) {
  const dir = resolve(workRoot, replicate), reportPath = resolve(evidenceRoot, `${replicate}.render.json`), interventionPath = resolve(evidenceRoot, `${replicate}.intervention.json`), manifestPath = resolve(evidenceRoot, `${replicate}.manifest.json`);
  await mkdir(dir, { recursive: true });
  const launched = await run(blender, ['--background', scenePath, '--disable-autoexec', '--python-exit-code', '1', '--python', configurator, '--python', renderer, '--', '--spec', reviewSpecPath, '--receipt', receiptPath, '--output-dir', dir, '--report', reportPath], {
    ...process.env, OCIO: ocioPath, BFS_B22_THREADS_MODE: 'FIXED', BFS_B22_THREADS: '8', BFS_B22_CELL: 'T08', BFS_B22_INTERVENTION_REPORT: interventionPath,
  });
  const report = JSON.parse(await readFile(reportPath, 'utf8'));
  const manifest = await makeManifest({ replicate, processId: launched.processId, report, specSha, tools });
  await writeFile(manifestPath, serialize(manifest));
  const record = { replicate, processId: launched.processId, dir, reportPath, interventionPath, manifestPath, manifest, report, tools, scenePath, ocioPath };
  const reason = await validateRun({ record, spec, expectedSpecSha: specSha, expectedDerivationSha: spec.evidenceBasis.derivationResultSha256, expectedB24Sha: spec.evidenceBasis.b24ResultsSha256, expectedReviewSpecSha: frozen.reviewRenderSpecSha256, expectedBlenderSha: frozen.blenderSha256, expectedOcioSha: frozen.ocioSha256, expectedSceneSha: frozen.sceneBlendSha256, expectedPlanHash: frozen.planHash, expectedStructureHash: frozen.structureHash, expectedConfiguratorSha: frozen.configuratorSha256, expectedRendererSha: frozen.rendererSha256 });
  if (reason !== 'OK') throw new Error(`${replicate} validation failed: ${reason}`);
  runs.set(replicate, record);
  process.stdout.write(`BFS_B25_RUN_OK ${replicate} pid=${record.processId} seconds=${report.totalRenderSeconds}\n`);
}
if (new Set([...runs.values()].map(record => record.processId)).size !== 3) throw new Error('Render PIDs are not unique');

const ledgerBody = { documentType: 'BFS_B25_PROCESS_LEDGER', version: '0.1.0', b25SpecSha256: specSha, processes: [...runs.values()].map(record => ({ replicate: record.replicate, processId: record.processId, manifestHash: record.manifest.sequenceHash })) };
const ledger = { ...ledgerBody, ledgerHash: sha256Canonical(ledgerBody) };
const ledgerPath = resolve(evidenceRoot, 'process-ledger.json'); await writeFile(ledgerPath, serialize(ledger));

const comparisons = new Map();
for (const pair of spec.holdout.replicatePairs) {
  const [aId, bId] = pair.split('-'), a = runs.get(aId), b = runs.get(bId);
  const comparisonPath = resolve(evidenceRoot, `${pair}.comparison.json`), bindingPath = resolve(evidenceRoot, `${pair}.binding.json`);
  await run(blender, ['--factory-startup', '--background', '--python-exit-code', '1', '--python', comparator, '--', '--a-dir', a.dir, '--b-dir', b.dir, '--frame-start', '1', '--frame-end', '144', '--static-envelope', JSON.stringify(spec.frozenStaticEnvelope), '--temporal-envelope', JSON.stringify(spec.frozenTemporalEnvelope), '--output', comparisonPath]);
  const comparison = JSON.parse(await readFile(comparisonPath, 'utf8'));
  const body = { documentType: 'BFS_B25_COMPARISON_BINDING', version: '0.1.0', pair, aReplicate: aId, bReplicate: bId, aSequenceHash: a.manifest.sequenceHash, bSequenceHash: b.manifest.sequenceHash, comparatorSha256: tools.comparatorSha256, staticEnvelopeHash: sha256Canonical(spec.frozenStaticEnvelope), temporalEnvelopeHash: sha256Canonical(spec.frozenTemporalEnvelope), comparisonSha256: await sha256File(comparisonPath) };
  const binding = { ...body, bindingHash: sha256Canonical(body) }; await writeFile(bindingPath, serialize(binding));
  const item = { pair, comparison, comparisonPath, bindingPath, binding };
  const reason = await validateComparison({ item, aManifest: a.manifest, bManifest: b.manifest, expectedComparatorSha: tools.comparatorSha256, expectedStaticEnvelope: spec.frozenStaticEnvelope, expectedTemporalEnvelope: spec.frozenTemporalEnvelope });
  if (reason !== 'OK') throw new Error(`${pair} comparison failed: ${reason}`);
  comparisons.set(pair, item);
}

const base = runs.get('A');
const defaults = { record: base, spec, expectedSpecSha: specSha, expectedDerivationSha: spec.evidenceBasis.derivationResultSha256, expectedB24Sha: spec.evidenceBasis.b24ResultsSha256, expectedReviewSpecSha: frozen.reviewRenderSpecSha256, expectedBlenderSha: frozen.blenderSha256, expectedOcioSha: frozen.ocioSha256, expectedSceneSha: frozen.sceneBlendSha256, expectedPlanHash: frozen.planHash, expectedStructureHash: frozen.structureHash, expectedConfiguratorSha: frozen.configuratorSha256, expectedRendererSha: frozen.rendererSha256 };
const attacks = [];
const attack = (id, expectedReason, observedReason) => attacks.push({ id, expectedReason, observedReason, pass: expectedReason === observedReason });
attack('N_B25_SPEC_SHA', 'B25_SPEC_SHA', await validateRun({ ...defaults, expectedSpecSha: '0'.repeat(64) }));
attack('N_DERIVATION_SHA', 'DERIVATION_SHA', await validateRun({ ...defaults, expectedDerivationSha: '0'.repeat(64) }));
attack('N_B24_RESULT_SHA', 'B24_RESULT_SHA', await validateRun({ ...defaults, expectedB24Sha: '0'.repeat(64) }));
attack('N_REVIEW_SPEC_SHA', 'REVIEW_SPEC_SHA', await validateRun({ ...defaults, expectedReviewSpecSha: '0'.repeat(64) }));
attack('N_BLENDER_SHA', 'BLENDER_SHA', await validateRun({ ...defaults, expectedBlenderSha: '0'.repeat(64) }));
attack('N_OCIO_SHA', 'OCIO_SHA', await validateRun({ ...defaults, expectedOcioSha: '0'.repeat(64) }));
attack('N_SCENE_SHA', 'SCENE_SHA', await validateRun({ ...defaults, expectedSceneSha: '0'.repeat(64) }));
attack('N_PLAN_STRUCTURE', 'PLAN_OR_STRUCTURE_HASH', await validateRun({ ...defaults, expectedPlanHash: '0'.repeat(64) }));
attack('N_CONFIGURATOR_SHA', 'CONFIGURATOR_SHA', await validateRun({ ...defaults, expectedConfiguratorSha: '0'.repeat(64) }));
attack('N_RENDERER_SHA', 'RENDERER_SHA', await validateRun({ ...defaults, expectedRendererSha: '0'.repeat(64) }));
const baseComparison = comparisons.get('A-B');
attack('N_COMPARATOR_SHA', 'COMPARATOR_SHA', await validateComparison({ item: baseComparison, aManifest: runs.get('A').manifest, bManifest: runs.get('B').manifest, expectedComparatorSha: '0'.repeat(64), expectedStaticEnvelope: spec.frozenStaticEnvelope, expectedTemporalEnvelope: spec.frozenTemporalEnvelope }));
attack('N_SOURCE_CONTROLS', 'SOURCE_OR_FIXED_CONTROLS', await validateRun({ ...defaults, expectedAfterDither: 1 }));
attack('N_PROCESS_BINDING', 'PROCESS_REPLICATE_BINDING', await validateRun({ ...defaults, expectedProcessId: -1 }));
attack('N_FRAME_ORDER_COUNT', 'FRAME_ORDER_OR_COUNT', await validateRun({ ...defaults, expectedFrameCount: 143 }));
attack('N_PNG_LAYOUT', 'PNG_LAYOUT', await validateRun({ ...defaults, expectedWidth: 961 }));
attack('N_OUTPUT_HASH', 'MISSING_OR_MUTATED_OUTPUT', await validateRun({ ...defaults, expectedFirstFrameSha: '0'.repeat(64) }));
const attackedBindingBody = structuredClone(baseComparison.binding); delete attackedBindingBody.bindingHash; attackedBindingBody.aSequenceHash = '0'.repeat(64);
const attackedBinding = { ...attackedBindingBody, bindingHash: sha256Canonical(attackedBindingBody) }, attackedBindingPath = resolve(evidenceRoot, 'attack-binding.json'); await writeFile(attackedBindingPath, serialize(attackedBinding));
attack('N_COMPARISON_BINDING', 'COMPARISON_BINDING', await validateComparison({ item: { ...baseComparison, bindingPath: attackedBindingPath }, aManifest: runs.get('A').manifest, bManifest: runs.get('B').manifest, expectedComparatorSha: tools.comparatorSha256, expectedStaticEnvelope: spec.frozenStaticEnvelope, expectedTemporalEnvelope: spec.frozenTemporalEnvelope }));
attack('N_ENVELOPE_MUTATION', 'ENVELOPE_MUTATION', await validateComparison({ item: baseComparison, aManifest: runs.get('A').manifest, bManifest: runs.get('B').manifest, expectedComparatorSha: tools.comparatorSha256, expectedStaticEnvelope: { ...spec.frozenStaticEnvelope, maximumAbsoluteErrorAtMost: 0 }, expectedTemporalEnvelope: spec.frozenTemporalEnvelope }));
const nonPendingSpec = structuredClone(spec); nonPendingSpec.executionContract.humanReviewMustRemainPending = false;
attack('N_HUMAN_STATUS', 'HUMAN_REVIEW_STATUS', await validateRun({ ...defaults, spec: nonPendingSpec }));

const pairResults = Object.fromEntries([...comparisons].map(([pair, item]) => [pair, {
  staticEnvelopePassFrames: item.comparison.staticEnvelopePassFrames,
  decodedPixelExactFrames: item.comparison.decodedPixelExactFrames,
  temporalEnvelopePassTransitions: item.comparison.temporalEnvelopePassTransitions,
  temporalExactTransitions: item.comparison.temporalExactTransitions,
  maximumAbsoluteError: item.comparison.maximumAbsoluteError,
  maximumRmsError: item.comparison.maximumRmsError,
  maximumFailurePixels: item.comparison.maximumFailurePixels,
  maximumAbsoluteResidualDelta: item.comparison.maximumAbsoluteResidualDelta,
  maximumRmsResidualDelta: item.comparison.maximumRmsResidualDelta,
  maximumChangedPixels: item.comparison.maximumChangedPixels,
  bindingHash: item.binding.bindingHash,
}]));
const staticPass = Object.values(pairResults).every(item => item.staticEnvelopePassFrames === 144);
const temporalPass = Object.values(pairResults).every(item => item.temporalEnvelopePassTransitions === 143);
const validExperiment = attacks.length === 19 && attacks.every(item => item.pass) && new Set([...runs.values()].map(record => record.processId)).size === 3;
let decision = 'INVALID_EXPERIMENT';
if (validExperiment && staticPass && temporalPass) decision = 'TEMPORAL_RESIDUAL_ENVELOPE_SUPPORT';
else if (validExperiment && staticPass && !temporalPass) decision = 'TEMPORAL_ONLY_ENVELOPE_FAIL';
else if (validExperiment && !staticPass && !temporalPass) decision = 'STATIC_AND_TEMPORAL_ENVELOPE_FAIL';
else if (validExperiment && !staticPass && temporalPass) decision = 'STATIC_ONLY_ENVELOPE_FAIL';
const result = {
  documentType: 'BFS_B25_TEMPORAL_RESIDUAL_HOLDOUT_RESULT', version: '0.1.0', executedAtUtc: new Date().toISOString(),
  decision, validExperiment, humanReview: { status: 'PENDING', claim: 'Automation cannot determine visibility, flicker perception or cinematic quality.' },
  design: spec.design, identities: { ...frozen, b25SpecSha256: specSha, derivationResultSha256: await sha256File(derivationPath), b24ResultsSha256: await sha256File(b24Path), ...tools },
  envelopes: { static: spec.frozenStaticEnvelope, temporal: spec.frozenTemporalEnvelope },
  processLedger: ledger, pairResults,
  aggregate: {
    uniqueRenderProcesses: new Set([...runs.values()].map(record => record.processId)).size,
    renderedFrames: [...runs.values()].reduce((sum, record) => sum + record.report.frameCount, 0),
    staticEnvelopePassFrames: Object.values(pairResults).reduce((sum, item) => sum + item.staticEnvelopePassFrames, 0),
    staticPairComparisons: 432,
    temporalEnvelopePassTransitions: Object.values(pairResults).reduce((sum, item) => sum + item.temporalEnvelopePassTransitions, 0),
    temporalTransitionComparisons: 429,
    decodedPixelExactFrames: Object.values(pairResults).reduce((sum, item) => sum + item.decodedPixelExactFrames, 0),
    temporalExactTransitions: Object.values(pairResults).reduce((sum, item) => sum + item.temporalExactTransitions, 0),
    maximumAbsoluteError: Math.max(...Object.values(pairResults).map(item => item.maximumAbsoluteError)),
    maximumRmsError: Math.max(...Object.values(pairResults).map(item => item.maximumRmsError)),
    maximumFailurePixels: Math.max(...Object.values(pairResults).map(item => item.maximumFailurePixels)),
    maximumAbsoluteResidualDelta: Math.max(...Object.values(pairResults).map(item => item.maximumAbsoluteResidualDelta)),
    maximumRmsResidualDelta: Math.max(...Object.values(pairResults).map(item => item.maximumRmsResidualDelta)),
    maximumChangedPixels: Math.max(...Object.values(pairResults).map(item => item.maximumChangedPixels)),
  },
  attacks,
  artifacts: { ledger: repoUri(ledgerPath), manifests: Object.fromEntries([...runs].map(([id, record]) => [id, repoUri(record.manifestPath)])), comparisons: Object.fromEntries([...comparisons].map(([id, item]) => [id, { comparison: repoUri(item.comparisonPath), binding: repoUri(item.bindingPath) }])) },
  nonClaims: spec.explicitNonClaims,
};
await writeFile(resolve(root, 'results.json'), serialize(result));
process.stdout.write(`BFS_B25_RESULT ${decision} static=${result.aggregate.staticEnvelopePassFrames}/432 temporal=${result.aggregate.temporalEnvelopePassTransitions}/429 attacks=${attacks.filter(item => item.pass).length}/19\n`);
if (!validExperiment) process.exitCode = 1;
