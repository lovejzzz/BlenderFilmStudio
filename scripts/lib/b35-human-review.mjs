import { sha256Canonical } from './receipt-format.mjs';

export const RATINGS = ['NONE', 'BARELY_VISIBLE', 'MILD', 'OBVIOUS', 'SEVERE'];
export const CONFIDENCE = ['LOW', 'MEDIUM', 'HIGH'];
export const PAIR_CHOICES = ['LEFT_MORE_STABLE', 'INDISTINGUISHABLE', 'RIGHT_MORE_STABLE'];
export const ORDER_PERMUTATIONS = ['NQ4Q8', 'NQ8Q4', 'Q4NQ8', 'Q4Q8N', 'Q8NQ4', 'Q8Q4N'];

const fail = reason => ({ valid: false, reason });
const same = (left, right) => JSON.stringify(left) === JSON.stringify(right);

export function responseBody(response) {
  const body = structuredClone(response);
  delete body.responseHash;
  return body;
}

export function validateB35Response({ spec, specSha, manifest, response }) {
  if (response.documentType !== 'BFS_B35_BLINDED_RESPONSE' || response.version !== spec.version) return fail('RESPONSE_TYPE');
  if (response.studySpecSha256 !== specSha || manifest.studySpecSha256 !== specSha) return fail('SPEC_BINDING');
  if (!/^[0-9a-f]{64}$/.test(response.responseHash || '') || sha256Canonical(responseBody(response)) !== response.responseHash) return fail('RESPONSE_HASH');
  const publicSession = manifest.sessions.find(item => item.sessionId === response.sessionId);
  if (!publicSession) return fail('SESSION_ID');
  if (response.mappingCommitment !== publicSession.mappingCommitment) return fail('SESSION_COMMITMENT');
  const expectedBindings = publicSession.visibleCarrierBindings.map(({ label, sha256 }) => ({ label, sha256 }));
  if (!same(response.carrierBindings, expectedBindings)) return fail('CARRIER_BINDING');
  const started = Date.parse(response.startedAt), locked = Date.parse(response.lockedAt);
  if (!Number.isFinite(started) || !Number.isFinite(locked) || locked <= started) return fail('TIMESTAMPS');

  const telemetry = response.playbackTelemetry;
  if (!Array.isArray(telemetry) || telemetry.length !== 3) return fail('PLAYBACK_TELEMETRY');
  for (const [index, clip] of telemetry.entries()) {
    if (clip.label !== expectedBindings[index].label || clip.carrierSha256 !== expectedBindings[index].sha256 || !Array.isArray(clip.plays) || clip.plays.length !== spec.observerDesign.playsPerClip) return fail('PLAYBACK_COUNT');
    for (const play of clip.plays) {
      if (play.playbackRate !== 1 || play.ended !== true || play.seekingEvents !== 0 || play.rateChangeEvents !== 0 || play.stallEvents !== 0 || play.pageHiddenDuringPlay !== false) return fail('PLAYBACK_CONTROL');
      if (!Number.isInteger(play.totalVideoFramesDelta) || play.totalVideoFramesDelta <= 0 || play.droppedVideoFramesDelta !== 0) return fail('DROPPED_FRAME');
      if (!Number.isFinite(play.elapsedSeconds) || play.elapsedSeconds < 5.5 || play.elapsedSeconds > 9) return fail('PLAYBACK_DURATION');
    }
  }

  if (!Array.isArray(response.clipResponses) || response.clipResponses.length !== 3) return fail('CLIP_RESPONSE_COUNT');
  for (const [index, item] of response.clipResponses.entries()) {
    if (item.label !== expectedBindings[index].label || item.carrierSha256 !== expectedBindings[index].sha256 || !RATINGS.includes(item.rating) || !CONFIDENCE.includes(item.confidence) || typeof item.note !== 'string') return fail('CLIP_RESPONSE');
  }
  const expectedPairs = [['CLIP-01', 'CLIP-02'], ['CLIP-01', 'CLIP-03'], ['CLIP-02', 'CLIP-03']];
  if (!Array.isArray(response.pairResponses) || response.pairResponses.length !== 3) return fail('PAIR_RESPONSE_COUNT');
  for (const [index, item] of response.pairResponses.entries()) {
    if (!same(item.labels, expectedPairs[index]) || !PAIR_CHOICES.includes(item.choice) || typeof item.note !== 'string') return fail('PAIR_RESPONSE');
  }

  const viewing = response.viewing || {};
  const requiredStrings = ['observerId', 'expertise', 'acuityScreening', 'colourVisionScreening', 'displayManufacturerModel', 'browser', 'operatingSystem', 'brightnessSetting', 'viewingDistance', 'ambientLighting'];
  if (requiredStrings.some(key => typeof viewing[key] !== 'string' || viewing[key].trim() === '')) return fail('VIEWING_RECORD');
  if (!/^[A-Za-z0-9_-]{3,40}$/.test(viewing.observerId) || viewing.directDevelopmentInvolvement !== 'NO') return fail('OBSERVER_INDEPENDENCE');
  const [minimumWidth, minimumHeight] = spec.viewingValidity.minimumDisplayNativeResolution;
  if (!Number.isInteger(viewing.displayNativeWidth) || viewing.displayNativeWidth < minimumWidth || !Number.isInteger(viewing.displayNativeHeight) || viewing.displayNativeHeight < minimumHeight) return fail('DISPLAY_RESOLUTION');
  if (!spec.viewingValidity.acceptedRefreshRatesHz.includes(viewing.refreshRateHz) || viewing.refreshRateHz % spec.renderDesign.frames.fps !== 0) return fail('DISPLAY_REFRESH');
  if (viewing.browserZoomPercent !== spec.viewingValidity.browserZoomPercent || viewing.zoomConfirmed !== true || !same(viewing.cssVideoSize, spec.viewingValidity.requiredCssVideoSize)) return fail('DISPLAY_GEOMETRY');
  if (!Number.isFinite(viewing.devicePixelRatio) || viewing.devicePixelRatio <= 0 || typeof viewing.userAgent !== 'string' || viewing.userAgent.length < 8) return fail('BROWSER_RECORD');
  return { valid: true, reason: 'OK', publicSession };
}

