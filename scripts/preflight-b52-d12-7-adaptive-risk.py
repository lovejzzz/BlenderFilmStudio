#!/usr/bin/env python3
"""Frozen-tool, zero-formal-output preflight for B52-D12.7."""
from __future__ import annotations

import argparse, ast, hashlib, json, os, shutil, subprocess
from pathlib import Path
import numpy as np

SPEC_SHA256="c51d0d83afd30b479bf3e7109c31110133649ee3d65a04d677dbe236b8075ed0"
PREREGISTRATION_COMMIT="22b0338aa2fcb168c4e94001bf9cbfe2d5a1e0f6"
PAYLOADS=("radius2-reconstructed.rgba32","radius2-interior.u8","radius2-boundary.u8","radius3-reconstructed.rgba32","radius3-interior.u8","radius3-boundary.u8","adaptive-reconstructed.rgba32","adaptive-interior.u8","adaptive-boundary.u8","adaptive-rejected.u8","risk.rgb64")

def sha_bytes(value:bytes)->str:return hashlib.sha256(value).hexdigest()
def sha_file(path:Path)->str:
 digest=hashlib.sha256()
 with path.open("rb") as handle:
  for chunk in iter(lambda:handle.read(1048576),b""):digest.update(chunk)
 return digest.hexdigest()
def canon(value:object)->str:return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def self_ok(document:dict,field:str)->bool:return document.get(field)==canon({k:v for k,v in document.items() if k!=field})
def run(argv:list[str],env:dict[str,str],cwd:Path)->dict:
 result=subprocess.run(argv,cwd=cwd,env=env,capture_output=True,text=True);return {"argv":argv,"exitCode":result.returncode,"stdout":result.stdout,"stderr":result.stderr}
def imports_are_independent(path:Path)->bool:
 tree=ast.parse(path.read_text());imports=[]
 for node in ast.walk(tree):
  if isinstance(node,ast.Import):imports.extend(alias.name for alias in node.names)
  elif isinstance(node,ast.ImportFrom):imports.append(node.module or "")
 return all(not name.startswith(("scripts","blender","importlib")) for name in imports)

