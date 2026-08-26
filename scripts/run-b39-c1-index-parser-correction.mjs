import { spawnSync } from 'node:child_process';
import { statfs, mkdir, readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256File } from './lib/receipt-format.mjs';
import { evaluateB39DiskAdmission, hashB39Evidence } from './lib/b39-linux-worker-architecture-preflight.mjs';
import {
  B39_C1_PREREG_COMMIT,
  B39_C1_SPEC_SHA256,
  analyzeB39C1Evidence,
  classifyB39C1Routes,
  parseB39C1Artifacts,
  readB39C1Spec,
  runB39C1Attacks,
} from './lib/b39-c1-index-parser-correction.mjs';

const experimentRoot = resolve(repositoryRoot, 'experiments/linux-worker-architecture-preflight-v0-2');
const runnerPath = resolve(repositoryRoot, 'scripts/run-b39-c1-index-parser-correction.mjs');
const libraryPath = resolve(repositoryRoot, 'scripts/lib/b39-c1-index-parser-correction.mjs');
const auditPath = resolve(repositoryRoot, 'scripts/audit-b39-c1-index-parser-correction.mjs');
const spec = await readB39C1Spec();

function probe(executable, args, label) {
  const result = spawnSync(executable, args, { cwd: repositoryRoot, encoding: 'utf8', maxBuffer: 1024 * 1024 });
  if (result.status !== 0) throw new Error(`${label} failed (${result.status}): ${result.stderr.trim()}`);
  return result.stdout.trim();
}

async function fetchBounded(url, label) {
  const response = await fetch(url, { redirect: 'error', signal: AbortSignal.timeout(15000) });
  if (!response.ok) throw new Error(`${label} returned HTTP ${response.status}`);
  const text = await response.text();
  if (text.length > 2 * 1024 * 1024) throw new Error(`${label} exceeded 2 MiB`);
  return text;
}

if (spawnSync('git', ['merge-base', '--is-ancestor', B39_C1_PREREG_COMMIT, 'HEAD'], { cwd: repositoryRoot }).status !== 0) throw new Error('B39-C1 preregistration is not an ancestor');
const toolFreezeCommit = probe('git', ['rev-parse', 'HEAD'], 'tool freeze identity');
if (probe('git', ['status', '--porcelain', '--untracked-files=no'], 'tracked status') !== '') throw new Error('B39-C1 tracked worktree must be clean');
if (process.version !== spec.runtime.nodeVersion || process.execPath !== spec.runtime.nodeBinary) throw new Error('B39-C1 Node identity differs');
const nodeBinarySha256 = await sha256File(process.execPath);
if (nodeBinarySha256 !== spec.runtime.nodeBinarySha256) throw new Error('B39-C1 Node SHA differs');
const parentResultSha256 = await sha256File(resolve(repositoryRoot, 'experiments/linux-worker-architecture-preflight-v0-1/results.json'));
const parentAuditSha256 = await sha256File(resolve(repositoryRoot, 'experiments/linux-worker-architecture-preflight-v0-1/audit.json'));
if (parentResultSha256 !== spec.correctionFrom.resultSha256 || parentAuditSha256 !== spec.correctionFrom.auditSha256) throw new Error('B39-C1 parent evidence differs');

const [indexText, checksumText] = await Promise.all([
  fetchBounded(spec.sources.releaseIndexUrl, 'release index'),
  fetchBounded(spec.sources.checksumUrl, 'checksum manifest'),
]);
const colima = JSON.parse(probe('colima', ['status', '--json'], 'Colima status'));
const images = JSON.parse(probe('docker', ['image', 'inspect', 'debian:bookworm-slim', 'alpine:3.20'], 'existing images'));
const filesystem = await statfs(repositoryRoot, { bigint: true });
const observations = {
  officialArtifacts: parseB39C1Artifacts(indexText, checksumText, spec),
  host: {
    hostArchitecture: probe('uname', ['-m'], 'host architecture'),
    colima: { driver: colima.driver, architecture: colima.arch },
    docker: {
      serverVersion: probe('docker', ['version', '--format', '{{.Server.Version}}'], 'Docker version'),
      architecture: probe('docker', ['info', '--format', '{{.Architecture}}'], 'Docker architecture'),
      securityOptions: JSON.parse(probe('docker', ['info', '--format', '{{json .SecurityOptions}}'], 'Docker security options')),
    },
    existingImages: images.map(image => ({ repoTags: image.RepoTags, architecture: image.Architecture, os: image.Os, id: image.Id })).sort((a, b) => a.repoTags[0].localeCompare(b.repoTags[0])),
  },
  diskAdmission: evaluateB39DiskAdmission({
    availableBytes: String(filesystem.bavail * filesystem.bsize),
    projectedWriteBytes: String(spec.diskAdmission.projectedRuntimeWriteBytes),
  }, { diskAdmission: spec.diskAdmission }),
  futureRuntime: structuredClone(spec.futureRuntime),
};
const evidence = {
  schemaVersion: 'bfs.linuxWorkerArchitecturePreflightEvidence.v0.2',
  experimentId: 'B39-C1',
  status: 'CORRECTED_READ_ONLY_PREFLIGHT_COMPLETE_NO_RUNTIME_OPERATION',
  preregistration: { commit: B39_C1_PREREG_COMMIT, specSha256: B39_C1_SPEC_SHA256 },
  correctionFrom: { ...spec.correctionFrom, parentResultObservedSha256: parentResultSha256, parentAuditObservedSha256: parentAuditSha256 },
  toolFreezeCommit,
  runtime: { nodeVersion: process.version, nodeBinary: process.execPath, nodeBinarySha256 },
  tools: {
    runner: { uri: 'scripts/run-b39-c1-index-parser-correction.mjs', sha256: await sha256File(runnerPath) },
    library: { uri: 'scripts/lib/b39-c1-index-parser-correction.mjs', sha256: await sha256File(libraryPath) },
    audit: { uri: 'scripts/audit-b39-c1-index-parser-correction.mjs', sha256: await sha256File(auditPath) },
  },
  sources: structuredClone(spec.sources),
  probeTrace: structuredClone(spec.probeTraceExact),
  runtimeOperationsExecuted: [],
  observations,
  routes: classifyB39C1Routes(observations, spec),
};
evidence.evidenceHash = hashB39Evidence(evidence);
const analysis = analyzeB39C1Evidence(evidence, spec);
const attacks = analysis.passed ? runB39C1Attacks(evidence, spec) : [];
const attacksPassed = attacks.length === 15 && attacks.every(attack => attack.passed);
const result = { ...evidence, analysis, attacks, attacksPassed, verdict: analysis.passed && attacksPassed ? spec.acceptedVerdict : analysis.decision, nonClaims: spec.nonClaims };
await mkdir(experimentRoot, { recursive: true });
await writeFile(resolve(experimentRoot, 'results.json'), `${JSON.stringify(result, null, 2)}\n`);
process.stdout.write(`BFS_B39_C1_RESULT verdict=${result.verdict} raw=${observations.officialArtifacts.x64.rawFilenameOccurrences} href=${observations.officialArtifacts.x64.exactHrefTargetOccurrences} native=${result.routes.nativeArm64.decision} x64=${result.routes.x64Emulated.decision} attacks=${attacks.filter(a => a.passed).length}/15 disk=${observations.diskAdmission.status} runtimeOps=0\n`);
if (!analysis.passed || !attacksPassed) process.exitCode = 1;
