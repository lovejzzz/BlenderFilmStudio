import { mkdir, readFile, readdir, rm, writeFile } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { relative, resolve, sep } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256Canonical, sha256File } from './lib/receipt-format.mjs';

const experimentRoot = resolve(repositoryRoot, 'experiments/pass-domain-localization-v0-1');
const evidenceRoot = resolve(experimentRoot, 'evidence');
const workRoot = resolve(experimentRoot, 'work');
const specPath = resolve(repositoryRoot, 'specs/pass-domain-localization-spec.v0.1.json');
const b28ResultPath = resolve(repositoryRoot, 'experiments/repeated-frame-mode-switch-v0-1/results.json');
const pilotReportPath = resolve(repositoryRoot, 'experiments/pass-domain-pilot-v0-1/evidence/pilot.json');
const pilotAnalysisPath = resolve(repositoryRoot, 'experiments/pass-domain-pilot-v0-1/pass-analysis.json');
const pilotRendererPath = resolve(repositoryRoot, 'blender/explore_b29_pass_domain.py');
const pilotAnalyzerPath = resolve(repositoryRoot, 'blender/analyze_b29_pass_pilot.py');
const reviewSpecPath = resolve(repositoryRoot, 'specs/review-render-spec.v0.1.json');
const configurator = resolve(repositoryRoot, 'blender/configure_eevee_threads.py');
const renderer = resolve(repositoryRoot, 'blender/render_b29_pass_domain.py');
const classifier = resolve(repositoryRoot, 'blender/classify_b29_pass_domain.py');
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
    child.on('close', code => code === 0 ? resolvePromise({ processId, output }) : reject(new Error(`${command} failed (${code}) pid=${processId}\n${output}`)));
  });
}

function chooseDecision(classification, valid) {
  if (!valid) return 'INVALID_EXPERIMENT';
  const counts = classification.summary.categoryCounts;
  if ((counts.PASS_SPACE_EXPANDED || 0) > 0) return 'PASS_SPACE_EXPANDED';
  if ((counts.CLOSEST_SAMPLE_PASS_VARIATION || 0) > 0) return 'CLOSEST_SAMPLE_PASS_VARIATION';
  if ((counts.DECOUPLED_PASS_PATTERN || 0) > 0) return 'DECOUPLED_PASS_PATTERN';
  if (classification.primary.supportingProcessCount >= 2) return 'COVERAGE_COUPLED_LOCALIZATION_SUPPORT';
  if (classification.primary.supportingProcessCount === 1) return 'SINGLE_PID_COUPLING_INCONCLUSIVE';
  return 'ALTERNATE_NOT_REPRODUCED';
}

await rm(evidenceRoot, { recursive: true, force: true });
await rm(workRoot, { recursive: true, force: true });
await mkdir(evidenceRoot, { recursive: true });
await mkdir(workRoot, { recursive: true });
const spec = JSON.parse(await readFile(specPath, 'utf8'));
const specSha = await sha256File(specPath);
if (specSha !== '38a3d32dc8ce4e85e3403685c3b727f68fa48a71f517e576dfaea2c643c555d9') throw new Error('B29 spec changed after pre-registration');
const review = JSON.parse(await readFile(reviewSpecPath, 'utf8'));
const receiptPath = resolve(repositoryRoot, review.source.receiptUri);
const receipt = JSON.parse(await readFile(receiptPath, 'utf8'));
const scenePath = resolve(repositoryRoot, receipt.run.sceneBlend.uri);
const ocioPath = resolve(repositoryRoot, receipt.executionIdentity.configuration.ocio.uri);
const frozen = spec.frozenIdentity;
const frozenInputs = [
  [b28ResultPath, spec.evidenceBasis.b28ResultsSha256, 'B28 result'], [pilotReportPath, spec.evidenceBasis.pilotReportSha256, 'pilot report'],
  [pilotAnalysisPath, spec.evidenceBasis.pilotAnalysisSha256, 'pilot analysis'], [pilotRendererPath, spec.evidenceBasis.pilotRendererSha256, 'pilot renderer'],
  [pilotAnalyzerPath, spec.evidenceBasis.pilotAnalyzerSha256, 'pilot analyzer'], [reviewSpecPath, frozen.reviewRenderSpecSha256, 'review spec'],
  [blender, frozen.blenderSha256, 'Blender'], [ocioPath, frozen.ocioSha256, 'OCIO'], [scenePath, frozen.sceneBlendSha256, 'scene'],
  [configurator, frozen.configuratorSha256, 'configurator'],
];
for (const [path, expected, label] of frozenInputs) if (await sha256File(path) !== expected) throw new Error(`${label} frozen SHA mismatch`);
if (JSON.parse(await readFile(b28ResultPath, 'utf8')).decision !== spec.evidenceBasis.b28Decision) throw new Error('B28 decision mismatch');
const tools = { configuratorSha256: await sha256File(configurator), rendererSha256: await sha256File(renderer), classifierSha256: await sha256File(classifier), runnerSha256: await sha256File(runner) };

