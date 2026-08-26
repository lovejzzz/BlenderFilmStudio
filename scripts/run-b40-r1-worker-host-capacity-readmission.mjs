import { spawnSync } from 'node:child_process';
import { mkdir, readFile, statfs, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256File } from './lib/receipt-format.mjs';
import { parseB40ColimaConfig, parseB40Df, parseB40Meminfo, readB40Spec } from './lib/b40-worker-host-capacity-admission.mjs';
import { parseB40C1Binfmt } from './lib/b40-c1-binfmt-parser-correction.mjs';
import {
  B40_R1_PREREG_COMMIT, B40_R1_SPEC_SHA256, analyzeB40R1Evidence, classifyB40Capacity,
  hashB40Evidence, readB40R1Spec, roundTripB40R1, runB40R1Attacks,
} from './lib/b40-r1-worker-host-capacity-readmission.mjs';

const root = resolve(repositoryRoot, 'experiments/worker-host-capacity-readmission-v0-1');
const runnerPath = resolve(repositoryRoot, 'scripts/run-b40-r1-worker-host-capacity-readmission.mjs');
const libraryPath = resolve(repositoryRoot, 'scripts/lib/b40-r1-worker-host-capacity-readmission.mjs');
const auditPath = resolve(repositoryRoot, 'scripts/audit-b40-r1-worker-host-capacity-readmission.mjs');
const colimaConfigPath = '/Users/tianxing/.colima/default/colima.yaml';
const spec = await readB40R1Spec();
const baseSpec = await readB40Spec();

function probe(executable, args, label) {
  const result = spawnSync(executable, args, { cwd: repositoryRoot, encoding: 'utf8', maxBuffer: 1024 * 1024 });
  if (result.status !== 0) throw new Error(`${label} failed (${result.status}): ${result.stderr.trim()}`);
  return result.stdout.trim();
}

if (spawnSync('git', ['merge-base', '--is-ancestor', B40_R1_PREREG_COMMIT, 'HEAD'], { cwd: repositoryRoot }).status !== 0) throw new Error('B40-R1 preregistration is not an ancestor');
const toolFreezeCommit = probe('git', ['rev-parse', 'HEAD'], 'tool freeze identity');
if (probe('git', ['status', '--porcelain', '--untracked-files=no'], 'tracked status') !== '') throw new Error('B40-R1 tracked worktree must be clean');
if (process.version !== spec.runtime.nodeVersion || process.execPath !== spec.runtime.nodeBinary) throw new Error('B40-R1 Node identity differs');
const nodeBinarySha256 = await sha256File(process.execPath);
if (nodeBinarySha256 !== spec.runtime.nodeBinarySha256) throw new Error('B40-R1 Node SHA differs');
const ancestryFiles = {
  baseAdmissionSpecSha256: 'specs/worker-host-capacity-admission.v0.1.json',
  b40C5ResultSha256: 'experiments/worker-host-capacity-admission-v0-6/results.json',
  b40C5AuditSha256: 'experiments/worker-host-capacity-admission-v0-6/audit.json',
};
const ancestry = Object.fromEntries(await Promise.all(Object.entries(ancestryFiles).map(async ([key, uri]) => [key, await sha256File(resolve(repositoryRoot, uri))])));
if (JSON.stringify(ancestry) !== JSON.stringify(spec.ancestry)) throw new Error('B40-R1 ancestry differs');
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
const evidence = {
  schemaVersion: 'bfs.workerHostCapacityReadmissionEvidence.v0.1', experimentId: 'B40-R1',
  status: 'POST_INTERVENTION_READ_ONLY_CAPACITY_READMISSION_NO_RUNTIME_OPERATION',
  preregistration: { commit: B40_R1_PREREG_COMMIT, specSha256: B40_R1_SPEC_SHA256 },
  ancestry, toolFreezeCommit,
  runtime: { nodeVersion: process.version, nodeBinary: process.execPath, nodeBinarySha256 },
  tools: {
    runner: { uri: 'scripts/run-b40-r1-worker-host-capacity-readmission.mjs', sha256: await sha256File(runnerPath) },
    library: { uri: 'scripts/lib/b40-r1-worker-host-capacity-readmission.mjs', sha256: await sha256File(libraryPath) },
    audit: { uri: 'scripts/audit-b40-r1-worker-host-capacity-readmission.mjs', sha256: await sha256File(auditPath) },
  },
  policy: { workerCeilings: structuredClone(baseSpec.frozenWorkerCeilingsFromB38), capacity: structuredClone(baseSpec.capacityPolicy) },
  probeTrace: structuredClone(spec.probeTraceExact), runtimeOperationsExecuted: [], observations,
  decision: classifyB40Capacity(observations, baseSpec), replayPassed: true,
};
evidence.evidenceHash = hashB40Evidence(evidence);
const analysis = await analyzeB40R1Evidence(evidence, spec, baseSpec);
const attacks = analysis.passed ? await runB40R1Attacks(evidence, spec, baseSpec) : [];
const roundTripEvidence = roundTripB40R1(evidence);
const roundTripAnalysis = await analyzeB40R1Evidence(roundTripEvidence, spec, baseSpec);
const roundTripAttacks = roundTripAnalysis.passed ? await runB40R1Attacks(roundTripEvidence, spec, baseSpec) : [];
const attacksPassed = attacks.length === 16 && attacks.every(attack => attack.passed);
const replayPassed = JSON.stringify(analysis) === JSON.stringify(roundTripAnalysis)
  && JSON.stringify(attacks) === JSON.stringify(roundTripAttacks);
if (!replayPassed) { evidence.replayPassed = false; evidence.evidenceHash = hashB40Evidence(evidence); }
const result = {
  ...evidence, analysis, attacks, attacksPassed,
  verdict: analysis.passed && attacksPassed && replayPassed ? spec.acceptedVerdict : 'WORKER_HOST_CAPACITY_READMISSION_FAILED',
  nonClaims: spec.nonClaims,
};
await mkdir(root, { recursive: true });
await writeFile(resolve(root, 'results.json'), `${JSON.stringify(result, null, 2)}\n`);
process.stdout.write(`BFS_B40_R1_RESULT verdict=${result.verdict} blockers=${result.decision.reasons.join(',')} attacks=${attacks.filter(a => a.passed).length}/16 replay=${replayPassed ? 'PASS' : 'FAIL'} runtimeOps=0\n`);
if (!analysis.passed || !attacksPassed || !replayPassed) process.exitCode = 1;
