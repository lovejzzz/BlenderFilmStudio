import { appendFile, copyFile, mkdir, readFile, readdir, rm, unlink, writeFile } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { relative, resolve, sep } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256Canonical, sha256File } from './lib/receipt-format.mjs';

const experimentRoot = resolve(repositoryRoot, 'experiments/eevee-thread-count-factorial-v0-1');
const evidenceRoot = resolve(experimentRoot, 'evidence');
const renderEvidence = resolve(evidenceRoot, 'renders');
const comparisonEvidence = resolve(evidenceRoot, 'comparisons');
const workRoot = resolve(experimentRoot, 'work');
const specPath = resolve(repositoryRoot, 'specs/eevee-thread-count-factorial-spec.v0.1.json');
const b21ResultPath = resolve(repositoryRoot, 'experiments/dual-output-localization-v0-1/results.json');
const inventoryPath = resolve(repositoryRoot, 'experiments/eevee-control-inventory-v0-1/results.json');
const reviewSpecPath = resolve(repositoryRoot, 'specs/review-render-spec.v0.1.json');
const configurator = resolve(repositoryRoot, 'blender/configure_eevee_threads.py');
const renderer = resolve(repositoryRoot, 'blender/render_thread_factorial_exr.py');
const comparator = resolve(repositoryRoot, 'blender/compare_thread_factorial_exr.py');
const runner = fileURLToPath(import.meta.url);
const blender = resolve(process.env.BLENDER_BIN || '/Applications/Blender.app/Contents/MacOS/Blender');
const serialize = value => `${JSON.stringify(value, null, 2)}\n`;
const repoUri = path => relative(repositoryRoot, path).split(sep).join('/');

function run(command, args, env = process.env) {
  return new Promise((resolvePromise, reject) => {
    const child = spawn(command, args, {
      cwd: repositoryRoot,
      env,
      stdio: ['ignore', 'pipe', 'pipe'],
    });
    const processId = child.pid;
    let output = '';
    child.stdout.on('data', chunk => { output += chunk; });
    child.stderr.on('data', chunk => { output += chunk; });
    child.on('error', reject);
    child.on('close', code => {
      if (code === 0) resolvePromise({ processId, output });
      else reject(new Error(`${command} failed (${code}) pid=${processId}\n${output}`));
    });
  });
}

async function renderOne({ invocationId, frame, cell, replicate, outputDir, receiptPath, scenePath, ocioPath }) {
  await mkdir(outputDir, { recursive: true });
  const reportPath = resolve(renderEvidence, `${invocationId}.render.json`);
  const interventionPath = resolve(renderEvidence, `${invocationId}.intervention.json`);
  const threads = cell === 'T01' ? 1 : 8;
  const launched = await run(
    blender,
    [
      '--background', scenePath, '--disable-autoexec', '--python-exit-code', '1',
      '--python', configurator, '--python', renderer, '--',
      '--spec', reviewSpecPath, '--receipt', receiptPath,
      '--output-dir', outputDir, '--report', reportPath,
      '--frame', String(frame), '--cell', cell, '--invocation-id', invocationId,
    ],
    {
      ...process.env,
      OCIO: ocioPath,
      BFS_B22_THREADS_MODE: 'FIXED',
      BFS_B22_THREADS: String(threads),
      BFS_B22_CELL: cell,
      BFS_B22_INTERVENTION_REPORT: interventionPath,
    },
  );
  const report = JSON.parse(await readFile(reportPath, 'utf8'));
  process.stdout.write(
    `BFS_B22_PROCESS_OK ${invocationId} pid=${launched.processId} ` +
    `cell=${cell} replicate=${replicate} seconds=${report.totalSeconds}\n`,
  );
  return {
    invocationId, frame, cell, replicate, threads, outputDir,
    reportPath, interventionPath, processId: launched.processId, report,
  };
}

