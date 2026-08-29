#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { closeSync, existsSync, fsyncSync, openSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { execFileSync, spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const repo = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const specPath = resolve(repo, 'specs/codex-host-disk-colima-ab.v0.1.json');
const spec = JSON.parse(readFileSync(specPath));
const root = resolve(repo, spec.formalRoot);
const auditPath = resolve(root, 'audit.json');
const canonical = value => Array.isArray(value)
  ? `[${value.map(canonical)}]`
  : value && typeof value === 'object'
    ? `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}`
    : JSON.stringify(value);
const sha = value => createHash('sha256').update(value).digest('hex');
const shaFile = path => sha(readFileSync(path));
const withoutHash = value => { const copy = structuredClone(value); delete copy.selfHash; return copy; };
const validHash = value => value.selfHash === sha(canonical(withoutHash(value)));
const seal = value => { value.selfHash = sha(canonical(withoutHash(value))); return value; };

function command(binary, args) {
  const result = spawnSync(binary, args, { cwd: repo, encoding: 'utf8', timeout: 10000, maxBuffer: 1024 * 1024, env: { ...process.env, LC_ALL: 'C' } });
  return { exitCode: result.status, stdout: result.stdout || '', stderr: result.stderr || '', errorCode: result.error?.code || null };
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

function aggregate(samples) {
  const phases = {};
  for (const phase of spec.observationPolicy.phaseOrder) {
    const values = samples.filter(sample => sample.phase === phase);
    if (!values.length) { phases[phase] = null; continue; }
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

function timingValid(samples, aggregateValue) {
  if (samples.length !== spec.observationPolicy.phaseOrder.length * spec.observationPolicy.samplesPerPhase) return false;
  return spec.observationPolicy.phaseOrder.every((phase, phaseOffset) => {
    const values = samples.filter(sample => sample.phase === phase);
    const summary = aggregateValue.phases[phase];
    return values.length === spec.observationPolicy.samplesPerPhase && summary && values.every((sample, offset) => sample.index === phaseOffset * spec.observationPolicy.samplesPerPhase + offset + 1 && sample.phaseIndex === offset + 1 && sample.latenessMs >= 0 && sample.latenessMs <= spec.observationPolicy.maximumLatenessSeconds * 1000) && summary.spanMs >= spec.observationPolicy.minimumPhaseSpanSeconds * 1000 && summary.intervalsMs.every(value => value >= spec.observationPolicy.minimumIntervalSeconds * 1000);
  });
}

function expectedGates(bundle) {
  const { start, samples, stopTransition, startTransition, results } = bundle;
  const aggregateValue = aggregate(samples);
  const resources = results.resourceAccounting;
  return {
    SPEC_PARENT_AND_RELEASE_IDENTITY: start.specSha256 === shaFile(specPath) && results.spec.sha256 === shaFile(specPath) && start.git.head === start.git.origin && start.git.scopedStatus === '',
    PARENT_EVIDENCE_IDENTITY: start.parentEvidence.resultsSha256 === spec.parentEvidence.resultsSha256 && start.parentEvidence.auditSha256 === spec.parentEvidence.auditSha256,
    INITIAL_MANIFEST_MATCH: initialManifestMatches(start.initialState),
    PHASE_COUNT_ORDER_AND_TIMING: timingValid(samples, aggregateValue),
    STOPPED_STATE_CONFIRMED: stopTransition.confirmed === true && stopTransition.command.exitCode === 0 && samples.filter(value => value.phase === 'STOPPED').every(value => !value.state.profile.running && !value.state.docker.socketReachable),
    RESTORED_PROFILE_RUNTIME_MATCH: profileMatches(results.finalState) && samples.filter(value => value.phase === 'RESTORED').every(value => profileMatches(value.state)),
    EXACT_CONTAINER_SET_RESTORED_RUNNING: exactContainers(results.finalState, true) && samples.filter(value => value.phase === 'RESTORED').every(value => exactContainers(value.state, true)),
    CONFIG_AND_DISK_IDENTITY_PRESERVED: configAndDiskIdentity(results.finalState) && samples.every(value => configAndDiskIdentity(value.state)),
    TRANSITIONS_BOUNDED_AND_ACCOUNTED: resources.stopCommands === 1 && resources.startCommands >= 1 && resources.startCommands <= spec.formalCeilings.maximumStartCommandsIncludingRecovery && resources.explicitContainerStarts <= spec.formalCeilings.maximumExplicitContainerStarts && stopTransition.command.exitCode === 0 && startTransition.command.exitCode === 0 && startTransition.confirmed === true,
    EVIDENCE_BOUNDED_AND_SELF_HASHED: 'RECEIPT_REPLAY',
    NO_UNAUTHORIZED_MUTATION: resources.filesystemWritesOutsideFormalRoot === 0 && resources.cleanupOperations === 0 && resources.profileConfigurationMutations === 0 && resources.containerCreates === 0 && resources.containerRemoves === 0 && resources.imageOrVolumeMutations === 0 && resources.signalsSent === 0 && resources.networkCalls === 0 && resources.modelCalls === 0,
    INDEPENDENT_AUDIT_REPLAY: 'PENDING'
  };
}

function receiptIntegrity(bundle, texts) {
  const { start, samples, stopTransition, startTransition, results } = bundle;
  const sampleRefs = results.sampleReceipts.length === samples.length && samples.every((sample, index) => {
    const receipt = results.sampleReceipts[index];
    const text = texts.samples[index];
    return validHash(sample) && receipt.index === sample.index && receipt.sha256 === sha(text) && receipt.selfHash === sample.selfHash && receipt.bytes === Buffer.byteLength(text) && receipt.bytes <= spec.byteCeilings.sample;
  });
  const transitionValues = [stopTransition, startTransition];
  const transitionRefs = results.transitionReceipts.length === 2 && transitionValues.every((value, index) => {
    const receipt = results.transitionReceipts[index];
    const text = texts.transitions[index];
    return validHash(value) && receipt.sha256 === sha(text) && receipt.selfHash === value.selfHash && receipt.bytes === Buffer.byteLength(text) && receipt.bytes <= spec.byteCeilings.transition;
  });
  return validHash(start) && results.startReceipt.sha256 === sha(texts.start) && results.startReceipt.selfHash === start.selfHash && results.startReceipt.bytes === Buffer.byteLength(texts.start) && sampleRefs && transitionRefs && validHash(results) && results.receiptBytes === Buffer.byteLength(texts.results) && results.receiptBytes <= spec.byteCeilings.results;
}

function validate(bundle, texts) {
  const expected = expectedGates(bundle);
  expected.EVIDENCE_BOUNDED_AND_SELF_HASHED = receiptIntegrity(bundle, texts);
  const projected = spec.requiredGates.filter(value => value !== 'INDEPENDENT_AUDIT_REPLAY').every(value => expected[value] === true && bundle.results.gates[value] === true);
  return projected && canonical(bundle.results.aggregate) === canonical(aggregate(bundle.samples)) && validHash(bundle.results);
}

function serializeBundle(bundle) {
  const start = `${JSON.stringify(bundle.start, null, 2)}\n`;
  const samples = bundle.samples.map(value => `${JSON.stringify(value, null, 2)}\n`);
  const transitions = [bundle.stopTransition, bundle.startTransition].map(value => `${JSON.stringify(value, null, 2)}\n`);
  const results = `${JSON.stringify(bundle.results, null, 2)}\n`;
  return { start, samples, transitions, results };
}

function resealBundle(bundle) {
  seal(bundle.start);
  bundle.samples.forEach(seal);
  seal(bundle.stopTransition);
  seal(bundle.startTransition);
  let texts = serializeBundle(bundle);
  bundle.results.startReceipt = { sha256: sha(texts.start), selfHash: bundle.start.selfHash, bytes: Buffer.byteLength(texts.start) };
  bundle.results.sampleReceipts = bundle.samples.map((sample, index) => ({ index: sample.index, sha256: sha(texts.samples[index]), selfHash: sample.selfHash, bytes: Buffer.byteLength(texts.samples[index]) }));
  bundle.results.transitionReceipts = [bundle.stopTransition, bundle.startTransition].map((value, index) => ({ name: index === 0 ? 'transition-stop.json' : 'transition-start.json', sha256: sha(texts.transitions[index]), selfHash: value.selfHash, bytes: Buffer.byteLength(texts.transitions[index]) }));
  bundle.results.aggregate = aggregate(bundle.samples);
  for (let index = 0; index < 8; index += 1) {
    seal(bundle.results);
    texts = serializeBundle(bundle);
    bundle.results.receiptBytes = Buffer.byteLength(texts.results);
  }
  seal(bundle.results);
  return serializeBundle(bundle);
}

if (process.argv.includes('--self-test')) {
  if (spec.registeredAttacks.length !== 13 || new Set(spec.registeredAttacks).size !== 13) throw new Error('attack registry self-test failed');
  process.stdout.write('{"selfTest":"PASS","registeredAttacks":13,"mutations":0}\n');
  process.exit(0);
}

if (!existsSync(resolve(root, 'results.json')) || existsSync(auditPath)) throw new Error('audit root state invalid');
const texts = {
  start: readFileSync(resolve(root, 'start.json'), 'utf8'),
  samples: [],
  transitions: [readFileSync(resolve(root, 'transition-stop.json'), 'utf8'), readFileSync(resolve(root, 'transition-start.json'), 'utf8')],
  results: readFileSync(resolve(root, 'results.json'), 'utf8')
};
for (let index = 1; index <= spec.observationPolicy.phaseOrder.length * spec.observationPolicy.samplesPerPhase; index += 1) texts.samples.push(readFileSync(resolve(root, `sample-${String(index).padStart(3, '0')}.json`), 'utf8'));
const observed = {
  start: JSON.parse(texts.start),
  samples: texts.samples.map(JSON.parse),
  stopTransition: JSON.parse(texts.transitions[0]),
  startTransition: JSON.parse(texts.transitions[1]),
  results: JSON.parse(texts.results)
};
const expected = expectedGates(observed);
expected.EVIDENCE_BOUNDED_AND_SELF_HASHED = receiptIntegrity(observed, texts);
const aggregateReplay = canonical(observed.results.aggregate) === canonical(aggregate(observed.samples));

const scoped = execFileSync('/usr/bin/git', ['status', '--short', '--', ...spec.releasePaths], { cwd: repo, encoding: 'utf8' }).trim();
const [head, origin] = execFileSync('/usr/bin/git', ['rev-parse', 'HEAD', 'origin/main'], { cwd: repo, encoding: 'utf8' }).trim().split('\n');
const statusResult = command(spec.profile.colimaBinary, ['status', '--profile', spec.profile.name]);
const statusCombined = `${statusResult.stdout}\n${statusResult.stderr}`;
const inspectResult = command(spec.profile.dockerBinary, ['--host', spec.profile.dockerSocket, 'inspect', ...spec.restoreManifest.containers.map(value => value.id)]);
const psResult = command(spec.profile.dockerBinary, ['--host', spec.profile.dockerSocket, 'ps', '--no-trunc', '--format', '{{.ID}}']);
let liveContainers = [];
try { liveContainers = JSON.parse(inspectResult.stdout).map(item => ({ id: item.Id, name: String(item.Name || '').replace(/^\//, ''), image: item.Config?.Image || null, restartPolicy: item.HostConfig?.RestartPolicy?.Name || null, autoRemove: item.HostConfig?.AutoRemove ?? null, running: item.State?.Running === true })).sort((a, b) => a.id.localeCompare(b.id)); } catch {}
const liveState = {
  profile: {
    running: statusResult.exitCode === 0 && /colima is running/.test(statusCombined),
    arch: (statusCombined.match(/arch:\s*([^"\s]+)/) || [])[1] || null,
    runtime: (statusCombined.match(/runtime:\s*([^"\s]+)/) || [])[1] || null,
    mountType: (statusCombined.match(/mountType:\s*([^"\s]+)/) || [])[1] || null
  },
  docker: { socketReachable: inspectResult.exitCode === 0 && psResult.exitCode === 0, runningIds: psResult.stdout.trim().split('\n').filter(Boolean).sort(), containers: liveContainers },
  configs: Object.fromEntries(Object.entries(spec.restoreManifest.configFiles).map(([key, value]) => [key, { path: value.path, sha256: shaFile(value.path) }])),
  disks: Object.fromEntries(Object.entries(spec.restoreManifest.diskFiles).map(([key, value]) => { const state = statSync(value.path); return [key, { path: value.path, device: state.dev, inode: state.ino, logicalBytes: state.size }]; }))
};

const integrity = {
  RECEIPT_HASHES_AND_BOUNDS: expected.EVIDENCE_BOUNDED_AND_SELF_HASHED,
  AGGREGATE_REPLAY: aggregateReplay,
  GATE_PROJECTION: spec.requiredGates.filter(value => value !== 'INDEPENDENT_AUDIT_REPLAY').every(value => expected[value] === true && observed.results.gates[value] === expected[value]),
  PARENT_FILES: shaFile(resolve(repo, spec.parentEvidence.resultsPath)) === spec.parentEvidence.resultsSha256 && shaFile(resolve(repo, spec.parentEvidence.auditPath)) === spec.parentEvidence.auditSha256,
  RELEASE_REPLAY: scoped === '' && head === origin && head === observed.start.git.head,
  LIVE_RESTORATION: profileMatches(liveState) && exactContainers(liveState, true) && configAndDiskIdentity(liveState)
};

const attacks = [
  ['A01_SPEC_SHA_MUTATION', bundle => { bundle.results.spec.sha256 = '0'.repeat(64); }, 'result'],
  ['A02_PARENT_EVIDENCE_MUTATION', bundle => { bundle.start.parentEvidence.resultsSha256 = '0'.repeat(64); }],
  ['A03_PHASE_SAMPLE_REMOVAL', bundle => { bundle.samples.pop(); }],
  ['A04_PHASE_ORDER_MUTATION', bundle => { bundle.samples[0].phase = 'STOPPED'; }],
  ['A05_TIMING_MUTATION', bundle => { bundle.samples[1].state.capturedAt = new Date(Date.parse(bundle.samples[0].state.capturedAt) + 1).toISOString(); }],
  ['A06_STOP_CONFIRMATION_MUTATION', bundle => { bundle.stopTransition.confirmed = false; }],
  ['A07_CONTAINER_SET_MUTATION', bundle => { bundle.results.finalState.docker.containers.pop(); }, 'result'],
  ['A08_CONFIG_HASH_MUTATION', bundle => { bundle.samples[0].state.configs.colimaConfig.sha256 = '0'.repeat(64); }],
  ['A09_DISK_IDENTITY_MUTATION', bundle => { bundle.samples[0].state.disks.vmDisk.inode += 1; }],
  ['A10_AGGREGATE_MUTATION', bundle => { bundle.results.aggregate.phases.ACTIVE_BASELINE.hostLossBytes += 1; }, 'result'],
  ['A11_TRANSITION_RECEIPT_MUTATION', bundle => { bundle.startTransition.command.exitCode = 1; }],
  ['A12_SAMPLE_SELF_HASH_MUTATION', bundle => { bundle.samples[0].selfHash = '0'.repeat(64); }, 'none'],
  ['A13_RESULT_SELF_HASH_MUTATION', bundle => { bundle.results.selfHash = '0'.repeat(64); }, 'none']
];
const attackResults = attacks.map(([id, mutate, mode = 'bundle']) => {
  const bundle = structuredClone(observed);
  mutate(bundle);
  let mutatedTexts;
  if (mode === 'bundle') mutatedTexts = resealBundle(bundle);
  else if (mode === 'result') { seal(bundle.results); mutatedTexts = serializeBundle(bundle); }
  else mutatedTexts = serializeBundle(bundle);
  return { id, rejected: !validate(bundle, mutatedTexts) };
});
const attackIdsExact = canonical(attacks.map(value => value[0])) === canonical(spec.registeredAttacks);
const attacksPassed = attackIdsExact && attackResults.every(value => value.rejected);
const basePassed = validate(observed, texts);
const integrityPassed = Object.values(integrity).every(Boolean);
const finalVerdict = basePassed && integrityPassed && attacksPassed ? 'VALID_CONTROLLED_AB_EVIDENCE' : 'INVALID_CONTROLLED_AB_EVIDENCE';
const finalGates = { ...observed.results.gates, INDEPENDENT_AUDIT_REPLAY: integrityPassed && attacksPassed };
const failedGates = spec.requiredGates.filter(value => finalGates[value] !== true);
const audit = {
  schemaVersion: 'bfs.codex-host-disk-colima-ab-audit.v0.1',
  experimentId: spec.experimentId,
  auditedAt: new Date().toISOString(),
  finalVerdict,
  interpretation: observed.results.interpretation,
  integrity,
  attackIdsExact,
  attackResults,
  attacksPassed: attackResults.filter(value => value.rejected).length,
  attacksTotal: attackResults.length,
  finalGates,
  passedGates: spec.requiredGates.filter(value => finalGates[value] === true).length,
  totalGates: spec.requiredGates.length,
  failedGates,
  liveRestoration: liveState,
  selfHash: ''
};
seal(audit);
const auditText = `${JSON.stringify(audit, null, 2)}\n`;
if (Buffer.byteLength(auditText) > spec.byteCeilings.audit) throw new Error('audit byte ceiling');
const fd = openSync(auditPath, 'wx');
try { writeFileSync(fd, auditText); fsyncSync(fd); } finally { closeSync(fd); }
const summary = `${JSON.stringify({ experimentId: spec.experimentId, finalVerdict, interpretation: observed.results.interpretation, gates: `${audit.passedGates}/${audit.totalGates}`, attacks: `${audit.attacksPassed}/${audit.attacksTotal}`, restored: integrity.LIVE_RESTORATION, failedGates })}\n`;
if (Buffer.byteLength(summary) > spec.byteCeilings.stdout) throw new Error('stdout ceiling');
process.stdout.write(summary);
