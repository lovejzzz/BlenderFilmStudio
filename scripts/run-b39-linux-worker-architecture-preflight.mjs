import { spawnSync } from 'node:child_process';
import { statfs, mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256File } from './lib/receipt-format.mjs';
import {
  B39_PREREG_COMMIT,
  B39_SPEC_SHA256,
  analyzeB39Evidence,
  classifyB39Routes,
  evaluateB39DiskAdmission,
  hashB39Evidence,
  parseB39OfficialArtifacts,
  readB39Spec,
  runB39AnalyzerAttacks,
} from './lib/b39-linux-worker-architecture-preflight.mjs';

const experimentRoot = resolve(repositoryRoot, 'experiments/linux-worker-architecture-preflight-v0-1');
const resultPath = resolve(experimentRoot, 'results.json');
const runnerPath = resolve(repositoryRoot, 'scripts/run-b39-linux-worker-architecture-preflight.mjs');
const libraryPath = resolve(repositoryRoot, 'scripts/lib/b39-linux-worker-architecture-preflight.mjs');
const auditPath = resolve(repositoryRoot, 'scripts/audit-b39-linux-worker-architecture-preflight.mjs');
const spec = await readB39Spec();

function probe(executable, args, label) {
  const result = spawnSync(executable, args, { cwd: repositoryRoot, encoding: 'utf8', maxBuffer: 1024 * 1024 });
  if (result.status !== 0) throw new Error(`${label} failed (${result.status}): ${result.stderr.trim()}`);
  return result.stdout.trim();
}

async function fetchBoundedText(url, label) {
  const response = await fetch(url, { redirect: 'error', signal: AbortSignal.timeout(15000) });
  if (!response.ok) throw new Error(`${label} returned HTTP ${response.status}`);
  const text = await response.text();
  if (text.length > 2 * 1024 * 1024) throw new Error(`${label} exceeded 2 MiB text limit`);
  return text;
}

const preregCheck = spawnSync('git', ['merge-base', '--is-ancestor', B39_PREREG_COMMIT, 'HEAD'], { cwd: repositoryRoot });
if (preregCheck.status !== 0) throw new Error(`B39 prereg commit ${B39_PREREG_COMMIT} is not an ancestor of HEAD`);
const toolFreezeCommit = probe('git', ['rev-parse', 'HEAD'], 'tool freeze identity');
const trackedStatus = probe('git', ['status', '--porcelain', '--untracked-files=no'], 'tracked status');
if (trackedStatus !== '') throw new Error(`B39 tracked worktree must be clean before result: ${trackedStatus}`);
if (process.version !== spec.runtime.nodeVersion || process.execPath !== spec.runtime.nodeBinary) throw new Error('B39 Node runtime identity differs');
const nodeBinarySha256 = await sha256File(process.execPath);
if (nodeBinarySha256 !== spec.runtime.nodeBinarySha256) throw new Error(`B39 Node SHA differs: ${nodeBinarySha256}`);

const releaseIndexText = await fetchBoundedText(spec.officialArtifactSource.releaseIndexUrl, 'Blender release index');
const checksumText = await fetchBoundedText(spec.officialArtifactSource.checksumUrl, 'Blender checksum manifest');
const officialArtifacts = parseB39OfficialArtifacts(releaseIndexText, checksumText, spec);
const hostArchitectureRaw = probe('uname', ['-m'], 'host architecture');
const colima = JSON.parse(probe('colima', ['status', '--json'], 'Colima status'));
const dockerServerVersion = probe('docker', ['version', '--format', '{{.Server.Version}}'], 'Docker server version');
const dockerArchitecture = probe('docker', ['info', '--format', '{{.Architecture}}'], 'Docker architecture');
const dockerSecurityOptions = JSON.parse(probe('docker', ['info', '--format', '{{json .SecurityOptions}}'], 'Docker security options'));
const existingImagesRaw = JSON.parse(probe('docker', ['image', 'inspect', 'debian:bookworm-slim', 'alpine:3.20'], 'existing base image metadata'));
const filesystem = await statfs(repositoryRoot, { bigint: true });
const diskAdmission = evaluateB39DiskAdmission({
  availableBytes: String(filesystem.bavail * filesystem.bsize),
  projectedWriteBytes: String(spec.diskAdmission.projectedRuntimeWriteBytes),
}, spec);

