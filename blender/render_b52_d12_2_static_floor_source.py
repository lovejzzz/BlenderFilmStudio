#!/usr/bin/env python3
"""Render one preregistered B52-D12.2 static multipart source cell."""

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


SPEC_SHA256 = "fa63daa0c3b7b3f080a488aa0fc84996fd52cd731efce94ebe28bbc81b55d9d3"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(payload).hexdigest()


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


def add_material(spec: dict) -> bpy.types.Material:
    definition = spec["sceneContract"]["material"]
    material = bpy.data.materials.new("BFS_D122_CONTINUOUS_EMISSION")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    output.name = "BFS_D122_MATERIAL_OUTPUT"
    emission = nodes.new("ShaderNodeEmission")
    emission.name = "BFS_D122_EMISSION"
    texcoord = nodes.new("ShaderNodeTexCoord")
    texcoord.name = "BFS_D122_GENERATED_COORDINATE"
    separate = nodes.new("ShaderNodeSeparateXYZ")
    separate.name = "BFS_D122_SEPARATE_UV"
    combine = nodes.new("ShaderNodeCombineColor")
    combine.name = "BFS_D122_COMBINE_RGB"
    links.new(texcoord.outputs["Generated"], separate.inputs["Vector"])

    def channel(name: str, socket: bpy.types.NodeSocket, row: dict) -> bpy.types.NodeSocket:
        multiply = nodes.new("ShaderNodeMath")
        multiply.name = f"BFS_D122_{name}_FREQUENCY"
        multiply.operation = "MULTIPLY"
        multiply.inputs[1].default_value = 2.0 * math.pi * row["frequency"]
        phase = nodes.new("ShaderNodeMath")
        phase.name = f"BFS_D122_{name}_PHASE"
        phase.operation = "ADD"
        phase.inputs[1].default_value = row["phase"]
        sine = nodes.new("ShaderNodeMath")
        sine.name = f"BFS_D122_{name}_SINE"
        sine.operation = "SINE"
        scale = nodes.new("ShaderNodeMath")
        scale.name = f"BFS_D122_{name}_AMPLITUDE_OFFSET"
        scale.operation = "MULTIPLY_ADD"
        scale.inputs[1].default_value = row["amplitude"]
        scale.inputs[2].default_value = row["offset"]
        links.new(socket, multiply.inputs[0])
        links.new(multiply.outputs[0], phase.inputs[0])
        links.new(phase.outputs[0], sine.inputs[0])
        links.new(sine.outputs[0], scale.inputs[0])
        return scale.outputs[0]

    red = channel("RED", separate.outputs["X"], definition["red"])
    green = channel("GREEN", separate.outputs["Y"], definition["green"])
    blue_row = definition["blue"]
    u_scale = nodes.new("ShaderNodeMath")
    u_scale.name = "BFS_D122_BLUE_U_SCALE"
    u_scale.operation = "MULTIPLY"
    u_scale.inputs[1].default_value = blue_row["linearUv"][0]
    v_scale = nodes.new("ShaderNodeMath")
    v_scale.name = "BFS_D122_BLUE_V_SCALE"
    v_scale.operation = "MULTIPLY"
    v_scale.inputs[1].default_value = blue_row["linearUv"][1]
    uv_add = nodes.new("ShaderNodeMath")
    uv_add.name = "BFS_D122_BLUE_UV_ADD"
    uv_add.operation = "ADD"
    links.new(separate.outputs["X"], u_scale.inputs[0])
    links.new(separate.outputs["Y"], v_scale.inputs[0])
    links.new(u_scale.outputs[0], uv_add.inputs[0])
    links.new(v_scale.outputs[0], uv_add.inputs[1])
    blue = channel("BLUE", uv_add.outputs[0], blue_row)
    links.new(red, combine.inputs["Red"])
    links.new(green, combine.inputs["Green"])
    links.new(blue, combine.inputs["Blue"])
    links.new(combine.outputs["Color"], emission.inputs["Color"])
    emission.inputs["Strength"].default_value = definition["emissionStrength"]
    links.new(emission.outputs["Emission"], output.inputs["Surface"])
    return material


def add_surface(spec: dict, fixture: dict) -> bpy.types.Object:
    width, height = spec["sceneContract"]["surfaceSizeWorld"]
    columns, rows = spec["sceneContract"]["surfaceSubdivisions"]
    vertices = [
        (-width / 2 + column * width / columns, -height / 2 + row * height / rows, 0.0)
        for row in range(rows + 1)
        for column in range(columns + 1)
    ]
    faces = []
    for row in range(rows):
        for column in range(columns):
            a = row * (columns + 1) + column
            faces.append((a, a + 1, a + columns + 2, a + columns + 1))
    mesh = bpy.data.meshes.new(f"BFS_D122_{fixture['id']}_MESH")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    surface = bpy.data.objects.new(f"BFS_D122_{fixture['id']}_SURFACE", mesh)
    surface.rotation_mode = "XYZ"
    surface.pass_index = fixture["passIndex"]
    mesh.materials.append(add_material(spec))
    bpy.context.scene.collection.objects.link(surface)
    return surface


