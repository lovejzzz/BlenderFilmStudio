import { spawn, spawnSync } from 'node:child_process';
import { chmod, mkdir, readFile, readdir, stat, statfs, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { readB41Spec } from './lib/b41-linux-amd64-blender-runtime-canary.mjs';
import { B45_PREREG_COMMIT, B45_SPEC_SHA256, analyzeB45Evidence, hashB45Evidence, readB45Spec, runB45Attacks } from './lib/b45-worker-pixel-promotion.mjs';
import { sha256File } from './lib/receipt-format.mjs';

const spec = await readB45Spec();
const workerSpec = await readB41Spec();
const experimentRoot = resolve(repositoryRoot, 'experiments/codex-worker-pixel-promotion-v0-1');
const runsRoot = resolve(experimentRoot, 'runs');
const dockerBase = ['--host', workerSpec.runtime.dockerHost];
const names = spec.shots.flatMap(shot => shot.inputs.map(input => `bfs-b45-${input.id.toLowerCase()}`));
const python = spec.hostPixelDecoder.pythonExecutable;
const analyzerUri = 'scripts/analyze-b45-worker-pixels.py';
const analyzerPath = resolve(repositoryRoot, analyzerUri);
const operations = [];
const errors = [];

function probe(executable, args, label, options = {}) {
  const result = spawnSync(executable, args, { cwd: repositoryRoot, encoding: 'utf8', maxBuffer: 30 * 1024 * 1024, timeout: 120000, ...options });
  if (result.status !== 0) throw new Error(`${label} failed (${result.status}): ${(result.stderr || result.stdout || '').trim().slice(-5000)}`);
  return result.stdout.trim();
}

async function observeFile(uri, expectedSha256) {
  const path = resolve(repositoryRoot, uri);
  const observedSha256 = await sha256File(path).catch(() => null);
  return { uri, expectedSha256, observedSha256, match: observedSha256 === expectedSha256 };
}

async function fileInfo(path) {
  try { return { uri: path.slice(repositoryRoot.length + 1), bytes: (await stat(path)).size, sha256: await sha256File(path) }; }
  catch { return { uri: path.slice(repositoryRoot.length + 1), bytes: 0, sha256: null }; }
}

async function pngInfo(path) {
  const info = await fileInfo(path);
  if (!info.sha256) return { ...info, valid: false, dimensions: null };
  const bytes = await readFile(path);
  const valid = bytes.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10])) && bytes.subarray(12, 16).toString('ascii') === 'IHDR';
  return { ...info, valid, dimensions: valid ? [bytes.readUInt32BE(16), bytes.readUInt32BE(20)] : null };
}

async function readMilestones(path) {
  const text = await readFile(path, 'utf8').catch(() => '');
  return text.split('\n').filter(Boolean).map(line => JSON.parse(line));
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
  clearTimeout(timer);
  if (killTimer) clearTimeout(killTimer);
  return { ...closed, elapsedMs: Date.now() - started, stdout, stderr, timeoutTriggered, termSent, killSent };
}

function dockerArgs(name, shot, input, outputRoot) {
  const c = spec.containerContract;
  const environment = {
    HOME: '/work/home', TMPDIR: '/work/tmp', LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8',
    BLENDER_USER_CONFIG: '/work/blender-config', BLENDER_USER_SCRIPTS: '/work/blender-scripts',
    OCIO: `/repo/${spec.frozenInputs.ocio.uri}`,
  };
  const args = [...dockerBase, 'run', '--rm', '--name', name, '--platform', c.platform, '--pull', 'never', '--read-only', '--network', c.network, '--user', c.user, '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges:true', '--pids-limit', String(c.pidsLimit), '--memory', String(c.memoryBytes), '--cpus', String(c.cpus), '--shm-size', String(c.shmBytes), '--mount', `type=bind,src=${repositoryRoot},dst=/repo,readonly`, '--mount', `type=bind,src=${outputRoot},dst=/repo/worker-output`, '--tmpfs', '/tmp:rw,noexec,nosuid,nodev,size=536870912,uid=65532,gid=65532', '--tmpfs', '/work:rw,noexec,nosuid,nodev,size=1073741824,uid=65532,gid=65532'];
  for (const [key, value] of Object.entries(environment).sort(([a], [b]) => a.localeCompare(b))) args.push('--env', `${key}=${value}`);
  return [...args, spec.image.id, '--background', '--disable-autoexec', '--offline-mode', `/repo/${input.blendUri}`, '--python-exit-code', '1', '--python', '/repo/blender/render_b45_worker_pixel_canary.py', '--', '--source-sha256', input.blendSha256, '--shot-id', shot.shotId, '--frame', String(shot.frame), '--plan-hash', shot.planHash, '--scene-hash', shot.sourceSceneCanonicalSha256, '--structure-hash', shot.structureHash, '--ocio-sha256', spec.frozenInputs.ocio.sha256, '--output-dir', '/repo/worker-output'];
}

