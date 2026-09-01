import { spawn } from 'node:child_process';
import { mkdir, readFile, writeFile, lstat, statfs, readdir } from 'node:fs/promises';
import { resolve, isAbsolute } from 'node:path';
import { canonicalize, canonicalJson, repositoryRoot, sha256 } from './lib/scene-spec.mjs';

const FREEZE_URI = 'specs/ai-native-studio-film-language-typed-executor-tool-freeze.v0.1.json';
const CONTEXT_URI = 'specs/fixtures/visual-review/PC4_VX2.execution-context.v0.1.json';
const EXECUTOR_URI = 'scripts/execute-film-language-plan-v2.py';
const REOPEN_URI = 'scripts/audit-film-language-plan-v2-reopen.py';

function requireCondition(condition, message) { if (!condition) throw new Error(message); }
function safeRepositoryPath(uri) {
  requireCondition(typeof uri === 'string' && !isAbsolute(uri) && !uri.split('/').includes('..'), `unsafe repository uri ${uri}`);
  const path = resolve(repositoryRoot, uri);
  requireCondition(path.startsWith(`${repositoryRoot}/`), `outside repository ${uri}`);
  return path;
}
async function sha256File(path) { return sha256(await readFile(path)); }
function selfHash(value, key) { const copy = structuredClone(value); delete copy[key]; return sha256(canonicalJson(copy)); }
async function assertAbsent(path, label) { try { await lstat(path); throw new Error(`${label} already exists`); } catch (error) { if (error.code !== 'ENOENT') throw error; } }
function runTimed(command, args) {
  return new Promise((resolveRun, reject) => {
    const started = process.hrtime.bigint();
    const child = spawn('/usr/bin/time', ['-l', command, ...args], { cwd: repositoryRoot, env: { ...process.env, LC_ALL: 'C' }, stdio: ['ignore', 'pipe', 'pipe'] });
    const stdout = [], stderr = [];
    child.stdout.on('data', value => stdout.push(value)); child.stderr.on('data', value => stderr.push(value)); child.on('error', reject);
    child.on('close', (code, signal) => {
      const stderrText = Buffer.concat(stderr).toString('utf8');
      const match = stderrText.match(/\n\s*(\d+)\s+maximum resident set size/);
      resolveRun({ code, signal, wallSeconds: Number(process.hrtime.bigint() - started) / 1e9, peakRssBytes: match ? Number(match[1]) : null, stdout: Buffer.concat(stdout).toString('utf8'), stderr: stderrText, argv: [command, ...args] });
    });
  });
}
async function treeBytes(path) { const stat = await lstat(path); if (stat.isFile()) return stat.size; if (!stat.isDirectory()) return 0; let total = 0; for (const entry of await readdir(path)) total += await treeBytes(resolve(path, entry)); return total; }
async function processEvidence(root, id, run) {
  await mkdir(resolve(root, 'logs'), { recursive: true }); await mkdir(resolve(root, 'processes'), { recursive: true });
  const stdoutPath = resolve(root, 'logs', `${id}.stdout.log`), stderrPath = resolve(root, 'logs', `${id}.stderr.log`);
  await writeFile(stdoutPath, run.stdout, { flag: 'wx' }); await writeFile(stderrPath, run.stderr, { flag: 'wx' });
  const record = { schemaVersion: 'bfs.filmLanguageExecutionProcess.v0.1', id, argv: run.argv, exitCode: run.code, signal: run.signal, wallSeconds: run.wallSeconds, peakRssBytes: run.peakRssBytes, stdout: { sha256: await sha256File(stdoutPath), bytes: (await lstat(stdoutPath)).size }, stderr: { sha256: await sha256File(stderrPath), bytes: (await lstat(stderrPath)).size } };
  await writeFile(resolve(root, 'processes', `${id}.json`), `${JSON.stringify(canonicalize(record), null, 2)}\n`, { flag: 'wx' });
  return record;
}
async function retainFailure(evidenceRoot, workRoot, stage, error, runs) {
  await mkdir(evidenceRoot, { recursive: true });
  const failure = { schemaVersion: 'bfs.filmLanguageExecutionFailure.v0.1', experimentId: 'PC4-VX2', status: 'FAIL', stage, error: String(error?.message ?? error), completedProcesses: runs, roots: { evidence: evidenceRoot, work: workRoot }, failureHash: '' };
  failure.failureHash = selfHash(failure, 'failureHash');
  await writeFile(resolve(evidenceRoot, 'failure.json'), `${JSON.stringify(canonicalize(failure), null, 2)}\n`, { flag: 'wx' });
}

