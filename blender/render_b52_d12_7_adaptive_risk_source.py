#!/usr/bin/env python3
"""Render one preregistered B52-D12.7 fresh static source cell."""

from __future__ import annotations

import argparse, hashlib, json, math, os, sys, time
from pathlib import Path
import bpy

SPEC_SHA256="c51d0d83afd30b479bf3e7109c31110133649ee3d65a04d677dbe236b8075ed0"
def sha_file(path:Path)->str:
    d=hashlib.sha256()
    with path.open("rb") as h:
        for chunk in iter(lambda:h.read(1024*1024),b""):d.update(chunk)
    return d.hexdigest()
def canon(value:object)->str:return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def args()->argparse.Namespace:
    raw=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [];p=argparse.ArgumentParser();p.add_argument("--spec",type=Path,required=True);p.add_argument("--fixture",required=True);p.add_argument("--frame",type=int,choices=(0,1),required=True);p.add_argument("--repeat",type=int,choices=(1,2),required=True);p.add_argument("--output-exr",type=Path);p.add_argument("--report",type=Path,required=True);p.add_argument("--probe-only",action="store_true");return p.parse_args(raw)
def math_node(nodes,operation:str,name:str,constant:float|None=None):
    node=nodes.new("ShaderNodeMath");node.name=name;node.operation=operation
    if constant is not None:node.inputs[1].default_value=constant
    return node
def material(owner:dict)->bpy.types.Material:
    p=owner["material"];result=bpy.data.materials.new(f"BFS_D127_{owner['id']}_EMISSION");result.use_nodes=True;nodes,links=result.node_tree.nodes,result.node_tree.links;nodes.clear();output=nodes.new("ShaderNodeOutputMaterial");output.name="BFS_D127_OUTPUT";emission=nodes.new("ShaderNodeEmission");emission.name="BFS_D127_EMISSION";emission.inputs["Strength"].default_value=1.0;tex=nodes.new("ShaderNodeTexCoord");tex.name="BFS_D127_GENERATED";separate=nodes.new("ShaderNodeSeparateXYZ");separate.name="BFS_D127_SEPARATE";combine=nodes.new("ShaderNodeCombineColor");combine.name="BFS_D127_RGB";links.new(tex.outputs["Generated"],separate.inputs["Vector"]);coords=(separate.outputs["X"],separate.outputs["Y"],separate.outputs["Z"]);dot=[]
    for axis,source in enumerate(coords):
        term=math_node(nodes,"MULTIPLY",f"BFS_D127_WAVE_DOT_{axis}",float(p["waveFrequency"][axis]));links.new(source,term.inputs[0]);dot.append(term.outputs[0])
    xy=math_node(nodes,"ADD","BFS_D127_WAVE_XY");links.new(dot[0],xy.inputs[0]);links.new(dot[1],xy.inputs[1]);xyz=math_node(nodes,"ADD","BFS_D127_WAVE_XYZ");links.new(xy.outputs[0],xyz.inputs[0]);links.new(dot[2],xyz.inputs[1]);phase=math_node(nodes,"ADD","BFS_D127_WAVE_PHASE",float(p["wavePhase"]));links.new(xyz.outputs[0],phase.inputs[0]);sine=math_node(nodes,"SINE","BFS_D127_WAVE_SINE");links.new(phase.outputs[0],sine.inputs[0])
    for channel,socket in enumerate(("Red","Green","Blue")):
        terms=[]
        for axis,source in enumerate(coords):
            term=math_node(nodes,"MULTIPLY",f"BFS_D127_C{channel}_AXIS_{axis}",float(p[("coeffX","coeffY","coeffZ")[axis]][channel]));links.new(source,term.inputs[0]);terms.append(term.outputs[0])
        add_xy=math_node(nodes,"ADD",f"BFS_D127_C{channel}_XY");links.new(terms[0],add_xy.inputs[0]);links.new(terms[1],add_xy.inputs[1]);add_xyz=math_node(nodes,"ADD",f"BFS_D127_C{channel}_XYZ");links.new(add_xy.outputs[0],add_xyz.inputs[0]);links.new(terms[2],add_xyz.inputs[1]);wave=math_node(nodes,"MULTIPLY",f"BFS_D127_C{channel}_WAVE",float(p["waveAmplitude"][channel]));links.new(sine.outputs[0],wave.inputs[0]);add_wave=math_node(nodes,"ADD",f"BFS_D127_C{channel}_ADD_WAVE");links.new(add_xyz.outputs[0],add_wave.inputs[0]);links.new(wave.outputs[0],add_wave.inputs[1]);add_base=math_node(nodes,"ADD",f"BFS_D127_C{channel}_ADD_BASE",float(p["baseRGB"][channel]));links.new(add_wave.outputs[0],add_base.inputs[0]);clamp=nodes.new("ShaderNodeClamp");clamp.name=f"BFS_D127_C{channel}_CLAMP";clamp.inputs["Min"].default_value=.08;clamp.inputs["Max"].default_value=.92;links.new(add_base.outputs[0],clamp.inputs["Value"]);links.new(clamp.outputs["Result"],combine.inputs[socket])
    links.new(combine.outputs["Color"],emission.inputs["Color"]);links.new(emission.outputs["Emission"],output.inputs["Surface"]);return result
