#!/usr/bin/env node

import { createHash } from 'node:crypto';
import { closeSync, existsSync, fsyncSync, openSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { execFileSync, spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const repo = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const specIndex = process.argv.indexOf('--spec');
const specRelative = specIndex === -1 ? 'specs/host-capacity-retention.v0.1.json' : process.argv[specIndex + 1];
if (!specRelative || !/^specs\/[A-Za-z0-9][A-Za-z0-9._-]*[.]json$/.test(specRelative)) throw new Error('invalid --spec path');
const specPath = resolve(repo, specRelative);
const spec = JSON.parse(readFileSync(specPath, 'utf8'));
const sentinelSpec = JSON.parse(readFileSync(resolve(repo, 'specs/host-capacity-sentinel.v0.2.json'), 'utf8'));
const root = resolve(repo, spec.formalRoot);
const auditPath = resolve(root, 'audit.json');
const canonical = value => Array.isArray(value) ? `[${value.map(canonical).join(',')}]`
  : value && typeof value === 'object' ? `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}` : JSON.stringify(value);
const sha = value => createHash('sha256').update(value).digest('hex');
const shaFile = path => sha(readFileSync(path));
const serialized = value => `${JSON.stringify(value, null, 2)}\n`;
const withoutHash = value => { const copy = structuredClone(value); delete copy.selfHash; return copy; };
const validHash = value => value?.selfHash === sha(canonical(withoutHash(value)));
const seal = value => { value.selfHash = sha(canonical(withoutHash(value))); return value; };

function run(command, args) {
  const result = spawnSync(command, args, { cwd: repo, encoding: 'utf8', timeout: 10000, maxBuffer: 1024 * 1024, env: { ...process.env, LC_ALL: 'C' } });
  return { exitCode: result.status, stdout: result.stdout || '', stderr: result.stderr || '' };
}

function maximumLossWithin(samples, current, minimumSpanSeconds, maximumSpanSeconds) {
  const currentMs = Date.parse(current.capturedAt);
  return samples.filter(sample => { const span = (currentMs - Date.parse(sample.capturedAt)) / 1000; return span >= minimumSpanSeconds && span <= maximumSpanSeconds; })
    .reduce((maximum, sample) => Math.max(maximum, sample.availableBytes - current.availableBytes), 0);
}

function severity(samples, current) {
  const t = sentinelSpec.thresholds;
  const rapid = maximumLossWithin(samples, current, t.rapidLossMinimumSpanSeconds, t.rapidLossMaximumSpanSeconds);
  const long = maximumLossWithin(samples, current, t.longLossMinimumSpanSeconds, t.longLossMaximumSpanSeconds);
  if (current.availableBytes < t.emergencyAvailableBytes || current.browserTempFilesystem.allocatedBytes >= t.browserCriticalBytes) return 'EMERGENCY_CAPACITY';
  if (current.availableBytes < t.criticalAvailableBytes) return 'CRITICAL_CAPACITY';
  if (current.availableBytes < t.warningAvailableBytes) return 'WARNING_CAPACITY';
  if (rapid >= t.rapidLossBytes || long >= t.longLossBytes || current.browserTempFilesystem.allocatedBytes >= t.browserWarningBytes) return 'WARNING_RAPID_LOSS';
  return 'HEALTHY';
}

function aggregate(samples, observedAt) {
  if (!samples.length) return { sampleCount: 0, intervalsMs: [], spanMs: 0, latestAgeMs: Infinity };
  const first = samples[0];
  const last = samples.at(-1);
  const intervalsMs = samples.slice(1).map((sample, index) => Date.parse(sample.capturedAt) - Date.parse(samples[index].capturedAt));
  const spanMs = Date.parse(last.capturedAt) - Date.parse(first.capturedAt);
  const hours = spanMs / 3600000;
  const diskLossBytes = Math.max(0, first.availableBytes - last.availableBytes);
  const colimaFirst = first.colima.vmDisk.allocatedBytes + first.colima.dataDisk.allocatedBytes;
  const colimaLast = last.colima.vmDisk.allocatedBytes + last.colima.dataDisk.allocatedBytes;
  const colimaGrowth = Math.max(0, colimaLast - colimaFirst);
  return {
    sampleCount: samples.length, intervalsMs, spanMs, latestAgeMs: Date.parse(observedAt) - Date.parse(last.capturedAt),
    minimumAvailableBytes: Math.min(...samples.map(sample => sample.availableBytes)),
    diskLossBytes, diskLossRateBytesPerHour: hours > 0 ? diskLossBytes / hours : Infinity,
    maximumSingleIntervalLossBytes: Math.max(0, ...samples.slice(1).map((sample, index) => Math.max(0, samples[index].availableBytes - sample.availableBytes))),
    browserMaximumBytes: Math.max(...samples.map(sample => sample.browserTempFilesystem.allocatedBytes)),
    browserGrowthBytes: last.browserTempFilesystem.allocatedBytes - first.browserTempFilesystem.allocatedBytes,
    colimaAllocatedGrowthBytes: colimaGrowth, colimaAllocatedGrowthRateBytesPerHour: hours > 0 ? colimaGrowth / hours : Infinity,
    severities: samples.map((sample, index) => severity(samples.slice(0, index), sample)),
  };
}

function diskRateBreachLoss(samples) {
  const spanMs = Date.parse(samples.at(-1).capturedAt) - Date.parse(samples[0].capturedAt);
  if (!(spanMs > 0)) throw new Error('A09 requires a positive sample span');
  const maximumRate = spec.observationPolicy.maximumDiskLossRateBytesPerHour;
  const lossBytes = Math.floor(maximumRate * spanMs / 3600000) + 1;
  if (!(lossBytes / (spanMs / 3600000) > maximumRate)) throw new Error('A09 failed to construct a strict rate breach');
  return lossBytes;
}

function readPlistString(path, key) {
  const text = readFileSync(path, 'utf8');
  return (text.match(new RegExp(`<key>${key}</key>\\s*<string>([^<]+)</string>`)) || [])[1] || null;
}

function liveRuntime(firstSampleAt) {
  const rows = run('/bin/ps', ['-axo', 'pid=,lstart=,command=']).stdout.split('\n').filter(Boolean);
  const mainPath = '/Applications/ChatGPT.app/Contents/MacOS/ChatGPT';
  const main = rows.map(line => { const match = line.match(/^\s*(\d+)\s+(.{24})\s+(.*)$/); return match ? { pid: Number(match[1]), startedAt: new Date(match[2]).toISOString(), command: match[3] } : null; }).filter(value => value?.command === mainPath);
  const firstMs = Date.parse(firstSampleAt);
  const crashes = existsSync(spec.runtimeExpectation.diagnosticReportsPath)
    ? readdirSync(spec.runtimeExpectation.diagnosticReportsPath).filter(name => /^ChatGPT.*[.]ips$/.test(name))
      .map(name => ({ name, modifiedMs: statSync(join(spec.runtimeExpectation.diagnosticReportsPath, name)).mtimeMs }))
      .filter(value => value.modifiedMs > firstMs).sort((a, b) => a.name.localeCompare(b.name)) : [];
  const app = spec.runtimeExpectation.appPlistPath;
  return { codexVersion: `${readPlistString(app, 'CFBundleShortVersionString')} (${readPlistString(app, 'CFBundleVersion')})`, appPlistSha256: shaFile(app), bundleIdentifier: readPlistString(app, 'CFBundleIdentifier'), main, crashReports: crashes };
}

function liveLaunchd() {
  const target = `${spec.source.launchdDomain}/${spec.source.launchdLabel}`;
  const result = run('/bin/launchctl', ['print', target]);
  return { loaded: result.exitCode === 0, runs: Number((result.stdout.match(/\bruns = (\d+)/) || [])[1] || -1), lastExitCode: Number((result.stdout.match(/\blast exit code = (-?\d+)/) || [])[1] || -1), intervalSeconds: Number((result.stdout.match(/\brun interval = (\d+) seconds/) || [])[1] || -1), printSha256: sha(result.stdout) };
}

function runtimeValid(runtime, firstAt) {
  return runtime.codexVersion === spec.runtimeExpectation.codexVersion && runtime.appPlistSha256 === spec.runtimeExpectation.appPlistSha256
    && runtime.bundleIdentifier === spec.runtimeExpectation.bundleIdentifier && runtime.main.length === 1
    && runtime.main[0].pid === spec.runtimeExpectation.requiredMainPid && Date.parse(runtime.main[0].startedAt) <= Date.parse(firstAt)
    && runtime.crashReports.length === 0;
}

function semanticGates(bundle) {
  const { start, history, latest, results } = bundle;
  const samples = history.samples || [];
  const agg = aggregate(samples, results.observedAt);
  const cadence = samples.length >= spec.observationPolicy.minimumSamples && agg.spanMs >= spec.observationPolicy.minimumSpanSeconds * 1000
    && agg.intervalsMs.every(value => value >= spec.observationPolicy.minimumIntervalSeconds * 1000 && value <= spec.observationPolicy.maximumIntervalSeconds * 1000)
    && agg.latestAgeMs <= spec.observationPolicy.maximumLatestAgeSeconds * 1000;
  return {
    SPEC_PARENT_AND_RELEASE_IDENTITY: results.spec.sha256 === shaFile(specPath) && start.specSha256 === results.spec.sha256
      && start.parentEvidence.resultsSha256 === spec.parentEvidence.resultsSha256 && start.parentEvidence.auditSha256 === spec.parentEvidence.auditSha256,
    SOURCE_SELF_HASH_AND_BOUNDS: validHash(history) && validHash(latest) && samples.every(validHash) && latest.sample?.selfHash === samples.at(-1)?.selfHash
      && Buffer.byteLength(serialized(history)) <= spec.observationPolicy.maximumStateBytes && samples.length <= spec.observationPolicy.maximumHistorySamples,
    SAMPLE_COUNT_SPAN_AND_CADENCE: cadence,
    ALL_SAMPLES_CLASSIFY_HEALTHY: agg.severities.every(value => value === 'HEALTHY') && latest.classification.severity === 'HEALTHY',
    DISK_FLOOR_AND_LOSS_RATE: agg.minimumAvailableBytes >= spec.observationPolicy.minimumAvailableBytes && agg.diskLossRateBytesPerHour <= spec.observationPolicy.maximumDiskLossRateBytesPerHour && agg.maximumSingleIntervalLossBytes <= spec.observationPolicy.maximumSingleIntervalLossBytes,
    BROWSER_TEMP_BOUNDED: agg.browserMaximumBytes <= spec.observationPolicy.maximumBrowserTempBytes && agg.browserGrowthBytes <= spec.observationPolicy.maximumBrowserGrowthBytes,
    COLIMA_ALLOCATION_GROWTH_BOUNDED: agg.colimaAllocatedGrowthRateBytesPerHour <= spec.observationPolicy.maximumColimaAllocatedGrowthRateBytesPerHour,
    PROHIBITED_ACTIONS_ZERO: samples.every(sample => Object.values(sample.prohibitedActions || {}).every(value => value === 0)),
    LAUNCHD_CONTINUITY: results.launchd.loaded && results.launchd.runs >= samples.length && results.launchd.lastExitCode === 0 && results.launchd.intervalSeconds === spec.observationPolicy.requiredLaunchdIntervalSeconds,
    CODEX_RUNTIME_PID_AND_CRASH_CONTINUITY: samples.length > 0 && runtimeValid(results.runtime, samples[0].capturedAt),
    SNAPSHOT_AND_RESULTS_INTEGRITY: validHash(start) && validHash(results) && canonical(results.aggregate) === canonical(agg),
    INDEPENDENT_AUDIT_REPLAY: 'PENDING',
  };
}

function resealBundle(bundle) {
  bundle.history.samples.forEach(seal);
  seal(bundle.history);
  bundle.latest.sample = structuredClone(bundle.history.samples.at(-1));
  const previous = bundle.history.samples.slice(0, -1);
  bundle.latest.classification.severity = severity(previous, bundle.latest.sample);
  seal(bundle.latest);
  seal(bundle.start);
  const historyText = serialized(bundle.history);
  const latestText = serialized(bundle.latest);
  const startText = serialized(bundle.start);
  bundle.results.startReceipt = { sha256: sha(startText), bytes: Buffer.byteLength(startText), selfHash: bundle.start.selfHash };
  bundle.results.sourceReceipts = { history: { sha256: sha(historyText), bytes: Buffer.byteLength(historyText), selfHash: null }, latest: { sha256: sha(latestText), bytes: Buffer.byteLength(latestText), selfHash: null } };
  bundle.results.aggregate = aggregate(bundle.history.samples, bundle.results.observedAt);
  seal(bundle.results);
  return { start: startText, history: historyText, latest: latestText, results: serialized(bundle.results) };
}

function candidateValid(bundle, texts) {
  const expected = semanticGates(bundle);
  const names = spec.requiredGates.filter(name => name !== 'INDEPENDENT_AUDIT_REPLAY');
  return names.every(name => expected[name] === true && bundle.results.gates[name] === true)
    && bundle.results.startReceipt.sha256 === sha(texts.start) && bundle.results.sourceReceipts.history.sha256 === sha(texts.history)
    && bundle.results.sourceReceipts.latest.sha256 === sha(texts.latest) && validHash(bundle.results);
}

if (process.argv.includes('--self-test')) {
  const start = Date.now() - 3600000;
  const samples = Array.from({ length: 5 }, (_, index) => seal({ capturedAt: new Date(start + index * 900000).toISOString(), availableBytes: 300 * 1024 ** 3, browserTempFilesystem: { allocatedBytes: 20480 }, colima: { vmDisk: { allocatedBytes: 1024 ** 3 }, dataDisk: { allocatedBytes: 7 * 1024 ** 3 } }, prohibitedActions: { deletions: 0, cleanupOperations: 0, serviceRestarts: 0, dockerCalls: 0, blenderProcesses: 0, networkCalls: 0, modelCalls: 0 }, selfHash: '' }));
  const agg = aggregate(samples, new Date(start + 3600000).toISOString());
  if (agg.spanMs !== 3600000 || agg.severities.some(value => value !== 'HEALTHY') || spec.registeredAttacks.length !== 15) throw new Error('retention auditor self-test failed');
  const drifted = structuredClone(samples);
  drifted.at(-1).capturedAt = new Date(start + 3600821).toISOString();
  const breachLossBytes = diskRateBreachLoss(drifted);
  const breachRate = breachLossBytes / (3600821 / 3600000);
  if (!(breachRate > spec.observationPolicy.maximumDiskLossRateBytesPerHour)) throw new Error('span-normalized A09 self-test failed');
  process.stdout.write(`${JSON.stringify({ selfTest: 'PASS', independentAggregate: true, registeredAttacks: 15, driftSpanMs: 3600821, spanNormalizedA09: true })}\n`);
  process.exit(0);
}

if (!existsSync(resolve(root, 'results.json')) || existsSync(auditPath)) throw new Error('formal evidence state invalid');
const texts = { start: readFileSync(resolve(root, 'start.json'), 'utf8'), history: readFileSync(resolve(root, 'history-snapshot.json'), 'utf8'), latest: readFileSync(resolve(root, 'latest-snapshot.json'), 'utf8'), results: readFileSync(resolve(root, 'results.json'), 'utf8') };
const observed = { start: JSON.parse(texts.start), history: JSON.parse(texts.history), latest: JSON.parse(texts.latest), results: JSON.parse(texts.results) };
const expected = semanticGates(observed);
const names = spec.requiredGates.filter(name => name !== 'INDEPENDENT_AUDIT_REPLAY');
const scoped = execFileSync('/usr/bin/git', ['status', '--short', '--', ...spec.releasePaths], { cwd: repo, encoding: 'utf8' }).trim();
const [head, origin] = execFileSync('/usr/bin/git', ['rev-parse', 'HEAD', 'origin/main'], { cwd: repo, encoding: 'utf8' }).trim().split('\n');
const currentLaunchd = liveLaunchd();
const currentRuntime = liveRuntime(observed.history.samples[0].capturedAt);
const fileIntegrity = {
  START: validHash(observed.start) && observed.results.startReceipt.sha256 === sha(texts.start),
  SNAPSHOTS: validHash(observed.history) && validHash(observed.latest) && observed.results.sourceReceipts.history.sha256 === sha(texts.history) && observed.results.sourceReceipts.latest.sha256 === sha(texts.latest),
  RESULTS: validHash(observed.results) && observed.results.receiptBytes === Buffer.byteLength(texts.results) && Buffer.byteLength(texts.results) <= spec.byteCeilings.results,
  GATE_PROJECTION: names.every(name => expected[name] === true && observed.results.gates[name] === expected[name]),
  RELEASE: scoped === '' && head === origin && head === observed.start.git.head,
  PARENT: shaFile(resolve(repo, spec.parentEvidence.resultsPath)) === spec.parentEvidence.resultsSha256 && shaFile(resolve(repo, spec.parentEvidence.auditPath)) === spec.parentEvidence.auditSha256,
  LIVE_LAUNCHD: currentLaunchd.loaded && currentLaunchd.lastExitCode === 0 && currentLaunchd.intervalSeconds === spec.observationPolicy.requiredLaunchdIntervalSeconds,
  LIVE_RUNTIME: runtimeValid(currentRuntime, observed.history.samples[0].capturedAt),
  NO_ALERT: !existsSync(spec.source.alertPath),
};

const attacks = [
  ['A01_SPEC_SHA_MUTATION', bundle => { bundle.results.spec.sha256 = '0'.repeat(64); }, 'result'],
  ['A02_PARENT_EVIDENCE_MUTATION', bundle => { bundle.start.parentEvidence.resultsSha256 = '0'.repeat(64); }],
  ['A03_SAMPLE_REMOVAL', bundle => { bundle.history.samples.pop(); }],
  ['A04_TOTAL_SPAN_SHORTENING', bundle => { bundle.history.samples.at(-1).capturedAt = new Date(Date.parse(bundle.history.samples[0].capturedAt) + 3599999).toISOString(); }],
  ['A05_INTERVAL_TOO_SHORT', bundle => { bundle.history.samples[1].capturedAt = new Date(Date.parse(bundle.history.samples[0].capturedAt) + 599999).toISOString(); }],
  ['A06_INTERVAL_TOO_LONG', bundle => { bundle.history.samples[1].capturedAt = new Date(Date.parse(bundle.history.samples[0].capturedAt) + 1200001).toISOString(); }],
  ['A07_STALE_LATEST_SAMPLE', bundle => { bundle.results.observedAt = new Date(Date.parse(bundle.history.samples.at(-1).capturedAt) + 1200001).toISOString(); }],
  ['A08_DISK_FLOOR_BREACH', bundle => { bundle.history.samples[0].availableBytes = spec.observationPolicy.minimumAvailableBytes - 1; }],
  ['A09_DISK_RATE_BREACH', bundle => { bundle.history.samples.at(-1).availableBytes = bundle.history.samples[0].availableBytes - diskRateBreachLoss(bundle.history.samples); }],
  ['A10_BROWSER_GROWTH_BREACH', bundle => { bundle.history.samples.at(-1).browserTempFilesystem.allocatedBytes = bundle.history.samples[0].browserTempFilesystem.allocatedBytes + spec.observationPolicy.maximumBrowserGrowthBytes + 1; }],
  ['A11_COLIMA_GROWTH_BREACH', bundle => { bundle.history.samples.at(-1).colima.dataDisk.allocatedBytes += spec.observationPolicy.maximumColimaAllocatedGrowthRateBytesPerHour + 1; }],
  ['A12_PROHIBITED_ACTION_MUTATION', bundle => { bundle.history.samples[0].prohibitedActions.deletions = 1; }],
  ['A13_MAIN_PID_MUTATION', bundle => { bundle.results.runtime.main[0].pid = 1; }, 'result'],
  ['A14_NEW_CRASH_REPORT_MUTATION', bundle => { bundle.results.runtime.crashReports.push({ name: 'ChatGPT-test.ips', modifiedMs: Date.now() }); }, 'result'],
  ['A15_SELF_HASH_MUTATION', bundle => { bundle.results.selfHash = '0'.repeat(64); }, 'none'],
];
const attackResults = attacks.map(([id, mutate, mode = 'bundle']) => {
  const bundle = structuredClone(observed);
  mutate(bundle);
  let candidateTexts;
  if (mode === 'bundle') candidateTexts = resealBundle(bundle);
  else if (mode === 'result') { seal(bundle.results); candidateTexts = { ...texts, results: serialized(bundle.results) }; }
  else candidateTexts = { ...texts, results: serialized(bundle.results) };
  return { id, rejected: !candidateValid(bundle, candidateTexts) };
});
const attackIdsExact = canonical(attacks.map(value => value[0])) === canonical(spec.registeredAttacks);
const attacksPassed = attackIdsExact && attackResults.every(value => value.rejected);
const integrityPassed = Object.values(fileIntegrity).every(Boolean);
const finalGates = { ...observed.results.gates, INDEPENDENT_AUDIT_REPLAY: integrityPassed && attacksPassed };
const failedGates = spec.requiredGates.filter(name => finalGates[name] !== true);
const finalVerdict = failedGates.length ? 'INVALID_UNATTENDED_RETENTION' : 'ONE_HOUR_UNATTENDED_RETENTION_ADMITTED';
const audit = { schemaVersion: 'bfs.host-capacity-retention-audit.v0.1', experimentId: spec.experimentId, auditedAt: new Date().toISOString(), finalVerdict, fileIntegrity, attackIdsExact, attackResults, attacksPassed: attackResults.filter(value => value.rejected).length, attacksTotal: attackResults.length, finalGates, passedGates: spec.requiredGates.filter(name => finalGates[name] === true).length, totalGates: spec.requiredGates.length, failedGates, currentLaunchd, currentRuntime, selfHash: '' };
seal(audit);
const auditText = serialized(audit);
if (Buffer.byteLength(auditText) > spec.byteCeilings.audit) throw new Error('audit ceiling');
const fd = openSync(auditPath, 'wx', 0o644);
try { writeFileSync(fd, auditText); fsyncSync(fd); } finally { closeSync(fd); }
process.stdout.write(`${JSON.stringify({ experimentId: spec.experimentId, finalVerdict, gates: `${audit.passedGates}/${audit.totalGates}`, attacks: `${audit.attacksPassed}/${audit.attacksTotal}`, failedGates })}\n`);
