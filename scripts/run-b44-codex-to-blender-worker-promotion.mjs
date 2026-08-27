import { spawn, spawnSync } from 'node:child_process';
import { chmod, mkdir, readFile, readdir, statfs, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { canonicalJson, repositoryRoot, sha256 } from './lib/scene-spec.mjs';
import { createProposalValidator, materializeSceneSpec, readB43Spec, validateProposal } from './lib/b43-codex-scenespec-adapter.mjs';
import { readB41Spec } from './lib/b41-linux-amd64-blender-runtime-canary.mjs';
import { observeSuccessfulRun } from './lib/b42-linux-amd64-compiler-repro.mjs';
import { B44_PREREG_COMMIT, B44_SPEC_SHA256, analyzeB44Evidence, hashB44Evidence, readB44Spec, runB44Attacks } from './lib/b44-codex-to-blender-worker-promotion.mjs';
import { sha256File } from './lib/receipt-format.mjs';

const spec = await readB44Spec();
const [adapterSpec, workerSpec] = await Promise.all([readB43Spec(), readB41Spec()]);
const validator = await createProposalValidator(adapterSpec);
const experimentRoot = resolve(repositoryRoot, 'experiments/codex-to-blender-worker-promotion-v0-1');
const runsRoot = resolve(experimentRoot, 'runs');
const dockerBase = ['--host', workerSpec.runtime.dockerHost];
const names = spec.selectedProposals.filter(item => item.decision === 'ACCEPT').flatMap(item => item.runs.map(runId => `bfs-b44-${runId.toLowerCase()}`));
const operations = [];
const errors = [];

function probe(executable, args, label) {
  const result = spawnSync(executable, args, { cwd: repositoryRoot, encoding: 'utf8', maxBuffer: 20 * 1024 * 1024, timeout: 120000 });
  if (result.status !== 0) throw new Error(`${label} failed (${result.status}): ${(result.stderr || result.stdout || '').trim().slice(-4000)}`);
  return result.stdout.trim();
}

async function observeFile(uri, expectedSha256) {
  const observedSha256 = await sha256File(resolve(repositoryRoot, uri)).catch(() => null);
  return { uri, expectedSha256, observedSha256, match: observedSha256 === expectedSha256 };
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

function dockerArgs(name, planUri, outputRoot) {
  const c = spec.containerContract;
  const environment = {
    HOME: '/work/home', TMPDIR: '/work/tmp', LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8',
    BLENDER_USER_CONFIG: '/work/blender-config', BLENDER_USER_SCRIPTS: '/work/blender-scripts',
    OCIO: `/repo/${spec.inputs.ocio.uri}`,
  };
  const args = [...dockerBase, 'run', '--rm', '--name', name, '--platform', c.platform, '--pull', 'never', '--read-only', '--network', c.network, '--user', c.user, '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges:true', '--pids-limit', String(c.pidsLimit), '--memory', String(c.memoryBytes), '--cpus', String(c.cpus), '--shm-size', String(c.shmBytes), '--mount', `type=bind,src=${repositoryRoot},dst=/repo,readonly`, '--mount', `type=bind,src=${outputRoot},dst=/repo/worker-output`, '--tmpfs', '/tmp:rw,noexec,nosuid,nodev,size=536870912,uid=65532,gid=65532', '--tmpfs', '/work:rw,noexec,nosuid,nodev,size=1073741824,uid=65532,gid=65532'];
  for (const [key, value] of Object.entries(environment).sort(([a], [b]) => a.localeCompare(b))) args.push('--env', `${key}=${value}`);
  return [...args, spec.image.id, '--background', '--factory-startup', '--disable-autoexec', '--offline-mode', '--python-exit-code', '1', '--python', '/repo/blender/compile_scene.py', '--', '--plan', `/repo/${planUri}`, '--repository-root', '/repo', '--output-dir', '/repo/worker-output'];
}

if (spawnSync('git', ['merge-base', '--is-ancestor', B44_PREREG_COMMIT, 'HEAD'], { cwd: repositoryRoot }).status !== 0) throw new Error('B44 preregistration is not an ancestor');
const toolFreezeCommit = probe('git', ['rev-parse', 'HEAD'], 'tool freeze identity');
const existing = await readdir(experimentRoot).catch(error => error.code === 'ENOENT' ? [] : Promise.reject(error));
if (existing.length > 0) throw new Error(`B44 output root is not empty: ${existing.join(', ')}`);
for (const name of names) if (spawnSync('docker', [...dockerBase, 'container', 'inspect', name], { encoding: 'utf8' }).status === 0) throw new Error(`B44 container already exists: ${name}`);

const parentObservations = [];
for (const parent of Object.values(spec.parents)) {
  parentObservations.push(await observeFile(parent.resultUri, parent.resultSha256));
  parentObservations.push(await observeFile(parent.auditUri, parent.auditSha256));
  const result = JSON.parse(await readFile(resolve(repositoryRoot, parent.resultUri), 'utf8'));
  if (result.verdict !== parent.verdict) throw new Error(`B44 parent verdict differs: ${parent.resultUri}`);
}
if (parentObservations.some(item => !item.match)) throw new Error('B44 parent evidence differs');

const inputRecords = [...Object.values(spec.inputs)];
for (const item of spec.selectedProposals) {
  inputRecords.push({ uri: item.uri, sha256: item.fileSha256 });
  if (item.decision === 'ACCEPT') {
    inputRecords.push({ uri: item.sceneSpec.uri, sha256: item.sceneSpec.fileSha256 }, { uri: item.buildPlan.uri, sha256: item.buildPlan.fileSha256 }, ...item.assets);
  }
}
const inputObservations = await Promise.all(inputRecords.map(item => observeFile(item.uri, item.sha256)));
if (inputObservations.some(item => !item.match)) throw new Error('B44 frozen input differs');

operations.push('DOCKER_IMAGE_INSPECT');
const image = JSON.parse(probe('docker', [...dockerBase, 'image', 'inspect', spec.image.id], 'image inspect'))[0];
if (image.Id !== spec.image.id || image.Os !== spec.image.os || image.Architecture !== spec.image.architecture || image.Size !== spec.image.dockerReportedSizeBytes) throw new Error('B44 image identity differs');
const fs = await statfs(repositoryRoot, { bigint: true });
const availableBytes = fs.bavail * fs.bsize;
const freeAfterProjectedBytes = availableBytes - BigInt(spec.diskAdmission.projectedWriteBytes);
const diskAdmission = { availableBytes: String(availableBytes), projectedWriteBytes: spec.diskAdmission.projectedWriteBytes, minimumReserveBytes: spec.diskAdmission.minimumReserveBytes, freeAfterProjectedBytes: String(freeAfterProjectedBytes), status: freeAfterProjectedBytes >= BigInt(spec.diskAdmission.minimumReserveBytes) ? 'ACCEPTED' : 'BLOCKED' };
if (diskAdmission.status !== 'ACCEPTED') throw new Error('B44 disk admission blocked');

await mkdir(runsRoot, { recursive: true });
const proposals = [];
try {
  for (const expected of spec.selectedProposals) {
    const proposalText = await readFile(resolve(repositoryRoot, expected.uri), 'utf8');
    const proposal = JSON.parse(proposalText);
    const fileSha256 = sha256(Buffer.from(proposalText));
    const canonicalSha256 = sha256(Buffer.from(canonicalJson(proposal)));
    const schemaValid = validator(proposal);
    const semantic = await validateProposal(proposal, expected.briefId, adapterSpec, validator);
    const record = { id: expected.id, briefId: expected.briefId, decision: proposal.decision, fileSha256, canonicalSha256, schemaValid, semanticValid: semantic.valid, materialize: semantic.materialize, sceneSpecCount: 0, buildPlanCount: 0, containerLaunchCount: 0 };
    if (!semantic.materialize) {
      proposals.push(record);
      process.stdout.write(`BFS_B44_REJECT ${expected.id} preContainer=true launches=0\n`);
      continue;
    }

    const materialized = await materializeSceneSpec(proposal, adapterSpec, validator);
    const frozenSceneText = await readFile(resolve(repositoryRoot, expected.sceneSpec.uri), 'utf8');
    const frozenScene = JSON.parse(frozenSceneText);
    const planText = await readFile(resolve(repositoryRoot, expected.buildPlan.uri), 'utf8');
    const plan = JSON.parse(planText);
    record.sceneSpecCount = 1;
    record.buildPlanCount = 1;
    record.sceneSpec = {
      uri: expected.sceneSpec.uri,
      fileSha256: sha256(Buffer.from(frozenSceneText)),
      canonicalSha256: sha256(Buffer.from(canonicalJson(frozenScene))),
      materializedCanonicalSha256: sha256(Buffer.from(canonicalJson(materialized.scene))),
    };
    record.buildPlan = {
      uri: expected.buildPlan.uri,
      fileSha256: sha256(Buffer.from(planText)),
      planHash: plan.planHash,
      sourceSceneCanonicalSha256: plan.plan.source.canonicalSha256,
    };
    record.runs = [];
    for (const runId of expected.runs) {
      const outputRoot = resolve(runsRoot, runId);
      await mkdir(outputRoot);
      await chmod(outputRoot, 0o777);
      const name = `bfs-b44-${runId.toLowerCase()}`;
      const argv = dockerArgs(name, expected.buildPlan.uri, outputRoot);
      operations.push(`DOCKER_RUN_${runId}`);
      record.containerLaunchCount += 1;
      const processResult = await runTimed(name, argv);
      await Promise.all([writeFile(resolve(outputRoot, 'stdout.log'), processResult.stdout), writeFile(resolve(outputRoot, 'stderr.log'), processResult.stderr)]);
      const observed = processResult.exitCode === 0 && !processResult.timeoutTriggered ? await observeSuccessfulRun(outputRoot) : null;
      record.runs.push({ id: runId, containerName: name, imageId: spec.image.id, argv, ...processResult, observed, completed: observed !== null });
      process.stdout.write(`BFS_B44_RUN ${runId} completed=${observed !== null} exit=${processResult.exitCode} elapsedMs=${processResult.elapsedMs}\n`);
    }
    record.structureFilesByteEqual = record.runs[0].observed?.structure.sha256 === record.runs[1].observed?.structure.sha256;
    record.structureHash = record.runs[0].observed?.structure.sha256 ?? null;
    record.blendByteIdentical = record.runs[0].observed?.blend.sha256 === record.runs[1].observed?.blend.sha256;
    proposals.push(record);
  }
} catch (error) {
  errors.push(error instanceof Error ? error.message : String(error));
}

operations.push('DOCKER_RUNNING_CONTAINER_CHECK');
const running = probe('docker', [...dockerBase, 'ps', '--format', '{{.Names}}'], 'running container check').split('\n').filter(Boolean);
const evidence = {
  schemaVersion: 'bfs.codexToBlenderWorkerPromotionEvidence.v0.1', experimentId: 'B44',
  preregistration: { commit: B44_PREREG_COMMIT, specSha256: B44_SPEC_SHA256 }, parents: spec.parents, parentObservations,
  toolFreezeCommit,
  tools: {
    runner: { uri: 'scripts/run-b44-codex-to-blender-worker-promotion.mjs', sha256: await sha256File(resolve(repositoryRoot, 'scripts/run-b44-codex-to-blender-worker-promotion.mjs')) },
    library: { uri: 'scripts/lib/b44-codex-to-blender-worker-promotion.mjs', sha256: await sha256File(resolve(repositoryRoot, 'scripts/lib/b44-codex-to-blender-worker-promotion.mjs')) },
    audit: { uri: 'scripts/audit-b44-codex-to-blender-worker-promotion.mjs', sha256: await sha256File(resolve(repositoryRoot, 'scripts/audit-b44-codex-to-blender-worker-promotion.mjs')) },
    adapter: spec.inputs.adapter,
    sceneCompiler: spec.inputs.sceneCompiler,
  },
  inputObservations, image: { id: image.Id, os: image.Os, architecture: image.Architecture, sizeBytes: image.Size }, diskAdmission,
  securityBoundary: spec.containerContract, proposals, runtimeOperationsExecuted: operations,
  cleanup: { experimentContainersRunningAfter: running.filter(name => names.includes(name)).length }, errors,
};
evidence.evidenceHash = hashB44Evidence(evidence);
evidence.attacks = runB44Attacks(evidence, spec);
evidence.attacksPassed = evidence.attacks.filter(item => item.passed).length;
evidence.analysis = analyzeB44Evidence(evidence, spec);
evidence.verdict = evidence.analysis.passed ? spec.acceptedVerdict : spec.rejectedVerdict;
evidence.nonClaims = spec.nonClaims;
await writeFile(resolve(experimentRoot, 'results.json'), `${JSON.stringify(evidence, null, 2)}\n`);
process.stdout.write(`BFS_B44_RESULT verdict=${evidence.verdict} structures=${proposals.filter(item => item.decision === 'ACCEPT').map(item => `${item.id}:${item.structureHash}`).join(',')} attacks=${evidence.attacksPassed}/${evidence.attacks.length} failures=${evidence.analysis.failures.join(',') || 'none'}\n`);
if (!evidence.analysis.passed) process.exitCode = 1;
