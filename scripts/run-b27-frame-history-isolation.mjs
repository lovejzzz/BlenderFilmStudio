import { mkdir, readFile, readdir, rm, writeFile } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { relative, resolve, sep } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256Canonical, sha256File } from './lib/receipt-format.mjs';

const experimentRoot = resolve(repositoryRoot, 'experiments/frame-history-isolation-v0-1');
const evidenceRoot = resolve(experimentRoot, 'evidence');
const workRoot = resolve(experimentRoot, 'work');
const specPath = resolve(repositoryRoot, 'specs/frame-history-isolation-spec.v0.1.json');
const b25ResultPath = resolve(repositoryRoot, 'experiments/temporal-residual-holdout-v0-1/results.json');
const b25SpecPath = resolve(repositoryRoot, 'specs/temporal-residual-holdout-spec.v0.1.json');
const reviewSpecPath = resolve(repositoryRoot, 'specs/review-render-spec.v0.1.json');
const configurator = resolve(repositoryRoot, 'blender/configure_eevee_threads.py');
const renderer = resolve(repositoryRoot, 'blender/render_b27_frame_history.py');
const comparator = resolve(repositoryRoot, 'blender/compare_b27_frame_history.py');
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

function expectedFrames(cell) { return cell === 'HISTORY' ? Array.from({ length: 38 }, (_, index) => index + 1) : [38]; }

async function makeManifest(record, specSha, tools) {
  const body = {
    documentType: 'BFS_B27_RENDER_MANIFEST', version: '0.1.0', b27SpecSha256: specSha,
    cell: record.cell, replicate: record.replicate, processId: record.processId,
    toolIdentities: tools,
    renderReportSha256: await sha256File(record.reportPath),
    interventionReportSha256: await sha256File(record.interventionPath),
    frameOrder: record.report.frameOrder,
    frames: record.report.frames.map(frame => ({
      renderCallOrdinal: frame.renderCallOrdinal,
      frame: frame.frame,
      uri: repoUri(resolve(record.outputDir, frame.name)),
      name: frame.name,
      sha256: frame.sha256,
      bytes: frame.bytes,
    })),
  };
  return { ...body, manifestHash: sha256Canonical(body) };
}

