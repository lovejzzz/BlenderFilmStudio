#!/usr/bin/env node

import { readFile, readdir, stat, statfs } from 'node:fs/promises';
import { resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { isDeepStrictEqual } from 'node:util';
import { measureOutput } from './lib/budgeted-process.mjs';
import {
  canonicalHash, resolveExistingRepositoryPath, sha256File,
  validSelfHash, writeDurableHashed,
} from './preflight-b62-phase0.mjs';

const repositoryRoot = resolve(fileURLToPath(new URL('../', import.meta.url)));

const CONTRACT_URI = 'specs/b62-phase0-asset-animatic-calibration.v0.1.json';
const CORRECTION_URI = 'specs/b62-phase0-c1-ffprobe-accounting-correction.v0.1.json';
const CORRECTION_2_URI = 'specs/b62-phase0-c2-fresh-clone-node-dependency-correction.v0.1.json';
const CORRECTION_3_URI = 'specs/b62-phase0-c3-blender52-multilayer-media-correction.v0.1.json';
const CORRECTION_4_URI = 'specs/b62-phase0-c4-dynamic-exr-setter-correction.v0.1.json';
const CORRECTION_5_URI = 'specs/b62-phase0-c5-v02-retry-binding.v0.1.json';
const CORRECTION_6_URI = 'specs/b62-phase0-c6-blender52-config-surface-diagnostic.v0.1.json';
const CORRECTION_7_URI = 'specs/b62-phase0-c7-eevee-engine-runtime-correction.v0.1.json';
const CORRECTION_8_URI = 'specs/b62-phase0-c8-runtime-config-promotion-and-generator-smoke.v0.1.json';
const CORRECTION_9_URI = 'specs/b62-phase0-c9-v03-formal-binding.v0.1.json';
const CORRECTION_10_URI = 'specs/b62-phase0-c10-library-locality-diagnostic.v0.1.json';
const CORRECTION_11_URI = 'specs/b62-phase0-c11-auditor-library-locality-correction.v0.1.json';
const CORRECTION_12_URI = 'specs/b62-phase0-c12-v04-formal-retry-binding.v0.1.json';
const EXPECTED = {
  preflightRoot: 'experiments/b62-phase0-preflight-v0-4',
  attemptRoot: 'experiments/b62-phase0-attempt-v0-4',
  formalRoot: 'experiments/b62-phase0-v0-4',
};
const PROCESS_IDS = [
  '01-GENERATOR', '02-ANIMATIC', '03-FFMPEG', '04-FFPROBE',
  '05-CALIBRATION-48', '06-CALIBRATION-144', '07-CALIBRATION-240', '08-BLENDER-AUDITOR',
];
const CALIBRATION = [['WIDE_APPROACH', 48], ['MEDIUM_CONTACT', 144], ['CLOSE_REFLECTION', 240]];
const NEUTRAL_COLOR = { display: 'sRGB - Display', view: 'ACES 2.0 - SDR 100 nits (Rec.709)', look: 'None', exposure: 0, gamma: 1 };

function parseArguments(argv) {
  const parsed = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--preflight-root') parsed.preflightRoot = argv[++index];
    else if (token === '--attempt-root') parsed.attemptRoot = argv[++index];
    else if (token === '--formal-root') parsed.formalRoot = argv[++index];
    else if (token === '--output') parsed.output = argv[++index];
    else throw new Error(`Unknown or incomplete argument: ${token}`);
  }
  for (const [key, expected] of Object.entries(EXPECTED)) if (parsed[key] !== expected) throw new Error(`B62 ${key} mismatch`);
  if (parsed.output !== `${parsed.formalRoot}/audit.json`) throw new Error('B62 audit output mismatch');
  return parsed;
}

function requireValue(condition, message) { if (!condition) throw new Error(message); }
async function json(uri) {
  const path = await resolveExistingRepositoryPath(uri, `B62 audit input ${uri}`);
  return { path, value: JSON.parse(await readFile(path, 'utf8')) };
}
async function identity(row, label) {
  const path = await resolveExistingRepositoryPath(row.uri, label);
  requireValue(await sha256File(path) === row.sha256 && (await stat(path)).size === row.bytes, `${label} identity mismatch`);
  return path;
}