function analyzeExr(input, output) {
  const stdout = probe(python, [analyzerPath, '--input', input, '--expected-width', String(spec.renderControl.width), '--expected-height', String(spec.renderControl.height), '--output', output], 'B45 EXR analysis', { env: { ...process.env, OPENCV_IO_ENABLE_OPENEXR: '1' } });
  return stdout;
}

if (spawnSync('git', ['merge-base', '--is-ancestor', B45_PREREG_COMMIT, 'HEAD'], { cwd: repositoryRoot }).status !== 0) throw new Error('B45 preregistration is not an ancestor');
const toolFreezeCommit = probe('git', ['rev-parse', 'HEAD'], 'tool freeze identity');
const existing = await readdir(experimentRoot).catch(error => error.code === 'ENOENT' ? [] : Promise.reject(error));
if (existing.length > 0) throw new Error(`B45 output root is not empty: ${existing.join(', ')}`);
for (const name of names) if (spawnSync('docker', [...dockerBase, 'container', 'inspect', name], { encoding: 'utf8' }).status === 0) throw new Error(`B45 container already exists: ${name}`);

const parentObservations = [];
for (const parent of Object.values(spec.parents)) {
  parentObservations.push(await observeFile(parent.resultUri, parent.resultSha256), await observeFile(parent.auditUri, parent.auditSha256));
  const result = JSON.parse(await readFile(resolve(repositoryRoot, parent.resultUri), 'utf8'));
  if (parent.verdict && result.verdict !== parent.verdict) throw new Error(`B45 parent verdict differs: ${parent.resultUri}`);
  if (parent.classification && result.classification !== parent.classification) throw new Error(`B45 parent classification differs: ${parent.resultUri}`);
}
if (parentObservations.some(item => !item.match)) throw new Error('B45 parent evidence differs');

const inputMap = new Map(Object.values(spec.frozenInputs).map(item => [item.uri, item.sha256]));
for (const shot of spec.shots) for (const input of shot.inputs) {
  inputMap.set(input.blendUri, input.blendSha256);
  inputMap.set(input.blendUri.replace(/scene\.blend$/, 'scene.manifest.json'), input.compileManifestSha256);
}
const inputObservations = await Promise.all([...inputMap].map(([uri, digest]) => observeFile(uri, digest)));
if (inputObservations.some(item => !item.match)) throw new Error('B45 frozen input differs');
for (const shot of spec.shots) for (const input of shot.inputs) if ((await stat(resolve(repositoryRoot, input.blendUri))).size !== input.blendBytes) throw new Error(`B45 source size differs: ${input.id}`);

const pythonVersion = probe(python, ['-c', 'import platform; print(platform.python_version())'], 'Python version');
const decoderVersions = JSON.parse(probe(python, ['-c', 'import json,cv2,numpy; print(json.dumps({"opencv":cv2.__version__,"numpy":numpy.__version__}))'], 'decoder versions'));
const pythonSha256 = await sha256File(python);
const hostPixelDecoder = { ...spec.hostPixelDecoder };
if (pythonVersion !== hostPixelDecoder.pythonVersion || pythonSha256 !== hostPixelDecoder.pythonExecutableSha256 || decoderVersions.opencv !== hostPixelDecoder.opencvVersion || decoderVersions.numpy !== hostPixelDecoder.numpyVersion) throw new Error('B45 host pixel decoder identity differs');

