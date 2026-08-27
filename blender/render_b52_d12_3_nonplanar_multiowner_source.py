#!/usr/bin/env python3
"""Render one preregistered B52-D12.3 static nonplanar/multi-owner source cell."""

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


SPEC_SHA256 = "f1ffe5b4fe0912936b1e03677dd0985f11c34e6b5df4ddf70854533c4ad0b590"


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


def material(owner: dict, ordinal: int) -> bpy.types.Material:
    result = bpy.data.materials.new(f"BFS_D123_{owner['id']}_EMISSION")
    result.use_nodes = True
    nodes, links = result.node_tree.nodes, result.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    output.name = "BFS_D123_OUTPUT"
    emission = nodes.new("ShaderNodeEmission")
    emission.name = "BFS_D123_EMISSION"
    texcoord = nodes.new("ShaderNodeTexCoord")
    texcoord.name = "BFS_D123_GENERATED"
    separate = nodes.new("ShaderNodeSeparateXYZ")
    separate.name = "BFS_D123_SEPARATE"
    combine = nodes.new("ShaderNodeCombineColor")
    combine.name = "BFS_D123_RGB"
    links.new(texcoord.outputs["Generated"], separate.inputs["Vector"])
    channels = []
    for channel_index, socket_name in enumerate(("X", "Y", "Z")):
        multiply = nodes.new("ShaderNodeMath")
        multiply.name = f"BFS_D123_C{channel_index}_FREQUENCY"
        multiply.operation = "MULTIPLY"
        multiply.inputs[1].default_value = 2.0 * math.pi * (0.61 + ordinal * 0.17 + channel_index * 0.23)
        phase = nodes.new("ShaderNodeMath")
        phase.name = f"BFS_D123_C{channel_index}_PHASE"
        phase.operation = "ADD"
        phase.inputs[1].default_value = 0.29 + ordinal * 0.31 + channel_index * 0.47
        sine = nodes.new("ShaderNodeMath")
        sine.name = f"BFS_D123_C{channel_index}_SINE"
        sine.operation = "SINE"
        scale = nodes.new("ShaderNodeMath")
        scale.name = f"BFS_D123_C{channel_index}_SCALE"
        scale.operation = "MULTIPLY_ADD"
        scale.inputs[1].default_value = 0.14 + channel_index * 0.025
        scale.inputs[2].default_value = 0.42 + ordinal * 0.07
        links.new(separate.outputs[socket_name], multiply.inputs[0])
        links.new(multiply.outputs[0], phase.inputs[0])
        links.new(phase.outputs[0], sine.inputs[0])
        links.new(sine.outputs[0], scale.inputs[0])
        channels.append(scale.outputs[0])
    for socket, channel in zip(("Red", "Green", "Blue"), channels):
        links.new(channel, combine.inputs[socket])
    links.new(combine.outputs["Color"], emission.inputs["Color"])
    emission.inputs["Strength"].default_value = 1.0
    links.new(emission.outputs["Emission"], output.inputs["Surface"])
    return result


def grid_mesh(owner: dict) -> bpy.types.Object:
    geometry = owner["geometry"]
    width, height = geometry["size"]
    columns, rows = geometry["subdivisions"]
    vertices = [(-width / 2 + x * width / columns, -height / 2 + y * height / rows, 0.0) for y in range(rows + 1) for x in range(columns + 1)]
    faces = []
    for y in range(rows):
        for x in range(columns):
            a = y * (columns + 1) + x
            faces.append((a, a + 1, a + columns + 2, a + columns + 1))
    mesh = bpy.data.meshes.new(f"BFS_D123_{owner['id']}_MESH")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    return bpy.data.objects.new(f"BFS_D123_{owner['id']}", mesh)