async function validateRun({
  record,
  identities,
  expectedSpecSha,
  expectedB21Sha,
  expectedInventorySha,
  expectedSourceMode = 'FIXED',
  expectedSourceThreads = 8,
  expectedRequestedMode = 'FIXED',
  expectedRequestedThreads = record.threads,
  expectedSamples = 32,
  expectedConstants = { ditherIntensity: 0, useFastGi: true, useTaaReprojection: true },
  expectedRenderCalls = 1,
  expectedLayout = { width: 960, height: 540, channels: ['R', 'G', 'B', 'A'], pixelFormat: 'float' },
}) {
  if (await sha256File(specPath) !== expectedSpecSha) return 'B22_SPEC_SHA';
  if (await sha256File(b21ResultPath) !== expectedB21Sha) return 'B21_RESULT_SHA';
  if (await sha256File(inventoryPath) !== expectedInventorySha) return 'CONTROL_INVENTORY_SHA';
  if (await sha256File(reviewSpecPath) !== identities.reviewRenderSpecSha256) return 'REVIEW_SPEC_SHA';
  if (await sha256File(blender) !== identities.blenderSha256) return 'BLENDER_SHA';
  if (await sha256File(identities.ocioPath) !== identities.ocioSha256) return 'OCIO_SHA';
  if (await sha256File(identities.scenePath) !== identities.sceneBlendSha256) return 'SCENE_SHA';
  if (await sha256File(configurator) !== identities.configuratorSha256) return 'CONFIGURATOR_SHA';
  if (await sha256File(renderer) !== identities.rendererSha256) return 'RENDERER_SHA';

  const intervention = JSON.parse(await readFile(record.interventionPath, 'utf8'));
  if (intervention.before.threadsMode !== expectedSourceMode || intervention.before.threads !== expectedSourceThreads) return 'SOURCE_THREAD_STATE';
  if (intervention.requested.threadsMode !== expectedRequestedMode || intervention.after.threadsMode !== expectedRequestedMode) return 'REQUESTED_THREAD_MODE';
  if (intervention.requested.threads !== expectedRequestedThreads || intervention.after.threads !== expectedRequestedThreads) return 'REQUESTED_THREAD_COUNT';
  if (
    intervention.after.ditherIntensity !== expectedConstants.ditherIntensity ||
    intervention.after.useFastGi !== expectedConstants.useFastGi ||
    intervention.after.useTaaReprojection !== expectedConstants.useTaaReprojection
  ) return 'FIXED_RENDER_CONSTANTS';
  if (intervention.cell !== record.cell || intervention.savedSourceBlend !== false) return 'INTERVENTION_BINDING';

  const report = JSON.parse(await readFile(record.reportPath, 'utf8'));
  if (report.processId !== record.processId || report.invocationId !== record.invocationId || report.frame !== record.frame || report.cell !== record.cell) return 'PROCESS_BINDING';
  if (report.observedThreadState.threadsMode !== expectedRequestedMode || report.observedThreadState.threads !== expectedRequestedThreads) return 'REQUESTED_THREAD_COUNT';
  if (report.observedControls.renderSamples !== expectedSamples) return 'RENDER_SAMPLES';
  if (
    report.observedControls.ditherIntensity !== expectedConstants.ditherIntensity ||
    report.observedControls.useFastGi !== expectedConstants.useFastGi ||
    report.observedControls.useTaaReprojection !== expectedConstants.useTaaReprojection
  ) return 'FIXED_RENDER_CONSTANTS';
  if (report.renderOperatorCallCount !== expectedRenderCalls || report.saveCount !== 1) return 'RENDER_CALL_COUNT';
  if (report.source.sceneBlendSha256 !== identities.sceneBlendSha256 || report.savedSourceBlend !== false) return 'SOURCE_BLEND';
  if (report.cameraAndTimelineInvariant !== true) return 'CAMERA_TIMELINE_INVARIANT';
  const decoded = report.output.decoded;
  if (
    decoded.width !== expectedLayout.width || decoded.height !== expectedLayout.height ||
    JSON.stringify(decoded.channels) !== JSON.stringify(expectedLayout.channels) ||
    decoded.pixelFormat !== expectedLayout.pixelFormat
  ) return 'EXR_LAYOUT';
  if (await sha256File(resolve(record.outputDir, report.output.name)) !== report.output.sha256) return 'MISSING_OR_MUTATED_EXR';
  return 'OK';
}