function primaryPairDirection(response, mapping) {
  const visibleByUnderlying = Object.fromEntries(mapping.map(item => [item.sourceLabel, item.visibleLabel]));
  const natural = visibleByUnderlying.NATURAL32, q8 = visibleByUnderlying.STRATIFIED8;
  const pair = response.pairResponses.find(item => item.labels.includes(natural) && item.labels.includes(q8));
  if (!pair) throw new Error('PRIMARY_PAIR_MISSING');
  if (pair.choice === 'INDISTINGUISHABLE') return 'INDISTINGUISHABLE';
  const chosenVisible = pair.choice === 'LEFT_MORE_STABLE' ? pair.labels[0] : pair.labels[1];
  return chosenVisible === q8 ? 'Q8_MORE_STABLE' : 'NATURAL_MORE_STABLE';
}

export function analyzeB35Responses({ spec, specSha, manifest, sealed, responses }) {
  const validations = responses.map(response => validateB35Response({ spec, specSha, manifest, sealed, response }));
  if (validations.some(item => !item.valid)) return { status: 'INVALID_REVIEW', decision: 'INVALID_REVIEW', validations };
  if (new Set(responses.map(item => item.responseHash)).size !== responses.length || new Set(responses.map(item => item.sessionId)).size !== responses.length || new Set(responses.map(item => item.viewing.observerId)).size !== responses.length) return { status: 'INVALID_REVIEW', decision: 'INVALID_REVIEW', validations, reason: 'DUPLICATE_RESPONSE_SESSION_OR_OBSERVER' };
  const count = responses.length;
  if (count === 0) return { status: 'HUMAN_REVIEW_PENDING', decision: null, validations };

  const observations = responses.map(response => {
    const session = sealed.sessions.find(item => item.sessionId === response.sessionId);
    const mapping = session.mapping;
    const ratingByVisible = Object.fromEntries(response.clipResponses.map(item => [item.label, item.rating]));
    const ratingByMethod = Object.fromEntries(mapping.map(item => [item.sourceLabel, ratingByVisible[item.visibleLabel]]));
    return { sessionId: response.sessionId, observerId: response.viewing.observerId, permutation: session.permutation, primaryDirection: primaryPairDirection(response, mapping), ratingByMethod };
  });
  const directionCounts = Object.fromEntries(['Q8_MORE_STABLE', 'NATURAL_MORE_STABLE', 'INDISTINGUISHABLE'].map(label => [label, observations.filter(item => item.primaryDirection === label).length]));
  const mildOrWorseCounts = Object.fromEntries(['NATURAL32', 'QUADRATURE4', 'STRATIFIED8'].map(method => [method, observations.filter(item => RATINGS.indexOf(item.ratingByMethod[method]) >= RATINGS.indexOf('MILD')).length]));
  const permutationCounts = Object.fromEntries(ORDER_PERMUTATIONS.map(label => [label, observations.filter(item => item.permutation === label).length]));
  let status, decision = null;
  if (count <= 14) status = 'INFORMAL_REVIEW_ONLY';
  else if (count <= 17) status = 'FORMAL_REVIEW_INCOMPLETE';
  else if (count !== 18 || Object.values(permutationCounts).some(value => value !== 3)) status = decision = 'INVALID_REVIEW';
  else {
    status = 'FORMAL_REVIEW_COMPLETE';
    if (directionCounts.Q8_MORE_STABLE >= 14 && mildOrWorseCounts.STRATIFIED8 <= mildOrWorseCounts.NATURAL32) decision = spec.formalDecision.q8PreferenceLabel;
    else if (directionCounts.NATURAL_MORE_STABLE >= 14 && mildOrWorseCounts.NATURAL32 <= mildOrWorseCounts.STRATIFIED8) decision = spec.formalDecision.naturalPreferenceLabel;
    else if (directionCounts.INDISTINGUISHABLE >= 14 && mildOrWorseCounts.NATURAL32 <= 2 && mildOrWorseCounts.STRATIFIED8 <= 2) decision = spec.formalDecision.noDirectionalDifferenceLabel;
    else decision = spec.formalDecision.otherwise;
  }
  return { status, decision, validResponseCount: count, directionCounts, mildOrWorseCounts, permutationCounts, observations, validations };
}
