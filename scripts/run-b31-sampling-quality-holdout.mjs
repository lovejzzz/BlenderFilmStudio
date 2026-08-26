import { mkdir, readFile, readdir, rm, writeFile } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { relative, resolve, sep } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256Canonical, sha256File } from './lib/receipt-format.mjs';

const experimentRoot = resolve(repositoryRoot, 'experiments/sampling-quality-holdout-v0-1');
const evidenceRoot = resolve(experimentRoot, 'evidence');
const workRoot = resolve(experimentRoot, 'work');
const specPath = resolve(repositoryRoot, 'specs/sampling-quality-holdout-spec.v0.1.json');
const b30ResultPath = resolve(repositoryRoot, 'experiments/fixed-jitter-intervention-v0-1/results.json');
const b30SpecPath = resolve(repositoryRoot, 'specs/fixed-jitter-intervention-spec.v0.1.json');
const derivationResultPath = resolve(repositoryRoot, 'experiments/sampling-quality-derivation-v0-1/results.json');
const derivationAnalysisPath = resolve(repositoryRoot, 'experiments/sampling-quality-derivation-v0-1/analysis.json');
const derivationRenderer = resolve(repositoryRoot, 'blender/render_b31_sampling_quality_derivation.py');
const derivationAnalyzer = resolve(repositoryRoot, 'blender/analyze_b31_sampling_quality_derivation.py');
const derivationRunner = resolve(repositoryRoot, 'scripts/run-b31-sampling-quality-derivation.mjs');
const reviewPath = resolve(repositoryRoot, 'specs/review-render-spec.v0.1.json');
const configurator = resolve(repositoryRoot, 'blender/configure_eevee_threads.py');
const renderer = resolve(repositoryRoot, 'blender/render_b31_sampling_quality_holdout.py');
const analyzer = resolve(repositoryRoot, 'blender/analyze_b31_sampling_quality_holdout.py');
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
    child.on('close', code => code === 0 ? resolvePromise({ processId, output })
      : reject(new Error(`${command} failed (${code}) pid=${processId}\n${output}`)));
  });
}

await rm(evidenceRoot, { recursive: true, force: true });
await rm(workRoot, { recursive: true, force: true });
await mkdir(evidenceRoot, { recursive: true });
await mkdir(workRoot, { recursive: true });

const spec = JSON.parse(await readFile(specPath, 'utf8'));
const specSha = await sha256File(specPath);
if (specSha !== 'e73d824cf2a1f35efb35584363205a612e624f4c9fe0d481b240dec9cddf6b55') {
  throw new Error('B31 spec changed after pre-registration');
}
const review = JSON.parse(await readFile(reviewPath, 'utf8'));
const receiptPath = resolve(repositoryRoot, review.source.receiptUri);
const receipt = JSON.parse(await readFile(receiptPath, 'utf8'));
const scenePath = resolve(repositoryRoot, receipt.run.sceneBlend.uri);
const ocioPath = resolve(repositoryRoot, receipt.executionIdentity.configuration.ocio.uri);
const frozen = spec.frozenIdentity;
const fixedInputs = [
  [b30ResultPath, spec.evidenceBasis.b30ResultsSha256, 'B30 result'], [b30SpecPath, spec.evidenceBasis.b30SpecSha256, 'B30 spec'],
  [derivationResultPath, spec.evidenceBasis.derivationResultsSha256, 'derivation result'],
  [derivationAnalysisPath, spec.evidenceBasis.derivationAnalysisSha256, 'derivation analysis'],
  [derivationRenderer, spec.evidenceBasis.derivationRendererSha256, 'derivation renderer'],
  [derivationAnalyzer, spec.evidenceBasis.derivationAnalyzerSha256, 'derivation analyzer'],
  [derivationRunner, spec.evidenceBasis.derivationRunnerSha256, 'derivation runner'],
  [reviewPath, frozen.reviewRenderSpecSha256, 'review spec'], [blender, frozen.blenderSha256, 'Blender'],
  [ocioPath, frozen.ocioSha256, 'OCIO'], [scenePath, frozen.sceneBlendSha256, 'scene'],
  [configurator, frozen.configuratorSha256, 'configurator'],
];
for (const [path, expected, label] of fixedInputs) {
  if (await sha256File(path) !== expected) throw new Error(`${label} frozen SHA mismatch`);
}
const b30Result = JSON.parse(await readFile(b30ResultPath, 'utf8'));
const derivationResult = JSON.parse(await readFile(derivationResultPath, 'utf8'));
if (b30Result.decision !== spec.evidenceBasis.b30Decision) throw new Error('B30 decision mismatch');
if (derivationResult.status !== spec.evidenceBasis.derivationStatus) throw new Error('derivation status mismatch');

