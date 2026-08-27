#!/usr/bin/env python3
"""C1 audit-only replay with analyzer mutation-roster protection for B52-D12.7."""
from __future__ import annotations

import argparse, ast, copy, hashlib, json, math, os, sys
from pathlib import Path
import numpy as np

SPEC_SHA256="c51d0d83afd30b479bf3e7109c31110133649ee3d65a04d677dbe236b8075ed0"
CORRECTION_SPEC_SHA256="d66a40dffd8688e28d1887a2b6834e55f8345c9a5ca3bcca3c099fdebc223678"
SOURCE={"previousRgba":("previous.rgba32",4),"currentRgba":("current.rgba32",4),"previousOwner":("previous-owner.f32",1),"currentOwner":("current-owner.f32",1),"vector":("vector.xy32",2),"vectorNext":("vector-next.xy32",2)}
PAYLOAD={"radius2Reconstructed":("radius2-reconstructed.rgba32",4,"<f4"),"radius2Interior":("radius2-interior.u8",1,"u1"),"radius2Boundary":("radius2-boundary.u8",1,"u1"),"radius3Reconstructed":("radius3-reconstructed.rgba32",4,"<f4"),"radius3Interior":("radius3-interior.u8",1,"u1"),"radius3Boundary":("radius3-boundary.u8",1,"u1"),"adaptiveReconstructed":("adaptive-reconstructed.rgba32",4,"<f4"),"adaptiveInterior":("adaptive-interior.u8",1,"u1"),"adaptiveBoundary":("adaptive-boundary.u8",1,"u1"),"adaptiveRejected":("adaptive-rejected.u8",1,"u1"),"riskRgb":("risk.rgb64",3,"<f8")}

def sha_bytes(value:bytes)->str:return hashlib.sha256(value).hexdigest()
def sha(path:Path)->str:
 d=hashlib.sha256()
 with path.open("rb") as h:
  for chunk in iter(lambda:h.read(1048576),b""):d.update(chunk)
 return d.hexdigest()
def canon(value:object)->str:return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def self_ok(document:dict,field:str)->bool:return document.get(field)==canon({k:v for k,v in document.items() if k!=field})
def arr(path:Path,shape:tuple[int,...],dtype:str)->np.ndarray:
 payload=path.read_bytes()
 if len(payload)!=math.prod(shape)*np.dtype(dtype).itemsize:raise RuntimeError(f"length mismatch: {path}")
 return np.frombuffer(payload,dtype=dtype).reshape(shape).copy()
def independent(path:Path)->bool:
 tree=ast.parse(path.read_text());imports=[]
 for node in ast.walk(tree):
  if isinstance(node,ast.Import):imports.extend(alias.name for alias in node.names)
  elif isinstance(node,ast.ImportFrom):imports.append(node.module or "")
 return all(not name.startswith(("scripts","blender","importlib")) for name in imports)

def eligible(radius:int,a:dict[str,np.ndarray],owners:set[np.float32])->np.ndarray:
 current,previous=a["current"],a["previous"];height,width=a["owner"].shape;mask=np.zeros((height,width),dtype=bool)
 for y in range(height):
  for x in range(width):
   owner=a["owner"][y,x]
   if owner not in owners or current[y,x,3]<=np.float32(.999):continue
   vx,vy=float(a["vector"][y,x,0]),float(a["vector"][y,x,1]);qx,qy=x+vx,y-vy;x0,y0=math.floor(qx),math.floor(qy);x1,y1=x0+1,y0+1
   ok=x>=radius and y>=radius and x<width-radius and y<height-radius
   if ok:ok=all(a["owner"][ty,tx]==owner and current[ty,tx,3]>np.float32(.999) for ty in range(y-radius,y+radius+1) for tx in range(x-radius,x+radius+1))
   if ok:ok=x0>=0 and y0>=0 and x1<width and y1<height and all(a["previousOwner"][ty,tx]==owner and previous[ty,tx,3]>np.float32(.999) for ty,tx in ((y0,x0),(y0,x1),(y1,x0),(y1,x1)))
   mask[y,x]=ok
 return mask

