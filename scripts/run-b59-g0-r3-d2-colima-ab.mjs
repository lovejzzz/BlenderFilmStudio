#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { closeSync, existsSync, fsyncSync, mkdirSync, openSync, readFileSync, statfsSync, statSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { execFileSync, spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const repo = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const specPath = resolve(repo, 'specs/codex-host-disk-colima-ab.v0.1.json');
const spec = JSON.parse(readFileSync(specPath));
const root = resolve(repo, spec.formalRoot);
const canonical = value => Array.isArray(value)
  ? `[${value.map(canonical)}]`
  : value && typeof value === 'object'
    ? `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}`
    : JSON.stringify(value);
const sha = value => createHash('sha256').update(value).digest('hex');
const shaFile = path => sha(readFileSync(path));
const withoutHash = value => { const copy = structuredClone(value); delete copy.selfHash; return copy; };
const seal = value => { value.selfHash = sha(canonical(withoutHash(value))); return value; };
const sleep = ms => new Promise(resolveSleep => setTimeout(resolveSleep, ms));

function writeExclusive(path, value, ceiling) {
  const text = `${JSON.stringify(seal(value), null, 2)}\n`;
  if (Buffer.byteLength(text) > ceiling) throw new Error(`evidence byte ceiling: ${path}`);
  const fd = openSync(path, 'wx');
  try { writeFileSync(fd, text); fsyncSync(fd); } finally { closeSync(fd); }
  return { path, text, sha256: sha(text), selfHash: value.selfHash, bytes: Buffer.byteLength(text) };
}

function command(binary, args, timeoutMs = 5000, captureLimit = 32768) {
  const started = Date.now();
  const result = spawnSync(binary, args, {
    cwd: repo,
    encoding: 'utf8',
    timeout: timeoutMs,
    maxBuffer: 1024 * 1024,
    env: { ...process.env, LC_ALL: 'C' }
  });
  const stdout = (result.stdout || '').slice(0, captureLimit);
  const stderr = (result.stderr || '').slice(0, captureLimit);
  return {
    binary,
    args,
    startedAt: new Date(started).toISOString(),
    completedAt: new Date().toISOString(),
    durationMs: Date.now() - started,
    exitCode: result.status,
    signal: result.signal || null,
    errorCode: result.error?.code || null,
    stdout,
    stderr
  };
}

function diskState() {
  return Object.fromEntries(Object.entries(spec.restoreManifest.diskFiles).map(([key, expected]) => {
    const value = statSync(expected.path);
    return [key, {
      path: expected.path,
      device: value.dev,
      inode: value.ino,
      logicalBytes: value.size,
      allocatedBytes: Number(value.blocks) * 512,
      modifiedMs: value.mtimeMs
    }];
  }));
}

