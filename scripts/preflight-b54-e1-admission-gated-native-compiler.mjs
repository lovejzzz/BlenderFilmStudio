#!/opt/homebrew/Cellar/node/26.5.0/bin/node

import { spawn } from 'node:child_process';
import { lstat, mkdir, readFile, realpath, statfs, writeFile } from 'node:fs/promises';
import { relative, resolve, sep } from 'node:path';
import { admitFormalRun, canonicalHash, runGit, sha256File, sortValue } from './lib/formal-run-admission.mjs';
import { compileBuildPlan } from './compile-build-plan.mjs';
import { canonicalJson, repositoryRoot } from './lib/scene-spec.mjs';

const SPEC_SHA256 = '4453d24e7e2a36ca114435a979dc7501247b3da1f5ec0f394143356c058d30cd';
const PREREGISTRATION_COMMIT = 'ad13c0bc7400a3e43b296449d8263f10e6a974af';
const NODE_EXECUTABLE = '/opt/homebrew/Cellar/node/26.5.0/bin/node';
const BLENDER_EXECUTABLE = '/Applications/Blender.app/Contents/MacOS/Blender';
const COMPONENT_EVIDENCE = 'experiments/blender-material-owner-projective-depth-holdout-preflight-v0-1';
const COMPONENT_OUTPUT = 'experiments/.b54-e1-relative-admission-probe-output';
const TOOL_PATHS = [
  'scripts/lib/formal-run-admission.mjs',
  'scripts/preflight-b54-e1-admission-gated-native-compiler.mjs',
  'scripts/run-b54-e1-admission-gated-native-compiler.mjs',
  'scripts/audit-b54-e1-admission-gated-native-compiler.mjs',
  'scripts/compile-build-plan.mjs',
  'scripts/lib/scene-spec.mjs',
  'scripts/lib/scene-spec-v02.mjs',
  'scripts/lib/scene-spec-v03.mjs',
  'scripts/lib/scene-spec-v04.mjs',
  'scripts/lib/scene-spec-v05.mjs',
  'scripts/lib/actor-spec.mjs',
  'scripts/lib/grasp-spec.mjs',
  'scripts/lib/trajectory-spec.mjs',
  'scripts/run-restricted-blender-compile.mjs',
  'scripts/lib/budgeted-process.mjs',
  'scripts/lib/compile-receipt.mjs',
  'scripts/lib/receipt-format.mjs',
  'scripts/verify-compile-receipt.mjs',
  'blender/compile_scene.py',
  'blender/audit_compiled_artifact.py',
];
const CONFIG_PATHS = [
  'specs/restricted-compile-budget.v0.1.json',
  'specs/output-spec.v0.1.json',
  'color/ocio/cg-config-v4.0.0_aces-v2.0_ocio-v2.5.ocio',
  'specs/benchmarks/B01.scene.json',
  'specs/benchmarks/B02.scene.json',
];

function parseArguments(argv) {
  const parsed = { developmentProbe: false };
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--development-probe') parsed.developmentProbe = true;
    else if (token === '--spec') parsed.spec = argv[++index];
    else if (token === '--output-root') parsed.outputRoot = argv[++index];
    else if (token === '--tool-freeze-commit') parsed.toolFreezeCommit = argv[++index];
    else throw new Error(`Unknown or incomplete argument: ${token}`);
  }
  return parsed;
}

async function pathState(path) {
  try { return await lstat(path); } catch (error) {
    if (error?.code === 'ENOENT') return null;
    throw error;
  }
}

function repoUri(path) {
  return relative(repositoryRoot, path).split(sep).join('/');
}

async function writeJson(path, value) {
  await writeFile(path, `${JSON.stringify(sortValue(value), null, 2)}\n`, { encoding: 'utf8', flag: 'wx' });
}

async function writeHashed(path, body, field) {
  const record = { ...body, [field]: canonicalHash(body) };
  await writeJson(path, record);
  return record;
}

