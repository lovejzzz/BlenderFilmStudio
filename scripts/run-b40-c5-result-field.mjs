import { spawnSync } from 'node:child_process';
import { statfs, mkdir, readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256File } from './lib/receipt-format.mjs';
import { hashB40Evidence, parseB40ColimaConfig, parseB40Df, parseB40Meminfo, readB40Spec } from './lib/b40-worker-host-capacity-admission.mjs';
import { parseB40C1Binfmt } from './lib/b40-c1-binfmt-parser-correction.mjs';
import { readB40C2Spec } from './lib/b40-c2-serialization-stability.mjs';
import { readB40C4Spec } from './lib/b40-c4-projection-identity.mjs';
import {
  B40_C5_PREREG_COMMIT, B40_C5_SPEC_SHA256, analyzeB40C5Evidence, classifyB40C2Capacity,
  readB40C5Spec, roundTripB40C2, runB40C5Attacks,
} from './lib/b40-c5-result-field.mjs';

const root = resolve(repositoryRoot, 'experiments/worker-host-capacity-admission-v0-6');
const runnerPath = resolve(repositoryRoot, 'scripts/run-b40-c5-result-field.mjs');
const libraryPath = resolve(repositoryRoot, 'scripts/lib/b40-c5-result-field.mjs');
const auditPath = resolve(repositoryRoot, 'scripts/audit-b40-c5-result-field.mjs');
const colimaConfigPath = '/Users/tianxing/.colima/default/colima.yaml';
const c5Spec = await readB40C5Spec();
const c4Spec = await readB40C4Spec();
const c2Spec = await readB40C2Spec();
const baseSpec = await readB40Spec();

