#!/usr/bin/env node

import { execFile } from 'node:child_process';
import { createHash } from 'node:crypto';
import { lstat, mkdir, open, readFile, readdir, statfs } from 'node:fs/promises';
import { dirname, relative, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { promisify } from 'node:util';
import { runBudgetedProcess } from './lib/budgeted-process.mjs';

const execFileAsync = promisify(execFile);
const repositoryRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const SPEC_URI = 'specs/b62-camera-quality-geometric-diagnostic.v0.1.json';
const PROTOCOL_URI = 'research/2026-08-29-b62-camera-quality-geometric-diagnostic-protocol.md';
const CORRECTION_URI = 'specs/b62-camera-quality-c1-version-normalization.v0.1.json';
const CORRECTION_PROTOCOL_URI = 'research/2026-08-29-b62-camera-quality-c1-version-normalization.md';
const ROOT_URI = 'experiments/b62-camera-quality-geometric-diagnostic-v0-2';
const PREREGISTRATION_COMMIT = '3383cf9';
const CORRECTION_COMMIT = '44acc2b';
const TOOL_URIS = [
  'blender/probe_b62_q1_geometric_visibility.py',
  'blender/audit_b62_q1_geometric_visibility.py',
  'scripts/run-b62-q1-geometric-diagnostic.mjs',
  'scripts/audit-b62-q1-geometric-diagnostic.mjs',
];

function canonicalize(value) {
  if (Array.isArray(value)) return value.map(canonicalize);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).sort(([left], [right]) => left.localeCompare(right)).map(([key, child]) => [key, canonicalize(child)]));
  }
  return value;
}

const canonicalJson = value => JSON.stringify(canonicalize(value));
const sha256Bytes = value => createHash('sha256').update(value).digest('hex');

async function sha256File(path) {
  return sha256Bytes(await readFile(path));
}

function validSelfHash(value, field) {
  if (!value || typeof value !== 'object' || !/^[0-9a-f]{64}$/.test(value[field] ?? '')) return false;
  const copy = structuredClone(value);
  const expected = copy[field];
  delete copy[field];
  return sha256Bytes(canonicalJson(copy)) === expected;
}

function requireValue(condition, message) {
  if (!condition) throw new Error(message);
}

function containedPath(uri) {
  requireValue(typeof uri === 'string' && uri.length > 0 && !uri.startsWith('/') && !uri.split('/').includes('..'), `unsafe repository path ${uri}`);
  const path = resolve(repositoryRoot, uri);
  const rel = relative(repositoryRoot, path);
  requireValue(rel !== '..' && !rel.startsWith(`..${process.platform === 'win32' ? '\\' : '/'}`), `repository path escapes ${uri}`);
  return path;
}

async function exists(path) {
  try {
    await lstat(path);
    return true;
  } catch (error) {
    if (error.code === 'ENOENT') return false;
    throw error;
  }
}

async function durableHashed(path, value, field) {
  const body = structuredClone(value);
  body[field] = sha256Bytes(canonicalJson(body));
  const handle = await open(path, 'wx', 0o600);
  try {
    await handle.writeFile(`${JSON.stringify(body, null, 2)}\n`);
    await handle.sync();
  } finally {
    await handle.close();
  }
  return body;
}

async function git(args, encoding = 'utf8') {
  return (await execFileAsync('/usr/bin/git', args, {
    cwd: repositoryRoot,
    encoding,
    timeout: 15000,
    maxBuffer: 32 * 1024 * 1024,
    env: { PATH: '/usr/bin:/bin', LANG: 'C', LC_ALL: 'C', GIT_CONFIG_NOSYSTEM: '1', GIT_TERMINAL_PROMPT: '0' },
  })).stdout;
}

async function committedFileHash(commit, uri) {
  return sha256Bytes(await git(['show', `${commit}:${uri}`], null));
}

async function treeIdentity(rootUri) {
  const rootPath = containedPath(rootUri);
  const files = [];
  async function walk(directory) {
    for (const entry of await readdir(directory, { withFileTypes: true })) {
      const path = resolve(directory, entry.name);
      if (entry.isDirectory()) await walk(path);
      else if (entry.isFile()) files.push(path);
      else throw new Error(`retained tree special file ${path}`);
    }
  }
  await walk(rootPath);
  files.sort();
  let bytes = 0;
  let material = '';
  for (const path of files) {
    const content = await readFile(path);
    bytes += content.length;
    material += `${relative(rootPath, path).split('\\').join('/')}\0${sha256Bytes(content)}\n`;
  }
  return { files: files.length, bytes, treeSha256: sha256Bytes(Buffer.from(material)) };
}

