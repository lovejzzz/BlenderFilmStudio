import { spawn, spawnSync } from 'node:child_process';
import { chmod, mkdir, readFile, readdir, statfs, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { compileBuildPlan } from './compile-build-plan.mjs';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256File } from './lib/receipt-format.mjs';
import { readB41Spec } from './lib/b41-linux-amd64-blender-runtime-canary.mjs';
import { B42_C1_PREREG_COMMIT, B42_C1_SPEC_SHA256, B42_PREREG_COMMIT, B42_SPEC_SHA256, analyzeB42C1Evidence, analyzeB42Evidence, hashB42Evidence, observeSuccessfulRun, readB42C1Spec, readB42Spec } from './lib/b42-linux-amd64-compiler-repro.mjs';

const c1Mode = process.argv.includes('--c1');
const [spec, baseSpec, correctionSpec] = await Promise.all([readB42Spec(), readB41Spec(), c1Mode ? readB42C1Spec() : null]);
const experimentRoot = resolve(repositoryRoot, c1Mode ? 'experiments/linux-amd64-compiler-repro-c1-v0-1' : 'experiments/linux-amd64-compiler-repro-v0-1');
const plansRoot = resolve(experimentRoot, 'plans');
const runsRoot = resolve(experimentRoot, 'runs');
const dockerBase = ['--host', baseSpec.runtime.dockerHost];
const runnerPath = resolve(repositoryRoot, 'scripts/run-b42-linux-amd64-compiler-repro.mjs');
const libraryPath = resolve(repositoryRoot, 'scripts/lib/b42-linux-amd64-compiler-repro.mjs');
const auditPath = resolve(repositoryRoot, 'scripts/audit-b42-linux-amd64-compiler-repro.mjs');
const names = [...spec.runs.map(id => `bfs-b42-${id.toLowerCase()}`), 'bfs-b42-b01-tampered'];
const operations = [];
const errors = [];

function probe(executable, args, label) {
  const result = spawnSync(executable, args, { cwd: repositoryRoot, encoding: 'utf8', maxBuffer: 20 * 1024 * 1024, timeout: 120000 });
  if (result.status !== 0) throw new Error(`${label} failed (${result.status}): ${(result.stderr || result.stdout || '').trim().slice(-4000)}`);
  return result.stdout.trim();
}

async function runTimed(name, args) {
  const started = Date.now();
  let stdout = '', stderr = '', timeoutTriggered = false, termSent = false, killSent = false;
  const child = spawn('docker', args, { cwd: repositoryRoot });
  child.stdout.on('data', chunk => { stdout += chunk.toString(); });
  child.stderr.on('data', chunk => { stderr += chunk.toString(); });
  let killTimer;
  const timer = setTimeout(() => {
    timeoutTriggered = true;
    termSent = spawnSync('docker', [...dockerBase, 'kill', '--signal', 'TERM', name], { encoding: 'utf8' }).status === 0;
    killTimer = setTimeout(() => { killSent = spawnSync('docker', [...dockerBase, 'kill', '--signal', 'KILL', name], { encoding: 'utf8' }).status === 0; }, spec.containerContract.killGraceMs);
  }, spec.containerContract.wallTimeMs);
  const closed = await new Promise((accept, reject) => { child.once('error', reject); child.once('close', (exitCode, signal) => accept({ exitCode, signal })); });
  clearTimeout(timer); if (killTimer) clearTimeout(killTimer);
  return { ...closed, elapsedMs: Date.now() - started, stdout, stderr, timeoutTriggered, termSent, killSent };
}

function dockerArgs(name, planRel, outputRoot) {
  const c = spec.containerContract;
  const env = {
    HOME: '/work/home', TMPDIR: '/work/tmp', LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8',
    BLENDER_USER_CONFIG: '/work/blender-config', BLENDER_USER_SCRIPTS: '/work/blender-scripts',
    OCIO: `/repo/${spec.inputs.ocio.uri}`,
  };
  const args = [...dockerBase, 'run', '--rm', '--name', name, '--platform', c.platform, '--pull', 'never', '--read-only', '--network', c.network, '--user', c.user, '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges:true', '--pids-limit', String(c.pidsLimit), '--memory', String(c.memoryBytes), '--cpus', String(c.cpus), '--shm-size', String(c.shmBytes), '--mount', `type=bind,src=${repositoryRoot},dst=/repo,readonly`, '--mount', `type=bind,src=${outputRoot},dst=/repo/worker-output`, '--tmpfs', '/tmp:rw,noexec,nosuid,nodev,size=536870912,uid=65532,gid=65532', '--tmpfs', '/work:rw,noexec,nosuid,nodev,size=1073741824,uid=65532,gid=65532'];
  for (const [key, value] of Object.entries(env).sort(([a], [b]) => a.localeCompare(b))) args.push('--env', `${key}=${value}`);
  return [...args, spec.image.id, '--background', '--factory-startup', '--disable-autoexec', '--offline-mode', '--python-exit-code', '1', '--python', '/repo/blender/compile_scene.py', '--', '--plan', `/repo/${planRel}`, '--repository-root', '/repo', '--output-dir', '/repo/worker-output'];
}

