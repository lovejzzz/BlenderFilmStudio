import { mkdir, readFile, readdir, rm, writeFile } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { relative, resolve, sep } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256Canonical, sha256File } from './lib/receipt-format.mjs';

const experimentRoot = resolve(repositoryRoot, 'experiments/fixed-jitter-intervention-v0-1');
const evidenceRoot = resolve(experimentRoot, 'evidence');
const workRoot = resolve(experimentRoot, 'work');
const specPath = resolve(repositoryRoot, 'specs/fixed-jitter-intervention-spec.v0.1.json');
const b29ResultPath = resolve(repositoryRoot, 'experiments/pass-domain-localization-v0-1/results.json');
const b29SpecPath = resolve(repositoryRoot, 'specs/pass-domain-localization-spec.v0.1.json');
const derivationResultPath = resolve(repositoryRoot, 'experiments/fixed-jitter-derivation-v0-1/results.json');
const derivationAnalysisPath = resolve(repositoryRoot, 'experiments/fixed-jitter-derivation-v0-1/analysis.json');
const derivationRenderer = resolve(repositoryRoot, 'blender/explore_b30_fixed_jitter.py');
const derivationAnalyzer = resolve(repositoryRoot, 'blender/analyze_b30_fixed_jitter_derivation.py');
const derivationRunner = resolve(repositoryRoot, 'scripts/run-b30-fixed-jitter-derivation.mjs');
const reviewSpecPath = resolve(repositoryRoot, 'specs/review-render-spec.v0.1.json');
const configurator = resolve(repositoryRoot, 'blender/configure_eevee_threads.py');
const renderer = resolve(repositoryRoot, 'blender/render_b30_jitter_intervention.py');
const classifier = resolve(repositoryRoot, 'blender/classify_b30_jitter_intervention.py');
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

function cellFor(replicate) {
  return replicate.startsWith('N') ? 'NATURAL' : 'CENTER';
}

function decisionFor(classification, valid) {
  if (!valid) return 'INVALID_EXPERIMENT';
  if ((classification.summary.novelDecodedRgbHashes.NATURAL || []).length > 0) return 'NATURAL_MODE_SPACE_EXPANDED';
  if ((classification.summary.novelDecodedRgbHashes.CENTER || []).length > 0) return 'CENTER_VARIATION';
  const switching = classification.primary.naturalSwitchingProcessCount;
  if (switching >= 2) return 'FIXED_JITTER_STRICT_STABILITY_SUPPORT';
  if (switching === 1) return 'NATURAL_SINGLE_PID_SWITCH_INCONCLUSIVE';
  return 'NATURAL_WITHIN_PID_SWITCH_NOT_REPRODUCED';
}

await rm(evidenceRoot, { recursive: true, force: true });
await rm(workRoot, { recursive: true, force: true });
await mkdir(evidenceRoot, { recursive: true });
await mkdir(workRoot, { recursive: true });

const spec = JSON.parse(await readFile(specPath, 'utf8'));
const specSha = await sha256File(specPath);
if (specSha !== 'de5da4a38ce22fe80f17d1bc220ceb70680ebd56a5b03104a650132c4a12ae00') {
  throw new Error('B30 spec changed after pre-registration');
}
const reviewSpec = JSON.parse(await readFile(reviewSpecPath, 'utf8'));
const receiptPath = resolve(repositoryRoot, reviewSpec.source.receiptUri);
const receipt = JSON.parse(await readFile(receiptPath, 'utf8'));
const scenePath = resolve(repositoryRoot, receipt.run.sceneBlend.uri);
const ocioPath = resolve(repositoryRoot, receipt.executionIdentity.configuration.ocio.uri);
const frozen = spec.frozenIdentity;
const fixedInputs = [
  [b29ResultPath, spec.evidenceBasis.b29ResultsSha256, 'B29 result'],
  [b29SpecPath, spec.evidenceBasis.b29SpecSha256, 'B29 spec'],
  [derivationResultPath, spec.evidenceBasis.derivationResultsSha256, 'derivation result'],
  [derivationAnalysisPath, spec.evidenceBasis.derivationAnalysisSha256, 'derivation analysis'],
  [derivationRenderer, spec.evidenceBasis.derivationRendererSha256, 'derivation renderer'],
  [derivationAnalyzer, spec.evidenceBasis.derivationAnalyzerSha256, 'derivation analyzer'],
  [derivationRunner, spec.evidenceBasis.derivationRunnerSha256, 'derivation runner'],
  [reviewSpecPath, frozen.reviewRenderSpecSha256, 'review spec'],
  [blender, frozen.blenderSha256, 'Blender'], [ocioPath, frozen.ocioSha256, 'OCIO'],
  [scenePath, frozen.sceneBlendSha256, 'scene'], [configurator, frozen.configuratorSha256, 'configurator'],
];
for (const [path, expected, label] of fixedInputs) {
  if (await sha256File(path) !== expected) throw new Error(`${label} frozen SHA mismatch`);
}
const b29Result = JSON.parse(await readFile(b29ResultPath, 'utf8'));
const derivationResult = JSON.parse(await readFile(derivationResultPath, 'utf8'));
if (b29Result.decision !== spec.evidenceBasis.b29Decision) throw new Error('B29 decision mismatch');
if (derivationResult.status !== spec.evidenceBasis.derivationStatus) throw new Error('derivation status mismatch');

