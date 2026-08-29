#!/usr/bin/env node

import { createHash } from 'node:crypto';
import {
  closeSync, existsSync, fsyncSync, mkdirSync, openSync, readFileSync, readdirSync,
  statfsSync, statSync, writeFileSync
} from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const repositoryRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const specRelativePath = 'specs/codex-host-stability-longitudinal.v0.1.json';
const specPath = resolve(repositoryRoot, specRelativePath);
const spec = JSON.parse(readFileSync(specPath, 'utf8'));
const formalRoot = resolve(repositoryRoot, spec.formalRoot);
const startPath = resolve(formalRoot, 'start.json');
const resultsPath = resolve(formalRoot, 'results.json');
const commandRecords = [];

function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  if (value && typeof value === 'object') {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}`;
  }
  return JSON.stringify(value);
}

function sha256Bytes(value) {
  return createHash('sha256').update(value).digest('hex');
}

function sha256File(path) {
  return sha256Bytes(readFileSync(path));
}

function withoutSelfHash(value) {
  const clone = structuredClone(value);
  delete clone.selfHash;
  return clone;
}

function verifySelfHash(value, label) {
  if (value.selfHash !== sha256Bytes(canonical(withoutSelfHash(value)))) throw new Error(`${label} self-hash mismatch`);
}

function writeExclusiveDurable(path, value) {
  const fd = openSync(path, 'wx', 0o644);
  try {
    writeFileSync(fd, value, 'utf8');
    fsyncSync(fd);
  } finally {
    closeSync(fd);
  }
  const directoryFd = openSync(dirname(path), 'r');
  try {
    fsyncSync(directoryFd);
  } finally {
    closeSync(directoryFd);
  }
}

function serializeSelfHashed(value, maximumBytes, label) {
  value.selfHash = sha256Bytes(canonical(withoutSelfHash(value)));
  const text = `${JSON.stringify(value, null, 2)}\n`;
  if (Buffer.byteLength(text) > maximumBytes) throw new Error(`${label} exceeds byte ceiling`);
  return text;
}

function runBounded(command, args, label, maxBytes = 524288) {
  const startedAt = Date.now();
  const stdout = execFileSync(command, args, {
    cwd: repositoryRoot,
    encoding: 'utf8',
    timeout: 5000,
    maxBuffer: maxBytes,
    env: { ...process.env, LC_ALL: 'C' }
  });
  if (Buffer.byteLength(stdout) > maxBytes) throw new Error(`${label} exceeded output ceiling`);
  commandRecords.push({ label, durationMs: Date.now() - startedAt, stdoutBytes: Buffer.byteLength(stdout) });
  return stdout;
}

function readPlistString(path, key) {
  const xml = readFileSync(path, 'utf8');
  const match = xml.match(new RegExp(`<key>${key}</key>\\s*<string>([^<]+)</string>`));
  if (!match) throw new Error(`missing plist key ${key}`);
  return match[1];
}

function parseProcesses(stdout) {
  return stdout.split('\n').filter(Boolean).map((line) => {
    const match = line.match(/^\s*(\d+)\s+(\d+)\s+(\d+)\s+(\S+)\s+(.*)$/);
    if (!match) throw new Error('unparseable bounded ps row');
    return {
      pid: Number(match[1]),
      parentPid: Number(match[2]),
      rssBytes: Number(match[3]) * 1024,
      elapsed: match[4],
      command: match[5]
    };
  });
}

function summarizeProcesses(processes) {
  const appPrefix = '/Applications/ChatGPT.app/Contents/';
  const mainPath = '/Applications/ChatGPT.app/Contents/MacOS/ChatGPT';
  const main = processes.filter((item) => item.command === mainPath);
  const renderers = processes.filter((item) => item.command.includes('/Codex (Renderer).app/Contents/MacOS/Codex (Renderer)'));
  const tree = processes.filter((item) => item.command.startsWith(appPrefix));
  const crashpads = processes.filter((item) => item.command.includes('/browser_crashpad_handler'));
  return {
    mainCodexProcessCount: main.length,
    mainCodexPids: main.map((item) => item.pid).sort((a, b) => a - b),
    rendererCount: renderers.length,
    maximumRendererRssBytes: Math.max(0, ...renderers.map((item) => item.rssBytes)),
    codexTreeRssBytes: tree.reduce((sum, item) => sum + item.rssBytes, 0),
    activeBlenderProcessCount: processes.filter((item) => item.command.startsWith('/Applications/Blender.app/Contents/MacOS/Blender')).length,
    activeB58WorkerProcessCount: processes.filter((item) => /(?:run-restart-safe-production-job|preflight-b58-e1|run-b58-e1|audit-b58-e1)[.]mjs/.test(item.command)).length,
    browserAutomationProcessCount: processes.filter((item) => /(?:^|[/ ])(?:agent-browser|chromedriver)(?:$|[/ ])|playwright/.test(item.command)).length,
    crashpadHandlerCount: crashpads.length,
    orphanCrashpadHandlerCount: crashpads.filter((item) => item.parentPid === 1).length
  };
}

function allocatedTree(path, maximumEntries) {
  let allocatedBytes = 0;
  let entries = 0;
  const pending = [path];
  while (pending.length) {
    const current = pending.pop();
    if (!existsSync(current)) continue;
    const stats = statSync(current);
    entries += 1;
    if (entries > maximumEntries) throw new Error('browser temporary filesystem entry ceiling exceeded');
    allocatedBytes += Number(stats.blocks ?? Math.ceil(stats.size / 512)) * 512;
    if (stats.isDirectory()) {
      for (const name of readdirSync(current)) pending.push(join(current, name));
    }
  }
  return { allocatedBytes, entries };
}

function matchingCrashReports(path, afterMs) {
  if (!existsSync(path)) return [];
  return readdirSync(path)
    .filter((name) => /^ChatGPT.*[.]ips$/.test(name))
    .map((name) => ({ name, modifiedMs: statSync(join(path, name)).mtimeMs }))
    .filter((item) => item.modifiedMs > afterMs)
    .sort((a, b) => a.name.localeCompare(b.name));
}

function releaseIdentity(label) {
  const scopedStatus = runBounded('/usr/bin/git', ['status', '--short', '--', ...spec.releasePaths], `${label}-git-status`, 32768).trim();
  const [headCommit, originMainCommit] = runBounded('/usr/bin/git', ['rev-parse', 'HEAD', 'origin/main'], `${label}-git-identities`, 4096).trim().split('\n');
  let parentIsAncestor = true;
  try {
    runBounded('/usr/bin/git', ['merge-base', '--is-ancestor', spec.parentCommit, headCommit], `${label}-git-ancestor`, 4096);
  } catch {
    parentIsAncestor = false;
  }
  return { scopedStatus, headCommit, originMainCommit, parentIsAncestor };
}

function captureSample(index, scheduledAtMs, experimentStartedAtMs) {
  const appPlist = spec.runtimeExpectation.appPlistPath;
  const filesystem = statfsSync('/');
  const memoryOutput = runBounded('/usr/bin/memory_pressure', ['-Q'], `sample-${index}-memory`, 32768);
  const memoryMatch = memoryOutput.match(/System-wide memory free percentage:\s*(\d+)%/);
  if (!memoryMatch) throw new Error('memory_pressure output missing free percentage');
  const processes = summarizeProcesses(parseProcesses(runBounded('/bin/ps', ['-axo', 'pid=,ppid=,rss=,etime=,command='], `sample-${index}-processes`)));
  const capturedAtMs = Date.now();
  const sample = {
    schemaVersion: 'bfs.codex-host-stability-longitudinal-sample.v0.1',
    experimentId: spec.experimentId,
    index,
    scheduledAt: new Date(scheduledAtMs).toISOString(),
    capturedAt: new Date(capturedAtMs).toISOString(),
    latenessMs: capturedAtMs - scheduledAtMs,
    runtime: {
      codexVersion: `${readPlistString(appPlist, 'CFBundleShortVersionString')} (${readPlistString(appPlist, 'CFBundleVersion')})`,
      appPlistSha256: sha256File(appPlist),
      bundleIdentifier: readPlistString(appPlist, 'CFBundleIdentifier')
    },
    disk: { availableBytes: Number(filesystem.bavail * filesystem.bsize) },
    memory: { systemWideFreePercent: Number(memoryMatch[1]) },
    processes,
    browserTempFilesystem: allocatedTree(spec.observationPolicy.browserTempFilesystemPath, spec.observationPolicy.maximumFilesystemEntries),
    newCrashReports: matchingCrashReports(spec.observationPolicy.diagnosticReportsPath, experimentStartedAtMs),
    selfHash: ''
  };
  return sample;
}

function samplePath(index) {
  return resolve(formalRoot, `sample-${String(index).padStart(3, '0')}.json`);
}

function readAndVerifySample(index) {
  const path = samplePath(index);
  const text = readFileSync(path, 'utf8');
  if (Buffer.byteLength(text) > spec.resourcePolicy.maximumSampleBytes) throw new Error(`sample ${index} exceeds byte ceiling`);
  const sample = JSON.parse(text);
  verifySelfHash(sample, `sample ${index}`);
  if (sample.experimentId !== spec.experimentId || sample.index !== index) throw new Error(`sample ${index} identity mismatch`);
  return { sample, sha256: sha256Bytes(text), bytes: Buffer.byteLength(text), path };
}

function aggregateGates(start, sampleReceipts, endRelease) {
  const samples = sampleReceipts.map((item) => item.sample);
  const first = samples[0];
  const last = samples.at(-1);
  const intervalsMs = samples.slice(1).map((sample, index) => Date.parse(sample.capturedAt) - Date.parse(samples[index].capturedAt));
  const totalSpanMs = Date.parse(last.capturedAt) - Date.parse(first.capturedAt);
  const rssGrowthBytes = last.processes.codexTreeRssBytes - first.processes.codexTreeRssBytes;
  const diskLossBytes = first.disk.availableBytes - last.disk.availableBytes;
  const browserGrowthBytes = last.browserTempFilesystem.allocatedBytes - first.browserTempFilesystem.allocatedBytes;
  const parentResultsSha = sha256File(resolve(repositoryRoot, spec.parentEvidence.resultsPath));
  const parentAuditSha = sha256File(resolve(repositoryRoot, spec.parentEvidence.auditPath));
  const runtimeIdentity = samples.every((sample) => sample.runtime.codexVersion === spec.runtimeExpectation.codexVersion
    && sample.runtime.appPlistSha256 === spec.runtimeExpectation.appPlistSha256
    && sample.runtime.bundleIdentifier === spec.runtimeExpectation.bundleIdentifier);
  const mainContinuity = samples.every((sample) => sample.processes.mainCodexProcessCount === spec.processPolicy.requiredMainCodexProcessCount
    && sample.processes.mainCodexPids.length === 1
    && sample.processes.mainCodexPids[0] === spec.runtimeExpectation.requiredMainPid
    && !sample.processes.mainCodexPids.includes(spec.runtimeExpectation.forbiddenPreviousMainPid));
  const perSampleResources = samples.every((sample) => sample.disk.availableBytes >= spec.resourcePolicy.minimumAvailableBytes
    && sample.memory.systemWideFreePercent >= spec.resourcePolicy.minimumMemoryFreePercent
    && sample.processes.rendererCount <= spec.resourcePolicy.maximumCodexRendererCount
    && sample.processes.maximumRendererRssBytes <= spec.resourcePolicy.maximumSingleRendererRssBytes
    && sample.processes.codexTreeRssBytes <= spec.resourcePolicy.maximumCodexTreeRssBytes);
  const forbiddenAbsent = samples.every((sample) => sample.processes.activeBlenderProcessCount === spec.processPolicy.requiredActiveBlenderProcessCount
    && sample.processes.activeB58WorkerProcessCount === spec.processPolicy.requiredActiveB58WorkerProcessCount
    && sample.processes.browserAutomationProcessCount === spec.processPolicy.requiredBrowserAutomationProcessCount);
  const sampleOrder = samples.every((sample, index) => sample.index === index + 1);
  const sampleHashesValid = sampleReceipts.every((item) => item.sample.selfHash === sha256Bytes(canonical(withoutSelfHash(item.sample)))
    && item.bytes <= spec.resourcePolicy.maximumSampleBytes);
  return {
    aggregate: { intervalsMs, totalSpanMs, rssGrowthBytes, diskLossBytes, browserGrowthBytes },
    gates: {
      SPEC_PARENT_AND_RELEASE_IDENTITY: start.specSha256 === sha256File(specPath)
        && start.git.scopedStatus === '' && endRelease.scopedStatus === ''
        && start.git.headCommit === start.git.originMainCommit
        && endRelease.headCommit === endRelease.originMainCommit
        && start.git.headCommit === endRelease.headCommit
        && start.git.parentIsAncestor && endRelease.parentIsAncestor,
      PARENT_EVIDENCE_IDENTITY: parentResultsSha === spec.parentEvidence.resultsSha256
        && parentAuditSha === spec.parentEvidence.auditSha256,
      SAMPLE_COUNT_AND_ORDER: samples.length === spec.observationPolicy.requiredSampleCount && sampleOrder,
      TIMING_WINDOW: intervalsMs.every((value) => value >= spec.observationPolicy.minimumIntervalSeconds * 1000)
        && totalSpanMs >= spec.observationPolicy.minimumTotalSpanSeconds * 1000
        && samples.every((sample) => sample.latenessMs >= 0 && sample.latenessMs <= spec.observationPolicy.maximumSampleLatenessSeconds * 1000),
      RUNTIME_IDENTITY: runtimeIdentity,
      MAIN_PROCESS_CONTINUITY: mainContinuity,
      PER_SAMPLE_RESOURCE_CEILINGS: perSampleResources,
      RSS_GROWTH_BOUNDED: rssGrowthBytes <= spec.observationPolicy.maximumCodexTreeRssGrowthBytes,
      DISK_RETENTION_BOUNDED: diskLossBytes <= spec.observationPolicy.maximumDiskLossBytes,
      BROWSER_TEMP_FILESYSTEM_BOUNDED: samples.every((sample) => sample.browserTempFilesystem.allocatedBytes <= spec.observationPolicy.maximumBrowserTempFilesystemBytes)
        && browserGrowthBytes <= spec.observationPolicy.maximumBrowserTempFilesystemGrowthBytes,
      NO_FORBIDDEN_PROCESS: forbiddenAbsent,
      NO_NEW_CODEX_CRASH_REPORT: samples.every((sample) => sample.newCrashReports.length === 0),
      RESOURCE_ACCOUNTING_ZERO: true,
      EVIDENCE_BOUNDED_AND_SELF_HASHED: sampleHashesValid,
      INDEPENDENT_AUDIT_REPLAY: 'PENDING'
    }
  };
}

function waitUntil(targetMs) {
  const remaining = targetMs - Date.now();
  if (remaining <= 0) return Promise.resolve();
  return new Promise((resolveWait) => setTimeout(resolveWait, Math.min(remaining, 30000))).then(() => waitUntil(targetMs));
}

if (existsSync(resultsPath)) throw new Error('formal results already exist; immutable run cannot be repeated');

let start;
if (!existsSync(formalRoot)) {
  const git = releaseIdentity('start');
  if (git.scopedStatus || git.headCommit !== git.originMainCommit || !git.parentIsAncestor) throw new Error('release identity preflight failed');
  mkdirSync(formalRoot, { recursive: false });
  start = {
    schemaVersion: 'bfs.codex-host-stability-longitudinal-start.v0.1',
    experimentId: spec.experimentId,
    startedAt: new Date().toISOString(),
    specPath: specRelativePath,
    specSha256: sha256File(specPath),
    git,
    parentEvidence: {
      resultsSha256: sha256File(resolve(repositoryRoot, spec.parentEvidence.resultsPath)),
      auditSha256: sha256File(resolve(repositoryRoot, spec.parentEvidence.auditPath))
    },
    resourceAccounting: {
      blenderProcesses: 0, renderProcesses: 0, browserAutomationCalls: 0, networkCalls: 0,
      modelCalls: 0, dockerCalls: 0, cleanupOperations: 0, signalsSent: 0, hostRestarts: 0, codexRestarts: 0
    },
    selfHash: ''
  };
  writeExclusiveDurable(startPath, serializeSelfHashed(start, spec.resourcePolicy.maximumSampleBytes, 'start receipt'));
} else {
  if (!existsSync(startPath)) throw new Error('formal root exists without start receipt');
  start = JSON.parse(readFileSync(startPath, 'utf8'));
  verifySelfHash(start, 'start receipt');
  if (start.specSha256 !== sha256File(specPath) || start.experimentId !== spec.experimentId) throw new Error('resume identity mismatch');
}

const startedAtMs = Date.parse(start.startedAt);
for (let index = 1; index <= spec.observationPolicy.requiredSampleCount; index += 1) {
  const dueMs = startedAtMs + (index - 1) * spec.observationPolicy.minimumIntervalSeconds * 1000;
  const path = samplePath(index);
  if (!existsSync(path)) {
    await waitUntil(dueMs);
    const sample = captureSample(index, dueMs, startedAtMs);
    writeExclusiveDurable(path, serializeSelfHashed(sample, spec.resourcePolicy.maximumSampleBytes, `sample ${index}`));
    process.stderr.write(`R3 sample ${index}/${spec.observationPolicy.requiredSampleCount} captured\n`);
  }
  readAndVerifySample(index);
}

const sampleReceipts = [];
for (let index = 1; index <= spec.observationPolicy.requiredSampleCount; index += 1) sampleReceipts.push(readAndVerifySample(index));
const endRelease = releaseIdentity('end');
const { aggregate, gates } = aggregateGates(start, sampleReceipts, endRelease);
const admissionNames = spec.requiredGates.filter((name) => name !== 'INDEPENDENT_AUDIT_REPLAY');
const failedGates = admissionNames.filter((name) => gates[name] !== true);
const provisionalVerdict = failedGates.length ? 'BLOCKED_HOST_STABILITY' : 'ADMITTED_PENDING_AUDIT';
const results = {
  schemaVersion: 'bfs.codex-host-stability-longitudinal-results.v0.1',
  experimentId: spec.experimentId,
  completedAt: new Date().toISOString(),
  spec: { path: specRelativePath, sha256: sha256File(specPath) },
  git: { start: start.git, end: endRelease },
  parentEvidence: start.parentEvidence,
  startReceipt: { path: `${spec.formalRoot}/start.json`, sha256: sha256File(startPath), selfHash: start.selfHash, bytes: statSync(startPath).size },
  sampleReceipts: sampleReceipts.map((item) => ({
    index: item.sample.index,
    path: `${spec.formalRoot}/sample-${String(item.sample.index).padStart(3, '0')}.json`,
    sha256: item.sha256,
    selfHash: item.sample.selfHash,
    bytes: item.bytes
  })),
  aggregate,
  resourceAccounting: {
    ...start.resourceAccounting,
    observationCommands: commandRecords.length
  },
  gates,
  failedGates,
  provisionalVerdict,
  receiptBytes: 0,
  selfHash: ''
};

let resultsText = '';
for (let index = 0; index < 8; index += 1) {
  results.selfHash = sha256Bytes(canonical(withoutSelfHash(results)));
  resultsText = `${JSON.stringify(results, null, 2)}\n`;
  const nextBytes = Buffer.byteLength(resultsText);
  if (nextBytes === results.receiptBytes) break;
  results.receiptBytes = nextBytes;
}
results.selfHash = sha256Bytes(canonical(withoutSelfHash(results)));
resultsText = `${JSON.stringify(results, null, 2)}\n`;
results.receiptBytes = Buffer.byteLength(resultsText);
results.selfHash = sha256Bytes(canonical(withoutSelfHash(results)));
resultsText = `${JSON.stringify(results, null, 2)}\n`;
if (Buffer.byteLength(resultsText) > spec.resourcePolicy.maximumResultsBytes) throw new Error('results exceed byte ceiling');
if (results.resourceAccounting.observationCommands > spec.formalCeilings.maximumObservationCommands) throw new Error('observation command ceiling exceeded');
writeExclusiveDurable(resultsPath, resultsText);

const summaryText = `${JSON.stringify({
  experimentId: spec.experimentId,
  provisionalVerdict,
  gates: `${admissionNames.filter((name) => gates[name] === true).length}/${admissionNames.length}`,
  failedGates,
  resultsPath: `${spec.formalRoot}/results.json`
})}\n`;
if (Buffer.byteLength(summaryText) > spec.resourcePolicy.maximumStdoutBytes) throw new Error('summary exceeds byte ceiling');
process.stdout.write(summaryText);
