import { appendFile, copyFile, mkdir, readFile, readdir, rm, unlink, writeFile } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { relative, resolve, sep } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256Canonical, sha256File } from './lib/receipt-format.mjs';

const root = resolve(repositoryRoot, 'experiments/dual-output-localization-v0-1');
const evidence = resolve(root, 'evidence'), renderEvidence = resolve(evidence, 'renders'), comparisonEvidence = resolve(evidence, 'comparisons'), work = resolve(root, 'work');
const specPath = resolve(repositoryRoot, 'specs/dual-output-localization-spec.v0.1.json');
const b20ResultPath = resolve(repositoryRoot, 'experiments/eevee-process-history-isolation-v0-1/results.json');
const inventoryPath = resolve(repositoryRoot, 'experiments/render-result-float-inventory-v0-1/results.json');
const reviewSpecPath = resolve(repositoryRoot, 'specs/review-render-spec.v0.1.json');
const renderer = resolve(repositoryRoot, 'blender/render_dual_output_localization.py');
const comparator = resolve(repositoryRoot, 'blender/compare_dual_outputs.py');
const configurator = resolve(repositoryRoot, 'blender/configure_gi_reprojection_factorial.py');
const runner = fileURLToPath(import.meta.url);
const blender = resolve(process.env.BLENDER_BIN || '/Applications/Blender.app/Contents/MacOS/Blender');
const serialize = value => `${JSON.stringify(value, null, 2)}\n`;
const repoUri = path => relative(repositoryRoot, path).split(sep).join('/');

function run(command, args, env = process.env) {
  return new Promise((resolvePromise, reject) => {
    const child = spawn(command, args, { cwd: repositoryRoot, env, stdio: ['ignore', 'pipe', 'pipe'] });
    const processId = child.pid; let output = '';
    child.stdout.on('data', chunk => { output += chunk; }); child.stderr.on('data', chunk => { output += chunk; }); child.on('error', reject);
    child.on('close', code => code === 0 ? resolvePromise({ processId, output }) : reject(new Error(`${command} failed (${code}) pid=${processId}\n${output}`)));
  });
}

async function renderOne({ invocationId, frame, outputDir, receiptPath, scenePath, ocioPath }) {
  await mkdir(outputDir, { recursive: true });
  const reportPath = resolve(renderEvidence, `${invocationId}.render.json`), interventionPath = resolve(renderEvidence, `${invocationId}.intervention.json`);
  const launched = await run(blender, ['--background', scenePath, '--disable-autoexec', '--python-exit-code', '1', '--python', configurator, '--python', renderer, '--', '--spec', reviewSpecPath, '--receipt', receiptPath, '--output-dir', outputDir, '--report', reportPath, '--frame', String(frame), '--invocation-id', invocationId], { ...process.env, OCIO: ocioPath, BFS_B19_DITHER: '0.0', BFS_B19_FAST_GI: '1', BFS_B19_REPROJECTION: '1', BFS_B19_INTERVENTION_REPORT: interventionPath });
  const report = JSON.parse(await readFile(reportPath, 'utf8'));
  process.stdout.write(`BFS_B21_PROCESS_OK ${invocationId} pid=${launched.processId} seconds=${report.totalSeconds}\n`);
  return { invocationId, frame, outputDir, reportPath, interventionPath, processId: launched.processId, report };
}

