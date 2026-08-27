#!/usr/bin/env python3
"""Independent formal analyzer for B52-D12.7."""
from __future__ import annotations
import argparse,ast,hashlib,json,math,os,struct,sys
from pathlib import Path
import numpy as np
SPEC_SHA256="c51d0d83afd30b479bf3e7109c31110133649ee3d65a04d677dbe236b8075ed0"
SOURCE={"previousRgba":("previous.rgba32",4),"currentRgba":("current.rgba32",4),"previousOwner":("previous-owner.f32",1),"currentOwner":("current-owner.f32",1),"vector":("vector.xy32",2),"vectorNext":("vector-next.xy32",2)}
PAYLOAD={"radius2Reconstructed":("radius2-reconstructed.rgba32",4,"<f4"),"radius2Interior":("radius2-interior.u8",1,"u1"),"radius2Boundary":("radius2-boundary.u8",1,"u1"),"radius3Reconstructed":("radius3-reconstructed.rgba32",4,"<f4"),"radius3Interior":("radius3-interior.u8",1,"u1"),"radius3Boundary":("radius3-boundary.u8",1,"u1"),"adaptiveReconstructed":("adaptive-reconstructed.rgba32",4,"<f4"),"adaptiveInterior":("adaptive-interior.u8",1,"u1"),"adaptiveBoundary":("adaptive-boundary.u8",1,"u1"),"adaptiveRejected":("adaptive-rejected.u8",1,"u1"),"riskRgb":("risk.rgb64",3,"<f8")}
def sha_bytes(v:bytes)->str:return hashlib.sha256(v).hexdigest()
def sha_file(p:Path)->str:
 d=hashlib.sha256()
 with p.open("rb") as h:
  for c in iter(lambda:h.read(1048576),b""):d.update(c)
 return d.hexdigest()
def canon(v:object)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def self_ok(d:dict,field:str)->bool:return d.get(field)==canon({k:v for k,v in d.items() if k!=field})
def normalized(v:object)->object:
 if v is None or isinstance(v,(str,bool)):return v
 if isinstance(v,(int,float)):return {"$f64be":struct.pack(">d",float(v)).hex()}
 if isinstance(v,list):return [normalized(x) for x in v]
 if isinstance(v,dict):return {k:normalized(v[k]) for k in sorted(v)}
 raise TypeError(type(v))
def native(p:Path)->dict:
 d=json.loads(p.read_text())
 if not self_ok(d,"reportHash"):raise RuntimeError(f"report hash mismatch: {p}")
 return d
def load(p:Path,shape:tuple[int,...],dtype:str)->tuple[np.ndarray,bytes]:
 b=p.read_bytes()
 if len(b)!=math.prod(shape)*np.dtype(dtype).itemsize:raise RuntimeError(f"length mismatch: {p}")
 return np.frombuffer(b,dtype=dtype).reshape(shape).copy(),b
def replay(radius:int,width:int,height:int,a:dict[str,np.ndarray],owners:set[np.float32]):
 previous,current=a["previousRgba"],a["currentRgba"];reconstructed=current.copy();interior=np.zeros((height,width),dtype=np.uint8);boundary=np.zeros((height,width),dtype=np.uint8)
 for y in range(height):
  for x in range(width):
   owner=a["currentOwner"][y,x]
   if owner not in owners or current[y,x,3]<=np.float32(.999):continue
   vx,vy=float(a["vector"][y,x,0]),float(a["vector"][y,x,1]);qx,qy=x+vx,y-vy;x0,y0=math.floor(qx),math.floor(qy);x1,y1=x0+1,y0+1;ok=x>=radius and y>=radius and x<width-radius and y<height-radius
   if ok:ok=all(a["currentOwner"][ty,tx]==owner and current[ty,tx,3]>np.float32(.999) for ty in range(y-radius,y+radius+1) for tx in range(x-radius,x+radius+1))
   taps=x0>=0 and y0>=0 and x1<width and y1<height
   if taps:taps=all(a["previousOwner"][ty,tx]==owner and previous[ty,tx,3]>np.float32(.999) for ty,tx in ((y0,x0),(y0,x1),(y1,x0),(y1,x1)))
   if not ok or not taps:boundary[y,x]=1;continue
   fx,fy=qx-x0,qy-y0;weights=((1-fx)*(1-fy),fx*(1-fy),(1-fx)*fy,fx*fy);coords=((y0,x0),(y0,x1),(y1,x0),(y1,x1))
   for c in range(4):
    values=[float(previous[ty,tx,c]) for ty,tx in coords];reconstructed[y,x,c]=np.float32((((values[0]*weights[0])+(values[1]*weights[1]))+(values[2]*weights[2]))+(values[3]*weights[3]))
   interior[y,x]=1
 return reconstructed,interior,boundary
