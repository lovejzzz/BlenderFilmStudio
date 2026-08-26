import { access, mkdir, readFile, rm, stat, writeFile } from 'node:fs/promises';
import { constants } from 'node:fs';
import { spawn } from 'node:child_process';
import { relative, resolve, sep } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { rehashReceipt, sha256File } from './lib/receipt-format.mjs';
import { verifyCompileReceipt } from './verify-compile-receipt.mjs';

const experimentRoot = resolve(repositoryRoot, 'experiments/compile-receipt-v0-1');
const evidenceRoot = resolve(experimentRoot, 'evidence');
const workRoot = resolve(experimentRoot, 'work');
const restrictedCli = resolve(repositoryRoot, 'scripts/run-restricted-blender-compile.mjs');
const blendAuditor = resolve(repositoryRoot, 'blender/audit_compiled_artifact.py');
const blender = process.env.BLENDER_BIN ?? '/Applications/Blender.app/Contents/MacOS/Blender';
const serialize = value => `${JSON.stringify(value, null, 2)}\n`;
const repoUri = path => relative(repositoryRoot, path).split(sep).join('/');

function run(command, args) {
  return new Promise((resolvePromise, reject) => {
    const child = spawn(command, args, { cwd: repositoryRoot, stdio: ['ignore', 'pipe', 'pipe'] });
    let output = '';
    child.stdout.on('data', chunk => { output += chunk; });
    child.stderr.on('data', chunk => { output += chunk; });
    child.on('error', reject);
    child.on('close', code => resolvePromise({ code, output }));
  });
}

async function compileRun(benchmark, label) {
  const output = resolve(evidenceRoot, `${benchmark}-${label}`);
  await mkdir(output, { recursive: true });
  const plan = resolve(repositoryRoot, `experiments/compiler-v0-1/plans/${benchmark}.build-plan.json`);
  const budgetReport = resolve(output, 'budget.report.json');
  const receiptPath = resolve(output, 'compile.receipt.json');
  const cli = await run(process.execPath, [restrictedCli, '--plan', plan, '--output-dir', output, '--report', budgetReport, '--receipt', receiptPath]);
  if (cli.code !== 0) throw new Error(`${benchmark}-${label} restricted compile failed:\n${cli.output}`);
  const receipt = JSON.parse(await readFile(receiptPath, 'utf8'));
  const verification = await verifyCompileReceipt(receiptPath);
  const blendAuditPath = resolve(output, 'blend.audit.json');
  const blendAuditRun = await run(blender, ['--background', '--factory-startup', '--disable-autoexec', '--python-exit-code', '1', '--python', blendAuditor, '--', '--input', resolve(output, 'scene.blend'), '--output', blendAuditPath]);
  if (blendAuditRun.code !== 0) throw new Error(`${benchmark}-${label} compiled blend audit failed:\n${blendAuditRun.output}`);
  const blendAudit = JSON.parse(await readFile(blendAuditPath, 'utf8'));
  return {
    benchmark, label, outputUri: repoUri(output), cliExitCode: cli.code, cliOutput: cli.output.trim(), receipt,
    verification, blendAudit,
    summary: {
      receiptHash: receipt.receiptHash,
      executionIdentityHash: receipt.executionIdentityHash,
      planHash: receipt.executionIdentity.buildPlan.planHash,
      structureHash: receipt.run.sceneManifest.structureHash,
      blendSha256: receipt.run.sceneBlend.sha256,
      manifestSha256: receipt.run.sceneManifest.sha256,
      budgetReportSha256: receipt.run.budgetReport.sha256,
    },
  };
}

async function writeReceiptVariant(id, receipt) {
  const path = resolve(workRoot, `${id}.receipt.json`);
  await writeFile(path, serialize(receipt));
  return path;
}

async function receiptNegative(baseReceipt, id, expectedReason, mutate, rehash = true) {
  let receipt = structuredClone(baseReceipt);
  await mutate(receipt);
  if (rehash) receipt = rehashReceipt(receipt);
  const path = await writeReceiptVariant(id, receipt);
  const verification = await verifyCompileReceipt(path);
  return { id, expectedReason, observedReason: verification.reason, rejected: !verification.valid, pass: !verification.valid && verification.reason === expectedReason, verification };
}

