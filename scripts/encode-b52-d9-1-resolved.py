#!/usr/bin/env python3
"""Encode one B52-D9.1 canonical resolved RGBA32 array to Raw FLOAT EXR."""
from __future__ import annotations
import argparse, hashlib, json, os
from pathlib import Path
import numpy as np, OpenImageIO as oiio

SPEC_SHA256="669077423e0101dd5600576d295c0b7a62189a30b18c1dd6ab18a3b5257cd28f"
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ch(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def ah(a): return hashlib.sha256(np.ascontiguousarray(a,dtype="<f4").tobytes()).hexdigest()
def read_exr(p):
 i=oiio.ImageInput.open(str(p))
 if i is None: raise RuntimeError(oiio.geterror() or f"cannot read {p}")
 s=i.spec(); a=np.asarray(i.read_image(0,0,0,4,oiio.FLOAT),np.float32).reshape(s.height,s.width,4); i.close()
 return np.ascontiguousarray(a,dtype="<f4"),s
def main():
 p=argparse.ArgumentParser(); p.add_argument("--spec",type=Path,required=True); p.add_argument("--fixture",required=True); p.add_argument("--producer",choices=("python","node"),required=True); p.add_argument("--input",type=Path,required=True); p.add_argument("--output",type=Path,required=True); p.add_argument("--report",type=Path,required=True); a=p.parse_args()
 spec=json.loads(a.spec.read_text()); f=next((x for x in spec["fixtures"] if x["id"]==a.fixture),None)
 if sha(a.spec)!=SPEC_SHA256 or f is None or sha(Path(spec["runtime"]["python"]["executable"]))!=spec["runtime"]["python"]["sha256"] or a.output.exists() or a.report.exists(): raise RuntimeError("identity/output")
 w,h=f["resolution"]; raw=a.input.read_bytes()
 if len(raw)!=w*h*4*4: raise RuntimeError("input size")
 pixels=np.frombuffer(raw,dtype="<f4").reshape(h,w,4); a.output.parent.mkdir(parents=True,exist_ok=True)
 o=oiio.ImageOutput.create(str(a.output)); s=oiio.ImageSpec(w,h,4,oiio.FLOAT); s.channelnames=("R","G","B","A"); s.attribute("oiio:ColorSpace","Raw"); s.attribute("compression","zip")
 if o is None or not o.open(str(a.output),s) or not o.write_image(pixels): raise RuntimeError(oiio.geterror() or "EXR write")
 o.close(); decoded,dsp=read_exr(a.output); exact=bool(np.array_equal(decoded,pixels)); layout={"width":dsp.width,"height":dsp.height,"channels":list(dsp.channelnames),"format":str(dsp.format),"compression":dsp.get_string_attribute("compression")}
 body={"schemaVersion":"bfs.layerDepthTemporalHoldoutEncoderReport.v0.1","experimentId":spec["experimentId"],"fixtureId":a.fixture,"producer":a.producer,"pid":os.getpid(),"input":{"uri":str(a.input),"sha256":sha(a.input),"bytes":a.input.stat().st_size},"output":{"uri":str(a.output),"sha256":sha(a.output),"bytes":a.output.stat().st_size,"decodedCanonicalFloat32Sha256":ah(decoded)},"layout":layout,"encodeDecodeExact":exact,"operationCounts":{"pythonAccumulatorProcesses":0,"nodeAccumulatorProcesses":0,"exrEncoderProcesses":1,"blenderProcesses":0,"renderCalls":0,"cyclesRayRenders":0}}
 a.report.parent.mkdir(parents=True,exist_ok=True); a.report.write_text(json.dumps({**body,"reportHash":ch(body)},indent=2,sort_keys=True,allow_nan=False)+"\n")
 print(f"BFS_B52_D9_1_ENCODER_OK fixture={a.fixture} producer={a.producer} exact={exact}")
 if not exact: raise SystemExit(1)
if __name__=="__main__": main()