async function validateRun({
  record, spec, identities, tools,
  expectedSpecSha = identities.b27SpecSha256,
  expectedB25ResultSha = identities.b25ResultsSha256,
  expectedB25SpecSha = identities.b25SpecSha256,
  expectedReviewSpecSha = identities.reviewRenderSpecSha256,
  expectedBlenderSha = identities.blenderSha256,
  expectedOcioSha = identities.ocioSha256,
  expectedSceneSha = identities.sceneBlendSha256,
  expectedPlanHash = identities.planHash,
  expectedStructureHash = identities.structureHash,
  expectedConfiguratorSha = tools.configuratorSha256,
  expectedRendererSha = tools.rendererSha256,
  expectedReferenceSha = identities.referenceContainerSha256,
  expectedThreads = 8,
  expectedProcessId = record.processId,
  expectedCell = record.cell,
  expectedReplicate = record.replicate,
  expectedFrameOrder = expectedFrames(record.cell),
  expectedFirstOutputSha = record.report.frames[0].sha256,
}) {
  if (await sha256File(specPath) !== expectedSpecSha) return 'B27_SPEC_SHA';
  if (await sha256File(b25ResultPath) !== expectedB25ResultSha || await sha256File(b25SpecPath) !== expectedB25SpecSha) return 'B25_EVIDENCE_SHA';
  if (await sha256File(reviewSpecPath) !== expectedReviewSpecSha) return 'REVIEW_SPEC_SHA';
  if (await sha256File(blender) !== expectedBlenderSha) return 'BLENDER_SHA';
  if (await sha256File(identities.ocioPath) !== expectedOcioSha) return 'OCIO_SHA';
  if (await sha256File(identities.scenePath) !== expectedSceneSha) return 'SCENE_SHA';
  if (await sha256File(configurator) !== expectedConfiguratorSha) return 'CONFIGURATOR_SHA';
  if (await sha256File(renderer) !== expectedRendererSha) return 'RENDERER_SHA';
  if (await sha256File(identities.referencePath) !== expectedReferenceSha) return 'REFERENCE_IDENTITY';

  const intervention = JSON.parse(await readFile(record.interventionPath, 'utf8'));
  if (intervention.before.threadsMode !== 'FIXED' || intervention.before.threads !== expectedThreads
      || intervention.after.threadsMode !== 'FIXED' || intervention.after.threads !== 8
      || intervention.after.ditherIntensity !== 0 || intervention.after.useFastGi !== true
      || intervention.after.useTaaReprojection !== true || intervention.savedSourceBlend !== false) return 'SOURCE_OR_FIXED_CONTROLS';
  const report = JSON.parse(await readFile(record.reportPath, 'utf8'));
  if (report.processId !== expectedProcessId || report.cell !== expectedCell || report.replicate !== expectedReplicate) return 'PROCESS_CELL_BINDING';
  if (report.b27SpecSha256 !== identities.b27SpecSha256 || report.documentType !== 'BFS_B27_FRAME_HISTORY_RENDER') return 'B27_SPEC_SHA';
  if (report.source.sceneBlendSha256 !== expectedSceneSha || report.source.planHash !== expectedPlanHash || report.source.structureHash !== expectedStructureHash) return 'PLAN_OR_STRUCTURE_IDENTITY';
  if (report.savedSourceBlend !== false || report.cameraAndTimelineInvariant !== true) return 'SOURCE_OR_FIXED_CONTROLS';
  const expectedCalls = expectedFrameOrder.length;
  if (JSON.stringify(report.frameOrder) !== JSON.stringify(expectedFrameOrder)
      || report.renderOperatorCallCount !== expectedCalls || report.outputFileCount !== expectedCalls
      || report.frames.length !== expectedCalls) return record.cell === 'HISTORY' ? 'HISTORY_FRAME_ORDER_COUNT' : 'DIRECT_FRAME_ORDER_COUNT';
  if (report.renderCallsBeforeTarget !== expectedCalls - 1 || report.target.frame !== 38) return record.cell === 'HISTORY' ? 'HISTORY_FRAME_ORDER_COUNT' : 'DIRECT_FRAME_ORDER_COUNT';
  if (report.observedControls.threadsMode !== 'FIXED' || report.observedControls.threads !== 8
      || report.observedControls.renderSamples !== 32 || report.observedControls.ditherIntensity !== 0
      || report.observedControls.useFastGi !== true || report.observedControls.useTaaReprojection !== true
      || report.observedControls.motionBlur !== false) return 'SOURCE_OR_FIXED_CONTROLS';
  if (report.profile.width !== 960 || report.profile.height !== 540 || report.profile.imageFormat !== 'PNG'
      || report.profile.colorMode !== 'RGBA' || report.profile.colorDepth !== '8') return 'PNG_LAYOUT';
  const names = (await readdir(record.outputDir)).filter(name => name.endsWith('.png')).sort();
  if (names.length !== expectedCalls) return 'MISSING_OR_MUTATED_OUTPUT';
  for (const frame of report.frames) {
    if (!names.includes(frame.name) || await sha256File(resolve(record.outputDir, frame.name)) !== frame.sha256) return 'MISSING_OR_MUTATED_OUTPUT';
  }
  if (report.frames[0].sha256 !== expectedFirstOutputSha) return 'MISSING_OR_MUTATED_OUTPUT';
  if (spec.executionContract.humanReviewMustRemainPending !== true) return 'HUMAN_REVIEW_STATUS';
  return 'OK';
}

