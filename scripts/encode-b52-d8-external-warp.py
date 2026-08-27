#!/usr/bin/env python3
"""Encode one B52-D8 canonical RGBA32 array to Raw FLOAT EXR and verify decode."""
from __future__ import annotations
import argparse, hashlib, json, os, sys
from pathlib import Path
import numpy as np, OpenImageIO as oiio
SPEC_SHA256="94a58f4e3c36b1828cb7e1bc4d5646cd577fac1afd411685235185590644a6a5"
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ch(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def ah(a):return hashlib.sha256(np.ascontiguousarray(a,dtype="<f4").tobytes()).hexdigest()
def read(path):
 im=oiio.ImageInput.open(str(path));
 if im is None:raise RuntimeError(oiio.geterror())
 sp=im.spec();a=np.asarray(im.read_image(0,0,0,4,oiio.FLOAT),np.float32).reshape(sp.height,sp.width,4);im.close();return np.ascontiguousarray(a,dtype="<f4"),sp
def main():
 p=argparse.ArgumentParser();p.add_argument("--spec",type=Path,required=True);p.add_argument("--fixture",required=True);p.add_argument("--producer",choices=("python","node"),required=True);p.add_argument("--input",type=Path,required=True);p.add_argument("--output",type=Path,required=True);p.add_argument("--report",type=Path,required=True);a=p.parse_args();spec=json.loads(a.spec.read_text());f=next((x for x in spec["fixtures"] if x["id"]==a.fixture),None)
 if sha(a.spec)!=SPEC_SHA256 or f is None or sha(sys.executable)!=spec["runtime"]["python"]["sha256"]:raise RuntimeError("identity mismatch")
 if a.output.exists() or a.report.exists():raise RuntimeError("refusing overwrite")
 w,h=f["resolution"];raw=a.input.read_bytes()
 if len(raw)!=w*h*16:raise RuntimeError("raw length mismatch")
 pixels=np.frombuffer(raw,dtype="<f4").reshape(h,w,4);sp=oiio.ImageSpec(w,h,4,oiio.FLOAT);sp.channelnames=("R","G","B","A");sp.attribute("compression","zip");sp.attribute("oiio:ColorSpace","Raw");a.output.parent.mkdir(parents=True,exist_ok=True);o=oiio.ImageOutput.create(str(a.output))
 if o is None or not o.open(str(a.output),sp) or not o.write_image(np.ascontiguousarray(pixels,np.float32)):raise RuntimeError(oiio.geterror() or (o.geterror() if o else "writer"))
 o.close();decoded,dsp=read(a.output);exact=bool(np.array_equal(decoded,pixels));layout={"width":dsp.width,"height":dsp.height,"channels":list(dsp.channelnames),"format":str(dsp.format)};body={"schemaVersion":"bfs.externalCanonicalWarpEncoderReport.v0.1","experimentId":spec["experimentId"],"fixtureId":a.fixture,"producer":a.producer,"pid":os.getpid(),"input":{"uri":str(a.input),"sha256":sha(a.input),"bytes":a.input.stat().st_size},"output":{"uri":str(a.output),"sha256":sha(a.output),"bytes":a.output.stat().st_size,"decodedCanonicalFloat32Sha256":ah(decoded)},"layout":layout,"encodeDecodeExact":exact,"operationCounts":{"pythonProducerProcesses":0,"nodeProducerProcesses":0,"exrEncoderProcesses":1,"blenderProcesses":0,"renderCalls":0,"cyclesRayRenders":0}};a.report.write_text(json.dumps({**body,"reportHash":ch(body)},indent=2,sort_keys=True)+"\n");print(f"BFS_B52_D8_ENCODER_OK fixture={a.fixture} producer={a.producer} exact={exact}")
 if not exact:raise SystemExit(2)
if __name__=="__main__":main()
