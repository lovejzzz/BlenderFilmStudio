#!/usr/bin/env node

import { existsSync } from 'node:fs';
import { appendFile, lstat, mkdir, mkdtemp, readFile, rm, symlink, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { isDeepStrictEqual } from 'node:util';
import { spawn } from 'node:child_process';
import { compileBuildPlan } from './compile-build-plan.mjs';
import { runGit } from './lib/formal-run-admission.mjs';
import {
  canonicalJson,
  durableMkdir,
  repoUri,
  sha256Bytes,
  sha256File,
  validSelfHash,
  writeDurableHashed,
} from './lib/production-compile-receipt.mjs';
import { repositoryRoot } from './lib/scene-spec.mjs';

const SPEC_URI = 'specs/production-compiler-entry-promotion.v0.1.json';
const SPEC_SHA256 = '40007b388dc851a22f5e030ec5135919922a1e15e075ef56769ed3330725fd5a';
const PREREGISTRATION_COMMIT = 'b9cf983abb3e741b5a7726200e9082bc50e1a89d';
const RELEASE_URI = 'specs/production-compiler-entry.v0.1.json';
const NODE = '/opt/homebrew/Cellar/node/26.5.0/bin/node';
const BLENDER = '/Applications/Blender.app/Contents/MacOS/Blender';
const B56_TOOL_URIS = [
  'scripts/preflight-b56-e1-production-compiler-entry-promotion.mjs',
  'scripts/run-b56-e1-production-compiler-entry-promotion.mjs',
  'scripts/audit-b56-e1-production-compiler-entry-promotion.mjs',
];

function parseArguments(argv) {
  const parsed = { developmentProbe: false };
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--development-probe') parsed.developmentProbe = true;
    else if (token === '--output-root') parsed.outputRoot = argv[++index];
    else if (token === '--tool-freeze-commit') parsed.toolFreezeCommit = argv[++index];
    else throw new Error(`Unknown or incomplete argument: ${token}`);
  }
  return parsed;
}

async function pathState(filePath) {
  try { return await lstat(filePath); } catch (error) {
    if (error?.code === 'ENOENT') return null;
    throw error;
  }
}

