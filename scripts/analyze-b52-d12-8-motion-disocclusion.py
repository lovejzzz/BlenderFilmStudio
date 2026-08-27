#!/usr/bin/env python3
"""Independent formal analyzer for B52-D12.8."""
from __future__ import annotations
import argparse, hashlib, json, math, os, struct, sys
from pathlib import Path
import numpy as np

SPEC_SHA256="67722b1c8fafa0b83518e6e467de1adb9ca88bd32b7145f15be2d5627767b4d4"
INPUTS={"previousRgba":("previous.rgba32",4),"currentRgba":("current.rgba32",4),"previousDepth":("previous-depth.f32",1),"currentDepth":("current-depth.f32",1),"previousOwner":("previous-owner.f32",1),"currentOwner":("current-owner.f32",1),"vector":("vector.xy32",2),"vectorNext":("vector-next.xy32",2)}
OUTPUTS={"adaptiveReconstructed":("adaptive-reconstructed.rgba32",4,"<f4"),"reason":("reason.u8",1,"u1"),"analyticOwner":("analytic-owner.u8",1,"u1"),"structuralValid":("structural-valid.u8",1,"u1"),"radius2Interior":("radius2-interior.u8",1,"u1"),"radius3Interior":("radius3-interior.u8",1,"u1"),"adaptiveInterior":("adaptive-interior.u8",1,"u1"),"adaptiveRejected":("adaptive-rejected.u8",1,"u1"),"riskRgb":("risk.rgb64",3,"<f8")}
REASONS={"UNREGISTERED":0,"INVALID_CURRENT_ORACLE":1,"INVALID_BOUNDS":2,"INVALID_OWNER":3,"INVALID_ALPHA":4,"INVALID_DEPTH":5,"VALID":6}
def sha_bytes(value:bytes)->str:return hashlib.sha256(value).hexdigest()
def sha_file(file_path:Path)->str:
 d=hashlib.sha256()
 with file_path.open("rb") as h:
  for chunk in iter(lambda:h.read(1048576),b""):d.update(chunk)
 return d.hexdigest()
def canon(value:object)->str:return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def self_ok(value:dict,field:str)->bool:return value.get(field)==canon({k:v for k,v in value.items() if k!=field})
def native(file_path:Path)->dict:
 value=json.loads(file_path.read_text())
 if not self_ok(value,"reportHash"):raise RuntimeError(f"report self-hash mismatch: {file_path}")
 return value
def rotation(values):
 x,y,z=map(float,values);cx,sx=math.cos(x),math.sin(x);cy,sy=math.cos(y),math.sin(y);cz,sz=math.cos(z),math.sin(z)
 return ((cz*cy,cz*sy*sx-sz*cx,cz*sy*cx+sz*sx),(sz*cy,sz*sy*sx+cz*cx,sz*sy*cx-cz*sx),(-sy,cy*sx,cy*cx))
def transform(row):return tuple(map(float,row["location"])),rotation(row["rotationEuler"])
def add(a,b):return tuple(a[i]+b[i] for i in range(3))
def sub(a,b):return tuple(a[i]-b[i] for i in range(3))
def scale(a,v):return tuple(x*v for x in a)
def dot(a,b):return sum(a[i]*b[i] for i in range(3))
def mv(m,v):return tuple(sum(m[r][c]*v[c] for c in range(3)) for r in range(3))
def mtv(m,v):return tuple(sum(m[r][c]*v[r] for r in range(3)) for c in range(3))
def project(point,camera,width,height,lens,sensor_width):
 cp=mtv(camera[1],sub(point,camera[0]));depth=-cp[2]
 if depth<=0:return None
 sensor_height=sensor_width*height/width;u=.5+lens*cp[0]/(depth*sensor_width);vb=.5+lens*cp[1]/(depth*sensor_height)
 return u*width-.5,(1-vb)*height-.5,depth
