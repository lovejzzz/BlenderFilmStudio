import { spawnSync } from 'node:child_process';
import { statfs, mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256Canonical, sha256File } from './lib/receipt-format.mjs';
import {
  B38_PARENT_CANARY_KEY,
  B38_PARENT_CANARY_VALUE,
  B38_PREREG_COMMIT,
  B38_SPEC_SHA256,
  analyzeB38Admission,
  analyzeB38Evidence,
  analyzeB38Plan,
  analyzeB38Receipt,
  compileB38WorkerLaunchPlan,
  createB38SyntheticReceipt,
  evaluateB38Admission,
  readB38Spec,
  reverseObjectOrderDeep,
  runB38AnalyzerAttacks,
} from './lib/b38-worker-launch-contract.mjs';

const experimentRoot = resolve(repositoryRoot, 'experiments/worker-launch-contract-v0-1');
const resultPath = resolve(experimentRoot, 'results.json');
const runnerPath = resolve(repositoryRoot, 'scripts/run-b38-worker-launch-contract.mjs');
const libraryPath = resolve(repositoryRoot, 'scripts/lib/b38-worker-launch-contract.mjs');
const auditPath = resolve(repositoryRoot, 'scripts/audit-b38-worker-launch-contract.mjs');
const spec = await readB38Spec();

const preregCheck = spawnSync('git', ['merge-base', '--is-ancestor', B38_PREREG_COMMIT, 'HEAD'], { cwd: repositoryRoot });
if (preregCheck.status !== 0) throw new Error(`B38 prereg commit ${B38_PREREG_COMMIT} is not an ancestor of HEAD`);
const toolFreezeCommit = spawnSync('git', ['rev-parse', 'HEAD'], { cwd: repositoryRoot, encoding: 'utf8' }).stdout.trim();
const trackedStatus = spawnSync('git', ['status', '--porcelain', '--untracked-files=no'], { cwd: repositoryRoot, encoding: 'utf8' }).stdout.trim();
if (trackedStatus !== '') throw new Error(`B38 tracked worktree must be clean before result: ${trackedStatus}`);
if (process.version !== spec.runtime.nodeVersion || process.execPath !== spec.runtime.nodeBinary) throw new Error('B38 Node runtime identity differs');
const nodeBinarySha256 = await sha256File(process.execPath);
if (nodeBinarySha256 !== spec.runtime.nodeBinarySha256) throw new Error(`B38 Node SHA differs: ${nodeBinarySha256}`);

const imageDigest = `bfs/blender-worker@sha256:${'a'.repeat(64)}`;
const requests = [
  {
    schemaVersion: 'bfs.workerRequest.v0.1', jobId: 'B38_COMPILE', attemptId: 'ATTEMPT_01',
    inputRootIdentity: 'bfs-input:compile-b01', outputRootIdentity: 'bfs-output:compile-b01-attempt-01',
    sceneUri: 'scenes/B01.scene.blend', trustedScriptUri: 'trusted/compile_scene.py',
    scriptArgs: ['--plan', '/inputs/plans/B01.build-plan.json', '--output-dir', '/outputs'],
    projectedWriteBytes: '134217728', imageReference: imageDigest,
  },
  {
    schemaVersion: 'bfs.workerRequest.v0.1', jobId: 'B38_RENDER', attemptId: 'ATTEMPT_01',
    inputRootIdentity: 'bfs-input:render-b02', outputRootIdentity: 'bfs-output:render-b02-attempt-01',
    sceneUri: 'scenes/B02.scene.blend', trustedScriptUri: 'trusted/render_review.py',
    scriptArgs: ['--frames', '1:24', '--output-dir', '/outputs/frames'],
    projectedWriteBytes: '5368709120', imageReference: imageDigest,
  },
  {
    schemaVersion: 'bfs.workerRequest.v0.1', jobId: 'B38_AUDIT', attemptId: 'ATTEMPT_01',
    inputRootIdentity: 'bfs-input:audit-b03', outputRootIdentity: 'bfs-output:audit-b03-attempt-01',
    sceneUri: 'scenes/B03.scene.blend', trustedScriptUri: 'trusted/audit_scene.py',
    scriptArgs: ['--report', '/outputs/audit.json'], projectedWriteBytes: '67108864', imageReference: imageDigest,
  },
];
const parentEnvironment = { ...process.env, [B38_PARENT_CANARY_KEY]: B38_PARENT_CANARY_VALUE };
const fixtures = requests.map((request, index) => {
  const reorderedRequest = reverseObjectOrderDeep(request);
  const plan = compileB38WorkerLaunchPlan(request, spec, parentEnvironment);
  const reorderedPlan = compileB38WorkerLaunchPlan(reorderedRequest, spec, parentEnvironment);
  return {
    id: `P${index + 1}`,
    request,
    reorderedRequest,
    requestHash: sha256Canonical(request),
    reorderedRequestHash: sha256Canonical(reorderedRequest),
    plan,
    reorderedPlan,
    analysis: analyzeB38Plan(plan, request, spec),
    reorderedAnalysis: analyzeB38Plan(reorderedPlan, reorderedRequest, spec),
  };
});

