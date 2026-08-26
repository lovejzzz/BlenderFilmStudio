import { mkdir, readFile, readdir, rm, writeFile } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { relative, resolve, sep } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256Canonical, sha256File } from './lib/receipt-format.mjs';

const experimentRoot = resolve(repositoryRoot, 'experiments/repeated-frame-mode-switch-v0-1');
const evidenceRoot = resolve(experimentRoot, 'evidence');
const workRoot = resolve(experimentRoot, 'work');
const specPath = resolve(repositoryRoot, 'specs/repeated-frame-mode-switch-spec.v0.1.json');
const b27ResultPath = resolve(repositoryRoot, 'experiments/frame-history-isolation-v0-1/results.json');
const b27VariantPath = resolve(repositoryRoot, 'experiments/frame-history-isolation-v0-1/variant-analysis.json');
const reviewSpecPath = resolve(repositoryRoot, 'specs/review-render-spec.v0.1.json');
const configurator = resolve(repositoryRoot, 'blender/configure_eevee_threads.py');
const renderer = resolve(repositoryRoot, 'blender/render_b28_repeated_frame.py');
const classifier = resolve(repositoryRoot, 'blender/classify_b28_repeated_modes.py');
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

function decisionFor(classification, valid) {
  if (!valid) return 'INVALID_EXPERIMENT';
  if (classification.summary.novelDecodedRgbHashes.length > 0) return 'MODE_SPACE_EXPANDED';
  const switches = classification.primary.switchingProcessCount;
  if (switches >= 2) return 'WITHIN_PID_MODE_SWITCH_SUPPORT';
  if (switches === 1) return 'SINGLE_PID_SWITCH_INCONCLUSIVE';
  const occurrences = classification.summary.modeOccurrences;
  const processCounts = classification.summary.modeProcessCounts;
  const both = (occurrences.REFERENCE || 0) > 0 && (occurrences.ALTERNATE || 0) > 0;
  if (both && (processCounts.REFERENCE || 0) >= 2 && (processCounts.ALTERNATE || 0) >= 2) return 'PROCESS_LOCK_SUPPORT';
  if (both) return 'BETWEEN_PID_SPLIT_INCONCLUSIVE';
  return 'MODE_NOT_REPRODUCED';
}

await rm(evidenceRoot, { recursive: true, force: true });
await rm(workRoot, { recursive: true, force: true });
await mkdir(evidenceRoot, { recursive: true });
await mkdir(workRoot, { recursive: true });

const spec = JSON.parse(await readFile(specPath, 'utf8'));
const specSha = await sha256File(specPath);
if (specSha !== '60e3057d378201bc6c6f376422ec723277d733238547f9c206408a4f3f196ff5') throw new Error('B28 spec changed after pre-registration');
const reviewSpec = JSON.parse(await readFile(reviewSpecPath, 'utf8'));
const receiptPath = resolve(repositoryRoot, reviewSpec.source.receiptUri);
const receipt = JSON.parse(await readFile(receiptPath, 'utf8'));
const scenePath = resolve(repositoryRoot, receipt.run.sceneBlend.uri);
const ocioPath = resolve(repositoryRoot, receipt.executionIdentity.configuration.ocio.uri);
const referencePath = resolve(repositoryRoot, spec.knownModes.REFERENCE.anchorUri);
const alternatePath = resolve(repositoryRoot, spec.knownModes.ALTERNATE.anchorUri);
const frozen = spec.frozenIdentity;

const fixedInputs = [
  [b27ResultPath, spec.evidenceBasis.b27ResultsSha256, 'B27 result'],
  [b27VariantPath, spec.evidenceBasis.b27VariantAnalysisSha256, 'B27 variant analysis'],
  [reviewSpecPath, frozen.reviewRenderSpecSha256, 'review spec'],
  [blender, frozen.blenderSha256, 'Blender'], [ocioPath, frozen.ocioSha256, 'OCIO'],
  [scenePath, frozen.sceneBlendSha256, 'scene'], [configurator, frozen.configuratorSha256, 'configurator'],
  [referencePath, spec.knownModes.REFERENCE.anchorContainerSha256, 'REFERENCE anchor'],
  [alternatePath, spec.knownModes.ALTERNATE.anchorContainerSha256, 'ALTERNATE anchor'],
];
for (const [path, expected, label] of fixedInputs) if (await sha256File(path) !== expected) throw new Error(`${label} frozen SHA mismatch`);
const b27Result = JSON.parse(await readFile(b27ResultPath, 'utf8'));
if (b27Result.decision !== spec.evidenceBasis.b27Decision) throw new Error('B27 decision mismatch');