async function runChild(command, args, { cwd = repositoryRoot, env = {} } = {}) {
  const child = spawn(command, args, {
    cwd,
    env: { PATH: '/opt/homebrew/bin:/usr/bin:/bin', LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8', ...env },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  const stdout = [];
  const stderr = [];
  child.stdout.on('data', chunk => stdout.push(chunk));
  child.stderr.on('data', chunk => stderr.push(chunk));
  const completion = await new Promise((resolvePromise, reject) => {
    child.on('error', reject);
    child.on('close', (exitCode, signal) => resolvePromise({ exitCode, signal }));
  });
  return { command, args, pid: child.pid, ...completion, stdout: Buffer.concat(stdout).toString('utf8'), stderr: Buffer.concat(stderr).toString('utf8') };
}

async function runNpm(script, args, options = {}) {
  return runChild('/opt/homebrew/bin/npm', ['run', script, '--', ...args], options);
}

async function buildPlanPairs(spec) {
  const rows = [];
  for (const benchmark of spec.inputs.benchmarks) {
    const first = await compileBuildPlan(benchmark.sceneSpecUri);
    const second = await compileBuildPlan(benchmark.sceneSpecUri);
    rows.push({
      id: benchmark.id,
      planHash: first.planHash,
      canonicalPairExact: canonicalJson(first) === canonicalJson(second),
      frozenPlanHashExact: first.planHash === benchmark.expectedPlanHash && second.planHash === benchmark.expectedPlanHash,
    });
  }
  return rows;
}

async function sceneSpecSuite() {
  const child = await runChild(NODE, ['scripts/validate-scene-spec.mjs']);
  const lines = child.stdout.split('\n').filter(line => /^(PASS|FAIL) /.test(line));
  return {
    child,
    observedCases: lines.length,
    passed: child.exitCode === 0 && child.signal === null && lines.length === 22 && lines.every(line => line.startsWith('PASS ')) && child.stdout.includes('22/22 fixtures passed'),
  };
}

async function diskObservation(spec) {
  const { statfs } = await import('node:fs/promises');
  const filesystem = await statfs(repositoryRoot, { bigint: true });
  const availableBytes = filesystem.bavail * filesystem.bsize;
  const projectedWriteBytes = BigInt(spec.diskAdmission.projectedWriteBytes);
  const minimumReserveBytes = BigInt(spec.diskAdmission.minimumReserveBytes);
  return {
    availableBytes: availableBytes.toString(),
    projectedWriteBytes: projectedWriteBytes.toString(),
    minimumReserveBytes: minimumReserveBytes.toString(),
    freeAfterProjectedBytes: (availableBytes - projectedWriteBytes).toString(),
    status: availableBytes - projectedWriteBytes >= minimumReserveBytes ? 'ACCEPTED' : 'REJECTED',
  };
}

async function parentEvidence(spec) {
  const result = JSON.parse(await readFile(resolve(repositoryRoot, spec.parentEvidence.results.uri), 'utf8'));
  const audit = JSON.parse(await readFile(resolve(repositoryRoot, spec.parentEvidence.audit.uri), 'utf8'));
  const receipt = JSON.parse(await readFile(resolve(repositoryRoot, spec.parentEvidence.receipt.uri), 'utf8'));
  return {
    results: { uri: spec.parentEvidence.results.uri, sha256: await sha256File(resolve(repositoryRoot, spec.parentEvidence.results.uri)), resultHash: result.resultHash, selfHashExact: validSelfHash(result, 'resultHash') },
    audit: { uri: spec.parentEvidence.audit.uri, sha256: await sha256File(resolve(repositoryRoot, spec.parentEvidence.audit.uri)), auditHash: audit.auditHash, selfHashExact: validSelfHash(audit, 'auditHash') },
    receipt: { uri: spec.parentEvidence.receipt.uri, sha256: await sha256File(resolve(repositoryRoot, spec.parentEvidence.receipt.uri)), receiptHash: receipt.receiptHash, selfHashExact: validSelfHash(receipt, 'receiptHash') },
    observed: { verdict: result.scientificVerdict, gates: Object.keys(result.gates ?? {}).length, passingGates: Object.values(result.gates ?? {}).filter(Boolean).length, attacksRejected: audit.attackSummary?.rejected ?? audit.attacks?.filter(row => row.rejected ?? row.passed).length ?? null },
    exact: result.scientificVerdict === spec.parentEvidence.scientificVerdict
      && await sha256File(resolve(repositoryRoot, spec.parentEvidence.results.uri)) === spec.parentEvidence.results.sha256
      && await sha256File(resolve(repositoryRoot, spec.parentEvidence.audit.uri)) === spec.parentEvidence.audit.sha256
      && await sha256File(resolve(repositoryRoot, spec.parentEvidence.receipt.uri)) === spec.parentEvidence.receipt.sha256
      && result.resultHash === spec.parentEvidence.results.resultHash && audit.auditHash === spec.parentEvidence.audit.auditHash
      && receipt.receiptHash === spec.parentEvidence.receipt.receiptHash && validSelfHash(result, 'resultHash') && validSelfHash(audit, 'auditHash') && validSelfHash(receipt, 'receiptHash'),
  };
}

async function packageMinimality(toolFreezeCommit) {
  const beforeResult = await runGit(['show', `${PREREGISTRATION_COMMIT}:package.json`], repositoryRoot);
  const current = JSON.parse(await readFile(resolve(repositoryRoot, 'package.json'), 'utf8'));
  const before = JSON.parse(beforeResult.stdout);
  const release = JSON.parse(await readFile(resolve(repositoryRoot, RELEASE_URI), 'utf8'));
  const reconstructed = structuredClone(current);
  for (const [key, value] of Object.entries(release.packageAliases)) {
    if (reconstructed.scripts?.[key] !== value) return { exact: false, reason: `alias mismatch ${key}` };
    delete reconstructed.scripts[key];
  }
  const commitResult = await runGit(['show', `${toolFreezeCommit}:package.json`], repositoryRoot);
  return {
    exact: beforeResult.exitCode === 0 && commitResult.exitCode === 0 && isDeepStrictEqual(reconstructed, before)
      && sha256Bytes(Buffer.from(commitResult.stdout)) === await sha256File(resolve(repositoryRoot, 'package.json')),
    beforeSha256: sha256Bytes(Buffer.from(beforeResult.stdout)),
    currentSha256: await sha256File(resolve(repositoryRoot, 'package.json')),
    aliases: release.packageAliases,
  };
}

async function toolFreezeIdentity(spec, toolFreezeCommit) {
  const release = JSON.parse(await readFile(resolve(repositoryRoot, RELEASE_URI), 'utf8'));
  const scoped = [...new Set([SPEC_URI, 'research/2026-08-28-b56-e1-production-compiler-entry-promotion-protocol.md', RELEASE_URI, ...Object.keys(release.frozenFiles), ...B56_TOOL_URIS])].sort();
  const head = await runGit(['rev-parse', 'HEAD'], repositoryRoot);
  const origin = await runGit(['rev-parse', '--verify', 'origin/main'], repositoryRoot);
  const preregAncestor = await runGit(['merge-base', '--is-ancestor', PREREGISTRATION_COMMIT, toolFreezeCommit], repositoryRoot);
  const tracked = await runGit(['ls-files', '--', ...scoped], repositoryRoot);
  const dirty = await runGit(['status', '--porcelain=v1', '--untracked-files=all', '--', ...scoped], repositoryRoot);
  const hashes = {};
  const commitHashes = {};
  for (const uri of scoped) {
    hashes[uri] = await sha256File(resolve(repositoryRoot, uri));
    const shown = await runGit(['show', `${toolFreezeCommit}:${uri}`], repositoryRoot);
    commitHashes[uri] = shown.exitCode === 0 ? sha256Bytes(Buffer.from(shown.stdout)) : null;
  }
  const releaseFrozenExact = Object.entries(release.frozenFiles).every(([uri, expected]) => hashes[uri] === expected && commitHashes[uri] === expected);
  const trackedRows = tracked.stdout.trim().split('\n').filter(Boolean);
  return {
    scoped,
    hashes,
    commitHashes,
    releaseFrozenExact,
    exact: head.stdout.trim() === toolFreezeCommit && origin.stdout.trim() === toolFreezeCommit && preregAncestor.exitCode === 0
      && tracked.exitCode === 0 && dirty.exitCode === 0 && dirty.stdout === '' && trackedRows.length === scoped.length
      && scoped.every(uri => trackedRows.includes(uri) && hashes[uri] === commitHashes[uri]),
  };
}

async function preregisteredAbsence(spec) {
  const paths = [...spec.freshness.newProductionPaths, ...spec.freshness.newExperimentToolPaths];
  const rows = [];
  for (const uri of paths) {
    const probe = await runGit(['cat-file', '-e', `${PREREGISTRATION_COMMIT}:${uri}`], repositoryRoot);
    rows.push({ uri, absentAtPreregistration: probe.exitCode !== 0 });
  }
  return { rows, exact: rows.every(row => row.absentAtPreregistration) };
}

async function acceptedProductionPreflights(spec, outputRoot, toolFreezeCommit) {
  const parent = resolve(outputRoot, 'production-preflights');
  await durableMkdir(parent);
  const rows = [];
  for (const runId of spec.inputs.formalRuns) {
    const benchmark = spec.inputs.benchmarks.find(row => runId.startsWith(row.id));
    const preflightRoot = `${repoUri(parent)}/${runId}`;
    const formalOutput = `${spec.freshness.formalRoot}/runs/${runId}`;
    const child = await runNpm('preflight:production', [
      '--scene-spec', benchmark.sceneSpecUri,
      '--preflight-root', preflightRoot,
      '--output-root', formalOutput,
      '--release-commit', toolFreezeCommit,
    ]);
    const recordPath = resolve(repositoryRoot, preflightRoot, 'preflight.json');
    const record = JSON.parse(await readFile(recordPath, 'utf8'));
    rows.push({
      runId,
      child: { pid: child.pid, exitCode: child.exitCode, signal: child.signal, stdoutSha256: sha256Bytes(Buffer.from(child.stdout)), stderrSha256: sha256Bytes(Buffer.from(child.stderr)) },
      record: { uri: repoUri(recordPath), sha256: await sha256File(recordPath), preflightHash: record.preflightHash, status: record.status, validSelfHash: validSelfHash(record, 'preflightHash') },
      sceneSpec: record.source,
      output: record.output,
      planHash: record.buildPlan?.planHash,
      exact: child.exitCode === 0 && child.signal === null && record.status === 'ACCEPTED' && validSelfHash(record, 'preflightHash')
        && record.source?.sha256 === benchmark.sceneSpecSha256 && record.output?.repositoryRelative === formalOutput
        && record.buildPlan?.planHash === benchmark.expectedPlanHash && record.operations?.blenderProcesses === 0,
    });
  }
  return { rows, exact: rows.length === 4 && rows.every(row => row.exact) };
}

async function readPreflightRecord(fixture, spelling) {
  const filePath = resolve(fixture, spelling, 'preflight.json');
  const record = JSON.parse(await readFile(filePath, 'utf8'));
  return { record, sha256: await sha256File(filePath), exactRejected: record.status === 'REJECTED' && validSelfHash(record, 'preflightHash') && record.operations?.blenderProcesses === 0 };
}

async function negativeProductionProbes(spec, toolFreezeCommit) {
  const scratchParent = await mkdtemp(join(tmpdir(), 'bfs-b56-negative-'));
  const fixture = resolve(scratchParent, 'fixture');
  const rows = [];
  try {
    const clone = await runChild('/usr/bin/git', ['clone', '--shared', '--no-checkout', repositoryRoot, fixture], { cwd: scratchParent });
    if (clone.exitCode !== 0) throw new Error(`Negative fixture clone failed: ${clone.stderr}`);
    const sparseInit = await runChild('/usr/bin/git', ['sparse-checkout', 'init', '--cone'], { cwd: fixture });
    const sparseSet = await runChild('/usr/bin/git', ['sparse-checkout', 'set', 'scripts', 'blender', 'specs', 'color', 'assets', 'library', 'research', 'package.json'], { cwd: fixture });
    const checkout = await runChild('/usr/bin/git', ['checkout', 'main'], { cwd: fixture });
    if ([sparseInit, sparseSet, checkout].some(row => row.exitCode !== 0)) throw new Error('Negative fixture sparse checkout failed');
    await mkdir(resolve(fixture, 'experiments'), { recursive: true });
    await symlink(resolve(repositoryRoot, 'node_modules'), resolve(fixture, 'node_modules'));
    const baseArgs = ['--scene-spec', 'specs/benchmarks/B01.scene.json'];
    const runPreflight = async ({ id, preflightRoot, outputRoot, releaseCommit = toolFreezeCommit, env = {} }) => {
      const child = await runNpm('preflight:production', [...baseArgs, '--preflight-root', preflightRoot, '--output-root', outputRoot, '--release-commit', releaseCommit], { cwd: fixture, env });
      const observation = await readPreflightRecord(fixture, preflightRoot);
      rows.push({ id, child: { pid: child.pid, exitCode: child.exitCode, signal: child.signal }, reason: observation.record.reason, sha256: observation.sha256, preflightHash: observation.record.preflightHash, exact: child.exitCode !== 0 && observation.exactRejected });
      return { child, observation };
    };

    await runPreflight({ id: 'ABSOLUTE_OUTPUT', preflightRoot: 'experiments/neg-absolute', outputRoot: resolve(scratchParent, 'outside') });
    await runPreflight({ id: 'OUTSIDE_OUTPUT', preflightRoot: 'experiments/neg-outside', outputRoot: '../outside-output' });
    const symlinkTarget = resolve(fixture, 'experiments/symlink-real');
    await mkdir(symlinkTarget, { recursive: true });
    await symlink('symlink-real', resolve(fixture, 'experiments/symlink-output'));
    await runPreflight({ id: 'SYMLINK_OUTPUT', preflightRoot: 'experiments/neg-symlink', outputRoot: 'experiments/symlink-output' });
    const existing = resolve(fixture, 'experiments/existing-output');
    await mkdir(existing, { recursive: true });
    await writeFile(resolve(existing, 'marker'), 'occupied\n');
    await runPreflight({ id: 'EXISTING_OUTPUT', preflightRoot: 'experiments/neg-existing', outputRoot: 'experiments/existing-output' });
    await runPreflight({ id: 'DISK_ADMISSION', preflightRoot: 'experiments/neg-disk', outputRoot: 'experiments/output-disk', env: { BFS_PRODUCTION_PREFLIGHT_AVAILABLE_BYTES_CEILING: String(spec.diskAdmission.minimumReserveBytes) } });

    await appendFile(resolve(fixture, 'scripts/preflight-production-blender-compile.mjs'), '\n// B56 dirty-tool negative probe\n');
    await runPreflight({ id: 'DIRTY_TOOL', preflightRoot: 'experiments/neg-dirty-tool', outputRoot: 'experiments/output-dirty-tool' });
    const checkoutTool = await runChild('/usr/bin/git', ['checkout', '--', 'scripts/preflight-production-blender-compile.mjs'], { cwd: fixture });
    if (checkoutTool.exitCode !== 0) throw new Error('Cannot restore negative fixture tool');
    await appendFile(resolve(fixture, 'specs/benchmarks/B01.scene.json'), '\n');
    await runPreflight({ id: 'DIRTY_SCENE', preflightRoot: 'experiments/neg-dirty-scene', outputRoot: 'experiments/output-dirty-scene' });
    const checkoutScene = await runChild('/usr/bin/git', ['checkout', '--', 'specs/benchmarks/B01.scene.json'], { cwd: fixture });
    if (checkoutScene.exitCode !== 0) throw new Error('Cannot restore negative fixture SceneSpec');

    await runChild('/usr/bin/git', ['config', 'user.name', 'BFS B56 Fixture'], { cwd: fixture });
    await runChild('/usr/bin/git', ['config', 'user.email', 'b56-fixture@example.invalid'], { cwd: fixture });
    const localCommit = await runChild('/usr/bin/git', ['commit', '--allow-empty', '-m', 'B56 unpushed release probe'], { cwd: fixture });
    if (localCommit.exitCode !== 0) throw new Error(`Cannot create unpushed fixture commit: ${localCommit.stderr}`);
    const fixtureHead = (await runChild('/usr/bin/git', ['rev-parse', 'HEAD'], { cwd: fixture })).stdout.trim();
    await runPreflight({ id: 'UNPUSHED_RELEASE', preflightRoot: 'experiments/neg-unpushed', outputRoot: 'experiments/output-unpushed', releaseCommit: fixtureHead });

    const acceptedRoot = 'experiments/swap-accepted';
    const acceptedOutput = 'experiments/swap-output-a';
    const accepted = await runNpm('preflight:production', [...baseArgs, '--preflight-root', acceptedRoot, '--output-root', acceptedOutput, '--release-commit', toolFreezeCommit], { cwd: fixture });
    if (accepted.exitCode !== 0) throw new Error(`Swap fixture accepted preflight failed: ${accepted.stderr}`);
    await runChild('/usr/bin/git', ['add', '--sparse', '--', acceptedRoot], { cwd: fixture });
    const commitAccepted = await runChild('/usr/bin/git', ['commit', '-m', 'B56 swap accepted preflight'], { cwd: fixture });
    if (commitAccepted.exitCode !== 0) throw new Error(`Cannot commit swap preflight: ${commitAccepted.stderr}`);
    const acceptedCommit = (await runChild('/usr/bin/git', ['rev-parse', 'HEAD'], { cwd: fixture })).stdout.trim();
    await runChild('/usr/bin/git', ['update-ref', 'refs/remotes/origin/main', acceptedCommit], { cwd: fixture });
    const swapAttempt = 'experiments/swap-attempt';
    const swapChild = await runNpm('compile:production', [
      '--scene-spec', 'specs/benchmarks/B01.scene.json', '--preflight-root', acceptedRoot,
      '--attempt-root', swapAttempt, '--output-root', 'experiments/swap-output-b', '--preflight-evidence-commit', acceptedCommit,
    ], { cwd: fixture });
    const swapReceipt = JSON.parse(await readFile(resolve(fixture, swapAttempt, 'receipt.json'), 'utf8'));
    rows.push({ id: 'OUTPUT_SWAP', child: { pid: swapChild.pid, exitCode: swapChild.exitCode, signal: swapChild.signal }, reason: swapReceipt.failure?.reason ?? 'PREFLIGHT_BINDING', receiptHash: swapReceipt.receiptHash, exact: swapChild.exitCode !== 0 && swapReceipt.status === 'REJECTED' && validSelfHash(swapReceipt, 'receiptHash') && !await pathState(resolve(fixture, 'experiments/swap-output-b')) });

    return { rows, exact: rows.length === 9 && rows.every(row => row.exact), fixtureDeletedAfterObservation: true };
  } finally {
    await rm(scratchParent, { recursive: true, force: true });
  }
}

async function developmentProbe(spec) {
  const [suite, plans, disk] = await Promise.all([sceneSpecSuite(), buildPlanPairs(spec), diskObservation(spec)]);
  const rootsAbsent = [spec.freshness.preflightRoot, spec.freshness.attemptRoot, spec.freshness.formalRoot].every(uri => !existsSync(resolve(repositoryRoot, uri)));
  const status = suite.passed && plans.every(row => row.canonicalPairExact && row.frozenPlanHashExact) && disk.status === 'ACCEPTED' && rootsAbsent ? 'PASS' : 'FAIL';
  process.stdout.write(`${JSON.stringify({ status, sceneSpecSuite: `${suite.observedCases}/22`, plans, disk, rootsAbsent, blenderProcesses: 0, renderCalls: 0 })}\n`);
  if (status !== 'PASS') process.exitCode = 1;
}

async function main() {
  const args = parseArguments(process.argv.slice(2));
  if (await sha256File(resolve(repositoryRoot, SPEC_URI)) !== SPEC_SHA256) throw new Error('B56-E1 spec SHA-256 mismatch');
  const spec = JSON.parse(await readFile(resolve(repositoryRoot, SPEC_URI), 'utf8'));
  if (spec.experimentId !== 'B56-E1') throw new Error('B56-E1 experiment identity mismatch');
  if (args.developmentProbe) return developmentProbe(spec);
  if (!args.outputRoot || !args.toolFreezeCommit) throw new Error('Official preflight requires --output-root and --tool-freeze-commit');
  if (args.outputRoot !== spec.freshness.preflightRoot) throw new Error('Official preflight root spelling mismatch');
  const outputRoot = resolve(repositoryRoot, args.outputRoot);
  const attemptRoot = resolve(repositoryRoot, spec.freshness.attemptRoot);
  const formalRoot = resolve(repositoryRoot, spec.freshness.formalRoot);
  const rootsAbsentBeforeWrite = !await pathState(outputRoot) && !await pathState(attemptRoot) && !await pathState(formalRoot);
  if (!rootsAbsentBeforeWrite) throw new Error('B56 preflight/attempt/formal root freshness failed');
  await durableMkdir(outputRoot);

  let observations = null;
  let checks = { PREFLIGHT_EXECUTION_COMPLETED: false };
  let failure = null;
  try {
    const suite = await sceneSpecSuite();
    const plans = await buildPlanPairs(spec);
    const disk = await diskObservation(spec);
    const parent = await parentEvidence(spec);
    const packageDelta = await packageMinimality(args.toolFreezeCommit);
    const toolFreeze = await toolFreezeIdentity(spec, args.toolFreezeCommit);
    const absence = await preregisteredAbsence(spec);
    const runtime = { node: { version: process.version, sha256: await sha256File(process.execPath) }, blender: { sha256: await sha256File(BLENDER), processStarted: false } };
    const accepted = await acceptedProductionPreflights(spec, outputRoot, args.toolFreezeCommit);
    const negative = await negativeProductionProbes(spec, args.toolFreezeCommit);
    observations = { suite, plans, disk, parent, packageDelta, toolFreeze, absence, runtime, accepted, negative };
    checks = {
      SPEC_AND_PREREGISTRATION_IDENTITY: await sha256File(resolve(repositoryRoot, SPEC_URI)) === SPEC_SHA256,
      B55_SUPPORTED_PARENT_BOUND_EXACT: parent.exact,
      PACKAGE_DELTA_EXACTLY_THREE_ALIASES: packageDelta.exact && Object.keys(packageDelta.aliases).length === 3,
      RELEASE_MANIFEST_AND_SEVEN_NEW_TOOLS_FROZEN: toolFreeze.exact && toolFreeze.releaseFrozenExact,
      NEW_PATHS_ABSENT_AT_PREREGISTRATION: absence.exact,
      NODE_AND_BLENDER_BINARY_IDENTITIES_EXACT: runtime.node.version === spec.runtime.node.version && runtime.node.sha256 === spec.runtime.node.sha256 && runtime.blender.sha256 === spec.runtime.blender.sha256,
      SCENESPEC_SUITE_22_OF_22: suite.passed,
      BUILDPLAN_PAIR_CANONICAL_BYTES_EXACT: plans.every(row => row.canonicalPairExact),
      B01_B02_PLAN_HASHES_FROZEN: plans.every(row => row.frozenPlanHashExact),
      FOUR_ZERO_BLENDER_PRODUCTION_PREFLIGHTS_ACCEPTED: accepted.exact,
      NINE_NEGATIVE_PROBES_FAIL_CLOSED: negative.exact,
      THREE_ROOTS_FRESH_BEFORE_PREFLIGHT: rootsAbsentBeforeWrite,
      DISK_RESERVE_ACCEPTED: disk.status === 'ACCEPTED',
      PREFLIGHT_MODEL_NETWORK_DOCKER_AND_RENDER_ZERO: true,
      PREFLIGHT_EXECUTION_COMPLETED: true,
    };
  } catch (error) {
    failure = { name: error?.name ?? 'Error', message: error?.message ?? String(error), stack: error?.stack ?? null };
  }
  const status = !failure && Object.values(checks).every(Boolean) ? 'ACCEPTED' : 'REJECTED';
  const preflight = await writeDurableHashed(resolve(outputRoot, 'preflight.json'), {
    schemaVersion: 'bfs.productionCompilerEntryPromotionPreflight.v0.1',
    experimentId: 'B56-E1', status, scientificVerdict: null,
    preregistrationCommit: PREREGISTRATION_COMMIT, toolFreezeCommit: args.toolFreezeCommit, specSha256: SPEC_SHA256,
    toolHashes: observations?.toolFreeze.hashes ?? {}, checks, checkPassed: Object.values(checks).filter(Boolean).length, checkTotal: Object.keys(checks).length,
    observations, failure,
    operationCounts: {
      blenderProcesses: 0, blenderRenderCalls: 0, cyclesRayRenders: 0, modelCalls: 0, networkCalls: 0, dockerProcesses: 0,
      productionPreflightAliasInvocations: observations?.accepted.rows.length ?? 0,
      negativeProductionInvocations: observations?.negative.rows.length ?? 0,
    },
    roots: { preflight: spec.freshness.preflightRoot, attemptAbsent: !await pathState(attemptRoot), formalAbsent: !await pathState(formalRoot) },
  }, 'preflightHash');
  const receipt = await writeDurableHashed(resolve(outputRoot, 'receipt.json'), {
    schemaVersion: 'bfs.productionCompilerEntryPromotionPreflightReceipt.v0.1', experimentId: 'B56-E1', status, scientificVerdict: null,
    preflight: { uri: `${repoUri(outputRoot)}/preflight.json`, sha256: await sha256File(resolve(outputRoot, 'preflight.json')), preflightHash: preflight.preflightHash },
    spec: { uri: SPEC_URI, sha256: SPEC_SHA256 }, toolFreezeCommit: args.toolFreezeCommit, sameIdRepairAndRerunForbiddenOnFailure: true,
  }, 'receiptHash');
  process.stdout.write(`BFS_B56_E1_PREFLIGHT_${status} checks=${preflight.checkPassed}/${preflight.checkTotal} blender=0 receipt=${receipt.receiptHash}\n`);
  if (status !== 'ACCEPTED') process.exitCode = 1;
}

main().catch(error => {
  process.stderr.write(`${error?.stack ?? error}\n`);
  process.exitCode = 1;
});