async function makeManifest({ cell, replicate, records, dir, specSha, tools, sentinels }) {
  const frames = [];
  for (const frame of sentinels) {
    const name = `frame-${String(frame).padStart(4, '0')}.exr`;
    frames.push({ frame, name, sha256: await sha256File(resolve(dir, name)) });
  }
  const body = {
    documentType: 'BFS_B22_THREAD_CELL_MANIFEST', version: '0.1.0',
    cell, replicate, threadsMode: 'FIXED', threads: cell === 'T01' ? 1 : 8,
    b22SpecSha256: specSha, toolIdentities: tools, selectedFrames: sentinels,
    invocations: records.map(record => ({
      invocationId: record.invocationId,
      processId: record.processId,
      renderReportSha256: null,
      interventionReportSha256: null,
    })),
    frames,
  };
  for (let index = 0; index < records.length; index += 1) {
    body.invocations[index].renderReportSha256 = await sha256File(records[index].reportPath);
    body.invocations[index].interventionReportSha256 = await sha256File(records[index].interventionPath);
  }
  return { ...body, manifestHash: sha256Canonical(body) };
}

async function validateManifest({ path, dir, expectedSpecSha, tools, sentinels }) {
  const manifest = JSON.parse(await readFile(path, 'utf8'));
  const body = structuredClone(manifest);
  delete body.manifestHash;
  if (sha256Canonical(body) !== manifest.manifestHash) return 'MANIFEST_SELF_HASH';
  if (manifest.b22SpecSha256 !== expectedSpecSha) return 'MANIFEST_SPEC_BINDING';
  if (JSON.stringify(manifest.toolIdentities) !== JSON.stringify(tools)) return 'MANIFEST_TOOL_BINDING';
  if (JSON.stringify(manifest.selectedFrames) !== JSON.stringify(sentinels)) return 'SENTINEL_SET';
  const names = await readdir(dir);
  for (const frame of manifest.frames) {
    if (!names.includes(frame.name)) return 'MISSING_OR_MUTATED_EXR';
    if (await sha256File(resolve(dir, frame.name)) !== frame.sha256) return 'MISSING_OR_MUTATED_EXR';
  }
  return 'OK';
}

async function validateComparison({ bindingPath, comparisonPath, a, b, expectedComparatorSha, sentinels }) {
  if (await sha256File(comparator) !== expectedComparatorSha) return 'COMPARATOR_SHA';
  const binding = JSON.parse(await readFile(bindingPath, 'utf8'));
  const body = structuredClone(binding);
  delete body.bindingHash;
  if (sha256Canonical(body) !== binding.bindingHash) return 'COMPARISON_SELF_HASH';
  if (binding.aManifestHash !== a.manifestHash || binding.bManifestHash !== b.manifestHash) return 'COMPARISON_FILE_BINDING';
  if (binding.comparisonSha256 !== await sha256File(comparisonPath)) return 'COMPARISON_FILE_BINDING';
  const comparison = JSON.parse(await readFile(comparisonPath, 'utf8'));
  if (comparison.extension !== '.exr' || comparison.pixelFormat !== 'float' || comparison.frameCount !== 12 || JSON.stringify(comparison.selectedFrames) !== JSON.stringify(sentinels)) return 'COMPARISON_FORMAT';
  for (const item of comparison.frames) {
    const aFrame = a.frames.find(frame => frame.frame === item.frame);
    const bFrame = b.frames.find(frame => frame.frame === item.frame);
    if (item.aSha256 !== aFrame.sha256 || item.bSha256 !== bFrame.sha256) return 'COMPARISON_FILE_BINDING';
  }
  return 'OK';
}

await rm(evidenceRoot, { recursive: true, force: true });
await rm(workRoot, { recursive: true, force: true });
await mkdir(renderEvidence, { recursive: true });
await mkdir(comparisonEvidence, { recursive: true });

