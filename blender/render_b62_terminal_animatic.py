"""Render the preregistered B62 terminal 288-frame Eevee animatic."""
from __future__ import annotations
import argparse, hashlib, json, math, os, struct, sys, time
from pathlib import Path
import bpy
import numpy
import OpenImageIO as oiio

SCENE_SHA="0acd4d135c9bac9a7928a9a38da1a0e2f4838fd052a87a9663cef83cb2c373dc"
CAMERAS=((1,96,"SHOT_WIDE_APPROACH","CAM_WIDE_APPROACH"),(97,192,"SHOT_MEDIUM_CONTACT","CAM_MEDIUM_CONTACT"),(193,288,"SHOT_CLOSE_REFLECTION","CAM_CLOSE_MOTION_TERMINAL"))
EXPECTED_OIIO="3.1.13.1"
EXPECTED_NUMPY="2.3.4"

def args():
    tail=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []; p=argparse.ArgumentParser(); p.add_argument("--repository-root",type=Path,required=True); p.add_argument("--formal-root",type=Path,required=True); p.add_argument("--report",type=Path,required=True); return p.parse_args(tail)
def req(x,m):
    if not x: raise RuntimeError(m)
def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for c in iter(lambda:f.read(1048576),b""):h.update(c)
    return h.hexdigest()
def norm(v):
    if isinstance(v,float) and math.isfinite(v) and v.is_integer():return int(v)
    if isinstance(v,float) and math.isfinite(v):return {"$f64be":struct.pack(">d",v).hex()}
    if isinstance(v,list):return [norm(x) for x in v]
    if isinstance(v,dict):return {k:norm(x) for k,x in v.items()}
    return v
