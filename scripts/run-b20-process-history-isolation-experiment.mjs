import { appendFile, copyFile, mkdir, readFile, readdir, rm, stat, unlink, writeFile } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { relative, resolve, sep } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256Canonical, sha256File } from './lib/receipt-format.mjs';

const root = resolve(repositoryRoot, 'experiments/eevee-process-history-isolation-v0-1');
const evidenceRoot = resolve(root, 'evidence');
const workRoot = resolve(root, 'work');
const renderEvidenceRoot = resolve(evidenceRoot, 'renders');
const comparisonEvidenceRoot = resolve(evidenceRoot, 'comparisons');
const specPath = resolve(repositoryRoot, 'specs/eevee-process-history-isolation-spec.v0.1.json');
const reviewSpecPath = resolve(repositoryRoot, 'specs/review-render-spec.v0.1.json');
const renderer = resolve(repositoryRoot, 'blender/render_process_history_isolation.py');
const comparator = resolve(repositoryRoot, 'blender/compare_selected_frames.py');
const configurator = resolve(repositoryRoot, 'blender/configure_gi_reprojection_factorial.py');
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
    child.on('close', code => code === 0 ? resolvePromise({ output, processId }) : reject(new Error(`${command} failed (${code}) pid=${processId}\n${output}`)));
  });
}

async function pngNames(dir) {
  return (await readdir(dir)).filter(name => name.endsWith('.png')).sort();
}

async function renderInvocation({ invocationId, mode, frames, outputDir, receiptPath, scenePath, ocioPath }) {
  const reportPath = resolve(renderEvidenceRoot, `${invocationId}.render.json`);
  const interventionPath = resolve(renderEvidenceRoot, `${invocationId}.intervention.json`);
  await mkdir(outputDir, { recursive: true });
  const renderArgs = [
    '--background', scenePath, '--disable-autoexec', '--python-exit-code', '1',
    '--python', configurator, '--python', renderer, '--',
    '--spec', reviewSpecPath, '--receipt', receiptPath, '--output-dir', outputDir,
    '--report', reportPath, '--mode', mode, '--invocation-id', invocationId,
  ];
  if (mode === 'fresh') renderArgs.push('--frame', String(frames[0]));
  const launched = await run(blender, renderArgs, {
    ...process.env,
    OCIO: ocioPath,
    BFS_B19_DITHER: '0.0',
    BFS_B19_FAST_GI: '1',
    BFS_B19_REPROJECTION: '1',
    BFS_B19_INTERVENTION_REPORT: interventionPath,
  });
  const report = JSON.parse(await readFile(reportPath, 'utf8'));
  const record = { invocationId, mode, frames, outputDir, reportPath, interventionPath, launchProcessId: launched.processId, report };
  process.stdout.write(`BFS_B20_PROCESS_OK ${invocationId} mode=${mode} pid=${launched.processId} frames=${report.frameCount} seconds=${report.totalRenderSeconds}\n`);
  return record;
}