const preregistrationCommit = c1Mode ? B42_C1_PREREG_COMMIT : B42_PREREG_COMMIT;
const preregistrationSpecSha256 = c1Mode ? B42_C1_SPEC_SHA256 : B42_SPEC_SHA256;
if (spawnSync('git', ['merge-base', '--is-ancestor', preregistrationCommit, 'HEAD'], { cwd: repositoryRoot }).status !== 0) throw new Error('B42 preregistration is not an ancestor');
const toolFreezeCommit = probe('git', ['rev-parse', 'HEAD'], 'tool freeze identity');
if (probe('git', ['status', '--porcelain', '--untracked-files=no'], 'tracked status') !== '') throw new Error('B42 tracked worktree must be clean');
for (const item of Object.values(spec.inputs)) if (await sha256File(resolve(repositoryRoot, item.uri)) !== item.sha256) throw new Error(`B42 input differs: ${item.uri}`);
if (c1Mode && await sha256File(resolve(repositoryRoot, correctionSpec.mountpointFixture.uri)) !== correctionSpec.mountpointFixture.sha256) throw new Error('B42-C1 mountpoint fixture differs');
for (const benchmark of spec.benchmarks) {
  if (await sha256File(resolve(repositoryRoot, benchmark.sceneSpec.uri)) !== benchmark.sceneSpec.sha256) throw new Error(`B42 SceneSpec differs: ${benchmark.id}`);
  for (const asset of benchmark.assets) if (await sha256File(resolve(repositoryRoot, asset.uri)) !== asset.sha256) throw new Error(`B42 asset differs: ${asset.uri}`);
}
if (await sha256File(resolve(repositoryRoot, 'experiments/linux-amd64-render-backend-control-v0-1/results.json')) !== spec.parent.resultSha256 || await sha256File(resolve(repositoryRoot, 'experiments/linux-amd64-render-backend-control-v0-1/audit.json')) !== spec.parent.auditSha256) throw new Error('B42 parent evidence differs');
if (c1Mode && await sha256File(resolve(repositoryRoot, 'experiments/linux-amd64-compiler-repro-v0-1/failure.json')) !== correctionSpec.parent.failureSha256) throw new Error('B42-C1 failure evidence differs');
for (const name of names) if (spawnSync('docker', [...dockerBase, 'container', 'inspect', name], { encoding: 'utf8' }).status === 0) throw new Error(`B42 container already exists: ${name}`);
operations.push('DOCKER_IMAGE_INSPECT');
const image = JSON.parse(probe('docker', [...dockerBase, 'image', 'inspect', spec.image.id], 'image inspect'))[0];
if (image.Id !== spec.image.id || image.Os !== spec.image.os || image.Architecture !== spec.image.architecture || image.Size !== spec.image.dockerReportedSizeBytes) throw new Error('B42 image identity differs');
const fs = await statfs(repositoryRoot, { bigint: true });
const availableBytes = fs.bavail * fs.bsize;
const freeAfterProjectedBytes = availableBytes - BigInt(spec.diskAdmission.projectedWriteBytes);
const diskAdmission = { availableBytes: String(availableBytes), projectedWriteBytes: spec.diskAdmission.projectedWriteBytes, minimumReserveBytes: spec.diskAdmission.minimumReserveBytes, freeAfterProjectedBytes: String(freeAfterProjectedBytes), status: freeAfterProjectedBytes >= BigInt(spec.diskAdmission.minimumReserveBytes) ? 'ACCEPTED' : 'BLOCKED' };
if (diskAdmission.status !== 'ACCEPTED') throw new Error('B42 disk admission blocked');

await mkdir(plansRoot, { recursive: true });
await mkdir(runsRoot, { recursive: true });
const benchmarks = [];
try {
  for (const expected of spec.benchmarks) {
    const plans = [];
    for (const suffix of ['A', 'B']) {
      const plan = await compileBuildPlan(resolve(repositoryRoot, expected.sceneSpec.uri));
      const path = resolve(plansRoot, `${expected.id}-${suffix}.build-plan.json`);
      await writeFile(path, `${JSON.stringify(plan, null, 2)}\n`);
      plans.push({ suffix, uri: path.slice(repositoryRoot.length + 1), fileSha256: await sha256File(path), planHash: plan.planHash });
    }
    const runs = [];
    for (const plan of plans) {
      const runId = `${expected.id}-${plan.suffix}`;
      const outputRoot = resolve(runsRoot, runId);
      await mkdir(outputRoot); await chmod(outputRoot, 0o777);
      const name = `bfs-b42-${runId.toLowerCase()}`;
      const argv = dockerArgs(name, plan.uri, outputRoot);
      operations.push(`DOCKER_RUN_${runId}`);
      const processResult = await runTimed(name, argv);
      await Promise.all([writeFile(resolve(outputRoot, 'stdout.log'), processResult.stdout), writeFile(resolve(outputRoot, 'stderr.log'), processResult.stderr)]);
      let observed = null;
      if (processResult.exitCode === 0 && !processResult.timeoutTriggered) observed = await observeSuccessfulRun(outputRoot);
      const completed = observed !== null;
      runs.push({ id: runId, containerName: name, imageId: spec.image.id, argv, ...processResult, observed, completed });
      process.stdout.write(`BFS_B42_RUN ${runId} completed=${completed} exit=${processResult.exitCode} elapsedMs=${processResult.elapsedMs}\n`);
    }
    benchmarks.push({ id: expected.id, plans, planFilesByteEqual: plans[0].fileSha256 === plans[1].fileSha256, runs, structureFilesByteEqual: runs[0].observed?.structure.sha256 === runs[1].observed?.structure.sha256, structureHash: runs[0].observed?.structure.sha256 ?? null, blendByteIdentical: runs[0].observed?.blend.sha256 === runs[1].observed?.blend.sha256 });
  }
} catch (error) { errors.push(error instanceof Error ? error.message : String(error)); }

