import { spawn } from 'node:child_process';
import { mkdir, readFile, readdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { canonicalJson, repositoryRoot, sha256 } from './lib/scene-spec.mjs';
import { createProposalValidator, readB43Spec, validateProposal } from './lib/b43-codex-scenespec-adapter.mjs';
import {
  B43_PREREG_COMMIT, B43_SPEC_SHA256, analyzeB43HoldoutEvidence, hashB43HoldoutEvidence,
  inspectB43EventStream, readB43HoldoutSpec, renderB43Prompt, runB43HoldoutAttacks,
  sha256File, verifyB43HoldoutFiles,
} from './lib/b43-codex-scenespec-holdout.mjs';

const outputRoot = resolve(repositoryRoot, 'experiments/codex-scenespec-holdout-v0-1');
const rawRoot = resolve(outputRoot, 'raw');
const workRoot = resolve(outputRoot, 'work');
const serialize = value => `${JSON.stringify(value, null, 2)}\n`;

function childEnvironment(spec) {
  const env = {};
  for (const name of spec.invocation.environmentPolicy.allowNames) if (process.env[name] !== undefined) env[name] = process.env[name];
  Object.assign(env, spec.invocation.environmentPolicy.force);
  for (const name of spec.invocation.environmentPolicy.denyNames) delete env[name];
  return env;
}

function runProcess(command, args, { cwd, env, stdin = '', wallTimeMs, killGraceMs }) {
  return new Promise(resolveRun => {
    const started = Date.now();
    const child = spawn(command, args, { cwd, env, stdio: ['pipe', 'pipe', 'pipe'] });
    const stdout = [], stderr = [];
    let timeoutTriggered = false, termSent = false, killSent = false, killTimer;
    child.stdout.on('data', chunk => stdout.push(chunk));
    child.stderr.on('data', chunk => stderr.push(chunk));
    const timeout = setTimeout(() => {
      timeoutTriggered = true;
      termSent = child.kill('SIGTERM');
      killTimer = setTimeout(() => { killSent = child.kill('SIGKILL'); }, killGraceMs);
    }, wallTimeMs);
    child.on('error', error => stderr.push(Buffer.from(`${error.name}: ${error.message}\n`)));
    child.on('close', (exitCode, signal) => {
      clearTimeout(timeout);
      if (killTimer) clearTimeout(killTimer);
      resolveRun({ exitCode, signal, elapsedMs: Date.now() - started, timeoutTriggered, termSent, killSent, stdout: Buffer.concat(stdout), stderr: Buffer.concat(stderr), processId: child.pid });
    });
    child.stdin.end(stdin);
  });
}

await mkdir(outputRoot, { recursive: true });
const existing = await readdir(outputRoot);
if (existing.length > 0) throw new Error(`B43 output root is not empty: ${existing.join(', ')}`);
await mkdir(rawRoot);
await mkdir(workRoot);
const spec = await readB43HoldoutSpec();
const frozenFileObservations = await verifyB43HoldoutFiles(spec);
if (frozenFileObservations.some(item => !item.match)) throw new Error('B43 frozen file identity mismatch');
const cliSha256 = await sha256File(spec.codexIdentity.releaseExecutable);
if (cliSha256 !== spec.codexIdentity.releaseExecutableSha256) throw new Error(`B43 Codex executable mismatch: ${cliSha256}`);
const env = childEnvironment(spec);
const apiKeyEnvironmentPresent = spec.codexIdentity.requiredAbsentEnvironmentKeys.some(name => Object.hasOwn(env, name) || Object.hasOwn(process.env, name));
if (apiKeyEnvironmentPresent) throw new Error('B43 API key environment is present');
const preflightOptions = { cwd: repositoryRoot, env, stdin: '', wallTimeMs: 30000, killGraceMs: 5000 };
const versionRun = await runProcess(spec.codexIdentity.releaseExecutable, ['--version'], preflightOptions);
const loginRun = await runProcess(spec.codexIdentity.releaseExecutable, ['login', 'status'], preflightOptions);
const version = versionRun.stdout.toString('utf8').trim();
const authenticationStatus = `${loginRun.stdout.toString('utf8')}${loginRun.stderr.toString('utf8')}`.trim();
if (version !== spec.codexIdentity.version || authenticationStatus !== spec.codexIdentity.authenticationStatusExact) throw new Error(`B43 Codex preflight mismatch: ${version} / ${authenticationStatus}`);

const template = await readFile(resolve(repositoryRoot, spec.frozenInputs.promptTemplate.uri), 'utf8');
const catalog = JSON.parse(await readFile(resolve(repositoryRoot, spec.frozenInputs.presetCatalog.uri), 'utf8'));
const derivationSpec = await readB43Spec();
const proposalValidator = await createProposalValidator(derivationSpec);
const invocations = [];
const schemaPath = resolve(repositoryRoot, spec.frozenInputs.proposalSchema.uri);

for (const run of spec.runOrder) {
  const workDir = resolve(workRoot, run.invocationId);
  await mkdir(workDir);
  const workingDirectoryEmptyBefore = (await readdir(workDir)).length === 0;
  const briefRecord = spec.frozenInputs.briefs.find(item => item.id === run.briefId);
  const intent = JSON.parse(await readFile(resolve(repositoryRoot, briefRecord.uri), 'utf8'));
  const prompt = renderB43Prompt(template, catalog, intent, spec);
  const promptPath = resolve(rawRoot, `${run.invocationId}.prompt.txt`);
  const proposalPath = resolve(rawRoot, `${run.invocationId}.proposal.json`);
  const eventsPath = resolve(rawRoot, `${run.invocationId}.events.jsonl`);
  const stderrPath = resolve(rawRoot, `${run.invocationId}.stderr.log`);
  await writeFile(promptPath, prompt);
  const actualArgs = [
    'exec', '--ephemeral', '--ignore-user-config', '--ignore-rules', '--skip-git-repo-check',
    '--sandbox', 'read-only', '--model', spec.model.id, '--config', `model_reasoning_effort="${spec.model.reasoningEffort}"`,
    '--color', 'never', '--output-schema', schemaPath, '--output-last-message', proposalPath, '--json', '-',
  ];
  const argvPolicyExact = canonicalJson(actualArgs.slice(1).map(value => value === schemaPath ? '<ABSOLUTE_FROZEN_PROPOSAL_SCHEMA>' : value === proposalPath ? '<ABSOLUTE_INVOCATION_PROPOSAL_OUTPUT>' : value))
    === canonicalJson(spec.invocation.argvAfterCommandBeforePrompt);
  const processResult = await runProcess(spec.codexIdentity.releaseExecutable, actualArgs, {
    cwd: workDir, env, stdin: prompt, wallTimeMs: spec.invocation.wallTimeMs, killGraceMs: spec.invocation.killGraceMs,
  });
  await writeFile(eventsPath, processResult.stdout);
  await writeFile(stderrPath, processResult.stderr);
  const eventStream = inspectB43EventStream(processResult.stdout.toString('utf8'), spec.invocation.forbiddenItemTypes);
  let proposal = null, proposalParseError = null, proposalSchemaValid = false, proposalSemanticValid = false, proposalOracleExact = false;
  try {
    proposal = JSON.parse(await readFile(proposalPath, 'utf8'));
    proposalSchemaValid = proposalValidator(proposal);
    try { proposalSemanticValid = (await validateProposal(proposal, run.briefId, derivationSpec, proposalValidator)).valid; } catch {}
    const goldenRecord = spec.frozenInputs.goldenProposals.find(item => item.id === run.briefId);
    const golden = JSON.parse(await readFile(resolve(repositoryRoot, goldenRecord.uri), 'utf8'));
    proposalOracleExact = canonicalJson(proposal) === canonicalJson(golden);
  } catch (error) { proposalParseError = `${error.name}: ${error.message}`; }
  invocations.push({
    invocationId: run.invocationId,
    briefId: run.briefId,
    replicate: run.replicate,
    workingDirectoryUri: `experiments/codex-scenespec-holdout-v0-1/work/${run.invocationId}`,
    workingDirectoryEmptyBefore,
    workingDirectoryEntriesAfter: await readdir(workDir),
    argvPolicyExact,
    promptUri: `experiments/codex-scenespec-holdout-v0-1/raw/${run.invocationId}.prompt.txt`,
    promptSha256: await sha256File(promptPath),
    eventsUri: `experiments/codex-scenespec-holdout-v0-1/raw/${run.invocationId}.events.jsonl`,
    eventsSha256: await sha256File(eventsPath),
    stderrUri: `experiments/codex-scenespec-holdout-v0-1/raw/${run.invocationId}.stderr.log`,
    stderrSha256: await sha256File(stderrPath),
    proposalUri: `experiments/codex-scenespec-holdout-v0-1/raw/${run.invocationId}.proposal.json`,
    proposalSha256: proposal ? await sha256File(proposalPath) : null,
    proposalCanonicalSha256: proposal ? sha256(canonicalJson(proposal)) : null,
    proposal,
    proposalParseError,
    proposalSchemaValid,
    proposalSemanticValid,
    proposalOracleExact,
    eventStream,
    process: {
      processId: processResult.processId,
      exitCode: processResult.exitCode,
      signal: processResult.signal,
      elapsedMs: processResult.elapsedMs,
      timeoutTriggered: processResult.timeoutTriggered,
      termSent: processResult.termSent,
      killSent: processResult.killSent,
    },
    sceneSpecCount: 0,
    buildPlanCount: 0,
    blenderInvocationCount: 0,
  });
}

const replicates = spec.frozenInputs.briefs.map(brief => {
  const records = invocations.filter(item => item.briefId === brief.id);
  return { briefId: brief.id, invocationIds: records.map(item => item.invocationId), proposalCanonicalSha256: records.map(item => item.proposalCanonicalSha256), exact: records.length === spec.model.replicatesPerBrief && new Set(records.map(item => item.proposalCanonicalSha256)).size === 1 && records.every(item => item.proposalCanonicalSha256 !== null) };
});
const toolUris = { library: 'scripts/lib/b43-codex-scenespec-holdout.mjs', runner: 'scripts/run-b43-codex-scenespec-holdout.mjs', audit: 'scripts/audit-b43-codex-scenespec-holdout.mjs', adapter: 'scripts/lib/b43-codex-scenespec-adapter.mjs' };
const tools = Object.fromEntries(await Promise.all(Object.entries(toolUris).map(async ([key, uri]) => [key, { uri, sha256: await sha256File(resolve(repositoryRoot, uri)) }])));
const evidence = {
  schemaVersion: 'bfs.codexSceneSpecHoldoutEvidence.v0.1',
  experimentId: 'B43',
  preregistration: { commit: B43_PREREG_COMMIT, specSha256: B43_SPEC_SHA256 },
  derivationAuthority: { resultSha256: spec.derivationAuthority.result.sha256, auditSha256: spec.derivationAuthority.audit.sha256, auditPassed: spec.derivationAuthority.audit.passed },
  toolFreezeCommit: (await readFile(resolve(repositoryRoot, '.git/refs/heads/main'), 'utf8')).trim(),
  tools,
  frozenFilesVerified: true,
  frozenFileObservations,
  codex: {
    command: spec.codexIdentity.releaseExecutable,
    releaseExecutableSha256: cliSha256,
    version,
    authenticationStatus,
    apiKeyEnvironmentPresent,
    modelId: spec.model.id,
    reasoningEffort: spec.model.reasoningEffort,
    commercialBoundary: spec.model.commercialBoundary,
    invocationPolicyHash: sha256(canonicalJson(spec.invocation)),
  },
  runOrder: spec.runOrder,
  invocations,
  replicates,
  operations: {
    codexInvocations: invocations.length,
    modelResponses: invocations.filter(item => item.proposal !== null).length,
    forbiddenToolEvents: invocations.reduce((sum, item) => sum + item.eventStream.forbiddenItemCount, 0),
    sceneSpecsCreated: 0,
    buildPlansCreated: 0,
    blenderInvocations: 0,
    containerInvocations: 0,
  },
  nonClaims: spec.explicitNonClaims,
};
evidence.evidenceHash = hashB43HoldoutEvidence(evidence);
evidence.attacks = runB43HoldoutAttacks(evidence, spec);
evidence.attacksPassed = evidence.attacks.filter(item => item.passed).length;
evidence.analysis = analyzeB43HoldoutEvidence(evidence, spec);
evidence.verdict = evidence.analysis.passed ? spec.acceptedVerdict : spec.rejectedVerdict;
await writeFile(resolve(outputRoot, 'results.json'), serialize(evidence));
process.stdout.write(`BFS_B43 ${evidence.verdict} exact=${invocations.filter(item => item.proposalOracleExact).length}/${invocations.length} tools=${evidence.operations.forbiddenToolEvents} attacks=${evidence.attacksPassed}/${evidence.attacks.length}\n`);
if (!evidence.analysis.passed) process.exitCode = 1;