async function validateManifest({ record, expectedSpecSha, tools }) {
  const manifest = JSON.parse(await readFile(record.manifestPath, 'utf8'));
  const body = structuredClone(manifest); delete body.manifestHash;
  if (sha256Canonical(body) !== manifest.manifestHash) return 'MANIFEST_SELF_HASH';
  if (manifest.b27SpecSha256 !== expectedSpecSha || manifest.cell !== record.cell || manifest.replicate !== record.replicate || manifest.processId !== record.processId) return 'PROCESS_CELL_BINDING';
  if (JSON.stringify(manifest.toolIdentities) !== JSON.stringify(tools)) return 'MANIFEST_TOOL_BINDING';
  for (const frame of manifest.frames) if (await sha256File(resolve(repositoryRoot, frame.uri)) !== frame.sha256) return 'MISSING_OR_MUTATED_OUTPUT';
  return 'OK';
}

async function validateLedger({ ledgerPath, expectedOrder, expectedProcessCount = 24 }) {
  const ledger = JSON.parse(await readFile(ledgerPath, 'utf8'));
  const body = structuredClone(ledger); delete body.ledgerHash;
  if (sha256Canonical(body) !== ledger.ledgerHash) return 'LEDGER_SELF_HASH';
  if (JSON.stringify(ledger.processes.map(item => item.replicate)) !== JSON.stringify(expectedOrder)) return 'PROCESS_ORDER';
  if (ledger.processes.length !== expectedProcessCount || new Set(ledger.processes.map(item => item.processId)).size !== expectedProcessCount) return 'PID_UNIQUENESS';
  return 'OK';
}

function choose(n, k) {
  if (k < 0 || k > n) return 0;
  let value = 1;
  for (let index = 1; index <= Math.min(k, n - k); index += 1) value = value * (n - index + 1) / index;
  return value;
}

function fisherTwoSided(a, b, c, d) {
  const rowH = a + b, rowD = c + d, failures = a + c, total = rowH + rowD;
  const denominator = choose(total, failures);
  const probability = h => choose(rowH, h) * choose(rowD, failures - h) / denominator;
  const observed = probability(a);
  let sum = 0;
  for (let h = Math.max(0, failures - rowD); h <= Math.min(rowH, failures); h += 1) if (probability(h) <= observed + 1e-15) sum += probability(h);
  return Math.min(1, sum);
}

