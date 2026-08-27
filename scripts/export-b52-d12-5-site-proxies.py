"""Export non-decisional ACES display and paired radius-domain proxies for D12.5-C2."""

from __future__ import annotations

import argparse, hashlib, json
from pathlib import Path
import numpy as np
import OpenImageIO as oiio
import PyOpenColorIO as ocio

def sha_file(path:Path)->str:
    d=hashlib.sha256()
    with path.open("rb") as h:
        for chunk in iter(lambda:h.read(1024*1024),b""):d.update(chunk)
    return d.hexdigest()
def combined(path:Path)->np.ndarray:
    first=oiio.ImageBuf(str(path),0,0)
    for index in range(first.nsubimages):
        image=oiio.ImageBuf(str(path),index,0)
        if str(image.spec().getattribute("oiio:subimagename") or "").endswith(".Combined"):return np.asarray(image.get_pixels(oiio.FLOAT),dtype=np.float32)
    raise RuntimeError(f"Combined pass absent: {path}")
def write_png(path:Path,pixels:np.ndarray)->None:
    encoded=np.rint(np.clip(pixels,0,1)*255).astype(np.uint8);spec=oiio.ImageSpec(encoded.shape[1],encoded.shape[0],encoded.shape[2],oiio.UINT8);writer=oiio.ImageOutput.create(str(path))
    if writer is None or not writer.open(str(path),spec):raise RuntimeError(f"cannot open PNG: {path}")
    if not writer.write_image(encoded):raise RuntimeError(writer.geterror())
    writer.close()
def main()->None:
    p=argparse.ArgumentParser();p.add_argument("--experiment-root",type=Path,required=True);p.add_argument("--spec",type=Path,required=True);p.add_argument("--ocio",type=Path,required=True);p.add_argument("--output-dir",type=Path,required=True);a=p.parse_args();spec=json.loads(a.spec.read_text());results_path=a.experiment_root/"results.json";results=json.loads(results_path.read_text());config=ocio.Config.CreateFromFile(str(a.ocio));transform=ocio.DisplayViewTransform(src="ACEScg",display="sRGB - Display",view="ACES 2.0 - SDR 100 nits (Rec.709)");processor=config.getProcessor(transform).getDefaultCPUProcessor();a.output_dir.mkdir(parents=True,exist_ok=True)
    names={"STATIC_BEVELED_WEDGE_PANEL_109X67":"wedge-panel","STATIC_NESTED_CURVE_OCCLUSION_137X89":"nested-curves","STATIC_CROSSING_RODS_SPHERE_149X97":"crossing-rods"};artifacts=[]
    for fixture in spec["fixtures"]:
        fid=fixture["id"];width,height=fixture["resolution"];source=a.experiment_root/"sources"/fid/"R1/frame-0/source.exr";beauty=combined(source);rgb=beauty[...,:3].reshape(-1,3);display=np.asarray([processor.applyRGB(row.tolist()) for row in rgb],dtype=np.float32).reshape(height,width,3);alpha=np.clip(beauty[...,3:4],0,1);base=names[fid];beauty_output=a.output_dir/f"{base}-beauty.png";write_png(beauty_output,np.concatenate((display,alpha),axis=2));artifacts.append({"id":f"{base}-beauty","kind":"ACES_DISPLAY_PROXY","source":{"uri":str(source),"sha256":sha_file(source)},"output":{"uri":str(beauty_output),"sha256":sha_file(beauty_output),"bytes":beauty_output.stat().st_size}})
        consumer=a.experiment_root/"consumers/python"/fid/"R1/arrays"
        for radius,color in ((2,np.asarray([.35,1,.56],dtype=np.float32)),(3,np.asarray([.35,.82,1],dtype=np.float32))):
            interior_path=consumer/f"radius{radius}-interior.u8";boundary_path=consumer/f"radius{radius}-boundary.u8";interior=np.fromfile(interior_path,dtype=np.uint8).reshape(height,width).astype(bool);boundary=np.fromfile(boundary_path,dtype=np.uint8).reshape(height,width).astype(bool);overlay=display*np.float32(.22);overlay[interior]=overlay[interior]*np.float32(.2)+color*np.float32(.8);overlay[boundary]=overlay[boundary]*np.float32(.15)+np.asarray([1,.4,.24],dtype=np.float32)*np.float32(.85);output=a.output_dir/f"{base}-radius{radius}.png";write_png(output,np.concatenate((overlay,np.ones((height,width,1),dtype=np.float32)),axis=2));artifacts.append({"id":f"{base}-radius{radius}","kind":"OWNER_RADIUS_DOMAIN_DIAGNOSTIC","radius":radius,"legend":{"interior":"green" if radius==2 else "cyan","boundary":"orange","unregistered":"dark"},"sources":[{"uri":str(interior_path),"sha256":sha_file(interior_path)},{"uri":str(boundary_path),"sha256":sha_file(boundary_path)}],"counts":{"interior":int(interior.sum()),"boundary":int(boundary.sum())},"output":{"uri":str(output),"sha256":sha_file(output),"bytes":output.stat().st_size}})
    manifest={"schemaVersion":"bfs.b52D125SiteProxyManifest.v0.1","decisionRole":"HUMAN_NAVIGATION_ONLY_FORMAL_DECISION_UNCHANGED","experimentId":spec["experimentId"],"formalResult":{"uri":str(results_path),"sha256":sha_file(results_path),"verdict":results["verdict"]},"sourceEncoding":"ACEScg scene-linear float32","display":"sRGB - Display","view":"ACES 2.0 - SDR 100 nits (Rec.709)","ocio":{"uri":str(a.ocio),"sha256":sha_file(a.ocio),"name":config.getName()},"artifacts":artifacts};manifest_path=a.output_dir/"manifest.json";manifest_path.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n");print(f"BFS_B52_D125_SITE_PROXIES_OK count={len(artifacts)} manifest={sha_file(manifest_path)}")
if __name__=="__main__":main()