const records = new Map();
for (const replicate of spec.design.processOrder) {
  const outputDir = resolve(workRoot, replicate);
  const reportPath = resolve(evidenceRoot, `${replicate}.render.json`);
  const interventionPath = resolve(evidenceRoot, `${replicate}.intervention.json`);
  const manifestPath = resolve(evidenceRoot, `${replicate}.manifest.json`);
  await mkdir(outputDir, { recursive: true });
  const launched = await run(blender, ['--background', scenePath, '--disable-autoexec', '--python-exit-code', '1', '--python', configurator, '--python', renderer, '--', '--b29-spec', specPath, '--review-spec', reviewSpecPath, '--receipt', receiptPath, '--output-dir', outputDir, '--report', reportPath, '--replicate', replicate], { ...process.env, OCIO: ocioPath, BFS_B22_THREADS_MODE: 'FIXED', BFS_B22_THREADS: '8', BFS_B22_CELL: 'T08', BFS_B22_INTERVENTION_REPORT: interventionPath });
  const report = JSON.parse(await readFile(reportPath, 'utf8'));
  if (report.processId !== launched.processId) throw new Error(`${replicate} PID binding mismatch`);
  const intervention = JSON.parse(await readFile(interventionPath, 'utf8'));
  const manifestBody = { documentType: 'BFS_B29_RENDER_MANIFEST', version: '0.1.0', b29SpecSha256: specSha, replicate, processId: launched.processId, toolIdentities: tools, renderReportSha256: await sha256File(reportPath), interventionReportSha256: await sha256File(interventionPath), renders: report.outputs.map(item => ({ callOrdinal: item.callOrdinal, frame: item.frame, png: { uri: repoUri(resolve(outputDir, item.png.name)), sha256: item.png.sha256, bytes: item.png.bytes }, exr: { uri: repoUri(resolve(outputDir, item.exr.name)), sha256: item.exr.sha256, bytes: item.exr.bytes } })) };
  const manifest = { ...manifestBody, manifestHash: sha256Canonical(manifestBody) };
  await writeFile(manifestPath, serialize(manifest));
  records.set(replicate, { replicate, processId: launched.processId, outputDir, reportPath, interventionPath, manifestPath, report, intervention, manifest });
  process.stdout.write(`BFS_B29_PROCESS_OK ${replicate} pid=${launched.processId} calls=${report.renderOperatorCallCount} saves=${report.saveCount}\n`);
}

const ledgerBody = { documentType: 'BFS_B29_PROCESS_LEDGER', version: '0.1.0', b29SpecSha256: specSha, processes: spec.design.processOrder.map((replicate, orderIndex) => { const item = records.get(replicate); return { orderIndex, replicate, processId: item.processId, renderCalls: item.report.renderOperatorCallCount, saves: item.report.saveCount, callOrder: item.report.callOrder, renderReportSha256: null, interventionReportSha256: null, manifestHash: item.manifest.manifestHash }; }) };
for (const item of ledgerBody.processes) { item.renderReportSha256 = await sha256File(records.get(item.replicate).reportPath); item.interventionReportSha256 = await sha256File(records.get(item.replicate).interventionPath); }
const ledger = { ...ledgerBody, ledgerHash: sha256Canonical(ledgerBody) };
const ledgerPath = resolve(evidenceRoot, 'process-ledger.json');
await writeFile(ledgerPath, serialize(ledger));
const indexBody = { documentType: 'BFS_B29_CLASSIFICATION_INDEX', version: '0.1.0', b29SpecSha256: specSha, processes: spec.design.processOrder.map(replicate => { const item = records.get(replicate); return { replicate, processId: item.processId, manifestHash: item.manifest.manifestHash, renders: item.manifest.renders.map(render => ({ callOrdinal: render.callOrdinal, pngUri: render.png.uri, pngContainerSha256: render.png.sha256, exrUri: render.exr.uri, exrContainerSha256: render.exr.sha256 })) }; }) };
const index = { ...indexBody, indexHash: sha256Canonical(indexBody) };
const indexPath = resolve(evidenceRoot, 'classification-index.json');
await writeFile(indexPath, serialize(index));
const classificationPath = resolve(evidenceRoot, 'pass-classification.json');
await run(blender, ['--factory-startup', '--background', '--disable-autoexec', '--python-exit-code', '1', '--python', classifier, '--', '--index', indexPath, '--spec', specPath, '--output', classificationPath]);
const classification = JSON.parse(await readFile(classificationPath, 'utf8'));
const manifestHashes = Object.fromEntries([...records].map(([id, item]) => [id, item.manifest.manifestHash]));
const contractHash = sha256Canonical({ design: spec.design, knownHashes: spec.knownHashes, primaryEndpoint: spec.primaryEndpoint, decisionRule: spec.decisionRule });
const bindingBody = { documentType: 'BFS_B29_CLASSIFICATION_BINDING', version: '0.1.0', b29SpecSha256: specSha, ledgerHash: ledger.ledgerHash, indexSha256: await sha256File(indexPath), classificationSha256: await sha256File(classificationPath), manifestHashes, classifierSha256: tools.classifierSha256, runnerSha256: tools.runnerSha256, contractHash };
const binding = { ...bindingBody, bindingHash: sha256Canonical(bindingBody) };
const bindingPath = resolve(evidenceRoot, 'classification-binding.json');
await writeFile(bindingPath, serialize(binding));

