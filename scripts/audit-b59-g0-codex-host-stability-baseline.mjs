#!/usr/bin/env node

import { createHash } from 'node:crypto';
import { closeSync, existsSync, openSync, readFileSync, statSync, statfsSync, writeFileSync, fsyncSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const repositoryRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const specPath = resolve(repositoryRoot, 'specs/codex-host-stability-baseline.v0.1.json');
const spec = JSON.parse(readFileSync(specPath, 'utf8'));
const formalRoot = resolve(repositoryRoot, spec.formalRoot);
const resultsPath = resolve(formalRoot, 'results.json');
const auditPath = resolve(formalRoot, 'audit.json');
const auditCommands = [];

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

function reseal(value) {
  value.selfHash = sha256Bytes(canonical(withoutSelfHash(value)));
  return value;
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
  auditCommands.push({ label, exitCode: 0, stdoutBytes: bytes, durationMs: Date.now() - startedAt });
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
    return { pid: Number(match[1]), parentPid: Number(match[2]), rssBytes: Number(match[3]) * 1024, command: match[5] };
  });
}

function summarizeProcesses(processes) {
  const codexPrefix = '/Applications/ChatGPT.app/Contents/';
  const mainPath = '/Applications/ChatGPT.app/Contents/MacOS/ChatGPT';
  const renderers = processes.filter((item) => item.command.includes('/Codex (Renderer).app/Contents/MacOS/Codex (Renderer)'));
  const codexTree = processes.filter((item) => item.command.startsWith(codexPrefix));
  const crashpads = processes.filter((item) => item.command.includes('/browser_crashpad_handler'));
  return {
    mainCodexProcessCount: processes.filter((item) => item.command === mainPath).length,
    rendererCount: renderers.length,
    maximumRendererRssBytes: Math.max(0, ...renderers.map((item) => item.rssBytes)),
    codexTreeRssBytes: codexTree.reduce((sum, item) => sum + item.rssBytes, 0),
    activeBlenderProcessCount: processes.filter((item) => item.command.startsWith('/Applications/Blender.app/Contents/MacOS/Blender')).length,
    activeB58WorkerProcessCount: processes.filter((item) => /(?:run-restart-safe-production-job|preflight-b58-e1|run-b58-e1|audit-b58-e1)[.]mjs/.test(item.command)).length,
    browserAutomationProcessCount: processes.filter((item) => /(?:^|[/ ])(?:agent-browser|chromedriver)(?:$|[/ ])|playwright/.test(item.command)).length,
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

function expectedGateVector(candidate) {
  const maximumAgeMs = spec.resourcePolicy.maximumSnapshotAgeSecondsAtAudit * 1000;
  const ageMs = Date.now() - Date.parse(candidate.capturedAt);
  const signature = candidate.crash;
  const resources = candidate.resourceAccounting;
  return {
    SPEC_AND_PARENT_IDENTITY: candidate.spec.sha256 === sha256File(specPath)
      && candidate.git.specParentCommit === spec.parentCommit
      && candidate.git.parentIsAncestor === true
      && candidate.git.headCommit === candidate.git.originMainCommit
      && candidate.git.scopedStatus === '',
    FRESH_FORMAL_ROOT: candidate.formalRoot === spec.formalRoot && candidate.formalRootFreshAtStart === true,
    CRASH_EVIDENCE_IDENTITY: signature.sha256 === spec.crashEvidence.sha256 && signature.bytes === spec.crashEvidence.bytes && signature.lines === spec.crashEvidence.lines,
    CRASH_SIGNATURE_EXACT: signature.processExact === true && signature.identifierExact === true && signature.versionExact === true && signature.threadExact === true && signature.exceptionExact === true && signature.serializerSymbolPresent === true,
    CURRENT_CODEX_VERSION_EXACT: candidate.currentRuntime.codexVersion === spec.crashEvidence.version,
    SNAPSHOT_FRESHNESS: Number.isFinite(ageMs) && ageMs >= 0 && ageMs <= maximumAgeMs,
    DISK_STABILITY_MARGIN: candidate.disk.minimumAvailableBytes === spec.resourcePolicy.minimumAvailableBytes
      && candidate.disk.minimumAvailableBytes === candidate.disk.minimumCoreDiskReserveBytes + candidate.disk.b58ProjectedWriteBytes + candidate.disk.additionalStabilityMarginBytes
      && candidate.disk.headroomBytes === candidate.disk.availableBytes - candidate.disk.minimumAvailableBytes
      && candidate.disk.availableBytes >= candidate.disk.minimumAvailableBytes,
    MEMORY_PRESSURE: candidate.memory.minimumFreePercent === spec.resourcePolicy.minimumMemoryFreePercent && candidate.memory.systemWideFreePercent >= candidate.memory.minimumFreePercent,
    CODEX_MAIN_PROCESS_COUNT: candidate.processes.mainCodexProcessCount === spec.processPolicy.requiredMainCodexProcessCount,
    CODEX_RENDERER_COUNT: candidate.processes.rendererCount <= spec.resourcePolicy.maximumCodexRendererCount,
    SINGLE_RENDERER_RSS: candidate.processes.maximumRendererRssBytes <= spec.resourcePolicy.maximumSingleRendererRssBytes,
    CODEX_TREE_RSS: candidate.processes.codexTreeRssBytes <= spec.resourcePolicy.maximumCodexTreeRssBytes,
    NO_ACTIVE_BLENDER: candidate.processes.activeBlenderProcessCount === spec.processPolicy.requiredActiveBlenderProcessCount,
    NO_ACTIVE_B58_WORKER: candidate.processes.activeB58WorkerProcessCount === spec.processPolicy.requiredActiveB58WorkerProcessCount,
    NO_BROWSER_AUTOMATION_PROCESS: candidate.processes.browserAutomationProcessCount === spec.processPolicy.requiredBrowserAutomationProcessCount,
    RESOURCE_CEILINGS_ZERO: resources.blenderProcesses === 0 && resources.renderProcesses === 0
      && resources.browserAutomationCalls === 0 && resources.networkCalls === 0 && resources.modelCalls === 0
      && resources.dockerCalls === 0 && resources.cleanupOperations === 0 && resources.signalsSent === 0
      && resources.hostRestarts === 0 && resources.codexRestarts === 0
      && resources.childProcesses <= spec.formalCeilings.childProcesses,
    STDOUT_BOUNDED: candidate.stdoutBytes <= spec.resourcePolicy.maximumStdoutBytes,
    RECEIPT_BOUNDED: candidate.receiptBytes <= spec.resourcePolicy.maximumReceiptBytes,
    RECEIPT_SELF_HASH: candidate.selfHash === sha256Bytes(canonical(withoutSelfHash(candidate))),
    INDEPENDENT_AUDIT_REPLAY: 'PENDING'
  };
}

function validateCandidate(candidate) {
  const expected = expectedGateVector(candidate);
  const gateNames = spec.requiredGates.filter((name) => name !== 'INDEPENDENT_AUDIT_REPLAY');
  const gateProjectionExact = gateNames.every((name) => candidate.gates[name] === expected[name]);
  const expectedFailures = gateNames.filter((name) => expected[name] !== true);
  const failureProjectionExact = canonical(candidate.failedGates) === canonical(expectedFailures);
  const expectedVerdict = expectedFailures.length ? 'BLOCKED_HOST_STABILITY' : 'ADMITTED_PENDING_AUDIT';
  return gateProjectionExact && failureProjectionExact && candidate.provisionalVerdict === expectedVerdict
    && expected.SPEC_AND_PARENT_IDENTITY && expected.FRESH_FORMAL_ROOT
    && expected.CRASH_EVIDENCE_IDENTITY && expected.CRASH_SIGNATURE_EXACT
    && expected.RECEIPT_SELF_HASH && expected.STDOUT_BOUNDED && expected.RECEIPT_BOUNDED;
}

function makeSyntheticAdmissibleControl(observed) {
  const control = structuredClone(observed);
  control.syntheticControl = true;
  control.capturedAt = new Date().toISOString();
  control.disk.availableBytes = spec.resourcePolicy.minimumAvailableBytes + 1;
  control.disk.minimumCoreDiskReserveBytes = spec.resourcePolicy.minimumCoreDiskReserveBytes;
  control.disk.b58ProjectedWriteBytes = spec.resourcePolicy.b58ProjectedWriteBytes;
  control.disk.additionalStabilityMarginBytes = spec.resourcePolicy.additionalStabilityMarginBytes;
  control.disk.minimumAvailableBytes = spec.resourcePolicy.minimumAvailableBytes;
  control.disk.headroomBytes = 1;
  control.memory.minimumFreePercent = spec.resourcePolicy.minimumMemoryFreePercent;
  control.memory.systemWideFreePercent = spec.resourcePolicy.minimumMemoryFreePercent;
  control.processes.mainCodexProcessCount = spec.processPolicy.requiredMainCodexProcessCount;
  control.processes.rendererCount = 0;
  control.processes.maximumRendererRssBytes = 0;
  control.processes.codexTreeRssBytes = 0;
  control.processes.activeBlenderProcessCount = spec.processPolicy.requiredActiveBlenderProcessCount;
  control.processes.activeB58WorkerProcessCount = spec.processPolicy.requiredActiveB58WorkerProcessCount;
  control.processes.browserAutomationProcessCount = spec.processPolicy.requiredBrowserAutomationProcessCount;
  control.resourceAccounting = {
    ...control.resourceAccounting,
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
  };
  control.stdoutBytes = Math.min(control.stdoutBytes, spec.resourcePolicy.maximumStdoutBytes);
  control.receiptBytes = Math.min(control.receiptBytes, spec.resourcePolicy.maximumReceiptBytes);
  control.gates = Object.fromEntries(spec.requiredGates.map((name) => [name, name === 'INDEPENDENT_AUDIT_REPLAY' ? 'PENDING' : true]));
  control.failedGates = [];
  control.provisionalVerdict = 'ADMITTED_PENDING_AUDIT';
  return reseal(control);
}

if (!existsSync(resultsPath)) throw new Error('missing results.json');
if (existsSync(auditPath)) throw new Error('audit.json already exists');
const resultsText = readFileSync(resultsPath, 'utf8');
const results = JSON.parse(resultsText);

const scopedStatus = runBounded('/usr/bin/git', [
  'status', '--short', '--',
  'specs/codex-host-stability-baseline.v0.1.json',
  'research/2026-08-28-b59-g0-codex-host-stability-baseline-protocol.md',
  'scripts/run-b59-g0-codex-host-stability-baseline.mjs',
  'scripts/audit-b59-g0-codex-host-stability-baseline.mjs'
], 'git-scoped-status', 32768).trim();

const memoryOutput = runBounded('/usr/bin/memory_pressure', ['-Q'], 'memory-pressure', 32768);
const memoryMatch = memoryOutput.match(/System-wide memory free percentage:\s*(\d+)%/);
if (!memoryMatch) throw new Error('memory replay missing free percentage');
const replayMemoryPercent = Number(memoryMatch[1]);
const replayProcesses = summarizeProcesses(parseProcesses(runBounded('/bin/ps', ['-axo', 'pid=,ppid=,rss=,etime=,command='], 'process-snapshot')));
const filesystem = statfsSync('/');
const replayAvailableBytes = Number(filesystem.bavail * filesystem.bsize);
const appPlist = '/Applications/ChatGPT.app/Contents/Info.plist';
const replayVersion = `${readPlistString(appPlist, 'CFBundleShortVersionString')} (${readPlistString(appPlist, 'CFBundleVersion')})`;

const integrityChecks = {
  SPEC_SHA: results.spec.sha256 === sha256File(specPath),
  RECEIPT_FILE_SIZE: results.receiptBytes === statSync(resultsPath).size,
  RECEIPT_SELF_HASH: results.selfHash === sha256Bytes(canonical(withoutSelfHash(results))),
  SCOPED_RELEASE_CLEAN: scopedStatus === '',
  CRASH_REPORT_SHA: sha256File(spec.crashEvidence.sourcePath) === spec.crashEvidence.sha256,
  CURRENT_VERSION_REPLAY: replayVersion === results.currentRuntime.codexVersion,
  DISK_GATE_REPLAY: (replayAvailableBytes >= spec.resourcePolicy.minimumAvailableBytes) === results.gates.DISK_STABILITY_MARGIN,
  MEMORY_GATE_REPLAY: (replayMemoryPercent >= spec.resourcePolicy.minimumMemoryFreePercent) === results.gates.MEMORY_PRESSURE,
  MAIN_PROCESS_GATE_REPLAY: (replayProcesses.mainCodexProcessCount === spec.processPolicy.requiredMainCodexProcessCount) === results.gates.CODEX_MAIN_PROCESS_COUNT,
  RENDERER_COUNT_GATE_REPLAY: (replayProcesses.rendererCount <= spec.resourcePolicy.maximumCodexRendererCount) === results.gates.CODEX_RENDERER_COUNT,
  SINGLE_RENDERER_GATE_REPLAY: (replayProcesses.maximumRendererRssBytes <= spec.resourcePolicy.maximumSingleRendererRssBytes) === results.gates.SINGLE_RENDERER_RSS,
  CODEX_TREE_GATE_REPLAY: (replayProcesses.codexTreeRssBytes <= spec.resourcePolicy.maximumCodexTreeRssBytes) === results.gates.CODEX_TREE_RSS,
  NO_BLENDER_GATE_REPLAY: (replayProcesses.activeBlenderProcessCount === 0) === results.gates.NO_ACTIVE_BLENDER,
  NO_B58_GATE_REPLAY: (replayProcesses.activeB58WorkerProcessCount === 0) === results.gates.NO_ACTIVE_B58_WORKER,
  NO_BROWSER_AUTOMATION_GATE_REPLAY: (replayProcesses.browserAutomationProcessCount === 0) === results.gates.NO_BROWSER_AUTOMATION_PROCESS,
  BASE_SEMANTIC_MODEL: validateCandidate(results)
};

const syntheticControl = makeSyntheticAdmissibleControl(results);
const syntheticControlValid = validateCandidate(syntheticControl);

const attacks = [
  ['A01_SPEC_SHA_MUTATION', (x) => { x.spec.sha256 = '0'.repeat(64); }],
  ['A02_PARENT_COMMIT_MUTATION', (x) => { x.git.specParentCommit = '0'.repeat(40); }],
  ['A03_DIRTY_FORMAL_ROOT', (x) => { x.formalRootFreshAtStart = false; }],
  ['A04_CRASH_REPORT_SHA_MUTATION', (x) => { x.crash.sha256 = '0'.repeat(64); }],
  ['A05_CRASH_REPORT_BYTE_COUNT_MUTATION', (x) => { x.crash.bytes += 1; }],
  ['A06_CRASH_THREAD_MUTATION', (x) => { x.crash.threadExact = false; }],
  ['A07_CRASH_EXCEPTION_MUTATION', (x) => { x.crash.exceptionExact = false; }],
  ['A08_CODEX_VERSION_MUTATION', (x) => { x.currentRuntime.codexVersion = '0.0.0 (0)'; }],
  ['A09_STALE_CAPTURE_TIME', (x) => { x.capturedAt = '2000-01-01T00:00:00.000Z'; }],
  ['A10_DISK_AVAILABLE_BELOW_MARGIN', (x) => { x.disk.availableBytes = x.disk.minimumAvailableBytes - 1; }],
  ['A11_DISK_PROJECTION_MUTATION', (x) => { x.disk.b58ProjectedWriteBytes += 1; }],
  ['A12_MEMORY_FREE_BELOW_FLOOR', (x) => { x.memory.systemWideFreePercent = x.memory.minimumFreePercent - 1; }],
  ['A13_MAIN_PROCESS_COUNT_MUTATION', (x) => { x.processes.mainCodexProcessCount = 2; }],
  ['A14_RENDERER_COUNT_ABOVE_CEILING', (x) => { x.processes.rendererCount = spec.resourcePolicy.maximumCodexRendererCount + 1; }],
  ['A15_SINGLE_RENDERER_RSS_ABOVE_CEILING', (x) => { x.processes.maximumRendererRssBytes = spec.resourcePolicy.maximumSingleRendererRssBytes + 1; }],
  ['A16_CODEX_TREE_RSS_ABOVE_CEILING', (x) => { x.processes.codexTreeRssBytes = spec.resourcePolicy.maximumCodexTreeRssBytes + 1; }],
  ['A17_ACTIVE_BLENDER_PROCESS', (x) => { x.processes.activeBlenderProcessCount = 1; }],
  ['A18_ACTIVE_B58_WORKER', (x) => { x.processes.activeB58WorkerProcessCount = 1; }],
  ['A19_BROWSER_AUTOMATION_PROCESS', (x) => { x.processes.browserAutomationProcessCount = 1; }],
  ['A20_NONZERO_NETWORK_OR_MODEL_OR_DOCKER', (x) => { x.resourceAccounting.networkCalls = 1; }],
  ['A21_NONZERO_SIGNAL_OR_CLEANUP', (x) => { x.resourceAccounting.signalsSent = 1; }],
  ['A22_STDOUT_SIZE_ABOVE_CEILING', (x) => { x.stdoutBytes = spec.resourcePolicy.maximumStdoutBytes + 1; }],
  ['A23_RECEIPT_SIZE_ABOVE_CEILING', (x) => { x.receiptBytes = spec.resourcePolicy.maximumReceiptBytes + 1; }],
  ['A24_RECEIPT_SELF_HASH_MUTATION', (x) => { x.selfHash = '0'.repeat(64); }, false]
];

const attackResults = attacks.map(([id, mutate, shouldReseal = true]) => {
  const candidate = structuredClone(syntheticControl);
  mutate(candidate);
  if (shouldReseal) reseal(candidate);
  return { id, rejected: !validateCandidate(candidate) };
});
const attackIdsExact = canonical(attacks.map(([id]) => id)) === canonical(spec.registeredAttacks);
const attacksPassed = attackIdsExact && attackResults.every((item) => item.rejected);
const integrityPassed = Object.values(integrityChecks).every(Boolean) && syntheticControlValid;
const independentAuditPassed = integrityPassed && attacksPassed
  && results.resourceAccounting.childProcesses + auditCommands.length <= spec.formalCeilings.childProcesses;
const finalGates = { ...results.gates, INDEPENDENT_AUDIT_REPLAY: independentAuditPassed };
const failedGates = spec.requiredGates.filter((name) => finalGates[name] !== true);
const integrityGateNames = [
  'SPEC_AND_PARENT_IDENTITY', 'FRESH_FORMAL_ROOT', 'CRASH_EVIDENCE_IDENTITY', 'CRASH_SIGNATURE_EXACT',
  'STDOUT_BOUNDED', 'RECEIPT_BOUNDED', 'RECEIPT_SELF_HASH', 'INDEPENDENT_AUDIT_REPLAY'
];
const invalid = integrityGateNames.some((name) => finalGates[name] !== true);
const finalVerdict = invalid ? 'INVALID_EVIDENCE' : failedGates.length ? 'BLOCKED_HOST_STABILITY' : 'ADMITTED_FOR_LIGHTWEIGHT_WORK';

const audit = {
  schemaVersion: 'bfs.codex-host-stability-baseline-audit.v0.1',
  experimentId: spec.experimentId,
  auditedAt: new Date().toISOString(),
  results: { path: spec.formalRoot + '/results.json', sha256: sha256File(resultsPath), selfHash: results.selfHash },
  replay: { availableBytes: replayAvailableBytes, memoryFreePercent: replayMemoryPercent, processes: replayProcesses, codexVersion: replayVersion },
  integrityChecks,
  syntheticAdmissibleControl: { valid: syntheticControlValid, selfHash: syntheticControl.selfHash },
  attackIdsExact,
  attackResults,
  attacksPassed: attackResults.filter((item) => item.rejected).length,
  attacksTotal: attackResults.length,
  auditCommands,
  combinedChildProcesses: results.resourceAccounting.childProcesses + auditCommands.length,
  finalGates,
  passedGates: spec.requiredGates.filter((name) => finalGates[name] === true).length,
  totalGates: spec.requiredGates.length,
  failedGates,
  finalVerdict,
  receiptBytes: 0,
  selfHash: ''
};

let serialized = '';
for (let index = 0; index < 8; index += 1) {
  audit.selfHash = sha256Bytes(canonical(withoutSelfHash(audit)));
  serialized = `${JSON.stringify(audit, null, 2)}\n`;
  const nextBytes = Buffer.byteLength(serialized);
  if (nextBytes === audit.receiptBytes) break;
  audit.receiptBytes = nextBytes;
}
audit.selfHash = sha256Bytes(canonical(withoutSelfHash(audit)));
serialized = `${JSON.stringify(audit, null, 2)}\n`;

if (Buffer.byteLength(serialized) > spec.resourcePolicy.maximumReceiptBytes) throw new Error('audit receipt exceeds ceiling');
const summary = {
  schemaVersion: 'bfs.codex-host-stability-baseline-audit-summary.v0.1',
  experimentId: spec.experimentId,
  finalVerdict,
  gates: `${audit.passedGates}/${audit.totalGates}`,
  attacks: `${audit.attacksPassed}/${audit.attacksTotal}`,
  failedGates,
  auditPath: spec.formalRoot + '/audit.json'
};
const summaryText = `${JSON.stringify(summary)}\n`;
if (Buffer.byteLength(summaryText) > spec.resourcePolicy.maximumStdoutBytes) throw new Error('audit summary exceeds stdout ceiling');
writeExclusiveDurable(auditPath, serialized);
process.stdout.write(summaryText);
