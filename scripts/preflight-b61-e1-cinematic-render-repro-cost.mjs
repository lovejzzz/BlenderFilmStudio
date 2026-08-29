#!/usr/bin/env node

import { execFile } from 'node:child_process';
import { readFile, readdir, statfs } from 'node:fs/promises';
import { relative, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { isDeepStrictEqual, promisify } from 'node:util';
import {
  durableMkdir,
  resolveExistingRepositoryPath,
  resolveFreshRepositoryPath,
  sha256Bytes,
  sha256File,
  validSelfHash,
  writeDurableHashed,
} from './lib/production-compile-receipt.mjs';
import { repositoryRoot } from './lib/scene-spec.mjs';

const execFileAsync = promisify(execFile);
const CONTRACT_URI = 'specs/cinematic-render-repro-cost.v0.1.json';
const CORRECTION_URI = 'specs/cinematic-render-repro-cost-c4-generated-review-image-correction.v0.1.json';
const PROTOCOL_URI = 'research/2026-08-29-b61-e1-cinematic-render-repro-cost-protocol.md';
const PREREGISTRATION_COMMIT = 'e603864';
const EXPECTED_ROOTS = {
  outputRoot: 'experiments/cinematic-render-repro-cost-preflight-v0-5',
  attemptRoot: 'experiments/cinematic-render-repro-cost-attempt-v0-5',
  formalRoot: 'experiments/cinematic-render-repro-cost-v0-5',
};
const TOOL_PATHS = [
  CONTRACT_URI,
  'specs/cinematic-render-repro-cost-c2-multilayer-exr-decoder-correction.v0.1.json',
  'specs/cinematic-render-repro-cost-c3-isolated-png-review-correction.v0.1.json',
  CORRECTION_URI,
  PROTOCOL_URI,
  'research/2026-08-29-b61-e1-c1-terminal-observability-correction.md',
  'research/2026-08-29-b61-e1-c2-multilayer-exr-decoder-correction.md',
  'research/2026-08-29-b61-e1-c3-isolated-png-review-correction.md',
  'research/2026-08-29-b61-e1-c4-generated-review-image-correction.md',
  'experiments/b61-exr-reopen-reconciliation-v0-1/result.json',
  'experiments/b61-exr-reopen-reconciliation-v0-1/receipt.json',
  'experiments/b61-png-export-context-diagnostic-v0-1/result.json',
  'experiments/b61-png-export-context-diagnostic-v0-1/receipt.json',
  'experiments/b61-generated-review-image-diagnostic-v0-1/result.json',
  'experiments/b61-generated-review-image-diagnostic-v0-1/receipt.json',
  'blender/render_b61_frames.py',
  'blender/audit_b61_exr.py',
  'scripts/preflight-b61-e1-cinematic-render-repro-cost.mjs',
  'scripts/run-b61-e1-cinematic-render-repro-cost.mjs',
  'scripts/audit-b61-e1-cinematic-render-repro-cost.mjs',
];

function parseArguments(argv) {
  const parsed = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--output-root') parsed.outputRoot = argv[++index];
    else if (token === '--attempt-root') parsed.attemptRoot = argv[++index];
    else if (token === '--formal-root') parsed.formalRoot = argv[++index];
    else if (token === '--tool-freeze-commit') parsed.toolFreezeCommit = argv[++index];
    else throw new Error(`Unknown or incomplete argument: ${token}`);
  }
  for (const key of [...Object.keys(EXPECTED_ROOTS), 'toolFreezeCommit']) {
    if (!parsed[key]) throw new Error(`Missing --${key.replace(/[A-Z]/g, letter => `-${letter.toLowerCase()}`)}`);
  }
  if (!/^[0-9a-f]{40}$/.test(parsed.toolFreezeCommit)) throw new Error('Tool-freeze commit must be a full lowercase SHA-1');
  for (const [key, expected] of Object.entries(EXPECTED_ROOTS)) if (parsed[key] !== expected) throw new Error(`B61 ${key} mismatch`);
  return parsed;
}