async function validateRun({
  record, expectedSpecSha, expectedReviewSpecSha, expectedBlenderSha, expectedOcioSha, expectedSceneSha,
  expectedRendererSha, expectedConfiguratorSha, expectedSamples = 32, expectedDither = 0,
  expectedFastGi = true, expectedReprojection = true, expectedFrames = record.frames, expectedFrameCount = expectedFrames.length,
}) {
  if (await sha256File(specPath) !== expectedSpecSha) return 'B20_SPEC_SHA';
  if (await sha256File(reviewSpecPath) !== expectedReviewSpecSha) return 'REVIEW_SPEC_SHA';
  if (await sha256File(blender) !== expectedBlenderSha) return 'BLENDER_SHA';
  const receipt = JSON.parse(await readFile(resolve(repositoryRoot, JSON.parse(await readFile(reviewSpecPath, 'utf8')).source.receiptUri), 'utf8'));
  const ocioPath = resolve(repositoryRoot, receipt.executionIdentity.configuration.ocio.uri);
  const scenePath = resolve(repositoryRoot, receipt.run.sceneBlend.uri);
  if (await sha256File(ocioPath) !== expectedOcioSha) return 'OCIO_SHA';
  if (await sha256File(scenePath) !== expectedSceneSha) return 'SCENE_SHA';
  if (await sha256File(renderer) !== expectedRendererSha) return 'RENDERER_SHA';
  if (await sha256File(configurator) !== expectedConfiguratorSha) return 'CONFIGURATOR_SHA';

  const intervention = JSON.parse(await readFile(record.interventionPath, 'utf8'));
  if (intervention.before.ditherIntensity !== 1 || intervention.before.useFastGi !== true || intervention.before.useTaaReprojection !== true) return 'SOURCE_CONTROLS';
  if (intervention.after.ditherIntensity !== expectedDither || intervention.requested.ditherIntensity !== expectedDither) return 'FIXED_DITHER';
  if (intervention.after.useFastGi !== expectedFastGi || intervention.requested.useFastGi !== expectedFastGi) return 'FAST_GI';
  if (intervention.after.useTaaReprojection !== expectedReprojection || intervention.requested.useTaaReprojection !== expectedReprojection) return 'TAA_REPROJECTION';
  if (intervention.savedSourceBlend !== false || intervention.sceneBlendSha256 !== expectedSceneSha) return 'SOURCE_BLEND';

  const report = JSON.parse(await readFile(record.reportPath, 'utf8'));
  if (report.invocationId !== record.invocationId || report.processId !== record.launchProcessId) return 'PROCESS_BINDING';
  if (report.mode !== record.mode) return 'MODE';
  if (report.observedControls.renderSamples !== expectedSamples || report.profile.renderSamples !== expectedSamples) return 'RENDER_SAMPLES';
  if (report.observedControls.ditherIntensity !== expectedDither) return 'FIXED_DITHER';
  if (report.observedControls.useFastGi !== expectedFastGi) return 'FAST_GI';
  if (report.observedControls.useTaaReprojection !== expectedReprojection) return 'TAA_REPROJECTION';
  if (report.source.sceneBlendSha256 !== expectedSceneSha) return 'RENDER_SCENE_SHA';
  if (report.cameraAndTimelineInvariant !== true) return 'CAMERA_TIMELINE_INVARIANT';
  if (JSON.stringify(report.requestedFrames) !== JSON.stringify(expectedFrames) || JSON.stringify(report.frames.map(frame => frame.frame)) !== JSON.stringify(expectedFrames)) return 'FRAME_SCHEDULE';
  if (report.frameCount !== expectedFrameCount || report.frames.length !== expectedFrameCount) return 'FRAME_COUNT';
  if (record.mode === 'fresh' && report.frameCount !== 1) return 'FRESH_SCOPE';
  const observedNames = await pngNames(record.outputDir);
  const expectedNames = report.frames.map(frame => frame.name);
  if (JSON.stringify(observedNames) !== JSON.stringify([...expectedNames].sort())) return 'OUTPUT_FILES';
  for (const frame of report.frames) if (await sha256File(resolve(record.outputDir, frame.name)) !== frame.sha256) return 'FRAME_SHA';
  return 'OK';
}

async function makeManifest({ mode, replicate, records, aggregateDir, sentinels, specSha, tools }) {
  const selected = [];
  for (const frame of sentinels) {
    const path = resolve(aggregateDir, `frame-${String(frame).padStart(4, '0')}.png`);
    selected.push({ frame, name: `frame-${String(frame).padStart(4, '0')}.png`, sha256: await sha256File(path), bytes: (await stat(path)).size });
  }
  const body = {
    documentType: 'BFS_B20_PROCESS_MODE_MANIFEST', version: '0.1.0', mode, replicate,
    b20SpecSha256: specSha, toolIdentities: tools, selectedFrames: sentinels,
    fullTimelineRendered: mode === 'HISTORY', totalRenderedFrames: records.reduce((sum, record) => sum + record.report.frameCount, 0),
    invocations: records.map(record => ({ invocationId: record.invocationId, processId: record.launchProcessId, renderReportSha256: null, interventionReportSha256: null })),
    frames: selected,
  };
  for (let index = 0; index < records.length; index += 1) {
    body.invocations[index].renderReportSha256 = await sha256File(records[index].reportPath);
    body.invocations[index].interventionReportSha256 = await sha256File(records[index].interventionPath);
  }
  return { ...body, manifestHash: sha256Canonical(body) };
}