const contextPath = safeRepositoryPath(CONTEXT_URI), contextBytes = await readFile(contextPath), context = JSON.parse(contextBytes);
requireCondition(context.schemaVersion === 'bfs.filmLanguageExecutionContext.v0.1' && context.contextHash === selfHash(context, 'contextHash'), 'context self hash');
const freezePath = safeRepositoryPath(FREEZE_URI), freezeBytes = await readFile(freezePath), freeze = JSON.parse(freezeBytes);
requireCondition(freeze.schemaVersion === 'bfs.filmLanguageTypedExecutorToolFreeze.v0.1' && freeze.freezeHash === selfHash(freeze, 'freezeHash'), 'freeze self hash');
for (const input of freeze.inputs) requireCondition(await sha256File(safeRepositoryPath(input.uri)) === input.sha256, `frozen input drift ${input.uri}`);
const binary = context.binary.path, source = context.source.path, workRoot = context.roots.work, evidenceRoot = safeRepositoryPath(context.roots.evidence);
requireCondition(await sha256File(binary) === context.binary.sha256 && await sha256File(source) === context.source.sha256, 'external identity');
requireCondition(await sha256File(safeRepositoryPath(context.plan.uri)) === context.plan.sha256 && await sha256File(safeRepositoryPath(context.packet.uri)) === context.packet.sha256, 'semantic identity');
await assertAbsent(workRoot, 'work root'); await assertAbsent(evidenceRoot, 'evidence root');
const disk = await statfs(resolve(workRoot, '..')), freeBytes = Number(disk.bavail) * Number(disk.bsize);
requireCondition(freeBytes >= 107374182400, `free disk ${freeBytes}`);
await mkdir(workRoot, { recursive: false }); await mkdir(evidenceRoot, { recursive: false }); await mkdir(resolve(evidenceRoot, 'review'), { recursive: false });
const common = ['--context', contextPath, '--evidence-root', evidenceRoot, '--work-root', workRoot];
const runs = []; let stage = 'BUILD';
try {
  const buildRun = await runTimed(binary, ['--background', source, '--python-exit-code', '93', '--python', safeRepositoryPath(EXECUTOR_URI), '--', ...common]);
  const buildRecord = await processEvidence(evidenceRoot, '01-build', buildRun); runs.push(buildRecord); requireCondition(buildRun.code === 0, `build exit ${buildRun.code}`);
  const buildPath = resolve(evidenceRoot, 'build.json'), build = JSON.parse(await readFile(buildPath));
  requireCondition(build.status === 'MACHINE_PASS_VISUAL_REVIEW_REQUIRED' && build.buildHash === selfHash(build, 'buildHash'), 'build receipt');
  requireCondition(build.operationsConsumed.length === 5 && build.effects.length === 5 && build.screenshots.length === 3, 'semantic counts');
  const derived = resolve(workRoot, 'FILM_LANGUAGE_IMPROVEMENT.blend'); requireCondition(await sha256File(derived) === build.derived.sha256, 'derived identity');
  stage = 'REOPEN';
  const reopenRun = await runTimed(binary, ['--background', derived, '--python-exit-code', '94', '--python', safeRepositoryPath(REOPEN_URI), '--', ...common]);
  const reopenRecord = await processEvidence(evidenceRoot, '02-reopen', reopenRun); runs.push(reopenRecord); requireCondition(reopenRun.code === 0, `reopen exit ${reopenRun.code}`);
  const reopenPath = resolve(evidenceRoot, 'reopen-audit.json'), reopen = JSON.parse(await readFile(reopenPath));
  requireCondition(reopen.status === 'PASS' && reopen.auditHash === selfHash(reopen, 'auditHash'), 'reopen audit');
  requireCondition(await sha256File(source) === context.source.sha256, 'source drift');
  requireCondition(runs.every(run => run.peakRssBytes !== null && run.peakRssBytes <= 4294967296), 'rss ceiling');
  requireCondition(runs.reduce((sum, run) => sum + run.wallSeconds, 0) <= 900 && await treeBytes(workRoot) <= 1073741824 && await treeBytes(evidenceRoot) <= 67108864, 'resource ceiling');
  const receipt = { schemaVersion: 'bfs.filmLanguageExecutionReceipt.v0.1', experimentId: context.experimentId, status: 'MACHINE_PASS_VISUAL_REVIEW_REQUIRED', preregistration: freeze.preregistration, toolFreeze: { uri: FREEZE_URI, sha256: sha256(freezeBytes), freezeHash: freeze.freezeHash }, context: { uri: CONTEXT_URI, sha256: sha256(contextBytes), contextHash: context.contextHash }, plan: context.plan, source: { path: source, beforeSha256: context.source.sha256, afterSha256: await sha256File(source) }, binary: context.binary, build: { uri: `${context.roots.evidence}/build.json`, sha256: await sha256File(buildPath), buildHash: build.buildHash }, reopen: { uri: `${context.roots.evidence}/reopen-audit.json`, sha256: await sha256File(reopenPath), auditHash: reopen.auditHash }, derived: build.derived, screenshots: build.screenshots, processes: runs, resources: { freeBytesAtAdmission: freeBytes, workRootBytes: await treeBytes(workRoot), evidenceRootBytesBeforeReceipt: await treeBytes(evidenceRoot), wallSeconds: runs.reduce((sum, run) => sum + run.wallSeconds, 0), peakRssBytes: Math.max(...runs.map(run => run.peakRssBytes)) }, operationCounts: { blenderStarts: 2, renderCalls: 3, sceneSaves: 1, reopenAudits: 1, networkCalls: 0, modelCallsDuringExecution: 0, mouseInteractions: 0, retainedExr: 0 }, visualVerdict: 'PENDING_DIRECT_MODEL_REVIEW', receiptHash: '' };
  receipt.receiptHash = selfHash(receipt, 'receiptHash'); await writeFile(resolve(evidenceRoot, 'receipt.json'), `${JSON.stringify(canonicalize(receipt), null, 2)}\n`, { flag: 'wx' });
  process.stdout.write(`BFS_FILM_LANGUAGE_RUN MACHINE_PASS_VISUAL_REVIEW_REQUIRED ${build.buildHash} ${reopen.auditHash} ${receipt.receiptHash}\n`);
} catch (error) { await retainFailure(evidenceRoot, workRoot, stage, error, runs).catch(() => {}); throw error; }