async function validateRun({ record, identities, expectedSpecSha, expectedB20Sha, expectedInventorySha, expectedSamples = 32, expectedDither = 0, expectedGi = true, expectedReprojection = true, expectedRenderCalls = 1, expectedSaves = 2, expectedExrFormat = 'float', expectedPngFormat = 'uint8' }) {
  if (await sha256File(specPath) !== expectedSpecSha) return 'B21_SPEC_SHA';
  if (await sha256File(b20ResultPath) !== expectedB20Sha) return 'B20_RESULT_SHA';
  if (await sha256File(inventoryPath) !== expectedInventorySha) return 'FLOAT_INVENTORY_SHA';
  if (await sha256File(reviewSpecPath) !== identities.reviewRenderSpecSha256) return 'REVIEW_SPEC_SHA';
  if (await sha256File(blender) !== identities.blenderSha256) return 'BLENDER_SHA';
  if (await sha256File(identities.ocioPath) !== identities.ocioSha256) return 'OCIO_SHA';
  if (await sha256File(identities.scenePath) !== identities.sceneBlendSha256) return 'SCENE_SHA';
  if (await sha256File(renderer) !== identities.rendererSha256) return 'RENDERER_SHA';
  if (await sha256File(configurator) !== identities.configuratorSha256) return 'CONFIGURATOR_SHA';
  const intervention = JSON.parse(await readFile(record.interventionPath, 'utf8'));
  if (intervention.after.ditherIntensity !== expectedDither) return 'FIXED_DITHER';
  if (intervention.after.useFastGi !== expectedGi) return 'FAST_GI';
  if (intervention.after.useTaaReprojection !== expectedReprojection) return 'TAA_REPROJECTION';
  const report = JSON.parse(await readFile(record.reportPath, 'utf8'));
  if (report.processId !== record.processId || report.invocationId !== record.invocationId || report.frame !== record.frame) return 'PROCESS_BINDING';
  if (report.observedControls.renderSamples !== expectedSamples) return 'RENDER_SAMPLES';
  if (report.observedControls.ditherIntensity !== expectedDither) return 'FIXED_DITHER';
  if (report.observedControls.useFastGi !== expectedGi) return 'FAST_GI';
  if (report.observedControls.useTaaReprojection !== expectedReprojection) return 'TAA_REPROJECTION';
  if (report.renderOperatorCallCount !== expectedRenderCalls) return 'RENDER_CALL_COUNT';
  if (report.saveCount !== expectedSaves || report.sameRenderResultWithoutRerender !== true || report.directImagePixelsAccessed !== false) return 'SAVE_COUNT';
  if (report.source.sceneBlendSha256 !== identities.sceneBlendSha256 || report.savedSourceBlend !== false) return 'SOURCE_BLEND';
  if (report.cameraAndTimelineInvariant !== true) return 'CAMERA_TIMELINE_INVARIANT';
  const exr = report.outputs.EXR32_SCENE_LINEAR, png = report.outputs.PNG8_DISPLAY;
  if (JSON.stringify(exr.decoded) !== JSON.stringify({ width: 960, height: 540, channels: ['R', 'G', 'B', 'A'], pixelFormat: expectedExrFormat })) return 'EXR_LAYOUT';
  if (JSON.stringify(png.decoded) !== JSON.stringify({ width: 960, height: 540, channels: ['R', 'G', 'B', 'A'], pixelFormat: expectedPngFormat })) return 'PNG_LAYOUT';
  for (const output of [exr, png]) if (await sha256File(resolve(record.outputDir, output.name)) !== output.sha256) return 'OUTPUT_SHA';
  return 'OK';
}

async function makeManifest({ replicate, records, dir, specSha, tools, sentinels }) {
  const frames = [];
  for (const frame of sentinels) {
    const base = `frame-${String(frame).padStart(4, '0')}`;
    frames.push({ frame, png: { name: `${base}.png`, sha256: await sha256File(resolve(dir, `${base}.png`)) }, exr: { name: `${base}.exr`, sha256: await sha256File(resolve(dir, `${base}.exr`)) } });
  }
  const body = { documentType: 'BFS_B21_DUAL_OUTPUT_MANIFEST', version: '0.1.0', replicate, b21SpecSha256: specSha, toolIdentities: tools, selectedFrames: sentinels, invocations: records.map(record => ({ invocationId: record.invocationId, processId: record.processId, renderReportSha256: null, interventionReportSha256: null })), frames };
  for (let i = 0; i < records.length; i += 1) { body.invocations[i].renderReportSha256 = await sha256File(records[i].reportPath); body.invocations[i].interventionReportSha256 = await sha256File(records[i].interventionPath); }
  return { ...body, manifestHash: sha256Canonical(body) };
}