def reconstruct_and_risk(a:dict[str,np.ndarray],mask:np.ndarray)->tuple[np.ndarray,np.ndarray]:
 previous,current=a["previous"],a["current"];height,width=mask.shape;reconstructed=current.copy();risk=np.zeros((height,width,3),dtype="<f8")
 for y,x in np.argwhere(mask):
  vx,vy=float(a["vector"][y,x,0]),float(a["vector"][y,x,1]);qx,qy=int(x)+vx,int(y)-vy;x0,y0=math.floor(qx),math.floor(qy);fx,fy=qx-x0,qy-y0;weights=((1-fx)*(1-fy),fx*(1-fy),(1-fx)*fy,fx*fy);coords=((y0,x0),(y0,x0+1),(y0+1,x0),(y0+1,x0+1))
  for channel in range(4):
   values=[float(previous[ty,tx,channel]) for ty,tx in coords];pre=(((values[0]*weights[0])+(values[1]*weights[1]))+(values[2]*weights[2]))+(values[3]*weights[3]);reconstructed[y,x,channel]=np.float32(pre)
   if channel<3:risk[y,x,channel]=sum(abs(weight)*abs(value-float(current[y,x,channel])) for weight,value in zip(weights,values))+abs(float(np.spacing(np.float32(pre))))
 return reconstructed,risk

def metric(left:np.ndarray,right:np.ndarray,mask:np.ndarray)->dict:
 values=(left[...,:3].astype(np.float64)-right[...,:3].astype(np.float64))[mask]
 if not values.size:raise RuntimeError("empty metric mask")
 return {"maximum":float(np.abs(values).max()),"rmse":float(np.sqrt(np.mean(values*values))),"sampleCount":int(values.size)}