const tools = { configuratorSha256: await sha256File(configurator), rendererSha256: await sha256File(renderer),
  analyzerSha256: await sha256File(analyzer), runnerSha256: await sha256File(runner) };
const records = new Map();
const manifests = new Map();
for (const replicateId of spec.design.schedule) {
  const separator = replicateId.lastIndexOf('_');
  const cell = replicateId.slice(0, separator);
  const replicate = replicateId.slice(separator + 1);
  const outputDir = resolve(workRoot, replicateId);
  const reportPath = resolve(evidenceRoot, `${replicateId}.render.json`);
  const threadPath = resolve(evidenceRoot, `${replicateId}.threads.json`);
  const manifestPath = resolve(evidenceRoot, `${replicateId}.manifest.json`);
  await mkdir(outputDir, { recursive: true });
  const launched = await run(blender, [
    '--background', scenePath, '--disable-autoexec', '--python-exit-code', '1', '--python', configurator,
    '--python', renderer, '--', '--b31-spec', specPath, '--review-spec', reviewPath, '--receipt', receiptPath,
    '--output-dir', outputDir, '--report', reportPath, '--cell', cell, '--replicate', replicate,
  ], { ...process.env, OCIO: ocioPath, BFS_B22_THREADS_MODE: 'FIXED', BFS_B22_THREADS: '8',
    BFS_B22_CELL: 'T08', BFS_B22_INTERVENTION_REPORT: threadPath });
  const report = JSON.parse(await readFile(reportPath, 'utf8'));
  if (report.processId !== launched.processId) throw new Error(`${replicateId} PID binding mismatch`);
  const threads = JSON.parse(await readFile(threadPath, 'utf8'));
  const manifestBody = {
    documentType: 'BFS_B31_RENDER_MANIFEST', version: '0.1.0', b31SpecSha256: specSha,
    replicateId, cell, replicate, processId: launched.processId, toolIdentities: tools,
    renderReportSha256: await sha256File(reportPath), threadReportSha256: await sha256File(threadPath),
    outputs: report.outputs.map(item => ({ frame: item.frame, name: item.name, fileUri: repoUri(resolve(outputDir, item.name)),
      containerSha256: item.sha256, bytes: item.bytes })),
  };
  const manifest = { ...manifestBody, manifestHash: sha256Canonical(manifestBody) };
  await writeFile(manifestPath, serialize(manifest));
  records.set(replicateId, { replicateId, cell, replicate, processId: launched.processId, outputDir,
    reportPath, threadPath, manifestPath, report, threads, manifest });
  manifests.set(replicateId, manifest);
  process.stdout.write(`BFS_B31_HOLDOUT_PROCESS_OK ${replicateId} pid=${launched.processId} seconds=${report.totalRenderSeconds}\n`);
}

const ledgerBody = {
  documentType: 'BFS_B31_PROCESS_LEDGER', version: '0.1.0', b31SpecSha256: specSha,
  processes: spec.design.schedule.map((replicateId, orderIndex) => {
    const item = records.get(replicateId);
    return { orderIndex, replicateId, cell: item.cell, replicate: item.replicate, processId: item.processId,
      frames: item.report.frames, renderCalls: item.report.renderCalls, renderReportSha256: null,
      threadReportSha256: null, manifestHash: item.manifest.manifestHash };
  }),
};
for (const item of ledgerBody.processes) {
  item.renderReportSha256 = await sha256File(records.get(item.replicateId).reportPath);
  item.threadReportSha256 = await sha256File(records.get(item.replicateId).threadPath);
}
const ledger = { ...ledgerBody, ledgerHash: sha256Canonical(ledgerBody) };
const ledgerPath = resolve(evidenceRoot, 'process-ledger.json');
await writeFile(ledgerPath, serialize(ledger));
const indexBody = {
  documentType: 'BFS_B31_ANALYSIS_INDEX', version: '0.1.0', b31SpecSha256: specSha,
  processes: spec.design.schedule.map(replicateId => {
    const item = records.get(replicateId);
    return { replicateId, cell: item.cell, replicate: item.replicate, processId: item.processId,
      manifestHash: item.manifest.manifestHash, outputs: item.manifest.outputs };
  }),
};
const index = { ...indexBody, indexHash: sha256Canonical(indexBody) };
const indexPath = resolve(evidenceRoot, 'analysis-index.json');
await writeFile(indexPath, serialize(index));
const analysisPath = resolve(evidenceRoot, 'quality-analysis.json');
await run(blender, ['--factory-startup', '--background', '--disable-autoexec', '--python-exit-code', '1',
  '--python', analyzer, '--', '--index', indexPath, '--spec', specPath, '--output', analysisPath]);
