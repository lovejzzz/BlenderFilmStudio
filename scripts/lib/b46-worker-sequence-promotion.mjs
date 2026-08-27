import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { canonicalJson, repositoryRoot, sha256 } from './scene-spec.mjs';

export const B46_SPEC_URI = 'specs/codex-worker-sequence-promotion.v0.1.json';
export const B46_SPEC_PATH = resolve(repositoryRoot, B46_SPEC_URI);
export const B46_SPEC_SHA256 = '08f11141503e87bcb341ab9d82b15773c637a2dfdda0794e038f1620a0a76c58';
export const B46_PREREG_COMMIT = '259cf3071b8ccd3884ecb3154a2dcc99380dec7b';
export const B46_OCIO_SHA256 = '24ec81841048fc5db160a7bad882263246183385c5d49d0e86e11464917ead15';

export async function readB46Spec() {
  const bytes = await readFile(B46_SPEC_PATH);
  const digest = sha256(bytes);
  if (digest !== B46_SPEC_SHA256) throw new Error(`B46 spec SHA mismatch: ${digest}`);
  return JSON.parse(bytes);
}

export function hashB46Evidence(evidence) {
  const copy = structuredClone(evidence);
  for (const key of ['evidenceHash', 'analysis', 'attacks', 'attacksPassed', 'verdict', 'nonClaims']) delete copy[key];
  return sha256(Buffer.from(canonicalJson(copy)));
}

export function expectedB46AppliedSettings(spec, seed) {
  const value = spec.renderControl;
  return {
    engine:value.engine, device:value.device, resolution:[value.width,value.height,value.resolutionPercentage],
    samples:value.samples, seed, animatedSeed:value.animatedSeed, denoising:value.denoising,
    motionBlur:value.motionBlur, persistentData:value.persistentData, threadsMode:value.threadsMode,
    threads:value.threads, filmTransparent:value.filmTransparent, compositing:value.compositing, sequencer:value.sequencer,
  };
}

function expectedMilestones(frames) {
  return ['PROCESS_STARTED','SOURCE_VERIFIED','SCENE_CONFIGURED', ...frames.flatMap(() => ['FRAME_STARTED','FRAME_COMPLETED']), 'REPORT_WRITTEN'];
}