async function validateComparison({
  comparisonPath, bindingPath, indexPath, manifests, spec, identities, tools,
  expectedComparatorSha = tools.comparatorSha256,
  expectedRunnerSha = tools.runnerSha256,
  expectedReferenceSha = identities.referenceContainerSha256,
  expectedReferenceDecodedSha = identities.referenceDecodedRgbSha256,
  expectedIndexSha = null,
  expectedEnvelope = spec.frozenStaticEnvelope,
  expectedWidth = 960,
  expectedAlpha = 0.05,
  expectedEndpoint = 'fixedReferenceStaticEnvelopeFailure',
  expectedSampleCount = 24,
}) {
  const resolvedExpectedIndexSha = expectedIndexSha ?? await sha256File(indexPath);
  if (await sha256File(comparator) !== expectedComparatorSha) return 'COMPARATOR_SHA';
  if (await sha256File(runner) !== expectedRunnerSha) return 'RUNNER_SHA';
  if (await sha256File(identities.referencePath) !== expectedReferenceSha) return 'REFERENCE_IDENTITY';
  const binding = JSON.parse(await readFile(bindingPath, 'utf8'));
  const bindingBody = structuredClone(binding); delete bindingBody.bindingHash;
  if (sha256Canonical(bindingBody) !== binding.bindingHash) return 'COMPARISON_SELF_HASH';
  if (binding.indexSha256 !== resolvedExpectedIndexSha || binding.comparisonSha256 !== await sha256File(comparisonPath)) return 'COMPARISON_BINDING';
  if (binding.comparatorSha256 !== tools.comparatorSha256 || binding.runnerSha256 !== tools.runnerSha256) return 'COMPARISON_BINDING';
  const expectedManifestHashes = Object.fromEntries([...manifests].map(([id, item]) => [id, item.manifest.manifestHash]));
  if (JSON.stringify(binding.manifestHashes) !== JSON.stringify(expectedManifestHashes)) return 'COMPARISON_BINDING';
  const comparison = JSON.parse(await readFile(comparisonPath, 'utf8'));
  if (comparison.b27SpecSha256 !== identities.b27SpecSha256 || comparison.indexSha256 !== resolvedExpectedIndexSha) return 'COMPARISON_BINDING';
  if (comparison.reference.containerSha256 !== expectedReferenceSha || comparison.reference.decodedRgbSha256 !== expectedReferenceDecodedSha) return 'REFERENCE_IDENTITY';
  if (comparison.layout.width !== expectedWidth || comparison.layout.height !== 540 || JSON.stringify(comparison.layout.channels) !== JSON.stringify(['R', 'G', 'B', 'A']) || comparison.layout.pixelFormat !== 'uint8') return 'PNG_LAYOUT';
  if (sha256Canonical(comparison.frozenStaticEnvelope) !== sha256Canonical(expectedEnvelope)) return 'STATIC_ENVELOPE_MUTATION';
  if (comparison.samples.length !== expectedSampleCount || comparison.referenceComparisonSummary.HISTORY.samples !== 12 || comparison.referenceComparisonSummary.DIRECT.samples !== 12) return 'PRIMARY_CONTRACT_MUTATION';
  if (comparison.primary.alpha !== expectedAlpha || comparison.primary.endpoint !== expectedEndpoint || comparison.primary.test !== 'two-sided Fisher exact test') return 'PRIMARY_CONTRACT_MUTATION';
  const table = comparison.primary.table;
  const independentP = fisherTwoSided(table.historyFail, table.historyPass, table.directFail, table.directPass);
  if (Math.abs(independentP - comparison.primary.twoSidedFisherExactP) > 1e-12) return 'PRIMARY_CONTRACT_MUTATION';
  if (comparison.withinCell.HISTORY.summary.comparisons !== 66 || comparison.withinCell.DIRECT.summary.comparisons !== 66 || comparison.crossCell.summary.comparisons !== 144) return 'PRIMARY_CONTRACT_MUTATION';
  for (const sample of comparison.samples) {
    const manifest = manifests.get(sample.replicate)?.manifest;
    const target = manifest?.frames.at(-1);
    if (!manifest || sample.manifestHash !== manifest.manifestHash || sample.containerSha256 !== target.sha256 || sample.fileUri !== target.uri) return 'COMPARISON_BINDING';
  }
  if (spec.executionContract.humanReviewMustRemainPending !== true) return 'HUMAN_REVIEW_STATUS';
  return 'OK';
}

await rm(evidenceRoot, { recursive: true, force: true });
await rm(workRoot, { recursive: true, force: true });
await mkdir(evidenceRoot, { recursive: true });
await mkdir(workRoot, { recursive: true });
const spec = JSON.parse(await readFile(specPath, 'utf8'));
const specSha = await sha256File(specPath);
if (specSha !== '2b0a9f5ec9168fdb7589c4a69366ca58c2dd79c52cf3a17030c45eecd7b7b8a2') throw new Error('B27 spec changed after pre-registration');
const b25Result = JSON.parse(await readFile(b25ResultPath, 'utf8'));
if (b25Result.decision !== spec.evidenceBasis.b25Decision) throw new Error('B25 decision mismatch');
const reviewSpec = JSON.parse(await readFile(reviewSpecPath, 'utf8'));
const receiptPath = resolve(repositoryRoot, reviewSpec.source.receiptUri);
const receipt = JSON.parse(await readFile(receiptPath, 'utf8'));
const scenePath = resolve(repositoryRoot, receipt.run.sceneBlend.uri);
const ocioPath = resolve(repositoryRoot, receipt.executionIdentity.configuration.ocio.uri);
const referencePath = resolve(repositoryRoot, spec.evidenceBasis.reference.uri);
const frozen = spec.frozenIdentity;
for (const [path, expected, label] of [
  [b25ResultPath, spec.evidenceBasis.b25ResultsSha256, 'B25 result'], [b25SpecPath, spec.evidenceBasis.b25SpecSha256, 'B25 spec'],
  [reviewSpecPath, frozen.reviewRenderSpecSha256, 'review spec'], [blender, frozen.blenderSha256, 'Blender'],
  [ocioPath, frozen.ocioSha256, 'OCIO'], [scenePath, frozen.sceneBlendSha256, 'scene'],
  [configurator, frozen.configuratorSha256, 'configurator'], [referencePath, spec.evidenceBasis.reference.containerSha256, 'reference'],
]) if (await sha256File(path) !== expected) throw new Error(`${label} frozen SHA mismatch`);
const tools = {
  configuratorSha256: await sha256File(configurator), rendererSha256: await sha256File(renderer),
  comparatorSha256: await sha256File(comparator), runnerSha256: await sha256File(runner),
};
const identities = {
  ...frozen, b27SpecSha256: specSha, b25ResultsSha256: await sha256File(b25ResultPath), b25SpecSha256: await sha256File(b25SpecPath),
  referenceContainerSha256: spec.evidenceBasis.reference.containerSha256, referenceDecodedRgbSha256: spec.evidenceBasis.reference.decodedRgbSha256,
  scenePath, ocioPath, referencePath,
};