const tools = {
  configuratorSha256: await sha256File(configurator), rendererSha256: await sha256File(renderer),
  classifierSha256: await sha256File(classifier), runnerSha256: await sha256File(runner),
};
const records = new Map();
const manifests = new Map();
for (const replicate of spec.design.schedule) {
  const cell = cellFor(replicate);
  const outputDir = resolve(workRoot, replicate);
  const reportPath = resolve(evidenceRoot, `${replicate}.render.json`);
  const interventionPath = resolve(evidenceRoot, `${replicate}.threads.json`);
  const manifestPath = resolve(evidenceRoot, `${replicate}.manifest.json`);
  await mkdir(outputDir, { recursive: true });
  const launched = await run(blender, [
    '--background', scenePath, '--disable-autoexec', '--python-exit-code', '1',
    '--python', configurator, '--python', renderer, '--',
    '--b30-spec', specPath, '--review-spec', reviewSpecPath, '--receipt', receiptPath,
    '--output-dir', outputDir, '--report', reportPath, '--replicate', replicate, '--cell', cell,
  ], {
    ...process.env, OCIO: ocioPath, BFS_B22_THREADS_MODE: 'FIXED', BFS_B22_THREADS: '8',
    BFS_B22_CELL: 'T08', BFS_B22_INTERVENTION_REPORT: interventionPath,
  });
  const report = JSON.parse(await readFile(reportPath, 'utf8'));
  if (report.processId !== launched.processId) throw new Error(`${replicate} process binding mismatch`);
  const intervention = JSON.parse(await readFile(interventionPath, 'utf8'));
  const manifestBody = {
    documentType: 'BFS_B30_RENDER_MANIFEST', version: '0.1.0', b30SpecSha256: specSha,
    replicate, cell, processId: launched.processId, toolIdentities: tools,
    renderReportSha256: await sha256File(reportPath), threadInterventionReportSha256: await sha256File(interventionPath),
    renders: report.outputs.map(item => ({
      callOrdinal: item.callOrdinal, frame: item.frame, name: item.name,
      uri: repoUri(resolve(outputDir, item.name)), sha256: item.sha256, bytes: item.bytes,
    })),
  };
  const manifest = { ...manifestBody, manifestHash: sha256Canonical(manifestBody) };
  await writeFile(manifestPath, serialize(manifest));
  records.set(replicate, { replicate, cell, processId: launched.processId, outputDir, reportPath, interventionPath, manifestPath, report, intervention, manifest });
  manifests.set(replicate, manifest);
  process.stdout.write(`BFS_B30_PROCESS_OK ${replicate} cell=${cell} pid=${launched.processId} calls=${report.renderOperatorCallCount}\n`);
}

