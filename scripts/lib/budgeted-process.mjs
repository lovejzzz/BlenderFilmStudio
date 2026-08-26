import { execFile } from 'node:child_process';
import { createHash } from 'node:crypto';
import { lstat, readdir } from 'node:fs/promises';
import { performance } from 'node:perf_hooks';
import { spawn } from 'node:child_process';
import { setTimeout as delay } from 'node:timers/promises';

const REASONS = new Set(['WALL_TIME', 'RSS_BYTES', 'LOG_BYTES', 'OUTPUT_FILES', 'OUTPUT_BYTES']);

function requirePositiveInteger(value, label) {
  if (!Number.isSafeInteger(value) || value <= 0) throw new Error(`${label} must be a positive safe integer`);
}

export function validateBudgets(budgets) {
  for (const key of ['wallTimeMs', 'maxRssBytes', 'maxLogBytes', 'maxOutputFiles', 'maxOutputBytes', 'sampleIntervalMs']) requirePositiveInteger(budgets[key], key);
  return budgets;
}

export async function measureOutput(root) {
  const totals = { fileCount: 0, bytes: 0, symlinkCount: 0 };
  async function visit(directory) {
    let entries;
    try { entries = await readdir(directory, { withFileTypes: true }); } catch (error) {
      if (error.code === 'ENOENT') return;
      throw error;
    }
    for (const entry of entries) {
      const path = `${directory}/${entry.name}`;
      if (entry.isSymbolicLink()) { totals.symlinkCount += 1; continue; }
      if (entry.isDirectory()) { await visit(path); continue; }
      if (entry.isFile()) {
        const metadata = await lstat(path);
        totals.fileCount += 1;
        totals.bytes += metadata.size;
      }
    }
  }
  await visit(root);
  return totals;
}

function sampleRootRss(pid) {
  return new Promise(resolve => {
    execFile('/bin/ps', ['-o', 'rss=', '-p', String(pid)], { timeout: 1000 }, (error, stdout) => {
      if (error) { resolve(null); return; }
      const kibibytes = Number.parseInt(stdout.trim(), 10);
      resolve(Number.isFinite(kibibytes) ? kibibytes * 1024 : null);
    });
  });
}

export async function runBudgetedProcess({ command, args = [], cwd, env = process.env, outputRoot, budgets }) {
  validateBudgets(budgets);
  const started = performance.now();
  const child = spawn(command, args, { cwd, env, detached: process.platform !== 'win32', stdio: ['ignore', 'pipe', 'pipe'] });
  let closed = false;
  let spawnError = null;
  let logBytes = 0;
  let peakSampledRssBytes = 0;
  let breach = null;
  let monitorBusy = false;
  let terminationRequested = false;
  let forceTimer = null;
  const previewChunks = [];
  let previewBytes = 0;
  const logSha256 = createHash('sha256');

  function terminate() {
    if (closed || terminationRequested) return;
    terminationRequested = true;
    const signalTarget = process.platform === 'win32' ? child.pid : -child.pid;
    try { process.kill(signalTarget, 'SIGTERM'); } catch { try { child.kill('SIGTERM'); } catch {} }
    forceTimer = setTimeout(() => {
      if (closed) return;
      try { process.kill(signalTarget, 'SIGKILL'); } catch { try { child.kill('SIGKILL'); } catch {} }
    }, 500);
  }

  function recordBreach(reason, observed, limit) {
    if (breach) return;
    if (!REASONS.has(reason)) throw new Error(`Unknown budget reason ${reason}`);
    breach = { reason, observed, limit };
    terminate();
  }

  function recordLog(chunk) {
    logBytes += chunk.length;
    logSha256.update(chunk);
    if (previewBytes < 4096) {
      const slice = chunk.subarray(0, 4096 - previewBytes);
      previewChunks.push(slice);
      previewBytes += slice.length;
    }
    if (logBytes > budgets.maxLogBytes) recordBreach('LOG_BYTES', logBytes, budgets.maxLogBytes);
  }
  child.stdout.on('data', recordLog);
  child.stderr.on('data', recordLog);

  const completion = new Promise(resolve => {
    child.on('error', error => { spawnError = error; });
    child.on('close', (code, signal) => { closed = true; resolve({ code, signal }); });
  });

  async function monitor() {
    if (closed || monitorBusy || breach) return;
    monitorBusy = true;
    try {
      const elapsedMs = performance.now() - started;
      if (elapsedMs > budgets.wallTimeMs) { recordBreach('WALL_TIME', Math.ceil(elapsedMs), budgets.wallTimeMs); return; }
      const rss = await sampleRootRss(child.pid);
      if (rss !== null) peakSampledRssBytes = Math.max(peakSampledRssBytes, rss);
      if (rss !== null && rss > budgets.maxRssBytes) { recordBreach('RSS_BYTES', rss, budgets.maxRssBytes); return; }
      const output = await measureOutput(outputRoot);
      if (output.fileCount > budgets.maxOutputFiles) { recordBreach('OUTPUT_FILES', output.fileCount, budgets.maxOutputFiles); return; }
      if (output.bytes > budgets.maxOutputBytes) recordBreach('OUTPUT_BYTES', output.bytes, budgets.maxOutputBytes);
    } finally {
      monitorBusy = false;
    }
  }

  await monitor();
  const interval = setInterval(() => { void monitor(); }, budgets.sampleIntervalMs);
  const completionResult = await completion;
  clearInterval(interval);
  if (forceTimer) clearTimeout(forceTimer);
  while (monitorBusy) await delay(1);
  const finalOutput = await measureOutput(outputRoot);
  const elapsedMs = Math.ceil(performance.now() - started);
  if (!breach && elapsedMs > budgets.wallTimeMs) breach = { reason: 'WALL_TIME', observed: elapsedMs, limit: budgets.wallTimeMs };
  if (!breach && finalOutput.fileCount > budgets.maxOutputFiles) breach = { reason: 'OUTPUT_FILES', observed: finalOutput.fileCount, limit: budgets.maxOutputFiles };
  if (!breach && finalOutput.bytes > budgets.maxOutputBytes) breach = { reason: 'OUTPUT_BYTES', observed: finalOutput.bytes, limit: budgets.maxOutputBytes };
  const outcome = breach ? 'BUDGET_EXCEEDED' : spawnError || completionResult.code !== 0 ? 'CHILD_FAILED' : 'PASS';
  return {
    documentType: 'BFS_BUDGETED_PROCESS_RESULT', version: '0.1.0', outcome,
    command, args, budgets, metrics: { elapsedMs, peakSampledRssBytes, logBytes, output: finalOutput },
    breach, child: { exitCode: completionResult.code, signal: completionResult.signal, spawnError: spawnError?.message ?? null },
    termination: { requested: terminationRequested, awaited: true },
    logSha256: logSha256.digest('hex'),
    outputPreview: Buffer.concat(previewChunks).toString('utf8'),
    outputPreviewTruncated: logBytes > previewBytes,
  };
}
