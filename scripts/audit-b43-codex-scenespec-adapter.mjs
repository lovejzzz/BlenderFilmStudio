import { access, readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { compileBuildPlan } from './compile-build-plan.mjs';
import { canonicalJson, repositoryRoot, validateSceneSpec } from './lib/scene-spec.mjs';
import {
  analyzeB43Evidence, createProposalValidator, hashB43Evidence, readB43Spec,
  runB43Attacks, sha256File, validateProposal, verifyFrozenInputs,
} from './lib/b43-codex-scenespec-adapter.mjs';

const outputRoot = resolve(repositoryRoot, 'experiments/codex-scenespec-adapter-derivation-v0-1');
const result = JSON.parse(await readFile(resolve(outputRoot, 'results.json'), 'utf8'));
const spec = await readB43Spec();
const frozenInputObservations = await verifyFrozenInputs(spec);
const frozenInputsMatch = frozenInputObservations.every(item => item.match);
const proposalValidator = await createProposalValidator(spec);
const toolObservations = Object.fromEntries(await Promise.all(Object.entries(result.tools).map(async ([key, item]) => {
  const observedSha256 = await sha256File(resolve(repositoryRoot, item.uri)).catch(() => null);
  return [key, { uri: item.uri, expectedSha256: item.sha256, observedSha256, match: observedSha256 === item.sha256 }];
})));
const toolsMatch = Object.values(toolObservations).every(item => item.match);

const caseObservations = [];
for (const expected of spec.expectedProposals) {
  const record = result.cases.find(item => item.briefId === expected.briefId);
  const proposalPath = resolve(repositoryRoot, record.proposalUri);
  const proposal = JSON.parse(await readFile(proposalPath, 'utf8'));
  let semanticValid = false;
  try { semanticValid = (await validateProposal(proposal, expected.briefId, spec, proposalValidator)).valid; } catch { semanticValid = false; }
  const observation = {
    briefId: expected.briefId,
    proposalSchemaValid: proposalValidator(proposal),
    proposalSemanticValid: semanticValid,
    proposalOracleExact: canonicalJson(proposal) === canonicalJson(expected),
    proposalFileHashMatch: await sha256File(proposalPath) === record.proposalFileSha256,
  };
  if (expected.decision === 'ACCEPT') {
    const scenePath = resolve(repositoryRoot, record.sceneSpecUri);
    const planPath = resolve(repositoryRoot, record.buildPlanUri);
    const scene = JSON.parse(await readFile(scenePath, 'utf8'));
    const observedPlanBytes = await readFile(planPath, 'utf8');
    const independentlyCompiled = `${JSON.stringify(await compileBuildPlan(scenePath), null, 2)}\n`;
    Object.assign(observation, {
      sceneSpecValid: validateSceneSpec(scene).valid,
      sceneFileHashMatch: await sha256File(scenePath) === record.sceneSpecFileSha256,
      planFileHashMatch: await sha256File(planPath) === record.buildPlanFileSha256,
      planReplayByteEqual: independentlyCompiled === observedPlanBytes,
    });
  } else {
    const forbidden = spec.materializations.filter(item => item.briefId === expected.briefId).flatMap(item => [item.outputSceneUri, item.outputPlanUri]);
    let forbiddenFiles = 0;
    for (const uri of forbidden) {
      try { await access(resolve(repositoryRoot, uri)); forbiddenFiles += 1; } catch {}
    }
    Object.assign(observation, { rejectedOutputCountsExact: record.sceneSpecCount === 0 && record.buildPlanCount === 0 && forbiddenFiles === 0 });
  }
  caseObservations.push(observation);
}
const artifactsMatch = caseObservations.every(item => item.proposalSchemaValid && item.proposalSemanticValid && item.proposalOracleExact && item.proposalFileHashMatch
  && (item.sceneSpecValid === undefined || (item.sceneSpecValid && item.sceneFileHashMatch && item.planFileHashMatch && item.planReplayByteEqual))
  && (item.rejectedOutputCountsExact === undefined || item.rejectedOutputCountsExact));
const attacks = await runB43Attacks(spec);
const attacksMatch = canonicalJson(attacks) === canonicalJson(result.attacks) && attacks.every(item => item.passed);
const analysis = analyzeB43Evidence(result, spec);
const selfHashMatch = result.evidenceHash === hashB43Evidence(result);
const audit = {
  schemaVersion: 'bfs.codexSceneSpecAdapterDerivationIndependentAudit.v0.1',
  experimentId: 'B43-D1',
  analysis,
  frozenInputsMatch,
  toolsMatch,
  toolObservations,
  artifactsMatch,
  caseObservations,
  attacksMatch,
  attacks,
  selfHashMatch,
  prohibitedOperationCountsExact: Object.values(result.operations).every(value => value === 0),
};
audit.passed = audit.analysis.passed && audit.frozenInputsMatch && audit.toolsMatch && audit.artifactsMatch
  && audit.attacksMatch && audit.selfHashMatch && audit.prohibitedOperationCountsExact;
await writeFile(resolve(outputRoot, 'audit.json'), `${JSON.stringify(audit, null, 2)}\n`);
process.stdout.write(`BFS_B43_D1_AUDIT ${audit.passed ? 'PASS' : 'FAIL'} tools=${toolsMatch ? 'MATCH' : 'MISMATCH'} artifacts=${artifactsMatch ? 'MATCH' : 'MISMATCH'} attacks=${attacks.filter(item => item.passed).length}/${attacks.length}\n`);
if (!audit.passed) process.exitCode = 1;

