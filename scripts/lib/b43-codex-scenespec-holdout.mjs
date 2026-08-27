import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { canonicalJson, repositoryRoot, sha256 } from './scene-spec.mjs';

export const B43_SPEC_URI = 'specs/codex-scenespec-holdout.v0.1.json';
export const B43_SPEC_PATH = resolve(repositoryRoot, B43_SPEC_URI);
export const B43_SPEC_SHA256 = '15ab5b64bd46d57f108650f580c9b3df78c8b07e20898bd89712a11471b2605c';
export const B43_PREREG_COMMIT = '4a6329296489bca4b7665f30e3d2fbaa315232e4';

export async function sha256File(path) {
  return sha256(await readFile(path));
}

export async function readB43HoldoutSpec() {
  const bytes = await readFile(B43_SPEC_PATH);
  const digest = sha256(bytes);
  if (digest !== B43_SPEC_SHA256) throw new Error(`B43_SPEC_HASH: ${digest}`);
  return JSON.parse(bytes);
}

function fileRecords(value, records = []) {
  if (Array.isArray(value)) value.forEach(item => fileRecords(item, records));
  else if (value && typeof value === 'object') {
    if (typeof value.uri === 'string' && typeof value.sha256 === 'string' && !value.uri.includes('://')) records.push(value);
    Object.values(value).forEach(item => fileRecords(item, records));
  }
  return records;
}

export async function verifyB43HoldoutFiles(spec) {
  const observations = [];
  for (const record of fileRecords({ derivationAuthority: spec.derivationAuthority, frozenInputs: spec.frozenInputs })) {
    const observedSha256 = await sha256File(resolve(repositoryRoot, record.uri)).catch(() => null);
    observations.push({ uri: record.uri, expectedSha256: record.sha256, observedSha256, match: observedSha256 === record.sha256 });
  }
  return observations;
}

export function renderB43Prompt(template, catalog, intent, spec) {
  const rendered = template
    .replace(spec.promptRendering.catalogPlaceholder, JSON.stringify(catalog, null, 2))
    .replace(spec.promptRendering.intentPlaceholder, JSON.stringify(intent, null, 2));
  if (rendered.includes(spec.promptRendering.catalogPlaceholder) || rendered.includes(spec.promptRendering.intentPlaceholder)) {
    throw new Error('PROMPT_RENDERING: unresolved placeholder');
  }
  return rendered;
}

export function inspectB43EventStream(text, forbiddenItemTypes) {
  const events = [];
  const parseErrors = [];
  for (const [index, line] of text.split(/\r?\n/).entries()) {
    if (!line.trim()) continue;
    try { events.push(JSON.parse(line)); }
    catch (error) { parseErrors.push({ line: index + 1, message: error.message }); }
  }
  const eventTypes = Object.create(null);
  const itemTypes = Object.create(null);
  const forbiddenItems = [];
  for (const event of events) {
    eventTypes[event.type] = (eventTypes[event.type] ?? 0) + 1;
    const itemType = event.item?.type;
    if (itemType) {
      itemTypes[itemType] = (itemTypes[itemType] ?? 0) + 1;
      if (forbiddenItemTypes.includes(itemType)) forbiddenItems.push({ eventType: event.type, itemType, itemId: event.item?.id ?? null });
    }
  }
  const threadIds = events.filter(event => event.type === 'thread.started').map(event => event.thread_id).filter(Boolean);
  const hasFailure = (eventTypes['turn.failed'] ?? 0) > 0 || (eventTypes.error ?? 0) > 0;
  const requiredEventsPresent = (eventTypes['thread.started'] ?? 0) === 1 && (eventTypes['turn.started'] ?? 0) === 1 && (eventTypes['turn.completed'] ?? 0) === 1;
  return {
    valid: parseErrors.length === 0 && requiredEventsPresent && !hasFailure,
    eventCount: events.length,
    eventTypes,
    itemTypes,
    parseErrors,
    requiredEventsPresent,
    hasFailure,
    forbiddenItemCount: forbiddenItems.length,
    forbiddenItems,
    threadId: threadIds.length === 1 ? threadIds[0] : null,
  };
}

export function hashB43HoldoutEvidence(evidence) {
  const projection = structuredClone(evidence);
  for (const key of ['evidenceHash', 'analysis', 'attacks', 'attacksPassed', 'verdict']) delete projection[key];
  return sha256(canonicalJson(projection));
}

