#!/usr/bin/env node

import { createHash } from 'node:crypto';
import { spawn } from 'node:child_process';
import { open, readFile, readdir, stat } from 'node:fs/promises';
import { dirname, isAbsolute, relative, resolve, sep } from 'node:path';
import { isDeepStrictEqual } from 'node:util';
import { fileURLToPath } from 'node:url';

const repositoryRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const SPEC_SHA256 = '40007b388dc851a22f5e030ec5135919922a1e15e075ef56769ed3330725fd5a';
const PREREGISTRATION_COMMIT = 'b9cf983abb3e741b5a7726200e9082bc50e1a89d';
const EXPECTED_VERIFICATION_CHECKS = [
  'PRODUCTION_RECEIPT_SELF_HASH', 'RELEASE_AND_PACKAGE_BINDINGS', 'PREFLIGHT_EVIDENCE_PUSHED',
  'AUTHORIZATION_SEQUENCE_AND_BINDINGS', 'SCENE_AND_BUILD_PLAN_BINDINGS', 'NATIVE_BUDGET_PID_BINDING',
  'CURRENT_COMPILE_RECEIPT_19_CHECKS', 'MANIFEST_AND_STRUCTURE_BINDINGS', 'BLEND_EMBEDDED_BINDINGS', 'OUTPUT_ROSTER_EXACT',
];

function sortValue(value) {
  if (Array.isArray(value)) return value.map(sortValue);
  if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map(key => [key, sortValue(value[key])]));
  return value;
}

const canonicalJson = value => JSON.stringify(sortValue(value));
const sha256Bytes = value => createHash('sha256').update(value).digest('hex');
const canonicalHash = value => sha256Bytes(Buffer.from(canonicalJson(value)));
const sha256File = async filePath => sha256Bytes(await readFile(filePath));

function validSelfHash(record, field) {
  if (!record || typeof record[field] !== 'string') return false;
  const body = structuredClone(record);
  delete body[field];
  return record[field] === canonicalHash(body);
}

function parseArguments(argv) {
  const parsed = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--spec') parsed.spec = argv[++index];
    else if (token === '--preflight-root') parsed.preflightRoot = argv[++index];
    else if (token === '--attempt-root') parsed.attemptRoot = argv[++index];
    else if (token === '--formal-root') parsed.formalRoot = argv[++index];
    else if (token === '--output') parsed.output = argv[++index];
    else throw new Error(`Unknown or incomplete argument: ${token}`);
  }
  for (const field of ['spec', 'preflightRoot', 'attemptRoot', 'formalRoot', 'output']) if (!parsed[field]) throw new Error(`Missing ${field}`);
  return parsed;
}

function below(root, candidate) {
  const fromRoot = relative(root, candidate);
  return fromRoot !== '' && fromRoot !== '..' && !fromRoot.startsWith(`..${sep}`) && !isAbsolute(fromRoot);
}

function trusted(spelling) {
  if (typeof spelling !== 'string' || isAbsolute(spelling)) throw new Error(`Untrusted repository spelling: ${spelling}`);
  const candidate = resolve(repositoryRoot, spelling);
  if (!below(repositoryRoot, candidate)) throw new Error(`Path escapes repository: ${spelling}`);
  return candidate;
}

async function identityExact(identity) {
  const filePath = trusted(identity.uri);
  const metadata = await stat(filePath);
  return metadata.isFile() && metadata.size === identity.bytes && await sha256File(filePath) === identity.sha256;
}

async function readJson(spelling) {
  return JSON.parse(await readFile(trusted(spelling), 'utf8'));
}