const observations = {
  officialArtifacts,
  host: {
    hostArchitecture: hostArchitectureRaw === 'arm64' ? 'arm64' : hostArchitectureRaw,
    colima: {
      driver: colima.driver,
      architecture: colima.arch,
      runtime: colima.runtime,
      mountType: colima.mount_type,
      cpu: colima.cpu,
      memoryBytes: colima.memory,
    },
    docker: {
      serverVersion: dockerServerVersion,
      architecture: dockerArchitecture,
      securityOptions: dockerSecurityOptions,
    },
    existingImages: existingImagesRaw.map(image => ({
      repoTags: image.RepoTags,
      architecture: image.Architecture,
      os: image.Os,
      id: image.Id,
    })).sort((left, right) => left.repoTags[0].localeCompare(right.repoTags[0])),
  },
  diskAdmission,
  futureRuntime: {
    experimentId: spec.futureRuntimeCanary.experimentId,
    state: 'PENDING_SEPARATE_PREREGISTRATION',
    workerImageDigest: spec.futureRuntimeCanary.workerImageDigest,
  },
};

const evidence = {
  schemaVersion: 'bfs.linuxWorkerArchitecturePreflightEvidence.v0.1',
  experimentId: 'B39',
  status: 'READ_ONLY_PREFLIGHT_COMPLETE_NO_RUNTIME_OPERATION',
  preregistration: { commit: B39_PREREG_COMMIT, specSha256: B39_SPEC_SHA256 },
  toolFreezeCommit,
  runtime: { nodeVersion: process.version, nodeBinary: process.execPath, nodeBinarySha256 },
  tools: {
    runner: { uri: 'scripts/run-b39-linux-worker-architecture-preflight.mjs', sha256: await sha256File(runnerPath) },
    library: { uri: 'scripts/lib/b39-linux-worker-architecture-preflight.mjs', sha256: await sha256File(libraryPath) },
    audit: { uri: 'scripts/audit-b39-linux-worker-architecture-preflight.mjs', sha256: await sha256File(auditPath) },
  },
  sources: {
    releaseIndexUrl: spec.officialArtifactSource.releaseIndexUrl,
    checksumUrl: spec.officialArtifactSource.checksumUrl,
  },
  probeTrace: [
    'HOST_UNAME',
    'COLIMA_STATUS',
    'DOCKER_SERVER_VERSION',
    'DOCKER_ARCH_SECURITY',
    'DOCKER_EXISTING_IMAGE_INSPECT',
    'BLENDER_RELEASE_INDEX_HTTPS',
    'BLENDER_SHA256_MANIFEST_HTTPS',
    'HOST_STATFS',
  ],
  runtimeOperationsExecuted: [],
  observations,
  routes: classifyB39Routes(observations, spec),
};
evidence.evidenceHash = hashB39Evidence(evidence);
const analysis = analyzeB39Evidence(evidence, spec);
const attacks = analysis.passed ? runB39AnalyzerAttacks(evidence, spec) : [];
const attacksPassed = attacks.length === spec.frozenAnalyzerAttacks.length && attacks.every(attack => attack.passed);
const result = {
  ...evidence,
  analysis,
  attacks,
  attacksPassed,
  verdict: analysis.passed && attacksPassed ? 'ARCHITECTURE_PREFLIGHT_SUPPORT_RUNTIME_BLOCKED' : analysis.decision,
  nonClaims: spec.nonClaims,
};
await mkdir(experimentRoot, { recursive: true });
await writeFile(resultPath, `${JSON.stringify(result, null, 2)}\n`);
process.stdout.write(`BFS_B39_RESULT verdict=${result.verdict} native=${result.routes.nativeArm64.decision} x64=${result.routes.x64Emulated.decision} attacks=${attacks.filter(attack => attack.passed).length}/15 disk=${diskAdmission.status} runtimeOps=0\n`);
if (!analysis.passed || !attacksPassed) process.exitCode = 1;