def mesh_object(owner:dict,vertices:list[tuple],faces:list[tuple])->bpy.types.Object:
    mesh=bpy.data.meshes.new(f"BFS_D127_{owner['id']}_MESH");mesh.from_pydata(vertices,[],faces);mesh.update();return bpy.data.objects.new(f"BFS_D127_{owner['id']}",mesh)
def dual_ripple(owner:dict)->bpy.types.Object:
    g=owner["geometry"];width,height=g["size"];columns,rows=g["subdivisions"];a,fx,fy=g["waveA"];b,gx,gy=g["waveB"];vertices=[]
    for y in range(rows+1):
        py=-height/2+y*height/rows
        for x in range(columns+1):
            px=-width/2+x*width/columns;vertices.append((px,py,a*math.sin(px*fx+py*fy)+b*math.cos(px*gx+py*gy)))
    faces=[]
    for y in range(rows):
        for x in range(columns):
            i=y*(columns+1)+x;faces.append((i,i+1,i+columns+2,i+columns+1))
    return mesh_object(owner,vertices,faces)
def superellipse(owner:dict)->bpy.types.Object:
    g=owner["geometry"];width,height,depth=g["dimensions"];segments=g["segments"];exponent=g["exponent"];ring=[]
    for i in range(segments):
        angle=2*math.pi*i/segments;c,s=math.cos(angle),math.sin(angle);ring.append((width*.5*math.copysign(abs(c)**(2/exponent),c),height*.5*math.copysign(abs(s)**(2/exponent),s)))
    vertices=[(x,y,-depth/2) for x,y in ring]+[(x,y,depth/2) for x,y in ring];faces=[tuple(reversed(range(segments))),tuple(range(segments,2*segments))]
    for i in range(segments):
        j=(i+1)%segments;faces.append((i,j,j+segments,i+segments))
    return mesh_object(owner,vertices,faces)
def freeze(obj:bpy.types.Object)->None:
    action=obj.animation_data.action if obj.animation_data else None
    if action is None:raise RuntimeError(f"missing action: {obj.name}")
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for point in curve.keyframe_points:point.interpolation="LINEAR"
def add_owner(owner:dict)->bpy.types.Object:
    g=owner["geometry"];kind=g["type"]
    if kind=="DUAL_RIPPLE_GRID":obj=dual_ripple(owner);bpy.context.scene.collection.objects.link(obj)
    elif kind=="SUPERELLIPSE_PRISM":obj=superellipse(owner);bpy.context.scene.collection.objects.link(obj)
    elif kind=="ROUNDED_BOX":bpy.ops.mesh.primitive_cube_add();obj=bpy.context.object;obj.dimensions=tuple(g["dimensions"]);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    elif kind=="TORUS":bpy.ops.mesh.primitive_torus_add(major_segments=g["majorSegments"],minor_segments=g["minorSegments"],major_radius=g["majorRadius"],minor_radius=g["minorRadius"]);obj=bpy.context.object
    elif kind=="UV_SPHERE":bpy.ops.mesh.primitive_uv_sphere_add(segments=g["segments"],ring_count=g["rings"],radius=g["radius"]);obj=bpy.context.object
    elif kind=="CONE_FRUSTUM":bpy.ops.mesh.primitive_cone_add(vertices=g["vertices"],radius1=g["radiusBottom"],radius2=g["radiusTop"],depth=g["depth"]);obj=bpy.context.object
    elif kind=="CYLINDER":bpy.ops.mesh.primitive_cylinder_add(vertices=g["vertices"],radius=g["radius"],depth=g["depth"]);obj=bpy.context.object
    else:raise RuntimeError(f"unknown D12.7 geometry: {kind}")
    obj.name=f"BFS_D127_{owner['id']}";obj.data.name=f"BFS_D127_{owner['id']}_MESH";obj.rotation_mode="XYZ";obj.pass_index=owner["passIndex"]
    if "bevelWidth" in g:
        mod=obj.modifiers.new("BFS_D127_BEVEL","BEVEL");mod.width=g["bevelWidth"];mod.segments=g["bevelSegments"]
    obj.data.materials.append(material(owner));t=owner["transform"]
    for frame in (0,1,2):
        obj.location=tuple(t["location"]);obj.rotation_euler=tuple(t["rotationEuler"]);obj.scale=tuple(t["scale"]);obj.keyframe_insert(data_path="location",frame=frame);obj.keyframe_insert(data_path="rotation_euler",frame=frame);obj.keyframe_insert(data_path="scale",frame=frame)
    freeze(obj);return obj
