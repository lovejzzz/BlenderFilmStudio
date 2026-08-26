import { copyFile, mkdir, readFile, rm, unlink, writeFile } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { relative, resolve, sep } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256Canonical, sha256File } from './lib/receipt-format.mjs';

const experimentRoot = resolve(repositoryRoot, 'experiments/eevee-repeated-render-boundary-v0-1');
const evidenceRoot = resolve(experimentRoot, 'evidence');
const renderEvidence = resolve(evidenceRoot, 'renders');
const comparisonEvidence = resolve(evidenceRoot, 'comparisons');
const workRoot = resolve(experimentRoot, 'work');
const specPath = resolve(repositoryRoot, 'specs/eevee-repeated-render-boundary-spec.v0.1.json');
const b22ResultPath = resolve(repositoryRoot, 'experiments/eevee-thread-count-factorial-v0-1/results.json');
const reviewSpecPath = resolve(repositoryRoot, 'specs/review-render-spec.v0.1.json');
const configurator = resolve(repositoryRoot, 'blender/configure_eevee_threads.py');
const renderer = resolve(repositoryRoot, 'blender/render_repeated_process_exr.py');
const comparator = resolve(repositoryRoot, 'blender/compare_repeated_process_exr.py');
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

async function renderOne({ invocationId, frame, cell, replicate, outputDir, receiptPath, scenePath, ocioPath }) {
  await mkdir(outputDir, { recursive: true });
  const reportPath = resolve(renderEvidence, `${invocationId}.render.json`);
  const interventionPath = resolve(renderEvidence, `${invocationId}.intervention.json`);
  const launched = await run(blender, [
    '--background', scenePath, '--disable-autoexec', '--python-exit-code', '1',
    '--python', configurator, '--python', renderer, '--',
    '--spec', reviewSpecPath, '--receipt', receiptPath, '--output-dir', outputDir,
    '--report', reportPath, '--frame', String(frame), '--cell', cell,
    '--replicate', replicate, '--invocation-id', invocationId,
  ], {
    ...process.env,
    OCIO: ocioPath,
    BFS_B22_THREADS_MODE: 'FIXED', BFS_B22_THREADS: '8', BFS_B22_CELL: 'T08',
    BFS_B22_INTERVENTION_REPORT: interventionPath,
  });
  const report = JSON.parse(await readFile(reportPath, 'utf8'));
  process.stdout.write(`BFS_B23_PROCESS_OK ${invocationId} pid=${launched.processId} renders=${report.renderOperatorCallCount} seconds=${report.totalSeconds}\n`);
  return { invocationId, frame, cell, replicate, outputDir, reportPath, interventionPath, processId: launched.processId, report };
}

async function validateRun({
  record, identities, expectedSpecSha, expectedB22Sha,
  expectedSourceThreads = 8,
  expectedControls = { renderSamples: 32, ditherIntensity: 0, useFastGi: true, useTaaReprojection: true },
  expectedCell = record.cell,
  expectedRenderCount = record.cell === 'PERSIST' ? 3 : 1,
  expectedSameFrame = true,
  expectedFormat = 'float',
}) {
  if (await sha256File(specPath) !== expectedSpecSha) return 'B23_SPEC_SHA';
  if (await sha256File(b22ResultPath) !== expectedB22Sha) return 'B22_RESULT_SHA';
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
  if (report.processId !== record.processId || report.invocationId !== record.invocationId || report.frame !== record.frame || report.replicate !== record.replicate || report.cell !== expectedCell) return 'CELL_PROCESS_BINDING';
  if (report.observedControls.renderSamples !== expectedControls.renderSamples || report.observedControls.ditherIntensity !== expectedControls.ditherIntensity || report.observedControls.useFastGi !== expectedControls.useFastGi || report.observedControls.useTaaReprojection !== expectedControls.useTaaReprojection) return 'REQUESTED_FIXED_CONTROLS';
  const countReason = record.cell === 'PERSIST' ? 'PERSIST_RENDER_COUNT' : 'FRESH_RENDER_COUNT';
  if (report.renderOperatorCallCount !== expectedRenderCount || report.saveCount !== expectedRenderCount || report.outputs.length !== expectedRenderCount || report.blendLoadCount !== 1) return countReason;
  if (report.sameFrameAcrossRenders !== expectedSameFrame || report.outputs.some((output, index) => output.renderOrdinal !== index + 1 || output.frameBefore !== record.frame || output.frameAfter !== record.frame)) return 'RENDER_ORDINAL_FRAME_INVARIANT';
  if (report.source.sceneBlendSha256 !== identities.sceneBlendSha256 || report.savedSourceBlend !== false || report.cameraAndTimelineInvariant !== true) return 'SOURCE_OR_TIMELINE_INVARIANT';
  for (const output of report.outputs) {
    const decoded = output.decoded;
    if (decoded.width !== 960 || decoded.height !== 540 || JSON.stringify(decoded.channels) !== JSON.stringify(['R', 'G', 'B', 'A']) || decoded.pixelFormat !== expectedFormat) return 'EXR_LAYOUT';
    const path = resolve(record.outputDir, output.name);
    try { if (await sha256File(path) !== output.sha256) return 'MISSING_OR_MUTATED_EXR'; } catch { return 'MISSING_OR_MUTATED_EXR'; }
  }
  return 'OK';
}

