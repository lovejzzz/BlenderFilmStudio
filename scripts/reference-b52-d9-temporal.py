#!/usr/bin/env python3
"""Independent scalar-Python layer/depth temporal accumulator for B52-D9."""
from __future__ import annotations
import argparse, hashlib, json, math, os, struct, sys
from pathlib import Path
SPEC_SHA256="d02986d1e682f0a945c68b307a993452de59e0ac4f4ecf769b002c9e2de51030"
ARRAY_FILES={"previousRgba":"previous.rgba32","currentRgba":"current.rgba32","previousDepth":"previous-depth.f32","currentDepth":"current-depth.f32","previousLayer":"previous-layer.f32","currentLayer":"current-layer.f32","motion":"motion.xy32","analyticValidity":"analytic-validity.u8","resolvedRgba":"resolved.rgba32","cleanTarget":"clean-target.rgba32"}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ch(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def f32(v):return struct.unpack("<f",struct.pack("<f",v))[0]
def noise(x,y):
 s=1 if (x+3*y)%2==0 else -1;return (f32(s/16),f32(-s/32),f32(s/64),0.0)
def color(name):
 return {"background":(.125,.25,.5,1),"foreground":(1.5,-.25,.75,1),"patternA":(.25,1.25,-.5,1),"patternB":(1.75,.125,.375,1),"oldPatch":(1.5,-.5,.25,1),"newPatch":(.25,1.5,-.25,1)}[name]
def inside(x,y,box):return box[0]<=x<box[2] and box[1]<=y<box[3]
def clean_scene(fid,frame,x,y):
 if fid=="FOREGROUND_CROSSING_97X61":
  box=(28,15,49,46) if frame=="previous" else (36,15,57,46);return (color("foreground"),1.0,2.0) if inside(x,y,box) else (color("background"),4.0,1.0)
 if fid=="CAMERA_PAN_101X59":
  box=(30,12,65,43) if frame=="previous" else (35,15,70,46);return (color("patternA"),2.0,2.0) if inside(x,y,box) else (color("patternB"),8.0,1.0)
 if fid=="DEPTH_SWAP_SAME_ID_83X47":
  if frame=="previous" and inside(x,y,(30,12,50,35)):return color("oldPatch"),1.0,7.0
  if frame=="current" and inside(x,y,(26,12,46,35)):return color("newPatch"),4.0,7.0
  return color("background"),4.0,7.0
 if fid=="STATIC_CONTROL_73X41":return (color("foreground"),2.0,2.0) if inside(x,y,(19,9,54,33)) else (color("background"),8.0,1.0)
 raise RuntimeError("unknown fixture")
def motion(fid,x,y):
 if fid=="FOREGROUND_CROSSING_97X61":return (8.0,0.0) if inside(x,y,(36,15,57,46)) else (0.0,0.0)
 if fid=="CAMERA_PAN_101X59":return 5.0,-3.0
 if fid=="DEPTH_SWAP_SAME_ID_83X47":return (-4.0,0.0) if inside(x,y,(26,12,46,35)) else (0.0,0.0)
 if fid=="STATIC_CONTROL_73X41":return 0.0,0.0
 raise RuntimeError("unknown fixture")
def build(f):
 fid=f["id"];w,h=f["resolution"];n=w*h;pc=[0.0]*(n*4);cc=[0.0]*(n*4);pd=[0.0]*n;cd=[0.0]*n;pi=[0.0]*n;ci=[0.0]*n;mv=[0.0]*(n*2)
 for y in range(h):
  for x in range(w):
   k=y*w+x;pcol,pz,pid=clean_scene(fid,"previous",x,y);ccol,cz,cid=clean_scene(fid,"current",x,y);no=noise(x,y);pc[k*4:k*4+4]=[f32(pcol[c]+no[c]) for c in range(4)];cc[k*4:k*4+4]=[f32(v) for v in ccol];pd[k]=f32(pz);cd[k]=f32(cz);pi[k]=f32(pid);ci[k]=f32(cid);mv[k*2:k*2+2]=[f32(v) for v in motion(fid,x,y)]
 valid=bytearray(n);target=[0.0]*(n*4)
 for y in range(h):
  for x in range(w):
   k=y*w+x;dx,dy=mv[k*2:k*2+2];qx,qy=x-int(dx),y+int(dy);ok=0<=qx<w and 0<=qy<h
   if ok:
    q=qy*w+qx;ok=pi[q]==ci[k] and abs(pd[q]-cd[k])<=max(1.0,cd[k])/1024 and pc[q*4+3]>0 and cc[k*4+3]>0
   valid[k]=int(ok);clean=clean_scene(fid,"current",x,y)[0];target[k*4:k*4+4]=[f32(v) for v in clean]
   if ok:
    no=noise(qx,qy);cc[k*4:k*4+4]=[f32(clean[c]-no[c]) for c in range(4)]
 def accumulate(sign=1,naive=False):
  out=list(cc)
  for y in range(h):
   for x in range(w):
    k=y*w+x;dx,dy=mv[k*2:k*2+2];qx,qy=x-sign*int(dx),y+sign*int(dy);ok=0<=qx<w and 0<=qy<h
    if ok and not naive:
     q=qy*w+qx;ok=pi[q]==ci[k] and abs(pd[q]-cd[k])<=max(1.0,cd[k])/1024 and pc[q*4+3]>0 and cc[k*4+3]>0
    if ok:
     q=qy*w+qx
     for c in range(4):out[k*4+c]=f32(.5*cc[k*4+c]+.5*pc[q*4+c])
  return out
 resolved=accumulate();naive=accumulate(1,True);wrong=accumulate(-1,False)
 def metrics(a):
  dif=[abs(float(a[i])-float(target[i])) for i in range(len(a))];wrong_pixels=sum(any(dif[(k*4)+c]!=0 for c in range(4)) for k in range(n));return {"wrongPixels":wrong_pixels,"maximumAbsoluteError":max(dif)}
 return {"previousRgba":pc,"currentRgba":cc,"previousDepth":pd,"currentDepth":cd,"previousLayer":pi,"currentLayer":ci,"motion":mv,"analyticValidity":bytes(valid),"resolvedRgba":resolved,"cleanTarget":target},metrics(naive),metrics(wrong)
def encode(name,data):
 if name=="analyticValidity":return data
 return struct.pack(f"<{len(data)}f",*data)
def main():
 p=argparse.ArgumentParser();p.add_argument("--spec",type=Path,required=True);p.add_argument("--fixture",required=True);p.add_argument("--output-dir",type=Path,required=True);p.add_argument("--report",type=Path,required=True);a=p.parse_args();spec=json.loads(a.spec.read_text());f=next((x for x in spec["fixtures"] if x["id"]==a.fixture),None)
 if sha(a.spec)!=SPEC_SHA256 or f is None or sha(sys.executable)!=spec["runtime"]["python"]["sha256"]:raise RuntimeError("identity mismatch")
 if a.output_dir.exists() or a.report.exists():raise RuntimeError("refusing overwrite")
 arrays,naive,wrong=build(f);a.output_dir.mkdir(parents=True);records={}
 for name,file in ARRAY_FILES.items():
  pth=a.output_dir/file;pth.write_bytes(encode(name,arrays[name]));records[name]={"uri":str(pth),"sha256":sha(pth),"bytes":pth.stat().st_size}
 validity=arrays["analyticValidity"];resolved=arrays["resolvedRgba"];target=arrays["cleanTarget"];invalid_exact=all(validity[k] or all(resolved[k*4+c]==arrays["currentRgba"][k*4+c] for c in range(4)) for k in range(len(validity)));valid_exact=all(not validity[k] or all(resolved[k*4+c]==target[k*4+c] for c in range(4)) for k in range(len(validity)));body={"schemaVersion":"bfs.layerDepthTemporalPythonReport.v0.1","experimentId":spec["experimentId"],"fixtureId":a.fixture,"producer":"python","pid":os.getpid(),"arrays":records,"metrics":{"validPixels":sum(validity),"invalidPixels":len(validity)-sum(validity),"resolvedExact":encode("resolvedRgba",resolved)==encode("cleanTarget",target),"invalidPixelsEqualCurrent":invalid_exact,"validPixelsEqualTarget":valid_exact,"naiveControl":naive,"wrongSignControl":wrong},"operationCounts":{"pythonAccumulatorProcesses":1,"nodeAccumulatorProcesses":0,"exrEncoderProcesses":0,"blenderProcesses":0,"renderCalls":0,"cyclesRayRenders":0}};a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps({**body,"reportHash":ch(body)},indent=2,sort_keys=True,allow_nan=False)+"\n");print(f"BFS_B52_D9_PYTHON_OK fixture={a.fixture} resolved={records['resolvedRgba']['sha256']} valid={sum(validity)}/{len(validity)}")
if __name__=="__main__":main()
