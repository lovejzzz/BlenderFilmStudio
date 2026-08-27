import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { canonicalJson, repositoryRoot, sha256 } from './scene-spec.mjs';

export const B47_SPEC_URI='specs/codex-worker-production-pass-promotion.v0.1.json';
export const B47_SPEC_PATH=resolve(repositoryRoot,B47_SPEC_URI);
export const B47_SPEC_SHA256='eece60ee1cd686086384e200f6ddc0bfa9b7a4e1bcc2a47e59c49701bfb4dc5e';
export const B47_PREREG_COMMIT='c93ef549982fcf55cb53a4c3383b145cb14d20a4';
export const B47_OCIO_SHA256='24ec81841048fc5db160a7bad882263246183385c5d49d0e86e11464917ead15';

export async function readB47Spec(){const bytes=await readFile(B47_SPEC_PATH);const digest=sha256(bytes);if(digest!==B47_SPEC_SHA256)throw new Error(`B47 spec SHA mismatch: ${digest}`);return JSON.parse(bytes);}
export function hashB47Evidence(evidence){const copy=structuredClone(evidence);for(const key of ['evidenceHash','analysis','attacks','attacksPassed','verdict','nonClaims'])delete copy[key];return sha256(Buffer.from(canonicalJson(copy)));}
export function expectedB47Settings(spec,seed){const v=spec.renderControl;return {engine:v.engine,device:v.device,resolution:[v.width,v.height,v.resolutionPercentage],samples:v.samples,seed,animatedSeed:v.animatedSeed,denoising:v.denoising,motionBlur:v.motionBlur,persistentData:v.persistentData,threadsMode:v.threadsMode,threads:v.threads,filmTransparent:v.filmTransparent,compositing:v.compositing,sequencer:v.sequencer};}
export function expectedB47PassState(spec){return {viewLayer:spec.productionPack.viewLayer,Combined:true,Depth:true,Normal:true,Position:false,Vector:true,CryptoObject:true,CryptoMaterial:false,CryptoAsset:false,cryptomatteDepth:6,cryptomatteAccurate:true};}
const expectedMilestones=()=>['PROCESS_STARTED','SOURCE_VERIFIED','SCENE_CONFIGURED','FRAME_STARTED','FRAME_COMPLETED','FRAME_STARTED','FRAME_COMPLETED','REPORT_WRITTEN'];

function packLayout(frame,spec){
  if(frame?.subimageCount!==spec.productionPack.subimageCount||frame?.subimages?.length!==spec.productionPack.subimageCount)return false;
  return spec.productionPack.subimages.every((expected,index)=>{const item=frame.subimages[index];const prefix=`${spec.productionPack.viewLayer}.${expected.pass}`;return item?.index===index&&item?.pass===expected.pass&&item?.name===prefix&&item?.width===spec.renderControl.width&&item?.height===spec.renderControl.height&&canonicalJson(item?.channels)===canonicalJson(expected.channels.map(channel=>`${prefix}.${channel}`))&&item?.channelFormats?.every(format=>format===spec.productionPack.channelFormat)&&item?.metadata?.dtype==='float32-le'&&item?.metadata?.order==='C';});
}
function passSemantics(frame,pass,spec,shot){
  const item=frame?.subimages?.find(value=>value.pass===pass);if(!item)return false;
  if(item.componentCount!==item.finiteCount||item.nanCount!==0||item.infinityCount!==0)return false;
  if(pass==='Combined')return item.nonZeroFiniteCount>0;
  if(pass==='Depth')return item.finiteMin>0&&item.finiteMax<=spec.productionPack.subimages.find(value=>value.pass==='Depth').maximumInclusive;
  if(pass==='Normal')return item.nonZeroFiniteCount>0&&item.finiteMin>=-1&&item.finiteMax<=1;
  if(pass==='Vector'&&shot.temporalRole==='MOVING_CAMERA')return item.nonZeroFiniteCount>0;
  return true;
}
function cryptoSemantics(frame,spec,shot){const c=frame?.cryptomatte,p=spec.productionPack.cryptomatte;return c?.hash===p.hash&&c?.conversion===p.conversion&&c?.name===p.layerName&&c?.manifestValid===true&&shot.requiredAssetObjectNames.every(name=>Object.hasOwn(c.manifest??{},name));}