async function validateManifest({ manifestPath, dir, expectedSpecSha, expectedRendererSha, expectedComparatorSha, expectedConfiguratorSha, expectedSentinels }) {
  const manifest = JSON.parse(await readFile(manifestPath, 'utf8'));
  const body = structuredClone(manifest); delete body.manifestHash;
  if (sha256Canonical(body) !== manifest.manifestHash) return 'MANIFEST_SELF_HASH';
  if (manifest.b20SpecSha256 !== expectedSpecSha) return 'MANIFEST_SPEC_BINDING';
  if (manifest.toolIdentities.rendererSha256 !== expectedRendererSha || manifest.toolIdentities.comparatorSha256 !== expectedComparatorSha || manifest.toolIdentities.configuratorSha256 !== expectedConfiguratorSha) return 'MANIFEST_TOOL_BINDING';
  if (JSON.stringify(manifest.selectedFrames) !== JSON.stringify(expectedSentinels)) return 'SENTINEL_SET';
  const observedNames = await pngNames(dir);
  const expectedNames = manifest.frames.map(frame => frame.name).sort();
  if (expectedNames.some(name => !observedNames.includes(name))) return 'MISSING_SENTINEL';
  for (const frame of manifest.frames) if (await sha256File(resolve(dir, frame.name)) !== frame.sha256) return 'IMAGE_SHA';
  return 'OK';
}

async function validateLedger(ledger, expectedCount = 39) {
  const body = structuredClone(ledger); delete body.ledgerHash;
  if (sha256Canonical(body) !== ledger.ledgerHash) return 'LEDGER_SELF_HASH';
  if (ledger.processes.length !== expectedCount) return 'PROCESS_COUNT';
  if (new Set(ledger.processes.map(record => record.invocationId)).size !== ledger.processes.length) return 'INVOCATION_ALIAS';
  if (new Set(ledger.processes.map(record => record.processId)).size !== ledger.processes.length) return 'PROCESS_ALIAS';
  return 'OK';
}

async function validateComparison({ bindingPath, comparisonPath, aManifest, bManifest, expectedComparatorSha, sentinels }) {
  if (await sha256File(comparator) !== expectedComparatorSha) return 'COMPARATOR_SHA';
  const binding = JSON.parse(await readFile(bindingPath, 'utf8'));
  const body = structuredClone(binding); delete body.bindingHash;
  if (sha256Canonical(body) !== binding.bindingHash) return 'COMPARISON_SELF_HASH';
  if (binding.aManifestHash !== aManifest.manifestHash || binding.bManifestHash !== bManifest.manifestHash) return 'COMPARISON_MANIFEST_BINDING';
  if (binding.comparisonSha256 !== await sha256File(comparisonPath)) return 'COMPARISON_SHA';
  const comparison = JSON.parse(await readFile(comparisonPath, 'utf8'));
  if (JSON.stringify(comparison.selectedFrames) !== JSON.stringify(sentinels) || comparison.frameCount !== sentinels.length) return 'COMPARISON_FRAME_SET';
  const aByFrame = new Map(aManifest.frames.map(frame => [frame.frame, frame]));
  const bByFrame = new Map(bManifest.frames.map(frame => [frame.frame, frame]));
  for (const frame of comparison.frames) if (frame.aSha256 !== aByFrame.get(frame.frame).sha256 || frame.bSha256 !== bByFrame.get(frame.frame).sha256) return 'COMPARISON_IMAGE_BINDING';
  return 'OK';
}

await rm(evidenceRoot, { recursive: true, force: true });
await rm(workRoot, { recursive: true, force: true });
await mkdir(renderEvidenceRoot, { recursive: true });
await mkdir(comparisonEvidenceRoot, { recursive: true });

const spec = JSON.parse(await readFile(specPath, 'utf8'));
const specSha = await sha256File(specPath);
if (specSha !== 'b59908f4ffcd3f4bf67f3c04f490df48b626e9d969fd31c3277b88b2f49fbedf') throw new Error('B20 spec changed after pre-registration');
const reviewSpec = JSON.parse(await readFile(reviewSpecPath, 'utf8'));
const receiptPath = resolve(repositoryRoot, reviewSpec.source.receiptUri);
const receipt = JSON.parse(await readFile(receiptPath, 'utf8'));
const scenePath = resolve(repositoryRoot, receipt.run.sceneBlend.uri);
const ocioPath = resolve(repositoryRoot, receipt.executionIdentity.configuration.ocio.uri);
const frozen = spec.frozenIdentity;
for (const [path, expected, label] of [
  [reviewSpecPath, frozen.reviewRenderSpecSha256, 'ReviewRenderSpec'], [configurator, frozen.b19ConfiguratorSha256, 'configurator'],
  [blender, frozen.blenderSha256, 'Blender'], [scenePath, frozen.sceneBlendSha256, 'scene'], [ocioPath, frozen.ocioSha256, 'OCIO'],
]) if (await sha256File(path) !== expected) throw new Error(`${label} frozen SHA mismatch`);