async function makeManifest({ cell, records, specSha, tools }) {
  const body = {
    documentType: 'BFS_B23_CELL_MANIFEST', version: '0.1.0', cell,
    b23SpecSha256: specSha, toolIdentities: tools,
    invocations: records.map(record => ({
      invocationId: record.invocationId, processId: record.processId,
      frame: record.frame, replicate: record.replicate,
      renderReportSha256: null, interventionReportSha256: null,
      outputs: record.report.outputs.map(output => ({ renderOrdinal: output.renderOrdinal, name: output.name, sha256: output.sha256 })),
    })),
  };
  for (let index = 0; index < records.length; index += 1) {
    body.invocations[index].renderReportSha256 = await sha256File(records[index].reportPath);
    body.invocations[index].interventionReportSha256 = await sha256File(records[index].interventionPath);
  }
  return { ...body, manifestHash: sha256Canonical(body) };
}

function outputFor(records, cell, frame, replicate, ordinal) {
  const record = records.get(`${cell}-${String(frame).padStart(4, '0')}-${replicate}`);
  const output = record.report.outputs.find(item => item.renderOrdinal === ordinal);
  if (!output) throw new Error(`Missing output ${cell}/${frame}/${replicate}/R${ordinal}`);
  return { record, output, path: resolve(record.outputDir, output.name) };
}

function pair(id, gate, a, b, metadata) {
  return { id, gate, aPath: a.path, bPath: b.path, aSha256: a.output.sha256, bSha256: b.output.sha256, metadata };
}

function makePairSets(records, sentinels) {
  const within = [], persistentCross = [], freshCross = [];
  const replicatePairs = [['A', 'B'], ['A', 'C'], ['B', 'C']];
  const ordinalPairs = [[1, 2], [1, 3], [2, 3]];
  for (const frame of sentinels) {
    for (const replicate of ['A', 'B', 'C']) for (const [aOrdinal, bOrdinal] of ordinalPairs) {
      within.push(pair(`W-${frame}-${replicate}-R${aOrdinal}R${bOrdinal}`, 'WITHIN_PERSIST', outputFor(records, 'PERSIST', frame, replicate, aOrdinal), outputFor(records, 'PERSIST', frame, replicate, bOrdinal), { frame, replicate, aOrdinal, bOrdinal, sameProcess: true }));
    }
    for (const ordinal of [1, 2, 3]) for (const [aReplicate, bReplicate] of replicatePairs) {
      persistentCross.push(pair(`P-${frame}-R${ordinal}-${aReplicate}${bReplicate}`, 'PERSIST_CROSS', outputFor(records, 'PERSIST', frame, aReplicate, ordinal), outputFor(records, 'PERSIST', frame, bReplicate, ordinal), { frame, ordinal, aReplicate, bReplicate, sameProcess: false }));
    }
    for (const [aReplicate, bReplicate] of replicatePairs) {
      freshCross.push(pair(`F-${frame}-${aReplicate}${bReplicate}`, 'FRESH_CROSS', outputFor(records, 'FRESH', frame, aReplicate, 1), outputFor(records, 'FRESH', frame, bReplicate, 1), { frame, ordinal: 1, aReplicate, bReplicate, sameProcess: false }));
    }
  }
  return { WITHIN_PERSIST: within, PERSIST_CROSS: persistentCross, FRESH_CROSS: freshCross };
}

