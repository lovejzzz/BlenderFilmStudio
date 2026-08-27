#!/usr/bin/env python3
"""Run B52-D8 external canonical warp bridge."""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path
PREREGISTRATION_COMMIT="099036577028d18f298af82987400d143df9d012";SPEC_SHA256="94a58f4e3c36b1828cb7e1bc4d5646cd577fac1afd411685235185590644a6a5"
TOOLS={"pythonProducer":"scripts/reference-b52-d8-external-warp.py","nodeProducer":"scripts/reference-b52-d8-external-warp.mjs","encoder":"scripts/encode-b52-d8-external-warp.py","worker":"blender/render_b52_d8_external_warp_passthrough.py","analyzer":"scripts/analyze-b52-d8-external-warp-bridge.py","audit":"scripts/audit-b52-d8-external-warp-bridge.py","runner":"scripts/run-b52-d8-external-warp-bridge.py","tests":"tests/test_b52_d8_external_warp_bridge_contract.py"}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ch(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def blob(root,commit,uri):
 p=subprocess.run(["git","show",f"{commit}:{uri}"],cwd=root,capture_output=True);return hashlib.sha256(p.stdout).hexdigest() if p.returncode==0 else None
def observe(root,uri,expected,bytes_=None):
 p=Path(uri) if Path(uri).is_absolute() else root/uri;o=sha(p) if p.is_file() else None;b=p.stat().st_size if p.is_file() else None;return {"uri":str(uri),"expectedSha256":expected,"observedSha256":o,"expectedBytes":bytes_,"observedBytes":b,"match":o==expected and (bytes_ is None or b==bytes_)}
def launch(cmd,root,env,timeout=60):
 start=time.monotonic();p=subprocess.Popen(cmd,cwd=root,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);timed=False
 try:out,err=p.communicate(timeout=timeout)
 except subprocess.TimeoutExpired:
  timed=True;p.terminate()
  try:out,err=p.communicate(timeout=5)
  except subprocess.TimeoutExpired:p.kill();out,err=p.communicate()
 return {"pid":p.pid,"exitCode":p.returncode,"timedOut":timed,"elapsedSeconds":round(time.monotonic()-start,6),"stdout":out,"stderr":err}
def clean_env(root,spec,tmp,blender=False):
 e={k:v for k,v in os.environ.items() if k=="PATH"};e.update({"LANG":"C.UTF-8","LC_ALL":"C.UTF-8"})
 if blender:
  e.update({"OCIO":str((root/spec["runtime"]["ocio"]["uri"]).resolve()),"TMPDIR":str(tmp/"tmp"),"BLENDER_USER_CONFIG":str(tmp/"config"),"BLENDER_USER_SCRIPTS":str(tmp/"scripts")})
  for k in ("TMPDIR","BLENDER_USER_CONFIG","BLENDER_USER_SCRIPTS"):Path(e[k]).mkdir(parents=True,exist_ok=True)
 return e
def finish(cell,run):cell.mkdir(parents=True,exist_ok=True);(cell/"stdout.log").write_text(run["stdout"]);(cell/"stderr.log").write_text(run["stderr"])
def record(run,kind,fid,producer,report_uri,root,repeat=None):
 rp=root/report_uri;r=json.loads(rp.read_text()) if rp.is_file() else None;return {"kind":kind,"fixtureId":fid,"producer":producer,"repeat":repeat,"pid":run["pid"],"exitCode":run["exitCode"],"timedOut":run["timedOut"],"elapsedSeconds":run["elapsedSeconds"],"reportUri":report_uri,"report":r}
def main():
 p=argparse.ArgumentParser();p.add_argument("--spec",type=Path,required=True);p.add_argument("--output-root",type=Path,required=True);p.add_argument("--tool-freeze-commit",required=True);p.add_argument("--preflight-only",action="store_true");p.add_argument("--preflight-output",type=Path);a=p.parse_args();root=a.spec.resolve().parent.parent;spec=json.loads(a.spec.read_text());out=a.output_root.resolve()
 if sha(a.spec)!=SPEC_SHA256 or out!=(root/spec["formalOutputRoot"]).resolve() or out.exists() or a.preflight_only!=(a.preflight_output is not None):raise RuntimeError("spec/output mismatch")
 if subprocess.run(["git","merge-base","--is-ancestor",a.tool_freeze_commit,"HEAD"],cwd=root).returncode:raise RuntimeError("freeze is not ancestor")
 tools={}
 for name,uri in TOOLS.items():
  current=sha(root/uri) if (root/uri).is_file() else None;frozen=blob(root,a.tool_freeze_commit,uri)
  if current is None or current!=frozen:raise RuntimeError(f"tool mismatch {uri}")
  tools[name]={"uri":uri,"sha256":current,"freezeCommit":a.tool_freeze_commit}
 parents=[observe(root,x["uri"],x["sha256"]) for x in spec["parents"].values()];br=spec["runtime"]["blender"];pr=spec["runtime"]["python"];nr=spec["runtime"]["node"];bo=observe(root,br["executable"],br["sha256"],br["bytes"]);po=observe(root,pr["executable"],pr["sha256"],pr["bytes"]);no=observe(root,nr["executable"],nr["sha256"],nr["bytes"]);oo=observe(root,spec["runtime"]["ocio"]["uri"],spec["runtime"]["ocio"]["sha256"]);checks={"parentIdentity":all(x["match"] for x in parents),"blenderRuntimeIdentity":bo["match"],"pythonRuntimeIdentity":po["match"],"nodeRuntimeIdentity":no["match"],"ocioIdentity":oo["match"]}
 if not all(checks.values()):raise RuntimeError(f"identity checks {checks}")
 free=shutil.disk_usage(root).free;disk={"availableBytes":free,"projectedWriteBytes":spec["projectedWriteBytes"],"projectedFreeAfterBytes":free-spec["projectedWriteBytes"],"reserveBytes":spec["diskReserveBytes"]};disk["status"]="ACCEPTED" if disk["projectedFreeAfterBytes"]>=disk["reserveBytes"] else "BLOCKED"
 if disk["status"]!="ACCEPTED":raise RuntimeError(f"disk blocked {disk}")
 prereg={"commit":PREREGISTRATION_COMMIT,"specUri":"specs/external-canonical-warp-bridge.v0.1.json","specSha256":SPEC_SHA256};spec_uri=str(a.spec.resolve().relative_to(root))
 if a.preflight_only:
  target=a.preflight_output.resolve()
  if target.exists() or root not in target.parents:raise RuntimeError("preflight target")
  with tempfile.TemporaryDirectory(prefix="bfs-b52-d8-preflight-") as td:
   t=Path(td);f=spec["fixtures"][0];fid=f["id"];probe=[];raws={};exrs={}
   for producer,exe,tool in (("python",pr["executable"],TOOLS["pythonProducer"]),("node",nr["executable"],TOOLS["nodeProducer"])):
    raw=t/producer/"reference.rgba32";rp=t/producer/"producer.json";x=launch([exe,tool,"--spec",spec_uri,"--fixture",fid,"--output",str(raw),"--report",str(rp)],root,clean_env(root,spec,t));raws[producer]=raw;er=t/producer/"encoder.json";ex=t/producer/"source.exr";y=launch([pr["executable"],TOOLS["encoder"],"--spec",spec_uri,"--fixture",fid,"--producer",producer,"--input",str(raw),"--output",str(ex),"--report",str(er)],root,clean_env(root,spec,t));exrs[producer]=ex;probe.append({"producer":producer,"producerRun":x,"producerReport":json.loads(rp.read_text()) if rp.is_file() else None,"encoderRun":y,"encoderReport":json.loads(er.read_text()) if er.is_file() else None})
   rp=t/"blender.json";z=launch([br["executable"],*br["launchFlags"],"--python",TOOLS["worker"],"--","--spec",spec_uri,"--fixture",fid,"--producer","python","--repeat","1","--input",str(exrs["python"]),"--probe-only","--report",str(rp)],root,clean_env(root,spec,t,True));brep=json.loads(rp.read_text()) if rp.is_file() else None;ok=all(q["producerRun"]["exitCode"]==0 and q["encoderRun"]["exitCode"]==0 and q["encoderReport"] and q["encoderReport"]["encodeDecodeExact"] for q in probe) and raws["python"].read_bytes()==raws["node"].read_bytes() and z["exitCode"]==0 and brep and brep["operationCounts"]["renderCalls"]==0
  if not ok:raise RuntimeError("frozen preflight component failure")
  body={"schemaVersion":"bfs.externalCanonicalWarpBridgeFrozenToolPreflight.v0.1","experimentId":spec["experimentId"],"classification":"ZERO_FORMAL_OUTPUT_COMPONENT_AND_GRAPH_PREFLIGHT","preregistration":prereg,"toolFreezeCommit":a.tool_freeze_commit,"tools":tools,"parentObservations":parents,"runtimeObservations":{"blender":bo,"python":po,"node":no,"ocio":oo},"checks":checks,"diskAdmission":disk,"formalOutputRoot":{"uri":spec["formalOutputRoot"],"absent":not out.exists()},"componentProbes":probe,"blenderProbe":{"pid":z["pid"],"report":brep},"formalOperationCounts":{"childProcesses":0,"blenderRenderCalls":0,"formalMeasurements":0}};target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps({**body,"preflightHash":ch(body)},indent=2,sort_keys=True,allow_nan=False)+"\n");print(f"BFS_B52_D8_PREFLIGHT_OK tools={len(tools)} dualProducer=True outputAbsent={not out.exists()} sha256={sha(target)}");return
 out.mkdir(parents=True);producers=[];encoders=[];blenders=[]
 for f in spec["fixtures"]:
  fid=f["id"]
  for producer,exe,tool in (("python",pr["executable"],TOOLS["pythonProducer"]),("node",nr["executable"],TOOLS["nodeProducer"])):
   cell=out/"references"/producer/fid;raw=cell/"reference.rgba32";rp=cell/"report.json";x=launch([exe,tool,"--spec",spec_uri,"--fixture",fid,"--output",str(raw.relative_to(root)),"--report",str(rp.relative_to(root))],root,clean_env(root,spec,Path(tempfile.gettempdir())));finish(cell,x);rec=record(x,"producer",fid,producer,str(rp.relative_to(root)),root);producers.append(rec)
   if x["exitCode"]!=0 or x["timedOut"] or rec["report"] is None:raise RuntimeError(f"producer failed {producer} {fid}")
   ecell=out/"encoded"/producer/fid;ex=ecell/"source.exr";er=ecell/"report.json";y=launch([pr["executable"],TOOLS["encoder"],"--spec",spec_uri,"--fixture",fid,"--producer",producer,"--input",str(raw.relative_to(root)),"--output",str(ex.relative_to(root)),"--report",str(er.relative_to(root))],root,clean_env(root,spec,Path(tempfile.gettempdir())));finish(ecell,y);erec=record(y,"encoder",fid,producer,str(er.relative_to(root)),root);encoders.append(erec)
   if y["exitCode"]!=0 or y["timedOut"] or erec["report"] is None:raise RuntimeError(f"encoder failed {producer} {fid}")
   for repeat in (1,2):
    bcell=out/"cells"/producer/f"{fid}_R{repeat}";bx=bcell/"passthrough.exr";bp=bcell/"report.json"
    with tempfile.TemporaryDirectory(prefix="bfs-b52-d8-") as td:z=launch([br["executable"],*br["launchFlags"],"--python",TOOLS["worker"],"--","--spec",spec_uri,"--fixture",fid,"--producer",producer,"--repeat",str(repeat),"--input",str(ex.relative_to(root)),"--output",str(bx.relative_to(root)),"--report",str(bp.relative_to(root))],root,clean_env(root,spec,Path(td),True))
    finish(bcell,z);brec=record(z,"blender",fid,producer,str(bp.relative_to(root)),root,repeat);blenders.append(brec)
    if z["exitCode"]!=0 or z["timedOut"] or brec["report"] is None:raise RuntimeError(f"blender failed {producer} {fid} R{repeat}")
 body={"schemaVersion":"bfs.externalCanonicalWarpBridgeReceipt.v0.1","experimentId":spec["experimentId"],"preregistration":prereg,"toolFreezeCommit":a.tool_freeze_commit,"tools":tools,"parentObservations":parents,"runtimeObservations":{"blender":bo,"python":po,"node":no,"ocio":oo},"checks":checks,"diskAdmission":disk,"producerRuns":producers,"encoderRuns":encoders,"blenderRuns":blenders};receipt={**body,"receiptHash":ch(body)};rp=out/"run.receipt.json";result=out/"results.json";rp.write_text(json.dumps(receipt,indent=2,sort_keys=True,allow_nan=False)+"\n");x=subprocess.run([pr["executable"],TOOLS["analyzer"],"--spec",spec_uri,"--receipt",str(rp.relative_to(root)),"--output",str(result.relative_to(root))],cwd=root,capture_output=True,text=True);(out/"analysis.stdout.log").write_text(x.stdout);(out/"analysis.stderr.log").write_text(x.stderr)
 if x.returncode:raise RuntimeError(f"analysis failed {x.stderr}")
 print(x.stdout.strip());print(f"BFS_B52_D8_RUN_OK receipt={sha(rp)} result={sha(result)}")
if __name__=="__main__":main()
