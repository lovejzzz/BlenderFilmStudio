import { spawnSync } from 'node:child_process';
import { statfs, mkdir, readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256File } from './lib/receipt-format.mjs';
import {
  B40_PREREG_COMMIT,
  B40_SPEC_SHA256,
  analyzeB40Evidence,
  classifyB40Capacity,
  hashB40Evidence,
  parseB40Binfmt,
  parseB40ColimaConfig,
  parseB40Df,
  parseB40Meminfo,
  readB40Spec,
  runB40Attacks,
} from './lib/b40-worker-host-capacity-admission.mjs';

const experimentRoot = resolve(repositoryRoot, 'experiments/worker-host-capacity-admission-v0-1');
const resultPath = resolve(experimentRoot, 'results.json');
const runnerPath = resolve(repositoryRoot, 'scripts/run-b40-worker-host-capacity-admission.mjs');
const libraryPath = resolve(repositoryRoot, 'scripts/lib/b40-worker-host-capacity-admission.mjs');
const auditPath = resolve(repositoryRoot, 'scripts/audit-b40-worker-host-capacity-admission.mjs');
const colimaConfigPath = '/Users/tianxing/.colima/default/colima.yaml';
const spec = await readB40Spec();

function probe(executable, args, label) {
  const result = spawnSync(executable, args, { cwd: repositoryRoot, encoding: 'utf8', maxBuffer: 1024 * 1024 });
  if (result.status !== 0) throw new Error(`${label} failed (${result.status}): ${result.stderr.trim()}`);
  return result.stdout.trim();
}

if (spawnSync('git', ['merge-base', '--is-ancestor', B40_PREREG_COMMIT, 'HEAD'], { cwd: repositoryRoot }).status !== 0) throw new Error('B40 preregistration is not an ancestor');
const toolFreezeCommit = probe('git', ['rev-parse', 'HEAD'], 'tool freeze identity');
if (probe('git', ['status', '--porcelain', '--untracked-files=no'], 'tracked status') !== '') throw new Error('B40 tracked worktree must be clean');
if (process.version !== spec.runtime.nodeVersion || process.execPath !== spec.runtime.nodeBinary) throw new Error('B40 Node identity differs');
const nodeBinarySha256 = await sha256File(process.execPath);
if (nodeBinarySha256 !== spec.runtime.nodeBinarySha256) throw new Error('B40 Node SHA differs');

const ancestryFiles = {
  b38SpecSha256: 'specs/worker-launch-contract.v0.1.json',
  b38ResultSha256: 'experiments/worker-launch-contract-v0-1/results.json',
  b38AuditSha256: 'experiments/worker-launch-contract-v0-1/audit.json',
  b39C1ResultSha256: 'experiments/linux-worker-architecture-preflight-v0-2/results.json',
  b39C1AuditSha256: 'experiments/linux-worker-architecture-preflight-v0-2/audit.json',
};
const ancestry = Object.fromEntries(await Promise.all(Object.entries(ancestryFiles).map(async ([key, uri]) => [key, await sha256File(resolve(repositoryRoot, uri))])));
if (JSON.stringify(ancestry) !== JSON.stringify(spec.ancestry)) throw new Error('B40 ancestry differs');

const colimaStatus = JSON.parse(probe('colima', ['status', '--json'], 'Colima status'));
const colimaConfigText = await readFile(colimaConfigPath, 'utf8');
const meminfo = parseB40Meminfo(probe('colima', ['ssh', '--', 'cat', '/proc/meminfo'], 'VM meminfo'));
const vmCpus = Number(probe('colima', ['ssh', '--', 'getconf', '_NPROCESSORS_ONLN'], 'VM CPU count'));
const dockerStorage = parseB40Df(probe('colima', ['ssh', '--', 'df', '-B1', '/var/lib/docker'], 'VM Docker storage'));
const registration = spec.capacityPolicy.requiredEmulator.registration;
const emulator = parseB40Binfmt(probe('colima', ['ssh', '--', 'cat', `/proc/sys/fs/binfmt_misc/${registration}`], 'VM emulator registration'), registration);
const runningContainerOutput = probe('docker', ['ps', '--no-trunc', '--quiet'], 'running containers');
const filesystem = await statfs(repositoryRoot, { bigint: true });

const observations = {
  host: {
    architecture: probe('uname', ['-m'], 'host architecture'),
    availableBytes: String(filesystem.bavail * filesystem.bsize),
  },
  colima: {
    status: colimaStatus,
    config: parseB40ColimaConfig(colimaConfigText),
    configSha256: await sha256File(colimaConfigPath),
  },
  vm: {
    ...meminfo,
    onlineCpus: vmCpus,
    dockerStorage,
    emulator,
  },
  docker: {
    runningContainerIds: runningContainerOutput === '' ? [] : runningContainerOutput.split('\n'),
  },
};
const evidence = {
  schemaVersion: 'bfs.workerHostCapacityEvidence.v0.1',
  experimentId: 'B40',
  status: 'READ_ONLY_CAPACITY_ADMISSION_COMPLETE_NO_RUNTIME_OPERATION',
  preregistration: { commit: B40_PREREG_COMMIT, specSha256: B40_SPEC_SHA256 },
  ancestry,
  toolFreezeCommit,
  runtime: { nodeVersion: process.version, nodeBinary: process.execPath, nodeBinarySha256 },
  tools: {
    runner: { uri: 'scripts/run-b40-worker-host-capacity-admission.mjs', sha256: await sha256File(runnerPath) },
    library: { uri: 'scripts/lib/b40-worker-host-capacity-admission.mjs', sha256: await sha256File(libraryPath) },
    audit: { uri: 'scripts/audit-b40-worker-host-capacity-admission.mjs', sha256: await sha256File(auditPath) },
  },
  policy: { workerCeilings: structuredClone(spec.frozenWorkerCeilingsFromB38), capacity: structuredClone(spec.capacityPolicy) },
  probeTrace: structuredClone(spec.probeTraceExact),
  runtimeOperationsExecuted: [],
  observations,
  decision: classifyB40Capacity(observations, spec),
};
evidence.evidenceHash = hashB40Evidence(evidence);
const analysis = analyzeB40Evidence(evidence, spec);
const attacks = analysis.passed ? runB40Attacks(evidence, spec) : [];
const attacksPassed = attacks.length === 14 && attacks.every(attack => attack.passed);
const result = { ...evidence, analysis, attacks, attacksPassed, verdict: analysis.passed && attacksPassed ? spec.acceptedVerdict : analysis.decision, nonClaims: spec.nonClaims };
await mkdir(experimentRoot, { recursive: true });
await writeFile(resultPath, `${JSON.stringify(result, null, 2)}\n`);
process.stdout.write(`BFS_B40_RESULT verdict=${result.verdict} blockers=${result.decision.reasons.join(',')} attacks=${attacks.filter(a => a.passed).length}/14 emulator=${result.decision.gates.x64Emulator.status} runtimeOps=0\n`);
if (!analysis.passed || !attacksPassed) process.exitCode = 1;
