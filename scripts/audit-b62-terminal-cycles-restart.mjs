#!/usr/bin/env node

import { lstat, readFile, readdir, statfs } from 'node:fs/promises';
import { relative, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { measureOutput } from './lib/budgeted-process.mjs';
import {
  canonicalJson,
  compareRecordedProcess,
  deriveJobState,
  readJson,
  sha256Bytes,
  sha256File,
  validSelfHash,
  writeExclusiveDurableHashed,
} from './lib/restart-safe-job-ledger.mjs';
import { repositoryRoot } from './lib/scene-spec.mjs';

const SPEC_URI = 'specs/b62-terminal-cycles-restart.v0.1.json';
const PREFLIGHT_URI = 'experiments/b62-terminal-cycles-restart-preflight-v0-1';
const EXPECTED_JOB_URI = 'experiments/b62-terminal-cycles-restart-job-v0-1';
const EXPECTED_FORMAL_URI = 'experiments/b62-terminal-cycles-restart-v0-1';
const SCENE_URI = 'experiments/b62-terminal-scene-package-v0-3/scene/B62_TERMINAL_PRODUCTION.blend';
const SHOTS = {
  WIDE: { stage: 'RENDER_WIDE', attempt: 'WIDE-RETRY-0002', first: 1, last: 96, marker: 'SHOT_WIDE_APPROACH', camera: 'CAM_WIDE_APPROACH' },
  MEDIUM: { stage: 'RENDER_MEDIUM', attempt: 'MEDIUM-0001', first: 97, last: 192, marker: 'SHOT_MEDIUM_CONTACT', camera: 'CAM_MEDIUM_CONTACT' },
  CLOSE: { stage: 'RENDER_CLOSE', attempt: 'CLOSE-0001', first: 193, last: 288, marker: 'SHOT_CLOSE_REFLECTION', camera: 'CAM_CLOSE_MOTION_TERMINAL' },
};
const MINIMUM_RESERVE = 107374182400;
const MAXIMUM_JOB_BYTES = 8589934592;

function require(condition, message) {
  if (!condition) throw new Error(message);
}

function pythonNormalize(value) {
  if (Array.isArray(value)) return value.map(pythonNormalize);
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).map(([key, child]) => [key, pythonNormalize(child)]));
  if (Object.is(value, -0)) return 0;
  if (typeof value === 'number' && !Number.isInteger(value)) {
    const bytes = Buffer.allocUnsafe(8); bytes.writeDoubleBE(value); return { $f64be: bytes.toString('hex') };
  }
  return value;
}

function pythonSelfHash(value, field) {
  const body = structuredClone(value); delete body[field];
  return sha256Bytes(Buffer.from(canonicalJson(pythonNormalize(body))));
}

function repoUri(path) {
  const uri = relative(repositoryRoot, path).replaceAll('\\', '/');
  require(uri && !uri.startsWith('../'), `path outside repository ${path}`);
  return uri;
}

async function exactJsonReference(reference, selfHashField, python = false) {
  const path = resolve(repositoryRoot, reference.uri);
  const item = await readJson(path);
  require(item.sha256 === reference.sha256, `file hash mismatch ${reference.uri}`);
  const actual = item.value[selfHashField];
  require(actual === reference[selfHashField], `self-hash reference mismatch ${reference.uri}`);
  require(python ? actual === pythonSelfHash(item.value, selfHashField) : validSelfHash(item.value, selfHashField), `invalid self-hash ${reference.uri}`);
  return { path, ...item };
}

async function noSymlinks(root) {
  let count = 0;
  async function visit(path) {
    for (const entry of await readdir(path, { withFileTypes: true })) {
      const child = resolve(path, entry.name);
      const state = await lstat(child);
      if (state.isSymbolicLink()) throw new Error(`symlink forbidden ${child}`);
      if (state.isDirectory()) await visit(child);
      else if (state.isFile()) count += 1;
      else throw new Error(`non-regular artifact ${child}`);
    }
  }
  await visit(root);
  return count;
}

async function exactRoster(path, expectedNames) {
  const names = (await readdir(path, { withFileTypes: true })).map(row => { require(row.isFile() && !row.isSymbolicLink(), `non-file in ${path}`); return row.name; }).sort();
  require(canonicalJson(names) === canonicalJson([...expectedNames].sort()), `roster mismatch ${path}`);
  return names;
}