def add_owner(owner: dict, ordinal: int) -> bpy.types.Object:
    geometry = owner["geometry"]
    kind = geometry["type"]
    if kind == "UV_SPHERE":
        bpy.ops.mesh.primitive_uv_sphere_add(segments=geometry["segments"], ring_count=geometry["rings"], radius=geometry["radius"])
        obj = bpy.context.object
    elif kind == "TORUS":
        bpy.ops.mesh.primitive_torus_add(major_segments=geometry["majorSegments"], minor_segments=geometry["minorSegments"], major_radius=geometry["majorRadius"], minor_radius=geometry["minorRadius"])
        obj = bpy.context.object
    elif kind == "GRID":
        obj = grid_mesh(owner)
        bpy.context.scene.collection.objects.link(obj)
    elif kind == "BEVELED_CUBE":
        bpy.ops.mesh.primitive_cube_add(size=geometry["size"])
        obj = bpy.context.object
        modifier = obj.modifiers.new("BFS_D123_BEVEL", "BEVEL")
        modifier.width = geometry["bevelWidth"]
        modifier.segments = geometry["bevelSegments"]
    elif kind == "ICO_SPHERE":
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=geometry["subdivisions"], radius=geometry["radius"])
        obj = bpy.context.object
    elif kind == "CYLINDER":
        bpy.ops.mesh.primitive_cylinder_add(vertices=geometry["vertices"], radius=geometry["radius"], depth=geometry["depth"])
        obj = bpy.context.object
    else:
        raise RuntimeError(f"unknown D12.3 geometry: {kind}")
    obj.name = f"BFS_D123_{owner['id']}"
    obj.data.name = f"BFS_D123_{owner['id']}_MESH"
    obj.rotation_mode = "XYZ"
    obj.pass_index = owner["passIndex"]
    obj.data.materials.append(material(owner, ordinal))
    transform = owner["transform"]
    for frame in (0, 1, 2):
        obj.location = tuple(transform["location"])
        obj.rotation_euler = tuple(transform["rotationEuler"])
        obj.scale = tuple(transform["scale"])
        obj.keyframe_insert(data_path="location", frame=frame)
        obj.keyframe_insert(data_path="rotation_euler", frame=frame)
        obj.keyframe_insert(data_path="scale", frame=frame)
    freeze_interpolation(obj)
    return obj


def freeze_interpolation(owner: bpy.types.Object) -> None:
    action = owner.animation_data.action if owner.animation_data else None
    if action is None:
        raise RuntimeError(f"missing action for {owner.name}")
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for point in curve.keyframe_points:
                        point.interpolation = "LINEAR"


def key_camera(camera: bpy.types.Object, transform: dict) -> None:
    for frame in (0, 1, 2):
        camera.location = tuple(transform["location"])
        camera.rotation_euler = tuple(transform["rotationEuler"])
        camera.keyframe_insert(data_path="location", frame=frame)
        camera.keyframe_insert(data_path="rotation_euler", frame=frame)
    freeze_interpolation(camera)


def action_rows(owner: bpy.types.Object) -> list[dict]:
    action = owner.animation_data.action if owner.animation_data else None
    rows = []
    if action:
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for curve in bag.fcurves:
                        rows.append({"dataPath": curve.data_path, "arrayIndex": curve.array_index, "keys": [[float(p.co.x), float(p.co.y), p.interpolation] for p in curve.keyframe_points]})
    return sorted(rows, key=lambda row: (row["dataPath"], row["arrayIndex"]))


def setup(spec: dict, fixture: dict, frame: int, repeat: int) -> tuple[bpy.types.Scene, bpy.types.Object, list[bpy.types.Object]]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = f"BFS_D123_{fixture['id']}_F{frame}_R{repeat}"
    render = spec["sceneContract"]["render"]
    scene.render.engine = render["engine"]
    scene.cycles.device = render["device"]
    scene.cycles.samples = render["samples"]
    scene.cycles.seed = render["seed"]
    scene.cycles.use_animated_seed = render["animatedSeed"]
    scene.cycles.use_adaptive_sampling = render["adaptiveSampling"]
    scene.cycles.use_denoising = render["denoising"]
    scene.render.resolution_x, scene.render.resolution_y = fixture["resolution"]
    scene.render.resolution_percentage = 100
    scene.render.pixel_aspect_x, scene.render.pixel_aspect_y = render["pixelAspect"]
    scene.render.film_transparent = render["filmTransparent"]
    scene.render.use_motion_blur = render["motionBlur"]
    scene.render.use_persistent_data = render["persistentData"]
    scene.render.use_compositing = False
    scene.render.use_sequencer = False
    scene.render.use_stamp = False
    scene.render.threads_mode = render["threadsMode"]
    scene.render.threads = render["threads"]
    scene.frame_start, scene.frame_end = 0, 2
    world = bpy.data.worlds.new("BFS_D123_WORLD")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0
    scene.world = world
    camera_data = bpy.data.cameras.new("BFS_D123_CAMERA_DATA")
    camera_data.type = "PERSP"
    camera_data.lens = fixture["lensMm"]
    camera_data.sensor_width = fixture["sensorWidthMm"]
    camera_data.sensor_fit = "HORIZONTAL"
    camera_data.clip_start = 0.1
    camera_data.clip_end = 100.0
    camera_data.dof.use_dof = False
    camera = bpy.data.objects.new("BFS_D123_CAMERA", camera_data)
    camera.rotation_mode = "XYZ"
    scene.collection.objects.link(camera)
    scene.camera = camera
    key_camera(camera, fixture["cameraTransform"])
    owners = [add_owner(owner, index) for index, owner in enumerate(fixture["owners"])]
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    layer = bpy.context.view_layer
    layer.name = render["viewLayer"]
    layer.use_pass_combined = True
    layer.use_pass_z = True
    layer.use_pass_vector = True
    layer.use_pass_object_index = True
    layer.pass_alpha_threshold = render["passAlphaThreshold"]
    scene.render.image_settings.media_type = "MULTI_LAYER_IMAGE"
    scene.render.image_settings.file_format = render["fileFormat"]
    scene.render.image_settings.color_mode = render["colorMode"]
    scene.render.image_settings.color_depth = render["colorDepth"]
    scene.render.image_settings.exr_codec = render["exrCodec"]
    return scene, camera, owners


