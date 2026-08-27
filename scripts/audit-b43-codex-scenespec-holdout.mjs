import { readFile, readdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { canonicalJson, repositoryRoot, sha256 } from './lib/scene-spec.mjs';
import { createProposalValidator, readB43Spec, validateProposal } from './lib/b43-codex-scenespec-adapter.mjs';
import {
  analyzeB43HoldoutEvidence, hashB43HoldoutEvidence, inspectB43EventStream,
  readB43HoldoutSpec, renderB43Prompt, runB43HoldoutAttacks, sha256File,
  verifyB43HoldoutFiles,
} from './lib/b43-codex-scenespec-holdout.mjs';

const outputRoot = resolve(repositoryRoot, 'experiments/codex-scenespec-holdout-v0-1');
const result = JSON.parse(await readFile(resolve(outputRoot, 'results.json'), 'utf8'));
const spec = await readB43HoldoutSpec();
const derivationSpec = await readB43Spec();
const validator = await createProposalValidator(derivationSpec);
const frozenFileObservations = await verifyB43HoldoutFiles(spec);
const frozenFilesMatch = frozenFileObservations.every(item => item.match);
const template = await readFile(resolve(repositoryRoot, spec.frozenInputs.promptTemplate.uri), 'utf8');
const catalog = JSON.parse(await readFile(resolve(repositoryRoot, spec.frozenInputs.presetCatalog.uri), 'utf8'));
const toolObservations = Object.fromEntries(await Promise.all(Object.entries(result.tools).map(async ([key, item]) => {
  const observedSha256 = await sha256File(resolve(repositoryRoot, item.uri)).catch(() => null);
  return [key, { uri: item.uri, expectedSha256: item.sha256, observedSha256, match: observedSha256 === item.sha256 }];
})));
const toolsMatch = Object.values(toolObservations).every(item => item.match);
const invocationObservations = [];
for (const record of result.invocations) {
  const briefRecord = spec.frozenInputs.briefs.find(item => item.id === record.briefId);
  const intent = JSON.parse(await readFile(resolve(repositoryRoot, briefRecord.uri), 'utf8'));
  const expectedPrompt = renderB43Prompt(template, catalog, intent, spec);
  const promptPath = resolve(repositoryRoot, record.promptUri);
  const eventPath = resolve(repositoryRoot, record.eventsUri);
  const proposalPath = resolve(repositoryRoot, record.proposalUri);
  const proposal = JSON.parse(await readFile(proposalPath, 'utf8'));
  const goldenRecord = spec.frozenInputs.goldenProposals.find(item => item.id === record.briefId);
  const golden = JSON.parse(await readFile(resolve(repositoryRoot, goldenRecord.uri), 'utf8'));
  let semanticValid = false;
  try { semanticValid = (await validateProposal(proposal, record.briefId, derivationSpec, validator)).valid; } catch {}
  const eventText = await readFile(eventPath, 'utf8');
  const eventStream = inspectB43EventStream(eventText, spec.invocation.forbiddenItemTypes);
  invocationObservations.push({
    invocationId: record.invocationId,
    promptByteExact: (await readFile(promptPath, 'utf8')) === expectedPrompt && await sha256File(promptPath) === record.promptSha256,
    eventsHashMatch: await sha256File(eventPath) === record.eventsSha256,
    eventStreamExact: canonicalJson(eventStream) === canonicalJson(record.eventStream),
    proposalFileHashMatch: await sha256File(proposalPath) === record.proposalSha256,
    proposalCanonicalHashMatch: sha256(canonicalJson(proposal)) === record.proposalCanonicalSha256,
    proposalSchemaValid: validator(proposal),
    proposalSemanticValid: semanticValid,
    proposalOracleExact: canonicalJson(proposal) === canonicalJson(golden),
    workingDirectoryEntriesExact: canonicalJson(await readdir(resolve(repositoryRoot, record.workingDirectoryUri))) === canonicalJson(record.workingDirectoryEntriesAfter),
  });
}
const artifactsMatch = invocationObservations.every(item => Object.entries(item).every(([key, value]) => key === 'invocationId' || value === true));
const attacks = runB43HoldoutAttacks(result, spec);
const attacksMatch = canonicalJson(attacks) === canonicalJson(result.attacks) && attacks.every(item => item.passed);
const analysis = analyzeB43HoldoutEvidence(result, spec);
const audit = {
  schemaVersion: 'bfs.codexSceneSpecHoldoutIndependentAudit.v0.1',
  experimentId: 'B43',
  analysis,
  frozenFilesMatch,
  frozenFileObservations,
  toolsMatch,
  toolObservations,
  artifactsMatch,
  invocationObservations,
  attacksMatch,
  attacks,
  evidenceSelfHashMatch: result.evidenceHash === hashB43HoldoutEvidence(result),
  exactProposalCount: invocationObservations.filter(item => item.proposalOracleExact).length,
  forbiddenToolEventCount: result.invocations.reduce((sum, item) => sum + item.eventStream.forbiddenItemCount, 0),
};
audit.passed = analysis.passed && frozenFilesMatch && toolsMatch && artifactsMatch && attacksMatch && audit.evidenceSelfHashMatch
  && audit.exactProposalCount === spec.runOrder.length && audit.forbiddenToolEventCount === 0;
await writeFile(resolve(outputRoot, 'audit.json'), `${JSON.stringify(audit, null, 2)}\n`);
process.stdout.write(`BFS_B43_AUDIT ${audit.passed ? 'PASS' : 'FAIL'} exact=${audit.exactProposalCount}/${spec.runOrder.length} tools=${audit.forbiddenToolEventCount} attacks=${attacks.filter(item => item.passed).length}/${attacks.length}\n`);
if (!audit.passed) process.exitCode = 1;