async function verifyProcess(parsed, id) {
  const record = await json(`${parsed.attemptRoot}/processes/${id}.json`);
  requireValue(record.value.id === id && record.value.exitCode === 0 && record.value.signal === null
    && record.value.limitReason === null && record.value.terminationRequested === false, `${id} process failed or was terminated`);
  requireValue(record.value.logs.stdout.truncated === false && record.value.logs.stderr.truncated === false, `${id} log truncated`);
  for (const stream of ['stdout', 'stderr']) {
    const log = record.value.logs[stream];
    const path = await resolveExistingRepositoryPath(log.uri, `${id} ${stream}`);
    requireValue((await stat(path)).size === log.capturedBytes && await sha256File(path) === log.sha256
      && record.value[stream].bytes === log.bytes && record.value[stream].sha256 === log.streamSha256, `${id} ${stream} log binding mismatch`);
  }
  requireValue(Number.isFinite(record.value.elapsedSeconds) && record.value.elapsedSeconds > 0
    && Number.isFinite(record.value.timing.maximumResidentSetSizeBytes) && record.value.timing.maximumResidentSetSizeBytes > 0, `${id} resource metrics absent`);
  return record.value;
}

function makeReceiptProbe() {
  const body = { schemaVersion: 'bfs.b62Phase0ReceiptProbe.v0.1', status: 'PROSPECTIVE', verdict: 'B62_PHASE0_ASSET_ANIMATIC_AND_CALIBRATION_ADMITTED' };
  return { ...body, receiptHash: canonicalHash(body) };
}

function validateObservation(observation) {
  requireValue(observation.upstreamExact, 'upstream receipt drift');
  requireValue(observation.preregistrationPushed, 'preregistration ancestry drift');
  requireValue(observation.assetIdentityExact, 'asset identity drift');
  requireValue(observation.assetSafe, 'forbidden asset behavior');
  requireValue(observation.requiredBonesExact, 'required bone missing');
  requireValue(observation.shotContractExact, 'shot range or lens drift');
  requireValue(observation.contactDistanceM <= 0.02, 'contact distance over limit');
  requireValue(observation.transitionCausal, 'core transition precedes contact');
  requireValue(observation.warmHeld, 'warm state reset');
  requireValue(observation.animaticFrameCount === 288 && observation.animaticRosterExact, 'animatic roster drift');
  requireValue(observation.videoFps === '24/1' && observation.videoFrameCount === 288 && Math.abs(observation.videoDurationSeconds - 12) < 1e-6, 'video metadata drift');
  requireValue(observation.cyclesSettingsExact, 'Cycles settings drift');
  requireValue(observation.exrStorageAndDimensionsExact, 'EXR storage drift');
  requireValue(observation.pixelsFiniteDynamic, 'nonfinite or empty pixels');
  requireValue(observation.outputRosterExact, 'output roster substitution');
  requireValue(validSelfHash(observation.receiptProbe, 'receiptHash'), 'receipt self-hash mutation');
  return true;
}

