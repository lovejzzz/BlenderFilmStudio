#!/usr/bin/env node

import { execFile, spawn } from 'node:child_process';
import { open, readFile, stat, statfs } from 'node:fs/promises';
import { resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { promisify } from 'node:util';
import { measureOutput } from './lib/budgeted-process.mjs';
import {
  durableMkdir, repoUri, resolveExistingRepositoryPath, resolveFreshRepositoryPath,
  sha256Bytes, sha256File, validSelfHash, writeDurableHashed, writeDurableJson,
} from './preflight-b62-phase0.mjs';

const repositoryRoot = resolve(fileURLToPath(new URL('../', import.meta.url)));

const execFileAsync = promisify(execFile);
const CONTRACT_URI = 'specs/b62-phase0-asset-animatic-calibration.v0.1.json';
const CORRECTION_URI = 'specs/b62-phase0-c1-ffprobe-accounting-correction.v0.1.json';
const CORRECTION_2_URI = 'specs/b62-phase0-c2-fresh-clone-node-dependency-correction.v0.1.json';
const CORRECTION_3_URI = 'specs/b62-phase0-c3-blender52-multilayer-media-correction.v0.1.json';
const CORRECTION_4_URI = 'specs/b62-phase0-c4-dynamic-exr-setter-correction.v0.1.json';
const CORRECTION_5_URI = 'specs/b62-phase0-c5-v02-retry-binding.v0.1.json';
const CORRECTION_6_URI = 'specs/b62-phase0-c6-blender52-config-surface-diagnostic.v0.1.json';
const CORRECTION_7_URI = 'specs/b62-phase0-c7-eevee-engine-runtime-correction.v0.1.json';
const CORRECTION_8_URI = 'specs/b62-phase0-c8-runtime-config-promotion-and-generator-smoke.v0.1.json';
const CORRECTION_9_URI = 'specs/b62-phase0-c9-v03-formal-binding.v0.1.json';
const CORRECTION_10_URI = 'specs/b62-phase0-c10-library-locality-diagnostic.v0.1.json';
const CORRECTION_11_URI = 'specs/b62-phase0-c11-auditor-library-locality-correction.v0.1.json';
const CORRECTION_12_URI = 'specs/b62-phase0-c12-v04-formal-retry-binding.v0.1.json';
const EXPECTED = {
  preflightRoot: 'experiments/b62-phase0-preflight-v0-4',
  attemptRoot: 'experiments/b62-phase0-attempt-v0-4',
  formalRoot: 'experiments/b62-phase0-v0-4',
};
const TOOL_PATHS = [
  CONTRACT_URI, CORRECTION_URI, CORRECTION_2_URI, CORRECTION_3_URI, CORRECTION_4_URI, CORRECTION_5_URI,
  CORRECTION_6_URI, CORRECTION_7_URI, CORRECTION_8_URI, CORRECTION_9_URI,
  CORRECTION_10_URI, CORRECTION_11_URI, CORRECTION_12_URI,
  'research/2026-08-29-b62-terminal-cinematic-proof-goal.md',
  'research/2026-08-29-b62-phase0-asset-animatic-calibration-protocol.md',
  'research/2026-08-29-b62-phase0-c1-ffprobe-accounting-correction.md',
  'research/2026-08-29-b62-phase0-c2-fresh-clone-node-dependency-correction.md',
  'research/2026-08-29-b62-phase0-c3-blender52-multilayer-media-correction.md',
  'research/2026-08-29-b62-phase0-c4-dynamic-exr-setter-correction.md',
  'research/2026-08-29-b62-phase0-c5-v02-retry-binding.md',
  'research/2026-08-29-b62-phase0-c6-blender52-config-surface-diagnostic.md',
  'research/2026-08-29-b62-phase0-c7-eevee-engine-runtime-correction.md',
  'research/2026-08-29-b62-phase0-c8-runtime-config-promotion-and-generator-smoke.md',
  'research/2026-08-29-b62-phase0-c9-v03-formal-binding.md',
  'research/2026-08-29-b62-phase0-c10-library-locality-diagnostic.md',
  'research/2026-08-29-b62-phase0-c11-auditor-library-locality-correction.md',
  'research/2026-08-29-b62-phase0-c12-v04-formal-retry-binding.md',
  'experiments/b62-phase0-d2-exr-media-state-ab-v0-1/result.json',
  'experiments/b62-phase0-d2-exr-media-state-ab-v0-1/receipt.json',
  'experiments/b62-phase0-d4-config-surface-v0-1/result.json',
  'experiments/b62-phase0-d4-config-surface-v0-1/receipt.json',
  'experiments/b62-phase0-d5-generator-smoke-v0-1/result.json',
  'experiments/b62-phase0-d5-generator-smoke-v0-1/receipt.json',
  'experiments/b62-phase0-d6-library-locality-v0-1/probe.json',
  'experiments/b62-phase0-d6-library-locality-v0-1/result.json',
  'experiments/b62-phase0-d6-library-locality-v0-1/receipt.json',
  'experiments/b62-phase0-d7-corrected-auditor-smoke-v0-1/blender-audit.json',
  'experiments/b62-phase0-d7-corrected-auditor-smoke-v0-1/result.json',
  'experiments/b62-phase0-d7-corrected-auditor-smoke-v0-1/receipt.json',
  'blender/generate_b62_phase0_assets.py', 'blender/render_b62_phase0.py', 'blender/audit_b62_phase0.py',
  'scripts/preflight-b62-phase0.mjs', 'scripts/run-b62-phase0.mjs', 'scripts/audit-b62-phase0.mjs',
];
const BLENDER = '/Applications/Blender.app/Contents/MacOS/Blender';
const FFMPEG = '/opt/homebrew/bin/ffmpeg';
const FFPROBE = '/opt/homebrew/bin/ffprobe';

function parseArguments(argv) {
  const parsed = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--preflight-root') parsed.preflightRoot = argv[++index];
    else if (token === '--attempt-root') parsed.attemptRoot = argv[++index];
    else if (token === '--formal-root') parsed.formalRoot = argv[++index];
    else if (token === '--tool-freeze-commit') parsed.toolFreezeCommit = argv[++index];
    else if (token === '--preflight-evidence-commit') parsed.preflightEvidenceCommit = argv[++index];
    else throw new Error(`Unknown or incomplete argument: ${token}`);
  }
  for (const [key, expected] of Object.entries(EXPECTED)) if (parsed[key] !== expected) throw new Error(`B62 ${key} mismatch`);
  for (const key of ['toolFreezeCommit', 'preflightEvidenceCommit']) if (!/^[0-9a-f]{40}$/.test(parsed[key] ?? '')) throw new Error(`B62 ${key} invalid`);
  return parsed;
}