const analysis = JSON.parse(await readFile(analysisPath, 'utf8'));

const contractHash = sha256Canonical({ design: spec.design, referenceProxy: spec.referenceProxy, edgeRule: spec.edgeRule,
  primaryEndpoint: spec.primaryEndpoint, decisionPrecedence: spec.decisionPrecedence, decisionRule: spec.decisionRule });
const bindingBody = {
  documentType: 'BFS_B31_ANALYSIS_BINDING', version: '0.1.0', b31SpecSha256: specSha,
  indexSha256: await sha256File(indexPath), analysisSha256: await sha256File(analysisPath),
  ledgerHash: ledger.ledgerHash, manifestHashes: Object.fromEntries([...manifests].map(([id, value]) => [id, value.manifestHash])),
  analyzerSha256: tools.analyzerSha256, runnerSha256: tools.runnerSha256, contractHash,
};
const binding = { ...bindingBody, bindingHash: sha256Canonical(bindingBody) };
const bindingPath = resolve(evidenceRoot, 'analysis-binding.json');
await writeFile(bindingPath, serialize(binding));

async function validate(overrides = {}) {
  const first = records.get('NATURAL32_A');
  const expected = {
    specSha, b30ResultSha: spec.evidenceBasis.b30ResultsSha256, b30SpecSha: spec.evidenceBasis.b30SpecSha256,
    derivationResultSha: spec.evidenceBasis.derivationResultsSha256,
    derivationAnalysisSha: spec.evidenceBasis.derivationAnalysisSha256,
    derivationRendererSha: spec.evidenceBasis.derivationRendererSha256,
    derivationAnalyzerSha: spec.evidenceBasis.derivationAnalyzerSha256,
    derivationRunnerSha: spec.evidenceBasis.derivationRunnerSha256,
    reviewSha: frozen.reviewRenderSpecSha256, blenderSha: frozen.blenderSha256, ocioSha: frozen.ocioSha256,
    sceneSha: frozen.sceneBlendSha256, planHash: frozen.planHash, structureHash: frozen.structureHash,
    configuratorSha: frozen.configuratorSha256, rendererSha: tools.rendererSha256,
    analyzerSha: tools.analyzerSha256, runnerSha: tools.runnerSha256,
    threads: 8, centerSamples: 32, centerJitter: [0, 0], schedule: spec.design.schedule,
    firstPid: first.processId, frames: spec.design.holdoutFrames, width: 960,
    firstOutputSha: first.report.outputs[0].sha256, indexSha: await sha256File(indexPath), contractHash,
    humanPending: true, ...overrides,
  };
  if (await sha256File(specPath) !== expected.specSha) return 'B31_SPEC_SHA';
  if (await sha256File(b30ResultPath) !== expected.b30ResultSha || await sha256File(b30SpecPath) !== expected.b30SpecSha) return 'B30_IDENTITY';
  if (await sha256File(derivationResultPath) !== expected.derivationResultSha
      || await sha256File(derivationAnalysisPath) !== expected.derivationAnalysisSha) return 'DERIVATION_IDENTITY';
  if (await sha256File(derivationRenderer) !== expected.derivationRendererSha
      || await sha256File(derivationAnalyzer) !== expected.derivationAnalyzerSha
      || await sha256File(derivationRunner) !== expected.derivationRunnerSha) return 'DERIVATION_TOOLS';
  if (await sha256File(reviewPath) !== expected.reviewSha) return 'REVIEW_SPEC_SHA';
  if (await sha256File(blender) !== expected.blenderSha) return 'BLENDER_SHA';
  if (await sha256File(ocioPath) !== expected.ocioSha) return 'OCIO_SHA';
  if (await sha256File(scenePath) !== expected.sceneSha) return 'SCENE_SHA';
  if (receipt.executionIdentity.buildPlan.planHash !== expected.planHash
      || receipt.run.sceneManifest.structureHash !== expected.structureHash) return 'PLAN_STRUCTURE';
  if (await sha256File(configurator) !== expected.configuratorSha) return 'CONFIGURATOR_SHA';
  if (await sha256File(renderer) !== expected.rendererSha) return 'RENDERER_SHA';
  if (await sha256File(analyzer) !== expected.analyzerSha) return 'ANALYZER_SHA';
  if (await sha256File(runner) !== expected.runnerSha) return 'RUNNER_SHA';
  for (const item of records.values()) {
    if (item.threads.after.threads !== expected.threads || item.threads.after.threadsMode !== 'FIXED'
        || item.report.savedSourceBlend !== false || item.report.observedControls.ditherIntensity !== 0
        || item.report.observedControls.useFastGi !== true || item.report.observedControls.useTaaReprojection !== true
        || item.report.source.sceneBlendSha256 !== frozen.sceneBlendSha256) return 'SOURCE_CONTROLS';
  }
  const center = records.get('CENTER32_A').report.observedControls;
  if (center.samples !== expected.centerSamples || JSON.stringify(center.jitter) !== JSON.stringify(expected.centerJitter)
      || records.get('NATURAL32_A').report.observedControls.jitter !== null
      || records.get('REFERENCE1024_A').report.observedControls.samples !== 1024) return 'CELL_CONTROLS';
  if (JSON.stringify(ledger.processes.map(item => item.replicateId)) !== JSON.stringify(expected.schedule)) return 'SCHEDULE';
  if (ledger.processes.length !== 6 || new Set(ledger.processes.map(item => item.processId)).size !== 6
      || first.processId !== expected.firstPid) return 'PID_BINDING';
  for (const item of records.values()) {
    if (item.report.renderCalls !== 4 || item.report.outputFileCount !== 4
        || JSON.stringify(item.report.frames) !== JSON.stringify(expected.frames)) return 'FRAME_RENDER_ORDER';
  }
  if (analysis.layout.width !== expected.width || analysis.layout.height !== 540
      || JSON.stringify(analysis.layout.channels) !== JSON.stringify(['R', 'G', 'B', 'A'])
      || analysis.layout.pixelFormat !== 'float') return 'EXR_LAYOUT_FINITE';
  for (const item of records.values()) {
    const names = (await readdir(item.outputDir)).filter(name => name.endsWith('.exr'));
    if (names.length !== 4) return 'OUTPUT_BINDING';
  }
  if (await sha256File(resolve(first.outputDir, first.report.outputs[0].name)) !== expected.firstOutputSha) return 'OUTPUT_BINDING';
  const indexClone = structuredClone(index); delete indexClone.indexHash;
  const bindingClone = structuredClone(binding); delete bindingClone.bindingHash;
  if (sha256Canonical(indexClone) !== index.indexHash || sha256Canonical(bindingClone) !== binding.bindingHash
      || binding.indexSha256 !== expected.indexSha || binding.analysisSha256 !== await sha256File(analysisPath)
      || analysis.indexSha256 !== await sha256File(indexPath)
      || index.processes.some(item => item.manifestHash !== manifests.get(item.replicateId).manifestHash)) return 'ANALYSIS_BINDING';
  if (binding.contractHash !== expected.contractHash || spec.design.renderCalls !== 24
      || spec.referenceProxy.maximumReliabilityRatioPerFrame !== 0.05
      || spec.primaryEndpoint.costSupportThreshold !== 1.5
      || spec.edgeRule.quantile !== 0.95 || spec.decisionPrecedence[0] !== 'INVALID_EXPERIMENT') return 'FROZEN_CONTRACT';
  if (spec.executionContract.humanReviewMustRemainPending !== expected.humanPending) return 'HUMAN_REVIEW';
  return 'OK';
}

