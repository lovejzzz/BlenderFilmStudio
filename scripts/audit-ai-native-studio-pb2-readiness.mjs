#!/usr/bin/env node

import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { mkdir, readFile, stat, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const repositoryRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const contractUri = 'specs/ai-native-studio-pb2-readiness-preregistration.v0.1.json';
const defaultOutput = 'experiments/ai-native-studio-phase-b/PB.2-readiness-2026-08-31-mac-m2max-attempt-01/audit.json';
const outputUri = process.argv[2] || defaultOutput;
const outputPath = resolve(repositoryRoot, outputUri);

function sha256(bytes) {
  return createHash('sha256').update(bytes).digest('hex');
}

async function json(uri) {
  return JSON.parse(await readFile(resolve(repositoryRoot, uri), 'utf8'));
}

async function fileIdentity(root, record) {
  const path = resolve(root, record.uri);
  const bytes = await readFile(path);
  const metadata = await stat(path);
  return {
    uri: record.uri,
    expectedSha256: record.sha256 || record.sceneSpecFileSha256 || record.proposalFileSha256 || record.approvalFileSha256,
    actualSha256: sha256(bytes),
    expectedBytes: record.bytes ?? null,
    actualBytes: metadata.size,
  };
}

function git(args, cwd) {
  return execFileSync('git', args, { cwd, encoding: 'utf8' }).trim();
}

function exactKeys(value, keys) {
  return JSON.stringify(Object.keys(value).sort()) === JSON.stringify([...keys].sort());
}

const contract = await json(contractUri);
const currentState = await json('handoff/ai-native-studio-current-state.v0.1.json');
const source = contract.engineSourceReadOnlyBinding.retainedSourceRoot;
const checks = {};
const observations = {};

checks.contractStatusReadinessOnly = contract.status === 'PREREGISTERED_READINESS_ONLY_PB2_NOT_AUTHORIZED';
checks.authorizationIsReadOnly = contract.authorization.researchRepositoryWrites === true
  && contract.authorization.pb2FormalExecution === false
  && contract.authorization.engineSourceMutation === false
  && contract.authorization.engineRemoteWrite === false
  && contract.authorization.blenderStarts === 0
  && contract.authorization.renders === 0
  && contract.authorization.networkCalls === 0
  && contract.authorization.beginPb3ThroughPb7 === false;
checks.parentResearchCommitExact = git(['rev-parse', 'HEAD'], repositoryRoot) === contract.parentResearchCommit;
checks.currentStatePb1Pass = currentState.status === 'F0_COMPLETE_REPOSITORY_PUBLICATION_C1_PASS_PB1_VALIDATION_PASS'
  && currentState.phaseBPreparation.activeCorrection.status === 'PB1_CLOSED_PASS';
checks.currentStatePb2StillUnauthorized = currentState.phaseBPreparation.pb2ThroughPb7Authorized === false
  && currentState.phaseBPreparation.activeCorrection.pb2ThroughPb7Authorized === false
  && currentState.phaseBPreparation.activeCorrection.nextGate === 'PB.2'
  && currentState.phaseBPreparation.activeCorrection.nextGateStatus === 'NOT_STARTED_UNAUTHORIZED';
checks.pb1HashesExact = currentState.phaseBPreparation.attempt04.buildReceiptHash === contract.pb1AcceptedBinding.attempt04BuildReceiptHash
  && currentState.phaseBPreparation.attempt04.binarySha256 === contract.pb1AcceptedBinding.binarySha256
  && currentState.phaseBPreparation.acceptedRecovery.runtimeReceiptHash === contract.pb1AcceptedBinding.runtimeRecoveryReceiptHash
  && currentState.phaseBPreparation.acceptedRecovery.verdictReceiptHash === contract.pb1AcceptedBinding.runtimeRecoveryVerdictHash
  && currentState.phaseBPreparation.acceptedRecovery.acceptedAuditReceiptHash === contract.pb1AcceptedBinding.runtimeRecoveryAuditHash;

observations.engineHead = git(['rev-parse', 'HEAD'], source);
observations.engineStatus = git(['status', '--porcelain=v1'], source);
checks.engineHeadExact = observations.engineHead === contract.engineSourceReadOnlyBinding.requiredHead;
checks.engineWorktreeClean = observations.engineStatus === '';

const engineFiles = [];
for (const record of contract.engineSourceReadOnlyBinding.files) {
  const identity = await fileIdentity(source, record);
  identity.expectedGitBlobOid = record.gitBlobOid;
  identity.actualGitBlobOid = git(['rev-parse', `${contract.engineSourceReadOnlyBinding.requiredHead}:${record.uri}`], source);
  identity.pass = identity.actualSha256 === identity.expectedSha256
    && identity.actualBytes === identity.expectedBytes
    && identity.actualGitBlobOid === identity.expectedGitBlobOid;
  engineFiles.push(identity);
}
observations.engineFiles = engineFiles;
checks.engineFilesExact = engineFiles.every((item) => item.pass);

const contractSource = await readFile(resolve(source, 'scripts/modules/film_studio_contract.py'), 'utf8');
const bridgeSource = await readFile(resolve(source, 'scripts/startup/bl_operators/film_studio_workspace.py'), 'utf8');
checks.contractDeclaresNoBpyDependency = contractSource.includes('This module deliberately has no bpy dependency.');
checks.contractSecurityExact = contractSource.includes('exact_security = {"networkAccess": False, "arbitraryPython": False, "sceneMutation": False}')
  && contractSource.includes('APPROVED_OPERATION = "COMPILE_BUILD_PLAN"')
  && contractSource.includes('APPROVED_SCOPE = ["WRITE_BUILD_PLAN"]');
checks.contractInspectionRequired = contractSource.includes('raise ContractError("INSPECTION_REQUIRED"')
  && contractSource.includes('os.O_WRONLY | os.O_CREAT | os.O_EXCL');
checks.noDynamicProposalExecutionSurface = !/(^|\W)(eval|exec)\s*\(/m.test(contractSource)
  && !/(subprocess|socket|urllib|requests|http\.client)/.test(contractSource);
checks.bridgeSeparatesInspectAndExecute = bridgeSource.includes('class FILMSTUDIO_OT_inspect_contract')
  && bridgeSource.includes('class FILMSTUDIO_OT_execute_contract')
  && bridgeSource.includes('state.contract_status == "APPROVED_READY" and state.contract_inspection_token');

const inheritedIdentities = [];
const inheritedRecords = [
  { uri: contract.inheritedF04Bindings.acceptedRoot + '/verdict.json', sha256: contract.inheritedF04Bindings.acceptedVerdictFileSha256 },
  { uri: contract.inheritedF04Bindings.acceptedRoot + '/audit.json', sha256: contract.inheritedF04Bindings.acceptedAuditFileSha256 },
  ...contract.inheritedF04Bindings.supportingFiles,
];
for (const fixture of contract.inheritedF04Bindings.fixtures) {
  inheritedRecords.push(
    { uri: fixture.sceneSpecUri, sha256: fixture.sceneSpecFileSha256 },
    { uri: fixture.proposalUri, sha256: fixture.proposalFileSha256 },
    { uri: fixture.approvalUri, sha256: fixture.approvalFileSha256 },
  );
}
for (const record of inheritedRecords) {
  const identity = await fileIdentity(repositoryRoot, record);
  identity.pass = identity.actualSha256 === identity.expectedSha256;
  inheritedIdentities.push(identity);
}
observations.inheritedFileIdentities = inheritedIdentities;
checks.inheritedFilesExact = inheritedIdentities.every((item) => item.pass);

const acceptedVerdict = await json(contract.inheritedF04Bindings.acceptedRoot + '/verdict.json');
checks.f04AcceptedVerdictExact = acceptedVerdict.status === 'PASS'
  && acceptedVerdict.verdictHash === contract.inheritedF04Bindings.acceptedVerdictReceiptHash
  && acceptedVerdict.checks.productAcceptsFrozenSceneSpecWithoutArbitraryGeneratedPython === true
  && acceptedVerdict.checks.proposalDiffAndApprovalScopeInspectedBeforeExecution === true
  && acceptedVerdict.checks.unapprovedMutationRejectedBeforeMutation === true
  && acceptedVerdict.checks.allRequiredAcceptanceCriteriaPassed === true;

const typedFixtures = [];
for (const fixture of contract.inheritedF04Bindings.fixtures) {
  const proposal = await json(fixture.proposalUri);
  const approval = await json(fixture.approvalUri);
  const proposalHash = sha256(await readFile(resolve(repositoryRoot, fixture.proposalUri)));
  const pass = proposal.schemaVersion === contract.inheritedF04Bindings.proposalVersion
    && proposal.decision === 'PROPOSE'
    && proposal.sceneSpec.uri === fixture.sceneSpecUri
    && proposal.sceneSpec.fileSha256 === fixture.sceneSpecFileSha256
    && proposal.sceneSpec.canonicalSha256 === fixture.sceneSpecCanonicalSha256
    && proposal.requestedOperation === contract.inheritedF04Bindings.approvedOperation
    && JSON.stringify(proposal.requestedMutationScope) === JSON.stringify(contract.inheritedF04Bindings.approvedMutationScope)
    && JSON.stringify(proposal.security) === JSON.stringify(contract.inheritedF04Bindings.exactSecurity)
    && approval.schemaVersion === contract.inheritedF04Bindings.approvalVersion
    && approval.decision === 'APPROVED'
    && approval.proposal.uri === fixture.proposalUri
    && approval.proposal.fileSha256 === proposalHash
    && approval.approvedOperation === contract.inheritedF04Bindings.approvedOperation
    && JSON.stringify(approval.approvedMutationScope) === JSON.stringify(contract.inheritedF04Bindings.approvedMutationScope)
    && JSON.stringify(approval.security) === JSON.stringify(contract.inheritedF04Bindings.exactSecurity)
    && exactKeys(proposal.security, ['networkAccess', 'arbitraryPython', 'sceneMutation']);
  typedFixtures.push({ id: fixture.id, proposalHash, planHash: fixture.planHash, pass });
}
observations.typedFixtures = typedFixtures;
checks.typedFixturesExact = typedFixtures.every((item) => item.pass);

const negativeSpec = await json('experiments/ai-native-studio-f0/F0.4-2026-08-30-mac-m2max-attempt-01/negative-fixture-spec.json');
const negativeEvidence = await json('experiments/ai-native-studio-f0/F0.4-2026-08-30-mac-m2max-attempt-01/negative-fixtures.json');
const requiredInheritedCases = ['N_UNKNOWN_FIELD', 'N_PATH_ESCAPE', 'N_NONFINITE', 'N_UNAPPROVED_MUTATION'];
checks.inheritedNegativeCasesExact = JSON.stringify(negativeSpec.cases.map((item) => item.id)) === JSON.stringify(requiredInheritedCases)
  && negativeEvidence.status === 'PASS'
  && negativeEvidence.sceneFingerprintExact === true
  && negativeEvidence.cases.length === requiredInheritedCases.length
  && negativeEvidence.cases.every((item) => item.passed === true
    && item.buildPlanFilesWritten === 0
    && item.sceneMutations === 0
    && item.sceneCompilerProcessesStarted === 0
    && item.networkCalls === 0
    && item.arbitraryPythonFromProposalExecuted === 0);

const future = contract.futureFormalPb2Protocol;
checks.futureProtocolFrozenButClosed = future.status === 'FROZEN_BUT_NOT_AUTHORIZED_TO_EXECUTE'
  && future.positiveCases.length === 2
  && future.negativeCases.length === 8
  && future.maximumBlenderStarts === 0
  && future.maximumRenders === 0
  && future.engineSourceEdits === 0
  && future.engineRemoteWrites === 0
  && Object.values(future.requiredZeroCountsForEveryNegative).every((value) => value === 0);

const passed = Object.values(checks).filter(Boolean).length;
const total = Object.keys(checks).length;
const body = {
  schemaVersion: 'bfs.aiNativeStudioPb2ReadinessAudit.v0.1',
  auditId: 'PB2-READINESS-2026-08-31-MAC-M2MAX-ATTEMPT-01',
  status: passed === total ? 'PASS' : 'FAIL',
  mode: 'READ_ONLY_INVENTORY_NO_PB2_EXECUTION',
  contract: {
    uri: contractUri,
    sha256: sha256(await readFile(resolve(repositoryRoot, contractUri))),
  },
  parentResearchCommit: contract.parentResearchCommit,
  checks,
  counts: {
    passed,
    total,
    blenderStarts: 0,
    renders: 0,
    proposalsExecuted: 0,
    buildPlanFilesWritten: 0,
    engineSourceEdits: 0,
    engineRemoteWrites: 0,
    networkCalls: 0,
  },
  observations,
  claimCeiling: contract.claimCeiling,
};
body.auditHash = sha256(Buffer.from(JSON.stringify(body)));
await mkdir(dirname(outputPath), { recursive: true });
await writeFile(outputPath, JSON.stringify(body, null, 2) + '\n', { flag: 'wx' });
console.log(`PB2_READINESS ${body.status} ${passed}/${total} auditHash=${body.auditHash}`);
if (body.status !== 'PASS') process.exitCode = 1;