def action_rows(obj:bpy.types.Object)->list[dict]:
    action=obj.animation_data.action if obj.animation_data else None;rows=[]
    if action:
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for curve in bag.fcurves:rows.append({"dataPath":curve.data_path,"arrayIndex":curve.array_index,"keys":[[float(p.co.x),float(p.co.y),p.interpolation] for p in curve.keyframe_points]})
    return sorted(rows,key=lambda row:(row["dataPath"],row["arrayIndex"]))
def setup(spec:dict,fixture:dict,frame:int,repeat:int):
    bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.name=f"BFS_D127_{fixture['id']}_F{frame}_R{repeat}";r=spec["sceneContract"]["render"];scene.render.engine=r["engine"];scene.cycles.device=r["device"];scene.cycles.samples=r["samples"];scene.cycles.seed=r["seed"];scene.cycles.use_animated_seed=r["animatedSeed"];scene.cycles.use_adaptive_sampling=r["adaptiveSampling"];scene.cycles.use_denoising=r["denoising"];scene.render.resolution_x,scene.render.resolution_y=fixture["resolution"];scene.render.resolution_percentage=100;scene.render.pixel_aspect_x,scene.render.pixel_aspect_y=r["pixelAspect"];scene.render.film_transparent=r["filmTransparent"];scene.render.use_motion_blur=r["motionBlur"];scene.render.use_persistent_data=r["persistentData"];scene.render.use_compositing=False;scene.render.use_sequencer=False;scene.render.use_stamp=False;scene.render.threads_mode=r["threadsMode"];scene.render.threads=r["threads"];scene.frame_start,scene.frame_end=0,2;world=bpy.data.worlds.new("BFS_D127_WORLD");world.use_nodes=True;world.node_tree.nodes["Background"].inputs["Color"].default_value=(0,0,0,1);world.node_tree.nodes["Background"].inputs["Strength"].default_value=0;scene.world=world;data=bpy.data.cameras.new("BFS_D127_CAMERA_DATA");data.type="PERSP";data.lens=fixture["lensMm"];data.sensor_width=fixture["sensorWidthMm"];data.sensor_fit="HORIZONTAL";data.clip_start=.1;data.clip_end=100;data.dof.use_dof=False;camera=bpy.data.objects.new("BFS_D127_CAMERA",data);camera.rotation_mode="XYZ";scene.collection.objects.link(camera);scene.camera=camera
    for f in (0,1,2):
        camera.location=tuple(fixture["cameraTransform"]["location"]);camera.rotation_euler=tuple(fixture["cameraTransform"]["rotationEuler"]);camera.keyframe_insert(data_path="location",frame=f);camera.keyframe_insert(data_path="rotation_euler",frame=f)
    freeze(camera);owners=[add_owner(owner) for owner in fixture["owners"]];scene.frame_set(frame);bpy.context.view_layer.update();layer=bpy.context.view_layer;layer.name=r["viewLayer"];layer.use_pass_combined=True;layer.use_pass_z=True;layer.use_pass_vector=True;layer.use_pass_object_index=True;layer.pass_alpha_threshold=r["passAlphaThreshold"];scene.render.image_settings.media_type="MULTI_LAYER_IMAGE";scene.render.image_settings.file_format=r["fileFormat"];scene.render.image_settings.color_mode=r["colorMode"];scene.render.image_settings.color_depth=r["colorDepth"];scene.render.image_settings.exr_codec=r["exrCodec"];return scene,camera,owners