const sentinels = spec.evidenceBasis.sentinelFrames;
const historyFrames = Array.from({ length: 144 }, (_, index) => index + 1);
const toolIdentities = {
  rendererSha256: await sha256File(renderer), comparatorSha256: await sha256File(comparator),
  configuratorSha256: await sha256File(configurator), runnerSha256: await sha256File(runner),
};
const records = new Map();
const replicateRecords = new Map();
for (const letter of ['A', 'B', 'C']) {
  const historyId = `H-${letter}`, historyDir = resolve(workRoot, historyId);
  const historyRecord = await renderInvocation({ invocationId: historyId, mode: 'history', frames: historyFrames, outputDir: historyDir, receiptPath, scenePath, ocioPath });
  const historyReason = await validateRun({ record: historyRecord, expectedSpecSha: specSha, expectedReviewSpecSha: frozen.reviewRenderSpecSha256, expectedBlenderSha: frozen.blenderSha256, expectedOcioSha: frozen.ocioSha256, expectedSceneSha: frozen.sceneBlendSha256, expectedRendererSha: toolIdentities.rendererSha256, expectedConfiguratorSha: toolIdentities.configuratorSha256 });
  if (historyReason !== 'OK') throw new Error(`${historyId} invalid: ${historyReason}`);
  records.set(historyId, historyRecord); replicateRecords.set(historyId, [historyRecord]);

  const freshReplicateId = `F-${letter}`, aggregateDir = resolve(workRoot, freshReplicateId), freshRecords = [];
  await mkdir(aggregateDir, { recursive: true });
  for (const frame of sentinels) {
    const invocationId = `${freshReplicateId}-${String(frame).padStart(4, '0')}`;
    const invocationDir = resolve(workRoot, 'fresh-invocations', invocationId);
    const freshRecord = await renderInvocation({ invocationId, mode: 'fresh', frames: [frame], outputDir: invocationDir, receiptPath, scenePath, ocioPath });
    const freshReason = await validateRun({ record: freshRecord, expectedSpecSha: specSha, expectedReviewSpecSha: frozen.reviewRenderSpecSha256, expectedBlenderSha: frozen.blenderSha256, expectedOcioSha: frozen.ocioSha256, expectedSceneSha: frozen.sceneBlendSha256, expectedRendererSha: toolIdentities.rendererSha256, expectedConfiguratorSha: toolIdentities.configuratorSha256 });
    if (freshReason !== 'OK') throw new Error(`${invocationId} invalid: ${freshReason}`);
    await copyFile(resolve(invocationDir, `frame-${String(frame).padStart(4, '0')}.png`), resolve(aggregateDir, `frame-${String(frame).padStart(4, '0')}.png`));
    records.set(invocationId, freshRecord); freshRecords.push(freshRecord);
  }
  replicateRecords.set(freshReplicateId, freshRecords);
}

const ledgerBody = {
  documentType: 'BFS_B20_PROCESS_LEDGER', version: '0.1.0', b20SpecSha256: specSha,
  processes: [...records.values()].map(record => ({ invocationId: record.invocationId, mode: record.mode, processId: record.launchProcessId, frames: record.frames, renderReportSha256: null })),
};
for (const processRecord of ledgerBody.processes) processRecord.renderReportSha256 = await sha256File(records.get(processRecord.invocationId).reportPath);
const ledger = { ...ledgerBody, ledgerHash: sha256Canonical(ledgerBody) };
if (await validateLedger(ledger) !== 'OK') throw new Error(`Process ledger invalid: ${await validateLedger(ledger)}`);
const ledgerPath = resolve(evidenceRoot, 'process-ledger.json'); await writeFile(ledgerPath, serialize(ledger));

