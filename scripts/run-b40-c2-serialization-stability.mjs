import { spawnSync } from 'node:child_process';
import { statfs, mkdir, readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256File } from './lib/receipt-format.mjs';
import { hashB40Evidence, parseB40ColimaConfig, parseB40Df, parseB40Meminfo, readB40Spec } from './lib/b40-worker-host-capacity-admission.mjs';
import { parseB40C1Binfmt } from './lib/b40-c1-binfmt-parser-correction.mjs';
import {
  B40_C2_PREREG_COMMIT,
  B40_C2_SPEC_SHA256,
  analyzeB40C2Evidence,
  classifyB40C2Capacity,
  readB40C2Spec,
  roundTripB40C2,
  runB40C2Attacks,
} from './lib/b40-c2-serialization-stability.mjs';

const root = resolve(repositoryRoot, 'experiments/worker-host-capacity-admission-v0-3');
const runnerPath = resolve(repositoryRoot, 'scripts/run-b40-c2-serialization-stability.mjs');
const libraryPath = resolve(repositoryRoot, 'scripts/lib/b40-c2-serialization-stability.mjs');
const auditPath = resolve(repositoryRoot, 'scripts/audit-b40-c2-serialization-stability.mjs');
const colimaConfigPath = '/Users/tianxing/.colima/default/colima.yaml';
const correctionSpec = await readB40C2Spec();
const baseSpec = await readB40Spec();

function probe(executable, args, label) {
  const result = spawnSync(executable, args, { cwd: repositoryRoot, encoding: 'utf8', maxBuffer: 1024 * 1024 });
  if (result.status !== 0) throw new Error(`${label} failed (${result.status}): ${result.stderr.trim()}`);
  return result.stdout.trim();
}

if (spawnSync('git', ['merge-base', '--is-ancestor', B40_C2_PREREG_COMMIT, 'HEAD'], { cwd: repositoryRoot }).status !== 0) throw new Error('B40-C2 preregistration is not an ancestor');
const toolFreezeCommit = probe('git', ['rev-parse', 'HEAD'], 'tool freeze identity');
if (probe('git', ['status', '--porcelain', '--untracked-files=no'], 'tracked status') !== '') throw new Error('B40-C2 tracked worktree must be clean');
if (process.version !== baseSpec.runtime.nodeVersion || process.execPath !== baseSpec.runtime.nodeBinary) throw new Error('B40-C2 Node identity differs');
const nodeBinarySha256 = await sha256File(process.execPath);
if (nodeBinarySha256 !== baseSpec.runtime.nodeBinarySha256) throw new Error('B40-C2 Node SHA differs');
const rejectedC1ResultSha256 = await sha256File(resolve(repositoryRoot, 'experiments/worker-host-capacity-admission-v0-2/results.json'));
const rejectedC1AuditSha256 = await sha256File(resolve(repositoryRoot, 'experiments/worker-host-capacity-admission-v0-2/audit.json'));
if (rejectedC1ResultSha256 !== correctionSpec.rejectedC1.resultSha256 || rejectedC1AuditSha256 !== correctionSpec.rejectedC1.auditSha256) throw new Error('B40-C2 rejected C1 evidence differs');

const ancestryFiles = {
  b38SpecSha256: 'specs/worker-launch-contract.v0.1.json', b38ResultSha256: 'experiments/worker-launch-contract-v0-1/results.json',
  b38AuditSha256: 'experiments/worker-launch-contract-v0-1/audit.json', b39C1ResultSha256: 'experiments/linux-worker-architecture-preflight-v0-2/results.json',
  b39C1AuditSha256: 'experiments/linux-worker-architecture-preflight-v0-2/audit.json',
};
const ancestry = Object.fromEntries(await Promise.all(Object.entries(ancestryFiles).map(async ([key, uri]) => [key, await sha256File(resolve(repositoryRoot, uri))])));
if (JSON.stringify(ancestry) !== JSON.stringify(baseSpec.ancestry)) throw new Error('B40-C2 base ancestry differs');
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
  schemaVersion: 'bfs.workerHostCapacityEvidence.v0.3', experimentId: 'B40-C2',
  status: 'SERIALIZATION_STABLE_READ_ONLY_CAPACITY_ADMISSION_NO_RUNTIME_OPERATION',
  preregistration: { commit: B40_C2_PREREG_COMMIT, specSha256: B40_C2_SPEC_SHA256 },
  correctionChain: {
    baseSpecSha256: correctionSpec.baseProtocol.specSha256,
    parserCorrectionSpecSha256: correctionSpec.parserCorrection.specSha256,
    rejectedC1ResultSha256,
    rejectedC1AuditSha256,
  },
  ancestry,
  toolFreezeCommit,
  runtime: { nodeVersion: process.version, nodeBinary: process.execPath, nodeBinarySha256 },
  tools: {
    runner: { uri: 'scripts/run-b40-c2-serialization-stability.mjs', sha256: await sha256File(runnerPath) },
    library: { uri: 'scripts/lib/b40-c2-serialization-stability.mjs', sha256: await sha256File(libraryPath) },
    audit: { uri: 'scripts/audit-b40-c2-serialization-stability.mjs', sha256: await sha256File(auditPath) },
  },
  policy: { workerCeilings: structuredClone(baseSpec.frozenWorkerCeilingsFromB38), capacity: structuredClone(baseSpec.capacityPolicy) },
  probeTrace: structuredClone(baseSpec.probeTraceExact), runtimeOperationsExecuted: [], observations,
  decision: classifyB40C2Capacity(observations, baseSpec),
  serializationGates: structuredClone(correctionSpec.requiredSerializationGates),
  serializationPassed: true,
};
evidence.evidenceHash = hashB40Evidence(evidence);
const analysis = await analyzeB40C2Evidence(evidence, correctionSpec, baseSpec);
const attacks = analysis.passed ? await runB40C2Attacks(evidence, correctionSpec, baseSpec) : [];
const roundTripEvidence = roundTripB40C2(evidence);
const roundTripAnalysis = await analyzeB40C2Evidence(roundTripEvidence, correctionSpec, baseSpec);
const roundTripAttacks = roundTripAnalysis.passed ? await runB40C2Attacks(roundTripEvidence, correctionSpec, baseSpec) : [];
const attacksPassed = attacks.length === 14 && attacks.every(attack => attack.passed);
const serializationPassed = JSON.stringify(analysis) === JSON.stringify(roundTripAnalysis)
  && JSON.stringify(evidence.decision) === JSON.stringify(roundTripEvidence.decision)
  && evidence.evidenceHash === roundTripEvidence.evidenceHash
  && JSON.stringify(attacks) === JSON.stringify(roundTripAttacks);
if (!serializationPassed) {
  evidence.serializationPassed = false;
  evidence.evidenceHash = hashB40Evidence(evidence);
}
const result = { ...evidence, analysis, attacks, attacksPassed, serializationPassed, verdict: analysis.passed && attacksPassed && serializationPassed ? correctionSpec.acceptedVerdict : 'SERIALIZATION_STABILITY_FAILED', nonClaims: correctionSpec.nonClaims };
await mkdir(root, { recursive: true });
await writeFile(resolve(root, 'results.json'), `${JSON.stringify(result, null, 2)}\n`);
process.stdout.write(`BFS_B40_C2_RESULT verdict=${result.verdict} blockers=${result.decision.reasons.join(',')} attacks=${attacks.filter(a => a.passed).length}/14 serialization=${serializationPassed ? 'PASS' : 'FAIL'} runtimeOps=0\n`);
if (!analysis.passed || !attacksPassed || !serializationPassed) process.exitCode = 1;
