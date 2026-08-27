"""Export B48 Combined passes through the frozen ACES 2 SDR display transform."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import OpenImageIO as oiio
import PyOpenColorIO as ocio


CELLS=("C032_RAW","C032_OIDN","C128_RAW","C128_OIDN","REF_A")


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


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--experiment-root",type=Path,required=True);parser.add_argument("--ocio",type=Path,required=True);parser.add_argument("--output-dir",type=Path,required=True);args=parser.parse_args();args.output_dir.mkdir(parents=True,exist_ok=True)
    config=ocio.Config.CreateFromFile(str(args.ocio));transform=ocio.DisplayViewTransform(src="ACEScg",display="sRGB - Display",view="ACES 2.0 - SDR 100 nits (Rec.709)");processor=config.getProcessor(transform).getDefaultCPUProcessor();artifacts=[]
    for shot in ("TABLETOP","INTERIOR"):
        for cell in CELLS:
            source=args.experiment_root/f"{shot}-{cell}"/"production.exr";pixels=combined(source);rgb=pixels[...,:3].reshape(-1,3);display=np.asarray([processor.applyRGB(row.tolist()) for row in rgb],dtype=np.float32).reshape(pixels.shape[0],pixels.shape[1],3);rgba=np.concatenate((np.clip(display,0,1),np.clip(pixels[...,3:4],0,1)),axis=2);encoded=np.rint(rgba*255).astype(np.uint8)
            output=args.output_dir/f"{shot.lower()}-{cell.lower().replace('_','-')}.png";spec=oiio.ImageSpec(pixels.shape[1],pixels.shape[0],4,oiio.UINT8);writer=oiio.ImageOutput.create(str(output))
            if writer is None or not writer.open(str(output),spec):raise RuntimeError(f"cannot open PNG output: {output}")
            if not writer.write_image(encoded):raise RuntimeError(writer.geterror())
            writer.close();artifacts.append({"shot":shot,"cell":cell,"source":{"uri":str(source),"sha256":sha256_file(source)},"proxy":{"uri":str(output),"sha256":sha256_file(output),"bytes":output.stat().st_size}})
    manifest={"schemaVersion":"bfs.b48ReviewProxyManifest.v0.1","decisionRole":"HUMAN_NAVIGATION_ONLY","sourceEncoding":"ACEScg","display":"sRGB - Display","view":"ACES 2.0 - SDR 100 nits (Rec.709)","ocio":{"uri":str(args.ocio),"sha256":sha256_file(args.ocio),"name":config.getName()},"artifacts":artifacts}
    (args.output_dir/"manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8");print(f"BFS_B48_PROXIES_OK count={len(artifacts)}",flush=True)


if __name__=="__main__":main()