function runNegativeControls(observation, expectedIds) {
  const attacks = [
    ['N01_UPSTREAM_RECEIPT_HASH_DRIFT', row => { row.upstreamExact = false; }],
    ['N02_UNPUSHED_PREREGISTRATION_COMMIT', row => { row.preregistrationPushed = false; }],
    ['N03_ACTOR_IDENTITY_HASH_DRIFT', row => { row.assetIdentityExact = false; }],
    ['N04_FORBIDDEN_DRIVER_OR_SCRIPT_IN_ASSET', row => { row.assetSafe = false; }],
    ['N05_REQUIRED_BONE_MISSING', row => { row.requiredBonesExact = false; }],
    ['N06_SHOT_FRAME_RANGE_OR_LENS_DRIFT', row => { row.shotContractExact = false; }],
    ['N07_RIGHT_HAND_CONTACT_DISTANCE_OVER_LIMIT', row => { row.contactDistanceM = 0.020001; }],
    ['N08_CORE_TRANSITION_PRECEDES_CONTACT', row => { row.transitionCausal = false; }],
    ['N09_WARM_STATE_RESETS_IN_CLOSE_SHOT', row => { row.warmHeld = false; }],
    ['N10_ANIMATIC_FRAME_MISSING_OR_EXTRA', row => { row.animaticFrameCount = 287; }],
    ['N11_ANIMATIC_VIDEO_DURATION_OR_FPS_DRIFT', row => { row.videoFps = '25/1'; }],
    ['N12_CYCLES_SAMPLE_OR_SEED_DRIFT', row => { row.cyclesSettingsExact = false; }],
    ['N13_EXR_FORMAT_OR_DIMENSION_DRIFT', row => { row.exrStorageAndDimensionsExact = false; }],
    ['N14_NONFINITE_OR_EMPTY_COMBINED_PIXELS', row => { row.pixelsFiniteDynamic = false; }],
    ['N15_OUTPUT_ROSTER_SUBSTITUTION', row => { row.outputRosterExact = false; }],
    ['N16_FINAL_RECEIPT_HASH_MUTATION', row => { row.receiptProbe.receiptHash = '0'.repeat(64); }],
  ];
  requireValue(isDeepStrictEqual(attacks.map(row => row[0]), expectedIds), 'B62 negative-control roster drift');
  return attacks.map(([id, mutate]) => {
    const copy = structuredClone(observation); mutate(copy);
    try { validateObservation(copy); return { id, pass: false, rejection: null }; }
    catch (error) { return { id, pass: true, rejection: error.message }; }
  });
}

async function expectedFormalRoster(parsed) {
  const expected = [
    `${parsed.formalRoot}/formal-start.json`,
    `${parsed.formalRoot}/reports/generation-report.json`,
    `${parsed.formalRoot}/reports/video-metadata.json`,
    `${parsed.formalRoot}/reports/blender-audit.json`,
    `${parsed.formalRoot}/scene/B62_PHASE0_MASTER.blend`,
    `${parsed.formalRoot}/motion/B62_GUARDIAN_PERFORMANCE.blend`,
    ...['CHAR_B62_GUARDIAN', 'SET_B62_OBSERVATORY', 'PROP_B62_CONSOLE_CORE'].map(name => `${parsed.formalRoot}/assets/${name}.blend`),
    ...Array.from({ length: 288 }, (_, index) => `${parsed.formalRoot}/animatic/frame-${String(index + 1).padStart(4, '0')}.png`),
    `${parsed.formalRoot}/animatic/animatic-render-report.json`,
    `${parsed.formalRoot}/animatic/B62_PHASE0_ANIMATIC.mp4`,
    ...CALIBRATION.flatMap(([shot, frame]) => ['exr', 'png', 'pixel.json'].map(extension => `${parsed.formalRoot}/calibration/${shot}-${String(frame).padStart(4, '0')}.${extension}`)),
  ].sort();
  const root = resolve(repositoryRoot, parsed.formalRoot);
  const actual = [];
  async function walk(directory) {
    for (const entry of await readdir(directory, { withFileTypes: true })) {
      const path = resolve(directory, entry.name);
      requireValue(!entry.isSymbolicLink(), 'B62 formal output contains a symlink');
      if (entry.isDirectory()) await walk(path);
      else if (entry.isFile()) actual.push(path.slice(repositoryRoot.length + 1));
      else throw new Error('B62 formal output contains a special file');
    }
  }
  await walk(root);
  return { expected, actual: actual.sort(), exact: isDeepStrictEqual(actual.sort(), expected) };
}