def structure(obj:bpy.types.Object)->dict:return {"name":obj.name,"passIndex":int(obj.pass_index),"vertices":len(obj.data.vertices),"polygons":len(obj.data.polygons),"location":[float(v) for v in obj.location],"rotationEuler":[float(v) for v in obj.rotation_euler],"scale":[float(v) for v in obj.scale],"modifiers":[{"name":m.name,"type":m.type} for m in obj.modifiers],"material":obj.data.materials[0].name,"materialNodes":sorted(n.name for n in obj.data.materials[0].node_tree.nodes)}
def main()->None:
    a=args();spec=json.loads(a.spec.read_text())
    if sha_file(a.spec)!=SPEC_SHA256:raise RuntimeError("D12.7 spec identity mismatch")
    fixture=next((row for row in spec["fixtures"] if row["id"]==a.fixture),None)
    if fixture is None or a.report.exists() or (a.output_exr and a.output_exr.exists()):raise RuntimeError("D12.7 fixture/output invalid")
    if not a.probe_only and a.output_exr is None:raise RuntimeError("output EXR required")
    if sha_file(Path(bpy.app.binary_path))!=spec["runtime"]["blender"]["sha256"] or bpy.app.version_string!=spec["runtime"]["blender"]["version"] or bpy.app.build_hash.decode()!=spec["runtime"]["blender"]["buildHash"]:raise RuntimeError("Blender identity mismatch")
    if sha_file(Path(os.environ["OCIO"]))!=spec["runtime"]["ocio"]["sha256"]:raise RuntimeError("OCIO identity mismatch")
    started=time.monotonic();scene,camera,owners=setup(spec,fixture,a.frame,a.repeat);body={"schemaVersion":"bfs.blenderStaticAdaptiveRiskSourceReport.v0.1","experimentId":spec["experimentId"],"fixtureId":fixture["id"],"frame":a.frame,"repeat":a.repeat,"pid":os.getpid(),"probeOnly":a.probe_only,"fixture":fixture,"runtime":{"blender":bpy.app.version_string,"buildHash":bpy.app.build_hash.decode(),"executableSha256":sha_file(Path(bpy.app.binary_path)),"engine":scene.render.engine,"device":scene.cycles.device,"samples":scene.cycles.samples,"seed":scene.cycles.seed},"sceneStructure":{"camera":{"lensMm":camera.data.lens,"sensorWidthMm":camera.data.sensor_width},"owners":[structure(o) for o in owners]},"animation":{"camera":action_rows(camera),"owners":{o.name:action_rows(o) for o in owners}},"passState":{"viewLayer":bpy.context.view_layer.name,"Combined":bpy.context.view_layer.use_pass_combined,"Depth":bpy.context.view_layer.use_pass_z,"Vector":bpy.context.view_layer.use_pass_vector,"Object Index":bpy.context.view_layer.use_pass_object_index}}
    render_seconds=0.0
    if not a.probe_only:
        a.output_exr.parent.mkdir(parents=True,exist_ok=False);tick=time.monotonic();outcome=bpy.ops.render.render(write_still=False)
        if "FINISHED" not in outcome:raise RuntimeError("D12.7 render failed")
        render_seconds=time.monotonic()-tick;bpy.data.images["Render Result"].save_render(str(a.output_exr),scene=scene);body["output"]={"uri":str(a.output_exr),"sha256":sha_file(a.output_exr),"bytes":a.output_exr.stat().st_size}
    else:body["output"]=None
    body["operationCounts"]={"blenderProcesses":1,"blenderRenderCalls":0 if a.probe_only else 1,"cyclesRayRenders":0 if a.probe_only else 1,"modelCalls":0,"networkCalls":0};body["renderSeconds"]=round(render_seconds,6);body["elapsedSeconds"]=round(time.monotonic()-started,6);report={**body,"reportHash":canon(body)};a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+"\n");print(f"BFS_B52_D127_SOURCE_OK fixture={a.fixture} frame={a.frame} repeat={a.repeat} owners={len(owners)} probe={a.probe_only}")
if __name__=="__main__":main()