def canon(v):return json.dumps(norm(v),ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def write(path,body):
    req(not path.exists(),f"report exists {path}"); body={**body,"reportHash":hashlib.sha256(canon(body)).hexdigest()}; path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("x",encoding="utf-8") as f:json.dump(body,f,ensure_ascii=False,indent=2,sort_keys=True,allow_nan=False);f.write("\n");f.flush();os.fsync(f.fileno())
    return body
def png(path):
    b=path.read_bytes()[:24];req(b[:8]==b"\x89PNG\r\n\x1a\n",f"invalid PNG {path}");return int.from_bytes(b[16:20],"big"),int.from_bytes(b[20:24],"big")
def expected_route(frame):
    return next((marker,camera) for start,end,marker,camera in CAMERAS if start<=frame<=end)
def decode_combined(path):
    req(oiio.VERSION_STRING==EXPECTED_OIIO and numpy.__version__==EXPECTED_NUMPY,"decoder runtime")
    image=oiio.ImageInput.open(str(path));req(image is not None,"OpenImageIO open")
    try:
        candidates=[];subimage=0
        while image.seek_subimage(subimage,0):
            spec=image.spec();names=list(spec.channelnames);positions={name:index for index,name in enumerate(names)}
            for name in names:
                if not name.endswith(".R"):continue
                prefix=name[:-2];wanted=[f"{prefix}.{channel}" for channel in "RGBA"]
                if prefix.split(".")[-1]=="Combined" and all(channel in positions for channel in wanted):candidates.append((subimage,spec.width,spec.height,spec.nchannels,prefix,wanted,[positions[channel] for channel in wanted]))
            subimage+=1
        req(len(candidates)==1,f"Combined RGBA count {len(candidates)}")
        subimage,width,height,channels,prefix,names,indices=candidates[0];pixels=image.read_image(subimage,0,0,channels,oiio.FLOAT);array=numpy.asarray(pixels);req(tuple(array.shape)==(height,width,channels),f"decoded shape {array.shape}");rgba=numpy.ascontiguousarray(array[...,indices],dtype=numpy.dtype("<f4"));req(numpy.isfinite(rgba).all(),"non-finite Combined")
        return rgba,{"subimage":subimage,"prefix":prefix,"channelNames":names,"channelIndices":indices,"decodedCombinedSha256":hashlib.sha256(rgba.tobytes(order="C")).hexdigest()}
    finally:image.close()
def main():
    a=args(); repo=a.repository_root.resolve(strict=True); root=a.formal_root.resolve(); report=a.report.resolve(); loaded=Path(bpy.data.filepath).resolve(strict=True)
    req(root.is_dir() and report==root/"reports/render-report.json","output contract")
    req(bpy.app.version_string=="5.2.0 LTS" and bpy.app.build_hash.decode()=="fbe6228777e7","runtime")
    req(sha(loaded)==SCENE_SHA,"scene identity"); req(os.environ.get("OCIO","").endswith("color/ocio/cg-config-v4.0.0_aces-v2.0_ocio-v2.5.ocio"),"OCIO")
    master=bpy.context.scene; req(master.frame_start==1 and master.frame_end==288 and master.render.fps==24,"timeline")
    markers=sorted((m.name,int(m.frame),m.camera.name if m.camera else None) for m in master.timeline_markers)
    req(markers==[("SHOT_CLOSE_REFLECTION",193,"CAM_CLOSE_MOTION_TERMINAL"),("SHOT_MEDIUM_CONTACT",97,"CAM_MEDIUM_CONTACT"),("SHOT_WIDE_APPROACH",1,"CAM_WIDE_APPROACH")],"markers")
    out=root/"frames";out.mkdir(parents=True,exist_ok=False)
    scene=master;req(scene.name=="B62_PHASE0_MASTER","production scene name")
    if bpy.context.window is not None:bpy.context.window.scene=scene
    req(bpy.context.scene==scene,"production scene is not active context")
    scene.display_settings.display_device="sRGB - Display";scene.view_settings.view_transform="ACES 2.0 - SDR 100 nits (Rec.709)";scene.view_settings.look="None";scene.view_settings.exposure=0;scene.view_settings.gamma=1
    scene.camera=bpy.data.objects["CAM_WIDE_APPROACH"]
    production_file_format=scene.render.image_settings.file_format;production_media_type=scene.render.image_settings.media_type;req(production_file_format=="OPEN_EXR_MULTILAYER" and production_media_type=="MULTI_LAYER_IMAGE","production file format")
    scene.render.engine="BLENDER_EEVEE";scene.render.resolution_x=640;scene.render.resolution_y=360;scene.render.resolution_percentage=100;scene.render.film_transparent=False;scene.render.use_motion_blur=True
    req(hasattr(scene,"eevee"),"Eevee settings");scene.eevee.taa_samples=16;scene.eevee.taa_render_samples=16
    req(scene.render.engine=="BLENDER_EEVEE" and scene.eevee.taa_samples==16 and scene.eevee.taa_render_samples==16,"Eevee contract")
    output_scene=bpy.data.scenes.new("B62_TERMINAL_PNG_OUTPUT");output_scene.display_settings.display_device="sRGB - Display";output_scene.view_settings.view_transform="ACES 2.0 - SDR 100 nits (Rec.709)";output_scene.view_settings.look="None";output_scene.view_settings.exposure=0;output_scene.view_settings.gamma=1;output_scene.render.image_settings.file_format="PNG";output_scene.render.image_settings.color_mode="RGBA";output_scene.render.image_settings.color_depth="8";req(output_scene.render.image_settings.file_format=="PNG","PNG adapter")
    scratch=root/"scratch";scratch.mkdir(exist_ok=False);scratch_exr=scratch/"current-frame.exr"
    rows=[];started=time.perf_counter()
    for frame in range(1,289):
        scene.frame_set(frame);bpy.context.view_layer.update();expected_marker,expected_camera=expected_route(frame);active=max((m for m in scene.timeline_markers if m.frame<=frame),key=lambda m:(m.frame,m.name));req(active.name==expected_marker and active.camera and active.camera.name==expected_camera,f"marker route {frame}");scene.camera=active.camera;req(bpy.context.scene==scene and scene.frame_current==frame and scene.camera.name==expected_camera,f"active render context {frame}");applied_marker=active.name;applied_camera=scene.camera.name;context_scene=bpy.context.scene.name;context_frame=int(bpy.context.scene.frame_current)
        path=out/f"frame-{frame:04d}.png";req(not path.exists() and not scratch_exr.exists(),"frame or scratch exists");scene.render.filepath=str(scratch_exr);t=time.perf_counter();result=bpy.ops.render.render(write_still=True);elapsed=time.perf_counter()-t;req("FINISHED" in result and scratch_exr.is_file() and scratch_exr.stat().st_size>0,f"render result {frame}");scratch_bytes=scratch_exr.stat().st_size;scratch_sha=sha(scratch_exr);rgba,decoded=decode_combined(scratch_exr);req(tuple(rgba.shape)==(360,640,4),f"Combined dimensions {frame}")
        image=bpy.data.images.new(f"B62_TERMINAL_REVIEW_{frame:04d}",width=640,height=360,alpha=True,float_buffer=True)
        try:
            image.colorspace_settings.name="ACEScg";blender_rows=numpy.ascontiguousarray(numpy.flipud(rgba),dtype=numpy.float32);image.pixels.foreach_set(blender_rows.reshape(-1));image.update();req(image.has_data and list(image.size)==[640,360] and len(image.pixels)==640*360*4,f"generated image {frame}");image.save_render(filepath=str(path),scene=output_scene)
        finally:bpy.data.images.remove(image)
        scratch_exr.unlink();req(not scratch_exr.exists(),f"scratch retained {frame}")
        req(png(path)==(640,360),f"dimensions {frame}");camera_after=scene.camera.name if scene.camera else None
        rows.append({"frame":frame,"contextScene":context_scene,"contextFrame":context_frame,"marker":applied_marker,"camera":applied_camera,"sceneCameraAfterRender":camera_after,"seconds":elapsed,"scratchExr":{"bytes":scratch_bytes,"sha256":scratch_sha},"decodedCombined":decoded,"png":{"uri":path.relative_to(repo).as_posix(),"sha256":sha(path),"bytes":path.stat().st_size}})
    scratch.rmdir();source_after=sha(loaded);req(source_after==SCENE_SHA,"source changed");adapter={"name":output_scene.name,"storageAdapter":"PRODUCTION_MULTILAYER_EXR_OIIO_GENERATED_FLOAT_IMAGE_ISOLATED_PNG","productionFileFormat":production_file_format,"productionMediaType":production_media_type,"format":output_scene.render.image_settings.file_format,"colorMode":output_scene.render.image_settings.color_mode,"colorDepth":output_scene.render.image_settings.color_depth,"oiioVersion":oiio.VERSION_STRING,"numpyVersion":numpy.__version__,"sourceColorSpace":"ACEScg","rowOrderConversion":"OIIO_Y0_TOP_TO_BLENDER_PIXEL0_BOTTOM"};bpy.data.scenes.remove(output_scene)
    doc=write(report,{"schemaVersion":"bfs.b62TerminalAnimaticRenderReport.v0.1","experimentId":"B62-T2-E1","status":"PASS","source":{"uri":loaded.relative_to(repo).as_posix(),"sha256":SCENE_SHA,"sha256AfterRender":source_after,"unchanged":source_after==SCENE_SHA},"settings":{"engine":scene.render.engine,"engineFamily":"BLENDER_EEVEE_NEXT","resolution":[640,360],"samples":int(scene.eevee.taa_render_samples),"format":"PNG","colorMode":"RGBA","colorDepth":"8","motionBlur":True,"storage":adapter,"color":{"display":scene.display_settings.display_device,"view":scene.view_settings.view_transform,"look":scene.view_settings.look,"exposure":float(scene.view_settings.exposure),"gamma":float(scene.view_settings.gamma)}},"frames":rows,"elapsedSeconds":time.perf_counter()-started,"operations":{"blenderStarts":1,"sceneSaves":0,"renderCalls":288,"eeveeRenderCalls":288,"cyclesRenderCalls":0,"temporaryExrWrites":288,"oiioDecodes":288,"generatedFloatImages":288,"outputAdapterRenderCalls":0,"temporaryExrFilesRetained":0,"modelCalls":0,"networkCalls":0,"dockerProcesses":0}})
    print(f"BFS_B62_T2_RENDER PASS {len(rows)} {doc['reportHash']}")
if __name__=="__main__":
    try:main()
    except Exception as e:print(f"BFS_B62_T2_RENDER_ERROR {type(e).__name__}: {e}",file=sys.stderr);raise SystemExit(1) from e