const tools = {
  configuratorSha256: await sha256File(configurator), rendererSha256: await sha256File(renderer),
  classifierSha256: await sha256File(classifier), runnerSha256: await sha256File(runner),
};
const records = new Map();
const manifests = new Map();
for (const replicate of spec.design.processOrder) {
  const outputDir = resolve(workRoot, replicate);
  const reportPath = resolve(evidenceRoot, `${replicate}.render.json`);
  const interventionPath = resolve(evidenceRoot, `${replicate}.intervention.json`);
  const manifestPath = resolve(evidenceRoot, `${replicate}.manifest.json`);
  await mkdir(outputDir, { recursive: true });
  const launched = await run(blender, [
    '--background', scenePath, '--disable-autoexec', '--python-exit-code', '1',
    '--python', configurator, '--python', renderer, '--',
    '--b28-spec', specPath, '--review-spec', reviewSpecPath, '--receipt', receiptPath,
    '--output-dir', outputDir, '--report', reportPath, '--replicate', replicate,
  ], {
    ...process.env, OCIO: ocioPath, BFS_B22_THREADS_MODE: 'FIXED', BFS_B22_THREADS: '8', BFS_B22_CELL: 'T08',
    BFS_B22_INTERVENTION_REPORT: interventionPath,
  });
  const report = JSON.parse(await readFile(reportPath, 'utf8'));
  if (report.processId !== launched.processId) throw new Error(`${replicate} process binding mismatch`);
  const intervention = JSON.parse(await readFile(interventionPath, 'utf8'));
  const manifestBody = {
    documentType: 'BFS_B28_RENDER_MANIFEST', version: '0.1.0', b28SpecSha256: specSha,
    replicate, processId: launched.processId, toolIdentities: tools,
    renderReportSha256: await sha256File(reportPath), interventionReportSha256: await sha256File(interventionPath),
    renders: report.outputs.map(item => ({
      callOrdinal: item.callOrdinal, frame: item.frame, name: item.name,
      uri: repoUri(resolve(outputDir, item.name)), sha256: item.sha256, bytes: item.bytes,
    })),
  };
  const manifest = { ...manifestBody, manifestHash: sha256Canonical(manifestBody) };
  await writeFile(manifestPath, serialize(manifest));
  records.set(replicate, { replicate, processId: launched.processId, outputDir, reportPath, interventionPath, manifestPath, report, intervention, manifest });
  manifests.set(replicate, manifest);
  process.stdout.write(`BFS_B28_PROCESS_OK ${replicate} pid=${launched.processId} calls=${report.renderOperatorCallCount} seconds=${report.totalRenderSeconds}\n`);
}

const ledgerBody = {
  documentType: 'BFS_B28_PROCESS_LEDGER', version: '0.1.0', b28SpecSha256: specSha,
  processes: spec.design.processOrder.map((replicate, orderIndex) => {
    const item = records.get(replicate);
    return { orderIndex, replicate, processId: item.processId, renderCalls: item.report.renderOperatorCallCount,
      callOrder: item.report.callOrder, renderReportSha256: null, interventionReportSha256: null, manifestHash: item.manifest.manifestHash };
  }),
};
for (const item of ledgerBody.processes) {
  item.renderReportSha256 = await sha256File(records.get(item.replicate).reportPath);
  item.interventionReportSha256 = await sha256File(records.get(item.replicate).interventionPath);
}
const ledger = { ...ledgerBody, ledgerHash: sha256Canonical(ledgerBody) };
const ledgerPath = resolve(evidenceRoot, 'process-ledger.json');
await writeFile(ledgerPath, serialize(ledger));

