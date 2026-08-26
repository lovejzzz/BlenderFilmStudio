import { mkdir, readFile, readdir, rm, writeFile } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { relative, resolve, sep } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256Canonical, sha256File } from './lib/receipt-format.mjs';

const experimentRoot = resolve(repositoryRoot, 'experiments/quadrature-cost-holdout-v0-1');
const evidenceRoot = resolve(experimentRoot, 'evidence');
const workRoot = resolve(experimentRoot, 'work');
const specPath = resolve(repositoryRoot, 'specs/quadrature-cost-holdout-spec.v0.1.json');
const reviewPath = resolve(repositoryRoot, 'specs/review-render-spec.v0.1.json');
const configurator = resolve(repositoryRoot, 'blender/configure_eevee_threads.py');
const renderer = resolve(repositoryRoot, 'blender/render_b32_quadrature_cost_holdout.py');
const analyzer = resolve(repositoryRoot, 'blender/analyze_b32_quadrature_cost_holdout.py');
const runner = fileURLToPath(import.meta.url);
const blender = resolve(process.env.BLENDER_BIN || '/Applications/Blender.app/Contents/MacOS/Blender');
const q4ResultPath = resolve(repositoryRoot, 'experiments/quadrature-derivation-v0-1/results.json');
const q4AnalysisPath = resolve(repositoryRoot, 'experiments/quadrature-derivation-v0-1/analysis.json');
const q4ResearchPath = resolve(repositoryRoot, 'research/2026-08-26-b32-quadrature-derivation.md');
const q8ResultPath = resolve(repositoryRoot, 'experiments/stratified8-derivation-v0-1/results.json');
const q8AnalysisPath = resolve(repositoryRoot, 'experiments/stratified8-derivation-v0-1/analysis.json');
const q8ProtocolPath = resolve(repositoryRoot, 'research/2026-08-26-b32-stratified8-derivation-protocol.md');
const q8ResultNotePath = resolve(repositoryRoot, 'research/2026-08-26-b32-stratified8-derivation-result.md');
const serialize = value => `${JSON.stringify(value, null, 2)}\n`;
const repoUri = path => relative(repositoryRoot, path).split(sep).join('/');

function schedule() {
  const items = ['NATURAL32_A', 'NATURAL32_B', 'REFERENCE1024_A', 'REFERENCE1024_B'];
  for (const replicate of ['A', 'B']) for (let index = 1; index <= 4; index += 1) items.push(`Q4_${index}_${replicate}`);
  for (const replicate of ['A', 'B']) for (let index = 1; index <= 8; index += 1) items.push(`Q8_${index}_${replicate}`);
  return items;
}

function run(command, args, env = process.env) {
  return new Promise((resolvePromise, reject) => {
    const child = spawn(command, args, { cwd: repositoryRoot, env, stdio: ['ignore', 'pipe', 'pipe'] });
    const processId = child.pid;
    let output = '';
    child.stdout.on('data', chunk => { output += chunk; });
    child.stderr.on('data', chunk => { output += chunk; });
    child.on('error', reject);
    child.on('close', code => code === 0 ? resolvePromise({ processId, output, code })
      : reject(Object.assign(new Error(`${command} failed (${code}) pid=${processId}\n${output}`), { processId, output, code })));
  });
}

async function expectFailure(command, args, env, pattern) {
  try {
    await run(command, args, env);
    return { pass: false, observed: 'UNEXPECTED_SUCCESS' };
  } catch (error) {
    return { pass: error.output?.includes(pattern) === true, observed: error.output?.includes(pattern) ? pattern : `EXIT_${error.code}` };
  }
}

function cellControls(spec, cell) {
  if (cell === 'NATURAL32') return { samples: spec.design.natural32.samples, jitter: null };
  if (cell === 'REFERENCE1024') return { samples: spec.design.reference1024.samples, jitter: null };
  const [family, indexText] = cell.split('_');
  const definition = family === 'Q4' ? spec.design.quadrature4 : spec.design.stratified8;
  return { samples: definition.samplesPerComponent, jitter: definition.points[Number(indexText) - 1] };
}

await rm(evidenceRoot, { recursive: true, force: true });
await rm(workRoot, { recursive: true, force: true });
await mkdir(evidenceRoot, { recursive: true });
await mkdir(workRoot, { recursive: true });

