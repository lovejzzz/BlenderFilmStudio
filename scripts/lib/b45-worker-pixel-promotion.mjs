import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { canonicalJson, repositoryRoot, sha256 } from './scene-spec.mjs';

export const B45_SPEC_URI = 'specs/codex-worker-pixel-promotion.v0.1.json';
export const B45_SPEC_PATH = resolve(repositoryRoot, B45_SPEC_URI);
export const B45_SPEC_SHA256 = 'bca84a43296c1f783bff4669e7a616a4c89a5d0b1660b6c8a11680b6ca0c11e8';
export const B45_PREREG_COMMIT = 'd0eeb985bb9db39338fce02f1b0cbeaac96cc640';
export const B45_C1_SPEC_URI = 'specs/codex-worker-pixel-promotion-media-type-correction.v0.1.json';
export const B45_C1_SPEC_PATH = resolve(repositoryRoot, B45_C1_SPEC_URI);
export const B45_C1_SPEC_SHA256 = '7f7ae50999c412a251fef55e941e109b58cbc41904f9f297ecfaddbf6aaeda11';
export const B45_C1_PREREG_COMMIT = '222574d793088c04e1d02b9a5d1d1c56f0776c88';

export const B45_IDENTITY = {
  schemaVersion: 'bfs.codexWorkerPixelPromotionEvidence.v0.1',
  experimentId: 'B45',
  preregistrationCommit: B45_PREREG_COMMIT,
  specSha256: B45_SPEC_SHA256,
  analysisSchemaVersion: 'bfs.codexWorkerPixelPromotionAnalysis.v0.1',
};
export const B45_C1_IDENTITY = {
  schemaVersion: 'bfs.codexWorkerPixelPromotionEvidence.v0.2',
  experimentId: 'B45-C1',
  preregistrationCommit: B45_C1_PREREG_COMMIT,
  specSha256: B45_C1_SPEC_SHA256,
  analysisSchemaVersion: 'bfs.codexWorkerPixelPromotionAnalysis.v0.2',
};

export async function readB45Spec() {
  const bytes = await readFile(B45_SPEC_PATH);
  const digest = sha256(bytes);
  if (digest !== B45_SPEC_SHA256) throw new Error(`B45 spec SHA mismatch: ${digest}`);
  return JSON.parse(bytes);
}

export async function readB45C1Spec() {
  const bytes = await readFile(B45_C1_SPEC_PATH);
  const digest = sha256(bytes);
  if (digest !== B45_C1_SPEC_SHA256) throw new Error(`B45-C1 spec SHA mismatch: ${digest}`);
  return JSON.parse(bytes);
}

export function hashB45Evidence(evidence) {
  const copy = structuredClone(evidence);
  for (const key of ['evidenceHash', 'analysis', 'attacks', 'attacksPassed', 'correctionAttacks', 'correctionAttacksPassed', 'verdict', 'nonClaims']) delete copy[key];
  return sha256(Buffer.from(canonicalJson(copy)));
}

export function expectedAppliedSettings(spec) {
  const value = spec.renderControl;
  return {
    engine: value.engine,
    device: value.device,
    resolution: [value.width, value.height, value.resolutionPercentage],
    samples: value.samples,
    seed: null,
    animatedSeed: value.animatedSeed,
    denoising: value.denoising,
    threadsMode: value.threadsMode,
    threads: value.threads,
    filmTransparent: value.filmTransparent,
    compositing: value.compositing,
    sequencer: value.sequencer,
  };
}