const spec = JSON.parse(await readFile(specPath, 'utf8'));
const specSha = await sha256File(specPath);
if (specSha !== '6c498b69000d6e0bb1dccc8fce3a529845f162131f7ad65fb3fca617a86b68cd') {
  throw new Error('B22 spec changed after pre-registration');
}
const reviewSpec = JSON.parse(await readFile(reviewSpecPath, 'utf8'));
const receiptPath = resolve(repositoryRoot, reviewSpec.source.receiptUri);
const receipt = JSON.parse(await readFile(receiptPath, 'utf8'));
const scenePath = resolve(repositoryRoot, receipt.run.sceneBlend.uri);
const ocioPath = resolve(repositoryRoot, receipt.executionIdentity.configuration.ocio.uri);
const frozen = spec.frozenIdentity;
for (const [path, expected, label] of [
  [b21ResultPath, spec.evidenceBasis.b21ResultsSha256, 'B21 result'],
  [inventoryPath, spec.evidenceBasis.controlInventorySha256, 'control inventory'],
  [reviewSpecPath, frozen.reviewRenderSpecSha256, 'review spec'],
  [blender, frozen.blenderSha256, 'Blender'],
  [ocioPath, frozen.ocioSha256, 'OCIO'],
  [scenePath, frozen.sceneBlendSha256, 'scene'],
]) {
  if (await sha256File(path) !== expected) throw new Error(`${label} SHA mismatch`);
}

const tools = {
  configuratorSha256: await sha256File(configurator),
  rendererSha256: await sha256File(renderer),
  comparatorSha256: await sha256File(comparator),
  runnerSha256: await sha256File(runner),
};
const identities = { ...frozen, ...tools, ocioPath, scenePath };
const sentinels = spec.design.sentinelFrames;
const runOrder = [];
for (const frame of spec.design.frameOrder) {
  for (const block of spec.design.blockOrderPerFrame) {
    const [cell, replicate] = block.split('-');
    runOrder.push({
      invocationId: `${cell}-${String(frame).padStart(4, '0')}-${replicate}`,
      frame, cell, replicate,
    });
  }
}
if (runOrder.length !== spec.design.processes) throw new Error('Frozen run order count mismatch');
const runOrderPath = resolve(evidenceRoot, 'run-order.json');
await writeFile(runOrderPath, serialize({
  documentType: 'BFS_B22_FROZEN_RUN_ORDER', version: '0.1.0',
  b22SpecSha256: specSha, order: runOrder,
  orderHash: sha256Canonical(runOrder),
}));

const records = new Map();
const groups = new Map();
const aggregate = new Map();
for (const cell of ['T01', 'T08']) {
  for (const replicate of ['A', 'B', 'C']) {
    const id = `${cell}-${replicate}`;
    groups.set(id, []);
    const dir = resolve(workRoot, id);
    await mkdir(dir, { recursive: true });
    aggregate.set(id, dir);
  }
}

for (const item of runOrder) {
  const outputDir = resolve(workRoot, 'invocations', item.invocationId);
  const record = await renderOne({ ...item, outputDir, receiptPath, scenePath, ocioPath });
  const reason = await validateRun({
    record, identities, expectedSpecSha: specSha,
    expectedB21Sha: spec.evidenceBasis.b21ResultsSha256,
    expectedInventorySha: spec.evidenceBasis.controlInventorySha256,
  });
  if (reason !== 'OK') throw new Error(`${item.invocationId}: ${reason}`);
  const name = `frame-${String(item.frame).padStart(4, '0')}.exr`;
  await copyFile(resolve(outputDir, name), resolve(aggregate.get(`${item.cell}-${item.replicate}`), name));
  records.set(item.invocationId, record);
  groups.get(`${item.cell}-${item.replicate}`).push(record);
}