def owner_structure(owner: bpy.types.Object) -> dict:
    return {
        "name": owner.name, "passIndex": int(owner.pass_index), "vertices": len(owner.data.vertices), "polygons": len(owner.data.polygons),
        "location": [float(value) for value in owner.location], "rotationEuler": [float(value) for value in owner.rotation_euler], "scale": [float(value) for value in owner.scale],
        "modifiers": [{"name": modifier.name, "type": modifier.type} for modifier in owner.modifiers],
        "material": owner.data.materials[0].name, "materialNodes": sorted(node.name for node in owner.data.materials[0].node_tree.nodes),
    }


def main() -> None:
    args = arguments()
    spec = json.loads(args.spec.read_text())
    if sha256_file(args.spec) != SPEC_SHA256:
        raise RuntimeError("B52-D12.3 spec identity mismatch")
    fixture = next((row for row in spec["fixtures"] if row["id"] == args.fixture), None)
    if fixture is None:
        raise RuntimeError("fixture outside D12.3 roster")
    if args.report.exists() or (args.output_exr and args.output_exr.exists()):
        raise RuntimeError("refusing to overwrite D12.3 source output")
    if not args.probe_only and args.output_exr is None:
        raise RuntimeError("output EXR required")
    if sha256_file(Path(bpy.app.binary_path)) != spec["runtime"]["blender"]["sha256"]:
        raise RuntimeError("Blender executable identity mismatch")
    if bpy.app.version_string != spec["runtime"]["blender"]["version"] or bpy.app.build_hash.decode() != spec["runtime"]["blender"]["buildHash"]:
        raise RuntimeError("Blender version identity mismatch")
    if sha256_file(Path(os.environ["OCIO"])) != spec["runtime"]["ocio"]["sha256"]:
        raise RuntimeError("OCIO identity mismatch")
    started = time.monotonic()
    scene, camera, owners = setup(spec, fixture, args.frame, args.repeat)
    body = {
        "schemaVersion": "bfs.blenderStaticNonplanarMultiownerSourceReport.v0.1", "experimentId": spec["experimentId"],
        "fixtureId": fixture["id"], "frame": args.frame, "repeat": args.repeat, "pid": os.getpid(), "probeOnly": args.probe_only,
        "fixture": fixture,
        "runtime": {"blender": bpy.app.version_string, "buildHash": bpy.app.build_hash.decode(), "executableSha256": sha256_file(Path(bpy.app.binary_path)), "engine": scene.render.engine, "device": scene.cycles.device, "samples": scene.cycles.samples, "seed": scene.cycles.seed},
        "sceneStructure": {"camera": {"lensMm": camera.data.lens, "sensorWidthMm": camera.data.sensor_width}, "owners": [owner_structure(owner) for owner in owners]},
        "animation": {"camera": action_rows(camera), "owners": {owner.name: action_rows(owner) for owner in owners}},
        "passState": {"viewLayer": bpy.context.view_layer.name, "Combined": bpy.context.view_layer.use_pass_combined, "Depth": bpy.context.view_layer.use_pass_z, "Vector": bpy.context.view_layer.use_pass_vector, "Object Index": bpy.context.view_layer.use_pass_object_index},
    }
    render_seconds = 0.0
    if not args.probe_only:
        args.output_exr.parent.mkdir(parents=True, exist_ok=False)
        tick = time.monotonic()
        outcome = bpy.ops.render.render(write_still=False)
        if "FINISHED" not in outcome:
            raise RuntimeError(f"D12.3 render failed: {sorted(outcome)}")
        render_seconds = time.monotonic() - tick
        bpy.data.images["Render Result"].save_render(str(args.output_exr), scene=scene)
        body["output"] = {"uri": str(args.output_exr), "sha256": sha256_file(args.output_exr), "bytes": args.output_exr.stat().st_size}
    else:
        body["output"] = None
    body["operationCounts"] = {"blenderProcesses": 1, "blenderRenderCalls": 0 if args.probe_only else 1, "cyclesRayRenders": 0 if args.probe_only else 1, "modelCalls": 0, "networkCalls": 0}
    body["renderSeconds"] = round(render_seconds, 6)
    body["elapsedSeconds"] = round(time.monotonic() - started, 6)
    report = {**body, "reportHash": canonical_hash(body)}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D123_SOURCE_OK fixture={fixture['id']} frame={args.frame} repeat={args.repeat} owners={len(owners)} probe={args.probe_only}", flush=True)


if __name__ == "__main__":
    main()