const records = new Map();
const manifests = new Map();
for (const replicate of spec.design.processOrder) {
  const cell = replicate.startsWith('H') ? 'HISTORY' : 'DIRECT';
  const outputDir = resolve(workRoot, replicate);
  const reportPath = resolve(evidenceRoot, `${replicate}.render.json`);
  const interventionPath = resolve(evidenceRoot, `${replicate}.intervention.json`);
  const manifestPath = resolve(evidenceRoot, `${replicate}.manifest.json`);
  await mkdir(outputDir, { recursive: true });
  const launched = await run(blender, [
    '--background', scenePath, '--disable-autoexec', '--python-exit-code', '1',
    '--python', configurator, '--python', renderer, '--',
    '--b27-spec', specPath, '--review-spec', reviewSpecPath, '--receipt', receiptPath,
    '--output-dir', outputDir, '--report', reportPath, '--cell', cell, '--replicate', replicate,
  ], {
    ...process.env, OCIO: ocioPath, BFS_B22_THREADS_MODE: 'FIXED', BFS_B22_THREADS: '8', BFS_B22_CELL: 'T08',
    BFS_B22_INTERVENTION_REPORT: interventionPath,
  });
  const report = JSON.parse(await readFile(reportPath, 'utf8'));
  const record = { replicate, cell, processId: launched.processId, outputDir, reportPath, interventionPath, manifestPath, report };
  const reason = await validateRun({ record, spec, identities, tools });
  if (reason !== 'OK') throw new Error(`${replicate}: ${reason}`);
  const manifest = await makeManifest(record, specSha, tools);
  await writeFile(manifestPath, serialize(manifest));
  record.manifest = manifest;
  const manifestReason = await validateManifest({ record, expectedSpecSha: specSha, tools });
  if (manifestReason !== 'OK') throw new Error(`${replicate} manifest: ${manifestReason}`);
  records.set(replicate, record);
  manifests.set(replicate, { manifest, path: manifestPath });
  process.stdout.write(`BFS_B27_PROCESS_OK ${replicate} cell=${cell} pid=${record.processId} calls=${report.renderOperatorCallCount} seconds=${report.totalRenderSeconds}\n`);
}

