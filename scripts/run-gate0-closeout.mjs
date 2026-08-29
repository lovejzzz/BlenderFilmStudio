#!/usr/bin/env node

import { createHash } from 'node:crypto';
import { closeSync, existsSync, fsyncSync, mkdirSync, openSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { execFileSync, spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const repo = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const specPath = resolve(repo, 'specs/gate0-closeout.v0.1.json');
const spec = JSON.parse(readFileSync(specPath, 'utf8'));
const root = resolve(repo, spec.formalRoot);
const canonical = value => Array.isArray(value) ? `[${value.map(canonical).join(',')}]`
  : value && typeof value === 'object' ? `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}` : JSON.stringify(value);
const sha = value => createHash('sha256').update(value).digest('hex');
const shaFile = path => sha(readFileSync(path));
const withoutHash = value => { const copy = structuredClone(value); delete copy.selfHash; return copy; };
const validHash = value => value?.selfHash === sha(canonical(withoutHash(value)));
const seal = value => { value.selfHash = sha(canonical(withoutHash(value))); return value; };
const same = (left, right) => canonical(left) === canonical(right);

function run(command, args, timeout = 10000) {
  const value = spawnSync(command, args, { cwd: repo, encoding: 'utf8', timeout, maxBuffer: 1024 * 1024, env: { ...process.env, LC_ALL: 'C' } });
  return { exitCode: value.status, stdout: value.stdout || '', stderr: value.stderr || '', errorCode: value.error?.code || null };
}

function readPlistString(path, key) {
  const text = readFileSync(path, 'utf8');
  return (text.match(new RegExp(`<key>${key}</key>\\s*<string>([^<]+)</string>`)) || [])[1] || null;
}

function loadEvidence() {
  const evidence = {};
  const receipts = {};
  for (const [id, [relativePath, expectedSha256]] of Object.entries(spec.evidence)) {
    const path = resolve(repo, relativePath);
    const text = readFileSync(path, 'utf8');
    evidence[id] = JSON.parse(text);
    receipts[id] = { path: relativePath, expectedSha256, actualSha256: sha(text), bytes: Buffer.byteLength(text), selfHashValid: validHash(evidence[id]) };
  }
  return { evidence, receipts };
}

function launchdState() {
  const value = run('/bin/launchctl', ['print', spec.live.launchdTarget]);
  return {
    loaded: value.exitCode === 0,
    runs: Number((value.stdout.match(/\bruns = (\d+)/) || [])[1] || -1),
    lastExitCode: Number((value.stdout.match(/\blast exit code = (-?\d+)/) || [])[1] || -1),
    intervalSeconds: Number((value.stdout.match(/\brun interval = (\d+) seconds/) || [])[1] || -1),
    printSha256: sha(value.stdout), printBytes: Buffer.byteLength(value.stdout),
  };
}

function runtimeState() {
  const mainPath = '/Applications/ChatGPT.app/Contents/MacOS/ChatGPT';
  const rows = run('/bin/ps', ['-axo', 'pid=,lstart=,command=']).stdout.split('\n').filter(Boolean);
  const main = rows.map(line => {
    const match = line.match(/^\s*(\d+)\s+(.{24})\s+(.*)$/);
    return match ? { pid: Number(match[1]), startedAt: new Date(match[2]).toISOString(), command: match[3] } : null;
  }).filter(value => value?.command === mainPath);
  const cutoff = Date.parse(spec.live.crashCutoff);
  const crashReports = existsSync(spec.live.diagnosticReportsPath)
    ? readdirSync(spec.live.diagnosticReportsPath).filter(name => /^ChatGPT.*[.]ips$/.test(name))
      .map(name => ({ name, modifiedMs: statSync(join(spec.live.diagnosticReportsPath, name)).mtimeMs }))
      .filter(value => value.modifiedMs > cutoff).sort((a, b) => a.name.localeCompare(b.name)) : [];
  return {
    codexVersion: `${readPlistString(spec.live.appPlistPath, 'CFBundleShortVersionString')} (${readPlistString(spec.live.appPlistPath, 'CFBundleVersion')})`,
    appPlistSha256: shaFile(spec.live.appPlistPath), bundleIdentifier: readPlistString(spec.live.appPlistPath, 'CFBundleIdentifier'), main, crashReports,
  };
}

function liveSentinelState(observedAtMs = Date.now()) {
  const historyText = readFileSync(spec.live.historyPath, 'utf8');
  const latestText = readFileSync(spec.live.latestPath, 'utf8');
  const history = JSON.parse(historyText);
  const latest = JSON.parse(latestText);
  return {
    history, latest, historyBytes: Buffer.byteLength(historyText), latestBytes: Buffer.byteLength(latestText),
    historySha256: sha(historyText), latestSha256: sha(latestText), latestAgeMs: observedAtMs - Date.parse(latest.sample?.capturedAt),
    alertAbsent: !existsSync(spec.live.alertPath), installedPlistSha256: shaFile(spec.live.installedPlistPath), templatePlistSha256: shaFile(resolve(repo, spec.live.templatePlistPath)),
  };
}

function matchingContainers(initial, final) {
  const fields = value => ({ id: value.id, name: value.name, image: value.image, restartPolicy: value.restartPolicy, autoRemove: value.autoRemove, running: value.running });
  return same(initial.docker.containers.map(fields).sort((a, b) => a.id.localeCompare(b.id)), final.docker.containers.map(fields).sort((a, b) => a.id.localeCompare(b.id)));
}

function diskIdentity(initial, final, key) {
  return ['path', 'device', 'inode', 'logicalBytes'].every(field => initial.disks[key][field] === final.disks[key][field]);
}

function d2Operational(e) {
  const initial = e.d2Start.initialState;
  const started = e.d2StartTransition.state;
  const final = e.d2Failure.finalState;
  const expected = spec.expected.d2;
  const resource = e.d2Failure.resourceAccounting;
  return e.d2Stop.transition === 'STOP_DEFAULT' && e.d2Stop.confirmed === true && e.d2Stop.command.exitCode === 0
    && e.d2Stop.state.profile.running === false && e.d2Stop.state.docker.socketReachable === false && e.d2Stop.state.docker.runningIds.length === 0
    && e.d2StartTransition.transition === 'START_DEFAULT_AND_RESTORE' && e.d2StartTransition.confirmed === true && e.d2StartTransition.command.exitCode === 0
    && e.d2StartTransition.explicitContainerStarts.length === 0 && started.profile.running === true && started.docker.socketReachable === true
    && same(started.docker.runningIds, expected.containerIds) && same(final.docker.runningIds, expected.containerIds) && matchingContainers(initial, started) && matchingContainers(initial, final)
    && ['arch', 'runtime', 'mountType'].every(field => initial.profile[field] === started.profile[field] && initial.profile[field] === final.profile[field])
    && initial.configs.colimaConfig.sha256 === expected.authoritativeConfigSha256 && started.configs.colimaConfig.sha256 === expected.authoritativeConfigSha256 && final.configs.colimaConfig.sha256 === expected.authoritativeConfigSha256
    && initial.configs.limaConfig.sha256 === expected.generatedLimaInitialSha256 && started.configs.limaConfig.sha256 === expected.generatedLimaFinalSha256 && final.configs.limaConfig.sha256 === expected.generatedLimaFinalSha256
    && expected.generatedLimaInitialSha256 !== expected.generatedLimaFinalSha256 && diskIdentity(initial, started, 'vmDisk') && diskIdentity(initial, started, 'dataDisk') && diskIdentity(initial, final, 'vmDisk') && diskIdentity(initial, final, 'dataDisk')
    && e.d2Failure.error === expected.formalFailure && e.d2Failure.finalRestored === false && e.d2Recovery.reason === 'final-restoration-invariant' && e.d2Recovery.restored === false && e.d2Recovery.actions.length === 0
    && resource.stopCommands === 1 && resource.startCommands === 1 && resource.explicitContainerStarts === 0
    && ['filesystemWritesOutsideFormalRoot', 'cleanupOperations', 'profileConfigurationMutations', 'containerCreates', 'containerRemoves', 'imageOrVolumeMutations', 'signalsSent', 'networkCalls', 'modelCalls'].every(key => resource[key] === 0)
    && !existsSync(resolve(repo, 'experiments/codex-host-disk-colima-ab-v0-1/results.json')) && !existsSync(resolve(repo, 'experiments/codex-host-disk-colima-ab-v0-1/audit.json'));
}

function semanticGates(model) {
  const { evidence: e, receipts, live, launchd, runtime, resourceAccounting } = model;
  const latest = live.latest;
  const history = live.history;
  const latestSample = latest.sample;
  const r5Actions = e.r5Install.actions;
  const gates = {
    SPEC_RELEASE_AND_EVIDENCE_HASHES: model.releaseValid && Object.values(receipts).every(value => value.actualSha256 === value.expectedSha256),
    EVIDENCE_SELF_HASHES: Object.values(receipts).every(value => value.selfHashValid),
    R2_RESTART_READMISSION: e.r2Results.provisionalVerdict === 'ADMITTED_PENDING_AUDIT' && e.r2Results.failedGates.length === 0 && Object.values(e.r2Results.gates).filter(value => value !== 'PENDING').every(value => value === true) && e.r2Audit.finalVerdict === spec.expected.r2.verdict && e.r2Audit.passedGates === spec.expected.r2.gates && e.r2Audit.totalGates === spec.expected.r2.gates && e.r2Audit.attacksPassed === spec.expected.r2.attacks && e.r2Audit.attacksTotal === spec.expected.r2.attacks,
    R3_FAILURE_PRESERVED: e.r3Results.provisionalVerdict === 'BLOCKED_HOST_STABILITY' && same(e.r3Results.failedGates, [spec.expected.r3.failedGate]) && e.r3Audit.finalVerdict === spec.expected.r3.verdict && e.r3Audit.passedGates === spec.expected.r3.passedGates && e.r3Audit.totalGates === spec.expected.r3.gates && e.r3Audit.attacksPassed === spec.expected.r3.attacks && same(e.r3Audit.failedGates, [spec.expected.r3.failedGate]),
    R4_POST_RECLAIM_STABILITY: e.r4Results.provisionalVerdict === 'ADMITTED_PENDING_AUDIT' && e.r4Results.failedGates.length === 0 && e.r4Results.gates.DISK_RETENTION_BOUNDED === true && e.r4Results.gates.BROWSER_TEMP_FILESYSTEM_BOUNDED === true && e.r4Audit.finalVerdict === spec.expected.r4.verdict && e.r4Audit.passedGates === spec.expected.r4.gates && e.r4Audit.attacksPassed === spec.expected.r4.attacks,
    D2_OPERATIONAL_RECOVERY_AND_FORMAL_FAILURE_PRESERVED: d2Operational(e),
    R5_V1_ROLLBACK_FAILURE_PRESERVED: e.r5v1Failure.error.startsWith('launchctl kickstart failed') && e.r5v1Failure.rollback.serviceBootedOut === true && e.r5v1Failure.rollback.plistRemoved === true && e.r5v1Failure.rollback.stateRetained === true,
    R5_ACTIVE_SENTINEL_ADMITTED: e.r5Audit.finalVerdict === spec.expected.r5.verdict && e.r5Audit.passedGates === spec.expected.r5.gates && e.r5Audit.totalGates === spec.expected.r5.gates && e.r5Audit.attacksPassed === spec.expected.r5.attacks && Object.values(e.r5Audit.gates).every(Boolean) && r5Actions.plistCreates === 1 && r5Actions.bootstrapCalls === 1 && r5Actions.kickstartCalls === 0 && ['deletions', 'cleanupOperations', 'serviceRestarts', 'dockerCalls', 'blenderProcesses', 'networkCalls', 'modelCalls'].every(key => r5Actions[key] === 0) && e.r5Install.reversible.stateRetainedOnUninstall === true,
    R6_INVALID_AUDIT_PRESERVED: e.r6InvalidResults.provisionalVerdict === 'ADMITTED_PENDING_AUDIT' && e.r6InvalidAudit.finalVerdict === spec.expected.r6Invalid.verdict && e.r6InvalidAudit.passedGates === spec.expected.r6Invalid.passedGates && e.r6InvalidAudit.totalGates === spec.expected.r6Invalid.gates && e.r6InvalidAudit.attacksPassed === spec.expected.r6Invalid.passedAttacks && e.r6InvalidAudit.attacksTotal === spec.expected.r6Invalid.attacks && same(e.r6InvalidAudit.failedGates, [spec.expected.r6Invalid.failedGate]) && same(e.r6InvalidAudit.attackResults.filter(value => !value.rejected).map(value => value.id), [spec.expected.r6Invalid.failedAttack]),
    R6_C1_UNATTENDED_RETENTION: e.r6c1Results.provisionalVerdict === 'ADMITTED_PENDING_AUDIT' && e.r6c1Results.failedGates.length === 0 && e.r6c1Results.gates.DISK_FLOOR_AND_LOSS_RATE === true && e.r6c1Audit.finalVerdict === spec.expected.r6c1.verdict && e.r6c1Audit.passedGates === spec.expected.r6c1.gates && e.r6c1Audit.attacksPassed === spec.expected.r6c1.attacks && e.r6c1Audit.attacksTotal === spec.expected.r6c1.attacks,
    LIVE_SENTINEL_HEALTH_AND_BOUNDS: validHash(history) && validHash(latest) && history.samples.every(validHash) && latestSample?.selfHash === history.samples.at(-1)?.selfHash && live.historyBytes <= spec.live.maximumStateBytes && live.latestBytes <= spec.live.maximumStateBytes && history.samples.length <= spec.live.maximumHistorySamples && live.latestAgeMs >= 0 && live.latestAgeMs <= spec.live.maximumLatestAgeSeconds * 1000 && latest.classification?.severity === 'HEALTHY' && latestSample.availableBytes >= spec.live.minimumAvailableBytes && latestSample.browserTempFilesystem.allocatedBytes < spec.live.maximumBrowserBytes && live.alertAbsent && live.installedPlistSha256 === spec.live.plistSha256 && live.templatePlistSha256 === spec.live.plistSha256 && launchd.loaded && launchd.runs >= history.samples.length && launchd.lastExitCode === 0 && launchd.intervalSeconds === spec.live.requiredIntervalSeconds,
    LIVE_CODEX_CONTINUITY_AND_NO_CRASH: runtime.codexVersion === spec.live.codexVersion && runtime.appPlistSha256 === spec.live.appPlistSha256 && runtime.bundleIdentifier === spec.live.bundleIdentifier && runtime.main.length === 1 && runtime.main[0].pid === spec.live.requiredMainPid && Date.parse(runtime.main[0].startedAt) <= Date.parse(spec.live.crashCutoff) && runtime.crashReports.length === 0,
    CLOSEOUT_RESOURCE_ACCOUNTING_ZERO: Object.entries(spec.resourceCeilings).every(([key, ceiling]) => resourceAccounting[key] === ceiling),
    CLOSEOUT_RECEIPT_INTEGRITY: model.results ? validHash(model.results) : 'PENDING_WRITE',
    INDEPENDENT_AUDIT_REPLAY: 'PENDING',
  };
  return gates;
}

function releaseState() {
  const scoped = execFileSync('/usr/bin/git', ['status', '--short', '--', ...spec.releasePaths], { cwd: repo, encoding: 'utf8' }).trim();
  const [head, origin] = execFileSync('/usr/bin/git', ['rev-parse', 'HEAD', 'origin/main'], { cwd: repo, encoding: 'utf8' }).trim().split('\n');
  const ancestor = run('/usr/bin/git', ['merge-base', '--is-ancestor', spec.parentCommit, head]).exitCode === 0;
  return { scoped, head, origin, ancestor, valid: scoped === '' && head === origin && ancestor };
}

function writeExclusive(path, value, ceiling) {
  let text;
  if (typeof value === 'string') text = value;
  else { seal(value); text = `${JSON.stringify(value, null, 2)}\n`; }
  if (Buffer.byteLength(text) > ceiling) throw new Error(`evidence ceiling: ${path}`);
  const fd = openSync(path, 'wx', 0o644);
  try { writeFileSync(fd, text); fsyncSync(fd); } finally { closeSync(fd); }
  const directoryFd = openSync(dirname(path), 'r');
  try { fsyncSync(directoryFd); } finally { closeSync(directoryFd); }
  return { sha256: sha(text), bytes: Buffer.byteLength(text), selfHash: typeof value === 'string' ? null : value.selfHash };
}

const loaded = loadEvidence();
if (process.argv.includes('--self-test')) {
  if (!d2Operational(loaded.evidence) || Object.keys(loaded.receipts).length !== 19 || !Object.values(loaded.receipts).every(value => value.actualSha256 === value.expectedSha256 && value.selfHashValid) || spec.registeredAttacks.length !== 20 || spec.requiredGates.length !== 15) throw new Error('Gate 0 closeout self-test failed');
  process.stdout.write('{"selfTest":"PASS","evidence":19,"gates":15,"attacks":20,"d2Boundary":"OPERATIONAL_RECOVERY_FORMAL_FAILURE"}\n');
  process.exit(0);
}

const observedAtMs = Date.now();
const release = releaseState();
const live = liveSentinelState(observedAtMs);
const launchd = launchdState();
const runtime = runtimeState();
const resourceAccounting = { blenderProcesses: 0, dockerCalls: 0, networkCalls: 0, modelCalls: 0, cleanupOperations: 0, serviceMutations: 0 };
const model = { ...loaded, live, launchd, runtime, resourceAccounting, releaseValid: release.valid, results: null };
const gates = semanticGates(model);
const preAuditNames = spec.requiredGates.filter(name => name !== 'INDEPENDENT_AUDIT_REPLAY');
const failedGates = preAuditNames.filter(name => gates[name] !== true && name !== 'CLOSEOUT_RECEIPT_INTEGRITY');

if (process.argv.includes('--preflight')) {
  process.stdout.write(`${JSON.stringify({ status: failedGates.length ? 'BLOCKED_GATE0_CLOSEOUT' : 'READY_GATE0_CLOSEOUT', failedGates, releaseValid: release.valid, evidenceHashesExact: Object.values(loaded.receipts).every(value => value.actualSha256 === value.expectedSha256), latestAgeMs: live.latestAgeMs, sampleCount: live.history.samples.length, formalRootAbsent: !existsSync(root) })}\n`);
  process.exit(failedGates.length || existsSync(root) ? 75 : 0);
}

if (existsSync(root)) throw new Error('formal root is not fresh');
if (failedGates.length) throw new Error(`Gate 0 closeout preflight failed: ${failedGates.join(',')}`);
mkdirSync(root, { recursive: false });
const start = { schemaVersion: 'bfs.gate0-closeout-start.v0.1', experimentId: spec.experimentId, startedAt: new Date().toISOString(), specSha256: shaFile(specPath), git: release, evidenceReceipts: loaded.receipts, selfHash: '' };
const startReceipt = writeExclusive(resolve(root, 'start.json'), start, spec.byteCeilings.results);
const liveSummary = {
  observedAt: new Date(observedAtMs).toISOString(), historySha256: live.historySha256, latestSha256: live.latestSha256, historyBytes: live.historyBytes, latestBytes: live.latestBytes,
  sampleCount: live.history.samples.length, latestAgeMs: live.latestAgeMs, severity: live.latest.classification.severity, availableBytes: live.latest.sample.availableBytes,
  browserBytes: live.latest.sample.browserTempFilesystem.allocatedBytes, alertAbsent: live.alertAbsent, installedPlistSha256: live.installedPlistSha256, templatePlistSha256: live.templatePlistSha256,
};
const observations = {
  r2: { verdict: loaded.evidence.r2Audit.finalVerdict, gates: `${loaded.evidence.r2Audit.passedGates}/${loaded.evidence.r2Audit.totalGates}`, attacks: `${loaded.evidence.r2Audit.attacksPassed}/${loaded.evidence.r2Audit.attacksTotal}` },
  r3: { verdict: loaded.evidence.r3Audit.finalVerdict, failedGates: loaded.evidence.r3Audit.failedGates },
  r4: { verdict: loaded.evidence.r4Audit.finalVerdict, diskLossBytes: loaded.evidence.r4Results.aggregate.diskLossBytes, spanMs: loaded.evidence.r4Results.aggregate.totalSpanMs },
  d2: { formalVerdict: 'FAILURE_PRESERVED', operationalRecovery: true, generatedLimaHashChanged: true, containerIds: spec.expected.d2.containerIds },
  r5: { verdict: loaded.evidence.r5Audit.finalVerdict, reversible: loaded.evidence.r5Install.reversible.stateRetainedOnUninstall },
  r6Invalid: { verdict: loaded.evidence.r6InvalidAudit.finalVerdict, failedAttack: spec.expected.r6Invalid.failedAttack },
  r6c1: { verdict: loaded.evidence.r6c1Audit.finalVerdict, diskLossRateBytesPerHour: loaded.evidence.r6c1Results.aggregate.diskLossRateBytesPerHour, spanMs: loaded.evidence.r6c1Results.aggregate.spanMs },
};
const results = { schemaVersion: 'bfs.gate0-closeout-results.v0.1', experimentId: spec.experimentId, completedAt: new Date().toISOString(), spec: { path: 'specs/gate0-closeout.v0.1.json', sha256: shaFile(specPath) }, startReceipt, evidenceReceipts: loaded.receipts, observations, live: liveSummary, launchd, runtime, resourceAccounting, gates, failedGates: [], provisionalVerdict: '', receiptBytes: 0, selfHash: '' };
results.gates.CLOSEOUT_RECEIPT_INTEGRITY = true;
results.failedGates = preAuditNames.filter(name => results.gates[name] !== true);
results.provisionalVerdict = results.failedGates.length ? 'BLOCKED_GATE0_CLOSEOUT' : 'GATE0_CLOSEOUT_PENDING_AUDIT';
let text;
for (let index = 0; index < 6; index += 1) { seal(results); text = `${JSON.stringify(results, null, 2)}\n`; results.receiptBytes = Buffer.byteLength(text); }
const resultReceipt = writeExclusive(resolve(root, 'results.json'), results, spec.byteCeilings.results);
process.stdout.write(`${JSON.stringify({ experimentId: spec.experimentId, provisionalVerdict: results.provisionalVerdict, gates: `${preAuditNames.filter(name => results.gates[name] === true).length}/${preAuditNames.length}`, failedGates: results.failedGates, resultsSha256: resultReceipt.sha256 })}\n`);