export function analyzeB45Evidence(evidence, spec, { requireAttacks = true, requireEvidenceHash = true, identity = B45_IDENTITY } = {}) {
  const failures = [];
  const gate = (condition, code) => { if (!condition && !failures.includes(code)) failures.push(code); };
  gate(evidence?.schemaVersion === identity.schemaVersion && evidence?.experimentId === identity.experimentId, 'EVIDENCE_SCHEMA');
  gate(evidence?.preregistration?.commit === identity.preregistrationCommit && evidence?.preregistration?.specSha256 === identity.specSha256, 'PREREGISTRATION_IDENTITY');
  gate(canonicalJson(evidence?.parents) === canonicalJson(spec.parents), 'PARENT_IDENTITY');
  gate(evidence?.parentObservations?.length === 4 && evidence.parentObservations.every(item => item.match), 'PARENT_HASH');
  gate(evidence?.inputObservations?.length >= 11 && evidence.inputObservations.every(item => item.match), 'FROZEN_INPUT_HASH');
  gate(/^[a-f0-9]{40}$/.test(evidence?.toolFreezeCommit ?? '') && Object.values(evidence?.tools ?? {}).every(item => /^[a-f0-9]{64}$/.test(item.sha256 ?? '')), 'TOOL_IDENTITY');
  gate(canonicalJson(evidence?.hostPixelDecoder) === canonicalJson(spec.hostPixelDecoder), 'DECODER_IDENTITY');
  gate(canonicalJson(evidence?.image) === canonicalJson({ id: spec.image.id, os: spec.image.os, architecture: spec.image.architecture, sizeBytes: spec.image.dockerReportedSizeBytes }), 'IMAGE_IDENTITY');
  gate(evidence?.diskAdmission?.status === 'ACCEPTED' && BigInt(evidence.diskAdmission.freeAfterProjectedBytes) >= BigInt(spec.diskAdmission.minimumReserveBytes), 'DISK_ADMISSION');
  gate(canonicalJson(evidence?.securityBoundary) === canonicalJson(spec.containerContract), 'SECURITY_BOUNDARY');
  gate(canonicalJson(evidence?.renderControl) === canonicalJson(spec.renderControl), 'RENDER_CONTROL');
  gate(evidence?.shots?.length === spec.shots.length, 'SHOT_COUNT');

  for (const expectedShot of spec.shots) {
    const shot = evidence?.shots?.find(item => item.id === expectedShot.id);
    gate(shot?.sourceBlendHashesDifferent === true, `SOURCE_DIVERGENCE_${expectedShot.id}`);
    gate(shot?.runs?.length === expectedShot.inputs.length, `RUN_COUNT_${expectedShot.id}`);
    for (const expectedInput of expectedShot.inputs) {
      const run = shot?.runs?.find(item => item.id === expectedInput.id);
      gate(run?.source?.uri === expectedInput.blendUri && run?.source?.sha256 === expectedInput.blendSha256 && run?.source?.bytes === expectedInput.blendBytes, `SOURCE_IDENTITY_${expectedInput.id}`);
      gate(run?.exitCode === 0 && run?.timeoutTriggered === false && run?.completed === true, `RUN_COMPLETE_${expectedInput.id}`);
      const report = run?.report;
      gate(report?.source?.sha256 === expectedInput.blendSha256 && report?.source?.bytes === expectedInput.blendBytes && report?.source?.uri === `/repo/${expectedInput.blendUri}`, `REPORT_SOURCE_${expectedInput.id}`);
      gate(report?.bindings?.planHash === expectedShot.planHash && report?.bindings?.sceneSpecHash === expectedShot.sourceSceneCanonicalSha256 && report?.bindings?.structureHash === expectedShot.structureHash, `REPORT_PLAN_${expectedInput.id}`);
      gate(report?.shotId === expectedShot.shotId && report?.frame === expectedShot.frame && canonicalJson(report?.originalSettings?.frameRange) === canonicalJson(expectedShot.frameRange), `REPORT_FRAME_${expectedInput.id}`);
      const expectedSettings = expectedAppliedSettings(spec);
      if (report?.bindings) expectedSettings.seed = report.bindings.shotSeed;
      gate(Number.isInteger(report?.bindings?.shotSeed) && report.bindings.shotSeed >= 0 && report?.appliedSettings?.seed === report.bindings.shotSeed && canonicalJson(report.appliedSettings) === canonicalJson(expectedSettings)
        && report?.renderOperatorCalls === spec.renderControl.renderOperatorCallsPerContainer
        && report?.savesFromSameRenderResult === spec.renderControl.savesFromSameRenderResult, `RENDER_SETTINGS_${expectedInput.id}`);
      gate(report?.blender?.version === spec.image.blenderVersion && report?.blender?.buildHash === spec.image.blenderBuildHash
        && report?.blender?.buildPlatform === 'Linux' && report?.ocio?.sha256 === spec.frozenInputs.ocio.sha256
        && report?.ocio?.declaredEncoding === 'ACEScg', `RUNTIME_BINDING_${expectedInput.id}`);
      gate(run?.artifacts?.exr?.sha256 === report?.artifacts?.exr?.sha256 && run?.decoded?.input?.sha256 === run?.artifacts?.exr?.sha256
        && run?.decoded?.finite === true && run?.decoded?.metadata?.dtype === 'float32-le'
        && run?.decoded?.metadata?.channelOrder === 'BGRA'
        && canonicalJson(run?.decoded?.metadata?.shape) === canonicalJson([spec.renderControl.height, spec.renderControl.width, 4]), `EXR_DECODE_${expectedInput.id}`);
      gate(run?.artifacts?.png?.valid === true && canonicalJson(run.artifacts.png.dimensions) === canonicalJson([spec.renderControl.width, spec.renderControl.height])
        && run.artifacts.png.sha256 === report?.artifacts?.png?.sha256, `PNG_REVIEW_${expectedInput.id}`);
      gate(run?.milestones?.length === 6 && canonicalJson(run.milestones.map(item => item.name)) === canonicalJson(['PROCESS_STARTED', 'SOURCE_VERIFIED', 'SCENE_CONFIGURED', 'RENDER_STARTED', 'RENDER_COMPLETED', 'REPORT_WRITTEN']), `MILESTONES_${expectedInput.id}`);
    }
    gate(shot?.pairComparison?.pixelExact === true && shot?.pairComparison?.canonicalPixelSha256A === shot?.pairComparison?.canonicalPixelSha256B
      && shot?.runs?.[0]?.decoded?.canonicalPixelSha256 === shot?.runs?.[1]?.decoded?.canonicalPixelSha256
      && shot?.pairComparison?.canonicalPixelSha256A === shot?.runs?.[0]?.decoded?.canonicalPixelSha256, `PIXEL_PAIR_${expectedShot.id}`);
  }

  gate(evidence?.negativeControl?.id === spec.negativeControl.id && evidence?.negativeControl?.reason === spec.negativeControl.expectedReason
    && evidence?.negativeControl?.observedSha256 !== spec.negativeControl.declaredSha256 && evidence?.negativeControl?.containerLaunchCount === 0, 'NEGATIVE_PRE_CONTAINER');
  const operations = evidence?.runtimeOperationsExecuted ?? [];
  gate(Array.isArray(operations) && operations[0] === 'DOCKER_IMAGE_INSPECT' && operations.at(-1) === 'DOCKER_RUNNING_CONTAINER_CHECK'
    && operations.filter(item => item.startsWith('DOCKER_RUN_')).length === spec.operationBoundary.dockerRuns
    && operations.filter(item => item.startsWith('HOST_EXR_ANALYSIS_')).length === spec.operationBoundary.hostExrAnalyses
    && !operations.some(item => /BUILD|PULL|DOWNLOAD|MODEL|CODEX|VIDEO_API/.test(item)), 'OPERATION_BOUNDARY');
  gate(evidence?.cleanup?.experimentContainersRunningAfter === 0, 'CLEANUP_BOUNDARY');
  gate(Array.isArray(evidence?.errors) && evidence.errors.length === 0, 'RUN_ERRORS');
  if (requireAttacks) gate(evidence?.attacks?.length === spec.attacks.length && evidence.attacks.every(item => item.passed), 'ATTACKS');
  if (requireEvidenceHash) gate(evidence?.evidenceHash === hashB45Evidence(evidence), 'EVIDENCE_SELF_HASH');
  return { schemaVersion: identity.analysisSchemaVersion, passed: failures.length === 0, failures, decision: failures[0] ?? spec.acceptedVerdict };
}

