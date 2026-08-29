#!/usr/bin/env node

import { createHash } from 'node:crypto';
import {
  closeSync, existsSync, fsyncSync, mkdirSync, openSync, readFileSync, readdirSync,
  renameSync, statfsSync, statSync, unlinkSync, writeFileSync,
} from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const repositoryRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const spec = JSON.parse(readFileSync(resolve(repositoryRoot, 'specs/host-capacity-sentinel.v0.1.json'), 'utf8'));
const canonical = value => Array.isArray(value)
  ? `[${value.map(canonical).join(',')}]`
  : value && typeof value === 'object'
    ? `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}`
    : JSON.stringify(value);
const sha256 = value => createHash('sha256').update(value).digest('hex');
const withoutHash = value => { const copy = structuredClone(value); delete copy.selfHash; return copy; };
const seal = value => { value.selfHash = sha256(canonical(withoutHash(value))); return value; };
const validHash = value => value?.selfHash === sha256(canonical(withoutHash(value)));

function parseArguments(argv) {
  const options = { stateRoot: spec.state.root, dryRun: false, selfTest: false, noNotify: false, quiet: false };
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--state-root') options.stateRoot = argv[++index];
    else if (token === '--dry-run') options.dryRun = true;
    else if (token === '--self-test') options.selfTest = true;
    else if (token === '--no-notify') options.noNotify = true;
    else if (token === '--quiet') options.quiet = true;
    else throw new Error(`unknown argument: ${token}`);
  }
  if (!options.stateRoot) throw new Error('missing --state-root value');
  return options;
}

function allocatedTree(path, maximumEntries) {
  let allocatedBytes = 0;
  let entries = 0;
  const pending = [path];
  while (pending.length) {
    const current = pending.pop();
    if (!existsSync(current)) continue;
    const state = statSync(current);
    entries += 1;
    if (entries > maximumEntries) throw new Error('browser filesystem entry ceiling exceeded');
    allocatedBytes += Number(state.blocks) * 512;
    if (state.isDirectory()) for (const name of readdirSync(current)) pending.push(join(current, name));
  }
  return { allocatedBytes, entries };
}

function diskFile(path) {
  const state = statSync(path);
  return {
    path,
    device: state.dev,
    inode: state.ino,
    logicalBytes: state.size,
    allocatedBytes: Number(state.blocks) * 512,
    modifiedMs: state.mtimeMs,
  };
}

function maximumLossWithin(samples, current, minimumSpanSeconds, maximumSpanSeconds) {
  const currentMs = Date.parse(current.capturedAt);
  const eligible = samples.filter(sample => {
    const span = (currentMs - Date.parse(sample.capturedAt)) / 1000;
    return span >= minimumSpanSeconds && span <= maximumSpanSeconds;
  });
  return eligible.reduce((maximum, sample) => Math.max(maximum, sample.availableBytes - current.availableBytes), 0);
}

function classify(samples, current) {
  const thresholds = spec.thresholds;
  const rapidLossBytes = maximumLossWithin(samples, current, thresholds.rapidLossMinimumSpanSeconds, thresholds.rapidLossMaximumSpanSeconds);
  const longLossBytes = maximumLossWithin(samples, current, thresholds.longLossMinimumSpanSeconds, thresholds.longLossMaximumSpanSeconds);
  let severity = 'HEALTHY';
  const reasons = [];
  if (current.availableBytes < thresholds.emergencyAvailableBytes) {
    severity = 'EMERGENCY_CAPACITY';
    reasons.push('AVAILABLE_BELOW_EMERGENCY');
  } else if (current.browserTempFilesystem.allocatedBytes >= thresholds.browserCriticalBytes) {
    severity = 'EMERGENCY_CAPACITY';
    reasons.push('BROWSER_TEMP_CRITICAL');
  } else if (current.availableBytes < thresholds.criticalAvailableBytes) {
    severity = 'CRITICAL_CAPACITY';
    reasons.push('AVAILABLE_BELOW_CRITICAL');
  } else if (current.availableBytes < thresholds.warningAvailableBytes) {
    severity = 'WARNING_CAPACITY';
    reasons.push('AVAILABLE_BELOW_WARNING');
  } else if (rapidLossBytes >= thresholds.rapidLossBytes || longLossBytes >= thresholds.longLossBytes
    || current.browserTempFilesystem.allocatedBytes >= thresholds.browserWarningBytes) {
    severity = 'WARNING_RAPID_LOSS';
    if (rapidLossBytes >= thresholds.rapidLossBytes) reasons.push('RAPID_LOSS');
    if (longLossBytes >= thresholds.longLossBytes) reasons.push('LONG_LOSS');
    if (current.browserTempFilesystem.allocatedBytes >= thresholds.browserWarningBytes) reasons.push('BROWSER_TEMP_WARNING');
  }
  return {
    severity,
    reasons,
    rapidLossBytes,
    longLossBytes,
    productionRecommendation: severity === 'HEALTHY' ? 'NORMAL_GUARDED_ADMISSION' : 'FAIL_CLOSED_PRESERVE_AND_ATTRIBUTE',
  };
}

