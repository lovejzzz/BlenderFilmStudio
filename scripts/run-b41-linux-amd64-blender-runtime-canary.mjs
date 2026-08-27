import { spawn, spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { createWriteStream } from 'node:fs';
import { chmod, cp, mkdir, mkdtemp, readFile, readdir, rm, stat, statfs, writeFile } from 'node:fs/promises';
import { basename, join, relative, resolve } from 'node:path';
import { Readable } from 'node:stream';
import { pipeline } from 'node:stream/promises';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256File } from './lib/receipt-format.mjs';
import {
  B41_PREREG_COMMIT, B41_SPEC_SHA256, analyzeB41Evidence, expectedB41Argv, expectedB41Environment,
  hashB41Evidence, readB41Spec,
} from './lib/b41-linux-amd64-blender-runtime-canary.mjs';
import {
  B41_C1_PREREG_COMMIT, B41_C1_SPEC_SHA256, analyzeB41C1Evidence, normalizeB41DockerArchitecture, readB41C1Spec,
} from './lib/b41-c1-docker-architecture-correction.mjs';
import {
  B41_C2_PREREG_COMMIT, B41_C2_SPEC_SHA256, analyzeB41C2Evidence, hashB41C2Evidence, readB41C2Spec,
} from './lib/b41-c2-build-receipt-tooling-correction.mjs';
import {
  B41_C3_PREREG_COMMIT, B41_C3_SPEC_SHA256, analyzeB41C3Evidence, hashB41C3Evidence, readB41C3Spec,
} from './lib/b41-c3-guest-buildx-correction.mjs';
import {
  B41_C4_PREREG_COMMIT, B41_C4_SPEC_SHA256, analyzeB41C4Evidence, hashB41C4Evidence, readB41C4Spec,
} from './lib/b41-c4-platform-binary-identity-correction.mjs';

const spec = await readB41Spec();
const binaryIdentityCorrectionMode = process.argv.includes('--c4');
const buildxCorrectionMode = process.argv.includes('--c3') || binaryIdentityCorrectionMode;
const toolingCorrectionMode = process.argv.includes('--c2') || buildxCorrectionMode;
const correctionMode = process.argv.includes('--c1') || toolingCorrectionMode;
const correctionSpec = correctionMode ? await readB41C1Spec() : null;
const toolingCorrectionSpec = toolingCorrectionMode ? await readB41C2Spec() : null;
const buildxCorrectionSpec = buildxCorrectionMode ? await readB41C3Spec() : null;
const binaryIdentityCorrectionSpec = binaryIdentityCorrectionMode ? await readB41C4Spec() : null;
const experimentRoot = resolve(repositoryRoot, binaryIdentityCorrectionMode
  ? 'experiments/linux-amd64-blender-runtime-canary-v0-5'
  : buildxCorrectionMode
  ? 'experiments/linux-amd64-blender-runtime-canary-v0-4'
  : toolingCorrectionMode ? 'experiments/linux-amd64-blender-runtime-canary-v0-3'
  : correctionMode ? 'experiments/linux-amd64-blender-runtime-canary-v0-2' : 'experiments/linux-amd64-blender-runtime-canary-v0-1');
const successRoot = resolve(experimentRoot, 'success');
const timeoutRoot = resolve(experimentRoot, 'timeout');
const dockerfilePath = resolve(repositoryRoot, 'worker/b41/Dockerfile');
const runtimeCanaryPath = resolve(repositoryRoot, 'fixtures/b41/runtime-canary.py');
const timeoutCanaryPath = resolve(repositoryRoot, 'fixtures/b41/timeout-canary.py');
const libraryPath = resolve(repositoryRoot, binaryIdentityCorrectionMode
  ? 'scripts/lib/b41-c4-platform-binary-identity-correction.mjs'
  : buildxCorrectionMode
  ? 'scripts/lib/b41-c3-guest-buildx-correction.mjs'
  : toolingCorrectionMode ? 'scripts/lib/b41-c2-build-receipt-tooling-correction.mjs'
  : correctionMode ? 'scripts/lib/b41-c1-docker-architecture-correction.mjs'
  : 'scripts/lib/b41-linux-amd64-blender-runtime-canary.mjs');
