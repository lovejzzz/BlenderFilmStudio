#!/usr/bin/env python3
"""Decode one B52-D12.5 multipart pair into canonical float32 arrays."""

from __future__ import annotations

import argparse, hashlib, json, os, sys
from pathlib import Path
import numpy as np
import OpenImageIO as oiio

SPEC_SHA256="b24aa05aeb1ab7a33e8fc57afc646308b5454eb0a5c5bf77dbbf8cc33f2ed5f2"
FILES={"previousRgba":"previous.rgba32","currentRgba":"current.rgba32","previousOwner":"previous-owner.f32","currentOwner":"current-owner.f32","vector":"vector.xy32","vectorNext":"vector-next.xy32"}
def sha_bytes(value:bytes)->str:return hashlib.sha256(value).hexdigest()
def sha_file(path:Path)->str:
    d=hashlib.sha256()
    with path.open("rb") as h:
        for chunk in iter(lambda:h.read(1024*1024),b""):d.update(chunk)
    return d.hexdigest()
def canon(value:object)->str:return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def source(path:Path,exr:Path,fixture:str,repeat:int,frame:int)->dict:
    report=json.loads(path.read_text());body={k:v for k,v in report.items() if k!="reportHash"}
    if report.get("reportHash")!=canon(body) or report.get("fixtureId")!=fixture or report.get("repeat")!=repeat or report.get("frame")!=frame or report.get("probeOnly") is not False:raise RuntimeError("D12.5 source identity mismatch")
    if report.get("output",{}).get("sha256")!=sha_file(exr):raise RuntimeError("D12.5 source EXR binding mismatch")
    return report
def multipart(path:Path,width:int,height:int,layer:str)->dict:
    first=oiio.ImageBuf(str(path),0,0)
    if first.has_error:raise RuntimeError(first.geterror())
    roster=[];channels={};parts={}
    for index in range(first.nsubimages):
        image=oiio.ImageBuf(str(path),index,0);spec=image.spec();name=str(spec.getattribute("oiio:subimagename") or f"subimage-{index}");roster.append(name);channels[name]=list(spec.channelnames);parts[name]=np.ascontiguousarray(np.asarray(image.get_pixels(oiio.FLOAT),dtype="<f4"))
    expected=[f"{layer}.Combined",f"{layer}.Depth",f"{layer}.Vector",f"{layer}.Object Index"]
    expected_channels={expected[0]:[f"{expected[0]}.R",f"{expected[0]}.G",f"{expected[0]}.B",f"{expected[0]}.A"],expected[1]:[f"{expected[1]}.Z"],expected[2]:[f"{expected[2]}.X",f"{expected[2]}.Y",f"{expected[2]}.Z",f"{expected[2]}.W"],expected[3]:[f"{expected[3]}.X"]}
    if roster!=expected or channels!=expected_channels:raise RuntimeError("D12.5 multipart roster/channel mismatch")
    for name,count in ((expected[0],4),(expected[1],1),(expected[2],4),(expected[3],1)):
        if list(parts[name].shape)!=[height,width,count] or not np.isfinite(parts[name]).all():raise RuntimeError(f"D12.5 multipart shape/finite mismatch: {name}")
    return {"roster":roster,"channels":channels,"parts":parts}
def main()->None:
    p=argparse.ArgumentParser();p.add_argument("--spec",type=Path,required=True);p.add_argument("--fixture",required=True);p.add_argument("--repeat",type=int,choices=(1,2),required=True);p.add_argument("--previous-exr",type=Path,required=True);p.add_argument("--current-exr",type=Path,required=True);p.add_argument("--previous-report",type=Path,required=True);p.add_argument("--current-report",type=Path,required=True);p.add_argument("--output-dir",type=Path,required=True);p.add_argument("--report",type=Path,required=True);a=p.parse_args();spec=json.loads(a.spec.read_text())
    if sha_file(a.spec)!=SPEC_SHA256 or sha_file(Path(sys.executable))!=spec["runtime"]["python"]["sha256"]:raise RuntimeError("D12.5 spec/Python identity mismatch")
    if oiio.VERSION_STRING!=spec["runtime"]["python"]["openImageIO"] or np.__version__!=spec["runtime"]["python"]["numpy"]:raise RuntimeError("D12.5 library identity mismatch")
    fixture=next((row for row in spec["fixtures"] if row["id"]==a.fixture),None)
    if fixture is None or a.output_dir.exists() or a.report.exists():raise RuntimeError("D12.5 fixture invalid or output exists")
    previous_report=source(a.previous_report,a.previous_exr,a.fixture,a.repeat,0);current_report=source(a.current_report,a.current_exr,a.fixture,a.repeat,1);width,height=fixture["resolution"];layer=spec["sceneContract"]["render"]["viewLayer"];previous=multipart(a.previous_exr,width,height,layer);current=multipart(a.current_exr,width,height,layer)
    arrays={"previousRgba":previous["parts"][f"{layer}.Combined"],"currentRgba":current["parts"][f"{layer}.Combined"],"previousOwner":previous["parts"][f"{layer}.Object Index"][...,0],"currentOwner":current["parts"][f"{layer}.Object Index"][...,0],"vector":current["parts"][f"{layer}.Vector"][...,:2],"vectorNext":current["parts"][f"{layer}.Vector"][...,2:4]}
    a.output_dir.mkdir(parents=True,exist_ok=False);records={}
    for name,filename in FILES.items():
        payload=np.ascontiguousarray(arrays[name],dtype="<f4").tobytes(order="C");target=a.output_dir/filename;target.write_bytes(payload);records[name]={"uri":str(target),"sha256":sha_bytes(payload),"bytes":len(payload),"shape":list(arrays[name].shape),"dtype":"little-endian-float32"}
    body={"schemaVersion":"bfs.blenderStaticRadiusInterventionAdapterReport.v0.1","experimentId":spec["experimentId"],"fixtureId":a.fixture,"repeat":a.repeat,"pid":os.getpid(),"runtime":{"pythonExecutableSha256":sha_file(Path(sys.executable)),"openImageIO":oiio.VERSION_STRING,"numpy":np.__version__},"inputs":{"previousExr":{"uri":str(a.previous_exr),"sha256":previous_report["output"]["sha256"]},"currentExr":{"uri":str(a.current_exr),"sha256":current_report["output"]["sha256"]}},"multipart":{"previousRoster":previous["roster"],"currentRoster":current["roster"],"channels":previous["channels"]},"arrays":records,"operationCounts":{"adapterProcesses":1,"multipartExrsOpened":2,"canonicalArraysWritten":len(FILES),"modelCalls":0,"networkCalls":0}};report={**body,"reportHash":canon(body)};a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+"\n");print(f"BFS_B52_D125_ADAPTER_OK fixture={a.fixture} repeat={a.repeat} vector={records['vector']['sha256']}")
if __name__=="__main__":main()