async function git(args, encoding = 'utf8') {
  const result = await execFileAsync('/usr/bin/git', args, {
    cwd: repositoryRoot, encoding, timeout: 15000, maxBuffer: 32 * 1024 * 1024,
    env: { PATH: '/usr/bin:/bin', LANG: 'C', LC_ALL: 'C', GIT_CONFIG_NOSYSTEM: '1', GIT_TERMINAL_PROMPT: '0' },
  });
  return result.stdout;
}

async function verifyToolFreeze(commit) {
  const head = (await git(['rev-parse', 'HEAD'])).trim();
  const origin = (await git(['rev-parse', 'origin/main'])).trim();
  if (head !== commit || origin !== commit) throw new Error('B61 tool-freeze commit must equal pushed HEAD and origin/main');
  await git(['merge-base', '--is-ancestor', PREREGISTRATION_COMMIT, commit]);
  const hashes = {};
  for (const uri of TOOL_PATHS) {
    const path = await resolveExistingRepositoryPath(uri, `B61 frozen tool ${uri}`);
    const current = await sha256File(path);
    const frozen = sha256Bytes(await git(['show', `${commit}:${uri}`], null));
    if (current !== frozen) throw new Error(`B61 tool-freeze mismatch: ${uri}`);
    hashes[uri] = current;
  }
  return hashes;
}

async function validateInputs(contract) {
  const rows = [];
  const ocioPath = await resolveExistingRepositoryPath(contract.runtime.ocio.uri, 'B61 OCIO config');
  if (await sha256File(ocioPath) !== contract.runtime.ocio.sha256) throw new Error('B61 OCIO hash mismatch');
  const calibrationPath = await resolveExistingRepositoryPath(contract.calibration.uri, 'B61 calibration result');
  const calibration = JSON.parse(await readFile(calibrationPath, 'utf8'));
  if (await sha256File(calibrationPath) !== contract.calibration.sha256 || !validSelfHash(calibration, 'resultHash')
    || calibration.resultHash !== contract.calibration.resultHash || calibration.status !== 'PASS'
    || calibration.calibrationDecision?.formalB61Samples !== contract.render.samples) throw new Error('B61 calibration binding mismatch');
  const failures = [];
  for (const uri of contract.calibration.retainedFailures) {
    const path = await resolveExistingRepositoryPath(uri, `B61 retained failure ${uri}`);
    const record = JSON.parse(await readFile(path, 'utf8'));
    if (!validSelfHash(record, 'failureHash') || record.status !== 'INVALIDATED') throw new Error(`B61 retained failure invalid: ${uri}`);
    failures.push({ uri, sha256: await sha256File(path), failureHash: record.failureHash, reason: record.reason });
  }
  for (const shot of contract.shots) {
    const blendPath = await resolveExistingRepositoryPath(shot.sourceBlend.uri, `${shot.label} source blend`);
    const receiptPath = await resolveExistingRepositoryPath(shot.productionReceipt.uri, `${shot.label} production receipt`);
    if (await sha256File(blendPath) !== shot.sourceBlend.sha256 || await sha256File(receiptPath) !== shot.productionReceipt.sha256) throw new Error(`${shot.label} source hash mismatch`);
    const receipt = JSON.parse(await readFile(receiptPath, 'utf8'));
    if (!validSelfHash(receipt, 'receiptHash') || receipt.receiptHash !== shot.productionReceipt.receiptHash || receipt.status !== 'PASS'
      || receipt.buildPlan?.planHash !== shot.planHash || receipt.restrictedCompile?.sceneStructureCanonical?.structureHash !== shot.structureHash
      || receipt.restrictedCompile?.sceneBlend?.sha256 !== shot.sourceBlend.sha256) throw new Error(`${shot.label} production receipt binding mismatch`);
    rows.push({ label: shot.label, sourceBlend: shot.sourceBlend, productionReceipt: shot.productionReceipt, planHash: shot.planHash, structureHash: shot.structureHash });
  }
  return { rows, calibration: { uri: contract.calibration.uri, sha256: await sha256File(calibrationPath), resultHash: calibration.resultHash }, failures };
}