const ledgerBody = {
  documentType: 'BFS_B27_PROCESS_LEDGER', version: '0.1.0', b27SpecSha256: specSha,
  scheduleSeed: spec.design.scheduleSeed, scheduleSeedSha256: spec.design.scheduleSeedSha256,
  processes: spec.design.processOrder.map((replicate, orderIndex) => {
    const record = records.get(replicate);
    return {
      orderIndex, replicate, cell: record.cell, processId: record.processId,
      renderCalls: record.report.renderOperatorCallCount,
      frameOrder: record.report.frameOrder,
      renderReportSha256: null,
      interventionReportSha256: null,
      manifestHash: record.manifest.manifestHash,
    };
  }),
};
for (const item of ledgerBody.processes) {
  item.renderReportSha256 = await sha256File(records.get(item.replicate).reportPath);
  item.interventionReportSha256 = await sha256File(records.get(item.replicate).interventionPath);
}
const ledger = { ...ledgerBody, ledgerHash: sha256Canonical(ledgerBody) };
const ledgerPath = resolve(evidenceRoot, 'process-ledger.json');
await writeFile(ledgerPath, serialize(ledger));
const ledgerReason = await validateLedger({ ledgerPath, expectedOrder: spec.design.processOrder });
if (ledgerReason !== 'OK') throw new Error(`Process ledger: ${ledgerReason}`);

const indexBody = {
  documentType: 'BFS_B27_COMPARISON_INDEX', version: '0.1.0', b27SpecSha256: specSha,
  reference: spec.evidenceBasis.reference,
  samples: spec.design.processOrder.map(replicate => {
    const record = records.get(replicate), target = record.manifest.frames.at(-1);
    return { replicate, cell: record.cell, processId: record.processId, manifestHash: record.manifest.manifestHash, fileUri: target.uri, containerSha256: target.sha256 };
  }),
};
const index = { ...indexBody, indexHash: sha256Canonical(indexBody) };
const indexPath = resolve(evidenceRoot, 'comparison-index.json');
await writeFile(indexPath, serialize(index));
const comparisonPath = resolve(evidenceRoot, 'frame-0038.comparison.json');
await run(blender, ['--factory-startup', '--background', '--disable-autoexec', '--python-exit-code', '1', '--python', comparator, '--', '--index', indexPath, '--spec', specPath, '--output', comparisonPath]);
const comparison = JSON.parse(await readFile(comparisonPath, 'utf8'));
const manifestHashes = Object.fromEntries([...manifests].map(([id, item]) => [id, item.manifest.manifestHash]));
const bindingBody = {
  documentType: 'BFS_B27_COMPARISON_BINDING', version: '0.1.0', b27SpecSha256: specSha,
  indexSha256: await sha256File(indexPath), referenceContainerSha256: identities.referenceContainerSha256,
  manifestHashes, comparatorSha256: tools.comparatorSha256, runnerSha256: tools.runnerSha256,
  envelopeHash: sha256Canonical(spec.frozenStaticEnvelope), primaryContractHash: sha256Canonical(spec.primaryEndpoint),
  comparisonSha256: await sha256File(comparisonPath),
};
const binding = { ...bindingBody, bindingHash: sha256Canonical(bindingBody) };
const bindingPath = resolve(evidenceRoot, 'frame-0038.binding.json');
await writeFile(bindingPath, serialize(binding));
const comparisonReason = await validateComparison({ comparisonPath, bindingPath, indexPath, manifests, spec, identities, tools });
if (comparisonReason !== 'OK') throw new Error(`Comparison: ${comparisonReason}`);

