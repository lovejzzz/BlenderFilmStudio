#!/usr/bin/env python3
"""Frozen-tool, owner-boundary, Blender API and disk preflight for B52-D12.3."""

from __future__ import annotations

import argparse, ast, hashlib, json, os, shutil, subprocess
from pathlib import Path
import numpy as np


SPEC_SHA256="f1ffe5b4fe0912936b1e03677dd0985f11c34e6b5df4ddf70854533c4ad0b590";PREREGISTRATION_COMMIT="1f2a232a8c3a7dabc0074f1c465e8d51ada801bd"
def sha_bytes(value:bytes)->str:return hashlib.sha256(value).hexdigest()
def sha_file(path:Path)->str:
    d=hashlib.sha256()
    with path.open("rb") as h:
        for chunk in iter(lambda:h.read(1024*1024),b""):d.update(chunk)
    return d.hexdigest()
def canon(value:object)->str:return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def run(argv:list[str],env:dict[str,str],cwd:Path)->dict:
    c=subprocess.run(argv,cwd=cwd,env=env,capture_output=True,text=True);return {"argv":argv,"exitCode":c.returncode,"stdout":c.stdout,"stderr":c.stderr}


def main()->None:
    p=argparse.ArgumentParser();p.add_argument("--spec",type=Path,required=True);p.add_argument("--tool-freeze-commit",required=True);p.add_argument("--output-root",type=Path,required=True);a=p.parse_args();repo=Path.cwd().resolve();spec_path=a.spec.resolve();spec=json.loads(spec_path.read_text());formal=(repo/spec["diskAdmission"]["formalRoot"]).resolve();root=a.output_root.resolve()
    if root.exists() or formal.exists():raise RuntimeError("D12.3 preflight/formal root freshness failure")
    root.mkdir(parents=True,exist_ok=False);tests=[]
    def check(name:str,passed:bool,detail:object=None)->None:tests.append({"id":name,"passed":bool(passed),"detail":detail})
    check("SPEC_IDENTITY",sha_file(spec_path)==SPEC_SHA256,sha_file(spec_path));check("PREREGISTRATION_COMMIT",subprocess.run(["git","cat-file","-e",f"{PREREGISTRATION_COMMIT}^{{commit}}"],cwd=repo).returncode==0,PREREGISTRATION_COMMIT)
    working={};frozen={};match=True
    for relative in spec["formalToolPaths"]:
        payload=(repo/relative).read_bytes();blob=subprocess.run(["git","show",f"{a.tool_freeze_commit}:{relative}"],cwd=repo,capture_output=True);working[relative]=sha_bytes(payload);frozen[relative]=sha_bytes(blob.stdout) if blob.returncode==0 else None;match=match and blob.returncode==0 and payload==blob.stdout
    check("FROZEN_TOOL_IDENTITY",match,{"working":working,"git":frozen})
    check("RUNTIME_BLENDER",sha_file(Path(spec["runtime"]["blender"]["executable"]))==spec["runtime"]["blender"]["sha256"]);check("RUNTIME_PYTHON",sha_file(Path(spec["runtime"]["python"]["executable"]))==spec["runtime"]["python"]["sha256"]);check("RUNTIME_NODE",sha_file(Path(spec["runtime"]["node"]["executable"]))==spec["runtime"]["node"]["sha256"]);check("RUNTIME_OCIO",sha_file(repo/spec["runtime"]["ocio"]["uri"])==spec["runtime"]["ocio"]["sha256"])
    syntax=[]
    for relative in spec["formalToolPaths"]:
        try:
            if relative.endswith(".py"):ast.parse((repo/relative).read_text())
            elif subprocess.run([spec["runtime"]["node"]["executable"],"--check",str(repo/relative)],capture_output=True).returncode!=0:raise RuntimeError("node syntax")
            syntax.append({"uri":relative,"passed":True})
        except Exception as error:syntax.append({"uri":relative,"passed":False,"error":str(error)})
    check("TOOL_SYNTAX",all(row["passed"] for row in syntax),syntax)
    tree=ast.parse((repo/"scripts/analyze-b52-d12-3-nonplanar-multiowner.py").read_text());imports=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):imports.extend(alias.name for alias in node.names)
        elif isinstance(node,ast.ImportFrom):imports.append(node.module or "")
    check("ANALYZER_IMPORT_INDEPENDENCE",all(not name.startswith(("scripts","blender","importlib")) for name in imports),imports)
    env={"PATH":os.environ.get("PATH",""),"LANG":"C.UTF-8","LC_ALL":"C.UTF-8","OCIO":str((repo/spec["runtime"]["ocio"]["uri"]).resolve())};fixture=spec["fixtures"][0];width,height=fixture["resolution"];synthetic=root/"synthetic";arrays=synthetic/"adapter-arrays";arrays.mkdir(parents=True)
    previous=np.zeros((height,width,4),dtype="<f4")
    for y in range(height):
        for x in range(width):previous[y,x]=(x/width,y/height,(x+y)/(width+height),1.0)
    current=previous.copy();owner=np.empty((height,width),dtype="<f4");split=width//2;owner[:,:split]=fixture["owners"][0]["passIndex"];owner[:,split:]=fixture["owners"][1]["passIndex"];vector=np.zeros((height,width,2),dtype="<f4");vector[...,0]=np.float32(1/65536)
    records={}
    for name,filename,array in (("previousRgba","previous.rgba32",previous),("currentRgba","current.rgba32",current),("previousOwner","previous-owner.f32",owner),("currentOwner","current-owner.f32",owner),("vector","vector.xy32",vector)):
        payload=np.ascontiguousarray(array,dtype="<f4").tobytes();target=arrays/filename;target.write_bytes(payload);records[name]={"uri":str(target),"sha256":sha_bytes(payload),"bytes":len(payload)}
    abody={"schemaVersion":"synthetic","fixtureId":fixture["id"],"repeat":1,"arrays":records};adapter={**abody,"reportHash":canon(abody)};adapter_path=synthetic/"adapter-report.json";adapter_path.write_text(json.dumps(adapter,indent=2,sort_keys=True)+"\n")
    results={}
    for producer,exe,tool in (("python",spec["runtime"]["python"]["executable"],repo/"scripts/reconstruct-b52-d12-3-nonplanar-multiowner.py"),("node",spec["runtime"]["node"]["executable"],repo/"scripts/reconstruct-b52-d12-3-nonplanar-multiowner.mjs")):
        out=synthetic/producer;results[producer]=run([exe,str(tool),"--spec",str(spec_path),"--fixture",fixture["id"],"--repeat","1","--input-dir",str(arrays),"--adapter-report",str(adapter_path),"--output-dir",str(out/"arrays"),"--report",str(out/"report.json")],env,repo)
    dual=all(row["exitCode"]==0 for row in results.values())
    if dual:
        dual=all((synthetic/"python/arrays"/name).read_bytes()==(synthetic/"node/arrays"/name).read_bytes() for name in ("reconstructed.rgba32","valid.u8","boundary.u8"));valid=np.frombuffer((synthetic/"python/arrays/valid.u8").read_bytes(),dtype="u1");boundary=np.frombuffer((synthetic/"python/arrays/boundary.u8").read_bytes(),dtype="u1");dual=dual and valid.sum()>0 and boundary.sum()>0 and np.logical_and(valid,boundary).sum()==0
    check("SYNTHETIC_OWNER_BOUNDARY_DUAL_CONSUMER",dual,results)
    probe=root/"blender-probe";probe_env={**env}
    for key,suffix in (("TMPDIR","tmp"),("BLENDER_USER_CONFIG","config"),("BLENDER_USER_SCRIPTS","scripts")):
        target=probe/suffix;target.mkdir(parents=True,exist_ok=True);probe_env[key]=str(target)
    probe_result=run([spec["runtime"]["blender"]["executable"],*spec["runtime"]["blender"]["launchFlags"],"--python",str(repo/"blender/render_b52_d12_3_nonplanar_multiowner_source.py"),"--","--spec",str(spec_path),"--fixture",fixture["id"],"--frame","1","--repeat","1","--report",str(probe/"report.json"),"--probe-only"],probe_env,repo);probe_ok=probe_result["exitCode"]==0 and (probe/"report.json").is_file()
    if probe_ok:
        report=json.loads((probe/"report.json").read_text());probe_ok=report["operationCounts"]["blenderRenderCalls"]==0 and report["output"] is None and len(report["sceneStructure"]["owners"])==len(fixture["owners"])
    check("REAL_BLENDER_ZERO_RENDER_GEOMETRY_PROBE",probe_ok,probe_result)
    available=shutil.disk_usage(repo).free;projected=spec["diskAdmission"]["projectedWriteBytes"];reserve=spec["diskAdmission"]["minimumReserveBytes"];disk={"availableBytes":available,"projectedWriteBytes":projected,"minimumReserveBytes":reserve,"freeAfterProjectedBytes":available-projected,"status":"ACCEPTED" if available-projected>=reserve else "REJECTED"};check("DISK_ADMISSION",disk["status"]=="ACCEPTED",disk);check("FORMAL_ROOT_REMAINS_ABSENT",not formal.exists(),str(formal))
    status="ACCEPTED" if all(row["passed"] for row in tests) else "REJECTED";body={"schemaVersion":"bfs.blenderStaticNonplanarMultiownerPreflight.v0.1","experimentId":spec["experimentId"],"preregistrationCommit":PREREGISTRATION_COMMIT,"toolFreezeCommit":a.tool_freeze_commit,"specSha256":sha_file(spec_path),"toolHashes":working,"gitBlobHashes":frozen,"diskAdmission":disk,"tests":tests,"passedTests":sum(row["passed"] for row in tests),"totalTests":len(tests),"status":status,"formalOperations":{"blenderRenders":0,"adapters":0,"consumers":0,"envelopeEncoders":0,"analyzers":0}};receipt={**body,"preflightHash":canon(body)};(root/"frozen-tool-preflight.json").write_text(json.dumps(receipt,indent=2,sort_keys=True,allow_nan=False)+"\n");print(f"BFS_B52_D123_PREFLIGHT_{status} tests={receipt['passedTests']}/{receipt['totalTests']} disk={disk['freeAfterProjectedBytes']-reserve}")
    if status!="ACCEPTED":raise SystemExit(2)


if __name__=="__main__":main()