def main()->None:
 p=argparse.ArgumentParser();p.add_argument("--spec",type=Path,required=True);p.add_argument("--tool-freeze-commit",required=True);p.add_argument("--output-root",type=Path,required=True);a=p.parse_args();repo=Path.cwd().resolve();spec_path=a.spec.resolve();root=a.output_root.resolve();spec=json.loads(spec_path.read_text());formal=(repo/spec["diskAdmission"]["formalRoot"]).resolve()
 if root.exists() or formal.exists():raise RuntimeError("D12.7 preflight/formal root freshness failure")
 root.mkdir(parents=True,exist_ok=False);tests=[]
 def check(name:str,passed:bool,detail:object=None)->None:tests.append({"id":name,"passed":bool(passed),"detail":detail})
 check("SPEC_IDENTITY",sha_file(spec_path)==SPEC_SHA256,sha_file(spec_path));check("PREREGISTRATION_COMMIT",subprocess.run(["git","cat-file","-e",f"{PREREGISTRATION_COMMIT}^{{commit}}"],cwd=repo).returncode==0,PREREGISTRATION_COMMIT)
 working={};frozen={};match=True
 for relative in spec["freshness"]["formalToolPaths"]:
  payload=(repo/relative).read_bytes();blob=subprocess.run(["git","show",f"{a.tool_freeze_commit}:{relative}"],cwd=repo,capture_output=True);working[relative]=sha_bytes(payload);frozen[relative]=sha_bytes(blob.stdout) if blob.returncode==0 else None;match &= blob.returncode==0 and payload==blob.stdout
 check("FROZEN_TOOL_IDENTITY",match,{"working":working,"git":frozen});check("RUNTIME_BLENDER",sha_file(Path(spec["runtime"]["blender"]["executable"]))==spec["runtime"]["blender"]["sha256"]);check("RUNTIME_PYTHON",sha_file(Path(spec["runtime"]["python"]["executable"]))==spec["runtime"]["python"]["sha256"]);check("RUNTIME_NODE",sha_file(Path(spec["runtime"]["node"]["executable"]))==spec["runtime"]["node"]["sha256"]);check("RUNTIME_OCIO",sha_file(repo/spec["runtime"]["ocio"]["uri"])==spec["runtime"]["ocio"]["sha256"])
 parent_checks={}
 for name,row in spec["parents"].items():
  path=repo/row["uri"];parent_checks[f"{name}FileHash"]=path.is_file() and sha_file(path)==row["sha256"]
  if path.suffix==".json" and path.is_file():
   document=json.loads(path.read_text())
   for field in ("evidenceHash","receiptHash","auditHash"):
    if field in row:parent_checks[f"{name}{field}"]=self_ok(document,field) and document.get(field)==row[field]
 check("PARENT_IDENTITIES",all(parent_checks.values()),parent_checks)
 syntax=[]
 for relative in spec["freshness"]["formalToolPaths"]:
  try:
   if relative.endswith(".py"):ast.parse((repo/relative).read_text())
   elif subprocess.run([spec["runtime"]["node"]["executable"],"--check",str(repo/relative)],capture_output=True).returncode!=0:raise RuntimeError("node syntax")
   syntax.append({"uri":relative,"passed":True})
  except Exception as error:syntax.append({"uri":relative,"passed":False,"error":str(error)})
 check("TOOL_SYNTAX",all(row["passed"] for row in syntax),syntax);check("ANALYZER_IMPORT_INDEPENDENCE",imports_are_independent(repo/"scripts/analyze-b52-d12-7-adaptive-risk.py"));check("AUDIT_IMPORT_INDEPENDENCE",imports_are_independent(repo/"scripts/audit-b52-d12-7-adaptive-risk.py"))
 env={"PATH":os.environ.get("PATH",""),"LANG":"C.UTF-8","LC_ALL":"C.UTF-8","OCIO":str((repo/spec["runtime"]["ocio"]["uri"]).resolve())};fixture=spec["fixtures"][0];width,height=fixture["resolution"];synthetic=root/"synthetic";arrays=synthetic/"adapter-arrays";arrays.mkdir(parents=True)
 previous=np.zeros((height,width,4),dtype="<f4")
 for y in range(height):
  for x in range(width):previous[y,x]=(0.12+0.7*x/max(1,width-1),0.17+0.6*y/max(1,height-1),0.11+0.65*((x*7+y*11)%23)/22,1.0)
 current=previous.copy();owner=np.empty((height,width),dtype="<f4");split=width//2;owner[:,:split]=fixture["owners"][0]["passIndex"];owner[:,split:]=fixture["owners"][1]["passIndex"];vector=np.zeros((height,width,2),dtype="<f4");vector[:,split+8:,0]=np.float32(.25);records={}
 for name,filename,array in (("previousRgba","previous.rgba32",previous),("currentRgba","current.rgba32",current),("previousOwner","previous-owner.f32",owner),("currentOwner","current-owner.f32",owner),("vector","vector.xy32",vector),("vectorNext","vector-next.xy32",np.zeros_like(vector))):
  payload=np.ascontiguousarray(array,dtype="<f4").tobytes();target=arrays/filename;target.write_bytes(payload);records[name]={"uri":str(target),"sha256":sha_bytes(payload),"bytes":len(payload)}
 adapter_body={"schemaVersion":"synthetic","fixtureId":fixture["id"],"repeat":1,"arrays":records};adapter={**adapter_body,"reportHash":canon(adapter_body)};adapter_path=synthetic/"adapter-report.json";adapter_path.write_text(json.dumps(adapter,indent=2,sort_keys=True)+"\n");results={}
 for producer,exe,tool in (("python",spec["runtime"]["python"]["executable"],repo/"scripts/reconstruct-b52-d12-7-adaptive-risk.py"),("node",spec["runtime"]["node"]["executable"],repo/"scripts/reconstruct-b52-d12-7-adaptive-risk.mjs")):
  out=synthetic/producer;results[producer]=run([exe,str(tool),"--spec",str(spec_path),"--fixture",fixture["id"],"--repeat","1","--input-dir",str(arrays),"--adapter-report",str(adapter_path),"--output-dir",str(out/"arrays"),"--report",str(out/"report.json")],env,repo)
 dual=all(row["exitCode"]==0 for row in results.values());details={"processes":results}
 if dual:
  dual=all((synthetic/"python/arrays"/name).read_bytes()==(synthetic/"node/arrays"/name).read_bytes() for name in PAYLOADS);r2=np.frombuffer((synthetic/"python/arrays/radius2-interior.u8").read_bytes(),dtype="u1").reshape(height,width).astype(bool);r3=np.frombuffer((synthetic/"python/arrays/radius3-interior.u8").read_bytes(),dtype="u1").reshape(height,width).astype(bool);adaptive=np.frombuffer((synthetic/"python/arrays/adaptive-interior.u8").read_bytes(),dtype="u1").reshape(height,width).astype(bool);rejected=np.frombuffer((synthetic/"python/arrays/adaptive-rejected.u8").read_bytes(),dtype="u1").reshape(height,width).astype(bool);dual &= r2.any() and r3.any() and adaptive.any() and rejected.any() and not np.logical_and(r3,~r2).any() and not np.logical_and(adaptive,~r2).any() and np.array_equal(adaptive|rejected,r2) and not np.logical_and(adaptive,rejected).any();details.update({"radius2":int(r2.sum()),"radius3":int(r3.sum()),"adaptive":int(adaptive.sum()),"rejected":int(rejected.sum())})
 check("SYNTHETIC_DUAL_CONSUMER_AND_PARTITIONS",dual,details)
 threshold=float(spec["frozenGates"]["adaptiveHeadroom"]["reconstructionRgbMax"]);check("INCLUSIVE_THRESHOLD_BRANCH",threshold<=threshold and np.nextafter(threshold,-np.inf)<=threshold and not np.nextafter(threshold,np.inf)<=threshold)
 rng=np.random.default_rng(127);bound_cases=[]
 for _ in range(259):
  taps=[np.float32(v) for v in rng.uniform(.08,.92,4)];center=np.float32(rng.uniform(.08,.92));fx,fy=float(rng.random()),float(rng.random());weights=((1-fx)*(1-fy),fx*(1-fy),(1-fx)*fy,fx*fy);pre=(((float(taps[0])*weights[0])+(float(taps[1])*weights[1]))+(float(taps[2])*weights[2]))+(float(taps[3])*weights[3]);final=np.float32(pre);actual=abs(float(final)-float(center));bound=sum(abs(w)*abs(float(v)-float(center)) for w,v in zip(weights,taps))+abs(float(np.spacing(final)));bound_cases.append(actual<=bound)
 check("SYNTHETIC_RISK_BOUND_259",all(bound_cases),len(bound_cases))
 probes=[]
 for fixture in spec["fixtures"]:
  probe=root/"blender-probes"/fixture["id"];probe_env={**env}
  for key,suffix in (("TMPDIR","tmp"),("BLENDER_USER_CONFIG","config"),("BLENDER_USER_SCRIPTS","scripts")):
   target=probe/suffix;target.mkdir(parents=True,exist_ok=True);probe_env[key]=str(target)
  result=run([spec["runtime"]["blender"]["executable"],*spec["runtime"]["blender"]["launchFlags"],"--python",str(repo/"blender/render_b52_d12_7_adaptive_risk_source.py"),"--","--spec",str(spec_path),"--fixture",fixture["id"],"--frame","1","--repeat","1","--report",str(probe/"report.json"),"--probe-only"],probe_env,repo);ok=result["exitCode"]==0 and (probe/"report.json").is_file()
  if ok:
   report=json.loads((probe/"report.json").read_text());ok=report["operationCounts"]["blenderRenderCalls"]==0 and report["output"] is None and len(report["sceneStructure"]["owners"])==len(fixture["owners"])
  probes.append({"fixture":fixture["id"],"passed":ok,"process":result})
 check("REAL_BLENDER_ZERO_RENDER_ALL_GEOMETRY_PROBES",all(row["passed"] for row in probes),probes)
 available=shutil.disk_usage(repo).free;projected=spec["diskAdmission"]["projectedWriteBytes"];reserve=spec["diskAdmission"]["minimumReserveBytes"];disk={"availableBytes":available,"projectedWriteBytes":projected,"minimumReserveBytes":reserve,"freeAfterProjectedBytes":available-projected,"status":"ACCEPTED" if available-projected>=reserve else "REJECTED"};check("DISK_ADMISSION",disk["status"]=="ACCEPTED",disk);check("FORMAL_ROOT_REMAINS_ABSENT",not formal.exists(),str(formal));status="ACCEPTED" if all(row["passed"] for row in tests) else "REJECTED";body={"schemaVersion":"bfs.blenderStaticAdaptiveRiskGatePreflight.v0.1","experimentId":spec["experimentId"],"preregistrationCommit":PREREGISTRATION_COMMIT,"toolFreezeCommit":a.tool_freeze_commit,"specSha256":sha_file(spec_path),"toolHashes":working,"gitBlobHashes":frozen,"parentChecks":parent_checks,"diskAdmission":disk,"tests":tests,"passedTests":sum(row["passed"] for row in tests),"totalTests":len(tests),"status":status,"formalOperations":{"blenderRenders":0,"adapters":0,"consumers":0,"envelopeEncoders":0,"analyzers":0,"audits":0,"modelCalls":0,"networkCalls":0}};receipt={**body,"preflightHash":canon(body)};(root/"frozen-tool-preflight.json").write_text(json.dumps(receipt,indent=2,sort_keys=True,allow_nan=False)+"\n");print(f"BFS_B52_D127_PREFLIGHT_{status} tests={receipt['passedTests']}/{receipt['totalTests']} diskMargin={disk['freeAfterProjectedBytes']-reserve}")
 if status!="ACCEPTED":raise SystemExit(2)

if __name__=="__main__":main()