await rm(evidenceRoot, { recursive: true, force: true });
await rm(workRoot, { recursive: true, force: true });
await mkdir(evidenceRoot, { recursive: true });
await mkdir(workRoot, { recursive: true });

const runs = [];
for (const benchmark of ['B01', 'B02']) for (const label of ['A', 'B']) runs.push(await compileRun(benchmark, label));
const byId = new Map(runs.map(runResult => [`${runResult.benchmark}-${runResult.label}`, runResult]));
const b01a = byId.get('B01-A');
const baseReceipt = b01a.receipt;
const zeros = '0'.repeat(64);
const negativeTests = [];
negativeTests.push(await receiptNegative(baseReceipt, 'N_RECEIPT_SELF_HASH', 'RECEIPT_SELF_HASH', receipt => { receipt.createdAtUtc = '2000-01-01T00:00:00.000Z'; }, false));
negativeTests.push(await receiptNegative(baseReceipt, 'N_PLAN_FILE_SHA', 'PLAN_FILE_SHA', receipt => { receipt.executionIdentity.buildPlan.sha256 = zeros; }));
negativeTests.push(await receiptNegative(baseReceipt, 'N_PLAN_HASH_BINDING', 'PLAN_HASH_BINDING', receipt => { receipt.executionIdentity.buildPlan.planHash = zeros; }));
negativeTests.push(await receiptNegative(baseReceipt, 'N_COMPILER_SHA', 'COMPILER_SHA', receipt => { receipt.executionIdentity.tools.sceneCompiler.sha256 = zeros; }));
negativeTests.push(await receiptNegative(baseReceipt, 'N_BUDGET_PROFILE_SHA', 'BUDGET_PROFILE_SHA', receipt => { receipt.executionIdentity.configuration.budgetProfile.sha256 = zeros; }));
negativeTests.push(await receiptNegative(baseReceipt, 'N_OCIO_SHA', 'OCIO_SHA', receipt => { receipt.executionIdentity.configuration.ocio.sha256 = zeros; }));
negativeTests.push(await receiptNegative(baseReceipt, 'N_BLENDER_BINARY_SHA', 'BLENDER_BINARY_SHA', receipt => { receipt.executionIdentity.runtime.blender.sha256 = zeros; }));
negativeTests.push(await receiptNegative(baseReceipt, 'N_MANIFEST_SHA', 'MANIFEST_SHA', receipt => { receipt.run.sceneManifest.sha256 = zeros; }));
negativeTests.push(await receiptNegative(baseReceipt, 'N_BLEND_SHA', 'BLEND_SHA', receipt => { receipt.run.sceneBlend.sha256 = zeros; }));

negativeTests.push(await receiptNegative(baseReceipt, 'N_MANIFEST_PLAN_BINDING', 'MANIFEST_PLAN_BINDING', async receipt => {
  const sourceManifest = resolve(repositoryRoot, receipt.run.sceneManifest.uri);
  const manifest = JSON.parse(await readFile(sourceManifest, 'utf8'));
  manifest.execution.planHash = zeros;
  const mutatedManifest = resolve(workRoot, 'N_MANIFEST_PLAN_BINDING.scene.manifest.json');
  await writeFile(mutatedManifest, serialize(manifest));
  const metadata = await stat(mutatedManifest);
  receipt.run.sceneManifest.uri = repoUri(mutatedManifest);
  receipt.run.sceneManifest.sha256 = await sha256File(mutatedManifest);
  receipt.run.sceneManifest.bytes = metadata.size;
}));

negativeTests.push(await receiptNegative(baseReceipt, 'S_STRUCTURE_CANONICAL_SHA', 'STRUCTURE_CANONICAL_SHA', receipt => { receipt.run.sceneStructureCanonical.sha256 = zeros; }));