const ledgerBody = {
  documentType: 'BFS_B30_PROCESS_LEDGER', version: '0.1.0', b30SpecSha256: specSha,
  processes: spec.design.schedule.map((replicate, orderIndex) => {
    const item = records.get(replicate);
    return { orderIndex, replicate, cell: item.cell, processId: item.processId,
      renderCalls: item.report.renderOperatorCallCount, callOrder: item.report.callOrder,
      renderReportSha256: null, threadInterventionReportSha256: null, manifestHash: item.manifest.manifestHash };
  }),
};
for (const item of ledgerBody.processes) {
  item.renderReportSha256 = await sha256File(records.get(item.replicate).reportPath);
  item.threadInterventionReportSha256 = await sha256File(records.get(item.replicate).interventionPath);
}
const ledger = { ...ledgerBody, ledgerHash: sha256Canonical(ledgerBody) };
const ledgerPath = resolve(evidenceRoot, 'process-ledger.json');
await writeFile(ledgerPath, serialize(ledger));

const indexBody = {
  documentType: 'BFS_B30_CLASSIFICATION_INDEX', version: '0.1.0', b30SpecSha256: specSha,
  processes: spec.design.schedule.map(replicate => {
    const item = records.get(replicate);
    return { replicate, cell: item.cell, processId: item.processId, manifestHash: item.manifest.manifestHash,
      renders: item.manifest.renders.map(render => ({ callOrdinal: render.callOrdinal, fileUri: render.uri, containerSha256: render.sha256 })) };
  }),
};
const index = { ...indexBody, indexHash: sha256Canonical(indexBody) };
const indexPath = resolve(evidenceRoot, 'classification-index.json');
await writeFile(indexPath, serialize(index));
const classificationPath = resolve(evidenceRoot, 'mode-classification.json');
await run(blender, ['--factory-startup', '--background', '--disable-autoexec', '--python-exit-code', '1',
  '--python', classifier, '--', '--index', indexPath, '--spec', specPath, '--output', classificationPath]);
const classification = JSON.parse(await readFile(classificationPath, 'utf8'));

const manifestHashes = Object.fromEntries([...manifests].map(([id, value]) => [id, value.manifestHash]));
const contractHash = sha256Canonical({
  design: spec.design, frozenDecodedRgbHashes: spec.frozenDecodedRgbHashes,
  primaryEndpoint: spec.primaryEndpoint, decisionPrecedence: spec.decisionPrecedence, decisionRule: spec.decisionRule,
});
const bindingBody = {
  documentType: 'BFS_B30_CLASSIFICATION_BINDING', version: '0.1.0', b30SpecSha256: specSha,
  indexSha256: await sha256File(indexPath), classificationSha256: await sha256File(classificationPath),
  ledgerHash: ledger.ledgerHash, manifestHashes, classifierSha256: tools.classifierSha256,
  runnerSha256: tools.runnerSha256, contractHash,
};
const binding = { ...bindingBody, bindingHash: sha256Canonical(bindingBody) };
const bindingPath = resolve(evidenceRoot, 'classification-binding.json');
await writeFile(bindingPath, serialize(binding));