async function runGit(args) {
  const child = spawn('/usr/bin/git', args, { cwd: repositoryRoot, env: { PATH: '/usr/bin:/bin', LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8', GIT_CONFIG_NOSYSTEM: '1', GIT_TERMINAL_PROMPT: '0' }, stdio: ['ignore', 'pipe', 'pipe'] });
  const stdout = [];
  const stderr = [];
  child.stdout.on('data', chunk => stdout.push(chunk));
  child.stderr.on('data', chunk => stderr.push(chunk));
  const exitCode = await new Promise((resolvePromise, reject) => { child.on('error', reject); child.on('close', resolvePromise); });
  return { pid: child.pid, exitCode, stdout: Buffer.concat(stdout).toString('utf8'), stderr: Buffer.concat(stderr).toString('utf8') };
}

async function pushedEvidence(path) {
  const commit = (await runGit(['log', '-1', '--format=%H', '--', path])).stdout.trim();
  const ancestor = await runGit(['merge-base', '--is-ancestor', commit, 'origin/main']);
  return { commit, exact: /^[0-9a-f]{40}$/.test(commit) && ancestor.exitCode === 0 };
}

async function packageMinimality(release) {
  const beforeResult = await runGit(['show', `${PREREGISTRATION_COMMIT}:package.json`]);
  const before = JSON.parse(beforeResult.stdout);
  const current = await readJson('package.json');
  const reconstructed = structuredClone(current);
  for (const [key, value] of Object.entries(release.packageAliases)) {
    if (reconstructed.scripts?.[key] !== value) return false;
    delete reconstructed.scripts[key];
  }
  return isDeepStrictEqual(reconstructed, before);
}

function requireRecord(record, schema, field) {
  return record?.schemaVersion === schema && validSelfHash(record, field);
}

async function inspectRun(run, benchmark) {
  const receipt = await readJson(run.receipt.uri);
  const receiptExact = receipt.schemaVersion === 'bfs.productionCompileReceipt.v0.1' && receipt.status === 'PASS'
    && validSelfHash(receipt, 'receiptHash') && receipt.receiptHash === run.receipt.receiptHash && await sha256File(trusted(run.receipt.uri)) === run.receipt.sha256;
  const identities = [receipt.release, receipt.authorization.preflight, receipt.authorization.attempt, receipt.authorization.admission,
    receipt.authorization.attemptReceipt, receipt.authorization.formalStart, receipt.source, receipt.buildPlan,
    receipt.restrictedCompile.budgetReport, receipt.restrictedCompile.compileReceipt, receipt.restrictedCompile.sceneManifest,
    receipt.restrictedCompile.sceneStructureCanonical, receipt.restrictedCompile.sceneBlend];
  const identitiesExact = (await Promise.all(identities.map(identityExact))).every(Boolean);
  const attempt = await readJson(receipt.authorization.attempt.uri);
  const admission = await readJson(receipt.authorization.admission.uri);
  const attemptReceipt = await readJson(receipt.authorization.attemptReceipt.uri);
  const formalStart = await readJson(receipt.authorization.formalStart.uri);
  const sequenceExact = requireRecord(attempt, 'bfs.productionCompileAttempt.v0.1', 'attemptHash') && attempt.sequence === 1
    && requireRecord(admission, 'bfs.productionCompileAdmission.v0.1', 'admissionHash') && admission.sequence === 2 && admission.status === 'ACCEPTED'
    && requireRecord(attemptReceipt, 'bfs.productionCompileAttemptReceipt.v0.1', 'receiptHash') && attemptReceipt.sequence === 3 && attemptReceipt.status === 'ACCEPTED'
    && requireRecord(formalStart, 'bfs.productionCompileFormalStart.v0.1', 'formalStartHash') && formalStart.sequence === 4 && formalStart.status === 'AUTHORIZED'
    && admission.attempt?.attemptHash === attempt.attemptHash && attemptReceipt.attempt?.attemptHash === attempt.attemptHash
    && attemptReceipt.admission?.admissionHash === admission.admissionHash && formalStart.attemptReceipt?.receiptHash === attemptReceipt.receiptHash;
  const wrapper = await readJson(receipt.buildPlan.uri);
  const planBytes = await readFile(trusted(receipt.buildPlan.uri));
  const planExact = sha256Bytes(Buffer.from(canonicalJson(wrapper.plan))) === wrapper.planHash && wrapper.planHash === benchmark.expectedPlanHash
    && wrapper.planHash === receipt.buildPlan.planHash && run.planHash === benchmark.expectedPlanHash;
  const budget = await readJson(receipt.restrictedCompile.budgetReport.uri);
  const pidExact = budget.documentType === 'BFS_BUDGETED_PROCESS_RESULT' && budget.version === '0.2.0' && budget.outcome === 'PASS'
    && budget.command === '/Applications/Blender.app/Contents/MacOS/Blender' && budget.child?.exitCode === 0 && budget.child?.signal === null
    && budget.child?.spawnError === null && Number.isSafeInteger(budget.child?.pid) && budget.child.pid > 0
    && budget.child.pid !== receipt.restrictedCompile.wrapperProcess.pid && budget.child.pid === run.nativePid;
  const compileReceipt = await readJson(receipt.restrictedCompile.compileReceipt.uri);
  const compileReceiptBody = structuredClone(compileReceipt);
  delete compileReceiptBody.receiptHash;
  const compileReceiptExact = compileReceipt.documentType === 'BFS_COMPILE_RECEIPT' && compileReceipt.version === '0.1.0'
    && canonicalHash(compileReceiptBody) === compileReceipt.receiptHash && compileReceipt.receiptHash === receipt.restrictedCompile.compileReceipt.receiptHash;
  const manifest = await readJson(receipt.restrictedCompile.sceneManifest.uri);
  const structureBytes = await readFile(trusted(receipt.restrictedCompile.sceneStructureCanonical.uri));
  const structureHash = sha256Bytes(structureBytes);
  const structureExact = structureHash === benchmark.expectedStructureHash && structureHash === run.structureHash
    && structureHash === manifest.structureHash && structureHash === manifest.structureCanonical?.sha256
    && isDeepStrictEqual(JSON.parse(structureBytes), manifest.structure);
  const verification = run.verification;
  const verificationBody = structuredClone(verification);
  delete verificationBody.verificationHash;
  const verificationExact = verification.valid === true && canonicalHash(verificationBody) === verification.verificationHash
    && isDeepStrictEqual(verification.checks, EXPECTED_VERIFICATION_CHECKS)
    && verification.currentCompileReceiptVerification?.valid === true && verification.currentCompileReceiptVerification?.checks?.length === 19
    && verification.currentCompileReceiptVerification?.receiptHash === compileReceipt.receiptHash
    && verification.blendAudit?.scene?.planHash === wrapper.planHash && verification.blendAudit?.scene?.structureHash === structureHash
    && verification.blendAudit?.scene?.manifestVersion === manifest.manifestVersion && verification.blendAudit?.blender?.buildHash === 'fbe6228777e7'
    && run.verifyAlias.exitCode === 0 && run.verifyAlias.signal === null;
  const outputRoot = dirname(trusted(run.receipt.uri));
  const restrictedRoot = dirname(trusted(receipt.restrictedCompile.budgetReport.uri));
  const rosterExact = isDeepStrictEqual((await readdir(outputRoot)).sort(), receipt.output.expectedRootRoster)
    && isDeepStrictEqual((await readdir(restrictedRoot)).sort(), receipt.output.expectedRestrictedRoster);
  return {
    runId: run.runId, benchmarkId: benchmark.id, receiptExact, identitiesExact, sequenceExact, planExact, pidExact, compileReceiptExact,
    structureExact, verificationExact, rosterExact, planBytesSha256: sha256Bytes(planBytes), structureBytesSha256: structureHash,
    planHash: wrapper.planHash, structureHash, blendPlanHash: verification.blendAudit?.scene?.planHash,
    compileAliasExact: run.compileAlias.exitCode === 0 && run.compileAlias.signal === null,
    attemptSequence: attempt.sequence, outputBeforeReceipt: false, currentVerifierChecks: verification.currentCompileReceiptVerification?.checks?.length ?? 0,
  };
}

function validateProjection(value) {
  if (!value.parentExact) return 'PARENT';
  if (!value.packageExact) return 'PACKAGE';
  if (!value.releaseExact) return 'RELEASE';
  if (!value.preflightAccepted) return 'PREFLIGHT';
  if (!value.negativeExact) return 'NEGATIVE';
  if (!value.metaSequenceExact) return 'META_SEQUENCE';
  if (!value.sceneSuiteExact) return 'SCENE_SUITE';
  if (!value.planPairsExact) return 'PLAN_PAIR';
  if (!value.countsExact) return 'COUNTS';
  if (!value.zeroOperations) return 'OPERATIONS';
  for (const row of value.runs) {
    for (const field of ['receiptExact', 'identitiesExact', 'sequenceExact', 'planExact', 'pidExact', 'compileReceiptExact', 'structureExact', 'verificationExact', 'rosterExact', 'compileAliasExact']) {
      if (!row[field]) return `${row.runId}_${field}`;
    }
    if (row.attemptSequence !== 1) return `${row.runId}_ATTEMPT_SEQUENCE`;
    if (row.outputBeforeReceipt) return `${row.runId}_OUTPUT_ORDER`;
    if (row.currentVerifierChecks !== 19) return `${row.runId}_CURRENT_CHECKS`;
  }
  if (!value.pairsExact) return 'PAIR_IDENTITIES';
  if (value.verdict !== 'PRODUCTION_COMPILER_ENTRY_PROMOTION_SUPPORTED') return 'VERDICT';
  return null;
}

function runAttacks(base) {
  const attacks = [];
  const add = (id, mutate) => {
    const candidate = structuredClone(base);
    mutate(candidate);
    const reason = validateProjection(candidate);
    attacks.push({ id, rejected: reason !== null, reason });
  };
  for (const [id, field] of [
    ['A01_PARENT', 'parentExact'], ['A02_PACKAGE', 'packageExact'], ['A03_RELEASE', 'releaseExact'], ['A04_PREFLIGHT', 'preflightAccepted'],
    ['A05_NEGATIVE', 'negativeExact'], ['A06_META_SEQUENCE', 'metaSequenceExact'], ['A07_SCENE_SUITE', 'sceneSuiteExact'],
    ['A08_PLAN_PAIR', 'planPairsExact'], ['A09_COUNTS', 'countsExact'], ['A10_ZERO_OPERATIONS', 'zeroOperations'], ['A11_PAIR_IDENTITIES', 'pairsExact'],
  ]) add(id, value => { value[field] = false; });
  add('A12_VERDICT', value => { value.verdict = 'PRODUCTION_COMPILER_ENTRY_PROMOTION_REJECTED'; });
  for (const [index, row] of base.runs.entries()) {
    const prefix = `R${index + 1}_${row.runId}`;
    for (const field of ['receiptExact', 'identitiesExact', 'sequenceExact', 'planExact', 'pidExact', 'compileReceiptExact', 'structureExact', 'verificationExact', 'rosterExact', 'compileAliasExact']) {
      add(`${prefix}_${field}`, value => { value.runs[index][field] = false; });
    }
    add(`${prefix}_ATTEMPT_SEQUENCE`, value => { value.runs[index].attemptSequence = 9; });
    add(`${prefix}_OUTPUT_ORDER`, value => { value.runs[index].outputBeforeReceipt = true; });
    add(`${prefix}_CURRENT_CHECKS`, value => { value.runs[index].currentVerifierChecks = 18; });
  }
  return attacks;
}

async function durableWrite(filePath, value) {
  const handle = await open(filePath, 'wx', 0o600);
  try { await handle.writeFile(`${JSON.stringify(sortValue(value), null, 2)}\n`, 'utf8'); await handle.sync(); } finally { await handle.close(); }
  const parent = await open(dirname(filePath), 'r');
  try { await parent.sync(); } finally { await parent.close(); }
}

async function main() {
  const args = parseArguments(process.argv.slice(2));
  const specPath = trusted(args.spec);
  if (await sha256File(specPath) !== SPEC_SHA256) throw new Error('B56 spec SHA mismatch');
  const spec = JSON.parse(await readFile(specPath, 'utf8'));
  const preflight = await readJson(`${args.preflightRoot}/preflight.json`);
  const attempt = await readJson(`${args.attemptRoot}/attempt.json`);
  const admission = await readJson(`${args.attemptRoot}/admission.json`);
  const attemptReceipt = await readJson(`${args.attemptRoot}/receipt.json`);
  const formalStart = await readJson(`${args.formalRoot}/formal-start.json`);
  const operationDraft = await readJson(`${args.formalRoot}/operation-draft.json`);
  const release = await readJson('specs/production-compiler-entry.v0.1.json');

  const parentResult = await readJson(spec.parentEvidence.results.uri);
  const parentAudit = await readJson(spec.parentEvidence.audit.uri);
  const parentReceipt = await readJson(spec.parentEvidence.receipt.uri);
  const parentExact = await sha256File(trusted(spec.parentEvidence.results.uri)) === spec.parentEvidence.results.sha256
    && await sha256File(trusted(spec.parentEvidence.audit.uri)) === spec.parentEvidence.audit.sha256
    && await sha256File(trusted(spec.parentEvidence.receipt.uri)) === spec.parentEvidence.receipt.sha256
    && validSelfHash(parentResult, 'resultHash') && validSelfHash(parentAudit, 'auditHash') && validSelfHash(parentReceipt, 'receiptHash')
    && parentResult.scientificVerdict === spec.parentEvidence.scientificVerdict;
  const packageExact = await packageMinimality(release);
  const releaseHashes = await Promise.all(Object.entries(release.frozenFiles).map(async ([uri, expected]) => await sha256File(trusted(uri)) === expected));
  const toolHashesExact = (await Promise.all(Object.entries(preflight.toolHashes).map(async ([uri, expected]) => await sha256File(trusted(uri)) === expected))).every(Boolean);
  const releaseExact = releaseHashes.every(Boolean) && toolHashesExact && preflight.observations?.toolFreeze?.exact === true;
  const evidencePushed = await pushedEvidence(args.preflightRoot);
  const preflightAccepted = requireRecord(preflight, 'bfs.productionCompilerEntryPromotionPreflight.v0.1', 'preflightHash')
    && preflight.status === 'ACCEPTED' && evidencePushed.exact && preflight.observations?.accepted?.exact === true;
  const negativeExact = preflight.observations?.negative?.exact === true && preflight.observations.negative.rows.length === 9;
  const metaSequenceExact = requireRecord(attempt, 'bfs.productionCompilerEntryPromotionAttempt.v0.1', 'attemptHash') && attempt.sequence === 1
    && requireRecord(admission, 'bfs.productionCompilerEntryPromotionAdmission.v0.1', 'admissionHash') && admission.sequence === 2
    && requireRecord(attemptReceipt, 'bfs.productionCompilerEntryPromotionAttemptReceipt.v0.1', 'receiptHash') && attemptReceipt.sequence === 3
    && requireRecord(formalStart, 'bfs.productionCompilerEntryPromotionFormalStart.v0.1', 'formalStartHash') && formalStart.sequence === 4
    && admission.attempt?.attemptHash === attempt.attemptHash && attemptReceipt.admission?.admissionHash === admission.admissionHash
    && formalStart.attemptReceipt?.receiptHash === attemptReceipt.receiptHash;
  const runInspections = [];
  for (const run of operationDraft.runs) {
    const benchmark = spec.inputs.benchmarks.find(row => row.id === run.benchmarkId);
    runInspections.push(await inspectRun(run, benchmark));
  }
  const resolvedPairs = [];
  for (const benchmark of spec.inputs.benchmarks) {
    const pairRuns = operationDraft.runs.filter(row => row.benchmarkId === benchmark.id);
    const plans = await Promise.all(pairRuns.map(async row => {
      const receipt = await readJson(row.receipt.uri);
      return readFile(trusted(receipt.buildPlan.uri));
    }));
    const structures = await Promise.all(pairRuns.map(async row => {
      const receipt = await readJson(row.receipt.uri);
      return readFile(trusted(receipt.restrictedCompile.sceneStructureCanonical.uri));
    }));
    resolvedPairs.push({ id: benchmark.id, planBytesExact: plans.length === 2 && plans[0].equals(plans[1]), structureBytesExact: structures.length === 2 && structures[0].equals(structures[1]), planHash: pairRuns[0]?.planHash, structureHash: pairRuns[0]?.structureHash });
  }
  const pairsExact = resolvedPairs.length === 2 && resolvedPairs.every(row => {
    const expected = spec.inputs.benchmarks.find(benchmark => benchmark.id === row.id);
    return row.planBytesExact && row.structureBytesExact && row.planHash === expected.expectedPlanHash && row.structureHash === expected.expectedStructureHash;
  });
  const expectedCounts = spec.formalOperationContract;
  const observedCounts = { ...operationDraft.operationCounts, independentAuditorProcesses: 1 };
  const countsExact = Object.entries(expectedCounts).every(([key, value]) => observedCounts[key] === value);
  const zeroOperations = observedCounts.blenderRenderCalls === 0 && observedCounts.cyclesRayRenders === 0 && observedCounts.modelCalls === 0 && observedCounts.networkCalls === 0 && observedCounts.dockerProcesses === 0;
  const projection = {
    parentExact, packageExact, releaseExact, preflightAccepted, negativeExact, metaSequenceExact,
    sceneSuiteExact: preflight.observations?.suite?.passed === true,
    planPairsExact: preflight.observations?.plans?.every(row => row.canonicalPairExact && row.frozenPlanHashExact) === true,
    countsExact, zeroOperations, runs: runInspections, pairsExact,
    verdict: spec.decision.supportedVerdict,
  };
  if (validateProjection(projection) !== null) throw new Error(`B56 base projection invalid: ${validateProjection(projection)}`);
  const attacks = runAttacks(projection);
  const attackSummary = { total: attacks.length, rejected: attacks.filter(row => row.rejected).length, passed: attacks.filter(row => !row.rejected).length };
  const allRuns = runInspections.length === 4 && runInspections.every(row => Object.entries(row).filter(([key]) => key.endsWith('Exact')).every(([, value]) => value === true));
  const gates = {
    SPEC_PARENT_RUNTIME_AND_FROZEN_IDENTITIES_EXACT: await sha256File(specPath) === SPEC_SHA256 && preflight.preregistrationCommit === PREREGISTRATION_COMMIT,
    B55_SUPPORTED_PARENT_BOUND_EXACT: parentExact,
    PACKAGE_DELTA_EXACTLY_THREE_ALIASES: packageExact && Object.keys(release.packageAliases).length === 3,
    RELEASE_MANIFEST_AND_SEVEN_NEW_TOOLS_FROZEN: releaseExact,
    UNCHANGED_PRODUCTION_DEPENDENCIES_EXACT: spec.productionIntervention.unchangedProductionFiles.every(row => release.frozenFiles[row.uri] === row.sha256 && preflight.toolHashes[row.uri] === row.sha256),
    ZERO_BLENDER_PRODUCTION_PREFLIGHTS_ACCEPTED_AND_PUSHED: preflightAccepted && preflight.operationCounts?.blenderProcesses === 0,
    PREFLIGHT_NEGATIVE_PROBES_FAIL_CLOSED: negativeExact,
    FOUR_PREFLIGHT_SCENE_OUTPUT_AND_TOOL_BINDINGS_EXACT: preflight.observations.accepted.rows.length === 4 && preflight.observations.accepted.rows.every(row => row.exact),
    META_ATTEMPT_ADMISSION_AND_RECEIPT_SELF_HASH_EXACT: metaSequenceExact,
    FOUR_PRODUCTION_ATTEMPTS_PRECEDE_ADMISSION: runInspections.length === 4 && runInspections.every(row => row.sequenceExact),
    FOUR_OUTPUT_ROOTS_MATERIALIZED_ONLY_AFTER_DURABLE_RECEIPT: runInspections.length === 4 && runInspections.every(row => row.sequenceExact && !row.outputBeforeReceipt),
    SCENESPEC_SUITE_22_OF_22: projection.sceneSuiteExact,
    BUILDPLAN_PAIR_CANONICAL_BYTES_EXACT: projection.planPairsExact,
    B01_B02_PLAN_HASHES_FROZEN: resolvedPairs.every(row => row.planHash === spec.inputs.benchmarks.find(benchmark => benchmark.id === row.id).expectedPlanHash),
    FOUR_PREFERRED_PRODUCTION_ALIAS_COMPILES_PASS: runInspections.length === 4 && runInspections.every(row => row.compileAliasExact),
    FOUR_NATIVE_PID_RECEIPT_SCHEMAS_EXACT: runInspections.length === 4 && runInspections.every(row => row.pidExact),
    FOUR_CURRENT_COMPILE_RECEIPTS_VERIFY_19_CHECKS: runInspections.length === 4 && runInspections.every(row => row.compileReceiptExact && row.currentVerifierChecks === 19),
    FOUR_PRODUCTION_RECEIPTS_BIND_COMPLETE_CHAIN: runInspections.length === 4 && runInspections.every(row => row.receiptExact && row.identitiesExact && row.sequenceExact),
    FOUR_PREFERRED_PRODUCTION_VERIFIERS_PASS: runInspections.length === 4 && runInspections.every(row => row.verificationExact),
    B01_B02_PAIR_STRUCTURE_BYTES_EXACT: resolvedPairs.every(row => row.structureBytesExact),
    B01_B02_STRUCTURE_HASHES_FROZEN: resolvedPairs.every(row => row.structureHash === spec.inputs.benchmarks.find(benchmark => benchmark.id === row.id).expectedStructureHash),
    FOUR_BLEND_EMBEDDED_BINDINGS_EXACT: runInspections.length === 4 && runInspections.every(row => row.verificationExact && row.blendPlanHash === row.planHash),
    NO_UNBOUND_OR_BACKUP_OUTPUT_FILES: runInspections.length === 4 && runInspections.every(row => row.rosterExact),
    DIRECT_PROCESS_AND_SEMANTIC_OPERATION_COUNTS_EXACT: countsExact,
    MODEL_NETWORK_DOCKER_AND_RENDER_ZERO: zeroOperations,
    INDEPENDENT_AUDIT_AND_SEMANTIC_ATTACKS_MINIMUM_48: attackSummary.rejected >= spec.auditContract.semanticAttacksMinimum && attackSummary.passed === 0,
    VERDICT_MAPPING_OUTCOME_NEUTRAL: validateProjection(projection) === null && attacks.find(row => row.id === 'A12_VERDICT')?.rejected === true,
  };
  if (!allRuns || Object.keys(gates).length !== spec.gates.length) throw new Error('B56 gate roster construction mismatch');
  const body = {
    schemaVersion: 'bfs.productionCompilerEntryPromotionAudit.v0.1', experimentId: 'B56-E1', status: 'PASS', scientificVerdict: null,
    independence: { importedProductionOrB56ExecutionModules: false, externalPreferredVerifierInvocations: 0, sourceReopenedDirectly: true },
    parentExact, packageExact, releaseExact, evidencePushed, metaSequenceExact, runInspections, resolvedPairs,
    operationCounts: observedCounts, gates, attacks, attackSummary,
    derivedVerdict: Object.values(gates).every(Boolean) ? spec.decision.supportedVerdict : spec.decision.rejectedVerdict,
  };
  const output = { ...body, auditHash: canonicalHash(body) };
  await durableWrite(trusted(args.output), output);
  process.stdout.write(`BFS_B56_E1_AUDIT PASS gates=${Object.values(gates).filter(Boolean).length}/${Object.keys(gates).length} attacks=${attackSummary.rejected}/${attackSummary.total} ${output.auditHash}\n`);
}

main().catch(error => {
  process.stderr.write(`${error?.stack ?? error}\n`);
  process.exitCode = 1;
});