const dirtyOutput = resolve(workRoot, 'S_DIRTY_OUTPUT');
await mkdir(dirtyOutput, { recursive: true });
const dirtyMarker = resolve(dirtyOutput, 'pre-existing.marker');
await writeFile(dirtyMarker, 'owned B13 fixture\n');
const dirtyCli = await run(process.execPath, [restrictedCli,
  '--plan', resolve(repositoryRoot, 'experiments/compiler-v0-1/plans/B01.build-plan.json'),
  '--output-dir', dirtyOutput,
  '--report', resolve(workRoot, 'S_DIRTY_OUTPUT.report.json'),
  '--receipt', resolve(workRoot, 'S_DIRTY_OUTPUT.receipt.json'),
]);
const dirtySceneExists = await access(resolve(dirtyOutput, 'scene.blend'), constants.F_OK).then(() => true).catch(() => false);
const supplementaryTests = [
  negativeTests.pop(),
  { id: 'S_DIRTY_OUTPUT', expectedReason: 'EMPTY_OUTPUT_REQUIRED', observedReason: dirtyCli.output.trim(), rejected: dirtyCli.code !== 0, pass: dirtyCli.code !== 0 && dirtyCli.output.includes('Restricted compile output must be empty') && !dirtySceneExists, dirtySceneExists },
];

const preRegisteredNegatives = negativeTests;
const expectedStructures = {
  B01: 'c699fc27230d8dc378a9d4e6aa23a6425cc7007c0ee33a3172b6928f8e1b7f0b',
  B02: '025c6fa50dcacef3c6c30ea9ec7ed97ce09bce0a9f51157887bc73c3981fa856',
};
const positiveChecks = {
  fourReceiptsVerify: runs.length === 4 && runs.every(runResult => runResult.verification.valid),
  b01IdentityEqual: byId.get('B01-A').summary.executionIdentityHash === byId.get('B01-B').summary.executionIdentityHash,
  b02IdentityEqual: byId.get('B02-A').summary.executionIdentityHash === byId.get('B02-B').summary.executionIdentityHash,
  benchmarkIdentitiesDiffer: byId.get('B01-A').summary.executionIdentityHash !== byId.get('B02-A').summary.executionIdentityHash,
  b01StructureFrozen: ['A', 'B'].every(label => byId.get(`B01-${label}`).summary.structureHash === expectedStructures.B01),
  b02StructureFrozen: ['A', 'B'].every(label => byId.get(`B02-${label}`).summary.structureHash === expectedStructures.B02),
  receiptsRunSpecific: ['B01', 'B02'].every(benchmark => byId.get(`${benchmark}-A`).summary.receiptHash !== byId.get(`${benchmark}-B`).summary.receiptHash),
  blendEmbeddedBindings: runs.every(runResult => runResult.blendAudit.scene.planHash === runResult.summary.planHash && runResult.blendAudit.scene.structureHash === runResult.summary.structureHash && runResult.blendAudit.scene.manifestVersion === '0.2.0' && runResult.blendAudit.blender.buildHash === runResult.receipt.executionIdentity.runtime.blender.buildHash),
};
const report = {
  documentType: 'BFS_B13_COMPILE_RECEIPT_EXPERIMENT', version: '0.1.0', executedAtUtc: new Date().toISOString(),
  environment: { blenderVersion: baseReceipt.executionIdentity.runtime.blender.version, blenderBuildHash: baseReceipt.executionIdentity.runtime.blender.buildHash, blenderBinarySha256: baseReceipt.executionIdentity.runtime.blender.sha256, nodeVersion: process.version, nodeBinarySha256: baseReceipt.executionIdentity.runtime.node.sha256, platform: `${process.platform}-${process.arch}` },
  runs: runs.map(({ receipt, ...runResult }) => runResult), positiveChecks,
  negativeTests: preRegisteredNegatives,
  supplementaryTests,
  preRegisteredNegativeCount: 10,
  supplementaryNegativeCount: 2,
  formalB13Complete: Object.values(positiveChecks).every(Boolean) && preRegisteredNegatives.length === 10 && preRegisteredNegatives.every(test => test.pass) && supplementaryTests.every(test => test.pass),
  nonClaims: ['Receipt SHA-256 is not a signature.', 'The verifier is not remote attestation.', 'Clean .blend byte identity is not required.', 'Cinematic and physical quality remain separate gates.'],
};
await writeFile(resolve(experimentRoot, 'results.json'), serialize(report));
process.stdout.write(`BFS_B13_COMPILE_RECEIPT ${report.formalB13Complete ? 'FORMAL_TRUE' : 'FAILED'} ${preRegisteredNegatives.filter(test => test.pass).length}/${preRegisteredNegatives.length} preregistered + ${supplementaryTests.filter(test => test.pass).length}/${supplementaryTests.length} supplementary\n`);
if (!report.formalB13Complete) process.exitCode = 1;