export function analyzeB43HoldoutEvidence(evidence, spec) {
  const failures = [];
  const gate = (condition, code) => { if (!condition && !failures.includes(code)) failures.push(code); };
  gate(evidence?.schemaVersion === 'bfs.codexSceneSpecHoldoutEvidence.v0.1' && evidence?.experimentId === 'B43', 'EVIDENCE_SCHEMA');
  gate(evidence?.preregistration?.commit === B43_PREREG_COMMIT && evidence?.preregistration?.specSha256 === B43_SPEC_SHA256, 'PREREGISTRATION_IDENTITY');
  gate(evidence?.derivationAuthority?.resultSha256 === spec.derivationAuthority.result.sha256
    && evidence?.derivationAuthority?.auditSha256 === spec.derivationAuthority.audit.sha256
    && evidence?.derivationAuthority?.auditPassed === true, 'DERIVATION_AUTHORITY');
  gate(evidence?.frozenFilesVerified === true && evidence?.frozenFileObservations?.every(item => item.match), 'FROZEN_FILE_IDENTITY');
  gate(evidence?.codex?.releaseExecutableSha256 === spec.codexIdentity.releaseExecutableSha256
    && evidence?.codex?.version === spec.codexIdentity.version, 'CODEX_IDENTITY');
  gate(evidence?.codex?.authenticationStatus === spec.codexIdentity.authenticationStatusExact
    && evidence?.codex?.apiKeyEnvironmentPresent === false, 'AUTHENTICATION');
  gate(evidence?.codex?.modelId === spec.model.id && evidence?.codex?.reasoningEffort === spec.model.reasoningEffort, 'MODEL_IDENTITY');
  gate(evidence?.codex?.invocationPolicyHash === sha256(canonicalJson(spec.invocation))
    && evidence?.invocations?.every(item => item.argvPolicyExact), 'INVOCATION_POLICY');
  const expectedIds = spec.runOrder.map(item => item.invocationId);
  const observedIds = evidence?.invocations?.map(item => item.invocationId) ?? [];
  const threadIds = evidence?.invocations?.map(item => item.eventStream?.threadId).filter(Boolean) ?? [];
  gate(canonicalJson(observedIds) === canonicalJson(expectedIds)
    && evidence?.invocations?.every(item => item.workingDirectoryEmptyBefore === true)
    && threadIds.length === expectedIds.length && new Set(threadIds).size === expectedIds.length, 'RUN_SET');
  gate(evidence?.invocations?.every(item => item.process?.exitCode === 0 && item.process?.timeoutTriggered === false), 'CLI_PROCESS');
  gate(evidence?.invocations?.every(item => item.eventStream?.valid === true), 'CLI_EVENT_STREAM');
  gate(evidence?.invocations?.every(item => item.eventStream?.forbiddenItemCount === 0), 'FORBIDDEN_TOOL_ACTIVITY');
  gate(evidence?.invocations?.every(item => item.proposalSchemaValid === true && item.proposalSemanticValid === true), 'PROPOSAL_VALIDATION');
  gate(evidence?.invocations?.every(item => item.proposalOracleExact === true), 'PROPOSAL_ORACLE');
  gate(evidence?.replicates?.length === spec.frozenInputs.briefs.length && evidence?.replicates?.every(item => item.exact === true), 'REPLICATE_EXACTNESS');
  const unauthorized = evidence?.invocations?.filter(item => item.briefId === 'BRIEF_B43_UNAUTHORIZED_DOWNLOAD') ?? [];
  gate(unauthorized.length === spec.model.replicatesPerBrief && unauthorized.every(item => item.sceneSpecCount === 0 && item.buildPlanCount === 0 && item.blenderInvocationCount === 0)
    && evidence?.operations?.sceneSpecsCreated === 0 && evidence?.operations?.buildPlansCreated === 0
    && evidence?.operations?.blenderInvocations === 0 && evidence?.operations?.containerInvocations === 0, 'REJECTION_OUTPUT');
  gate(evidence?.evidenceHash === hashB43HoldoutEvidence(evidence), 'EVIDENCE_SELF_HASH');
  gate(evidence?.attacks?.length === spec.requiredAttacks.length && evidence?.attacks?.every(item => item.passed), 'ATTACKS');
  return { schemaVersion: 'bfs.codexSceneSpecHoldoutAnalysis.v0.1', passed: failures.length === 0, failures, decision: failures[0] ?? spec.acceptedVerdict };
}

export function runB43HoldoutAttacks(evidence, spec) {
  const mutate = (change, rehash = true) => {
    const candidate = structuredClone(evidence);
    for (const key of ['analysis', 'attacks', 'attacksPassed', 'verdict']) delete candidate[key];
    change(candidate);
    if (rehash) candidate.evidenceHash = hashB43HoldoutEvidence(candidate);
    return candidate;
  };
  const cases = [
    ['H01_CLI_HASH', value => { value.codex.releaseExecutableSha256 = '0'.repeat(64); }],
    ['H02_AUTH_MODE', value => { value.codex.authenticationStatus = 'API key'; }],
    ['H03_API_KEY_PRESENT', value => { value.codex.apiKeyEnvironmentPresent = true; }],
    ['H04_MODEL_ID', value => { value.codex.modelId = 'unfrozen-model'; }],
    ['H05_INVOCATION_FLAGS', value => { value.invocations[0].argvPolicyExact = false; }],
    ['H06_TOOL_EVENT', value => { value.invocations[0].eventStream.forbiddenItemCount = 1; }],
    ['H07_PROPOSAL_DRIFT', value => { value.invocations[0].proposalOracleExact = false; }],
    ['H08_MISSING_REPLICATE', value => { value.invocations.pop(); }],
    ['H09_REPLICATE_DISAGREEMENT', value => { value.replicates[0].exact = false; }],
    ['H10_REJECT_OUTPUT', value => { const item = value.invocations.find(run => run.briefId === 'BRIEF_B43_UNAUTHORIZED_DOWNLOAD'); item.sceneSpecCount = 1; }],
    ['H11_EVENT_FAILURE', value => { value.invocations[0].eventStream.valid = false; }],
    ['H12_EVIDENCE_SELF_HASH', value => { value.evidenceHash = 'f'.repeat(64); }, false],
  ];
  const expected = new Map(spec.requiredAttacks.map(item => [item.id, item.expectedReason]));
  return cases.map(([id, change, rehash]) => {
    const analysis = analyzeB43HoldoutEvidence(mutate(change, rehash !== false), spec);
    const expectedReason = expected.get(id);
    return { id, expectedReason, observedFailures: analysis.failures, passed: !analysis.passed && analysis.failures[0] === expectedReason };
  });
}