const manifests = new Map();
for (const mode of ['HISTORY', 'FRESH']) for (const letter of ['A', 'B', 'C']) {
  const replicate = `${mode === 'HISTORY' ? 'H' : 'F'}-${letter}`, aggregateDir = resolve(workRoot, replicate);
  const manifest = await makeManifest({ mode, replicate, records: replicateRecords.get(replicate), aggregateDir, sentinels, specSha, tools: toolIdentities });
  const manifestPath = resolve(evidenceRoot, `${replicate}.manifest.json`); await writeFile(manifestPath, serialize(manifest));
  const reason = await validateManifest({ manifestPath, dir: aggregateDir, expectedSpecSha: specSha, expectedRendererSha: toolIdentities.rendererSha256, expectedComparatorSha: toolIdentities.comparatorSha256, expectedConfiguratorSha: toolIdentities.configuratorSha256, expectedSentinels: sentinels });
  if (reason !== 'OK') throw new Error(`${replicate} manifest invalid: ${reason}`);
  manifests.set(replicate, { manifest, manifestPath, dir: aggregateDir });
}

const pairDefinitions = [];
for (const prefix of ['H', 'F']) for (const [a, b] of [['A', 'B'], ['A', 'C'], ['B', 'C']]) pairDefinitions.push({ id: `${prefix}-${a}_${prefix}-${b}`, kind: prefix === 'H' ? 'WITHIN_HISTORY' : 'WITHIN_FRESH', a: `${prefix}-${a}`, b: `${prefix}-${b}` });
for (const h of ['A', 'B', 'C']) for (const f of ['A', 'B', 'C']) pairDefinitions.push({ id: `H-${h}_F-${f}`, kind: 'CROSS_MODE', a: `H-${h}`, b: `F-${f}` });
const comparisons = new Map();
for (const pair of pairDefinitions) {
  const comparisonPath = resolve(comparisonEvidenceRoot, `${pair.id}.comparison.json`), bindingPath = resolve(comparisonEvidenceRoot, `${pair.id}.binding.json`);
  await run(blender, ['--factory-startup', '--background', '--python-exit-code', '1', '--python', comparator, '--', '--a-dir', manifests.get(pair.a).dir, '--b-dir', manifests.get(pair.b).dir, '--frames', sentinels.join(','), '--output', comparisonPath]);
  const comparison = JSON.parse(await readFile(comparisonPath, 'utf8'));
  const bindingBody = { documentType: 'BFS_B20_COMPARISON_BINDING', version: '0.1.0', pairId: pair.id, kind: pair.kind, aReplicate: pair.a, bReplicate: pair.b, aManifestHash: manifests.get(pair.a).manifest.manifestHash, bManifestHash: manifests.get(pair.b).manifest.manifestHash, comparatorSha256: toolIdentities.comparatorSha256, comparisonSha256: await sha256File(comparisonPath) };
  const binding = { ...bindingBody, bindingHash: sha256Canonical(bindingBody) }; await writeFile(bindingPath, serialize(binding));
  const reason = await validateComparison({ bindingPath, comparisonPath, aManifest: manifests.get(pair.a).manifest, bManifest: manifests.get(pair.b).manifest, expectedComparatorSha: toolIdentities.comparatorSha256, sentinels });
  if (reason !== 'OK') throw new Error(`${pair.id} comparison invalid: ${reason}`);
  comparisons.set(pair.id, { ...pair, comparison, comparisonPath, binding, bindingPath });
}