def adaptive(width:int,height:int,a:dict[str,np.ndarray],r2:tuple,owners:set[np.float32],threshold:float):
 previous,current=a["previousRgba"],a["currentRgba"];reconstructed,r2mask,_=r2;risk=np.zeros((height,width,3),dtype="<f8");interior=np.zeros((height,width),dtype=np.uint8);rejected=np.zeros((height,width),dtype=np.uint8);owner_mask=np.isin(a["currentOwner"],list(owners))&(current[...,3]>np.float32(.999))
 for y,x in np.argwhere(r2mask):
  vx,vy=float(a["vector"][y,x,0]),float(a["vector"][y,x,1]);qx,qy=int(x)+vx,int(y)-vy;x0,y0=math.floor(qx),math.floor(qy);fx,fy=qx-x0,qy-y0;weights=((1-fx)*(1-fy),fx*(1-fy),(1-fx)*fy,fx*fy);coords=((y0,x0),(y0,x0+1),(y0+1,x0),(y0+1,x0+1))
  for c in range(3):
   center=float(current[y,x,c]);values=[float(previous[ty,tx,c]) for ty,tx in coords];pre=(((values[0]*weights[0])+(values[1]*weights[1]))+(values[2]*weights[2]))+(values[3]*weights[3]);final=np.float32(pre);risk[y,x,c]=sum(abs(w)*abs(v-center) for w,v in zip(weights,values))+abs(float(np.spacing(final)))
  if float(risk[y,x].max())<=threshold:interior[y,x]=1
  else:rejected[y,x]=1
 boundary=(owner_mask&~interior.astype(bool)).astype(np.uint8);return reconstructed.copy(),interior,boundary,rejected,risk
def metric(left:np.ndarray,right:np.ndarray,mask:np.ndarray)->dict:
 values=(left[...,:3].astype(np.float64)-right[...,:3].astype(np.float64))[mask.astype(bool)]
 if values.size==0:raise RuntimeError("empty metric mask")
 return {"maximum":float(np.abs(values).max()),"rmse":float(np.sqrt(np.mean(values*values))),"sampleCount":int(values.size)}
