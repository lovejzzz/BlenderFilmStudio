#!/usr/bin/env python3
"""Independent evidence analyzer for the B52-D9.1 temporal-accumulation holdout."""
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
import numpy as np, OpenImageIO as oiio

SPEC_SHA256="669077423e0101dd5600576d295c0b7a62189a30b18c1dd6ab18a3b5257cd28f"
FILES={"previousRgba":"previous.rgba32","currentRgba":"current.rgba32","previousDepth":"previous-depth.f32","currentDepth":"current-depth.f32","previousLayer":"previous-layer.f32","currentLayer":"current-layer.f32","motion":"motion.xy32","analyticValidity":"analytic-validity.u8","resolvedRgba":"resolved.rgba32","cleanTarget":"clean-target.rgba32"}
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ch(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def ah(a): return hashlib.sha256(np.ascontiguousarray(a,dtype="<f4").tobytes()).hexdigest()
def resolved(root,uri):
 p=Path(uri); return p if p.is_absolute() else root/p
def report_ok(r): return isinstance(r,dict) and r.get("reportHash")==ch({k:v for k,v in r.items() if k!="reportHash"})
def inside(x,y,b): return b[0]<=x<b[2] and b[1]<=y<b[3]
def texture(spec,name,x,y,offset):
 lx=x-offset[0]; ly=y-offset[1]; t=spec["surfaceTextures"][name]
 if name=="BACKGROUND_CHECKER": bit=(math.floor(lx/2)+math.floor(ly/3))%2
 elif name=="FOREGROUND_STRIPE": bit=(math.floor(lx/2)+math.floor(ly/2))%2
 elif name=="OLD_PATCH": bit=math.floor(lx/2)%2
 elif name=="NEW_PATCH": bit=math.floor(ly/2)%2
 else: raise RuntimeError("texture")
 return t[f"b{bit}"]
def scene(spec,f,frame):
 w,h=f["resolution"]; rgba=np.empty((h,w,4),np.float32); depth=np.empty((h,w),np.float32); layer=np.empty((h,w),np.float32); motion=np.empty((h,w,2),np.float32)
 for y in range(h):
  for x in range(w):
   if f["id"].startswith("TEXTURED_FOREGROUND"):
    fg=inside(x,y,f[f"{frame}ForegroundBox"]); s=f["foreground"] if fg else f["background"]; off=f["foregroundLocalOffset"][frame] if fg else f["backgroundLocalOffset"][frame]; mv=f["foregroundMotion"] if fg else f["backgroundMotion"]
   elif f["id"].startswith("TEXTURED_CAMERA"):
    fg=inside(x,y,f[f"{frame}ForegroundBox"]); s=f["foreground"] if fg else f["background"]; off=f["allLayerLocalOffset"][frame]; mv=f["allLayerMotion"]
   elif f["id"].startswith("TEXTURED_DEPTH"):
    patch=inside(x,y,f[f"{frame}PatchBox"]); s=f[f"{frame}Patch"] if patch else f["background"]; off=s["localOffset"]; mv=f["patchMotion"] if patch else f["backgroundMotion"]
   else:
    fg=inside(x,y,f["foregroundBox"]); s=f["foreground"] if fg else f["background"]; off=[0,0]; mv=f["motion"]
   rgba[y,x]=texture(spec,s["texture"],x,y,off); depth[y,x]=s["depth"]; layer[y,x]=s["layerId"]; motion[y,x]=mv
 return rgba,depth,layer,motion
def truth(spec,f):
 clean_previous,pd,pl,_=scene(spec,f,"previous"); clean,cd,cl,mv=scene(spec,f,"current"); h,w=cd.shape; valid=np.zeros((h,w),np.uint8); pr=clean_previous.copy(); cr=clean.copy()
 for y in range(h):
  for x in range(w):
   s=-1.0 if ((x+3*y)%2) else 1.0; pr[y,x]=np.asarray(clean_previous[y,x]+np.asarray([s/16,-s/32,s/64,0],np.float32),np.float32)
 for y in range(h):
  for x in range(w):
   dx,dy=(int(mv[y,x,0]),int(mv[y,x,1])); qx,qy=x-dx,y+dy; ok=0<=qx<w and 0<=qy<h
   if ok: ok=pl[qy,qx]==cl[y,x] and abs(float(pd[qy,qx])-float(cd[y,x]))<=max(1.0,float(cd[y,x]))/1024 and pr[qy,qx,3]>0 and cr[y,x,3]>0
   if ok:
    valid[y,x]=1; s=-1.0 if ((qx+3*qy)%2) else 1.0; cr[y,x]=np.asarray(clean[y,x]-np.asarray([s/16,-s/32,s/64,0],np.float32),np.float32)
 resolved_rgba=accumulate({"previousRgba":pr,"currentRgba":cr,"previousDepth":pd,"currentDepth":cd,"previousLayer":pl,"currentLayer":cl,"motion":mv})
 return {"previousRgba":pr,"currentRgba":cr,"previousDepth":pd,"currentDepth":cd,"previousLayer":pl,"currentLayer":cl,"motion":mv,"analyticValidity":valid,"resolvedRgba":resolved_rgba,"cleanTarget":clean}
def accumulate(arr,sign=1,naive=False):
 pr,cr,pd,cd,pl,cl,mv=(arr[k] for k in ("previousRgba","currentRgba","previousDepth","currentDepth","previousLayer","currentLayer","motion")); h,w=cd.shape; out=np.zeros_like(cr)
 for y in range(h):
  for x in range(w):
   qx=x-sign*int(mv[y,x,0]); qy=y+sign*int(mv[y,x,1]); ok=0<=qx<w and 0<=qy<h
   if ok and not naive: ok=pl[qy,qx]==cl[y,x] and abs(float(pd[qy,qx])-float(cd[y,x]))<=max(1.0,float(cd[y,x]))/1024 and pr[qy,qx,3]>0 and cr[y,x,3]>0
   out[y,x]=np.asarray(np.float32(.5)*cr[y,x]+np.float32(.5)*pr[qy,qx],np.float32) if ok else cr[y,x]
 return out
def metric(a,b):
 d=np.abs(a-b); return {"wrongPixels":int(np.any(d!=0,axis=2).sum()),"maximumAbsoluteError":float(d.max())}
def read_array(p,name,w,h):
 if name=="analyticValidity": return np.fromfile(p,dtype=np.uint8).reshape(h,w)
 shape=(h,w,4) if name.endswith("Rgba") or name=="cleanTarget" else ((h,w,2) if name=="motion" else (h,w)); return np.fromfile(p,dtype="<f4").reshape(shape)
def read_exr(path):
 i=oiio.ImageInput.open(str(path))
 if i is None: raise RuntimeError(oiio.geterror() or f"cannot read {path}")
 s=i.spec(); a=np.asarray(i.read_image(0,0,0,4,oiio.FLOAT),np.float32).reshape(s.height,s.width,4); layout={"width":s.width,"height":s.height,"channels":list(s.channelnames),"format":str(s.format)}; i.close(); return np.ascontiguousarray(a,dtype="<f4"),layout
def write_png(path,a):
 o=oiio.ImageOutput.create(str(path)); s=oiio.ImageSpec(a.shape[1],a.shape[0],3,oiio.UINT8)
 if o is None or not o.open(str(path),s) or not o.write_image(np.ascontiguousarray(a,np.uint8)): raise RuntimeError(oiio.geterror() or "png")
 o.close()
def read_png(path):
 i=oiio.ImageInput.open(str(path)); s=i.spec(); a=np.asarray(i.read_image(0,0,0,3,oiio.UINT8),np.uint8).reshape(s.height,s.width,3); i.close(); return a
def diagnostic(folder,canon,fid,kind,pixels,sources):
 slug=fid.lower().replace("_","-"); p=folder/f"{slug}-{kind}.png"; j=folder/f"{slug}-{kind}.json"; write_png(p,pixels); decoded=read_png(p); pb={"uri":f"{canon}/{p.name}","sha256":sha(p),"bytes":p.stat().st_size,"decodedSha256":hashlib.sha256(decoded.tobytes()).hexdigest()}; body={"schemaVersion":"bfs.layerDepthTemporalHoldoutDiagnostic.v0.1","fixtureId":fid,"kind":kind,"sources":sources,"png":pb,"decodedIdentityMatch":bool(np.array_equal(decoded,pixels))}; j.write_text(json.dumps(body,indent=2,sort_keys=True,allow_nan=False)+"\n"); return {"fixtureId":fid,"kind":kind,"png":pb,"sidecar":{"uri":f"{canon}/{j.name}","sha256":sha(j),"bytes":j.stat().st_size},"identityMatch":body["decodedIdentityMatch"]}
def bound(run,kind):
 r=run.get("report") or {}; c=r.get("operationCounts",{})
 if not report_ok(r) or r.get("pid")!=run.get("pid") or r.get("fixtureId")!=run.get("fixtureId") or r.get("producer")!=run.get("producer"): return False
 if kind=="producer": return c.get("pythonAccumulatorProcesses")==int(run["producer"]=="python") and c.get("nodeAccumulatorProcesses")==int(run["producer"]=="node")
 if kind=="encoder": return c.get("exrEncoderProcesses")==1
 return r.get("repeat")==run.get("repeat") and c.get("blenderProcesses")==1 and c.get("renderCalls")==1 and c.get("cyclesRayRenders")==0
def first_failure(e,spec):
 for name in spec["attacks"]:
  if not e.get(name,False): return name
 return None
def synthetic_attacks(spec):
 out=[]
 for name in spec["attacks"]:
  e={k:True for k in spec["attacks"]}; e[name]=False; got=first_failure(e,spec); out.append({"attack":name,"expectedFailure":name,"observedFailure":got,"passed":got==name})
 return out
def analyze(spec,receipt,output,receipt_sha,root):
 dr=output.parent/"diagnostics"; dr.mkdir(parents=True,exist_ok=False); prods=receipt.get("producerRuns",[]); encs=receipt.get("encoderRuns",[]); bls=receipt.get("blenderRuns",[]); allruns=prods+encs+bls; measurements=[]; diagnostics=[]; pb=[]; eb=[]; bb=[]; output_hash=[]; layouts=[]; enc_exact=[]; blender_exact=[]; graph_exact=[]; repeat_exact=[]; convergence=[]; array_identity=[]; dual_exact=[]; validity_exact=[]; resolved_exact=[]; invalid_exact=[]; valid_exact=[]; naive_sensitive=[]; wrong_sensitive=[]; static_ok=[]
 naive_set=set(spec["sensitivityControls"]["naiveUnconditionalHistory"]["applicableFixtures"]); wrong_set=set(spec["sensitivityControls"]["wrongMotionSign"]["applicableFixtures"])
 for f in spec["fixtures"]:
  fid=f["id"]; w,h=f["resolution"]; expected=truth(spec,f); refs={}; producer_details={}
  for producer in ("python","node"):
   run=next((x for x in prods if x.get("fixtureId")==fid and x.get("producer")==producer),{}); pb.append(bound(run,"producer")); rep=run.get("report") or {}; arrays={}; checks={}
   for name in FILES:
    rec=(rep.get("arrays") or {}).get(name,{ }); path=resolved(root,rec.get("uri","")); good=path.is_file() and sha(path)==rec.get("sha256") and path.stat().st_size==rec.get("bytes"); output_hash.append(good); arrays[name]=read_array(path,name,w,h) if good else np.asarray([]); checks[name]=good and np.array_equal(arrays[name],expected[name])
   array_identity.append(all(checks.values())); refs[producer]=arrays; producer_details[producer]={"allArraysGroundTruthExact":all(checks.values()),"arrayChecks":checks,"metrics":rep.get("metrics")}
  dual=all(np.array_equal(refs["python"][k],refs["node"][k]) for k in FILES); dual_exact.append(dual); val=refs["python"]["analyticValidity"]; resolved_rgba=refs["python"]["resolvedRgba"]; current=refs["python"]["currentRgba"]; target=expected["cleanTarget"]; validity_exact.append(np.array_equal(val,expected["analyticValidity"])); resolved_exact.append(np.array_equal(resolved_rgba,target)); invalid_exact.append(bool(np.array_equal(resolved_rgba[val==0],current[val==0]))); valid_exact.append(bool(np.array_equal(resolved_rgba[val==1],target[val==1]))); naive=accumulate(expected,naive=True); wrong=accumulate(expected,sign=-1); nm=metric(naive,target); wm=metric(wrong,target)
  if fid in naive_set: naive_sensitive.append(nm["wrongPixels"]>=spec["sensitivityControls"]["naiveUnconditionalHistory"]["minimumWrongPixels"] and nm["maximumAbsoluteError"]>=spec["sensitivityControls"]["naiveUnconditionalHistory"]["minimumMaximumAbsoluteError"])
  if fid in wrong_set: wrong_sensitive.append(wm["wrongPixels"]>=spec["sensitivityControls"]["wrongMotionSign"]["minimumWrongPixels"] and wm["maximumAbsoluteError"]>=spec["sensitivityControls"]["wrongMotionSign"]["minimumMaximumAbsoluteError"])
  if fid=="TEXTURED_STATIC_CONTROL_71X43": static_ok.append(bool(val.all() and np.array_equal(resolved_rgba,target)))
  blender_by_producer={}
  for producer in ("python","node"):
   er=next((x for x in encs if x.get("fixtureId")==fid and x.get("producer")==producer),{}); eb.append(bound(er,"encoder")); erep=er.get("report") or {}; eo=erep.get("output") or {}; ep=resolved(root,eo.get("uri","")); ok=ep.is_file() and sha(ep)==eo.get("sha256") and ep.stat().st_size==eo.get("bytes"); output_hash.append(ok); ea,layout=read_exr(ep) if ok else (np.asarray([]),{}); layouts.append(layout=={"width":w,"height":h,"channels":["R","G","B","A"],"format":"float"}); ex=ok and bool(erep.get("encodeDecodeExact")) and np.array_equal(ea,refs[producer]["resolvedRgba"]) and eo.get("decodedCanonicalFloat32Sha256")==ah(ea); enc_exact.append(ex); runs=[]
   for repeat in (1,2):
    br=next((x for x in bls if x.get("fixtureId")==fid and x.get("producer")==producer and x.get("repeat")==repeat),{}); bb.append(bound(br,"blender")); brep=br.get("report") or {}; bo=brep.get("output") or {}; bp_=resolved(root,bo.get("uri","")); bok=bp_.is_file() and sha(bp_)==bo.get("sha256") and bp_.stat().st_size==bo.get("bytes"); output_hash.append(bok); ba,blayout=read_exr(bp_) if bok else (np.asarray([]),{}); layouts.append(blayout=={"width":w,"height":h,"channels":["R","G","B","A"],"format":"float"}); exact=bok and np.array_equal(ba,target); blender_exact.append(exact); graph_exact.append(bool((brep.get("graph") or {}).get("match") and (brep.get("rna") or {}).get("match"))); runs.append({"repeat":repeat,"pid":br.get("pid"),"decodedCanonicalFloat32Sha256":ah(ba) if ba.size else None,"exact":exact,"output":bo})
   re=len(runs)==2 and runs[0]["decodedCanonicalFloat32Sha256"]==runs[1]["decodedCanonicalFloat32Sha256"]; repeat_exact.append(re); blender_by_producer[producer]={"encoderExact":ex,"runs":runs,"repeatExact":re}
  conv=blender_by_producer["python"]["runs"][0]["decodedCanonicalFloat32Sha256"]==blender_by_producer["node"]["runs"][0]["decodedCanonicalFloat32Sha256"]; convergence.append(conv); maxerr=max(float(np.max(np.abs(target-refs[p]["resolvedRgba"]))) for p in ("python","node")); changed=sum(int(np.count_nonzero(target!=refs[p]["resolvedRgba"])) for p in ("python","node")); sources={"resolvedFloat32Sha256":ah(target),"pythonResolvedSha256":ah(refs["python"]["resolvedRgba"]),"nodeResolvedSha256":ah(refs["node"]["resolvedRgba"])}; rgb=lambda a:np.floor(np.clip((a[...,:3]+.5)/2.5,0,1)*255+.5).astype(np.uint8); mask=np.repeat((val[...,None]*255).astype(np.uint8),3,2); err=lambda a:np.floor(np.clip(np.max(np.abs(a[...,:3]-target[...,:3]),axis=2)[...,None]/1.25,0,1)*255+.5).astype(np.uint8).repeat(3,2); diagnostics += [diagnostic(dr,f"{spec['formalOutputRoot']}/diagnostics",fid,"current",rgb(current),sources),diagnostic(dr,f"{spec['formalOutputRoot']}/diagnostics",fid,"history-validity",mask,sources),diagnostic(dr,f"{spec['formalOutputRoot']}/diagnostics",fid,"resolved",rgb(resolved_rgba),sources),diagnostic(dr,f"{spec['formalOutputRoot']}/diagnostics",fid,"naive-history-error",err(naive),sources),diagnostic(dr,f"{spec['formalOutputRoot']}/diagnostics",fid,"wrong-sign-error",err(wrong),sources)]; measurements.append({"fixtureId":fid,"resolution":f["resolution"],"producerPaths":producer_details,"pythonNodeAllArraysExact":dual,"validPixels":int(val.sum()),"invalidPixels":int(val.size-val.sum()),"naiveControl":nm,"wrongSignControl":wm,"allEncoderDecodedExact":all(enc_exact[-2:]),"allBlenderDecodedExact":all(blender_exact[-4:]),"allBlenderRepeatsExact":all(repeat_exact[-2:]),"producerPathConvergence":conv,"maximumAbsoluteResolvedError":maxerr,"changedResolvedScalars":changed,"blender":blender_by_producer})
 counts={"pythonAccumulatorProcesses":sum(x.get("producer")=="python" for x in prods),"nodeAccumulatorProcesses":sum(x.get("producer")=="node" for x in prods),"exrEncoderProcesses":len(encs),"blenderProcesses":len(bls),"totalChildProcesses":len(allruns),"blenderRenderCalls":sum(((x.get("report") or {}).get("operationCounts") or {}).get("renderCalls",0) for x in bls),"cyclesRayRenders":sum(((x.get("report") or {}).get("operationCounts") or {}).get("cyclesRayRenders",0) for x in bls),"sourceBlendFilesOpened":sum(((x.get("report") or {}).get("operationCounts") or {}).get("sourceBlendFilesOpened",0) for x in bls),"generatedExternalExrAssetsOpened":sum(((x.get("report") or {}).get("operationCounts") or {}).get("generatedExternalExrAssetsOpened",0) for x in bls)}; expected_counts={k:spec["processMatrix"][k] for k in counts}; pids=[x.get("pid") for x in allruns]; fixtures={f["id"] for f in spec["fixtures"]}; pf={(p,f) for p in ("python","node") for f in fixtures}; attacks={"PARENT_IDENTITY":bool((receipt.get("checks") or {}).get("parentIdentity")),"D9_INVALID_PARENT_IDENTITY":bool((receipt.get("checks") or {}).get("d9InvalidParentIdentity")),"FRESHNESS_IDENTITY":bool((receipt.get("checks") or {}).get("freshnessIdentity")),"PREREGISTRATION_IDENTITY":receipt.get("preregistration")=={"commit":"c14c3d430c2309fa50b6b7e12233de8cd82abc1b","specUri":"specs/layer-depth-temporal-accumulation-holdout.v0.1.json","specSha256":SPEC_SHA256},"TOOL_FREEZE_IDENTITY":len(receipt.get("tools",{}))==8 and all(x.get("freezeCommit")==receipt.get("toolFreezeCommit") for x in receipt.get("tools",{}).values()),"RUNTIME_IDENTITY":all((receipt.get("checks") or {}).get(k) for k in ("blenderRuntimeIdentity","pythonRuntimeIdentity","nodeRuntimeIdentity","ocioIdentity")),"PROCESS_ROSTER":len(allruns)==32 and all(x.get("exitCode")==0 and not x.get("timedOut") for x in allruns) and counts==expected_counts,"PID_UNIQUENESS":len(pids)==len(set(pids))==32,"FIXTURE_ROSTER":{(x.get("producer"),x.get("fixtureId")) for x in prods}==pf and {(x.get("producer"),x.get("fixtureId")) for x in encs}==pf and {(x.get("producer"),x.get("fixtureId"),x.get("repeat")) for x in bls}=={(p,f,r) for p,f in pf for r in (1,2)},"PRODUCER_REPORT_BINDING":len(pb)==8 and all(pb),"INPUT_ARRAY_IDENTITY":len(array_identity)==8 and all(array_identity),"DUAL_ALL_ARRAYS_EXACT":len(dual_exact)==4 and all(dual_exact),"ANALYTIC_VALIDITY_GROUND_TRUTH":len(validity_exact)==4 and all(validity_exact),"ANALYTIC_RESOLVED_GROUND_TRUTH":len(resolved_exact)==4 and all(resolved_exact),"INVALID_PIXEL_CURRENT_IDENTITY":len(invalid_exact)==4 and all(invalid_exact),"VALID_PIXEL_TARGET_IDENTITY":len(valid_exact)==4 and all(valid_exact),"NAIVE_CONTROL_SENSITIVITY":len(naive_sensitive)==2 and all(naive_sensitive),"WRONG_SIGN_CONTROL_SENSITIVITY":len(wrong_sensitive)==3 and all(wrong_sensitive),"STATIC_NEGATIVE_CONTROL":len(static_ok)==1 and all(static_ok),"ENCODER_REPORT_BINDING":len(eb)==8 and all(eb),"EXR_LAYOUT":len(layouts)==24 and all(layouts),"EXR_ENCODE_DECODE_IDENTITY":len(enc_exact)==8 and all(enc_exact),"BLENDER_REPORT_BINDING":len(bb)==16 and all(bb),"BLENDER_GRAPH_RNA":len(graph_exact)==16 and all(graph_exact),"BLENDER_OUTPUT_HASH":len(output_hash)==104 and all(output_hash),"BLENDER_DECODED_IDENTITY":len(blender_exact)==16 and all(blender_exact),"BLENDER_REPEAT_IDENTITY":len(repeat_exact)==8 and all(repeat_exact),"PRODUCER_PATH_CONVERGENCE":len(convergence)==4 and all(convergence),"DIAGNOSTIC_TOTALITY":len(diagnostics)==20 and all(x["identityMatch"] for x in diagnostics),"RESULT_SELF_HASH":True}; ats=synthetic_attacks(spec); base=first_failure(attacks,spec); verdict=spec["decisionRule"]["passVerdict"] if base is None else spec["decisionRule"]["failVerdict"]; core={"evidence":attacks,"measurements":measurements,"operationCounts":counts,"verdict":verdict,"baseFailure":base}; body={"schemaVersion":"bfs.layerDepthTemporalHoldoutResult.v0.1","experimentId":spec["experimentId"],"preregistration":receipt["preregistration"],"toolFreezeCommit":receipt["toolFreezeCommit"],"receipt":{"uri":f"{spec['formalOutputRoot']}/run.receipt.json","sha256":receipt_sha},"evidence":attacks,"measurements":measurements,"diagnostics":diagnostics,"operationCounts":counts,"attacks":ats,"attacksPassed":sum(x["passed"] for x in ats),"evidenceCoreHash":ch(core),"verdict":verdict,"baseFailure":base,"nonClaims":spec["nonClaims"]}; return {**body,"resultHash":ch(body)}
def main():
 p=argparse.ArgumentParser(); p.add_argument("--spec",type=Path,required=True); p.add_argument("--receipt",type=Path,required=True); p.add_argument("--output",type=Path,required=True); a=p.parse_args(); spec=json.loads(a.spec.read_text()); receipt=json.loads(a.receipt.read_text())
 if sha(a.spec)!=SPEC_SHA256 or a.output.exists() or (a.output.parent/"diagnostics").exists(): raise RuntimeError("identity/overwrite")
 result=analyze(spec,receipt,a.output,sha(a.receipt),a.spec.resolve().parent.parent); a.output.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n"); print(f"BFS_B52_D9_1_ANALYSIS {result['verdict']} baseFailure={result['baseFailure']} attacks={result['attacksPassed']}/{len(spec['attacks'])}")
if __name__=="__main__": main()
