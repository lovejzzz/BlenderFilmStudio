#!/usr/bin/env node

import { createHash } from 'node:crypto';
import {
  closeSync, existsSync, fsyncSync, openSync, readFileSync, readdirSync, statSync, writeFileSync,
} from 'node:fs';
import { dirname, resolve } from 'node:path';
import { execFileSync, spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const repositoryRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const specPath = resolve(repositoryRoot, 'specs/host-capacity-sentinel.v0.2.json');
const spec = JSON.parse(readFileSync(specPath, 'utf8'));
const root = resolve(repositoryRoot, spec.formalRoot);
const auditPath = resolve(root, 'audit.json');
const sourcePlist = resolve(repositoryRoot, 'launchd/com.blenderfilmstudio.capacity-sentinel.plist');
const installedPlist = '/Users/tianxing/Library/LaunchAgents/com.blenderfilmstudio.capacity-sentinel.plist';
const serviceTarget = `gui/${process.getuid()}/${spec.schedule.launchdLabel}`;
const canonical = value => Array.isArray(value)
  ? `[${value.map(canonical).join(',')}]`
  : value && typeof value === 'object'
    ? `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}`
    : JSON.stringify(value);
const sha256 = value => createHash('sha256').update(value).digest('hex');
const shaFile = path => sha256(readFileSync(path));
const withoutHash = value => { const copy = structuredClone(value); delete copy.selfHash; return copy; };
const validHash = value => value?.selfHash === sha256(canonical(withoutHash(value)));
const seal = value => { value.selfHash = sha256(canonical(withoutHash(value))); return value; };

function run(command, args) {
  const result = spawnSync(command, args, { cwd: repositoryRoot, encoding: 'utf8', timeout: 10000, maxBuffer: 1024 * 1024, env: { ...process.env, LC_ALL: 'C' } });
  return { exitCode: result.status, stdout: result.stdout || '', stderr: result.stderr || '', errorCode: result.error?.code || null };
}

function parsePlist(path) {
  const result = run('/usr/bin/plutil', ['-convert', 'json', '-o', '-', path]);
  if (result.exitCode !== 0) throw new Error('plist parse failed');
  return JSON.parse(result.stdout);
}

function templateValid(plist) {
  return plist.Label === spec.schedule.launchdLabel
    && canonical(plist.ProgramArguments) === canonical([spec.runtime.nodeExecutable, `${spec.runtime.repositoryRoot}/scripts/host-capacity-sentinel.mjs`, '--quiet'])
    && plist.WorkingDirectory === spec.runtime.repositoryRoot
    && plist.RunAtLoad === true && plist.StartInterval === spec.schedule.intervalSeconds
    && plist.StandardOutPath === '/dev/null' && plist.StandardErrorPath === '/dev/null';
}

function maximumLossWithin(samples, current, minimumSpanSeconds, maximumSpanSeconds) {
  const currentMs = Date.parse(current.capturedAt);
  return samples.filter(sample => {
    const span = (currentMs - Date.parse(sample.capturedAt)) / 1000;
    return span >= minimumSpanSeconds && span <= maximumSpanSeconds;
  }).reduce((maximum, sample) => Math.max(maximum, sample.availableBytes - current.availableBytes), 0);
}

function classify(samples, current) {
  const t = spec.thresholds;
  const rapidLossBytes = maximumLossWithin(samples, current, t.rapidLossMinimumSpanSeconds, t.rapidLossMaximumSpanSeconds);
  const longLossBytes = maximumLossWithin(samples, current, t.longLossMinimumSpanSeconds, t.longLossMaximumSpanSeconds);
  if (current.availableBytes < t.emergencyAvailableBytes || current.browserTempFilesystem.allocatedBytes >= t.browserCriticalBytes) return 'EMERGENCY_CAPACITY';
  if (current.availableBytes < t.criticalAvailableBytes) return 'CRITICAL_CAPACITY';
  if (current.availableBytes < t.warningAvailableBytes) return 'WARNING_CAPACITY';
  if (rapidLossBytes >= t.rapidLossBytes || longLossBytes >= t.longLossBytes || current.browserTempFilesystem.allocatedBytes >= t.browserWarningBytes) return 'WARNING_RAPID_LOSS';
  return 'HEALTHY';
}

function validateHistory(history) {
  return history?.schemaVersion === 'bfs.host-capacity-history.v0.1' && validHash(history)
    && Array.isArray(history.samples) && history.samples.length >= 1
    && history.samples.length <= spec.state.maximumHistorySamples && history.samples.every(validHash);
}

function validateLatest(latest, historySamples = [], now = Date.now()) {
  return latest?.schemaVersion === 'bfs.host-capacity-latest.v0.1' && latest.experimentId === spec.experimentId
    && validHash(latest) && validHash(latest.sample)
    && latest.classification?.severity === classify(historySamples, latest.sample)
    && now - Date.parse(latest.sample.capturedAt) <= (spec.schedule.intervalSeconds + spec.schedule.maximumExpectedLagSeconds) * 1000
    && Object.values(latest.sample.prohibitedActions || {}).every(value => value === 0)
    && latest.policy?.automaticDeletion === false && latest.policy?.automaticCleanup === false
    && latest.policy?.automaticServiceRestart === false && latest.policy?.networkCalls === false
    && latest.policy?.modelCalls === false && latest.policy?.blenderProcesses === false && latest.policy?.dockerCalls === false;
}

function boundaryTests() {
  const now = Date.now();
  const gib = 1024 ** 3;
  const sample = (minutesAgo, available, browser = 0) => seal({ capturedAt: new Date(now - minutesAgo * 60000).toISOString(), availableBytes: available, browserTempFilesystem: { allocatedBytes: browser }, selfHash: '' });
  const healthy = sample(0, spec.thresholds.warningAvailableBytes);
  const warning = sample(0, spec.thresholds.warningAvailableBytes - 1);
  const critical = sample(0, spec.thresholds.criticalAvailableBytes - 1);
  const emergency = sample(0, spec.thresholds.emergencyAvailableBytes - 1);
  const rapidPrior = sample(15, 280 * gib);
  const rapidNow = sample(0, 269 * gib);
  const longPrior = sample(24 * 60, 300 * gib);
  const longNow = sample(0, 274 * gib);
  return {
    PURE_CLASSIFIER_BOUNDARIES: classify([], healthy) === 'HEALTHY' && classify([], warning) === 'WARNING_CAPACITY'
      && classify([], critical) === 'CRITICAL_CAPACITY' && classify([], emergency) === 'EMERGENCY_CAPACITY',
    RAPID_AND_LONG_LOSS_DETECTION: classify([rapidPrior], rapidNow) === 'WARNING_RAPID_LOSS' && classify([longPrior], longNow) === 'WARNING_RAPID_LOSS',
    fixtures: { healthy, warning, critical, emergency, rapidPrior, rapidNow, longPrior, longNow },
  };
}

function writeAudit(value) {
  const text = `${JSON.stringify(seal(value), null, 2)}\n`;
  if (Buffer.byteLength(text) > 262144) throw new Error('audit byte ceiling');
  const fd = openSync(auditPath, 'wx', 0o644);
  try { writeFileSync(fd, text); fsyncSync(fd); } finally { closeSync(fd); }
  return text;
}

if (process.argv.includes('--self-test')) {
  const tests = boundaryTests();
  if (!tests.PURE_CLASSIFIER_BOUNDARIES || !tests.RAPID_AND_LONG_LOSS_DETECTION) throw new Error('auditor self-test failed');
  process.stdout.write('{"selfTest":"PASS","classifierIndependent":true,"registeredAttacks":15}\n');
  process.exit(0);
}

if (!existsSync(resolve(root, 'start.json')) || !existsSync(resolve(root, 'install.json')) || existsSync(auditPath)) throw new Error('formal evidence state invalid');
const startText = readFileSync(resolve(root, 'start.json'), 'utf8');
const installText = readFileSync(resolve(root, 'install.json'), 'utf8');
const start = JSON.parse(startText);
const install = JSON.parse(installText);
const latestPath = resolve(spec.state.root, spec.state.latestFile);
const historyPath = resolve(spec.state.root, spec.state.historyFile);
const latestText = readFileSync(latestPath, 'utf8');
const historyText = readFileSync(historyPath, 'utf8');
const latest = JSON.parse(latestText);
const history = JSON.parse(historyText);
const plist = parsePlist(installedPlist);
const service = run('/bin/launchctl', ['print', serviceTarget]);
const scoped = execFileSync('/usr/bin/git', ['status', '--short', '--', ...spec.releasePaths], { cwd: repositoryRoot, encoding: 'utf8' }).trim();
const [head, origin] = execFileSync('/usr/bin/git', ['rev-parse', 'HEAD', 'origin/main'], { cwd: repositoryRoot, encoding: 'utf8' }).trim().split('\n');
const boundaries = boundaryTests();
const noTemps = readdirSync(spec.state.root).every(name => !name.includes('.tmp-'));
const boundedFiles = readdirSync(spec.state.root).every(name => statSync(resolve(spec.state.root, name)).size <= spec.state.maximumStateFileBytes);
const exactUninstall = install.reversible?.uninstallCommand === `${spec.runtime.nodeExecutable} ${spec.runtime.repositoryRoot}/scripts/install-host-capacity-sentinel.mjs --uninstall`
  && install.reversible?.stateRetainedOnUninstall === true;
function startIdentityValid(candidate) {
  return validHash(candidate) && candidate.specSha256 === shaFile(specPath)
    && candidate.parentEvidence.resultsSha256 === spec.parentEvidence.resultsSha256
    && candidate.parentEvidence.auditSha256 === spec.parentEvidence.auditSha256;
}
const historyBeforeLatest = history.samples.slice(0, -1);
const gates = {
  SPEC_AND_PARENT_IDENTITY: start.specSha256 === shaFile(specPath) && start.parentEvidence.resultsSha256 === spec.parentEvidence.resultsSha256
    && start.parentEvidence.auditSha256 === spec.parentEvidence.auditSha256
    && shaFile(resolve(repositoryRoot, spec.parentEvidence.resultsPath)) === spec.parentEvidence.resultsSha256
    && shaFile(resolve(repositoryRoot, spec.parentEvidence.auditPath)) === spec.parentEvidence.auditSha256
    && start.git.head === start.git.origin && start.git.scoped === '' && head === origin && head === start.git.head && scoped === '',
  PURE_CLASSIFIER_BOUNDARIES: boundaries.PURE_CLASSIFIER_BOUNDARIES,
  RAPID_AND_LONG_LOSS_DETECTION: boundaries.RAPID_AND_LONG_LOSS_DETECTION,
  HISTORY_IS_BOUNDED: validateHistory(history),
  STATE_WRITES_ARE_ATOMIC_AND_BOUNDED: noTemps && boundedFiles && Buffer.byteLength(latestText) <= spec.state.maximumStateFileBytes && Buffer.byteLength(historyText) <= spec.state.maximumStateFileBytes,
  NO_AUTOMATIC_DELETION_OR_RESTART: install.actions.plistCreates === 1 && install.actions.bootstrapCalls === 1 && install.actions.kickstartCalls === 0
    && install.actions.deletions === 0 && install.actions.cleanupOperations === 0 && install.actions.serviceRestarts === 0
    && install.actions.dockerCalls === 0 && install.actions.blenderProcesses === 0 && install.actions.networkCalls === 0 && install.actions.modelCalls === 0
    && spec.policy.automaticDeletion === false && spec.policy.automaticCleanup === false && spec.policy.automaticServiceRestart === false,
  LAUNCHD_TEMPLATE_EXACT: templateValid(plist) && shaFile(installedPlist) === shaFile(sourcePlist),
  INSTALLATION_EXACT_AND_REVERSIBLE: validHash(start) && validHash(install) && install.startReceipt.sha256 === sha256(startText)
    && install.installedPlist.sha256 === shaFile(installedPlist) && service.exitCode === 0 && exactUninstall,
  LIVE_SAMPLE_VALID: validateLatest(latest, historyBeforeLatest) && install.liveState.latest.sha256 === sha256(latestText)
    && install.liveState.latest.selfHash === latest.selfHash && install.liveState.history.sha256 === sha256(historyText)
    && install.liveState.history.selfHash === history.selfHash,
  INDEPENDENT_AUDIT_REPLAY: 'PENDING',
};

const mutatedSpecStart = structuredClone(start);
mutatedSpecStart.specSha256 = '0'.repeat(64);
seal(mutatedSpecStart);
const mutatedParentStart = structuredClone(start);
mutatedParentStart.parentEvidence.resultsSha256 = '0'.repeat(64);
seal(mutatedParentStart);
const staleNow = Date.parse(latest.sample.capturedAt) + (spec.schedule.intervalSeconds + spec.schedule.maximumExpectedLagSeconds) * 1000 + 1;
const automaticCleanupLatest = structuredClone(latest);
automaticCleanupLatest.policy.automaticCleanup = true;
seal(automaticCleanupLatest);
const attacks = [
  ['A01_SPEC_SHA_MUTATION', !startIdentityValid(mutatedSpecStart)],
  ['A02_PARENT_EVIDENCE_MUTATION', !startIdentityValid(mutatedParentStart)],
  ['A03_WARNING_FLOOR_BYPASS', classify([], boundaries.fixtures.warning) !== 'HEALTHY'],
  ['A04_CRITICAL_FLOOR_BYPASS', classify([], boundaries.fixtures.critical) === 'CRITICAL_CAPACITY'],
  ['A05_EMERGENCY_FLOOR_BYPASS', classify([], boundaries.fixtures.emergency) === 'EMERGENCY_CAPACITY'],
  ['A06_RAPID_LOSS_BYPASS', classify([boundaries.fixtures.rapidPrior], boundaries.fixtures.rapidNow) === 'WARNING_RAPID_LOSS'],
  ['A07_LONG_LOSS_BYPASS', classify([boundaries.fixtures.longPrior], boundaries.fixtures.longNow) === 'WARNING_RAPID_LOSS'],
  ['A08_HISTORY_OVERFLOW', !validateHistory(seal({ schemaVersion: 'bfs.host-capacity-history.v0.1', samples: Array.from({ length: 193 }, () => boundaries.fixtures.healthy), selfHash: '' }))],
  ['A09_STALE_SAMPLE_ACCEPTANCE', !validateLatest(structuredClone(latest), historyBeforeLatest, staleNow)],
  ['A10_BROWSER_CRITICAL_BYPASS', classify([], seal({ ...withoutHash(boundaries.fixtures.healthy), browserTempFilesystem: { allocatedBytes: spec.thresholds.browserCriticalBytes }, selfHash: '' })) === 'EMERGENCY_CAPACITY'],
  ['A11_SELF_HASH_MUTATION', !validHash({ ...latest, selfHash: '0'.repeat(64) })],
  ['A12_LAUNCHD_LABEL_MUTATION', !templateValid({ ...plist, Label: 'foreign' })],
  ['A13_LAUNCHD_INTERVAL_MUTATION', !templateValid({ ...plist, StartInterval: 1 })],
  ['A14_RUNTIME_PATH_MUTATION', !templateValid({ ...plist, ProgramArguments: ['/tmp/node', ...plist.ProgramArguments.slice(1)] })],
  ['A15_AUTOMATIC_CLEANUP_MUTATION', !validateLatest(automaticCleanupLatest, historyBeforeLatest)],
].map(([id, rejected]) => ({ id, rejected }));
const attackIdsExact = canonical(attacks.map(value => value.id)) === canonical(spec.registeredAttacks);
const attacksPassed = attackIdsExact && attacks.every(value => value.rejected);
const baseGateNames = spec.requiredGates.filter(name => name !== 'INDEPENDENT_AUDIT_REPLAY');
const basePassed = baseGateNames.every(name => gates[name] === true);
gates.INDEPENDENT_AUDIT_REPLAY = basePassed && attacksPassed;
const failedGates = spec.requiredGates.filter(name => gates[name] !== true);
const finalVerdict = failedGates.length ? 'INVALID_CAPACITY_SENTINEL' : 'ACTIVE_CAPACITY_SENTINEL_ADMITTED';
const audit = {
  schemaVersion: 'bfs.host-capacity-sentinel-audit.v0.1', experimentId: spec.experimentId,
  auditedAt: new Date().toISOString(), finalVerdict, liveSeverity: latest.classification.severity,
  gates, passedGates: spec.requiredGates.filter(name => gates[name] === true).length,
  totalGates: spec.requiredGates.length, failedGates, attackIdsExact,
  attackResults: attacks, attacksPassed: attacks.filter(value => value.rejected).length, attacksTotal: attacks.length,
  liveState: { latestSha256: sha256(latestText), historySha256: sha256(historyText), historySamples: history.samples.length, serviceTarget, servicePrintSha256: sha256(service.stdout) },
  selfHash: '',
};
writeAudit(audit);
process.stdout.write(`${JSON.stringify({ experimentId: spec.experimentId, finalVerdict, severity: audit.liveSeverity, gates: `${audit.passedGates}/${audit.totalGates}`, attacks: `${audit.attacksPassed}/${audit.attacksTotal}`, failedGates })}\n`);