async function validateManifest({ path, dir, expectedSpecSha, tools, sentinels }) {
  const manifest = JSON.parse(await readFile(path, 'utf8')), body = structuredClone(manifest); delete body.manifestHash;
  if (sha256Canonical(body) !== manifest.manifestHash) return 'MANIFEST_SELF_HASH';
  if (manifest.b21SpecSha256 !== expectedSpecSha) return 'MANIFEST_SPEC_BINDING';
  if (JSON.stringify(manifest.toolIdentities) !== JSON.stringify(tools)) return 'MANIFEST_TOOL_BINDING';
  if (JSON.stringify(manifest.selectedFrames) !== JSON.stringify(sentinels)) return 'SENTINEL_SET';
  const names = await readdir(dir);
  for (const frame of manifest.frames) {
    if (!names.includes(frame.png.name) || !names.includes(frame.exr.name)) return 'MISSING_PARTNER';
    if (await sha256File(resolve(dir, frame.png.name)) !== frame.png.sha256 || await sha256File(resolve(dir, frame.exr.name)) !== frame.exr.sha256) return 'OUTPUT_SHA';
  }
  return 'OK';
}

async function validateComparison({ bindingPath, comparisonPath, a, b, expectedComparatorSha, extension, sentinels }) {
  if (await sha256File(comparator) !== expectedComparatorSha) return 'COMPARATOR_SHA';
  const binding = JSON.parse(await readFile(bindingPath, 'utf8')), body = structuredClone(binding); delete body.bindingHash;
  if (sha256Canonical(body) !== binding.bindingHash) return 'COMPARISON_SELF_HASH';
  if (binding.aManifestHash !== a.manifestHash || binding.bManifestHash !== b.manifestHash) return 'COMPARISON_MANIFEST_BINDING';
  if (binding.comparisonSha256 !== await sha256File(comparisonPath)) return 'COMPARISON_SHA';
  const comparison = JSON.parse(await readFile(comparisonPath, 'utf8'));
  if (comparison.extension !== extension || comparison.frameCount !== 12 || JSON.stringify(comparison.selectedFrames) !== JSON.stringify(sentinels)) return 'COMPARISON_FORMAT';
  for (const item of comparison.frames) {
    const af = a.frames.find(frame => frame.frame === item.frame), bf = b.frames.find(frame => frame.frame === item.frame), key = extension === '.png' ? 'png' : 'exr';
    if (item.aSha256 !== af[key].sha256 || item.bSha256 !== bf[key].sha256) return 'COMPARISON_FILE_BINDING';
  }
  return 'OK';
}

