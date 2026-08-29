#!/usr/bin/env node

import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { lstat, readFile, statfs } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { compileBuildPlan } from './compile-build-plan.mjs';
import { runGit } from './lib/formal-run-admission.mjs';
import {
  canonicalJson,
  durableMkdir,
  sha256File,
  validSelfHash,
  writeExclusiveDurableHashed,
} from './lib/restart-safe-job-ledger.mjs';
import { repositoryRoot } from './lib/scene-spec.mjs';

const SPEC_URI = 'specs/restart-safe-production-orchestrator.v0.1.json';
const SPEC_SHA256 = 'a1ea52598d66263989c56f9737917b7ff297122b6731ec31d6f535cacc32cf41';
const PROTOCOL_URI = 'research/2026-08-28-b58-e1-restart-safe-production-orchestrator-protocol.md';
const PROTOCOL_SHA256 = '50c3d8f8e61ea894e4dadf0d1f2a2ff92e793de56bacfe1f2d01d48951d35f81';
const CORRECTION_URI = 'specs/restart-safe-production-orchestrator-verifier-accounting-correction.v0.1.json';
const CORRECTION_SHA256 = '1a8f17bda34e7d1f7c683b742e93a2f32d1b9c3a1651388c68efddf566f9c3cd';
const CORRECTION_PROTOCOL_URI = 'research/2026-08-28-b58-e1-c1-verifier-process-accounting-correction.md';
const CORRECTION_PROTOCOL_SHA256 = 'e297c5b2396aac39409fc0eeb8185d2d19deace0ebf10bfb347aa6091aff7b34';
const GATE0_CORRECTION_URI = 'specs/restart-safe-production-orchestrator-gate0-binding-correction.v0.1.json';
const GATE0_CORRECTION_SHA256 = '180eff8d30e2b6ca8cdf0f71f1434ec2b3fe9279cdf539043ebe2f988c3a0785';
const GATE0_CORRECTION_PROTOCOL_URI = 'research/2026-08-29-b58-e1-c2-gate0-binding-correction.md';
const GATE0_CORRECTION_PROTOCOL_SHA256 = 'bd50f4e34017a6ddfefd9ae4c7262cc446ed8715ebb19f1c3c75c8995e34e837';
const ENTRY_CORRECTION_URI = 'specs/restart-safe-production-orchestrator-entry-correction.v0.1.json';
const ENTRY_CORRECTION_SHA256 = '97cfb3c9b01fe6b06173d77bbab65a41ec974015836c61fd1cde762a80cd137e';
const ENTRY_CORRECTION_PROTOCOL_URI = 'research/2026-08-29-b58-e1-c3-entry-correction.md';
const ENTRY_CORRECTION_PROTOCOL_SHA256 = 'b5dfe47a7e8999b3d468dc0a22cec98897b01925f0a5c6463a4f574a1fb43d07';
const NESTED_CORRECTION_URI = 'specs/restart-safe-production-orchestrator-nested-preflight-correction.v0.1.json';
const NESTED_CORRECTION_SHA256 = 'a2e5422adf7603cb0a6d25ca2dc06e2eb9115a633c3ecf3d90a9be1f390ed022';
const NESTED_CORRECTION_PROTOCOL_URI = 'research/2026-08-29-b58-e1-c4-nested-preflight-correction.md';
const NESTED_CORRECTION_PROTOCOL_SHA256 = '1eac0841e060858589e99e70527d237e4b2ce8c4fbcbd6caf6235971960f84f1';
const RELEASE_URI = 'specs/production-compiler-entry.v0.2.json';
const PREREGISTRATION_COMMIT = '9fe37d7c8b3d2e6b3ea522ba9c2e4515a100d99b';
const CORRECTION_COMMIT = 'fc01f6fb74d3ad0517d27b2639e1bc057a3d44cb';
const GATE0_CORRECTION_COMMIT = '6dba91af525351b64c2147a63bf1681569ed9e29';
const ENTRY_CORRECTION_COMMIT = 'fd808bffd0a02109dff349d9d821d9ec0ad4df3d';
const NESTED_CORRECTION_COMMIT = 'cc808b45cacd50e415c957c6a40694e07f0151dc';
const NODE = '/opt/homebrew/Cellar/node/26.5.0/bin/node';
const NPM = '/opt/homebrew/bin/npm';
const JOB_TOOL_PATHS = [
  'scripts/lib/restart-safe-job-ledger.mjs',
  'scripts/run-restart-safe-production-job.mjs',
];
const FORMAL_TOOL_PATHS = [
  ...JOB_TOOL_PATHS,
  'scripts/preflight-b58-e1-restart-safe-production-orchestrator.mjs',
  'scripts/run-b58-e1-restart-safe-production-orchestrator.mjs',
  'scripts/audit-b58-e1-restart-safe-production-orchestrator.mjs',
];
const STAGE_DAG = [
  { id: 'PLAN_BIND', dependsOn: [] },
  { id: 'PRODUCTION_COMPILE', dependsOn: ['PLAN_BIND'] },
  { id: 'VERIFY_RECEIPT', dependsOn: ['PRODUCTION_COMPILE'] },
  { id: 'FINALIZE', dependsOn: ['VERIFY_RECEIPT'] },
];
const SCENES = {
  B01: {
    uri: 'specs/benchmarks/B01.scene.json',
    sha256: '1e3192aff070ac244f89b2cef96078e0d88c93a0d043e679e45f210f8d3cfde4',
    planHash: '316114f10d4ec3a2b9e6b569e39476a143fc1b1db10e1603ba54d37dc73c3eaf',
  },
  B02: {
    uri: 'specs/benchmarks/B02.scene.json',
    sha256: '774415a396bec91598ea8fac407443f04b6a630bdee046b15a14fae5fcad6c16',
    planHash: 'a9022bf6f881b1c8d7b7866813d22454c81f72de9190e05af82c10bf62a26687',
  },
};

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