function atomicJson(path, value, maximumBytes) {
  const text = `${JSON.stringify(seal(value), null, 2)}\n`;
  if (Buffer.byteLength(text) > maximumBytes) throw new Error(`state byte ceiling exceeded: ${path}`);
  const temporary = `${path}.tmp-${process.pid}`;
  const fd = openSync(temporary, 'wx', 0o600);
  try { writeFileSync(fd, text); fsyncSync(fd); } finally { closeSync(fd); }
  try { renameSync(temporary, path); } catch (error) { try { unlinkSync(temporary); } catch {} throw error; }
  const directoryFd = openSync(dirname(path), 'r');
  try { fsyncSync(directoryFd); } finally { closeSync(directoryFd); }
  return { sha256: sha256(text), selfHash: value.selfHash, bytes: Buffer.byteLength(text) };
}

function readState(path, fallback) {
  if (!existsSync(path)) return fallback;
  const text = readFileSync(path, 'utf8');
  if (Buffer.byteLength(text) > spec.state.maximumStateFileBytes) throw new Error(`oversized prior state: ${path}`);
  const value = JSON.parse(text);
  if (!validHash(value)) throw new Error(`invalid prior state self-hash: ${path}`);
  return value;
}

function capture() {
  const filesystem = statfsSync(spec.runtime.volumeTarget);
  return seal({
    schemaVersion: 'bfs.host-capacity-sample.v0.1',
    capturedAt: new Date().toISOString(),
    availableBytes: Number(filesystem.bavail * filesystem.bsize),
    capacityBytes: Number(filesystem.blocks * filesystem.bsize),
    browserTempFilesystem: allocatedTree(spec.tracked.browserTempFilesystemPath, spec.state.maximumBrowserEntries),
    colima: {
      vmDisk: diskFile(spec.tracked.colimaVmDiskPath),
      dataDisk: diskFile(spec.tracked.colimaDataDiskPath),
    },
    prohibitedActions: {
      deletions: 0, cleanupOperations: 0, serviceRestarts: 0, dockerCalls: 0,
      blenderProcesses: 0, networkCalls: 0, modelCalls: 0,
    },
    selfHash: '',
  });
}

