import { mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { relative, resolve, sep } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256Canonical, sha256File } from './lib/receipt-format.mjs';

const experimentRoot = resolve(repositoryRoot, 'experiments/quadrature-temporal-derivation-v0-1');
const evidenceRoot = resolve(experimentRoot, 'evidence');
const workRoot = resolve(experimentRoot, 'work');
const specPath = resolve(repositoryRoot, 'specs/quadrature-temporal-derivation-spec.v0.1.json');
const reviewPath = resolve(repositoryRoot, 'specs/review-render-spec.v0.1.json');
const configurator = resolve(repositoryRoot, 'blender/configure_eevee_threads.py');
const renderer = resolve(repositoryRoot, 'blender/render_b33_quadrature_temporal_derivation.py');
const analyzer = resolve(repositoryRoot, 'blender/analyze_b33_quadrature_temporal_derivation.py');
const runner = fileURLToPath(import.meta.url);
const blender = resolve(process.env.BLENDER_BIN || '/Applications/Blender.app/Contents/MacOS/Blender');
const b32SpecPath = resolve(repositoryRoot, 'specs/quadrature-cost-holdout-spec.v0.2.json');
const b32ResultPath = resolve(repositoryRoot, 'experiments/quadrature-cost-holdout-v0-2/results.json');
const b32AnalysisPath = resolve(repositoryRoot, 'experiments/quadrature-cost-holdout-v0-2/evidence/quality-analysis.json');
const b32ResearchPath = resolve(repositoryRoot, 'research/2026-08-26-b32-quadrature-cost-holdout-v02-result.md');
const expectedSpecSha = '5630ed7cc9a43f9f195292296923ff7864625bad6b0dbad4a7eb7b7eeb4ab594';
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
    return {
      pass: error.output?.includes(pattern) === true,
      observed: error.output?.includes(pattern) ? pattern : `EXIT_${error.code}`,
    };
  }
}

function failUnless(condition, message) {
  if (!condition) throw new Error(message);
}

function expectedCellControls(spec, cell) {
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
failUnless(specSha === expectedSpecSha, 'B33 derivation spec changed after preregistration');
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
  [b32SpecPath, spec.evidenceBasis.b32SpecSha256, 'B32 spec'],
  [b32ResultPath, spec.evidenceBasis.b32ResultSha256, 'B32 result'],
  [b32AnalysisPath, spec.evidenceBasis.b32AnalysisSha256, 'B32 analysis'],
  [b32ResearchPath, spec.evidenceBasis.b32ResearchSha256, 'B32 research note'],
];
for (const [path, expected, label] of fixedInputs) {
  failUnless(await sha256File(path) === expected, `${label} frozen SHA mismatch`);
}
const b32Result = JSON.parse(await readFile(b32ResultPath, 'utf8'));
failUnless(b32Result.decision === spec.evidenceBasis.b32Decision, 'B32 frozen decision mismatch');

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
    '--derivation-spec', specPath, '--review-spec', reviewPath, '--receipt', receiptPath,
    '--output-dir', outputDir, '--report', reportPath, '--cell', cell, '--replicate', replicate,
  ], {
    ...process.env,
    OCIO: ocioPath,
    BFS_B22_THREADS_MODE: 'FIXED', BFS_B22_THREADS: '8', BFS_B22_CELL: 'T08',
    BFS_B22_INTERVENTION_REPORT: threadPath,
  });
  const report = JSON.parse(await readFile(reportPath, 'utf8'));
  failUnless(report.processId === launched.processId, `${replicateId} PID binding mismatch`);
  failUnless(JSON.stringify(report.frames) === JSON.stringify(spec.design.frames), `${replicateId} frame order mismatch`);
  failUnless(report.renderCalls === spec.design.frames.length, `${replicateId} render count mismatch`);
  const controls = expectedCellControls(spec, cell);
  failUnless(report.observedControls.samples === controls.samples, `${replicateId} samples mismatch`);
  failUnless(JSON.stringify(report.observedControls.jitter) === JSON.stringify(controls.jitter), `${replicateId} jitter mismatch`);
  const manifestBody = {
    documentType: 'BFS_B33_QUADRATURE_TEMPORAL_RENDER_MANIFEST',
    version: spec.version,
    derivationSpecSha256: specSha,
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
  records.set(replicateId, { replicateId, cell, replicate, processId: launched.processId,
    outputDir, reportPath, threadPath, manifestPath, report, manifest });
  manifests.set(replicateId, manifest);
  process.stdout.write(`BFS_B33_DERIVATION_PROCESS_OK ${replicateId} pid=${launched.processId} seconds=${report.totalRenderSeconds}\n`);
}

failUnless(new Set([...records.values()].map(item => item.processId)).size === spec.design.totalProcesses,
  'B33 official process IDs are missing or duplicated');
const totalRenderCalls = [...records.values()].reduce((sum, item) => sum + item.report.renderCalls, 0);
failUnless(totalRenderCalls === spec.design.totalRenderCalls, 'B33 total render calls mismatch');

