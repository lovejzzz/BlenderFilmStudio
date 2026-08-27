"""Canonicalize one formal B47 multipart EXR by subimage."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


def sha256_file(path):
    digest=hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b""): digest.update(chunk)
    return digest.hexdigest()


def value(attribute,spec):
    try: raw=attribute.value
    except Exception: raw=spec.getattribute(str(attribute.name))
    if raw is None or isinstance(raw,(bool,int,float,str)): return raw
    try: return [value_item for value_item in raw]
    except TypeError: return str(raw)


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--input",type=Path,required=True); parser.add_argument("--frame",type=int,required=True); parser.add_argument("--output",required=True); args=parser.parse_args()
    first=oiio.ImageBuf(str(args.input),0,0)
    if not first.initialized: raise RuntimeError(first.geterror())
    subimages=[]; crypto_raw={}
    for index in range(first.nsubimages):
        image=oiio.ImageBuf(str(args.input),index,0); spec=image.spec(); pixels=np.ascontiguousarray(np.asarray(image.get_pixels(oiio.FLOAT),dtype="<f4"))
        name=str(spec.getattribute("oiio:subimagename") or f"subimage-{index}"); pass_name=name.rsplit(".",1)[-1]; channels=list(spec.channelnames)
        metadata={"name":name,"shape":list(pixels.shape),"channels":channels,"dtype":"float32-le","order":"C"}; header=json.dumps(metadata,sort_keys=True,separators=(",",":")).encode()+b"\n"
        finite=np.isfinite(pixels); finite_values=pixels[finite]
        for attribute in spec.extra_attribs:
            key=str(attribute.name)
            if "cryptomatte" in key.lower(): crypto_raw[key]=value(attribute,spec)
        subimages.append({"index":index,"pass":pass_name,"name":name,"width":spec.width,"height":spec.height,"channels":channels,"channelFormats":[str(item) for item in spec.channelformats] if spec.channelformats else [str(spec.format)]*spec.nchannels,"metadata":metadata,"canonicalFloat32Sha256":hashlib.sha256(header+pixels.tobytes(order="C")).hexdigest(),"componentCount":int(pixels.size),"finiteCount":int(np.count_nonzero(finite)),"nanCount":int(np.count_nonzero(np.isnan(pixels))),"infinityCount":int(np.count_nonzero(np.isinf(pixels))),"nonZeroFiniteCount":int(np.count_nonzero(np.logical_and(finite,pixels!=0))),"finiteMin":float(finite_values.min()) if finite_values.size else None,"finiteMax":float(finite_values.max()) if finite_values.size else None})
    def suffix(name):
        return next((item for key,item in crypto_raw.items() if key.lower().endswith("/"+name)),None)
    manifest_raw=suffix("manifest"); manifest_valid=False; manifest={}
    if isinstance(manifest_raw,str):
        try: manifest=json.loads(manifest_raw); manifest_valid=isinstance(manifest,dict)
        except json.JSONDecodeError: pass
    binding={"frame":args.frame,"passes":[{"pass":item["pass"],"canonicalFloat32Sha256":item["canonicalFloat32Sha256"]} for item in subimages]}
    result={"schemaVersion":"bfs.workerProductionPassInspection.v0.1","runtime":{"python":platform.python_version(),"openImageIO":oiio.VERSION_STRING,"numpy":np.__version__},"frame":args.frame,"input":{"uri":str(args.input.resolve()),"sha256":sha256_file(args.input),"bytes":args.input.stat().st_size},"subimageCount":len(subimages),"subimages":subimages,"cryptomatte":{"hash":suffix("hash"),"conversion":suffix("conversion"),"name":suffix("name"),"manifestRaw":manifest_raw,"manifestValid":manifest_valid,"manifest":dict(sorted(manifest.items()))},"packSha256":hashlib.sha256(json.dumps(binding,sort_keys=True,separators=(",",":")).encode()).hexdigest()}
    encoded=json.dumps(result,indent=2,sort_keys=True)+"\n"
    if args.output=="-": sys.stdout.write(encoded)
    else: Path(args.output).write_text(encoded,encoding="utf-8")
    print(f"BFS_B47_ANALYSIS_OK frame={args.frame} subimages={len(subimages)}",file=sys.stderr,flush=True)


if __name__=="__main__":
    try: main()
    except Exception as error: print(f"BFS_B47_ANALYSIS_ERROR {error}",file=sys.stderr); raise SystemExit(1) from error
