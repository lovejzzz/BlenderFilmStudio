import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { canonicalJson, repositoryRoot, sha256 } from './lib/scene-spec.mjs';
import { createProposalValidator, materializeSceneSpec, readB43Spec, validateProposal } from './lib/b43-codex-scenespec-adapter.mjs';
import { observeSuccessfulRun } from './lib/b42-linux-amd64-compiler-repro.mjs';
import { analyzeB44Evidence, hashB44Evidence, readB44Spec, runB44Attacks } from './lib/b44-codex-to-blender-worker-promotion.mjs';
import { sha256File } from './lib/receipt-format.mjs';

const outputRoot = resolve(repositoryRoot, 'experiments/codex-to-blender-worker-promotion-v0-1');
const result = JSON.parse(await readFile(resolve(outputRoot, 'results.json'), 'utf8'));
const [spec, adapterSpec] = await Promise.all([readB44Spec(), readB43Spec()]);
const validator = await createProposalValidator(adapterSpec);

const parentObservations = [];
for (const parent of Object.values(spec.parents)) {
  for (const [uri, expectedSha256] of [[parent.resultUri, parent.resultSha256], [parent.auditUri, parent.auditSha256]]) {
    const observedSha256 = await sha256File(resolve(repositoryRoot, uri)).catch(() => null);
    parentObservations.push({ uri, expectedSha256, observedSha256, match: observedSha256 === expectedSha256 });
  }
}
const parentsMatch = parentObservations.every(item => item.match) && canonicalJson(parentObservations) === canonicalJson(result.parentObservations);

const toolObservations = Object.fromEntries(await Promise.all(Object.entries(result.tools).map(async ([key, item]) => {
  const observedSha256 = await sha256File(resolve(repositoryRoot, item.uri)).catch(() => null);
  return [key, { uri: item.uri, expectedSha256: item.sha256, observedSha256, match: observedSha256 === item.sha256 }];
})));
const toolsMatch = Object.values(toolObservations).every(item => item.match);

const inputObservations = await Promise.all(result.inputObservations.map(async item => {
  const observedSha256 = await sha256File(resolve(repositoryRoot, item.uri)).catch(() => null);
  return { uri: item.uri, expectedSha256: item.expectedSha256, observedSha256, match: observedSha256 === item.expectedSha256 };
}));
const inputsMatch = inputObservations.every(item => item.match) && canonicalJson(inputObservations) === canonicalJson(result.inputObservations);

const proposalObservations = [];
for (const expected of spec.selectedProposals) {
  const recorded = result.proposals.find(item => item.id === expected.id);
  const text = await readFile(resolve(repositoryRoot, expected.uri), 'utf8');
  const proposal = JSON.parse(text);
  let semantic = null;
  let materializedCanonicalSha256 = null;
  try {
    semantic = await validateProposal(proposal, expected.briefId, adapterSpec, validator);
    if (semantic.materialize) materializedCanonicalSha256 = sha256(Buffer.from(canonicalJson((await materializeSceneSpec(proposal, adapterSpec, validator)).scene)));
  } catch {}
  proposalObservations.push({
    id: expected.id,
    fileHashMatch: sha256(Buffer.from(text)) === recorded.fileSha256 && recorded.fileSha256 === expected.fileSha256,
    canonicalHashMatch: sha256(Buffer.from(canonicalJson(proposal))) === recorded.canonicalSha256 && recorded.canonicalSha256 === expected.canonicalSha256,
    schemaValid: validator(proposal),
    semanticValid: semantic?.valid === true,
    materializationMatch: expected.decision === 'ACCEPT'
      ? semantic?.materialize === true && materializedCanonicalSha256 === expected.sceneSpec.canonicalSha256 && recorded.sceneSpec.materializedCanonicalSha256 === materializedCanonicalSha256
      : semantic?.materialize === false && recorded.sceneSpecCount === 0 && recorded.buildPlanCount === 0 && recorded.containerLaunchCount === 0,
  });
}
const proposalsMatch = proposalObservations.every(item => Object.entries(item).every(([key, value]) => key === 'id' || value === true));

const outputObservations = [];
for (const proposal of result.proposals.filter(item => item.decision === 'ACCEPT')) {
  for (const run of proposal.runs) {
    const observed = await observeSuccessfulRun(resolve(outputRoot, 'runs', run.id));
    outputObservations.push({ id: run.id, value: observed, match: canonicalJson(observed) === canonicalJson(run.observed) });
  }
}
const outputsMatch = outputObservations.length === 4 && outputObservations.every(item => item.match);
const attacks = runB44Attacks(result, spec);
const attacksMatch = canonicalJson(attacks) === canonicalJson(result.attacks) && attacks.every(item => item.passed);
const analysis = analyzeB44Evidence(result, spec);
const audit = {
  schemaVersion: 'bfs.codexToBlenderWorkerPromotionIndependentAudit.v0.1', experimentId: 'B44', analysis,
  parentsMatch, parentObservations, toolsMatch, toolObservations, inputsMatch, inputObservations,
  proposalsMatch, proposalObservations, outputsMatch, outputObservations,
  attacksMatch, attacks, evidenceSelfHashMatch: result.evidenceHash === hashB44Evidence(result),
};
audit.passed = analysis.passed && parentsMatch && toolsMatch && inputsMatch && proposalsMatch && outputsMatch && attacksMatch && audit.evidenceSelfHashMatch;
await writeFile(resolve(outputRoot, 'audit.json'), `${JSON.stringify(audit, null, 2)}\n`);
process.stdout.write(`BFS_B44_AUDIT ${audit.passed ? 'PASS' : 'FAIL'} parents=${parentsMatch ? 'MATCH' : 'MISMATCH'} proposals=${proposalsMatch ? 'MATCH' : 'MISMATCH'} outputs=${outputsMatch ? 'MATCH' : 'MISMATCH'} attacks=${attacks.filter(item => item.passed).length}/${attacks.length}\n`);
if (!audit.passed) process.exitCode = 1;