const ledgerBody = {
  documentType: 'BFS_B22_PROCESS_LEDGER', version: '0.1.0', b22SpecSha256: specSha,
  processes: [...records.values()].map(record => ({
    invocationId: record.invocationId, processId: record.processId,
    frame: record.frame, cell: record.cell, replicate: record.replicate,
    reportSha256: null, interventionSha256: null,
  })),
};
for (const item of ledgerBody.processes) {
  const record = records.get(item.invocationId);
  item.reportSha256 = await sha256File(record.reportPath);
  item.interventionSha256 = await sha256File(record.interventionPath);
}
const ledger = { ...ledgerBody, ledgerHash: sha256Canonical(ledgerBody) };
if (new Set(ledger.processes.map(item => item.processId)).size !== 72) {
  throw new Error('B22 render PIDs are not unique');
}
const ledgerPath = resolve(evidenceRoot, 'process-ledger.json');
await writeFile(ledgerPath, serialize(ledger));

const manifests = new Map();
for (const cell of ['T01', 'T08']) {
  for (const replicate of ['A', 'B', 'C']) {
    const id = `${cell}-${replicate}`;
    const manifest = await makeManifest({
      cell, replicate, records: groups.get(id), dir: aggregate.get(id), specSha, tools, sentinels,
    });
    const path = resolve(evidenceRoot, `${id}.manifest.json`);
    await writeFile(path, serialize(manifest));
    const reason = await validateManifest({ path, dir: aggregate.get(id), expectedSpecSha: specSha, tools, sentinels });
    if (reason !== 'OK') throw new Error(`Manifest ${id}: ${reason}`);
    manifests.set(id, { manifest, path, dir: aggregate.get(id) });
  }
}

const comparisons = new Map();
for (const cell of ['T01', 'T08']) {
  for (const [aId, bId] of [['A', 'B'], ['A', 'C'], ['B', 'C']]) {
    const id = `${cell}-${aId}-${bId}`;
    const comparisonPath = resolve(comparisonEvidence, `${id}.comparison.json`);
    const bindingPath = resolve(comparisonEvidence, `${id}.binding.json`);
    const a = manifests.get(`${cell}-${aId}`);
    const b = manifests.get(`${cell}-${bId}`);
    await run(blender, [
      '--factory-startup', '--background', '--python-exit-code', '1', '--python', comparator, '--',
      '--a-dir', a.dir, '--b-dir', b.dir, '--frames', sentinels.join(','), '--output', comparisonPath,
    ]);
    const comparison = JSON.parse(await readFile(comparisonPath, 'utf8'));
    const bindingBody = {
      documentType: 'BFS_B22_COMPARISON_BINDING', version: '0.1.0', id, cell,
      aReplicate: aId, bReplicate: bId,
      aManifestHash: a.manifest.manifestHash,
      bManifestHash: b.manifest.manifestHash,
      comparatorSha256: tools.comparatorSha256,
      comparisonSha256: await sha256File(comparisonPath),
    };
    const binding = { ...bindingBody, bindingHash: sha256Canonical(bindingBody) };
    await writeFile(bindingPath, serialize(binding));
    const reason = await validateComparison({
      bindingPath, comparisonPath, a: a.manifest, b: b.manifest,
      expectedComparatorSha: tools.comparatorSha256, sentinels,
    });
    if (reason !== 'OK') throw new Error(`${id}: ${reason}`);
    comparisons.set(id, { id, cell, comparison, comparisonPath, bindingPath, binding });
  }
}