async function treeIdentity(uri) {
  const root = await resolveExistingRepositoryPath(uri, `B61 retained tree ${uri}`, 'directory');
  async function walk(directory) {
    const output = [];
    for (const entry of await readdir(directory, { withFileTypes: true })) {
      const path = resolve(directory, entry.name);
      if (entry.isDirectory()) output.push(...await walk(path));
      else if (entry.isFile()) output.push(path);
      else throw new Error(`Unsupported retained-tree entry: ${path}`);
    }
    return output;
  }
  const files = (await walk(root)).sort();
  let bytes = 0;
  let material = '';
  for (const path of files) {
    const content = await readFile(path);
    bytes += content.length;
    material += `${relative(root, path).split('\\').join('/')}\0${sha256Bytes(content)}\n`;
  }
  return { files: files.length, bytes, sha256: sha256Bytes(Buffer.from(material)) };
}

async function validateCorrection(parsed) {
  const path = await resolveExistingRepositoryPath(CORRECTION_URI, 'B61 C4 correction');
  const correction = JSON.parse(await readFile(path, 'utf8'));
  if (correction.status !== 'PREREGISTERED' || correction.authorizedRetryRoots.preflight !== parsed.outputRoot
    || correction.authorizedRetryRoots.attempt !== parsed.attemptRoot || correction.authorizedRetryRoots.formal !== parsed.formalRoot) throw new Error('B61 C4 retry-root binding mismatch');
  const attemptTree = await treeIdentity(correction.failedFormalRun.attemptRoot);
  const formalTree = await treeIdentity(correction.failedFormalRun.formalRoot);
  if (!isDeepStrictEqual(attemptTree, correction.failedFormalRun.attemptTree) || !isDeepStrictEqual(formalTree, correction.failedFormalRun.formalTree)) throw new Error('B61 v0.4 retained failure tree mismatch');
  const summaryPath = await resolveExistingRepositoryPath(correction.failedFormalRun.failureSummary.uri, 'B61 v0.4 failure summary');
  const summary = JSON.parse(await readFile(summaryPath, 'utf8'));
  if (await sha256File(summaryPath) !== correction.failedFormalRun.failureSummary.sha256 || !validSelfHash(summary, 'failureHash')
    || summary.failureHash !== correction.failedFormalRun.failureSummary.failureHash || summary.rootCauseProven !== true) throw new Error('B61 v0.4 failure-summary binding mismatch');
  const resultPath = await resolveExistingRepositoryPath(correction.diagnosticEvidence.result.uri, 'B61 D5 result');
  const result = JSON.parse(await readFile(resultPath, 'utf8'));
  const receiptPath = await resolveExistingRepositoryPath(correction.diagnosticEvidence.receipt.uri, 'B61 D5 receipt');
  const receipt = JSON.parse(await readFile(receiptPath, 'utf8'));
  if (await sha256File(resultPath) !== correction.diagnosticEvidence.result.sha256 || !validSelfHash(result, 'resultHash')
    || result.resultHash !== correction.diagnosticEvidence.result.resultHash || result.status !== 'PASS' || result.productionSettingsUnchanged !== true
    || result.generatedImage?.hasData !== true || result.png?.validHeader !== true || result.png?.dimensions?.[0] !== 1920 || result.png?.dimensions?.[1] !== 1080
    || await sha256File(receiptPath) !== correction.diagnosticEvidence.receipt.sha256 || !validSelfHash(receipt, 'receiptHash')
    || receipt.receiptHash !== correction.diagnosticEvidence.receipt.receiptHash || receipt.status !== 'PASS') throw new Error('B61 D5 evidence mismatch');
  return { uri: CORRECTION_URI, sha256: await sha256File(path), attemptTree, formalTree, failureHash: summary.failureHash, generatedReviewResultHash: result.resultHash, generatedReviewReceiptHash: receipt.receiptHash };
}