const spec = JSON.parse(await readFile(specPath, 'utf8'));
const specSha = await sha256File(specPath);
if (specSha !== 'e2a66a170df8b83d79883e292fc82ddc961a9d2326831ec9237a0d641ac0b51d') {
  throw new Error('B32 holdout spec changed after preregistration');
}
const review = JSON.parse(await readFile(reviewPath, 'utf8'));
const receiptPath = resolve(repositoryRoot, review.source.receiptUri);
const receipt = JSON.parse(await readFile(receiptPath, 'utf8'));
const scenePath = resolve(repositoryRoot, receipt.run.sceneBlend.uri);
const ocioPath = resolve(repositoryRoot, receipt.executionIdentity.configuration.ocio.uri);
const fixedInputs = [
  [reviewPath, spec.source.reviewSpecSha256, 'review spec'],
  [blender, spec.runtime.blenderBinarySha256, 'Blender'],
  [ocioPath, spec.runtime.ocioSha256, 'OCIO'],
  [scenePath, spec.source.sceneBlendSha256, 'scene'],
  [q4ResultPath, spec.evidenceBasis.quadrature4ResultsSha256, 'Q4 result'],
  [q4AnalysisPath, spec.evidenceBasis.quadrature4AnalysisSha256, 'Q4 analysis'],
  [q4ResearchPath, spec.evidenceBasis.quadrature4ResearchSha256, 'Q4 research'],
  [q8ResultPath, spec.evidenceBasis.stratified8ResultsSha256, 'Q8 result'],
  [q8AnalysisPath, spec.evidenceBasis.stratified8AnalysisSha256, 'Q8 analysis'],
  [q8ProtocolPath, spec.evidenceBasis.stratified8ProtocolSha256, 'Q8 protocol'],
  [q8ResultNotePath, spec.evidenceBasis.stratified8ResultNoteSha256, 'Q8 result note'],
];
for (const [path, expected, label] of fixedInputs) {
  if (await sha256File(path) !== expected) throw new Error(`${label} frozen SHA mismatch`);
}
const q4Result = JSON.parse(await readFile(q4ResultPath, 'utf8'));
const q8Result = JSON.parse(await readFile(q8ResultPath, 'utf8'));
const q8Analysis = JSON.parse(await readFile(q8AnalysisPath, 'utf8'));
if (q4Result.status !== spec.evidenceBasis.quadrature4Status) throw new Error('Q4 status mismatch');
if (q8Result.status !== spec.evidenceBasis.stratified8Status) throw new Error('Q8 status mismatch');
if (q8Analysis.decision !== spec.evidenceBasis.stratified8Decision) throw new Error('Q8 decision mismatch');

const tools = {
  configuratorSha256: await sha256File(configurator),
  rendererSha256: await sha256File(renderer),
  analyzerSha256: await sha256File(analyzer),
  runnerSha256: await sha256File(runner),
};
const records = new Map();
const manifests = new Map();
const frozenSchedule = schedule();
for (const replicateId of frozenSchedule) {
  const separator = replicateId.lastIndexOf('_');
  const cell = replicateId.slice(0, separator);
  const replicate = replicateId.slice(separator + 1);
  const outputDir = resolve(workRoot, replicateId);
  const reportPath = resolve(evidenceRoot, `${replicateId}.render.json`);
  const threadPath = resolve(evidenceRoot, `${replicateId}.threads.json`);
  const manifestPath = resolve(evidenceRoot, `${replicateId}.manifest.json`);
  await mkdir(outputDir, { recursive: true });
  const launched = await run(blender, [
    '--background', scenePath, '--disable-autoexec', '--python-exit-code', '1',
    '--python', configurator, '--python', renderer, '--',
    '--holdout-spec', specPath, '--review-spec', reviewPath, '--receipt', receiptPath,
    '--output-dir', outputDir, '--report', reportPath, '--cell', cell, '--replicate', replicate,
  ], {
    ...process.env,
    OCIO: ocioPath,
    BFS_B22_THREADS_MODE: 'FIXED',
    BFS_B22_THREADS: '8',
    BFS_B22_CELL: 'T08',
    BFS_B22_INTERVENTION_REPORT: threadPath,
  });
  const report = JSON.parse(await readFile(reportPath, 'utf8'));
  if (report.processId !== launched.processId) throw new Error(`${replicateId} PID binding mismatch`);
  const threads = JSON.parse(await readFile(threadPath, 'utf8'));
  const manifestBody = {
    documentType: 'BFS_B32_QUADRATURE_COST_RENDER_MANIFEST',
    version: '0.1.0',
    holdoutSpecSha256: specSha,
    replicateId, cell, replicate, processId: launched.processId,
    totalRenderSeconds: report.totalRenderSeconds,
    toolIdentities: tools,
    renderReportSha256: await sha256File(reportPath),
    threadReportSha256: await sha256File(threadPath),
    outputs: report.outputs.map(item => ({
      frame: item.frame, name: item.name,
      fileUri: repoUri(resolve(outputDir, item.name)),
      containerSha256: item.sha256, bytes: item.bytes,
    })),
  };
  const manifest = { ...manifestBody, manifestHash: sha256Canonical(manifestBody) };
  await writeFile(manifestPath, serialize(manifest));
  records.set(replicateId, { replicateId, cell, replicate, processId: launched.processId, outputDir,
    reportPath, threadPath, manifestPath, report, threads, manifest });
  manifests.set(replicateId, manifest);
  process.stdout.write(`BFS_B32_HOLDOUT_PROCESS_OK ${replicateId} pid=${launched.processId} seconds=${report.totalRenderSeconds}\n`);
}

