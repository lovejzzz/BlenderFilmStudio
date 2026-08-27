#!/usr/bin/env python3
"""Render one B52-D8 external Raw EXR through the minimal Blender 5.2 compositor graph."""
from __future__ import annotations
import argparse, hashlib, json, os, sys
from pathlib import Path
import bpy
SPEC_SHA256="94a58f4e3c36b1828cb7e1bc4d5646cd577fac1afd411685235185590644a6a5"
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ch(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def main():
 av=sys.argv[sys.argv.index("--")+1:];p=argparse.ArgumentParser();p.add_argument("--spec",type=Path,required=True);p.add_argument("--fixture",required=True);p.add_argument("--producer",choices=("python","node"),required=True);p.add_argument("--repeat",type=int,choices=(1,2),required=True);p.add_argument("--input",type=Path,required=True);p.add_argument("--output",type=Path);p.add_argument("--report",type=Path,required=True);p.add_argument("--probe-only",action="store_true");a=p.parse_args(av);spec=json.loads(a.spec.read_text());f=next((x for x in spec["fixtures"] if x["id"]==a.fixture),None)
 if sha(a.spec)!=SPEC_SHA256 or f is None or sha(bpy.app.binary_path)!=spec["runtime"]["blender"]["sha256"] or sha(os.environ["OCIO"])!=spec["runtime"]["ocio"]["sha256"]:raise RuntimeError("identity mismatch")
 if (a.probe_only and a.output) or (not a.probe_only and not a.output) or a.report.exists() or (a.output and a.output.exists()):raise RuntimeError("output mismatch")
 bpy.ops.wm.read_factory_settings(use_empty=True);im=bpy.data.images.load(str(a.input),check_existing=False);im.colorspace_settings.name="Raw";scene=bpy.context.scene;w,h=f["resolution"]
 if list(im.size)!=[w,h]:raise RuntimeError("image size mismatch")
 scene.render.engine="BLENDER_WORKBENCH";scene.render.resolution_x=w;scene.render.resolution_y=h;scene.render.resolution_percentage=100;scene.render.film_transparent=True;scene.render.use_compositing=True;scene.render.use_sequencer=False;scene.render.use_stamp=False;scene.render.compositor_device="CPU";scene.render.threads_mode="FIXED";scene.render.threads=1;scene.render.image_settings.file_format="OPEN_EXR";scene.render.image_settings.color_mode="RGBA";scene.render.image_settings.color_depth="32";scene.render.image_settings.exr_codec="ZIP"
 t=bpy.data.node_groups.new("BFS_D8_TREE","CompositorNodeTree");scene.compositing_node_group=t;n=t.nodes.new("CompositorNodeImage");n.name="BFS_D8_EXTERNAL_SOURCE";n.image=im;t.interface.new_socket(name="Image",in_out="OUTPUT",socket_type="NodeSocketColor");g=t.nodes.new("NodeGroupOutput");g.name="BFS_D8_GROUP_OUTPUT";t.links.new(n.outputs["Image"],g.inputs["Image"]);links=sorted(f"{x.from_node.name}.{x.from_socket.identifier}->{x.to_node.name}.{x.to_socket.identifier}" for x in t.links);expected=spec["canonicalContract"]["blenderGraph"];gm=links==expected and len(t.nodes)==2 and not hasattr(scene,"node_tree");rna={"nodeType":n.bl_idname,"outputIdentifier":n.outputs["Image"].identifier,"colorspace":im.colorspace_settings.name,"match":n.bl_idname=="CompositorNodeImage" and n.outputs["Image"].identifier=="Image" and im.colorspace_settings.name=="Raw"}
 out=None;renders=0
 if not a.probe_only:
  cd=bpy.data.cameras.new("BFS_D8_CAMERA_DATA");cam=bpy.data.objects.new("BFS_D8_CAMERA",cd);scene.collection.objects.link(cam);scene.camera=cam;a.output.parent.mkdir(parents=True,exist_ok=True);scene.render.filepath=str(a.output);ok=bpy.ops.render.render(write_still=True);renders=1
  if "FINISHED" not in ok or not a.output.is_file():raise RuntimeError("render failed")
  out={"uri":str(a.output),"sha256":sha(a.output),"bytes":a.output.stat().st_size}
 body={"schemaVersion":"bfs.externalCanonicalWarpBlenderReport.v0.1","experimentId":spec["experimentId"],"fixtureId":a.fixture,"producer":a.producer,"repeat":a.repeat,"pid":os.getpid(),"classification":"ZERO_RENDER_FROZEN_TOOL_PREFLIGHT" if a.probe_only else "FORMAL_BLENDER_CELL","blender":{"version":bpy.app.version_string,"buildHash":bpy.app.build_hash.decode()},"input":{"uri":str(a.input),"sha256":sha(a.input),"bytes":a.input.stat().st_size},"rna":rna,"graph":{"links":links,"nodeCount":len(t.nodes),"match":gm},"output":out,"operationCounts":{"pythonProducerProcesses":0,"nodeProducerProcesses":0,"exrEncoderProcesses":0,"blenderProcesses":1,"renderCalls":renders,"cyclesRayRenders":0,"sourceBlendFilesOpened":0,"generatedExternalExrAssetsOpened":1}};a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps({**body,"reportHash":ch(body)},indent=2,sort_keys=True)+"\n");print(f"BFS_B52_D8_{'PREFLIGHT' if a.probe_only else 'CELL'}_OK fixture={a.fixture} producer={a.producer} repeat={a.repeat}")
if __name__=="__main__":main()