const runnerPath = resolve(repositoryRoot, 'scripts/run-b41-linux-amd64-blender-runtime-canary.mjs');
const auditPath = resolve(repositoryRoot, binaryIdentityCorrectionMode
  ? 'scripts/audit-b41-c4-platform-binary-identity-correction.mjs'
  : buildxCorrectionMode
  ? 'scripts/audit-b41-c3-guest-buildx-correction.mjs'
  : toolingCorrectionMode ? 'scripts/audit-b41-c2-build-receipt-tooling-correction.mjs'
  : correctionMode ? 'scripts/audit-b41-c1-docker-architecture-correction.mjs'
  : 'scripts/audit-b41-linux-amd64-blender-runtime-canary.mjs');
const dockerBase = ['--host', spec.runtime.dockerHost];
const experimentNames = ['bfs-b41-success-01', 'bfs-b41-timeout-01'];
const operations = [];
const errors = [];

function probe(executable, args, label, options = {}) {
  const result = spawnSync(executable, args, {
    cwd: options.cwd ?? repositoryRoot, encoding: 'utf8', maxBuffer: options.maxBuffer ?? 100 * 1024 * 1024,
    timeout: options.timeout,
  });
  if (result.status !== 0) throw new Error(`${label} failed (${result.status}): ${(result.stderr || result.stdout || '').trim().slice(-4000)}`);
  return result.stdout.trim();
}

async function treeManifestSha256(root) {
  const files = [];
  async function visit(directory) {
    for (const entry of await readdir(directory, { withFileTypes: true })) {
      const path = join(directory, entry.name);
      if (entry.isDirectory()) await visit(path);
      else if (entry.isFile()) files.push(path);
    }
  }
  await visit(root);
  files.sort((left, right) => toolingCorrectionMode
    ? Buffer.compare(Buffer.from(relative(root, left)), Buffer.from(relative(root, right)))
    : relative(root, left).localeCompare(relative(root, right), 'en'));
  const lines = [];
  for (const file of files) lines.push(`${await sha256File(file)}  ./${relative(root, file).replaceAll('\\', '/')}`);
  return createHash('sha256').update(`${lines.join('\n')}\n`).digest('hex');
}

async function download(url, destination) {
  const response = await fetch(url, { redirect: 'follow' });
  if (!response.ok || !response.body) throw new Error(`download failed: HTTP ${response.status}`);
  await pipeline(Readable.fromWeb(response.body), createWriteStream(destination, { flags: 'wx' }));
}

function pngInfo(path) {
  return readFile(path).then(bytes => ({
    valid: bytes.length >= 24 && bytes.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]))
      && bytes.subarray(12, 16).toString('ascii') === 'IHDR',
    dimensions: bytes.length >= 24 ? [bytes.readUInt32BE(16), bytes.readUInt32BE(20)] : null,
    bytes: bytes.length,
    sha256: createHash('sha256').update(bytes).digest('hex'),
  })).catch(() => ({ valid: false, dimensions: null, bytes: 0, sha256: null }));
}

async function fileInfo(path) {
  try { const info = await stat(path); return { bytes: info.size, sha256: await sha256File(path) }; }
  catch { return { bytes: 0, sha256: null }; }
}

function dockerRunArgs({ name, imageId, inputRoot, outputRoot, environment, argv }) {
  const args = [...dockerBase, 'run', '--rm', '--name', name, '--platform', spec.runtime.containerPlatform, '--pull', 'never',
    '--read-only', '--network', 'none', '--user', spec.containerContract.user, '--cap-drop', 'ALL',
    '--security-opt', 'no-new-privileges:true', '--pids-limit', String(spec.containerContract.pidsLimit),
    '--memory', String(spec.containerContract.memoryBytes), '--cpus', String(spec.containerContract.cpus),
    '--shm-size', String(spec.containerContract.shmBytes),
    '--mount', `type=bind,src=${inputRoot},dst=/inputs,readonly`, '--mount', `type=bind,src=${outputRoot},dst=/outputs`,
  ];
  for (const tmpfs of spec.containerContract.tmpfs) args.push('--tmpfs', tmpfs);
  for (const key of spec.containerContract.environmentKeysExact) args.push('--env', `${key}=${environment[key]}`);
  return [...args, imageId, ...argv];
}

