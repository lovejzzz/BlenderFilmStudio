import { readFile, readdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256File } from './lib/receipt-format.mjs';

const root = resolve(repositoryRoot, 'experiments/quadrature-cost-holdout-v0-1');
const evidence = resolve(root, 'evidence');
const specPath = resolve(repositoryRoot, 'specs/quadrature-cost-holdout-spec.v0.1.json');
const ledgerPath = resolve(evidence, 'process-ledger.json');
const indexPath = resolve(evidence, 'analysis-index.json');
const diagnosticPath = resolve(evidence, 'edge-mask-tie-diagnostic.json');
const rendererPath = resolve(repositoryRoot, 'blender/render_b32_quadrature_cost_holdout.py');
const analyzerPath = resolve(repositoryRoot, 'blender/analyze_b32_quadrature_cost_holdout.py');
const runnerPath = resolve(repositoryRoot, 'scripts/run-b32-quadrature-cost-holdout.mjs');
const diagnosticToolPath = resolve(repositoryRoot, 'blender/diagnose_b32_edge_mask_ties.py');
const serialize = value => `${JSON.stringify(value, null, 2)}\n`;

const spec = JSON.parse(await readFile(specPath, 'utf8'));
const ledger = JSON.parse(await readFile(ledgerPath, 'utf8'));
const index = JSON.parse(await readFile(indexPath, 'utf8'));
const diagnostic = JSON.parse(await readFile(diagnosticPath, 'utf8'));
const files = await readdir(evidence);
const manifests = files.filter(name => name.endsWith('.manifest.json'));
const reports = files.filter(name => name.endsWith('.render.json'));
const threads = files.filter(name => name.endsWith('.threads.json'));
const outputFiles = index.processes.reduce((sum, item) => sum + item.outputs.length, 0);
const uniqueProcesses = new Set(index.processes.map(item => item.processId)).size;
if (manifests.length !== 28 || reports.length !== 28 || threads.length !== 28
    || outputFiles !== 112 || uniqueProcesses !== 28) {
  throw new Error('Invalid-attempt capture counts do not match completed formal renders');
}
const failedFrame = diagnostic.observations.find(item => item.pixelsGreaterThanOrEqualThreshold !== item.targetTopFivePercentPixels);
if (failedFrame?.frame !== 22 || failedFrame.pixelsGreaterThanOrEqualThreshold !== 25921) {
  throw new Error('Unexpected edge-mask diagnostic');
}
const result = {
  documentType: 'BFS_B32_QUADRATURE_COST_HOLDOUT_INVALID_ATTEMPT',
  version: '0.1.0',
  status: 'FORMAL_ATTEMPT_INVALID_BEFORE_METRIC_DECISION',
  decision: 'IDENTITY_OR_DESIGN_INVALID',
  validExperiment: false,
  attempt: 1,
  holdoutSpecSha256: await sha256File(specPath),
  failure: {
    stage: 'analysis edge-mask construction',
    message: 'Frame 22 edge pixel count mismatch',
    preregisteredExpectedPixels: spec.analysis.edgeMaskExpectedPixelsPerFrame,
    observedPixelsUsingQuantileGreaterEqual: failedFrame.pixelsGreaterThanOrEqualThreshold,
    pixelsGreaterThanThreshold: failedFrame.pixelsGreaterThanThreshold,
    pixelsEqualToThreshold: failedFrame.pixelsEqualToThreshold,
    cause: 'Two gradient values tied at the cutoff; quantile plus >= selected 25,921 rather than exactly 25,920 pixels.',
  },
  completedBeforeFailure: {
    formalRenderProcesses: index.processes.length,
    uniqueFormalProcessIds: uniqueProcesses,
    renderCalls: outputFiles,
    outputFiles,
    manifests: manifests.length,
    renderReports: reports.length,
    threadReports: threads.length,
    analysisProduced: false,
    attacksRunByFormalRunner: 0,
  },
  identities: {
    blenderBinarySha256: spec.runtime.blenderBinarySha256,
    sceneBlendSha256: spec.source.sceneBlendSha256,
    ocioSha256: spec.runtime.ocioSha256,
    rendererSha256: await sha256File(rendererPath),
    analyzerSha256: await sha256File(analyzerPath),
    runnerSha256: await sha256File(runnerPath),
    diagnosticToolSha256: await sha256File(diagnosticToolPath),
  },
  artifacts: {
    processLedgerSha256: await sha256File(ledgerPath),
    analysisIndexSha256: await sha256File(indexPath),
    edgeMaskTieDiagnosticSha256: await sha256File(diagnosticPath),
    ledgerHash: ledger.ledgerHash,
    indexHash: index.indexHash,
  },
  nonClaims: [
    'No cost-quality metric decision was produced from attempt 1.',
    'The invalidity is an analysis-contract failure, not evidence for or against Q4 or Q8 quality.',
    'The completed renders remain evidence of execution but cannot be relabeled as a clean preregistered confirmation.',
  ],
};
await writeFile(resolve(root, 'results.json'), serialize(result));
process.stdout.write(`BFS_B32_INVALID_ATTEMPT_CAPTURED frame=${failedFrame.frame} observed=${failedFrame.pixelsGreaterThanOrEqualThreshold} renders=${outputFiles}\n`);