async function git(args, encoding = 'utf8') {
  const result = await execFileAsync('/usr/bin/git', args, {
    cwd: repositoryRoot, encoding, timeout: 15000, maxBuffer: 32 * 1024 * 1024,
    env: { PATH: '/usr/bin:/bin', LANG: 'C', LC_ALL: 'C', GIT_CONFIG_NOSYSTEM: '1', GIT_TERMINAL_PROMPT: '0' },
  });
  return result.stdout;
}

async function verifyFreeze(parsed, preflightPath) {
  const origin = (await git(['rev-parse', 'origin/main'])).trim();
  await git(['merge-base', '--is-ancestor', parsed.toolFreezeCommit, parsed.preflightEvidenceCommit]);
  await git(['merge-base', '--is-ancestor', parsed.preflightEvidenceCommit, origin]);
  const hashes = {};
  for (const uri of TOOL_PATHS) {
    const path = await resolveExistingRepositoryPath(uri, `B62 tool ${uri}`);
    const current = await sha256File(path);
    const frozen = sha256Bytes(await git(['show', `${parsed.toolFreezeCommit}:${uri}`], null));
    if (current !== frozen) throw new Error(`B62 frozen tool mismatch: ${uri}`);
    hashes[uri] = current;
  }
  const preflightUri = repoUri(preflightPath);
  if (await sha256File(preflightPath) !== sha256Bytes(await git(['show', `${parsed.preflightEvidenceCommit}:${preflightUri}`], null))) throw new Error('B62 preflight evidence commit mismatch');
  return hashes;
}