const attacks = [];
const attack = (id, expectedReason, observedReason) => attacks.push({
  id, expectedReason, observedReason, pass: expectedReason === observedReason,
});
const baseRecord = records.get('T01-0001-A');
const defaults = {
  record: baseRecord, identities, expectedSpecSha: specSha,
  expectedB21Sha: spec.evidenceBasis.b21ResultsSha256,
  expectedInventorySha: spec.evidenceBasis.controlInventorySha256,
};
attack('N_B22_SPEC_SHA', 'B22_SPEC_SHA', await validateRun({ ...defaults, expectedSpecSha: '0'.repeat(64) }));
attack('N_B21_RESULT_SHA', 'B21_RESULT_SHA', await validateRun({ ...defaults, expectedB21Sha: '0'.repeat(64) }));
attack('N_CONTROL_INVENTORY_SHA', 'CONTROL_INVENTORY_SHA', await validateRun({ ...defaults, expectedInventorySha: '0'.repeat(64) }));
attack('N_REVIEW_SPEC_SHA', 'REVIEW_SPEC_SHA', await validateRun({ ...defaults, identities: { ...identities, reviewRenderSpecSha256: '0'.repeat(64) } }));
attack('N_BLENDER_SHA', 'BLENDER_SHA', await validateRun({ ...defaults, identities: { ...identities, blenderSha256: '0'.repeat(64) } }));
attack('N_OCIO_SHA', 'OCIO_SHA', await validateRun({ ...defaults, identities: { ...identities, ocioSha256: '0'.repeat(64) } }));
attack('N_SCENE_SHA', 'SCENE_SHA', await validateRun({ ...defaults, identities: { ...identities, sceneBlendSha256: '0'.repeat(64) } }));
attack('N_CONFIGURATOR_SHA', 'CONFIGURATOR_SHA', await validateRun({ ...defaults, identities: { ...identities, configuratorSha256: '0'.repeat(64) } }));
attack('N_RENDERER_SHA', 'RENDERER_SHA', await validateRun({ ...defaults, identities: { ...identities, rendererSha256: '0'.repeat(64) } }));
const baseComparison = comparisons.get('T01-A-B');
attack('N_COMPARATOR_SHA', 'COMPARATOR_SHA', await validateComparison({
  bindingPath: baseComparison.bindingPath, comparisonPath: baseComparison.comparisonPath,
  a: manifests.get('T01-A').manifest, b: manifests.get('T01-B').manifest,
  expectedComparatorSha: '0'.repeat(64), sentinels,
}));
attack('N_SOURCE_THREAD_STATE', 'SOURCE_THREAD_STATE', await validateRun({ ...defaults, expectedSourceThreads: 7 }));
attack('N_REQUESTED_THREAD_MODE', 'REQUESTED_THREAD_MODE', await validateRun({ ...defaults, expectedRequestedMode: 'AUTO' }));
attack('N_REQUESTED_THREAD_COUNT', 'REQUESTED_THREAD_COUNT', await validateRun({ ...defaults, expectedRequestedThreads: 7 }));
attack('N_RENDER_SAMPLES', 'RENDER_SAMPLES', await validateRun({ ...defaults, expectedSamples: 31 }));
attack('N_FIXED_RENDER_CONSTANTS', 'FIXED_RENDER_CONSTANTS', await validateRun({
  ...defaults, expectedConstants: { ditherIntensity: 1, useFastGi: true, useTaaReprojection: true },
}));
attack('N_RENDER_CALL_COUNT', 'RENDER_CALL_COUNT', await validateRun({ ...defaults, expectedRenderCalls: 2 }));
attack('N_EXR_LAYOUT', 'EXR_LAYOUT', await validateRun({
  ...defaults, expectedLayout: { width: 960, height: 540, channels: ['R', 'G', 'B', 'A'], pixelFormat: 'half' },
}));
const attackRoot = resolve(workRoot, 'attacks');
await mkdir(attackRoot, { recursive: true });
const missingDir = resolve(attackRoot, 'missing');
await mkdir(missingDir, { recursive: true });
for (const frame of sentinels) {
  const name = `frame-${String(frame).padStart(4, '0')}.exr`;
  await copyFile(resolve(manifests.get('T01-A').dir, name), resolve(missingDir, name));
}
await unlink(resolve(missingDir, 'frame-0110.exr'));
attack('N_MISSING_OR_MUTATED_EXR', 'MISSING_OR_MUTATED_EXR', await validateManifest({
  path: manifests.get('T01-A').path, dir: missingDir, expectedSpecSha: specSha, tools, sentinels,
}));
const badBindingBody = JSON.parse(await readFile(baseComparison.bindingPath, 'utf8'));
delete badBindingBody.bindingHash;
badBindingBody.aManifestHash = '0'.repeat(64);
const badBinding = { ...badBindingBody, bindingHash: sha256Canonical(badBindingBody) };
const badBindingPath = resolve(attackRoot, 'bad-binding.json');
await writeFile(badBindingPath, serialize(badBinding));
attack('N_COMPARISON_FILE_BINDING', 'COMPARISON_FILE_BINDING', await validateComparison({
  bindingPath: badBindingPath, comparisonPath: baseComparison.comparisonPath,
  a: manifests.get('T01-A').manifest, b: manifests.get('T01-B').manifest,
  expectedComparatorSha: tools.comparatorSha256, sentinels,
}));