def expected_cell(spec:dict,root:Path,fixture:dict,repeat:int)->tuple[dict,dict]:
 fid=fixture["id"];width,height=fixture["resolution"];adir=root/"adapters"/fid/f"R{repeat}"/"arrays";py_dir=root/"consumers/python"/fid/f"R{repeat}"/"arrays";node_dir=root/"consumers/node"/fid/f"R{repeat}"/"arrays"
 sources={};source_hash={}
 for name,(filename,channels) in SOURCE.items():
  shape=(height,width,channels) if channels>1 else (height,width);sources[name]=arr(adir/filename,shape,"<f4");source_hash[name]=sha(adir/filename)
 a={"previous":sources["previousRgba"],"current":sources["currentRgba"],"previousOwner":sources["previousOwner"],"owner":sources["currentOwner"],"vector":sources["vector"]};owners={np.float32(o["passIndex"]) for o in fixture["owners"]};r2mask=eligible(2,a,owners);r3mask=eligible(3,a,owners);r2recon,risk=reconstruct_and_risk(a,r2mask);r3recon,_=reconstruct_and_risk(a,r3mask);threshold=float(spec["frozenGates"]["adaptiveHeadroom"]["reconstructionRgbMax"]);adaptive=r2mask&(risk.max(axis=2)<=threshold);rejected=r2mask&~adaptive;owner_mask=np.isin(a["owner"],list(owners))&(a["current"][...,3]>np.float32(.999))
 formal={};consumer_hash={}
 for name,(filename,channels,dtype) in PAYLOAD.items():
  shape=(height,width,channels) if channels>1 else (height,width);formal[name]=arr(py_dir/filename,shape,dtype);consumer_hash[name]=sha(py_dir/filename)
  if (py_dir/filename).read_bytes()!=(node_dir/filename).read_bytes():raise RuntimeError(f"dual payload mismatch: {fid}/R{repeat}/{name}")
 expected_masks={"radius2":r2mask,"radius3":r3mask,"adaptive":adaptive};formal_masks={name:formal[f"{name}Interior"].astype(bool) for name in expected_masks}
 replay=np.array_equal(r2recon,formal["radius2Reconstructed"]) and np.array_equal(r3recon,formal["radius3Reconstructed"]) and np.array_equal(r2recon,formal["adaptiveReconstructed"]) and np.array_equal(risk,formal["riskRgb"]) and np.array_equal(rejected,formal["adaptiveRejected"].astype(bool))
 for name,mask in expected_masks.items():replay &= np.array_equal(mask,formal_masks[name]) and np.array_equal((owner_mask&~mask).astype(np.uint8),formal[f"{name}Boundary"])
 replay &= not np.any(risk[~r2mask])
 if not replay:raise RuntimeError(f"independent payload replay mismatch: {fid}/R{repeat}")
 domains={};recons={"radius2":formal["radius2Reconstructed"],"radius3":formal["radius3Reconstructed"],"adaptive":formal["adaptiveReconstructed"]}
 for name,mask in formal_masks.items():domains[name]={"interiorPixels":int(mask.sum()),"rgb":metric(recons[name],a["current"],mask),"vectorComponentAbsoluteMaximum":max((abs(float(a["vector"][y,x,c])) for y,x in np.argwhere(mask) for c in (0,1)),default=0.0),"owners":{str(int(owner)):int((mask&(a["owner"]==owner)).sum()) for owner in sorted(owners)}}
 coverage={"adaptiveToRadius2Total":domains["adaptive"]["interiorPixels"]/domains["radius2"]["interiorPixels"],"adaptiveToRadius3Total":domains["adaptive"]["interiorPixels"]/domains["radius3"]["interiorPixels"],"owners":{}}
 for owner in sorted(owners):
  key=str(int(owner));r2=domains["radius2"]["owners"][key];r3=domains["radius3"]["owners"][key];ad=domains["adaptive"]["owners"][key];coverage["owners"][key]={"radius2":r2,"radius3":r3,"adaptive":ad,"adaptiveToRadius2":ad/r2 if r2 else None,"adaptiveMinusRadius3":ad-r3}
 under=sum(int(abs(float(formal["radius2Reconstructed"][y,x,c])-float(a["current"][y,x,c]))>float(risk[y,x,c])) for y,x in np.argwhere(r2mask) for c in range(3))
 measurement={"cell":f"{fid}/R{repeat}","fixtureId":fid,"repeat":repeat,"registeredOwnerPixels":int(owner_mask.sum()),"domains":domains,"adaptiveRejectedPixels":int(rejected.sum()),"riskRgbMaximum":float(risk[r2mask].max()),"riskUnderboundRgbSamples":under,"coverage":coverage}
 return measurement,{"source":source_hash,"consumer":consumer_hash}

def parent_state(spec:dict)->dict:
 checks={};documents={}
 for name,row in spec["parents"].items():
  path=Path(row["uri"]);checks[f"{name}FileHash"]=path.is_file() and sha(path)==row["sha256"]
  if path.suffix==".json" and path.is_file():documents[name]=json.loads(path.read_text())
 for name,field in (("d12_5Result","evidenceHash"),("d12_5Receipt","receiptHash"),("d12_6Result","evidenceHash"),("d12_6Audit","auditHash"),("d12_6Receipt","receiptHash")):checks[f"{name}InternalHash"]=name in documents and self_ok(documents[name],field) and documents[name].get(field)==spec["parents"][name][field]
 return checks

