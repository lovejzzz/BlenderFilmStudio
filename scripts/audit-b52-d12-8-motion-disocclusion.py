#!/usr/bin/env python3
"""Independent result and raw-payload audit for B52-D12.8."""
from __future__ import annotations
import argparse,hashlib,json,math,os,sys
from pathlib import Path
import numpy as np

SPEC_SHA256="d7e7c0ee0bd7f512766188eabda9fa0dccb098a0729b26487aa38bee97d6aea6"
ARRAYS={"previousRgba":("previous.rgba32",4,"<f4"),"currentRgba":("current.rgba32",4,"<f4"),"currentOwner":("current-owner.f32",1,"<f4"),"adaptiveReconstructed":("adaptive-reconstructed.rgba32",4,"<f4"),"reason":("reason.u8",1,"u1"),"analyticOwner":("analytic-owner.u8",1,"u1"),"structuralValid":("structural-valid.u8",1,"u1"),"radius2Interior":("radius2-interior.u8",1,"u1"),"radius3Interior":("radius3-interior.u8",1,"u1"),"adaptiveInterior":("adaptive-interior.u8",1,"u1"),"adaptiveRejected":("adaptive-rejected.u8",1,"u1"),"riskRgb":("risk.rgb64",3,"<f8")}
REASONS={"UNREGISTERED":0,"INVALID_CURRENT_ORACLE":1,"INVALID_BOUNDS":2,"INVALID_OWNER":3,"INVALID_ALPHA":4,"INVALID_DEPTH":5,"VALID":6}
def sha_bytes(value:bytes)->str:return hashlib.sha256(value).hexdigest()
def sha_file(file_path:Path)->str:
 d=hashlib.sha256()
 with file_path.open("rb") as h:
  for chunk in iter(lambda:h.read(1048576),b""):d.update(chunk)
 return d.hexdigest()
def canon(value:object)->str:return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def self_ok(value:dict,field:str)->bool:return value.get(field)==canon({k:v for k,v in value.items() if k!=field})
def load(file_path:Path,shape,dtype):
 payload=file_path.read_bytes()
 if len(payload)!=math.prod(shape)*np.dtype(dtype).itemsize:raise RuntimeError(f"audit payload length mismatch: {file_path}")
 return np.frombuffer(payload,dtype=dtype).reshape(shape).copy(),payload
def metric(left,right,mask):
 values=(left[...,:3].astype(np.float64)-right[...,:3].astype(np.float64))[mask]
 return {"maximum":float(np.abs(values).max()) if values.size else None,"rmse":float(np.sqrt(np.mean(values*values))) if values.size else None,"sampleCount":int(values.size)}
def close(left,right,tolerance=1e-15):
 if left is None or right is None:return left is right
 return abs(float(left)-float(right))<=tolerance
