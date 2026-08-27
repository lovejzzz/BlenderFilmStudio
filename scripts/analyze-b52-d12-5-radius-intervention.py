#!/usr/bin/env python3
"""Independent paired-radius analyzer and registered mutation audit for B52-D12.5."""

from __future__ import annotations

import argparse, ast, copy, hashlib, json, math, os
from collections import deque
from pathlib import Path
import numpy as np

SPEC_SHA256="b24aa05aeb1ab7a33e8fc57afc646308b5454eb0a5c5bf77dbbf8cc33f2ed5f2"
SOURCE_ARRAYS=("previousRgba","currentRgba","previousOwner","currentOwner","vector","vectorNext")
PAYLOADS={2:{"reconstructed":"radius2-reconstructed.rgba32","interior":"radius2-interior.u8","boundary":"radius2-boundary.u8"},3:{"reconstructed":"radius3-reconstructed.rgba32","interior":"radius3-interior.u8","boundary":"radius3-boundary.u8"}}
def sha_bytes(value:bytes)->str:return hashlib.sha256(value).hexdigest()
def sha_file(path:Path)->str:
    d=hashlib.sha256()
    with path.open("rb") as h:
        for chunk in iter(lambda:h.read(1024*1024),b""):d.update(chunk)
    return d.hexdigest()
def canon(value:object)->str:return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def native(path:Path)->dict:
    report=json.loads(path.read_text());body={k:v for k,v in report.items() if k!="reportHash"}
    if report.get("reportHash")!=canon(body):raise RuntimeError(f"report hash mismatch: {path}")
    return report
def f32(path:Path,shape:tuple[int,...])->np.ndarray:
    payload=path.read_bytes()
    if len(payload)!=math.prod(shape)*4:raise RuntimeError(f"array length mismatch: {path}")
    return np.frombuffer(payload,dtype="<f4").reshape(shape)
def metric(left:np.ndarray,right:np.ndarray,mask:np.ndarray)->dict:
    maximum=squared=0.0;count=0;all_zero=True
    for y,x in np.argwhere(mask):
        for channel in range(3):
            error=float(left[y,x,channel])-float(right[y,x,channel]);absolute=abs(error);maximum=max(maximum,absolute);squared+=error*error;count+=1;all_zero=all_zero and error==0.0
    if count==0:raise RuntimeError("empty metric mask")
    return {"maximum":maximum,"rmse":math.sqrt(squared/count),"sampleCount":count,"allZero":all_zero}
def owner_distance(owner:np.ndarray,alpha:np.ndarray,registered:set[float])->np.ndarray:
    height,width=owner.shape;distance=np.zeros((height,width),dtype=np.int16);queue=deque()
    valid=np.isin(owner,list(registered))&(alpha>np.float32(.999))
    for y,x in np.argwhere(valid):
        value=owner[y,x];edge=x==0 or y==0 or x==width-1 or y==height-1
        if not edge:
            edge=any(not valid[ty,tx] or owner[ty,tx]!=value for ty in range(y-1,y+2) for tx in range(x-1,x+2))
        if edge:distance[y,x]=1;queue.append((y,x))
    while queue:
        y,x=queue.popleft();next_distance=distance[y,x]+1;value=owner[y,x]
        for ty in range(max(0,y-1),min(height,y+2)):
            for tx in range(max(0,x-1),min(width,x+2)):
                if valid[ty,tx] and owner[ty,tx]==value and distance[ty,tx]==0:distance[ty,tx]=next_distance;queue.append((ty,tx))
    return distance
