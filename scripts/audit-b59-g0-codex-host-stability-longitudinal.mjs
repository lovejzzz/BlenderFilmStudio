#!/usr/bin/env node

import { createHash } from 'node:crypto';
import {
  closeSync, existsSync, fsyncSync, openSync, readFileSync, readdirSync, statSync, writeFileSync
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

function selfHashValid(value) {
  return value.selfHash === sha256Bytes(canonical(withoutSelfHash(value)));
}

function serialized(value) {
  return `${JSON.stringify(value, null, 2)}\n`;
}

function reseal(value) {
  value.selfHash = sha256Bytes(canonical(withoutSelfHash(value)));
  return value;
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

function runBounded(command, args, label, maxBytes = 524288) {
  const stdout = execFileSync(command, args, {
    cwd: repositoryRoot,
    encoding: 'utf8',
    timeout: 5000,
    maxBuffer: maxBytes,
    env: { ...process.env, LC_ALL: 'C' }
  });
  if (Buffer.byteLength(stdout) > maxBytes) throw new Error(`${label} exceeded output ceiling`);
  auditCommands.push({ label, stdoutBytes: Buffer.byteLength(stdout) });
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
  const appPrefix = '/Applications/ChatGPT.app/Contents/';
  const mainPath = '/Applications/ChatGPT.app/Contents/MacOS/ChatGPT';
  const main = processes.filter((item) => item.command === mainPath);
  const renderers = processes.filter((item) => item.command.includes('/Codex (Renderer).app/Contents/MacOS/Codex (Renderer)'));
  const tree = processes.filter((item) => item.command.startsWith(appPrefix));
  return {
    mainCodexProcessCount: main.length,
    mainCodexPids: main.map((item) => item.pid).sort((a, b) => a - b),
    rendererCount: renderers.length,
    maximumRendererRssBytes: Math.max(0, ...renderers.map((item) => item.rssBytes)),
    codexTreeRssBytes: tree.reduce((sum, item) => sum + item.rssBytes, 0),
    activeBlenderProcessCount: processes.filter((item) => item.command.startsWith('/Applications/Blender.app/Contents/MacOS/Blender')).length,
    activeB58WorkerProcessCount: processes.filter((item) => /(?:run-restart-safe-production-job|preflight-b58-e1|run-b58-e1|audit-b58-e1)[.]mjs/.test(item.command)).length,
    browserAutomationProcessCount: processes.filter((item) => /(?:^|[/ ])(?:agent-browser|chromedriver)(?:$|[/ ])|playwright/.test(item.command)).length
  };
}

function matchingCrashReports(path, afterMs) {
  if (!existsSync(path)) return [];
  return readdirSync(path)
    .filter((name) => /^ChatGPT.*[.]ips$/.test(name))
    .map((name) => ({ name, modifiedMs: statSync(join(path, name)).mtimeMs }))
    .filter((item) => item.modifiedMs > afterMs)
    .sort((a, b) => a.name.localeCompare(b.name));
}

function calculateAggregate(samples) {
  if (!samples.length) return { intervalsMs: [], totalSpanMs: 0, rssGrowthBytes: 0, diskLossBytes: 0, browserGrowthBytes: 0 };
  const first = samples[0];
  const last = samples.at(-1);
  return {
    intervalsMs: samples.slice(1).map((sample, index) => Date.parse(sample.capturedAt) - Date.parse(samples[index].capturedAt)),
    totalSpanMs: Date.parse(last.capturedAt) - Date.parse(first.capturedAt),
    rssGrowthBytes: last.processes.codexTreeRssBytes - first.processes.codexTreeRssBytes,
    diskLossBytes: first.disk.availableBytes - last.disk.availableBytes,
    browserGrowthBytes: last.browserTempFilesystem.allocatedBytes - first.browserTempFilesystem.allocatedBytes
  };
}

function expectedGates(bundle) {
  const { start, samples, results } = bundle;
  const aggregate = calculateAggregate(samples);
  const intervalsValid = aggregate.intervalsMs.every((value) => value >= spec.observationPolicy.minimumIntervalSeconds * 1000);
  const runtimeValid = samples.every((sample) => sample.runtime.codexVersion === spec.runtimeExpectation.codexVersion
    && sample.runtime.appPlistSha256 === spec.runtimeExpectation.appPlistSha256
    && sample.runtime.bundleIdentifier === spec.runtimeExpectation.bundleIdentifier);
  const pidValid = samples.every((sample) => sample.processes.mainCodexProcessCount === spec.processPolicy.requiredMainCodexProcessCount
    && sample.processes.mainCodexPids.length === 1
    && sample.processes.mainCodexPids[0] === spec.runtimeExpectation.requiredMainPid
    && !sample.processes.mainCodexPids.includes(spec.runtimeExpectation.forbiddenPreviousMainPid));
  const resourcesValid = samples.every((sample) => sample.disk.availableBytes >= spec.resourcePolicy.minimumAvailableBytes
    && sample.memory.systemWideFreePercent >= spec.resourcePolicy.minimumMemoryFreePercent
    && sample.processes.rendererCount <= spec.resourcePolicy.maximumCodexRendererCount
    && sample.processes.maximumRendererRssBytes <= spec.resourcePolicy.maximumSingleRendererRssBytes
    && sample.processes.codexTreeRssBytes <= spec.resourcePolicy.maximumCodexTreeRssBytes);
  const forbiddenAbsent = samples.every((sample) => sample.processes.activeBlenderProcessCount === spec.processPolicy.requiredActiveBlenderProcessCount
    && sample.processes.activeB58WorkerProcessCount === spec.processPolicy.requiredActiveB58WorkerProcessCount
    && sample.processes.browserAutomationProcessCount === spec.processPolicy.requiredBrowserAutomationProcessCount);
  const sampleReceiptsValid = results.sampleReceipts.length === samples.length && samples.every((sample, index) => {
    const receipt = results.sampleReceipts[index];
    const text = serialized(sample);
    return selfHashValid(sample)
      && receipt.index === sample.index
      && receipt.selfHash === sample.selfHash
      && receipt.sha256 === sha256Bytes(text)
      && receipt.bytes === Buffer.byteLength(text)
      && receipt.bytes <= spec.resourcePolicy.maximumSampleBytes;
  });
  const startText = serialized(start);
  const startValid = selfHashValid(start)
    && results.startReceipt.selfHash === start.selfHash
    && results.startReceipt.sha256 === sha256Bytes(startText)
    && results.startReceipt.bytes === Buffer.byteLength(startText)
    && results.startReceipt.bytes <= spec.resourcePolicy.maximumSampleBytes;
  const zeros = results.resourceAccounting;
  return {
    SPEC_PARENT_AND_RELEASE_IDENTITY: results.spec.sha256 === sha256File(specPath)
      && results.spec.path === specRelativePath
      && start.specSha256 === results.spec.sha256
      && start.git.scopedStatus === '' && results.git.end.scopedStatus === ''
      && start.git.headCommit === start.git.originMainCommit
      && results.git.end.headCommit === results.git.end.originMainCommit
      && start.git.headCommit === results.git.end.headCommit
      && start.git.parentIsAncestor === true && results.git.end.parentIsAncestor === true,
    PARENT_EVIDENCE_IDENTITY: start.parentEvidence.resultsSha256 === spec.parentEvidence.resultsSha256
      && start.parentEvidence.auditSha256 === spec.parentEvidence.auditSha256
      && results.parentEvidence.resultsSha256 === spec.parentEvidence.resultsSha256
      && results.parentEvidence.auditSha256 === spec.parentEvidence.auditSha256,
    SAMPLE_COUNT_AND_ORDER: samples.length === spec.observationPolicy.requiredSampleCount
      && samples.every((sample, index) => sample.index === index + 1),
    TIMING_WINDOW: intervalsValid
      && aggregate.totalSpanMs >= spec.observationPolicy.minimumTotalSpanSeconds * 1000
      && samples.every((sample) => sample.latenessMs >= 0 && sample.latenessMs <= spec.observationPolicy.maximumSampleLatenessSeconds * 1000),
    RUNTIME_IDENTITY: runtimeValid,
    MAIN_PROCESS_CONTINUITY: pidValid,
    PER_SAMPLE_RESOURCE_CEILINGS: resourcesValid,
    RSS_GROWTH_BOUNDED: aggregate.rssGrowthBytes <= spec.observationPolicy.maximumCodexTreeRssGrowthBytes,
    DISK_RETENTION_BOUNDED: aggregate.diskLossBytes <= spec.observationPolicy.maximumDiskLossBytes,
    BROWSER_TEMP_FILESYSTEM_BOUNDED: samples.every((sample) => sample.browserTempFilesystem.allocatedBytes <= spec.observationPolicy.maximumBrowserTempFilesystemBytes)
      && aggregate.browserGrowthBytes <= spec.observationPolicy.maximumBrowserTempFilesystemGrowthBytes,
    NO_FORBIDDEN_PROCESS: forbiddenAbsent,
    NO_NEW_CODEX_CRASH_REPORT: samples.every((sample) => sample.newCrashReports.length === 0),
    RESOURCE_ACCOUNTING_ZERO: zeros.blenderProcesses === 0 && zeros.renderProcesses === 0
      && zeros.browserAutomationCalls === 0 && zeros.networkCalls === 0 && zeros.modelCalls === 0
      && zeros.dockerCalls === 0 && zeros.cleanupOperations === 0 && zeros.signalsSent === 0
      && zeros.hostRestarts === 0 && zeros.codexRestarts === 0
      && zeros.observationCommands <= spec.formalCeilings.maximumObservationCommands,
    EVIDENCE_BOUNDED_AND_SELF_HASHED: startValid && sampleReceiptsValid
      && results.receiptBytes <= spec.resourcePolicy.maximumResultsBytes,
    INDEPENDENT_AUDIT_REPLAY: 'PENDING'
  };
}

function project(bundle) {
  bundle.results.aggregate = calculateAggregate(bundle.samples);
  const gates = expectedGates(bundle);
  bundle.results.gates = gates;
  const names = spec.requiredGates.filter((name) => name !== 'INDEPENDENT_AUDIT_REPLAY');
  bundle.results.failedGates = names.filter((name) => gates[name] !== true);
  bundle.results.provisionalVerdict = bundle.results.failedGates.length ? 'BLOCKED_HOST_STABILITY' : 'ADMITTED_PENDING_AUDIT';
}

function resealBundle(bundle, shouldProject = true) {
  reseal(bundle.start);
  for (const sample of bundle.samples) reseal(sample);
  bundle.results.startReceipt.selfHash = bundle.start.selfHash;
  bundle.results.startReceipt.sha256 = sha256Bytes(serialized(bundle.start));
  bundle.results.startReceipt.bytes = Buffer.byteLength(serialized(bundle.start));
  bundle.results.sampleReceipts = bundle.samples.map((sample) => ({
    index: sample.index,
    path: `${spec.formalRoot}/sample-${String(sample.index).padStart(3, '0')}.json`,
    sha256: sha256Bytes(serialized(sample)),
    selfHash: sample.selfHash,
    bytes: Buffer.byteLength(serialized(sample))
  }));
  reseal(bundle.results);
  if (shouldProject) project(bundle);
  reseal(bundle.results);
  return bundle;
}

function validateCandidate(bundle) {
  const expected = expectedGates(bundle);
  const names = spec.requiredGates.filter((name) => name !== 'INDEPENDENT_AUDIT_REPLAY');
  const projectionExact = names.every((name) => bundle.results.gates[name] === expected[name]);
  const failed = names.filter((name) => expected[name] !== true);
  const failureProjectionExact = canonical(bundle.results.failedGates) === canonical(failed);
  const verdict = failed.length ? 'BLOCKED_HOST_STABILITY' : 'ADMITTED_PENDING_AUDIT';
  return projectionExact && failureProjectionExact && bundle.results.provisionalVerdict === verdict
    && names.every((name) => expected[name] === true) && selfHashValid(bundle.results);
}

function makeSyntheticControl(observed) {
  const control = structuredClone(observed);
  const startedMs = Date.parse(control.start.startedAt);
  control.samples = Array.from({ length: spec.observationPolicy.requiredSampleCount }, (_, offset) => {
    const sample = structuredClone(observed.samples[Math.min(offset, observed.samples.length - 1)]);
    const atMs = startedMs + offset * spec.observationPolicy.minimumIntervalSeconds * 1000;
    sample.index = offset + 1;
    sample.scheduledAt = new Date(atMs).toISOString();
    sample.capturedAt = new Date(atMs).toISOString();
    sample.latenessMs = 0;
    sample.runtime = {
      codexVersion: spec.runtimeExpectation.codexVersion,
      appPlistSha256: spec.runtimeExpectation.appPlistSha256,
      bundleIdentifier: spec.runtimeExpectation.bundleIdentifier
    };
    sample.disk.availableBytes = spec.resourcePolicy.minimumAvailableBytes + 2 * spec.observationPolicy.maximumDiskLossBytes;
    sample.memory.systemWideFreePercent = spec.resourcePolicy.minimumMemoryFreePercent;
    sample.processes.mainCodexProcessCount = spec.processPolicy.requiredMainCodexProcessCount;
    sample.processes.mainCodexPids = [spec.runtimeExpectation.requiredMainPid];
    sample.processes.rendererCount = 0;
    sample.processes.maximumRendererRssBytes = 0;
    sample.processes.codexTreeRssBytes = 1073741824 + offset * 1048576;
    sample.processes.activeBlenderProcessCount = 0;
    sample.processes.activeB58WorkerProcessCount = 0;
    sample.processes.browserAutomationProcessCount = 0;
    sample.browserTempFilesystem = { allocatedBytes: 0, entries: 1 };
    sample.newCrashReports = [];
    return sample;
  });
  control.results.spec = { path: specRelativePath, sha256: sha256File(specPath) };
  control.start.specSha256 = control.results.spec.sha256;
  control.start.parentEvidence = { resultsSha256: spec.parentEvidence.resultsSha256, auditSha256: spec.parentEvidence.auditSha256 };
  control.results.parentEvidence = structuredClone(control.start.parentEvidence);
  control.results.resourceAccounting = {
    blenderProcesses: 0, renderProcesses: 0, browserAutomationCalls: 0, networkCalls: 0,
    modelCalls: 0, dockerCalls: 0, cleanupOperations: 0, signalsSent: 0, hostRestarts: 0,
    codexRestarts: 0, observationCommands: 0
  };
  control.results.receiptBytes = Math.min(control.results.receiptBytes, spec.resourcePolicy.maximumResultsBytes);
  return resealBundle(control, true);
}

if (!existsSync(startPath) || !existsSync(resultsPath)) throw new Error('formal evidence incomplete');
if (existsSync(auditPath)) throw new Error('audit already exists; immutable audit cannot be repeated');
const startText = readFileSync(startPath, 'utf8');
const resultsText = readFileSync(resultsPath, 'utf8');
const start = JSON.parse(startText);
const results = JSON.parse(resultsText);
const samples = [];
const sampleTexts = [];
for (let index = 1; index <= spec.observationPolicy.requiredSampleCount; index += 1) {
  const text = readFileSync(resolve(formalRoot, `sample-${String(index).padStart(3, '0')}.json`), 'utf8');
  sampleTexts.push(text);
  samples.push(JSON.parse(text));
}
const observed = { start, samples, results };
const expectedObservedGates = expectedGates(observed);
const admissionNames = spec.requiredGates.filter((name) => name !== 'INDEPENDENT_AUDIT_REPLAY');
const observedProjectionExact = admissionNames.every((name) => results.gates[name] === expectedObservedGates[name]);

const scopedStatus = runBounded('/usr/bin/git', ['status', '--short', '--', ...spec.releasePaths], 'audit-git-status', 32768).trim();
const [headCommit, originMainCommit] = runBounded('/usr/bin/git', ['rev-parse', 'HEAD', 'origin/main'], 'audit-git-identities', 4096).trim().split('\n');
const replayProcesses = summarizeProcesses(parseProcesses(runBounded('/bin/ps', ['-axo', 'pid=,ppid=,rss=,etime=,command='], 'audit-processes')));
const appPlist = spec.runtimeExpectation.appPlistPath;
const replayVersion = `${readPlistString(appPlist, 'CFBundleShortVersionString')} (${readPlistString(appPlist, 'CFBundleVersion')})`;
const replayCrashes = matchingCrashReports(spec.observationPolicy.diagnosticReportsPath, Date.parse(start.startedAt));

const fileIntegrity = {
  SPEC_SHA: results.spec.sha256 === sha256File(specPath),
  START_SHA: results.startReceipt.sha256 === sha256Bytes(startText) && results.startReceipt.bytes === Buffer.byteLength(startText),
  SAMPLE_FILES: sampleTexts.every((text, index) => results.sampleReceipts[index].sha256 === sha256Bytes(text)
    && results.sampleReceipts[index].bytes === Buffer.byteLength(text)),
  RESULTS_BYTES: results.receiptBytes === Buffer.byteLength(resultsText) && Buffer.byteLength(resultsText) <= spec.resourcePolicy.maximumResultsBytes,
  SELF_HASHES: selfHashValid(start) && samples.every(selfHashValid) && selfHashValid(results),
  PARENT_FILES: sha256File(resolve(repositoryRoot, spec.parentEvidence.resultsPath)) === spec.parentEvidence.resultsSha256
    && sha256File(resolve(repositoryRoot, spec.parentEvidence.auditPath)) === spec.parentEvidence.auditSha256,
  RELEASE_REPLAY: scopedStatus === '' && headCommit === originMainCommit && headCommit === results.git.end.headCommit,
  RUNTIME_REPLAY: replayVersion === spec.runtimeExpectation.codexVersion
    && sha256File(appPlist) === spec.runtimeExpectation.appPlistSha256
    && readPlistString(appPlist, 'CFBundleIdentifier') === spec.runtimeExpectation.bundleIdentifier,
  PID_REPLAY: replayProcesses.mainCodexProcessCount === 1
    && replayProcesses.mainCodexPids[0] === spec.runtimeExpectation.requiredMainPid
    && !replayProcesses.mainCodexPids.includes(spec.runtimeExpectation.forbiddenPreviousMainPid),
  CRASH_REPLAY: replayCrashes.length === 0,
  OBSERVED_GATE_PROJECTION: observedProjectionExact,
  AUDIT_COMMAND_CEILING: auditCommands.length <= spec.formalCeilings.maximumAuditCommands
};

const synthetic = makeSyntheticControl(observed);
const syntheticValid = validateCandidate(synthetic);
const attacks = [
  ['A01_SPEC_SHA_MUTATION', (x) => { x.results.spec.sha256 = '0'.repeat(64); x.start.specSha256 = '0'.repeat(64); }],
  ['A02_PARENT_EVIDENCE_MUTATION', (x) => { x.results.parentEvidence.resultsSha256 = '0'.repeat(64); }],
  ['A03_SAMPLE_REMOVAL', (x) => { x.samples.pop(); }],
  ['A04_SAMPLE_REORDER', (x) => { [x.samples[0], x.samples[1]] = [x.samples[1], x.samples[0]]; }],
  ['A05_INTERVAL_BELOW_MINIMUM', (x) => {
    x.samples[1].capturedAt = new Date(Date.parse(x.samples[0].capturedAt) + spec.observationPolicy.minimumIntervalSeconds * 1000 - 1).toISOString();
    x.samples[1].latenessMs = 0;
  }],
  ['A06_TOTAL_SPAN_BELOW_MINIMUM', (x) => { x.samples.at(-1).capturedAt = new Date(Date.parse(x.samples[0].capturedAt) + 100000).toISOString(); x.samples.at(-1).latenessMs = 0; }],
  ['A07_RUNTIME_VERSION_MUTATION', (x) => { x.samples[0].runtime.codexVersion = '0.0.0 (0)'; }],
  ['A08_MAIN_PID_MUTATION', (x) => { x.samples[0].processes.mainCodexPids = [1]; }],
  ['A09_OLD_PID_RESURRECTION', (x) => { x.samples[0].processes.mainCodexPids = [spec.runtimeExpectation.forbiddenPreviousMainPid]; }],
  ['A10_DISK_BELOW_FLOOR', (x) => { x.samples[0].disk.availableBytes = spec.resourcePolicy.minimumAvailableBytes - 1; }],
  ['A11_DISK_LOSS_ABOVE_CEILING', (x) => { x.samples.at(-1).disk.availableBytes = x.samples[0].disk.availableBytes - spec.observationPolicy.maximumDiskLossBytes - 1; }],
  ['A12_MEMORY_BELOW_FLOOR', (x) => { x.samples[0].memory.systemWideFreePercent = spec.resourcePolicy.minimumMemoryFreePercent - 1; }],
  ['A13_RENDERER_OR_RSS_ABOVE_CEILING', (x) => { x.samples[0].processes.codexTreeRssBytes = spec.resourcePolicy.maximumCodexTreeRssBytes + 1; }],
  ['A14_RSS_GROWTH_ABOVE_CEILING', (x) => { x.samples.at(-1).processes.codexTreeRssBytes = x.samples[0].processes.codexTreeRssBytes + spec.observationPolicy.maximumCodexTreeRssGrowthBytes + 1; }],
  ['A15_BROWSER_TEMP_SIZE_ABOVE_CEILING', (x) => { x.samples[0].browserTempFilesystem.allocatedBytes = spec.observationPolicy.maximumBrowserTempFilesystemBytes + 1; }],
  ['A16_BROWSER_TEMP_GROWTH_ABOVE_CEILING', (x) => { x.samples.at(-1).browserTempFilesystem.allocatedBytes = x.samples[0].browserTempFilesystem.allocatedBytes + spec.observationPolicy.maximumBrowserTempFilesystemGrowthBytes + 1; }],
  ['A17_FORBIDDEN_PROCESS_PRESENT', (x) => { x.samples[0].processes.activeBlenderProcessCount = 1; }],
  ['A18_NEW_CRASH_REPORT', (x) => { x.samples[0].newCrashReports = [{ name: 'ChatGPT-forged.ips', modifiedMs: Date.now() }]; }],
  ['A19_SAMPLE_SELF_HASH_MUTATION', (x) => { x.samples[0].selfHash = '0'.repeat(64); }, false],
  ['A20_EVIDENCE_SIZE_ABOVE_CEILING', (x) => { x.results.receiptBytes = spec.resourcePolicy.maximumResultsBytes + 1; }, false]
];

const attackResults = attacks.map(([id, mutate, shouldReseal = true]) => {
  const candidate = structuredClone(synthetic);
  mutate(candidate);
  if (shouldReseal) resealBundle(candidate, true);
  else reseal(candidate.results);
  return { id, rejected: !validateCandidate(candidate) };
});
const attackIdsExact = canonical(attacks.map(([id]) => id)) === canonical(spec.registeredAttacks);
const attacksPassed = attackIdsExact && attackResults.every((item) => item.rejected);
const integrityPassed = Object.values(fileIntegrity).every(Boolean) && syntheticValid;
const baseGatesPassed = admissionNames.every((name) => expectedObservedGates[name] === true && results.gates[name] === true);
const finalVerdict = integrityPassed && attacksPassed && baseGatesPassed
  ? 'ADMITTED_FOR_GATE0_CLOSEOUT' : 'BLOCKED_HOST_STABILITY';
const finalGates = { ...results.gates, INDEPENDENT_AUDIT_REPLAY: integrityPassed && attacksPassed };
const failedGates = spec.requiredGates.filter((name) => finalGates[name] !== true);
const audit = {
  schemaVersion: 'bfs.codex-host-stability-longitudinal-audit.v0.1',
  experimentId: spec.experimentId,
  auditedAt: new Date().toISOString(),
  finalVerdict,
  fileIntegrity,
  syntheticAdmissibleControl: { valid: syntheticValid, selfHash: synthetic.results.selfHash },
  attackIdsExact,
  attackResults,
  attacksPassed: attackResults.filter((item) => item.rejected).length,
  attacksTotal: attackResults.length,
  auditCommands,
  replay: { codexVersion: replayVersion, processes: replayProcesses, newCrashReports: replayCrashes },
  finalGates,
  passedGates: spec.requiredGates.filter((name) => finalGates[name] === true).length,
  totalGates: spec.requiredGates.length,
  failedGates,
  selfHash: ''
};
const auditText = `${JSON.stringify(reseal(audit), null, 2)}\n`;
if (Buffer.byteLength(auditText) > spec.resourcePolicy.maximumAuditBytes) throw new Error('audit exceeds byte ceiling');
writeExclusiveDurable(auditPath, auditText);
const summaryText = `${JSON.stringify({
  experimentId: spec.experimentId,
  finalVerdict,
  gates: `${audit.passedGates}/${audit.totalGates}`,
  attacks: `${audit.attacksPassed}/${audit.attacksTotal}`,
  failedGates,
  auditPath: `${spec.formalRoot}/audit.json`
})}\n`;
if (Buffer.byteLength(summaryText) > spec.resourcePolicy.maximumStdoutBytes) throw new Error('audit summary exceeds byte ceiling');
process.stdout.write(summaryText);
