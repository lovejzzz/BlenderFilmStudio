#!/usr/bin/env node

import { spawn } from 'node:child_process';
import { lstat, mkdir, readFile, statfs } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { compileBuildPlan } from './compile-build-plan.mjs';
import { runGit } from './lib/formal-run-admission.mjs';
import {
  canonicalJson,
  durableMkdir,
  sha256Bytes,
  sha256File,
  validSelfHash,
  writeDurableHashed,
} from './lib/production-compile-receipt.mjs';
import { repositoryRoot } from './lib/scene-spec.mjs';

const SPEC_URI = 'specs/production-disk-jit-readmission.v0.1.json';
const SPEC_SHA256 = 'fa91173f1e824b8b9f1689d401586100a04e2632817895f6e209ace007833ecf';
const PROTOCOL_URI = 'research/2026-08-28-b57-e1-production-disk-jit-readmission-protocol.md';
const PREREGISTRATION_COMMIT = 'c9e0b9e25c41b751fb456cf115e29e63996dbea4';
const RELEASE_URI = 'specs/production-compiler-entry.v0.2.json';
const B57_TOOLS = [
  'scripts/preflight-b57-e1-production-disk-jit-readmission.mjs',
  'scripts/run-b57-e1-production-disk-jit-readmission.mjs',
  'scripts/audit-b57-e1-production-disk-jit-readmission.mjs',
];
const NODE = '/opt/homebrew/Cellar/node/26.5.0/bin/node';
const NPM = '/opt/homebrew/bin/npm';

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
  for (const key of ['outputRoot', 'attemptRoot', 'formalRoot', 'toolFreezeCommit']) {
    if (!parsed[key]) throw new Error(`Missing --${key.replace(/[A-Z]/g, letter => `-${letter.toLowerCase()}`)}`);
  }
  if (!/^[0-9a-f]{40}$/.test(parsed.toolFreezeCommit)) throw new Error('Tool-freeze commit must be a full lowercase SHA-1');
  return parsed;
}

async function state(path) {
  try { return await lstat(path); } catch (error) {
    if (error?.code === 'ENOENT') return null;
    throw error;
  }
}

