#!/usr/bin/env python3
"""Python radius and frozen adaptive-risk consumer for B52-D12.7."""
from __future__ import annotations
import argparse,hashlib,json,math,os,sys
from pathlib import Path
import numpy as np
SPEC_SHA256="c51d0d83afd30b479bf3e7109c31110133649ee3d65a04d677dbe236b8075ed0"
INPUTS={"previousRgba":("previous.rgba32",4),"currentRgba":("current.rgba32",4),"previousOwner":("previous-owner.f32",1),"currentOwner":("current-owner.f32",1),"vector":("vector.xy32",2)}
def sha_bytes(v:bytes)->str:return hashlib.sha256(v).hexdigest()
def sha_file(p:Path)->str:
 d=hashlib.sha256()
 with p.open("rb") as h:
  for c in iter(lambda:h.read(1048576),b""):d.update(c)
 return d.hexdigest()
def canon(v:object)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def consume(radius:int,width:int,height:int,a:dict[str,np.ndarray],owners:set[np.float32]):
 previous,current=a["previousRgba"],a["currentRgba"];reconstructed=current.copy();interior=np.zeros((height,width),dtype=np.uint8);boundary=np.zeros((height,width),dtype=np.uint8)
 for y in range(height):
  for x in range(width):
   owner=a["currentOwner"][y,x]
   if owner not in owners or current[y,x,3]<=np.float32(.999):continue
   vx,vy=float(a["vector"][y,x,0]),float(a["vector"][y,x,1]);qx,qy=x+vx,y-vy;x0,y0=math.floor(qx),math.floor(qy);x1,y1=x0+1,y0+1;neighborhood=x>=radius and y>=radius and x<width-radius and y<height-radius
   if neighborhood:neighborhood=all(a["currentOwner"][ty,tx]==owner and current[ty,tx,3]>np.float32(.999) for ty in range(y-radius,y+radius+1) for tx in range(x-radius,x+radius+1))
   taps=x0>=0 and y0>=0 and x1<width and y1<height
   if taps:taps=all(a["previousOwner"][ty,tx]==owner and previous[ty,tx,3]>np.float32(.999) for ty,tx in ((y0,x0),(y0,x1),(y1,x0),(y1,x1)))
   if not neighborhood or not taps:boundary[y,x]=1;continue
   fx,fy=qx-x0,qy-y0;weights=((1-fx)*(1-fy),fx*(1-fy),(1-fx)*fy,fx*fy);coords=((y0,x0),(y0,x1),(y1,x0),(y1,x1))
   for channel in range(4):
    values=[float(previous[ty,tx,channel]) for ty,tx in coords];reconstructed[y,x,channel]=np.float32((((values[0]*weights[0])+(values[1]*weights[1]))+(values[2]*weights[2]))+(values[3]*weights[3]))
   interior[y,x]=1
 return reconstructed,interior,boundary
def adaptive(width:int,height:int,a:dict[str,np.ndarray],r2:tuple[np.ndarray,np.ndarray,np.ndarray],owners:set[np.float32],threshold:float):
 previous,current=a["previousRgba"],a["currentRgba"];reconstructed,r2_interior,_=r2;risk=np.zeros((height,width,3),dtype="<f8");interior=np.zeros((height,width),dtype=np.uint8);rejected=np.zeros((height,width),dtype=np.uint8);owner_mask=np.isin(a["currentOwner"],list(owners))&(current[...,3]>np.float32(.999))
 for y,x in np.argwhere(r2_interior):
  vx,vy=float(a["vector"][y,x,0]),float(a["vector"][y,x,1]);qx,qy=int(x)+vx,int(y)-vy;x0,y0=math.floor(qx),math.floor(qy);fx,fy=qx-x0,qy-y0;weights=((1-fx)*(1-fy),fx*(1-fy),(1-fx)*fy,fx*fy);coords=((y0,x0),(y0,x0+1),(y0+1,x0),(y0+1,x0+1))
  for channel in range(3):
   center=float(current[y,x,channel]);values=[float(previous[ty,tx,channel]) for ty,tx in coords];pre=(((values[0]*weights[0])+(values[1]*weights[1]))+(values[2]*weights[2]))+(values[3]*weights[3]);final=np.float32(pre);risk[y,x,channel]=sum(abs(w)*abs(v-center) for w,v in zip(weights,values))+abs(float(np.spacing(final)))
  if float(risk[y,x].max())<=threshold:interior[y,x]=1
  else:rejected[y,x]=1
 boundary=(owner_mask&~interior.astype(bool)).astype(np.uint8);return reconstructed.copy(),interior,boundary,rejected,risk