function parseArgs(argv) {
  requireValue(argv.length === 2 && argv[0] === '--tool-freeze-commit' && /^[0-9a-f]{40}$/.test(argv[1]), 'usage: --tool-freeze-commit <40-hex-sha>');
  return argv[1];
}

async function writeProcessReceipt(rootPath, processId, command, args, result) {
  return durableHashed(resolve(rootPath, 'processes', `${processId}.json`), {
    schemaVersion: 'bfs.b62CameraQualityProcessReceipt.v0.1',
    experimentId: 'B62-Q1-D1',
    processId,
    command,
    args,
    result,
  }, 'processHash');
}

async function runBlenderChild({ rootPath, processId, toolUri, outputName, masterPath, masterSha, spec }) {
  const blender = spec.runtime.blender.executable;
  const toolPath = containedPath(toolUri);
  const outputPath = resolve(rootPath, outputName);
  const args = [
    '--background', '--factory-startup', '--disable-autoexec', masterPath,
    '--python-exit-code', '1', '--python', toolPath, '--',
    '--output', outputPath, '--master-sha256', masterSha,
  ];
  const result = await runBudgetedProcess({
    command: blender,
    args,
    cwd: repositoryRoot,
    env: {
      PATH: '/usr/bin:/bin', LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8',
      OCIO: resolve(repositoryRoot, 'color/ocio/cg-config-v4.0.0_aces-v2.0_ocio-v2.5.ocio'),
    },
    outputRoot: rootPath,
    budgets: {
      wallTimeMs: spec.processBudget.maximumWallSecondsPerBlender * 1000,
      maxRssBytes: spec.processBudget.maximumPeakResidentSetSizeBytesPerBlender,
      maxLogBytes: spec.processBudget.maximumCombinedLogBytesPerChild,
      maxOutputFiles: 64,
      maxOutputBytes: spec.processBudget.projectedWriteBytes,
      sampleIntervalMs: 100,
    },
  });
  const receipt = await writeProcessReceipt(rootPath, processId, blender, args.map(value => value.startsWith(repositoryRoot) ? relative(repositoryRoot, value).split('\\').join('/') : value), result);
  requireValue(result.outcome === 'PASS' && result.child.exitCode === 0 && result.breach === null, `${processId} Blender child failed: ${result.outcome}`);
  requireValue(await exists(outputPath), `${processId} output missing`);
  return receipt;
}