async function validate(overrides = {}) {
  const base = records.get('P01');
  const expected = { specSha, b28Sha: spec.evidenceBasis.b28ResultsSha256, pilotReportSha: spec.evidenceBasis.pilotReportSha256, pilotAnalysisSha: spec.evidenceBasis.pilotAnalysisSha256, pilotRendererSha: spec.evidenceBasis.pilotRendererSha256, pilotAnalyzerSha: spec.evidenceBasis.pilotAnalyzerSha256, reviewSha: frozen.reviewRenderSpecSha256, blenderSha: frozen.blenderSha256, ocioSha: frozen.ocioSha256, sceneSha: frozen.sceneBlendSha256, planHash: frozen.planHash, structureHash: frozen.structureHash, configuratorSha: frozen.configuratorSha256, rendererSha: tools.rendererSha256, classifierSha: tools.classifierSha256, runnerSha: tools.runnerSha256, threads: 8, passCount: 8, processOrder: spec.design.processOrder, firstPid: base.processId, callOrder: Array.from({ length: 12 }, (_, index_) => index_ + 1), saves: 24, width: 960, firstPngSha: base.report.outputs[0].png.sha256, indexSha: await sha256File(indexPath), contractHash, humanPending: true, ...overrides };
  if (await sha256File(specPath) !== expected.specSha) return 'B29_SPEC_SHA';
  if (await sha256File(b28ResultPath) !== expected.b28Sha) return 'B28_RESULT_SHA';
  if (await sha256File(pilotReportPath) !== expected.pilotReportSha) return 'PILOT_REPORT_SHA';
  if (await sha256File(pilotAnalysisPath) !== expected.pilotAnalysisSha) return 'PILOT_ANALYSIS_SHA';
  if (await sha256File(pilotRendererPath) !== expected.pilotRendererSha || await sha256File(pilotAnalyzerPath) !== expected.pilotAnalyzerSha) return 'PILOT_TOOL_SHA';
  if (await sha256File(reviewSpecPath) !== expected.reviewSha) return 'REVIEW_SPEC_SHA';
  if (await sha256File(blender) !== expected.blenderSha) return 'BLENDER_SHA';
  if (await sha256File(ocioPath) !== expected.ocioSha) return 'OCIO_SHA';
  if (await sha256File(scenePath) !== expected.sceneSha) return 'SCENE_SHA';
  if (receipt.executionIdentity.buildPlan.planHash !== expected.planHash || receipt.run.sceneManifest.structureHash !== expected.structureHash) return 'PLAN_STRUCTURE';
  if (await sha256File(configurator) !== expected.configuratorSha) return 'CONFIGURATOR_SHA';
  if (await sha256File(renderer) !== expected.rendererSha) return 'RENDERER_SHA';
  if (await sha256File(classifier) !== expected.classifierSha) return 'CLASSIFIER_SHA';
  if (await sha256File(runner) !== expected.runnerSha) return 'RUNNER_SHA';
  if (base.intervention.after.threads !== expected.threads || base.report.controls.threads !== 8 || base.report.controls.ditherIntensity !== 0 || base.report.controls.useFastGi !== true || base.report.controls.useTaaReprojection !== true || base.report.savedSourceBlend !== false || base.report.cameraAndTimelineInvariant !== true) return 'SOURCE_CONTROLS';
  if (Object.keys(base.report.passState).length !== expected.passCount || base.report.passState.Position !== true || base.report.passState.CryptoObject !== true || base.report.passState.cryptomatteDepth !== 6) return 'PASS_SETTINGS';
  if (JSON.stringify(ledger.processes.map(item => item.replicate)) !== JSON.stringify(expected.processOrder)) return 'PROCESS_ORDER';
  if (ledger.processes.length !== 12 || new Set(ledger.processes.map(item => item.processId)).size !== 12 || base.processId !== expected.firstPid) return 'PID_BINDING';
  if (base.report.frameSetCountBeforeRenders !== 1 || base.report.targetFrame !== 38 || base.report.renderOperatorCallCount !== 12 || JSON.stringify(base.report.callOrder) !== JSON.stringify(expected.callOrder)) return 'FRAME_CALL_ORDER';
  if (base.report.saveCount !== expected.saves || base.report.sameRenderResultForEveryPngExrPair !== true || base.report.outputs.some(item => item.renderOperatorCalls !== 1 || item.sameRenderResultSaveCount !== 2)) return 'ONE_RENDER_TWO_SAVE';
  const firstCall = classification.processes[0].calls[0];
  if (firstCall.pngLayout.width !== expected.width || firstCall.pngLayout.height !== 540 || firstCall.pngLayout.pixelFormat !== 'uint8') return 'OUTPUT_LAYOUT';
  const names = await readdir(base.outputDir);
  if (names.filter(name => name.endsWith('.png')).length !== 12 || names.filter(name => name.endsWith('.exr')).length !== 12 || await sha256File(resolve(base.outputDir, base.report.outputs[0].png.name)) !== expected.firstPngSha) return 'OUTPUT_BINDING';
  const indexCopy = structuredClone(index); delete indexCopy.indexHash;
  const bindingCopy = structuredClone(binding); delete bindingCopy.bindingHash;
  if (sha256Canonical(indexCopy) !== index.indexHash || sha256Canonical(bindingCopy) !== binding.bindingHash || binding.indexSha256 !== expected.indexSha || classification.indexSha256 !== await sha256File(indexPath) || binding.classificationSha256 !== await sha256File(classificationPath) || classification.processes.some(item => item.manifestHash !== records.get(item.replicate).manifest.manifestHash)) return 'CLASSIFICATION_BINDING';
  if (binding.contractHash !== expected.contractHash || spec.design.renderCalls !== 144 || spec.design.saves !== 288 || spec.primaryEndpoint.supportThresholdProcesses !== 2) return 'FROZEN_CONTRACT';
  if (spec.executionContract.humanReviewMustRemainPending !== expected.humanPending) return 'HUMAN_REVIEW';
  return 'OK';
}

