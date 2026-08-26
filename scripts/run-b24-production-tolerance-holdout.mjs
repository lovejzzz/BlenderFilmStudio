import { copyFile, mkdir, readFile, readdir, rm, unlink, writeFile } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { relative, resolve, sep } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256Canonical, sha256File } from './lib/receipt-format.mjs';

const experimentRoot = resolve(repositoryRoot, 'experiments/production-tolerance-holdout-v0-1');
const evidenceRoot = resolve(experimentRoot, 'evidence');
const renderEvidence = resolve(evidenceRoot, 'renders');
const comparisonEvidence = resolve(evidenceRoot, 'comparisons');
const workRoot = resolve(experimentRoot, 'work');
const specPath = resolve(repositoryRoot, 'specs/production-tolerance-holdout-spec.v0.1.json');
const derivationPath = resolve(repositoryRoot, 'experiments/production-tolerance-derivation-v0-1/results.json');
const b23ResultPath = resolve(repositoryRoot, 'experiments/eevee-repeated-render-boundary-v0-1/results.json');
const reviewSpecPath = resolve(repositoryRoot, 'specs/review-render-spec.v0.1.json');
const configurator = resolve(repositoryRoot, 'blender/configure_eevee_threads.py');
const renderer = resolve(repositoryRoot, 'blender/render_dual_output_localization.py');
const comparator = resolve(repositoryRoot, 'blender/compare_b24_holdout_tolerance.py');
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

async function renderOne({ invocationId, frame, replicate, outputDir, receiptPath, scenePath, ocioPath }) {
  await mkdir(outputDir, { recursive: true });
  const reportPath = resolve(renderEvidence, `${invocationId}.render.json`);
  const interventionPath = resolve(renderEvidence, `${invocationId}.intervention.json`);
  const launched = await run(blender, [
    '--background', scenePath, '--disable-autoexec', '--python-exit-code', '1',
    '--python', configurator, '--python', renderer, '--',
    '--spec', reviewSpecPath, '--receipt', receiptPath, '--output-dir', outputDir,
    '--report', reportPath, '--frame', String(frame), '--invocation-id', invocationId,
  ], {
    ...process.env,
    OCIO: ocioPath,
    BFS_B22_THREADS_MODE: 'FIXED', BFS_B22_THREADS: '8', BFS_B22_CELL: 'T08',
    BFS_B22_INTERVENTION_REPORT: interventionPath,
  });
  const report = JSON.parse(await readFile(reportPath, 'utf8'));
  process.stdout.write(`BFS_B24_PROCESS_OK ${invocationId} pid=${launched.processId} replicate=${replicate} seconds=${report.totalSeconds}\n`);
  return { invocationId, frame, replicate, outputDir, reportPath, interventionPath, processId: launched.processId, report };
}