const indexBody = {
  documentType: 'BFS_B28_CLASSIFICATION_INDEX', version: '0.1.0', b28SpecSha256: specSha,
  processes: spec.design.processOrder.map(replicate => {
    const item = records.get(replicate);
    return { replicate, processId: item.processId, manifestHash: item.manifest.manifestHash,
      renders: item.manifest.renders.map(render => ({ callOrdinal: render.callOrdinal, fileUri: render.uri, containerSha256: render.sha256 })) };
  }),
};
const index = { ...indexBody, indexHash: sha256Canonical(indexBody) };
const indexPath = resolve(evidenceRoot, 'classification-index.json');
await writeFile(indexPath, serialize(index));
const classificationPath = resolve(evidenceRoot, 'mode-classification.json');
await run(blender, ['--factory-startup', '--background', '--disable-autoexec', '--python-exit-code', '1', '--python', classifier, '--', '--index', indexPath, '--spec', specPath, '--output', classificationPath]);
const classification = JSON.parse(await readFile(classificationPath, 'utf8'));

const manifestHashes = Object.fromEntries([...manifests].map(([id, value]) => [id, value.manifestHash]));
const contractHash = sha256Canonical({ knownModes: spec.knownModes, design: spec.design, primaryEndpoint: spec.primaryEndpoint, decisionRule: spec.decisionRule });
const bindingBody = {
  documentType: 'BFS_B28_CLASSIFICATION_BINDING', version: '0.1.0', b28SpecSha256: specSha,
  indexSha256: await sha256File(indexPath), classificationSha256: await sha256File(classificationPath),
  ledgerHash: ledger.ledgerHash, manifestHashes, classifierSha256: tools.classifierSha256, runnerSha256: tools.runnerSha256, contractHash,
};
const binding = { ...bindingBody, bindingHash: sha256Canonical(bindingBody) };
const bindingPath = resolve(evidenceRoot, 'classification-binding.json');
await writeFile(bindingPath, serialize(binding));