async function run(command, args, env, timeoutMs, maximumLogBytes) {
  const started = process.hrtime.bigint();
  const child = spawn('/usr/bin/time', ['-lp', command, ...args], { cwd: repositoryRoot, env, detached: true, stdio: ['ignore', 'pipe', 'pipe'] });
  const stdoutChunks = []; const stderrChunks = [];
  let logBytes = 0; let limitReason = null; let spawnError = null; let terminationRequested = false; let forceTimer = null;
  const terminate = reason => {
    if (terminationRequested) return;
    terminationRequested = true; limitReason = reason;
    try { process.kill(-child.pid, 'SIGTERM'); } catch { try { child.kill('SIGTERM'); } catch {} }
    forceTimer = setTimeout(() => { try { process.kill(-child.pid, 'SIGKILL'); } catch { try { child.kill('SIGKILL'); } catch {} } }, 2000);
  };
  const collect = (bucket, chunk) => {
    logBytes += chunk.length;
    if (logBytes <= maximumLogBytes + 65536) bucket.push(chunk);
    if (logBytes > maximumLogBytes) terminate('LOG_BYTES');
  };
  child.stdout.on('data', chunk => collect(stdoutChunks, chunk));
  child.stderr.on('data', chunk => collect(stderrChunks, chunk));
  child.on('error', error => { spawnError = error; });
  const timeout = setTimeout(() => terminate('WALL_TIME'), timeoutMs);
  const closed = await new Promise(resolveClose => child.on('close', (exitCode, signal) => resolveClose({ exitCode, signal })));
  clearTimeout(timeout); if (forceTimer) clearTimeout(forceTimer);
  return {
    exitCode: spawnError ? 1 : closed.exitCode, signal: closed.signal,
    elapsedSeconds: Number(process.hrtime.bigint() - started) / 1e9,
    stdout: Buffer.concat(stdoutChunks).toString('utf8'), stderr: Buffer.concat(stderrChunks).toString('utf8'),
    limitReason, terminationRequested,
  };
}

async function durableLog(path, value, maximumBytes) {
  const full = Buffer.from(value);
  const captured = full.subarray(0, maximumBytes);
  const handle = await open(path, 'wx', 0o600);
  try { await handle.writeFile(captured); await handle.sync(); } finally { await handle.close(); }
  return { uri: repoUri(path), sha256: sha256Bytes(captured), streamSha256: sha256Bytes(full), bytes: full.length, capturedBytes: captured.length, truncated: captured.length !== full.length };
}

async function persistProcess(attemptPath, id, kind, result, maximumBytes) {
  const stdout = await durableLog(resolve(attemptPath, 'logs', `${id}.stdout.log`), result.stdout, maximumBytes);
  const stderr = await durableLog(resolve(attemptPath, 'logs', `${id}.stderr.log`), result.stderr, maximumBytes);
  const record = {
    schemaVersion: 'bfs.b62Phase0Process.v0.1', id, kind,
    exitCode: result.exitCode, signal: result.signal, elapsedSeconds: result.elapsedSeconds,
    timing: {
      realSeconds: Number(result.stderr.match(/^real\s+([0-9.]+)/m)?.[1] ?? result.elapsedSeconds),
      userSeconds: Number(result.stderr.match(/^user\s+([0-9.]+)/m)?.[1] ?? 0),
      systemSeconds: Number(result.stderr.match(/^sys\s+([0-9.]+)/m)?.[1] ?? 0),
      maximumResidentSetSizeBytes: Number(result.stderr.match(/^\s*([0-9]+)\s+maximum resident set size/m)?.[1] ?? 0),
    },
    stdout: { bytes: Buffer.byteLength(result.stdout), sha256: sha256Bytes(Buffer.from(result.stdout)) },
    stderr: { bytes: Buffer.byteLength(result.stderr), sha256: sha256Bytes(Buffer.from(result.stderr)) },
    limitReason: result.limitReason ?? null, terminationRequested: result.terminationRequested ?? false,
    logs: { stdout, stderr },
  };
  await writeDurableJson(resolve(attemptPath, 'processes', `${id}.json`), record);
  return record;
}