const attackRecord = records.get('H-A');
const defaults = { record: attackRecord, expectedSpecSha: specSha, expectedReviewSpecSha: frozen.reviewRenderSpecSha256, expectedBlenderSha: frozen.blenderSha256, expectedOcioSha: frozen.ocioSha256, expectedSceneSha: frozen.sceneBlendSha256, expectedRendererSha: toolIdentities.rendererSha256, expectedConfiguratorSha: toolIdentities.configuratorSha256 };
const attacks = []; const recordAttack = (id, expected, observed) => attacks.push({ id, expectedReason: expected, observedReason: observed, pass: observed === expected });
recordAttack('N_B20_SPEC_SHA', 'B20_SPEC_SHA', await validateRun({ ...defaults, expectedSpecSha: '0'.repeat(64) }));
recordAttack('N_REVIEW_SPEC_SHA', 'REVIEW_SPEC_SHA', await validateRun({ ...defaults, expectedReviewSpecSha: '0'.repeat(64) }));
recordAttack('N_BLENDER_SHA', 'BLENDER_SHA', await validateRun({ ...defaults, expectedBlenderSha: '0'.repeat(64) }));
recordAttack('N_OCIO_SHA', 'OCIO_SHA', await validateRun({ ...defaults, expectedOcioSha: '0'.repeat(64) }));
recordAttack('N_SCENE_SHA', 'SCENE_SHA', await validateRun({ ...defaults, expectedSceneSha: '0'.repeat(64) }));
recordAttack('N_RENDERER_SHA', 'RENDERER_SHA', await validateRun({ ...defaults, expectedRendererSha: '0'.repeat(64) }));
recordAttack('N_CONFIGURATOR_SHA', 'CONFIGURATOR_SHA', await validateRun({ ...defaults, expectedConfiguratorSha: '0'.repeat(64) }));
recordAttack('N_RENDER_SAMPLES', 'RENDER_SAMPLES', await validateRun({ ...defaults, expectedSamples: 31 }));
recordAttack('N_DITHER', 'FIXED_DITHER', await validateRun({ ...defaults, expectedDither: 1 }));
recordAttack('N_FAST_GI', 'FAST_GI', await validateRun({ ...defaults, expectedFastGi: false }));
recordAttack('N_REPROJECTION', 'TAA_REPROJECTION', await validateRun({ ...defaults, expectedReprojection: false }));
recordAttack('N_HISTORY_ORDER', 'FRAME_SCHEDULE', await validateRun({ ...defaults, expectedFrames: [...historyFrames].reverse() }));
const freshAttackRecord = records.get('F-A-0001');
recordAttack('N_FRESH_SCOPE', 'FRAME_COUNT', await validateRun({ ...defaults, record: freshAttackRecord, expectedFrames: [1], expectedFrameCount: 2 }));
const aliasBody = structuredClone(ledgerBody); aliasBody.processes[1].processId = aliasBody.processes[0].processId; const aliasLedger = { ...aliasBody, ledgerHash: sha256Canonical(aliasBody) };
recordAttack('N_PROCESS_ALIAS', 'PROCESS_ALIAS', await validateLedger(aliasLedger));
const attackRoot = resolve(workRoot, 'attacks'); await mkdir(attackRoot, { recursive: true });
async function copySentinels(target) { await mkdir(target, { recursive: true }); for (const frame of sentinels) { const name = `frame-${String(frame).padStart(4, '0')}.png`; await copyFile(resolve(manifests.get('H-A').dir, name), resolve(target, name)); } }
const missingDir = resolve(attackRoot, 'missing'); await copySentinels(missingDir); await unlink(resolve(missingDir, 'frame-0110.png'));
recordAttack('N_MISSING_SENTINEL', 'MISSING_SENTINEL', await validateManifest({ manifestPath: manifests.get('H-A').manifestPath, dir: missingDir, expectedSpecSha: specSha, expectedRendererSha: toolIdentities.rendererSha256, expectedComparatorSha: toolIdentities.comparatorSha256, expectedConfiguratorSha: toolIdentities.configuratorSha256, expectedSentinels: sentinels }));
const mutatedDir = resolve(attackRoot, 'mutated'); await copySentinels(mutatedDir); await appendFile(resolve(mutatedDir, 'frame-0110.png'), Buffer.from([0]));
recordAttack('N_MUTATED_SENTINEL', 'IMAGE_SHA', await validateManifest({ manifestPath: manifests.get('H-A').manifestPath, dir: mutatedDir, expectedSpecSha: specSha, expectedRendererSha: toolIdentities.rendererSha256, expectedComparatorSha: toolIdentities.comparatorSha256, expectedConfiguratorSha: toolIdentities.configuratorSha256, expectedSentinels: sentinels }));
const comparisonAttack = comparisons.get('H-A_H-B'), attackedBindingBody = structuredClone(comparisonAttack.binding); delete attackedBindingBody.bindingHash; attackedBindingBody.aManifestHash = '0'.repeat(64); const attackedBinding = { ...attackedBindingBody, bindingHash: sha256Canonical(attackedBindingBody) }, attackedBindingPath = resolve(attackRoot, 'comparison-binding.json'); await writeFile(attackedBindingPath, serialize(attackedBinding));
recordAttack('N_COMPARISON_BINDING', 'COMPARISON_MANIFEST_BINDING', await validateComparison({ bindingPath: attackedBindingPath, comparisonPath: comparisonAttack.comparisonPath, aManifest: manifests.get('H-A').manifest, bManifest: manifests.get('H-B').manifest, expectedComparatorSha: toolIdentities.comparatorSha256, sentinels }));
recordAttack('N_COMPARATOR_SHA', 'COMPARATOR_SHA', await validateComparison({ bindingPath: comparisonAttack.bindingPath, comparisonPath: comparisonAttack.comparisonPath, aManifest: manifests.get('H-A').manifest, bManifest: manifests.get('H-B').manifest, expectedComparatorSha: '0'.repeat(64), sentinels }));

