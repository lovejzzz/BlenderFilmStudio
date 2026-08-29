#!/usr/bin/env node

import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { execFile } from 'node:child_process';
import { lstat, mkdir, open, readFile, readdir } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { promisify } from 'node:util';

const ROOT = resolve(import.meta.dirname, '..');
const SPEC_URI = 'specs/restart-safe-production-orchestrator-reaudit-correction.v0.1.json';
const PROTOCOL_URI = 'research/2026-08-29-b58-e1-c7-reaudit-correction.md';
const AUDITOR_URI = 'scripts/audit-b58-e1-restart-safe-production-orchestrator.mjs';
const RUNNER_URI = 'scripts/run-b58-e1-c7-reaudit.mjs';
const OUTPUT_ROOT = 'experiments/restart-safe-production-orchestrator-c7-reaudit-v0-1';
const PREFLIGHT_ROOT = 'experiments/restart-safe-production-orchestrator-preflight-v0-3';
const ATTEMPT_ROOT = 'experiments/restart-safe-production-orchestrator-attempt-v0-3';
const FORMAL_ROOT = 'experiments/restart-safe-production-orchestrator-v0-3';
const NODE = '/opt/homebrew/Cellar/node/26.5.0/bin/node';
const execFileAsync = promisify(execFile);

function sortValue(value) {
  if (Array.isArray(value)) return value.map(sortValue);
  if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map(key => [key, sortValue(value[key])]));
  return value;
}
function canonical(value) { return JSON.stringify(sortValue(value)); }
function hashBytes(value) { return createHash('sha256').update(value).digest('hex'); }
async function fileHash(path) { return hashBytes(await readFile(path)); }
function selfHash(value, field) { const copy = structuredClone(value); delete copy[field]; return hashBytes(Buffer.from(canonical(copy))); }
function validSelfHash(value, field) { return value?.[field] === selfHash(value, field); }
async function exists(path) { try { await lstat(path); return true; } catch (error) { if (error?.code === 'ENOENT') return false; throw error; } }

async function syncDirectory(path) {
  const handle = await open(path, 'r');
  try { await handle.sync(); } finally { await handle.close(); }
}

async function durableMkdir(path) {
  await mkdir(path, { recursive: true });
  await syncDirectory(path);
  await syncDirectory(dirname(path));
}

async function writeHashed(path, body, field) {
  const record = { ...body, [field]: selfHash(body, field) };
  const handle = await open(path, 'wx', 0o600);
  try { await handle.writeFile(`${JSON.stringify(sortValue(record), null, 2)}\n`); await handle.sync(); } finally { await handle.close(); }
  await syncDirectory(dirname(path));
  return record;
}

async function walk(path) {
  const rows = [];
  for (const entry of await readdir(path, { withFileTypes: true })) {
    const child = join(path, entry.name);
    if (entry.isDirectory()) rows.push(...await walk(child));
    else if (entry.isFile()) rows.push(child);
  }
  return rows;
}

async function evidenceTree(spec) {
  const roots = [spec.immutableFormalV03.attemptRoot, spec.immutableFormalV03.formalRoot];
  const files = (await Promise.all(roots.map(uri => walk(resolve(ROOT, uri))))).flat().sort();
  const rows = [];
  for (const absolutePath of files) rows.push({ uri: absolutePath.slice(ROOT.length + 1), sha256: await fileHash(absolutePath) });
  return { files: rows, fileCount: rows.length, treeSha256: hashBytes(Buffer.from(JSON.stringify(rows))) };
}

async function git(args) {
  const result = await execFileAsync('/usr/bin/git', args, { cwd: ROOT, encoding: 'utf8', env: { PATH: '/usr/bin:/bin', LANG: 'C', LC_ALL: 'C', GIT_CONFIG_NOSYSTEM: '1', GIT_TERMINAL_PROMPT: '0' } });
  return result.stdout.trim();
}