export async function runB61Preflight(argv) {
  const parsed = parseArguments(argv);
  const outputPath = await resolveFreshRepositoryPath(parsed.outputRoot, 'B61 preflight root');
  await resolveFreshRepositoryPath(parsed.attemptRoot, 'B61 attempt root');
  await resolveFreshRepositoryPath(parsed.formalRoot, 'B61 formal root');
  const contractPath = await resolveExistingRepositoryPath(CONTRACT_URI, 'B61 contract');
  const contract = JSON.parse(await readFile(contractPath, 'utf8'));
  if (contract.schemaVersion !== 'bfs.cinematicRenderReproCost.v0.1' || contract.status !== 'PREREGISTERED') throw new Error('B61 contract binding mismatch');
  const toolHashes = await verifyToolFreeze(parsed.toolFreezeCommit);
  const inputs = await validateInputs(contract);
  inputs.correction = await validateCorrection(parsed);
  const filesystem = await statfs(repositoryRoot, { bigint: true });
  const availableBytes = filesystem.bavail * filesystem.bsize;
  const reserve = BigInt(contract.resourceCeilings.minimumDiskReserveBytes);
  const projected = BigInt(contract.resourceCeilings.maximumFormalBytes);
  if (availableBytes - projected < reserve) throw new Error('B61 projected formal output violates disk reserve');
  const checks = [
    ['PREREGISTRATION_ANCESTRY', true],
    ['TOOL_FREEZE_EXACT', Object.keys(toolHashes).length === TOOL_PATHS.length],
    ['SOURCE_BINDINGS_EXACT', inputs.rows.length === 3],
    ['CALIBRATION_AND_FAILURES_EXACT', inputs.failures.length === 2],
    ['MATRIX_EXACT', contract.render.frames.length === 3 && contract.render.repetitions.length === 2],
    ['RESOURCE_CEILINGS_EXACT', contract.resourceCeilings.renderBlenderStarts === 6 && contract.resourceCeilings.renderCalls === 18],
    ['DISK_RESERVE_PASS', availableBytes - projected >= reserve],
    ['OFFICIAL_ATTEMPT_AND_FORMAL_ROOTS_FRESH', true],
    ['ZERO_BLENDER_PREFLIGHT', true],
  ].map(([id, pass]) => ({ id, pass }));
  if (!checks.every(row => row.pass)) throw new Error('B61 preflight checks failed');
  await durableMkdir(outputPath);
  const record = await writeDurableHashed(resolve(outputPath, 'preflight.json'), {
    schemaVersion: 'bfs.cinematicRenderReproCostPreflight.v0.1', status: 'ACCEPTED', reason: null,
    preregistrationCommit: PREREGISTRATION_COMMIT, toolFreezeCommit: parsed.toolFreezeCommit,
    contract: { uri: CONTRACT_URI, sha256: await sha256File(contractPath) }, roots: { preflight: parsed.outputRoot, attempt: parsed.attemptRoot, formal: parsed.formalRoot },
    inputs, checks, toolHashes,
    disk: { availableBytes: availableBytes.toString(), projectedBytes: projected.toString(), minimumReserveBytes: reserve.toString() },
    operations: { nodeChildren: 0, blenderProcesses: 0, renderCalls: 0, frames: 0, modelCalls: 0, networkCalls: 0, dockerProcesses: 0 },
  }, 'preflightHash');
  process.stdout.write(`BFS_B61_PREFLIGHT ACCEPTED ${checks.length}/${checks.length} ${record.preflightHash}\n`);
  return record;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  runB61Preflight(process.argv.slice(2)).catch(error => { process.stderr.write(`BFS_B61_PREFLIGHT_ERROR ${error.message}\n`); process.exitCode = 1; });
}