async function pathState(absolutePath) {
  try { return await lstat(absolutePath); } catch (error) {
    if (error?.code === 'ENOENT') return null;
    throw error;
  }
}

function rootsOverlap(left, right) {
  return left === right || left.startsWith(`${right}/`) || right.startsWith(`${left}/`);
}

async function runChild(command, args) {
  const child = spawn(command, args, {
    cwd: repositoryRoot,
    env: { PATH: '/opt/homebrew/bin:/usr/bin:/bin', LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8' },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  const stdout = [];
  const stderr = [];
  child.stdout.on('data', chunk => stdout.push(chunk));
  child.stderr.on('data', chunk => stderr.push(chunk));
  const terminal = await new Promise((resolvePromise, reject) => {
    child.on('error', reject);
    child.on('close', (exitCode, signal) => resolvePromise({ exitCode, signal }));
  });
  return { pid: child.pid, ...terminal, stdout: Buffer.concat(stdout).toString('utf8'), stderr: Buffer.concat(stderr).toString('utf8') };
}

async function hashGitBlob(commit, uri) {
  const shown = await runGit(['show', `${commit}:${uri}`], repositoryRoot);
  return shown.exitCode === 0 ? createHash('sha256').update(Buffer.from(shown.stdout)).digest('hex') : null;
}

async function requireToolFreeze(parsed, release) {
  const scoped = [...new Set([
    SPEC_URI, PROTOCOL_URI, CORRECTION_URI, CORRECTION_PROTOCOL_URI, GATE0_CORRECTION_URI, GATE0_CORRECTION_PROTOCOL_URI, ENTRY_CORRECTION_URI, ENTRY_CORRECTION_PROTOCOL_URI, NESTED_CORRECTION_URI, NESTED_CORRECTION_PROTOCOL_URI, RELEASE_URI,
    'package.json', ...Object.keys(release.frozenFiles), ...FORMAL_TOOL_PATHS,
  ])].sort();
  const head = await runGit(['rev-parse', 'HEAD'], repositoryRoot);
  const origin = await runGit(['rev-parse', '--verify', 'origin/main'], repositoryRoot);
  const preregAncestor = await runGit(['merge-base', '--is-ancestor', PREREGISTRATION_COMMIT, parsed.toolFreezeCommit], repositoryRoot);
  const correctionAncestor = await runGit(['merge-base', '--is-ancestor', CORRECTION_COMMIT, parsed.toolFreezeCommit], repositoryRoot);
  const gate0CorrectionAncestor = await runGit(['merge-base', '--is-ancestor', GATE0_CORRECTION_COMMIT, parsed.toolFreezeCommit], repositoryRoot);
  const entryCorrectionAncestor = await runGit(['merge-base', '--is-ancestor', ENTRY_CORRECTION_COMMIT, parsed.toolFreezeCommit], repositoryRoot);
  const nestedCorrectionAncestor = await runGit(['merge-base', '--is-ancestor', NESTED_CORRECTION_COMMIT, parsed.toolFreezeCommit], repositoryRoot);
  const dirty = await runGit(['status', '--porcelain=v1', '--untracked-files=all', '--', ...scoped], repositoryRoot);
  const hashes = {};
  const commitHashes = {};
  for (const uri of scoped) {
    hashes[uri] = await sha256File(resolve(repositoryRoot, uri));
    commitHashes[uri] = await hashGitBlob(parsed.toolFreezeCommit, uri);
  }
  const releaseExact = Object.entries(release.frozenFiles).every(([uri, expected]) => hashes[uri] === expected && commitHashes[uri] === expected);
  const exact = head.stdout.trim() === parsed.toolFreezeCommit && origin.stdout.trim() === parsed.toolFreezeCommit
    && preregAncestor.exitCode === 0 && correctionAncestor.exitCode === 0 && gate0CorrectionAncestor.exitCode === 0 && entryCorrectionAncestor.exitCode === 0 && nestedCorrectionAncestor.exitCode === 0 && dirty.exitCode === 0 && dirty.stdout === ''
    && scoped.every(uri => hashes[uri] === commitHashes[uri]) && releaseExact
    && hashes[SPEC_URI] === SPEC_SHA256 && hashes[PROTOCOL_URI] === PROTOCOL_SHA256
    && hashes[CORRECTION_URI] === CORRECTION_SHA256 && hashes[CORRECTION_PROTOCOL_URI] === CORRECTION_PROTOCOL_SHA256
    && hashes[GATE0_CORRECTION_URI] === GATE0_CORRECTION_SHA256 && hashes[GATE0_CORRECTION_PROTOCOL_URI] === GATE0_CORRECTION_PROTOCOL_SHA256
    && hashes[ENTRY_CORRECTION_URI] === ENTRY_CORRECTION_SHA256 && hashes[ENTRY_CORRECTION_PROTOCOL_URI] === ENTRY_CORRECTION_PROTOCOL_SHA256
    && hashes[NESTED_CORRECTION_URI] === NESTED_CORRECTION_SHA256 && hashes[NESTED_CORRECTION_PROTOCOL_URI] === NESTED_CORRECTION_PROTOCOL_SHA256;
  return { scoped, hashes, commitHashes, releaseExact, exact };
}

async function readGate0(correction) {
  const resultPath = resolve(repositoryRoot, correction.gate0.results[0]);
  const auditPath = resolve(repositoryRoot, correction.gate0.audit[0]);
  const historyPath = correction.gate0.liveSentinel.historyPath;
  const latestPath = correction.gate0.liveSentinel.latestPath;
  const [resultsText, auditText, historyText, latestText] = await Promise.all([
    readFile(resultPath, 'utf8'), readFile(auditPath, 'utf8'), readFile(historyPath, 'utf8'), readFile(latestPath, 'utf8'),
  ]);
  const results = JSON.parse(resultsText);
  const audit = JSON.parse(auditText);
  const history = JSON.parse(historyText);
  const latest = JSON.parse(latestText);
  const ageMs = Date.now() - Date.parse(latest.sample?.capturedAt);
  const alertAbsent = await pathState(correction.gate0.liveSentinel.alertPath) === null;
  const evidenceExact = createHash('sha256').update(resultsText).digest('hex') === correction.gate0.results[1]
    && createHash('sha256').update(auditText).digest('hex') === correction.gate0.audit[1]
    && validSelfHash(results, 'selfHash') && validSelfHash(audit, 'selfHash')
    && audit.finalVerdict === correction.gate0.requiredVerdict && audit.passedGates === correction.gate0.requiredGates
    && audit.totalGates === correction.gate0.requiredGates && audit.attacksPassed === correction.gate0.requiredAttacks
    && audit.attacksTotal === correction.gate0.requiredAttacks && audit.failedGates.length === 0;
  const liveExact = validSelfHash(history, 'selfHash') && validSelfHash(latest, 'selfHash') && history.samples.every(row => validSelfHash(row, 'selfHash'))
    && latest.sample?.selfHash === history.samples.at(-1)?.selfHash && ageMs >= 0 && ageMs <= correction.gate0.liveSentinel.maximumAgeSeconds * 1000
    && latest.classification?.severity === 'HEALTHY' && latest.sample.availableBytes >= correction.gate0.liveSentinel.minimumAvailableBytes
    && latest.sample.browserTempFilesystem.allocatedBytes < correction.gate0.liveSentinel.maximumBrowserBytes && alertAbsent;
  return {
    exact: evidenceExact && liveExact,
    evidenceCommit: correction.gate0.evidenceCommit,
    results: { uri: correction.gate0.results[0], sha256: createHash('sha256').update(resultsText).digest('hex'), selfHash: results.selfHash },
    audit: { uri: correction.gate0.audit[0], sha256: createHash('sha256').update(auditText).digest('hex'), selfHash: audit.selfHash, verdict: audit.finalVerdict, gates: `${audit.passedGates}/${audit.totalGates}`, attacks: `${audit.attacksPassed}/${audit.attacksTotal}` },
    live: { sampleCount: history.samples.length, latestAgeMs: ageMs, severity: latest.classification?.severity, availableBytes: latest.sample.availableBytes, browserBytes: latest.sample.browserTempFilesystem.allocatedBytes, alertAbsent, exact: liveExact },
  };
}

async function readParent(spec) {
  const rows = {};
  for (const key of ['results', 'audit', 'receipt']) {
    const reference = spec.parent[key];
    const absolutePath = resolve(repositoryRoot, reference.uri);
    const value = JSON.parse(await readFile(absolutePath, 'utf8'));
    rows[key] = { uri: reference.uri, sha256: await sha256File(absolutePath), value };
  }
  const exact = rows.results.sha256 === spec.parent.results.sha256
    && rows.audit.sha256 === spec.parent.audit.sha256
    && rows.receipt.sha256 === spec.parent.receipt.sha256
    && rows.results.value.scientificVerdict === spec.parent.verdict
    && rows.audit.value.scientificVerdict === spec.parent.verdict
    && rows.receipt.value.scientificVerdict === spec.parent.verdict
    && validSelfHash(rows.results.value, 'resultHash') && validSelfHash(rows.audit.value, 'auditHash')
    && validSelfHash(rows.receipt.value, 'receiptHash') && rows.receipt.value.receiptHash === spec.parent.receipt.receiptHash;
  return {
    exact,
    results: { uri: rows.results.uri, sha256: rows.results.sha256, resultHash: rows.results.value.resultHash },
    audit: { uri: rows.audit.uri, sha256: rows.audit.sha256, auditHash: rows.audit.value.auditHash },
    receipt: { uri: rows.receipt.uri, sha256: rows.receipt.sha256, receiptHash: rows.receipt.value.receiptHash },
  };
}

async function sceneSuite() {
  const child = await runChild(NODE, ['scripts/validate-scene-spec.mjs']);
  const rows = child.stdout.split('\n').filter(line => /^(PASS|FAIL) /.test(line));
  return { child: { pid: child.pid, exitCode: child.exitCode, signal: child.signal }, count: rows.length, exact: child.exitCode === 0 && rows.length === 22 && rows.every(row => row.startsWith('PASS ')) };
}

async function planPairs() {
  const rows = [];
  for (const [benchmarkId, scene] of Object.entries(SCENES)) {
    const first = await compileBuildPlan(scene.uri);
    const second = await compileBuildPlan(scene.uri);
    rows.push({ benchmarkId, sceneSpec: scene.uri, planHash: first.planHash, exact: canonicalJson(first) === canonicalJson(second) && first.planHash === scene.planHash });
  }
  return rows;
}

async function observeDisk() {
  const filesystem = await statfs(repositoryRoot, { bigint: true });
  const available = filesystem.bavail * filesystem.bsize;
  const projected = 536870912n;
  const reserve = 107374182400n;
  return {
    availableBytes: available.toString(),
    projectedWriteBytes: projected.toString(),
    freeAfterProjectedBytes: (available - projected).toString(),
    minimumReserveBytes: reserve.toString(),
    status: available - projected >= reserve ? 'ACCEPTED' : 'REJECTED',
  };
}

function formalCases(parsed) {
  return [
    { id: 'BASELINE_B01', benchmarkId: 'B01', preflightRoot: `${parsed.outputRoot}/production-preflights/BASELINE_B01`, productionAttemptRoot: `${parsed.attemptRoot}/production-attempts/BASELINE_B01`, outputRoot: `${parsed.formalRoot}/outputs/BASELINE_B01` },
    { id: 'EXIT86_B01', benchmarkId: 'B01', preflightRoot: `${parsed.outputRoot}/production-preflights/EXIT86_B01`, productionAttemptRoot: `${parsed.attemptRoot}/production-attempts/EXIT86_B01`, outputRoot: `${parsed.formalRoot}/outputs/EXIT86_B01` },
    { id: 'INTERRUPTED_B02_1', benchmarkId: 'B02', preflightRoot: `${parsed.outputRoot}/production-preflights/INTERRUPTED_B02_1`, productionAttemptRoot: `${parsed.attemptRoot}/production-attempts/INTERRUPTED_B02_1`, outputRoot: `${parsed.formalRoot}/outputs/INTERRUPTED_B02_1` },
    { id: 'INTERRUPTED_B02_2', benchmarkId: 'B02', preflightRoot: `${parsed.outputRoot}/production-preflights/INTERRUPTED_B02_2`, productionAttemptRoot: `${parsed.attemptRoot}/production-attempts/INTERRUPTED_B02_2`, outputRoot: `${parsed.formalRoot}/outputs/INTERRUPTED_B02_2` },
    { id: 'LIVE_B01', benchmarkId: 'B01', preflightRoot: `${parsed.outputRoot}/production-preflights/LIVE_B01`, productionAttemptRoot: `${parsed.attemptRoot}/production-attempts/LIVE_B01`, outputRoot: `${parsed.formalRoot}/outputs/LIVE_B01` },
  ];
}

async function createProductionPreflights(parsed, cases) {
  const rows = [];
  for (const row of cases) {
    const scene = SCENES[row.benchmarkId];
    const child = await runChild(NPM, ['run', 'preflight:production', '--', '--scene-spec', scene.uri, '--preflight-root', row.preflightRoot, '--output-root', row.outputRoot, '--release-commit', parsed.toolFreezeCommit]);
    const absolutePath = resolve(repositoryRoot, row.preflightRoot, 'preflight.json');
    if (child.exitCode !== 0 || !(await pathState(absolutePath))) {
      const diagnostic = JSON.stringify({ caseId: row.id, exitCode: child.exitCode, signal: child.signal, stdout: child.stdout.slice(0, 4096), stderr: child.stderr.slice(0, 4096) });
      throw new Error(`Production preflight child failed before an accepted receipt: ${diagnostic}`);
    }
    const record = JSON.parse(await readFile(absolutePath, 'utf8'));
    rows.push({
      ...row,
      child: { pid: child.pid, exitCode: child.exitCode, signal: child.signal },
      status: record.status,
      sha256: await sha256File(absolutePath),
      preflightHash: record.preflightHash,
      exact: child.exitCode === 0 && record.status === 'ACCEPTED' && validSelfHash(record, 'preflightHash')
        && record.invocation.sceneSpec === scene.uri && record.invocation.preflightRoot === row.preflightRoot
        && record.invocation.outputRoot === row.outputRoot && record.buildPlan.planHash === scene.planHash,
    });
  }
  return rows;
}

async function writeRequest(parsed, toolFreeze, caseMap, body) {
  const scene = SCENES[body.benchmarkId];
  const requestPath = resolve(repositoryRoot, parsed.outputRoot, 'job-requests', `${body.jobId}.json`);
  const compileAttempts = body.attempts.map(({ caseId, attemptId, fault }) => {
    const row = caseMap.get(caseId);
    return { attemptId, preflightRoot: row.preflightRoot, productionAttemptRoot: row.productionAttemptRoot, outputRoot: row.outputRoot, fault };
  });
  const { record } = await writeExclusiveDurableHashed(requestPath, {
    schemaVersion: 'bfs.restartSafeProductionJobRequest.v0.1',
    jobId: body.jobId,
    jobRoot: `${parsed.formalRoot}/jobs/${body.jobId}`,
    sceneSpec: { uri: scene.uri, sha256: scene.sha256 },
    expectedBuildPlanHash: scene.planHash,
    productionRelease: { uri: RELEASE_URI, sha256: toolFreeze.hashes[RELEASE_URI] },
    toolFreezeCommit: parsed.toolFreezeCommit,
    toolHashes: Object.fromEntries(JOB_TOOL_PATHS.map(uri => [uri, toolFreeze.hashes[uri]])),
    stageDag: STAGE_DAG,
    compileAttempts,
    orchestratorFault: body.orchestratorFault,
    resourcePolicy: { minimumReserveBytes: '107374182400', projectedWriteBytes: '536870912', overrideAllowed: false },
  }, 'requestHash');
  return { id: body.id, jobId: body.jobId, jobRoot: record.jobRoot, uri: `${parsed.outputRoot}/job-requests/${body.jobId}.json`, sha256: await sha256File(requestPath), requestHash: record.requestHash };
}

async function createJobRequests(parsed, toolFreeze, cases) {
  await durableMkdir(resolve(repositoryRoot, parsed.outputRoot, 'job-requests'));
  const caseMap = new Map(cases.map(row => [row.id, row]));
  const definitions = [
    { id: 'BASELINE_B01', jobId: 'B58-FORMAL-BASELINE-B01', benchmarkId: 'B01', orchestratorFault: null, attempts: [{ caseId: 'BASELINE_B01', attemptId: 'BASELINE-COMPILE-0001', fault: null }] },
    { id: 'ORCHESTRATOR_EXIT_AFTER_COMPILE_B01', jobId: 'B58-FORMAL-EXIT86-B01', benchmarkId: 'B01', orchestratorFault: 'EXIT_AFTER_PRODUCTION_COMPILE', attempts: [{ caseId: 'EXIT86_B01', attemptId: 'EXIT86-COMPILE-0001', fault: null }] },
    { id: 'BLENDER_INTERRUPTED_B02', jobId: 'B58-FORMAL-INTERRUPTED-B02', benchmarkId: 'B02', orchestratorFault: null, attempts: [{ caseId: 'INTERRUPTED_B02_1', attemptId: 'INTERRUPTED-COMPILE-0001', fault: 'INTERRUPT_NATIVE_AFTER_OBSERVED' }, { caseId: 'INTERRUPTED_B02_2', attemptId: 'RETRY-COMPILE-0002', fault: null }] },
    { id: 'LIVE_PROCESS_REFUSAL', jobId: 'B58-FORMAL-LIVE-B01', benchmarkId: 'B01', orchestratorFault: null, attempts: [{ caseId: 'LIVE_B01', attemptId: 'LIVE-COMPILE-0001', fault: null }] },
  ];
  const requests = [];
  for (const definition of definitions) requests.push(await writeRequest(parsed, toolFreeze, caseMap, definition));
  return requests;
}

export async function runB58Preflight(argv) {
  const parsed = parseArguments(argv);
  const roots = [parsed.outputRoot, parsed.attemptRoot, parsed.formalRoot];
  if (roots.some((left, index) => roots.some((right, other) => index !== other && rootsOverlap(left, right)))) throw new Error('B58 roots must be disjoint');
  if ((await Promise.all(roots.map(uri => pathState(resolve(repositoryRoot, uri))))).some(Boolean)) throw new Error('B58 roots must be fresh and absent');
  const spec = JSON.parse(await readFile(resolve(repositoryRoot, SPEC_URI), 'utf8'));
  const correction = JSON.parse(await readFile(resolve(repositoryRoot, CORRECTION_URI), 'utf8'));
  const gate0Correction = JSON.parse(await readFile(resolve(repositoryRoot, GATE0_CORRECTION_URI), 'utf8'));
  const entryCorrection = JSON.parse(await readFile(resolve(repositoryRoot, ENTRY_CORRECTION_URI), 'utf8'));
  const nestedCorrection = JSON.parse(await readFile(resolve(repositoryRoot, NESTED_CORRECTION_URI), 'utf8'));
  const packageRecord = JSON.parse(await readFile(resolve(repositoryRoot, 'package.json'), 'utf8'));
  const release = JSON.parse(await readFile(resolve(repositoryRoot, RELEASE_URI), 'utf8'));
  const parent = await readParent(spec);
  const toolFreeze = await requireToolFreeze(parsed, release);
  const gate0 = await readGate0(gate0Correction);
  if (!gate0.exact) throw new Error('Gate 0 closeout or live sentinel binding is not exact');
  const suite = await sceneSuite();
  const plans = await planPairs();
  const disk = await observeDisk();
  await durableMkdir(resolve(repositoryRoot, parsed.outputRoot, 'production-preflights'));
  const cases = formalCases(parsed);
  const productionPreflights = await createProductionPreflights(parsed, cases);
  const jobRequests = await createJobRequests(parsed, toolFreeze, cases);
  const checks = {
    SPEC_AND_CORRECTION_EXACT: await sha256File(resolve(repositoryRoot, SPEC_URI)) === SPEC_SHA256
      && await sha256File(resolve(repositoryRoot, CORRECTION_URI)) === CORRECTION_SHA256,
    PROTOCOLS_EXACT: await sha256File(resolve(repositoryRoot, PROTOCOL_URI)) === PROTOCOL_SHA256
      && await sha256File(resolve(repositoryRoot, CORRECTION_PROTOCOL_URI)) === CORRECTION_PROTOCOL_SHA256
      && await sha256File(resolve(repositoryRoot, GATE0_CORRECTION_PROTOCOL_URI)) === GATE0_CORRECTION_PROTOCOL_SHA256
      && await sha256File(resolve(repositoryRoot, ENTRY_CORRECTION_PROTOCOL_URI)) === ENTRY_CORRECTION_PROTOCOL_SHA256
      && await sha256File(resolve(repositoryRoot, NESTED_CORRECTION_PROTOCOL_URI)) === NESTED_CORRECTION_PROTOCOL_SHA256,
    GATE0_CORRECTION_AND_CLOSEOUT_EXACT: await sha256File(resolve(repositoryRoot, GATE0_CORRECTION_URI)) === GATE0_CORRECTION_SHA256 && gate0.exact,
    RESTART_SAFE_DIRECT_ENTRY_AND_B57_PACKAGE_EXACT: await sha256File(resolve(repositoryRoot, ENTRY_CORRECTION_URI)) === ENTRY_CORRECTION_SHA256
      && spec.candidateProductionEntry.command === entryCorrection.authorizedCorrection.effectiveProductionEntry
      && toolFreeze.hashes['package.json'] === release.frozenFiles['package.json'] && packageRecord.scripts?.['job:production'] === undefined,
    NESTED_PREFLIGHT_PARENT_AND_FAILURE_PROPAGATION_EXACT: await sha256File(resolve(repositoryRoot, NESTED_CORRECTION_URI)) === NESTED_CORRECTION_SHA256
      && nestedCorrection.authorizedCorrection.prepareExactParent === '<b58-preflight-root>/production-preflights'
      && productionPreflights.every(row => row.preflightRoot.startsWith(`${parsed.outputRoot}/production-preflights/`)),
    PREREGISTRATIONS_PUSHED: toolFreeze.exact,
    B57_PARENT_EXACT: parent.exact,
    PRODUCTION_RELEASE_AND_TOOLS_FROZEN: toolFreeze.exact && toolFreeze.releaseExact,
    FORMAL_ROOTS_FRESH_AND_DISJOINT: true,
    SCENESPEC_22_OF_22: suite.exact,
    B01_B02_BUILDPLAN_PAIRS: plans.length === 2 && plans.every(row => row.exact),
    REAL_DISK_ADMITTED: disk.status === 'ACCEPTED',
    FIVE_PRODUCTION_PREFLIGHTS_ACCEPTED: productionPreflights.length === 5 && productionPreflights.every(row => row.exact),
    FOUR_JOB_REQUESTS_SELF_HASHED: jobRequests.length === 4 && jobRequests.every(row => /^[0-9a-f]{64}$/.test(row.requestHash)),
    EFFECTIVE_PROCESS_ACCOUNTING_FROZEN: correction.authorizedCorrection.effectiveOperationCeilings.totalBlenderStarts === 7,
    BLENDER_RENDER_MODEL_NETWORK_DOCKER_ZERO: true,
  };
  const passed = Object.values(checks).filter(Boolean).length;
  const { record } = await writeExclusiveDurableHashed(resolve(repositoryRoot, parsed.outputRoot, 'preflight.json'), {
    schemaVersion: 'bfs.restartSafeProductionOrchestratorPreflight.v0.1',
    experimentId: 'B58-E1',
    status: passed === Object.keys(checks).length ? 'ACCEPTED' : 'REJECTED',
    reason: passed === Object.keys(checks).length ? null : 'CHECK_FAILURE',
    invocation: parsed,
    spec: { uri: SPEC_URI, sha256: SPEC_SHA256 },
    correction: { uri: CORRECTION_URI, sha256: CORRECTION_SHA256 },
    gate0Correction: { uri: GATE0_CORRECTION_URI, sha256: GATE0_CORRECTION_SHA256 },
    entryCorrection: { uri: ENTRY_CORRECTION_URI, sha256: ENTRY_CORRECTION_SHA256, effectiveProductionEntry: entryCorrection.authorizedCorrection.effectiveProductionEntry },
    nestedPreflightCorrection: { uri: NESTED_CORRECTION_URI, sha256: NESTED_CORRECTION_SHA256, parent: `${parsed.outputRoot}/production-preflights`, childFailurePolicy: 'STOP_BEFORE_RECEIPT_READ' },
    gate0,
    preregistrationCommit: PREREGISTRATION_COMMIT,
    correctionCommit: CORRECTION_COMMIT,
    gate0CorrectionCommit: GATE0_CORRECTION_COMMIT,
    entryCorrectionCommit: ENTRY_CORRECTION_COMMIT,
    nestedPreflightCorrectionCommit: NESTED_CORRECTION_COMMIT,
    parent,
    toolFreeze,
    toolHashes: toolFreeze.hashes,
    suite,
    plans,
    disk,
    productionPreflights,
    jobRequests,
    checks,
    checkPassed: passed,
    checkTotal: Object.keys(checks).length,
    operations: { productionPreflightProcesses: 5, blenderProcesses: 0, renderCalls: 0, modelCalls: 0, networkCalls: 0, dockerProcesses: 0 },
    scientificVerdict: null,
  }, 'preflightHash');
  process.stdout.write(`BFS_B58_PREFLIGHT ${record.status} ${passed}/${Object.keys(checks).length} ${record.preflightHash}\n`);
  if (record.status !== 'ACCEPTED') process.exitCode = 1;
  return record;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  runB58Preflight(process.argv.slice(2)).catch(error => {
    process.stderr.write(`BFS_B58_PREFLIGHT_ERROR ${error.message}\n`);
    process.exitCode = 1;
  });
}