async function runTimedContainer({ name, args, wallTimeMs, graceMs }) {
  const started = Date.now();
  let stdout = '';
  let stderr = '';
  let timeoutTriggered = false;
  let termSent = false;
  let forceKillSent = false;
  let termAtMs = null;
  let forceAtMs = null;
  const child = spawn('docker', args, { cwd: repositoryRoot, env: { ...process.env, BFS_PARENT_SECRET: 'MUST_NOT_ENTER_CONTAINER' } });
  child.stdout.on('data', chunk => { stdout += chunk.toString(); });
  child.stderr.on('data', chunk => { stderr += chunk.toString(); });
  let forceTimer = null;
  const wallTimer = setTimeout(() => {
    timeoutTriggered = true;
    termAtMs = Date.now() - started;
    const term = spawnSync('docker', [...dockerBase, 'kill', '--signal', 'TERM', name], { encoding: 'utf8' });
    operations.push('DOCKER_KILL_TERM');
    termSent = term.status === 0;
    forceTimer = setTimeout(() => {
      forceAtMs = Date.now() - started;
      const killed = spawnSync('docker', [...dockerBase, 'kill', '--signal', 'KILL', name], { encoding: 'utf8' });
      operations.push('DOCKER_KILL_KILL');
      forceKillSent = killed.status === 0;
    }, graceMs);
  }, wallTimeMs);
  const close = await new Promise(resolveClose => child.on('close', (code, signal) => resolveClose({ code, signal })));
  clearTimeout(wallTimer);
  if (forceTimer) clearTimeout(forceTimer);
  return {
    exitCode: close.code, signal: close.signal, elapsedMs: Date.now() - started, stdout, stderr,
    timedOut: timeoutTriggered, timeoutTriggered, termSent, forceKillSent, termAtMs, forceAtMs,
  };
}

const preregistrationCommit = binaryIdentityCorrectionMode ? B41_C4_PREREG_COMMIT : buildxCorrectionMode ? B41_C3_PREREG_COMMIT : toolingCorrectionMode ? B41_C2_PREREG_COMMIT : correctionMode ? B41_C1_PREREG_COMMIT : B41_PREREG_COMMIT;
const preregistrationSpecSha256 = binaryIdentityCorrectionMode ? B41_C4_SPEC_SHA256 : buildxCorrectionMode ? B41_C3_SPEC_SHA256 : toolingCorrectionMode ? B41_C2_SPEC_SHA256 : correctionMode ? B41_C1_SPEC_SHA256 : B41_SPEC_SHA256;
if (spawnSync('git', ['merge-base', '--is-ancestor', preregistrationCommit, 'HEAD'], { cwd: repositoryRoot }).status !== 0) throw new Error('B41 preregistration is not an ancestor');
const toolFreezeCommit = probe('git', ['rev-parse', 'HEAD'], 'tool freeze identity');
if (probe('git', ['status', '--porcelain', '--untracked-files=no'], 'tracked status') !== '') throw new Error('B41 tracked worktree must be clean');
if (process.version !== spec.runtime.nodeVersion || process.execPath !== spec.runtime.nodeBinary) throw new Error('B41 Node identity differs');
const nodeBinarySha256 = await sha256File(process.execPath);
if (nodeBinarySha256 !== spec.runtime.nodeBinarySha256) throw new Error('B41 Node SHA differs');
const dockerIdentity = JSON.parse(probe('docker', [...dockerBase, 'version', '--format', '{{json .Server}}'], 'Docker server identity'));
const rawDockerArchitecture = dockerIdentity.Arch;
const canonicalDockerArchitecture = correctionMode
  ? normalizeB41DockerArchitecture(rawDockerArchitecture, correctionSpec)
  : rawDockerArchitecture;