function summarize(kind) {
  const selected = [...comparisons.values()].filter(item => item.kind === kind);
  const expectedPairCount = kind === 'CROSS_MODE' ? 9 : 3;
  const totalFrameComparisons = selected.reduce((sum, item) => sum + item.comparison.frameCount, 0);
  const exactFrameComparisons = selected.reduce((sum, item) => sum + item.comparison.decodedPixelExactFrames, 0);
  return {
    pairCount: selected.length, expectedPairCount, totalFrameComparisons, exactFrameComparisons,
    maximumAbsoluteError: Math.max(...selected.map(item => item.comparison.maximumAbsoluteError)),
    totalFailurePixels: selected.reduce((sum, item) => sum + item.comparison.totalFailurePixels, 0),
    exact: selected.length === expectedPairCount && exactFrameComparisons === expectedPairCount * sentinels.length && selected.every(item => item.comparison.maximumAbsoluteError === 0 && item.comparison.totalFailurePixels === 0),
  };
}
const history = summarize('WITHIN_HISTORY'), fresh = summarize('WITHIN_FRESH'), cross = summarize('CROSS_MODE');
const validExperiment = attacks.length >= 17 && attacks.every(attack => attack.pass) && await validateLedger(ledger) === 'OK';
let decision = 'PROCESS_ISOLATION_NOT_SUFFICIENT';
if (!validExperiment) decision = 'INVALID_EXPERIMENT';
else if (fresh.exact && !history.exact) decision = 'FRESH_PROCESS_RESTORES_EXACTNESS';
else if (history.exact && !fresh.exact) decision = 'HISTORY_PROCESS_ONLY_EXACT';
else if (history.exact && fresh.exact && cross.exact) decision = 'NO_HISTORY_EFFECT_DETECTED';
else if (history.exact && fresh.exact && !cross.exact) decision = 'DETERMINISTIC_HISTORY_EFFECT';
const result = {
  documentType: 'BFS_B20_PROCESS_HISTORY_ISOLATION_EXPERIMENT', version: '0.1.0', executedAtUtc: new Date().toISOString(),
  decision, validExperiment, sentinels, design: spec.design, identities: { ...frozen, b20SpecSha256: specSha, ...toolIdentities },
  modes: { HISTORY: history, FRESH: fresh }, crossMode: cross, processLedger: { processCount: ledger.processes.length, uniqueProcessIds: new Set(ledger.processes.map(item => item.processId)).size, ledgerHash: ledger.ledgerHash, uri: repoUri(ledgerPath) },
  comparisons: Object.fromEntries([...comparisons.entries()].map(([id, item]) => [id, { kind: item.kind, a: item.a, b: item.b, decodedPixelExactFrames: item.comparison.decodedPixelExactFrames, frameCount: item.comparison.frameCount, maximumAbsoluteError: item.comparison.maximumAbsoluteError, totalFailurePixels: item.comparison.totalFailurePixels, comparisonUri: repoUri(item.comparisonPath), bindingHash: item.binding.bindingHash }])),
  attacks, artifacts: { manifests: Object.fromEntries([...manifests.entries()].map(([id, item]) => [id, repoUri(item.manifestPath)])), comparisons: repoUri(comparisonEvidenceRoot), renders: repoUri(renderEvidenceRoot) }, nonClaims: spec.explicitNonClaims,
};
await writeFile(resolve(root, 'results.json'), serialize(result));
process.stdout.write(`BFS_B20_PROCESS_HISTORY ${decision} HISTORY=${history.exactFrameComparisons}/${history.totalFrameComparisons} FRESH=${fresh.exactFrameComparisons}/${fresh.totalFrameComparisons} CROSS=${cross.exactFrameComparisons}/${cross.totalFrameComparisons} pids=${ledger.processes.length}/${ledger.processes.length} attacks=${attacks.filter(attack => attack.pass).length}/${attacks.length}\n`);
if (!validExperiment) process.exitCode = 1;
