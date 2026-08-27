#!/usr/bin/env python3
"""Paired radius-2/radius-3 owner-aware scalar Python consumer for B52-D12.5."""

from __future__ import annotations

import argparse, hashlib, json, math, os, sys
from pathlib import Path
import numpy as np

SPEC_SHA256="b24aa05aeb1ab7a33e8fc57afc646308b5454eb0a5c5bf77dbbf8cc33f2ed5f2"
INPUTS={"previousRgba":("previous.rgba32",4),"currentRgba":("current.rgba32",4),"previousOwner":("previous-owner.f32",1),"currentOwner":("current-owner.f32",1),"vector":("vector.xy32",2)}
def sha_bytes(value:bytes)->str:return hashlib.sha256(value).hexdigest()
def sha_file(path:Path)->str:
    d=hashlib.sha256()
    with path.open("rb") as h:
        for chunk in iter(lambda:h.read(1024*1024),b""):d.update(chunk)
    return d.hexdigest()
def canon(value:object)->str:return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def consume(radius:int,width:int,height:int,arrays:dict[str,np.ndarray],owner_ids:set[np.float32]):
    previous,current=arrays["previousRgba"],arrays["currentRgba"];reconstructed=current.copy();interior=np.zeros((height,width),dtype=np.uint8);boundary=np.zeros((height,width),dtype=np.uint8)
    for y in range(height):
        for x in range(width):
            owner=arrays["currentOwner"][y,x]
            if owner not in owner_ids or current[y,x,3]<=np.float32(0.999):continue
            vx,vy=float(arrays["vector"][y,x,0]),float(arrays["vector"][y,x,1]);qx,qy=x+vx,y-vy;x0,y0=math.floor(qx),math.floor(qy);x1,y1=x0+1,y0+1
            neighborhood_ok=x>=radius and y>=radius and x<width-radius and y<height-radius
            if neighborhood_ok:neighborhood_ok=all(arrays["currentOwner"][ty,tx]==owner and current[ty,tx,3]>np.float32(0.999) for ty in range(y-radius,y+radius+1) for tx in range(x-radius,x+radius+1))
            taps_ok=x0>=0 and y0>=0 and x1<width and y1<height
            if taps_ok:taps_ok=all(arrays["previousOwner"][ty,tx]==owner and previous[ty,tx,3]>np.float32(0.999) for ty,tx in ((y0,x0),(y0,x1),(y1,x0),(y1,x1)))
            if not neighborhood_ok or not taps_ok:boundary[y,x]=1;continue
            fx,fy=qx-x0,qy-y0;weights=((1-fx)*(1-fy),fx*(1-fy),(1-fx)*fy,fx*fy);coords=((y0,x0),(y0,x1),(y1,x0),(y1,x1))
            for channel in range(4):
                values=[float(previous[ty,tx,channel]) for ty,tx in coords]
                reconstructed[y,x,channel]=np.float32((((values[0]*weights[0])+(values[1]*weights[1]))+(values[2]*weights[2]))+(values[3]*weights[3]))
            interior[y,x]=1
    return reconstructed,interior,boundary
def main()->None:
    p=argparse.ArgumentParser();p.add_argument("--spec",type=Path,required=True);p.add_argument("--fixture",required=True);p.add_argument("--repeat",type=int,choices=(1,2),required=True);p.add_argument("--input-dir",type=Path,required=True);p.add_argument("--adapter-report",type=Path,required=True);p.add_argument("--output-dir",type=Path,required=True);p.add_argument("--report",type=Path,required=True);a=p.parse_args();spec=json.loads(a.spec.read_text())
    if sha_file(a.spec)!=SPEC_SHA256 or sha_file(Path(sys.executable))!=spec["runtime"]["python"]["sha256"] or np.__version__!=spec["runtime"]["python"]["numpy"]:raise RuntimeError("D12.5 spec/Python identity mismatch")
    fixture=next((row for row in spec["fixtures"] if row["id"]==a.fixture),None)
    if fixture is None or a.output_dir.exists() or a.report.exists():raise RuntimeError("D12.5 fixture invalid or output exists")
    adapter=json.loads(a.adapter_report.read_text());body={k:v for k,v in adapter.items() if k!="reportHash"}
    if adapter.get("reportHash")!=canon(body) or adapter.get("fixtureId")!=a.fixture or adapter.get("repeat")!=a.repeat:raise RuntimeError("D12.5 adapter identity mismatch")
    width,height=fixture["resolution"];arrays={}
    for name,(filename,channels) in INPUTS.items():
        path=a.input_dir/filename;payload=path.read_bytes()
        if sha_bytes(payload)!=adapter["arrays"][name]["sha256"]:raise RuntimeError(f"D12.5 adapter array mismatch: {name}")
        arrays[name]=np.frombuffer(payload,dtype="<f4").reshape((height,width,channels) if channels>1 else (height,width)).copy()
    owner_ids={np.float32(owner["passIndex"]) for owner in fixture["owners"]};outputs={radius:consume(radius,width,height,arrays,owner_ids) for radius in (2,3)};a.output_dir.mkdir(parents=True,exist_ok=False);records={}
    for radius,(reconstructed,interior,boundary) in outputs.items():
        for suffix,filename,array,dtype in (("reconstructed",f"radius{radius}-reconstructed.rgba32",reconstructed,"little-endian-float32"),("interior",f"radius{radius}-interior.u8",interior,"uint8"),("boundary",f"radius{radius}-boundary.u8",boundary,"uint8")):
            name=f"radius{radius}{suffix.title()}";payload=np.ascontiguousarray(array,dtype="<f4" if suffix=="reconstructed" else "u1").tobytes(order="C");target=a.output_dir/filename;target.write_bytes(payload);records[name]={"uri":str(target),"sha256":sha_bytes(payload),"bytes":len(payload),"shape":list(array.shape),"dtype":dtype}
    report={"schemaVersion":"bfs.blenderStaticRadiusInterventionConsumerReport.v0.1","experimentId":spec["experimentId"],"producer":"python","fixtureId":a.fixture,"repeat":a.repeat,"pid":os.getpid(),"runtime":{"python":sys.version.split()[0],"pythonExecutableSha256":sha_file(Path(sys.executable)),"numpy":np.__version__},"adapter":{"uri":str(a.adapter_report),"sha256":sha_file(a.adapter_report),"reportHash":adapter["reportHash"]},"contract":spec["consumerContract"],"arrays":records,"integrity":"external dual typed-envelope sidecars","operationCounts":{"consumerProcesses":1,"radiusEvaluations":2,"pixelsVisited":width*height*2,"modelCalls":0,"networkCalls":0}};a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+"\n");print(f"BFS_B52_D125_CONSUMER_PY_OK fixture={a.fixture} repeat={a.repeat} r2={int(outputs[2][1].sum())} r3={int(outputs[3][1].sum())}")
if __name__=="__main__":main()