const baseline = await validate();
if (baseline !== 'OK') throw new Error(`Baseline validation failed: ${baseline}`);
const attacks = [];
const attack = async (id, expected, overrides) => {
  const observed = await validate(overrides);
  attacks.push({ id, expected, observed, pass: expected === observed });
};
await attack('N_B31_SPEC_IDENTITY', 'B31_SPEC_SHA', { specSha: '0'.repeat(64) });
await attack('N_B30_IDENTITY', 'B30_IDENTITY', { b30ResultSha: '0'.repeat(64) });
await attack('N_DERIVATION_IDENTITY', 'DERIVATION_IDENTITY', { derivationResultSha: '0'.repeat(64) });
await attack('N_DERIVATION_TOOLS', 'DERIVATION_TOOLS', { derivationRendererSha: '0'.repeat(64) });
await attack('N_REVIEW_SPEC', 'REVIEW_SPEC_SHA', { reviewSha: '0'.repeat(64) });
await attack('N_BLENDER', 'BLENDER_SHA', { blenderSha: '0'.repeat(64) });
await attack('N_OCIO', 'OCIO_SHA', { ocioSha: '0'.repeat(64) });
await attack('N_SCENE', 'SCENE_SHA', { sceneSha: '0'.repeat(64) });
await attack('N_PLAN_STRUCTURE', 'PLAN_STRUCTURE', { planHash: '0'.repeat(64) });
await attack('N_CONFIGURATOR', 'CONFIGURATOR_SHA', { configuratorSha: '0'.repeat(64) });
await attack('N_RENDERER', 'RENDERER_SHA', { rendererSha: '0'.repeat(64) });
await attack('N_ANALYZER', 'ANALYZER_SHA', { analyzerSha: '0'.repeat(64) });
await attack('N_RUNNER', 'RUNNER_SHA', { runnerSha: '0'.repeat(64) });
await attack('N_SOURCE_CONTROLS', 'SOURCE_CONTROLS', { threads: 7 });
await attack('N_CELL_CONTROLS', 'CELL_CONTROLS', { centerSamples: 31 });
const swapped = [...spec.design.schedule]; [swapped[0], swapped[1]] = [swapped[1], swapped[0]];
await attack('N_SCHEDULE', 'SCHEDULE', { schedule: swapped });
await attack('N_PID_BINDING', 'PID_BINDING', { firstPid: -1 });
await attack('N_FRAME_RENDER_ORDER', 'FRAME_RENDER_ORDER', { frames: [11, 44, 86, 120] });
await attack('N_EXR_LAYOUT_FINITE', 'EXR_LAYOUT_FINITE', { width: 961 });
await attack('N_OUTPUT_BINDING', 'OUTPUT_BINDING', { firstOutputSha: '0'.repeat(64) });
await attack('N_ANALYSIS_BINDING', 'ANALYSIS_BINDING', { indexSha: '0'.repeat(64) });
await attack('N_FROZEN_CONTRACT', 'FROZEN_CONTRACT', { contractHash: '0'.repeat(64) });
await attack('N_HUMAN_REVIEW', 'HUMAN_REVIEW', { humanPending: false });