await rm(evidence, { recursive: true, force: true }); await rm(work, { recursive: true, force: true }); await mkdir(renderEvidence, { recursive: true }); await mkdir(comparisonEvidence, { recursive: true });
const spec = JSON.parse(await readFile(specPath, 'utf8')), specSha = await sha256File(specPath);
if (specSha !== '3f7aa6beabb1f7904986395f5a11a8a8e83cdc18fcd83caacf843980d812cda6') throw new Error('B21 spec changed after pre-registration');
const reviewSpec = JSON.parse(await readFile(reviewSpecPath, 'utf8')), receiptPath = resolve(repositoryRoot, reviewSpec.source.receiptUri), receipt = JSON.parse(await readFile(receiptPath, 'utf8'));
const scenePath = resolve(repositoryRoot, receipt.run.sceneBlend.uri), ocioPath = resolve(repositoryRoot, receipt.executionIdentity.configuration.ocio.uri), frozen = spec.frozenIdentity;
for (const [path, expected, label] of [[b20ResultPath, spec.evidenceBasis.b20ResultsSha256, 'B20 result'], [inventoryPath, spec.evidenceBasis.floatInventorySha256, 'inventory'], [reviewSpecPath, frozen.reviewRenderSpecSha256, 'review spec'], [configurator, frozen.configuratorSha256, 'configurator'], [blender, frozen.blenderSha256, 'Blender'], [ocioPath, frozen.ocioSha256, 'OCIO'], [scenePath, frozen.sceneBlendSha256, 'scene']]) if (await sha256File(path) !== expected) throw new Error(`${label} SHA mismatch`);
const tools = { rendererSha256: await sha256File(renderer), comparatorSha256: await sha256File(comparator), configuratorSha256: await sha256File(configurator), runnerSha256: await sha256File(runner) };
const identities = { ...frozen, ...tools, ocioPath, scenePath };
const sentinels = spec.design.sentinelFrames, records = new Map(), byReplicate = new Map([['A', []], ['B', []], ['C', []]]), aggregate = new Map();
for (const replicate of ['A', 'B', 'C']) { const dir = resolve(work, replicate); await mkdir(dir, { recursive: true }); aggregate.set(replicate, dir); }
for (const invocationId of spec.design.runOrder) {
  const match = /^D-(\d{4})-([ABC])$/.exec(invocationId); if (!match) throw new Error(`Bad run id ${invocationId}`);
  const frame = Number(match[1]), replicate = match[2], dir = resolve(work, 'invocations', invocationId);
  const record = await renderOne({ invocationId, frame, outputDir: dir, receiptPath, scenePath, ocioPath });
  const reason = await validateRun({ record, identities, expectedSpecSha: specSha, expectedB20Sha: spec.evidenceBasis.b20ResultsSha256, expectedInventorySha: spec.evidenceBasis.floatInventorySha256 }); if (reason !== 'OK') throw new Error(`${invocationId}: ${reason}`);
  for (const extension of ['.png', '.exr']) await copyFile(resolve(dir, `frame-${match[1]}${extension}`), resolve(aggregate.get(replicate), `frame-${match[1]}${extension}`));
  records.set(invocationId, record); byReplicate.get(replicate).push(record);
}
const ledgerBody = { documentType: 'BFS_B21_PROCESS_LEDGER', version: '0.1.0', b21SpecSha256: specSha, processes: [...records.values()].map(record => ({ invocationId: record.invocationId, processId: record.processId, frame: record.frame, reportSha256: null })) };
for (const item of ledgerBody.processes) item.reportSha256 = await sha256File(records.get(item.invocationId).reportPath);
const ledger = { ...ledgerBody, ledgerHash: sha256Canonical(ledgerBody) };
if (new Set(ledger.processes.map(item => item.processId)).size !== 36) throw new Error('B21 render PIDs are not unique');
const ledgerPath = resolve(evidence, 'process-ledger.json'); await writeFile(ledgerPath, serialize(ledger));
const manifests = new Map();
for (const replicate of ['A', 'B', 'C']) { const manifest = await makeManifest({ replicate, records: byReplicate.get(replicate), dir: aggregate.get(replicate), specSha, tools, sentinels }), path = resolve(evidence, `${replicate}.manifest.json`); await writeFile(path, serialize(manifest)); const reason = await validateManifest({ path, dir: aggregate.get(replicate), expectedSpecSha: specSha, tools, sentinels }); if (reason !== 'OK') throw new Error(`Manifest ${replicate}: ${reason}`); manifests.set(replicate, { manifest, path, dir: aggregate.get(replicate) }); }

const comparisons = new Map();
for (const extension of ['.png', '.exr']) for (const [aId, bId] of [['A', 'B'], ['A', 'C'], ['B', 'C']]) {
  const format = extension === '.png' ? 'PNG8_DISPLAY' : 'EXR32_SCENE_LINEAR', id = `${format}-${aId}-${bId}`, comparisonPath = resolve(comparisonEvidence, `${id}.comparison.json`), bindingPath = resolve(comparisonEvidence, `${id}.binding.json`);
  await run(blender, ['--factory-startup', '--background', '--python-exit-code', '1', '--python', comparator, '--', '--a-dir', aggregate.get(aId), '--b-dir', aggregate.get(bId), '--frames', sentinels.join(','), '--extension', extension, '--output', comparisonPath]);
  const comparison = JSON.parse(await readFile(comparisonPath, 'utf8')), body = { documentType: 'BFS_B21_COMPARISON_BINDING', version: '0.1.0', id, format, aReplicate: aId, bReplicate: bId, aManifestHash: manifests.get(aId).manifest.manifestHash, bManifestHash: manifests.get(bId).manifest.manifestHash, comparatorSha256: tools.comparatorSha256, comparisonSha256: await sha256File(comparisonPath) }, binding = { ...body, bindingHash: sha256Canonical(body) }; await writeFile(bindingPath, serialize(binding));
  const reason = await validateComparison({ bindingPath, comparisonPath, a: manifests.get(aId).manifest, b: manifests.get(bId).manifest, expectedComparatorSha: tools.comparatorSha256, extension, sentinels }); if (reason !== 'OK') throw new Error(`${id}: ${reason}`);
  comparisons.set(id, { id, format, extension, aId, bId, comparison, comparisonPath, bindingPath, binding });
}

