import { spawnSync } from 'node:child_process';
import { mkdir, readFile, statfs, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { canonicalJson, sha256File } from './lib/receipt-format.mjs';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { classifyB40Capacity, parseB40ColimaConfig, parseB40Df, parseB40Meminfo, readB40Spec } from './lib/b40-worker-host-capacity-admission.mjs';
import { parseB40C1Binfmt } from './lib/b40-c1-binfmt-parser-correction.mjs';
import { readB40R1Spec } from './lib/b40-r1-worker-host-capacity-readmission.mjs';
import {
  B40_R2_PREREG_COMMIT, B40_R2_SPEC_SHA256, analyzeB40R2Evidence, hashB40Evidence,
  readB40R2Spec, roundTripB40R2, runB40R2Attacks,
} from './lib/b40-r2-readmission-replay-correction.mjs';

const root = resolve(repositoryRoot, 'experiments/worker-host-capacity-readmission-v0-2');
const runnerPath = resolve(repositoryRoot, 'scripts/run-b40-r2-readmission-replay-correction.mjs');
const libraryPath = resolve(repositoryRoot, 'scripts/lib/b40-r2-readmission-replay-correction.mjs');
const auditPath = resolve(repositoryRoot, 'scripts/audit-b40-r2-readmission-replay-correction.mjs');
const colimaConfigPath = '/Users/tianxing/.colima/default/colima.yaml';
const r2Spec = await readB40R2Spec();
const r1Spec = await readB40R1Spec();
const baseSpec = await readB40Spec();

function probe(executable, args, label) {
  const result = spawnSync(executable, args, { cwd: repositoryRoot, encoding: 'utf8', maxBuffer: 1024 * 1024 });
  if (result.status !== 0) throw new Error(`${label} failed (${result.status}): ${result.stderr.trim()}`);
  return result.stdout.trim();
}

if (spawnSync('git', ['merge-base', '--is-ancestor', B40_R2_PREREG_COMMIT, 'HEAD'], { cwd: repositoryRoot }).status !== 0) throw new Error('B40-R2 preregistration is not an ancestor');
const toolFreezeCommit = probe('git', ['rev-parse', 'HEAD'], 'tool freeze identity');
if (probe('git', ['status', '--porcelain', '--untracked-files=no'], 'tracked status') !== '') throw new Error('B40-R2 tracked worktree must be clean');
if (process.version !== r1Spec.runtime.nodeVersion || process.execPath !== r1Spec.runtime.nodeBinary) throw new Error('B40-R2 Node identity differs');
const nodeBinarySha256 = await sha256File(process.execPath);
if (nodeBinarySha256 !== r1Spec.runtime.nodeBinarySha256) throw new Error('B40-R2 Node SHA differs');
const failedResultSha256 = await sha256File(resolve(repositoryRoot, 'experiments/worker-host-capacity-readmission-v0-1/attempt-1-results.json'));
const failedAuditSha256 = await sha256File(resolve(repositoryRoot, 'experiments/worker-host-capacity-readmission-v0-1/attempt-1-audit.json'));
if (failedResultSha256 !== r2Spec.r1.failedResultSha256 || failedAuditSha256 !== r2Spec.r1.failedAuditSha256) throw new Error('B40-R2 R1 failure evidence differs');
const ancestryFiles = {
  baseAdmissionSpecSha256: 'specs/worker-host-capacity-admission.v0.1.json',
  b40C5ResultSha256: 'experiments/worker-host-capacity-admission-v0-6/results.json',
  b40C5AuditSha256: 'experiments/worker-host-capacity-admission-v0-6/audit.json',
};
const ancestry = Object.fromEntries(await Promise.all(Object.entries(ancestryFiles).map(async ([key, uri]) => [key, await sha256File(resolve(repositoryRoot, uri))])));
if (JSON.stringify(ancestry) !== JSON.stringify(r1Spec.ancestry)) throw new Error('B40-R2 ancestry differs');
const colimaStatus = JSON.parse(probe('colima', ['status', '--json'], 'Colima status'));
const colimaConfigText = await readFile(colimaConfigPath, 'utf8');
const registration = baseSpec.capacityPolicy.requiredEmulator.registration;
const running = probe('docker', ['ps', '--no-trunc', '--quiet'], 'running containers');
const filesystem = await statfs(repositoryRoot, { bigint: true });
const observations = {
  host: { architecture: probe('uname', ['-m'], 'host architecture'), availableBytes: String(filesystem.bavail * filesystem.bsize) },
  colima: { status: colimaStatus, config: parseB40ColimaConfig(colimaConfigText), configSha256: await sha256File(colimaConfigPath) },
  vm: {
    ...parseB40Meminfo(probe('colima', ['ssh', '--', 'cat', '/proc/meminfo'], 'VM meminfo')),
    onlineCpus: Number(probe('colima', ['ssh', '--', 'getconf', '_NPROCESSORS_ONLN'], 'VM CPUs')),
    dockerStorage: parseB40Df(probe('colima', ['ssh', '--', 'df', '-B1', '/var/lib/docker'], 'VM Docker storage')),
    emulator: parseB40C1Binfmt(probe('colima', ['ssh', '--', 'cat', `/proc/sys/fs/binfmt_misc/${registration}`], 'VM emulator'), registration),
  },
  docker: { runningContainerIds: running === '' ? [] : running.split('\n') },
};
const rawEvidence = {
  schemaVersion: 'bfs.workerHostCapacityReadmissionEvidence.v0.2', experimentId: 'B40-R2',
  status: 'CANONICAL_REPLAY_DIAGNOSTIC_READ_ONLY_CAPACITY_READMISSION',
  preregistration: { commit: B40_R2_PREREG_COMMIT, specSha256: B40_R2_SPEC_SHA256 },
  replayCorrection: {
    r1SpecSha256: r2Spec.r1.specSha256, r1PreregistrationCommit: r2Spec.r1.preregistrationCommit,
    r1ToolFreezeCommit: r2Spec.r1.toolFreezeCommit, failedResultSha256, failedAuditSha256,
    changedImplementationExact: structuredClone(r2Spec.changedImplementationExact),
  },
  ancestry, toolFreezeCommit,
  runtime: { nodeVersion: process.version, nodeBinary: process.execPath, nodeBinarySha256 },
  tools: {
    runner: { uri: 'scripts/run-b40-r2-readmission-replay-correction.mjs', sha256: await sha256File(runnerPath) },
    library: { uri: 'scripts/lib/b40-r2-readmission-replay-correction.mjs', sha256: await sha256File(libraryPath) },
    audit: { uri: 'scripts/audit-b40-r2-readmission-replay-correction.mjs', sha256: await sha256File(auditPath) },
  },
  policy: { workerCeilings: structuredClone(baseSpec.frozenWorkerCeilingsFromB38), capacity: structuredClone(baseSpec.capacityPolicy) },
  probeTrace: structuredClone(r1Spec.probeTraceExact), runtimeOperationsExecuted: [], observations,
  decision: classifyB40Capacity(observations, baseSpec),
  replayDiagnostics: { evidenceCanonicalEqual: true, analysisEqual: true, attackVectorEqual: true }, replayPassed: true,
};
let evidence = roundTripB40R2(rawEvidence);
evidence.evidenceHash = hashB40Evidence(evidence);
const firstAnalysis = await analyzeB40R2Evidence(evidence, r2Spec, r1Spec, baseSpec);
const firstAttacks = firstAnalysis.passed ? await runB40R2Attacks(evidence, r2Spec, r1Spec, baseSpec) : [];
const replayEvidence = roundTripB40R2(evidence);
const replayAnalysis = await analyzeB40R2Evidence(replayEvidence, r2Spec, r1Spec, baseSpec);
const replayAttacks = replayAnalysis.passed ? await runB40R2Attacks(replayEvidence, r2Spec, r1Spec, baseSpec) : [];
const diagnostics = {
  evidenceCanonicalEqual: canonicalJson(evidence) === canonicalJson(replayEvidence),
  analysisEqual: canonicalJson(firstAnalysis) === canonicalJson(replayAnalysis),
  attackVectorEqual: canonicalJson(firstAttacks) === canonicalJson(replayAttacks),
};
const replayPassed = Object.values(diagnostics).every(Boolean);
evidence.replayDiagnostics = diagnostics;
evidence.replayPassed = replayPassed;
evidence.evidenceHash = hashB40Evidence(evidence);
const analysis = await analyzeB40R2Evidence(evidence, r2Spec, r1Spec, baseSpec);
const attacks = analysis.passed ? await runB40R2Attacks(evidence, r2Spec, r1Spec, baseSpec) : firstAttacks;
const attacksPassed = attacks.length === 16 && attacks.every(attack => attack.passed);
const result = {
  ...evidence, analysis, attacks, attacksPassed,
  verdict: analysis.passed && attacksPassed && replayPassed ? r2Spec.acceptedVerdict : 'WORKER_HOST_CAPACITY_REPLAY_CORRECTION_FAILED',
  nonClaims: r2Spec.nonClaims,
};
await mkdir(root, { recursive: true });
await writeFile(resolve(root, 'results.json'), `${JSON.stringify(result, null, 2)}\n`);
process.stdout.write(`BFS_B40_R2_RESULT verdict=${result.verdict} blockers=${result.decision.reasons.join(',')} attacks=${attacks.filter(a => a.passed).length}/16 replay=${replayPassed ? 'PASS' : 'FAIL'} diagnostics=${Object.values(diagnostics).map(v => v ? '1' : '0').join('')} runtimeOps=0\n`);
if (!analysis.passed || !attacksPassed || !replayPassed) process.exitCode = 1;