async function runComparison({ gate, pairs, manifests, tools }) {
  const pairBody = { documentType: 'BFS_B23_PAIR_SPEC', version: '0.1.0', id: gate, gate, pairs };
  const pairSpec = { ...pairBody, pairSpecHash: sha256Canonical(pairBody) };
  const pairPath = resolve(workRoot, 'pair-specs', `${gate}.json`);
  const comparisonPath = resolve(comparisonEvidence, `${gate}.comparison.json`);
  const bindingPath = resolve(comparisonEvidence, `${gate}.binding.json`);
  await mkdir(resolve(workRoot, 'pair-specs'), { recursive: true });
  await writeFile(pairPath, serialize(pairSpec));
  await run(blender, ['--factory-startup', '--background', '--python-exit-code', '1', '--python', comparator, '--', '--pairs', pairPath, '--output', comparisonPath]);
  const comparison = JSON.parse(await readFile(comparisonPath, 'utf8'));
  const bindingBody = {
    documentType: 'BFS_B23_COMPARISON_BINDING', version: '0.1.0', gate,
    manifestHashes: gate === 'FRESH_CROSS'
      ? { FRESH: manifests.FRESH.manifestHash }
      : { PERSIST: manifests.PERSIST.manifestHash },
    comparatorSha256: tools.comparatorSha256,
    pairSpecHash: pairSpec.pairSpecHash,
    comparisonSha256: await sha256File(comparisonPath),
  };
  const binding = { ...bindingBody, bindingHash: sha256Canonical(bindingBody) };
  await writeFile(bindingPath, serialize(binding));
  return { gate, pairs, pairSpec, pairPath, comparison, comparisonPath, binding, bindingPath };
}

async function validateComparison({ item, manifests, expectedComparatorSha, expectedBinding = true, expectedSamePid = null }) {
  if (await sha256File(comparator) !== expectedComparatorSha) return 'COMPARATOR_SHA';
  const binding = JSON.parse(await readFile(item.bindingPath, 'utf8'));
  const body = structuredClone(binding); delete body.bindingHash;
  if (sha256Canonical(body) !== binding.bindingHash) return 'COMPARISON_SELF_HASH';
  const expectedManifests = item.gate === 'FRESH_CROSS' ? { FRESH: manifests.FRESH.manifestHash } : { PERSIST: manifests.PERSIST.manifestHash };
  if (expectedBinding && JSON.stringify(binding.manifestHashes) !== JSON.stringify(expectedManifests)) return item.gate === 'WITHIN_PERSIST' ? 'WITHIN_PROCESS_COMPARISON_BINDING' : 'CROSS_PROCESS_COMPARISON_BINDING';
  if (binding.pairSpecHash !== item.pairSpec.pairSpecHash || binding.comparisonSha256 !== await sha256File(item.comparisonPath)) return item.gate === 'WITHIN_PERSIST' ? 'WITHIN_PROCESS_COMPARISON_BINDING' : 'CROSS_PROCESS_COMPARISON_BINDING';
  if (item.comparison.pairSpecHash !== item.pairSpec.pairSpecHash || item.comparison.pairCount !== item.pairs.length) return 'COMPARISON_PAIR_SPEC';
  for (let index = 0; index < item.pairs.length; index += 1) {
    const source = item.pairs[index], observed = item.comparison.pairs[index];
    if (observed.id !== source.id || observed.aSha256 !== source.aSha256 || observed.bSha256 !== source.bSha256) return item.gate === 'WITHIN_PERSIST' ? 'WITHIN_PROCESS_COMPARISON_BINDING' : 'CROSS_PROCESS_COMPARISON_BINDING';
    if (expectedSamePid !== null && Boolean(observed.metadata.sameProcess) !== expectedSamePid) return 'WITHIN_PROCESS_COMPARISON_BINDING';
  }
  return 'OK';
}

function validateProcessIds(processes, expectedUniqueCount = 72) {
  return new Set(processes.map(item => item.processId)).size === expectedUniqueCount
    ? 'OK'
    : 'PROCESS_ID_UNIQUENESS';
}

