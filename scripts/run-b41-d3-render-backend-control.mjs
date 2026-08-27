import { spawn, spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { chmod, cp, mkdir, mkdtemp, readFile, readdir, rm, stat, statfs, writeFile } from 'node:fs/promises';
import { join, relative, resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256File } from './lib/receipt-format.mjs';
import { readB41Spec } from './lib/b41-linux-amd64-blender-runtime-canary.mjs';
import { B41_D3_PREREG_COMMIT, B41_D3_SPEC_SHA256, analyzeB41D3Evidence, classifyB41D3, expectedB41D3Argv, expectedB41D3Environment, hashB41D3Evidence, readB41D3Spec } from './lib/b41-d3-render-backend-control.mjs';

const spec = await readB41D3Spec();
const baseSpec = await readB41Spec();
const outputRoot = resolve(repositoryRoot, 'experiments/linux-amd64-render-backend-control-v0-1');
const controlPath = resolve(repositoryRoot, 'fixtures/b41/render-backend-control.py');
const runnerPath = resolve(repositoryRoot, 'scripts/run-b41-d3-render-backend-control.mjs');
const libraryPath = resolve(repositoryRoot, 'scripts/lib/b41-d3-render-backend-control.mjs');
const auditPath = resolve(repositoryRoot, 'scripts/audit-b41-d3-render-backend-control.mjs');
const dockerBase = ['--host', baseSpec.runtime.dockerHost];
const names = spec.controls.map(control => `bfs-b41-d3-${control.id.toLowerCase().replaceAll('_', '-')}`);
const operations = [];
const errors = [];

function probe(executable, args, label, options = {}) {
  const result = spawnSync(executable, args, { cwd: repositoryRoot, encoding: 'utf8', maxBuffer: options.maxBuffer ?? 20 * 1024 * 1024, timeout: options.timeout ?? 120000 });
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
  files.sort((left, right) => Buffer.compare(Buffer.from(relative(root, left)), Buffer.from(relative(root, right))));
  const lines = [];
  for (const file of files) lines.push(`${await sha256File(file)}  ./${relative(root, file).replaceAll('\\', '/')}`);
  return createHash('sha256').update(`${lines.join('\n')}\n`).digest('hex');
}

async function fileInfo(path) {
  try { const info = await stat(path); return { bytes: info.size, sha256: await sha256File(path) }; }
  catch { return { bytes: 0, sha256: null }; }
}

async function pngInfo(path) {
  try { const bytes = await readFile(path); return { valid: bytes.length >= 24 && bytes.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10])) && bytes.subarray(12, 16).toString('ascii') === 'IHDR', dimensions: bytes.length >= 24 ? [bytes.readUInt32BE(16), bytes.readUInt32BE(20)] : null, bytes: bytes.length, sha256: createHash('sha256').update(bytes).digest('hex') }; }
  catch { return { valid: false, dimensions: null, bytes: 0, sha256: null }; }
}

async function readMilestones(path) {
  try { return (await readFile(path, 'utf8')).split(/\r?\n/).filter(Boolean).map(line => JSON.parse(line)); }
  catch { return []; }
}

function dockerRunArgs({ name, inputRoot, outputPath, environment, argv }) {
  const contract = baseSpec.containerContract;
  const args = [...dockerBase, 'run', '--rm', '--name', name, '--platform', baseSpec.runtime.containerPlatform, '--pull', 'never', '--read-only', '--network', 'none', '--user', contract.user, '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges:true', '--pids-limit', String(contract.pidsLimit), '--memory', String(contract.memoryBytes), '--cpus', String(contract.cpus), '--shm-size', String(contract.shmBytes), '--mount', `type=bind,src=${inputRoot},dst=/inputs,readonly`, '--mount', `type=bind,src=${outputPath},dst=/outputs`];
  for (const tmpfs of contract.tmpfs) args.push('--tmpfs', tmpfs);
  for (const [key, value] of Object.entries(environment).sort(([a], [b]) => a.localeCompare(b))) args.push('--env', `${key}=${value}`);
  return [...args, spec.image.id, ...argv];
}