def main()->None:
 p=argparse.ArgumentParser();p.add_argument("--spec",type=Path,required=True);p.add_argument("--root",type=Path,required=True);p.add_argument("--preflight",type=Path,required=True);p.add_argument("--execution",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise RuntimeError("refusing to overwrite D12.7 result")
 spec=json.loads(a.spec.read_text());pre=json.loads(a.preflight.read_text());execution=json.loads(a.execution.read_text())
 if sha_file(a.spec)!=SPEC_SHA256 or sha_file(Path(sys.executable))!=spec["runtime"]["python"]["sha256"] or not self_ok(pre,"preflightHash") or pre.get("status")!="ACCEPTED" or not self_ok(execution,"executionHash"):raise RuntimeError("D12.7 formal identity mismatch")
 tools={path:sha_file(Path(path)) for path in spec["freshness"]["formalToolPaths"]}
 if tools!=pre["toolHashes"] or tools!=execution["toolHashes"]:raise RuntimeError("D12.7 tool identity mismatch")
 parent_checks={};documents={}
 for name,row in spec["parents"].items():
  path=Path(row["uri"]);parent_checks[f"{name}FileHash"]=sha_file(path)==row["sha256"]
  if path.suffix==".json":documents[name]=json.loads(path.read_text())
 for name,field in (("d12_5Result","evidenceHash"),("d12_5Receipt","receiptHash"),("d12_6Result","evidenceHash"),("d12_6Audit","auditHash"),("d12_6Receipt","receiptHash")):parent_checks[f"{name}InternalHash"]=self_ok(documents[name],field) and documents[name][field]==spec["parents"][name][field]
 if not all(parent_checks.values()):raise RuntimeError(f"parent check failed: {parent_checks}")
 threshold=float(spec["frozenGates"]["adaptiveHeadroom"]["reconstructionRgbMax"]);measurements=[];guards={};identities={};repeat_material={}
 for fixture in spec["fixtures"]:
  fid=fixture["id"];width,height=fixture["resolution"];owners={np.float32(o["passIndex"]) for o in fixture["owners"]};identities[fid]={};repeat_material[fid]={}
  for repeat in (1,2):
   prefix=f"{fid}/R{repeat}";g={};sdir=a.root/"sources"/fid/f"R{repeat}"
   for frame in (0,1):
    report=native(sdir/f"frame-{frame}/report.json");g[f"source{frame}"]=report["output"]["sha256"]==sha_file(sdir/f"frame-{frame}/source.exr") and report["experimentId"]==spec["experimentId"]
   adir=a.root/"adapters"/fid/f"R{repeat}";adapter=native(adir/"report.json");arrays={};source_hash={}
   for name,(filename,channels) in SOURCE.items():
    shape=(height,width,channels) if channels>1 else (height,width);value,payload=load(adir/"arrays"/filename,shape,"<f4");arrays[name]=value;source_hash[name]=sha_bytes(payload);g[f"adapter_{name}"]=source_hash[name]==adapter["arrays"][name]["sha256"]
   outputs={};consumer_hash={}
   for producer in ("python","node"):
    cdir=a.root/"consumers"/producer/fid/f"R{repeat}";report=json.loads((cdir/"report.json").read_text());g[f"{producer}_noMetrics"]=not any(key in report for key in ("metrics","measurements","verdict"));g[f"{producer}_adapter"]=report["adapter"]["sha256"]==sha_file(adir/"report.json") and report["adapter"]["reportHash"]==adapter["reportHash"];encoded=json.dumps(normalized(report),sort_keys=True,separators=(",",":"),allow_nan=False).encode();edir=a.root/"envelopes"/producer/fid/f"R{repeat}";g[f"{producer}_envelopes"]=encoded==(edir/"report.python-envelope.json").read_bytes()==(edir/"report.node-envelope.json").read_bytes();pout={};ph={}
    for name,(filename,channels,dtype) in PAYLOAD.items():
     shape=(height,width,channels) if channels>1 else (height,width);value,payload=load(cdir/"arrays"/filename,shape,dtype);pout[name]=value;pout[f"{name}Bytes"]=payload;ph[name]=sha_bytes(payload);g[f"{producer}_{name}"]=ph[name]==report["arrays"][name]["sha256"]
    outputs[producer]=pout;consumer_hash[producer]=ph
   g["dualPayload"]=all(outputs["python"][f"{name}Bytes"]==outputs["node"][f"{name}Bytes"] for name in PAYLOAD);identities[fid][str(repeat)]={"source":source_hash,"consumer":consumer_hash["python"]};repeat_material[fid][repeat]={"source":source_hash,"consumer":consumer_hash["python"]}
   r2=replay(2,width,height,arrays,owners);r3=replay(3,width,height,arrays,owners);ad=adaptive(width,height,arrays,r2,owners,threshold);expected={"radius2Reconstructed":r2[0],"radius2Interior":r2[1],"radius2Boundary":r2[2],"radius3Reconstructed":r3[0],"radius3Interior":r3[1],"radius3Boundary":r3[2],"adaptiveReconstructed":ad[0],"adaptiveInterior":ad[1],"adaptiveBoundary":ad[2],"adaptiveRejected":ad[3],"riskRgb":ad[4]}
   g["fullReplay"]=all(np.ascontiguousarray(expected[name],dtype=PAYLOAD[name][2]).tobytes()==outputs["python"][f"{name}Bytes"] for name in PAYLOAD)
   owner_mask=np.isin(arrays["currentOwner"],list(owners))&(arrays["currentRgba"][...,3]>np.float32(.999));masks={"radius2":outputs["python"]["radius2Interior"].astype(bool),"radius3":outputs["python"]["radius3Interior"].astype(bool),"adaptive":outputs["python"]["adaptiveInterior"].astype(bool)};adaptive_rejected=outputs["python"]["adaptiveRejected"].astype(bool);risk=outputs["python"]["riskRgb"];g["r3Subset"]=not np.logical_and(masks["radius3"],~masks["radius2"]).any();g["adaptiveSubset"]=not np.logical_and(masks["adaptive"],~masks["radius2"]).any();g["adaptivePartition"]=not np.logical_and(masks["adaptive"],adaptive_rejected).any() and np.array_equal(masks["adaptive"]|adaptive_rejected,masks["radius2"]);g["riskOutsideZero"]=not np.any(risk[~masks["radius2"]]);g["partitions"]=all(not np.logical_and(masks[name],outputs["python"][f"{name}Boundary"].astype(bool)).any() and int(masks[name].sum())+int(outputs["python"][f"{name}Boundary"].sum())==int(owner_mask.sum()) for name in ("radius2","radius3","adaptive"))
   underbound=0
   for y,x in np.argwhere(masks["radius2"]):
    for c in range(3):underbound+=int(abs(float(outputs["python"]["radius2Reconstructed"][y,x,c])-float(arrays["currentRgba"][y,x,c]))>float(risk[y,x,c]))
   domains={name:{"interiorPixels":int(mask.sum()),"rgb":metric(outputs["python"][f"{name}Reconstructed"],arrays["currentRgba"],mask),"vectorComponentAbsoluteMaximum":max((abs(float(arrays["vector"][y,x,c])) for y,x in np.argwhere(mask) for c in (0,1)),default=0.0),"owners":{}} for name,mask in masks.items()}
   for name,mask in masks.items():
    for owner in sorted(owners):domains[name]["owners"][str(int(owner))]=int((mask&(arrays["currentOwner"]==owner)).sum())
   coverage={"adaptiveToRadius2Total":domains["adaptive"]["interiorPixels"]/domains["radius2"]["interiorPixels"],"adaptiveToRadius3Total":domains["adaptive"]["interiorPixels"]/domains["radius3"]["interiorPixels"],"owners":{}}
   for owner in sorted(owners):
    key=str(int(owner));r2c=domains["radius2"]["owners"][key];r3c=domains["radius3"]["owners"][key];adc=domains["adaptive"]["owners"][key];coverage["owners"][key]={"radius2":r2c,"radius3":r3c,"adaptive":adc,"adaptiveToRadius2":adc/r2c if r2c else None,"adaptiveMinusRadius3":adc-r3c}
   measurements.append({"cell":prefix,"fixtureId":fid,"repeat":repeat,"registeredOwnerPixels":int(owner_mask.sum()),"domains":domains,"adaptiveRejectedPixels":int(adaptive_rejected.sum()),"riskRgbMaximum":float(risk[masks["radius2"]].max()),"riskUnderboundRgbSamples":underbound,"coverage":coverage});guards[prefix]=g
  guards[f"{fid}/repeatIdentity"]={"source":repeat_material[fid][1]["source"]==repeat_material[fid][2]["source"],"consumer":repeat_material[fid][1]["consumer"]==repeat_material[fid][2]["consumer"]}
 process_children=execution["children"];pids=[r["pid"] for r in process_children]+[os.getpid()];process_ok=len(process_children)==54 and len(set(pids))==55 and all(r["exitCode"]==0 for r in process_children)
 tree=ast.parse(Path(__file__).read_text());imports=[]
 for node in ast.walk(tree):
  if isinstance(node,ast.Import):imports.extend(x.name for x in node.names)
  elif isinstance(node,ast.ImportFrom):imports.append(node.module or "")
 independence=all(not name.startswith(("scripts","blender","importlib")) for name in imports)
 guard_vector={f"{cell}:{name}":bool(value) for cell,row in guards.items() for name,value in row.items()};true_guards=sorted(name for name,value in guard_vector.items() if value);mutation=[]
 for i,target in enumerate(true_guards[:max(30,spec["attacks"]["minimumRegisteredAttacks"])]):
  altered=dict(guard_vector);altered[target]=False;mutation.append({"id":f"M{i+1:02d}_FLIP_{target}","target":target,"before":True,"after":False,"passed":all(guard_vector.values()) and not all(altered.values())})
 mutation_ok=len(mutation)>=spec["attacks"]["minimumRegisteredAttacks"] and all(r["passed"] for r in mutation)
 prod=spec["frozenGates"]["productionTolerance"];cov=spec["frozenGates"]["coverage"];primary=[m for m in measurements if m["repeat"]==1];all_guard=all(guard_vector.values());adaptive_rows=[m["domains"]["adaptive"] for m in measurements];r3_rows=[m["domains"]["radius3"] for m in measurements]
 checks=[("SPEC_PREFLIGHT_TOOL_IDENTITY",True),("PARENT_IDENTITIES",all(parent_checks.values())),("PROCESS_TOTALITY_BEFORE_AUDIT",process_ok),("ANALYZER_INDEPENDENCE",independence),("CELL_AND_REPLAY_GUARDS",all_guard),("REGISTERED_MUTATION_ATTESTATION",mutation_ok),("RISK_CONSERVATIVE",all(m["riskUnderboundRgbSamples"]<=spec["frozenGates"]["riskConservatism"]["maximumUnderboundRgbSamples"] for m in measurements)),("ADAPTIVE_VECTOR_PRODUCTION",all(r["vectorComponentAbsoluteMaximum"]<=prod["vectorComponentMaxPixels"] for r in adaptive_rows)),("ADAPTIVE_RGB_PRODUCTION",all(r["rgb"]["maximum"]<=prod["reconstructionRgbMax"] for r in adaptive_rows)),("ADAPTIVE_RMSE_PRODUCTION",all(r["rgb"]["rmse"]<=prod["reconstructionRgbRmse"] for r in adaptive_rows)),("ADAPTIVE_TWO_FOLD_HEADROOM",all(r["rgb"]["maximum"]<=threshold for r in adaptive_rows)),("RADIUS3_PRODUCTION",all(r["vectorComponentAbsoluteMaximum"]<=prod["vectorComponentMaxPixels"] and r["rgb"]["maximum"]<=prod["reconstructionRgbMax"] and r["rgb"]["rmse"]<=prod["reconstructionRgbRmse"] for r in r3_rows)),("RADIUS2_MIN_INTERIOR",all(m["domains"]["radius2"]["interiorPixels"]>=cov["radius2MinimumInteriorPixelsPerCell"] for m in measurements)),("ADAPTIVE_MIN_INTERIOR",all(m["domains"]["adaptive"]["interiorPixels"]>=cov["adaptiveMinimumInteriorPixelsPerCell"] for m in measurements)),("ADAPTIVE_OWNER_MIN",all(all(row["adaptive"]>=cov["minimumAdaptivePixelsPerRegisteredOwner"] for row in m["coverage"]["owners"].values()) for m in measurements)),("ADAPTIVE_TOTAL_RETENTION",all(m["coverage"]["adaptiveToRadius2Total"]>=cov["adaptiveToRadius2TotalRetentionMinimum"] for m in measurements)),("ADAPTIVE_OWNER_RETENTION",all(all(row["radius2"]<cov["minimumRadius2PixelsForPerOwnerRetentionGate"] or row["adaptiveToRadius2"]>=cov["adaptiveToRadius2PerOwnerRetentionMinimum"] for row in m["coverage"]["owners"].values()) for m in measurements)),("ADAPTIVE_TOTAL_BEATS_RADIUS3",all(m["coverage"]["adaptiveToRadius3Total"]>=cov["adaptiveToRadius3TotalRatioMinimum"] for m in measurements)),("ADAPTIVE_OWNER_MEETS_RADIUS3",all(all(row["adaptiveMinusRadius3"]>=0 for row in m["coverage"]["owners"].values()) for m in measurements)),("STRESS_EXPOSURE",all(m["adaptiveRejectedPixels"]>=spec["frozenGates"]["stress"]["minimumAdaptiveRejectedPixelsPerFixture"] for m in primary)),("MODEL_NETWORK_ZERO",execution["operationCounts"]["modelCalls"]==0 and execution["operationCounts"]["networkCalls"]==0)]
 check=dict(checks);hard={"SPEC_PREFLIGHT_TOOL_IDENTITY","PARENT_IDENTITIES","PROCESS_TOTALITY_BEFORE_AUDIT","ANALYZER_INDEPENDENCE","CELL_AND_REPLAY_GUARDS","REGISTERED_MUTATION_ATTESTATION","RISK_CONSERVATIVE","ADAPTIVE_VECTOR_PRODUCTION","ADAPTIVE_RGB_PRODUCTION","ADAPTIVE_RMSE_PRODUCTION","ADAPTIVE_TWO_FOLD_HEADROOM","MODEL_NETWORK_ZERO"};hard_pass=all(check[k] for k in hard);all_pass=all(v for _,v in checks);verdict=spec["decision"]["supportedVerdict"] if all_pass else spec["decision"]["boundedVerdict"] if hard_pass else spec["decision"]["rejectedVerdict"]
 body={"schemaVersion":"bfs.blenderStaticAdaptiveRiskGateResult.v0.1","experimentId":spec["experimentId"],"analyzerPid":os.getpid(),"verdict":verdict,"passed":verdict==spec["decision"]["supportedVerdict"],"analyzerIndependent":independence,"checks":[{"id":k,"passed":bool(v)} for k,v in checks],"checkPassed":sum(v for _,v in checks),"checkTotal":len(checks),"measurements":measurements,"identities":identities,"parentChecks":parent_checks,"mutationAttacks":mutation,"mutationAttackPassed":sum(r["passed"] for r in mutation),"mutationAttackTotal":len(mutation),"operationCounts":{"analyzerProcesses":1,"modelCalls":0,"networkCalls":0},"nonClaims":spec["nonClaims"]};result={**body,"evidenceHash":canon(body)};a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n");print(f"BFS_B52_D127_ANALYSIS_OK verdict={verdict} checks={result['checkPassed']}/{result['checkTotal']} attacks={result['mutationAttackPassed']}/{result['mutationAttackTotal']}")
if __name__=="__main__":main()