const ledgerBody = {
  documentType: 'BFS_B32_QUADRATURE_COST_PROCESS_LEDGER',
  version: '0.1.0',
  holdoutSpecSha256: specSha,
  processes: frozenSchedule.map((replicateId, orderIndex) => {
    const item = records.get(replicateId);
    return {
      orderIndex, replicateId, cell: item.cell, replicate: item.replicate,
      processId: item.processId, frames: item.report.frames,
      renderCalls: item.report.renderCalls,
      renderReportSha256: item.manifest.renderReportSha256,
      threadReportSha256: item.manifest.threadReportSha256,
      manifestHash: item.manifest.manifestHash,
    };
  }),
};
const ledger = { ...ledgerBody, ledgerHash: sha256Canonical(ledgerBody) };
const ledgerPath = resolve(evidenceRoot, 'process-ledger.json');
await writeFile(ledgerPath, serialize(ledger));
const indexBody = {
  documentType: 'BFS_B32_QUADRATURE_COST_ANALYSIS_INDEX',
  version: '0.1.0',
  holdoutSpecSha256: specSha,
  processes: frozenSchedule.map(replicateId => {
    const item = records.get(replicateId);
    return {
      replicateId, cell: item.cell, replicate: item.replicate,
      processId: item.processId, totalRenderSeconds: item.report.totalRenderSeconds,
      manifestHash: item.manifest.manifestHash, outputs: item.manifest.outputs,
    };
  }),
};
const index = { ...indexBody, indexHash: sha256Canonical(indexBody) };
const indexPath = resolve(evidenceRoot, 'analysis-index.json');
await writeFile(indexPath, serialize(index));
const analysisPath = resolve(evidenceRoot, 'quality-analysis.json');
await run(blender, [
  '--factory-startup', '--background', '--disable-autoexec', '--python-exit-code', '1',
  '--python', analyzer, '--', '--index', indexPath, '--spec', specPath, '--output', analysisPath,
]);
const analysis = JSON.parse(await readFile(analysisPath, 'utf8'));

const contractHash = sha256Canonical({
  source: spec.source,
  runtime: spec.runtime,
  design: spec.design,
  analysis: spec.analysis,
  gates: spec.gates,
  componentVerdicts: spec.componentVerdicts,
  overallDecision: spec.overallDecision,
});
const bindingBody = {
  documentType: 'BFS_B32_QUADRATURE_COST_ANALYSIS_BINDING',
  version: '0.1.0',
  holdoutSpecSha256: specSha,
  indexSha256: await sha256File(indexPath),
  analysisSha256: await sha256File(analysisPath),
  ledgerHash: ledger.ledgerHash,
  manifestHashes: Object.fromEntries([...manifests].map(([id, value]) => [id, value.manifestHash])),
  analyzerSha256: tools.analyzerSha256,
  runnerSha256: tools.runnerSha256,
  contractHash,
};
const binding = { ...bindingBody, bindingHash: sha256Canonical(bindingBody) };
const bindingPath = resolve(evidenceRoot, 'analysis-binding.json');
await writeFile(bindingPath, serialize(binding));