export function runB45Attacks(evidence, spec, { identity = B45_IDENTITY } = {}) {
  const attacks = [
    ['A01_PARENT_IDENTITY', 'PARENT_IDENTITY', value => { value.parents.codexWorkerPromotion.resultSha256 = '0'.repeat(64); }],
    ['A02_SOURCE_IDENTITY', 'SOURCE_IDENTITY_TABLETOP-A1', value => { value.shots.find(item => item.id === 'TABLETOP').runs[0].source.sha256 = '0'.repeat(64); }],
    ['A03_SOURCE_DIVERGENCE', 'SOURCE_DIVERGENCE_TABLETOP', value => { value.shots.find(item => item.id === 'TABLETOP').sourceBlendHashesDifferent = false; }],
    ['A04_IMAGE_IDENTITY', 'IMAGE_IDENTITY', value => { value.image.id = `sha256:${'0'.repeat(64)}`; }],
    ['A05_SECURITY_BOUNDARY', 'SECURITY_BOUNDARY', value => { value.securityBoundary.network = 'bridge'; }],
    ['A06_REPORT_SOURCE', 'REPORT_SOURCE_TABLETOP-A1', value => { value.shots.find(item => item.id === 'TABLETOP').runs[0].report.source.sha256 = '0'.repeat(64); }],
    ['A07_REPORT_PLAN', 'REPORT_PLAN_TABLETOP-A1', value => { value.shots.find(item => item.id === 'TABLETOP').runs[0].report.bindings.planHash = '0'.repeat(64); }],
    ['A08_REPORT_FRAME', 'REPORT_FRAME_TABLETOP-A1', value => { value.shots.find(item => item.id === 'TABLETOP').runs[0].report.frame = 25; }],
    ['A09_RENDER_SETTINGS', 'RENDER_SETTINGS_TABLETOP-A1', value => { value.shots.find(item => item.id === 'TABLETOP').runs[0].report.appliedSettings.samples = 2; }],
    ['A10_NON_FINITE_ACCEPTED', 'EXR_DECODE_TABLETOP-A1', value => { value.shots.find(item => item.id === 'TABLETOP').runs[0].decoded.finite = false; }],
    ['A11_PIXEL_HASH', 'PIXEL_PAIR_TABLETOP', value => { value.shots.find(item => item.id === 'TABLETOP').runs[1].decoded.canonicalPixelSha256 = '0'.repeat(64); }],
    ['A12_FIFTH_DOCKER_RUN', 'OPERATION_BOUNDARY', value => { value.runtimeOperationsExecuted.splice(-1, 0, 'DOCKER_RUN_FIFTH'); }],
    ['A13_NEGATIVE_LAUNCH', 'NEGATIVE_PRE_CONTAINER', value => { value.negativeControl.containerLaunchCount = 1; }],
    ['A14_EVIDENCE_HASH', 'EVIDENCE_SELF_HASH', value => { value.evidenceHash = '0'.repeat(64); }],
  ];
  return attacks.map(([id, expectedReason, mutate]) => {
    const value = structuredClone(evidence);
    try {
      mutate(value);
      const observedReason = analyzeB45Evidence(value, spec, { requireAttacks: false, identity }).failures[0] ?? 'NO_REJECTION';
      return { id, expectedReason, observedReason, passed: observedReason === expectedReason };
    } catch (error) {
      return { id, expectedReason, observedReason: 'ATTACK_FIXTURE_UNAVAILABLE', passed: false, error: error instanceof Error ? error.message : String(error) };
    }
  });
}