const negativeObservedSha256 = await sha256File(resolve(repositoryRoot, spec.negativeControl.sourceUri));
const negativeControl = {
  id: spec.negativeControl.id, sourceUri: spec.negativeControl.sourceUri, declaredSha256: spec.negativeControl.declaredSha256,
  observedSha256: negativeObservedSha256, reason: negativeObservedSha256 === spec.negativeControl.declaredSha256 ? 'NO_REJECTION' : 'SOURCE_BLEND_HASH_MISMATCH', containerLaunchCount: 0,
};

operations.push('DOCKER_IMAGE_INSPECT');
const image = JSON.parse(probe('docker', [...dockerBase, 'image', 'inspect', spec.image.id], 'image inspect'))[0];
if (image.Id !== spec.image.id || image.Os !== spec.image.os || image.Architecture !== spec.image.architecture || image.Size !== spec.image.dockerReportedSizeBytes) throw new Error('B45 image identity differs');
const fs = await statfs(repositoryRoot, { bigint: true });
const availableBytes = fs.bavail * fs.bsize;
const freeAfterProjectedBytes = availableBytes - BigInt(spec.diskAdmission.projectedWriteBytes);
const diskAdmission = { availableBytes: String(availableBytes), projectedWriteBytes: spec.diskAdmission.projectedWriteBytes, minimumReserveBytes: spec.diskAdmission.minimumReserveBytes, freeAfterProjectedBytes: String(freeAfterProjectedBytes), status: freeAfterProjectedBytes >= BigInt(spec.diskAdmission.minimumReserveBytes) ? 'ACCEPTED' : 'BLOCKED' };
if (diskAdmission.status !== 'ACCEPTED') throw new Error('B45 disk admission blocked');

await mkdir(runsRoot, { recursive: true });
const shots = [];
try {
  for (const expectedShot of spec.shots) {
    const shot = { id: expectedShot.id, shotId: expectedShot.shotId, frame: expectedShot.frame, planHash: expectedShot.planHash, structureHash: expectedShot.structureHash, sourceBlendHashesDifferent: expectedShot.inputs[0].blendSha256 !== expectedShot.inputs[1].blendSha256, runs: [] };
    for (const input of expectedShot.inputs) {
      const outputRoot = resolve(runsRoot, input.id);
      await mkdir(outputRoot);
      await chmod(outputRoot, 0o777);
      const name = `bfs-b45-${input.id.toLowerCase()}`;
      const argv = dockerArgs(name, expectedShot, input, outputRoot);
      operations.push(`DOCKER_RUN_${input.id}`);
      const processResult = await runTimed(name, argv);
      await Promise.all([writeFile(resolve(outputRoot, 'stdout.log'), processResult.stdout), writeFile(resolve(outputRoot, 'stderr.log'), processResult.stderr)]);
      let report = null, decoded = null;
      const reportPath = resolve(outputRoot, 'render.report.json');
      const exrPath = resolve(outputRoot, 'frame.exr');
      const pngPath = resolve(outputRoot, 'frame.png');
      const analysisPath = resolve(outputRoot, 'pixel-analysis.json');
      if (processResult.exitCode === 0 && !processResult.timeoutTriggered) {
        report = JSON.parse(await readFile(reportPath, 'utf8'));
        operations.push(`HOST_EXR_ANALYSIS_${input.id}`);
        analyzeExr(exrPath, analysisPath);
        decoded = JSON.parse(await readFile(analysisPath, 'utf8'));
      }
      const artifacts = { exr: await fileInfo(exrPath), png: await pngInfo(pngPath), report: await fileInfo(reportPath), pixelAnalysis: await fileInfo(analysisPath) };
      const milestones = await readMilestones(resolve(outputRoot, 'milestones.jsonl'));
      const source = { uri: input.blendUri, sha256: await sha256File(resolve(repositoryRoot, input.blendUri)), bytes: (await stat(resolve(repositoryRoot, input.blendUri))).size };
      const completed = processResult.exitCode === 0 && !processResult.timeoutTriggered && report?.passed === true && decoded?.finite === true && artifacts.png.valid === true;
      shot.runs.push({ id: input.id, source, compileManifestSha256: input.compileManifestSha256, containerName: name, imageId: spec.image.id, argv, ...processResult, milestones, report, decoded, artifacts, completed });
      process.stdout.write(`BFS_B45_RUN ${input.id} completed=${completed} exit=${processResult.exitCode} elapsedMs=${processResult.elapsedMs} pixel=${decoded?.canonicalPixelSha256 ?? 'none'}\n`);
    }
    shot.pairComparison = {
      canonicalPixelSha256A: shot.runs[0].decoded?.canonicalPixelSha256 ?? null,
      canonicalPixelSha256B: shot.runs[1].decoded?.canonicalPixelSha256 ?? null,
      pixelExact: shot.runs[0].decoded?.canonicalPixelSha256 === shot.runs[1].decoded?.canonicalPixelSha256,
      exrContainerByteExact: shot.runs[0].artifacts.exr.sha256 === shot.runs[1].artifacts.exr.sha256,
      pngContainerByteExact: shot.runs[0].artifacts.png.sha256 === shot.runs[1].artifacts.png.sha256,
    };
    shots.push(shot);
  }
} catch (error) {
  errors.push(error instanceof Error ? error.message : String(error));
}