if (canonicalDockerArchitecture !== spec.runtime.dockerServerArchitecture) throw new Error('B41 Docker server architecture differs');
for (const name of experimentNames) {
  const existing = spawnSync('docker', [...dockerBase, 'container', 'inspect', name], { encoding: 'utf8' });
  if (existing.status === 0) throw new Error(`B41 container name already exists: ${name}`);
}
const ancestryFiles = {
  b38SpecSha256: 'specs/worker-launch-contract.v0.1.json', b38ResultSha256: 'experiments/worker-launch-contract-v0-1/results.json',
  b38AuditSha256: 'experiments/worker-launch-contract-v0-1/audit.json', b39C1ResultSha256: 'experiments/linux-worker-architecture-preflight-v0-2/results.json',
  b39C1AuditSha256: 'experiments/linux-worker-architecture-preflight-v0-2/audit.json', b40R2ResultSha256: 'experiments/worker-host-capacity-readmission-v0-2/results.json',
  b40R2AuditSha256: 'experiments/worker-host-capacity-readmission-v0-2/audit.json',
};
const ancestry = Object.fromEntries(await Promise.all(Object.entries(ancestryFiles).map(async ([key, uri]) => [key, await sha256File(resolve(repositoryRoot, uri))])));
if (JSON.stringify(ancestry) !== JSON.stringify(spec.ancestry)) throw new Error('B41 ancestry differs');
let c1FailedResultSha256 = null;
let c1FailedAuditSha256 = null;
if (toolingCorrectionMode) {
  c1FailedResultSha256 = await sha256File(resolve(repositoryRoot, 'experiments/linux-amd64-blender-runtime-canary-v0-2/results.json'));
  c1FailedAuditSha256 = await sha256File(resolve(repositoryRoot, 'experiments/linux-amd64-blender-runtime-canary-v0-2/audit.json'));
  if (c1FailedResultSha256 !== toolingCorrectionSpec.parent.failedResultSha256
    || c1FailedAuditSha256 !== toolingCorrectionSpec.parent.failedAuditSha256) throw new Error('B41-C2 parent failure evidence differs');
}
let c2FailedResultSha256 = null;
let c2FailedAuditSha256 = null;
if (buildxCorrectionMode) {
  c2FailedResultSha256 = await sha256File(resolve(repositoryRoot, 'experiments/linux-amd64-blender-runtime-canary-v0-3/results.json'));
  c2FailedAuditSha256 = await sha256File(resolve(repositoryRoot, 'experiments/linux-amd64-blender-runtime-canary-v0-3/audit.json'));
  if (c2FailedResultSha256 !== buildxCorrectionSpec.parent.failedResultSha256
    || c2FailedAuditSha256 !== buildxCorrectionSpec.parent.failedAuditSha256) throw new Error('B41-C3 parent failure evidence differs');
}
let c3FailedResultSha256 = null;
let c3FailedAuditSha256 = null;
let derivedLinuxResultSha256 = null;
let derivedLinuxAuditSha256 = null;
if (binaryIdentityCorrectionMode) {
  c3FailedResultSha256 = await sha256File(resolve(repositoryRoot, 'experiments/linux-amd64-blender-runtime-canary-v0-4/results.json'));
  c3FailedAuditSha256 = await sha256File(resolve(repositoryRoot, 'experiments/linux-amd64-blender-runtime-canary-v0-4/audit.json'));
  derivedLinuxResultSha256 = await sha256File(resolve(repositoryRoot, 'experiments/linux-amd64-blender-binary-identity-derivation-v0-2/results.json'));
  derivedLinuxAuditSha256 = await sha256File(resolve(repositoryRoot, 'experiments/linux-amd64-blender-binary-identity-derivation-v0-2/audit.json'));
  if (c3FailedResultSha256 !== binaryIdentityCorrectionSpec.parent.failedResultSha256
    || c3FailedAuditSha256 !== binaryIdentityCorrectionSpec.parent.failedAuditSha256
    || derivedLinuxResultSha256 !== binaryIdentityCorrectionSpec.derivation.resultSha256
    || derivedLinuxAuditSha256 !== binaryIdentityCorrectionSpec.derivation.auditSha256) throw new Error('B41-C4 parent or derivation evidence differs');
}
let buildTransport = null;
if (buildxCorrectionMode) {
  const versionText = probe('colima', ['ssh', '--', 'docker', 'buildx', 'version'], 'B41-C3 buildx version');
  const inspectText = probe('colima', ['ssh', '--', 'docker', 'buildx', 'inspect'], 'B41-C3 buildx inspect');
  const platforms = inspectText.match(/^Platforms:\s*(.+)$/m)?.[1].split(',').map(value => value.trim()) ?? [];
  buildTransport = {
    buildxVersion: versionText.match(/\bv[0-9]+\.[0-9]+\.[0-9]+\b/)?.[0] ?? null,
    builderName: inspectText.match(/^Name:\s*(\S+)/m)?.[1] ?? null,
    driver: inspectText.match(/^Driver:\s*(\S+)/m)?.[1] ?? null,
    buildkitVersion: inspectText.match(/^BuildKit version:\s*(\S+)/m)?.[1] ?? null,
    platforms,
    command: null,
  };
}
const filesystem = await statfs(repositoryRoot, { bigint: true });
const availableBytes = filesystem.bavail * filesystem.bsize;
const freeAfterProjected = availableBytes - BigInt(spec.diskAdmission.projectedWriteBytes);
const diskAdmission = {
  availableBytes: String(availableBytes), projectedWriteBytes: String(spec.diskAdmission.projectedWriteBytes),
  minimumReserveBytes: String(spec.diskAdmission.minimumReserveBytes), freeAfterProjectedBytes: String(freeAfterProjected),
  status: freeAfterProjected >= BigInt(spec.diskAdmission.minimumReserveBytes) ? 'ACCEPTED' : 'BLOCKED',
};
if (diskAdmission.status !== 'ACCEPTED') throw new Error('B41 disk admission blocked');

