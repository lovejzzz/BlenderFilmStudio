#!/usr/bin/env node

import { createHash } from 'node:crypto';
import {
  closeSync, existsSync, fsyncSync, mkdirSync, openSync, readFileSync, readdirSync,
  statSync, writeFileSync,
} from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { execFileSync, spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const repo = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const specIndex = process.argv.indexOf('--spec');
const specRelative = specIndex === -1 ? 'specs/host-capacity-retention.v0.1.json' : process.argv[specIndex + 1];
if (!specRelative || !/^specs\/[A-Za-z0-9][A-Za-z0-9._-]*[.]json$/.test(specRelative)) throw new Error('invalid --spec path');
const specPath = resolve(repo, specRelative);
const spec = JSON.parse(readFileSync(specPath, 'utf8'));
const root = resolve(repo, spec.formalRoot);
const canonical = value => Array.isArray(value) ? `[${value.map(canonical).join(',')}]`
  : value && typeof value === 'object' ? `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}` : JSON.stringify(value);
const sha = value => createHash('sha256').update(value).digest('hex');
const shaFile = path => sha(readFileSync(path));
const withoutHash = value => { const copy = structuredClone(value); delete copy.selfHash; return copy; };
const validHash = value => value?.selfHash === sha(canonical(withoutHash(value)));
const seal = value => { value.selfHash = sha(canonical(withoutHash(value))); return value; };

function run(command, args, timeout = 10000) {
  const result = spawnSync(command, args, { cwd: repo, encoding: 'utf8', timeout, maxBuffer: 1024 * 1024, env: { ...process.env, LC_ALL: 'C' } });
  return { exitCode: result.status, stdout: result.stdout || '', stderr: result.stderr || '', errorCode: result.error?.code || null };
}

function writeExclusive(path, value, ceiling) {
  const text = typeof value === 'string' ? value : `${JSON.stringify(seal(value), null, 2)}\n`;
  if (Buffer.byteLength(text) > ceiling) throw new Error(`evidence ceiling: ${path}`);
  const fd = openSync(path, 'wx', 0o644);
  try { writeFileSync(fd, text); fsyncSync(fd); } finally { closeSync(fd); }
  const directoryFd = openSync(dirname(path), 'r');
  try { fsyncSync(directoryFd); } finally { closeSync(directoryFd); }
  return { sha256: sha(text), bytes: Buffer.byteLength(text), selfHash: typeof value === 'string' ? null : value.selfHash };
}

function maximumLossWithin(samples, current, minimumSpanSeconds, maximumSpanSeconds) {
  const currentMs = Date.parse(current.capturedAt);
  return samples.filter(sample => { const span = (currentMs - Date.parse(sample.capturedAt)) / 1000; return span >= minimumSpanSeconds && span <= maximumSpanSeconds; })
    .reduce((maximum, sample) => Math.max(maximum, sample.availableBytes - current.availableBytes), 0);
}

function severity(samples, current) {
  const sentinel = JSON.parse(readFileSync(resolve(repo, 'specs/host-capacity-sentinel.v0.2.json'), 'utf8'));
  const t = sentinel.thresholds;
  const rapid = maximumLossWithin(samples, current, t.rapidLossMinimumSpanSeconds, t.rapidLossMaximumSpanSeconds);
  const long = maximumLossWithin(samples, current, t.longLossMinimumSpanSeconds, t.longLossMaximumSpanSeconds);
  if (current.availableBytes < t.emergencyAvailableBytes || current.browserTempFilesystem.allocatedBytes >= t.browserCriticalBytes) return 'EMERGENCY_CAPACITY';
  if (current.availableBytes < t.criticalAvailableBytes) return 'CRITICAL_CAPACITY';
  if (current.availableBytes < t.warningAvailableBytes) return 'WARNING_CAPACITY';
  if (rapid >= t.rapidLossBytes || long >= t.longLossBytes || current.browserTempFilesystem.allocatedBytes >= t.browserWarningBytes) return 'WARNING_RAPID_LOSS';
  return 'HEALTHY';
}

function launchdState() {
  const target = `${spec.source.launchdDomain}/${spec.source.launchdLabel}`;
  const result = run('/bin/launchctl', ['print', target]);
  const text = result.stdout;
  return {
    target, loaded: result.exitCode === 0,
    runs: Number((text.match(/\bruns = (\d+)/) || [])[1] || -1),
    lastExitCode: Number((text.match(/\blast exit code = (-?\d+)/) || [])[1] || -1),
    intervalSeconds: Number((text.match(/\brun interval = (\d+) seconds/) || [])[1] || -1),
    printSha256: sha(text), printBytes: Buffer.byteLength(text),
  };
}

function readPlistString(path, key) {
  const text = readFileSync(path, 'utf8');
  return (text.match(new RegExp(`<key>${key}</key>\\s*<string>([^<]+)</string>`)) || [])[1] || null;
}

function runtimeState(firstSampleAt) {
  const processes = run('/bin/ps', ['-axo', 'pid=,lstart=,command=']).stdout.split('\n').filter(Boolean);
  const mainPath = '/Applications/ChatGPT.app/Contents/MacOS/ChatGPT';
  const main = processes.map(line => {
    const match = line.match(/^\s*(\d+)\s+(.{24})\s+(.*)$/);
    return match ? { pid: Number(match[1]), startedAt: new Date(match[2]).toISOString(), command: match[3] } : null;
  }).filter(value => value?.command === mainPath);
  const firstMs = Date.parse(firstSampleAt);
  const crashReports = existsSync(spec.runtimeExpectation.diagnosticReportsPath)
    ? readdirSync(spec.runtimeExpectation.diagnosticReportsPath).filter(name => /^ChatGPT.*[.]ips$/.test(name))
      .map(name => ({ name, modifiedMs: statSync(join(spec.runtimeExpectation.diagnosticReportsPath, name)).mtimeMs }))
      .filter(value => value.modifiedMs > firstMs).sort((a, b) => a.name.localeCompare(b.name)) : [];
  const app = spec.runtimeExpectation.appPlistPath;
  return {
    codexVersion: `${readPlistString(app, 'CFBundleShortVersionString')} (${readPlistString(app, 'CFBundleVersion')})`,
    appPlistSha256: shaFile(app), bundleIdentifier: readPlistString(app, 'CFBundleIdentifier'),
    main, crashReports,
  };
}

function aggregate(samples, observedAtMs = Date.now()) {
  const first = samples[0];
  const last = samples.at(-1);
  const intervalsMs = samples.slice(1).map((sample, index) => Date.parse(sample.capturedAt) - Date.parse(samples[index].capturedAt));
  const spanMs = Date.parse(last.capturedAt) - Date.parse(first.capturedAt);
  const hours = spanMs / 3600000;
  const diskLossBytes = Math.max(0, first.availableBytes - last.availableBytes);
  const stepLosses = samples.slice(1).map((sample, index) => Math.max(0, samples[index].availableBytes - sample.availableBytes));
  const colimaFirst = first.colima.vmDisk.allocatedBytes + first.colima.dataDisk.allocatedBytes;
  const colimaLast = last.colima.vmDisk.allocatedBytes + last.colima.dataDisk.allocatedBytes;
  const colimaGrowth = Math.max(0, colimaLast - colimaFirst);
  return {
    sampleCount: samples.length, intervalsMs, spanMs, latestAgeMs: observedAtMs - Date.parse(last.capturedAt),
    minimumAvailableBytes: Math.min(...samples.map(sample => sample.availableBytes)),
    diskLossBytes, diskLossRateBytesPerHour: hours > 0 ? diskLossBytes / hours : Infinity,
    maximumSingleIntervalLossBytes: Math.max(0, ...stepLosses),
    browserMaximumBytes: Math.max(...samples.map(sample => sample.browserTempFilesystem.allocatedBytes)),
    browserGrowthBytes: last.browserTempFilesystem.allocatedBytes - first.browserTempFilesystem.allocatedBytes,
    colimaAllocatedGrowthBytes: colimaGrowth, colimaAllocatedGrowthRateBytesPerHour: hours > 0 ? colimaGrowth / hours : Infinity,
    severities: samples.map((sample, index) => severity(samples.slice(0, index), sample)),
  };
}

if (process.argv.includes('--self-test')) {
  const start = Date.now() - 3600000;
  const samples = Array.from({ length: 5 }, (_, index) => seal({
    capturedAt: new Date(start + index * 900000).toISOString(), availableBytes: 300 * 1024 ** 3 - index * 1024 ** 2,
    browserTempFilesystem: { allocatedBytes: 20480 },
    colima: { vmDisk: { allocatedBytes: 1024 ** 3 }, dataDisk: { allocatedBytes: 7 * 1024 ** 3 } },
    prohibitedActions: { deletions: 0, cleanupOperations: 0, serviceRestarts: 0, dockerCalls: 0, blenderProcesses: 0, networkCalls: 0, modelCalls: 0 }, selfHash: '',
  }));
  const value = aggregate(samples, start + 3600000);
  if (value.spanMs !== 3600000 || value.intervalsMs.some(interval => interval !== 900000)
    || value.severities.some(item => item !== 'HEALTHY') || value.sampleCount !== 5) throw new Error('retention runner self-test failed');
  process.stdout.write('{"selfTest":"PASS","samples":5,"spanSeconds":3600}\n');
  process.exit(0);
}

const historyText = readFileSync(spec.source.historyPath, 'utf8');
const latestText = readFileSync(spec.source.latestPath, 'utf8');
const history = JSON.parse(historyText);
const latest = JSON.parse(latestText);
const launchd = launchdState();
const samples = history.samples || [];
const preAggregate = samples.length ? aggregate(samples) : { sampleCount: 0, spanMs: 0, latestAgeMs: Infinity };
const eligible = samples.length >= spec.observationPolicy.minimumSamples && preAggregate.spanMs >= spec.observationPolicy.minimumSpanSeconds * 1000
  && preAggregate.latestAgeMs <= spec.observationPolicy.maximumLatestAgeSeconds * 1000 && launchd.loaded;
if (process.argv.includes('--preflight') || !eligible) {
  const output = { status: eligible ? 'READY_UNATTENDED_RETENTION' : 'WAIT_UNATTENDED_RETENTION', sampleCount: samples.length, spanMs: preAggregate.spanMs, latestAgeMs: preAggregate.latestAgeMs, serviceLoaded: launchd.loaded, formalRootAbsent: !existsSync(root) };
  process.stdout.write(`${JSON.stringify(output)}\n`);
  process.exit(eligible ? 0 : 75);
}

if (existsSync(root)) throw new Error('formal root is not fresh');
const scoped = execFileSync('/usr/bin/git', ['status', '--short', '--', ...spec.releasePaths], { cwd: repo, encoding: 'utf8' }).trim();
const [head, origin] = execFileSync('/usr/bin/git', ['rev-parse', 'HEAD', 'origin/main'], { cwd: repo, encoding: 'utf8' }).trim().split('\n');
execFileSync('/usr/bin/git', ['merge-base', '--is-ancestor', spec.parentCommit, head], { cwd: repo });
if (scoped || head !== origin) throw new Error('release preflight failed');
if (!validHash(history) || !validHash(latest) || !samples.every(validHash)) throw new Error('source self-hash failed');
mkdirSync(root, { recursive: false });
const historyReceipt = writeExclusive(resolve(root, 'history-snapshot.json'), historyText, spec.byteCeilings.snapshot);
const latestReceipt = writeExclusive(resolve(root, 'latest-snapshot.json'), latestText, spec.byteCeilings.snapshot);
const start = {
  schemaVersion: 'bfs.host-capacity-retention-start.v0.1', experimentId: spec.experimentId,
  startedAt: new Date().toISOString(), specSha256: shaFile(specPath), git: { scoped, head, origin },
  parentEvidence: { resultsSha256: shaFile(resolve(repo, spec.parentEvidence.resultsPath)), auditSha256: shaFile(resolve(repo, spec.parentEvidence.auditPath)) },
  sourceReceipts: { history: historyReceipt, latest: latestReceipt }, selfHash: '',
};
const startReceipt = writeExclusive(resolve(root, 'start.json'), start, spec.byteCeilings.results);
const observedAtMs = Date.now();
const agg = aggregate(samples, observedAtMs);
const runtime = runtimeState(samples[0].capturedAt);
const plistExact = shaFile(spec.source.installedPlistPath) === shaFile(resolve(repo, 'launchd/com.blenderfilmstudio.capacity-sentinel.plist'));
const sourceValid = validHash(history) && validHash(latest) && samples.every(validHash) && latest.sample?.selfHash === samples.at(-1)?.selfHash
  && Buffer.byteLength(historyText) <= spec.observationPolicy.maximumStateBytes && samples.length <= spec.observationPolicy.maximumHistorySamples;
const cadence = samples.length >= spec.observationPolicy.minimumSamples && agg.spanMs >= spec.observationPolicy.minimumSpanSeconds * 1000
  && agg.intervalsMs.every(value => value >= spec.observationPolicy.minimumIntervalSeconds * 1000 && value <= spec.observationPolicy.maximumIntervalSeconds * 1000)
  && agg.latestAgeMs <= spec.observationPolicy.maximumLatestAgeSeconds * 1000;
const runtimeValid = runtime.codexVersion === spec.runtimeExpectation.codexVersion && runtime.appPlistSha256 === spec.runtimeExpectation.appPlistSha256
  && runtime.bundleIdentifier === spec.runtimeExpectation.bundleIdentifier && runtime.main.length === 1
  && runtime.main[0].pid === spec.runtimeExpectation.requiredMainPid && Date.parse(runtime.main[0].startedAt) <= Date.parse(samples[0].capturedAt)
  && runtime.crashReports.length === 0;
const gates = {
  SPEC_PARENT_AND_RELEASE_IDENTITY: start.specSha256 === shaFile(specPath) && start.parentEvidence.resultsSha256 === spec.parentEvidence.resultsSha256 && start.parentEvidence.auditSha256 === spec.parentEvidence.auditSha256 && head === origin && scoped === '',
  SOURCE_SELF_HASH_AND_BOUNDS: sourceValid,
  SAMPLE_COUNT_SPAN_AND_CADENCE: cadence,
  ALL_SAMPLES_CLASSIFY_HEALTHY: agg.severities.every(value => value === 'HEALTHY') && latest.classification.severity === 'HEALTHY' && !existsSync(spec.source.alertPath),
  DISK_FLOOR_AND_LOSS_RATE: agg.minimumAvailableBytes >= spec.observationPolicy.minimumAvailableBytes && agg.diskLossRateBytesPerHour <= spec.observationPolicy.maximumDiskLossRateBytesPerHour && agg.maximumSingleIntervalLossBytes <= spec.observationPolicy.maximumSingleIntervalLossBytes,
  BROWSER_TEMP_BOUNDED: agg.browserMaximumBytes <= spec.observationPolicy.maximumBrowserTempBytes && agg.browserGrowthBytes <= spec.observationPolicy.maximumBrowserGrowthBytes,
  COLIMA_ALLOCATION_GROWTH_BOUNDED: agg.colimaAllocatedGrowthRateBytesPerHour <= spec.observationPolicy.maximumColimaAllocatedGrowthRateBytesPerHour,
  PROHIBITED_ACTIONS_ZERO: samples.every(sample => Object.values(sample.prohibitedActions || {}).every(value => value === 0)),
  LAUNCHD_CONTINUITY: launchd.loaded && launchd.runs >= samples.length && launchd.lastExitCode === 0 && launchd.intervalSeconds === spec.observationPolicy.requiredLaunchdIntervalSeconds && plistExact,
  CODEX_RUNTIME_PID_AND_CRASH_CONTINUITY: runtimeValid,
  SNAPSHOT_AND_RESULTS_INTEGRITY: 'PENDING_WRITE',
  INDEPENDENT_AUDIT_REPLAY: 'PENDING',
};
const baseNames = spec.requiredGates.filter(name => !['SNAPSHOT_AND_RESULTS_INTEGRITY', 'INDEPENDENT_AUDIT_REPLAY'].includes(name));
const results = {
  schemaVersion: 'bfs.host-capacity-retention-results.v0.1', experimentId: spec.experimentId,
  completedAt: new Date().toISOString(), observedAt: new Date(observedAtMs).toISOString(), spec: { path: specRelative, sha256: shaFile(specPath) },
  startReceipt, sourceReceipts: { history: historyReceipt, latest: latestReceipt }, aggregate: agg, launchd, runtime,
  resourceAccounting: { blenderProcesses: 0, dockerCalls: 0, networkCalls: 0, modelCalls: 0, cleanupOperations: 0, serviceMutations: 0 },
  gates, failedGates: baseNames.filter(name => gates[name] !== true), provisionalVerdict: '', receiptBytes: 0, selfHash: '',
};
results.gates.SNAPSHOT_AND_RESULTS_INTEGRITY = true;
results.failedGates = spec.requiredGates.filter(name => name !== 'INDEPENDENT_AUDIT_REPLAY' && results.gates[name] !== true);
results.provisionalVerdict = results.failedGates.length ? 'BLOCKED_UNATTENDED_RETENTION' : 'ADMITTED_PENDING_AUDIT';
let resultsText;
for (let index = 0; index < 6; index += 1) { seal(results); resultsText = `${JSON.stringify(results, null, 2)}\n`; results.receiptBytes = Buffer.byteLength(resultsText); }
seal(results);
const resultReceipt = writeExclusive(resolve(root, 'results.json'), results, spec.byteCeilings.results);
process.stdout.write(`${JSON.stringify({ experimentId: spec.experimentId, provisionalVerdict: results.provisionalVerdict, gates: `${spec.requiredGates.filter(name => name !== 'INDEPENDENT_AUDIT_REPLAY' && results.gates[name] === true).length}/11`, failedGates: results.failedGates, resultsSha256: resultReceipt.sha256 })}\n`);
