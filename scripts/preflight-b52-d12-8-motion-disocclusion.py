#!/usr/bin/env python3
"""Zero-formal-output admission preflight for B52-D12.8-C1."""
from __future__ import annotations
import argparse,ast,datetime as dt,hashlib,importlib.util,json,os,shutil,subprocess,sys,tempfile
from pathlib import Path
import numpy as np

SPEC_SHA256="d7e7c0ee0bd7f512766188eabda9fa0dccb098a0729b26487aa38bee97d6aea6"
FILES={"previousRgba":"previous.rgba32","currentRgba":"current.rgba32","previousDepth":"previous-depth.f32","currentDepth":"current-depth.f32","previousOwner":"previous-owner.f32","currentOwner":"current-owner.f32","vector":"vector.xy32","vectorNext":"vector-next.xy32"}
def sha_bytes(value:bytes)->str:return hashlib.sha256(value).hexdigest()
def sha_file(file_path:Path)->str:
 d=hashlib.sha256()
 with file_path.open("rb") as h:
  for chunk in iter(lambda:h.read(1048576),b""):d.update(chunk)
 return d.hexdigest()
def canon(value:object)->str:return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def run(argv,repo,env=None):
 process=subprocess.run(argv,cwd=repo,env=env,capture_output=True,text=True);return {"pid":None,"exitCode":process.returncode,"stdout":process.stdout,"stderr":process.stderr,"argv":argv}