export function analyzeB47Evidence(evidence,spec,{requireAttacks=true}={}){
  const failures=[];const gate=(condition,code)=>{if(!condition&&!failures.includes(code))failures.push(code);};
  gate(evidence?.schemaVersion==='bfs.codexWorkerProductionPassPromotionEvidence.v0.1'&&evidence?.experimentId==='B47','EVIDENCE_SCHEMA');
  gate(evidence?.preregistration?.commit===B47_PREREG_COMMIT&&evidence?.preregistration?.specSha256===B47_SPEC_SHA256,'PREREGISTRATION_IDENTITY');
  gate(canonicalJson(evidence?.parents)===canonicalJson(spec.parents),'PARENT_IDENTITY');
  gate(evidence?.parentObservations?.length===5&&evidence.parentObservations.every(item=>item.match),'PARENT_HASH');
  gate(evidence?.inputObservations?.length>=16&&evidence.inputObservations.every(item=>item.match),'FROZEN_INPUT_HASH');
  gate(/^[a-f0-9]{40}$/.test(evidence?.toolFreezeCommit??'')&&Object.values(evidence?.tools??{}).every(item=>/^[a-f0-9]{64}$/.test(item?.sha256??'')),'TOOL_IDENTITY');
  gate(canonicalJson(evidence?.hostInspector)===canonicalJson(spec.hostInspector),'INSPECTOR_IDENTITY');
  gate(canonicalJson(evidence?.image)===canonicalJson({id:spec.image.id,os:spec.image.os,architecture:spec.image.architecture,sizeBytes:spec.image.dockerReportedSizeBytes}),'IMAGE_IDENTITY');
  let disk=false;try{disk=evidence?.diskAdmission?.status==='ACCEPTED'&&BigInt(evidence.diskAdmission.freeAfterProjectedBytes)>=BigInt(spec.diskAdmission.minimumReserveBytes);}catch{}
  gate(disk,'DISK_ADMISSION');gate(canonicalJson(evidence?.securityBoundary)===canonicalJson(spec.containerContract),'SECURITY_BOUNDARY');gate(canonicalJson(evidence?.renderControl)===canonicalJson(spec.renderControl),'RENDER_CONTROL');gate(evidence?.shots?.length===2,'SHOT_COUNT');
  for(const expectedShot of spec.shots){
    const shot=evidence?.shots?.find(item=>item.id===expectedShot.id);gate(shot?.runs?.length===2,`RUN_COUNT_${expectedShot.id}`);
    for(const expectedInput of expectedShot.inputs){
      const run=shot?.runs?.find(item=>item.id===expectedInput.id);gate(run?.source?.uri===expectedInput.blendUri&&run?.source?.sha256===expectedInput.blendSha256&&run?.source?.bytes===expectedInput.blendBytes,`SOURCE_IDENTITY_${expectedInput.id}`);gate(run?.exitCode===0&&run?.timeoutTriggered===false&&run?.completed===true,`RUN_COMPLETE_${expectedInput.id}`);
      const report=run?.report;gate(report?.source?.uri===`/repo/${expectedInput.blendUri}`&&report?.source?.sha256===expectedInput.blendSha256&&report?.source?.bytes===expectedInput.blendBytes,`REPORT_SOURCE_${expectedInput.id}`);gate(report?.bindings?.planHash===expectedShot.planHash&&report?.bindings?.sceneSpecHash===expectedShot.sourceSceneCanonicalSha256&&report?.bindings?.structureHash===expectedShot.structureHash,`REPORT_PLAN_${expectedInput.id}`);gate(canonicalJson(report?.frames)===canonicalJson(expectedShot.frames),`FRAME_ORDER_${expectedInput.id}`);
      gate(Number.isInteger(report?.bindings?.shotSeed)&&canonicalJson(report?.appliedSettings)===canonicalJson(expectedB47Settings(spec,report.bindings.shotSeed))&&canonicalJson(report?.passState)===canonicalJson(expectedB47PassState(spec))&&report?.renderOperatorCalls===2&&report?.savesFromSameRenderResult===2&&canonicalJson(report?.saveSettings)===canonicalJson({mediaType:spec.renderControl.mediaType,fileFormat:spec.renderControl.format,colorMode:spec.renderControl.channels,colorDepth:spec.renderControl.colorDepth,codec:spec.renderControl.codec}),`RENDER_SETTINGS_${expectedInput.id}`);
      gate(report?.blender?.version===spec.image.blenderVersion&&report?.blender?.buildHash===spec.image.blenderBuildHash&&report?.blender?.buildPlatform==='Linux'&&report?.ocio?.sha256===B47_OCIO_SHA256&&report?.ocio?.declaredEncoding==='ACEScg',`RUNTIME_BINDING_${expectedInput.id}`);
      for(const frameNo of expectedShot.frames){
        const frame=run?.inspections?.find(item=>item.frame===frameNo),artifact=run?.artifacts?.frames?.find(item=>item.frame===frameNo),reportFrame=report?.frameReports?.find(item=>item.frame===frameNo);
        gate(frame?.input?.sha256===artifact?.exr?.sha256&&frame?.input?.sha256===reportFrame?.artifact?.sha256&&artifact?.exr?.bytes===reportFrame?.artifact?.bytes,`FRAME_BINDING_${expectedInput.id}_${frameNo}`);gate(packLayout(frame,spec),`PACK_LAYOUT_${expectedInput.id}_${frameNo}`);
        for(const expectedPass of spec.productionPack.subimages)gate(passSemantics(frame,expectedPass.pass,spec,expectedShot),`PASS_SEMANTICS_${expectedInput.id}_${frameNo}_${expectedPass.pass}`);
        gate(cryptoSemantics(frame,spec,expectedShot),`CRYPTOMATTE_${expectedInput.id}_${frameNo}`);
      }
      gate(canonicalJson(run?.milestones?.map(item=>item.name))===canonicalJson(expectedMilestones()),`MILESTONES_${expectedInput.id}`);
    }
    gate(shot?.pairComparison?.passes?.length===14,`PASS_PAIR_COUNT_${expectedShot.id}`);for(const item of shot?.pairComparison?.passes??[])gate(item.exact===true&&item.canonicalFloat32Sha256A===item.canonicalFloat32Sha256B,`PASS_PAIR_${expectedShot.id}_${item.frame}_${item.pass}`);
    gate(shot?.pairComparison?.manifests?.length===2&&(shot.pairComparison.manifests.every(item=>item.exact===true)),`CRYPTOMATTE_PAIR_${expectedShot.id}`);
    const temporal=shot?.temporalChecks??[];gate(temporal.length===2&&temporal.every(run=>expectedShot.requiredChangedPasses.every(pass=>run.passes.find(item=>item.pass===pass)?.changed===true)&&expectedShot.requiredUnchangedPasses.every(pass=>run.passes.find(item=>item.pass===pass)?.changed===false)),`TEMPORAL_ROLE_${expectedShot.id}`);
  }
  gate(evidence?.negativeControl?.id===spec.negativeControl.id&&evidence?.negativeControl?.reason===spec.negativeControl.expectedReason&&evidence?.negativeControl?.observedSha256!==spec.negativeControl.declaredSha256&&evidence?.negativeControl?.containerLaunchCount===0,'NEGATIVE_PRE_CONTAINER');
  const ops=evidence?.runtimeOperationsExecuted??[];gate(Array.isArray(ops)&&ops.filter(item=>item.startsWith('DOCKER_RUN_')).length===4&&ops.filter(item=>item.startsWith('HOST_EXR_ANALYSIS_')).length===8&&ops[0]==='DOCKER_IMAGE_INSPECT'&&ops.at(-1)==='DOCKER_RUNNING_CONTAINER_CHECK'&&!ops.some(item=>/BUILD|PULL|DOWNLOAD|MODEL|CODEX|VIDEO_API|FFMPEG/.test(item)),'OPERATION_BOUNDARY');gate(evidence?.cleanup?.experimentContainersRunningAfter===0,'CLEANUP_BOUNDARY');gate(Array.isArray(evidence?.errors)&&evidence.errors.length===0,'RUN_ERRORS');if(requireAttacks)gate(evidence?.attacks?.length===18&&evidence.attacks.every(item=>item.passed),'ATTACKS');gate(evidence?.evidenceHash===hashB47Evidence(evidence),'EVIDENCE_SELF_HASH');
  return {schemaVersion:'bfs.codexWorkerProductionPassPromotionAnalysis.v0.1',passed:failures.length===0,failures,decision:failures[0]??spec.acceptedVerdict};
}