const attacks = [], attack = (id, expected, observed) => attacks.push({ id, expectedReason: expected, observedReason: observed, pass: expected === observed });
const baseRecord = records.get('D-0001-A'), defaults = { record: baseRecord, identities, expectedSpecSha: specSha, expectedB20Sha: spec.evidenceBasis.b20ResultsSha256, expectedInventorySha: spec.evidenceBasis.floatInventorySha256 };
attack('N_B21_SPEC_SHA', 'B21_SPEC_SHA', await validateRun({ ...defaults, expectedSpecSha: '0'.repeat(64) })); attack('N_B20_RESULT_SHA', 'B20_RESULT_SHA', await validateRun({ ...defaults, expectedB20Sha: '0'.repeat(64) })); attack('N_INVENTORY_SHA', 'FLOAT_INVENTORY_SHA', await validateRun({ ...defaults, expectedInventorySha: '0'.repeat(64) }));
attack('N_REVIEW_SPEC_SHA', 'REVIEW_SPEC_SHA', await validateRun({ ...defaults, identities: { ...identities, reviewRenderSpecSha256: '0'.repeat(64) } })); attack('N_BLENDER_SHA', 'BLENDER_SHA', await validateRun({ ...defaults, identities: { ...identities, blenderSha256: '0'.repeat(64) } })); attack('N_OCIO_SHA', 'OCIO_SHA', await validateRun({ ...defaults, identities: { ...identities, ocioSha256: '0'.repeat(64) } })); attack('N_SCENE_SHA', 'SCENE_SHA', await validateRun({ ...defaults, identities: { ...identities, sceneBlendSha256: '0'.repeat(64) } })); attack('N_RENDERER_SHA', 'RENDERER_SHA', await validateRun({ ...defaults, identities: { ...identities, rendererSha256: '0'.repeat(64) } })); attack('N_CONFIGURATOR_SHA', 'CONFIGURATOR_SHA', await validateRun({ ...defaults, identities: { ...identities, configuratorSha256: '0'.repeat(64) } }));
attack('N_RENDER_SAMPLES', 'RENDER_SAMPLES', await validateRun({ ...defaults, expectedSamples: 31 })); attack('N_DITHER', 'FIXED_DITHER', await validateRun({ ...defaults, expectedDither: 1 })); attack('N_FAST_GI', 'FAST_GI', await validateRun({ ...defaults, expectedGi: false })); attack('N_REPROJECTION', 'TAA_REPROJECTION', await validateRun({ ...defaults, expectedReprojection: false })); attack('N_RENDER_CALLS', 'RENDER_CALL_COUNT', await validateRun({ ...defaults, expectedRenderCalls: 2 })); attack('N_SAVE_COUNT', 'SAVE_COUNT', await validateRun({ ...defaults, expectedSaves: 1 })); attack('N_EXR_LAYOUT', 'EXR_LAYOUT', await validateRun({ ...defaults, expectedExrFormat: 'half' })); attack('N_PNG_LAYOUT', 'PNG_LAYOUT', await validateRun({ ...defaults, expectedPngFormat: 'float' }));
const baseManifest = manifests.get('A'), attackRoot = resolve(work, 'attacks'); await mkdir(attackRoot, { recursive: true });
async function copyAggregate(target) { await mkdir(target, { recursive: true }); for (const frame of sentinels) for (const extension of ['.png', '.exr']) { const name = `frame-${String(frame).padStart(4, '0')}${extension}`; await copyFile(resolve(baseManifest.dir, name), resolve(target, name)); } }
const missingDir = resolve(attackRoot, 'missing'); await copyAggregate(missingDir); await unlink(resolve(missingDir, 'frame-0110.exr')); attack('N_MISSING_PARTNER', 'MISSING_PARTNER', await validateManifest({ path: baseManifest.path, dir: missingDir, expectedSpecSha: specSha, tools, sentinels }));
const mutatedDir = resolve(attackRoot, 'mutated'); await copyAggregate(mutatedDir); await appendFile(resolve(mutatedDir, 'frame-0110.exr'), Buffer.from([0])); attack('N_MUTATED_OUTPUT', 'OUTPUT_SHA', await validateManifest({ path: baseManifest.path, dir: mutatedDir, expectedSpecSha: specSha, tools, sentinels }));
const baseComparison = comparisons.get('PNG8_DISPLAY-A-B'); let body = JSON.parse(await readFile(baseComparison.bindingPath, 'utf8')); delete body.bindingHash; body.aManifestHash = '0'.repeat(64); const badBinding = { ...body, bindingHash: sha256Canonical(body) }, badBindingPath = resolve(attackRoot, 'bad-binding.json'); await writeFile(badBindingPath, serialize(badBinding)); attack('N_COMPARISON_BINDING', 'COMPARISON_MANIFEST_BINDING', await validateComparison({ bindingPath: badBindingPath, comparisonPath: baseComparison.comparisonPath, a: manifests.get('A').manifest, b: manifests.get('B').manifest, expectedComparatorSha: tools.comparatorSha256, extension: '.png', sentinels })); attack('N_COMPARATOR_SHA', 'COMPARATOR_SHA', await validateComparison({ bindingPath: baseComparison.bindingPath, comparisonPath: baseComparison.comparisonPath, a: manifests.get('A').manifest, b: manifests.get('B').manifest, expectedComparatorSha: '0'.repeat(64), extension: '.png', sentinels }));