async function validate(overrides = {}) {
  const expected = {
    specSha, b27ResultSha: spec.evidenceBasis.b27ResultsSha256, b27VariantSha: spec.evidenceBasis.b27VariantAnalysisSha256,
    reviewSha: frozen.reviewRenderSpecSha256, blenderSha: frozen.blenderSha256, ocioSha: frozen.ocioSha256,
    sceneSha: frozen.sceneBlendSha256, planHash: frozen.planHash, structureHash: frozen.structureHash,
    configuratorSha: frozen.configuratorSha256, rendererSha: tools.rendererSha256, classifierSha: tools.classifierSha256, runnerSha: tools.runnerSha256,
    referenceSha: spec.knownModes.REFERENCE.anchorContainerSha256, alternateSha: spec.knownModes.ALTERNATE.anchorContainerSha256,
    threads: 8, processOrder: spec.design.processOrder, firstPid: records.get('P01').processId,
    callOrder: Array.from({ length: 12 }, (_, index_) => index_ + 1), width: 960,
    firstOutputSha: records.get('P01').report.outputs[0].sha256, indexSha: await sha256File(indexPath), contractHash,
    humanPending: true, ...overrides,
  };
  if (await sha256File(specPath) !== expected.specSha) return 'B28_SPEC_SHA';
  if (await sha256File(b27ResultPath) !== expected.b27ResultSha) return 'B27_RESULT_SHA';
  if (await sha256File(b27VariantPath) !== expected.b27VariantSha) return 'B27_VARIANT_SHA';
  if (await sha256File(reviewSpecPath) !== expected.reviewSha) return 'REVIEW_SPEC_SHA';
  if (await sha256File(blender) !== expected.blenderSha) return 'BLENDER_SHA';
  if (await sha256File(ocioPath) !== expected.ocioSha) return 'OCIO_SHA';
  if (await sha256File(scenePath) !== expected.sceneSha) return 'SCENE_SHA';
  if (receipt.executionIdentity.buildPlan.planHash !== expected.planHash || receipt.run.sceneManifest.structureHash !== expected.structureHash) return 'PLAN_STRUCTURE';
  if (await sha256File(configurator) !== expected.configuratorSha) return 'CONFIGURATOR_SHA';
  if (await sha256File(renderer) !== expected.rendererSha) return 'RENDERER_SHA';
  if (await sha256File(classifier) !== expected.classifierSha) return 'CLASSIFIER_SHA';
  if (await sha256File(runner) !== expected.runnerSha) return 'RUNNER_SHA';
  if (await sha256File(referencePath) !== expected.referenceSha) return 'REFERENCE_ANCHOR';
  if (await sha256File(alternatePath) !== expected.alternateSha) return 'ALTERNATE_ANCHOR';
  const base = records.get('P01');
  if (base.intervention.after.threads !== expected.threads || base.intervention.after.threadsMode !== 'FIXED'
      || base.report.observedControls.threads !== 8 || base.report.observedControls.ditherIntensity !== 0
      || base.report.observedControls.useFastGi !== true || base.report.observedControls.useTaaReprojection !== true
      || base.report.savedSourceBlend !== false || base.report.cameraAndTimelineInvariant !== true) return 'SOURCE_CONTROLS';
  if (JSON.stringify(ledger.processes.map(item => item.replicate)) !== JSON.stringify(expected.processOrder)) return 'PROCESS_ORDER';
  if (ledger.processes.length !== 12 || new Set(ledger.processes.map(item => item.processId)).size !== 12 || base.processId !== expected.firstPid) return 'PID_BINDING';
  if (base.report.frameSetCountBeforeRenders !== 1 || base.report.targetFrame !== 38 || base.report.frameAfterSet !== 38
      || base.report.renderOperatorCallCount !== 12 || base.report.outputFileCount !== 12 || base.report.frameObservedEveryCall !== true
      || JSON.stringify(base.report.callOrder) !== JSON.stringify(expected.callOrder)) return 'FRAME_CALL_ORDER';
  if (classification.layout.width !== expected.width || classification.layout.height !== 540
      || JSON.stringify(classification.layout.channels) !== JSON.stringify(['R', 'G', 'B', 'A']) || classification.layout.pixelFormat !== 'uint8') return 'PNG_LAYOUT';
  const names = (await readdir(base.outputDir)).filter(name => name.endsWith('.png')).sort();
  if (names.length !== 12 || await sha256File(resolve(base.outputDir, base.report.outputs[0].name)) !== expected.firstOutputSha) return 'OUTPUT_BINDING';
  const indexClone = structuredClone(index); delete indexClone.indexHash;
  const bindingClone = structuredClone(binding); delete bindingClone.bindingHash;
  if (sha256Canonical(indexClone) !== index.indexHash || sha256Canonical(bindingClone) !== binding.bindingHash
      || binding.indexSha256 !== expected.indexSha || binding.classificationSha256 !== await sha256File(classificationPath)
      || classification.indexSha256 !== await sha256File(indexPath)
      || classification.processes.some(item => item.manifestHash !== manifests.get(item.replicate).manifestHash)) return 'CLASSIFICATION_BINDING';
  if (binding.contractHash !== expected.contractHash || spec.design.renderCalls !== 144
      || spec.primaryEndpoint.supportThresholdProcesses !== 2 || Object.keys(spec.knownModes).length !== 2) return 'FROZEN_CONTRACT';
  if (spec.executionContract.humanReviewMustRemainPending !== expected.humanPending) return 'HUMAN_REVIEW';
  return 'OK';
}

