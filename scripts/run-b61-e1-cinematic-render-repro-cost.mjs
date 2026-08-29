#!/usr/bin/env node

import { execFile } from 'node:child_process';
import { open, readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { promisify } from 'node:util';
import { durableMkdir, repoUri, resolveExistingRepositoryPath, resolveFreshRepositoryPath, sha256Bytes, sha256File, validSelfHash, writeDurableHashed, writeDurableJson } from './lib/production-compile-receipt.mjs';
import { repositoryRoot } from './lib/scene-spec.mjs';

const execFileAsync = promisify(execFile);
const CONTRACT_URI = 'specs/cinematic-render-repro-cost.v0.1.json';
const CORRECTION_URI = 'specs/cinematic-render-repro-cost-c1-terminal-observability-correction.v0.1.json';
const EXPECTED = { preflightRoot: 'experiments/cinematic-render-repro-cost-preflight-v0-2', attemptRoot: 'experiments/cinematic-render-repro-cost-attempt-v0-2', formalRoot: 'experiments/cinematic-render-repro-cost-v0-2' };
const TOOL_PATHS = [CONTRACT_URI, CORRECTION_URI, 'research/2026-08-29-b61-e1-cinematic-render-repro-cost-protocol.md', 'research/2026-08-29-b61-e1-c1-terminal-observability-correction.md', 'blender/render_b61_frames.py', 'blender/audit_b61_exr.py', 'scripts/preflight-b61-e1-cinematic-render-repro-cost.mjs', 'scripts/run-b61-e1-cinematic-render-repro-cost.mjs', 'scripts/audit-b61-e1-cinematic-render-repro-cost.mjs'];
const MAXIMUM_LOG_BYTES = 4 * 1024 * 1024;

function parseArguments(argv) {
  const parsed = {};
  for (let index = 0; index < argv.length; index += 1) { const token = argv[index]; if (token === '--preflight-root') parsed.preflightRoot = argv[++index]; else if (token === '--attempt-root') parsed.attemptRoot = argv[++index]; else if (token === '--formal-root') parsed.formalRoot = argv[++index]; else if (token === '--tool-freeze-commit') parsed.toolFreezeCommit = argv[++index]; else if (token === '--preflight-evidence-commit') parsed.preflightEvidenceCommit = argv[++index]; else throw new Error(`Unknown argument ${token}`); }
  for (const [key, expected] of Object.entries(EXPECTED)) if (parsed[key] !== expected) throw new Error(`B61 ${key} mismatch`);
  for (const key of ['toolFreezeCommit', 'preflightEvidenceCommit']) if (!/^[0-9a-f]{40}$/.test(parsed[key] ?? '')) throw new Error(`B61 ${key} invalid`);
  return parsed;
}

async function git(args, encoding = 'utf8') { const result = await execFileAsync('/usr/bin/git', args, { cwd: repositoryRoot, encoding, timeout: 15000, maxBuffer: 32 * 1024 * 1024, env: { PATH: '/usr/bin:/bin', LANG: 'C', LC_ALL: 'C', GIT_CONFIG_NOSYSTEM: '1', GIT_TERMINAL_PROMPT: '0' } }); return result.stdout; }
async function verifyFreeze(parsed, preflightPath) {
  const origin = (await git(['rev-parse', 'origin/main'])).trim(); await git(['merge-base', '--is-ancestor', parsed.toolFreezeCommit, origin]); await git(['merge-base', '--is-ancestor', parsed.preflightEvidenceCommit, origin]); await git(['merge-base', '--is-ancestor', parsed.toolFreezeCommit, parsed.preflightEvidenceCommit]);
  const hashes = {}; for (const uri of TOOL_PATHS) { const path = await resolveExistingRepositoryPath(uri, uri); const current = await sha256File(path); const frozen = sha256Bytes(await git(['show', `${parsed.toolFreezeCommit}:${uri}`], null)); if (current !== frozen) throw new Error(`B61 tool mismatch ${uri}`); hashes[uri] = current; }
  const uri = repoUri(preflightPath); const frozen = sha256Bytes(await git(['show', `${parsed.preflightEvidenceCommit}:${uri}`], null)); if (frozen !== await sha256File(preflightPath)) throw new Error('B61 preflight evidence commit mismatch');
  const dirty = await git(['status', '--porcelain=v1', '--untracked-files=all', '--', parsed.preflightRoot]); if (dirty.length) throw new Error('B61 preflight root dirty'); return hashes;
}

async function run(command, args, env, timeout) {
  const started = process.hrtime.bigint();
  try { const result = await execFileAsync(command, args, { cwd: repositoryRoot, encoding: 'utf8', timeout, maxBuffer: 16 * 1024 * 1024, env }); return { exitCode: 0, signal: null, elapsedSeconds: Number(process.hrtime.bigint() - started) / 1e9, stdout: result.stdout, stderr: result.stderr }; }
  catch (error) { return { exitCode: typeof error.code === 'number' ? error.code : 1, signal: error.signal ?? null, elapsedSeconds: Number(process.hrtime.bigint() - started) / 1e9, stdout: error.stdout ?? '', stderr: error.stderr ?? error.message }; }
}
function phaseGate(stdout, source, ocio) { const using = stdout.indexOf(`Using OCIO=${ocio}`); const read = stdout.indexOf(`blend            | Read blend: "${source}"`); const warnings = [...stdout.matchAll(/color_management \| WARNING/g)].map(match => match.index); return { usingFrozenOcio: using >= 0, targetBlendRead: read >= 0, startupWarningCount: warnings.filter(index => index < read).length, postReadWarningCount: warnings.filter(index => index > read).length }; }
function processRecord(id, result, gate) { return { id, exitCode: result.exitCode, signal: result.signal, elapsedSeconds: result.elapsedSeconds, phaseGate: gate, stdout: { bytes: Buffer.byteLength(result.stdout), sha256: sha256Bytes(Buffer.from(result.stdout)) }, stderr: { bytes: Buffer.byteLength(result.stderr), sha256: sha256Bytes(Buffer.from(result.stderr)) }, timing: { realSeconds: Number(result.stderr.match(/^real\s+([0-9.]+)/m)?.[1] ?? result.elapsedSeconds), userSeconds: Number(result.stderr.match(/^user\s+([0-9.]+)/m)?.[1] ?? 0), systemSeconds: Number(result.stderr.match(/^sys\s+([0-9.]+)/m)?.[1] ?? 0), maximumResidentSetSizeBytes: Number(result.stderr.match(/^\s*([0-9]+)\s+maximum resident set size/m)?.[1] ?? 0) } }; }

async function writeDurableLog(path, text) {
  const full = Buffer.from(text);
  const captured = full.subarray(0, MAXIMUM_LOG_BYTES);
  const handle = await open(path, 'wx', 0o600);
  try { await handle.writeFile(captured); await handle.sync(); } finally { await handle.close(); }
  const directory = await open(resolve(path, '..'), 'r'); try { await directory.sync(); } finally { await directory.close(); }
  return { uri: repoUri(path), sha256: sha256Bytes(captured), streamSha256: sha256Bytes(full), bytes: full.length, capturedBytes: captured.length, truncated: captured.length !== full.length };
}

async function persistProcess(attemptPath, id, result, gate) {
  const stdoutLog = await writeDurableLog(resolve(attemptPath, 'logs', `${id}.stdout.log`), result.stdout);
  const stderrLog = await writeDurableLog(resolve(attemptPath, 'logs', `${id}.stderr.log`), result.stderr);
  const record = { ...processRecord(id, result, gate), pythonExitCodeEnforced: id === 'EXR-AUDITOR' || !id.includes('AUDITOR'), logs: { stdout: stdoutLog, stderr: stderrLog } };
  await writeDurableJson(resolve(attemptPath, 'processes', `${id}.json`), record);
  return record;
}

export async function runB61(argv) {
  const parsed = parseArguments(argv); const preflightPath = await resolveExistingRepositoryPath(`${parsed.preflightRoot}/preflight.json`, 'B61 preflight'); const attemptPath = await resolveFreshRepositoryPath(parsed.attemptRoot, 'B61 attempt root'); const formalPath = await resolveFreshRepositoryPath(parsed.formalRoot, 'B61 formal root');
  const contractPath = await resolveExistingRepositoryPath(CONTRACT_URI, 'B61 contract'); const contract = JSON.parse(await readFile(contractPath, 'utf8')); const correction = JSON.parse(await readFile(await resolveExistingRepositoryPath(CORRECTION_URI, 'B61 C1 correction'), 'utf8')); const preflight = JSON.parse(await readFile(preflightPath, 'utf8'));
  if (correction.status !== 'PREREGISTERED' || correction.authorizedRetryRoots.preflight !== parsed.preflightRoot || correction.authorizedRetryRoots.attempt !== parsed.attemptRoot || correction.authorizedRetryRoots.formal !== parsed.formalRoot) throw new Error('B61 C1 retry-root binding mismatch');
  if (!validSelfHash(preflight, 'preflightHash') || preflight.status !== 'ACCEPTED' || preflight.toolFreezeCommit !== parsed.toolFreezeCommit) throw new Error('B61 preflight invalid'); const toolHashes = await verifyFreeze(parsed, preflightPath);
  await durableMkdir(attemptPath); const attempt = await writeDurableHashed(resolve(attemptPath, 'attempt.json'), { schemaVersion: 'bfs.cinematicRenderReproCostAttempt.v0.1', sequence: 1, status: 'STARTED', invocation: parsed, preflight: { uri: repoUri(preflightPath), sha256: await sha256File(preflightPath), preflightHash: preflight.preflightHash }, toolHashes, verdict: null }, 'attemptHash');
  const admission = await writeDurableHashed(resolve(attemptPath, 'admission.json'), { schemaVersion: 'bfs.cinematicRenderReproCostAdmission.v0.1', sequence: 2, status: 'ACCEPTED', attemptHash: attempt.attemptHash, renderBlenderStartsAuthorized: 6, renderCallsAuthorized: 18, exrAuditBlenderStartsAuthorized: 1, verdict: null }, 'admissionHash');
  const attemptReceipt = await writeDurableHashed(resolve(attemptPath, 'receipt.json'), { schemaVersion: 'bfs.cinematicRenderReproCostAttemptReceipt.v0.1', sequence: 3, status: 'ACCEPTED', admissionHash: admission.admissionHash, formalOutputAuthorized: true, verdict: null }, 'receiptHash');
  await durableMkdir(formalPath); await durableMkdir(resolve(formalPath, 'runs')); await durableMkdir(resolve(attemptPath, 'processes')); await durableMkdir(resolve(attemptPath, 'logs')); await writeDurableHashed(resolve(formalPath, 'formal-start.json'), { schemaVersion: 'bfs.cinematicRenderReproCostFormalStart.v0.2', sequence: 4, status: 'AUTHORIZED', attemptReceiptHash: attemptReceipt.receiptHash, formalRoot: parsed.formalRoot, correction: CORRECTION_URI }, 'formalStartHash');
  const ocio = resolve(repositoryRoot, contract.runtime.ocio.uri); const env = { PATH: '/usr/bin:/bin', LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8', OCIO: ocio }; const processes = [];
  try {
    for (const shot of contract.shots) for (const repetition of contract.render.repetitions) {
      const id = `${shot.label}-${repetition}`; const output = resolve(formalPath, 'runs', id); await durableMkdir(output); const source = resolve(repositoryRoot, shot.sourceBlend.uri);
      const result = await run('/usr/bin/time', ['-lp', contract.runtime.blenderBinary, '--background', source, '--disable-autoexec', '--python-exit-code', '1', '--python', resolve(repositoryRoot, 'blender/render_b61_frames.py'), '--', '--repository-root', repositoryRoot, '--contract', contractPath, '--shot', shot.label, '--repetition', repetition, '--output-dir', output], env, contract.resourceCeilings.perRenderProcessTimeoutSeconds * 1000);
      const record = await persistProcess(attemptPath, id, result, phaseGate(result.stdout, source, ocio)); processes.push(record);
      if (record.exitCode !== 0 || record.signal !== null || !record.phaseGate.usingFrozenOcio || !record.phaseGate.targetBlendRead || record.phaseGate.postReadWarningCount !== 0) throw new Error(`B61 render process failed ${id}: ${result.stderr || result.stdout}`);
      const runReport = JSON.parse(await readFile(resolve(output, 'run-report.json'), 'utf8')); if (!validSelfHash(runReport, 'runReportHash') || runReport.status !== 'PASS') throw new Error(`B61 run report invalid ${id}`);
    }
    const reopenPath = resolve(formalPath, 'exr-reopen-audit.json'); const reopen = await run(contract.runtime.blenderBinary, ['--background', '--factory-startup', '--disable-autoexec', '--python-exit-code', '1', '--python', resolve(repositoryRoot, 'blender/audit_b61_exr.py'), '--', '--repository-root', repositoryRoot, '--contract', contractPath, '--formal-root', formalPath, '--output', reopenPath], env, 120000);
    await persistProcess(attemptPath, 'EXR-AUDITOR', reopen, { usingFrozenOcio: reopen.stdout.includes(`Using OCIO=${ocio}`) }); if (reopen.exitCode !== 0) throw new Error(`B61 EXR auditor failed: ${reopen.stderr || reopen.stdout}`);
    const auditPath = resolve(formalPath, 'audit.json'); const auditor = await run(process.execPath, ['scripts/audit-b61-e1-cinematic-render-repro-cost.mjs', '--preflight-root', parsed.preflightRoot, '--attempt-root', parsed.attemptRoot, '--formal-root', parsed.formalRoot, '--output', `${parsed.formalRoot}/audit.json`], { ...env, PATH: '/opt/homebrew/bin:/usr/bin:/bin' }, 120000); await persistProcess(attemptPath, 'NODE-AUDITOR', auditor, {}); if (auditor.exitCode !== 0) throw new Error(`B61 Node auditor failed: ${auditor.stderr || auditor.stdout}`);
    const audit = JSON.parse(await readFile(auditPath, 'utf8')); if (!validSelfHash(audit, 'auditHash') || audit.status !== 'PASS') throw new Error('B61 audit invalid');
    const results = await writeDurableHashed(resolve(formalPath, 'results.json'), { schemaVersion: 'bfs.cinematicRenderReproCostResults.v0.1', status: 'PASS', verdict: contract.passVerdict, audit: { uri: repoUri(auditPath), sha256: await sha256File(auditPath), auditHash: audit.auditHash }, gates: audit.gates, attacks: audit.attacks, costs: audit.costs, operations: audit.operations, claimBoundary: contract.claimBoundary }, 'resultsHash');
    const receipt = await writeDurableHashed(resolve(formalPath, 'receipt.json'), { schemaVersion: 'bfs.cinematicRenderReproCostReceipt.v0.1', status: 'PASS', verdict: contract.passVerdict, authorization: { attemptHash: attempt.attemptHash, admissionHash: admission.admissionHash, attemptReceiptHash: attemptReceipt.receiptHash }, results: { uri: `${parsed.formalRoot}/results.json`, sha256: await sha256File(resolve(formalPath, 'results.json')), resultsHash: results.resultsHash }, processes, operations: audit.operations, claimBoundary: contract.claimBoundary }, 'receiptHash'); process.stdout.write(`BFS_B61_FORMAL PASS ${audit.gates.length}/${audit.gates.length} attacks=${audit.attacks.length}/${audit.attacks.length} ${receipt.receiptHash}\n`); return receipt;
  } catch (error) { await writeDurableHashed(resolve(formalPath, 'invalidation.json'), { schemaVersion: 'bfs.cinematicRenderReproCostInvalidation.v0.1', status: 'INVALIDATED', error: error.message, completedRenderProcesses: processes.length, partialEvidenceRetained: true, verdict: null }, 'invalidationHash'); process.stderr.write(`BFS_B61_FORMAL_INVALIDATED ${error.message}\n`); process.exitCode = 1; return null; }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) runB61(process.argv.slice(2)).catch(error => { process.stderr.write(`BFS_B61_FORMAL_ERROR ${error.message}\n`); process.exitCode = 1; });