let negativeControl = null;
try {
  const source = JSON.parse(await readFile(resolve(plansRoot, 'B01-A.build-plan.json'), 'utf8'));
  source.planHash = '0'.repeat(64);
  const tamperedPath = resolve(plansRoot, 'B01-TAMPERED.build-plan.json');
  await writeFile(tamperedPath, `${JSON.stringify(source, null, 2)}\n`);
  const outputRoot = resolve(runsRoot, 'B01-TAMPERED');
  await mkdir(outputRoot); await chmod(outputRoot, 0o777);
  const name = 'bfs-b42-b01-tampered';
  const argv = dockerArgs(name, tamperedPath.slice(repositoryRoot.length + 1), outputRoot);
  operations.push('DOCKER_RUN_B01_TAMPERED');
  const result = await runTimed(name, argv);
  await Promise.all([writeFile(resolve(outputRoot, 'stdout.log'), result.stdout), writeFile(resolve(outputRoot, 'stderr.log'), result.stderr)]);
  const outputFiles = (await readdir(outputRoot)).filter(file => !['stdout.log', 'stderr.log'].includes(file)).length;
  negativeControl = { id: spec.negativeControl.id, containerName: name, imageId: spec.image.id, argv, ...result, diagnosticMatched: `${result.stdout}\n${result.stderr}`.includes(spec.negativeControl.expectedDiagnosticSubstring), outputFiles };
  process.stdout.write(`BFS_B42_NEGATIVE rejected=${result.exitCode !== 0} diagnostic=${negativeControl.diagnosticMatched}\n`);
} catch (error) { errors.push(error instanceof Error ? error.message : String(error)); }

operations.push('DOCKER_RUNNING_CONTAINER_CHECK');
const running = probe('docker', [...dockerBase, 'ps', '--format', '{{.Names}}'], 'running container check').split('\n').filter(Boolean);
const evidence = {
  schemaVersion: c1Mode ? 'bfs.linuxAmd64CompilerReproEvidence.v0.2' : 'bfs.linuxAmd64CompilerReproEvidence.v0.1', experimentId: c1Mode ? 'B42-C1' : 'B42', preregistration: { commit: preregistrationCommit, specSha256: preregistrationSpecSha256 }, parent: spec.parent,
  ...(c1Mode ? { correctionParent: correctionSpec.parent } : {}),
  toolFreezeCommit, tools: { runner: { uri: 'scripts/run-b42-linux-amd64-compiler-repro.mjs', sha256: await sha256File(runnerPath) }, library: { uri: 'scripts/lib/b42-linux-amd64-compiler-repro.mjs', sha256: await sha256File(libraryPath) }, audit: { uri: 'scripts/audit-b42-linux-amd64-compiler-repro.mjs', sha256: await sha256File(auditPath) }, planCompiler: spec.inputs.planCompiler, sceneCompiler: spec.inputs.sceneCompiler },
  image: { id: image.Id, os: image.Os, architecture: image.Architecture, sizeBytes: image.Size }, diskAdmission, securityBoundary: spec.containerContract, benchmarks, negativeControl, runtimeOperationsExecuted: operations, cleanup: { experimentContainersRunningAfter: running.filter(name => names.includes(name)).length }, errors,
};
evidence.evidenceHash = hashB42Evidence(evidence);
evidence.analysis = c1Mode ? analyzeB42C1Evidence(evidence, spec, correctionSpec) : analyzeB42Evidence(evidence, spec);
evidence.verdict = evidence.analysis.passed ? (c1Mode ? correctionSpec.acceptedVerdict : spec.acceptedVerdict) : (c1Mode ? correctionSpec.rejectedVerdict : 'LINUX_AMD64_COMPILER_REPRO_REJECTED');
evidence.nonClaims = spec.nonClaims;
await writeFile(resolve(experimentRoot, 'results.json'), `${JSON.stringify(evidence, null, 2)}\n`);
process.stdout.write(`BFS_${c1Mode ? 'B42_C1' : 'B42'}_RESULT verdict=${evidence.verdict} failures=${evidence.analysis.failures.join(',') || 'none'}\n`);
if (!evidence.analysis.passed) process.exitCode = 1;