async function validateRun({
  record, identities, expectedSpecSha, expectedDerivationSha, expectedB23Sha,
  expectedSourceThreads = 8,
  expectedControls = { renderSamples: 32, ditherIntensity: 0, useFastGi: true, useTaaReprojection: true },
  expectedReplicate = record.replicate,
  expectedRenderCalls = 1, expectedSaves = 2,
  expectedExrFormat = 'float', expectedPngFormat = 'uint8',
}) {
  if (await sha256File(specPath) !== expectedSpecSha) return 'B24_SPEC_SHA';
  if (await sha256File(derivationPath) !== expectedDerivationSha) return 'DERIVATION_SHA';
  if (await sha256File(b23ResultPath) !== expectedB23Sha) return 'B23_RESULT_SHA';
  if (await sha256File(reviewSpecPath) !== identities.reviewRenderSpecSha256) return 'REVIEW_SPEC_SHA';
  if (await sha256File(blender) !== identities.blenderSha256) return 'BLENDER_SHA';
  if (await sha256File(identities.ocioPath) !== identities.ocioSha256) return 'OCIO_SHA';
  if (await sha256File(identities.scenePath) !== identities.sceneBlendSha256) return 'SCENE_SHA';
  if (await sha256File(configurator) !== identities.configuratorSha256) return 'CONFIGURATOR_SHA';
  if (await sha256File(renderer) !== identities.rendererSha256) return 'RENDERER_SHA';
  const intervention = JSON.parse(await readFile(record.interventionPath, 'utf8'));
  if (intervention.before.threadsMode !== 'FIXED' || intervention.before.threads !== expectedSourceThreads) return 'SOURCE_THREAD_STATE';
  if (intervention.after.threadsMode !== 'FIXED' || intervention.after.threads !== 8 || intervention.after.ditherIntensity !== expectedControls.ditherIntensity || intervention.after.useFastGi !== expectedControls.useFastGi || intervention.after.useTaaReprojection !== expectedControls.useTaaReprojection) return 'REQUESTED_FIXED_CONTROLS';
  const report = JSON.parse(await readFile(record.reportPath, 'utf8'));
  if (report.processId !== record.processId || report.invocationId !== record.invocationId || report.frame !== record.frame || record.replicate !== expectedReplicate) return 'PROCESS_REPLICATE_BINDING';
  if (report.observedControls.renderSamples !== expectedControls.renderSamples || report.observedControls.ditherIntensity !== expectedControls.ditherIntensity || report.observedControls.useFastGi !== expectedControls.useFastGi || report.observedControls.useTaaReprojection !== expectedControls.useTaaReprojection) return 'REQUESTED_FIXED_CONTROLS';
  if (report.renderOperatorCallCount !== expectedRenderCalls) return 'RENDER_CALL_COUNT';
  if (report.saveCount !== expectedSaves || report.sameRenderResultWithoutRerender !== true || report.directImagePixelsAccessed !== false) return 'SAVE_COUNT';
  if (report.source.sceneBlendSha256 !== identities.sceneBlendSha256 || report.savedSourceBlend !== false || report.cameraAndTimelineInvariant !== true) return 'SOURCE_OR_TIMELINE_INVARIANT';
  const exr = report.outputs.EXR32_SCENE_LINEAR, png = report.outputs.PNG8_DISPLAY;
  if (exr.decoded.width !== 960 || exr.decoded.height !== 540 || JSON.stringify(exr.decoded.channels) !== JSON.stringify(['R', 'G', 'B', 'A']) || exr.decoded.pixelFormat !== expectedExrFormat) return 'EXR_LAYOUT';
  if (png.decoded.width !== 960 || png.decoded.height !== 540 || JSON.stringify(png.decoded.channels) !== JSON.stringify(['R', 'G', 'B', 'A']) || png.decoded.pixelFormat !== expectedPngFormat) return 'PNG_LAYOUT';
  for (const output of [exr, png]) {
    try { if (await sha256File(resolve(record.outputDir, output.name)) !== output.sha256) return 'MISSING_OR_MUTATED_OUTPUT'; }
    catch { return 'MISSING_OR_MUTATED_OUTPUT'; }
  }
  return 'OK';
}

async function makeManifest({ replicate, records, dir, specSha, tools, frames }) {
  const entries = [];
  for (const frame of frames) {
    const base = `frame-${String(frame).padStart(4, '0')}`;
    entries.push({
      frame,
      png: { name: `${base}.png`, sha256: await sha256File(resolve(dir, `${base}.png`)) },
      exr: { name: `${base}.exr`, sha256: await sha256File(resolve(dir, `${base}.exr`)) },
    });
  }
  const body = {
    documentType: 'BFS_B24_HOLDOUT_MANIFEST', version: '0.1.0', replicate,
    b24SpecSha256: specSha, toolIdentities: tools, holdoutFrames: frames,
    invocations: records.map(record => ({ invocationId: record.invocationId, processId: record.processId, renderReportSha256: null, interventionReportSha256: null })),
    frames: entries,
  };
  for (let index = 0; index < records.length; index += 1) {
    body.invocations[index].renderReportSha256 = await sha256File(records[index].reportPath);
    body.invocations[index].interventionReportSha256 = await sha256File(records[index].interventionPath);
  }
  return { ...body, manifestHash: sha256Canonical(body) };
}