const accepted = evaluateB38Admission({ availableBytes: String(140 * 1024 ** 3), projectedWriteBytes: String(20 * 1024 ** 3), outputRootEmpty: true }, spec);
const dirty = evaluateB38Admission({ availableBytes: String(140 * 1024 ** 3), projectedWriteBytes: String(1024 ** 3), outputRootEmpty: false }, spec);
const belowReserve = evaluateB38Admission({ availableBytes: String(119 * 1024 ** 3), projectedWriteBytes: String(20 * 1024 ** 3), outputRootEmpty: true }, spec);
const filesystem = await statfs(repositoryRoot, { bigint: true });
const hostObserved = evaluateB38Admission({
  availableBytes: String(filesystem.bavail * filesystem.bsize),
  projectedWriteBytes: String(spec.contract.diskAdmission.defaultProjectedWriteBytes),
  outputRootEmpty: true,
}, spec);
const admissions = {
  accepted, acceptedAnalysis: analyzeB38Admission(accepted, spec),
  dirty, dirtyAnalysis: analyzeB38Admission(dirty, spec),
  belowReserve, belowReserveAnalysis: analyzeB38Admission(belowReserve, spec),
  hostObserved, hostObservedAnalysis: analyzeB38Admission(hostObserved, spec),
};
const basePlan = fixtures[0].plan;
const receiptEntries = Object.fromEntries(['SUCCEEDED', 'FAILED', 'TIMED_OUT', 'CANCELLED'].flatMap(status => {
  const key = status.toLowerCase();
  const receipt = createB38SyntheticReceipt(basePlan, status, spec);
  return [[key, receipt], [`${key}Analysis`, analyzeB38Receipt(receipt, basePlan, spec)]];
}));
const evidence = {
  schemaVersion: 'bfs.workerLaunchContractEvidence.v0.1', experimentId: 'B38',
  status: 'PURE_CONTRACT_RUN_COMPLETE_NO_CHILD_PROCESS',
  preregistration: { commit: B38_PREREG_COMMIT, specSha256: B38_SPEC_SHA256 },
  toolFreezeCommit,
  runtime: { nodeVersion: process.version, nodeBinary: process.execPath, nodeBinarySha256 },
  tools: {
    runner: { uri: 'scripts/run-b38-worker-launch-contract.mjs', sha256: await sha256File(runnerPath) },
    library: { uri: 'scripts/lib/b38-worker-launch-contract.mjs', sha256: await sha256File(libraryPath) },
    audit: { uri: 'scripts/audit-b38-worker-launch-contract.mjs', sha256: await sha256File(auditPath) },
  },
  fixtures,
  admissions,
  receipts: receiptEntries,
};
const analysis = analyzeB38Evidence(evidence, spec);
const attacks = analysis.passed ? runB38AnalyzerAttacks(evidence, spec) : [];
const attacksPassed = attacks.length === spec.frozenAnalyzerAttacks.length && attacks.every(attack => attack.passed);
const result = {
  ...evidence,
  analysis,
  attacks,
  attacksPassed,
  verdict: analysis.passed && attacksPassed ? 'WORKER_LAUNCH_CONTRACT_LOGIC_SUPPORT_ONLY' : analysis.decision,
  nonClaims: spec.nonClaims,
};
await mkdir(experimentRoot, { recursive: true });
await writeFile(resultPath, `${JSON.stringify(result, null, 2)}\n`);
process.stdout.write(`BFS_B38_RESULT verdict=${result.verdict} fixtures=${fixtures.length} canonicalPairs=${fixtures.filter(fixture => fixture.plan.planHash === fixture.reorderedPlan.planHash).length}/3 attacks=${attacks.filter(attack => attack.passed).length}/25 hostAdmission=${hostObserved.status}\n`);
if (!analysis.passed || !attacksPassed) process.exitCode = 1;
