#!/usr/bin/env node

import { createHash } from 'node:crypto';
import { closeSync, existsSync, mkdirSync, openSync, readFileSync, statfsSync, writeFileSync, fsyncSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const repositoryRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const defaultSpecRelativePath = 'specs/codex-host-stability-baseline.v0.1.json';
let specRelativePath = defaultSpecRelativePath;
if (process.argv.length > 2) {
  if (process.argv.length !== 4 || process.argv[2] !== '--spec') throw new Error('usage: runner [--spec specs/name.json]');
  specRelativePath = process.argv[3];
}
if (!/^specs\/[A-Za-z0-9._/-]+[.]json$/.test(specRelativePath) || specRelativePath.includes('..')) {
  throw new Error('spec path must be a repository-relative specs/*.json path');
}
const specPath = resolve(repositoryRoot, specRelativePath);
const spec = JSON.parse(readFileSync(specPath, 'utf8'));
const formalRoot = resolve(repositoryRoot, spec.formalRoot);
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

function runBounded(command, args, label, maxBytes = 524288) {
  const startedAt = Date.now();
  const stdout = execFileSync(command, args, {
    cwd: repositoryRoot,
    encoding: 'utf8',
    timeout: 5000,
    maxBuffer: maxBytes,
    env: { ...process.env, LC_ALL: 'C' }
  });
  const bytes = Buffer.byteLength(stdout);
  if (bytes > maxBytes) throw new Error(`${label} exceeded ${maxBytes} bytes`);
  commandRecords.push({ label, exitCode: 0, stdoutBytes: bytes, durationMs: Date.now() - startedAt });
  return stdout;
}

function readPlistString(path, key) {
  const xml = readFileSync(path, 'utf8');
  const match = xml.match(new RegExp(`<key>${key}</key>\\s*<string>([^<]+)</string>`));
  if (!match) throw new Error(`missing plist key ${key} in ${path}`);
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
  const codexPrefix = '/Applications/ChatGPT.app/Contents/';
  const mainPath = '/Applications/ChatGPT.app/Contents/MacOS/ChatGPT';
  const mainProcesses = processes.filter((item) => item.command === mainPath);
  const renderers = processes.filter((item) => item.command.includes('/Codex (Renderer).app/Contents/MacOS/Codex (Renderer)'));
  const codexTree = processes.filter((item) => item.command.startsWith(codexPrefix));
  const crashpads = processes.filter((item) => item.command.includes('/browser_crashpad_handler'));
  const blender = processes.filter((item) => item.command.startsWith('/Applications/Blender.app/Contents/MacOS/Blender'));
  const b58 = processes.filter((item) => /(?:run-restart-safe-production-job|preflight-b58-e1|run-b58-e1|audit-b58-e1)[.]mjs/.test(item.command));
  const browserAutomation = processes.filter((item) => /(?:^|[/ ])(?:agent-browser|chromedriver)(?:$|[/ ])|playwright/.test(item.command));
  return {
    mainCodexProcessCount: mainProcesses.length,
    mainCodexPids: mainProcesses.map((item) => item.pid).sort((left, right) => left - right),
    rendererCount: renderers.length,
    maximumRendererRssBytes: Math.max(0, ...renderers.map((item) => item.rssBytes)),
    codexTreeRssBytes: codexTree.reduce((sum, item) => sum + item.rssBytes, 0),
    activeBlenderProcessCount: blender.length,
    activeB58WorkerProcessCount: b58.length,
    browserAutomationProcessCount: browserAutomation.length,
    crashpadHandlerCount: crashpads.length,
    orphanCrashpadHandlerCount: crashpads.filter((item) => item.parentPid === 1).length
  };
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

if (existsSync(formalRoot)) throw new Error(`formal root is not fresh: ${formalRoot}`);

const defaultReleasePaths = [
  'specs/codex-host-stability-baseline.v0.1.json',
  'research/2026-08-28-b59-g0-codex-host-stability-baseline-protocol.md',
  'scripts/run-b59-g0-codex-host-stability-baseline.mjs',
  'scripts/audit-b59-g0-codex-host-stability-baseline.mjs'
];
const releasePaths = spec.releasePaths ?? defaultReleasePaths;
const scopedStatus = runBounded('/usr/bin/git', ['status', '--short', '--', ...releasePaths], 'git-scoped-status', 32768).trim();
if (scopedStatus) throw new Error(`scoped release files are dirty: ${scopedStatus}`);

const [headCommit, originMainCommit] = runBounded('/usr/bin/git', ['rev-parse', 'HEAD', 'origin/main'], 'git-identities', 4096).trim().split('\n');
let parentIsAncestor = true;
try {
  runBounded('/usr/bin/git', ['merge-base', '--is-ancestor', spec.parentCommit, headCommit], 'git-parent-ancestry', 4096);
} catch {
  parentIsAncestor = false;
  commandRecords.push({ label: 'git-parent-ancestry', exitCode: 1, stdoutBytes: 0, durationMs: 0 });
}

const crashBytes = readFileSync(spec.crashEvidence.sourcePath);
const crashText = crashBytes.toString('utf8');
const crashLineCount = (crashText.match(/\n/g) ?? []).length;
const crash = {
  path: spec.crashEvidence.sourcePath,
  sha256: sha256Bytes(crashBytes),
  bytes: crashBytes.length,
  lines: crashLineCount,
  processExact: crashText.includes('Process:             ChatGPT [91700]'),
  identifierExact: crashText.includes('Identifier:          com.openai.codex'),
  versionExact: crashText.includes(`Version:             ${spec.crashEvidence.version}`),
  threadExact: crashText.includes('Triggered by Thread: 20  Chrome_IOThread'),
  exceptionExact: crashText.includes('Exception Type:    EXC_BREAKPOINT (SIGTRAP)'),
  serializerSymbolPresent: crashText.includes('v8::ValueSerializer::WriteValue')
};

const appPlist = '/Applications/ChatGPT.app/Contents/Info.plist';
const systemPlist = '/System/Library/CoreServices/SystemVersion.plist';
const currentVersion = `${readPlistString(appPlist, 'CFBundleShortVersionString')} (${readPlistString(appPlist, 'CFBundleVersion')})`;
const expectedCurrentVersion = spec.currentRuntimeExpectation?.codexVersion ?? spec.crashEvidence.version;
const currentAppPlistSha256 = sha256File(appPlist);
const currentBundleIdentifier = readPlistString(appPlist, 'CFBundleIdentifier');
const currentRuntimeIdentityMatches = !spec.currentRuntimeExpectation
  || (currentAppPlistSha256 === spec.currentRuntimeExpectation.appPlistSha256
    && currentBundleIdentifier === spec.currentRuntimeExpectation.bundleIdentifier);
const currentOsVersion = `macOS ${readPlistString(systemPlist, 'ProductUserVisibleVersion')} (${readPlistString(systemPlist, 'ProductBuildVersion')})`;

const filesystem = statfsSync('/');
const availableBytes = Number(filesystem.bavail * filesystem.bsize);
const minimumAvailableBytes = spec.resourcePolicy.minimumCoreDiskReserveBytes
  + spec.resourcePolicy.b58ProjectedWriteBytes
  + spec.resourcePolicy.additionalStabilityMarginBytes;
const disk = {
  availableBytes,
  minimumCoreDiskReserveBytes: spec.resourcePolicy.minimumCoreDiskReserveBytes,
  b58ProjectedWriteBytes: spec.resourcePolicy.b58ProjectedWriteBytes,
  additionalStabilityMarginBytes: spec.resourcePolicy.additionalStabilityMarginBytes,
  minimumAvailableBytes,
  headroomBytes: availableBytes - minimumAvailableBytes
};

const memoryOutput = runBounded('/usr/bin/memory_pressure', ['-Q'], 'memory-pressure', 32768);
const memoryMatch = memoryOutput.match(/System-wide memory free percentage:\s*(\d+)%/);
if (!memoryMatch) throw new Error('memory_pressure output missing free percentage');
const memory = { systemWideFreePercent: Number(memoryMatch[1]), minimumFreePercent: spec.resourcePolicy.minimumMemoryFreePercent };

const processes = parseProcesses(runBounded('/bin/ps', ['-axo', 'pid=,ppid=,rss=,etime=,command='], 'process-snapshot'));
const processSummary = summarizeProcesses(processes);
const restartBoundary = spec.restartBoundary ? {
  previousMainPid: spec.restartBoundary.previousMainPid,
  currentMainPids: processSummary.mainCodexPids,
  oldPidPresent: processSummary.mainCodexPids.includes(spec.restartBoundary.previousMainPid),
  currentPidDifferent: processSummary.mainCodexPids.length === 1 && processSummary.mainCodexPids[0] !== spec.restartBoundary.previousMainPid,
  valid: processSummary.mainCodexPids.length === spec.restartBoundary.requiredCurrentMainProcessCount
    && !processSummary.mainCodexPids.includes(spec.restartBoundary.previousMainPid)
} : null;

const capturedAt = new Date().toISOString();
const specSha256 = sha256File(specPath);
const parentEvidence = spec.parentEvidence ? {
  resultsSha256: sha256File(resolve(repositoryRoot, spec.parentEvidence.resultsPath)),
  auditSha256: sha256File(resolve(repositoryRoot, spec.parentEvidence.auditPath)),
  valid: sha256File(resolve(repositoryRoot, spec.parentEvidence.resultsPath)) === spec.parentEvidence.resultsSha256
    && sha256File(resolve(repositoryRoot, spec.parentEvidence.auditPath)) === spec.parentEvidence.auditSha256
} : null;
const gates = {
  SPEC_AND_PARENT_IDENTITY: specSha256.length === 64 && parentIsAncestor && headCommit === originMainCommit && (parentEvidence?.valid ?? true),
  FRESH_FORMAL_ROOT: true,
  CRASH_EVIDENCE_IDENTITY: crash.sha256 === spec.crashEvidence.sha256 && crash.bytes === spec.crashEvidence.bytes && crash.lines === spec.crashEvidence.lines,
  CRASH_SIGNATURE_EXACT: crash.processExact && crash.identifierExact && crash.versionExact && crash.threadExact && crash.exceptionExact && crash.serializerSymbolPresent,
  CURRENT_CODEX_VERSION_EXACT: currentVersion === expectedCurrentVersion && currentRuntimeIdentityMatches,
  SNAPSHOT_FRESHNESS: true,
  DISK_STABILITY_MARGIN: disk.availableBytes >= disk.minimumAvailableBytes,
  MEMORY_PRESSURE: memory.systemWideFreePercent >= memory.minimumFreePercent,
  CODEX_MAIN_PROCESS_COUNT: processSummary.mainCodexProcessCount === spec.processPolicy.requiredMainCodexProcessCount && (restartBoundary?.valid ?? true),
  CODEX_RENDERER_COUNT: processSummary.rendererCount <= spec.resourcePolicy.maximumCodexRendererCount,
  SINGLE_RENDERER_RSS: processSummary.maximumRendererRssBytes <= spec.resourcePolicy.maximumSingleRendererRssBytes,
  CODEX_TREE_RSS: processSummary.codexTreeRssBytes <= spec.resourcePolicy.maximumCodexTreeRssBytes,
  NO_ACTIVE_BLENDER: processSummary.activeBlenderProcessCount === spec.processPolicy.requiredActiveBlenderProcessCount,
  NO_ACTIVE_B58_WORKER: processSummary.activeB58WorkerProcessCount === spec.processPolicy.requiredActiveB58WorkerProcessCount,
  NO_BROWSER_AUTOMATION_PROCESS: processSummary.browserAutomationProcessCount === spec.processPolicy.requiredBrowserAutomationProcessCount,
  RESOURCE_CEILINGS_ZERO: true,
  STDOUT_BOUNDED: true,
  RECEIPT_BOUNDED: true,
  RECEIPT_SELF_HASH: true,
  INDEPENDENT_AUDIT_REPLAY: 'PENDING'
};

const admissionGateNames = spec.requiredGates.filter((name) => name !== 'INDEPENDENT_AUDIT_REPLAY');
const failedGates = admissionGateNames.filter((name) => gates[name] !== true);
const provisionalVerdict = failedGates.length ? 'BLOCKED_HOST_STABILITY' : 'ADMITTED_PENDING_AUDIT';
const summary = {
  schemaVersion: 'bfs.codex-host-stability-baseline-summary.v0.1',
  experimentId: spec.experimentId,
  provisionalVerdict,
  failedGates,
  resultsPath: spec.formalRoot + '/results.json'
};
const summaryText = `${JSON.stringify(summary)}\n`;
gates.STDOUT_BOUNDED = Buffer.byteLength(summaryText) <= spec.resourcePolicy.maximumStdoutBytes;

const results = {
  schemaVersion: 'bfs.codex-host-stability-baseline-results.v0.1',
  experimentId: spec.experimentId,
  capturedAt,
  git: { headCommit, originMainCommit, specParentCommit: spec.parentCommit, parentIsAncestor, scopedStatus },
  spec: { path: specRelativePath, sha256: specSha256 },
  parentEvidence,
  formalRoot: spec.formalRoot,
  formalRootFreshAtStart: true,
  crash,
  currentRuntime: {
    codexVersion: currentVersion,
    expectedCodexVersion: expectedCurrentVersion,
    appPlistSha256: currentAppPlistSha256,
    bundleIdentifier: currentBundleIdentifier,
    osVersion: currentOsVersion
  },
  disk,
  memory,
  processes: processSummary,
  restartBoundary,
  commandRecords,
  resourceAccounting: {
    childProcesses: commandRecords.length,
    blenderProcesses: 0,
    renderProcesses: 0,
    browserAutomationCalls: 0,
    networkCalls: 0,
    modelCalls: 0,
    dockerCalls: 0,
    cleanupOperations: 0,
    signalsSent: 0,
    hostRestarts: 0,
    codexRestarts: 0
  },
  gates,
  failedGates,
  provisionalVerdict,
  stdoutBytes: Buffer.byteLength(summaryText),
  receiptBytes: 0,
  selfHash: ''
};

let serialized = '';
for (let index = 0; index < 8; index += 1) {
  results.gates.RECEIPT_BOUNDED = results.receiptBytes <= spec.resourcePolicy.maximumReceiptBytes;
  results.selfHash = sha256Bytes(canonical(withoutSelfHash(results)));
  serialized = `${JSON.stringify(results, null, 2)}\n`;
  const nextBytes = Buffer.byteLength(serialized);
  if (nextBytes === results.receiptBytes) break;
  results.receiptBytes = nextBytes;
}
results.gates.RECEIPT_BOUNDED = results.receiptBytes <= spec.resourcePolicy.maximumReceiptBytes;
results.selfHash = sha256Bytes(canonical(withoutSelfHash(results)));
serialized = `${JSON.stringify(results, null, 2)}\n`;
results.receiptBytes = Buffer.byteLength(serialized);
results.selfHash = sha256Bytes(canonical(withoutSelfHash(results)));
serialized = `${JSON.stringify(results, null, 2)}\n`;

if (!results.gates.STDOUT_BOUNDED) throw new Error('summary exceeds stdout ceiling');
if (!results.gates.RECEIPT_BOUNDED || Buffer.byteLength(serialized) > spec.resourcePolicy.maximumReceiptBytes) throw new Error('receipt exceeds ceiling');
if (results.resourceAccounting.childProcesses > spec.formalCeilings.childProcesses) throw new Error('child process ceiling exceeded');

mkdirSync(formalRoot, { recursive: false });
writeExclusiveDurable(resultsPath, serialized);
process.stdout.write(summaryText);