operations.push('DOCKER_RUNNING_CONTAINER_CHECK');
const running = probe('docker', [...dockerBase, 'ps', '--format', '{{.Names}}'], 'running container check').split('\n').filter(Boolean);
const evidence = {
  schemaVersion: 'bfs.codexWorkerPixelPromotionEvidence.v0.1', experimentId: 'B45',
  preregistration: { commit: B45_PREREG_COMMIT, specSha256: B45_SPEC_SHA256 }, parents: spec.parents, parentObservations,
  toolFreezeCommit,
  tools: {
    runner: { uri: 'scripts/run-b45-worker-pixel-promotion.mjs', sha256: await sha256File(resolve(repositoryRoot, 'scripts/run-b45-worker-pixel-promotion.mjs')) },
    library: { uri: 'scripts/lib/b45-worker-pixel-promotion.mjs', sha256: await sha256File(resolve(repositoryRoot, 'scripts/lib/b45-worker-pixel-promotion.mjs')) },
    audit: { uri: 'scripts/audit-b45-worker-pixel-promotion.mjs', sha256: await sha256File(resolve(repositoryRoot, 'scripts/audit-b45-worker-pixel-promotion.mjs')) },
    renderer: { uri: 'blender/render_b45_worker_pixel_canary.py', sha256: await sha256File(resolve(repositoryRoot, 'blender/render_b45_worker_pixel_canary.py')) },
    pixelAnalyzer: { uri: analyzerUri, sha256: await sha256File(analyzerPath) },
  },
  hostPixelDecoder, inputObservations, image: { id: image.Id, os: image.Os, architecture: image.Architecture, sizeBytes: image.Size }, diskAdmission,
  securityBoundary: spec.containerContract, renderControl: spec.renderControl, shots, negativeControl,
  runtimeOperationsExecuted: operations, cleanup: { experimentContainersRunningAfter: running.filter(name => names.includes(name)).length }, errors,
};
evidence.evidenceHash = hashB45Evidence(evidence);
evidence.attacks = runB45Attacks(evidence, spec);
evidence.attacksPassed = evidence.attacks.filter(item => item.passed).length;
evidence.analysis = analyzeB45Evidence(evidence, spec);
evidence.verdict = evidence.analysis.passed ? spec.acceptedVerdict : spec.rejectedVerdict;
evidence.nonClaims = spec.nonClaims;
await writeFile(resolve(experimentRoot, 'results.json'), `${JSON.stringify(evidence, null, 2)}\n`);
process.stdout.write(`BFS_B45_RESULT verdict=${evidence.verdict} exact=${shots.filter(item => item.pairComparison.pixelExact).length}/${spec.shots.length} attacks=${evidence.attacksPassed}/${evidence.attacks.length} failures=${evidence.analysis.failures.join(',') || 'none'}\n`);
if (!evidence.analysis.passed) process.exitCode = 1;
