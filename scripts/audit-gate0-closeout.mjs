#!/usr/bin/env node

import { createHash } from 'node:crypto';
import { closeSync, existsSync, fsyncSync, openSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { execFileSync, spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const repo = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const specPath = resolve(repo, 'specs/gate0-closeout.v0.1.json');
const spec = JSON.parse(readFileSync(specPath, 'utf8'));
const root = resolve(repo, spec.formalRoot);
const auditPath = resolve(root, 'audit.json');
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

function evidenceState() {
  const evidence = {};
  const receipts = {};
  for (const [id, [relativePath, expectedSha256]] of Object.entries(spec.evidence)) {
    const text = readFileSync(resolve(repo, relativePath), 'utf8');
    evidence[id] = JSON.parse(text);
    receipts[id] = { path: relativePath, expectedSha256, actualSha256: sha(text), bytes: Buffer.byteLength(text), selfHashValid: validHash(evidence[id]) };
  }
  return { evidence, receipts };
}

function launchdState() {
  const value = run('/bin/launchctl', ['print', spec.live.launchdTarget]);
  return { loaded: value.exitCode === 0, runs: Number((value.stdout.match(/\bruns = (\d+)/) || [])[1] || -1), lastExitCode: Number((value.stdout.match(/\blast exit code = (-?\d+)/) || [])[1] || -1), intervalSeconds: Number((value.stdout.match(/\brun interval = (\d+) seconds/) || [])[1] || -1), printSha256: sha(value.stdout), printBytes: Buffer.byteLength(value.stdout) };
}

function runtimeState() {
  const mainPath = '/Applications/ChatGPT.app/Contents/MacOS/ChatGPT';
  const rows = run('/bin/ps', ['-axo', 'pid=,lstart=,command=']).stdout.split('\n').filter(Boolean);
  const main = rows.map(line => { const match = line.match(/^\s*(\d+)\s+(.{24})\s+(.*)$/); return match ? { pid: Number(match[1]), startedAt: new Date(match[2]).toISOString(), command: match[3] } : null; }).filter(value => value?.command === mainPath);
  const cutoff = Date.parse(spec.live.crashCutoff);
  const crashReports = existsSync(spec.live.diagnosticReportsPath)
    ? readdirSync(spec.live.diagnosticReportsPath).filter(name => /^ChatGPT.*[.]ips$/.test(name)).map(name => ({ name, modifiedMs: statSync(join(spec.live.diagnosticReportsPath, name)).mtimeMs })).filter(value => value.modifiedMs > cutoff).sort((a, b) => a.name.localeCompare(b.name)) : [];
  return { codexVersion: `${readPlistString(spec.live.appPlistPath, 'CFBundleShortVersionString')} (${readPlistString(spec.live.appPlistPath, 'CFBundleVersion')})`, appPlistSha256: shaFile(spec.live.appPlistPath), bundleIdentifier: readPlistString(spec.live.appPlistPath, 'CFBundleIdentifier'), main, crashReports };
}

function liveState(observedAtMs = Date.now()) {
  const historyText = readFileSync(spec.live.historyPath, 'utf8');
  const latestText = readFileSync(spec.live.latestPath, 'utf8');
  const history = JSON.parse(historyText);
  const latest = JSON.parse(latestText);
  return { history, latest, historyBytes: Buffer.byteLength(historyText), latestBytes: Buffer.byteLength(latestText), historySha256: sha(historyText), latestSha256: sha(latestText), latestAgeMs: observedAtMs - Date.parse(latest.sample?.capturedAt), alertAbsent: !existsSync(spec.live.alertPath), installedPlistSha256: shaFile(spec.live.installedPlistPath), templatePlistSha256: shaFile(resolve(repo, spec.live.templatePlistPath)) };
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
  return e.d2Stop.transition === 'STOP_DEFAULT' && e.d2Stop.confirmed === true && e.d2Stop.command.exitCode === 0 && e.d2Stop.state.profile.running === false && e.d2Stop.state.docker.socketReachable === false && e.d2Stop.state.docker.runningIds.length === 0
    && e.d2StartTransition.transition === 'START_DEFAULT_AND_RESTORE' && e.d2StartTransition.confirmed === true && e.d2StartTransition.command.exitCode === 0 && e.d2StartTransition.explicitContainerStarts.length === 0 && started.profile.running === true && started.docker.socketReachable === true
    && same(started.docker.runningIds, expected.containerIds) && same(final.docker.runningIds, expected.containerIds) && matchingContainers(initial, started) && matchingContainers(initial, final)
    && ['arch', 'runtime', 'mountType'].every(field => initial.profile[field] === started.profile[field] && initial.profile[field] === final.profile[field])
    && initial.configs.colimaConfig.sha256 === expected.authoritativeConfigSha256 && started.configs.colimaConfig.sha256 === expected.authoritativeConfigSha256 && final.configs.colimaConfig.sha256 === expected.authoritativeConfigSha256
    && initial.configs.limaConfig.sha256 === expected.generatedLimaInitialSha256 && started.configs.limaConfig.sha256 === expected.generatedLimaFinalSha256 && final.configs.limaConfig.sha256 === expected.generatedLimaFinalSha256 && expected.generatedLimaInitialSha256 !== expected.generatedLimaFinalSha256
    && diskIdentity(initial, started, 'vmDisk') && diskIdentity(initial, started, 'dataDisk') && diskIdentity(initial, final, 'vmDisk') && diskIdentity(initial, final, 'dataDisk')
    && e.d2Failure.error === expected.formalFailure && e.d2Failure.finalRestored === false && e.d2Recovery.reason === 'final-restoration-invariant' && e.d2Recovery.restored === false && e.d2Recovery.actions.length === 0
    && resource.stopCommands === 1 && resource.startCommands === 1 && resource.explicitContainerStarts === 0 && ['filesystemWritesOutsideFormalRoot', 'cleanupOperations', 'profileConfigurationMutations', 'containerCreates', 'containerRemoves', 'imageOrVolumeMutations', 'signalsSent', 'networkCalls', 'modelCalls'].every(key => resource[key] === 0)
    && !existsSync(resolve(repo, 'experiments/codex-host-disk-colima-ab-v0-1/results.json')) && !existsSync(resolve(repo, 'experiments/codex-host-disk-colima-ab-v0-1/audit.json'));
}

function gatesFor(model) {
  const { evidence: e, receipts, live, launchd, runtime, resourceAccounting } = model;
  const latest = live.latest;
  const history = live.history;
  const latestSample = latest.sample;
  const r5Actions = e.r5Install.actions;
  return {
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
    CLOSEOUT_RECEIPT_INTEGRITY: validHash(model.results),
    INDEPENDENT_AUDIT_REPLAY: 'PENDING',
  };
}

function releaseValid() {
  const scoped = execFileSync('/usr/bin/git', ['status', '--short', '--', ...spec.releasePaths], { cwd: repo, encoding: 'utf8' }).trim();
  const [head, origin] = execFileSync('/usr/bin/git', ['rev-parse', 'HEAD', 'origin/main'], { cwd: repo, encoding: 'utf8' }).trim().split('\n');
  return { valid: scoped === '' && head === origin && run('/usr/bin/git', ['merge-base', '--is-ancestor', spec.parentCommit, head]).exitCode === 0, scoped, head, origin };
}

const attackDefinitions = [
  ['A01_EVIDENCE_SHA_MUTATION', 'SPEC_RELEASE_AND_EVIDENCE_HASHES', model => { model.receipts.r2Audit.actualSha256 = '0'.repeat(64); }],
  ['A02_EVIDENCE_SELF_HASH_MUTATION', 'EVIDENCE_SELF_HASHES', model => { model.receipts.r2Audit.selfHashValid = false; }],
  ['A03_R2_VERDICT_MUTATION', 'R2_RESTART_READMISSION', model => { model.evidence.r2Audit.finalVerdict = 'BLOCKED'; }],
  ['A04_R2_ATTACK_COUNT_MUTATION', 'R2_RESTART_READMISSION', model => { model.evidence.r2Audit.attacksPassed -= 1; }],
  ['A05_R3_FAILURE_ERASURE', 'R3_FAILURE_PRESERVED', model => { model.evidence.r3Audit.finalVerdict = 'ADMITTED_FOR_GATE0_CLOSEOUT'; }],
  ['A06_R4_VERDICT_MUTATION', 'R4_POST_RECLAIM_STABILITY', model => { model.evidence.r4Audit.finalVerdict = 'BLOCKED_HOST_STABILITY'; }],
  ['A07_R4_DISK_GATE_MUTATION', 'R4_POST_RECLAIM_STABILITY', model => { model.evidence.r4Results.gates.DISK_RETENTION_BOUNDED = false; }],
  ['A08_D2_FORMAL_FAILURE_RELABEL', 'D2_OPERATIONAL_RECOVERY_AND_FORMAL_FAILURE_PRESERVED', model => { model.evidence.d2Failure.finalRestored = true; }],
  ['A09_D2_CONTAINER_ID_MUTATION', 'D2_OPERATIONAL_RECOVERY_AND_FORMAL_FAILURE_PRESERVED', model => { model.evidence.d2StartTransition.state.docker.runningIds[0] = '0'.repeat(64); }],
  ['A10_D2_AUTHORITATIVE_CONFIG_MUTATION', 'D2_OPERATIONAL_RECOVERY_AND_FORMAL_FAILURE_PRESERVED', model => { model.evidence.d2Failure.finalState.configs.colimaConfig.sha256 = '0'.repeat(64); }],
  ['A11_D2_GENERATED_LIMA_MISMATCH_ERASURE', 'D2_OPERATIONAL_RECOVERY_AND_FORMAL_FAILURE_PRESERVED', model => { model.evidence.d2Failure.finalState.configs.limaConfig.sha256 = spec.expected.d2.generatedLimaInitialSha256; }],
  ['A12_R5_V1_ROLLBACK_MUTATION', 'R5_V1_ROLLBACK_FAILURE_PRESERVED', model => { model.evidence.r5v1Failure.rollback.plistRemoved = false; }],
  ['A13_R5_VERDICT_MUTATION', 'R5_ACTIVE_SENTINEL_ADMITTED', model => { model.evidence.r5Audit.finalVerdict = 'INVALID'; }],
  ['A14_R5_AUTOMATIC_ACTION_MUTATION', 'R5_ACTIVE_SENTINEL_ADMITTED', model => { model.evidence.r5Install.actions.cleanupOperations = 1; }],
  ['A15_R6_INVALID_RELABEL', 'R6_INVALID_AUDIT_PRESERVED', model => { model.evidence.r6InvalidAudit.finalVerdict = 'ONE_HOUR_UNATTENDED_RETENTION_ADMITTED'; }],
  ['A16_R6_C1_VERDICT_MUTATION', 'R6_C1_UNATTENDED_RETENTION', model => { model.evidence.r6c1Audit.finalVerdict = 'INVALID'; }],
  ['A17_R6_C1_RATE_GATE_MUTATION', 'R6_C1_UNATTENDED_RETENTION', model => { model.evidence.r6c1Results.gates.DISK_FLOOR_AND_LOSS_RATE = false; }],
  ['A18_LIVE_SENTINEL_STALE_MUTATION', 'LIVE_SENTINEL_HEALTH_AND_BOUNDS', model => { model.live.latestAgeMs = spec.live.maximumLatestAgeSeconds * 1000 + 1; }],
  ['A19_LIVE_CODEX_PID_MUTATION', 'LIVE_CODEX_CONTINUITY_AND_NO_CRASH', model => { model.runtime.main[0].pid = 1; }],
  ['A20_CLOSEOUT_SELF_HASH_MUTATION', 'CLOSEOUT_RECEIPT_INTEGRITY', model => { model.results.selfHash = '0'.repeat(64); }],
];

const loaded = evidenceState();
if (process.argv.includes('--self-test')) {
  if (Object.keys(loaded.receipts).length !== 19 || !d2Operational(loaded.evidence) || attackDefinitions.length !== 20 || !same(attackDefinitions.map(value => value[0]), spec.registeredAttacks)) throw new Error('Gate 0 auditor self-test failed');
  process.stdout.write('{"selfTest":"PASS","independentEvidence":19,"targetedAttacks":20,"attackIdsExact":true}\n');
  process.exit(0);
}

if (!existsSync(resolve(root, 'start.json')) || !existsSync(resolve(root, 'results.json')) || existsSync(auditPath)) throw new Error('formal evidence state invalid');
const startText = readFileSync(resolve(root, 'start.json'), 'utf8');
const resultsText = readFileSync(resolve(root, 'results.json'), 'utf8');
const start = JSON.parse(startText);
const results = JSON.parse(resultsText);
const release = releaseValid();
const currentLive = liveState();
const currentLaunchd = launchdState();
const currentRuntime = runtimeState();
const model = { ...loaded, live: currentLive, launchd: currentLaunchd, runtime: currentRuntime, resourceAccounting: results.resourceAccounting, releaseValid: release.valid, results };
const expectedGates = gatesFor(model);
const preAuditNames = spec.requiredGates.filter(name => name !== 'INDEPENDENT_AUDIT_REPLAY');
const fileIntegrity = {
  START: validHash(start) && results.startReceipt.sha256 === sha(startText) && results.startReceipt.bytes === Buffer.byteLength(startText),
  RESULTS: validHash(results) && results.receiptBytes === Buffer.byteLength(resultsText) && Buffer.byteLength(resultsText) <= spec.byteCeilings.results,
  SPEC: results.spec.path === 'specs/gate0-closeout.v0.1.json' && results.spec.sha256 === shaFile(specPath) && start.specSha256 === results.spec.sha256,
  EVIDENCE_RECEIPTS: same(start.evidenceReceipts, loaded.receipts) && same(results.evidenceReceipts, loaded.receipts),
  RELEASE: release.valid && start.git.head === release.head && start.git.origin === release.origin,
  GATE_PROJECTION: preAuditNames.every(name => expectedGates[name] === true && results.gates[name] === true),
  LIVE_SENTINEL: expectedGates.LIVE_SENTINEL_HEALTH_AND_BOUNDS === true,
  LIVE_RUNTIME: expectedGates.LIVE_CODEX_CONTINUITY_AND_NO_CRASH === true,
};
const baseGates = gatesFor(model);
const attackResults = attackDefinitions.map(([id, targetGate, mutate]) => {
  const candidate = structuredClone(model);
  mutate(candidate);
  const after = gatesFor(candidate);
  return { id, targetGate, targetWasTrue: baseGates[targetGate] === true, targetBecameFalse: after[targetGate] === false, rejected: baseGates[targetGate] === true && after[targetGate] === false };
});
const attackIdsExact = same(attackDefinitions.map(value => value[0]), spec.registeredAttacks);
const attacksPassed = attackIdsExact && attackResults.every(value => value.rejected);
const integrityPassed = Object.values(fileIntegrity).every(Boolean);
const finalGates = { ...results.gates, INDEPENDENT_AUDIT_REPLAY: integrityPassed && attacksPassed };
const failedGates = spec.requiredGates.filter(name => finalGates[name] !== true);
const finalVerdict = failedGates.length ? 'INVALID_GATE0_CLOSEOUT' : 'GATE0_HOST_STABILITY_CLOSED';
const audit = { schemaVersion: 'bfs.gate0-closeout-audit.v0.1', experimentId: spec.experimentId, auditedAt: new Date().toISOString(), finalVerdict, fileIntegrity, attackIdsExact, attackResults, attacksPassed: attackResults.filter(value => value.rejected).length, attacksTotal: attackResults.length, finalGates, passedGates: spec.requiredGates.filter(name => finalGates[name] === true).length, totalGates: spec.requiredGates.length, failedGates, currentLive: { sampleCount: currentLive.history.samples.length, latestAgeMs: currentLive.latestAgeMs, severity: currentLive.latest.classification.severity, availableBytes: currentLive.latest.sample.availableBytes, browserBytes: currentLive.latest.sample.browserTempFilesystem.allocatedBytes, alertAbsent: currentLive.alertAbsent }, currentLaunchd, currentRuntime, resourceAccounting: { blenderProcesses: 0, dockerCalls: 0, networkCalls: 0, modelCalls: 0, cleanupOperations: 0, serviceMutations: 0 }, selfHash: '' };
seal(audit);
const auditText = `${JSON.stringify(audit, null, 2)}\n`;
if (Buffer.byteLength(auditText) > spec.byteCeilings.audit) throw new Error('audit ceiling');
const fd = openSync(auditPath, 'wx', 0o644);
try { writeFileSync(fd, auditText); fsyncSync(fd); } finally { closeSync(fd); }
process.stdout.write(`${JSON.stringify({ experimentId: spec.experimentId, finalVerdict, gates: `${audit.passedGates}/${audit.totalGates}`, attacks: `${audit.attacksPassed}/${audit.attacksTotal}`, failedGates })}\n`);