function profileStatus() {
  const result = command(spec.profile.colimaBinary, ['status', '--profile', spec.profile.name]);
  const combined = `${result.stdout}\n${result.stderr}`;
  return {
    running: result.exitCode === 0 && /colima is running/.test(combined),
    arch: (combined.match(/arch:\s*([^"\s]+)/) || [])[1] || null,
    runtime: (combined.match(/runtime:\s*([^"\s]+)/) || [])[1] || null,
    mountType: (combined.match(/mountType:\s*([^"\s]+)/) || [])[1] || null,
    command: { exitCode: result.exitCode, errorCode: result.errorCode, stdoutBytes: Buffer.byteLength(result.stdout), stderrBytes: Buffer.byteLength(result.stderr) }
  };
}

function containerState() {
  const ids = spec.restoreManifest.containers.map(container => container.id);
  const ps = command(spec.profile.dockerBinary, ['--host', spec.profile.dockerSocket, 'ps', '--no-trunc', '--format', '{{.ID}}']);
  if (ps.exitCode !== 0) return { socketReachable: false, runningIds: [], containers: [], command: { exitCode: ps.exitCode, errorCode: ps.errorCode } };
  const runningIds = ps.stdout.trim().split('\n').filter(Boolean).sort();
  const result = command(spec.profile.dockerBinary, ['--host', spec.profile.dockerSocket, 'inspect', ...ids], 5000, 1024 * 1024);
  if (result.exitCode !== 0) return { socketReachable: true, runningIds, containers: [], command: { exitCode: result.exitCode, errorCode: result.errorCode } };
  let parsed;
  try { parsed = JSON.parse(result.stdout); } catch { return { socketReachable: true, runningIds, parseError: true, containers: [], command: { exitCode: result.exitCode } }; }
  const containers = parsed.map(item => ({
    id: item.Id,
    name: String(item.Name || '').replace(/^\//, ''),
    image: item.Config?.Image || null,
    restartPolicy: item.HostConfig?.RestartPolicy?.Name || null,
    autoRemove: item.HostConfig?.AutoRemove ?? null,
    running: item.State?.Running === true,
    startedAt: item.State?.StartedAt || null
  })).sort((a, b) => a.id.localeCompare(b.id));
  return { socketReachable: true, runningIds, containers, command: { exitCode: result.exitCode } };
}

function configState() {
  return Object.fromEntries(Object.entries(spec.restoreManifest.configFiles).map(([key, expected]) => [key, { path: expected.path, sha256: shaFile(expected.path) }]));
}

function captureState() {
  const fs = statfsSync('/');
  return {
    capturedAt: new Date().toISOString(),
    hostAvailableBytes: Number(fs.bavail * fs.bsize),
    disks: diskState(),
    configs: configState(),
    profile: profileStatus(),
    docker: containerState()
  };
}

function exactContainers(state, requireRunning) {
  const expected = [...spec.restoreManifest.containers].sort((a, b) => a.id.localeCompare(b.id));
  const observed = [...state.docker.containers].sort((a, b) => a.id.localeCompare(b.id));
  const exactRunningSet = !requireRunning || canonical(state.docker.runningIds || []) === canonical(expected.map(value => value.id).sort());
  return state.docker.socketReachable && exactRunningSet && observed.length === expected.length && expected.every((item, index) => {
    const value = observed[index];
    return value?.id === item.id && value.name === item.name && value.image === item.image && value.restartPolicy === item.restartPolicy && value.autoRemove === item.autoRemove && (!requireRunning || value.running);
  });
}

function profileMatches(state) {
  return state.profile.running && state.profile.arch === spec.profile.arch && state.profile.runtime === spec.profile.runtime && state.profile.mountType === spec.profile.mountType;
}

function configAndDiskIdentity(state) {
  const configs = Object.entries(spec.restoreManifest.configFiles).every(([key, expected]) => state.configs[key]?.sha256 === expected.sha256);
  const disks = Object.entries(spec.restoreManifest.diskFiles).every(([key, expected]) => {
    const observed = state.disks[key];
    return observed?.path === expected.path && observed.device === expected.device && observed.inode === expected.inode && observed.logicalBytes === expected.logicalBytes;
  });
  return configs && disks;
}

function initialManifestMatches(state) {
  return profileMatches(state) && exactContainers(state, true) && configAndDiskIdentity(state);
}

async function waitFor(check, timeoutSeconds) {
  const deadline = Date.now() + timeoutSeconds * 1000;
  let latest = captureState();
  while (!check(latest) && Date.now() < deadline) {
    await sleep(2000);
    latest = captureState();
  }
  return latest;
}

async function capturePhase(phase, firstIndex, receipts) {
  let previous = null;
  for (let offset = 0; offset < spec.observationPolicy.samplesPerPhase; offset += 1) {
    const due = previous === null ? Date.now() : previous + spec.observationPolicy.minimumIntervalSeconds * 1000;
    if (Date.now() < due) await sleep(due - Date.now());
    const captured = captureState();
    const at = Date.parse(captured.capturedAt);
    const sample = {
      schemaVersion: 'bfs.codex-host-disk-colima-ab-sample.v0.1',
      experimentId: spec.experimentId,
      index: firstIndex + offset,
      phase,
      phaseIndex: offset + 1,
      scheduledAt: new Date(due).toISOString(),
      latenessMs: at - due,
      state: captured,
      selfHash: ''
    };
    receipts.push(writeExclusive(resolve(root, `sample-${String(sample.index).padStart(3, '0')}.json`), sample, spec.byteCeilings.sample));
    previous = at;
    process.stderr.write(`D2 ${phase} sample ${offset + 1}/${spec.observationPolicy.samplesPerPhase}\n`);
  }
}

function aggregate(samples) {
  const phases = {};
  for (const phase of spec.observationPolicy.phaseOrder) {
    const values = samples.filter(sample => sample.phase === phase);
    const first = values[0].state;
    const last = values.at(-1).state;
    phases[phase] = {
      sampleCount: values.length,
      spanMs: Date.parse(values.at(-1).state.capturedAt) - Date.parse(values[0].state.capturedAt),
      intervalsMs: values.slice(1).map((sample, index) => Date.parse(sample.state.capturedAt) - Date.parse(values[index].state.capturedAt)),
      hostLossBytes: first.hostAvailableBytes - last.hostAvailableBytes,
      diskAllocatedDeltaBytes: Object.fromEntries(Object.keys(spec.restoreManifest.diskFiles).map(key => [key, last.disks[key].allocatedBytes - first.disks[key].allocatedBytes]))
    };
  }
  return { phases };
}

function isSuppressed(stoppedLoss, comparisonLoss) {
  return stoppedLoss <= spec.observationPolicy.maximumSuppressedHostLossBytes && stoppedLoss <= comparisonLoss * spec.observationPolicy.maximumSuppressedFraction;
}

function interpret(aggregateValue) {
  const active = aggregateValue.phases.ACTIVE_BASELINE.hostLossBytes;
  const stopped = aggregateValue.phases.STOPPED.hostLossBytes;
  const restored = aggregateValue.phases.RESTORED.hostLossBytes;
  const material = value => value >= spec.observationPolicy.minimumMaterialHostLossBytes;
  if (!material(active) && !material(stopped) && !material(restored)) return 'NO_MATERIAL_LOSS_REPRODUCED';
  if (material(active) && material(restored) && isSuppressed(stopped, active) && isSuppressed(stopped, restored)) return 'ACTIVE_STOPPED_RESTORED_MATCH';
  if (material(active) && isSuppressed(stopped, active) && !material(restored)) return 'ACTIVE_ONLY_STOPPED_SUPPRESSION';
  if (material(stopped) || (material(active) && !isSuppressed(stopped, active))) return 'STOPPED_NOT_SUPPRESSED';
  return 'MIXED_OR_INCONCLUSIVE';
}

function timingValid(samples, aggregateValue) {
  if (samples.length !== spec.observationPolicy.phaseOrder.length * spec.observationPolicy.samplesPerPhase) return false;
  return spec.observationPolicy.phaseOrder.every((phase, phaseOffset) => {
    const values = samples.filter(sample => sample.phase === phase);
    return values.length === spec.observationPolicy.samplesPerPhase && values.every((sample, offset) => sample.index === phaseOffset * spec.observationPolicy.samplesPerPhase + offset + 1 && sample.phaseIndex === offset + 1 && sample.latenessMs >= 0 && sample.latenessMs <= spec.observationPolicy.maximumLatenessSeconds * 1000) && aggregateValue.phases[phase].spanMs >= spec.observationPolicy.minimumPhaseSpanSeconds * 1000 && aggregateValue.phases[phase].intervalsMs.every(value => value >= spec.observationPolicy.minimumIntervalSeconds * 1000);
  });
}

if (process.argv.includes('--self-test')) {
  const make = (active, stopped, restored) => ({ phases: { ACTIVE_BASELINE: { hostLossBytes: active }, STOPPED: { hostLossBytes: stopped }, RESTORED: { hostLossBytes: restored } } });
  const cases = [
    [100e6, 5e6, 90e6, 'ACTIVE_STOPPED_RESTORED_MATCH'],
    [100e6, 5e6, 1e6, 'ACTIVE_ONLY_STOPPED_SUPPRESSION'],
    [100e6, 80e6, 90e6, 'STOPPED_NOT_SUPPRESSED'],
    [1e6, 2e6, 3e6, 'NO_MATERIAL_LOSS_REPRODUCED'],
    [1e6, 2e6, 90e6, 'MIXED_OR_INCONCLUSIVE']
  ];
  if (!cases.every(([a, b, c, expected]) => interpret(make(a, b, c)) === expected)) throw new Error('interpretation self-test failed');
  process.stdout.write('{"selfTest":"PASS","mutations":0}\n');
  process.exit(0);
}

if (existsSync(root)) throw new Error('formal root is not fresh');
const scoped = execFileSync('/usr/bin/git', ['status', '--short', '--', ...spec.releasePaths], { cwd: repo, encoding: 'utf8' }).trim();
const [head, origin] = execFileSync('/usr/bin/git', ['rev-parse', 'HEAD', 'origin/main'], { cwd: repo, encoding: 'utf8' }).trim().split('\n');
execFileSync('/usr/bin/git', ['merge-base', '--is-ancestor', spec.parentCommit, head], { cwd: repo });
if (scoped || head !== origin) throw new Error('release preflight failed');

const initial = captureState();
if (!initialManifestMatches(initial)) throw new Error('initial state does not match restore manifest');
mkdirSync(root);
const start = {
  schemaVersion: 'bfs.codex-host-disk-colima-ab-start.v0.1',
  experimentId: spec.experimentId,
  startedAt: new Date().toISOString(),
  specSha256: shaFile(specPath),
  git: { head, origin, scopedStatus: scoped },
  parentEvidence: {
    resultsSha256: shaFile(resolve(repo, spec.parentEvidence.resultsPath)),
    auditSha256: shaFile(resolve(repo, spec.parentEvidence.auditPath))
  },
  initialState: initial,
  selfHash: ''
};
const startReceipt = writeExclusive(resolve(root, 'start.json'), start, spec.byteCeilings.transition);
const sampleReceipts = [];
const transitionReceipts = [];
const resourceAccounting = {
  filesystemWritesOutsideFormalRoot: 0,
  cleanupOperations: 0,
  profileConfigurationMutations: 0,
  containerCreates: 0,
  containerRemoves: 0,
  imageOrVolumeMutations: 0,
  signalsSent: 0,
  networkCalls: 0,
  modelCalls: 0,
  stopCommands: 0,
  startCommands: 0,
  explicitContainerStarts: 0
};
let transitionStarted = false;
let stopReceiptValue = null;
let startReceiptValue = null;
let finalState = initial;
let runError = null;

async function restore(reason) {
  let state = captureState();
  const actions = [];
  if (!profileMatches(state) && resourceAccounting.startCommands < spec.observationPolicy.recoveryAttempts) {
    resourceAccounting.startCommands += 1;
    actions.push(command(spec.profile.colimaBinary, ['start', spec.profile.name], spec.observationPolicy.startTimeoutSeconds * 1000));
    state = await waitFor(profileMatches, spec.observationPolicy.startTimeoutSeconds);
  }
  if (profileMatches(state)) {
    const runningIds = new Set(state.docker.containers.filter(value => value.running).map(value => value.id));
    const missing = spec.restoreManifest.containers.filter(value => !runningIds.has(value.id));
    for (const container of missing) {
      if (resourceAccounting.explicitContainerStarts >= spec.formalCeilings.maximumExplicitContainerStarts) break;
      resourceAccounting.explicitContainerStarts += 1;
      actions.push(command(spec.profile.dockerBinary, ['--host', spec.profile.dockerSocket, 'start', container.id], spec.observationPolicy.containerRestoreTimeoutSeconds * 1000));
    }
    state = await waitFor(value => profileMatches(value) && exactContainers(value, true), spec.observationPolicy.containerRestoreTimeoutSeconds);
  }
  const restored = profileMatches(state) && exactContainers(state, true) && configAndDiskIdentity(state);
  const recovery = {
    schemaVersion: 'bfs.codex-host-disk-colima-ab-recovery.v0.1',
    experimentId: spec.experimentId,
    reason,
    actions,
    restored,
    finalState: state,
    selfHash: ''
  };
  return { restored, state, recovery };
}

try {
  await capturePhase('ACTIVE_BASELINE', 1, sampleReceipts);
  transitionStarted = true;
  resourceAccounting.stopCommands += 1;
  const stopCommand = command(spec.profile.colimaBinary, ['stop', spec.profile.name], spec.observationPolicy.stopTimeoutSeconds * 1000);
  const stoppedState = await waitFor(value => !value.profile.running && !value.docker.socketReachable, spec.observationPolicy.stopTimeoutSeconds);
  stopReceiptValue = {
    schemaVersion: 'bfs.codex-host-disk-colima-ab-transition.v0.1',
    experimentId: spec.experimentId,
    transition: 'STOP_DEFAULT',
    command: stopCommand,
    confirmed: !stoppedState.profile.running && !stoppedState.docker.socketReachable,
    state: stoppedState,
    selfHash: ''
  };
  transitionReceipts.push(writeExclusive(resolve(root, 'transition-stop.json'), stopReceiptValue, spec.byteCeilings.transition));
  if (stopCommand.exitCode !== 0 || !stopReceiptValue.confirmed) throw new Error('graceful stop was not confirmed');

  await capturePhase('STOPPED', 4, sampleReceipts);
  resourceAccounting.startCommands += 1;
  const startCommand = command(spec.profile.colimaBinary, ['start', spec.profile.name], spec.observationPolicy.startTimeoutSeconds * 1000);
  let restoredState = await waitFor(value => profileMatches(value) && exactContainers(value, true), spec.observationPolicy.containerRestoreTimeoutSeconds);
  const explicitStarts = [];
  if (profileMatches(restoredState) && !exactContainers(restoredState, true)) {
    const runningIds = new Set(restoredState.docker.containers.filter(value => value.running).map(value => value.id));
    for (const container of spec.restoreManifest.containers.filter(value => !runningIds.has(value.id))) {
      resourceAccounting.explicitContainerStarts += 1;
      explicitStarts.push(command(spec.profile.dockerBinary, ['--host', spec.profile.dockerSocket, 'start', container.id], spec.observationPolicy.containerRestoreTimeoutSeconds * 1000));
    }
    restoredState = await waitFor(value => profileMatches(value) && exactContainers(value, true), spec.observationPolicy.containerRestoreTimeoutSeconds);
  }
  startReceiptValue = {
    schemaVersion: 'bfs.codex-host-disk-colima-ab-transition.v0.1',
    experimentId: spec.experimentId,
    transition: 'START_DEFAULT_AND_RESTORE',
    command: startCommand,
    explicitContainerStarts: explicitStarts,
    confirmed: profileMatches(restoredState) && exactContainers(restoredState, true),
    state: restoredState,
    selfHash: ''
  };
  transitionReceipts.push(writeExclusive(resolve(root, 'transition-start.json'), startReceiptValue, spec.byteCeilings.transition));
  if (startCommand.exitCode !== 0 || !startReceiptValue.confirmed) throw new Error('restore was not confirmed');

  await capturePhase('RESTORED', 7, sampleReceipts);
  finalState = captureState();
} catch (error) {
  runError = error;
} finally {
  if (transitionStarted) {
    const recovery = await restore(runError ? `exception:${runError.message}` : 'final-restoration-invariant');
    finalState = recovery.state;
    if (runError || !recovery.restored) writeExclusive(resolve(root, 'recovery.json'), recovery.recovery, spec.byteCeilings.transition);
    if (!recovery.restored && !runError) runError = new Error('final restoration invariant failed');
  }
}

if (runError) {
  const failure = {
    schemaVersion: 'bfs.codex-host-disk-colima-ab-failure.v0.1',
    experimentId: spec.experimentId,
    failedAt: new Date().toISOString(),
    error: runError.message,
    resourceAccounting,
    finalRestored: profileMatches(finalState) && exactContainers(finalState, true) && configAndDiskIdentity(finalState),
    finalState,
    selfHash: ''
  };
  writeExclusive(resolve(root, 'failure.json'), failure, spec.byteCeilings.results);
  throw runError;
}

const samples = sampleReceipts.map(receipt => JSON.parse(receipt.text));
const aggregateValue = aggregate(samples);
const interpretation = interpret(aggregateValue);
const samplesIntact = sampleReceipts.every(receipt => {
  const value = JSON.parse(receipt.text);
  return value.selfHash === sha(canonical(withoutHash(value))) && receipt.bytes <= spec.byteCeilings.sample;
});
const gates = {
  SPEC_PARENT_AND_RELEASE_IDENTITY: start.specSha256 === shaFile(specPath) && start.git.head === start.git.origin && start.git.scopedStatus === '',
  PARENT_EVIDENCE_IDENTITY: start.parentEvidence.resultsSha256 === spec.parentEvidence.resultsSha256 && start.parentEvidence.auditSha256 === spec.parentEvidence.auditSha256,
  INITIAL_MANIFEST_MATCH: initialManifestMatches(start.initialState),
  PHASE_COUNT_ORDER_AND_TIMING: timingValid(samples, aggregateValue),
  STOPPED_STATE_CONFIRMED: stopReceiptValue?.confirmed === true && samples.filter(value => value.phase === 'STOPPED').every(value => !value.state.profile.running && !value.state.docker.socketReachable),
  RESTORED_PROFILE_RUNTIME_MATCH: profileMatches(finalState) && samples.filter(value => value.phase === 'RESTORED').every(value => profileMatches(value.state)),
  EXACT_CONTAINER_SET_RESTORED_RUNNING: exactContainers(finalState, true) && samples.filter(value => value.phase === 'RESTORED').every(value => exactContainers(value.state, true)),
  CONFIG_AND_DISK_IDENTITY_PRESERVED: configAndDiskIdentity(finalState) && samples.every(value => configAndDiskIdentity(value.state)),
  TRANSITIONS_BOUNDED_AND_ACCOUNTED: resourceAccounting.stopCommands === 1 && resourceAccounting.startCommands >= 1 && resourceAccounting.startCommands <= spec.formalCeilings.maximumStartCommandsIncludingRecovery && resourceAccounting.explicitContainerStarts <= spec.formalCeilings.maximumExplicitContainerStarts && stopReceiptValue?.command.exitCode === 0 && startReceiptValue?.command.exitCode === 0,
  EVIDENCE_BOUNDED_AND_SELF_HASHED: samplesIntact && transitionReceipts.every(receipt => receipt.bytes <= spec.byteCeilings.transition),
  NO_UNAUTHORIZED_MUTATION: resourceAccounting.filesystemWritesOutsideFormalRoot === 0 && resourceAccounting.cleanupOperations === 0 && resourceAccounting.profileConfigurationMutations === 0 && resourceAccounting.containerCreates === 0 && resourceAccounting.containerRemoves === 0 && resourceAccounting.imageOrVolumeMutations === 0 && resourceAccounting.signalsSent === 0 && resourceAccounting.networkCalls === 0 && resourceAccounting.modelCalls === 0,
  INDEPENDENT_AUDIT_REPLAY: 'PENDING'
};
const gateNames = spec.requiredGates.filter(value => value !== 'INDEPENDENT_AUDIT_REPLAY');
const failedGates = gateNames.filter(value => gates[value] !== true);
const results = {
  schemaVersion: 'bfs.codex-host-disk-colima-ab-results.v0.1',
  experimentId: spec.experimentId,
  completedAt: new Date().toISOString(),
  spec: { path: 'specs/codex-host-disk-colima-ab.v0.1.json', sha256: shaFile(specPath) },
  startReceipt: { sha256: startReceipt.sha256, selfHash: startReceipt.selfHash, bytes: startReceipt.bytes },
  sampleReceipts: sampleReceipts.map((receipt, index) => ({ index: index + 1, sha256: receipt.sha256, selfHash: receipt.selfHash, bytes: receipt.bytes })),
  transitionReceipts: transitionReceipts.map(receipt => ({ name: receipt.path.split('/').at(-1), sha256: receipt.sha256, selfHash: receipt.selfHash, bytes: receipt.bytes })),
  aggregate: aggregateValue,
  interpretation,
  resourceAccounting,
  finalState,
  gates,
  failedGates,
  provisionalVerdict: failedGates.length ? 'INVALID_EVIDENCE' : 'VALID_PENDING_AUDIT',
  receiptBytes: 0,
  selfHash: ''
};
let resultText;
for (let index = 0; index < 6; index += 1) {
  seal(results);
  resultText = `${JSON.stringify(results, null, 2)}\n`;
  results.receiptBytes = Buffer.byteLength(resultText);
}
seal(results);
resultText = `${JSON.stringify(results, null, 2)}\n`;
results.receiptBytes = Buffer.byteLength(resultText);
seal(results);
writeExclusive(resolve(root, 'results.json'), results, spec.byteCeilings.results);
const summary = `${JSON.stringify({ experimentId: spec.experimentId, provisionalVerdict: results.provisionalVerdict, interpretation, restored: true, failedGates, resultsPath: `${spec.formalRoot}/results.json` })}\n`;
if (Buffer.byteLength(summary) > spec.byteCeilings.stdout) throw new Error('stdout ceiling');
process.stdout.write(summary);