async function runChild(command, args, env = {}) {
  const child = spawn(command, args, {
    cwd: repositoryRoot,
    env: { PATH: '/opt/homebrew/bin:/usr/bin:/bin', LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8', ...env },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  const stdout = [];
  const stderr = [];
  child.stdout.on('data', chunk => stdout.push(chunk));
  child.stderr.on('data', chunk => stderr.push(chunk));
  const completion = await new Promise((resolvePromise, reject) => {
    child.on('error', reject);
    child.on('close', (exitCode, signal) => resolvePromise({ exitCode, signal }));
  });
  return { pid: child.pid, ...completion, stdout: Buffer.concat(stdout).toString('utf8'), stderr: Buffer.concat(stderr).toString('utf8') };
}

async function requireToolFreeze(spec, parsed, release) {
  const scoped = [...new Set([SPEC_URI, PROTOCOL_URI, RELEASE_URI, ...Object.keys(release.frozenFiles), ...B57_TOOLS])].sort();
  const head = await runGit(['rev-parse', 'HEAD'], repositoryRoot);
  const origin = await runGit(['rev-parse', '--verify', 'origin/main'], repositoryRoot);
  const ancestor = await runGit(['merge-base', '--is-ancestor', PREREGISTRATION_COMMIT, parsed.toolFreezeCommit], repositoryRoot);
  const dirty = await runGit(['status', '--porcelain=v1', '--untracked-files=all', '--', ...scoped], repositoryRoot);
  const hashes = {};
  const commitHashes = {};
  for (const uri of scoped) {
    hashes[uri] = await sha256File(resolve(repositoryRoot, uri));
    const shown = await runGit(['show', `${parsed.toolFreezeCommit}:${uri}`], repositoryRoot);
    commitHashes[uri] = shown.exitCode === 0 ? sha256Bytes(Buffer.from(shown.stdout)) : null;
  }
  const releaseExact = Object.entries(release.frozenFiles).every(([uri, expected]) => hashes[uri] === expected && commitHashes[uri] === expected);
  return {
    scoped,
    hashes,
    commitHashes,
    releaseExact,
    exact: head.stdout.trim() === parsed.toolFreezeCommit && origin.stdout.trim() === parsed.toolFreezeCommit
      && ancestor.exitCode === 0 && dirty.exitCode === 0 && dirty.stdout === ''
      && scoped.every(uri => hashes[uri] === commitHashes[uri]) && releaseExact
      && hashes[SPEC_URI] === SPEC_SHA256 && spec.experimentId === 'B57-E1',
  };
}

async function readParent(spec) {
  const resultsPath = resolve(repositoryRoot, spec.parentEvidence.results.uri);
  const auditPath = resolve(repositoryRoot, spec.parentEvidence.audit.uri);
  const receiptPath = resolve(repositoryRoot, spec.parentEvidence.receipt.uri);
  const results = JSON.parse(await readFile(resultsPath, 'utf8'));
  const audit = JSON.parse(await readFile(auditPath, 'utf8'));
  const receipt = JSON.parse(await readFile(receiptPath, 'utf8'));
  const exact = await sha256File(resultsPath) === spec.parentEvidence.results.sha256
    && await sha256File(auditPath) === spec.parentEvidence.audit.sha256
    && await sha256File(receiptPath) === spec.parentEvidence.receipt.sha256
    && validSelfHash(results, 'resultHash') && validSelfHash(audit, 'auditHash') && validSelfHash(receipt, 'receiptHash')
    && results.scientificVerdict === spec.parentEvidence.observed.verdict
    && Object.values(results.gates).filter(Boolean).length === 27 && audit.attackSummary.rejected === 64;
  return { exact, results: { sha256: await sha256File(resultsPath), resultHash: results.resultHash }, audit: { sha256: await sha256File(auditPath), auditHash: audit.auditHash }, receipt: { sha256: await sha256File(receiptPath), receiptHash: receipt.receiptHash } };
}

async function sceneSuite() {
  const child = await runChild(NODE, ['scripts/validate-scene-spec.mjs']);
  const rows = child.stdout.split('\n').filter(line => /^(PASS|FAIL) /.test(line));
  return { child: { pid: child.pid, exitCode: child.exitCode, signal: child.signal }, count: rows.length, exact: child.exitCode === 0 && rows.length === 22 && rows.every(row => row.startsWith('PASS ')) };
}

async function planPairs(spec) {
  const rows = [];
  for (const benchmark of spec.formalMatrix.acceptedRuns.filter(id => id.endsWith('-A'))) {
    const id = benchmark.slice(0, 3);
    const sceneSpec = `specs/benchmarks/${id}.scene.json`;
    const first = await compileBuildPlan(sceneSpec);
    const second = await compileBuildPlan(sceneSpec);
    const expected = id === 'B01' ? '316114f10d4ec3a2b9e6b569e39476a143fc1b1db10e1603ba54d37dc73c3eaf' : 'a9022bf6f881b1c8d7b7866813d22454c81f72de9190e05af82c10bf62a26687';
    rows.push({ id, sceneSpec, planHash: first.planHash, exact: canonicalJson(first) === canonicalJson(second) && first.planHash === expected });
  }
  return rows;
}

async function observeDisk(spec) {
  const fs = await statfs(repositoryRoot, { bigint: true });
  const available = fs.bavail * fs.bsize;
  const reserve = BigInt(spec.diskPolicy.minimumReserveBytes);
  const projected = BigInt(spec.diskPolicy.projectedWriteBytes);
  const threshold = reserve + projected;
  const ceiling = BigInt(spec.formalMatrix.forcedStaleCapacityCase.jitEffectiveAvailableBytes);
  return {
    availableBytes: available.toString(),
    freeAfterProjectedBytes: (available - projected).toString(),
    minimumReserveBytes: reserve.toString(),
    projectedWriteBytes: projected.toString(),
    status: available - projected >= reserve ? 'ACCEPTED' : 'REJECTED',
    boundary: { thresholdBytes: threshold.toString(), forcedBytes: ceiling.toString(), exactlyOneByteBelow: ceiling === threshold - 1n, ceilingBelowReal: ceiling <= available },
  };
}

async function createProductionPreflights(parsed) {
  const parent = resolve(repositoryRoot, parsed.outputRoot, 'production-preflights');
  await mkdir(parent);
  const rows = [];
  const cases = [
    { runId: 'LOW-DISK', benchmarkId: 'B01', output: `${parsed.formalRoot}/low-disk` },
    ...['B01-A', 'B01-B', 'B02-A', 'B02-B'].map(runId => ({ runId, benchmarkId: runId.slice(0, 3), output: `${parsed.formalRoot}/runs/${runId}` })),
  ];
  for (const row of cases) {
    const preflightRoot = `${parsed.outputRoot}/production-preflights/${row.runId}`;
    const child = await runChild(NPM, ['run', 'preflight:production', '--', '--scene-spec', `specs/benchmarks/${row.benchmarkId}.scene.json`, '--preflight-root', preflightRoot, '--output-root', row.output, '--release-commit', parsed.toolFreezeCommit]);
    const recordPath = resolve(repositoryRoot, preflightRoot, 'preflight.json');
    const record = JSON.parse(await readFile(recordPath, 'utf8'));
    rows.push({ ...row, preflightRoot, child: { pid: child.pid, exitCode: child.exitCode, signal: child.signal }, status: record.status, preflightHash: record.preflightHash, sha256: await sha256File(recordPath), exact: child.exitCode === 0 && record.status === 'ACCEPTED' && validSelfHash(record, 'preflightHash') && record.output.repositoryRelative === row.output });
  }
  return rows;
}

export async function runB57Preflight(argv) {
  const parsed = parseArguments(argv);
  const roots = [parsed.outputRoot, parsed.attemptRoot, parsed.formalRoot];
  if (new Set(roots).size !== roots.length || roots.some(left => roots.some(right => left !== right && (left.startsWith(`${right}/`) || right.startsWith(`${left}/`))))) throw new Error('B57 roots must be disjoint');
  if ((await Promise.all(roots.map(uri => state(resolve(repositoryRoot, uri))))).some(Boolean)) throw new Error('B57 roots must be fresh and absent');
  const spec = JSON.parse(await readFile(resolve(repositoryRoot, SPEC_URI), 'utf8'));
  if (await sha256File(resolve(repositoryRoot, SPEC_URI)) !== SPEC_SHA256) throw new Error('B57 spec hash mismatch');
  const release = JSON.parse(await readFile(resolve(repositoryRoot, RELEASE_URI), 'utf8'));
  const parent = await readParent(spec);
  const toolFreeze = await requireToolFreeze(spec, parsed, release);
  const suite = await sceneSuite();
  const plans = await planPairs(spec);
  const disk = await observeDisk(spec);
  await durableMkdir(resolve(repositoryRoot, parsed.outputRoot));
  const productionPreflights = await createProductionPreflights(parsed);
  const checks = {
    SPEC_EXACT: await sha256File(resolve(repositoryRoot, SPEC_URI)) === SPEC_SHA256,
    PREREGISTRATION_PUSHED: toolFreeze.exact,
    B56_PARENT_EXACT: parent.exact,
    RELEASE_V0_1_PRESERVED: await sha256File(resolve(repositoryRoot, 'specs/production-compiler-entry.v0.1.json')) === spec.beforeIdentities.releaseManifest.sha256,
    RELEASE_V0_2_AND_TOOLS_FROZEN: toolFreeze.exact && toolFreeze.releaseExact,
    PACKAGE_ALIASES_UNCHANGED: JSON.stringify(release.packageAliases) === JSON.stringify({ 'preflight:production': 'node scripts/preflight-production-blender-compile.mjs', 'compile:production': 'node scripts/run-production-blender-compile.mjs', 'verify:production-receipt': 'node scripts/verify-production-compile-receipt.mjs' }),
    SCENESPEC_22_OF_22: suite.exact,
    B01_B02_BUILDPLAN_PAIRS: plans.length === 2 && plans.every(row => row.exact),
    REAL_DISK_ADMITTED: disk.status === 'ACCEPTED',
    ONE_BYTE_BOUNDARY_EXACT: disk.boundary.exactlyOneByteBelow && disk.boundary.ceilingBelowReal,
    FIVE_PRODUCTION_PREFLIGHTS_ACCEPTED: productionPreflights.length === 5 && productionPreflights.every(row => row.exact),
    BLENDER_AND_RENDER_ZERO: true,
  };
  const passed = Object.values(checks).filter(Boolean).length;
  const body = {
    schemaVersion: 'bfs.productionDiskJitReadmissionPreflight.v0.1',
    experimentId: 'B57-E1',
    status: passed === Object.keys(checks).length ? 'ACCEPTED' : 'REJECTED',
    reason: passed === Object.keys(checks).length ? null : 'CHECK_FAILURE',
    invocation: parsed,
    specSha256: SPEC_SHA256,
    preregistrationCommit: PREREGISTRATION_COMMIT,
    parent,
    toolFreeze,
    suite,
    plans,
    disk,
    productionPreflights,
    checks,
    checkPassed: passed,
    checkTotal: Object.keys(checks).length,
    operations: { productionPreflightProcesses: 5, blenderProcesses: 0, renderCalls: 0, modelCalls: 0, networkCalls: 0, dockerProcesses: 0 },
    scientificVerdict: null,
  };
  const record = await writeDurableHashed(resolve(repositoryRoot, parsed.outputRoot, 'preflight.json'), body, 'preflightHash');
  process.stdout.write(`BFS_B57_PREFLIGHT ${record.status} ${passed}/${Object.keys(checks).length} ${record.preflightHash}\n`);
  if (record.status !== 'ACCEPTED') process.exitCode = 1;
  return record;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  runB57Preflight(process.argv.slice(2)).catch(error => {
    process.stderr.write(`BFS_B57_PREFLIGHT_ERROR ${error.message}\n`);
    process.exitCode = 1;
  });
}