function selfTest() {
  const now = Date.now();
  const gib = 1024 ** 3;
  const sample = (minutesAgo, availableGiB, browser = 0) => seal({ capturedAt: new Date(now - minutesAgo * 60000).toISOString(), availableBytes: availableGiB * gib, browserTempFilesystem: { allocatedBytes: browser }, selfHash: '' });
  const cases = [
    [[], sample(0, 260), 'HEALTHY'],
    [[], sample(0, 249.999), 'WARNING_CAPACITY'],
    [[], sample(0, 179.999), 'CRITICAL_CAPACITY'],
    [[], sample(0, 139.999), 'EMERGENCY_CAPACITY'],
    [[sample(15, 280)], sample(0, 269), 'WARNING_RAPID_LOSS'],
    [[sample(24 * 60, 300)], sample(0, 274), 'WARNING_RAPID_LOSS'],
    [[], sample(0, 260, spec.thresholds.browserWarningBytes), 'WARNING_RAPID_LOSS'],
    [[], sample(0, 260, spec.thresholds.browserCriticalBytes), 'EMERGENCY_CAPACITY'],
  ];
  if (!cases.every(([history, current, expected]) => classify(history, current).severity === expected)) throw new Error('classifier boundary self-test failed');
  const oversized = Array.from({ length: 193 }, (_, index) => sample(index * 15, 300));
  if (oversized.slice(-spec.state.maximumHistorySamples).length !== 192) throw new Error('history ceiling self-test failed');
  const maximumHistory = seal({ schemaVersion: 'bfs.host-capacity-history.v0.1', samples: oversized.slice(-spec.state.maximumHistorySamples), selfHash: '' });
  if (Buffer.byteLength(`${JSON.stringify(maximumHistory, null, 2)}\n`) > spec.state.maximumStateFileBytes) throw new Error('maximum history exceeds state byte ceiling');
  const sensorError = sensorErrorLatest(new Error('synthetic sensor failure'));
  if (sensorError.classification.severity !== 'SENSOR_ERROR' || sensorError.classification.productionRecommendation !== 'FAIL_CLOSED_PRESERVE_AND_ATTRIBUTE') {
    throw new Error('sensor-error self-test failed');
  }
  return { selfTest: 'PASS', cases: cases.length + 1, historyCeiling: 192, prohibitedActions: 0 };
}

function sensorErrorLatest(error) {
  return seal({
    schemaVersion: 'bfs.host-capacity-latest.v0.1',
    experimentId: spec.experimentId,
    sample: seal({
      schemaVersion: 'bfs.host-capacity-sensor-error-sample.v0.1',
      capturedAt: new Date().toISOString(),
      error: { name: error?.name || 'Error', message: error?.message || String(error) },
      prohibitedActions: {
        deletions: 0, cleanupOperations: 0, serviceRestarts: 0, dockerCalls: 0,
        blenderProcesses: 0, networkCalls: 0, modelCalls: 0,
      },
      selfHash: '',
    }),
    classification: {
      severity: 'SENSOR_ERROR', reasons: ['SENSOR_FAILURE'], rapidLossBytes: null, longLossBytes: null,
      productionRecommendation: 'FAIL_CLOSED_PRESERVE_AND_ATTRIBUTE',
    },
    schedule: { intervalSeconds: spec.schedule.intervalSeconds },
    policy: spec.policy,
    selfHash: '',
  });
}

let options;
process.on('uncaughtException', error => {
  try {
    if (options && !options.selfTest && !options.dryRun) {
      const stateRoot = resolve(options.stateRoot);
      if (stateRoot === resolve(spec.state.root)) {
        mkdirSync(stateRoot, { recursive: true, mode: 0o700 });
        const latest = sensorErrorLatest(error);
        atomicJson(resolve(stateRoot, spec.state.latestFile), latest, spec.state.maximumStateFileBytes);
        atomicJson(resolve(stateRoot, spec.state.alertFile), seal({
          schemaVersion: 'bfs.host-capacity-alert.v0.1', createdAt: new Date().toISOString(), severity: 'SENSOR_ERROR',
          reasons: ['SENSOR_FAILURE'], availableBytes: null, productionRecommendation: 'FAIL_CLOSED_PRESERVE_AND_ATTRIBUTE',
          notification: { attempted: false, delivered: false, exitCode: null }, selfHash: '',
        }), spec.state.maximumStateFileBytes);
      }
    }
  } catch {}
  if (!options?.quiet) process.stderr.write(`BFS_CAPACITY_SENTINEL_ERROR ${error?.message || String(error)}\n`);
  process.exit(75);
});

options = parseArguments(process.argv.slice(2));
if (options.selfTest) {
  process.stdout.write(`${JSON.stringify(selfTest())}\n`);
  process.exit(0);
}

