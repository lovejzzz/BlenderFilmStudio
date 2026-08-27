#!/usr/bin/env python3
"""Render one B52-D7 Blender 5.2 Bilinear Displace cell."""

from __future__ import annotations
import argparse, hashlib, json, os, sys
from pathlib import Path
import bpy, numpy as np

SPEC_SHA256="f102a969cb59d92b0103c6807f20ca5436978504aafadd14a9b0353709ea0df5"
EXPECTED_INPUTS=[["Image","Image","NodeSocketColor"],["Displacement","Displacement","NodeSocketVector2D"],["Interpolation","Interpolation","NodeSocketMenu"],["Extension X","Extension X","NodeSocketMenu"],["Extension Y","Extension Y","NodeSocketMenu"]]
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def ah(a): return hashlib.sha256(np.ascontiguousarray(a,dtype="<f4").tobytes()).hexdigest()
def ch(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def arrays(f):
 w,h=f["resolution"];s=np.zeros((h,w,4),np.float32);d=np.zeros((h,w,2),np.float32)
 for y in range(h):
  for x in range(w):
   if f["sourcePattern"]=="LOW_FREQUENCY_ALPHA_RAMP": s[y,x]=((x%64)/64,(y%64)/64,((x+3*y)%64)/64,((x+2*y)%17)/16)
   else:s[y,x]=((x^y)&1,((5*x+11*y)%16)/16,((13*x+7*y)%32)/32,((3*x+5*y)%9)/8)
   i=f["id"]
   if i=="LF_63X47_CLIP_Q1":v=(1/4,3/4)
   elif i=="LF_63X47_EXTEND_MIX":v=(-3/2,1/8)
   elif i=="LF_63X47_REPEAT_FIELD":v=(3/8 if x<31 else -5/8,1/4 if y%2==0 else -3/4)
   elif i=="HF_127X73_CLIP_MIX":v=(-3/4,3/2)
   elif i=="HF_127X73_EXTEND_MIX":v=(17/8,-3/8)
   elif i=="HF_127X73_REPEAT_FIELD":v=((1/8,5/8,-7/8,3/8)[x%4],(-1/8,7/8)[y%2])
   d[y,x]=v
 return s,d
def image(name,a):
 h,w,c=a.shape;rgba=a if c==4 else np.dstack((a,np.zeros((h,w),np.float32),np.ones((h,w),np.float32)));im=bpy.data.images.new(name,width=w,height=h,alpha=True,float_buffer=True);im.colorspace_settings.name="Raw";im.pixels.foreach_set(np.ascontiguousarray(rgba[::-1]).reshape(-1));im.update();return im
def main():
 av=sys.argv[sys.argv.index("--")+1:];p=argparse.ArgumentParser();p.add_argument("--spec",type=Path,required=True);p.add_argument("--fixture",required=True);p.add_argument("--repeat",type=int,choices=(1,2),required=True);p.add_argument("--output-exr",type=Path);p.add_argument("--report",type=Path,required=True);p.add_argument("--probe-only",action="store_true");a=p.parse_args(av)
 spec=json.loads(a.spec.read_text());f=next((x for x in spec["fixtures"] if x["id"]==a.fixture),None)
 if sha(a.spec)!=SPEC_SHA256 or f is None:raise RuntimeError("spec/fixture mismatch")
 if sha(os.environ["OCIO"])!=spec["runtime"]["ocio"]["sha256"] or sha(bpy.app.binary_path)!=spec["runtime"]["blender"]["sha256"]:raise RuntimeError("runtime mismatch")
 if (a.probe_only and a.output_exr) or (not a.probe_only and not a.output_exr):raise RuntimeError("output/probe mismatch")
 for path in (a.output_exr,a.report):
  if path and path.exists():raise RuntimeError("refusing overwrite")
 bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;w,h=f["resolution"];scene.render.engine="BLENDER_WORKBENCH";scene.render.resolution_x=w;scene.render.resolution_y=h;scene.render.resolution_percentage=100;scene.render.film_transparent=True;scene.render.use_compositing=True;scene.render.use_sequencer=False;scene.render.use_stamp=False;scene.render.compositor_device="CPU";scene.render.threads_mode="FIXED";scene.render.threads=1;scene.render.image_settings.file_format="OPEN_EXR";scene.render.image_settings.color_mode="RGBA";scene.render.image_settings.color_depth="32";scene.render.image_settings.exr_codec="ZIP"
 s,d=arrays(f);t=bpy.data.node_groups.new("BFS_D7_TREE","CompositorNodeTree");scene.compositing_node_group=t;sn=t.nodes.new("CompositorNodeImage");sn.name="BFS_D7_SOURCE";sn.image=image("BFS_D7_SOURCE_IMAGE",s);dn=t.nodes.new("CompositorNodeImage");dn.name="BFS_D7_DISPLACEMENT";dn.image=image("BFS_D7_DISPLACEMENT_IMAGE",d);warp=t.nodes.new("CompositorNodeDisplace");warp.name="BFS_D7_DISPLACE";warp.inputs["Interpolation"].default_value="Bilinear";warp.inputs["Extension X"].default_value=f["extensionX"];warp.inputs["Extension Y"].default_value=f["extensionY"];t.interface.new_socket(name="Image",in_out="OUTPUT",socket_type="NodeSocketColor");go=t.nodes.new("NodeGroupOutput");go.name="BFS_D7_GROUP_OUTPUT";t.links.new(sn.outputs["Image"],warp.inputs["Image"]);t.links.new(dn.outputs["Image"],warp.inputs["Displacement"]);t.links.new(warp.outputs["Image"],go.inputs["Image"])
 rna=[[x.identifier,x.name,x.bl_idname] for x in warp.inputs];links=sorted(f"{x.from_node.name}.{x.from_socket.identifier}->{x.to_node.name}.{x.to_socket.identifier}" for x in t.links);expected=sorted(["BFS_D7_SOURCE.Image->BFS_D7_DISPLACE.Image","BFS_D7_DISPLACEMENT.Image->BFS_D7_DISPLACE.Displacement","BFS_D7_DISPLACE.Image->BFS_D7_GROUP_OUTPUT.Socket_0"]);rm=rna==EXPECTED_INPUTS and not hasattr(scene,"node_tree");gm=len(t.nodes)==4 and links==expected
 if not rm or not gm:raise RuntimeError("RNA/graph mismatch")
 out=None;renders=0
 if not a.probe_only:
  cd=bpy.data.cameras.new("BFS_D7_CAMERA_DATA");cam=bpy.data.objects.new("BFS_D7_CAMERA",cd);scene.collection.objects.link(cam);scene.camera=cam;a.output_exr.parent.mkdir(parents=True,exist_ok=False);scene.render.filepath=str(a.output_exr);ok=bpy.ops.render.render(write_still=True);renders=1
  if "FINISHED" not in ok or not a.output_exr.is_file():raise RuntimeError("render failed")
  out={"uri":str(a.output_exr),"sha256":sha(a.output_exr),"bytes":a.output_exr.stat().st_size}
 body={"schemaVersion":"bfs.subpixelBilinearBlenderCellReport.v0.1","experimentId":spec["experimentId"],"classification":"ZERO_RENDER_FROZEN_TOOL_PREFLIGHT" if a.probe_only else "FORMAL_BLENDER_CELL","fixtureId":a.fixture,"repeat":a.repeat,"pid":os.getpid(),"blender":{"version":bpy.app.version_string,"buildHash":bpy.app.build_hash.decode()},"arrays":{"sourceFloat32Sha256":ah(s),"displacementFloat32Sha256":ah(d)},"rna":{"match":rm,"inputs":rna},"graph":{"match":gm,"links":links,"nodeCount":len(t.nodes)},"sampling":{"interpolation":"Bilinear","extensionX":f["extensionX"],"extensionY":f["extensionY"]},"output":out,"operationCounts":{"pythonReferenceProcesses":0,"nodeReferenceProcesses":0,"blenderProcesses":1,"renderCalls":renders,"cyclesRayRenders":0,"sourceBlendFilesOpened":0,"externalAssetsOpened":0}}
 rep={**body,"reportHash":ch(body)};a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(rep,indent=2,sort_keys=True,allow_nan=False)+"\n");print(f"BFS_B52_D7_{'PREFLIGHT' if a.probe_only else 'CELL'}_OK fixture={a.fixture} repeat={a.repeat}")
if __name__=="__main__":main()
