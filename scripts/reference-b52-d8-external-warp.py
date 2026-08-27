#!/usr/bin/env python3
"""Independent scalar-Python canonical warp producer for B52-D8."""
from __future__ import annotations
import argparse, hashlib, json, math, os, struct, sys
from pathlib import Path
SPEC_SHA256="94a58f4e3c36b1828cb7e1bc4d5646cd577fac1afd411685235185590644a6a5"
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ch(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def f32(v):return struct.unpack("<f",struct.pack("<f",v))[0]
def values(f,x,y,w,h):
 p=f["sourcePattern"]
 if p=="SIGNED_HDR_ALPHA":return (((17*x+11*y)%64)/16-1,((x^(3*y))%64)/16-.25,((5*x+7*y)%128)/32-.5,((3*x+5*y)%17)/16)
 if p=="HIGH_FREQUENCY_HDR":return (2 if (x+y)%2 else -.25,((13*x+29*y)%32)/8-1,((x^y)&3)/2-.5,((7*x+11*y)%9)/8)
 if p=="EDGE_SENTINEL":
  if y==0:return (4,-1,.25,.125)
  if y==h-1:return (-.75,3,.5,.375)
  if x==0:return (1.5,.25,-.5,.625)
  if x==w-1:return (.75,2.5,-.25,.875)
  return (((9*x+5*y)%64)/16-.5,((3*x+13*y)%32)/8-.25,((x^y)%16)/8-.75,((5*x+7*y)%15)/16)
 raise RuntimeError("unknown pattern")
def displacement(fid,x,y):
 if fid=="SIGNED_HDR_ALPHA_61X43_CLIP":return 3/8,-5/8
 if fid=="HIGH_FREQUENCY_113X67_EXTEND":return -9/8,5/4
 if fid=="EDGE_SENTINEL_79X53_REPEAT_FIELD":return (1/8,-3/8,5/8,-7/8)[x%4],(-1/4,3/4)[y%2]
 raise RuntimeError("unknown fixture")
def resolve(v,n,m):
 if m=="Clip":return v if 0<=v<n else None
 if m=="Extend":return min(max(v,0),n-1)
 if m=="Repeat":return v%n
 raise RuntimeError("unknown extension")
def render(f):
 w,h=f["resolution"];src=[0.0]*(w*h*4);field=[0.0]*(w*h*2)
 for y in range(h):
  for x in range(w):
   si=(y*w+x)*4;src[si:si+4]=[f32(v) for v in values(f,x,y,w,h)];di=(y*w+x)*2;field[di:di+2]=[f32(v) for v in displacement(f["id"],x,y)]
 def tap(x,y):
  sx,sy=resolve(x,w,f["extensionX"]),resolve(y,h,f["extensionY"])
  if sx is None or sy is None:return (0.,0.,0.,0.)
  i=(sy*w+sx)*4;return src[i:i+4]
 out=bytearray(w*h*16)
 for y in range(h):
  for x in range(w):
   di=(y*w+x)*2;u=x-field[di];v=y+field[di+1];x0=math.floor(u);y0=math.floor(v);fx=u-x0;fy=v-y0;ws=((1-fx)*(1-fy),fx*(1-fy),(1-fx)*fy,fx*fy);ts=(tap(x0,y0),tap(x0+1,y0),tap(x0,y0+1),tap(x0+1,y0+1));rgba=[f32(sum(ts[i][c]*ws[i] for i in range(4))) for c in range(4)];struct.pack_into("<4f",out,(y*w+x)*16,*rgba)
 return bytes(out),hashlib.sha256(struct.pack(f"<{len(src)}f",*src)).hexdigest(),hashlib.sha256(struct.pack(f"<{len(field)}f",*field)).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--spec",type=Path,required=True);p.add_argument("--fixture",required=True);p.add_argument("--output",type=Path,required=True);p.add_argument("--report",type=Path,required=True);a=p.parse_args();spec=json.loads(a.spec.read_text());f=next((x for x in spec["fixtures"] if x["id"]==a.fixture),None)
 if sha(a.spec)!=SPEC_SHA256 or f is None or sha(sys.executable)!=spec["runtime"]["python"]["sha256"]:raise RuntimeError("identity mismatch")
 if a.output.exists() or a.report.exists():raise RuntimeError("refusing overwrite")
 raw,sh,dh=render(f);a.output.parent.mkdir(parents=True,exist_ok=False);a.output.write_bytes(raw);body={"schemaVersion":"bfs.externalCanonicalWarpPythonProducerReport.v0.1","experimentId":spec["experimentId"],"fixtureId":a.fixture,"producer":"python","pid":os.getpid(),"arrays":{"sourceFloat32Sha256":sh,"displacementFloat32Sha256":dh},"output":{"uri":str(a.output),"sha256":sha(a.output),"bytes":a.output.stat().st_size},"operationCounts":{"pythonProducerProcesses":1,"nodeProducerProcesses":0,"exrEncoderProcesses":0,"blenderProcesses":0,"renderCalls":0,"cyclesRayRenders":0}};a.report.write_text(json.dumps({**body,"reportHash":ch(body)},indent=2,sort_keys=True)+"\n");print(f"BFS_B52_D8_PYTHON_PRODUCER_OK fixture={a.fixture} sha={sha(a.output)}")
if __name__=="__main__":main()