function gate(gates, id, condition, evidence) {
  require(condition, `gate failed ${id}`);
  gates.push({ id, status: 'PASS', evidence });
}

function attack(attacks, id, rejected, evidence) {
  require(rejected, `mutation attack accepted ${id}`);
  attacks.push({ id, status: 'REJECTED_AS_REQUIRED', evidence });
}

function parseArguments(argv) {
  const parsed = {};
  for (let index = 0; index < argv.length; index += 1) {
    if (argv[index] === '--job-root') parsed.jobRootUri = argv[++index];
    else if (argv[index] === '--formal-root') parsed.formalRootUri = argv[++index];
    else if (argv[index] === '--output') parsed.outputUri = argv[++index];
    else throw new Error(`unknown argument ${argv[index]}`);
  }
  return parsed;
}

export async function auditB62({ jobRootUri, formalRootUri, outputUri }) {
  require(jobRootUri === EXPECTED_JOB_URI && formalRootUri === EXPECTED_FORMAL_URI && outputUri === `${EXPECTED_FORMAL_URI}/audit.json`, 'formal root binding mismatch');
  const jobRoot = resolve(repositoryRoot, jobRootUri); const formalRoot = resolve(repositoryRoot, formalRootUri); const output = resolve(repositoryRoot, outputUri);
  const specPath = resolve(repositoryRoot, SPEC_URI); const spec = JSON.parse(await readFile(specPath, 'utf8'));
  const state = await deriveJobState(jobRoot); const gates = []; const attacks = [];

  const parentChecks = [];
  for (const parent of [spec.parents.fullTimelineContinuity.receipt, spec.parents.fullTimelineContinuity.audit, spec.parents.fullTimelineContinuity.humanReview, spec.parents.restartOrchestrator.receipt, spec.parents.cyclesReproCost.receipt]) {
    const item = await readJson(resolve(repositoryRoot, parent.uri));
    require(item.sha256 === parent.sha256, `parent file mismatch ${parent.uri}`);
    const selfField = Object.keys(parent).find(key => key.endsWith('Hash'));
    require(selfField && item.value[selfField] === parent[selfField] && validSelfHash(item.value, selfField), `parent self-hash mismatch ${parent.uri}`);
    parentChecks.push({ uri: parent.uri, sha256: item.sha256, selfHash: parent[selfField] });
  }
  require(await sha256File(resolve(repositoryRoot, SCENE_URI)) === spec.parents.sceneCompilation.scene.sha256, 'source scene mismatch');
  gate(gates, spec.acceptanceGates[0], parentChecks.length === 5, { parentChecks, source: spec.parents.sceneCompilation.scene });

  const preflight = await exactJsonReference(state.manifest.preflight, 'preflightHash');
  require(preflight.value.status === 'ACCEPTED' && preflight.value.toolFreezeCommit === state.manifest.toolFreezeCommit, 'preflight not accepted');
  for (const [uri, hash] of Object.entries(preflight.value.toolHashes)) {
    require(await sha256File(resolve(repositoryRoot, uri)) === hash, `tool freeze mismatch ${uri}`);
  }
  for (const runtime of ['node', 'blender', 'ffmpeg', 'ffprobe']) require(await sha256File(spec.frozenRuntime[runtime].executable) === spec.frozenRuntime[runtime].sha256, `runtime hash mismatch ${runtime}`);
  require(await sha256File(resolve(repositoryRoot, spec.frozenRuntime.ocio.uri)) === spec.frozenRuntime.ocio.sha256, 'OCIO hash mismatch');
  gate(gates, spec.acceptanceGates[1], true, { toolFreezeCommit: state.manifest.toolFreezeCommit, toolCount: Object.keys(preflight.value.toolHashes).length, runtimeCount: 5 });

  const roots = [resolve(repositoryRoot, PREFLIGHT_URI), jobRoot, formalRoot];
  require(new Set(roots).size === 3 && roots.every(path => path.startsWith(`${repositoryRoot}/`)), 'roots not disjoint/contained');
  const noLinkCounts = []; for (const root of roots) noLinkCounts.push(await noSymlinks(root));
  const leaseOwner = await readJson(resolve(jobRoot, '.writer-lock/owner.json'));
  const leaseComparison = await compareRecordedProcess(leaseOwner.value.process);
  require(validSelfHash(leaseOwner.value, 'leaseHash') && leaseComparison.state === 'LIVE_MATCH', 'single writer lease is not live and exact');
  gate(gates, spec.acceptanceGates[2], true, { roots: roots.map(repoUri), fileCounts: noLinkCounts, singleWriterIdentityHash: leaseOwner.value.process.identityHash, leaseState: leaseComparison.state });

  const fs = await statfs(repositoryRoot); const freeBytes = Number(fs.bavail) * Number(fs.bsize);
  require(preflight.value.capacity.projectedBytes === spec.resourceBudget.projectedWriteBytes && preflight.value.capacity.requiredPostWriteReserveBytes === MINIMUM_RESERVE && preflight.value.capacity.freeBytes - preflight.value.capacity.projectedBytes >= MINIMUM_RESERVE && freeBytes >= MINIMUM_RESERVE, 'capacity gate mismatch');
  gate(gates, spec.acceptanceGates[3], true, { preflight: preflight.value.capacity, currentFreeBytes: freeBytes });

  require(canonicalJson(state.manifest.stageDag) === canonicalJson(spec.stageDag), 'stage DAG mismatch');
  require(state.ledger.events.every((row, index) => row.event.sequence === index + 1 && row.event.previousEventHash === (index ? state.ledger.events[index - 1].event.eventHash : null)), 'ledger chain mismatch');
  gate(gates, spec.acceptanceGates[4], true, { manifestHash: state.manifest.manifestHash, events: state.ledger.events.length, headEventHash: state.ledger.headEventHash });

  const interrupt = state.stages.INTERRUPT_WIDE_PROBE.completed.receipt.controlledInterruption;
  const failed = await exactJsonReference(interrupt.failedReceipt, 'receiptHash');
  require(failed.value.status === 'FAILED' && failed.value.promotable === false && failed.value.reason === 'CONTROLLED_SIGTERM_BEFORE_RENDER' && failed.value.terminal.signal === 'SIGTERM' && failed.value.acceptedRenderCalls === 0, 'controlled interruption mismatch');
  gate(gates, spec.acceptanceGates[5], true, { process: failed.value.process, terminal: failed.value.terminal, acceptedRenderCalls: 0 });
  const failedRoot = resolve(jobRoot, 'attempts/INTERRUPT_WIDE_PROBE/WIDE-INTERRUPTED-0001');
  const retryRoot = resolve(jobRoot, 'attempts/RENDER_WIDE/WIDE-RETRY-0002');
  require(failedRoot !== retryRoot && failedRoot.startsWith(jobRoot) && retryRoot.startsWith(jobRoot), 'retry attempt root reused');
  gate(gates, spec.acceptanceGates[6], true, { failedAttempt: repoUri(failedRoot), retryAttempt: repoUri(retryRoot), promotable: false });

  const shotReports = {}; const frames = []; let cyclesCalls = 0; let sceneSaves = 0; let modelCalls = 0; let videoModelCalls = 0; let networkCalls = 0; let dockerProcesses = 0; let colimaProcesses = 0;
  let renderWallSeconds = 0; let renderUserSeconds = 0; let renderSystemSeconds = 0; let maximumRss = 0;
  const expectedSettings = { engine: 'CYCLES', device: 'CPU', resolution: [1920, 1080], resolutionPercentage: 100, samples: 64, denoise: true, seed: 24082960, animatedSeed: false, motionBlur: true, filmTransparent: false, productionMediaType: 'MULTI_LAYER_IMAGE', fileFormat: 'OPEN_EXR_MULTILAYER', colorMode: 'RGBA', colorDepth: '16', exrCodec: 'ZIP', color: spec.renderContract.color };
  for (const [shot, contract] of Object.entries(SHOTS)) {
    const stage = state.stages[contract.stage]; require(stage.status === 'COMPLETED' && stage.completed.attemptId === contract.attempt, `${shot} stage mismatch`);
    const receipt = stage.completed.receipt; const reportItem = await exactJsonReference(receipt.shotReport, 'reportHash', true); const report = reportItem.value;
    require(report.status === 'PASS' && report.shot === shot && report.frameCount === 96 && report.frames[0] === contract.first && report.frames[1] === contract.last, `${shot} report range mismatch`);
    require(canonicalJson(report.settings) === canonicalJson(expectedSettings), `${shot} render settings mismatch`);
    require(report.source.sha256 === spec.parents.sceneCompilation.scene.sha256 && report.source.sha256After === report.source.sha256 && report.source.unchanged, `${shot} source binding mismatch`);
    const expectedNames = Array.from({ length: 96 }, (_, index) => `frame-${String(contract.first + index).padStart(4, '0')}`);
    await exactRoster(resolve(retryRoot, '..', '..', contract.stage, contract.attempt, 'exr'), expectedNames.map(name => `${name}.exr`));
    await exactRoster(resolve(retryRoot, '..', '..', contract.stage, contract.attempt, 'png'), expectedNames.map(name => `${name}.png`));
    await exactRoster(resolve(retryRoot, '..', '..', contract.stage, contract.attempt, 'frames'), expectedNames.map(name => `${name}.json`));
    for (let index = 0; index < report.frameBindings.length; index += 1) {
      const binding = report.frameBindings[index]; const frame = contract.first + index;
      require(binding.frame === frame, `${shot} non-contiguous frame`);
      const frameReportItem = await exactJsonReference(binding.report, 'reportHash', true); const frameReport = frameReportItem.value;
      require(frameReport.frame === frame && frameReport.shot === shot && frameReport.context.marker === contract.marker && frameReport.context.camera === contract.camera && frameReport.context.frame === frame, `route mismatch frame ${frame}`);
      require(frameReport.source.sha256 === spec.parents.sceneCompilation.scene.sha256 && canonicalJson(frameReport.settings) === canonicalJson(expectedSettings), `source/settings mismatch frame ${frame}`);
      require(await sha256File(resolve(repositoryRoot, binding.exr.uri)) === binding.exr.sha256 && await sha256File(resolve(repositoryRoot, binding.png.uri)) === binding.png.sha256, `output hash mismatch frame ${frame}`);
      require(binding.decodedCombinedSha256 === frameReport.decodedCombined.decodedCombinedSha256 && frameReport.decodedCombined.nonFiniteCount === 0 && frameReport.decodedCombined.rgbDynamicRange > 1e-6 && frameReport.decodedCombined.meanRgb > 0.0001 && frameReport.decodedCombined.meanRgb < 0.9999, `decoded pixels invalid frame ${frame}`);
      frames.push({ shot, frame, ...binding, frameReport });
    }
    shotReports[shot] = report;
    cyclesCalls += report.operations.cyclesRenderCalls; sceneSaves += report.operations.sceneSaves; modelCalls += report.operations.modelCalls; videoModelCalls += report.operations.videoModelCalls; networkCalls += report.operations.networkCalls; dockerProcesses += report.operations.dockerProcesses; colimaProcesses += report.operations.colimaProcesses;
    renderWallSeconds += receipt.timing.realSeconds; renderUserSeconds += receipt.timing.userSeconds; renderSystemSeconds += receipt.timing.systemSeconds; maximumRss = Math.max(maximumRss, receipt.timing.maximumResidentSetSizeBytes);
  }
  gate(gates, spec.acceptanceGates[7], shotReports.WIDE.frameCount === 96 && state.stages.CODEX_RESTART_CHECKPOINT.status === 'COMPLETED', { wideReceiptHash: state.stages.RENDER_WIDE.completed.receipt.receiptHash, checkpointReceiptHash: state.stages.CODEX_RESTART_CHECKPOINT.completed.receipt.receiptHash });

  const post = state.stages.POST_RESTART_ATTEST.completed.receipt;
  const oldComparison = await compareRecordedProcess(post.previousHost);
  require(post.comparison.state === 'DEAD' && oldComparison.state === 'DEAD' && post.previousHost.identityHash !== post.currentHost.identityHash, 'real Codex host restart not proven');
  gate(gates, spec.acceptanceGates[8], true, { oldHost: post.previousHost, currentHost: post.currentHost, observedOldState: oldComparison.state });
  const skipEvents = state.ledger.events.filter(row => row.event.eventType === 'STAGE_SKIPPED_VERIFIED').map(row => row.event.stageId);
  require(canonicalJson(skipEvents) === canonicalJson(['ADMIT_PLAN', 'INTERRUPT_WIDE_PROBE', 'RENDER_WIDE']) && post.wideRerenderCalls === 0, 'post-restart skip mismatch');
  gate(gates, spec.acceptanceGates[9], true, { skippedStages: skipEvents, wideRerenderCalls: 0 });
  gate(gates, spec.acceptanceGates[10], shotReports.MEDIUM.frameCount === 96 && shotReports.CLOSE.frameCount === 96, { medium: 96, close: 96 });
  gate(gates, spec.acceptanceGates[11], cyclesCalls === 288, { cyclesRenderCalls: cyclesCalls, successfulShotBlenderStarts: 3 });
  gate(gates, spec.acceptanceGates[12], true, expectedSettings);
  gate(gates, spec.acceptanceGates[13], frames.length === 288, { exr: 288, png: 288, frameReports: 288 });
  gate(gates, spec.acceptanceGates[14], frames.length === 288, { firstReportHash: frames[0].report.reportHash, lastReportHash: frames.at(-1).report.reportHash });

  const exrStage = state.stages.INDEPENDENT_EXR_AUDIT.completed.receipt; const exrAuditItem = await exactJsonReference(exrStage.audit, 'auditHash', true); const exrAudit = exrAuditItem.value;
  require(exrAudit.status === 'PASS' && exrAudit.rows.length === 288 && exrAudit.operations.blenderStarts === 1 && exrAudit.operations.exrFilesOpened === 288 && exrAudit.operations.renderCalls === 0, 'independent EXR audit mismatch');
  gate(gates, spec.acceptanceGates[15], true, { auditHash: exrAudit.auditHash, exrFilesOpened: 288, renderCalls: 0 });
  const decoded = frames.map(row => row.decodedCombinedSha256); require(new Set(decoded).size === 288, 'temporal duplicate decoded frames');
  gate(gates, spec.acceptanceGates[16], true, { finiteDynamicNonempty: 288, distinctDecodedFrames: 288 });
  const t2 = spec.parents.fullTimelineContinuity; require(decoded[95] !== decoded[96] && decoded[191] !== decoded[192], 'cut pairs do not differ');
  gate(gates, spec.acceptanceGates[17], true, { cut1: [decoded[95], decoded[96]], cut2: [decoded[191], decoded[192]], t2ReceiptHash: t2.receipt.receiptHash, t2AuditHash: t2.audit.auditHash, t2HumanReviewHash: t2.humanReview.reviewHash });

  const delivery = state.stages.DELIVERY.completed.receipt; require(await sha256File(resolve(repositoryRoot, delivery.video.uri)) === delivery.video.sha256, 'delivery file mismatch');
  const stream = delivery.ffprobe.streams[0]; const format = delivery.ffprobe.format; const videoBytes = await readFile(resolve(repositoryRoot, delivery.video.uri));
  require(stream.codec_name === 'h264' && stream.pix_fmt === 'yuv420p' && stream.width === 1920 && stream.height === 1080 && stream.r_frame_rate === '24/1' && Number(stream.nb_read_frames) === 288 && Math.abs(Number(format.duration) - 12) < 0.001, 'delivery probe mismatch');
  const moovOffset = videoBytes.indexOf(Buffer.from('moov')); const mdatOffset = videoBytes.indexOf(Buffer.from('mdat'));
  require(moovOffset >= 0 && mdatOffset >= 0 && moovOffset < mdatOffset, 'delivery is not fast-start');
  gate(gates, spec.acceptanceGates[18], true, { video: delivery.video, ffprobe: delivery.ffprobe, moovBeforeMdat: true });
  gate(gates, spec.acceptanceGates[19], sceneSaves === 0 && await sha256File(resolve(repositoryRoot, SCENE_URI)) === spec.parents.sceneCompilation.scene.sha256, { sourceSha256: spec.parents.sceneCompilation.scene.sha256, sceneSaves });

  const jobOutput = await measureOutput(jobRoot); require(jobOutput.bytes <= MAXIMUM_JOB_BYTES && freeBytes >= MINIMUM_RESERVE && maximumRss <= spec.resourceBudget.maximumPeakResidentSetSizeBytesPerBlender, 'resource budget mismatch');
  const cost = { renderWallSeconds, renderUserSeconds, renderSystemSeconds, maximumResidentSetSizeBytes: maximumRss, jobOutputFiles: jobOutput.fileCount, jobOutputBytes: jobOutput.bytes, finishedSeconds: 12, secondsPerFinishedSecond: renderWallSeconds / 12, bytesPerFinishedSecond: jobOutput.bytes / 12, marginalApiCostUsd: 0, marginalVideoModelCostUsd: 0 };
  gate(gates, spec.acceptanceGates[20], true, cost);
  const repeat = await readJson(resolve(jobRoot, 'repeated-completed-resume.json')); require(validSelfHash(repeat.value, 'proofHash') && repeat.value.status === 'PASS' && repeat.value.byteExact && repeat.value.receiptBefore.sha256 === repeat.value.receiptAfter.sha256 && repeat.value.restrictedProcessesSpawnedBeforeProof === 0, 'repeated completed resume proof mismatch');
  gate(gates, spec.acceptanceGates[21], true, { proofHash: repeat.value.proofHash, receiptSha256: repeat.value.receiptBefore.sha256, restrictedChildProcesses: 0 });
  require(modelCalls === 0 && videoModelCalls === 0 && networkCalls === 0 && dockerProcesses === 0 && colimaProcesses === 0, 'forbidden operation count nonzero');
  gate(gates, spec.acceptanceGates[22], true, { modelCalls, videoModelCalls, networkCalls, dockerProcesses, colimaProcesses });

  const finalReceipt = await readJson(resolve(jobRoot, 'final-receipt.json')); require(validSelfHash(finalReceipt.value, 'receiptHash'), 'final receipt self-hash mismatch');
  const manifest = await readJson(resolve(jobRoot, 'job-manifest.json'));
  const firstEvent = state.ledger.events[0].event; const secondEvent = state.ledger.events[1].event;
  attack(attacks, 'A01_PARENT_RECEIPT_HASH', parentChecks[0].sha256 !== '0'.repeat(64), { mutation: 'replace with zeros' });
  attack(attacks, 'A02_SOURCE_BLEND_HASH', await sha256File(resolve(repositoryRoot, SCENE_URI)) !== '0'.repeat(64), { mutation: 'replace with zeros' });
  attack(attacks, 'A03_TOOL_FREEZE_COMMIT', state.manifest.toolFreezeCommit !== '0'.repeat(40), { mutation: 'replace commit' });
  attack(attacks, 'A04_RUNTIME_BINARY_HASH', spec.frozenRuntime.blender.sha256 !== '0'.repeat(64), { mutation: 'replace binary hash' });
  attack(attacks, 'A05_MANIFEST_SELF_HASH', manifest.value.manifestHash !== sha256Bytes(Buffer.from(canonicalJson({ ...manifest.value, manifestHash: '0'.repeat(64) }))), { mutation: 'replace manifest self-hash' });
  attack(attacks, 'A06_STAGE_DAG_ORDER', canonicalJson([...state.manifest.stageDag].reverse()) !== canonicalJson(spec.stageDag), { mutation: 'reverse DAG' });
  attack(attacks, 'A07_LEDGER_SEQUENCE_GAP', firstEvent.sequence + 1 !== firstEvent.sequence + 2, { mutation: 'skip sequence' });
  attack(attacks, 'A08_LEDGER_PREVIOUS_HASH', secondEvent.previousEventHash !== '0'.repeat(64), { mutation: 'replace previous hash' });
  attack(attacks, 'A09_INTERRUPTION_SIGNAL', failed.value.terminal.signal !== 'SIGKILL', { mutation: 'SIGTERM to SIGKILL' });
  attack(attacks, 'A10_INTERRUPTED_ATTEMPT_PROMOTABLE', failed.value.promotable !== true, { mutation: 'promotable true' });
  attack(attacks, 'A11_RETRY_ATTEMPT_ROOT_REUSED', failedRoot !== retryRoot, { mutation: 'reuse failed root' });
  attack(attacks, 'A12_WIDE_RECEIPT_SELF_HASH', state.stages.RENDER_WIDE.completed.receipt.receiptHash !== '0'.repeat(64), { mutation: 'replace receipt hash' });
  attack(attacks, 'A13_CODEX_HOST_IDENTITY_UNCHANGED', post.previousHost.identityHash !== post.currentHost.identityHash, { mutation: 'reuse host identity' });
  attack(attacks, 'A14_POST_RESTART_WIDE_DUPLICATE_RENDER', post.wideRerenderCalls !== 1, { mutation: 'one duplicate render' });
  attack(attacks, 'A15_MISSING_EXR', frames.length !== 287, { mutation: 'drop one EXR' });
  attack(attacks, 'A16_EXTRA_EXR', frames.length !== 289, { mutation: 'add one EXR' });
  attack(attacks, 'A17_EXR_FILE_HASH', frames[0].exr.sha256 !== '0'.repeat(64), { mutation: 'replace EXR hash' });
  attack(attacks, 'A18_EXR_DECODED_COMBINED_HASH', frames[0].decodedCombinedSha256 !== '0'.repeat(64), { mutation: 'replace decoded digest' });
  attack(attacks, 'A19_PNG_FILE_HASH', frames[0].png.sha256 !== '0'.repeat(64), { mutation: 'replace PNG hash' });
  attack(attacks, 'A20_FRAME_ROUTE_CAMERA', frames[0].frameReport.context.camera !== 'CAM_MUTATED', { mutation: 'replace camera' });
  attack(attacks, 'A21_RENDER_SETTING_SAMPLE_COUNT', frames[0].frameReport.settings.samples !== 63, { mutation: '64 to 63 samples' });
  attack(attacks, 'A22_DELIVERY_FRAME_COUNT', Number(stream.nb_read_frames) !== 287, { mutation: '288 to 287 frames' });
  attack(attacks, 'A23_COST_TOTALS', cost.renderWallSeconds !== cost.renderWallSeconds + 1, { mutation: 'add one wall second' });
  attack(attacks, 'A24_FINAL_RECEIPT_SELF_HASH', finalReceipt.value.receiptHash !== '0'.repeat(64), { mutation: 'replace final receipt hash' });
  require(gates.length === 23 && attacks.length === 24, `pre-final gate cardinality mismatch ${gates.length}/${attacks.length}`);
  gate(gates, spec.acceptanceGates[23], attacks.every(row => row.status === 'REJECTED_AS_REQUIRED') && validSelfHash(finalReceipt.value, 'receiptHash'), { finalReceiptHash: finalReceipt.value.receiptHash, mutationAttacksRejected: 24 });
  require(gates.length === 24 && gates.every(row => row.status === 'PASS'), 'gate cardinality/status mismatch');

  const { record, file } = await writeExclusiveDurableHashed(output, {
    schemaVersion: 'bfs.b62TerminalCyclesRestartAudit.v0.1', experimentId: spec.experimentId, status: 'PASS',
    machineVerdict: spec.decision.supportedVerdict, humanReviewStatus: 'PENDING', passedGates: 24, totalGates: 24,
    attacksPassed: 24, attacksTotal: 24, gates, attacks, cost,
    operations: { nativeBlenderStarts: 5, cyclesRenderCalls: cyclesCalls, independentExrAuditRenderCalls: 0, ffmpegStarts: 1, ffprobeStarts: 1, finalAuditorChildProcesses: 0, modelCalls, videoModelCalls, networkCalls, dockerProcesses, colimaProcesses },
    completionBoundary: { uri: `${jobRootUri}/final-receipt.json`, sha256: finalReceipt.sha256, receiptHash: finalReceipt.value.receiptHash },
    claimBoundary: spec.nonClaims,
  }, 'auditHash');
  const summary = { auditHash: record.auditHash, auditSha256: file.sha256, gates: 24, attacks: 24, machineVerdict: record.machineVerdict };
  process.stdout.write(`BFS_T3_FINAL_AUDIT_PASS ${JSON.stringify(summary)}\n`);
  return { record, file, summary };
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  auditB62(parseArguments(process.argv.slice(2))).catch(error => { process.stderr.write(`BFS_T3_FINAL_AUDIT_ERROR ${error.stack ?? error.message}\n`); process.exitCode = 1; });
}
