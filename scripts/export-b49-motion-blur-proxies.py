"""Export B49-MB ACES display proxies and fixed-scale difference heatmaps."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import OpenImageIO as oiio
import PyOpenColorIO as ocio


def sha256_file(path):
    digest=hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b""):digest.update(chunk)
    return digest.hexdigest()


def combined(path):
    first=oiio.ImageBuf(str(path),0,0)
    for index in range(first.nsubimages):
        image=oiio.ImageBuf(str(path),index,0);name=str(image.spec().getattribute("oiio:subimagename") or "")
        if name.endswith(".Combined"):return np.asarray(image.get_pixels(oiio.FLOAT),dtype=np.float32)
    raise RuntimeError(f"Combined absent: {path}")


def write_png(path,pixels):
    encoded=np.rint(np.clip(pixels,0,1)*255).astype(np.uint8);spec=oiio.ImageSpec(encoded.shape[1],encoded.shape[0],encoded.shape[2],oiio.UINT8);writer=oiio.ImageOutput.create(str(path))
    if writer is None or not writer.open(str(path),spec):raise RuntimeError(f"cannot open PNG: {path}")
    if not writer.write_image(encoded):raise RuntimeError(writer.geterror())
    writer.close()


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--experiment-root",type=Path,required=True);parser.add_argument("--ocio",type=Path,required=True);parser.add_argument("--output-dir",type=Path,required=True);args=parser.parse_args();args.output_dir.mkdir(parents=True,exist_ok=True)
    sources={cell:args.experiment_root/cell/"production.exr" for cell in ("T_REF_A","T_REF_B","T_REF_C","T_C128_ON","T_C128_OFF","I_C128_ON","I_C128_OFF")};arrays={cell:combined(path) for cell,path in sources.items()};arrays["T_REFERENCE_ENSEMBLE"]=np.mean(np.stack([arrays["T_REF_A"],arrays["T_REF_B"],arrays["T_REF_C"]]).astype(np.float64),axis=0).astype(np.float32)
    config=ocio.Config.CreateFromFile(str(args.ocio));transform=ocio.DisplayViewTransform(src="ACEScg",display="sRGB - Display",view="ACES 2.0 - SDR 100 nits (Rec.709)");processor=config.getProcessor(transform).getDefaultCPUProcessor();artifacts=[]
    proxy_cells={"moving-off":"T_C128_OFF","moving-on":"T_C128_ON","moving-reference-ensemble":"T_REFERENCE_ENSEMBLE","static-off":"I_C128_OFF","static-on":"I_C128_ON"}
    for name,cell in proxy_cells.items():
        pixels=arrays[cell];rgb=pixels[...,:3].reshape(-1,3);display=np.asarray([processor.applyRGB(row.tolist()) for row in rgb],dtype=np.float32).reshape(pixels.shape[0],pixels.shape[1],3);rgba=np.concatenate((display,np.clip(pixels[...,3:4],0,1)),axis=2);output=args.output_dir/f"{name}.png";write_png(output,rgba);source_list=[sources[value] for value in ("T_REF_A","T_REF_B","T_REF_C")] if cell=="T_REFERENCE_ENSEMBLE" else [sources[cell]];artifacts.append({"id":name,"kind":"ACES_DISPLAY_PROXY","sourceExrs":[{"uri":str(path),"sha256":sha256_file(path)} for path in source_list],"output":{"uri":str(output),"sha256":sha256_file(output),"bytes":output.stat().st_size}})
    moving_delta=np.max(np.abs(arrays["T_C128_ON"][...,:3].astype(np.float64)-arrays["T_C128_OFF"][...,:3].astype(np.float64)),axis=2);static_delta=np.max(np.abs(arrays["I_C128_ON"][...,:3].astype(np.float64)-arrays["I_C128_OFF"][...,:3].astype(np.float64)),axis=2);scale=float(np.percentile(moving_delta,99));scale=max(scale,np.finfo(np.float64).eps)
    for name,delta in (("moving-difference",moving_delta),("static-difference",static_delta)):
        normalized=np.clip(delta/scale,0,1).astype(np.float32);rgb=np.stack((normalized*.88,normalized,normalized*.28),axis=2);rgba=np.concatenate((rgb,np.ones((*normalized.shape,1),dtype=np.float32)),axis=2);output=args.output_dir/f"{name}.png";write_png(output,rgba);artifacts.append({"id":name,"kind":"LINEAR_MAX_RGB_ABSOLUTE_DIFFERENCE_HEATMAP","scale":{"black":0,"fullScale":scale,"clamp":"99th percentile of moving on/off difference"},"statistics":{"maximum":float(np.max(delta)),"p99":float(np.percentile(delta,99)),"nonzeroPixels":int(np.count_nonzero(delta))},"output":{"uri":str(output),"sha256":sha256_file(output),"bytes":output.stat().st_size}})
    manifest={"schemaVersion":"bfs.b49MotionBlurProxyManifest.v0.1","decisionRole":"HUMAN_NAVIGATION_ONLY","sourceEncoding":"ACEScg scene-linear float32","display":"sRGB - Display","view":"ACES 2.0 - SDR 100 nits (Rec.709)","differenceScaleSharedAcrossMovingAndStatic":scale,"ocio":{"uri":str(args.ocio),"sha256":sha256_file(args.ocio),"name":config.getName()},"artifacts":artifacts};(args.output_dir/"manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8");print(f"BFS_B49_MB_PROXIES_OK count={len(artifacts)} scale={scale}",flush=True)


if __name__=="__main__":main()
