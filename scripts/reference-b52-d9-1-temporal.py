#!/usr/bin/env python3
"""Independent scalar-Python textured temporal holdout producer for B52-D9.1."""
from __future__ import annotations
import argparse, hashlib, json, os, struct, sys
from pathlib import Path
SPEC_SHA256="669077423e0101dd5600576d295c0b7a62189a30b18c1dd6ab18a3b5257cd28f"
FILES={"previousRgba":"previous.rgba32","currentRgba":"current.rgba32","previousDepth":"previous-depth.f32","currentDepth":"current-depth.f32","previousLayer":"previous-layer.f32","currentLayer":"current-layer.f32","motion":"motion.xy32","analyticValidity":"analytic-validity.u8","resolvedRgba":"resolved.rgba32","cleanTarget":"clean-target.rgba32"}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ch(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def f32(v):return struct.unpack("<f",struct.pack("<f",v))[0]
def inside(x,y,b):return b[0]<=x<b[2] and b[1]<=y<b[3]
def texture(name,lx,ly):
 if name=="BACKGROUND_CHECKER":b=((lx//2)+(ly//3))%2;return ((.125,-.5,.25,1),(1.625,.75,1.25,1))[b]
 if name=="FOREGROUND_STRIPE":b=((lx//2)+(ly//2))%2;return ((2,.125,-.5,1),(-.25,1.5,.875,1))[b]
 if name=="OLD_PATCH":b=(lx//2)%2;return ((1.75,-.5,.25,1),(-.25,.5,1.5,1))[b]
 if name=="NEW_PATCH":b=(ly//2)%2;return ((.25,1.75,-.5,1),(1.25,-.25,.75,1))[b]
 raise RuntimeError("texture")
def surface(tex,depth,layer,x,y,offset=(0,0)):return texture(tex,x-offset[0],y-offset[1]),float(depth),float(layer)
def scene(f,frame,x,y):
 fid=f["id"]
 if fid=="TEXTURED_FOREGROUND_CROSSING_103X63":
  fg=f["foreground"];bg=f["background"];box=f[f"{frame}ForegroundBox"];off=f["foregroundLocalOffset"][frame] if inside(x,y,box) else f["backgroundLocalOffset"][frame];s=fg if inside(x,y,box) else bg;return surface(s["texture"],s["depth"],s["layerId"],x,y,off)
 if fid=="TEXTURED_CAMERA_PAN_107X61":
  box=f[f"{frame}ForegroundBox"];s=f["foreground"] if inside(x,y,box) else f["background"];return surface(s["texture"],s["depth"],s["layerId"],x,y,f["allLayerLocalOffset"][frame])
 if fid=="TEXTURED_DEPTH_SWAP_SAME_ID_89X49":
  key=f"{frame}Patch";box=f[f"{frame}PatchBox"]
  if inside(x,y,box):s=f[key];return surface(s["texture"],s["depth"],s["layerId"],x,y,s["localOffset"])
  s=f["background"];return surface(s["texture"],s["depth"],s["layerId"],x,y,s["localOffset"])
 if fid=="TEXTURED_STATIC_CONTROL_71X43":
  s=f["foreground"] if inside(x,y,f["foregroundBox"]) else f["background"];return surface(s["texture"],s["depth"],s["layerId"],x,y)
 raise RuntimeError("fixture")
def motion(f,x,y):
 fid=f["id"]
 if fid=="TEXTURED_FOREGROUND_CROSSING_103X63":return f["foregroundMotion"] if inside(x,y,f["currentForegroundBox"]) else f["backgroundMotion"]
 if fid=="TEXTURED_CAMERA_PAN_107X61":return f["allLayerMotion"]
 if fid=="TEXTURED_DEPTH_SWAP_SAME_ID_89X49":return f["patchMotion"] if inside(x,y,f["currentPatchBox"]) else f["backgroundMotion"]
 return f["motion"]
def noise(x,y):s=1 if (x+3*y)%2==0 else -1;return (f32(s/16),f32(-s/32),f32(s/64),0.0)
def pack(values):return struct.pack(f"<{len(values)}f",*values)
def build(f):
 w,h=f["resolution"];n=w*h;pc=[0.0]*(n*4);cc=[0.0]*(n*4);pd=[0.0]*n;cd=[0.0]*n;pi=[0.0]*n;ci=[0.0]*n;mv=[0.0]*(n*2);target=[0.0]*(n*4)
 for y in range(h):
  for x in range(w):
   k=y*w+x;pcol,pz,pid=scene(f,"previous",x,y);ccol,cz,cid=scene(f,"current",x,y);no=noise(x,y);pc[k*4:k*4+4]=[f32(pcol[c]+no[c]) for c in range(4)];cc[k*4:k*4+4]=[f32(v) for v in ccol];target[k*4:k*4+4]=[f32(v) for v in ccol];pd[k]=f32(pz);cd[k]=f32(cz);pi[k]=f32(pid);ci[k]=f32(cid);mv[k*2:k*2+2]=[f32(v) for v in motion(f,x,y)]
 valid=bytearray(n)
 for y in range(h):
  for x in range(w):
   k=y*w+x;dx,dy=mv[k*2:k*2+2];qx,qy=x-int(dx),y+int(dy);ok=0<=qx<w and 0<=qy<h
   if ok:q=qy*w+qx;ok=pi[q]==ci[k] and abs(pd[q]-cd[k])<=max(1.,cd[k])/1024 and pc[q*4+3]>0 and cc[k*4+3]>0
   valid[k]=int(ok)
   if ok:
    no=noise(qx,qy);cc[k*4:k*4+4]=[f32(target[k*4+c]-no[c]) for c in range(4)]
 def accumulate(sign=1,naive=False):
  out=list(cc)
  for y in range(h):
   for x in range(w):
    k=y*w+x;dx,dy=mv[k*2:k*2+2];qx,qy=x-sign*int(dx),y+sign*int(dy);ok=0<=qx<w and 0<=qy<h
    if ok and not naive:q=qy*w+qx;ok=pi[q]==ci[k] and abs(pd[q]-cd[k])<=max(1.,cd[k])/1024 and pc[q*4+3]>0 and cc[k*4+3]>0
    if ok:
     q=qy*w+qx
     for c in range(4):out[k*4+c]=f32(.5*cc[k*4+c]+.5*pc[q*4+c])
  return out
 resolved=accumulate();naive=accumulate(1,True);wrong=accumulate(-1,False)
 def metrics(a):
  ds=[abs(float(a[i])-float(target[i])) for i in range(len(a))];return {"wrongPixels":sum(any(ds[k*4+c]!=0 for c in range(4)) for k in range(n)),"maximumAbsoluteError":max(ds)}
 arrays={"previousRgba":pc,"currentRgba":cc,"previousDepth":pd,"currentDepth":cd,"previousLayer":pi,"currentLayer":ci,"motion":mv,"analyticValidity":bytes(valid),"resolvedRgba":resolved,"cleanTarget":target};return arrays,metrics(naive),metrics(wrong)
def encoded(name,a):return a if name=="analyticValidity" else pack(a)
def main():
 p=argparse.ArgumentParser();p.add_argument("--spec",type=Path,required=True);p.add_argument("--fixture",required=True);p.add_argument("--output-dir",type=Path,required=True);p.add_argument("--report",type=Path,required=True);a=p.parse_args();spec=json.loads(a.spec.read_text());f=next((x for x in spec["fixtures"] if x["id"]==a.fixture),None)
 if sha(a.spec)!=SPEC_SHA256 or f is None or sha(sys.executable)!=spec["runtime"]["python"]["sha256"] or a.output_dir.exists() or a.report.exists():raise RuntimeError("identity/output mismatch")
 arrays,naive,wrong=build(f);a.output_dir.mkdir(parents=True);records={}
 for name,file in FILES.items():pth=a.output_dir/file;pth.write_bytes(encoded(name,arrays[name]));records[name]={"uri":str(pth),"sha256":sha(pth),"bytes":pth.stat().st_size}
 v=arrays["analyticValidity"];r=arrays["resolvedRgba"];t=arrays["cleanTarget"];cur=arrays["currentRgba"];invalid=all(v[k] or all(r[k*4+c]==cur[k*4+c] for c in range(4)) for k in range(len(v)));valid=all(not v[k] or all(r[k*4+c]==t[k*4+c] for c in range(4)) for k in range(len(v)));body={"schemaVersion":"bfs.layerDepthTemporalHoldoutPythonReport.v0.1","experimentId":spec["experimentId"],"fixtureId":a.fixture,"producer":"python","pid":os.getpid(),"arrays":records,"metrics":{"validPixels":sum(v),"invalidPixels":len(v)-sum(v),"resolvedExact":encoded("resolvedRgba",r)==encoded("cleanTarget",t),"invalidPixelsEqualCurrent":invalid,"validPixelsEqualTarget":valid,"naiveControl":naive,"wrongSignControl":wrong},"operationCounts":{"pythonAccumulatorProcesses":1,"nodeAccumulatorProcesses":0,"exrEncoderProcesses":0,"blenderProcesses":0,"renderCalls":0,"cyclesRayRenders":0}};a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps({**body,"reportHash":ch(body)},indent=2,sort_keys=True,allow_nan=False)+"\n");print(f"BFS_B52_D9_1_PYTHON_OK fixture={a.fixture} resolved={records['resolvedRgba']['sha256']} valid={sum(v)}/{len(v)}")
if __name__=="__main__":main()