await rm(evidenceRoot, { recursive: true, force: true });
await rm(workRoot, { recursive: true, force: true });
await mkdir(renderEvidence, { recursive: true });
await mkdir(comparisonEvidence, { recursive: true });
const spec = JSON.parse(await readFile(specPath, 'utf8'));
const specSha = await sha256File(specPath);
if (specSha !== '7a4b37ca2eb1d2c370270bb5cb45fdd741e85ccce140bc51501a6639150cc2f1') throw new Error('B23 spec changed after pre-registration');
const reviewSpec = JSON.parse(await readFile(reviewSpecPath, 'utf8'));
const receiptPath = resolve(repositoryRoot, reviewSpec.source.receiptUri);
const receipt = JSON.parse(await readFile(receiptPath, 'utf8'));
const scenePath = resolve(repositoryRoot, receipt.run.sceneBlend.uri);
const ocioPath = resolve(repositoryRoot, receipt.executionIdentity.configuration.ocio.uri);
const frozen = spec.frozenIdentity;
for (const [path, expected, label] of [
  [b22ResultPath, spec.evidenceBasis.b22ResultsSha256, 'B22 result'], [reviewSpecPath, frozen.reviewRenderSpecSha256, 'review spec'],
  [configurator, frozen.configuratorSha256, 'configurator'], [blender, frozen.blenderSha256, 'Blender'],
  [ocioPath, frozen.ocioSha256, 'OCIO'], [scenePath, frozen.sceneBlendSha256, 'scene'],
]) if (await sha256File(path) !== expected) throw new Error(`${label} SHA mismatch`);
const tools = { configuratorSha256: await sha256File(configurator), rendererSha256: await sha256File(renderer), comparatorSha256: await sha256File(comparator), runnerSha256: await sha256File(runner) };
const identities = { ...frozen, ...tools, ocioPath, scenePath };
const sentinels = spec.design.sentinelFrames;
const runOrder = [];
for (const frame of spec.design.frameOrder) for (const block of spec.design.blockOrderPerFrame) {
  const [cell, replicate] = block.split('-');
  runOrder.push({ invocationId: `${cell}-${String(frame).padStart(4, '0')}-${replicate}`, frame, cell, replicate });
}
if (runOrder.length !== 72) throw new Error('Frozen run order count mismatch');
const runOrderPath = resolve(evidenceRoot, 'run-order.json');
await writeFile(runOrderPath, serialize({ documentType: 'BFS_B23_FROZEN_RUN_ORDER', version: '0.1.0', b23SpecSha256: specSha, order: runOrder, orderHash: sha256Canonical(runOrder) }));

const records = new Map();
for (const item of runOrder) {
  const outputDir = resolve(workRoot, 'invocations', item.invocationId);
  const record = await renderOne({ ...item, outputDir, receiptPath, scenePath, ocioPath });
  const reason = await validateRun({ record, identities, expectedSpecSha: specSha, expectedB22Sha: spec.evidenceBasis.b22ResultsSha256 });
  if (reason !== 'OK') throw new Error(`${item.invocationId}: ${reason}`);
  records.set(item.invocationId, record);
}
const ledgerBody = { documentType: 'BFS_B23_PROCESS_LEDGER', version: '0.1.0', b23SpecSha256: specSha, processes: [...records.values()].map(record => ({ invocationId: record.invocationId, processId: record.processId, cell: record.cell, replicate: record.replicate, frame: record.frame, renderCount: record.report.renderOperatorCallCount, reportSha256: null })) };
for (const item of ledgerBody.processes) item.reportSha256 = await sha256File(records.get(item.invocationId).reportPath);
const ledger = { ...ledgerBody, ledgerHash: sha256Canonical(ledgerBody) };
const uniquePids = new Set(ledger.processes.map(item => item.processId)).size;
if (uniquePids !== 72) throw new Error('B23 render PIDs are not unique');
const ledgerPath = resolve(evidenceRoot, 'process-ledger.json');
await writeFile(ledgerPath, serialize(ledger));
const manifests = {};
for (const cell of ['PERSIST', 'FRESH']) {
  const manifest = await makeManifest({ cell, records: [...records.values()].filter(record => record.cell === cell), specSha, tools });
  const path = resolve(evidenceRoot, `${cell}.manifest.json`);
  await writeFile(path, serialize(manifest));
  manifests[cell] = { ...manifest, path };
}
const pairSets = makePairSets(records, sentinels);
const comparisons = {};
for (const gate of ['WITHIN_PERSIST', 'PERSIST_CROSS', 'FRESH_CROSS']) {
  comparisons[gate] = await runComparison({ gate, pairs: pairSets[gate], manifests, tools });
  const reason = await validateComparison({ item: comparisons[gate], manifests, expectedComparatorSha: tools.comparatorSha256, expectedSamePid: gate === 'WITHIN_PERSIST' ? true : null });
  if (reason !== 'OK') throw new Error(`${gate}: ${reason}`);
}