async function validate(overrides = {}) {
  const first = records.get('NATURAL32_A');
  const expected = {
    specSha,
    q4ResultSha: spec.evidenceBasis.quadrature4ResultsSha256,
    q8ResultSha: spec.evidenceBasis.stratified8ResultsSha256,
    reviewSha: spec.source.reviewSpecSha256,
    blenderSha: spec.runtime.blenderBinarySha256,
    ocioSha: spec.runtime.ocioSha256,
    sceneSha: spec.source.sceneBlendSha256,
    planHash: spec.source.planHash,
    structureHash: spec.source.structureHash,
    configuratorSha: tools.configuratorSha256,
    rendererSha: tools.rendererSha256,
    analyzerSha: tools.analyzerSha256,
    runnerSha: tools.runnerSha256,
    threads: spec.runtime.threads,
    schedule: frozenSchedule,
    uniqueProcesses: spec.design.totalProcesses,
    frames: spec.design.frames,
    renderCalls: spec.design.totalRenderCalls,
    firstOutputSha: first.report.outputs[0].sha256,
    width: spec.runtime.resolution[0],
    indexSha: await sha256File(indexPath),
    analysisSha: await sha256File(analysisPath),
    contractHash,
    q8Gate: spec.gates.q8ToNaturalEdgeMaximumEveryFrame,
    decision: analysis.decision,
    q8Mean: analysis.summary.q8ToNaturalEdgeMean,
    ...overrides,
  };
  if (await sha256File(specPath) !== expected.specSha) return 'SPEC_SHA';
  if (await sha256File(q4ResultPath) !== expected.q4ResultSha) return 'Q4_EVIDENCE';
  if (await sha256File(q8ResultPath) !== expected.q8ResultSha) return 'Q8_EVIDENCE';
  if (await sha256File(reviewPath) !== expected.reviewSha) return 'REVIEW_SHA';
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
    const controls = item.report.observedControls;
    const cell = cellControls(spec, item.cell);
    if (item.threads.after.threads !== expected.threads || item.threads.after.threadsMode !== 'FIXED'
        || controls.threads !== expected.threads || controls.threadsMode !== 'FIXED'
        || controls.dither !== 0 || controls.useFastGi !== true || controls.useTaaReprojection !== true
        || controls.motionBlur !== false || item.report.savedSourceBlend !== false) return 'SOURCE_CONTROLS';
    if (controls.samples !== cell.samples || JSON.stringify(controls.jitter) !== JSON.stringify(cell.jitter)) return 'CELL_CONTROLS';
  }
  if (JSON.stringify(ledger.processes.map(item => item.replicateId)) !== JSON.stringify(expected.schedule)) return 'SCHEDULE';
  if (ledger.processes.length !== expected.uniqueProcesses
      || new Set(ledger.processes.map(item => item.processId)).size !== expected.uniqueProcesses) return 'PID_BINDING';
  const actualRenderCalls = [...records.values()].reduce((sum, item) => sum + item.report.renderCalls, 0);
  if (actualRenderCalls !== expected.renderCalls) return 'RENDER_COUNT';
  for (const item of records.values()) {
    if (JSON.stringify(item.report.frames) !== JSON.stringify(expected.frames)
        || item.report.outputFileCount !== expected.frames.length) return 'FRAME_ORDER';
    const names = (await readdir(item.outputDir)).filter(name => name.endsWith('.exr'));
    if (names.length !== expected.frames.length) return 'OUTPUT_COUNT';
  }
  if (await sha256File(resolve(first.outputDir, first.report.outputs[0].name)) !== expected.firstOutputSha) return 'OUTPUT_HASH';
  if (analysis.layout.width !== expected.width || analysis.layout.height !== 540
      || JSON.stringify(analysis.layout.channels) !== JSON.stringify(['R', 'G', 'B', 'A'])
      || analysis.layout.pixelFormat !== 'float') return 'EXR_LAYOUT';
  const indexClone = structuredClone(index); delete indexClone.indexHash;
  const bindingClone = structuredClone(binding); delete bindingClone.bindingHash;
  if (sha256Canonical(indexClone) !== index.indexHash || sha256Canonical(bindingClone) !== binding.bindingHash
      || binding.indexSha256 !== expected.indexSha || binding.analysisSha256 !== expected.analysisSha
      || analysis.indexSha256 !== expected.indexSha) return 'ANALYSIS_BINDING';
  if (binding.contractHash !== expected.contractHash) return 'CONTRACT_HASH';
  if (spec.gates.q8ToNaturalEdgeMaximumEveryFrame !== expected.q8Gate) return 'FROZEN_GATE';
  if (analysis.decision !== expected.decision) return 'DECISION_TAMPER';
  if (analysis.summary.q8ToNaturalEdgeMean !== expected.q8Mean) return 'METRIC_TAMPER';
  return 'OK';
}

