#!/usr/bin/env python3
"""Render one preregistered B52-D12.5 fresh static radius-intervention source cell."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path

import bpy


SPEC_SHA256 = "b24aa05aeb1ab7a33e8fc57afc646308b5454eb0a5c5bf77dbbf8cc33f2ed5f2"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def arguments() -> argparse.Namespace:
    raw = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--frame", type=int, choices=(0, 1), required=True)
    parser.add_argument("--repeat", type=int, choices=(1, 2), required=True)
    parser.add_argument("--output-exr", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--probe-only", action="store_true")
    return parser.parse_args(raw)


def math_node(nodes, operation: str, name: str, constant: float | None = None):
    node = nodes.new("ShaderNodeMath")
    node.name = name
    node.operation = operation
    if constant is not None:
        node.inputs[1].default_value = constant
    return node


def material(owner: dict) -> bpy.types.Material:
    params = owner["material"]
    result = bpy.data.materials.new(f"BFS_D125_{owner['id']}_EMISSION")
    result.use_nodes = True
    nodes, links = result.node_tree.nodes, result.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial"); output.name = "BFS_D125_OUTPUT"
    emission = nodes.new("ShaderNodeEmission"); emission.name = "BFS_D125_EMISSION"; emission.inputs["Strength"].default_value = 1.0
    texcoord = nodes.new("ShaderNodeTexCoord"); texcoord.name = "BFS_D125_GENERATED"
    separate = nodes.new("ShaderNodeSeparateXYZ"); separate.name = "BFS_D125_SEPARATE"
    combine = nodes.new("ShaderNodeCombineColor"); combine.name = "BFS_D125_RGB"
    links.new(texcoord.outputs["Generated"], separate.inputs["Vector"])
    coords = (separate.outputs["X"], separate.outputs["Y"], separate.outputs["Z"])
    dot_terms = []
    for axis, source in enumerate(coords):
        term = math_node(nodes, "MULTIPLY", f"BFS_D125_WAVE_DOT_{axis}", float(params["waveFrequency"][axis]))
        links.new(source, term.inputs[0]); dot_terms.append(term.outputs[0])
    dot_xy = math_node(nodes, "ADD", "BFS_D125_WAVE_XY"); links.new(dot_terms[0], dot_xy.inputs[0]); links.new(dot_terms[1], dot_xy.inputs[1])
    dot_xyz = math_node(nodes, "ADD", "BFS_D125_WAVE_XYZ"); links.new(dot_xy.outputs[0], dot_xyz.inputs[0]); links.new(dot_terms[2], dot_xyz.inputs[1])
    phase = math_node(nodes, "ADD", "BFS_D125_WAVE_PHASE", float(params["wavePhase"])); links.new(dot_xyz.outputs[0], phase.inputs[0])
    sine = math_node(nodes, "SINE", "BFS_D125_WAVE_SINE"); links.new(phase.outputs[0], sine.inputs[0])
    channels = []
    for channel, socket_name in enumerate(("Red", "Green", "Blue")):
        terms = []
        for axis, source in enumerate(coords):
            coefficient = float(params[("coeffX", "coeffY", "coeffZ")[axis]][channel])
            term = math_node(nodes, "MULTIPLY", f"BFS_D125_C{channel}_AXIS_{axis}", coefficient)
            links.new(source, term.inputs[0]); terms.append(term.outputs[0])
        add_xy = math_node(nodes, "ADD", f"BFS_D125_C{channel}_XY"); links.new(terms[0], add_xy.inputs[0]); links.new(terms[1], add_xy.inputs[1])
        add_xyz = math_node(nodes, "ADD", f"BFS_D125_C{channel}_XYZ"); links.new(add_xy.outputs[0], add_xyz.inputs[0]); links.new(terms[2], add_xyz.inputs[1])
        wave = math_node(nodes, "MULTIPLY", f"BFS_D125_C{channel}_WAVE", float(params["waveAmplitude"][channel])); links.new(sine.outputs[0], wave.inputs[0])
        add_wave = math_node(nodes, "ADD", f"BFS_D125_C{channel}_ADD_WAVE"); links.new(add_xyz.outputs[0], add_wave.inputs[0]); links.new(wave.outputs[0], add_wave.inputs[1])
        add_base = math_node(nodes, "ADD", f"BFS_D125_C{channel}_ADD_BASE", float(params["baseRGB"][channel])); links.new(add_wave.outputs[0], add_base.inputs[0])
        clamp = nodes.new("ShaderNodeClamp"); clamp.name = f"BFS_D125_C{channel}_CLAMP"; clamp.inputs["Min"].default_value = 0.08; clamp.inputs["Max"].default_value = 0.92
        links.new(add_base.outputs[0], clamp.inputs["Value"]); channels.append(clamp.outputs["Result"])
        links.new(channels[-1], combine.inputs[socket_name])
    links.new(combine.outputs["Color"], emission.inputs["Color"])
    links.new(emission.outputs["Emission"], output.inputs["Surface"])
    return result


def grid_mesh(owner: dict) -> bpy.types.Object:
    geometry = owner["geometry"]
    width, height = geometry["size"]
    columns, rows = geometry["subdivisions"]
    amplitude, frequency_x, frequency_y = geometry["zWave"]
    vertices = []
    for y in range(rows + 1):
        py = -height / 2 + y * height / rows
        for x in range(columns + 1):
            px = -width / 2 + x * width / columns
            vertices.append((px, py, amplitude * math.sin(px * frequency_x + py * frequency_y)))
    faces = []
    for y in range(rows):
        for x in range(columns):
            a = y * (columns + 1) + x
            faces.append((a, a + 1, a + columns + 2, a + columns + 1))
    mesh = bpy.data.meshes.new(f"BFS_D125_{owner['id']}_MESH")
    mesh.from_pydata(vertices, [], faces); mesh.update()
    return bpy.data.objects.new(f"BFS_D125_{owner['id']}", mesh)


def prism_mesh(owner: dict) -> bpy.types.Object:
    width, height, depth = owner["geometry"]["dimensions"]
    vertices = [(-width/2,-height/2,-depth/2),(width/2,-height/2,-depth/2),(0,height/2,-depth/2),(-width/2,-height/2,depth/2),(width/2,-height/2,depth/2),(0,height/2,depth/2)]
    faces = [(0,2,1),(3,4,5),(0,1,4,3),(1,2,5,4),(2,0,3,5)]
    mesh = bpy.data.meshes.new(f"BFS_D125_{owner['id']}_MESH")
    mesh.from_pydata(vertices, [], faces); mesh.update()
    return bpy.data.objects.new(f"BFS_D125_{owner['id']}", mesh)


def freeze_interpolation(obj: bpy.types.Object) -> None:
    action = obj.animation_data.action if obj.animation_data else None
    if action is None:
        raise RuntimeError(f"missing action for {obj.name}")
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for point in curve.keyframe_points:
                        point.interpolation = "LINEAR"


def add_owner(owner: dict) -> bpy.types.Object:
    geometry, kind = owner["geometry"], owner["geometry"]["type"]
    if kind == "SUBDIVIDED_GRID":
        obj = grid_mesh(owner); bpy.context.scene.collection.objects.link(obj)
    elif kind == "TRIANGULAR_PRISM":
        obj = prism_mesh(owner); bpy.context.scene.collection.objects.link(obj)
    elif kind == "UV_SPHERE":
        bpy.ops.mesh.primitive_uv_sphere_add(segments=geometry["segments"], ring_count=geometry["rings"], radius=geometry["radius"]); obj = bpy.context.object
    elif kind == "TORUS":
        bpy.ops.mesh.primitive_torus_add(major_segments=geometry["majorSegments"], minor_segments=geometry["minorSegments"], major_radius=geometry["majorRadius"], minor_radius=geometry["minorRadius"]); obj = bpy.context.object
    elif kind == "ICO_SPHERE":
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=geometry["subdivisions"], radius=geometry["radius"]); obj = bpy.context.object
    elif kind == "CYLINDER":
        bpy.ops.mesh.primitive_cylinder_add(vertices=geometry["vertices"], radius=geometry["radius"], depth=geometry["depth"]); obj = bpy.context.object
    else:
        raise RuntimeError(f"unknown D12.5 geometry: {kind}")
    obj.name = f"BFS_D125_{owner['id']}"; obj.data.name = f"BFS_D125_{owner['id']}_MESH"; obj.rotation_mode = "XYZ"; obj.pass_index = owner["passIndex"]
    if "bevelWidth" in geometry:
        modifier = obj.modifiers.new("BFS_D125_BEVEL", "BEVEL"); modifier.width = geometry["bevelWidth"]; modifier.segments = geometry["bevelSegments"]
    obj.data.materials.append(material(owner))
    transform = owner["transform"]
    for frame in (0, 1, 2):
        obj.location = tuple(transform["location"]); obj.rotation_euler = tuple(transform["rotationEuler"]); obj.scale = tuple(transform["scale"])
        obj.keyframe_insert(data_path="location", frame=frame); obj.keyframe_insert(data_path="rotation_euler", frame=frame); obj.keyframe_insert(data_path="scale", frame=frame)
    freeze_interpolation(obj)
    return obj


def key_camera(camera: bpy.types.Object, transform: dict) -> None:
    for frame in (0, 1, 2):
        camera.location = tuple(transform["location"]); camera.rotation_euler = tuple(transform["rotationEuler"])
        camera.keyframe_insert(data_path="location", frame=frame); camera.keyframe_insert(data_path="rotation_euler", frame=frame)
    freeze_interpolation(camera)


def action_rows(obj: bpy.types.Object) -> list[dict]:
    action = obj.animation_data.action if obj.animation_data else None
    rows = []
    if action:
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for curve in bag.fcurves:
                        rows.append({"dataPath": curve.data_path, "arrayIndex": curve.array_index, "keys": [[float(p.co.x), float(p.co.y), p.interpolation] for p in curve.keyframe_points]})
    return sorted(rows, key=lambda row: (row["dataPath"], row["arrayIndex"]))


def setup(spec: dict, fixture: dict, frame: int, repeat: int):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene; scene.name = f"BFS_D125_{fixture['id']}_F{frame}_R{repeat}"
    render = spec["sceneContract"]["render"]
    scene.render.engine = render["engine"]; scene.cycles.device = render["device"]; scene.cycles.samples = render["samples"]; scene.cycles.seed = render["seed"]
    scene.cycles.use_animated_seed = render["animatedSeed"]; scene.cycles.use_adaptive_sampling = render["adaptiveSampling"]; scene.cycles.use_denoising = render["denoising"]
    scene.render.resolution_x, scene.render.resolution_y = fixture["resolution"]; scene.render.resolution_percentage = 100
    scene.render.pixel_aspect_x, scene.render.pixel_aspect_y = render["pixelAspect"]; scene.render.film_transparent = render["filmTransparent"]
    scene.render.use_motion_blur = render["motionBlur"]; scene.render.use_persistent_data = render["persistentData"]; scene.render.use_compositing = False; scene.render.use_sequencer = False; scene.render.use_stamp = False
    scene.render.threads_mode = render["threadsMode"]; scene.render.threads = render["threads"]; scene.frame_start, scene.frame_end = 0, 2
    world = bpy.data.worlds.new("BFS_D125_WORLD"); world.use_nodes = True; world.node_tree.nodes["Background"].inputs["Color"].default_value = (0,0,0,1); world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0; scene.world = world
    camera_data = bpy.data.cameras.new("BFS_D125_CAMERA_DATA"); camera_data.type = "PERSP"; camera_data.lens = fixture["lensMm"]; camera_data.sensor_width = fixture["sensorWidthMm"]; camera_data.sensor_fit = "HORIZONTAL"; camera_data.clip_start = 0.1; camera_data.clip_end = 100.0; camera_data.dof.use_dof = False
    camera = bpy.data.objects.new("BFS_D125_CAMERA", camera_data); camera.rotation_mode = "XYZ"; scene.collection.objects.link(camera); scene.camera = camera; key_camera(camera, fixture["cameraTransform"])
    owners = [add_owner(owner) for owner in fixture["owners"]]
    scene.frame_set(frame); bpy.context.view_layer.update(); layer = bpy.context.view_layer; layer.name = render["viewLayer"]
    layer.use_pass_combined = True; layer.use_pass_z = True; layer.use_pass_vector = True; layer.use_pass_object_index = True; layer.pass_alpha_threshold = render["passAlphaThreshold"]
    scene.render.image_settings.media_type = "MULTI_LAYER_IMAGE"; scene.render.image_settings.file_format = render["fileFormat"]; scene.render.image_settings.color_mode = render["colorMode"]; scene.render.image_settings.color_depth = render["colorDepth"]; scene.render.image_settings.exr_codec = render["exrCodec"]
    return scene, camera, owners


def owner_structure(owner: bpy.types.Object) -> dict:
    return {"name": owner.name, "passIndex": int(owner.pass_index), "vertices": len(owner.data.vertices), "polygons": len(owner.data.polygons), "location": [float(v) for v in owner.location], "rotationEuler": [float(v) for v in owner.rotation_euler], "scale": [float(v) for v in owner.scale], "modifiers": [{"name": m.name, "type": m.type} for m in owner.modifiers], "material": owner.data.materials[0].name, "materialNodes": sorted(node.name for node in owner.data.materials[0].node_tree.nodes)}


def main() -> None:
    args = arguments(); spec = json.loads(args.spec.read_text())
    if sha256_file(args.spec) != SPEC_SHA256: raise RuntimeError("D12.5 spec identity mismatch")
    fixture = next((row for row in spec["fixtures"] if row["id"] == args.fixture), None)
    if fixture is None: raise RuntimeError("fixture outside D12.5 roster")
    if args.report.exists() or (args.output_exr and args.output_exr.exists()): raise RuntimeError("refusing to overwrite D12.5 source output")
    if not args.probe_only and args.output_exr is None: raise RuntimeError("output EXR required")
    if sha256_file(Path(bpy.app.binary_path)) != spec["runtime"]["blender"]["sha256"]: raise RuntimeError("Blender executable identity mismatch")
    if bpy.app.version_string != spec["runtime"]["blender"]["version"] or bpy.app.build_hash.decode() != spec["runtime"]["blender"]["buildHash"]: raise RuntimeError("Blender version identity mismatch")
    if sha256_file(Path(os.environ["OCIO"])) != spec["runtime"]["ocio"]["sha256"]: raise RuntimeError("OCIO identity mismatch")
    started = time.monotonic(); scene, camera, owners = setup(spec, fixture, args.frame, args.repeat)
    body = {"schemaVersion":"bfs.blenderStaticRadiusInterventionSourceReport.v0.1","experimentId":spec["experimentId"],"fixtureId":fixture["id"],"frame":args.frame,"repeat":args.repeat,"pid":os.getpid(),"probeOnly":args.probe_only,"fixture":fixture,"runtime":{"blender":bpy.app.version_string,"buildHash":bpy.app.build_hash.decode(),"executableSha256":sha256_file(Path(bpy.app.binary_path)),"engine":scene.render.engine,"device":scene.cycles.device,"samples":scene.cycles.samples,"seed":scene.cycles.seed},"sceneStructure":{"camera":{"lensMm":camera.data.lens,"sensorWidthMm":camera.data.sensor_width},"owners":[owner_structure(owner) for owner in owners]},"animation":{"camera":action_rows(camera),"owners":{owner.name:action_rows(owner) for owner in owners}},"passState":{"viewLayer":bpy.context.view_layer.name,"Combined":bpy.context.view_layer.use_pass_combined,"Depth":bpy.context.view_layer.use_pass_z,"Vector":bpy.context.view_layer.use_pass_vector,"Object Index":bpy.context.view_layer.use_pass_object_index}}
    render_seconds = 0.0
    if not args.probe_only:
        args.output_exr.parent.mkdir(parents=True, exist_ok=False); tick = time.monotonic(); outcome = bpy.ops.render.render(write_still=False)
        if "FINISHED" not in outcome: raise RuntimeError(f"D12.5 render failed: {sorted(outcome)}")
        render_seconds = time.monotonic()-tick; bpy.data.images["Render Result"].save_render(str(args.output_exr), scene=scene); body["output"]={"uri":str(args.output_exr),"sha256":sha256_file(args.output_exr),"bytes":args.output_exr.stat().st_size}
    else: body["output"] = None
    body["operationCounts"]={"blenderProcesses":1,"blenderRenderCalls":0 if args.probe_only else 1,"cyclesRayRenders":0 if args.probe_only else 1,"modelCalls":0,"networkCalls":0}; body["renderSeconds"]=round(render_seconds,6); body["elapsedSeconds"]=round(time.monotonic()-started,6)
    report={**body,"reportHash":canonical_hash(body)}; args.report.parent.mkdir(parents=True,exist_ok=True); args.report.write_text(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(f"BFS_B52_D125_SOURCE_OK fixture={fixture['id']} frame={args.frame} repeat={args.repeat} owners={len(owners)} probe={args.probe_only}",flush=True)


if __name__ == "__main__": main()