async function validate(overrides = {}) {
  const firstNatural = records.get('N01');
  const firstCenter = records.get('C01');
  const expected = {
    specSha, b29ResultSha: spec.evidenceBasis.b29ResultsSha256, b29SpecSha: spec.evidenceBasis.b29SpecSha256,
    derivationResultSha: spec.evidenceBasis.derivationResultsSha256,
    derivationAnalysisSha: spec.evidenceBasis.derivationAnalysisSha256,
    derivationRendererSha: spec.evidenceBasis.derivationRendererSha256,
    derivationAnalyzerSha: spec.evidenceBasis.derivationAnalyzerSha256,
    derivationRunnerSha: spec.evidenceBasis.derivationRunnerSha256,
    reviewSha: frozen.reviewRenderSpecSha256, blenderSha: frozen.blenderSha256, ocioSha: frozen.ocioSha256,
    sceneSha: frozen.sceneBlendSha256, planHash: frozen.planHash, structureHash: frozen.structureHash,
    configuratorSha: frozen.configuratorSha256, rendererSha: tools.rendererSha256,
    classifierSha: tools.classifierSha256, runnerSha: tools.runnerSha256,
    threads: 8, schedule: spec.design.schedule, firstPid: firstNatural.processId,
    expectedNaturalProperty: null, expectedCenterProperty: [0, 0],
    callOrder: Array.from({ length: 12 }, (_, index_) => index_ + 1), width: 960,
    firstOutputSha: firstNatural.report.outputs[0].sha256,
    indexSha: await sha256File(indexPath), contractHash, humanPending: true, ...overrides,
  };
  if (await sha256File(specPath) !== expected.specSha) return 'B30_SPEC_SHA';
  if (await sha256File(b29ResultPath) !== expected.b29ResultSha) return 'B29_RESULT_SHA';
  if (await sha256File(b29SpecPath) !== expected.b29SpecSha) return 'B29_SPEC_SHA';
  if (await sha256File(derivationResultPath) !== expected.derivationResultSha) return 'DERIVATION_RESULT_SHA';
  if (await sha256File(derivationAnalysisPath) !== expected.derivationAnalysisSha) return 'DERIVATION_ANALYSIS_SHA';
  if (await sha256File(derivationRenderer) !== expected.derivationRendererSha
      || await sha256File(derivationAnalyzer) !== expected.derivationAnalyzerSha
      || await sha256File(derivationRunner) !== expected.derivationRunnerSha) return 'DERIVATION_TOOLS';
  if (await sha256File(reviewSpecPath) !== expected.reviewSha) return 'REVIEW_SPEC_SHA';
  if (await sha256File(blender) !== expected.blenderSha) return 'BLENDER_SHA';
  if (await sha256File(ocioPath) !== expected.ocioSha) return 'OCIO_SHA';
  if (await sha256File(scenePath) !== expected.sceneSha) return 'SCENE_SHA';
  if (receipt.executionIdentity.buildPlan.planHash !== expected.planHash
      || receipt.run.sceneManifest.structureHash !== expected.structureHash) return 'PLAN_STRUCTURE';
  if (await sha256File(configurator) !== expected.configuratorSha) return 'CONFIGURATOR_SHA';
  if (await sha256File(renderer) !== expected.rendererSha) return 'RENDERER_SHA';
  if (await sha256File(classifier) !== expected.classifierSha) return 'CLASSIFIER_SHA';
  if (await sha256File(runner) !== expected.runnerSha) return 'RUNNER_SHA';
  for (const item of records.values()) {
    if (item.intervention.after.threads !== expected.threads || item.intervention.after.threadsMode !== 'FIXED'
        || item.report.observedControls.threads !== 8 || item.report.observedControls.ditherIntensity !== 0
        || item.report.observedControls.useFastGi !== true || item.report.observedControls.useTaaReprojection !== true
        || item.report.savedSourceBlend !== false || item.report.cameraAndTimelineInvariant !== true
        || item.report.source.sceneBlendSha256 !== frozen.sceneBlendSha256) return 'SOURCE_CONTROLS';
  }
  if (JSON.stringify(firstNatural.report.intervention.after) !== JSON.stringify(expected.expectedNaturalProperty)
      || JSON.stringify(firstCenter.report.intervention.after) !== JSON.stringify(expected.expectedCenterProperty)
      || firstNatural.report.cell !== 'NATURAL' || firstCenter.report.cell !== 'CENTER') return 'CELL_INTERVENTION';
  if (JSON.stringify(ledger.processes.map(item => item.replicate)) !== JSON.stringify(expected.schedule)) return 'SCHEDULE';
  if (ledger.processes.length !== 24 || new Set(ledger.processes.map(item => item.processId)).size !== 24
      || firstNatural.processId !== expected.firstPid) return 'PID_BINDING';
  for (const item of records.values()) {
    if (item.report.frameSetCountBeforeRenders !== 1 || item.report.targetFrame !== 38 || item.report.frameAfterSet !== 38
        || item.report.renderOperatorCallCount !== 12 || item.report.outputFileCount !== 12
        || item.report.frameObservedEveryCall !== true
        || JSON.stringify(item.report.callOrder) !== JSON.stringify(expected.callOrder)) return 'FRAME_CALL_ORDER';
  }
  if (classification.layout.width !== expected.width || classification.layout.height !== 540
      || JSON.stringify(classification.layout.channels) !== JSON.stringify(['R', 'G', 'B', 'A'])
      || classification.layout.pixelFormat !== 'uint8') return 'PNG_LAYOUT';
  for (const item of records.values()) {
    const names = (await readdir(item.outputDir)).filter(name => name.endsWith('.png')).sort();
    if (names.length !== 12) return 'OUTPUT_BINDING';
  }
  if (await sha256File(resolve(firstNatural.outputDir, firstNatural.report.outputs[0].name)) !== expected.firstOutputSha) return 'OUTPUT_BINDING';
  const indexClone = structuredClone(index); delete indexClone.indexHash;
  const bindingClone = structuredClone(binding); delete bindingClone.bindingHash;
  if (sha256Canonical(indexClone) !== index.indexHash || sha256Canonical(bindingClone) !== binding.bindingHash
      || binding.indexSha256 !== expected.indexSha || binding.classificationSha256 !== await sha256File(classificationPath)
      || classification.indexSha256 !== await sha256File(indexPath)
      || classification.processes.some(item => item.manifestHash !== manifests.get(item.replicate).manifestHash)) return 'CLASSIFICATION_BINDING';
  if (binding.contractHash !== expected.contractHash || spec.design.processes !== 24 || spec.design.renderCalls !== 288
      || spec.primaryEndpoint.naturalSupportThresholdProcesses !== 2
      || Object.keys(spec.frozenDecodedRgbHashes).length !== 3
      || spec.decisionPrecedence[0] !== 'INVALID_EXPERIMENT') return 'FROZEN_CONTRACT';
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
await attack('N_B30_SPEC_IDENTITY', 'B30_SPEC_SHA', { specSha: '0'.repeat(64) });
await attack('N_B29_RESULT_IDENTITY', 'B29_RESULT_SHA', { b29ResultSha: '0'.repeat(64) });
await attack('N_B29_SPEC_IDENTITY', 'B29_SPEC_SHA', { b29SpecSha: '0'.repeat(64) });
await attack('N_DERIVATION_RESULT_IDENTITY', 'DERIVATION_RESULT_SHA', { derivationResultSha: '0'.repeat(64) });
await attack('N_DERIVATION_ANALYSIS_IDENTITY', 'DERIVATION_ANALYSIS_SHA', { derivationAnalysisSha: '0'.repeat(64) });
await attack('N_DERIVATION_TOOL_IDENTITY', 'DERIVATION_TOOLS', { derivationRendererSha: '0'.repeat(64) });
await attack('N_REVIEW_SPEC_IDENTITY', 'REVIEW_SPEC_SHA', { reviewSha: '0'.repeat(64) });
await attack('N_BLENDER_IDENTITY', 'BLENDER_SHA', { blenderSha: '0'.repeat(64) });
await attack('N_OCIO_IDENTITY', 'OCIO_SHA', { ocioSha: '0'.repeat(64) });
await attack('N_SCENE_IDENTITY', 'SCENE_SHA', { sceneSha: '0'.repeat(64) });
await attack('N_PLAN_STRUCTURE_IDENTITY', 'PLAN_STRUCTURE', { planHash: '0'.repeat(64) });
await attack('N_CONFIGURATOR_IDENTITY', 'CONFIGURATOR_SHA', { configuratorSha: '0'.repeat(64) });
await attack('N_RENDERER_IDENTITY', 'RENDERER_SHA', { rendererSha: '0'.repeat(64) });
await attack('N_CLASSIFIER_IDENTITY', 'CLASSIFIER_SHA', { classifierSha: '0'.repeat(64) });
await attack('N_RUNNER_IDENTITY', 'RUNNER_SHA', { runnerSha: '0'.repeat(64) });
await attack('N_SOURCE_CONTROLS', 'SOURCE_CONTROLS', { threads: 7 });
await attack('N_CELL_INTERVENTION', 'CELL_INTERVENTION', { expectedCenterProperty: [1, 0] });
const swapped = [...spec.design.schedule]; [swapped[0], swapped[1]] = [swapped[1], swapped[0]];
await attack('N_SCHEDULE', 'SCHEDULE', { schedule: swapped });
await attack('N_PID_BINDING', 'PID_BINDING', { firstPid: -1 });
await attack('N_FRAME_CALL_ORDER', 'FRAME_CALL_ORDER', { callOrder: [2, ...Array.from({ length: 11 }, (_, index_) => index_ + 2)] });
await attack('N_PNG_LAYOUT', 'PNG_LAYOUT', { width: 961 });
await attack('N_OUTPUT_BINDING', 'OUTPUT_BINDING', { firstOutputSha: '0'.repeat(64) });
await attack('N_CLASSIFICATION_BINDING', 'CLASSIFICATION_BINDING', { indexSha: '0'.repeat(64) });
await attack('N_FROZEN_CONTRACT', 'FROZEN_CONTRACT', { contractHash: '0'.repeat(64) });
await attack('N_HUMAN_REVIEW', 'HUMAN_REVIEW', { humanPending: false });

const allAttacksPass = attacks.length === spec.requiredNegativeCases.length && attacks.every(item => item.pass);
const uniqueRenderProcesses = new Set([...records.values()].map(item => item.processId)).size;
const renderCalls = [...records.values()].reduce((sum, item) => sum + item.report.renderOperatorCallCount, 0);
const outputFiles = [...records.values()].reduce((sum, item) => sum + item.report.outputFileCount, 0);
const validExperiment = allAttacksPass && uniqueRenderProcesses === 24 && renderCalls === 288 && outputFiles === 288;
const decision = decisionFor(classification, validExperiment);
const independentDecision = decisionFor(classification, true);
const result = {
  documentType: 'BFS_B30_FIXED_JITTER_INTERVENTION_RESULT', version: '0.1.0', executedAtUtc: new Date().toISOString(),
  decision, independentDecision, validExperiment, question: spec.question, design: spec.design,
  humanReview: { status: 'PENDING', claim: 'Automation cannot determine anti-aliasing quality, visibility, temporal perception or cinematic quality.' },
  identities: { ...frozen, b30SpecSha256: specSha, b29ResultsSha256: spec.evidenceBasis.b29ResultsSha256,
    b29SpecSha256: spec.evidenceBasis.b29SpecSha256, derivationResultsSha256: spec.evidenceBasis.derivationResultsSha256,
    derivationAnalysisSha256: spec.evidenceBasis.derivationAnalysisSha256, ...tools },
  primary: classification.primary, summary: classification.summary, ordinalModeCounts: classification.ordinalModeCounts,
  processes: classification.processes.map(item => ({ replicate: item.replicate, cell: item.cell, processId: item.processId,
    sequence: item.sequence, modeCounts: item.modeCounts, withinPidNaturalSwitch: item.withinPidNaturalSwitch,
    centerExact: item.centerExact, adjacentTransitionCount: item.adjacentTransitionCount, transitions: item.transitions })),
  aggregate: { uniqueRenderProcesses, renderProcesses: records.size, renderCalls, outputFiles,
    totalRenderSeconds: [...records.values()].reduce((sum, item) => sum + item.report.totalRenderSeconds, 0),
    attacksPassed: attacks.filter(item => item.pass).length, attacksTotal: attacks.length },
  derivationInterventionCost: {
    status: 'FROZEN_DERIVATION_DESCRIPTIVE_ONLY',
    centerVersusNaturalReferenceChangedPixels: 131779,
    centerVersusNaturalReferenceMaximumAbsoluteCodeDelta: 46,
    centerVersusNaturalReferenceRmsNormalized: 0.0036968891556978904,
  },
  processLedger: ledger.processes, attacks,
  artifacts: { processLedger: repoUri(ledgerPath), classificationIndex: repoUri(indexPath),
    classification: repoUri(classificationPath), binding: repoUri(bindingPath),
    manifests: Object.fromEntries([...records].map(([id, item]) => [id, repoUri(item.manifestPath)])) },
  nonClaims: spec.explicitNonClaims,
};
await writeFile(resolve(experimentRoot, 'results.json'), serialize(result));
process.stdout.write(`BFS_B30_RESULT ${decision} natural_switch=${classification.primary.naturalSwitchingProcessCount}/12 center_exact=${classification.primary.centerExactProcessCount}/12 attacks=${result.aggregate.attacksPassed}/${result.aggregate.attacksTotal}\n`);
if (!validExperiment) process.exitCode = 1;
