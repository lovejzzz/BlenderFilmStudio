import { spawn, spawnSync } from 'node:child_process';
import { chmod, mkdir, readFile, readdir, stat, statfs, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { readB41Spec } from './lib/b41-linux-amd64-blender-runtime-canary.mjs';
import { B46_OCIO_SHA256, B46_PREREG_COMMIT, B46_SPEC_SHA256, analyzeB46Evidence, hashB46Evidence, readB46Spec, runB46Attacks } from './lib/b46-worker-sequence-promotion.mjs';
import { sha256File } from './lib/receipt-format.mjs';

const spec = await readB46Spec();
const workerSpec = await readB41Spec();
const experimentRoot = resolve(repositoryRoot, spec.outputRoot);
const runsRoot = resolve(experimentRoot, 'runs');
const recoveryRoot = resolve(experimentRoot, 'recovery');
const dockerBase = ['--host', workerSpec.runtime.dockerHost];
const python = spec.hostPixelDecoder.pythonExecutable;
const sequenceAnalyzerUri = 'scripts/analyze-b46-worker-sequence.py';
const sequenceAnalyzerPath = resolve(repositoryRoot, sequenceAnalyzerUri);
const ocioUri = 'color/ocio/cg-config-v4.0.0_aces-v2.0_ocio-v2.5.ocio';
const operations = [];
const errors = [];
const primaryNames = spec.shots.flatMap(shot => shot.inputs.map(input => `bfs-b46-${input.id.toLowerCase()}`));
const faultName = 'bfs-b46-tabletop-interrupted';
const recoveryName = 'bfs-b46-tabletop-recovery';
const allNames = [...primaryNames, faultName, recoveryName];

function probe(executable, args, label, options = {}) {
  const result = spawnSync(executable, args, { cwd: repositoryRoot, encoding: 'utf8', maxBuffer: 40 * 1024 * 1024, timeout: 120000, ...options });
  if (result.status !== 0) throw new Error(`${label} failed (${result.status}): ${(result.stderr || result.stdout || '').trim().slice(-5000)}`);
  return result.stdout.trim();
}

async function observeFile(uri, expectedSha256) {
  const observedSha256 = await sha256File(resolve(repositoryRoot, uri)).catch(() => null);
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
  const valid = bytes.subarray(0, 8).equals(Buffer.from([137,80,78,71,13,10,26,10])) && bytes.subarray(12, 16).toString('ascii') === 'IHDR';
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

function dockerArgs(name, shot, input, outputRoot, faultAfterFrame = null) {
  const c = spec.containerContract;
  const environment = {
    HOME:'/work/home', TMPDIR:'/work/tmp', LANG:'C.UTF-8', LC_ALL:'C.UTF-8',
    BLENDER_USER_CONFIG:'/work/blender-config', BLENDER_USER_SCRIPTS:'/work/blender-scripts', OCIO:`/repo/${ocioUri}`,
  };
  const args = [...dockerBase, 'run', '--rm', '--name', name, '--platform', c.platform, '--pull', 'never', '--read-only', '--network', c.network, '--user', c.user, '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges:true', '--pids-limit', String(c.pidsLimit), '--memory', String(c.memoryBytes), '--cpus', String(c.cpus), '--shm-size', String(c.shmBytes), '--mount', `type=bind,src=${repositoryRoot},dst=/repo,readonly`, '--mount', `type=bind,src=${outputRoot},dst=/repo/worker-output`, '--tmpfs', '/tmp:rw,noexec,nosuid,nodev,size=536870912,uid=65532,gid=65532', '--tmpfs', '/work:rw,noexec,nosuid,nodev,size=1073741824,uid=65532,gid=65532'];
  for (const [key, value] of Object.entries(environment).sort(([a], [b]) => a.localeCompare(b))) args.push('--env', `${key}=${value}`);
  const blenderArgs = [spec.image.id, '--background', '--disable-autoexec', '--offline-mode', `/repo/${input.blendUri}`, '--python-exit-code', '1', '--python', '/repo/blender/render_b46_worker_sequence.py', '--', '--source-sha256', input.blendSha256, '--shot-id', shot.shotId, '--frames', shot.frames.join(','), '--plan-hash', shot.planHash, '--scene-hash', shot.sourceSceneCanonicalSha256, '--structure-hash', shot.structureHash, '--ocio-sha256', B46_OCIO_SHA256, '--output-dir', '/repo/worker-output'];
  if (faultAfterFrame !== null) blenderArgs.push('--fault-after-frame', String(faultAfterFrame));
  return [...args, ...blenderArgs];
}

function analyzeSequence(inputDir, frames, output) {
  probe(python, [sequenceAnalyzerPath, '--input-dir', inputDir, '--frames', frames.join(','), '--expected-width', String(spec.renderControl.width), '--expected-height', String(spec.renderControl.height), '--output', output], 'B46 EXR sequence analysis', { env:{...process.env, OPENCV_IO_ENABLE_OPENEXR:'1'} });
}

function ffprobeReview(path) {
  const raw = JSON.parse(probe(spec.reviewCarrier.ffprobeExecutable, ['-v','error','-count_frames','-show_entries','stream=codec_type,codec_name,width,height,pix_fmt,r_frame_rate,nb_read_frames','-of','json',path], 'B46 review probe'));
  const video = raw.streams?.find(item => item.codec_type === 'video') ?? {};
  return { codec_name:video.codec_name ?? null, width:video.width ?? null, height:video.height ?? null, pix_fmt:video.pix_fmt ?? null, r_frame_rate:video.r_frame_rate ?? null, nb_read_frames:video.nb_read_frames ?? null, audioStreams:(raw.streams ?? []).filter(item => item.codec_type === 'audio').length };
}

async function collectArtifacts(root, frames) {
  return {
    frames: await Promise.all(frames.map(async frame => ({ frame, exr:await fileInfo(resolve(root, `frame-${String(frame).padStart(4,'0')}.exr`)), png:await pngInfo(resolve(root, `frame-${String(frame).padStart(4,'0')}.png`)) }))),
    report: await fileInfo(resolve(root, 'sequence.report.json')),
    sequenceAnalysis: await fileInfo(resolve(root, 'sequence-analysis.json')),
    review: await fileInfo(resolve(root, 'review.mp4')),
  };
}

async function executeSuccessfulRun({ id, shot, input, root, name, encodeReview }) {
  await mkdir(root, { recursive:true });
  await chmod(root, 0o777);
  const argv = dockerArgs(name, shot, input, root);
  operations.push(`DOCKER_RUN_${id}`);
  const processResult = await runTimed(name, argv);
  await Promise.all([writeFile(resolve(root,'stdout.log'),processResult.stdout),writeFile(resolve(root,'stderr.log'),processResult.stderr)]);
  let report = null, sequence = null, review = null;
  if (processResult.exitCode === 0 && !processResult.timeoutTriggered) {
    report = JSON.parse(await readFile(resolve(root,'sequence.report.json'),'utf8'));
    analyzeSequence(root, shot.frames, resolve(root,'sequence-analysis.json'));
    sequence = JSON.parse(await readFile(resolve(root,'sequence-analysis.json'),'utf8'));
    for (const frame of shot.frames) operations.push(`HOST_EXR_ANALYSIS_${id}_${frame}`);
    if (encodeReview) {
      operations.push(`FFMPEG_REVIEW_${id}`);
      probe(spec.reviewCarrier.ffmpegExecutable, ['-hide_banner','-loglevel','error','-y','-framerate',String(spec.reviewCarrier.frameRate),'-start_number',String(shot.frames[0]),'-i',resolve(root,'frame-%04d.png'),'-frames:v',String(shot.frames.length),'-c:v',spec.reviewCarrier.codec,'-preset',spec.reviewCarrier.preset,'-crf',String(spec.reviewCarrier.crf),'-pix_fmt',spec.reviewCarrier.pixelFormat,'-movflags',spec.reviewCarrier.movflags,resolve(root,'review.mp4')], `B46 review encode ${id}`);
      const probeResult = ffprobeReview(resolve(root,'review.mp4'));
      review = { valid:true, probe:probeResult };
    }
  }
  const artifacts = await collectArtifacts(root, shot.frames);
  const milestones = await readMilestones(resolve(root,'milestones.jsonl'));
  const source = { uri:input.blendUri, sha256:await sha256File(resolve(repositoryRoot,input.blendUri)), bytes:(await stat(resolve(repositoryRoot,input.blendUri))).size };
  const completed = processResult.exitCode === 0 && !processResult.timeoutTriggered && report?.passed === true && sequence?.frames?.every(item => item.finite) === true && artifacts.frames.every(item => item.png.valid);
  return { id, source, compileManifestSha256:input.compileManifestSha256, containerName:name, imageId:spec.image.id, argv, ...processResult, milestones, report, sequence, review, artifacts, completed };
}

function compareRuns(a, b, frames) {
  return {
    frames:frames.map(frame => {
      const left=a.sequence?.frames.find(item=>item.frame===frame), right=b.sequence?.frames.find(item=>item.frame===frame);
      return { frame, canonicalPixelSha256A:left?.canonicalPixelSha256??null, canonicalPixelSha256B:right?.canonicalPixelSha256??null, pixelExact:left?.canonicalPixelSha256===right?.canonicalPixelSha256 };
    }),
    transitions:a.sequence?.transitions.map((left,index)=>{ const right=b.sequence?.transitions[index]; return { fromFrame:left.fromFrame,toFrame:left.toFrame,canonicalTransitionSha256A:left.canonicalTransitionSha256,canonicalTransitionSha256B:right?.canonicalTransitionSha256??null,deltaExact:left.canonicalTransitionSha256===right?.canonicalTransitionSha256 }; }) ?? [],
    sequenceExact:a.sequence?.sequenceSha256===b.sequence?.sequenceSha256,
  };
}

if (spawnSync('git',['merge-base','--is-ancestor',B46_PREREG_COMMIT,'HEAD'],{cwd:repositoryRoot}).status !== 0) throw new Error('B46 preregistration is not an ancestor');
const toolFreezeCommit = probe('git',['rev-parse','HEAD'],'B46 tool freeze identity');
const existing = await readdir(experimentRoot).catch(error => error.code === 'ENOENT' ? [] : Promise.reject(error));
if (existing.length > 0) throw new Error(`B46 output root is not empty: ${existing.join(', ')}`);
for (const name of allNames) if (spawnSync('docker',[...dockerBase,'container','inspect',name],{encoding:'utf8'}).status === 0) throw new Error(`B46 container already exists: ${name}`);

const parentObservations=[];
for (const parent of Object.values(spec.parents)) {
  parentObservations.push(await observeFile(parent.resultUri,parent.resultSha256),await observeFile(parent.auditUri,parent.auditSha256));
  const result=JSON.parse(await readFile(resolve(repositoryRoot,parent.resultUri),'utf8'));
  if (result.verdict !== parent.verdict) throw new Error(`B46 parent verdict differs: ${parent.resultUri}`);
}
if (parentObservations.some(item=>!item.match)) throw new Error('B46 parent evidence differs');

const b44Result=JSON.parse(await readFile(resolve(repositoryRoot,spec.parents.codexWorkerPromotion.resultUri),'utf8'));
const inputMap=new Map(b44Result.inputObservations.map(item=>[item.uri,item.expectedSha256]));
inputMap.set(ocioUri,B46_OCIO_SHA256);
inputMap.set(B46_SPEC_PATH_URI(),B46_SPEC_SHA256);
inputMap.set(spec.hostPixelDecoder.analyzerUri,spec.hostPixelDecoder.analyzerSha256);
for (const shot of spec.shots) for (const input of shot.inputs) {
  inputMap.set(input.blendUri,input.blendSha256);
  inputMap.set(input.blendUri.replace(/scene\.blend$/,'scene.manifest.json'),input.compileManifestSha256);
  inputMap.set(input.structureUri,input.structureSha256);
  if ((await stat(resolve(repositoryRoot,input.blendUri))).size !== input.blendBytes) throw new Error(`B46 source size differs: ${input.id}`);
}
const inputObservations=await Promise.all([...inputMap].map(([uri,digest])=>observeFile(uri,digest)));
if (inputObservations.some(item=>!item.match)) throw new Error('B46 frozen input differs');

function B46_SPEC_PATH_URI(){ return 'specs/codex-worker-sequence-promotion.v0.1.json'; }

const pythonVersion=probe(python,['-c','import platform; print(platform.python_version())'],'B46 Python version');
const decoderVersions=JSON.parse(probe(python,['-c','import json,cv2,numpy; print(json.dumps({"opencv":cv2.__version__,"numpy":numpy.__version__}))'],'B46 decoder versions'));
const pythonSha256=await sha256File(python);
if (pythonVersion!==spec.hostPixelDecoder.pythonVersion || pythonSha256!==spec.hostPixelDecoder.pythonExecutableSha256 || decoderVersions.opencv!==spec.hostPixelDecoder.opencvVersion || decoderVersions.numpy!==spec.hostPixelDecoder.numpyVersion) throw new Error('B46 host decoder identity differs');
if (await sha256File(spec.reviewCarrier.ffmpegExecutable)!==spec.reviewCarrier.ffmpegSha256 || !probe(spec.reviewCarrier.ffmpegExecutable,['-version'],'B46 ffmpeg version').startsWith(`ffmpeg version ${spec.reviewCarrier.ffmpegVersion}`)) throw new Error('B46 ffmpeg identity differs');
if (await sha256File(spec.reviewCarrier.ffprobeExecutable)!==spec.reviewCarrier.ffprobeSha256 || !probe(spec.reviewCarrier.ffprobeExecutable,['-version'],'B46 ffprobe version').startsWith(`ffprobe version ${spec.reviewCarrier.ffprobeVersion}`)) throw new Error('B46 ffprobe identity differs');

const negativeObservedSha256=await sha256File(resolve(repositoryRoot,spec.negativeControl.sourceUri));
const negativeControl={id:spec.negativeControl.id,sourceUri:spec.negativeControl.sourceUri,declaredSha256:spec.negativeControl.declaredSha256,observedSha256:negativeObservedSha256,reason:negativeObservedSha256===spec.negativeControl.declaredSha256?'NO_REJECTION':'SOURCE_BLEND_HASH_MISMATCH',containerLaunchCount:0};

operations.push('DOCKER_IMAGE_INSPECT');
const image=JSON.parse(probe('docker',[...dockerBase,'image','inspect',spec.image.id],'B46 image inspect'))[0];
if (image.Id!==spec.image.id || image.Os!==spec.image.os || image.Architecture!==spec.image.architecture || image.Size!==spec.image.dockerReportedSizeBytes) throw new Error('B46 image identity differs');
const fs=await statfs(repositoryRoot,{bigint:true});
const availableBytes=fs.bavail*fs.bsize;
const projectedWriteBytes=BigInt(spec.diskAdmission.projectedWriteBytes);
const freeAfterProjectedBytes=availableBytes-projectedWriteBytes;
const diskAdmission={availableBytes:String(availableBytes),projectedWriteBytes:spec.diskAdmission.projectedWriteBytes,minimumReserveBytes:spec.diskAdmission.minimumReserveBytes,freeAfterProjectedBytes:String(freeAfterProjectedBytes),status:freeAfterProjectedBytes>=BigInt(spec.diskAdmission.minimumReserveBytes)?'ACCEPTED':'BLOCKED'};
if(diskAdmission.status!=='ACCEPTED') throw new Error('B46 disk admission blocked');

await mkdir(runsRoot,{recursive:true});
await mkdir(recoveryRoot,{recursive:true});
const shots=[];
let faultAttempt=null,recoveryAttempt=null;
try {
  for(const expectedShot of spec.shots){
    const shot={id:expectedShot.id,shotId:expectedShot.shotId,frames:expectedShot.frames,temporalRole:expectedShot.temporalRole,planHash:expectedShot.planHash,structureHash:expectedShot.structureHash,sourceBlendHashesDifferent:expectedShot.inputs[0].blendSha256!==expectedShot.inputs[1].blendSha256,runs:[]};
    for(const input of expectedShot.inputs){
      const run=await executeSuccessfulRun({id:input.id,shot:expectedShot,input,root:resolve(runsRoot,input.id),name:`bfs-b46-${input.id.toLowerCase()}`,encodeReview:true});
      shot.runs.push(run);
      process.stdout.write(`BFS_B46_RUN ${input.id} completed=${run.completed} exit=${run.exitCode} elapsedMs=${run.elapsedMs} sequence=${run.sequence?.sequenceSha256??'none'}\n`);
    }
    shot.pairComparison=compareRuns(shot.runs[0],shot.runs[1],expectedShot.frames);
    shots.push(shot);
  }

  const tabletop=spec.shots.find(item=>item.id==='TABLETOP');
  const tabletopInput=tabletop.inputs.find(item=>item.id===spec.recovery.sourceInputId);
  const interruptedRoot=resolve(recoveryRoot,'interrupted');
  await mkdir(interruptedRoot);
  await chmod(interruptedRoot,0o777);
  const faultArgv=dockerArgs(faultName,tabletop,tabletopInput,interruptedRoot,spec.recovery.faultAfterCompletedFrame);
  operations.push(`DOCKER_RUN_${spec.recovery.faultAttemptId}`);
  const faultProcess=await runTimed(faultName,faultArgv);
  await Promise.all([writeFile(resolve(interruptedRoot,'stdout.log'),faultProcess.stdout),writeFile(resolve(interruptedRoot,'stderr.log'),faultProcess.stderr)]);
  const faultMilestones=await readMilestones(resolve(interruptedRoot,'milestones.jsonl'));
  const completedFrames=faultMilestones.filter(item=>item.name==='FRAME_COMPLETED').length;
  const faultArtifacts=await collectArtifacts(interruptedRoot,tabletop.frames);
  const reportExists=faultArtifacts.report.sha256!==null;
  faultAttempt={id:spec.recovery.faultAttemptId,containerName:faultName,argv:faultArgv,...faultProcess,milestones:faultMilestones,artifacts:faultArtifacts,completedFrames,reportExists,promotable:false};
  process.stdout.write(`BFS_B46_FAULT exit=${faultProcess.exitCode} completedFrames=${completedFrames} report=${reportExists}\n`);

  const retryRoot=resolve(recoveryRoot,'retry');
  const outputRootWasEmpty=(await readdir(retryRoot).catch(error=>error.code==='ENOENT'?[]:Promise.reject(error))).length===0;
  const recoveryRun=await executeSuccessfulRun({id:spec.recovery.recoveryAttemptId,shot:tabletop,input:tabletopInput,root:retryRoot,name:recoveryName,encodeReview:false});
  const primary=shots.find(item=>item.id==='TABLETOP').runs.find(item=>item.id===spec.recovery.recoveryMustMatchPrimaryRunId);
  const frameHashesExact=tabletop.frames.every(frame=>primary.sequence.frames.find(item=>item.frame===frame).canonicalPixelSha256===recoveryRun.sequence.frames.find(item=>item.frame===frame).canonicalPixelSha256);
  const transitionHashesExact=primary.sequence.transitions.every((item,index)=>item.canonicalTransitionSha256===recoveryRun.sequence.transitions[index].canonicalTransitionSha256);
  recoveryAttempt={id:spec.recovery.recoveryAttemptId,newContainer:recoveryRun.containerName!==faultName,outputRootWasEmpty,differentOutputRoot:retryRoot!==interruptedRoot,run:recoveryRun,matchesPrimary:frameHashesExact&&transitionHashesExact&&primary.sequence.sequenceSha256===recoveryRun.sequence.sequenceSha256,frameHashesExact,transitionHashesExact};
  process.stdout.write(`BFS_B46_RECOVERY completed=${recoveryRun.completed} match=${recoveryAttempt.matchesPrimary}\n`);
} catch(error){ errors.push(error instanceof Error?error.message:String(error)); }

operations.push('DOCKER_RUNNING_CONTAINER_CHECK');
const running=probe('docker',[...dockerBase,'ps','--format','{{.Names}}'],'B46 running container check').split('\n').filter(Boolean);
const evidence={
  schemaVersion:'bfs.codexWorkerSequencePromotionEvidence.v0.1',experimentId:'B46',preregistration:{commit:B46_PREREG_COMMIT,specSha256:B46_SPEC_SHA256},parents:spec.parents,parentObservations,
  toolFreezeCommit,tools:{
    runner:{uri:'scripts/run-b46-worker-sequence-promotion.mjs',sha256:await sha256File(resolve(repositoryRoot,'scripts/run-b46-worker-sequence-promotion.mjs'))},
    library:{uri:'scripts/lib/b46-worker-sequence-promotion.mjs',sha256:await sha256File(resolve(repositoryRoot,'scripts/lib/b46-worker-sequence-promotion.mjs'))},
    audit:{uri:'scripts/audit-b46-worker-sequence-promotion.mjs',sha256:await sha256File(resolve(repositoryRoot,'scripts/audit-b46-worker-sequence-promotion.mjs'))},
    renderer:{uri:'blender/render_b46_worker_sequence.py',sha256:await sha256File(resolve(repositoryRoot,'blender/render_b46_worker_sequence.py'))},
    sequenceAnalyzer:{uri:sequenceAnalyzerUri,sha256:await sha256File(sequenceAnalyzerPath)},
  },
  hostPixelDecoder:spec.hostPixelDecoder,reviewCarrierControl:spec.reviewCarrier,inputObservations,image:{id:image.Id,os:image.Os,architecture:image.Architecture,sizeBytes:image.Size},diskAdmission,
  securityBoundary:spec.containerContract,renderControl:spec.renderControl,shots,faultAttempt,recoveryAttempt,negativeControl,runtimeOperationsExecuted:operations,cleanup:{experimentContainersRunningAfter:running.filter(name=>allNames.includes(name)).length},errors,
};
evidence.evidenceHash=hashB46Evidence(evidence);
evidence.attacks=runB46Attacks(evidence,spec);
evidence.attacksPassed=evidence.attacks.filter(item=>item.passed).length;
evidence.analysis=analyzeB46Evidence(evidence,spec);
evidence.verdict=evidence.analysis.passed?spec.acceptedVerdict:spec.rejectedVerdict;
evidence.nonClaims=spec.nonClaims;
await writeFile(resolve(experimentRoot,'results.json'),`${JSON.stringify(evidence,null,2)}\n`);
const exactFrames=shots.flatMap(item=>item.pairComparison.frames).filter(item=>item.pixelExact).length;
const exactTransitions=shots.flatMap(item=>item.pairComparison.transitions).filter(item=>item.deltaExact).length;
process.stdout.write(`BFS_B46_RESULT verdict=${evidence.verdict} frames=${exactFrames}/16 transitions=${exactTransitions}/14 recovery=${recoveryAttempt?.matchesPrimary??false} attacks=${evidence.attacksPassed}/${evidence.attacks.length} failures=${evidence.analysis.failures.join(',')||'none'}\n`);
if(!evidence.analysis.passed) process.exitCode=1;
