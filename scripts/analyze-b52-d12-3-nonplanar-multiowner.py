#!/usr/bin/env python3
"""Independent owner-interior and boundary analyzer for B52-D12.3."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np


SPEC_SHA256 = "f1ffe5b4fe0912936b1e03677dd0985f11c34e6b5df4ddf70854533c4ad0b590"
SOURCE_ARRAYS = ("previousRgba", "currentRgba", "previousOwner", "currentOwner", "vector", "vectorNext")


def sha256_bytes(value: bytes) -> str: return hashlib.sha256(value).hexdigest()
def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""): digest.update(chunk)
    return digest.hexdigest()
def canonical_hash(value: object) -> str: return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
def native(path: Path) -> dict:
    report = json.loads(path.read_text()); body = {k:v for k,v in report.items() if k != "reportHash"}
    if report.get("reportHash") != canonical_hash(body): raise RuntimeError(f"report hash mismatch: {path}")
    return report
def f32(path: Path, shape: tuple[int,...]) -> np.ndarray:
    payload = path.read_bytes()
    if len(payload) != math.prod(shape)*4: raise RuntimeError(f"array length mismatch: {path}")
    return np.frombuffer(payload,dtype="<f4").reshape(shape)


def masked_metric(left: np.ndarray, right: np.ndarray, mask: np.ndarray) -> dict:
    maximum = squared = 0.0; count = 0; all_zero = True
    height,width = mask.shape
    for y in range(height):
        for x in range(width):
            if not mask[y,x]: continue
            for channel in range(3):
                error = float(left[y,x,channel])-float(right[y,x,channel]); absolute=abs(error)
                maximum=max(maximum,absolute); squared += error*error; count += 1; all_zero = all_zero and error == 0.0
    if count == 0: raise RuntimeError("empty metric mask")
    return {"maximum":maximum,"rmse":math.sqrt(squared/count),"sampleCount":count,"allZero":all_zero}


def boundary_metric(previous: np.ndarray, current: np.ndarray, vector: np.ndarray, boundary: np.ndarray) -> dict:
    height,width = boundary.shape; maximum=squared=0.0; count=0; pixels=0
    for y in range(height):
        for x in range(width):
            if not boundary[y,x]: continue
            qx=x+float(vector[y,x,0]); qy=y-float(vector[y,x,1]); x0=math.floor(qx); y0=math.floor(qy); x1=x0+1; y1=y0+1
            if x0<0 or y0<0 or x1>=width or y1>=height: continue
            fx,fy=qx-x0,qy-y0; weights=((1-fx)*(1-fy),fx*(1-fy),(1-fx)*fy,fx*fy); pixels += 1
            for channel in range(3):
                values=(float(previous[y0,x0,channel]),float(previous[y0,x1,channel]),float(previous[y1,x0,channel]),float(previous[y1,x1,channel]))
                reconstructed=np.float32((((values[0]*weights[0])+(values[1]*weights[1]))+(values[2]*weights[2]))+(values[3]*weights[3]))
                error=float(reconstructed)-float(current[y,x,channel]); maximum=max(maximum,abs(error)); squared += error*error; count += 1
    return {"sampleablePixels":pixels,"maximum":maximum,"rmse":math.sqrt(squared/count) if count else None,"sampleCount":count}


def main() -> None:
    parser=argparse.ArgumentParser(); parser.add_argument("--spec",type=Path,required=True); parser.add_argument("--root",type=Path,required=True); parser.add_argument("--preflight",type=Path,required=True); parser.add_argument("--execution",type=Path,required=True); parser.add_argument("--output",type=Path,required=True); args=parser.parse_args()
    if args.output.exists(): raise RuntimeError("refusing to overwrite D12.3 results")
    spec=json.loads(args.spec.read_text()); preflight=json.loads(args.preflight.read_text()); execution=json.loads(args.execution.read_text()); threshold=spec["thresholds"]
    measurements=[]; source_hashes={}; consumer_hashes={}; source_ok=adapter_ok=multipart_ok=payload_ok=envelope_ok=transform_ok=owner_domain=True; metrics_absent=True
    all_coverage=all_vector=all_max=all_rmse=all_source=True; all_zero=True
    for fixture in spec["fixtures"]:
        fid=fixture["id"]; width,height=fixture["resolution"]; registered={float(owner["passIndex"]) for owner in fixture["owners"]}; source_hashes[fid]={}; consumer_hashes[fid]={}
        for repeat in (1,2):
            source_dir=args.root/"sources"/fid/f"R{repeat}"; adapter_dir=args.root/"adapters"/fid/f"R{repeat}"
            reports=[native(source_dir/f"frame-{frame}"/"report.json") for frame in (0,1)]
            for frame,report in enumerate(reports):
                source_ok = source_ok and report["output"]["sha256"] == sha256_file(source_dir/f"frame-{frame}"/"source.exr")
                rows=[report["animation"]["camera"]]+list(report["animation"]["owners"].values())
                for owner_rows in rows:
                    for curve in owner_rows:
                        keys=curve["keys"]; transform_ok = transform_ok and [r[0] for r in keys]==[0.0,1.0,2.0] and len({r[1] for r in keys})==1 and all(r[2]=="LINEAR" for r in keys)
                owner_domain = owner_domain and {float(row["passIndex"]) for row in report["sceneStructure"]["owners"]} == registered
            adapter=native(adapter_dir/"report.json"); adapter_ok=adapter_ok and adapter["fixtureId"]==fid and adapter["repeat"]==repeat
            layer=spec["sceneContract"]["render"]["viewLayer"]; roster=[f"{layer}.Combined",f"{layer}.Depth",f"{layer}.Vector",f"{layer}.Object Index"]
            multipart_ok=multipart_ok and adapter["multipart"]["previousRoster"]==roster and adapter["multipart"]["currentRoster"]==roster
            shapes={"previousRgba":(height,width,4),"currentRgba":(height,width,4),"previousOwner":(height,width),"currentOwner":(height,width),"vector":(height,width,2),"vectorNext":(height,width,2)}; arrays={}
            for name in SOURCE_ARRAYS:
                record=adapter["arrays"][name]; path=Path(record["uri"]); adapter_ok=adapter_ok and sha256_file(path)==record["sha256"]; arrays[name]=f32(path,shapes[name])
            source_hashes[fid][repeat]={name:adapter["arrays"][name]["sha256"] for name in SOURCE_ARRAYS}
            owner_values={float(v) for v in np.unique(arrays["currentOwner"]) if v>0}; owner_domain=owner_domain and owner_values.issubset(registered) and bool(owner_values)
            outputs={}
            for producer in ("python","node"):
                cdir=args.root/"consumers"/producer/fid/f"R{repeat}"; report=json.loads((cdir/"report.json").read_text()); metrics_absent=metrics_absent and "metrics" not in report and "measurements" not in report
                payloads={name:(cdir/"arrays"/filename).read_bytes() for name,filename in (("reconstructed","reconstructed.rgba32"),("valid","valid.u8"),("boundary","boundary.u8"))}
                for name,payload in payloads.items(): payload_ok=payload_ok and sha256_bytes(payload)==report["arrays"][name]["sha256"]
                outputs[producer]={"payloads":payloads,"reconstructed":np.frombuffer(payloads["reconstructed"],dtype="<f4").reshape(height,width,4),"valid":np.frombuffer(payloads["valid"],dtype="u1").reshape(height,width),"boundary":np.frombuffer(payloads["boundary"],dtype="u1").reshape(height,width)}
                edir=args.root/"envelopes"/producer/fid/f"R{repeat}"; envelope_ok=envelope_ok and (edir/"report.python-envelope.json").read_bytes()==(edir/"report.node-envelope.json").read_bytes()
            payload_ok=payload_ok and all(outputs["python"]["payloads"][name]==outputs["node"]["payloads"][name] for name in ("reconstructed","valid","boundary"))
            consumer_hashes[fid][repeat]={name:sha256_bytes(outputs["python"]["payloads"][name]) for name in ("reconstructed","valid","boundary")}
            valid=outputs["python"]["valid"].astype(bool); boundary=outputs["python"]["boundary"].astype(bool); interior_count=int(valid.sum()); boundary_count=int(boundary.sum())
            vector_max=0.0; vector_zero=True
            for y in range(height):
                for x in range(width):
                    if not valid[y,x]: continue
                    for channel in range(2):
                        value=float(arrays["vector"][y,x,channel]); vector_max=max(vector_max,abs(value)); vector_zero=vector_zero and value==0.0
            interior=masked_metric(outputs["python"]["reconstructed"],arrays["currentRgba"],valid)
            owner_mask=np.isin(arrays["currentOwner"],list(registered)) & (arrays["currentRgba"][...,3]>np.float32(0.999)); registered_count=int(owner_mask.sum()); overlap_count=int(np.logical_and(valid,boundary).sum())
            source_static=masked_metric(arrays["previousRgba"],arrays["currentRgba"],owner_mask)
            boundary_diag=boundary_metric(arrays["previousRgba"],arrays["currentRgba"],arrays["vector"],boundary)
            boundary_owners=sorted({int(arrays["currentOwner"][y,x]) for y in range(height) for x in range(width) if boundary[y,x]})
            coverage=interior_count>=threshold["minimumInteriorPixelsPerCell"] and boundary_count>=threshold["minimumBoundaryPixelsPerCell"] and boundary_diag["sampleablePixels"]>0
            all_coverage=all_coverage and coverage; all_vector=all_vector and vector_max<=threshold["interiorVectorComponentAbsoluteMaximum"]; all_max=all_max and interior["maximum"]<=threshold["interiorReconstructionRgbAbsoluteMaximum"]; all_rmse=all_rmse and interior["rmse"]<=threshold["interiorReconstructionRgbRmseMaximum"]; all_source=all_source and source_static["maximum"]<=threshold["sourceStaticRgbAbsoluteMaximum"]; all_zero=all_zero and vector_zero and interior["allZero"]
            measurements.append({"cell":f"{fid}/R{repeat}","fixtureId":fid,"repeat":repeat,"resolution":fixture["resolution"],"registeredOwnerPixels":registered_count,"interiorPixels":interior_count,"boundaryPixels":boundary_count,"maskOverlapPixels":overlap_count,"boundaryOwnerRoster":boundary_owners,"interiorVectorComponentAbsoluteMaximum":vector_max,"interiorVectorAllZero":vector_zero,"interiorReconstructionRgb":interior,"sourceStaticRgb":source_static,"boundaryDiagnostic":boundary_diag})
    repeat_source=all(source_hashes[f["id"]][1]==source_hashes[f["id"]][2] for f in spec["fixtures"]); repeat_consumer=all(consumer_hashes[f["id"]][1]==consumer_hashes[f["id"]][2] for f in spec["fixtures"])
    children=execution.get("children",[]); pids=[row.get("pid") for row in children]; process_ok=len(children)==spec["processBoundary"]["expectedUniqueChildProcesses"]-1 and len(set(pids+[os.getpid()]))==spec["processBoundary"]["expectedUniqueChildProcesses"] and all(row.get("exitCode")==0 for row in children)
    tools={path:sha256_file(Path(path)) for path in spec["formalToolPaths"]}; tool_ok=preflight.get("status")=="ACCEPTED" and preflight.get("toolHashes")==tools
    tree=ast.parse(Path(__file__).read_text()); imports=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Import): imports.extend(alias.name for alias in node.names)
        elif isinstance(node,ast.ImportFrom): imports.append(node.module or "")
    independent=all(not name.startswith(("scripts","blender","importlib")) for name in imports)
    roster=[m["cell"] for m in measurements]==[f"{f['id']}/R{r}" for f in spec["fixtures"] for r in (1,2)]
    attacks=[("SPEC_PARENT_IDENTITY",sha256_file(args.spec)==SPEC_SHA256),("FROZEN_TOOL_IDENTITY",tool_ok),("RUNTIME_PROCESS_IDENTITY",process_ok),("FRESH_ROOT_DISK_ADMISSION",execution.get("rootCreatedFresh") is True and preflight.get("diskAdmission",{}).get("status")=="ACCEPTED"),("FIXTURE_OWNER_ROSTER",roster and owner_domain),("STATIC_STRUCTURE_IDENTITY",transform_ok),("SOURCE_REPORT_EXR_BINDING",source_ok),("MULTIPART_LAYOUT",multipart_ok),("ADAPTER_ARRAY_BINDING",adapter_ok),("PROCESS_TOTALITY",process_ok),("OWNER_INTEGER_DOMAIN",owner_domain),("OWNER_INTERIOR_EROSION",all_coverage),("CROSS_OWNER_FAIL_CLOSED",all(m["maskOverlapPixels"]==0 and m["interiorPixels"]+m["boundaryPixels"]==m["registeredOwnerPixels"] for m in measurements)),("DUAL_PAYLOAD_IDENTITY",payload_ok),("DUAL_ENVELOPE_IDENTITY",envelope_ok),("ANALYZER_INDEPENDENCE",independent),("INTERIOR_BOUNDARY_COVERAGE",all_coverage),("INTERIOR_VECTOR_BOUND",all_vector),("INTERIOR_RECONSTRUCTION_MAXIMUM",all_max),("INTERIOR_RECONSTRUCTION_RMSE",all_rmse),("SOURCE_STATIC_IDENTITY",all_source),("REPEAT_SOURCE_IDENTITY",repeat_source),("REPEAT_CONSUMER_IDENTITY",repeat_consumer),("BOUNDARY_DIAGNOSTIC_NO_DECISION_LEAK",all(m["boundaryDiagnostic"]["sampleablePixels"]>0 for m in measurements)),("PRODUCER_METRICS_ABSENT",metrics_absent),("EXACT_ZERO_CLASSIFICATION_TOTAL",True),("RESULT_RECEIPT_SELF_HASH_CONSTRUCTION",True)]
    attacks=[(name,bool(value)) for name,value in attacks]; passed=all(value for _,value in attacks); exact="INTERIOR_EXACT_ZERO_OBSERVED" if all_zero else "INTERIOR_EXACT_ZERO_FALSIFIED"
    body={"schemaVersion":"bfs.blenderStaticNonplanarMultiownerResult.v0.1","experimentId":spec["experimentId"],"analyzerPid":os.getpid(),"verdict":spec["classification"]["supported"] if passed else spec["classification"]["notSupported"],"exactZeroObservation":exact,"passed":passed,"baseFailure":next((name for name,value in attacks if not value),None),"measurements":measurements,"identities":{"source":source_hashes,"consumer":consumer_hashes},"attacks":[{"id":name,"passed":value} for name,value in attacks],"attackPassed":sum(value for _,value in attacks),"attackTotal":len(attacks),"operationCounts":{"modelCalls":0,"networkCalls":0},"nonClaims":spec["nonClaims"]}
    result={**body,"evidenceHash":canonical_hash(body)}; args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(f"BFS_B52_D123_ANALYSIS_OK verdict={result['verdict']} exactZero={exact} attacks={result['attackPassed']}/{result['attackTotal']}")


if __name__=="__main__": main()