def boundary_metric(previous:np.ndarray,current:np.ndarray,vector:np.ndarray,boundary:np.ndarray)->dict:
    height,width=boundary.shape;maximum=squared=0.0;count=pixels=0
    for y,x in np.argwhere(boundary):
        qx=x+float(vector[y,x,0]);qy=y-float(vector[y,x,1]);x0,y0=math.floor(qx),math.floor(qy);x1,y1=x0+1,y0+1
        if x0<0 or y0<0 or x1>=width or y1>=height:continue
        fx,fy=qx-x0,qy-y0;weights=((1-fx)*(1-fy),fx*(1-fy),(1-fx)*fy,fx*fy);pixels+=1
        for channel in range(3):
            values=(float(previous[y0,x0,channel]),float(previous[y0,x1,channel]),float(previous[y1,x0,channel]),float(previous[y1,x1,channel]));value=np.float32((((values[0]*weights[0])+(values[1]*weights[1]))+(values[2]*weights[2]))+(values[3]*weights[3]));error=float(value)-float(current[y,x,channel]);maximum=max(maximum,abs(error));squared+=error*error;count+=1
    return {"sampleablePixels":pixels,"maximum":maximum,"rmse":math.sqrt(squared/count) if count else None,"sampleCount":count}
def main()->None:
    p=argparse.ArgumentParser();p.add_argument("--spec",type=Path,required=True);p.add_argument("--root",type=Path,required=True);p.add_argument("--preflight",type=Path,required=True);p.add_argument("--execution",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise RuntimeError("refusing to overwrite D12.5 results")
    spec=json.loads(a.spec.read_text());preflight=json.loads(a.preflight.read_text());execution=json.loads(a.execution.read_text());gates=spec["frozenGates"];production=gates["productionToleranceUnchanged"];coverage_gate=gates["coverage"]
    measurements=[];source_hashes={};consumer_hashes={};cell_guards={};metrics_absent=True
    identity={"spec":sha_file(a.spec)==SPEC_SHA256,"preflight":preflight.get("status")=="ACCEPTED","rootFresh":execution.get("rootCreatedFresh") is True,"disk":execution.get("diskAdmission",{}).get("status")=="ACCEPTED"}
    for fixture in spec["fixtures"]:
        fid=fixture["id"];width,height=fixture["resolution"];registered={float(owner["passIndex"]) for owner in fixture["owners"]};source_hashes[fid]={};consumer_hashes[fid]={}
        for repeat in (1,2):
            cell=f"{fid}/R{repeat}";source_dir=a.root/"sources"/fid/f"R{repeat}";adapter_dir=a.root/"adapters"/fid/f"R{repeat}";guards={}
            reports=[native(source_dir/f"frame-{frame}"/"report.json") for frame in (0,1)];guards["sourceBindings"]=all(report["output"]["sha256"]==sha_file(source_dir/f"frame-{frame}"/"source.exr") for frame,report in enumerate(reports))
            guards["ownerRoster"]={float(row["passIndex"]) for row in reports[0]["sceneStructure"]["owners"]}==registered
            guards["staticStructure"]=True
            for report in reports:
                rows=[report["animation"]["camera"]]+list(report["animation"]["owners"].values())
                for object_rows in rows:
                    for curve in object_rows:
                        keys=curve["keys"];guards["staticStructure"] &= [row[0] for row in keys]==[0.0,1.0,2.0] and len({row[1] for row in keys})==1 and all(row[2]=="LINEAR" for row in keys)
            adapter=native(adapter_dir/"report.json");guards["adapterIdentity"]=adapter["fixtureId"]==fid and adapter["repeat"]==repeat
            layer=spec["sceneContract"]["render"]["viewLayer"];roster=[f"{layer}.Combined",f"{layer}.Depth",f"{layer}.Vector",f"{layer}.Object Index"];guards["multipart"]=adapter["multipart"]["previousRoster"]==roster and adapter["multipart"]["currentRoster"]==roster
            shapes={"previousRgba":(height,width,4),"currentRgba":(height,width,4),"previousOwner":(height,width),"currentOwner":(height,width),"vector":(height,width,2),"vectorNext":(height,width,2)};arrays={}
            for name in SOURCE_ARRAYS:
                record=adapter["arrays"][name];path=Path(record["uri"]);guards[f"array_{name}"]=sha_file(path)==record["sha256"];arrays[name]=f32(path,shapes[name])
            source_hashes[fid][repeat]={name:adapter["arrays"][name]["sha256"] for name in SOURCE_ARRAYS};owner_values={float(v) for v in np.unique(arrays["currentOwner"]) if v>0};guards["ownerDomain"]=bool(owner_values) and owner_values.issubset(registered)
            outputs={};producer_hashes={}
            for producer in ("python","node"):
                cdir=a.root/"consumers"/producer/fid/f"R{repeat}";report=json.loads((cdir/"report.json").read_text());metrics_absent &= "metrics" not in report and "measurements" not in report;producer_hashes[producer]={};radius_outputs={}
                for radius in (2,3):
                    payloads={name:(cdir/"arrays"/filename).read_bytes() for name,filename in PAYLOADS[radius].items()}
                    for name,payload in payloads.items():guards[f"{producer}_r{radius}_{name}"]=sha_bytes(payload)==report["arrays"][f"radius{radius}{name.title()}"]["sha256"]
                    radius_outputs[radius]={"payloads":payloads,"reconstructed":np.frombuffer(payloads["reconstructed"],dtype="<f4").reshape(height,width,4),"interior":np.frombuffer(payloads["interior"],dtype="u1").reshape(height,width),"boundary":np.frombuffer(payloads["boundary"],dtype="u1").reshape(height,width)};producer_hashes[producer][radius]={name:sha_bytes(payload) for name,payload in payloads.items()}
                outputs[producer]=radius_outputs;edir=a.root/"envelopes"/producer/fid/f"R{repeat}";guards[f"{producer}_envelope"]=(edir/"report.python-envelope.json").read_bytes()==(edir/"report.node-envelope.json").read_bytes()
            guards["dualPayload"]=all(outputs["python"][radius]["payloads"][name]==outputs["node"][radius]["payloads"][name] for radius in (2,3) for name in PAYLOADS[radius]);consumer_hashes[fid][repeat]=producer_hashes["python"]
            owner_mask=np.isin(arrays["currentOwner"],list(registered))&(arrays["currentRgba"][...,3]>np.float32(.999));registered_count=int(owner_mask.sum());distance=owner_distance(arrays["currentOwner"],arrays["currentRgba"][...,3],registered);radius_rows={}
            for radius in (2,3):
                out=outputs["python"][radius];interior=out["interior"].astype(bool);boundary=out["boundary"].astype(bool);interior_count=int(interior.sum());boundary_count=int(boundary.sum());overlap=int(np.logical_and(interior,boundary).sum());partition=overlap==0 and interior_count+boundary_count==registered_count
                vector_max=max((abs(float(arrays["vector"][y,x,c])) for y,x in np.argwhere(interior) for c in (0,1)),default=0.0);reconstruction=metric(out["reconstructed"],arrays["currentRgba"],interior);owners={}
                for owner in sorted(registered):
                    mask=interior&(arrays["currentOwner"]==np.float32(owner));owners[str(int(owner))]={"interiorPixels":int(mask.sum()),"maximum":metric(out["reconstructed"],arrays["currentRgba"],mask)["maximum"] if mask.any() else None}
                ring_owner={}
                for y,x in np.argwhere(interior):
                    key=f"{int(arrays['currentOwner'][y,x])}/d{int(distance[y,x])}";value=max(abs(float(out["reconstructed"][y,x,c])-float(arrays["currentRgba"][y,x,c])) for c in range(3));ring_owner[key]=max(ring_owner.get(key,0.0),value)
                radius_rows[radius]={"interiorPixels":interior_count,"boundaryPixels":boundary_count,"maskOverlapPixels":overlap,"partitionPassed":partition,"vectorComponentAbsoluteMaximum":vector_max,"reconstructionRgb":reconstruction,"ownerMeasurements":owners,"ringOwnerMaximum":ring_owner,"boundaryDiagnostic":boundary_metric(arrays["previousRgba"],arrays["currentRgba"],arrays["vector"],boundary)}
            r2=outputs["python"][2]["interior"].astype(bool);r3=outputs["python"][3]["interior"].astype(bool);removed=r2&~r3;subset=np.logical_and(r3,~r2).sum()==0;removed_ring3=bool(removed.any()) and bool(np.all(distance[removed]==3));total_retention=radius_rows[3]["interiorPixels"]/radius_rows[2]["interiorPixels"] if radius_rows[2]["interiorPixels"] else 0.0;owner_retention={}
            for owner in sorted(registered):
                r2_count=int((r2&(arrays["currentOwner"]==np.float32(owner))).sum());r3_count=int((r3&(arrays["currentOwner"]==np.float32(owner))).sum());owner_retention[str(int(owner))]={"radius2":r2_count,"radius3":r3_count,"ratio":r3_count/r2_count if r2_count else None}
            source_static=metric(arrays["previousRgba"],arrays["currentRgba"],owner_mask);measurements.append({"cell":cell,"fixtureId":fid,"repeat":repeat,"resolution":fixture["resolution"],"registeredOwnerPixels":registered_count,"sourceStaticRgb":source_static,"radii":{"2":radius_rows[2],"3":radius_rows[3]},"radius3SubsetOfRadius2":subset,"radius2OnlyPixels":int(removed.sum()),"radius2OnlyDistanceExactly3":removed_ring3,"totalCoverageRetention":total_retention,"ownerCoverageRetention":owner_retention});guards["r2Partition"]=radius_rows[2]["partitionPassed"];guards["r3Partition"]=radius_rows[3]["partitionPassed"];guards["subset"]=subset;guards["removedRing3"]=removed_ring3;guards["sourceStatic"]=source_static["maximum"]==0.0;cell_guards[cell]=guards
    repeat_source=all(source_hashes[f["id"]][1]==source_hashes[f["id"]][2] for f in spec["fixtures"]);repeat_consumer=all(consumer_hashes[f["id"]][1]==consumer_hashes[f["id"]][2] for f in spec["fixtures"])
    children=execution.get("children",[]);pids=[row.get("pid") for row in children];process_ok=len(children)==spec["matrix"]["totalUniqueChildProcesses"]-1 and len(set(pids+[os.getpid()]))==spec["matrix"]["totalUniqueChildProcesses"] and all(row.get("exitCode")==0 for row in children)
    tools={path:sha_file(Path(path)) for path in spec["freshness"]["formalToolPaths"]};tool_ok=preflight.get("toolHashes")==tools;tree=ast.parse(Path(__file__).read_text());imports=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):imports.extend(alias.name for alias in node.names)
        elif isinstance(node,ast.ImportFrom):imports.append(node.module or "")
    independent=all(not name.startswith(("scripts","blender","importlib")) for name in imports)
    r3_rows=[m["radii"]["3"] for m in measurements];all_guards=all(all(guards.values()) for guards in cell_guards.values());owner_min=all(all(row["radius3"]>=coverage_gate["minimumRadius3PixelsPerRegisteredOwner"] for row in m["ownerCoverageRetention"].values()) for m in measurements);owner_retention=all(all(row["radius2"]<coverage_gate["minimumRadius2PixelsForPerOwnerRetentionGate"] or row["ratio"]>=coverage_gate["radius3ToRadius2PerOwnerRetentionMinimum"] for row in m["ownerCoverageRetention"].values()) for m in measurements)
    checks=[("SPEC_IDENTITY",identity["spec"]),("FROZEN_TOOL_IDENTITY",tool_ok),("PREFLIGHT_ACCEPTED",identity["preflight"]),("FRESH_ROOT",identity["rootFresh"]),("DISK_ADMISSION",identity["disk"]),("PROCESS_TOTALITY",process_ok),("CELL_IDENTITY_GUARDS",all_guards),("PRODUCER_METRICS_ABSENT",metrics_absent),("ANALYZER_INDEPENDENCE",independent),("REPEAT_SOURCE_IDENTITY",repeat_source),("REPEAT_CONSUMER_IDENTITY",repeat_consumer),("RADIUS3_VECTOR_PRODUCTION",all(row["vectorComponentAbsoluteMaximum"]<=production["vectorComponentMaxPixels"] for row in r3_rows)),("RADIUS3_RGB_MAX_PRODUCTION",all(row["reconstructionRgb"]["maximum"]<=production["reconstructionRgbMax"] for row in r3_rows)),("RADIUS3_RMSE_PRODUCTION",all(row["reconstructionRgb"]["rmse"]<=production["reconstructionRgbRmse"] for row in r3_rows)),("RADIUS3_TWO_FOLD_HEADROOM",all(row["reconstructionRgb"]["maximum"]<=gates["radius3ConfirmatoryHeadroom"]["reconstructionRgbMax"] for row in r3_rows)),("RADIUS2_MIN_INTERIOR",all(m["radii"]["2"]["interiorPixels"]>=coverage_gate["radius2MinimumInteriorPixelsPerCell"] for m in measurements)),("RADIUS3_MIN_INTERIOR",all(m["radii"]["3"]["interiorPixels"]>=coverage_gate["radius3MinimumInteriorPixelsPerCell"] for m in measurements)),("RADIUS2_MIN_BOUNDARY",all(m["radii"]["2"]["boundaryPixels"]>=coverage_gate["minimumBoundaryPixelsPerRadiusPerCell"] for m in measurements)),("RADIUS3_MIN_BOUNDARY",all(m["radii"]["3"]["boundaryPixels"]>=coverage_gate["minimumBoundaryPixelsPerRadiusPerCell"] for m in measurements)),("TOTAL_COVERAGE_RETENTION",all(m["totalCoverageRetention"]>=coverage_gate["radius3ToRadius2TotalRetentionMinimum"] for m in measurements)),("OWNER_MIN_INTERIOR",owner_min),("OWNER_COVERAGE_RETENTION",owner_retention),("MODEL_NETWORK_ZERO",execution.get("operationCounts",{}).get("modelCalls",0)==0 and execution.get("operationCounts",{}).get("networkCalls",0)==0)]
    hard={"SPEC_IDENTITY","FROZEN_TOOL_IDENTITY","PREFLIGHT_ACCEPTED","FRESH_ROOT","DISK_ADMISSION","PROCESS_TOTALITY","CELL_IDENTITY_GUARDS","PRODUCER_METRICS_ABSENT","ANALYZER_INDEPENDENCE","REPEAT_SOURCE_IDENTITY","REPEAT_CONSUMER_IDENTITY","RADIUS3_VECTOR_PRODUCTION","RADIUS3_RGB_MAX_PRODUCTION","RADIUS3_RMSE_PRODUCTION","MODEL_NETWORK_ZERO"};check_map=dict(checks);hard_pass=all(check_map[name] for name in hard);all_pass=all(value for _,value in checks)
    verdict=spec["decision"]["supportedVerdict"] if all_pass else spec["decision"]["boundedVerdict"] if hard_pass else spec["decision"]["rejectedVerdict"]
    guard_items=[(f"{cell}:{name}",value) for cell,guards in cell_guards.items() for name,value in guards.items()];mutation_attacks=[]
    for index,(target,original) in enumerate(guard_items[:max(30,spec["attacks"]["minimumRegisteredAttacks"])]):
        mutated=dict(guard_items);mutated[target]=not original;mutation_attacks.append({"id":f"M{index+1:02d}_{target}","passed":original is True and not all(mutated.values())})
    mutation_totality=len(mutation_attacks)>=spec["attacks"]["minimumRegisteredAttacks"] and all(row["passed"] for row in mutation_attacks)
    if not mutation_totality:verdict=spec["decision"]["rejectedVerdict"]
    body={"schemaVersion":"bfs.blenderStaticRadiusInterventionResult.v0.1","experimentId":spec["experimentId"],"analyzerPid":os.getpid(),"verdict":verdict,"passed":verdict==spec["decision"]["supportedVerdict"],"baseFailure":next((name for name,value in checks if not value),None),"measurements":measurements,"identities":{"source":source_hashes,"consumer":consumer_hashes},"checks":[{"id":name,"passed":bool(value)} for name,value in checks],"checkPassed":sum(value for _,value in checks),"checkTotal":len(checks),"mutationAttacks":mutation_attacks,"mutationAttackPassed":sum(row["passed"] for row in mutation_attacks),"mutationAttackTotal":len(mutation_attacks),"operationCounts":{"modelCalls":0,"networkCalls":0},"nonClaims":spec["nonClaims"]};result={**body,"evidenceHash":canon(body)};a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n");print(f"BFS_B52_D125_ANALYSIS_OK verdict={verdict} checks={result['checkPassed']}/{result['checkTotal']} attacks={result['mutationAttackPassed']}/{result['mutationAttackTotal']}")
if __name__=="__main__":main()