const attacks = [];
const attack = (id, expected, observed) => attacks.push({ id, expected, observed, pass: expected === observed });
const baseHistory = records.get('H01');
const baseDirect = records.get('D01');
attack('N_B27_SPEC_IDENTITY', 'B27_SPEC_SHA', await validateRun({ record: baseHistory, spec, identities, tools, expectedSpecSha: '0'.repeat(64) }));
attack('N_B25_EVIDENCE_IDENTITY', 'B25_EVIDENCE_SHA', await validateRun({ record: baseHistory, spec, identities, tools, expectedB25ResultSha: '0'.repeat(64) }));
attack('N_REVIEW_SPEC_IDENTITY', 'REVIEW_SPEC_SHA', await validateRun({ record: baseHistory, spec, identities, tools, expectedReviewSpecSha: '0'.repeat(64) }));
attack('N_BLENDER_IDENTITY', 'BLENDER_SHA', await validateRun({ record: baseHistory, spec, identities, tools, expectedBlenderSha: '0'.repeat(64) }));
attack('N_OCIO_IDENTITY', 'OCIO_SHA', await validateRun({ record: baseHistory, spec, identities, tools, expectedOcioSha: '0'.repeat(64) }));
attack('N_SCENE_IDENTITY', 'SCENE_SHA', await validateRun({ record: baseHistory, spec, identities, tools, expectedSceneSha: '0'.repeat(64) }));
attack('N_PLAN_STRUCTURE_IDENTITY', 'PLAN_OR_STRUCTURE_IDENTITY', await validateRun({ record: baseHistory, spec, identities, tools, expectedPlanHash: '0'.repeat(64) }));
attack('N_CONFIGURATOR_IDENTITY', 'CONFIGURATOR_SHA', await validateRun({ record: baseHistory, spec, identities, tools, expectedConfiguratorSha: '0'.repeat(64) }));
attack('N_RENDERER_IDENTITY', 'RENDERER_SHA', await validateRun({ record: baseHistory, spec, identities, tools, expectedRendererSha: '0'.repeat(64) }));
attack('N_COMPARATOR_IDENTITY', 'COMPARATOR_SHA', await validateComparison({ comparisonPath, bindingPath, indexPath, manifests, spec, identities, tools, expectedComparatorSha: '0'.repeat(64) }));
attack('N_RUNNER_IDENTITY', 'RUNNER_SHA', await validateComparison({ comparisonPath, bindingPath, indexPath, manifests, spec, identities, tools, expectedRunnerSha: '0'.repeat(64) }));
attack('N_REFERENCE_IDENTITY', 'REFERENCE_IDENTITY', await validateRun({ record: baseHistory, spec, identities, tools, expectedReferenceSha: '0'.repeat(64) }));
attack('N_SOURCE_FIXED_CONTROLS', 'SOURCE_OR_FIXED_CONTROLS', await validateRun({ record: baseHistory, spec, identities, tools, expectedThreads: 7 }));
const attackedOrder = [...spec.design.processOrder]; [attackedOrder[0], attackedOrder[1]] = [attackedOrder[1], attackedOrder[0]];
attack('N_PROCESS_ORDER', 'PROCESS_ORDER', await validateLedger({ ledgerPath, expectedOrder: attackedOrder }));
attack('N_PID_CELL_BINDING', 'PROCESS_CELL_BINDING', await validateRun({ record: baseHistory, spec, identities, tools, expectedProcessId: -1 }));
attack('N_HISTORY_FRAME_ORDER', 'HISTORY_FRAME_ORDER_COUNT', await validateRun({ record: baseHistory, spec, identities, tools, expectedFrameOrder: expectedFrames('HISTORY').slice(1) }));
attack('N_DIRECT_FRAME_ORDER', 'DIRECT_FRAME_ORDER_COUNT', await validateRun({ record: baseDirect, spec, identities, tools, expectedFrameOrder: [37, 38] }));
attack('N_PNG_LAYOUT', 'PNG_LAYOUT', await validateComparison({ comparisonPath, bindingPath, indexPath, manifests, spec, identities, tools, expectedWidth: 961 }));
attack('N_OUTPUT_MUTATION', 'MISSING_OR_MUTATED_OUTPUT', await validateRun({ record: baseHistory, spec, identities, tools, expectedFirstOutputSha: '0'.repeat(64) }));
attack('N_COMPARISON_BINDING', 'COMPARISON_BINDING', await validateComparison({ comparisonPath, bindingPath, indexPath, manifests, spec, identities, tools, expectedIndexSha: '0'.repeat(64) }));
attack('N_STATIC_ENVELOPE', 'STATIC_ENVELOPE_MUTATION', await validateComparison({ comparisonPath, bindingPath, indexPath, manifests, spec, identities, tools, expectedEnvelope: { ...spec.frozenStaticEnvelope, zeroThresholdFailurePixelsAtMost: 17 } }));
attack('N_PRIMARY_CONTRACT', 'PRIMARY_CONTRACT_MUTATION', await validateComparison({ comparisonPath, bindingPath, indexPath, manifests, spec, identities, tools, expectedAlpha: 0.04 }));
const nonPendingSpec = structuredClone(spec); nonPendingSpec.executionContract.humanReviewMustRemainPending = false;
attack('N_HUMAN_STATUS', 'HUMAN_REVIEW_STATUS', await validateComparison({ comparisonPath, bindingPath, indexPath, manifests, spec: nonPendingSpec, identities, tools }));