async function validateManifest({ path, dir, expectedSpecSha, tools, frames }) {
  const manifest = JSON.parse(await readFile(path, 'utf8'));
  const body = structuredClone(manifest); delete body.manifestHash;
  if (sha256Canonical(body) !== manifest.manifestHash) return 'MANIFEST_SELF_HASH';
  if (manifest.b24SpecSha256 !== expectedSpecSha || JSON.stringify(manifest.holdoutFrames) !== JSON.stringify(frames)) return 'HOLDOUT_SET_RUN_ORDER';
  if (JSON.stringify(manifest.toolIdentities) !== JSON.stringify(tools)) return 'MANIFEST_TOOL_BINDING';
  const names = await readdir(dir);
  for (const frame of manifest.frames) for (const key of ['png', 'exr']) {
    if (!names.includes(frame[key].name)) return 'MISSING_OR_MUTATED_OUTPUT';
    if (await sha256File(resolve(dir, frame[key].name)) !== frame[key].sha256) return 'MISSING_OR_MUTATED_OUTPUT';
  }
  return 'OK';
}

async function validateComparison({
  item, aManifest, bManifest, expectedComparatorSha,
  expectedEnvelope = item.envelope,
  expectedYee = item.format === 'PNG8_DISPLAY'
    ? { luminance: item.envelope.yeeLuminanceCdM2, fov: item.envelope.yeeFieldOfViewDegrees }
    : null,
}) {
  if (await sha256File(comparator) !== expectedComparatorSha) return 'COMPARATOR_SHA';
  const binding = JSON.parse(await readFile(item.bindingPath, 'utf8'));
  const body = structuredClone(binding); delete body.bindingHash;
  if (sha256Canonical(body) !== binding.bindingHash) return 'COMPARISON_SELF_HASH';
  if (binding.aManifestHash !== aManifest.manifestHash || binding.bManifestHash !== bManifest.manifestHash || binding.comparisonSha256 !== await sha256File(item.comparisonPath)) return 'COMPARISON_MANIFEST_FILE_BINDING';
  const comparison = JSON.parse(await readFile(item.comparisonPath, 'utf8'));
  if (comparison.format !== item.format || comparison.frameCount !== 24 || JSON.stringify(comparison.selectedFrames) !== JSON.stringify(item.frames)) return 'COMPARISON_FORMAT';
  if (sha256Canonical(comparison.frozenEnvelope) !== sha256Canonical(expectedEnvelope)) return 'NUMERIC_ENVELOPE_MUTATION';
  if (expectedYee && (comparison.frozenEnvelope.yeeLuminanceCdM2 !== expectedYee.luminance || comparison.frozenEnvelope.yeeFieldOfViewDegrees !== expectedYee.fov)) return 'YEE_PARAMETER_MUTATION';
  const key = item.format === 'PNG8_DISPLAY' ? 'png' : 'exr';
  for (const observed of comparison.frames) {
    const a = aManifest.frames.find(frame => frame.frame === observed.frame)[key];
    const b = bManifest.frames.find(frame => frame.frame === observed.frame)[key];
    if (observed.aSha256 !== a.sha256 || observed.bSha256 !== b.sha256) return 'COMPARISON_MANIFEST_FILE_BINDING';
  }
  return 'OK';
}