const baseline = await validate();
if (baseline !== 'OK') throw new Error(`Baseline validation failed: ${baseline}`);
const attacks = [];
const attack = async (id, expected, overrides) => {
  const observed = await validate(overrides);
  attacks.push({ id, expected, observed, pass: expected === observed });
};
await attack('N_SPEC_SHA', 'SPEC_SHA', { specSha: '0'.repeat(64) });
await attack('N_Q4_EVIDENCE', 'Q4_EVIDENCE', { q4ResultSha: '0'.repeat(64) });
await attack('N_Q8_EVIDENCE', 'Q8_EVIDENCE', { q8ResultSha: '0'.repeat(64) });
await attack('N_REVIEW_SHA', 'REVIEW_SHA', { reviewSha: '0'.repeat(64) });
await attack('N_BLENDER_SHA', 'BLENDER_SHA', { blenderSha: '0'.repeat(64) });
await attack('N_OCIO_SHA', 'OCIO_SHA', { ocioSha: '0'.repeat(64) });
await attack('N_SCENE_SHA', 'SCENE_SHA', { sceneSha: '0'.repeat(64) });
await attack('N_PLAN_STRUCTURE', 'PLAN_STRUCTURE', { planHash: '0'.repeat(64) });
await attack('N_CONFIGURATOR_SHA', 'CONFIGURATOR_SHA', { configuratorSha: '0'.repeat(64) });
await attack('N_RENDERER_SHA', 'RENDERER_SHA', { rendererSha: '0'.repeat(64) });
await attack('N_ANALYZER_SHA', 'ANALYZER_SHA', { analyzerSha: '0'.repeat(64) });
await attack('N_RUNNER_SHA', 'RUNNER_SHA', { runnerSha: '0'.repeat(64) });
await attack('N_SOURCE_CONTROLS', 'SOURCE_CONTROLS', { threads: 7 });
const originalQ8Samples = spec.design.stratified8.samplesPerComponent;
spec.design.stratified8.samplesPerComponent = 31;
await attack('N_CELL_SAMPLES', 'CELL_CONTROLS', {});
spec.design.stratified8.samplesPerComponent = originalQ8Samples;
const originalQ8Point = spec.design.stratified8.points[0];
spec.design.stratified8.points[0] = [0, 0];
await attack('N_CELL_POINT', 'CELL_CONTROLS', {});
spec.design.stratified8.points[0] = originalQ8Point;
const swapped = [...frozenSchedule]; [swapped[0], swapped[1]] = [swapped[1], swapped[0]];
await attack('N_SCHEDULE', 'SCHEDULE', { schedule: swapped });
await attack('N_PID_BINDING', 'PID_BINDING', { uniqueProcesses: 27 });
await attack('N_RENDER_COUNT', 'RENDER_COUNT', { renderCalls: 111 });
await attack('N_FRAME_ORDER', 'FRAME_ORDER', { frames: [22, 59, 97, 135] });
await attack('N_OUTPUT_HASH', 'OUTPUT_HASH', { firstOutputSha: '0'.repeat(64) });
await attack('N_EXR_LAYOUT', 'EXR_LAYOUT', { width: 961 });
await attack('N_ANALYSIS_BINDING', 'ANALYSIS_BINDING', { indexSha: '0'.repeat(64) });
await attack('N_CONTRACT_HASH', 'CONTRACT_HASH', { contractHash: '0'.repeat(64) });
await attack('N_FROZEN_GATE', 'FROZEN_GATE', { q8Gate: 1.11 });
await attack('N_DECISION_TAMPER', 'DECISION_TAMPER', { decision: 'TAMPERED' });
await attack('N_METRIC_TAMPER', 'METRIC_TAMPER', { q8Mean: -1 });