def main()->None:
 p=argparse.ArgumentParser();p.add_argument("--spec",type=Path,required=True);p.add_argument("--fixture",required=True);p.add_argument("--repeat",type=int,choices=(1,2),required=True);p.add_argument("--input-dir",type=Path,required=True);p.add_argument("--adapter-report",type=Path,required=True);p.add_argument("--output-dir",type=Path,required=True);p.add_argument("--report",type=Path,required=True);a=p.parse_args();spec=json.loads(a.spec.read_text())
 if sha_file(a.spec)!=SPEC_SHA256 or sha_file(Path(sys.executable))!=spec["runtime"]["python"]["sha256"] or np.__version__!=spec["runtime"]["python"]["numpy"]:raise RuntimeError("D12.7 runtime identity mismatch")
 fixture=next((r for r in spec["fixtures"] if r["id"]==a.fixture),None)
 if fixture is None or a.output_dir.exists() or a.report.exists():raise RuntimeError("D12.7 fixture/output invalid")
 adapter=json.loads(a.adapter_report.read_text());body={k:v for k,v in adapter.items() if k!="reportHash"}
 if adapter.get("reportHash")!=canon(body) or adapter.get("fixtureId")!=a.fixture or adapter.get("repeat")!=a.repeat:raise RuntimeError("D12.7 adapter identity mismatch")
 width,height=fixture["resolution"];arrays={}
 for name,(filename,channels) in INPUTS.items():
  payload=(a.input_dir/filename).read_bytes()
  if sha_bytes(payload)!=adapter["arrays"][name]["sha256"]:raise RuntimeError(f"D12.7 input mismatch: {name}")
  arrays[name]=np.frombuffer(payload,dtype="<f4").reshape((height,width,channels) if channels>1 else (height,width)).copy()
 owners={np.float32(o["passIndex"]) for o in fixture["owners"]};r2=consume(2,width,height,arrays,owners);r3=consume(3,width,height,arrays,owners);threshold=float(spec["frozenGates"]["adaptiveHeadroom"]["reconstructionRgbMax"]);adaptive_out=adaptive(width,height,arrays,r2,owners,threshold);a.output_dir.mkdir(parents=True,exist_ok=False);records={}
 outputs=[("radius2Reconstructed","radius2-reconstructed.rgba32",r2[0],"<f4","little-endian-float32"),("radius2Interior","radius2-interior.u8",r2[1],"u1","uint8"),("radius2Boundary","radius2-boundary.u8",r2[2],"u1","uint8"),("radius3Reconstructed","radius3-reconstructed.rgba32",r3[0],"<f4","little-endian-float32"),("radius3Interior","radius3-interior.u8",r3[1],"u1","uint8"),("radius3Boundary","radius3-boundary.u8",r3[2],"u1","uint8"),("adaptiveReconstructed","adaptive-reconstructed.rgba32",adaptive_out[0],"<f4","little-endian-float32"),("adaptiveInterior","adaptive-interior.u8",adaptive_out[1],"u1","uint8"),("adaptiveBoundary","adaptive-boundary.u8",adaptive_out[2],"u1","uint8"),("adaptiveRejected","adaptive-rejected.u8",adaptive_out[3],"u1","uint8"),("riskRgb","risk.rgb64",adaptive_out[4],"<f8","little-endian-float64")]
 for name,filename,value,dtype,label in outputs:
  payload=np.ascontiguousarray(value,dtype=dtype).tobytes();target=a.output_dir/filename;target.write_bytes(payload);records[name]={"uri":str(target),"sha256":sha_bytes(payload),"bytes":len(payload),"shape":list(value.shape),"dtype":label}
 report={"schemaVersion":"bfs.blenderStaticAdaptiveRiskConsumerReport.v0.1","experimentId":spec["experimentId"],"producer":"python","fixtureId":a.fixture,"repeat":a.repeat,"pid":os.getpid(),"runtime":{"python":sys.version.split()[0],"pythonExecutableSha256":sha_file(Path(sys.executable)),"numpy":np.__version__},"adapter":{"uri":str(a.adapter_report),"sha256":sha_file(a.adapter_report),"reportHash":adapter["reportHash"]},"contract":spec["consumerContract"],"arrays":records,"integrity":"external dual typed-envelope sidecars","operationCounts":{"consumerProcesses":1,"radiusEvaluations":2,"adaptiveEvaluations":1,"pixelsVisited":width*height*3,"modelCalls":0,"networkCalls":0}};a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+"\n");print(f"BFS_B52_D127_CONSUMER_PY_OK fixture={a.fixture} repeat={a.repeat} r2={int(r2[1].sum())} r3={int(r3[1].sum())} adaptive={int(adaptive_out[1].sum())} rejected={int(adaptive_out[3].sum())}")
if __name__=="__main__":main()