def expected_checks(spec:dict,measurements:list[dict],execution:dict,result:dict,parent_checks:dict,identity_ok:bool,analyzer_independent:bool)->list[dict]:
 current_tools={path:sha(Path(path)) for path in spec["freshness"]["formalToolPaths"]};tool_ok=self_ok(execution,"executionHash") and execution.get("toolHashes")==current_tools and execution.get("spec",{}).get("sha256")==SPEC_SHA256
 children=execution.get("children",[]);pids=[row.get("pid") for row in children]+[result.get("analyzerPid")];process_ok=len(children)==54 and len(set(pids))==55 and all(row.get("exitCode")==0 for row in children)
 mutation=result.get("mutationAttacks",[]);mutation_ok=len(mutation)>=spec["attacks"]["minimumRegisteredAttacks"] and len({row.get("target") for row in mutation})==len(mutation) and all(row.get("before") is True and row.get("after") is False and row.get("passed") is True for row in mutation)
 prod=spec["frozenGates"]["productionTolerance"];cov=spec["frozenGates"]["coverage"];threshold=float(spec["frozenGates"]["adaptiveHeadroom"]["reconstructionRgbMax"]);primary=[m for m in measurements if m["repeat"]==1];adaptive=[m["domains"]["adaptive"] for m in measurements];radius3=[m["domains"]["radius3"] for m in measurements]
 rows=[("SPEC_PREFLIGHT_TOOL_IDENTITY",tool_ok),("PARENT_IDENTITIES",all(parent_checks.values())),("PROCESS_TOTALITY_BEFORE_AUDIT",process_ok),("ANALYZER_INDEPENDENCE",analyzer_independent),("CELL_AND_REPLAY_GUARDS",identity_ok),("REGISTERED_MUTATION_ATTESTATION",mutation_ok),("RISK_CONSERVATIVE",all(m["riskUnderboundRgbSamples"]<=spec["frozenGates"]["riskConservatism"]["maximumUnderboundRgbSamples"] for m in measurements)),("ADAPTIVE_VECTOR_PRODUCTION",all(r["vectorComponentAbsoluteMaximum"]<=prod["vectorComponentMaxPixels"] for r in adaptive)),("ADAPTIVE_RGB_PRODUCTION",all(r["rgb"]["maximum"]<=prod["reconstructionRgbMax"] for r in adaptive)),("ADAPTIVE_RMSE_PRODUCTION",all(r["rgb"]["rmse"]<=prod["reconstructionRgbRmse"] for r in adaptive)),("ADAPTIVE_TWO_FOLD_HEADROOM",all(r["rgb"]["maximum"]<=threshold for r in adaptive)),("RADIUS3_PRODUCTION",all(r["vectorComponentAbsoluteMaximum"]<=prod["vectorComponentMaxPixels"] and r["rgb"]["maximum"]<=prod["reconstructionRgbMax"] and r["rgb"]["rmse"]<=prod["reconstructionRgbRmse"] for r in radius3)),("RADIUS2_MIN_INTERIOR",all(m["domains"]["radius2"]["interiorPixels"]>=cov["radius2MinimumInteriorPixelsPerCell"] for m in measurements)),("ADAPTIVE_MIN_INTERIOR",all(m["domains"]["adaptive"]["interiorPixels"]>=cov["adaptiveMinimumInteriorPixelsPerCell"] for m in measurements)),("ADAPTIVE_OWNER_MIN",all(all(row["adaptive"]>=cov["minimumAdaptivePixelsPerRegisteredOwner"] for row in m["coverage"]["owners"].values()) for m in measurements)),("ADAPTIVE_TOTAL_RETENTION",all(m["coverage"]["adaptiveToRadius2Total"]>=cov["adaptiveToRadius2TotalRetentionMinimum"] for m in measurements)),("ADAPTIVE_OWNER_RETENTION",all(all(row["radius2"]<cov["minimumRadius2PixelsForPerOwnerRetentionGate"] or row["adaptiveToRadius2"]>=cov["adaptiveToRadius2PerOwnerRetentionMinimum"] for row in m["coverage"]["owners"].values()) for m in measurements)),("ADAPTIVE_TOTAL_BEATS_RADIUS3",all(m["coverage"]["adaptiveToRadius3Total"]>=cov["adaptiveToRadius3TotalRatioMinimum"] for m in measurements)),("ADAPTIVE_OWNER_MEETS_RADIUS3",all(all(row["adaptiveMinusRadius3"]>=0 for row in m["coverage"]["owners"].values()) for m in measurements)),("STRESS_EXPOSURE",all(m["adaptiveRejectedPixels"]>=spec["frozenGates"]["stress"]["minimumAdaptiveRejectedPixelsPerFixture"] for m in primary)),("MODEL_NETWORK_ZERO",execution.get("operationCounts",{}).get("modelCalls")==0 and execution.get("operationCounts",{}).get("networkCalls")==0)]
 return [{"id":name,"passed":bool(passed)} for name,passed in rows]

