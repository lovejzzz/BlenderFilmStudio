#!/usr/bin/env node

import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { mkdir, readFile, stat, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const correctionUri = 'specs/ai-native-studio-pb2-readiness-preregistration-c1.v0.2.json';
const outputUri = process.argv[2] || 'experiments/ai-native-studio-phase-b/PB.2-readiness-2026-08-31-mac-m2max-attempt-02/audit-c1.json';

const digest = (value) => createHash('sha256').update(value).digest('hex');
const bytes = (uri, base = root) => readFile(resolve(base, uri));
const json = async (uri, base = root) => JSON.parse(await readFile(resolve(base, uri), 'utf8'));
const git = (args, cwd) => execFileSync('git', args, { cwd, encoding: 'utf8' }).trim();

const correction = await json(correctionUri);
const baseBytes = await bytes(correction.baseContract.uri);
const base = JSON.parse(baseBytes);
const failedBytes = await bytes(correction.retainedAttempt01.uri);
const failed = JSON.parse(failedBytes);
const state = await json('handoff/ai-native-studio-current-state.v0.1.json');
const source = base.engineSourceReadOnlyBinding.retainedSourceRoot;
const sourceContract = await readFile(resolve(source, 'scripts/modules/film_studio_contract.py'), 'utf8');
const acceptedVerdict = await json(base.inheritedF04Bindings.acceptedRoot + '/verdict.json');
const checks = {};

checks.correctionScopeClosed = correction.status === 'PREREGISTERED_READINESS_CORRECTION_ONLY_PB2_NOT_AUTHORIZED'
  && correction.authorization.pb2FormalExecution === false
  && correction.authorization.engineSourceMutation === false
  && correction.authorization.engineRemoteWrite === false
  && correction.authorization.blenderStarts === 0
  && correction.authorization.renders === 0
  && correction.authorization.networkCalls === 0;
checks.parentResearchCommitExact = git(['rev-parse', 'HEAD'], root) === correction.parentResearchCommit;
checks.baseContractExact = digest(baseBytes) === correction.baseContract.sha256;
checks.retainedAttempt01Exact = digest(failedBytes) === correction.retainedAttempt01.fileSha256
  && failed.auditHash === correction.retainedAttempt01.auditHash
  && failed.status === 'FAIL'
  && failed.counts.passed === 16
  && failed.counts.total === 19;
checks.retainedFailureSetExact = JSON.stringify(Object.entries(failed.checks).filter(([, value]) => !value).map(([key]) => key))
  === JSON.stringify(correction.retainedAttempt01.failedChecks);
checks.retainedPassingChecksExact = Object.values(failed.checks).filter(Boolean).length === 16;
checks.retainedAttemptZeroCounts = [
  'blenderStarts', 'renders', 'proposalsExecuted', 'buildPlanFilesWritten',
  'engineSourceEdits', 'engineRemoteWrites', 'networkCalls',
].every((key) => failed.counts[key] === 0);
checks.engineStillExactAndClean = git(['rev-parse', 'HEAD'], source) === base.engineSourceReadOnlyBinding.requiredHead
  && git(['status', '--porcelain=v1'], source) === '';

const forbiddenImports = /(?:^|\n)\s*(?:import\s+(?:subprocess|socket|urllib|requests|http\.client)\b|from\s+(?:subprocess|socket|urllib|requests|http\.client)\b)/m;
const dynamicCalls = /(^|[^A-Za-z0-9_])(eval|exec)\s*\(/m;
checks.c1DynamicExecutionCheckPass = !forbiddenImports.test(sourceContract) && !dynamicCalls.test(sourceContract);
checks.c1F04SelfHashFieldPass = acceptedVerdict.status === 'PASS'
  && acceptedVerdict.receiptHash === correction.corrections.find((item) => item.id === 'C1_F04_SELF_HASH_FIELD').correctedValue
  && acceptedVerdict.checks.allRequiredAcceptanceCriteriaPassed === true;

const b02Correction = correction.corrections.find((item) => item.id === 'C1_B02_CANONICAL_HASH_TRANSCRIPTION');
const fixtureResults = [];
for (const fixture of base.inheritedF04Bindings.fixtures) {
  const proposalBytes = await bytes(fixture.proposalUri);
  const proposal = JSON.parse(proposalBytes);
  const approval = await json(fixture.approvalUri);
  const expectedCanonical = fixture.id === 'B02' ? b02Correction.correctedValue : fixture.sceneSpecCanonicalSha256;
  const sceneBytes = await bytes(fixture.sceneSpecUri);
  const pass = digest(proposalBytes) === fixture.proposalFileSha256
    && digest(sceneBytes) === fixture.sceneSpecFileSha256
    && proposal.sceneSpec.fileSha256 === fixture.sceneSpecFileSha256
    && proposal.sceneSpec.canonicalSha256 === expectedCanonical
    && proposal.requestedOperation === base.inheritedF04Bindings.approvedOperation
    && JSON.stringify(proposal.requestedMutationScope) === JSON.stringify(base.inheritedF04Bindings.approvedMutationScope)
    && JSON.stringify(proposal.security) === JSON.stringify(base.inheritedF04Bindings.exactSecurity)
    && approval.proposal.uri === fixture.proposalUri
    && approval.proposal.fileSha256 === digest(proposalBytes)
    && approval.approvedOperation === base.inheritedF04Bindings.approvedOperation
    && JSON.stringify(approval.approvedMutationScope) === JSON.stringify(base.inheritedF04Bindings.approvedMutationScope)
    && JSON.stringify(approval.security) === JSON.stringify(base.inheritedF04Bindings.exactSecurity);
  fixtureResults.push({ id: fixture.id, expectedCanonical, actualCanonical: proposal.sceneSpec.canonicalSha256, pass });
}
checks.c1TypedFixturesPass = fixtureResults.every((item) => item.pass);

checks.allInheritedFileObservationsRemainExact = failed.observations.engineFiles.every((item) => item.pass)
  && failed.observations.inheritedFileIdentities.every((item) => item.pass);
checks.futureProtocolRemainsClosed = base.futureFormalPb2Protocol.status === 'FROZEN_BUT_NOT_AUTHORIZED_TO_EXECUTE'
  && base.futureFormalPb2Protocol.maximumBlenderStarts === 0
  && base.futureFormalPb2Protocol.engineSourceEdits === 0
  && base.futureFormalPb2Protocol.engineRemoteWrites === 0;
checks.currentStateStillClosed = state.phaseBPreparation.activeCorrection.status === 'PB1_CLOSED_PASS'
  && state.phaseBPreparation.activeCorrection.nextGate === 'PB.2'
  && state.phaseBPreparation.activeCorrection.nextGateStatus === 'NOT_STARTED_UNAUTHORIZED'
  && state.phaseBPreparation.activeCorrection.pb2ThroughPb7Authorized === false;

const passed = Object.values(checks).filter(Boolean).length;
const total = Object.keys(checks).length;
const body = {
  schemaVersion: 'bfs.aiNativeStudioPb2ReadinessAuditC1.v0.2',
  auditId: 'PB2-READINESS-C1-2026-08-31-MAC-M2MAX-ATTEMPT-02',
  status: passed === total ? 'PASS' : 'FAIL',
  mode: 'READ_ONLY_C1_NO_PB2_EXECUTION',
  correction: { uri: correctionUri, sha256: digest(await bytes(correctionUri)) },
  retainedAttempt01: correction.retainedAttempt01,
  checks,
  counts: {
    passed,
    total,
    combinedReadinessPassed: passed === total ? 19 : 16,
    combinedReadinessTotal: 19,
    blenderStarts: 0,
    renders: 0,
    proposalsExecuted: 0,
    buildPlanFilesWritten: 0,
    engineSourceEdits: 0,
    engineRemoteWrites: 0,
    networkCalls: 0,
  },
  observations: {
    fixtureResults,
    engineHead: git(['rev-parse', 'HEAD'], source),
    engineStatus: git(['status', '--porcelain=v1'], source),
    acceptedF04ReceiptHash: acceptedVerdict.receiptHash,
  },
  claimCeiling: correction.claimCeiling,
};
body.auditHash = digest(Buffer.from(JSON.stringify(body)));
const outputPath = resolve(root, outputUri);
await mkdir(dirname(outputPath), { recursive: true });
await writeFile(outputPath, JSON.stringify(body, null, 2) + '\n', { flag: 'wx' });
console.log(`PB2_READINESS_C1 ${body.status} ${passed}/${total} combined=${body.counts.combinedReadinessPassed}/19 auditHash=${body.auditHash}`);
if (body.status !== 'PASS') process.exitCode = 1;