const baselineReason = await validate();
if (baselineReason !== 'OK') throw new Error(`Baseline validation failed: ${baselineReason}`);
const attacks = [];
const attack = async (id, expected, overrides) => { const observed = await validate(overrides); attacks.push({ id, expected, observed, pass: expected === observed }); };
await attack('N_B29_SPEC_IDENTITY', 'B29_SPEC_SHA', { specSha: '0'.repeat(64) });
await attack('N_B28_RESULT_IDENTITY', 'B28_RESULT_SHA', { b28Sha: '0'.repeat(64) });
await attack('N_PILOT_REPORT_IDENTITY', 'PILOT_REPORT_SHA', { pilotReportSha: '0'.repeat(64) });
await attack('N_PILOT_ANALYSIS_IDENTITY', 'PILOT_ANALYSIS_SHA', { pilotAnalysisSha: '0'.repeat(64) });
await attack('N_PILOT_TOOL_IDENTITY', 'PILOT_TOOL_SHA', { pilotRendererSha: '0'.repeat(64) });
await attack('N_REVIEW_SPEC_IDENTITY', 'REVIEW_SPEC_SHA', { reviewSha: '0'.repeat(64) });
await attack('N_BLENDER_IDENTITY', 'BLENDER_SHA', { blenderSha: '0'.repeat(64) });
await attack('N_OCIO_IDENTITY', 'OCIO_SHA', { ocioSha: '0'.repeat(64) });
await attack('N_SCENE_IDENTITY', 'SCENE_SHA', { sceneSha: '0'.repeat(64) });
await attack('N_PLAN_STRUCTURE', 'PLAN_STRUCTURE', { planHash: '0'.repeat(64) });
await attack('N_CONFIGURATOR_IDENTITY', 'CONFIGURATOR_SHA', { configuratorSha: '0'.repeat(64) });
await attack('N_RENDERER_IDENTITY', 'RENDERER_SHA', { rendererSha: '0'.repeat(64) });
await attack('N_CLASSIFIER_IDENTITY', 'CLASSIFIER_SHA', { classifierSha: '0'.repeat(64) });
await attack('N_RUNNER_IDENTITY', 'RUNNER_SHA', { runnerSha: '0'.repeat(64) });
await attack('N_SOURCE_CONTROLS', 'SOURCE_CONTROLS', { threads: 7 });
await attack('N_PASS_SETTINGS', 'PASS_SETTINGS', { passCount: 7 });
const swapped = [...spec.design.processOrder]; [swapped[0], swapped[1]] = [swapped[1], swapped[0]];
await attack('N_PROCESS_ORDER', 'PROCESS_ORDER', { processOrder: swapped });
await attack('N_PID_BINDING', 'PID_BINDING', { firstPid: -1 });
await attack('N_FRAME_CALL_ORDER', 'FRAME_CALL_ORDER', { callOrder: [2, ...Array.from({ length: 11 }, (_, i) => i + 2)] });
await attack('N_ONE_RENDER_TWO_SAVE', 'ONE_RENDER_TWO_SAVE', { saves: 23 });
await attack('N_OUTPUT_LAYOUT', 'OUTPUT_LAYOUT', { width: 961 });
await attack('N_OUTPUT_BINDING', 'OUTPUT_BINDING', { firstPngSha: '0'.repeat(64) });
await attack('N_CLASSIFICATION_BINDING', 'CLASSIFICATION_BINDING', { indexSha: '0'.repeat(64) });
await attack('N_FROZEN_CONTRACT', 'FROZEN_CONTRACT', { contractHash: '0'.repeat(64) });
await attack('N_HUMAN_REVIEW', 'HUMAN_REVIEW', { humanPending: false });
const allAttacksPass = attacks.length === spec.requiredNegativeCases.length && attacks.every(item => item.pass);
const renderCalls = [...records.values()].reduce((sum, item) => sum + item.report.renderOperatorCallCount, 0);
const saves = [...records.values()].reduce((sum, item) => sum + item.report.saveCount, 0);
const uniqueRenderProcesses = new Set([...records.values()].map(item => item.processId)).size;
const validExperiment = allAttacksPass && renderCalls === 144 && saves === 288 && uniqueRenderProcesses === 12;
const decision = chooseDecision(classification, validExperiment);
const result = { documentType: 'BFS_B29_PASS_DOMAIN_LOCALIZATION_RESULT', version: '0.1.0', executedAtUtc: new Date().toISOString(), decision, independentDecision: chooseDecision(classification, true), validExperiment, humanReview: { status: 'PENDING', claim: 'Pass identity cannot determine visibility or cinematic quality.' }, question: spec.question, design: spec.design, identities: { ...frozen, b29SpecSha256: specSha, ...spec.evidenceBasis, ...tools }, primary: classification.primary, summary: classification.summary, ordinalCategoryCounts: classification.ordinalCategoryCounts, numericReferenceToAlternate: classification.numericReferenceToAlternate, cryptoObject00Localization: classification.cryptoObject00Localization, secondary: classification.secondary, processes: classification.processes.map(item => ({ replicate: item.replicate, processId: item.processId, supportingProcess: item.supportingProcess, categoryCounts: item.categoryCounts, sequence: item.calls.map(call => call.category) })), aggregate: { uniqueRenderProcesses, renderProcesses: records.size, renderCalls, saves, pngFiles: 144, multilayerExrFiles: 144, attacksPassed: attacks.filter(item => item.pass).length, attacksTotal: attacks.length }, processLedger: ledger.processes, attacks, artifacts: { processLedger: repoUri(ledgerPath), classificationIndex: repoUri(indexPath), classification: repoUri(classificationPath), binding: repoUri(bindingPath), manifests: Object.fromEntries([...records].map(([id, item]) => [id, repoUri(item.manifestPath)])) }, nonClaims: spec.explicitNonClaims };
await writeFile(resolve(experimentRoot, 'results.json'), serialize(result));
process.stdout.write(`BFS_B29_RESULT ${decision} supporting=${classification.primary.supportingProcessCount}/12 categories=${JSON.stringify(classification.summary.categoryCounts)} attacks=${result.aggregate.attacksPassed}/${result.aggregate.attacksTotal}\n`);
if (!validExperiment) process.exitCode = 1;