await rm(evidenceRoot, { recursive: true, force: true });
await rm(workRoot, { recursive: true, force: true });
await mkdir(renderEvidence, { recursive: true });
await mkdir(comparisonEvidence, { recursive: true });
const spec = JSON.parse(await readFile(specPath, 'utf8'));
const specSha = await sha256File(specPath);
if (specSha !== 'd8cb2e230a5c093cca639cf12e2d210bcac0d1f27fc28d45498ad49382d1ebae') throw new Error('B24 spec changed after pre-registration');
const derivation = JSON.parse(await readFile(derivationPath, 'utf8'));
const derivedEnvelope = structuredClone(derivation.candidateEnvelope);
delete derivedEnvelope.EXR32_SCENE_LINEAR.derivationMustFit;
delete derivedEnvelope.PNG8_DISPLAY.derivationMustFit;
if (derivation.status !== 'DERIVATION_ONLY_NOT_VALIDATION' || sha256Canonical(derivedEnvelope) !== sha256Canonical(spec.frozenEnvelope)) throw new Error('B24 derivation/envelope mismatch');
const reviewSpec = JSON.parse(await readFile(reviewSpecPath, 'utf8'));
const receiptPath = resolve(repositoryRoot, reviewSpec.source.receiptUri);
const receipt = JSON.parse(await readFile(receiptPath, 'utf8'));
const scenePath = resolve(repositoryRoot, receipt.run.sceneBlend.uri);
const ocioPath = resolve(repositoryRoot, receipt.executionIdentity.configuration.ocio.uri);
const frozen = spec.frozenIdentity;
for (const [path, expected, label] of [
  [derivationPath, spec.evidenceBasis.derivationResultSha256, 'derivation'], [b23ResultPath, spec.evidenceBasis.b23ResultsSha256, 'B23 result'],
  [reviewSpecPath, frozen.reviewRenderSpecSha256, 'review spec'], [configurator, frozen.configuratorSha256, 'configurator'],
  [renderer, frozen.rendererSha256, 'renderer'], [blender, frozen.blenderSha256, 'Blender'], [ocioPath, frozen.ocioSha256, 'OCIO'], [scenePath, frozen.sceneBlendSha256, 'scene'],
]) if (await sha256File(path) !== expected) throw new Error(`${label} SHA mismatch`);
const tools = { configuratorSha256: await sha256File(configurator), rendererSha256: await sha256File(renderer), comparatorSha256: await sha256File(comparator), runnerSha256: await sha256File(runner) };
const identities = { ...frozen, ...tools, ocioPath, scenePath };
const frames = spec.holdout.frames;
const runOrder = frames.flatMap(frame => spec.design.blockOrderPerFrame.map(replicate => ({ invocationId: `H-${String(frame).padStart(4, '0')}-${replicate}`, frame, replicate })));
if (runOrder.length !== 72 || frames.some(frame => frame % 6 !== 4)) throw new Error('Holdout/run order mismatch');
const runOrderPath = resolve(evidenceRoot, 'run-order.json');
await writeFile(runOrderPath, serialize({ documentType: 'BFS_B24_FROZEN_RUN_ORDER', version: '0.1.0', b24SpecSha256: specSha, order: runOrder, orderHash: sha256Canonical(runOrder) }));
const records = new Map(), groups = new Map([['A', []], ['B', []], ['C', []]]), aggregate = new Map();
for (const replicate of ['A', 'B', 'C']) { const dir = resolve(workRoot, replicate); await mkdir(dir, { recursive: true }); aggregate.set(replicate, dir); }
for (const item of runOrder) {
  const outputDir = resolve(workRoot, 'invocations', item.invocationId);
  const record = await renderOne({ ...item, outputDir, receiptPath, scenePath, ocioPath });
  const reason = await validateRun({ record, identities, expectedSpecSha: specSha, expectedDerivationSha: spec.evidenceBasis.derivationResultSha256, expectedB23Sha: spec.evidenceBasis.b23ResultsSha256 });
  if (reason !== 'OK') throw new Error(`${item.invocationId}: ${reason}`);
  const base = `frame-${String(item.frame).padStart(4, '0')}`;
  for (const extension of ['.png', '.exr']) await copyFile(resolve(outputDir, `${base}${extension}`), resolve(aggregate.get(item.replicate), `${base}${extension}`));
  records.set(item.invocationId, record); groups.get(item.replicate).push(record);
}
const ledgerBody = { documentType: 'BFS_B24_PROCESS_LEDGER', version: '0.1.0', b24SpecSha256: specSha, processes: [...records.values()].map(record => ({ invocationId: record.invocationId, processId: record.processId, frame: record.frame, replicate: record.replicate, reportSha256: null })) };
for (const item of ledgerBody.processes) item.reportSha256 = await sha256File(records.get(item.invocationId).reportPath);
const ledger = { ...ledgerBody, ledgerHash: sha256Canonical(ledgerBody) };
const uniquePids = new Set(ledger.processes.map(item => item.processId)).size;
if (uniquePids !== 72) throw new Error('B24 render PIDs are not unique');
const ledgerPath = resolve(evidenceRoot, 'process-ledger.json'); await writeFile(ledgerPath, serialize(ledger));
const manifests = new Map();
for (const replicate of ['A', 'B', 'C']) {
  const manifest = await makeManifest({ replicate, records: groups.get(replicate), dir: aggregate.get(replicate), specSha, tools, frames });
  const path = resolve(evidenceRoot, `${replicate}.manifest.json`); await writeFile(path, serialize(manifest));
  const reason = await validateManifest({ path, dir: aggregate.get(replicate), expectedSpecSha: specSha, tools, frames });
  if (reason !== 'OK') throw new Error(`Manifest ${replicate}: ${reason}`);
  manifests.set(replicate, { manifest, path, dir: aggregate.get(replicate) });
}
const comparisons = new Map();
for (const format of ['EXR32_SCENE_LINEAR', 'PNG8_DISPLAY']) for (const [aId, bId] of [['A', 'B'], ['A', 'C'], ['B', 'C']]) {
  const id = `${format}-${aId}-${bId}`;
  const comparisonPath = resolve(comparisonEvidence, `${id}.comparison.json`), bindingPath = resolve(comparisonEvidence, `${id}.binding.json`), envelope = spec.frozenEnvelope[format];
  await run(blender, ['--factory-startup', '--background', '--python-exit-code', '1', '--python', comparator, '--', '--a-dir', aggregate.get(aId), '--b-dir', aggregate.get(bId), '--frames', frames.join(','), '--format', format, '--envelope', JSON.stringify(envelope), '--output', comparisonPath]);
  const comparison = JSON.parse(await readFile(comparisonPath, 'utf8'));
  const body = { documentType: 'BFS_B24_COMPARISON_BINDING', version: '0.1.0', id, format, aReplicate: aId, bReplicate: bId, aManifestHash: manifests.get(aId).manifest.manifestHash, bManifestHash: manifests.get(bId).manifest.manifestHash, comparatorSha256: tools.comparatorSha256, envelopeHash: sha256Canonical(envelope), comparisonSha256: await sha256File(comparisonPath) };
  const binding = { ...body, bindingHash: sha256Canonical(body) }; await writeFile(bindingPath, serialize(binding));
  const item = { id, format, aId, bId, frames, envelope, comparison, comparisonPath, bindingPath, binding };
  const reason = await validateComparison({ item, aManifest: manifests.get(aId).manifest, bManifest: manifests.get(bId).manifest, expectedComparatorSha: tools.comparatorSha256 });
  if (reason !== 'OK') throw new Error(`${id}: ${reason}`);
  comparisons.set(id, item);
}
const attacks = [], attack = (id, expectedReason, observedReason) => attacks.push({ id, expectedReason, observedReason, pass: expectedReason === observedReason });
const base = records.get('H-0004-A');
const defaults = { record: base, identities, expectedSpecSha: specSha, expectedDerivationSha: spec.evidenceBasis.derivationResultSha256, expectedB23Sha: spec.evidenceBasis.b23ResultsSha256 };
attack('N_B24_SPEC_SHA', 'B24_SPEC_SHA', await validateRun({ ...defaults, expectedSpecSha: '0'.repeat(64) }));
attack('N_DERIVATION_SHA', 'DERIVATION_SHA', await validateRun({ ...defaults, expectedDerivationSha: '0'.repeat(64) }));
attack('N_B23_RESULT_SHA', 'B23_RESULT_SHA', await validateRun({ ...defaults, expectedB23Sha: '0'.repeat(64) }));
attack('N_REVIEW_SPEC_SHA', 'REVIEW_SPEC_SHA', await validateRun({ ...defaults, identities: { ...identities, reviewRenderSpecSha256: '0'.repeat(64) } }));
attack('N_BLENDER_SHA', 'BLENDER_SHA', await validateRun({ ...defaults, identities: { ...identities, blenderSha256: '0'.repeat(64) } }));
attack('N_OCIO_SHA', 'OCIO_SHA', await validateRun({ ...defaults, identities: { ...identities, ocioSha256: '0'.repeat(64) } }));
attack('N_SCENE_SHA', 'SCENE_SHA', await validateRun({ ...defaults, identities: { ...identities, sceneBlendSha256: '0'.repeat(64) } }));
attack('N_CONFIGURATOR_SHA', 'CONFIGURATOR_SHA', await validateRun({ ...defaults, identities: { ...identities, configuratorSha256: '0'.repeat(64) } }));
attack('N_RENDERER_SHA', 'RENDERER_SHA', await validateRun({ ...defaults, identities: { ...identities, rendererSha256: '0'.repeat(64) } }));
const baseComparison = comparisons.get('PNG8_DISPLAY-A-B');
attack('N_COMPARATOR_SHA', 'COMPARATOR_SHA', await validateComparison({ item: baseComparison, aManifest: manifests.get('A').manifest, bManifest: manifests.get('B').manifest, expectedComparatorSha: '0'.repeat(64) }));
attack('N_SOURCE_THREAD_STATE', 'SOURCE_THREAD_STATE', await validateRun({ ...defaults, expectedSourceThreads: 7 }));
attack('N_REQUESTED_FIXED_CONTROLS', 'REQUESTED_FIXED_CONTROLS', await validateRun({ ...defaults, expectedControls: { renderSamples: 32, ditherIntensity: 1, useFastGi: true, useTaaReprojection: true } }));
attack('N_HOLDOUT_RUN_ORDER', 'HOLDOUT_SET_RUN_ORDER', await validateManifest({ path: manifests.get('A').path, dir: manifests.get('A').dir, expectedSpecSha: specSha, tools, frames: frames.slice(1) }));
attack('N_PROCESS_REPLICATE_BINDING', 'PROCESS_REPLICATE_BINDING', await validateRun({ ...defaults, expectedReplicate: 'B' }));
attack('N_RENDER_CALL_COUNT', 'RENDER_CALL_COUNT', await validateRun({ ...defaults, expectedRenderCalls: 2 }));
attack('N_SAVE_COUNT', 'SAVE_COUNT', await validateRun({ ...defaults, expectedSaves: 1 }));
attack('N_EXR_LAYOUT', 'EXR_LAYOUT', await validateRun({ ...defaults, expectedExrFormat: 'half' }));
attack('N_PNG_LAYOUT', 'PNG_LAYOUT', await validateRun({ ...defaults, expectedPngFormat: 'float' }));
const attackDir = resolve(workRoot, 'attacks', 'missing'); await mkdir(attackDir, { recursive: true });
for (const output of Object.values(base.report.outputs)) await copyFile(resolve(base.outputDir, output.name), resolve(attackDir, output.name));
await unlink(resolve(attackDir, base.report.outputs.PNG8_DISPLAY.name));
attack('N_MISSING_OUTPUT', 'MISSING_OR_MUTATED_OUTPUT', await validateRun({ ...defaults, record: { ...base, outputDir: attackDir } }));
const badBindingItem = structuredClone(baseComparison), badBody = structuredClone(badBindingItem.binding); delete badBody.bindingHash; badBody.aManifestHash = '0'.repeat(64); badBindingItem.binding = { ...badBody, bindingHash: sha256Canonical(badBody) }; badBindingItem.bindingPath = resolve(workRoot, 'attacks', 'bad-binding.json'); await writeFile(badBindingItem.bindingPath, serialize(badBindingItem.binding));
attack('N_COMPARISON_BINDING', 'COMPARISON_MANIFEST_FILE_BINDING', await validateComparison({ item: badBindingItem, aManifest: manifests.get('A').manifest, bManifest: manifests.get('B').manifest, expectedComparatorSha: tools.comparatorSha256 }));
attack('N_ENVELOPE_MUTATION', 'NUMERIC_ENVELOPE_MUTATION', await validateComparison({ item: baseComparison, aManifest: manifests.get('A').manifest, bManifest: manifests.get('B').manifest, expectedComparatorSha: tools.comparatorSha256, expectedEnvelope: { ...baseComparison.envelope, maximumAbsoluteErrorAtMost: 1 } }));
attack('N_YEE_PARAMETERS', 'YEE_PARAMETER_MUTATION', await validateComparison({ item: baseComparison, aManifest: manifests.get('A').manifest, bManifest: manifests.get('B').manifest, expectedComparatorSha: tools.comparatorSha256, expectedYee: { luminance: 99, fov: 45 } }));
function formatSummary(format) {
  const selected = [...comparisons.values()].filter(item => item.format === format);
  const passed = selected.reduce((sum, item) => sum + item.comparison.envelopePassFrames, 0);
  const exact = selected.reduce((sum, item) => sum + item.comparison.decodedPixelExactFrames, 0);
  return { pairGroups: 3, totalHoldoutPairs: 72, envelopePassPairs: passed, decodedExactPairs: exact, maximumAbsoluteError: Math.max(...selected.map(item => item.comparison.maximumAbsoluteError)), maximumRmsError: Math.max(...selected.map(item => item.comparison.maximumRmsError)), maximumFailurePixels: Math.max(...selected.map(item => item.comparison.maximumFailurePixels)), maximumYeeFailurePixels: Math.max(...selected.map(item => item.comparison.maximumYeeFailurePixels)), pass: passed === 72 };
}
const exr = formatSummary('EXR32_SCENE_LINEAR'), png = formatSummary('PNG8_DISPLAY');
const validExperiment = attacks.length === 22 && attacks.every(item => item.pass);
let decision = 'PRODUCTION_REPEATABILITY_ENVELOPE_SUPPORT';
if (!validExperiment) decision = 'INVALID_EXPERIMENT';
else if (!exr.pass && png.pass) decision = 'SCENE_LINEAR_ENVELOPE_FAIL_DISPLAY_PASS';
else if (!exr.pass && !png.pass) decision = 'DISPLAY_AND_SCENE_LINEAR_ENVELOPE_FAIL';
else if (exr.pass && !png.pass) decision = 'DISPLAY_ONLY_ENVELOPE_FAIL';
const result = { documentType: 'BFS_B24_PRODUCTION_TOLERANCE_HOLDOUT_EXPERIMENT', version: '0.1.0', executedAtUtc: new Date().toISOString(), decision, validExperiment, holdout: spec.holdout, design: { ...spec.design, materializedRunOrder: runOrder.map(item => item.invocationId) }, identities: { ...frozen, b24SpecSha256: specSha, derivationResultSha256: spec.evidenceBasis.derivationResultSha256, b23ResultsSha256: spec.evidenceBasis.b23ResultsSha256, ...tools }, frozenEnvelope: spec.frozenEnvelope, formats: { EXR32_SCENE_LINEAR: exr, PNG8_DISPLAY: png }, processLedger: { processCount: 72, uniqueProcessIds: uniquePids, renderCalls: 72, saves: 144, ledgerHash: ledger.ledgerHash, uri: repoUri(ledgerPath) }, comparisons: Object.fromEntries([...comparisons].map(([id, item]) => [id, { format: item.format, envelopePassFrames: item.comparison.envelopePassFrames, decodedPixelExactFrames: item.comparison.decodedPixelExactFrames, maximumAbsoluteError: item.comparison.maximumAbsoluteError, maximumRmsError: item.comparison.maximumRmsError, maximumFailurePixels: item.comparison.maximumFailurePixels, maximumYeeFailurePixels: item.comparison.maximumYeeFailurePixels, comparisonUri: repoUri(item.comparisonPath), bindingHash: item.binding.bindingHash }])), attacks, artifacts: { runOrder: repoUri(runOrderPath), manifests: Object.fromEntries([...manifests].map(([id, item]) => [id, repoUri(item.path)])), renders: repoUri(renderEvidence), comparisons: repoUri(comparisonEvidence) }, nonClaims: spec.explicitNonClaims };
await writeFile(resolve(experimentRoot, 'results.json'), serialize(result));
process.stdout.write(`BFS_B24_HOLDOUT ${decision} EXR=${exr.envelopePassPairs}/72 PNG=${png.envelopePassPairs}/72 exactEXR=${exr.decodedExactPairs}/72 exactPNG=${png.decodedExactPairs}/72 pids=${uniquePids}/72 attacks=${attacks.filter(item => item.pass).length}/${attacks.length}\n`);
if (!validExperiment) process.exitCode = 1;
