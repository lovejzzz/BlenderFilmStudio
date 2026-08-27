import { execFileSync } from 'node:child_process';
import { mkdir, readdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { compileBuildPlan } from './compile-build-plan.mjs';
import { canonicalJson, repositoryRoot, sha256, validateSceneSpec } from './lib/scene-spec.mjs';
import {
  B43_D1_PREREG_COMMIT, B43_D1_SPEC_SHA256, analyzeB43Evidence, createProposalValidator,
  hashB43Evidence, materializeSceneSpec, readB43Spec, runB43Attacks, sha256File,
  validateProposal, verifyFrozenInputs,
} from './lib/b43-codex-scenespec-adapter.mjs';

const outputRoot = resolve(repositoryRoot, 'experiments/codex-scenespec-adapter-derivation-v0-1');
const goldenRoot = resolve(outputRoot, 'golden');
const serialize = value => `${JSON.stringify(value, null, 2)}\n`;

await mkdir(outputRoot, { recursive: true });
const existing = await readdir(outputRoot);
if (existing.length > 0) throw new Error(`B43-D1 output root is not empty: ${existing.join(', ')}`);
await mkdir(goldenRoot);

const spec = await readB43Spec();
const frozenInputObservations = await verifyFrozenInputs(spec);
const proposalValidator = await createProposalValidator(spec);
const toolFreezeCommit = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: repositoryRoot, encoding: 'utf8' }).trim();
const toolUris = {
  library: 'scripts/lib/b43-codex-scenespec-adapter.mjs',
  runner: 'scripts/derive-b43-codex-scenespec-adapter.mjs',
  audit: 'scripts/audit-b43-codex-scenespec-adapter.mjs',
  planCompiler: 'scripts/compile-build-plan.mjs',
  sceneSpecLibrary: 'scripts/lib/scene-spec.mjs',
};
const tools = Object.fromEntries(await Promise.all(Object.entries(toolUris).map(async ([key, uri]) => [key, { uri, sha256: await sha256File(resolve(repositoryRoot, uri)) }])));

const cases = [];
for (const proposal of spec.expectedProposals) {
  const validation = await validateProposal(proposal, proposal.briefId, spec, proposalValidator);
  const proposalUri = `experiments/codex-scenespec-adapter-derivation-v0-1/golden/${proposal.briefId}.proposal.json`;
  const proposalPath = resolve(repositoryRoot, proposalUri);
  await writeFile(proposalPath, serialize(proposal));
  const record = {
    briefId: proposal.briefId,
    decision: proposal.decision,
    proposalUri,
    proposalFileSha256: await sha256File(proposalPath),
    proposalCanonicalSha256: sha256(canonicalJson(proposal)),
    proposalSchemaValid: proposalValidator(proposal),
    proposalSemanticValid: validation.valid,
    proposalOracleExact: canonicalJson(proposal) === canonicalJson(validation.expected),
  };
  if (validation.materialize) {
    const { scene, recipe } = await materializeSceneSpec(proposal, spec, proposalValidator);
    const scenePath = resolve(repositoryRoot, recipe.outputSceneUri);
    await writeFile(scenePath, serialize(scene));
    const planA = await compileBuildPlan(scenePath);
    const planB = await compileBuildPlan(scenePath);
    const planABytes = serialize(planA);
    const planBBytes = serialize(planB);
    await writeFile(resolve(repositoryRoot, recipe.outputPlanUri), planABytes);
    Object.assign(record, {
      sceneSpecCount: 1,
      buildPlanCount: 1,
      sceneSpecUri: recipe.outputSceneUri,
      sceneSpecFileSha256: await sha256File(scenePath),
      sceneSpecCanonicalSha256: sha256(canonicalJson(scene)),
      sceneSpecValid: validateSceneSpec(scene).valid,
      buildPlanUri: recipe.outputPlanUri,
      buildPlanFileSha256: await sha256File(resolve(repositoryRoot, recipe.outputPlanUri)),
      planHash: planA.planHash,
      buildPlansByteEqual: planABytes === planBBytes,
    });
  } else {
    Object.assign(record, { sceneSpecCount: 0, buildPlanCount: 0, sceneSpecValid: null, buildPlansByteEqual: null, planHash: null });
  }
  cases.push(record);
}

const attacks = await runB43Attacks(spec);
const evidence = {
  schemaVersion: 'bfs.codexSceneSpecAdapterDerivationEvidence.v0.1',
  experimentId: 'B43-D1',
  preregistration: { commit: B43_D1_PREREG_COMMIT, specSha256: B43_D1_SPEC_SHA256 },
  toolFreezeCommit,
  tools,
  frozenInputsVerified: true,
  frozenInputObservations,
  operations: { codex: 0, model: 0, blender: 0, container: 0, network: 0 },
  cases,
  nonClaims: spec.explicitNonClaims,
};
evidence.evidenceHash = hashB43Evidence(evidence);
evidence.attacks = attacks;
evidence.attacksPassed = attacks.filter(item => item.passed).length;
evidence.analysis = analyzeB43Evidence(evidence, spec);
evidence.verdict = evidence.analysis.passed ? spec.acceptedVerdict : spec.rejectedVerdict;
await writeFile(resolve(outputRoot, 'results.json'), serialize(evidence));
process.stdout.write(`BFS_B43_D1 ${evidence.verdict} cases=${cases.length} accepted=${cases.filter(item => item.decision === 'ACCEPT').length} attacks=${evidence.attacksPassed}/${attacks.length} operations=0\n`);
if (!evidence.analysis.passed) process.exitCode = 1;

