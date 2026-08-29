"""Render the preregistered B62 terminal 288-frame Eevee animatic."""
from __future__ import annotations
import argparse, hashlib, json, math, os, struct, sys, time
from pathlib import Path
import bpy

SCENE_SHA="0acd4d135c9bac9a7928a9a38da1a0e2f4838fd052a87a9663cef83cb2c373dc"
CAMERAS=((1,96,"SHOT_WIDE_APPROACH","CAM_WIDE_APPROACH"),(97,192,"SHOT_MEDIUM_CONTACT","CAM_MEDIUM_CONTACT"),(193,288,"SHOT_CLOSE_REFLECTION","CAM_CLOSE_MOTION_TERMINAL"))

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
def main():
    a=args(); repo=a.repository_root.resolve(strict=True); root=a.formal_root.resolve(); report=a.report.resolve(); loaded=Path(bpy.data.filepath).resolve(strict=True)
    req(root.is_dir() and report==root/"reports/render-report.json","output contract")
    req(bpy.app.version_string=="5.2.0 LTS" and bpy.app.build_hash.decode()=="fbe6228777e7","runtime")
    req(sha(loaded)==SCENE_SHA,"scene identity"); req(os.environ.get("OCIO","").endswith("color/ocio/cg-config-v4.0.0_aces-v2.0_ocio-v2.5.ocio"),"OCIO")
    master=bpy.context.scene; req(master.frame_start==1 and master.frame_end==288 and master.render.fps==24,"timeline")
    markers=sorted((m.name,int(m.frame),m.camera.name if m.camera else None) for m in master.timeline_markers)
    req(markers==[("SHOT_CLOSE_REFLECTION",193,"CAM_CLOSE_MOTION_TERMINAL"),("SHOT_MEDIUM_CONTACT",97,"CAM_MEDIUM_CONTACT"),("SHOT_WIDE_APPROACH",1,"CAM_WIDE_APPROACH")],"markers")
    out=root/"frames";out.mkdir(parents=True,exist_ok=False)
    scene=bpy.data.scenes.new("B62_TERMINAL_ANIMATIC_RENDER")
    content=bpy.data.collections.get("B62_PHASE0_CONTENT");req(content is not None,"content")
    scene.collection.children.link(content);scene.world=master.world;scene.frame_start=1;scene.frame_end=288;scene.render.fps=24;scene.render.fps_base=master.render.fps_base
    scene.display_settings.display_device="sRGB - Display";scene.view_settings.view_transform="ACES 2.0 - SDR 100 nits (Rec.709)";scene.view_settings.look="None";scene.view_settings.exposure=0;scene.view_settings.gamma=1
    for marker in master.timeline_markers:
        clone=scene.timeline_markers.new(marker.name,frame=marker.frame);clone.camera=marker.camera
    scene.camera=bpy.data.objects["CAM_WIDE_APPROACH"]
    scene.render.engine="BLENDER_EEVEE";scene.render.resolution_x=640;scene.render.resolution_y=360;scene.render.resolution_percentage=100;scene.render.image_settings.file_format="PNG";scene.render.image_settings.color_mode="RGBA";scene.render.image_settings.color_depth="8";scene.render.film_transparent=False;scene.render.use_motion_blur=True
    req(hasattr(scene,"eevee"),"Eevee settings");scene.eevee.taa_samples=16;scene.eevee.taa_render_samples=16
    req(scene.render.engine=="BLENDER_EEVEE" and scene.eevee.taa_samples==16 and scene.eevee.taa_render_samples==16,"Eevee contract")
    rows=[];started=time.perf_counter()
    for frame in range(1,289):
        scene.frame_set(frame);expected_marker,expected_camera=expected_route(frame);active=max((m for m in scene.timeline_markers if m.frame<=frame),key=lambda m:(m.frame,m.name));req(active.name==expected_marker and active.camera and active.camera.name==expected_camera,f"marker route {frame}");scene.camera=active.camera;req(scene.camera.name==expected_camera,f"camera application {frame}")
        path=out/f"frame-{frame:04d}.png";req(not path.exists(),"frame exists");scene.render.filepath=str(path);t=time.perf_counter();bpy.ops.render.render(scene=scene.name,write_still=True);elapsed=time.perf_counter()-t
        req(png(path)==(640,360),f"dimensions {frame}");camera=scene.camera.name if scene.camera else None;req(camera==expected_camera,f"camera {frame} {camera}")
        rows.append({"frame":frame,"marker":active.name,"camera":camera,"seconds":elapsed,"png":{"uri":path.relative_to(repo).as_posix(),"sha256":sha(path),"bytes":path.stat().st_size}})
    doc=write(report,{"schemaVersion":"bfs.b62TerminalAnimaticRenderReport.v0.1","experimentId":"B62-T2-E1","status":"PASS","source":{"uri":loaded.relative_to(repo).as_posix(),"sha256":sha(loaded)},"settings":{"engine":scene.render.engine,"engineFamily":"BLENDER_EEVEE_NEXT","resolution":[640,360],"samples":int(scene.eevee.taa_render_samples),"format":"PNG","colorMode":"RGBA","colorDepth":"8","motionBlur":True,"color":{"display":scene.display_settings.display_device,"view":scene.view_settings.view_transform,"look":scene.view_settings.look,"exposure":float(scene.view_settings.exposure),"gamma":float(scene.view_settings.gamma)}},"frames":rows,"elapsedSeconds":time.perf_counter()-started,"operations":{"blenderStarts":1,"renderCalls":288,"eeveeRenderCalls":288,"cyclesRenderCalls":0,"modelCalls":0,"networkCalls":0,"dockerProcesses":0}})
    print(f"BFS_B62_T2_RENDER PASS {len(rows)} {doc['reportHash']}")
if __name__=="__main__":
    try:main()
    except Exception as e:print(f"BFS_B62_T2_RENDER_ERROR {type(e).__name__}: {e}",file=sys.stderr);raise SystemExit(1) from e