def validate(document:dict,expected:dict)->bool:return self_ok(document,"evidenceHash") and all(document.get(key)==value for key,value in expected.items())
def mutate(document:dict,index:int)->dict:
 changed=copy.deepcopy(document);mode=index%15;cell=changed["measurements"][index%len(changed["measurements"])]
 if mode==0:changed["verdict"]="MUTATED"
 elif mode==1:cell["adaptiveRejectedPixels"]+=1
 elif mode==2:cell["riskUnderboundRgbSamples"]+=1
 elif mode==3:cell["domains"]["adaptive"]["interiorPixels"]+=1
 elif mode==4:cell["domains"]["adaptive"]["rgb"]["maximum"]+=1e-9
 elif mode==5:cell["coverage"]["adaptiveToRadius2Total"]-=.01
 elif mode==6:next(iter(cell["coverage"]["owners"].values()))["adaptiveMinusRadius3"]-=1
 elif mode==7:changed["checks"][0]["passed"]=not changed["checks"][0]["passed"]
 elif mode==8:changed["identities"]={}
 elif mode==9:changed["mutationAttacks"][0]["passed"]=False
 elif mode==10:changed["parentChecks"]={}
 elif mode==11:changed["analyzerIndependent"]=False
 elif mode==12:changed["operationCounts"]["modelCalls"]=1
 elif mode==13:changed["nonClaims"]=[]
 else:changed["checkPassed"]-=1
 changed["evidenceHash"]=canon({k:v for k,v in changed.items() if k!="evidenceHash"});return changed