if (await validate() !== 'OK') throw new Error(`Baseline validation failed: ${await validate()}`);
const attacks = [];
const attack = async (id, expected, overrides) => {
  const observed = await validate(overrides);
  attacks.push({ id, expected, observed, pass: expected === observed });
};
await attack('N_B28_SPEC_IDENTITY', 'B28_SPEC_SHA', { specSha: '0'.repeat(64) });
await attack('N_B27_RESULT_IDENTITY', 'B27_RESULT_SHA', { b27ResultSha: '0'.repeat(64) });
await attack('N_B27_VARIANT_IDENTITY', 'B27_VARIANT_SHA', { b27VariantSha: '0'.repeat(64) });
await attack('N_REVIEW_SPEC_IDENTITY', 'REVIEW_SPEC_SHA', { reviewSha: '0'.repeat(64) });
await attack('N_BLENDER_IDENTITY', 'BLENDER_SHA', { blenderSha: '0'.repeat(64) });
await attack('N_OCIO_IDENTITY', 'OCIO_SHA', { ocioSha: '0'.repeat(64) });
await attack('N_SCENE_IDENTITY', 'SCENE_SHA', { sceneSha: '0'.repeat(64) });
await attack('N_PLAN_STRUCTURE_IDENTITY', 'PLAN_STRUCTURE', { planHash: '0'.repeat(64) });
await attack('N_CONFIGURATOR_IDENTITY', 'CONFIGURATOR_SHA', { configuratorSha: '0'.repeat(64) });
await attack('N_RENDERER_IDENTITY', 'RENDERER_SHA', { rendererSha: '0'.repeat(64) });
await attack('N_CLASSIFIER_IDENTITY', 'CLASSIFIER_SHA', { classifierSha: '0'.repeat(64) });
await attack('N_RUNNER_IDENTITY', 'RUNNER_SHA', { runnerSha: '0'.repeat(64) });
await attack('N_REFERENCE_ANCHOR', 'REFERENCE_ANCHOR', { referenceSha: '0'.repeat(64) });
await attack('N_ALTERNATE_ANCHOR', 'ALTERNATE_ANCHOR', { alternateSha: '0'.repeat(64) });
await attack('N_SOURCE_CONTROLS', 'SOURCE_CONTROLS', { threads: 7 });
const swapped = [...spec.design.processOrder]; [swapped[0], swapped[1]] = [swapped[1], swapped[0]];
await attack('N_PROCESS_ORDER', 'PROCESS_ORDER', { processOrder: swapped });
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
const validExperiment = allAttacksPass && uniqueRenderProcesses === 12 && renderCalls === 144 && outputFiles === 144;
const decision = decisionFor(classification, validExperiment);
const independentDecision = decisionFor(classification, true);
const result = {
  documentType: 'BFS_B28_REPEATED_FRAME_MODE_SWITCH_RESULT', version: '0.1.0', executedAtUtc: new Date().toISOString(),
  decision, independentDecision, validExperiment,
  humanReview: { status: 'PENDING', claim: 'Automation cannot determine visibility, temporal perception or cinematic quality.' },
  question: spec.question, design: spec.design,
  identities: { ...frozen, b28SpecSha256: specSha, b27ResultsSha256: spec.evidenceBasis.b27ResultsSha256,
    b27VariantAnalysisSha256: spec.evidenceBasis.b27VariantAnalysisSha256, ...tools,
    referenceAnchorSha256: spec.knownModes.REFERENCE.anchorContainerSha256, alternateAnchorSha256: spec.knownModes.ALTERNATE.anchorContainerSha256 },
  primary: classification.primary, summary: classification.summary, ordinalModeCounts: classification.ordinalModeCounts,
  processes: classification.processes.map(item => ({ replicate: item.replicate, processId: item.processId, sequence: item.sequence,
    modeCounts: item.modeCounts, withinPidKnownModeSwitch: item.withinPidKnownModeSwitch,
    adjacentTransitionCount: item.adjacentTransitionCount, transitions: item.transitions })),
  aggregate: { uniqueRenderProcesses, renderProcesses: records.size, renderCalls, outputFiles,
    totalRenderSeconds: [...records.values()].reduce((sum, item) => sum + item.report.totalRenderSeconds, 0),
    attacksPassed: attacks.filter(item => item.pass).length, attacksTotal: attacks.length },
  processLedger: ledger.processes, attacks,
  artifacts: { processLedger: repoUri(ledgerPath), classificationIndex: repoUri(indexPath), classification: repoUri(classificationPath),
    binding: repoUri(bindingPath), manifests: Object.fromEntries([...records].map(([id, item]) => [id, repoUri(item.manifestPath)])),
    referenceAnchor: spec.knownModes.REFERENCE.anchorUri, alternateAnchor: spec.knownModes.ALTERNATE.anchorUri },
  nonClaims: spec.explicitNonClaims,
};
await writeFile(resolve(experimentRoot, 'results.json'), serialize(result));
process.stdout.write(`BFS_B28_RESULT ${decision} switches=${classification.primary.switchingProcessCount}/12 transitions=${classification.summary.observedAdjacentTransitions}/132 novel=${classification.summary.novelDecodedRgbHashes.length} attacks=${result.aggregate.attacksPassed}/${result.aggregate.attacksTotal}\n`);
if (!validExperiment) process.exitCode = 1;