export function analyzeB46Evidence(evidence, spec, { requireAttacks = true } = {}) {
  const failures = [];
  const gate = (condition, code) => { if (!condition && !failures.includes(code)) failures.push(code); };
  gate(evidence?.schemaVersion === 'bfs.codexWorkerSequencePromotionEvidence.v0.1' && evidence?.experimentId === 'B46', 'EVIDENCE_SCHEMA');
  gate(evidence?.preregistration?.commit === B46_PREREG_COMMIT && evidence?.preregistration?.specSha256 === B46_SPEC_SHA256, 'PREREGISTRATION_IDENTITY');
  gate(canonicalJson(evidence?.parents) === canonicalJson(spec.parents), 'PARENT_IDENTITY');
  gate(evidence?.parentObservations?.length === 4 && evidence.parentObservations.every(item => item.match), 'PARENT_HASH');
  gate(evidence?.inputObservations?.length >= 16 && evidence.inputObservations.every(item => item.match), 'FROZEN_INPUT_HASH');
  gate(/^[a-f0-9]{40}$/.test(evidence?.toolFreezeCommit ?? '') && Object.values(evidence?.tools ?? {}).every(item => /^[a-f0-9]{64}$/.test(item?.sha256 ?? '')), 'TOOL_IDENTITY');
  gate(canonicalJson(evidence?.hostPixelDecoder) === canonicalJson(spec.hostPixelDecoder), 'DECODER_IDENTITY');
  gate(canonicalJson(evidence?.reviewCarrierControl) === canonicalJson(spec.reviewCarrier), 'REVIEW_ENCODER_IDENTITY');
  gate(canonicalJson(evidence?.image) === canonicalJson({id:spec.image.id,os:spec.image.os,architecture:spec.image.architecture,sizeBytes:spec.image.dockerReportedSizeBytes}), 'IMAGE_IDENTITY');
  let diskAccepted = false;
  try { diskAccepted = evidence?.diskAdmission?.status === 'ACCEPTED' && BigInt(evidence.diskAdmission.freeAfterProjectedBytes) >= BigInt(spec.diskAdmission.minimumReserveBytes); } catch {}
  gate(diskAccepted, 'DISK_ADMISSION');
  gate(canonicalJson(evidence?.securityBoundary) === canonicalJson(spec.containerContract), 'SECURITY_BOUNDARY');
  gate(canonicalJson(evidence?.renderControl) === canonicalJson(spec.renderControl), 'RENDER_CONTROL');
  gate(evidence?.shots?.length === spec.shots.length, 'SHOT_COUNT');

  for (const expectedShot of spec.shots) {
    const shot = evidence?.shots?.find(item => item.id === expectedShot.id);
    gate(shot?.runs?.length === expectedShot.inputs.length, `RUN_COUNT_${expectedShot.id}`);
    for (const expectedInput of expectedShot.inputs) {
      const run = shot?.runs?.find(item => item.id === expectedInput.id);
      gate(run?.source?.uri === expectedInput.blendUri && run?.source?.sha256 === expectedInput.blendSha256 && run?.source?.bytes === expectedInput.blendBytes, `SOURCE_IDENTITY_${expectedInput.id}`);
      gate(run?.exitCode === 0 && run?.timeoutTriggered === false && run?.completed === true, `RUN_COMPLETE_${expectedInput.id}`);
      const report = run?.report;
      gate(report?.source?.uri === `/repo/${expectedInput.blendUri}` && report?.source?.sha256 === expectedInput.blendSha256 && report?.source?.bytes === expectedInput.blendBytes, `REPORT_SOURCE_${expectedInput.id}`);
      gate(report?.bindings?.planHash === expectedShot.planHash && report?.bindings?.sceneSpecHash === expectedShot.sourceSceneCanonicalSha256 && report?.bindings?.structureHash === expectedShot.structureHash, `REPORT_PLAN_${expectedInput.id}`);
      gate(canonicalJson(report?.frames) === canonicalJson(expectedShot.frames), `FRAME_ORDER_${expectedInput.id}`);
      gate(Number.isInteger(report?.bindings?.shotSeed) && canonicalJson(report?.appliedSettings) === canonicalJson(expectedB46AppliedSettings(spec, report?.bindings?.shotSeed))
        && report?.renderOperatorCalls === expectedShot.frames.length && report?.savesFromSameRenderResult === expectedShot.frames.length * spec.renderControl.savesPerRenderResult, `RENDER_SETTINGS_${expectedInput.id}`);
      gate(canonicalJson(report?.saveSettings) === canonicalJson({
        exr:{mediaType:spec.renderControl.master.mediaType,fileFormat:spec.renderControl.master.format,colorMode:spec.renderControl.master.channels,colorDepth:spec.renderControl.master.colorDepth,codec:spec.renderControl.master.codec},
        png:{mediaType:spec.renderControl.review.mediaType,fileFormat:spec.renderControl.review.format,colorMode:spec.renderControl.review.channels,colorDepth:spec.renderControl.review.colorDepth},
      }), `SAVE_SETTINGS_${expectedInput.id}`);
      gate(report?.blender?.version === spec.image.blenderVersion && report?.blender?.buildHash === spec.image.blenderBuildHash && report?.blender?.buildPlatform === 'Linux'
        && report?.ocio?.sha256 === B46_OCIO_SHA256 && report?.ocio?.declaredEncoding === 'ACEScg', `RUNTIME_BINDING_${expectedInput.id}`);
      gate(run?.sequence?.frames?.length === expectedShot.frames.length && run?.sequence?.transitions?.length === expectedShot.frames.length - 1, `SEQUENCE_SHAPE_${expectedInput.id}`);
      for (const frame of expectedShot.frames) {
        const decoded = run?.sequence?.frames?.find(item => item.frame === frame);
        const artifact = run?.artifacts?.frames?.find(item => item.frame === frame);
        const reportFrame = report?.frameReports?.find(item => item.frame === frame);
        gate(decoded?.finite === true && decoded?.componentCount === spec.renderControl.width * spec.renderControl.height * 4
          && decoded?.pixelCount === spec.renderControl.width * spec.renderControl.height
          && canonicalJson(decoded?.metadata?.shape) === canonicalJson([spec.renderControl.height,spec.renderControl.width,4])
          && decoded?.metadata?.dtype === 'float32-le' && decoded?.metadata?.channelOrder === 'BGRA'
          && decoded?.input?.sha256 === artifact?.exr?.sha256 && decoded?.input?.sha256 === reportFrame?.artifacts?.exr?.sha256
          && artifact?.png?.valid === true && canonicalJson(artifact.png.dimensions) === canonicalJson([spec.renderControl.width,spec.renderControl.height])
          && artifact?.png?.sha256 === reportFrame?.artifacts?.png?.sha256, `FRAME_DECODE_${expectedInput.id}_${frame}`);
      }
      gate(canonicalJson(run?.milestones?.map(item => item.name)) === canonicalJson(expectedMilestones(expectedShot.frames)), `MILESTONES_${expectedInput.id}`);
      const probe = run?.review?.probe;
      gate(run?.review?.valid === true && probe?.codec_name === spec.reviewCarrier.requiredProbe.codec_name && probe?.width === spec.reviewCarrier.requiredProbe.width
        && probe?.height === spec.reviewCarrier.requiredProbe.height && probe?.pix_fmt === spec.reviewCarrier.requiredProbe.pix_fmt
        && probe?.r_frame_rate === spec.reviewCarrier.requiredProbe.r_frame_rate && probe?.nb_read_frames === spec.reviewCarrier.requiredProbe.nb_read_frames
        && probe?.audioStreams === spec.reviewCarrier.requiredProbe.audioStreams, `REVIEW_CARRIER_${expectedInput.id}`);
    }
    for (const framePair of shot?.pairComparison?.frames ?? []) gate(framePair.pixelExact === true && framePair.canonicalPixelSha256A === framePair.canonicalPixelSha256B, `FRAME_PAIR_${expectedShot.id}_${framePair.frame}`);
    gate(shot?.pairComparison?.frames?.length === expectedShot.frames.length, `FRAME_PAIR_COUNT_${expectedShot.id}`);
    for (const transition of shot?.pairComparison?.transitions ?? []) gate(transition.deltaExact === true && transition.canonicalTransitionSha256A === transition.canonicalTransitionSha256B, `TRANSITION_PAIR_${expectedShot.id}_${transition.fromFrame}_${transition.toFrame}`);
    gate(shot?.pairComparison?.transitions?.length === expectedShot.frames.length - 1 && shot?.pairComparison?.sequenceExact === true, `TRANSITION_PAIR_COUNT_${expectedShot.id}`);
    const changed = (shot?.runs ?? []).flatMap(run => run?.sequence?.transitions ?? []).map(item => item.changedComponentCount);
    gate(expectedShot.temporalRole === 'MOVING_CAMERA' ? changed.length === 14 && changed.every(value => value > 0) : changed.length === 14 && changed.every(value => value === 0), `TEMPORAL_ROLE_${expectedShot.id}`);
  }

  const fault = evidence?.faultAttempt;
  gate(fault?.id === spec.recovery.faultAttemptId && fault?.exitCode === spec.recovery.faultExitCode && fault?.timeoutTriggered === false
    && fault?.completedFrames === spec.recovery.requiredPartialFrames && fault?.reportExists === false && fault?.promotable === false, 'FAULT_ATTEMPT');
  const recovery = evidence?.recoveryAttempt;
  gate(recovery?.id === spec.recovery.recoveryAttemptId && recovery?.newContainer === true && recovery?.outputRootWasEmpty === true
    && recovery?.differentOutputRoot === true && recovery?.run?.completed === true, 'RECOVERY_ATTEMPT');
  gate(recovery?.matchesPrimary === true && recovery?.frameHashesExact === true && recovery?.transitionHashesExact === true, 'RECOVERY_MATCH');
  gate(evidence?.negativeControl?.id === spec.negativeControl.id && evidence?.negativeControl?.reason === spec.negativeControl.expectedReason
    && evidence?.negativeControl?.observedSha256 !== spec.negativeControl.declaredSha256 && evidence?.negativeControl?.containerLaunchCount === 0, 'NEGATIVE_PRE_CONTAINER');
  const operations = evidence?.runtimeOperationsExecuted ?? [];
  gate(Array.isArray(operations) && operations.filter(item => item.startsWith('DOCKER_RUN_')).length === spec.operationBoundary.dockerRuns
    && operations.filter(item => item.startsWith('HOST_EXR_ANALYSIS_')).length === spec.operationBoundary.hostExrAnalyses
    && operations.filter(item => item.startsWith('FFMPEG_REVIEW_')).length === spec.operationBoundary.reviewEncodes
    && operations[0] === 'DOCKER_IMAGE_INSPECT' && operations.at(-1) === 'DOCKER_RUNNING_CONTAINER_CHECK'
    && !operations.some(item => /BUILD|PULL|DOWNLOAD|MODEL|CODEX|VIDEO_API/.test(item)), 'OPERATION_BOUNDARY');
  gate(evidence?.cleanup?.experimentContainersRunningAfter === 0, 'CLEANUP_BOUNDARY');
  gate(Array.isArray(evidence?.errors) && evidence.errors.length === 0, 'RUN_ERRORS');
  if (requireAttacks) gate(evidence?.attacks?.length === spec.requiredAttacks.length && evidence.attacks.every(item => item.passed), 'ATTACKS');
  gate(evidence?.evidenceHash === hashB46Evidence(evidence), 'EVIDENCE_SELF_HASH');
  return {schemaVersion:'bfs.codexWorkerSequencePromotionAnalysis.v0.1',passed:failures.length===0,failures,decision:failures[0]??spec.acceptedVerdict};
}