def main()->None:
 p=argparse.ArgumentParser();p.add_argument("--correction-spec",type=Path,required=True);p.add_argument("--spec",type=Path,required=True);p.add_argument("--root",type=Path,required=True);p.add_argument("--execution",type=Path,required=True);p.add_argument("--result",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise RuntimeError("refusing to overwrite D12.7 C1 audit")
 correction=json.loads(a.correction_spec.read_text())
 if sha(a.correction_spec)!=CORRECTION_SPEC_SHA256 or a.output.resolve()!=Path(correction["outputs"]["audit"]).resolve():raise RuntimeError("D12.7 C1 correction identity/output failure")
 for name,row in correction["parents"].items():
  path=Path(row["uri"])
  if not path.is_file() or sha(path)!=row["sha256"]:raise RuntimeError(f"D12.7 C1 parent file mismatch: {name}")
  if path.suffix==".json":
   document=json.loads(path.read_text())
   for field in ("executionHash","evidenceHash","auditHash","failureHash"):
    if field in row and (document.get(field)!=row[field] or not self_ok(document,field)):raise RuntimeError(f"D12.7 C1 parent internal mismatch: {name}/{field}")
 if a.spec.resolve()!=Path(correction["parents"]["d12_7Spec"]["uri"]).resolve() or a.execution.resolve()!=Path(correction["parents"]["execution"]["uri"]).resolve() or a.result.resolve()!=Path(correction["parents"]["result"]["uri"]).resolve() or a.root.resolve()!=Path(correction["parents"]["result"]["uri"]).resolve().parent:raise RuntimeError("D12.7 C1 immutable input redirect")
 failed_audit=json.loads(Path(correction["parents"]["failedAudit"]["uri"]).read_text())
 if failed_audit.get("mutationAttackPassed")!=correction["parents"]["failedAudit"]["mutationAttackPassed"] or failed_audit.get("mutationAttackTotal")!=correction["parents"]["failedAudit"]["mutationAttackTotal"]:raise RuntimeError("D12.7 C1 failed-audit diagnosis mismatch")
 spec=json.loads(a.spec.read_text());execution=json.loads(a.execution.read_text());result=json.loads(a.result.read_text())
 if sha(a.spec)!=SPEC_SHA256 or sha(Path(sys.executable))!=spec["runtime"]["python"]["sha256"] or not self_ok(execution,"executionHash"):raise RuntimeError("D12.7 audit identity failure")
 measurements=[];identities={}
 for fixture in spec["fixtures"]:
  fid=fixture["id"];identities[fid]={}
  for repeat in (1,2):
   measurement,identity=expected_cell(spec,a.root,fixture,repeat);measurements.append(measurement);identities[fid][str(repeat)]=identity
 identity_ok=all(identities[fid]["1"]==identities[fid]["2"] for fid in identities);parents=parent_state(spec);analyzer_independent=independent(Path("scripts/analyze-b52-d12-7-adaptive-risk.py"));checks=expected_checks(spec,measurements,execution,result,parents,identity_ok,analyzer_independent);check_map={row["id"]:row["passed"] for row in checks};hard={"SPEC_PREFLIGHT_TOOL_IDENTITY","PARENT_IDENTITIES","PROCESS_TOTALITY_BEFORE_AUDIT","ANALYZER_INDEPENDENCE","CELL_AND_REPLAY_GUARDS","REGISTERED_MUTATION_ATTESTATION","RISK_CONSERVATIVE","ADAPTIVE_VECTOR_PRODUCTION","ADAPTIVE_RGB_PRODUCTION","ADAPTIVE_RMSE_PRODUCTION","ADAPTIVE_TWO_FOLD_HEADROOM","MODEL_NETWORK_ZERO"};hard_pass=all(check_map[name] for name in hard);all_pass=all(check_map.values());verdict=spec["decision"]["supportedVerdict"] if all_pass else spec["decision"]["boundedVerdict"] if hard_pass else spec["decision"]["rejectedVerdict"]
 expected={"schemaVersion":"bfs.blenderStaticAdaptiveRiskGateResult.v0.1","experimentId":spec["experimentId"],"analyzerPid":result.get("analyzerPid"),"verdict":verdict,"passed":verdict==spec["decision"]["supportedVerdict"],"analyzerIndependent":analyzer_independent,"checks":checks,"checkPassed":sum(row["passed"] for row in checks),"checkTotal":len(checks),"measurements":measurements,"identities":identities,"parentChecks":parents,"mutationAttacks":result.get("mutationAttacks",[]),"mutationAttackPassed":len(result.get("mutationAttacks",[])),"mutationAttackTotal":len(result.get("mutationAttacks",[])),"operationCounts":{"analyzerProcesses":1,"modelCalls":0,"networkCalls":0},"nonClaims":spec["nonClaims"]}
 base=validate(result,expected);pids=[row["pid"] for row in execution["children"]]+[result.get("analyzerPid"),os.getpid()];process_ok=len(pids)==spec["matrix"]["totalUniqueChildProcesses"] and len(set(pids))==len(pids) and all(row.get("exitCode")==0 for row in execution["children"]);attacks=[{"id":f"M{i+1:02d}_REPAIRED_SELF_HASH","passed":not validate(mutate(result,i),expected)} for i in range(spec["attacks"]["minimumRegisteredAttacks"])];passed=base and process_ok and all(row["passed"] for row in attacks)
 body={"schemaVersion":"bfs.blenderStaticAdaptiveRiskGateAuditCorrection.v0.1","correctionExperimentId":correction["experimentId"],"correctionSpecSha256":sha(a.correction_spec),"immutableFailedAuditSha256":correction["parents"]["failedAudit"]["sha256"],"immutableFailureSha256":correction["parents"]["failure"]["sha256"],"experimentId":spec["experimentId"],"auditPid":os.getpid(),"analyzerPid":result.get("analyzerPid"),"passed":passed,"payloadReplayPassed":base,"processTotalityPassed":process_ok,"measurementHash":canon(measurements),"identityHash":canon(identities),"expectedVerdict":verdict,"expectedChecks":checks,"mutationAttacks":attacks,"mutationAttackPassed":sum(row["passed"] for row in attacks),"mutationAttackTotal":len(attacks),"operationCounts":{"auditProcesses":1,"modelCalls":0,"networkCalls":0}};audit={**body,"auditHash":canon(body)};a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(audit,indent=2,sort_keys=True,allow_nan=False)+"\n");print(f"BFS_B52_D127_AUDIT_C1_{'OK' if passed else 'FAILED'} attacks={audit['mutationAttackPassed']}/{audit['mutationAttackTotal']}")
 if not passed:raise SystemExit(1)

if __name__=="__main__":main()