const ledgerBody = {
  documentType: 'BFS_B33_QUADRATURE_TEMPORAL_PROCESS_LEDGER',
  version: spec.version,
  derivationSpecSha256: specSha,
  processes: frozenSchedule.map((replicateId, orderIndex) => {
    const item = records.get(replicateId);
    return {
      orderIndex, replicateId, cell: item.cell, replicate: item.replicate,
      processId: item.processId, frames: item.report.frames, renderCalls: item.report.renderCalls,
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
  documentType: 'BFS_B33_QUADRATURE_TEMPORAL_ANALYSIS_INDEX',
  version: spec.version,
  derivationSpecSha256: specSha,
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

const analysisPath = resolve(evidenceRoot, 'temporal-analysis.json');
const independentAnalysisPath = resolve(evidenceRoot, 'temporal-analysis-independent.json');
await run(blender, [
  '--factory-startup', '--background', '--disable-autoexec', '--python-exit-code', '1',
  '--python', analyzer, '--', '--index', indexPath, '--spec', specPath, '--output', analysisPath,
]);
await run(blender, [
  '--factory-startup', '--background', '--disable-autoexec', '--python-exit-code', '1',
  '--python', analyzer, '--', '--index', indexPath, '--spec', specPath, '--output', independentAnalysisPath,
]);
const analysisSha = await sha256File(analysisPath);
const independentAnalysisSha = await sha256File(independentAnalysisPath);
failUnless(analysisSha === independentAnalysisSha, 'independent analyzer output mismatch');
const analysis = JSON.parse(await readFile(analysisPath, 'utf8'));

const contractHash = sha256Canonical({
  source: spec.source, runtime: spec.runtime, design: spec.design, analysis: spec.analysis,
  derivationValidityGates: spec.derivationValidityGates, derivationDecision: spec.derivationDecision,
});
const bindingBody = {
  documentType: 'BFS_B33_QUADRATURE_TEMPORAL_ANALYSIS_BINDING',
  version: spec.version,
  derivationSpecSha256: specSha,
  indexSha256: await sha256File(indexPath), analysisSha256: analysisSha,
  independentAnalysisSha256: independentAnalysisSha,
  ledgerHash: ledger.ledgerHash,
  manifestHashes: Object.fromEntries([...manifests].map(([id, value]) => [id, value.manifestHash])),
  analyzerSha256: tools.analyzerSha256, runnerSha256: tools.runnerSha256, contractHash,
};
const binding = { ...bindingBody, bindingHash: sha256Canonical(bindingBody) };
const bindingPath = resolve(evidenceRoot, 'analysis-binding.json');
await writeFile(bindingPath, serialize(binding));

function validate(overrides = {}) {
  const observed = {
    specSha, b32ResultSha: spec.evidenceBasis.b32ResultSha256,
    sceneSha: spec.source.sceneBlendSha256, frames: spec.design.frames,
    processIds: frozenSchedule.map(id => records.get(id).processId),
    topK: spec.analysis.topKPixels, tieBreak: spec.analysis.spatialEdgeMaskRule,
    indexHash: index.indexHash, bindingHash: binding.bindingHash,
    decision: analysis.decision,
    ...overrides,
  };
  failUnless(observed.specSha === expectedSpecSha, 'spec hash mismatch');
  failUnless(observed.b32ResultSha === spec.evidenceBasis.b32ResultSha256, 'B32 evidence hash mismatch');
  failUnless(observed.sceneSha === spec.source.sceneBlendSha256, 'scene identity mismatch');
  failUnless(JSON.stringify(observed.frames) === JSON.stringify([121, 122, 123, 124, 125, 126, 127, 128]), 'frame interval mismatch');
  failUnless(new Set(observed.processIds).size === spec.design.totalProcesses, 'process ID uniqueness mismatch');
  failUnless(observed.topK === 25920 && observed.tieBreak.includes('flattened C-row-major index ascending'), 'top-k contract mismatch');
  failUnless(observed.indexHash === index.indexHash, 'index binding mismatch');
  failUnless(observed.bindingHash === binding.bindingHash, 'analysis binding mismatch');
  failUnless(observed.decision === analysis.decision, 'decision mismatch');
}

function validationAttack(name, overrides, expectedMessage) {
  try {
    validate(overrides);
    return { name, pass: false, observed: 'UNEXPECTED_SUCCESS' };
  } catch (error) {
    return { name, pass: error.message.includes(expectedMessage), observed: error.message };
  }
}

const attacks = [
  validationAttack('spec_hash_substitution', { specSha: '0'.repeat(64) }, 'spec hash mismatch'),
  validationAttack('b32_evidence_hash_substitution', { b32ResultSha: '1'.repeat(64) }, 'B32 evidence hash mismatch'),
  validationAttack('scene_identity_substitution', { sceneSha: '2'.repeat(64) }, 'scene identity mismatch'),
  validationAttack('frame_interval_substitution', { frames: [120, 121, 122, 123, 124, 125, 126, 127] }, 'frame interval mismatch'),
  validationAttack('duplicate_process_id_substitution', {
    processIds: frozenSchedule.map((id, indexValue) => indexValue === 1 ? records.get(frozenSchedule[0]).processId : records.get(id).processId),
  }, 'process ID uniqueness mismatch'),
  validationAttack('top_k_tie_break_substitution', { topK: 25921, tieBreak: 'quantile plus >=' }, 'top-k contract mismatch'),
  validationAttack('analysis_binding_substitution', { bindingHash: '3'.repeat(64) }, 'analysis binding mismatch'),
  validationAttack('decision_substitution', { decision: 'TEMPORAL_QUALITY_SUPPORT' }, 'decision mismatch'),
];

const tamperedIndexPath = resolve(evidenceRoot, 'attack-tampered-index.json');
const tamperedIndex = structuredClone(index);
tamperedIndex.processes[0].outputs[0].containerSha256 = '4'.repeat(64);
await writeFile(tamperedIndexPath, serialize(tamperedIndex));
attacks.push({ name: 'output_hash_substitution', ...(await expectFailure(blender, [
  '--factory-startup', '--background', '--disable-autoexec', '--python-exit-code', '1',
  '--python', analyzer, '--', '--index', tamperedIndexPath, '--spec', specPath,
  '--output', resolve(evidenceRoot, 'attack-output.json'),
], process.env, 'Container SHA mismatch')) });
await rm(tamperedIndexPath, { force: true });
await rm(resolve(evidenceRoot, 'attack-output.json'), { force: true });

const nonemptyDir = resolve(workRoot, 'attack-nonempty');
await mkdir(nonemptyDir, { recursive: true });
await writeFile(resolve(nonemptyDir, 'sentinel.txt'), 'must reject\n');
attacks.push({ name: 'nonempty_output_directory', ...(await expectFailure(blender, [
  '--background', scenePath, '--disable-autoexec', '--python-exit-code', '1',
  '--python', configurator, '--python', renderer, '--',
  '--derivation-spec', specPath, '--review-spec', reviewPath, '--receipt', receiptPath,
  '--output-dir', nonemptyDir, '--report', resolve(evidenceRoot, 'attack-nonempty.render.json'),
  '--cell', 'NATURAL32', '--replicate', 'A',
], {
  ...process.env, OCIO: ocioPath,
  BFS_B22_THREADS_MODE: 'FIXED', BFS_B22_THREADS: '8', BFS_B22_CELL: 'T08',
  BFS_B22_INTERVENTION_REPORT: resolve(evidenceRoot, 'attack-nonempty.threads.json'),
}, 'B33 derivation output directory must be empty')) });
await rm(nonemptyDir, { recursive: true, force: true });
await rm(resolve(evidenceRoot, 'attack-nonempty.render.json'), { force: true });
await rm(resolve(evidenceRoot, 'attack-nonempty.threads.json'), { force: true });

failUnless(attacks.every(item => item.pass), 'one or more B33 attacks did not reject');
validate();
const result = {
  documentType: 'BFS_B33_QUADRATURE_TEMPORAL_DERIVATION_RESULT',
  version: spec.version,
  experimentId: spec.experimentId,
  status: analysis.status,
  validExperiment: true,
  decision: analysis.decision,
  source: spec.source,
  runtime: spec.runtime,
  evidenceBasis: spec.evidenceBasis,
  execution: {
    frames: spec.design.frames,
    uniqueBlenderProcesses: new Set([...records.values()].map(item => item.processId)).size,
    renderCalls: totalRenderCalls,
    exrFiles: totalRenderCalls,
    independentAnalyzerByteExact: analysisSha === independentAnalysisSha,
  },
  identities: {
    derivationSpecSha256: specSha,
    processLedgerSha256: await sha256File(ledgerPath),
    analysisIndexSha256: await sha256File(indexPath),
    temporalAnalysisSha256: analysisSha,
    temporalAnalysisIndependentSha256: independentAnalysisSha,
    analysisBindingSha256: await sha256File(bindingPath),
    rendererSha256: tools.rendererSha256,
    analyzerSha256: tools.analyzerSha256,
    runnerSha256: tools.runnerSha256,
  },
  summary: analysis.summary,
  cost: analysis.cost,
  validityComponents: analysis.validityComponents,
  attacks: { passed: attacks.filter(item => item.pass).length, total: attacks.length, cases: attacks },
  nonClaims: spec.nonClaims,
};
const resultPath = resolve(experimentRoot, 'results.json');
await writeFile(resultPath, serialize(result));
process.stdout.write(
  `BFS_B33_DERIVATION_OK decision=${result.decision} processes=${result.execution.uniqueBlenderProcesses} `
  + `renders=${result.execution.renderCalls} attacks=${result.attacks.passed}/${result.attacks.total}\n`
);