async function runTimed(name, args, wallTimeMs) {
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
  const timer = setTimeout(() => {
    timeoutTriggered = true;
    termAtMs = Date.now() - started;
    operations.push(`DOCKER_KILL_TERM_${name}`);
    termSent = spawnSync('docker', [...dockerBase, 'kill', '--signal', 'TERM', name], { encoding: 'utf8' }).status === 0;
    forceTimer = setTimeout(() => {
      forceAtMs = Date.now() - started;
      operations.push(`DOCKER_KILL_KILL_${name}`);
      forceKillSent = spawnSync('docker', [...dockerBase, 'kill', '--signal', 'KILL', name], { encoding: 'utf8' }).status === 0;
    }, 5000);
  }, wallTimeMs);
  const close = await new Promise((resolveClose, reject) => { child.on('error', reject); child.on('close', (code, signal) => resolveClose({ code, signal })); });
  clearTimeout(timer);
  if (forceTimer) clearTimeout(forceTimer);
  return { exitCode: close.code, signal: close.signal, elapsedMs: Date.now() - started, stdout, stderr, timeoutTriggered, termSent, forceKillSent, termAtMs, forceAtMs };
}

if (spawnSync('git', ['merge-base', '--is-ancestor', B41_D3_PREREG_COMMIT, 'HEAD'], { cwd: repositoryRoot }).status !== 0) throw new Error('B41-D3 preregistration is not an ancestor');
const toolFreezeCommit = probe('git', ['rev-parse', 'HEAD'], 'tool freeze identity');
if (probe('git', ['status', '--porcelain', '--untracked-files=no'], 'tracked status') !== '') throw new Error('B41-D3 tracked worktree must be clean');
const parentResultSha256 = await sha256File(resolve(repositoryRoot, 'experiments/linux-amd64-eevee-headless-diagnostic-v0-1/results.json'));
const parentAuditSha256 = await sha256File(resolve(repositoryRoot, 'experiments/linux-amd64-eevee-headless-diagnostic-v0-1/audit.json'));
if (parentResultSha256 !== spec.parent.resultSha256 || parentAuditSha256 !== spec.parent.auditSha256) throw new Error('B41-D3 parent evidence differs');
for (const name of names) if (spawnSync('docker', [...dockerBase, 'container', 'inspect', name], { encoding: 'utf8' }).status === 0) throw new Error(`B41-D3 container already exists: ${name}`);
operations.push('DOCKER_IMAGE_INSPECT');
const image = JSON.parse(probe('docker', [...dockerBase, 'image', 'inspect', spec.image.id], 'B41-D3 image inspect'))[0];
if (image.Id !== spec.image.id || image.Os !== spec.image.os || image.Architecture !== spec.image.architecture || image.Size !== spec.image.dockerReportedSizeBytes) throw new Error('B41-D3 image identity differs');
const filesystem = await statfs(repositoryRoot, { bigint: true });
const availableBytes = filesystem.bavail * filesystem.bsize;
const freeAfterProjectedBytes = availableBytes - BigInt(spec.diskAdmission.projectedWriteBytes);
const diskAdmission = { availableBytes: String(availableBytes), projectedWriteBytes: String(spec.diskAdmission.projectedWriteBytes), minimumReserveBytes: String(spec.diskAdmission.minimumReserveBytes), freeAfterProjectedBytes: String(freeAfterProjectedBytes), status: freeAfterProjectedBytes >= BigInt(spec.diskAdmission.minimumReserveBytes) ? 'ACCEPTED' : 'BLOCKED' };
if (diskAdmission.status !== 'ACCEPTED') throw new Error('B41-D3 disk admission blocked');