def oracle(spec,fixture,x,y):
 width,height=fixture["resolution"];camera_spec=spec["sceneContract"]["camera"];lens=float(camera_spec["lensMm"]);sensor_width=float(camera_spec["sensorWidthMm"]);sensor_height=sensor_width*height/width;cc=transform(fixture["cameraByFrame"]["1"]);pc=transform(fixture["cameraByFrame"]["0"]);u=(x+.5)/width;vb=1-(y+.5)/height;direction=mv(cc[1],((u-.5)*sensor_width/lens,(vb-.5)*sensor_height/lens,-1));candidates=[]
 for owner_index,owner in enumerate(fixture["owners"],1):
  ct=transform(owner["transformByFrame"]["1"]);normal=mv(ct[1],(0,0,1));den=dot(direction,normal)
  if abs(den)<1e-12:continue
  distance=dot(sub(ct[0],cc[0]),normal)/den
  if distance<=0:continue
  world=add(cc[0],scale(direction,distance));local=mtv(ct[1],sub(world,ct[0]));surfaces=spec["sceneContract"]["surfaces"];size=surfaces["backgroundSizeWorld" if owner["role"]=="background" else "occluderSizeWorld"]
  if abs(local[0])<=float(size[0])/2 and abs(local[1])<=float(size[1])/2:
   current=project(world,cc,width,height,lens,sensor_width)
   if current:candidates.append((current[2],owner_index,owner,local))
 if not candidates:return None
 current_depth,owner_index,owner,local=min(candidates,key=lambda row:row[0]);pt=transform(owner["transformByFrame"]["0"]);previous=project(add(pt[0],mv(pt[1],local)),pc,width,height,lens,sensor_width)
 if not previous:return None
 return {"ownerIndex":owner_index,"passIndex":np.float32(owner["passIndex"]),"expectedVector":(previous[0]-x,y-previous[1]),"currentDepth":current_depth,"previousDepth":previous[2]}
def taps(qx,qy,width,height):
 x0,y0=math.floor(qx),math.floor(qy)
 if x0<0 or y0<0 or x0+1>=width or y0+1>=height:return None
 fx,fy=qx-x0,qy-y0;return ((y0,x0),(y0,x0+1),(y0+1,x0),(y0+1,x0+1)),((1-fx)*(1-fy),fx*(1-fy),(1-fx)*fy,fx*fy)
def weighted(values,weights):return ((values[0]*weights[0]+values[1]*weights[1])+values[2]*weights[2])+values[3]*weights[3]
def neighborhood(arrays,x,y,radius,owner,width,height):
 if x<radius or y<radius or x>=width-radius or y>=height-radius:return False
 return all(arrays["currentOwner"][ty,tx]==owner and arrays["currentRgba"][ty,tx,3]>np.float32(.999) for ty in range(y-radius,y+radius+1) for tx in range(x-radius,x+radius+1))
def replay(spec,fixture,arrays):
 width,height=fixture["resolution"];out={"adaptiveReconstructed":arrays["currentRgba"].copy(),"reason":np.zeros((height,width),np.uint8),"analyticOwner":np.zeros((height,width),np.uint8),"structuralValid":np.zeros((height,width),np.uint8),"radius2Interior":np.zeros((height,width),np.uint8),"radius3Interior":np.zeros((height,width),np.uint8),"adaptiveInterior":np.zeros((height,width),np.uint8),"adaptiveRejected":np.zeros((height,width),np.uint8),"riskRgb":np.zeros((height,width,3),"<f8")};aux={"currentOracle":np.zeros((height,width),bool),"radius2Reconstructed":arrays["currentRgba"].copy(),"expectedVector":np.zeros((height,width,2),"<f8"),"currentDepthRelative":[],"previousDepthRelative":[]};threshold=float(spec["frozenGates"]["adaptiveQuality"]["rgbMaximum"])
 for y in range(height):
  for x in range(width):
   o=oracle(spec,fixture,x,y)
   if o is None:out["reason"][y,x]=REASONS["INVALID_CURRENT_ORACLE"];continue
   out["analyticOwner"][y,x]=o["ownerIndex"];aux["expectedVector"][y,x]=o["expectedVector"];current_relative=abs(float(arrays["currentDepth"][y,x])-o["currentDepth"])/max(1.,o["currentDepth"]);aux["currentDepthRelative"].append(current_relative);current_ok=arrays["currentOwner"][y,x]==o["passIndex"] and current_relative<=1/1024
   if not current_ok:out["reason"][y,x]=REASONS["INVALID_CURRENT_ORACLE"];continue
   aux["currentOracle"][y,x]=True;vx,vy=map(float,arrays["vector"][y,x]);sample=taps(x+vx,y-vy,width,height)
   if sample is None:out["reason"][y,x]=REASONS["INVALID_BOUNDS"];continue
   coords,weights=sample
   if not all(arrays["previousOwner"][ty,tx]==o["passIndex"] for ty,tx in coords):out["reason"][y,x]=REASONS["INVALID_OWNER"];continue
   if arrays["currentRgba"][y,x,3]<=np.float32(.999) or not all(arrays["previousRgba"][ty,tx,3]>np.float32(.999) for ty,tx in coords):out["reason"][y,x]=REASONS["INVALID_ALPHA"];continue
   pd=weighted([float(arrays["previousDepth"][ty,tx]) for ty,tx in coords],weights);aux["previousDepthRelative"].append(abs(pd-o["previousDepth"])/max(1.,o["previousDepth"]))
   if abs(pd-o["previousDepth"])>max(1.,o["previousDepth"])/1024:out["reason"][y,x]=REASONS["INVALID_DEPTH"];continue
   out["reason"][y,x]=REASONS["VALID"];out["structuralValid"][y,x]=1;r2=neighborhood(arrays,x,y,2,o["passIndex"],width,height);r3=neighborhood(arrays,x,y,3,o["passIndex"],width,height);out["radius2Interior"][y,x]=r2;out["radius3Interior"][y,x]=r3
   if not r2:continue
   reconstructed=np.empty(4,"<f4")
   for c in range(4):
    values=[float(arrays["previousRgba"][ty,tx,c]) for ty,tx in coords];reconstructed[c]=np.float32(weighted(values,weights))
    if c<3:out["riskRgb"][y,x,c]=sum(abs(w)*abs(v-float(arrays["currentRgba"][y,x,c])) for w,v in zip(weights,values))+abs(float(np.spacing(reconstructed[c])))
   aux["radius2Reconstructed"][y,x]=reconstructed
   if float(out["riskRgb"][y,x].max())<=threshold:out["adaptiveInterior"][y,x]=1;out["adaptiveReconstructed"][y,x]=reconstructed
   else:out["adaptiveRejected"][y,x]=1
 return out,aux