const allAttacksPass = attacks.length === spec.requiredNegativeCases.length && attacks.every(item => item.pass);
const uniqueProcesses = new Set([...records.values()].map(item => item.processId)).size;
const renderCalls = [...records.values()].reduce((sum, item) => sum + item.report.renderCalls, 0);
const outputFiles = [...records.values()].reduce((sum, item) => sum + item.report.outputFileCount, 0);
const validExperiment = allAttacksPass && uniqueProcesses === 6 && renderCalls === 24 && outputFiles === 24;
const decision = validExperiment ? analysis.decision : 'INVALID_EXPERIMENT';
const result = {
  documentType: 'BFS_B31_SAMPLING_QUALITY_HOLDOUT_RESULT', version: '0.1.0', executedAtUtc: new Date().toISOString(),
  decision, independentDecision: analysis.decision, validExperiment, question: spec.question, design: spec.design,
  humanReview: { status: 'PENDING', claim: 'Scene-linear edge-reference error does not determine perceived aliasing or cinematic quality.' },
  identities: { ...frozen, b31SpecSha256: specSha, b30ResultsSha256: spec.evidenceBasis.b30ResultsSha256,
    derivationResultsSha256: spec.evidenceBasis.derivationResultsSha256,
    derivationAnalysisSha256: spec.evidenceBasis.derivationAnalysisSha256, ...tools },
  primary: { referenceProxyReliable: analysis.referenceProxyReliable, decision: analysis.decision,
    threshold: spec.primaryEndpoint.costSupportThreshold, frames: analysis.frames.map(item => ({ frame: item.frame,
      referenceReliabilityRatio: item.referenceAgreement.reliabilityRatio,
      centerToNaturalEdgeRmse: item.ratios.centerToNaturalEdgeRmse })) },
  summary: analysis.summary, frames: analysis.frames,
  aggregate: { uniqueProcesses, renderProcesses: records.size, renderCalls, outputFiles,
    totalRenderSeconds: [...records.values()].reduce((sum, item) => sum + item.report.totalRenderSeconds, 0),
    attacksPassed: attacks.filter(item => item.pass).length, attacksTotal: attacks.length },
  processLedger: ledger.processes, attacks,
  artifacts: { processLedger: repoUri(ledgerPath), analysisIndex: repoUri(indexPath), analysis: repoUri(analysisPath),
    binding: repoUri(bindingPath), manifests: Object.fromEntries([...records].map(([id, item]) => [id, repoUri(item.manifestPath)])) },
  nonClaims: spec.explicitNonClaims,
};
await writeFile(resolve(experimentRoot, 'results.json'), serialize(result));
process.stdout.write(`BFS_B31_HOLDOUT_RESULT ${decision} min_ratio=${analysis.summary.minimumEdgeCostRatio} reliable=${analysis.referenceProxyReliable} attacks=${result.aggregate.attacksPassed}/${result.aggregate.attacksTotal}\n`);
if (!validExperiment) process.exitCode = 1;
