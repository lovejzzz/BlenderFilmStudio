import { spawnSync } from 'node:child_process';
import { readFile, stat, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { canonicalJson, repositoryRoot } from './lib/scene-spec.mjs';
import { analyzeB46Evidence, hashB46Evidence, readB46Spec, runB46Attacks } from './lib/b46-worker-sequence-promotion.mjs';
import { sha256File } from './lib/receipt-format.mjs';

const spec=await readB46Spec();
const outputRoot=resolve(repositoryRoot,spec.outputRoot);
const result=JSON.parse(await readFile(resolve(outputRoot,'results.json'),'utf8'));
const analyzer=resolve(repositoryRoot,'scripts/analyze-b46-worker-sequence.py');

async function observeFile(uri,expectedSha256){
  const observedSha256=await sha256File(resolve(repositoryRoot,uri)).catch(()=>null);
  return {uri,expectedSha256,observedSha256,match:observedSha256===expectedSha256};
}

async function fileInfo(path){
  try{return {uri:path.slice(repositoryRoot.length+1),bytes:(await stat(path)).size,sha256:await sha256File(path)};}
  catch{return {uri:path.slice(repositoryRoot.length+1),bytes:0,sha256:null};}
}

async function pngInfo(path){
  const info=await fileInfo(path);
  if(!info.sha256)return {...info,valid:false,dimensions:null};
  const bytes=await readFile(path);
  const valid=bytes.subarray(0,8).equals(Buffer.from([137,80,78,71,13,10,26,10]))&&bytes.subarray(12,16).toString('ascii')==='IHDR';
  return {...info,valid,dimensions:valid?[bytes.readUInt32BE(16),bytes.readUInt32BE(20)]:null};
}

async function readMilestones(path){
  const text=await readFile(path,'utf8').catch(()=>'');
  return text.split('\n').filter(Boolean).map(line=>JSON.parse(line));
}

function analyzeSequence(root,frames){
  const executed=spawnSync(spec.hostPixelDecoder.pythonExecutable,[analyzer,'--input-dir',root,'--frames',frames.join(','),'--expected-width',String(spec.renderControl.width),'--expected-height',String(spec.renderControl.height),'--output','-'],{cwd:repositoryRoot,encoding:'utf8',maxBuffer:30*1024*1024,env:{...process.env,OPENCV_IO_ENABLE_OPENEXR:'1'}});
  if(executed.status!==0)throw new Error(`B46 audit decoder failed: ${executed.stderr}`);
  return JSON.parse(executed.stdout);
}

function ffprobeReview(path){
  const executed=spawnSync(spec.reviewCarrier.ffprobeExecutable,['-v','error','-count_frames','-show_entries','stream=codec_type,codec_name,width,height,pix_fmt,r_frame_rate,nb_read_frames','-of','json',path],{cwd:repositoryRoot,encoding:'utf8',maxBuffer:10*1024*1024});
  if(executed.status!==0)throw new Error(`B46 audit ffprobe failed: ${executed.stderr}`);
  const raw=JSON.parse(executed.stdout),video=raw.streams?.find(item=>item.codec_type==='video')??{};
  return {codec_name:video.codec_name??null,width:video.width??null,height:video.height??null,pix_fmt:video.pix_fmt??null,r_frame_rate:video.r_frame_rate??null,nb_read_frames:video.nb_read_frames??null,audioStreams:(raw.streams??[]).filter(item=>item.codec_type==='audio').length};
}

async function collectArtifacts(root,frames){
  return {frames:await Promise.all(frames.map(async frame=>({frame,exr:await fileInfo(resolve(root,`frame-${String(frame).padStart(4,'0')}.exr`)),png:await pngInfo(resolve(root,`frame-${String(frame).padStart(4,'0')}.png`))}))),report:await fileInfo(resolve(root,'sequence.report.json')),sequenceAnalysis:await fileInfo(resolve(root,'sequence-analysis.json')),review:await fileInfo(resolve(root,'review.mp4'))};
}

function compareRuns(a,b,frames){
  return {frames:frames.map(frame=>{const left=a.sequence.frames.find(item=>item.frame===frame),right=b.sequence.frames.find(item=>item.frame===frame);return {frame,canonicalPixelSha256A:left.canonicalPixelSha256,canonicalPixelSha256B:right.canonicalPixelSha256,pixelExact:left.canonicalPixelSha256===right.canonicalPixelSha256};}),transitions:a.sequence.transitions.map((left,index)=>{const right=b.sequence.transitions[index];return {fromFrame:left.fromFrame,toFrame:left.toFrame,canonicalTransitionSha256A:left.canonicalTransitionSha256,canonicalTransitionSha256B:right.canonicalTransitionSha256,deltaExact:left.canonicalTransitionSha256===right.canonicalTransitionSha256};}),sequenceExact:a.sequence.sequenceSha256===b.sequence.sequenceSha256};
}

const parentObservations=[];
for(const parent of Object.values(spec.parents))parentObservations.push(await observeFile(parent.resultUri,parent.resultSha256),await observeFile(parent.auditUri,parent.auditSha256));
const parentsMatch=parentObservations.every(item=>item.match)&&canonicalJson(parentObservations)===canonicalJson(result.parentObservations);
const toolObservations=Object.fromEntries(await Promise.all(Object.entries(result.tools).map(async([key,item])=>{const observedSha256=await sha256File(resolve(repositoryRoot,item.uri)).catch(()=>null);return [key,{uri:item.uri,expectedSha256:item.sha256,observedSha256,match:observedSha256===item.sha256}];})));
const toolsMatch=Object.values(toolObservations).every(item=>item.match);
const inputObservations=await Promise.all(result.inputObservations.map(item=>observeFile(item.uri,item.expectedSha256)));
const inputsMatch=inputObservations.every(item=>item.match)&&canonicalJson(inputObservations)===canonicalJson(result.inputObservations);

const runObservations=[];
const auditedShots=[];
for(const shot of result.shots){
  const auditedShot={id:shot.id,runs:[]};
  for(const run of shot.runs){
    const root=resolve(outputRoot,'runs',run.id);
    const report=JSON.parse(await readFile(resolve(root,'sequence.report.json'),'utf8'));
    const sequence=analyzeSequence(root,shot.frames);
    const milestones=await readMilestones(resolve(root,'milestones.jsonl'));
    const artifacts=await collectArtifacts(root,shot.frames);
    const review={valid:true,probe:ffprobeReview(resolve(root,'review.mp4'))};
    const sourceMatch=await sha256File(resolve(repositoryRoot,run.source.uri))===run.source.sha256;
    const match=sourceMatch&&canonicalJson(report)===canonicalJson(run.report)&&canonicalJson(sequence)===canonicalJson(run.sequence)&&canonicalJson(milestones)===canonicalJson(run.milestones)&&canonicalJson(artifacts)===canonicalJson(run.artifacts)&&canonicalJson(review)===canonicalJson(run.review);
    const observation={id:run.id,report,sequence,milestones,artifacts,review,sourceMatch,match};
    runObservations.push(observation);
    auditedShot.runs.push({...run,report,sequence,milestones,artifacts,review});
  }
  auditedShot.pairComparison=compareRuns(auditedShot.runs[0],auditedShot.runs[1],shot.frames);
  auditedShots.push(auditedShot);
}
const outputsMatch=runObservations.length===4&&runObservations.every(item=>item.match);
const pairObservations=auditedShots.map(item=>({id:item.id,...item.pairComparison}));
const pairsMatch=result.shots.every(shot=>canonicalJson(pairObservations.find(item=>item.id===shot.id))===canonicalJson({id:shot.id,...shot.pairComparison}))&&pairObservations.every(item=>item.sequenceExact&&item.frames.every(frame=>frame.pixelExact)&&item.transitions.every(transition=>transition.deltaExact));

const faultRoot=resolve(outputRoot,'recovery','interrupted');
const faultMilestones=await readMilestones(resolve(faultRoot,'milestones.jsonl'));
const faultArtifacts=await collectArtifacts(faultRoot,spec.shots.find(item=>item.id==='TABLETOP').frames);
const faultObservation={completedFrames:faultMilestones.filter(item=>item.name==='FRAME_COMPLETED').length,reportExists:faultArtifacts.report.sha256!==null,milestones:faultMilestones,artifacts:faultArtifacts};
const faultMatch=faultObservation.completedFrames===result.faultAttempt.completedFrames&&faultObservation.reportExists===result.faultAttempt.reportExists&&canonicalJson(faultObservation.milestones)===canonicalJson(result.faultAttempt.milestones)&&canonicalJson(faultObservation.artifacts)===canonicalJson(result.faultAttempt.artifacts);

const tabletop=spec.shots.find(item=>item.id==='TABLETOP');
const recoveryRun=result.recoveryAttempt.run;
const retryRoot=resolve(outputRoot,'recovery','retry');
const recoveryReport=JSON.parse(await readFile(resolve(retryRoot,'sequence.report.json'),'utf8'));
const recoverySequence=analyzeSequence(retryRoot,tabletop.frames);
const recoveryMilestones=await readMilestones(resolve(retryRoot,'milestones.jsonl'));
const recoveryArtifacts=await collectArtifacts(retryRoot,tabletop.frames);
const recoveryRunMatch=canonicalJson(recoveryReport)===canonicalJson(recoveryRun.report)&&canonicalJson(recoverySequence)===canonicalJson(recoveryRun.sequence)&&canonicalJson(recoveryMilestones)===canonicalJson(recoveryRun.milestones)&&canonicalJson(recoveryArtifacts)===canonicalJson(recoveryRun.artifacts);
const primary=result.shots.find(item=>item.id==='TABLETOP').runs.find(item=>item.id===spec.recovery.recoveryMustMatchPrimaryRunId);
const recoveryFrameHashesExact=tabletop.frames.every(frame=>primary.sequence.frames.find(item=>item.frame===frame).canonicalPixelSha256===recoverySequence.frames.find(item=>item.frame===frame).canonicalPixelSha256);
const recoveryTransitionHashesExact=primary.sequence.transitions.every((item,index)=>item.canonicalTransitionSha256===recoverySequence.transitions[index].canonicalTransitionSha256);
const recoveryObservation={runMatch:recoveryRunMatch,frameHashesExact:recoveryFrameHashesExact,transitionHashesExact:recoveryTransitionHashesExact,sequenceExact:primary.sequence.sequenceSha256===recoverySequence.sequenceSha256};
const recoveryMatch=recoveryRunMatch&&recoveryFrameHashesExact&&recoveryTransitionHashesExact&&recoveryObservation.sequenceExact&&result.recoveryAttempt.matchesPrimary;

const attacks=runB46Attacks(result,spec);
const attacksMatch=canonicalJson(attacks)===canonicalJson(result.attacks)&&attacks.every(item=>item.passed);
const analysis=analyzeB46Evidence(result,spec);
const audit={schemaVersion:'bfs.codexWorkerSequencePromotionIndependentAudit.v0.1',experimentId:'B46',analysis,parentsMatch,parentObservations,toolsMatch,toolObservations,inputsMatch,inputObservations,outputsMatch,runObservations,pairsMatch,pairObservations,faultMatch,faultObservation,recoveryMatch,recoveryObservation,attacksMatch,attacks,evidenceSelfHashMatch:result.evidenceHash===hashB46Evidence(result)};
audit.passed=analysis.passed&&parentsMatch&&toolsMatch&&inputsMatch&&outputsMatch&&pairsMatch&&faultMatch&&recoveryMatch&&attacksMatch&&audit.evidenceSelfHashMatch;
await writeFile(resolve(outputRoot,'audit.json'),`${JSON.stringify(audit,null,2)}\n`);
process.stdout.write(`BFS_B46_AUDIT ${audit.passed?'PASS':'FAIL'} outputs=${outputsMatch?'MATCH':'MISMATCH'} framePairs=${pairObservations.flatMap(item=>item.frames).filter(item=>item.pixelExact).length}/16 transitionPairs=${pairObservations.flatMap(item=>item.transitions).filter(item=>item.deltaExact).length}/14 recovery=${recoveryMatch?'MATCH':'MISMATCH'} attacks=${attacks.filter(item=>item.passed).length}/${attacks.length}\n`);
if(!audit.passed)process.exitCode=1;