await mkdir(experimentRoot, { recursive: false });
await mkdir(successRoot);
await mkdir(timeoutRoot);
await chmod(successRoot, 0o777);
await chmod(timeoutRoot, 0o777);
const temporaryRoot = await mkdtemp(resolve(repositoryRoot, '.bfs-b41-'));
const buildRoot = resolve(temporaryRoot, 'build');
const inputRoot = resolve(temporaryRoot, 'inputs');
await mkdir(buildRoot);
await mkdir(inputRoot);
await cp(dockerfilePath, resolve(buildRoot, 'Dockerfile'));
await cp(runtimeCanaryPath, resolve(inputRoot, basename(runtimeCanaryPath)));
await cp(timeoutCanaryPath, resolve(inputRoot, basename(timeoutCanaryPath)));
await cp(spec.inputFixture.ocioSource, resolve(inputRoot, 'ocio'), { recursive: true });
const ocioTreeManifestSha256 = await treeManifestSha256(resolve(inputRoot, 'ocio'));
const archivePath = resolve(buildRoot, spec.artifact.filename);
let artifact = { url: spec.artifact.url, filename: spec.artifact.filename, bytes: null, sha256: null };
let image = { buildExitCode: null, id: null, os: null, architecture: null };
let success = {};
let timeout = {};
let temporaryBuildRootRemoved = false;
try {
  await download(spec.artifact.url, archivePath);
  const archiveStat = await stat(archivePath);
  artifact = { ...artifact, bytes: archiveStat.size, sha256: await sha256File(archivePath) };
  if (artifact.bytes !== spec.artifact.bytes || artifact.sha256 !== spec.artifact.sha256) throw new Error('B41 downloaded archive identity differs');
  operations.push('DOCKER_BUILD');
  const buildStarted = Date.now();
  const buildxCommand = ['colima', 'ssh', '--', 'docker', ...(buildxCorrectionSpec?.buildTransport.innerArgsPrefix ?? []),
    '--tag', spec.imageBuild.tag, '--file', resolve(buildRoot, 'Dockerfile'), buildRoot];
  if (buildxCorrectionMode) buildTransport.command = buildxCommand;
  const build = buildxCorrectionMode
    ? spawnSync(buildxCommand[0], buildxCommand.slice(1), { cwd: repositoryRoot, encoding: 'utf8', maxBuffer: 100 * 1024 * 1024, timeout: 20 * 60 * 1000 })
    : spawnSync('docker', [...dockerBase, 'build', '--platform', spec.runtime.containerPlatform, '--pull',
      ...(toolingCorrectionMode ? [] : ['--progress', 'plain']),
      '--tag', spec.imageBuild.tag, '--file', 'Dockerfile', '.'], { cwd: buildRoot, encoding: 'utf8', maxBuffer: 100 * 1024 * 1024, timeout: 20 * 60 * 1000 });
  await writeFile(resolve(experimentRoot, 'build.stdout.log'), build.stdout ?? '');
  await writeFile(resolve(experimentRoot, 'build.stderr.log'), build.stderr ?? '');
  image.buildExitCode = build.status;
  image.buildElapsedMs = Date.now() - buildStarted;
  if (build.status !== 0) throw new Error(`B41 image build failed (${build.status})`);
  operations.push('DOCKER_IMAGE_INSPECT');
  const inspected = JSON.parse(probe('docker', [...dockerBase, 'image', 'inspect', spec.imageBuild.tag], 'B41 image inspect'))[0];
  image = { ...image, id: inspected.Id, os: inspected.Os, architecture: inspected.Architecture, repoTags: inspected.RepoTags ?? [] };

  const successEnvironment = expectedB41Environment(spec, spec.successCanary.jobId);
  const successArgv = expectedB41Argv(spec, spec.successCanary.script);
  const successDockerArgs = dockerRunArgs({ name: experimentNames[0], imageId: image.id, inputRoot, outputRoot: successRoot, environment: successEnvironment, argv: successArgv });
  operations.push('DOCKER_RUN_SUCCESS');
  const successProcess = await runTimedContainer({ name: experimentNames[0], args: successDockerArgs, wallTimeMs: spec.successCanary.wallTimeMs, graceMs: spec.timeoutCanary.terminateGraceMs });
  await writeFile(resolve(successRoot, 'stdout.log'), successProcess.stdout);
  await writeFile(resolve(successRoot, 'stderr.log'), successProcess.stderr);
  let successReport = null;
  try { successReport = JSON.parse(await readFile(resolve(successRoot, 'runtime-report.json'), 'utf8')); } catch {}
  success = {
    imageId: image.id, platform: spec.runtime.containerPlatform, argv: successArgv, environment: successEnvironment,
    ...successProcess, report: successReport,
    artifacts: { png: await pngInfo(resolve(successRoot, 'canary.png')), blend: await fileInfo(resolve(successRoot, 'canary.blend')) },
    promotable: successProcess.exitCode === 0 && successProcess.timedOut !== true && successReport?.passed === true,
  };

  const timeoutEnvironment = expectedB41Environment(spec, spec.timeoutCanary.jobId);
  const timeoutArgv = expectedB41Argv(spec, spec.timeoutCanary.script);
  const timeoutDockerArgs = dockerRunArgs({ name: experimentNames[1], imageId: image.id, inputRoot, outputRoot: timeoutRoot, environment: timeoutEnvironment, argv: timeoutArgv });
  operations.push('DOCKER_RUN_TIMEOUT');
  const timeoutProcess = await runTimedContainer({ name: experimentNames[1], args: timeoutDockerArgs, wallTimeMs: spec.timeoutCanary.wallTimeMs, graceMs: spec.timeoutCanary.terminateGraceMs });
  await writeFile(resolve(timeoutRoot, 'stdout.log'), timeoutProcess.stdout);
  await writeFile(resolve(timeoutRoot, 'stderr.log'), timeoutProcess.stderr);
  timeout = {
    imageId: image.id, platform: spec.runtime.containerPlatform, argv: timeoutArgv, environment: timeoutEnvironment,
    ...timeoutProcess,
    readyObserved: (await fileInfo(resolve(timeoutRoot, 'timeout-ready.json'))).bytes > 0,
    sigtermObserved: (await fileInfo(resolve(timeoutRoot, 'sigterm-observed.json'))).bytes > 0,
    outcome: timeoutProcess.timeoutTriggered && timeoutProcess.forceKillSent ? spec.timeoutCanary.requiredOutcome : 'TIMEOUT_ENFORCEMENT_FAILED',
    promotable: false,
  };
} catch (error) {
  errors.push(error instanceof Error ? error.message : String(error));
} finally {
  await rm(temporaryRoot, { recursive: true, force: true });
  temporaryBuildRootRemoved = true;
}
operations.push('DOCKER_RUNNING_CONTAINER_CHECK');
const runningNames = probe('docker', [...dockerBase, 'ps', '--format', '{{.Names}}'], 'B41 post-run container check').split('\n').filter(Boolean);
const experimentContainersRunningAfter = runningNames.filter(name => experimentNames.includes(name)).length;
const evidence = {
  schemaVersion: binaryIdentityCorrectionMode ? 'bfs.linuxAmd64BlenderRuntimeEvidence.v0.5' : buildxCorrectionMode ? 'bfs.linuxAmd64BlenderRuntimeEvidence.v0.4' : toolingCorrectionMode ? 'bfs.linuxAmd64BlenderRuntimeEvidence.v0.3' : correctionMode ? 'bfs.linuxAmd64BlenderRuntimeEvidence.v0.2' : 'bfs.linuxAmd64BlenderRuntimeEvidence.v0.1',
  experimentId: binaryIdentityCorrectionMode ? 'B41-C4' : buildxCorrectionMode ? 'B41-C3' : toolingCorrectionMode ? 'B41-C2' : correctionMode ? 'B41-C1' : 'B41',
  status: 'REAL_LINUX_AMD64_BLENDER_RUNTIME_AND_TIMEOUT_CANARY',
  preregistration: { commit: preregistrationCommit, specSha256: preregistrationSpecSha256 },
  ...(correctionMode ? { architectureCorrection: {
    parentSpecSha256: correctionSpec.parent.specSha256,
    parentPreregistrationCommit: correctionSpec.parent.preregistrationCommit,
    parentToolFreezeCommit: correctionSpec.parent.toolFreezeCommit,
    rawDockerArchitecture, canonicalDockerArchitecture,
    changedImplementationExact: correctionSpec.changedImplementationExact,
  } } : {}),
  ...(toolingCorrectionMode ? { toolingCorrection: {
    c1SpecSha256: toolingCorrectionSpec.parent.c1SpecSha256,
    c1PreregistrationCommit: toolingCorrectionSpec.parent.c1PreregistrationCommit,
    c1ToolFreezeCommit: toolingCorrectionSpec.parent.c1ToolFreezeCommit,
    failedResultSha256: c1FailedResultSha256,
    failedAuditSha256: c1FailedAuditSha256,
    changedImplementationExact: structuredClone(toolingCorrectionSpec.changedImplementationExact),
  } } : {}),
  ...(buildxCorrectionMode ? { buildxCorrection: {
    c2SpecSha256: buildxCorrectionSpec.parent.c2SpecSha256,
    c2PreregistrationCommit: buildxCorrectionSpec.parent.c2PreregistrationCommit,
    c2ToolFreezeCommit: buildxCorrectionSpec.parent.c2ToolFreezeCommit,
    failedResultSha256: c2FailedResultSha256,
    failedAuditSha256: c2FailedAuditSha256,
    changedImplementationExact: buildxCorrectionSpec.changedImplementationExact,
  }, buildTransport } : {}),
  ...(binaryIdentityCorrectionMode ? { binaryIdentityCorrection: {
    parent: structuredClone(binaryIdentityCorrectionSpec.parent),
    derivation: structuredClone(binaryIdentityCorrectionSpec.derivation),
    platformIdentity: structuredClone(binaryIdentityCorrectionSpec.platformIdentity),
    changedImplementationExact: structuredClone(binaryIdentityCorrectionSpec.changedImplementationExact),
  } } : {}),
  ancestry, toolFreezeCommit,
  runtime: { nodeVersion: process.version, nodeBinary: process.execPath, nodeBinarySha256, dockerHost: spec.runtime.dockerHost, dockerServerVersion: dockerIdentity.Version, dockerServerArchitecture: canonicalDockerArchitecture },
  tools: {
    runner: { uri: 'scripts/run-b41-linux-amd64-blender-runtime-canary.mjs', sha256: await sha256File(runnerPath) },
    library: { uri: binaryIdentityCorrectionMode ? 'scripts/lib/b41-c4-platform-binary-identity-correction.mjs' : buildxCorrectionMode ? 'scripts/lib/b41-c3-guest-buildx-correction.mjs' : toolingCorrectionMode ? 'scripts/lib/b41-c2-build-receipt-tooling-correction.mjs' : correctionMode ? 'scripts/lib/b41-c1-docker-architecture-correction.mjs' : 'scripts/lib/b41-linux-amd64-blender-runtime-canary.mjs', sha256: await sha256File(libraryPath) },
    audit: { uri: binaryIdentityCorrectionMode ? 'scripts/audit-b41-c4-platform-binary-identity-correction.mjs' : buildxCorrectionMode ? 'scripts/audit-b41-c3-guest-buildx-correction.mjs' : toolingCorrectionMode ? 'scripts/audit-b41-c2-build-receipt-tooling-correction.mjs' : correctionMode ? 'scripts/audit-b41-c1-docker-architecture-correction.mjs' : 'scripts/audit-b41-linux-amd64-blender-runtime-canary.mjs', sha256: await sha256File(auditPath) },
    dockerfile: { uri: 'worker/b41/Dockerfile', sha256: await sha256File(dockerfilePath) },
    runtimeCanary: { uri: 'fixtures/b41/runtime-canary.py', sha256: await sha256File(runtimeCanaryPath) },
    timeoutCanary: { uri: 'fixtures/b41/timeout-canary.py', sha256: await sha256File(timeoutCanaryPath) },
  },
  diskAdmission, artifact, inputFixture: { ocioTreeManifestSha256 }, image,
  launchContract: structuredClone(spec.containerContract), runtimeOperationsExecuted: operations,
  success, timeout, cleanup: { experimentContainersRunningAfter, temporaryBuildRootRemoved }, errors,
};
evidence.evidenceHash = binaryIdentityCorrectionMode ? hashB41C4Evidence(evidence) : buildxCorrectionMode ? hashB41C3Evidence(evidence) : toolingCorrectionMode ? hashB41C2Evidence(evidence) : hashB41Evidence(evidence);
const analysis = binaryIdentityCorrectionMode
  ? analyzeB41C4Evidence(evidence, binaryIdentityCorrectionSpec, buildxCorrectionSpec, toolingCorrectionSpec, correctionSpec, spec)
  : buildxCorrectionMode
  ? analyzeB41C3Evidence(evidence, buildxCorrectionSpec, toolingCorrectionSpec, correctionSpec, spec)
  : toolingCorrectionMode ? analyzeB41C2Evidence(evidence, toolingCorrectionSpec, correctionSpec, spec)
  : correctionMode ? analyzeB41C1Evidence(evidence, correctionSpec, spec)
  : analyzeB41Evidence(evidence, spec);