const allAttacksPass = attacks.length === spec.requiredNegativeCases.length && attacks.every(item => item.pass);
const uniqueRenderProcesses = new Set([...records.values()].map(record => record.processId)).size;
const validExperiment = allAttacksPass && uniqueRenderProcesses === 24 && comparisonReason === 'OK' && ledgerReason === 'OK';
const table = comparison.primary.table;
let decision = 'INVALID_EXPERIMENT';
if (validExperiment && table.historyFail + table.directFail === 0) decision = 'B25_ENVELOPE_FAILURE_NOT_REPRODUCED';
else if (validExperiment && comparison.primary.significant && table.historyFail > table.directFail) decision = 'HISTORY_ASSOCIATION_SUPPORT';
else if (validExperiment && comparison.primary.significant && table.directFail > table.historyFail) decision = 'OPPOSITE_DIRECTION_ASSOCIATION';
else if (validExperiment) decision = 'FAILURE_REPRODUCED_NO_SIGNIFICANT_HISTORY_ASSOCIATION';
const result = {
  documentType: 'BFS_B27_FRAME_HISTORY_ISOLATION_RESULT', version: '0.1.0', executedAtUtc: new Date().toISOString(),
  decision, validExperiment,
  humanReview: { status: 'PENDING', claim: 'Automation cannot determine visibility, flicker perception or cinematic quality.' },
  question: spec.question,
  design: spec.design,
  identities: { ...frozen, b27SpecSha256: specSha, b25ResultsSha256: identities.b25ResultsSha256, b25SpecSha256: identities.b25SpecSha256, referenceContainerSha256: identities.referenceContainerSha256, referenceDecodedRgbSha256: identities.referenceDecodedRgbSha256, ...tools },
  frozenStaticEnvelope: spec.frozenStaticEnvelope,
  primary: comparison.primary,
  referenceComparisonSummary: comparison.referenceComparisonSummary,
  variants: comparison.variants,
  pairwiseSummary: {
    withinHistory: comparison.withinCell.HISTORY.summary,
    withinDirect: comparison.withinCell.DIRECT.summary,
    crossCell: comparison.crossCell.summary,
  },
  aggregate: {
    uniqueRenderProcesses,
    renderProcesses: records.size,
    renderCalls: [...records.values()].reduce((sum, record) => sum + record.report.renderOperatorCallCount, 0),
    outputFiles: [...records.values()].reduce((sum, record) => sum + record.report.outputFileCount, 0),
    totalRenderSeconds: [...records.values()].reduce((sum, record) => sum + record.report.totalRenderSeconds, 0),
    attacksPassed: attacks.filter(item => item.pass).length,
    attacksTotal: attacks.length,
  },
  processLedger: ledger.processes,
  attacks,
  artifacts: {
    processLedger: repoUri(ledgerPath), comparisonIndex: repoUri(indexPath), comparison: repoUri(comparisonPath), binding: repoUri(bindingPath),
    manifests: Object.fromEntries([...manifests].map(([id, item]) => [id, repoUri(item.path)])),
    reference: spec.evidenceBasis.reference.uri,
  },
  nonClaims: spec.explicitNonClaims,
};
await writeFile(resolve(experimentRoot, 'results.json'), serialize(result));
process.stdout.write(`BFS_B27_RESULT ${decision} history_fail=${table.historyFail}/12 direct_fail=${table.directFail}/12 p=${comparison.primary.twoSidedFisherExactP} attacks=${result.aggregate.attacksPassed}/${result.aggregate.attacksTotal}\n`);
if (!validExperiment) process.exitCode = 1;