const attacks = [], attack = (id, expectedReason, observedReason) => attacks.push({ id, expectedReason, observedReason, pass: expectedReason === observedReason });
const basePersist = records.get('PERSIST-0001-A'), baseFresh = records.get('FRESH-0001-A');
const defaults = { record: basePersist, identities, expectedSpecSha: specSha, expectedB22Sha: spec.evidenceBasis.b22ResultsSha256 };
attack('N_B23_SPEC_SHA', 'B23_SPEC_SHA', await validateRun({ ...defaults, expectedSpecSha: '0'.repeat(64) }));
attack('N_B22_RESULT_SHA', 'B22_RESULT_SHA', await validateRun({ ...defaults, expectedB22Sha: '0'.repeat(64) }));
attack('N_REVIEW_SPEC_SHA', 'REVIEW_SPEC_SHA', await validateRun({ ...defaults, identities: { ...identities, reviewRenderSpecSha256: '0'.repeat(64) } }));
attack('N_BLENDER_SHA', 'BLENDER_SHA', await validateRun({ ...defaults, identities: { ...identities, blenderSha256: '0'.repeat(64) } }));
attack('N_OCIO_SHA', 'OCIO_SHA', await validateRun({ ...defaults, identities: { ...identities, ocioSha256: '0'.repeat(64) } }));
attack('N_SCENE_SHA', 'SCENE_SHA', await validateRun({ ...defaults, identities: { ...identities, sceneBlendSha256: '0'.repeat(64) } }));
attack('N_CONFIGURATOR_SHA', 'CONFIGURATOR_SHA', await validateRun({ ...defaults, identities: { ...identities, configuratorSha256: '0'.repeat(64) } }));
attack('N_RENDERER_SHA', 'RENDERER_SHA', await validateRun({ ...defaults, identities: { ...identities, rendererSha256: '0'.repeat(64) } }));
attack('N_COMPARATOR_SHA', 'COMPARATOR_SHA', await validateComparison({ item: comparisons.WITHIN_PERSIST, manifests, expectedComparatorSha: '0'.repeat(64), expectedSamePid: true }));
attack('N_SOURCE_THREAD_STATE', 'SOURCE_THREAD_STATE', await validateRun({ ...defaults, expectedSourceThreads: 7 }));
attack('N_REQUESTED_FIXED_CONTROLS', 'REQUESTED_FIXED_CONTROLS', await validateRun({ ...defaults, expectedControls: { renderSamples: 32, ditherIntensity: 1, useFastGi: true, useTaaReprojection: true } }));
attack('N_CELL_PROCESS_BINDING', 'CELL_PROCESS_BINDING', await validateRun({ ...defaults, expectedCell: 'FRESH' }));
attack('N_PERSIST_RENDER_COUNT', 'PERSIST_RENDER_COUNT', await validateRun({ ...defaults, expectedRenderCount: 2 }));
attack('N_FRESH_RENDER_COUNT', 'FRESH_RENDER_COUNT', await validateRun({ record: baseFresh, identities, expectedSpecSha: specSha, expectedB22Sha: spec.evidenceBasis.b22ResultsSha256, expectedRenderCount: 2 }));
attack('N_RENDER_ORDINAL_FRAME', 'RENDER_ORDINAL_FRAME_INVARIANT', await validateRun({ ...defaults, expectedSameFrame: false }));
attack('N_UNIQUE_PROCESS_IDS', 'PROCESS_ID_UNIQUENESS', validateProcessIds(ledger.processes, 71));
attack('N_EXR_LAYOUT', 'EXR_LAYOUT', await validateRun({ ...defaults, expectedFormat: 'half' }));
const attackDir = resolve(workRoot, 'attacks', 'missing'); await mkdir(attackDir, { recursive: true });
for (const output of basePersist.report.outputs) await copyFile(resolve(basePersist.outputDir, output.name), resolve(attackDir, output.name));
await unlink(resolve(attackDir, basePersist.report.outputs[0].name));
attack('N_MISSING_OR_MUTATED_EXR', 'MISSING_OR_MUTATED_EXR', await validateRun({ ...defaults, record: { ...basePersist, outputDir: attackDir } }));
const withinBad = structuredClone(comparisons.WITHIN_PERSIST); const withinBody = structuredClone(withinBad.binding); delete withinBody.bindingHash; withinBody.manifestHashes.PERSIST = '0'.repeat(64); withinBad.binding = { ...withinBody, bindingHash: sha256Canonical(withinBody) }; withinBad.bindingPath = resolve(workRoot, 'attacks', 'within-binding.json'); await writeFile(withinBad.bindingPath, serialize(withinBad.binding));
attack('N_WITHIN_BINDING', 'WITHIN_PROCESS_COMPARISON_BINDING', await validateComparison({ item: withinBad, manifests, expectedComparatorSha: tools.comparatorSha256, expectedSamePid: true }));
const crossBad = structuredClone(comparisons.FRESH_CROSS); const crossBody = structuredClone(crossBad.binding); delete crossBody.bindingHash; crossBody.manifestHashes.FRESH = '0'.repeat(64); crossBad.binding = { ...crossBody, bindingHash: sha256Canonical(crossBody) }; crossBad.bindingPath = resolve(workRoot, 'attacks', 'cross-binding.json'); await writeFile(crossBad.bindingPath, serialize(crossBad.binding));
attack('N_CROSS_BINDING', 'CROSS_PROCESS_COMPARISON_BINDING', await validateComparison({ item: crossBad, manifests, expectedComparatorSha: tools.comparatorSha256 }));

