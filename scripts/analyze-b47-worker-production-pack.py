"""Inspect B47-D1 multipart EXR with Blender-bundled OpenImageIO."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


def sha256_file(path):
    digest=hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b""): digest.update(chunk)
    return digest.hexdigest()


def json_value(value):
    if value is None or isinstance(value,(bool,int,float,str)): return value
    try: return [json_value(item) for item in value]
    except TypeError: return str(value)


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--input",type=Path,required=True); parser.add_argument("--output",type=Path,required=True); args=parser.parse_args()
    first=oiio.ImageBuf(str(args.input),0,0)
    if not first.initialized: raise RuntimeError(first.geterror())
    subimages=[]; crypto_attributes={}
    for index in range(first.nsubimages):
        image=oiio.ImageBuf(str(args.input),index,0); spec=image.spec(); pixels=np.asarray(image.get_pixels(oiio.FLOAT),dtype="<f4"); pixels=np.ascontiguousarray(pixels)
        name=str(spec.getattribute("oiio:subimagename") or f"subimage-{index}"); channels=list(spec.channelnames)
        metadata={"name":name,"shape":list(pixels.shape),"channels":channels,"dtype":"float32-le","order":"C"}
        header=json.dumps(metadata,sort_keys=True,separators=(",",":")).encode()+b"\n"
        attributes={}
        for attribute in spec.extra_attribs:
            key=str(attribute.name)
            if "cryptomatte" in key.lower():
                try:value=attribute.value
                except Exception:value=spec.getattribute(key)
                attributes[key]=json_value(value); crypto_attributes[key]=json_value(value)
        finite=np.isfinite(pixels); nan=np.isnan(pixels); inf=np.isinf(pixels)
        subimages.append({"index":index,"name":name,"width":spec.width,"height":spec.height,"channels":channels,"channelFormats":[str(item) for item in spec.channelformats] if spec.channelformats else [str(spec.format)]*spec.nchannels,"metadata":metadata,"canonicalFloat32Sha256":hashlib.sha256(header+pixels.tobytes(order="C")).hexdigest(),"componentCount":int(pixels.size),"finiteCount":int(np.count_nonzero(finite)),"nanCount":int(np.count_nonzero(nan)),"infinityCount":int(np.count_nonzero(inf)),"nonZeroFiniteCount":int(np.count_nonzero(np.logical_and(finite,pixels!=0))),"finiteMin":float(pixels[finite].min()) if finite.any() else None,"finiteMax":float(pixels[finite].max()) if finite.any() else None,"cryptomatteAttributes":attributes})
    result={"schemaVersion":"bfs.workerProductionPackInspection.v0.1","runtime":{"python":platform.python_version(),"openImageIO":oiio.VERSION_STRING,"numpy":np.__version__},"input":{"uri":str(args.input.resolve()),"sha256":sha256_file(args.input),"bytes":args.input.stat().st_size},"subimageCount":len(subimages),"subimages":subimages,"cryptomatteAttributes":dict(sorted(crypto_attributes.items()))}
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(f"BFS_B47_D1_ANALYSIS_OK subimages={len(subimages)}",flush=True)


if __name__=="__main__": main()
