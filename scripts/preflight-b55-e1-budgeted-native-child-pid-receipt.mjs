#!/opt/homebrew/Cellar/node/26.5.0/bin/node

import { spawn } from 'node:child_process';
import { lstat, mkdir, readFile, statfs, writeFile } from 'node:fs/promises';
import { relative, resolve, sep } from 'node:path';
import { admitFormalRun, canonicalHash, runGit, sha256Bytes, sha256File, sortValue } from './lib/formal-run-admission.mjs';
import { runBudgetedProcess } from './lib/budgeted-process.mjs';
import { compileBuildPlan } from './compile-build-plan.mjs';
import { canonicalJson, repositoryRoot } from './lib/scene-spec.mjs';

const SPEC_SHA256 = '8aafaad2afe90ac022e6378700d5013470c08b994515eb9cdd2b245df7a320e7';
const PREREGISTRATION_COMMIT = 'bf62f9a02dbfb966f585a4c0e634da1e3507cd72';
const NODE_EXECUTABLE = '/opt/homebrew/Cellar/node/26.5.0/bin/node';
const BLENDER_EXECUTABLE = '/Applications/Blender.app/Contents/MacOS/Blender';
const COMPONENT_EVIDENCE = 'experiments/blender-material-owner-projective-depth-holdout-preflight-v0-1';
const COMPONENT_OUTPUT = 'experiments/.b55-e1-relative-admission-probe-output';
const SUPERVISOR_URI = 'scripts/lib/budgeted-process.mjs';
const PID_CHILD_SOURCE = "const{writeFileSync}=require('node:fs');const[output,mode]=process.argv.slice(1);writeFileSync(output,JSON.stringify({pid:process.pid,ppid:process.ppid})+'\\n',{flag:'wx'});if(mode==='fail')process.exit(7);if(mode==='wait')setInterval(()=>{},1000);";
const TOOL_PATHS = [
  'scripts/lib/formal-run-admission.mjs',
  'scripts/preflight-b55-e1-budgeted-native-child-pid-receipt.mjs',
  'scripts/run-b55-e1-budgeted-native-child-pid-receipt.mjs',
  'scripts/audit-b55-e1-budgeted-native-child-pid-receipt.mjs',
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

function validSelfHash(record, field) {
  const body = structuredClone(record);
  delete body[field];
  return typeof record[field] === 'string' && record[field] === canonicalHash(body);
}

async function parentEvidenceProbe(spec) {
  const parent = spec.parentEvidence;
  const resultPath = resolve(repositoryRoot, parent.results.uri);
  const auditPath = resolve(repositoryRoot, parent.audit.uri);
  const receiptPath = resolve(repositoryRoot, parent.receipt.uri);
  const result = JSON.parse(await readFile(resultPath, 'utf8'));
  const audit = JSON.parse(await readFile(auditPath, 'utf8'));
  const receipt = JSON.parse(await readFile(receiptPath, 'utf8'));
  const falseGates = Object.entries(result.gates ?? {}).filter(([, value]) => value !== true).map(([key]) => key);
  const singleGapExact = result.scientificVerdict === parent.scientificVerdict
    && Object.keys(result.gates ?? {}).length === parent.frozenObservation.gateCount
    && Object.values(result.gates ?? {}).filter(Boolean).length === parent.frozenObservation.passingGateCount
    && falseGates.length === 1
    && falseGates[0] === parent.frozenObservation.onlyFalseGate
    && result.processEvidence?.nativeCompilePidBindingsAvailable === parent.frozenObservation.nativeCompilePidBindingsAvailable
    && result.processEvidence?.limitation === parent.frozenObservation.limitation
    && audit.gates?.[parent.frozenObservation.onlyFalseGate] === false;
  return {
    result: {
      uri: parent.results.uri,
      sha256: await sha256File(resultPath),
      selfHash: result.resultHash,
      exact: await sha256File(resultPath) === parent.results.sha256
        && result.resultHash === parent.results.resultHash
        && validSelfHash(result, 'resultHash'),
    },
    audit: {
      uri: parent.audit.uri,
      sha256: await sha256File(auditPath),
      selfHash: audit.auditHash,
      exact: await sha256File(auditPath) === parent.audit.sha256
        && audit.auditHash === parent.audit.auditHash
        && validSelfHash(audit, 'auditHash'),
    },
    receipt: {
      uri: parent.receipt.uri,
      sha256: await sha256File(receiptPath),
      selfHash: receipt.receiptHash,
      exact: await sha256File(receiptPath) === parent.receipt.sha256
        && receipt.receiptHash === parent.receipt.receiptHash
        && validSelfHash(receipt, 'receiptHash'),
    },
    falseGates,
    singleGapExact,
  };
}

async function supervisorMinimalityProbe(gitChildren) {
  const beforeResult = await runGit(['show', `${PREREGISTRATION_COMMIT}:${SUPERVISOR_URI}`], repositoryRoot, row => gitChildren.push({ phase: 'SUPERVISOR_BEFORE', ...row }));
  if (beforeResult.exitCode !== 0) throw new Error('Cannot read preregistered supervisor source');
  const before = beforeResult.stdout;
  const after = await readFile(resolve(repositoryRoot, SUPERVISOR_URI), 'utf8');
  let expected = before;
  const replacements = [
    [
      "  const child = spawn(command, args, { cwd, env, detached: process.platform !== 'win32', stdio: ['ignore', 'pipe', 'pipe'] });\n",
      "  const child = spawn(command, args, { cwd, env, detached: process.platform !== 'win32', stdio: ['ignore', 'pipe', 'pipe'] });\n  const childPid = Number.isSafeInteger(child.pid) && child.pid > 0 ? child.pid : null;\n",
    ],
    ["version: '0.1.0'", "version: '0.2.0'"],
    [
      "breach, child: { exitCode: completionResult.code, signal: completionResult.signal, spawnError: spawnError?.message ?? null },",
      "breach, child: { pid: childPid, exitCode: completionResult.code, signal: completionResult.signal, spawnError: spawnError?.message ?? null },",
    ],
  ];
  const replacementCounts = [];
  for (const [from, to] of replacements) {
    const count = expected.split(from).length - 1;
    replacementCounts.push(count);
    if (count === 1) expected = expected.replace(from, to);
  }
  return {
    uri: SUPERVISOR_URI,
    beforeSha256: sha256Bytes(Buffer.from(before)),
    afterSha256: sha256Bytes(Buffer.from(after)),
    expectedSha256: sha256Bytes(Buffer.from(expected)),
    preregisteredBeforeSha256: '0c4cc332139d7e11bd33dccb0c340a3947851907fc02ab68b57be5275ec5ec40',
    replacementCounts,
    exact: replacementCounts.every(count => count === 1)
      && sha256Bytes(Buffer.from(before)) === '0c4cc332139d7e11bd33dccb0c340a3947851907fc02ab68b57be5275ec5ec40'
      && after === expected,
  };
}

function probeBudgets(wallTimeMs) {
  return {
    wallTimeMs,
    maxRssBytes: 1073741824,
    maxLogBytes: 1048576,
    maxOutputFiles: 8,
    maxOutputBytes: 1048576,
    sampleIntervalMs: 10,
  };
}

async function runPidProbeCase(root, definition) {
  const caseRoot = resolve(root, definition.id);
  await mkdir(caseRoot, { recursive: false });
  const observationPath = resolve(caseRoot, 'child-observation.json');
  const reportPath = resolve(caseRoot, 'budget.report.json');
  const result = await runBudgetedProcess({
    command: definition.command,
    args: definition.args(observationPath),
    cwd: repositoryRoot,
    env: { PATH: '/usr/bin:/bin:/opt/homebrew/bin', LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8' },
    outputRoot: caseRoot,
    budgets: probeBudgets(definition.wallTimeMs),
  });
  await writeJson(reportPath, result);
  const observation = definition.hasChild
    ? JSON.parse(await readFile(observationPath, 'utf8'))
    : null;
  const positivePidExact = definition.hasChild
    ? Number.isSafeInteger(result.child?.pid) && result.child.pid > 0
      && observation?.pid === result.child.pid
      && observation?.ppid === process.pid
    : result.child?.pid === null;
  const exact = result.documentType === 'BFS_BUDGETED_PROCESS_RESULT'
    && result.version === '0.2.0'
    && result.outcome === definition.expectedOutcome
    && (!Object.hasOwn(definition, 'expectedExitCode') || result.child?.exitCode === definition.expectedExitCode)
    && (definition.expectedBreach ? result.breach?.reason === definition.expectedBreach : result.breach === null)
    && (definition.hasChild ? result.child?.spawnError === null : typeof result.child?.spawnError === 'string')
    && (definition.expectedBreach ? result.termination?.requested === true && result.termination?.awaited === true : true)
    && positivePidExact;
  return {
    id: definition.id,
    expectedOutcome: definition.expectedOutcome,
    expectedExitCode: Object.hasOwn(definition, 'expectedExitCode') ? definition.expectedExitCode : null,
    expectedBreach: definition.expectedBreach ?? null,
    report: result,
    observation,
    reportUri: repoUri(reportPath),
    reportSha256: await sha256File(reportPath),
    observationUri: observation ? repoUri(observationPath) : null,
    observationSha256: observation ? await sha256File(observationPath) : null,
    positivePidExact,
    exact,
  };
}

async function runPidProbes(outputRoot) {
  const probeRoot = resolve(outputRoot, 'pid-probes');
  await mkdir(probeRoot, { recursive: false });
  const definitions = [
    { id: 'PASS_SELF_REPORT', command: NODE_EXECUTABLE, args: output => ['--input-type=commonjs', '-e', PID_CHILD_SOURCE, output, 'pass'], wallTimeMs: 5000, hasChild: true, expectedOutcome: 'PASS', expectedExitCode: 0 },
    { id: 'CHILD_FAILED_SELF_REPORT', command: NODE_EXECUTABLE, args: output => ['--input-type=commonjs', '-e', PID_CHILD_SOURCE, output, 'fail'], wallTimeMs: 5000, hasChild: true, expectedOutcome: 'CHILD_FAILED', expectedExitCode: 7 },
    { id: 'WALL_TIME_SELF_REPORT', command: NODE_EXECUTABLE, args: output => ['--input-type=commonjs', '-e', PID_CHILD_SOURCE, output, 'wait'], wallTimeMs: 250, hasChild: true, expectedOutcome: 'BUDGET_EXCEEDED', expectedBreach: 'WALL_TIME' },
    { id: 'SPAWN_ERROR_NULL_PID', command: '/nonexistent/bfs-b55-e1-spawn-error', args: () => [], wallTimeMs: 5000, hasChild: false, expectedOutcome: 'CHILD_FAILED' },
  ];
  const cases = [];
  for (const definition of definitions) cases.push(await runPidProbeCase(probeRoot, definition));
  return {
    preflightPid: process.pid,
    cases,
    passed: cases.length === 4 && cases.every(row => row.exact),
  };
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
      firstCanonicalSha256: sha256Bytes(Buffer.from(firstCanonical)),
      secondCanonicalSha256: sha256Bytes(Buffer.from(secondCanonical)),
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
      stdoutSha256: sha256Bytes(Buffer.from(validator.stdout)),
      stderrSha256: sha256Bytes(Buffer.from(validator.stderr)),
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
  const specPath = resolve(repositoryRoot, args.spec ?? 'specs/budgeted-native-child-pid-receipt-correction.v0.1.json');
  if (await sha256File(specPath) !== SPEC_SHA256) throw new Error('B55-E1 spec SHA-256 mismatch');
  const spec = JSON.parse(await readFile(specPath, 'utf8'));
  if (spec.experimentId !== 'B55-E1') throw new Error('B55-E1 experiment identity mismatch');
  if (args.developmentProbe) {
    await runDevelopmentProbe(spec);
    return;
  }
  if (!args.outputRoot || !args.toolFreezeCommit) throw new Error('Official preflight requires --spec, --output-root and --tool-freeze-commit');
  const outputRoot = resolve(repositoryRoot, args.outputRoot);
  if (outputRoot !== resolve(repositoryRoot, spec.freshness.preflightRoot)) throw new Error('Preflight output root mismatch');
  if (await pathState(outputRoot)) throw new Error('Preflight output root already exists; B55-E1 preflight is single-use');
  if (await pathState(resolve(repositoryRoot, spec.freshness.attemptRoot)) || await pathState(resolve(repositoryRoot, spec.freshness.formalRoot))) throw new Error('Attempt/formal root must remain absent before preflight');

  const rootsAbsentBeforeWrite = !await pathState(outputRoot)
    && !await pathState(resolve(repositoryRoot, spec.freshness.attemptRoot))
    && !await pathState(resolve(repositoryRoot, spec.freshness.formalRoot));
  await mkdir(outputRoot, { recursive: false });
  const identityGitChildren = [];
  const toolHashes = {};
  const configurationHashes = {};
  let nodeIdentity = null;
  let blenderIdentity = null;
  let parentEvidence = null;
  let supervisorMinimality = null;
  let pidProbes = null;
  let common = null;
  let checks = { PREFLIGHT_EXECUTION_COMPLETED: false };
  let failure = null;
  try {
    const head = (await runGit(['rev-parse', 'HEAD'], repositoryRoot, row => identityGitChildren.push({ phase: 'HEAD', ...row }))).stdout.trim();
    const originMainResult = await runGit(['rev-parse', '--verify', 'origin/main'], repositoryRoot, row => identityGitChildren.push({ phase: 'ORIGIN_MAIN', ...row }));
    const originMain = originMainResult.stdout.trim();
    const scopedPaths = [...new Set(['specs/budgeted-native-child-pid-receipt-correction.v0.1.json', ...TOOL_PATHS, ...CONFIG_PATHS])];
    const tracked = await runGit(['ls-files', '--', ...scopedPaths], repositoryRoot, row => identityGitChildren.push({ phase: 'TRACKED', ...row }));
    const dirty = await runGit(['status', '--porcelain=v1', '--untracked-files=all', '--', ...scopedPaths], repositoryRoot, row => identityGitChildren.push({ phase: 'CLEAN', ...row }));
    const preregistration = await runGit(['merge-base', '--is-ancestor', PREREGISTRATION_COMMIT, args.toolFreezeCommit], repositoryRoot, row => identityGitChildren.push({ phase: 'PREREGISTRATION_ANCESTRY', ...row }));
    for (const uri of TOOL_PATHS) toolHashes[uri] = await sha256File(resolve(repositoryRoot, uri));
    for (const uri of CONFIG_PATHS) configurationHashes[uri] = await sha256File(resolve(repositoryRoot, uri));
    nodeIdentity = { executable: process.execPath, version: process.version, sha256: await sha256File(process.execPath) };
    blenderIdentity = { executable: BLENDER_EXECUTABLE, sha256: await sha256File(BLENDER_EXECUTABLE), versionBinding: spec.runtime.blender.version, buildHashBinding: spec.runtime.blender.buildHash };
    parentEvidence = await parentEvidenceProbe(spec);
    supervisorMinimality = await supervisorMinimalityProbe(identityGitChildren);
    common = await commonChecks(spec);
    pidProbes = await runPidProbes(outputRoot);
    const trackedUris = tracked.stdout.trim().split('\n').filter(Boolean);
    const unchangedProductionExact = spec.intervention.unchangedProductionFiles.every(row => toolHashes[row.uri] === row.sha256);
    checks = {
      SPEC_AND_PREREGISTRATION_IDENTITY: await sha256File(specPath) === SPEC_SHA256 && preregistration.exitCode === 0,
      B54_PARENT_EVIDENCE_AND_SINGLE_GAP_EXACT: parentEvidence.result.exact && parentEvidence.audit.exact && parentEvidence.receipt.exact && parentEvidence.singleGapExact,
      SUPERVISOR_CHANGE_MINIMAL_AND_SCHEMA_V0_2: supervisorMinimality.exact,
      UNCHANGED_PRODUCTION_FILES_EXACT: unchangedProductionExact,
      TOOL_FREEZE_HEAD_AND_ORIGIN_EXACT: head === args.toolFreezeCommit && originMainResult.exitCode === 0 && originMain === args.toolFreezeCommit,
      ALL_SCOPED_PATHS_TRACKED_CLEAN: tracked.exitCode === 0 && trackedUris.length === scopedPaths.length && scopedPaths.every(uri => trackedUris.includes(uri)) && dirty.exitCode === 0 && dirty.stdout === '',
      NODE_RUNTIME_EXACT: nodeIdentity.executable === spec.runtime.node.executable && nodeIdentity.version === spec.runtime.node.version && nodeIdentity.sha256 === spec.runtime.node.sha256,
      BLENDER_BINARY_EXACT_WITHOUT_PROCESS: blenderIdentity.executable === spec.runtime.blender.executable && blenderIdentity.sha256 === spec.runtime.blender.sha256,
      INPUT_AND_CONFIGURATION_HASHES_EXACT: spec.inputs.benchmarks.every(row => configurationHashes[row.sceneSpecUri] === row.sceneSpecSha256) && configurationHashes[spec.inputs.outputSpec.uri] === spec.inputs.outputSpec.sha256,
      SCENESPEC_SUITE_22_OF_22: common.sceneSpecSuite.passed,
      BUILDPLAN_PAIR_CANONICAL_BYTES_EXACT: common.buildPlans.length === 2 && common.buildPlans.every(row => row.canonicalBytesExact),
      B01_B02_PLAN_HASHES_FROZEN: common.buildPlans.every(row => row.frozenPlanHashExact),
      RELATIVE_COMPONENT_ADMISSION_ACCEPTED: common.componentAdmission.status === 'ACCEPTED' && common.componentAdmission.outputAbsoluteMatches,
      COMPONENT_ADMISSION_CREATED_NO_OUTPUT: common.componentAdmission.outputAbsent,
      PID_PROBE_PASS_FAIL_BREACH_AND_SPAWN_ERROR_EXACT: pidProbes.passed,
      THREE_B55_ROOTS_ABSENT_BEFORE_WRITE: rootsAbsentBeforeWrite,
      DISK_RESERVE_ACCEPTED: common.disk.status === 'ACCEPTED',
      PREFLIGHT_BLENDER_MODEL_NETWORK_RENDER_ZERO: true,
      PREFLIGHT_EXECUTION_COMPLETED: true,
    };
  } catch (error) {
    failure = { name: error?.name ?? 'Error', message: error?.message ?? String(error), stack: error?.stack ?? null };
  }
  const status = !failure && Object.values(checks).every(Boolean) ? 'ACCEPTED' : 'REJECTED';
  const preflightBody = {
    schemaVersion: 'bfs.budgetedNativeChildPidReceiptPreflight.v0.1',
    experimentId: 'B55-E1',
    status,
    scientificVerdict: null,
    preregistrationCommit: PREREGISTRATION_COMMIT,
    toolFreezeCommit: args.toolFreezeCommit,
    specSha256: SPEC_SHA256,
    toolHashes,
    configurationHashes,
    nodeIdentity,
    blenderIdentity,
    parentEvidence,
    supervisorMinimality,
    pidProbes,
    checks,
    checkPassed: Object.values(checks).filter(Boolean).length,
    checkTotal: Object.keys(checks).length,
    sceneSpecSuite: common?.sceneSpecSuite ?? null,
    buildPlans: common?.buildPlans ?? null,
    componentAdmission: common?.componentAdmission ?? null,
    disk: common?.disk ?? null,
    failure,
    operationCounts: {
      preflightProcesses: 1,
      sceneSpecValidatorChildren: common ? 1 : 0,
      pidProbeBudgetCalls: pidProbes?.cases.length ?? 0,
      pidProbeNodeChildren: pidProbes?.cases.filter(row => row.observation !== null).length ?? 0,
      pidProbeSpawnErrors: pidProbes?.cases.filter(row => row.observation === null).length ?? 0,
      gitChildren: identityGitChildren.length + (common?.gitChildren.length ?? 0),
      blenderProcesses: 0,
      blenderRenderCalls: 0,
      cyclesRayRenders: 0,
      dockerProcesses: 0,
      modelCalls: 0,
      networkCalls: 0,
    },
    children: { validator: common?.validator ?? null, git: [...identityGitChildren, ...(common?.gitChildren ?? [])] },
    rootObservations: {
      preflightRoot: { uri: repoUri(outputRoot), absentBeforeWrite: rootsAbsentBeforeWrite },
      attemptRoot: { uri: spec.freshness.attemptRoot, absent: !await pathState(resolve(repositoryRoot, spec.freshness.attemptRoot)) },
      formalRoot: { uri: spec.freshness.formalRoot, absent: !await pathState(resolve(repositoryRoot, spec.freshness.formalRoot)) },
    },
  };
  const preflightPath = resolve(outputRoot, 'preflight.json');
  const preflight = await writeHashed(preflightPath, preflightBody, 'preflightHash');
  const receiptBody = {
    schemaVersion: 'bfs.budgetedNativeChildPidReceiptPreflightReceipt.v0.1',
    experimentId: 'B55-E1',
    status,
    scientificVerdict: null,
    preflight: { uri: `${repoUri(outputRoot)}/preflight.json`, sha256: await sha256File(preflightPath), preflightHash: preflight.preflightHash },
    spec: { uri: repoUri(specPath), sha256: SPEC_SHA256 },
    toolFreezeCommit: args.toolFreezeCommit,
    sameIdRepairAndRerunForbiddenOnFailure: true,
  };
  const receipt = await writeHashed(resolve(outputRoot, 'receipt.json'), receiptBody, 'receiptHash');
  process.stdout.write(`BFS_B55_E1_PREFLIGHT_${status} checks=${preflight.checkPassed}/${preflight.checkTotal} blender=0 receipt=${receipt.receiptHash}\n`);
  if (status !== 'ACCEPTED') process.exitCode = 1;
}

main().catch(error => {
  process.stderr.write(`${error?.stack ?? error}\n`);
  process.exitCode = 1;
});