async function runChild(command, args, role) {
  const started = process.hrtime.bigint();
  const child = spawn(command, args, {
    cwd: repositoryRoot,
    env: { PATH: '/usr/bin:/bin:/opt/homebrew/bin', LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8' },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  const stdout = [];
  const stderr = [];
  child.stdout.on('data', chunk => stdout.push(chunk));
  child.stderr.on('data', chunk => stderr.push(chunk));
  const exitCode = await new Promise((resolvePromise, reject) => {
    child.on('error', reject);
    child.on('close', resolvePromise);
  });
  return {
    role,
    command,
    args,
    pid: child.pid,
    exitCode,
    stdout: Buffer.concat(stdout).toString('utf8'),
    stderr: Buffer.concat(stderr).toString('utf8'),
    elapsedNanoseconds: Number(process.hrtime.bigint() - started),
  };
}

async function buildPlanProbe(spec) {
  const observations = [];
  for (const benchmark of spec.inputs.benchmarks) {
    const first = await compileBuildPlan(benchmark.sceneSpecUri);
    const second = await compileBuildPlan(benchmark.sceneSpecUri);
    const firstCanonical = canonicalJson(first);
    const secondCanonical = canonicalJson(second);
    observations.push({
      benchmark: benchmark.id,
      firstPlanHash: first.planHash,
      secondPlanHash: second.planHash,
      firstCanonicalSha256: canonicalHash(first),
      secondCanonicalSha256: canonicalHash(second),
      canonicalBytesExact: firstCanonical === secondCanonical,
      frozenPlanHashExact: first.planHash === benchmark.expectedPlanHash && second.planHash === benchmark.expectedPlanHash,
    });
  }
  return observations;
}

async function componentAdmissionProbe(gitChildren) {
  if (await pathState(resolve(repositoryRoot, COMPONENT_OUTPUT))) throw new Error(`Component probe output exists: ${COMPONENT_OUTPUT}`);
  const admission = await admitFormalRun({
    repositoryRoot,
    evidenceInput: COMPONENT_EVIDENCE,
    formalOutput: COMPONENT_OUTPUT,
    originRef: 'origin/main',
    gitObserver: row => gitChildren.push({ phase: 'RELATIVE_COMPONENT_ADMISSION', ...row }),
  });
  const outputAbsent = await pathState(resolve(repositoryRoot, COMPONENT_OUTPUT)) === null;
  return {
    evidenceInput: COMPONENT_EVIDENCE,
    formalOutput: COMPONENT_OUTPUT,
    status: admission.status,
    evidenceIdentityHash: admission.evidence.identityHash,
    outputRepositoryRelative: admission.output.repositoryRelative,
    outputAbsoluteMatches: admission.output.absolute === resolve(repositoryRoot, COMPONENT_OUTPUT),
    outputAbsent,
  };
}

async function diskObservation(spec) {
  const fileSystem = await statfs(repositoryRoot);
  const availableBytes = Number(fileSystem.bavail) * Number(fileSystem.bsize);
  const projectedWriteBytes = spec.diskAdmission.projectedWriteBytes;
  const minimumReserveBytes = spec.diskAdmission.minimumReserveBytes;
  return {
    availableBytes,
    projectedWriteBytes,
    minimumReserveBytes,
    freeAfterProjectedBytes: availableBytes - projectedWriteBytes,
    status: availableBytes - projectedWriteBytes >= minimumReserveBytes ? 'ACCEPTED' : 'REJECTED',
  };
}

async function commonChecks(spec) {
  const gitChildren = [];
  const validator = await runChild(NODE_EXECUTABLE, ['scripts/validate-scene-spec.mjs'], 'SCENESPEC_VALIDATOR');
  const suiteLines = validator.stdout.split('\n').filter(line => /^(PASS|FAIL) /.test(line));
  const buildPlans = await buildPlanProbe(spec);
  const componentAdmission = await componentAdmissionProbe(gitChildren);
  const disk = await diskObservation(spec);
  return {
    validator,
    sceneSpecSuite: {
      passed: validator.exitCode === 0 && suiteLines.length === 22 && suiteLines.every(line => line.startsWith('PASS ')) && validator.stdout.includes('22/22 fixtures passed'),
      observedCases: suiteLines.length,
      stdoutSha256: canonicalHash({ stdout: validator.stdout }),
      stderrSha256: canonicalHash({ stderr: validator.stderr }),
    },
    buildPlans,
    componentAdmission,
    disk,
    gitChildren,
  };
}

async function runDevelopmentProbe(spec) {
  const common = await commonChecks(spec);
  const passed = common.sceneSpecSuite.passed
    && common.buildPlans.length === 2
    && common.buildPlans.every(row => row.canonicalBytesExact && row.frozenPlanHashExact)
    && common.componentAdmission.status === 'ACCEPTED'
    && common.componentAdmission.outputAbsent
    && common.disk.status === 'ACCEPTED';
  process.stdout.write(`${JSON.stringify({
    status: passed ? 'PASS' : 'FAIL',
    formalRootsCreated: false,
    sceneSpecSuite: `${common.sceneSpecSuite.observedCases}/22`,
    buildPlans: common.buildPlans,
    componentAdmission: common.componentAdmission,
    gitChildProcesses: common.gitChildren.length,
    blenderProcesses: 0,
    blenderRenderCalls: 0,
    disk: common.disk,
  })}\n`);
  if (!passed) process.exitCode = 1;
}

async function main() {
  const args = parseArguments(process.argv.slice(2));
  const specPath = resolve(repositoryRoot, args.spec ?? 'specs/admission-gated-native-compiler-integration.v0.1.json');
  if (await sha256File(specPath) !== SPEC_SHA256) throw new Error('B54-E1 spec SHA-256 mismatch');
  const spec = JSON.parse(await readFile(specPath, 'utf8'));
  if (spec.experimentId !== 'B54-E1') throw new Error('B54-E1 experiment identity mismatch');
  if (args.developmentProbe) {
    await runDevelopmentProbe(spec);
    return;
  }
  if (!args.outputRoot || !args.toolFreezeCommit) throw new Error('Official preflight requires --spec, --output-root and --tool-freeze-commit');
  const outputRoot = resolve(repositoryRoot, args.outputRoot);
  if (outputRoot !== resolve(repositoryRoot, spec.freshness.preflightRoot)) throw new Error('Preflight output root mismatch');
  if (await pathState(outputRoot)) throw new Error('Preflight output root already exists; B54-E1 preflight is single-use');
  if (await pathState(resolve(repositoryRoot, spec.freshness.attemptRoot)) || await pathState(resolve(repositoryRoot, spec.freshness.formalRoot))) throw new Error('Attempt/formal root must remain absent before preflight');

  const identityGitChildren = [];
  const head = (await runGit(['rev-parse', 'HEAD'], repositoryRoot, row => identityGitChildren.push({ phase: 'HEAD', ...row }))).stdout.trim();
  const originMainResult = await runGit(['rev-parse', '--verify', 'origin/main'], repositoryRoot, row => identityGitChildren.push({ phase: 'ORIGIN_MAIN', ...row }));
  const originMain = originMainResult.stdout.trim();
  const scopedPaths = ['specs/admission-gated-native-compiler-integration.v0.1.json', ...TOOL_PATHS, ...CONFIG_PATHS];
  const tracked = await runGit(['ls-files', '--', ...scopedPaths], repositoryRoot, row => identityGitChildren.push({ phase: 'TRACKED', ...row }));
  const dirty = await runGit(['status', '--porcelain=v1', '--untracked-files=all', '--', ...scopedPaths], repositoryRoot, row => identityGitChildren.push({ phase: 'CLEAN', ...row }));
  const preregistration = await runGit(['merge-base', '--is-ancestor', PREREGISTRATION_COMMIT, args.toolFreezeCommit], repositoryRoot, row => identityGitChildren.push({ phase: 'PREREGISTRATION_ANCESTRY', ...row }));
  const toolHashes = {};
  for (const uri of TOOL_PATHS) toolHashes[uri] = await sha256File(resolve(repositoryRoot, uri));
  const configurationHashes = {};
  for (const uri of CONFIG_PATHS) configurationHashes[uri] = await sha256File(resolve(repositoryRoot, uri));
  const nodeIdentity = { executable: process.execPath, version: process.version, sha256: await sha256File(process.execPath) };
  const blenderIdentity = { executable: BLENDER_EXECUTABLE, sha256: await sha256File(BLENDER_EXECUTABLE), versionBinding: spec.runtime.blender.version, buildHashBinding: spec.runtime.blender.buildHash };
  const common = await commonChecks(spec);
  const rootsAbsentBeforeWrite = !await pathState(outputRoot)
    && !await pathState(resolve(repositoryRoot, spec.freshness.attemptRoot))
    && !await pathState(resolve(repositoryRoot, spec.freshness.formalRoot));
  const checks = {
    SPEC_AND_PREREGISTRATION_IDENTITY: await sha256File(specPath) === SPEC_SHA256 && preregistration.exitCode === 0,
    TOOL_FREEZE_HEAD_AND_ORIGIN_EXACT: head === args.toolFreezeCommit && originMainResult.exitCode === 0 && originMain === args.toolFreezeCommit,
    ALL_SCOPED_PATHS_TRACKED_CLEAN: tracked.exitCode === 0 && tracked.stdout.trim().split('\n').filter(Boolean).length === scopedPaths.length && dirty.exitCode === 0 && dirty.stdout === '',
    NODE_RUNTIME_EXACT: nodeIdentity.executable === spec.runtime.node.executable && nodeIdentity.version === spec.runtime.node.version && nodeIdentity.sha256 === spec.runtime.node.sha256,
    BLENDER_BINARY_EXACT_WITHOUT_PROCESS: blenderIdentity.executable === spec.runtime.blender.executable && blenderIdentity.sha256 === spec.runtime.blender.sha256,
    INPUT_AND_CONFIGURATION_HASHES_EXACT: spec.inputs.benchmarks.every(row => configurationHashes[row.sceneSpecUri] === row.sceneSpecSha256) && configurationHashes[spec.inputs.outputSpec.uri] === spec.inputs.outputSpec.sha256,
    SCENESPEC_SUITE_22_OF_22: common.sceneSpecSuite.passed,
    BUILDPLAN_PAIR_CANONICAL_BYTES_EXACT: common.buildPlans.length === 2 && common.buildPlans.every(row => row.canonicalBytesExact),
    B01_B02_PLAN_HASHES_FROZEN: common.buildPlans.every(row => row.frozenPlanHashExact),
    RELATIVE_COMPONENT_ADMISSION_ACCEPTED: common.componentAdmission.status === 'ACCEPTED' && common.componentAdmission.outputAbsoluteMatches,
    COMPONENT_ADMISSION_CREATED_NO_OUTPUT: common.componentAdmission.outputAbsent,
    THREE_B54_ROOTS_ABSENT_BEFORE_WRITE: rootsAbsentBeforeWrite,
    DISK_RESERVE_ACCEPTED: common.disk.status === 'ACCEPTED',
    PREFLIGHT_BLENDER_MODEL_NETWORK_RENDER_ZERO: true,
  };
  const status = Object.values(checks).every(Boolean) ? 'ACCEPTED' : 'REJECTED';
  await mkdir(outputRoot, { recursive: false });
  const preflightBody = {
    schemaVersion: 'bfs.admissionGatedNativeCompilerPreflight.v0.1',
    experimentId: 'B54-E1',
    status,
    scientificVerdict: null,
    preregistrationCommit: PREREGISTRATION_COMMIT,
    toolFreezeCommit: args.toolFreezeCommit,
    specSha256: SPEC_SHA256,
    toolHashes,
    configurationHashes,
    nodeIdentity,
    blenderIdentity,
    checks,
    checkPassed: Object.values(checks).filter(Boolean).length,
    checkTotal: Object.keys(checks).length,
    sceneSpecSuite: common.sceneSpecSuite,
    buildPlans: common.buildPlans,
    componentAdmission: common.componentAdmission,
    disk: common.disk,
    operationCounts: {
      preflightProcesses: 1,
      sceneSpecValidatorChildren: 1,
      gitChildren: identityGitChildren.length + common.gitChildren.length,
      blenderProcesses: 0,
      blenderRenderCalls: 0,
      cyclesRayRenders: 0,
      dockerProcesses: 0,
      modelCalls: 0,
      networkCalls: 0,
    },
    children: { validator: common.validator, git: [...identityGitChildren, ...common.gitChildren] },
    rootObservations: {
      preflightRoot: { uri: repoUri(outputRoot), absentBeforeWrite: rootsAbsentBeforeWrite },
      attemptRoot: { uri: spec.freshness.attemptRoot, absent: !await pathState(resolve(repositoryRoot, spec.freshness.attemptRoot)) },
      formalRoot: { uri: spec.freshness.formalRoot, absent: !await pathState(resolve(repositoryRoot, spec.freshness.formalRoot)) },
    },
  };
  const preflightPath = resolve(outputRoot, 'preflight.json');
  const preflight = await writeHashed(preflightPath, preflightBody, 'preflightHash');
  const receiptBody = {
    schemaVersion: 'bfs.admissionGatedNativeCompilerPreflightReceipt.v0.1',
    experimentId: 'B54-E1',
    status,
    scientificVerdict: null,
    preflight: { uri: `${repoUri(outputRoot)}/preflight.json`, sha256: await sha256File(preflightPath), preflightHash: preflight.preflightHash },
    spec: { uri: repoUri(specPath), sha256: SPEC_SHA256 },
    toolFreezeCommit: args.toolFreezeCommit,
    sameIdRepairAndRerunForbiddenOnFailure: true,
  };
  const receipt = await writeHashed(resolve(outputRoot, 'receipt.json'), receiptBody, 'receiptHash');
  process.stdout.write(`BFS_B54_E1_PREFLIGHT_${status} checks=${preflight.checkPassed}/${preflight.checkTotal} blender=0 receipt=${receipt.receiptHash}\n`);
  if (status !== 'ACCEPTED') process.exitCode = 1;
}

main().catch(error => {
  process.stderr.write(`${error?.stack ?? error}\n`);
  process.exitCode = 1;
});