function requirePass(record, id) {
  if (record.exitCode !== 0 || record.signal !== null) throw new Error(`${id} failed; inspect durable process logs`);
  if (record.limitReason !== null) throw new Error(`${id} exceeded ${record.limitReason}`);
  if (record.logs.stdout.truncated || record.logs.stderr.truncated) throw new Error(`${id} exceeded the captured-log ceiling`);
}

async function enforceOutputBudget(formalPath, attemptPath, contract) {
  const formal = await measureOutput(formalPath);
  const attempt = await measureOutput(attemptPath);
  const output = { formal, attempt, bytes: formal.bytes + attempt.bytes, fileCount: formal.fileCount + attempt.fileCount, symlinkCount: formal.symlinkCount + attempt.symlinkCount };
  if (output.symlinkCount !== 0 || output.bytes > contract.processBudget.projectedWriteBytes) throw new Error('B62 total output budget or symlink policy violated');
  const filesystem = await statfs(repositoryRoot, { bigint: true });
  if (filesystem.bavail * filesystem.bsize < BigInt(contract.processBudget.minimumFreeReserveBytes)) throw new Error('B62 final free-space reserve violated');
  return output;
}

export async function runB62(argv) {
  const parsed = parseArguments(argv);
  const preflightPath = await resolveExistingRepositoryPath(`${parsed.preflightRoot}/preflight.json`, 'B62 preflight');
  const attemptPath = await resolveFreshRepositoryPath(parsed.attemptRoot, 'B62 attempt root');
  const formalPath = await resolveFreshRepositoryPath(parsed.formalRoot, 'B62 formal root');
  const contract = JSON.parse(await readFile(await resolveExistingRepositoryPath(CONTRACT_URI, 'B62 contract'), 'utf8'));
  const correction = JSON.parse(await readFile(await resolveExistingRepositoryPath(CORRECTION_URI, 'B62 C1'), 'utf8'));
  const correction2 = JSON.parse(await readFile(await resolveExistingRepositoryPath(CORRECTION_2_URI, 'B62 C2'), 'utf8'));
  const correction3 = JSON.parse(await readFile(await resolveExistingRepositoryPath(CORRECTION_3_URI, 'B62 C3'), 'utf8'));
  const correction4 = JSON.parse(await readFile(await resolveExistingRepositoryPath(CORRECTION_4_URI, 'B62 C4'), 'utf8'));
  const correction5 = JSON.parse(await readFile(await resolveExistingRepositoryPath(CORRECTION_5_URI, 'B62 C5'), 'utf8'));
  const correction6 = JSON.parse(await readFile(await resolveExistingRepositoryPath(CORRECTION_6_URI, 'B62 C6'), 'utf8'));
  const correction7 = JSON.parse(await readFile(await resolveExistingRepositoryPath(CORRECTION_7_URI, 'B62 C7'), 'utf8'));
  const correction8 = JSON.parse(await readFile(await resolveExistingRepositoryPath(CORRECTION_8_URI, 'B62 C8'), 'utf8'));
  const correction9 = JSON.parse(await readFile(await resolveExistingRepositoryPath(CORRECTION_9_URI, 'B62 C9'), 'utf8'));
  const correction10 = JSON.parse(await readFile(await resolveExistingRepositoryPath(CORRECTION_10_URI, 'B62 C10'), 'utf8'));
  const correction11 = JSON.parse(await readFile(await resolveExistingRepositoryPath(CORRECTION_11_URI, 'B62 C11'), 'utf8'));
  const correction12 = JSON.parse(await readFile(await resolveExistingRepositoryPath(CORRECTION_12_URI, 'B62 C12'), 'utf8'));
  const preflight = JSON.parse(await readFile(preflightPath, 'utf8'));
  if (!validSelfHash(preflight, 'preflightHash') || preflight.status !== 'ACCEPTED' || preflight.toolFreezeCommit !== parsed.toolFreezeCommit) throw new Error('B62 preflight invalid');
  if (correction.statusBeforeExecution !== 'PREREGISTERED' || correction.correction.ffprobeMetadataProcesses !== 1) throw new Error('B62 C1 invalid');
  if (correction2.statusBeforeRetry !== 'PREREGISTERED' || correction2.parent.c1Sha256 !== await sha256File(await resolveExistingRepositoryPath(CORRECTION_URI, 'B62 C1 binding'))) throw new Error('B62 C2 invalid');
  if (correction3.statusBeforeDiagnostic !== 'PREREGISTERED' || correction4.statusBeforeDiagnostic !== 'PREREGISTERED'
    || correction5.statusBeforeProductionToolChange !== 'PREREGISTERED' || correction6.statusBeforeDiagnostic !== 'PREREGISTERED'
    || correction7.statusBeforeDiagnostic !== 'PREREGISTERED' || correction8.statusBeforeProductionToolChange !== 'PREREGISTERED'
    || correction9.statusBeforeFormalToolChange !== 'PREREGISTERED' || correction10.statusBeforeDiagnostic !== 'PREREGISTERED'
    || correction11.statusBeforeAuditorChange !== 'PREREGISTERED' || correction12.statusBeforeFormalToolChange !== 'PREREGISTERED'
    || correction12.authorizedFormalToolChanges.roots.preflight !== parsed.preflightRoot || correction12.authorizedFormalToolChanges.roots.attempt !== parsed.attemptRoot
    || correction12.authorizedFormalToolChanges.roots.formal !== parsed.formalRoot) throw new Error('B62 C3-C12 invalid');
  const toolHashes = await verifyFreeze(parsed, preflightPath);
  await durableMkdir(attemptPath);
  const attempt = await writeDurableHashed(resolve(attemptPath, 'attempt.json'), {
    schemaVersion: 'bfs.b62Phase0Attempt.v0.1', sequence: 1, status: 'STARTED', invocation: parsed,
    preflight: { uri: repoUri(preflightPath), sha256: await sha256File(preflightPath), preflightHash: preflight.preflightHash }, toolHashes,
  }, 'attemptHash');
  const admission = await writeDurableHashed(resolve(attemptPath, 'admission.json'), {
    schemaVersion: 'bfs.b62Phase0Admission.v0.1', sequence: 2, status: 'ACCEPTED', attemptHash: attempt.attemptHash,
    authorized: { blenderStarts: 6, renderCalls: 291, ffmpegProcesses: 1, ffprobeProcesses: 1, nodeAuditorProcesses: 1 },
  }, 'admissionHash');
  const attemptReceipt = await writeDurableHashed(resolve(attemptPath, 'receipt.json'), {
    schemaVersion: 'bfs.b62Phase0AttemptReceipt.v0.1', sequence: 3, status: 'ACCEPTED', admissionHash: admission.admissionHash, formalOutputAuthorized: true,
  }, 'receiptHash');
  await durableMkdir(resolve(attemptPath, 'processes'));
  await durableMkdir(resolve(attemptPath, 'logs'));
  await durableMkdir(formalPath);
  await durableMkdir(resolve(formalPath, 'reports'));
  await writeDurableHashed(resolve(formalPath, 'formal-start.json'), {
    schemaVersion: 'bfs.b62Phase0FormalStart.v0.1', sequence: 4, status: 'AUTHORIZED', attemptReceiptHash: attemptReceipt.receiptHash,
    contract: CONTRACT_URI, corrections: [CORRECTION_URI, CORRECTION_2_URI, CORRECTION_3_URI, CORRECTION_4_URI, CORRECTION_5_URI, CORRECTION_6_URI, CORRECTION_7_URI, CORRECTION_8_URI, CORRECTION_9_URI, CORRECTION_10_URI, CORRECTION_11_URI, CORRECTION_12_URI], toolFreezeCommit: parsed.toolFreezeCommit, preflightEvidenceCommit: parsed.preflightEvidenceCommit,
  }, 'formalStartHash');
  const env = { PATH: '/opt/homebrew/bin:/usr/bin:/bin', LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8', OCIO: resolve(repositoryRoot, 'color/ocio/cg-config-v4.0.0_aces-v2.0_ocio-v2.5.ocio') };
  const maxLog = contract.processBudget.maximumCapturedLogBytesPerProcess;
  const processes = [];
  try {
    let result = await run(BLENDER, ['--background', '--factory-startup', '--disable-autoexec', '--python-exit-code', '1', '--python', resolve(repositoryRoot, 'blender/generate_b62_phase0_assets.py'), '--', '--formal-root', formalPath], env, contract.processBudget.timeoutsSeconds.generator * 1000, maxLog);
    let record = await persistProcess(attemptPath, '01-GENERATOR', 'BLENDER_GENERATOR', result, maxLog); processes.push(record); requirePass(record, record.id); await enforceOutputBudget(formalPath, attemptPath, contract);

    const master = resolve(formalPath, 'scene/B62_PHASE0_MASTER.blend');
    result = await run(BLENDER, ['--background', master, '--disable-autoexec', '--python-exit-code', '1', '--python', resolve(repositoryRoot, 'blender/render_b62_phase0.py'), '--', '--repository-root', repositoryRoot, '--formal-root', formalPath, '--mode', 'animatic'], env, contract.processBudget.timeoutsSeconds.animatic * 1000, maxLog);
    record = await persistProcess(attemptPath, '02-ANIMATIC', 'BLENDER_ANIMATIC', result, maxLog); processes.push(record); requirePass(record, record.id); await enforceOutputBudget(formalPath, attemptPath, contract);

    const video = resolve(formalPath, 'animatic/B62_PHASE0_ANIMATIC.mp4');
    result = await run(FFMPEG, ['-nostdin', '-hide_banner', '-loglevel', 'info', '-framerate', '24', '-start_number', '1', '-i', resolve(formalPath, 'animatic/frame-%04d.png'), '-frames:v', '288', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', video], env, 180000, maxLog);
    record = await persistProcess(attemptPath, '03-FFMPEG', 'FFMPEG_ENCODING', result, maxLog); processes.push(record); requirePass(record, record.id); await enforceOutputBudget(formalPath, attemptPath, contract);

    result = await run(FFPROBE, ['-v', 'error', '-count_frames', '-select_streams', 'v:0', '-show_entries', 'stream=codec_type,avg_frame_rate,nb_read_frames,duration,width,height', '-of', 'json', video], env, 60000, maxLog);
    record = await persistProcess(attemptPath, '04-FFPROBE', 'FFPROBE_METADATA', result, maxLog); processes.push(record); requirePass(record, record.id);
    const probe = JSON.parse(result.stdout);
    await writeDurableHashed(resolve(formalPath, 'reports/video-metadata.json'), {
      schemaVersion: 'bfs.b62Phase0VideoMetadata.v0.1', status: 'PASS', video: { uri: repoUri(video), sha256: await sha256File(video), bytes: (await stat(video)).size }, probe,
    }, 'metadataHash');

    for (const [index, frame] of [48, 144, 240].entries()) {
      result = await run(BLENDER, ['--background', master, '--disable-autoexec', '--python-exit-code', '1', '--python', resolve(repositoryRoot, 'blender/render_b62_phase0.py'), '--', '--repository-root', repositoryRoot, '--formal-root', formalPath, '--mode', 'calibration', '--frame', String(frame)], env, contract.processBudget.timeoutsSeconds.calibrationPerFrame * 1000, maxLog);
      record = await persistProcess(attemptPath, `0${index + 5}-CALIBRATION-${frame}`, 'BLENDER_CALIBRATION', result, maxLog); processes.push(record); requirePass(record, record.id); await enforceOutputBudget(formalPath, attemptPath, contract);
    }

    result = await run(BLENDER, ['--background', master, '--disable-autoexec', '--python-exit-code', '1', '--python', resolve(repositoryRoot, 'blender/audit_b62_phase0.py'), '--', '--repository-root', repositoryRoot, '--formal-root', formalPath, '--output', resolve(formalPath, 'reports/blender-audit.json')], env, contract.processBudget.timeoutsSeconds.independentAudit * 1000, maxLog);
    record = await persistProcess(attemptPath, '08-BLENDER-AUDITOR', 'BLENDER_INDEPENDENT_AUDIT', result, maxLog); processes.push(record); requirePass(record, record.id);

    result = await run(process.execPath, [resolve(repositoryRoot, 'scripts/audit-b62-phase0.mjs'), '--preflight-root', parsed.preflightRoot, '--attempt-root', parsed.attemptRoot, '--formal-root', parsed.formalRoot, '--output', `${parsed.formalRoot}/audit.json`], env, contract.processBudget.timeoutsSeconds.nodeAudit * 1000, maxLog);
    record = await persistProcess(attemptPath, '09-NODE-AUDITOR', 'NODE_INDEPENDENT_AUDIT', result, maxLog); processes.push(record); requirePass(record, record.id);
    const auditPath = resolve(formalPath, 'audit.json');
    const audit = JSON.parse(await readFile(auditPath, 'utf8'));
    if (!validSelfHash(audit, 'auditHash') || audit.status !== 'PASS') throw new Error('B62 Node audit invalid');
    const output = await enforceOutputBudget(formalPath, attemptPath, contract);
    const results = await writeDurableHashed(resolve(formalPath, 'results.json'), {
      schemaVersion: 'bfs.b62Phase0Results.v0.1', experimentId: contract.experimentId, status: 'PASS', verdict: contract.passVerdict,
      audit: { uri: repoUri(auditPath), sha256: await sha256File(auditPath), auditHash: audit.auditHash }, gates: audit.gates, attacks: audit.attacks,
      costs: audit.costs, operations: audit.operations, output, claimBoundary: contract.claimBoundary,
    }, 'resultHash');
    const receipt = await writeDurableHashed(resolve(formalPath, 'receipt.json'), {
      schemaVersion: 'bfs.b62Phase0Receipt.v0.1', experimentId: contract.experimentId, status: 'PASS', verdict: contract.passVerdict,
      authorization: { attemptHash: attempt.attemptHash, admissionHash: admission.admissionHash, attemptReceiptHash: attemptReceipt.receiptHash, preflightHash: preflight.preflightHash },
      toolFreezeCommit: parsed.toolFreezeCommit, preflightEvidenceCommit: parsed.preflightEvidenceCommit,
      results: { uri: `${parsed.formalRoot}/results.json`, sha256: await sha256File(resolve(formalPath, 'results.json')), resultHash: results.resultHash },
      audit: { uri: repoUri(auditPath), sha256: await sha256File(auditPath), auditHash: audit.auditHash },
      operations: audit.operations, claimBoundary: contract.claimBoundary,
    }, 'receiptHash');
    if (!validSelfHash(receipt, 'receiptHash')) throw new Error('B62 final receipt self-hash failed');
    await enforceOutputBudget(formalPath, attemptPath, contract);
    process.stdout.write(`BFS_B62_PHASE0 PASS ${contract.passVerdict} ${receipt.receiptHash}\n`);
    return receipt;
  } catch (error) {
    await writeDurableHashed(resolve(attemptPath, 'failure.json'), {
      schemaVersion: 'bfs.b62Phase0Failure.v0.1', experimentId: contract.experimentId, status: 'INVALIDATED', verdict: contract.failVerdict,
      error: error.message, completedProcessIds: processes.map(row => row.id), formalRoot: parsed.formalRoot,
    }, 'failureHash');
    throw error;
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  runB62(process.argv.slice(2)).catch(error => { process.stderr.write(`BFS_B62_PHASE0_ERROR ${error.message}\n`); process.exitCode = 1; });
}