const stateRoot = resolve(options.stateRoot);
if (stateRoot !== resolve(spec.state.root)) throw new Error('state root differs from frozen path');
const latestPath = resolve(stateRoot, spec.state.latestFile);
const historyPath = resolve(stateRoot, spec.state.historyFile);
const alertPath = resolve(stateRoot, spec.state.alertFile);
const previousLatest = existsSync(latestPath) ? readState(latestPath, null) : null;
const previousHistory = readState(historyPath, seal({ schemaVersion: 'bfs.host-capacity-history.v0.1', samples: [], selfHash: '' }));
if (previousHistory.schemaVersion !== 'bfs.host-capacity-history.v0.1' || !Array.isArray(previousHistory.samples)
  || previousHistory.samples.length > spec.state.maximumHistorySamples || !previousHistory.samples.every(validHash)) throw new Error('prior history schema invalid');

const sample = capture();
const classification = classify(previousHistory.samples, sample);
const latest = seal({
  schemaVersion: 'bfs.host-capacity-latest.v0.1',
  experimentId: spec.experimentId,
  sample,
  classification,
  schedule: { intervalSeconds: spec.schedule.intervalSeconds },
  policy: spec.policy,
  selfHash: '',
});
const samples = [...previousHistory.samples, sample].slice(-spec.state.maximumHistorySamples);
const history = seal({ schemaVersion: 'bfs.host-capacity-history.v0.1', samples, selfHash: '' });
const previousSeverity = previousLatest?.classification?.severity ?? null;
const previousAlert = existsSync(alertPath) ? readState(alertPath, null) : null;
const repeatDue = previousAlert ? Date.now() - Date.parse(previousAlert.createdAt) >= spec.schedule.notificationRepeatSeconds * 1000 : true;
const shouldAlert = classification.severity !== 'HEALTHY' && (classification.severity !== previousSeverity || repeatDue);
const dryResult = { latest, historySamples: samples.length, shouldAlert, previousSeverity, stateRoot };

if (options.dryRun) {
  if (!options.quiet) process.stdout.write(`${JSON.stringify({ ...dryResult, dryRun: true }, null, 2)}\n`);
  process.exit(0);
}

mkdirSync(stateRoot, { recursive: true, mode: 0o700 });
const historyReceipt = atomicJson(historyPath, history, spec.state.maximumStateFileBytes);
const latestReceipt = atomicJson(latestPath, latest, spec.state.maximumStateFileBytes);
let alertReceipt = null;
if (shouldAlert) {
  let notification = { attempted: false, delivered: false, exitCode: null };
  if (!options.noNotify && spec.policy.localNotificationOnTransition) {
    const message = `BlenderFilmStudio: ${classification.severity}; available ${(sample.availableBytes / 1024 ** 3).toFixed(1)} GiB`;
    const result = spawnSync('/usr/bin/osascript', ['-e', `display notification ${JSON.stringify(message)} with title "BlenderFilmStudio capacity"`], { encoding: 'utf8', timeout: 5000 });
    notification = { attempted: true, delivered: result.status === 0, exitCode: result.status, errorCode: result.error?.code || null };
  }
  const alert = seal({
    schemaVersion: 'bfs.host-capacity-alert.v0.1', createdAt: new Date().toISOString(),
    severity: classification.severity, reasons: classification.reasons,
    availableBytes: sample.availableBytes, productionRecommendation: classification.productionRecommendation,
    notification, selfHash: '',
  });
  alertReceipt = atomicJson(alertPath, alert, spec.state.maximumStateFileBytes);
}
const output = { status: classification.severity, sample, classification, historySamples: samples.length, receipts: { latest: latestReceipt, history: historyReceipt, alert: alertReceipt } };
if (!options.quiet) process.stdout.write(`${JSON.stringify(output, null, 2)}\n`);
if (['CRITICAL_CAPACITY', 'EMERGENCY_CAPACITY', 'SENSOR_ERROR'].includes(classification.severity)) process.exitCode = 75;