export function runB46Attacks(evidence, spec) {
  const tabletop = value => value.shots.find(item => item.id === 'TABLETOP');
  const interior = value => value.shots.find(item => item.id === 'INTERIOR');
  const definitions = [
    ['A01_PARENT_PIXEL_IDENTITY','PARENT_IDENTITY',v=>{v.parents.workerPixelPromotion.resultSha256='0'.repeat(64);}],
    ['A02_SOURCE_IDENTITY','SOURCE_IDENTITY_TABLETOP-A1',v=>{tabletop(v).runs[0].source.sha256='0'.repeat(64);}],
    ['A03_IMAGE_IDENTITY','IMAGE_IDENTITY',v=>{v.image.id=`sha256:${'0'.repeat(64)}`;}],
    ['A04_SECURITY_BOUNDARY','SECURITY_BOUNDARY',v=>{v.securityBoundary.network='bridge';}],
    ['A05_RENDER_SAMPLES','RENDER_SETTINGS_TABLETOP-A1',v=>{tabletop(v).runs[0].report.appliedSettings.samples=1;}],
    ['A06_FRAME_ORDER','FRAME_ORDER_TABLETOP-A1',v=>{tabletop(v).runs[0].report.frames.reverse();}],
    ['A07_REPORT_SOURCE','REPORT_SOURCE_TABLETOP-A1',v=>{tabletop(v).runs[0].report.source.sha256='0'.repeat(64);}],
    ['A08_REPORT_PLAN','REPORT_PLAN_TABLETOP-A1',v=>{tabletop(v).runs[0].report.bindings.planHash='0'.repeat(64);}],
    ['A09_NON_FINITE','FRAME_DECODE_TABLETOP-A1_21',v=>{tabletop(v).runs[0].sequence.frames[0].finite=false;}],
    ['A10_FRAME_PIXEL_HASH','FRAME_PAIR_TABLETOP_21',v=>{tabletop(v).pairComparison.frames[0].pixelExact=false;}],
    ['A11_TRANSITION_HASH','TRANSITION_PAIR_TABLETOP_21_22',v=>{tabletop(v).pairComparison.transitions[0].deltaExact=false;}],
    ['A12_MOVING_AS_STATIC','TEMPORAL_ROLE_TABLETOP',v=>{for(const r of tabletop(v).runs)for(const t of r.sequence.transitions)t.changedComponentCount=0;}],
    ['A13_STATIC_AS_MOVING','TEMPORAL_ROLE_INTERIOR',v=>{for(const r of interior(v).runs)for(const t of r.sequence.transitions)t.changedComponentCount=1;}],
    ['A14_REVIEW_FRAME_COUNT','REVIEW_CARRIER_TABLETOP-A1',v=>{tabletop(v).runs[0].review.probe.nb_read_frames=7;}],
    ['A15_FAULT_EXIT','FAULT_ATTEMPT',v=>{v.faultAttempt.exitCode=0;}],
    ['A16_FAULT_PROMOTED','FAULT_ATTEMPT',v=>{v.faultAttempt.promotable=true;}],
    ['A17_RECOVERY_ROOT_REUSED','RECOVERY_ATTEMPT',v=>{v.recoveryAttempt.outputRootWasEmpty=false;}],
    ['A18_RECOVERY_PIXEL_HASH','RECOVERY_MATCH',v=>{v.recoveryAttempt.matchesPrimary=false;}],
    ['A19_SEVENTH_DOCKER_RUN','OPERATION_BOUNDARY',v=>{v.runtimeOperationsExecuted.splice(-1,0,'DOCKER_RUN_SEVENTH');}],
    ['A20_NEGATIVE_LAUNCH','NEGATIVE_PRE_CONTAINER',v=>{v.negativeControl.containerLaunchCount=1;}],
    ['A21_EVIDENCE_HASH','EVIDENCE_SELF_HASH',v=>{v.evidenceHash='0'.repeat(64);}],
  ];
  return definitions.map(([id,expectedReason,mutate])=>{
    const value=structuredClone(evidence);
    try {
      mutate(value);
      const observedReason=analyzeB46Evidence(value,spec,{requireAttacks:false}).failures[0]??'NO_REJECTION';
      return {id,expectedReason,observedReason,passed:observedReason===expectedReason};
    } catch (error) {
      return {id,expectedReason,observedReason:'ATTACK_FIXTURE_UNAVAILABLE',passed:false,error:error instanceof Error?error.message:String(error)};
    }
  });
}