function probe(executable, args, label) {
  const result = spawnSync(executable, args, { cwd: repositoryRoot, encoding: 'utf8', maxBuffer: 1024 * 1024 });
  if (result.status !== 0) throw new Error(`${label} failed (${result.status}): ${result.stderr.trim()}`);
  return result.stdout.trim();
}
if (spawnSync('git', ['merge-base', '--is-ancestor', B40_C5_PREREG_COMMIT, 'HEAD'], { cwd: repositoryRoot }).status !== 0) throw new Error('B40-C5 preregistration is not an ancestor');
const toolFreezeCommit = probe('git', ['rev-parse', 'HEAD'], 'tool freeze identity');
if (probe('git', ['status', '--porcelain', '--untracked-files=no'], 'tracked status') !== '') throw new Error('B40-C5 tracked worktree must be clean');
if (process.version !== baseSpec.runtime.nodeVersion || process.execPath !== baseSpec.runtime.nodeBinary) throw new Error('B40-C5 Node identity differs');
const nodeBinarySha256 = await sha256File(process.execPath);
if (nodeBinarySha256 !== baseSpec.runtime.nodeBinarySha256) throw new Error('B40-C5 Node SHA differs');
const c4ResultSha256 = await sha256File(resolve(repositoryRoot, 'experiments/worker-host-capacity-admission-v0-5/results.json'));
const c4AuditSha256 = await sha256File(resolve(repositoryRoot, 'experiments/worker-host-capacity-admission-v0-5/audit.json'));
if (c4ResultSha256 !== c5Spec.c4.resultSha256 || c4AuditSha256 !== c5Spec.c4.auditSha256) throw new Error('B40-C5 C4 evidence differs');
const ancestryFiles = {
  b38SpecSha256: 'specs/worker-launch-contract.v0.1.json', b38ResultSha256: 'experiments/worker-launch-contract-v0-1/results.json',
  b38AuditSha256: 'experiments/worker-launch-contract-v0-1/audit.json', b39C1ResultSha256: 'experiments/linux-worker-architecture-preflight-v0-2/results.json',
  b39C1AuditSha256: 'experiments/linux-worker-architecture-preflight-v0-2/audit.json',
};
const ancestry = Object.fromEntries(await Promise.all(Object.entries(ancestryFiles).map(async ([key, uri]) => [key, await sha256File(resolve(repositoryRoot, uri))])));
if (JSON.stringify(ancestry) !== JSON.stringify(baseSpec.ancestry)) throw new Error('B40-C5 ancestry differs');
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
  schemaVersion: 'bfs.workerHostCapacityEvidence.v0.6', experimentId: 'B40-C5',
  status: 'REPLAY_STABLE_READ_ONLY_CAPACITY_ADMISSION_NO_RUNTIME_OPERATION',
  preregistration: { commit: B40_C5_PREREG_COMMIT, specSha256: B40_C5_SPEC_SHA256 },
  correctionChain: {
    baseSpecSha256: c2Spec.baseProtocol.specSha256, parserCorrectionSpecSha256: c2Spec.parserCorrection.specSha256,
    rejectedC1ResultSha256: c2Spec.rejectedC1.resultSha256, rejectedC1AuditSha256: c2Spec.rejectedC1.auditSha256,
  },
  projectionIdentityCorrection: {
    c3SpecSha256: c4Spec.c3Protocol.specSha256, c3ToolFreezeCommit: c4Spec.c3Protocol.toolFreezeCommit,
    changedImplementationExact: structuredClone(c4Spec.changedImplementationExact),
  },
  resultFieldCorrection: {
    c4SpecSha256: c5Spec.c4.specSha256, c4ResultSha256, c4AuditSha256,
    changedImplementationExact: structuredClone(c5Spec.changedImplementationExact),
  },
  ancestry, toolFreezeCommit,
  runtime: { nodeVersion: process.version, nodeBinary: process.execPath, nodeBinarySha256 },
  tools: {
    runner: { uri: 'scripts/run-b40-c5-result-field.mjs', sha256: await sha256File(runnerPath) },
    library: { uri: 'scripts/lib/b40-c5-result-field.mjs', sha256: await sha256File(libraryPath) },
    audit: { uri: 'scripts/audit-b40-c5-result-field.mjs', sha256: await sha256File(auditPath) },
  },
  policy: { workerCeilings: structuredClone(baseSpec.frozenWorkerCeilingsFromB38), capacity: structuredClone(baseSpec.capacityPolicy) },
  probeTrace: structuredClone(baseSpec.probeTraceExact), runtimeOperationsExecuted: [], observations,
  decision: classifyB40C2Capacity(observations, baseSpec),
  serializationGates: structuredClone(c2Spec.requiredSerializationGates), serializationPassed: true, replayPassed: true,
};
evidence.evidenceHash = hashB40Evidence(evidence);
const analysis = await analyzeB40C5Evidence(evidence, c5Spec, c4Spec, c2Spec, baseSpec);
const attacks = analysis.passed ? await runB40C5Attacks(evidence, c5Spec, c4Spec, c2Spec, baseSpec) : [];
const roundTripEvidence = roundTripB40C2(evidence);
const roundTripAnalysis = await analyzeB40C5Evidence(roundTripEvidence, c5Spec, c4Spec, c2Spec, baseSpec);
const roundTripAttacks = roundTripAnalysis.passed ? await runB40C5Attacks(roundTripEvidence, c5Spec, c4Spec, c2Spec, baseSpec) : [];
const attacksPassed = attacks.length === 14 && attacks.every(attack => attack.passed);
const replayPassed = JSON.stringify(analysis) === JSON.stringify(roundTripAnalysis) && JSON.stringify(attacks) === JSON.stringify(roundTripAttacks);
if (!replayPassed) { evidence.replayPassed = false; evidence.evidenceHash = hashB40Evidence(evidence); }
const result = { ...evidence, analysis, attacks, attacksPassed, verdict: analysis.passed && attacksPassed && replayPassed ? c5Spec.acceptedVerdict : 'RESULT_FIELD_CORRECTION_FAILED', nonClaims: c5Spec.nonClaims };
await mkdir(root, { recursive: true });
await writeFile(resolve(root, 'results.json'), `${JSON.stringify(result, null, 2)}\n`);
process.stdout.write(`BFS_B40_C5_RESULT verdict=${result.verdict} blockers=${result.decision.reasons.join(',')} attacks=${attacks.filter(a => a.passed).length}/14 replay=${replayPassed ? 'PASS' : 'FAIL'} runtimeOps=0\n`);
if (!analysis.passed || !attacksPassed || !replayPassed) process.exitCode = 1;