export function runB47Attacks(evidence,spec){
  const shot=(v,id)=>v.shots.find(item=>item.id===id),run=(v,id)=>v.shots.flatMap(item=>item.runs).find(item=>item.id===id),frame=(v,id,no)=>run(v,id).inspections.find(item=>item.frame===no),pass=(v,id,no,name)=>frame(v,id,no).subimages.find(item=>item.pass===name);
  const defs=[
    ['A01_PARENT_SEQUENCE','PARENT_IDENTITY',v=>{v.parents.workerSequence.resultSha256='0'.repeat(64);}],['A02_SOURCE_IDENTITY','SOURCE_IDENTITY_TABLETOP-A1',v=>{run(v,'TABLETOP-A1').source.sha256='0'.repeat(64);}],['A03_IMAGE_IDENTITY','IMAGE_IDENTITY',v=>{v.image.id=`sha256:${'0'.repeat(64)}`;}],['A04_SECURITY_BOUNDARY','SECURITY_BOUNDARY',v=>{v.securityBoundary.network='bridge';}],['A05_RENDER_SAMPLES','RENDER_SETTINGS_TABLETOP-A1',v=>{run(v,'TABLETOP-A1').report.appliedSettings.samples=1;}],['A06_MISSING_SUBIMAGE','PACK_LAYOUT_TABLETOP-A1_21',v=>{frame(v,'TABLETOP-A1',21).subimages.pop();frame(v,'TABLETOP-A1',21).subimageCount=6;}],['A07_CHANNEL_LAYOUT','PACK_LAYOUT_TABLETOP-A1_21',v=>{pass(v,'TABLETOP-A1',21,'Normal').channels[0]='wrong';}],['A08_NON_FINITE','PASS_SEMANTICS_TABLETOP-A1_21_Combined',v=>{pass(v,'TABLETOP-A1',21,'Combined').finiteCount-=1;pass(v,'TABLETOP-A1',21,'Combined').nanCount=1;}],['A09_DEPTH_SENTINEL','PASS_SEMANTICS_TABLETOP-A1_21_Depth',v=>{pass(v,'TABLETOP-A1',21,'Depth').finiteMax=1e11;}],['A10_NORMAL_RANGE','PASS_SEMANTICS_TABLETOP-A1_21_Normal',v=>{pass(v,'TABLETOP-A1',21,'Normal').finiteMax=2;}],['A11_VECTOR_ZERO','PASS_SEMANTICS_TABLETOP-A1_21_Vector',v=>{pass(v,'TABLETOP-A1',21,'Vector').nonZeroFiniteCount=0;}],['A12_CRYPTO_HASH','CRYPTOMATTE_TABLETOP-A1_21',v=>{frame(v,'TABLETOP-A1',21).cryptomatte.hash='wrong';}],['A13_CRYPTO_OBJECT_MISSING','CRYPTOMATTE_TABLETOP-A1_21',v=>{delete frame(v,'TABLETOP-A1',21).cryptomatte.manifest.STAGE;}],['A14_PASS_PAIR_HASH','PASS_PAIR_TABLETOP_21_Combined',v=>{shot(v,'TABLETOP').pairComparison.passes.find(item=>item.frame===21&&item.pass==='Combined').exact=false;}],['A15_MOVING_UNCHANGED','TEMPORAL_ROLE_TABLETOP',v=>{for(const item of shot(v,'TABLETOP').temporalChecks)for(const p of item.passes)if(['Combined','Depth','Normal','Vector'].includes(p.pass))p.changed=false;}],['A16_STATIC_CHANGED','TEMPORAL_ROLE_INTERIOR',v=>{shot(v,'INTERIOR').temporalChecks[0].passes[0].changed=true;}],['A17_FIFTH_DOCKER_RUN','OPERATION_BOUNDARY',v=>{v.runtimeOperationsExecuted.splice(-1,0,'DOCKER_RUN_FIFTH');}],['A18_EVIDENCE_HASH','EVIDENCE_SELF_HASH',v=>{v.evidenceHash='0'.repeat(64);}]
  ];
  return defs.map(([id,expectedReason,mutate])=>{const value=structuredClone(evidence);try{mutate(value);const observedReason=analyzeB47Evidence(value,spec,{requireAttacks:false}).failures[0]??'NO_REJECTION';return {id,expectedReason,observedReason,passed:observedReason===expectedReason};}catch(error){return {id,expectedReason,observedReason:'ATTACK_FIXTURE_UNAVAILABLE',passed:false,error:error instanceof Error?error.message:String(error)};}});
}