const acceptedVerdict = binaryIdentityCorrectionMode ? binaryIdentityCorrectionSpec.acceptedVerdict : buildxCorrectionMode ? buildxCorrectionSpec.acceptedVerdict : toolingCorrectionMode ? toolingCorrectionSpec.acceptedVerdict : correctionMode ? correctionSpec.acceptedVerdict : spec.acceptedVerdict;
const correctionNonClaims = binaryIdentityCorrectionMode ? [...correctionSpec.nonClaims, ...toolingCorrectionSpec.nonClaims, ...buildxCorrectionSpec.nonClaims, ...binaryIdentityCorrectionSpec.nonClaims] : buildxCorrectionMode ? [...correctionSpec.nonClaims, ...toolingCorrectionSpec.nonClaims, ...buildxCorrectionSpec.nonClaims] : toolingCorrectionMode ? [...correctionSpec.nonClaims, ...toolingCorrectionSpec.nonClaims] : correctionMode ? correctionSpec.nonClaims : [];
const result = { ...evidence, analysis, verdict: analysis.passed ? acceptedVerdict : 'LINUX_AMD64_BLENDER_5_2_CANARY_FAILED', nonClaims: [...spec.nonClaims, ...correctionNonClaims] };
await writeFile(resolve(experimentRoot, 'results.json'), `${JSON.stringify(result, null, 2)}\n`);
process.stdout.write(`BFS_${binaryIdentityCorrectionMode ? 'B41_C4' : buildxCorrectionMode ? 'B41_C3' : toolingCorrectionMode ? 'B41_C2' : correctionMode ? 'B41_C1' : 'B41'}_RESULT verdict=${result.verdict} build=${image.buildExitCode} success=${success.exitCode ?? 'NA'} timeout=${timeout.outcome ?? 'NA'} failures=${analysis.failures.join(',') || 'none'}\n`);
if (!analysis.passed) process.exitCode = 1;
