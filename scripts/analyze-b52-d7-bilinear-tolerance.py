#!/usr/bin/env python3
"""Analyze the fresh B52-D7 dual-reference Bilinear holdout."""
from __future__ import annotations
import argparse, copy, hashlib, json, math
from pathlib import Path
import numpy as np, OpenImageIO as oiio

SPEC_SHA256="f102a969cb59d92b0103c6807f20ca5436978504aafadd14a9b0353709ea0df5"
FIELDS={x:x for x in ["PARENT_IDENTITY","BLENDER_RUNTIME_IDENTITY","PYTHON_RUNTIME_IDENTITY","NODE_RUNTIME_IDENTITY","OCIO_IDENTITY","CASE_ROSTER","PROCESS_ROSTER","PID_UNIQUENESS","REPORT_SELF_HASH","SOURCE_FORMULA","DISPLACEMENT_FORMULA","RNA_CONTRACT","GRAPH_CONTRACT","OPERATION_COUNTS","OUTPUT_HASH","DECODED_REPEAT","DUAL_REFERENCE_EXACT","TOLERANCE_MAXIMUM","TOLERANCE_DISTRIBUTION","SIGNED_BIAS","TASK_SENSITIVITY","DIAGNOSTIC_TOTALITY","RESULT_SELF_HASH"]}
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def ch(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def ah(a):return hashlib.sha256(np.ascontiguousarray(a,dtype="<f4").tobytes()).hexdigest()
def report_ok(r):return isinstance(r,dict) and r.get("reportHash")==ch({k:v for k,v in r.items() if k!="reportHash"})
def run_report_bound(run):
 rep=run.get("report")
 if not isinstance(rep,dict) or rep.get("pid")!=run.get("pid") or rep.get("fixtureId")!=run.get("fixtureId"):return False
 kind=run.get("kind");counts=rep.get("operationCounts",{})
 if kind=="pythonReference":return counts.get("pythonReferenceProcesses")==1 and counts.get("nodeReferenceProcesses")==0 and counts.get("blenderProcesses")==0
 if kind=="nodeReference":return counts.get("pythonReferenceProcesses")==0 and counts.get("nodeReferenceProcesses")==1 and counts.get("blenderProcesses")==0
 return kind=="blender" and rep.get("repeat")==run.get("repeat") and counts.get("blenderProcesses")==1 and counts.get("renderCalls")==1 and counts.get("cyclesRayRenders")==0
def first_failure(e,s):
 for attack in s["attacks"]:
  if not e.get(attack,False):return attack
 return None
def attacks(s):
 out=[]
 for attack in s["attacks"]:
  e={x:True for x in FIELDS};e[attack]=False;o=first_failure(e,s);out.append({"attack":attack,"expectedFailure":attack,"observedFailure":o,"passed":o==attack})
 return out
def arrays(f):
 w,h=f["resolution"];s=np.zeros((h,w,4),np.float32);d=np.zeros((h,w,2),np.float32)
 for y in range(h):
  for x in range(w):
   if f["sourcePattern"]=="LOW_FREQUENCY_ALPHA_RAMP":s[y,x]=((x%64)/64,(y%64)/64,((x+3*y)%64)/64,((x+2*y)%17)/16)
   else:s[y,x]=((x^y)&1,((5*x+11*y)%16)/16,((13*x+7*y)%32)/32,((3*x+5*y)%9)/8)
   i=f["id"]
   if i=="LF_63X47_CLIP_Q1":v=(1/4,3/4)
   elif i=="LF_63X47_EXTEND_MIX":v=(-3/2,1/8)
   elif i=="LF_63X47_REPEAT_FIELD":v=(3/8 if x<31 else -5/8,1/4 if y%2==0 else -3/4)
   elif i=="HF_127X73_CLIP_MIX":v=(-3/4,3/2)
   elif i=="HF_127X73_EXTEND_MIX":v=(17/8,-3/8)
   else:v=((1/8,5/8,-7/8,3/8)[x%4],(-1/8,7/8)[y%2])
   d[y,x]=v
 return s,d
def read_exr(path):
 im=oiio.ImageInput.open(str(path));sp=im.spec();a=np.asarray(im.read_image(0,0,0,4,oiio.FLOAT),np.float32).reshape(sp.height,sp.width,4);im.close();return a
def write_png(path,a):
 o=oiio.ImageOutput.create(str(path));sp=oiio.ImageSpec(a.shape[1],a.shape[0],3,oiio.UINT8);o.open(str(path),sp);o.write_image(np.ascontiguousarray(a,np.uint8));o.close()
def read_png(path):
 im=oiio.ImageInput.open(str(path));sp=im.spec();a=np.asarray(im.read_image(0,0,0,3,oiio.UINT8),np.uint8).reshape(sp.height,sp.width,3);im.close();return a
def diag(root,canon,fid,kind,encoded,sources):
 slug=fid.lower().replace("_","-");p=root/f"{slug}-{kind}.png";j=root/f"{slug}-{kind}.json";write_png(p,encoded);decoded=read_png(p);identity=bool(np.array_equal(decoded,encoded));pb={"uri":f"{canon}/{p.name}","sha256":sha(p),"bytes":p.stat().st_size,"decodedSha256":hashlib.sha256(decoded.tobytes()).hexdigest()};body={"schemaVersion":"bfs.subpixelBilinearDiagnostic.v0.1","fixtureId":fid,"kind":kind,"sources":sources,"png":pb,"decodedIdentityMatch":identity};j.write_text(json.dumps(body,indent=2,sort_keys=True)+"\n");return {"fixtureId":fid,"kind":kind,"png":pb,"sidecar":{"uri":f"{canon}/{j.name}","sha256":sha(j),"bytes":j.stat().st_size},"identityMatch":identity}
def analyze(spec,receipt,output,receipt_sha,root):
 dr=output.parent/"diagnostics";dr.mkdir(parents=True,exist_ok=False);measurements=[];diags=[]
 py=receipt.get("pythonReferenceRuns",[]);node=receipt.get("nodeReferenceRuns",[]);bl=receipt.get("blenderRuns",[]);allruns=py+node+bl;expected={f["id"] for f in spec["fixtures"]};report_checks=[];output_checks=[];source_checks=[];field_checks=[];rna=[];graph=[];repeat=[];dual=[];maxg=[];dist=[];bias=[];sensitivity=[]
 for f in spec["fixtures"]:
  fid=f["id"];s,d=arrays(f);sh,dh=ah(s),ah(d);pr=next((x for x in py if x.get("fixtureId")==fid),{});nr=next((x for x in node if x.get("fixtureId")==fid),{});br=sorted([x for x in bl if x.get("fixtureId")==fid],key=lambda x:x.get("repeat",0));refs=[]
  for run in (pr,nr):
   rep=run.get("report");report_checks.append(report_ok(rep));b=rep.get("output") if rep else None;p=root/b["uri"] if b else None;ok=bool(p and p.is_file() and sha(p)==b["sha256"] and p.stat().st_size==b["bytes"]);output_checks.append(ok);refs.append(np.fromfile(p,dtype="<f4").reshape(f["resolution"][1],f["resolution"][0],4) if ok else np.full_like(s,np.nan));source_checks.append(bool(rep and rep["arrays"]["sourceFloat32Sha256"]==sh));field_checks.append(bool(rep and rep["arrays"]["displacementFloat32Sha256"]==dh))
  de=[];bindings=[]
  for run in br:
   rep=run.get("report");report_checks.append(report_ok(rep));b=rep.get("output") if rep else None;p=root/b["uri"] if b else None;ok=bool(p and p.is_file() and sha(p)==b["sha256"] and p.stat().st_size==b["bytes"]);output_checks.append(ok);a=read_exr(p) if ok else np.full_like(s,np.nan);de.append(a);source_checks.append(bool(rep and rep["arrays"]["sourceFloat32Sha256"]==sh));field_checks.append(bool(rep and rep["arrays"]["displacementFloat32Sha256"]==dh));rna.append(bool(rep and rep["rna"]["match"]));graph.append(bool(rep and rep["graph"]["match"]));bindings.append({"repeat":run.get("repeat"),"pid":run.get("pid"),"output":b,"decodedFloat32Sha256":ah(a) if np.isfinite(a).all() else None})
  dual_exact=len(refs)==2 and np.array_equal(refs[0],refs[1]);dual.append(dual_exact);reference=refs[0];re= len(de)==2 and np.array_equal(de[0],de[1]);repeat.append(re);obs=de[0] if de else np.full_like(s,np.nan);signed=obs.astype(np.float64)-reference.astype(np.float64);err=np.abs(signed);mx=float(np.max(err));rmse=float(np.sqrt(np.mean(err**2)));p99=float(np.quantile(err,0.99));means=[float(x) for x in signed.mean(axis=(0,1))];am=float(np.max(err[...,3]));pa=int(np.count_nonzero(np.max(err,axis=2)>spec["gates"]["maximumAbsoluteError"]));chg=np.max(np.abs(reference.astype(np.float64)-s.astype(np.float64)),axis=2);fraction=float(np.count_nonzero(chg>1/65536)/chg.size);mc=float(np.max(chg));maxpass=mx<=spec["gates"]["maximumAbsoluteError"] and am<=spec["gates"]["alphaMaximumAbsoluteError"] and pa==0;distpass=rmse<=spec["gates"]["rmse"] and p99<=spec["gates"]["p99AbsoluteScalarError"];biaspass=all(abs(x)<=spec["gates"]["absoluteMeanSignedErrorPerChannel"] for x in means);sense=fraction>=spec["gates"]["minimumChangedPixelFraction"] and mc>=spec["gates"]["minimumMaximumAbsoluteChange"];maxg.append(maxpass);dist.append(distpass);bias.append(biaspass);sensitivity.append(sense);sources={"pythonReferenceSha256":pr.get("report",{}).get("output",{}).get("sha256"),"nodeReferenceSha256":nr.get("report",{}).get("output",{}).get("sha256"),"blenderDecodedSha256":ah(obs) if np.isfinite(obs).all() else None};refpng=np.floor(np.clip(reference[...,:3],0,1)*255+0.5).astype(np.uint8);t=np.clip(np.max(err,axis=2)/(1/65536),0,1);errpng=np.floor(np.stack((t,t*t,np.zeros_like(t)),2)*255+0.5).astype(np.uint8);diags += [diag(dr,f"{spec['formalOutputRoot']}/diagnostics",fid,"reference",refpng,sources),diag(dr,f"{spec['formalOutputRoot']}/diagnostics",fid,"error",errpng,sources)]
  measurements.append({"fixtureId":fid,"resolution":f["resolution"],"dualReferenceExact":dual_exact,"referenceFloat32Sha256":ah(reference) if np.isfinite(reference).all() else None,"blenderRuns":bindings,"decodedRepeatExact":re,"maximumAbsoluteError":mx,"rmse":rmse,"p99AbsoluteScalarError":p99,"meanSignedErrorPerChannel":means,"alphaMaximumAbsoluteError":am,"pixelsAboveMaximum":pa,"changedPixelFraction":fraction,"maximumAbsoluteChange":mc,"maximumPass":maxpass,"distributionPass":distpass,"signedBiasPass":biaspass,"sensitivityPass":sense})
 counts={"pythonReferenceProcesses":len(py),"nodeReferenceProcesses":len(node),"blenderProcesses":len(bl),"totalChildProcesses":len(allruns),"blenderRenderCalls":sum((x.get("report") or {}).get("operationCounts",{}).get("renderCalls",0) for x in bl),"cyclesRayRenders":sum((x.get("report") or {}).get("operationCounts",{}).get("cyclesRayRenders",0) for x in bl)};expected_counts={k:spec["processMatrix"][k] for k in counts};pids=[x.get("pid") for x in allruns];e={"PARENT_IDENTITY":bool(receipt.get("checks",{}).get("parentIdentity")),"BLENDER_RUNTIME_IDENTITY":bool(receipt.get("checks",{}).get("blenderRuntimeIdentity")),"PYTHON_RUNTIME_IDENTITY":bool(receipt.get("checks",{}).get("pythonRuntimeIdentity")),"NODE_RUNTIME_IDENTITY":bool(receipt.get("checks",{}).get("nodeRuntimeIdentity")),"OCIO_IDENTITY":bool(receipt.get("checks",{}).get("ocioIdentity")),"CASE_ROSTER":{x.get("fixtureId") for x in py}==expected and {x.get("fixtureId") for x in node}==expected and {(x.get("fixtureId"),x.get("repeat")) for x in bl}=={(f,repeat) for f in expected for repeat in (1,2)},"PROCESS_ROSTER":len(allruns)==24 and all(x.get("exitCode")==0 and not x.get("timedOut") and run_report_bound(x) for x in allruns),"PID_UNIQUENESS":len(pids)==len(set(pids))==24,"REPORT_SELF_HASH":len(report_checks)==24 and all(report_checks),"SOURCE_FORMULA":len(source_checks)==24 and all(source_checks),"DISPLACEMENT_FORMULA":len(field_checks)==24 and all(field_checks),"RNA_CONTRACT":len(rna)==12 and all(rna),"GRAPH_CONTRACT":len(graph)==12 and all(graph),"OPERATION_COUNTS":counts==expected_counts,"OUTPUT_HASH":len(output_checks)==24 and all(output_checks),"DECODED_REPEAT":len(repeat)==6 and all(repeat),"DUAL_REFERENCE_EXACT":len(dual)==6 and all(dual),"TOLERANCE_MAXIMUM":len(maxg)==6 and all(maxg),"TOLERANCE_DISTRIBUTION":len(dist)==6 and all(dist),"SIGNED_BIAS":len(bias)==6 and all(bias),"TASK_SENSITIVITY":len(sensitivity)==6 and all(sensitivity),"DIAGNOSTIC_TOTALITY":len(diags)==12 and all(x["identityMatch"] for x in diags),"RESULT_SELF_HASH":True};ats=attacks(spec);base=first_failure(e,spec);verdict=spec["decision"]["passVerdict"] if base is None else spec["decision"]["failVerdict"];core={"evidence":e,"measurements":measurements,"operationCounts":counts,"verdict":verdict,"baseFailure":base};body={"schemaVersion":"bfs.subpixelBilinearToleranceHoldoutResult.v0.1","experimentId":spec["experimentId"],"preregistration":receipt["preregistration"],"toolFreezeCommit":receipt["toolFreezeCommit"],"receipt":{"uri":f"{spec['formalOutputRoot']}/run.receipt.json","sha256":receipt_sha},"evidence":e,"measurements":measurements,"diagnostics":diags,"operationCounts":counts,"attacks":ats,"attacksPassed":sum(x["passed"] for x in ats),"evidenceCoreHash":ch(core),"verdict":verdict,"baseFailure":base,"nonClaims":spec["decision"]["nonClaims"]};return {**body,"resultHash":ch(body)}
def main():
 p=argparse.ArgumentParser();p.add_argument("--spec",type=Path,required=True);p.add_argument("--receipt",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args();spec=json.loads(a.spec.read_text());receipt=json.loads(a.receipt.read_text());
 if sha(a.spec)!=SPEC_SHA256 or a.output.exists() or (a.output.parent/"diagnostics").exists():raise RuntimeError("identity/overwrite")
 result=analyze(spec,receipt,a.output,sha(a.receipt),a.spec.resolve().parent.parent);a.output.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n");print(f"BFS_B52_D7_ANALYSIS {result['verdict']} baseFailure={result['baseFailure']} attacks={result['attacksPassed']}/{len(spec['attacks'])}")
if __name__=="__main__":main()