async function runChild(command, args) {
  const child = spawn(command, args, { cwd: ROOT, env: { PATH: '/opt/homebrew/bin:/usr/bin:/bin', LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8' }, stdio: ['ignore', 'pipe', 'pipe'] });
  const stdout = []; const stderr = [];
  child.stdout.on('data', chunk => stdout.push(chunk)); child.stderr.on('data', chunk => stderr.push(chunk));
  const terminal = await new Promise((done, reject) => { child.on('error', reject); child.on('close', (exitCode, signal) => done({ exitCode, signal })); });
  return { pid: child.pid, ...terminal, stdout: Buffer.concat(stdout).toString('utf8'), stderr: Buffer.concat(stderr).toString('utf8') };
}

function parse(argv) {
  if (argv.length !== 2 || argv[0] !== '--tool-freeze-commit' || !/^[0-9a-f]{40}$/.test(argv[1])) throw new Error('Expected --tool-freeze-commit with full SHA-1');
  return { toolFreezeCommit: argv[1] };
}

async function run(argv) {
  const parsed = parse(argv);
  const spec = JSON.parse(await readFile(resolve(ROOT, SPEC_URI), 'utf8'));
  if (spec.authorizedCorrection.reauditOutputRoot !== OUTPUT_ROOT || spec.authorizedCorrection.runner !== RUNNER_URI) throw new Error('C7 output or runner binding mismatch');
  if (await exists(resolve(ROOT, OUTPUT_ROOT))) throw new Error('C7 re-audit output root must be fresh');

  const head = await git(['rev-parse', 'HEAD']);
  const origin = await git(['rev-parse', '--verify', 'origin/main']);
  if (head !== parsed.toolFreezeCommit || origin !== parsed.toolFreezeCommit) throw new Error('C7 tool-freeze commit must equal HEAD and origin/main');
  const scoped = [SPEC_URI, PROTOCOL_URI, AUDITOR_URI, RUNNER_URI, ATTEMPT_ROOT, FORMAL_ROOT];
  if (await git(['status', '--porcelain=v1', '--untracked-files=all', '--', ...scoped]) !== '') throw new Error('C7 scoped evidence or tools are dirty');
  const toolHashes = {};
  for (const uri of [SPEC_URI, PROTOCOL_URI, AUDITOR_URI, RUNNER_URI]) toolHashes[uri] = await fileHash(resolve(ROOT, uri));

  const before = await evidenceTree(spec);
  if (before.fileCount !== spec.immutableFormalV03.fileCount || before.treeSha256 !== spec.immutableFormalV03.canonicalTreeSha256) throw new Error('Immutable v0.3 evidence tree mismatch before re-audit');
  for (const [uri, expected] of [
    [`${FORMAL_ROOT}/operation-draft.json`, spec.immutableFormalV03.operationDraftSha256],
    [`${FORMAL_ROOT}/audit.json`, spec.immutableFormalV03.oldAudit.sha256],
    [`${FORMAL_ROOT}/results.json`, spec.immutableFormalV03.oldResults.sha256],
    [`${FORMAL_ROOT}/receipt.json`, spec.immutableFormalV03.oldReceipt.sha256],
  ]) if (await fileHash(resolve(ROOT, uri)) !== expected) throw new Error(`Frozen C7 input mismatch: ${uri}`);

  await durableMkdir(resolve(ROOT, OUTPUT_ROOT));
  const auditPath = resolve(ROOT, OUTPUT_ROOT, 'audit.json');
  const child = await runChild(NODE, [AUDITOR_URI, '--repository-root', ROOT, '--preflight-root', PREFLIGHT_ROOT, '--attempt-root', ATTEMPT_ROOT, '--formal-root', FORMAL_ROOT, '--output', auditPath]);
  if (child.exitCode !== 0 || child.signal !== null) throw new Error(`Corrected auditor failed: ${child.stderr || child.stdout}`);
  const audit = JSON.parse(await readFile(auditPath, 'utf8'));
  if (!validSelfHash(audit, 'auditHash')) throw new Error('Corrected audit self-hash mismatch');
  const admitted = audit.gatePassed === spec.admission.requiredGates && audit.gateTotal === spec.admission.requiredGates
    && audit.attackSummary.rejected === spec.admission.requiredOriginalAttacks && audit.attackSummary.total === spec.admission.requiredOriginalAttacks
    && audit.reAuditCorrectionAttackSummary.rejected === spec.admission.requiredC7Attacks && audit.reAuditCorrectionAttackSummary.total === spec.admission.requiredC7Attacks
    && audit.scientificVerdict === spec.admission.requiredVerdict;
  const after = await evidenceTree(spec);
  if (after.treeSha256 !== before.treeSha256 || after.fileCount !== before.fileCount) throw new Error('Immutable v0.3 evidence changed during re-audit');

  const resultsPath = resolve(ROOT, OUTPUT_ROOT, 'results.json');
  const results = await writeHashed(resultsPath, {
    schemaVersion: 'bfs.restartSafeProductionOrchestratorC7ReauditResult.v0.1', experimentId: 'B58-E1-C7', status: admitted ? 'PASS' : 'FAIL',
    toolFreezeCommit: parsed.toolFreezeCommit, toolHashes, immutableEvidence: { fileCount: before.fileCount, treeSha256: before.treeSha256 },
    oldAudit: spec.immutableFormalV03.oldAudit, correctedAudit: { uri: `${OUTPUT_ROOT}/audit.json`, sha256: await fileHash(auditPath), auditHash: audit.auditHash },
    gates: { passed: audit.gatePassed, total: audit.gateTotal }, attacks: { original: audit.attackSummary, c7: audit.reAuditCorrectionAttackSummary },
    operations: { nodeAuditorProcesses: 1, blenderProcesses: 0, renderCalls: 0, modelCalls: 0, networkCalls: 0, dockerProcesses: 0 }, scientificVerdict: audit.scientificVerdict,
  }, 'resultHash');
  const receipt = await writeHashed(resolve(ROOT, OUTPUT_ROOT, 'receipt.json'), {
    schemaVersion: 'bfs.restartSafeProductionOrchestratorC7ReauditReceipt.v0.1', status: admitted ? 'PASS' : 'FAIL',
    result: { uri: `${OUTPUT_ROOT}/results.json`, sha256: await fileHash(resultsPath), resultHash: results.resultHash },
    correctedAudit: results.correctedAudit, immutableEvidence: results.immutableEvidence, operations: results.operations, scientificVerdict: results.scientificVerdict,
  }, 'receiptHash');
  process.stdout.write(`BFS_B58_C7_REAUDIT ${admitted ? 'PASS' : 'FAIL'} gates=${audit.gatePassed}/${audit.gateTotal} attacks=${audit.attackSummary.rejected}/${audit.attackSummary.total} c7=${audit.reAuditCorrectionAttackSummary.rejected}/${audit.reAuditCorrectionAttackSummary.total} blender=0 ${receipt.receiptHash}\n`);
  if (!admitted) process.exitCode = 1;
  return receipt;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  run(process.argv.slice(2)).catch(error => { process.stderr.write(`BFS_B58_C7_REAUDIT_ERROR ${error.message}\n`); process.exitCode = 1; });
}
