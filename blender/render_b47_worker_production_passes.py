"""Render the frozen B47 two-frame multipart production-pass pack."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import bpy
import PyOpenColorIO as ocio


def parse_args():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source-sha256",required=True); parser.add_argument("--shot-id",required=True)
    parser.add_argument("--frames",required=True); parser.add_argument("--plan-hash",required=True)
    parser.add_argument("--scene-hash",required=True); parser.add_argument("--structure-hash",required=True)
    parser.add_argument("--ocio-sha256",required=True); parser.add_argument("--output-dir",type=Path,required=True)
    args=parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    args.frame_list=[int(value) for value in args.frames.split(",")]
    return args


def sha256_file(path):
    digest=hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b""): digest.update(chunk)
    return digest.hexdigest()


def main():
    args=parse_args()
    if len(args.frame_list)!=2 or args.frame_list!=sorted(set(args.frame_list)): raise RuntimeError("expected two strictly ascending unique frames")
    output=args.output_dir.resolve(); output.mkdir(parents=True,exist_ok=True); milestones=output/"milestones.jsonl"; sequence=0
    def mark(name,details=None):
        nonlocal sequence
        sequence+=1; record={"shotId":args.shot_id,"sequence":sequence,"name":name,"monotonicNs":time.monotonic_ns(),"processId":os.getpid(),"details":details or {}}
        with milestones.open("a",encoding="utf-8") as handle: handle.write(json.dumps(record,sort_keys=True,separators=(",",":"))+"\n"); handle.flush(); os.fsync(handle.fileno())
    started=time.perf_counter(); mark("PROCESS_STARTED")
    source=Path(bpy.data.filepath).resolve(); source_sha=sha256_file(source)
    if source_sha!=args.source_sha256: raise RuntimeError(f"source SHA mismatch: {source_sha}")
    if tuple(bpy.app.version[:3])!=(5,2,0): raise RuntimeError(f"Blender 5.2 required: {bpy.app.version_string}")
    scene=bpy.context.scene; layer=bpy.context.view_layer
    bindings={"planHash":scene.get("bfs_plan_hash"),"sceneSpecHash":scene.get("bfs_scene_spec_hash"),"structureHash":scene.get("bfs_structure_hash"),"ocioConfigSha256":scene.get("bfs_ocio_sha256")}
    expected={"planHash":args.plan_hash,"sceneSpecHash":args.scene_hash,"structureHash":args.structure_hash,"ocioConfigSha256":args.ocio_sha256}
    if bindings!=expected: raise RuntimeError(f"binding mismatch: {bindings}")
    bindings["shotSeed"]=int(scene["bfs_shot_seed"])
    if any(frame<scene.frame_start or frame>scene.frame_end for frame in args.frame_list): raise RuntimeError("frame outside source range")
    config=ocio.GetCurrentConfig()
    if config.getName()!=scene.get("bfs_ocio_config"): raise RuntimeError("OCIO config mismatch")
    mark("SOURCE_VERIFIED",{"sourceSha256":source_sha,**bindings})

    scene.render.engine="CYCLES"; scene.cycles.device="CPU"; scene.cycles.samples=8; scene.cycles.seed=bindings["shotSeed"]; scene.cycles.use_animated_seed=False; scene.cycles.use_denoising=False
    scene.render.use_motion_blur=False; scene.render.use_persistent_data=False; scene.render.threads_mode="FIXED"; scene.render.threads=4
    scene.render.resolution_x=128; scene.render.resolution_y=72; scene.render.resolution_percentage=100; scene.render.film_transparent=False; scene.render.use_compositing=False; scene.render.use_sequencer=False; scene.render.use_stamp=False
    layer.use_pass_combined=True; layer.use_pass_z=True; layer.use_pass_normal=True; layer.use_pass_position=False; layer.use_pass_vector=True
    layer.use_pass_cryptomatte_object=True; layer.use_pass_cryptomatte_material=False; layer.use_pass_cryptomatte_asset=False; layer.pass_cryptomatte_depth=6
    if hasattr(layer.cycles,"use_denoising"): layer.cycles.use_denoising=False
    settings={"engine":scene.render.engine,"device":scene.cycles.device,"resolution":[scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage],"samples":scene.cycles.samples,"seed":scene.cycles.seed,"animatedSeed":scene.cycles.use_animated_seed,"denoising":scene.cycles.use_denoising,"motionBlur":scene.render.use_motion_blur,"persistentData":scene.render.use_persistent_data,"threadsMode":scene.render.threads_mode,"threads":scene.render.threads,"filmTransparent":scene.render.film_transparent,"compositing":scene.render.use_compositing,"sequencer":scene.render.use_sequencer}
    pass_state={"viewLayer":layer.name,"Combined":layer.use_pass_combined,"Depth":layer.use_pass_z,"Normal":layer.use_pass_normal,"Position":layer.use_pass_position,"Vector":layer.use_pass_vector,"CryptoObject":layer.use_pass_cryptomatte_object,"CryptoMaterial":layer.use_pass_cryptomatte_material,"CryptoAsset":layer.use_pass_cryptomatte_asset,"cryptomatteDepth":layer.pass_cryptomatte_depth,"cryptomatteAccurate":layer.use_pass_cryptomatte_accurate}
    mark("SCENE_CONFIGURED",{"settings":settings,"passState":pass_state})
    reports=[]
    for frame in args.frame_list:
        scene.frame_set(frame); mark("FRAME_STARTED",{"frame":frame}); result=bpy.ops.render.render(write_still=False)
        if "FINISHED" not in result: raise RuntimeError(f"render failed at {frame}: {sorted(result)}")
        image=bpy.data.images.get("Render Result")
        if image is None: raise RuntimeError("Render Result absent")
        scene.render.image_settings.media_type="MULTI_LAYER_IMAGE"; scene.render.image_settings.file_format="OPEN_EXR_MULTILAYER"; scene.render.image_settings.color_mode="RGBA"; scene.render.image_settings.color_depth="32"; scene.render.image_settings.exr_codec="ZIP"
        exr=output/f"frame-{frame:04d}.exr"; image.save_render(str(exr),scene=scene)
        if not exr.exists(): raise RuntimeError(f"frame {frame} EXR absent")
        artifact={"uri":exr.name,"sha256":sha256_file(exr),"bytes":exr.stat().st_size}; reports.append({"frame":frame,"artifact":artifact}); mark("FRAME_COMPLETED",{"frame":frame,"exr":artifact})
    report={"schemaVersion":"bfs.workerProductionPassReport.v0.1","shotId":args.shot_id,"frames":args.frame_list,"source":{"uri":str(source),"sha256":source_sha,"bytes":source.stat().st_size},"bindings":bindings,"blender":{"version":bpy.app.version_string,"buildHash":bpy.app.build_hash.decode() if isinstance(bpy.app.build_hash,bytes) else str(bpy.app.build_hash),"buildPlatform":bpy.app.build_platform.decode() if isinstance(bpy.app.build_platform,bytes) else str(bpy.app.build_platform)},"ocio":{"name":config.getName(),"sha256":scene.get("bfs_ocio_sha256"),"declaredEncoding":scene.get("bfs_declared_encoding")},"appliedSettings":settings,"passState":pass_state,"saveSettings":{"mediaType":scene.render.image_settings.media_type,"fileFormat":scene.render.image_settings.file_format,"colorMode":scene.render.image_settings.color_mode,"colorDepth":scene.render.image_settings.color_depth,"codec":scene.render.image_settings.exr_codec},"renderOperatorCalls":len(args.frame_list),"savesFromSameRenderResult":len(args.frame_list),"frameReports":reports,"elapsedSeconds":round(time.perf_counter()-started,6),"passed":True}
    report_path=output/"render.report.json"; report_path.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8"); mark("REPORT_WRITTEN",{"reportSha256":sha256_file(report_path),"passed":True})
    print(f"BFS_B47_RENDER_OK {args.shot_id} frames={len(args.frame_list)}",flush=True)


if __name__=="__main__":
    try: main()
    except Exception as error: print(f"BFS_B47_RENDER_ERROR {error}",file=sys.stderr,flush=True); raise SystemExit(1) from error