def main():
 p=argparse.ArgumentParser();p.add_argument("--spec",type=Path,required=True);p.add_argument("--root",type=Path,required=True);p.add_argument("--result",type=Path,required=True);p.add_argument("--execution",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise RuntimeError("refusing to overwrite D12.8 audit")
 spec=json.loads(a.spec.read_text());result=json.loads(a.result.read_text());execution=json.loads(a.execution.read_text())
 if sha_file(a.spec)!=SPEC_SHA256 or sha_file(Path(sys.executable))!=spec["runtime"]["python"]["sha256"]:raise RuntimeError("D12.8 audit runtime identity mismatch")
 result_hash_ok=self_ok(result,"evidenceHash");execution_ok=self_ok(execution,"executionHash");raw_checks=[];measurement_checks=[];dual_checks=[];measurement_by_cell={row["cell"]:row for row in result["measurements"]}
 for fixture in spec["fixtures"]:
  fid=fixture["id"];width,height=fixture["resolution"]
  for repeat in (1,2):
   cell=f"{fid}/R{repeat}";adapter_dir=a.root/"adapters"/fid/f"R{repeat}";python_dir=a.root/"consumers"/"python"/fid/f"R{repeat}";node_dir=a.root/"consumers"/"node"/fid/f"R{repeat}";arrays={};hashes={}
   for name,(filename,channels,dtype) in ARRAYS.items():
    source_dir=adapter_dir/"arrays" if name in ("previousRgba","currentRgba","currentOwner") else python_dir/"arrays";shape=(height,width,channels) if channels>1 else (height,width);value,payload=load(source_dir/filename,shape,dtype);arrays[name]=value;hashes[name]=sha_bytes(payload)
    if name not in ("previousRgba","currentRgba","currentOwner"):
     node_payload=(node_dir/"arrays"/filename).read_bytes();dual_checks.append(node_payload==payload)
   r2=arrays["radius2Interior"].astype(bool);r3=arrays["radius3Interior"].astype(bool);adaptive=arrays["adaptiveInterior"].astype(bool);rejected=arrays["adaptiveRejected"].astype(bool);structural=arrays["structuralValid"].astype(bool);row=measurement_by_cell[cell];raw_checks.extend([np.array_equal(arrays["reason"]==REASONS["VALID"],structural),not np.logical_and(adaptive,~r2).any(),not np.logical_and(r3,~r2).any(),not np.logical_and(adaptive,rejected).any(),np.array_equal(adaptive|rejected,r2)])
   fallback=(~structural)|rejected;fallback_exact=np.array_equal(arrays["adaptiveReconstructed"][fallback],arrays["currentRgba"][fallback]);reason_counts={name:int((arrays["reason"]==code).sum()) for name,code in REASONS.items()};rgb=metric(arrays["adaptiveReconstructed"],arrays["currentRgba"],adaptive);owners={}
   for owner_index,owner in enumerate(fixture["owners"],1):
    mask=arrays["analyticOwner"]==owner_index;r2c=int((r2&mask).sum());adc=int((adaptive&mask).sum());owners[owner["analyticOwnerId"]]={"radius2":r2c,"adaptive":adc,"retention":adc/r2c if r2c else None}
   coverage={"radius2":int(r2.sum()),"adaptive":int(adaptive.sum()),"radius3":int(r3.sum()),"adaptiveToRadius2":float(adaptive.sum()/r2.sum()) if r2.any() else None,"owners":owners};measurement_checks.extend([row["reasonCounts"]==reason_counts,row["fallbackExact"]==fallback_exact,row["adaptiveRejectedPixels"]==int(rejected.sum()),row["coverage"]==coverage,row["adaptiveRgb"]["sampleCount"]==rgb["sampleCount"],close(row["adaptiveRgb"]["maximum"],rgb["maximum"]),close(row["adaptiveRgb"]["rmse"],rgb["rmse"]),row["comparatorReportOnly"]["radius3Pixels"]==int(r3.sum())]);raw_checks.append(not np.any(arrays["riskRgb"][~r2]))
 checks_map={row["id"]:bool(row["passed"]) for row in result["checks"]};decision=spec["decision"];hard={"PARENT_IDENTITY","PREFLIGHT_TOOL_IDENTITY","PROCESS_TOTALITY_BEFORE_AUDIT","SOURCE_ADAPTER_CONSUMER_IDENTITY","DUAL_AND_INDEPENDENT_REPLAY","VECTOR_DEPTH_ORACLE","STRUCTURAL_REJECTION","RISK_CONSERVATISM","ADAPTIVE_QUALITY","STATIC_CONTROL","COMPARATOR_REPORT_ONLY","MODEL_NETWORK_ZERO"};hard_pass=all(checks_map.get(name,False) for name in hard);all_pass=all(checks_map.values());expected_verdict=decision["supportedVerdict"] if all_pass else decision["boundedVerdict"] if hard_pass else decision["rejectedVerdict"];verdict_ok=result["verdict"]==expected_verdict and result["passed"]==(expected_verdict==decision["supportedVerdict"]);comparator_ok=checks_map.get("COMPARATOR_REPORT_ONLY") is True and not any("RADIUS3" in key.upper() for key in checks_map) and all(set(row["comparatorReportOnly"])=={"radius3Rgb","radius3Pixels"} for row in result["measurements"])
 attacks=result.get("mutationAttacks",[]);attack_ok=len(attacks)>=spec["attacks"]["minimumRegisteredAttacks"] and len({row["id"] for row in attacks})==len(attacks) and all(row.get("passed") is True for row in attacks) and result.get("mutationAttackPassed")==len(attacks)==result.get("mutationAttackTotal")
 children=execution.get("children",[]);pids=[row["pid"] for row in children]+[result.get("analyzerPid"),os.getpid()];process_ok=execution_ok and len(children)==72 and len(set(pids))==74 and all(row.get("exitCode")==0 for row in children) and execution["operationCounts"]["modelCalls"]==0 and execution["operationCounts"]["networkCalls"]==0
 checks=[("SPEC_RUNTIME_RESULT_HASH",result_hash_ok),("EXECUTION_AND_74_PID_TOTALITY",process_ok),("RAW_PAYLOAD_INVARIANTS",all(raw_checks)),("DUAL_PAYLOAD_IDENTITY",all(dual_checks)),("MEASUREMENT_RAW_REPLAY",all(measurement_checks)),("VERDICT_MAPPING",verdict_ok),("COMPARATOR_EXCLUSION",comparator_ok),("MUTATION_ROSTER_TOTALITY",attack_ok),("RESULT_COUNTS",result.get("checkPassed")==sum(checks_map.values()) and result.get("checkTotal")==len(checks_map)),("MODEL_NETWORK_ZERO",result["operationCounts"]["modelCalls"]==0 and result["operationCounts"]["networkCalls"]==0)];body={"schemaVersion":"bfs.blenderProjectiveMotionDisocclusionAdaptiveRiskAudit.v0.1","experimentId":spec["experimentId"],"auditPid":os.getpid(),"passed":all(value for _,value in checks),"checks":[{"id":name,"passed":bool(value)} for name,value in checks],"checkPassed":sum(value for _,value in checks),"checkTotal":len(checks),"expectedVerdict":expected_verdict,"resultEvidenceHash":result.get("evidenceHash"),"resultSha256":sha_file(a.result),"rawCellCount":len(measurement_by_cell),"dualPayloadChecks":len(dual_checks),"measurementReplayChecks":len(measurement_checks),"operationCounts":{"auditProcesses":1,"modelCalls":0,"networkCalls":0}};audit={**body,"auditHash":canon(body)};a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(audit,indent=2,sort_keys=True,allow_nan=False)+"\n");print(f"BFS_B52_D128_AUDIT_OK passed={audit['passed']} checks={audit['checkPassed']}/{audit['checkTotal']}");raise SystemExit(0 if audit["passed"] else 1)
if __name__=="__main__":main()