function gateSummary(item) { return { pairCount: item.comparison.pairCount, exactDecodedComparisons: item.comparison.decodedPixelExactPairs, maximumAbsoluteError: item.comparison.maximumAbsoluteError, totalFailurePixels: item.comparison.totalFailurePixels, exact: item.comparison.decodedPixelExactPairs === item.comparison.pairCount && item.comparison.maximumAbsoluteError === 0 && item.comparison.totalFailurePixels === 0, comparisonUri: repoUri(item.comparisonPath), bindingHash: item.binding.bindingHash }; }
const gates = { WITHIN_PERSIST: gateSummary(comparisons.WITHIN_PERSIST), PERSIST_CROSS: gateSummary(comparisons.PERSIST_CROSS), FRESH_CROSS: gateSummary(comparisons.FRESH_CROSS) };
const validExperiment = attacks.length === 20 && attacks.every(item => item.pass);
let decision = 'VARIATION_NOT_REPRODUCED';
if (!validExperiment) decision = 'INVALID_EXPERIMENT';
else if (!gates.WITHIN_PERSIST.exact) decision = 'PER_RENDER_VARIATION_SUPPORT';
else if (!gates.PERSIST_CROSS.exact && !gates.FRESH_CROSS.exact) decision = 'PROCESS_INITIALIZATION_BOUNDARY_SUPPORT';
else if (gates.PERSIST_CROSS.exact !== gates.FRESH_CROSS.exact) decision = 'MIXED_CROSS_PROCESS_PATTERN';
const result = { documentType: 'BFS_B23_EEVEE_REPEATED_RENDER_BOUNDARY_EXPERIMENT', version: '0.1.0', executedAtUtc: new Date().toISOString(), decision, validExperiment, sentinels, design: { ...spec.design, materializedRunOrder: runOrder.map(item => item.invocationId) }, identities: { ...frozen, b23SpecSha256: specSha, b22ResultsSha256: spec.evidenceBasis.b22ResultsSha256, ...tools }, gates, processLedger: { processCount: 72, uniqueProcessIds: uniquePids, renderCalls: ledger.processes.reduce((sum, item) => sum + item.renderCount, 0), ledgerHash: ledger.ledgerHash, uri: repoUri(ledgerPath) }, attacks, artifacts: { runOrder: repoUri(runOrderPath), manifests: { PERSIST: repoUri(manifests.PERSIST.path), FRESH: repoUri(manifests.FRESH.path) }, renders: repoUri(renderEvidence), comparisons: repoUri(comparisonEvidence) }, nonClaims: spec.explicitNonClaims };
await writeFile(resolve(experimentRoot, 'results.json'), serialize(result));
process.stdout.write(`BFS_B23_REPEATED_BOUNDARY ${decision} WITHIN=${gates.WITHIN_PERSIST.exactDecodedComparisons}/108 PERSIST_CROSS=${gates.PERSIST_CROSS.exactDecodedComparisons}/108 FRESH=${gates.FRESH_CROSS.exactDecodedComparisons}/36 pids=${uniquePids}/72 attacks=${attacks.filter(item => item.pass).length}/${attacks.length}\n`);
if (!validExperiment) process.exitCode = 1;