export async function auditB62(argv) {
  const parsed = parseArguments(argv);
  const contractRecord = await json(CONTRACT_URI); const contract = contractRecord.value;
  const correctionRecord = await json(CORRECTION_URI); const correction = correctionRecord.value;
  const correction2Record = await json(CORRECTION_2_URI); const correction2 = correction2Record.value;
  const correction3Record = await json(CORRECTION_3_URI); const correction3 = correction3Record.value;
  const correction4Record = await json(CORRECTION_4_URI); const correction4 = correction4Record.value;
  const correction5Record = await json(CORRECTION_5_URI); const correction5 = correction5Record.value;
  const correction6Record = await json(CORRECTION_6_URI); const correction6 = correction6Record.value;
  const correction7Record = await json(CORRECTION_7_URI); const correction7 = correction7Record.value;
  const correction8Record = await json(CORRECTION_8_URI); const correction8 = correction8Record.value;
  const correction9Record = await json(CORRECTION_9_URI); const correction9 = correction9Record.value;
  const correction10Record = await json(CORRECTION_10_URI); const correction10 = correction10Record.value;
  const correction11Record = await json(CORRECTION_11_URI); const correction11 = correction11Record.value;
  const correction12Record = await json(CORRECTION_12_URI); const correction12 = correction12Record.value;
  const preflight = await json(`${parsed.preflightRoot}/preflight.json`);
  requireValue(validSelfHash(preflight.value, 'preflightHash') && preflight.value.status === 'ACCEPTED', 'B62 preflight invalid');
  requireValue(preflight.value.contract.sha256 === await sha256File(contractRecord.path)
    && preflight.value.correction.sha256 === await sha256File(correctionRecord.path)
    && preflight.value.correction2.sha256 === await sha256File(correction2Record.path)
    && preflight.value.correction3.sha256 === await sha256File(correction3Record.path)
    && preflight.value.correction4.sha256 === await sha256File(correction4Record.path)
    && preflight.value.correction5.sha256 === await sha256File(correction5Record.path)
    && preflight.value.correction6.sha256 === await sha256File(correction6Record.path)
    && preflight.value.correction7.sha256 === await sha256File(correction7Record.path)
    && preflight.value.correction8.sha256 === await sha256File(correction8Record.path)
    && preflight.value.correction9.sha256 === await sha256File(correction9Record.path)
    && preflight.value.correction10.sha256 === await sha256File(correction10Record.path)
    && preflight.value.correction11.sha256 === await sha256File(correction11Record.path)
    && preflight.value.correction12.sha256 === await sha256File(correction12Record.path)
    && correction.correction.ffprobeMetadataProcesses === 1 && correction2.statusBeforeRetry === 'PREREGISTERED'
    && correction3.statusBeforeDiagnostic === 'PREREGISTERED' && correction4.statusBeforeDiagnostic === 'PREREGISTERED'
    && correction5.statusBeforeProductionToolChange === 'PREREGISTERED' && correction6.statusBeforeDiagnostic === 'PREREGISTERED'
    && correction7.statusBeforeDiagnostic === 'PREREGISTERED' && correction8.statusBeforeProductionToolChange === 'PREREGISTERED'
    && correction9.statusBeforeFormalToolChange === 'PREREGISTERED' && correction10.statusBeforeDiagnostic === 'PREREGISTERED'
    && correction11.statusBeforeAuditorChange === 'PREREGISTERED' && correction12.statusBeforeFormalToolChange === 'PREREGISTERED', 'B62 contract/correction binding mismatch');
  const generation = await json(`${parsed.formalRoot}/reports/generation-report.json`);
  requireValue(validSelfHash(generation.value, 'reportHash') && generation.value.status === 'PASS'
    && isDeepStrictEqual(generation.value.color, NEUTRAL_COLOR), 'B62 generation report invalid');
  const generationFiles = [
    [generation.value.files.master, `${parsed.formalRoot}/scene/B62_PHASE0_MASTER.blend`],
    [generation.value.files.motion, `${parsed.formalRoot}/motion/B62_GUARDIAN_PERFORMANCE.blend`],
    ...Object.entries(generation.value.files.assets).map(([id, row]) => [row, `${parsed.formalRoot}/assets/${id}.blend`]),
  ];
  for (const [row, uri] of generationFiles) {
    const path = await resolveExistingRepositoryPath(uri, `B62 generated file ${uri}`);
    requireValue(await sha256File(path) === row.sha256, `B62 generated file hash mismatch: ${uri}`);
  }
  const animatic = await json(`${parsed.formalRoot}/animatic/animatic-render-report.json`);
  requireValue(validSelfHash(animatic.value, 'reportHash') && animatic.value.status === 'PASS' && animatic.value.frames.length === 288, 'B62 animatic report invalid');
  const animaticSettingsExact = animatic.value.settings.engine === 'BLENDER_EEVEE'
    && isDeepStrictEqual(animatic.value.settings.resolution, [640, 360]) && animatic.value.settings.samples === 16
    && animatic.value.settings.format === 'PNG' && animatic.value.settings.fps === 24
    && isDeepStrictEqual(animatic.value.settings.color, NEUTRAL_COLOR);
  requireValue(animaticSettingsExact, 'B62 animatic settings drift');
  const expectedFrames = Array.from({ length: 288 }, (_, index) => index + 1);
  requireValue(isDeepStrictEqual(animatic.value.frames.map(row => row.frame), expectedFrames), 'B62 animatic frame indices drift');
  for (const row of animatic.value.frames) await identity(row, `B62 animatic frame ${row.frame}`);
  const video = await json(`${parsed.formalRoot}/reports/video-metadata.json`);
  requireValue(validSelfHash(video.value, 'metadataHash') && video.value.status === 'PASS', 'B62 video metadata invalid');
  await identity(video.value.video, 'B62 animatic video');
  const streams = video.value.probe.streams ?? [];
  requireValue(streams.length === 1 && streams[0].codec_type === 'video', 'B62 video stream roster drift');

  const calibration = [];
  for (const [shot, frame] of CALIBRATION) {
    const report = await json(`${parsed.formalRoot}/calibration/${shot}-${String(frame).padStart(4, '0')}.pixel.json`);
    requireValue(validSelfHash(report.value, 'reportHash') && report.value.status === 'PASS' && report.value.shot === shot && report.value.frame === frame, `B62 calibration report invalid: ${shot}`);
    await identity(report.value.exr, `${shot} EXR`); await identity(report.value.png, `${shot} PNG`);
    calibration.push(report.value);
  }
  const blenderAudit = await json(`${parsed.formalRoot}/reports/blender-audit.json`);
  requireValue(validSelfHash(blenderAudit.value, 'auditHash') && blenderAudit.value.status === 'PASS'
    && Object.values(blenderAudit.value.checks).every(Boolean), 'B62 independent Blender audit invalid');
  const localityExact = blenderAudit.value.masterLocality.libraries.length === 0 && blenderAudit.value.masterLocality.linkedIds.length === 0
    && blenderAudit.value.assetLibraries.length === 3 && blenderAudit.value.assetLibraries.every(row => row.findings.length === 0
      && row.locality.appendedIds.length > 0 && row.locality.appendedIds.every(item => item.library === null)
      && row.locality.sourceDescriptors.length === 1 && row.locality.sourceDescriptors[0].isMissing === false
      && row.locality.sourceDescriptors[0].filepath === resolve(repositoryRoot, parsed.formalRoot, 'assets', `${row.assetId}.blend`)
      && row.locality.descriptorRemovalErrors.length === 0 && row.locality.afterDescriptorRemoval.every(item => item.present && item.library === null)
      && Object.values(row.locality.cleanup).every(Boolean));
  requireValue(localityExact, 'B62 independent Blender locality evidence invalid');

  const processes = [];
  for (const id of PROCESS_IDS) processes.push(await verifyProcess(parsed, id));
  const processRoster = (await readdir(resolve(repositoryRoot, parsed.attemptRoot, 'processes'))).sort();
  requireValue(isDeepStrictEqual(processRoster, PROCESS_IDS.map(id => `${id}.json`).sort()), 'B62 process roster drift before Node auditor');
  const roster = await expectedFormalRoster(parsed);
  const formalMeasure = await measureOutput(resolve(repositoryRoot, parsed.formalRoot));
  const attemptMeasure = await measureOutput(resolve(repositoryRoot, parsed.attemptRoot));
  const filesystem = await statfs(repositoryRoot, { bigint: true });

  const state = blenderAudit.value.coreState;
  const contact = state.find(row => row.frame === 144);
  const stream = streams[0];
  const cyclesSettingsExact = calibration.every(row => row.settings.engine === 'CYCLES' && row.settings.device === 'CPU'
    && isDeepStrictEqual(row.settings.resolution, [1920, 1080]) && row.settings.samples === 64 && row.settings.denoise === true
    && row.settings.seed === 62001 && row.settings.animatedSeed === false && row.settings.mediaType === 'MULTI_LAYER_IMAGE' && row.settings.format === 'OPEN_EXR_MULTILAYER'
    && row.settings.pixelType === 'HALF' && row.settings.compression === 'ZIP' && isDeepStrictEqual(row.settings.color, NEUTRAL_COLOR));
  const independentCalibration = blenderAudit.value.calibration;
  const exrStorageAndDimensionsExact = independentCalibration.every(row => row.decoded.width === 1920 && row.decoded.height === 1080
    && row.decoded.pixelFormat === 'half' && String(row.decoded.compression).toLowerCase() === 'zip' && row.pngDimensionsExact && row.decodedMatchesReport);
  const pixelsFiniteDynamic = independentCalibration.every(row => row.decoded.nonFiniteCount === 0 && row.decoded.rgbDynamicRange > 1e-6);
  const shotContractExact = blenderAudit.value.checks.masterTimelineExact && blenderAudit.value.checks.markerCameraLensExact && blenderAudit.value.checks.cameraTransformsAnimatedExact;
  const observation = {
    upstreamExact: preflight.value.upstream.length === 3,
    preregistrationPushed: preflight.value.checks.every(row => row.pass) && /^[0-9a-f]{40}$/.test(preflight.value.toolFreezeCommit),
    assetIdentityExact: blenderAudit.value.checks.assetIdentityAndTopologyExact,
    assetSafe: blenderAudit.value.checks.assetLibrariesSafe && blenderAudit.value.checks.masterTextBlocksZero && blenderAudit.value.checks.masterDriversZero && blenderAudit.value.checks.masterExternalLibrariesZero && localityExact,
    requiredBonesExact: blenderAudit.value.checks.requiredBonesExact,
    shotContractExact,
    contactDistanceM: contact.contactDistanceM,
    transitionCausal: blenderAudit.value.checks.coreCausalStateExact && state.find(row => row.frame === 138).activation === 0 && state.find(row => row.frame === 143).activation === 0 && contact.activation === 0.5,
    warmHeld: blenderAudit.value.checks.warmLightMonotonicAndHeld && state.find(row => row.frame === 288).activation === 1,
    animaticFrameCount: animatic.value.frames.length,
    animaticRosterExact: blenderAudit.value.checks.animaticRosterExact && blenderAudit.value.checks.animaticPngDimensionsExact && animaticSettingsExact,
    videoFps: stream.avg_frame_rate,
    videoFrameCount: Number(stream.nb_read_frames),
    videoDurationSeconds: Number(stream.duration),
    cyclesSettingsExact,
    exrStorageAndDimensionsExact,
    pixelsFiniteDynamic,
    outputRosterExact: roster.exact,
    receiptProbe: makeReceiptProbe(),
  };
  validateObservation(observation);
  const attacks = runNegativeControls(observation, contract.negativeControls);
  requireValue(attacks.every(row => row.pass), 'B62 negative control failure');

  const processByKind = Object.groupBy(processes, row => row.kind);
  const resourceMetricsRecorded = processes.every(row => row.elapsedSeconds > 0 && row.timing.maximumResidentSetSizeBytes > 0
    && Number.isFinite(row.timing.userSeconds) && Number.isFinite(row.timing.systemSeconds));
  const declaredOperationRows = [generation.value.operations, animatic.value.operations, ...calibration.map(row => row.operations), blenderAudit.value.operations];
  const zeroExternalCalls = declaredOperationRows.every(row => row.modelCalls === 0 && row.networkCalls === 0 && row.dockerProcesses === 0);
  const budgetPass = formalMeasure.symlinkCount === 0 && attemptMeasure.symlinkCount === 0
    && formalMeasure.bytes + attemptMeasure.bytes <= contract.processBudget.projectedWriteBytes
    && BigInt(filesystem.bavail) * BigInt(filesystem.bsize) >= BigInt(contract.processBudget.minimumFreeReserveBytes)
    && processByKind.BLENDER_GENERATOR?.length === 1 && processByKind.BLENDER_ANIMATIC?.length === 1
    && processByKind.BLENDER_CALIBRATION?.length === 3 && processByKind.BLENDER_INDEPENDENT_AUDIT?.length === 1
    && processByKind.FFMPEG_ENCODING?.length === 1 && processByKind.FFPROBE_METADATA?.length === 1;
  const gateTruth = {
    G01_PREREGISTRATION_COMMIT_PUSHED_BEFORE_TOOLS_AND_OUTPUT_ROOTS: observation.preregistrationPushed,
    G02_B58_B60_B61_UPSTREAM_RECEIPTS_EXACT: observation.upstreamExact,
    G03_ZERO_BLENDER_PREFLIGHT_AND_CAPACITY_RESERVE_PASS: preflight.value.operations.blenderStarts === 0 && preflight.value.checks.every(row => row.pass),
    G04_ORIGINAL_ASSET_LIBRARIES_AND_MASTER_BLEND_COMPLETE: generationFiles.length === 5,
    G05_ASSET_SAFETY_AND_IDENTITY_MANIFEST_EXACT: observation.assetIdentityExact && observation.assetSafe,
    G06_MASTER_TIMELINE_288_FRAMES_24FPS_AND_THREE_SHOT_MARKERS_EXACT: blenderAudit.value.checks.masterTimelineExact && blenderAudit.value.checks.markerCameraLensExact,
    G07_CAMERA_LENSES_AND_ANIMATED_TRANSFORMS_MATCH_SHOT_CONTRACT: shotContractExact,
    G08_GUARDIAN_RIG_BONES_MATERIALS_AND_VISIBLE_SYSTEMS_COMPLETE: observation.requiredBonesExact && blenderAudit.value.checks.requiredObjectsPresent && blenderAudit.value.checks.requiredMaterialsPresent,
    G09_RIGHT_HAND_CONTACT_AND_CORE_STATE_CAUSAL_ORDER_PASS: observation.contactDistanceM <= 0.02 && observation.transitionCausal,
    G10_COLD_TO_WARM_LIGHT_AND_SHARED_STATE_CONTINUITY_PASS: observation.warmHeld,
    G11_ANIMATIC_288_FRAME_ROSTER_AND_VIDEO_METADATA_EXACT: observation.animaticFrameCount === 288 && observation.animaticRosterExact && observation.videoFps === '24/1' && observation.videoFrameCount === 288 && Math.abs(observation.videoDurationSeconds - 12) < 1e-6,
    G12_THREE_CYCLES_CALIBRATION_EXR_AND_REVIEW_PNG_PAIRS_COMPLETE: calibration.length === 3 && blenderAudit.value.checks.calibrationTriplesExact,
    G13_CALIBRATION_EXR_FORMAT_COLOR_FINITE_DYNAMIC_AND_NONEMPTY_PASS: observation.exrStorageAndDimensionsExact && observation.pixelsFiniteDynamic,
    G14_PROCESS_WALL_CPU_MEMORY_BYTES_AND_COSTS_RECORDED: resourceMetricsRecorded,
    G15_TIMEOUT_DISK_LOG_AND_OUTPUT_ROSTER_BOUNDS_PASS: budgetPass && observation.outputRosterExact,
    G16_INDEPENDENT_BLENDER_REOPEN_AUDIT_MATCHES_REPORTS: Object.values(blenderAudit.value.checks).every(Boolean),
    G17_SIXTEEN_NEGATIVE_CONTROL_MUTATIONS_REJECTED: attacks.length === 16 && attacks.every(row => row.pass),
    G18_FINAL_RECEIPT_SELF_HASH_AND_ZERO_MODEL_NETWORK_DOCKER: validSelfHash(observation.receiptProbe, 'receiptHash') && zeroExternalCalls,
  };
  const gates = contract.acceptanceGates.map(id => ({ id, pass: gateTruth[id] === true }));
  requireValue(gates.every(row => row.pass), `B62 gates failed: ${gates.filter(row => !row.pass).map(row => row.id).join(', ')}`);
  const calibrationRenderSeconds = calibration.map(row => row.renderSeconds);
  const costs = {
    processWallSecondsTotalBeforeNodeAudit: processes.reduce((sum, row) => sum + row.elapsedSeconds, 0),
    calibrationRenderSeconds: calibrationRenderSeconds.reduce((sum, value) => sum + value, 0),
    calibrationMeanSecondsPerFrame: calibrationRenderSeconds.reduce((sum, value) => sum + value, 0) / calibrationRenderSeconds.length,
    mechanicalProjectionSecondsFor288Frames: (calibrationRenderSeconds.reduce((sum, value) => sum + value, 0) / calibrationRenderSeconds.length) * 288,
    animaticRenderSeconds: animatic.value.elapsedSeconds,
    bytesBeforeAudit: { formal: formalMeasure.bytes, attempt: attemptMeasure.bytes, total: formalMeasure.bytes + attemptMeasure.bytes },
    peakResidentSetSizeBytes: Math.max(...processes.map(row => row.timing.maximumResidentSetSizeBytes)),
    projectionBoundary: 'MECHANICAL_STILL_FRAME_PROJECTION_ONLY_NOT_A_MEASURED_SEQUENCE_COST',
  };
  const operations = {
    blenderStarts: 6, generatorBlenderStarts: 1, animaticBlenderStarts: 1, calibrationBlenderStarts: 3, independentAuditBlenderStarts: 1,
    renderCalls: 291, eeveeRenderCalls: 288, cyclesRenderCalls: 3,
    ffmpegProcesses: 1, ffprobeProcesses: 1, nodeAuditorProcesses: 1,
    modelCalls: 0, networkCalls: 0, dockerProcesses: 0,
  };
  const output = resolve(repositoryRoot, parsed.output);
  const record = await writeDurableHashed(output, {
    schemaVersion: 'bfs.b62Phase0Audit.v0.1', experimentId: contract.experimentId, status: 'PASS', verdict: contract.passVerdict,
    contract: { uri: CONTRACT_URI, sha256: await sha256File(contractRecord.path) },
    corrections: [
      { uri: CORRECTION_URI, sha256: await sha256File(correctionRecord.path) }, { uri: CORRECTION_2_URI, sha256: await sha256File(correction2Record.path) },
      { uri: CORRECTION_3_URI, sha256: await sha256File(correction3Record.path) }, { uri: CORRECTION_4_URI, sha256: await sha256File(correction4Record.path) },
      { uri: CORRECTION_5_URI, sha256: await sha256File(correction5Record.path) },
      { uri: CORRECTION_6_URI, sha256: await sha256File(correction6Record.path) }, { uri: CORRECTION_7_URI, sha256: await sha256File(correction7Record.path) },
      { uri: CORRECTION_8_URI, sha256: await sha256File(correction8Record.path) }, { uri: CORRECTION_9_URI, sha256: await sha256File(correction9Record.path) },
      { uri: CORRECTION_10_URI, sha256: await sha256File(correction10Record.path) }, { uri: CORRECTION_11_URI, sha256: await sha256File(correction11Record.path) },
      { uri: CORRECTION_12_URI, sha256: await sha256File(correction12Record.path) },
    ],
    preflight: { uri: `${parsed.preflightRoot}/preflight.json`, sha256: await sha256File(preflight.path), preflightHash: preflight.value.preflightHash },
    generation: { reportHash: generation.value.reportHash, assetIdentityHashes: Object.fromEntries(Object.entries(generation.value.manifests).map(([id, row]) => [id, row.identityHash])) },
    blenderAudit: { uri: `${parsed.formalRoot}/reports/blender-audit.json`, sha256: await sha256File(blenderAudit.path), auditHash: blenderAudit.value.auditHash },
    calibration: calibration.map(row => ({ shot: row.shot, frame: row.frame, reportHash: row.reportHash, decodedPixelSha256: row.decodedCombined.sha256 })),
    video: { metadataHash: video.value.metadataHash, fps: observation.videoFps, frames: observation.videoFrameCount, durationSeconds: observation.videoDurationSeconds },
    costs, gates, attacks, operations, claimBoundary: contract.claimBoundary,
  }, 'auditHash');
  process.stdout.write(`BFS_B62_PHASE0_AUDIT PASS ${gates.length}/${gates.length} attacks=${attacks.length}/${attacks.length} ${record.auditHash}\n`);
  return record;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  auditB62(process.argv.slice(2)).catch(error => { process.stderr.write(`BFS_B62_PHASE0_AUDIT_ERROR ${error.message}\n`); process.exitCode = 1; });
}