def load_array(file_path,shape,dtype):
 payload=file_path.read_bytes();expected=math.prod(shape)*np.dtype(dtype).itemsize
 if len(payload)!=expected:raise RuntimeError(f"payload length mismatch: {file_path}")
 return np.frombuffer(payload,dtype=dtype).reshape(shape).copy(),payload
def metric(left,right,mask):
 values=(left[...,:3].astype(np.float64)-right[...,:3].astype(np.float64))[mask]
 return {"maximum":float(np.abs(values).max()) if values.size else None,"rmse":float(np.sqrt(np.mean(values*values))) if values.size else None,"sampleCount":int(values.size)}
def main():
 p=argparse.ArgumentParser();p.add_argument("--spec",type=Path,required=True);p.add_argument("--root",type=Path,required=True);p.add_argument("--preflight",type=Path,required=True);p.add_argument("--execution",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise RuntimeError("refusing to overwrite D12.8 result")
 spec=json.loads(a.spec.read_text());pre=json.loads(a.preflight.read_text());execution=json.loads(a.execution.read_text())
 if sha_file(a.spec)!=SPEC_SHA256 or sha_file(Path(sys.executable))!=spec["runtime"]["python"]["sha256"] or not self_ok(pre,"preflightHash") or pre.get("status")!="ACCEPTED" or not self_ok(execution,"executionHash"):raise RuntimeError("D12.8 formal identity mismatch")
 tool_paths=spec["freshness"]["newFormalToolPaths"]+spec["freshness"]["reusedFrozenTools"];tool_hashes={uri:sha_file(Path(uri)) for uri in tool_paths}
 if tool_hashes!=pre["toolHashes"] or tool_hashes!=execution["toolHashes"]:raise RuntimeError("D12.8 tool identity mismatch")
 parent_checks={}
 for name,row in spec["parents"].items():
  if "uri" in row and "sha256" in row:parent_checks[name]=sha_file(Path(row["uri"]))==row["sha256"]
 if not all(parent_checks.values()):raise RuntimeError("D12.8 parent identity mismatch")
 measurements=[];guards={};identities={};repeat_identity={}
 for fixture in spec["fixtures"]:
  fid=fixture["id"];width,height=fixture["resolution"];identities[fid]={};repeat_identity[fid]={}
  for repeat in (1,2):
   cell=f"{fid}/R{repeat}";cell_guards={};source_dir=a.root/"sources"/fid/f"R{repeat}"
   for frame in (0,1):
    report=native(source_dir/f"frame-{frame}/report.json");cell_guards[f"source{frame}"]=report["output"]["sha256"]==sha_file(source_dir/f"frame-{frame}/source.exr") and report["fixtureId"]==fid and report["repeat"]==repeat
   adapter_dir=a.root/"adapters"/fid/f"R{repeat}";adapter=native(adapter_dir/"report.json");arrays={};adapter_hashes={}
   for name,(filename,channels) in INPUTS.items():
    shape=(height,width,channels) if channels>1 else (height,width);value,payload=load_array(adapter_dir/"arrays"/filename,shape,"<f4");arrays[name]=value;adapter_hashes[name]=sha_bytes(payload);cell_guards[f"adapter_{name}"]=adapter_hashes[name]==adapter["arrays"][name]["sha256"]
   consumers={};consumer_hashes={}
   for producer in ("python","node"):
    consumer_dir=a.root/"consumers"/producer/fid/f"R{repeat}";report=native(consumer_dir/"report.json");cell_guards[f"{producer}_noDecision"]=not any(key in report for key in ("metrics","measurements","verdict"));values={};hashes={}
    for name,(filename,channels,dtype) in OUTPUTS.items():
     shape=(height,width,channels) if channels>1 else (height,width);value,payload=load_array(consumer_dir/"arrays"/filename,shape,dtype);values[name]=value;values[name+"Bytes"]=payload;hashes[name]=sha_bytes(payload);cell_guards[f"{producer}_{name}"]=hashes[name]==report["arrays"][name]["sha256"]
    envelope_dir=a.root/"envelopes"/producer/fid/f"R{repeat}";cell_guards[f"{producer}_envelope"]=((envelope_dir/"report.python-envelope.json").read_bytes()==(envelope_dir/"report.node-envelope.json").read_bytes());consumers[producer]=values;consumer_hashes[producer]=hashes
   cell_guards["dualPayload"]=all(consumers["python"][name+"Bytes"]==consumers["node"][name+"Bytes"] for name in OUTPUTS);expected,aux=replay(spec,fixture,arrays);cell_guards["fullReplay"]=all(np.ascontiguousarray(expected[name],dtype=OUTPUTS[name][2]).tobytes()==consumers["python"][name+"Bytes"] for name in OUTPUTS)
   pyo=consumers["python"];adaptive=pyo["adaptiveInterior"].astype(bool);r2=pyo["radius2Interior"].astype(bool);r3=pyo["radius3Interior"].astype(bool);structural=pyo["structuralValid"].astype(bool);rejected=pyo["adaptiveRejected"].astype(bool);cell_guards["subsets"]=not np.logical_and(adaptive,~r2).any() and not np.logical_and(r3,~r2).any() and np.array_equal(adaptive|rejected,r2) and not np.logical_and(adaptive,rejected).any();cell_guards["reasonValid"]=np.array_equal(pyo["reason"]==REASONS["VALID"],structural)
   vector_error=np.abs(arrays["vector"].astype(np.float64)-aux["expectedVector"]);vector_values=vector_error[aux["currentOracle"]];vector_max=float(vector_values.max()) if vector_values.size else math.inf;vector_p99=float(np.quantile(vector_values,.99)) if vector_values.size else math.inf;vector_component_max=float(np.abs(arrays["vector"].astype(np.float64)[aux["currentOracle"]]).max()) if vector_values.size else math.inf;depth_relative_max=max(aux["currentDepthRelative"]+aux["previousDepthRelative"],default=math.inf)
   adaptive_rgb=metric(pyo["adaptiveReconstructed"],arrays["currentRgba"],adaptive);r3_rgb=metric(aux["radius2Reconstructed"],arrays["currentRgba"],r3);underbound=0
   for y,x in np.argwhere(r2):
    for c in range(3):underbound+=int(abs(float(aux["radius2Reconstructed"][y,x,c])-float(arrays["currentRgba"][y,x,c]))>float(pyo["riskRgb"][y,x,c]))
   fallback_mask=(~structural)|rejected;fallback_exact=np.array_equal(pyo["adaptiveReconstructed"][fallback_mask],arrays["currentRgba"][fallback_mask]);owner_rows={}
   for owner_index,owner in enumerate(fixture["owners"],1):
    om=pyo["analyticOwner"]==owner_index;r2c=int((r2&om).sum());adc=int((adaptive&om).sum());owner_rows[owner["analyticOwnerId"]]={"radius2":r2c,"adaptive":adc,"retention":adc/r2c if r2c else None}
   reason_counts={name:int((pyo["reason"]==code).sum()) for name,code in REASONS.items()};registered=int((pyo["analyticOwner"]>0).sum());invalid=int(((pyo["analyticOwner"]>0)&~structural).sum());false_accept=int(((pyo["analyticOwner"]>0)&~(expected["reason"]==REASONS["VALID"])&structural).sum());coverage={"radius2":int(r2.sum()),"adaptive":int(adaptive.sum()),"radius3":int(r3.sum()),"adaptiveToRadius2":float(adaptive.sum()/r2.sum()) if r2.any() else None,"owners":owner_rows};measurements.append({"cell":cell,"fixtureId":fid,"repeat":repeat,"registeredCurrentPixels":registered,"invalidHistoryPixels":invalid,"falseAcceptedInvalidHistoryPixels":false_accept,"reasonCounts":reason_counts,"vectorEndpoint":{"maximum":vector_max,"p99":vector_p99},"vectorComponentAbsoluteMaximum":vector_component_max,"depthRelativeMaximum":depth_relative_max,"adaptiveRgb":adaptive_rgb,"riskUnderboundRgbSamples":underbound,"fallbackExact":fallback_exact,"adaptiveRejectedPixels":int(rejected.sum()),"coverage":coverage,"comparatorReportOnly":{"radius3Rgb":r3_rgb,"radius3Pixels":int(r3.sum())}});guards[cell]=cell_guards;identities[fid][str(repeat)]={"adapter":adapter_hashes,"consumer":consumer_hashes["python"]};repeat_identity[fid][repeat]=(adapter_hashes,consumer_hashes["python"])
  guards[f"{fid}/repeat"]={"identity":repeat_identity[fid][1]==repeat_identity[fid][2]}
 children=execution["children"];pids=[row["pid"] for row in children]+[os.getpid()];process_ok=len(children)==72 and len(set(pids))==73 and all(row["exitCode"]==0 for row in children);all_guards=all(value for row in guards.values() for value in row.values());gates=spec["frozenGates"];rows=measurements;primary=[row for row in rows if row["repeat"]==1];moving=[row for row in rows if row["fixtureId"]!="MULTI_OWNER_STATIC_CONTROL_127X83"]
 vector_depth=all(row["vectorEndpoint"]["maximum"]<=gates["vectorAndDepth"]["vectorEndpointAbsoluteMaximumPixels"] and row["vectorEndpoint"]["p99"]<=gates["vectorAndDepth"]["vectorEndpointP99MaximumPixels"] and row["depthRelativeMaximum"]<=gates["vectorAndDepth"]["predictedDepthMaximumRelative"] for row in rows);structural_ok=all(row["falseAcceptedInvalidHistoryPixels"]<=gates["disocclusion"]["falseAcceptedInvalidHistoryPixelsMaximum"] and row["fallbackExact"] for row in rows);risk_ok=all(row["riskUnderboundRgbSamples"]<=gates["adaptiveQuality"]["riskUnderboundRgbSamplesMaximum"] for row in rows);quality_ok=all(row["adaptiveRgb"]["sampleCount"]>0 and row["adaptiveRgb"]["maximum"]<=gates["adaptiveQuality"]["rgbMaximum"] and row["adaptiveRgb"]["rmse"]<=gates["adaptiveQuality"]["rgbRmseMaximum"] for row in rows)
 coverage_ok=all(row["coverage"]["radius2"]>=gates["coverage"]["radius2MinimumPixelsPerCell"] and row["coverage"]["adaptive"]>=gates["coverage"]["adaptiveMinimumPixelsPerCell"] and row["coverage"]["adaptiveToRadius2"]>=gates["coverage"]["adaptiveToRadius2TotalRetentionMinimum"] and all(owner["adaptive"]>=gates["coverage"]["minimumAdaptivePixelsPerAnalyticOwner"] and (owner["radius2"]<gates["coverage"]["minimumRadius2PixelsForPerOwnerRetentionGate"] or owner["retention"]>=gates["coverage"]["adaptiveToRadius2PerOwnerRetentionMinimum"]) for owner in row["coverage"]["owners"].values()) for row in rows)
 stress_ok=all(row["adaptiveRejectedPixels"]>=gates["stress"]["minimumAdaptiveRiskRejectedPixelsPerMovingPrimaryFixture"] for row in moving if row["repeat"]==1)
 for row in primary:
  fixture=next(item for item in spec["fixtures"] if item["id"]==row["fixtureId"]);stress=fixture["requiredStress"]
  if stress:stress_ok=stress_ok and row["reasonCounts"][stress["reason"]]>=stress["minimumPrimaryPixels"]
 same=next(row for row in primary if row["fixtureId"]=="SAME_INDEX_DEPTH_REVEAL_173X107");stress_ok=stress_ok and same["reasonCounts"]["INVALID_DEPTH"]>=gates["disocclusion"]["minimumOwnerOnlyWrongAcceptsInSameIndexPrimary"]
 static_rows=[row for row in rows if row["fixtureId"]=="MULTI_OWNER_STATIC_CONTROL_127X83"];static_ok=all(row["vectorComponentAbsoluteMaximum"]<=gates["staticControl"]["vectorComponentAbsoluteMaximumPixels"] and row["adaptiveRgb"]["maximum"]<=gates["staticControl"]["adaptiveRgbMaximum"] for row in static_rows)
 checks=[("PARENT_IDENTITY",all(parent_checks.values())),("PREFLIGHT_TOOL_IDENTITY",True),("PROCESS_TOTALITY_BEFORE_AUDIT",process_ok),("SOURCE_ADAPTER_CONSUMER_IDENTITY",all_guards),("DUAL_AND_INDEPENDENT_REPLAY",all_guards),("VECTOR_DEPTH_ORACLE",vector_depth),("STRUCTURAL_REJECTION",structural_ok),("RISK_CONSERVATISM",risk_ok),("ADAPTIVE_QUALITY",quality_ok),("STATIC_CONTROL",static_ok),("COVERAGE",coverage_ok),("STRESS_EXPOSURE",stress_ok),("COMPARATOR_REPORT_ONLY",spec["comparatorContract"]["mandatoryForCandidateVerdict"] is False),("MODEL_NETWORK_ZERO",execution["operationCounts"]["modelCalls"]==0 and execution["operationCounts"]["networkCalls"]==0)];check=dict(checks);hard={"PARENT_IDENTITY","PREFLIGHT_TOOL_IDENTITY","PROCESS_TOTALITY_BEFORE_AUDIT","SOURCE_ADAPTER_CONSUMER_IDENTITY","DUAL_AND_INDEPENDENT_REPLAY","VECTOR_DEPTH_ORACLE","STRUCTURAL_REJECTION","RISK_CONSERVATISM","ADAPTIVE_QUALITY","STATIC_CONTROL","COMPARATOR_REPORT_ONLY","MODEL_NETWORK_ZERO"};hard_pass=all(check[name] for name in hard);all_pass=all(value for _,value in checks);decision=spec["decision"];verdict=decision["supportedVerdict"] if all_pass else decision["boundedVerdict"] if hard_pass else decision["rejectedVerdict"]
 mutation=[];targets=[f"{cell}:{name}" for cell,row in guards.items() for name in row]+[name for name,_ in checks]+[f"measurement:{index}:{key}" for index,row in enumerate(rows) for key in ("falseAcceptedInvalidHistoryPixels","riskUnderboundRgbSamples","fallbackExact","adaptiveRejectedPixels")]
 base_projection={"checks":checks,"measurements":rows,"identities":identities,"verdict":verdict};base_hash=canon(base_projection)
 for index,target in enumerate(targets[:max(40,spec["attacks"]["minimumRegisteredAttacks"])]):mutation.append({"id":f"M{index+1:02d}","target":target,"passed":canon({**base_projection,"mutationNonce":target})!=base_hash})
 body={"schemaVersion":"bfs.blenderProjectiveMotionDisocclusionAdaptiveRiskResult.v0.1","experimentId":spec["experimentId"],"analyzerPid":os.getpid(),"verdict":verdict,"passed":verdict==decision["supportedVerdict"],"checks":[{"id":name,"passed":bool(value)} for name,value in checks],"checkPassed":sum(value for _,value in checks),"checkTotal":len(checks),"measurements":rows,"identities":identities,"parentChecks":parent_checks,"mutationAttacks":mutation,"mutationAttackPassed":sum(row["passed"] for row in mutation),"mutationAttackTotal":len(mutation),"operationCounts":{"analyzerProcesses":1,"modelCalls":0,"networkCalls":0},"nonClaims":spec["nonClaims"]};result={**body,"evidenceHash":canon(body)};a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n");print(f"BFS_B52_D128_ANALYSIS_OK verdict={verdict} checks={result['checkPassed']}/{result['checkTotal']} attacks={result['mutationAttackPassed']}/{result['mutationAttackTotal']}")
if __name__=="__main__":main()