const nonemptyDir = resolve(workRoot, 'attack-nonempty');
await mkdir(nonemptyDir, { recursive: true });
await writeFile(resolve(nonemptyDir, 'sentinel'), 'attack\n');
const nonemptyReport = resolve(workRoot, 'attack-nonempty.json');
const nonemptyThreads = resolve(workRoot, 'attack-nonempty.threads.json');
const nonemptyAttack = await expectFailure(blender, [
  '--background', scenePath, '--disable-autoexec', '--python-exit-code', '1',
  '--python', configurator, '--python', renderer, '--',
  '--holdout-spec', specPath, '--review-spec', reviewPath, '--receipt', receiptPath,
  '--output-dir', nonemptyDir, '--report', nonemptyReport, '--cell', 'Q4_1', '--replicate', 'A',
], {
  ...process.env, OCIO: ocioPath, BFS_B22_THREADS_MODE: 'FIXED', BFS_B22_THREADS: '8',
  BFS_B22_CELL: 'T08', BFS_B22_INTERVENTION_REPORT: nonemptyThreads,
}, 'B32 holdout output directory must be empty');
attacks.push({ id: 'N_NONEMPTY_OUTPUT', expected: 'REJECTED_NONEMPTY_OUTPUT',
  observed: nonemptyAttack.observed, pass: nonemptyAttack.pass });

const attacksPass = attacks.every(item => item.pass);
const uniqueProcesses = new Set([...records.values()].map(item => item.processId)).size;
const renderCalls = [...records.values()].reduce((sum, item) => sum + item.report.renderCalls, 0);
const outputFiles = [...records.values()].reduce((sum, item) => sum + item.report.outputFileCount, 0);
const validExperiment = attacksPass && uniqueProcesses === spec.design.totalProcesses
  && renderCalls === spec.design.totalRenderCalls && outputFiles === spec.design.totalRenderCalls;
const decision = validExperiment ? analysis.decision : 'IDENTITY_OR_DESIGN_INVALID';
const result = {
  documentType: 'BFS_B32_QUADRATURE_COST_HOLDOUT_RESULT',
  version: '0.1.0',
  executedAtUtc: new Date().toISOString(),
  decision,
  independentDecision: analysis.decision,
  validExperiment,
  question: spec.question,
  design: spec.design,
  identities: {
    ...spec.source, ...spec.runtime,
    holdoutSpecSha256: specSha,
    evidenceBasis: spec.evidenceBasis,
    ...tools,
  },
  componentVerdicts: analysis.componentVerdicts,
  summary: analysis.summary,
  cost: analysis.cost,
  frames: analysis.frames,
  aggregate: {
    uniqueProcesses,
    renderProcesses: records.size,
    renderCalls,
    outputFiles,
    totalRenderSeconds: [...records.values()].reduce((sum, item) => sum + item.report.totalRenderSeconds, 0),
    attacksPassed: attacks.filter(item => item.pass).length,
    attacksTotal: attacks.length,
  },
  processLedger: ledger.processes,
  attacks,
  artifacts: {
    processLedger: repoUri(ledgerPath),
    analysisIndex: repoUri(indexPath),
    analysis: repoUri(analysisPath),
    binding: repoUri(bindingPath),
    manifests: Object.fromEntries([...records].map(([id, item]) => [id, repoUri(item.manifestPath)])),
  },
  nonClaims: spec.nonClaims,
};
await writeFile(resolve(experimentRoot, 'results.json'), serialize(result));
process.stdout.write(
  `BFS_B32_HOLDOUT_RESULT ${decision} q4_mean=${analysis.summary.q4ToNaturalEdgeMean} `
  + `q8_mean=${analysis.summary.q8ToNaturalEdgeMean} attacks=${result.aggregate.attacksPassed}/${result.aggregate.attacksTotal}\n`
);
if (!validExperiment) process.exitCode = 1;
