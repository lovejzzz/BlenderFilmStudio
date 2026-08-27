#!/usr/bin/env python3
"""Run the preregistered B52-D9.1 textured temporal-accumulation holdout."""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, subprocess, tempfile, time
from pathlib import Path

PREREGISTRATION_COMMIT="c14c3d430c2309fa50b6b7e12233de8cd82abc1b"
SPEC_SHA256="669077423e0101dd5600576d295c0b7a62189a30b18c1dd6ab18a3b5257cd28f"
TOOLS={"pythonProducer":"scripts/reference-b52-d9-1-temporal.py","nodeProducer":"scripts/reference-b52-d9-1-temporal.mjs","encoder":"scripts/encode-b52-d9-1-resolved.py","worker":"blender/render_b52_d9_1_temporal_passthrough.py","analyzer":"scripts/analyze-b52-d9-1-temporal-holdout.py","audit":"scripts/audit-b52-d9-1-temporal-holdout.py","runner":"scripts/run-b52-d9-1-temporal-holdout.py","tests":"tests/test_b52_d9_1_temporal_holdout_contract.py"}
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ch(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def blob(root,commit,uri):
 p=subprocess.run(["git","show",f"{commit}:{uri}"],cwd=root,capture_output=True); return hashlib.sha256(p.stdout).hexdigest() if p.returncode==0 else None
def observe(root,uri,expected,bytes_=None):
 p=Path(uri) if Path(uri).is_absolute() else root/uri; got=sha(p) if p.is_file() else None; size=p.stat().st_size if p.is_file() else None; return {"uri":str(uri),"expectedSha256":expected,"observedSha256":got,"expectedBytes":bytes_,"observedBytes":size,"match":got==expected and (bytes_ is None or size==bytes_)}
def launch(cmd,root,env,timeout=90):
 start=time.monotonic(); p=subprocess.Popen(cmd,cwd=root,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True); timed=False
 try: out,err=p.communicate(timeout=timeout)
 except subprocess.TimeoutExpired:
  timed=True; p.terminate()
  try: out,err=p.communicate(timeout=5)
  except subprocess.TimeoutExpired: p.kill(); out,err=p.communicate()
 return {"pid":p.pid,"exitCode":p.returncode,"timedOut":timed,"elapsedSeconds":round(time.monotonic()-start,6),"stdout":out,"stderr":err}
def clean_env(root,spec,tmp,blender=False):
 env={k:v for k,v in os.environ.items() if k=="PATH"}; env.update({"LANG":"C.UTF-8","LC_ALL":"C.UTF-8"})
 if blender:
  env.update({"OCIO":str((root/spec["runtime"]["ocio"]["uri"]).resolve()),"TMPDIR":str(tmp/"tmp"),"BLENDER_USER_CONFIG":str(tmp/"config"),"BLENDER_USER_SCRIPTS":str(tmp/"scripts")})
  for k in ("TMPDIR","BLENDER_USER_CONFIG","BLENDER_USER_SCRIPTS"): Path(env[k]).mkdir(parents=True,exist_ok=True)
 return env
def finish(cell,run): cell.mkdir(parents=True,exist_ok=True); (cell/"stdout.log").write_text(run["stdout"]); (cell/"stderr.log").write_text(run["stderr"])
def record(run,kind,fid,producer,report_uri,root,repeat=None):
 rp=root/report_uri; report=json.loads(rp.read_text()) if rp.is_file() else None; return {"kind":kind,"fixtureId":fid,"producer":producer,"repeat":repeat,"pid":run["pid"],"exitCode":run["exitCode"],"timedOut":run["timedOut"],"elapsedSeconds":run["elapsedSeconds"],"reportUri":report_uri,"report":report}
def identities(root,spec):
 parents=[observe(root,x["uri"],x["sha256"]) for x in spec["parents"].values()]; br=spec["runtime"]["blender"]; pr=spec["runtime"]["python"]; nr=spec["runtime"]["node"]; runtime={"blender":observe(root,br["executable"],br["sha256"],br["bytes"]),"python":observe(root,pr["executable"],pr["sha256"],pr["bytes"]),"node":observe(root,nr["executable"],nr["sha256"],nr["bytes"]),"ocio":observe(root,spec["runtime"]["ocio"]["uri"],spec["runtime"]["ocio"]["sha256"])}; checks={"parentIdentity":all(x["match"] for x in parents),"d9InvalidParentIdentity":all(x["match"] for x in parents if "d9" in x["uri"].lower() or "D9" in x["uri"]),"freshnessIdentity":bool(spec["freshness"]["allFormalOutputsAbsentAtPreregistration"]) and not (root/"experiments/layer-depth-temporal-accumulation-calibration-v0-1").exists(),"blenderRuntimeIdentity":runtime["blender"]["match"],"pythonRuntimeIdentity":runtime["python"]["match"],"nodeRuntimeIdentity":runtime["node"]["match"],"ocioIdentity":runtime["ocio"]["match"]}; return parents,runtime,checks
def main():
 p=argparse.ArgumentParser(); p.add_argument("--spec",type=Path,required=True); p.add_argument("--output-root",type=Path,required=True); p.add_argument("--tool-freeze-commit",required=True); p.add_argument("--preflight-only",action="store_true"); p.add_argument("--preflight-output",type=Path); a=p.parse_args(); root=a.spec.resolve().parent.parent; spec=json.loads(a.spec.read_text()); out=a.output_root.resolve()
 if sha(a.spec)!=SPEC_SHA256 or out!=(root/spec["formalOutputRoot"]).resolve() or out.exists() or a.preflight_only!=(a.preflight_output is not None): raise RuntimeError("spec/output")
 if subprocess.run(["git","merge-base","--is-ancestor",a.tool_freeze_commit,"HEAD"],cwd=root).returncode: raise RuntimeError("freeze ancestry")
 tools={}
 for name,uri in TOOLS.items():
  current=sha(root/uri) if (root/uri).is_file() else None; frozen=blob(root,a.tool_freeze_commit,uri)
  if current is None or current!=frozen: raise RuntimeError(f"tool mismatch {uri}")
  tools[name]={"uri":uri,"sha256":current,"freezeCommit":a.tool_freeze_commit}
 parents,runtimes,checks=identities(root,spec)
 if not all(checks.values()): raise RuntimeError(f"identity {checks}")
 free=shutil.disk_usage(root).free; disk={"availableBytes":free,"projectedWriteBytes":spec["projectedWriteBytes"],"projectedFreeAfterBytes":free-spec["projectedWriteBytes"],"reserveBytes":spec["diskReserveBytes"]}; disk["status"]="ACCEPTED" if disk["projectedFreeAfterBytes"]>=disk["reserveBytes"] else "BLOCKED"
 if disk["status"]!="ACCEPTED": raise RuntimeError(f"disk blocked {disk}")
 prereg={"commit":PREREGISTRATION_COMMIT,"specUri":"specs/layer-depth-temporal-accumulation-holdout.v0.1.json","specSha256":SPEC_SHA256}; spec_uri=str(a.spec.resolve().relative_to(root)); pr=spec["runtime"]["python"]; nr=spec["runtime"]["node"]; br=spec["runtime"]["blender"]
 if a.preflight_only:
  target=a.preflight_output.resolve()
  if target.exists() or root not in target.parents: raise RuntimeError("preflight target")
  with tempfile.TemporaryDirectory(prefix="bfs-b52-d9-1-preflight-") as td:
   t=Path(td); f=spec["fixtures"][0]; fid=f["id"]; probes=[]; encoded={}; arrays={}
   for producer,exe,key in (("python",pr["executable"],"pythonProducer"),("node",nr["executable"],"nodeProducer")):
    od=t/producer/"arrays"; rp=t/producer/"producer.json"; x=launch([exe,TOOLS[key],"--spec",spec_uri,"--fixture",fid,"--output-dir",str(od),"--report",str(rp)],root,clean_env(root,spec,t)); ex=t/producer/"source.exr"; er=t/producer/"encoder.json"; y=launch([pr["executable"],TOOLS["encoder"],"--spec",spec_uri,"--fixture",fid,"--producer",producer,"--input",str(od/"resolved.rgba32"),"--output",str(ex),"--report",str(er)],root,clean_env(root,spec,t)); probes.append({"producer":producer,"producerRun":x,"producerReport":json.loads(rp.read_text()) if rp.is_file() else None,"encoderRun":y,"encoderReport":json.loads(er.read_text()) if er.is_file() else None}); arrays[producer]=od; encoded[producer]=ex
   bp=t/"blender.json"; z=launch([br["executable"],*br["launchFlags"],"--python",TOOLS["worker"],"--","--spec",spec_uri,"--fixture",fid,"--producer","python","--repeat","1","--input",str(encoded["python"]),"--probe-only","--report",str(bp)],root,clean_env(root,spec,t,True)); brep=json.loads(bp.read_text()) if bp.is_file() else None; exact=all((arrays["python"]/name).read_bytes()==(arrays["node"]/name).read_bytes() for name in ("previous.rgba32","current.rgba32","previous-depth.f32","current-depth.f32","previous-layer.f32","current-layer.f32","motion.xy32","analytic-validity.u8","resolved.rgba32","clean-target.rgba32")); ok=all(q["producerRun"]["exitCode"]==0 and q["encoderRun"]["exitCode"]==0 and (q["encoderReport"] or {}).get("encodeDecodeExact") for q in probes) and exact and z["exitCode"]==0 and brep and brep["operationCounts"]["renderCalls"]==0
  if not ok: raise RuntimeError("component preflight")
  body={"schemaVersion":"bfs.layerDepthTemporalHoldoutFrozenToolPreflight.v0.1","experimentId":spec["experimentId"],"classification":"ZERO_FORMAL_OUTPUT_COMPONENT_AND_GRAPH_PREFLIGHT","preregistration":prereg,"toolFreezeCommit":a.tool_freeze_commit,"tools":tools,"parentObservations":parents,"runtimeObservations":runtimes,"checks":checks,"diskAdmission":disk,"formalOutputRoot":{"uri":spec["formalOutputRoot"],"absent":not out.exists()},"componentProbes":probes,"dualAllArraysExact":exact,"blenderProbe":{"pid":z["pid"],"report":brep},"formalOperationCounts":{"childProcesses":0,"blenderRenderCalls":0,"formalMeasurements":0}}; target.parent.mkdir(parents=True,exist_ok=True); target.write_text(json.dumps({**body,"preflightHash":ch(body)},indent=2,sort_keys=True,allow_nan=False)+"\n"); print(f"BFS_B52_D9_1_PREFLIGHT_OK tools=8 dualArrays={exact} outputAbsent={not out.exists()} sha256={sha(target)}"); return
 out.mkdir(parents=True); producers=[]; encoders=[]; blenders=[]
 for f in spec["fixtures"]:
  fid=f["id"]
  for producer,exe,key in (("python",pr["executable"],"pythonProducer"),("node",nr["executable"],"nodeProducer")):
   cell=out/"references"/producer/fid; od=cell/"arrays"; rp=cell/"report.json"; x=launch([exe,TOOLS[key],"--spec",spec_uri,"--fixture",fid,"--output-dir",str(od.relative_to(root)),"--report",str(rp.relative_to(root))],root,clean_env(root,spec,Path(tempfile.gettempdir()))); finish(cell,x); rec=record(x,"producer",fid,producer,str(rp.relative_to(root)),root); producers.append(rec)
   if x["exitCode"]!=0 or x["timedOut"] or rec["report"] is None: raise RuntimeError(f"producer {producer} {fid}")
   ecell=out/"encoded"/producer/fid; ex=ecell/"source.exr"; er=ecell/"report.json"; y=launch([pr["executable"],TOOLS["encoder"],"--spec",spec_uri,"--fixture",fid,"--producer",producer,"--input",str((od/"resolved.rgba32").relative_to(root)),"--output",str(ex.relative_to(root)),"--report",str(er.relative_to(root))],root,clean_env(root,spec,Path(tempfile.gettempdir()))); finish(ecell,y); erec=record(y,"encoder",fid,producer,str(er.relative_to(root)),root); encoders.append(erec)
   if y["exitCode"]!=0 or y["timedOut"] or erec["report"] is None: raise RuntimeError(f"encoder {producer} {fid}")
   for repeat in (1,2):
    bcell=out/"cells"/producer/f"{fid}_R{repeat}"; bx=bcell/"passthrough.exr"; bp=bcell/"report.json"
    with tempfile.TemporaryDirectory(prefix="bfs-b52-d9-1-") as td: z=launch([br["executable"],*br["launchFlags"],"--python",TOOLS["worker"],"--","--spec",spec_uri,"--fixture",fid,"--producer",producer,"--repeat",str(repeat),"--input",str(ex.relative_to(root)),"--output",str(bx.relative_to(root)),"--report",str(bp.relative_to(root))],root,clean_env(root,spec,Path(td),True))
    finish(bcell,z); brec=record(z,"blender",fid,producer,str(bp.relative_to(root)),root,repeat); blenders.append(brec)
    if z["exitCode"]!=0 or z["timedOut"] or brec["report"] is None: raise RuntimeError(f"blender {producer} {fid} R{repeat}")
 counts={"pythonAccumulatorProcesses":4,"nodeAccumulatorProcesses":4,"exrEncoderProcesses":8,"blenderProcesses":16,"totalChildProcesses":32,"blenderRenderCalls":16,"cyclesRayRenders":0,"sourceBlendFilesOpened":0,"generatedExternalExrAssetsOpened":16}; body={"schemaVersion":"bfs.layerDepthTemporalHoldoutRunReceipt.v0.1","experimentId":spec["experimentId"],"preregistration":prereg,"toolFreezeCommit":a.tool_freeze_commit,"tools":tools,"parentObservations":parents,"runtimeObservations":runtimes,"checks":checks,"diskAdmission":disk,"producerRuns":producers,"encoderRuns":encoders,"blenderRuns":blenders,"operationCounts":counts}; receipt={**body,"receiptHash":ch(body)}; receipt_path=out/"run.receipt.json"; receipt_path.write_text(json.dumps(receipt,indent=2,sort_keys=True,allow_nan=False)+"\n"); result=out/"results.json"; ar=launch([pr["executable"],TOOLS["analyzer"],"--spec",spec_uri,"--receipt",str(receipt_path.relative_to(root)),"--output",str(result.relative_to(root))],root,clean_env(root,spec,Path(tempfile.gettempdir())),180); (out/"analysis.stdout.log").write_text(ar["stdout"]); (out/"analysis.stderr.log").write_text(ar["stderr"]); print(ar["stdout"].strip())
 if ar["exitCode"]!=0 or not result.is_file(): raise RuntimeError(f"analysis {ar}")
 print(f"BFS_B52_D9_1_RUN_OK receipt={sha(receipt_path)} result={sha(result)}")
if __name__=="__main__": main()
