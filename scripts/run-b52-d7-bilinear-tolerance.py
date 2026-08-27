#!/usr/bin/env python3
"""Run B52-D7 fresh dual-reference Bilinear holdout."""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path
PREREGISTRATION_COMMIT="bb68af37390ac4459e95ab78f17544446913c01f"
SPEC_SHA256="f102a969cb59d92b0103c6807f20ca5436978504aafadd14a9b0353709ea0df5"
TOOLS={"pythonReference":"scripts/reference-b52-d7-bilinear.py","nodeReference":"scripts/reference-b52-d7-bilinear.mjs","worker":"blender/render_b52_d7_bilinear_cell.py","analyzer":"scripts/analyze-b52-d7-bilinear-tolerance.py","audit":"scripts/audit-b52-d7-bilinear-tolerance.py","runner":"scripts/run-b52-d7-bilinear-tolerance.py","tests":"tests/test_b52_d7_bilinear_tolerance_contract.py"}
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def ch(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def blob(root,commit,uri):
 p=subprocess.run(["git","show",f"{commit}:{uri}"],cwd=root,capture_output=True);return hashlib.sha256(p.stdout).hexdigest() if p.returncode==0 else None
def observe(root,uri,expected,bytes_=None):
 p=Path(uri) if Path(uri).is_absolute() else root/uri;o=sha(p) if p.is_file() else None;b=p.stat().st_size if p.is_file() else None;return {"uri":str(uri),"expectedSha256":expected,"observedSha256":o,"expectedBytes":bytes_,"observedBytes":b,"match":o==expected and (bytes_ is None or b==bytes_)}
def launch(cmd,root,env,timeout=30):
 start=time.monotonic();p=subprocess.Popen(cmd,cwd=root,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);to=False
 try:out,err=p.communicate(timeout=timeout)
 except subprocess.TimeoutExpired:
  to=True;p.terminate()
  try:out,err=p.communicate(timeout=5)
  except subprocess.TimeoutExpired:p.kill();out,err=p.communicate()
 return {"pid":p.pid,"exitCode":p.returncode,"timedOut":to,"elapsedSeconds":round(time.monotonic()-start,6),"stdout":out,"stderr":err}
def env(root,spec,tmp,blender=False):
 e={k:v for k,v in os.environ.items() if k=="PATH"};e.update({"LANG":"C.UTF-8","LC_ALL":"C.UTF-8"})
 if blender:
  e.update({"OCIO":str((root/spec["runtime"]["ocio"]["uri"]).resolve()),"TMPDIR":str(tmp/"tmp"),"BLENDER_USER_CONFIG":str(tmp/"config"),"BLENDER_USER_SCRIPTS":str(tmp/"scripts")});[Path(e[k]).mkdir(parents=True,exist_ok=True) for k in ("TMPDIR","BLENDER_USER_CONFIG","BLENDER_USER_SCRIPTS")]
 return e
def finalize(root,cell,run):
 cell.mkdir(parents=True,exist_ok=True);(cell/"stdout.log").write_text(run["stdout"]);(cell/"stderr.log").write_text(run["stderr"])
def record(run,kind,fid,report_uri,root,repeat=None):
 rp=root/report_uri;report=json.loads(rp.read_text()) if rp.is_file() else None;return {"kind":kind,"fixtureId":fid,"repeat":repeat,"pid":run["pid"],"exitCode":run["exitCode"],"timedOut":run["timedOut"],"elapsedSeconds":run["elapsedSeconds"],"reportUri":report_uri,"report":report}
def main():
 p=argparse.ArgumentParser();p.add_argument("--spec",type=Path,required=True);p.add_argument("--output-root",type=Path,required=True);p.add_argument("--tool-freeze-commit",required=True);p.add_argument("--preflight-only",action="store_true");p.add_argument("--preflight-output",type=Path);a=p.parse_args();root=a.spec.resolve().parent.parent;spec=json.loads(a.spec.read_text());out=a.output_root.resolve()
 if sha(a.spec)!=SPEC_SHA256 or out!=(root/spec["formalOutputRoot"]).resolve() or out.exists():raise RuntimeError("spec/output mismatch")
 if a.preflight_only != (a.preflight_output is not None):raise RuntimeError("preflight args")
 if subprocess.run(["git","merge-base","--is-ancestor",a.tool_freeze_commit,"HEAD"],cwd=root).returncode:raise RuntimeError("freeze ancestor")
 tools={}
 for name,uri in TOOLS.items():
  cur=sha(root/uri) if (root/uri).is_file() else None;fr=blob(root,a.tool_freeze_commit,uri)
  if cur is None or cur!=fr:raise RuntimeError(f"tool mismatch {uri}")
  tools[name]={"uri":uri,"sha256":cur,"freezeCommit":a.tool_freeze_commit}
 parents=[observe(root,x["uri"],x["sha256"]) for x in spec["parents"].values()];br=spec["runtime"]["blender"];pr=spec["runtime"]["pythonReference"];nr=spec["runtime"]["nodeReference"];bo=observe(root,br["executable"],br["sha256"],br["bytes"]);po=observe(root,pr["executable"],pr["sha256"],pr["bytes"]);no=observe(root,nr["executable"],nr["sha256"],nr["bytes"]);oo=observe(root,spec["runtime"]["ocio"]["uri"],spec["runtime"]["ocio"]["sha256"]);checks={"parentIdentity":all(x["match"] for x in parents),"blenderRuntimeIdentity":bo["match"],"pythonRuntimeIdentity":po["match"],"nodeRuntimeIdentity":no["match"],"ocioIdentity":oo["match"]}
 if not all(checks.values()):raise RuntimeError(f"input identity {checks}")
 free=shutil.disk_usage(root).free;disk={"availableBytes":free,"projectedWriteBytes":spec["projectedWriteBytes"],"projectedFreeAfterBytes":free-spec["projectedWriteBytes"],"reserveBytes":spec["diskReserveBytes"]};disk["status"]="ACCEPTED" if disk["projectedFreeAfterBytes"]>=disk["reserveBytes"] else "BLOCKED"
 if disk["status"]!="ACCEPTED":raise RuntimeError(f"disk blocked {disk}")
 prereg={"commit":PREREGISTRATION_COMMIT,"specUri":"specs/subpixel-bilinear-tolerance-holdout.v0.1.json","specSha256":SPEC_SHA256};spec_uri=str(a.spec.resolve().relative_to(root))
 if a.preflight_only:
  target=a.preflight_output.resolve()
  if target.exists() or root not in target.parents:raise RuntimeError("preflight target")
  with tempfile.TemporaryDirectory(prefix="bfs-b52-d7-preflight-") as td:
   t=Path(td);fid=spec["fixtures"][0]["id"];runs=[]
   for kind,exe,tool in [("python",pr["executable"],TOOLS["pythonReference"]),("node",nr["executable"],TOOLS["nodeReference"])]:
    op=t/kind/"reference.rgba32";rp=t/kind/"report.json";cmd=[exe,tool,"--spec",spec_uri,"--fixture",fid,"--output",str(op),"--report",str(rp)];x=launch(cmd,root,env(root,spec,t));runs.append({"kind":kind,"run":x,"report":json.loads(rp.read_text()) if rp.is_file() else None,"outputSha256":sha(op) if op.is_file() else None})
   rp=t/"blender-report.json";cmd=[br["executable"],*br["launchFlags"],"--python",TOOLS["worker"],"--","--spec",spec_uri,"--fixture",fid,"--repeat","1","--probe-only","--report",str(rp)];x=launch(cmd,root,env(root,spec,t,True));brep=json.loads(rp.read_text()) if rp.is_file() else None
  ok=all(y["run"]["exitCode"]==0 and y["report"] for y in runs) and runs[0]["outputSha256"]==runs[1]["outputSha256"] and x["exitCode"]==0 and brep and brep["operationCounts"]["renderCalls"]==0
  if not ok:raise RuntimeError("preflight worker failure")
  body={"schemaVersion":"bfs.subpixelBilinearFrozenToolPreflight.v0.1","experimentId":spec["experimentId"],"classification":"ZERO_FORMAL_OUTPUT_DUAL_REFERENCE_AND_RNA_PREFLIGHT","preregistration":prereg,"toolFreezeCommit":a.tool_freeze_commit,"tools":tools,"parentObservations":parents,"runtimeObservations":{"blender":bo,"python":po,"node":no,"ocio":oo},"checks":checks,"diskAdmission":disk,"formalOutputRoot":{"uri":spec["formalOutputRoot"],"absent":not out.exists()},"referenceProbes":runs,"blenderProbe":{"pid":x["pid"],"report":brep},"formalOperationCounts":{"childProcesses":0,"blenderRenderCalls":0,"formalMeasurements":0}};result={**body,"preflightHash":ch(body)};target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n");print(f"BFS_B52_D7_PREFLIGHT_OK tools={len(tools)} dualReference=True outputAbsent={not out.exists()} sha256={sha(target)}");return
 out.mkdir(parents=True);pyr=[];nor=[];blr=[]
 for f in spec["fixtures"]:
  fid=f["id"]
  for kind,exe,tool,bucket in [("pythonReference",pr["executable"],TOOLS["pythonReference"],pyr),("nodeReference",nr["executable"],TOOLS["nodeReference"],nor)]:
   uri=f"{spec['formalOutputRoot']}/references/{kind}/{fid}";op=f"{uri}/reference.rgba32";rp=f"{uri}/report.json";cmd=[exe,tool,"--spec",spec_uri,"--fixture",fid,"--output",op,"--report",rp];x=launch(cmd,root,env(root,spec,Path(tempfile.gettempdir())));finalize(root,root/uri,x);rec=record(x,kind,fid,rp,root);bucket.append(rec)
   if x["exitCode"]!=0 or x["timedOut"] or rec["report"] is None:raise RuntimeError(f"reference failed {kind} {fid}")
  for repeat in (1,2):
   uri=f"{spec['formalOutputRoot']}/cells/{fid}_R{repeat}";op=f"{uri}/displace.exr";rp=f"{uri}/report.json"
   with tempfile.TemporaryDirectory(prefix="bfs-b52-d7-") as td:
    cmd=[br["executable"],*br["launchFlags"],"--python",TOOLS["worker"],"--","--spec",spec_uri,"--fixture",fid,"--repeat",str(repeat),"--output-exr",op,"--report",rp];x=launch(cmd,root,env(root,spec,Path(td),True))
   finalize(root,root/uri,x);rec=record(x,"blender",fid,rp,root,repeat);blr.append(rec)
   if x["exitCode"]!=0 or x["timedOut"] or rec["report"] is None:raise RuntimeError(f"blender failed {fid} R{repeat}")
 body={"schemaVersion":"bfs.subpixelBilinearToleranceReceipt.v0.1","experimentId":spec["experimentId"],"preregistration":prereg,"toolFreezeCommit":a.tool_freeze_commit,"tools":tools,"parentObservations":parents,"runtimeObservations":{"blender":bo,"python":po,"node":no,"ocio":oo},"checks":checks,"diskAdmission":disk,"pythonReferenceRuns":pyr,"nodeReferenceRuns":nor,"blenderRuns":blr};receipt={**body,"receiptHash":ch(body)};receipt_path=out/"run.receipt.json";result_path=out/"results.json";receipt_path.write_text(json.dumps(receipt,indent=2,sort_keys=True,allow_nan=False)+"\n");cmd=[sys.executable,TOOLS["analyzer"],"--spec",spec_uri,"--receipt",str(receipt_path.relative_to(root)),"--output",str(result_path.relative_to(root))];x=subprocess.run(cmd,cwd=root,capture_output=True,text=True);(out/"analysis.stdout.log").write_text(x.stdout);(out/"analysis.stderr.log").write_text(x.stderr)
 if x.returncode:raise SystemExit(x.returncode)
 print(x.stdout.strip());print(f"BFS_B52_D7_RUN_OK receipt={sha(receipt_path)} result={sha(result_path)}")
if __name__=="__main__":main()