function cellSummary(cell) {
  const selected = [...comparisons.values()].filter(item => item.cell === cell);
  const exactDecodedComparisons = selected.reduce(
    (sum, item) => sum + item.comparison.decodedPixelExactFrames, 0,
  );
  return {
    threadsMode: 'FIXED', threads: cell === 'T01' ? 1 : 8,
    pairCount: selected.length, totalDecodedComparisons: 36,
    exactDecodedComparisons,
    maximumAbsoluteError: Math.max(...selected.map(item => item.comparison.maximumAbsoluteError)),
    totalFailurePixels: selected.reduce((sum, item) => sum + item.comparison.totalFailurePixels, 0),
    exact: exactDecodedComparisons === 36 && selected.every(
      item => item.comparison.maximumAbsoluteError === 0 && item.comparison.totalFailurePixels === 0,
    ),
  };
}

const t01 = cellSummary('T01');
const t08 = cellSummary('T08');
const validExperiment = attacks.length === 19 && attacks.every(item => item.pass);
let decision = 'VARIATION_NOT_REPRODUCED';
if (!validExperiment) decision = 'INVALID_EXPERIMENT';
else if (t01.exact && !t08.exact) decision = 'THREAD_COUNT_CAUSAL_SUPPORT';
else if (!t01.exact && !t08.exact) decision = 'THREAD_COUNT_NOT_SUFFICIENT';
else if (!t01.exact && t08.exact) decision = 'REVERSE_OR_MIXED_THREAD_PATTERN';

const result = {
  documentType: 'BFS_B22_EEVEE_THREAD_COUNT_FACTORIAL_EXPERIMENT',
  version: '0.1.0', executedAtUtc: new Date().toISOString(),
  decision, validExperiment, sentinels,
  design: { ...spec.design, materializedRunOrder: runOrder.map(item => item.invocationId) },
  identities: {
    ...frozen,
    b22SpecSha256: specSha,
    b21ResultsSha256: spec.evidenceBasis.b21ResultsSha256,
    controlInventorySha256: spec.evidenceBasis.controlInventorySha256,
    ...tools,
  },
  cells: { T01: t01, T08: t08 },
  processLedger: {
    processCount: 72,
    uniqueProcessIds: new Set(ledger.processes.map(item => item.processId)).size,
    ledgerHash: ledger.ledgerHash,
    uri: repoUri(ledgerPath),
  },
  comparisons: Object.fromEntries([...comparisons].map(([id, item]) => [id, {
    cell: item.cell,
    decodedPixelExactFrames: item.comparison.decodedPixelExactFrames,
    maximumAbsoluteError: item.comparison.maximumAbsoluteError,
    totalFailurePixels: item.comparison.totalFailurePixels,
    comparisonUri: repoUri(item.comparisonPath),
    bindingHash: item.binding.bindingHash,
  }])),
  attacks,
  artifacts: {
    runOrder: repoUri(runOrderPath),
    manifests: Object.fromEntries([...manifests].map(([id, item]) => [id, repoUri(item.path)])),
    renders: repoUri(renderEvidence),
    comparisons: repoUri(comparisonEvidence),
  },
  nonClaims: spec.explicitNonClaims,
};
await writeFile(resolve(experimentRoot, 'results.json'), serialize(result));
process.stdout.write(
  `BFS_B22_THREAD_FACTORIAL ${decision} T01=${t01.exactDecodedComparisons}/36 ` +
  `T08=${t08.exactDecodedComparisons}/36 pids=${result.processLedger.uniqueProcessIds}/72 ` +
  `attacks=${attacks.filter(item => item.pass).length}/${attacks.length}\n`,
);
if (!validExperiment) process.exitCode = 1;