def main():
 p=argparse.ArgumentParser();p.add_argument("--spec",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args();repo=Path.cwd().resolve();spec_path=a.spec.resolve();output=a.output.resolve();spec=json.loads(spec_path.read_text())
 if sha_file(spec_path)!=SPEC_SHA256:raise RuntimeError("D12.8-C1 spec identity mismatch")
 expected_output=(repo/spec["diskAdmission"]["preflightRoot"]/"frozen-tool-preflight.json").resolve()
 if output!=expected_output or output.parent.exists() or (repo/spec["diskAdmission"]["formalRoot"]).exists():raise RuntimeError("D12.8-C1 preflight/formal freshness rejected")
 tool_paths=spec["freshness"]["newFormalToolPaths"]+spec["freshness"]["reusedFrozenTools"];tool_hashes={uri:sha_file(repo/uri) for uri in tool_paths};head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=repo,text=True).strip();git_checks={}
 for uri in tool_paths:
  tracked=subprocess.run(["git","diff","--quiet","HEAD","--",uri],cwd=repo).returncode==0 and subprocess.run(["git","ls-files","--error-unmatch",uri],cwd=repo,capture_output=True).returncode==0
  blob=subprocess.check_output(["git","show",f"HEAD:{uri}"],cwd=repo);git_checks[uri]=tracked and sha_bytes(blob)==tool_hashes[uri]
 parent_checks={name:sha_file(repo/row["uri"])==row["sha256"] for name,row in spec["parents"].items() if "uri" in row and "sha256" in row};runtime_checks={"blender":sha_file(Path(spec["runtime"]["blender"]["executable"]))==spec["runtime"]["blender"]["sha256"],"python":sha_file(Path(spec["runtime"]["python"]["executable"]))==spec["runtime"]["python"]["sha256"],"node":sha_file(Path(spec["runtime"]["node"]["executable"]))==spec["runtime"]["node"]["sha256"],"ocio":sha_file(repo/spec["runtime"]["ocio"]["uri"])==spec["runtime"]["ocio"]["sha256"]};free=shutil.disk_usage(repo).free;disk={"availableBytes":free,"projectedWriteBytes":spec["diskAdmission"]["projectedWriteBytes"],"minimumReserveBytes":spec["diskAdmission"]["minimumReserveBytes"],"freeAfterProjectedBytes":free-spec["diskAdmission"]["projectedWriteBytes"]};disk["passed"]=disk["freeAfterProjectedBytes"]>=disk["minimumReserveBytes"]
 analyzer_tree=ast.parse((repo/"scripts/analyze-b52-d12-8-motion-disocclusion.py").read_text());imports=[]
 for node in ast.walk(analyzer_tree):
  if isinstance(node,ast.Import):imports.extend(alias.name for alias in node.names)
  elif isinstance(node,ast.ImportFrom):imports.append(node.module or "")
 analyzer_independent=all("reconstruct" not in name and "bpy" not in name and "mathutils" not in name for name in imports)
 base_env={"PATH":os.environ.get("PATH",""),"LANG":"C.UTF-8","LC_ALL":"C.UTF-8","OCIO":str((repo/spec["runtime"]["ocio"]["uri"]).resolve())};probe_rows=[];synthetic={}
 with tempfile.TemporaryDirectory(prefix="bfs-d128-c1-preflight-") as temporary:
  temp=Path(temporary)
  for fixture in spec["fixtures"]:
   report=temp/"probes"/f"{fixture['id']}.json";runtime=temp/"runtime"/fixture["id"];env={**base_env}
   for key,suffix in (("TMPDIR","tmp"),("BLENDER_USER_CONFIG","config"),("BLENDER_USER_SCRIPTS","scripts")):
    target=runtime/suffix;target.mkdir(parents=True,exist_ok=True);env[key]=str(target)
   row=run([spec["runtime"]["blender"]["executable"],*spec["runtime"]["blender"]["launchFlags"],"--python",str(repo/"blender/render_b52_d12_8_motion_disocclusion_source.py"),"--","--spec",str(spec_path),"--fixture",fixture["id"],"--frame","1","--repeat","1","--report",str(report),"--probe-only"],repo,env);payload=json.loads(report.read_text()) if report.exists() else {};probe_rows.append({"fixtureId":fixture["id"],"exitCode":row["exitCode"],"reportHashValid":payload.get("reportHash")==canon({k:v for k,v in payload.items() if k!="reportHash"}) if payload else False,"probeOnly":payload.get("probeOnly"),"output":payload.get("output"),"ownerCount":len(payload.get("sceneStructure",{}).get("owners",[])),"passIndices":[owner["passIndex"] for owner in payload.get("sceneStructure",{}).get("owners",[])],"renderCalls":payload.get("operationCounts",{}).get("blenderRenderCalls"),"stdoutTail":row["stdout"].strip().splitlines()[-1:]})
  module_spec=importlib.util.spec_from_file_location("d128_consumer",repo/"scripts/reconstruct-b52-d12-8-motion-disocclusion.py");module=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(module);fixture=next(row for row in spec["fixtures"] if row["id"]=="MULTI_OWNER_STATIC_CONTROL_127X83");width,height=fixture["resolution"];arrays={"previousRgba":np.zeros((height,width,4),"<f4"),"currentRgba":np.zeros((height,width,4),"<f4"),"previousDepth":np.zeros((height,width),"<f4"),"currentDepth":np.zeros((height,width),"<f4"),"previousOwner":np.zeros((height,width),"<f4"),"currentOwner":np.zeros((height,width),"<f4"),"vector":np.zeros((height,width,2),"<f4"),"vectorNext":np.zeros((height,width,2),"<f4")}
  for y in range(height):
   for x in range(width):
    oracle=module.oracle_pixel(spec,fixture,x,y)
    if oracle:
     color=np.array((.25,.5,.75,1.) if oracle["ownerIndex"]==1 else (.75,.4,.2,1.),"<f4");owner=np.float32(oracle["passIndex"]);depth=np.float32(oracle["currentDepth"]);arrays["previousRgba"][y,x]=color;arrays["currentRgba"][y,x]=color;arrays["previousDepth"][y,x]=depth;arrays["currentDepth"][y,x]=depth;arrays["previousOwner"][y,x]=owner;arrays["currentOwner"][y,x]=owner
  for y in range(10,14):
   arrays["previousOwner"][y,10:14]=0;arrays["previousRgba"][y,20:24,3]=0;arrays["previousDepth"][y,30:34]+=1;arrays["vector"][y,40:44,0]=-100;arrays["currentOwner"][y,50:54]=0;arrays["previousRgba"][y,60:64,:3]+=np.float32(.125)
  input_dir=temp/"synthetic"/"input";input_dir.mkdir(parents=True);records={}
  for name,filename in FILES.items():
   payload=np.ascontiguousarray(arrays[name],dtype="<f4").tobytes();target=input_dir/filename;target.write_bytes(payload);records[name]={"uri":str(target),"sha256":sha_bytes(payload),"bytes":len(payload),"shape":list(arrays[name].shape),"dtype":"little-endian-float32"}
  adapter_body={"schemaVersion":"bfs.d128SyntheticAdapter.v0.1","experimentId":spec["experimentId"],"fixtureId":fixture["id"],"repeat":1,"pid":0,"arrays":records};adapter={**adapter_body,"reportHash":canon(adapter_body)};adapter_path=temp/"synthetic"/"adapter.json";adapter_path.write_text(json.dumps(adapter,indent=2,sort_keys=True)+"\n");reports={}
  for producer,executable,tool in (("python",spec["runtime"]["python"]["executable"],repo/"scripts/reconstruct-b52-d12-8-motion-disocclusion.py"),("node",spec["runtime"]["node"]["executable"],repo/"scripts/reconstruct-b52-d12-8-motion-disocclusion.mjs")):
   output_dir=temp/"synthetic"/producer/"arrays";report=temp/"synthetic"/f"{producer}.json";row=run([executable,str(tool),"--spec",str(spec_path),"--fixture",fixture["id"],"--repeat","1","--input-dir",str(input_dir),"--adapter-report",str(adapter_path),"--output-dir",str(output_dir),"--report",str(report)],repo,base_env)
   if row["exitCode"]!=0 or not report.exists():raise RuntimeError(f"D12.8-C1 synthetic {producer} failed exit={row['exitCode']} stdout={row['stdout']!r} stderr={row['stderr']!r}")
   reports[producer]=json.loads(report.read_text());synthetic[f"{producer}ExitZero"]=True
  exact={name:reports["python"]["arrays"][name]["sha256"]==reports["node"]["arrays"][name]["sha256"] for name in reports["python"]["arrays"]};reason=np.frombuffer((temp/"synthetic"/"python"/"arrays"/"reason.u8").read_bytes(),dtype="u1");rejected=np.frombuffer((temp/"synthetic"/"python"/"arrays"/"adaptive-rejected.u8").read_bytes(),dtype="u1");synthetic.update({"payloadExact":exact,"allPayloadExact":all(exact.values()),"reasonCounts":{name:int((reason==code).sum()) for name,code in module.REASONS.items()},"adaptiveRejectedPixels":int(rejected.sum())})
 probe_ok=all(row["exitCode"]==0 and row["reportHashValid"] and row["probeOnly"] is True and row["output"] is None and row["ownerCount"]==2 and row["renderCalls"]==0 for row in probe_rows);same_probe=next(row for row in probe_rows if row["fixtureId"]=="SAME_INDEX_DEPTH_REVEAL_173X107");synthetic_ok=synthetic.get("pythonExitZero") and synthetic.get("nodeExitZero") and synthetic.get("allPayloadExact") and all(synthetic["reasonCounts"][name]>0 for name in ("INVALID_CURRENT_ORACLE","INVALID_BOUNDS","INVALID_OWNER","INVALID_ALPHA","INVALID_DEPTH","VALID")) and synthetic["adaptiveRejectedPixels"]>0;checks=[("SPEC_AND_CORRECTION_IDENTITY",spec["experimentId"]=="B52-D12.8-C1" and spec["correction"]["originalSpecSha256"]=="67722b1c8fafa0b83518e6e467de1adb9ca88bd32b7145f15be2d5627767b4d4"),("FRESH_C1_ROOTS",not (repo/spec["diskAdmission"]["formalRoot"]).exists() and not output.parent.exists()),("PARENT_IDENTITIES",all(parent_checks.values())),("RUNTIME_IDENTITIES",all(runtime_checks.values())),("FROZEN_GIT_TOOL_IDENTITIES",all(git_checks.values())),("DISK_ADMISSION",disk["passed"]),("ANALYZER_IMPORT_INDEPENDENCE",analyzer_independent),("FOUR_REAL_BLENDER_ZERO_RENDER_PROBES",probe_ok),("SAME_INDEX_PROBE",same_probe["passIndices"]==[13505,13505]),("DUAL_SYNTHETIC_PAYLOAD_IDENTITY",synthetic_ok),("FORMAL_OUTPUT_ZERO",not (repo/spec["diskAdmission"]["formalRoot"]).exists())];status="ACCEPTED" if all(value for _,value in checks) else "REJECTED";body={"schemaVersion":"bfs.blenderProjectiveMotionDisocclusionPreflight.v0.1","experimentId":spec["experimentId"],"executedAtUtc":dt.datetime.now(dt.timezone.utc).isoformat(),"status":status,"checks":[{"id":name,"passed":bool(value)} for name,value in checks],"checkPassed":sum(value for _,value in checks),"checkTotal":len(checks),"specSha256":SPEC_SHA256,"toolFreezeCommit":head,"toolHashes":tool_hashes,"gitChecks":git_checks,"parentChecks":parent_checks,"runtimeChecks":runtime_checks,"diskAdmission":disk,"analyzerIndependent":analyzer_independent,"blenderProbes":probe_rows,"synthetic":synthetic,"operationCounts":{"blenderProcesses":len(probe_rows),"blenderRenderCalls":0,"syntheticPythonConsumers":1,"syntheticNodeConsumers":1,"formalRenders":0,"formalMeasurements":0,"modelCalls":0,"networkCalls":0}};preflight={**body,"preflightHash":canon(body)};output.parent.mkdir(parents=True,exist_ok=False);output.write_text(json.dumps(preflight,indent=2,sort_keys=True,allow_nan=False)+"\n");print(f"BFS_B52_D128_PREFLIGHT_{status} checks={preflight['checkPassed']}/{preflight['checkTotal']} hash={preflight['preflightHash']}");raise SystemExit(0 if status=="ACCEPTED" else 1)
if __name__=="__main__":main()