async function runAuditorChild({ rootPath, freeze, spec }) {
  const auditorUri = 'scripts/audit-b62-q1-geometric-diagnostic.mjs';
  const args = [containedPath(auditorUri), '--root', ROOT_URI, '--tool-freeze-commit', freeze];
  const result = await runBudgetedProcess({
    command: process.execPath,
    args,
    cwd: repositoryRoot,
    env: { PATH: '/usr/bin:/bin', LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8' },
    outputRoot: rootPath,
    budgets: {
      wallTimeMs: 60000,
      maxRssBytes: 536870912,
      maxLogBytes: spec.processBudget.maximumCombinedLogBytesPerChild,
      maxOutputFiles: 64,
      maxOutputBytes: spec.processBudget.projectedWriteBytes,
      sampleIntervalMs: 100,
    },
  });
  const receipt = await writeProcessReceipt(rootPath, 'AUDITOR', process.execPath, [auditorUri, '--root', ROOT_URI, '--tool-freeze-commit', freeze], result);
  requireValue(result.outcome === 'PASS' && result.child.exitCode === 0 && result.breach === null, `AUDITOR child failed: ${result.outcome}`);
  return receipt;
}

export async function run(argv) {
  const freeze = parseArgs(argv);
  const head = (await git(['rev-parse', 'HEAD'])).trim();
  const origin = (await git(['rev-parse', 'origin/main'])).trim();
  requireValue(head === freeze && origin === freeze, `tool freeze is not current pushed HEAD: head=${head} origin=${origin}`);
  await git(['merge-base', '--is-ancestor', PREREGISTRATION_COMMIT, freeze]);
  await git(['merge-base', '--is-ancestor', CORRECTION_COMMIT, freeze]);
  const specPath = containedPath(SPEC_URI);
  const protocolPath = containedPath(PROTOCOL_URI);
  const correctionPath = containedPath(CORRECTION_URI);
  const correctionProtocolPath = containedPath(CORRECTION_PROTOCOL_URI);
  const spec = JSON.parse(await readFile(specPath, 'utf8'));
  const correction = JSON.parse(await readFile(correctionPath, 'utf8'));
  requireValue(spec.experimentId === 'B62-Q1-D1' && spec.statusBeforeToolCreation === 'PREREGISTERED', 'spec state mismatch');
  requireValue(correction.correctionId === 'B62-Q1-D1-C1' && correction.statusBeforeToolChange === 'PREREGISTERED', 'C1 state mismatch');
  requireValue(spec.output.formalRoot === correction.retainedFailure.root && correction.authorizedChanges.retryRoot === ROOT_URI, 'formal/retry root mismatch');
  const allFrozenUris = [SPEC_URI, PROTOCOL_URI, CORRECTION_URI, CORRECTION_PROTOCOL_URI, ...TOOL_URIS];
  const toolHashes = {};
  for (const uri of allFrozenUris) {
    const current = await sha256File(containedPath(uri));
    const committed = await committedFileHash(freeze, uri);
    requireValue(current === committed, `scoped working byte drift ${uri}`);
    if (TOOL_URIS.includes(uri)) toolHashes[uri] = current;
  }
  requireValue(canonicalJson(await treeIdentity(correction.retainedFailure.root)) === canonicalJson(correction.retainedFailure.tree), 'retained v0.1 tree mismatch');
  for (const [uri, expected] of [
    [`${correction.retainedFailure.root}/admission.json`, correction.retainedFailure.admission.sha256],
    [`${correction.retainedFailure.root}/primary.json`, correction.retainedFailure.primary.sha256],
    [`${correction.retainedFailure.root}/independent.json`, correction.retainedFailure.independent.sha256],
    [`${correction.retainedFailure.root}/processes/PRIMARY.json`, correction.retainedFailure.primary.processSha256],
    [`${correction.retainedFailure.root}/processes/INDEPENDENT.json`, correction.retainedFailure.independent.processSha256],
    [`${correction.retainedFailure.root}/processes/AUDITOR.json`, correction.retainedFailure.auditor.processSha256],
    [`${correction.retainedFailure.root}/failure.json`, correction.retainedFailure.failure.sha256],
  ]) requireValue(await sha256File(containedPath(uri)) === expected, `retained v0.1 file mismatch ${uri}`);
  for (const [uri, expected] of Object.entries(correction.frozenBlenderToolHashes)) requireValue(toolHashes[uri] === expected, `frozen Blender tool changed ${uri}`);
  for (const row of [spec.parentEvidence.phase0Receipt, spec.parentEvidence.masterScene, ...spec.parentEvidence.calibrationPngs]) {
    requireValue(await sha256File(containedPath(row.uri)) === row.sha256, `parent evidence drift ${row.uri}`);
  }
  const parentReceipt = JSON.parse(await readFile(containedPath(spec.parentEvidence.phase0Receipt.uri), 'utf8'));
  requireValue(validSelfHash(parentReceipt, 'receiptHash') && parentReceipt.receiptHash === spec.parentEvidence.phase0Receipt.receiptHash, 'parent receipt invalid');
  requireValue(await sha256File(spec.runtime.blender.executable) === spec.runtime.blender.sha256, 'Blender executable identity mismatch');
  const rootPath = containedPath(ROOT_URI);
  requireValue(!await exists(rootPath), `formal root already exists: ${ROOT_URI}`);
  const filesystem = await statfs(repositoryRoot, { bigint: true });
  const availableBefore = filesystem.bavail * filesystem.bsize;
  requireValue(availableBefore - BigInt(spec.processBudget.projectedWriteBytes) >= BigInt(spec.processBudget.minimumFreeReserveBytes), 'disk admission rejected');
  await mkdir(rootPath, { recursive: false, mode: 0o700 });
  await mkdir(resolve(rootPath, 'processes'), { recursive: false, mode: 0o700 });
  const admission = await durableHashed(resolve(rootPath, 'admission.json'), {
    schemaVersion: 'bfs.b62CameraQualityAdmission.v0.1',
    experimentId: spec.experimentId,
    status: 'ACCEPTED',
    formalRoot: ROOT_URI,
    toolFreezeCommit: freeze,
    spec: { uri: SPEC_URI, sha256: await sha256File(specPath) },
    protocol: { uri: PROTOCOL_URI, sha256: await sha256File(protocolPath) },
    correction: { uri: CORRECTION_URI, sha256: await sha256File(correctionPath) },
    correctionProtocol: { uri: CORRECTION_PROTOCOL_URI, sha256: await sha256File(correctionProtocolPath) },
    toolHashes,
    parent: {
      receipt: { uri: spec.parentEvidence.phase0Receipt.uri, sha256: spec.parentEvidence.phase0Receipt.sha256, receiptHash: parentReceipt.receiptHash },
      master: { uri: spec.parentEvidence.masterScene.uri, sha256: spec.parentEvidence.masterScene.sha256 },
    },
    runtime: { node: { executable: process.execPath, version: process.version }, blender: spec.runtime.blender },
    disk: { availableBeforeBytes: Number(availableBefore), projectedWriteBytes: spec.processBudget.projectedWriteBytes, minimumReserveBytes: spec.processBudget.minimumFreeReserveBytes },
  }, 'admissionHash');
  try {
    const masterPath = containedPath(spec.parentEvidence.masterScene.uri);
    const primaryProcess = await runBlenderChild({ rootPath, processId: 'PRIMARY', toolUri: TOOL_URIS[0], outputName: 'primary.json', masterPath, masterSha: spec.parentEvidence.masterScene.sha256, spec });
    const independentProcess = await runBlenderChild({ rootPath, processId: 'INDEPENDENT', toolUri: TOOL_URIS[1], outputName: 'independent.json', masterPath, masterSha: spec.parentEvidence.masterScene.sha256, spec });
    const auditorProcess = await runAuditorChild({ rootPath, freeze, spec });
    const auditPath = resolve(rootPath, 'audit.json');
    const comparisonPath = resolve(rootPath, 'comparison.json');
    const audit = JSON.parse(await readFile(auditPath, 'utf8'));
    const comparison = JSON.parse(await readFile(comparisonPath, 'utf8'));
    requireValue(validSelfHash(audit, 'auditHash') && audit.status === 'PASS' && audit.scientificVerdict, 'final audit invalid');
    requireValue(validSelfHash(comparison, 'comparisonHash') && comparison.status === 'PASS', 'comparison invalid');
    const receipt = await durableHashed(resolve(rootPath, 'receipt.json'), {
      schemaVersion: 'bfs.b62CameraQualityGeometricReceipt.v0.1',
      experimentId: spec.experimentId,
      status: 'PASS',
      scientificVerdict: audit.scientificVerdict,
      admission: { uri: `${ROOT_URI}/admission.json`, sha256: await sha256File(resolve(rootPath, 'admission.json')), admissionHash: admission.admissionHash },
      comparison: { uri: `${ROOT_URI}/comparison.json`, sha256: await sha256File(comparisonPath), comparisonHash: comparison.comparisonHash },
      audit: { uri: `${ROOT_URI}/audit.json`, sha256: await sha256File(auditPath), auditHash: audit.auditHash },
      processes: {
        primary: { uri: `${ROOT_URI}/processes/PRIMARY.json`, sha256: await sha256File(resolve(rootPath, 'processes', 'PRIMARY.json')), processHash: primaryProcess.processHash },
        independent: { uri: `${ROOT_URI}/processes/INDEPENDENT.json`, sha256: await sha256File(resolve(rootPath, 'processes', 'INDEPENDENT.json')), processHash: independentProcess.processHash },
        auditor: { uri: `${ROOT_URI}/processes/AUDITOR.json`, sha256: await sha256File(resolve(rootPath, 'processes', 'AUDITOR.json')), processHash: auditorProcess.processHash },
      },
      operations: { runnerProcesses: 1, blenderStarts: 2, renderCalls: 0, nodeAuditorProcesses: 1, modelCalls: 0, networkCalls: 0, dockerProcesses: 0 },
      nonClaims: spec.nonClaims,
    }, 'receiptHash');
    process.stdout.write(`BFS_B62_Q1 PASS ${receipt.scientificVerdict} ${receipt.receiptHash}\n`);
    return receipt;
  } catch (error) {
    if (!await exists(resolve(rootPath, 'failure.json'))) {
      await durableHashed(resolve(rootPath, 'failure.json'), {
        schemaVersion: 'bfs.b62CameraQualityFailure.v0.1',
        experimentId: spec.experimentId,
        status: 'INVALIDATED',
        scientificVerdict: null,
        toolFreezeCommit: freeze,
        reason: error instanceof Error ? error.message : String(error),
      }, 'failureHash');
    }
    throw error;
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  run(process.argv.slice(2)).catch(error => {
    process.stderr.write(`BFS_B62_Q1_ERROR ${error.message}\n`);
    process.exitCode = 1;
  });
}