function summary(format) { const selected = [...comparisons.values()].filter(item => item.format === format), exact = selected.reduce((sum, item) => sum + item.comparison.decodedPixelExactFrames, 0); return { pairCount: selected.length, totalDecodedComparisons: 36, exactDecodedComparisons: exact, maximumAbsoluteError: Math.max(...selected.map(item => item.comparison.maximumAbsoluteError)), totalFailurePixels: selected.reduce((sum, item) => sum + item.comparison.totalFailurePixels, 0), exact: exact === 36 && selected.every(item => item.comparison.maximumAbsoluteError === 0 && item.comparison.totalFailurePixels === 0) }; }
const exr = summary('EXR32_SCENE_LINEAR'), png = summary('PNG8_DISPLAY'), validExperiment = attacks.length === 21 && attacks.every(item => item.pass);
let decision = 'VARIATION_NOT_REPRODUCED'; if (!validExperiment) decision = 'INVALID_EXPERIMENT'; else if (exr.exact && !png.exact) decision = 'DISPLAY_PNG_PATH_SUPPORT'; else if (!exr.exact && !png.exact) decision = 'PRE_PNG_VARIATION_SUPPORT'; else if (!exr.exact && png.exact) decision = 'PNG_QUANTIZATION_MASKS_FLOAT_VARIATION';
const result = { documentType: 'BFS_B21_DUAL_OUTPUT_LOCALIZATION_EXPERIMENT', version: '0.1.0', executedAtUtc: new Date().toISOString(), decision, validExperiment, sentinels, design: spec.design, identities: { ...frozen, b21SpecSha256: specSha, b20ResultsSha256: spec.evidenceBasis.b20ResultsSha256, floatInventorySha256: spec.evidenceBasis.floatInventorySha256, ...tools }, formats: { EXR32_SCENE_LINEAR: exr, PNG8_DISPLAY: png }, processLedger: { processCount: 36, uniqueProcessIds: new Set(ledger.processes.map(item => item.processId)).size, ledgerHash: ledger.ledgerHash, uri: repoUri(ledgerPath) }, comparisons: Object.fromEntries([...comparisons].map(([id, item]) => [id, { format: item.format, decodedPixelExactFrames: item.comparison.decodedPixelExactFrames, maximumAbsoluteError: item.comparison.maximumAbsoluteError, totalFailurePixels: item.comparison.totalFailurePixels, comparisonUri: repoUri(item.comparisonPath), bindingHash: item.binding.bindingHash }])), attacks, artifacts: { manifests: Object.fromEntries([...manifests].map(([id, item]) => [id, repoUri(item.path)])), renders: repoUri(renderEvidence), comparisons: repoUri(comparisonEvidence) }, nonClaims: spec.explicitNonClaims };
await writeFile(resolve(root, 'results.json'), serialize(result)); process.stdout.write(`BFS_B21_DUAL_OUTPUT ${decision} EXR=${exr.exactDecodedComparisons}/36 PNG=${png.exactDecodedComparisons}/36 pids=${result.processLedger.uniqueProcessIds}/36 attacks=${attacks.filter(item => item.pass).length}/${attacks.length}\n`); if (!validExperiment) process.exitCode = 1;