await mkdir(outputRoot, { recursive: false });
const temporaryRoot = await mkdtemp(resolve(repositoryRoot, '.bfs-b41-d3-'));
const inputRoot = resolve(temporaryRoot, 'inputs');
await mkdir(inputRoot);
await cp(controlPath, resolve(inputRoot, 'render-backend-control.py'));
await cp(baseSpec.inputFixture.ocioSource, resolve(inputRoot, 'ocio'), { recursive: true });
const ocioTreeManifestSha256 = await treeManifestSha256(resolve(inputRoot, 'ocio'));
if (ocioTreeManifestSha256 !== baseSpec.inputFixture.ocioTreeManifestSha256) throw new Error('B41-D3 OCIO identity differs');
const controls = [];
let temporaryInputRootRemoved = false;
try {
  for (let index = 0; index < spec.controls.length; index += 1) {
    const expected = spec.controls[index];
    const name = names[index];
    const outputPath = resolve(outputRoot, expected.id);
    await mkdir(outputPath);
    await chmod(outputPath, 0o777);
    const environment = expectedB41D3Environment(baseSpec, expected);
    const argv = expectedB41D3Argv(expected);
    operations.push(`DOCKER_RUN_${expected.id}`);
    const processResult = await runTimed(name, dockerRunArgs({ name, inputRoot, outputPath, environment, argv }), expected.wallTimeMs);
    await writeFile(resolve(outputPath, 'stdout.log'), processResult.stdout);
    await writeFile(resolve(outputPath, 'stderr.log'), processResult.stderr);
    let report = null;
    try { report = JSON.parse(await readFile(resolve(outputPath, 'report.json'), 'utf8')); } catch {}
    const artifacts = { blend: await fileInfo(resolve(outputPath, 'canary.blend')), png: await pngInfo(resolve(outputPath, 'canary.png')) };
    const milestones = await readMilestones(resolve(outputPath, 'milestones.jsonl'));
    const completed = processResult.exitCode === 0 && report?.passed === true && artifacts.png.valid === true;
    controls.push({ id: expected.id, engine: expected.engine, device: expected.device, gpuBackendArgv: expected.gpuBackendArgv, attempted: true, imageId: spec.image.id, argv, environment, ...processResult, milestones, report, artifacts, completed, promotable: false });
    process.stdout.write(`BFS_B41_D3_CONTROL ${expected.id} completed=${completed} exit=${processResult.exitCode} timeout=${processResult.timeoutTriggered} milestone=${milestones.at(-1)?.name ?? 'NONE'}\n`);
  }
} catch (error) {
  errors.push(error instanceof Error ? error.message : String(error));
} finally {
  await rm(temporaryRoot, { recursive: true, force: true });
  temporaryInputRootRemoved = true;
}
operations.push('DOCKER_RUNNING_CONTAINER_CHECK');
const running = probe('docker', [...dockerBase, 'ps', '--format', '{{.Names}}'], 'B41-D3 running container check').split('\n').filter(Boolean);
const evidence = { schemaVersion: 'bfs.linuxAmd64RenderBackendControlEvidence.v0.1', experimentId: 'B41-D3', status: 'NON_PROMOTABLE_RENDER_BACKEND_CONTROL', preregistration: { commit: B41_D3_PREREG_COMMIT, specSha256: B41_D3_SPEC_SHA256 }, parent: spec.parent, toolFreezeCommit, tools: { runner: { uri: 'scripts/run-b41-d3-render-backend-control.mjs', sha256: await sha256File(runnerPath) }, library: { uri: 'scripts/lib/b41-d3-render-backend-control.mjs', sha256: await sha256File(libraryPath) }, audit: { uri: 'scripts/audit-b41-d3-render-backend-control.mjs', sha256: await sha256File(auditPath) }, control: { uri: 'fixtures/b41/render-backend-control.py', sha256: await sha256File(controlPath) } }, runtime: { nodeVersion: process.version, nodeBinary: process.execPath, dockerHost: baseSpec.runtime.dockerHost, containerPlatform: baseSpec.runtime.containerPlatform }, diskAdmission, image: { id: image.Id, os: image.Os, architecture: image.Architecture, sizeBytes: image.Size }, inputFixture: { ocioTreeManifestSha256 }, securityBoundary: spec.securityBoundary, controls, classification: classifyB41D3(controls), runtimeOperationsExecuted: operations, cleanup: { experimentContainersRunningAfter: running.filter(name => names.includes(name)).length, temporaryInputRootRemoved }, promotable: false, errors };
evidence.evidenceHash = hashB41D3Evidence(evidence);
evidence.analysis = analyzeB41D3Evidence(evidence, spec, baseSpec);
evidence.verdict = evidence.analysis.passed ? spec.acceptedVerdict : 'RENDER_BACKEND_CONTROL_INVALID';
evidence.nonClaims = spec.nonClaims;
await writeFile(resolve(outputRoot, 'results.json'), `${JSON.stringify(evidence, null, 2)}\n`);
process.stdout.write(`BFS_B41_D3_RESULT verdict=${evidence.verdict} classification=${evidence.classification} failures=${evidence.analysis.failures.join(',') || 'none'}\n`);
if (!evidence.analysis.passed) process.exitCode = 1;