export function runB45FailureTotalitySelfTest(evidence, spec) {
  const value = structuredClone(evidence);
  const run = value?.shots?.find(item => item.id === 'TABLETOP')?.runs?.[0];
  if (run) run.report = null;
  try {
    const analysis = analyzeB45Evidence(value, spec, { requireAttacks: false, identity: B45_C1_IDENTITY });
    const attacks = runB45Attacks(value, spec, { identity: B45_C1_IDENTITY });
    const observedReason = analysis.failures[0] ?? 'NO_REJECTION';
    return {
      passed: observedReason === 'REPORT_SOURCE_TABLETOP-A1' && attacks.length === spec.attacks.length,
      expectedReason: 'REPORT_SOURCE_TABLETOP-A1', observedReason,
      attackGeneratorReturned: attacks.length,
      attackGeneratorThrew: false,
    };
  } catch (error) {
    return {
      passed: false, expectedReason: 'REPORT_SOURCE_TABLETOP-A1', observedReason: 'THREW',
      attackGeneratorReturned: 0, attackGeneratorThrew: true,
      error: error instanceof Error ? error.message : String(error),
    };
  }
}

export function analyzeB45C1Evidence(evidence, spec, correctionSpec, { requireAttacks = true } = {}) {
  const base = analyzeB45Evidence(evidence, spec, { requireAttacks: false, requireEvidenceHash: false, identity: B45_C1_IDENTITY });
  const failures = [...base.failures];
  const gate = (condition, code) => { if (!condition && !failures.includes(code)) failures.push(code); };
  gate(canonicalJson(evidence?.correctionParent) === canonicalJson(correctionSpec.parentFailure), 'C1_PARENT_FAILURE');
  const expectedExr = correctionSpec.corrections.find(item => item.id === 'EXR_MEDIA_TYPE')?.requiredReport;
  const expectedPng = { mediaType: 'IMAGE', fileFormat: 'PNG', colorMode: 'RGBA', colorDepth: '8' };
  for (const shot of spec.shots) for (const input of shot.inputs) {
    const report = evidence?.shots?.find(item => item.id === shot.id)?.runs?.find(item => item.id === input.id)?.report;
    gate(canonicalJson(report?.saveSettings?.exr) === canonicalJson(expectedExr)
      && canonicalJson(report?.saveSettings?.png) === canonicalJson(expectedPng), `C1_SAVE_SETTINGS_${input.id}`);
  }
  gate(evidence?.failureTotalSelfTest?.passed === true
    && evidence.failureTotalSelfTest.observedReason === 'REPORT_SOURCE_TABLETOP-A1'
    && evidence.failureTotalSelfTest.attackGeneratorReturned === spec.attacks.length
    && evidence.failureTotalSelfTest.attackGeneratorThrew === false, 'C1_FAILURE_TOTALITY');
  if (requireAttacks) {
    gate(evidence?.attacks?.length === spec.attacks.length && evidence.attacks.every(item => item.passed), 'ATTACKS');
    gate(evidence?.correctionAttacks?.length === correctionSpec.requiredCorrectionAttacks.length
      && evidence.correctionAttacks.every(item => item.passed), 'C1_ATTACKS');
  }
  gate(evidence?.evidenceHash === hashB45Evidence(evidence), 'EVIDENCE_SELF_HASH');
  return {
    schemaVersion: B45_C1_IDENTITY.analysisSchemaVersion,
    passed: failures.length === 0,
    failures,
    decision: failures[0] ?? correctionSpec.acceptedVerdict,
  };
}

export function runB45C1Attacks(evidence, spec, correctionSpec) {
  const definitions = [
    ['C1_A01_EXR_MEDIA_TYPE', 'C1_SAVE_SETTINGS_TABLETOP-A1', value => { value.shots.find(item => item.id === 'TABLETOP').runs[0].report.saveSettings.exr.mediaType = 'MULTI_LAYER_IMAGE'; }],
    ['C1_A02_NULL_TOTALITY', 'C1_FAILURE_TOTALITY', value => { value.failureTotalSelfTest.passed = false; }],
  ];
  return definitions.map(([id, expectedReason, mutate]) => {
    const value = structuredClone(evidence);
    try {
      mutate(value);
      const observedReason = analyzeB45C1Evidence(value, spec, correctionSpec, { requireAttacks: false }).failures[0] ?? 'NO_REJECTION';
      return { id, expectedReason, observedReason, passed: observedReason === expectedReason };
    } catch (error) {
      return { id, expectedReason, observedReason: 'ATTACK_FIXTURE_UNAVAILABLE', passed: false, error: error instanceof Error ? error.message : String(error) };
    }
  });
}