def key_static(owner: bpy.types.Object, transform: dict) -> None:
    for frame in (0, 1, 2):
        owner.location = tuple(transform["location"])
        owner.rotation_euler = tuple(transform["rotationEuler"])
        owner.keyframe_insert(data_path="location", frame=frame)
        owner.keyframe_insert(data_path="rotation_euler", frame=frame)
    action = owner.animation_data.action if owner.animation_data else None
    if action is None:
        raise RuntimeError(f"missing static action for {owner.name}")
    for layer in action.layers:
        for strip in layer.strips:
            for channelbag in strip.channelbags:
                for curve in channelbag.fcurves:
                    for point in curve.keyframe_points:
                        point.interpolation = "LINEAR"


def action_rows(owner: bpy.types.Object) -> list[dict]:
    action = owner.animation_data.action if owner.animation_data else None
    rows = []
    if action:
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for curve in bag.fcurves:
                        rows.append({
                            "dataPath": curve.data_path,
                            "arrayIndex": curve.array_index,
                            "keys": [[float(point.co.x), float(point.co.y), point.interpolation] for point in curve.keyframe_points],
                        })
    return sorted(rows, key=lambda row: (row["dataPath"], row["arrayIndex"]))


def setup(spec: dict, fixture: dict, frame: int, repeat: int) -> tuple[bpy.types.Scene, bpy.types.Object, bpy.types.Object]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = f"BFS_D122_{fixture['id']}_F{frame}_R{repeat}"
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
    world = bpy.data.worlds.new("BFS_D122_WORLD")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0
    scene.world = world

    camera_data = bpy.data.cameras.new("BFS_D122_CAMERA_DATA")
    camera_data.type = "PERSP"
    camera_data.lens = fixture["lensMm"]
    camera_data.sensor_width = fixture["sensorWidthMm"]
    camera_data.sensor_fit = "HORIZONTAL"
    camera_data.clip_start = 0.1
    camera_data.clip_end = 100.0
    camera_data.dof.use_dof = False
    camera = bpy.data.objects.new("BFS_D122_CAMERA", camera_data)
    camera.rotation_mode = "XYZ"
    bpy.context.scene.collection.objects.link(camera)
    scene.camera = camera
    surface = add_surface(spec, fixture)
    key_static(surface, fixture["surfaceTransform"])
    key_static(camera, fixture["cameraTransform"])
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
    return scene, camera, surface


def main() -> None:
    args = arguments()
    spec = json.loads(args.spec.read_text())
    if sha256_file(args.spec) != SPEC_SHA256:
        raise RuntimeError("B52-D12.2 spec identity mismatch")
    fixture = next((row for row in spec["fixtures"] if row["id"] == args.fixture), None)
    if fixture is None:
        raise RuntimeError("fixture outside D12.2 roster")
    if args.report.exists() or (args.output_exr and args.output_exr.exists()):
        raise RuntimeError("refusing to overwrite D12.2 source output")
    if not args.probe_only and args.output_exr is None:
        raise RuntimeError("output EXR required")
    if sha256_file(Path(bpy.app.binary_path)) != spec["runtime"]["blender"]["sha256"]:
        raise RuntimeError("Blender executable identity mismatch")
    if bpy.app.version_string != spec["runtime"]["blender"]["version"] or bpy.app.build_hash.decode() != spec["runtime"]["blender"]["buildHash"]:
        raise RuntimeError("Blender version identity mismatch")
    if sha256_file(Path(os.environ["OCIO"])) != spec["runtime"]["ocio"]["sha256"]:
        raise RuntimeError("OCIO identity mismatch")

    started = time.monotonic()
    scene, camera, surface = setup(spec, fixture, args.frame, args.repeat)
    body = {
        "schemaVersion": "bfs.blenderStaticVectorFloorSourceReport.v0.1",
        "experimentId": spec["experimentId"],
        "fixtureId": fixture["id"],
        "frame": args.frame,
        "repeat": args.repeat,
        "pid": os.getpid(),
        "probeOnly": args.probe_only,
        "fixture": fixture,
        "runtime": {
            "blender": bpy.app.version_string,
            "buildHash": bpy.app.build_hash.decode(),
            "executableSha256": sha256_file(Path(bpy.app.binary_path)),
            "engine": scene.render.engine,
            "device": scene.cycles.device,
            "samples": scene.cycles.samples,
            "seed": scene.cycles.seed,
        },
        "animation": {"surface": action_rows(surface), "camera": action_rows(camera)},
        "passState": {
            "viewLayer": bpy.context.view_layer.name,
            "Combined": bpy.context.view_layer.use_pass_combined,
            "Depth": bpy.context.view_layer.use_pass_z,
            "Vector": bpy.context.view_layer.use_pass_vector,
            "Object Index": bpy.context.view_layer.use_pass_object_index,
        },
    }
    render_seconds = 0.0
    if not args.probe_only:
        args.output_exr.parent.mkdir(parents=True, exist_ok=False)
        tick = time.monotonic()
        outcome = bpy.ops.render.render(write_still=False)
        if "FINISHED" not in outcome:
            raise RuntimeError(f"D12.2 render failed: {sorted(outcome)}")
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
    print(f"BFS_B52_D122_SOURCE_OK fixture={fixture['id']} frame={args.frame} repeat={args.repeat} probe={args.probe_only}", flush=True)


if __name__ == "__main__":
    main()
