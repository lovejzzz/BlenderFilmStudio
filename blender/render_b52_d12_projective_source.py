#!/usr/bin/env python3
"""Render one preregistered B52-D12 perspective multipart source cell."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import struct
import sys
import time
from pathlib import Path

import bpy


SPEC_SHA256 = "dd2e990d276e0ee5c2fee9d22cf42c7f84db2b6c1947b1219dceab06a76f66a2"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", value))[0]


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


def smooth_emission_material(spec: dict) -> bpy.types.Material:
    definition = spec["scene"]["material"]
    material = bpy.data.materials.new("BFS_D12_CONTINUOUS_EMISSION")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    output.name = "BFS_D12_MATERIAL_OUTPUT"
    emission = nodes.new("ShaderNodeEmission")
    emission.name = "BFS_D12_EMISSION"
    texcoord = nodes.new("ShaderNodeTexCoord")
    texcoord.name = "BFS_D12_GENERATED_COORDINATE"
    separate = nodes.new("ShaderNodeSeparateXYZ")
    separate.name = "BFS_D12_SEPARATE_UV"
    combine = nodes.new("ShaderNodeCombineColor")
    combine.name = "BFS_D12_COMBINE_RGB"
    links.new(texcoord.outputs["Generated"], separate.inputs["Vector"])

    def sine_channel(name: str, source: bpy.types.NodeSocket, frequency: float, phase: float, amplitude: float, offset: float):
        multiply = nodes.new("ShaderNodeMath")
        multiply.name = f"BFS_D12_{name}_FREQUENCY"
        multiply.operation = "MULTIPLY"
        multiply.inputs[1].default_value = 2.0 * math.pi * frequency
        add_phase = nodes.new("ShaderNodeMath")
        add_phase.name = f"BFS_D12_{name}_PHASE"
        add_phase.operation = "ADD"
        add_phase.inputs[1].default_value = phase
        sine = nodes.new("ShaderNodeMath")
        sine.name = f"BFS_D12_{name}_SINE"
        sine.operation = "SINE"
        scale = nodes.new("ShaderNodeMath")
        scale.name = f"BFS_D12_{name}_AMPLITUDE_OFFSET"
        scale.operation = "MULTIPLY_ADD"
        scale.inputs[1].default_value = amplitude
        scale.inputs[2].default_value = offset
        links.new(source, multiply.inputs[0])
        links.new(multiply.outputs[0], add_phase.inputs[0])
        links.new(add_phase.outputs[0], sine.inputs[0])
        links.new(sine.outputs[0], scale.inputs[0])
        return scale.outputs[0]

    red_spec, green_spec, blue_spec = definition["red"], definition["green"], definition["blue"]
    red = sine_channel("RED", separate.outputs["X"], red_spec["frequency"], red_spec["phase"], red_spec["amplitude"], red_spec["offset"])
    green = sine_channel("GREEN", separate.outputs["Y"], green_spec["frequency"], green_spec["phase"], green_spec["amplitude"], green_spec["offset"])
    u_scale = nodes.new("ShaderNodeMath")
    u_scale.name = "BFS_D12_BLUE_U_SCALE"
    u_scale.operation = "MULTIPLY"
    u_scale.inputs[1].default_value = blue_spec["linearUv"][0]
    v_scale = nodes.new("ShaderNodeMath")
    v_scale.name = "BFS_D12_BLUE_V_SCALE"
    v_scale.operation = "MULTIPLY"
    v_scale.inputs[1].default_value = blue_spec["linearUv"][1]
    uv_add = nodes.new("ShaderNodeMath")
    uv_add.name = "BFS_D12_BLUE_UV_ADD"
    uv_add.operation = "ADD"
    links.new(separate.outputs["X"], u_scale.inputs[0])
    links.new(separate.outputs["Y"], v_scale.inputs[0])
    links.new(u_scale.outputs[0], uv_add.inputs[0])
    links.new(v_scale.outputs[0], uv_add.inputs[1])
    blue = sine_channel("BLUE", uv_add.outputs[0], blue_spec["frequency"], blue_spec["phase"], blue_spec["amplitude"], blue_spec["offset"])
    links.new(red, combine.inputs["Red"])
    links.new(green, combine.inputs["Green"])
    links.new(blue, combine.inputs["Blue"])
    links.new(combine.outputs["Color"], emission.inputs["Color"])
    emission.inputs["Strength"].default_value = definition["emissionStrength"]
    links.new(emission.outputs["Emission"], output.inputs["Surface"])
    return material


def add_surface(spec: dict, fixture: dict) -> bpy.types.Object:
    width, height = spec["scene"]["surfaceSizeWorld"]
    columns, rows = spec["scene"]["surfaceSubdivisions"]
    vertices = []
    for row in range(rows + 1):
        y = -height / 2.0 + row * height / rows
        for column in range(columns + 1):
            x = -width / 2.0 + column * width / columns
            vertices.append((x, y, 0.0))
    faces = []
    for row in range(rows):
        for column in range(columns):
            a = row * (columns + 1) + column
            faces.append((a, a + 1, a + columns + 2, a + columns + 1))
    mesh = bpy.data.meshes.new(f"BFS_D12_{fixture['id']}_MESH")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    owner = bpy.data.objects.new(f"BFS_D12_{fixture['id']}_SURFACE", mesh)
    owner.rotation_mode = spec["scene"]["eulerOrder"]
    owner.pass_index = fixture["passIndex"]
    mesh.materials.append(smooth_emission_material(spec))
    bpy.context.scene.collection.objects.link(owner)
    return owner


def key_transform(owner: bpy.types.Object, values: dict[str, dict]) -> None:
    for frame_text, transform in values.items():
        owner.location = tuple(transform["location"])
        owner.rotation_euler = tuple(transform["rotationEuler"])
        frame = int(frame_text)
        owner.keyframe_insert(data_path="location", frame=frame)
        owner.keyframe_insert(data_path="rotation_euler", frame=frame)
    action = owner.animation_data.action if owner.animation_data else None
    if action is None:
        raise RuntimeError(f"missing action for {owner.name}")
    for layer in action.layers:
        for strip in layer.strips:
            for channelbag in strip.channelbags:
                for curve in channelbag.fcurves:
                    for point in curve.keyframe_points:
                        point.interpolation = "LINEAR"


def action_rows(owner: bpy.types.Object) -> list[dict]:
    action = owner.animation_data.action if owner.animation_data else None
    if action is None:
        return []
    rows = []
    for layer_index, layer in enumerate(action.layers):
        for strip_index, strip in enumerate(layer.strips):
            for bag_index, bag in enumerate(strip.channelbags):
                for curve in bag.fcurves:
                    rows.append({
                        "layerIndex": layer_index,
                        "stripIndex": strip_index,
                        "channelBagIndex": bag_index,
                        "dataPath": curve.data_path,
                        "arrayIndex": curve.array_index,
                        "keyframes": [{"frame": float(p.co.x), "value": float(p.co.y), "interpolation": p.interpolation} for p in curve.keyframe_points],
                    })
    return sorted(rows, key=lambda row: (row["dataPath"], row["arrayIndex"]))


def setup_scene(spec: dict, fixture: dict, frame: int, repeat: int) -> tuple[bpy.types.Scene, bpy.types.Object, bpy.types.Object]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = f"BFS_D12_{fixture['id']}_F{frame}_R{repeat}"
    render = spec["sourceRender"]
    scene.render.engine = render["engine"]
    scene.cycles.device = render["device"]
    scene.cycles.samples = render["samples"]
    scene.cycles.seed = render["seed"]
    scene.cycles.use_animated_seed = render["animatedSeed"]
    scene.cycles.use_adaptive_sampling = render["adaptiveSampling"]
    scene.cycles.use_denoising = render["denoising"]
    scene.render.resolution_x, scene.render.resolution_y = render["resolution"]
    scene.render.resolution_percentage = render["resolutionPercentage"]
    scene.render.pixel_aspect_x, scene.render.pixel_aspect_y = render["pixelAspect"]
    scene.render.film_transparent = render["filmTransparent"]
    scene.render.use_motion_blur = render["motionBlur"]
    scene.render.use_persistent_data = render["persistentData"]
    scene.render.use_compositing = False
    scene.render.use_sequencer = False
    scene.render.use_stamp = False
    scene.render.threads_mode = render["threadsMode"]
    scene.render.threads = render["threads"]
    scene.frame_start, scene.frame_end = spec["scene"]["frameRange"]
    world = bpy.data.worlds.new("BFS_D12_WORLD")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0
    scene.world = world

    camera_spec = spec["scene"]["camera"]
    camera_data = bpy.data.cameras.new("BFS_D12_CAMERA_DATA")
    camera = bpy.data.objects.new("BFS_D12_CAMERA", camera_data)
    camera.rotation_mode = spec["scene"]["eulerOrder"]
    camera_data.type = camera_spec["type"]
    camera_data.lens = camera_spec["lensMm"]
    camera_data.sensor_width = camera_spec["sensorWidthMm"]
    camera_data.sensor_fit = camera_spec["sensorFit"]
    camera_data.clip_start = camera_spec["clipStart"]
    camera_data.clip_end = camera_spec["clipEnd"]
    camera_data.dof.use_dof = render["depthOfField"]
    scene.collection.objects.link(camera)
    scene.camera = camera
    surface = add_surface(spec, fixture)
    key_transform(surface, fixture["surfaceByFrame"])
    key_transform(camera, fixture["cameraByFrame"])
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


def structure(scene: bpy.types.Scene, camera: bpy.types.Object, surface: bpy.types.Object) -> dict:
    material = surface.data.materials[0]
    return {
        "sceneName": scene.name,
        "frame": scene.frame_current,
        "camera": {
            "name": camera.name,
            "type": camera.data.type,
            "lensMm": f32(camera.data.lens),
            "sensorWidthMm": f32(camera.data.sensor_width),
            "sensorFit": camera.data.sensor_fit,
            "location": [float(v) for v in camera.location],
            "rotationEuler": [float(v) for v in camera.rotation_euler],
        },
        "surface": {
            "name": surface.name,
            "type": surface.type,
            "passIndex": int(surface.pass_index),
            "location": [float(v) for v in surface.location],
            "rotationEuler": [float(v) for v in surface.rotation_euler],
            "dimensions": [f32(surface.dimensions.x), f32(surface.dimensions.y), f32(surface.dimensions.z)],
            "vertices": len(surface.data.vertices),
            "polygons": len(surface.data.polygons),
            "material": material.name,
            "materialNodes": sorted(node.name for node in material.node_tree.nodes),
        },
    }


def main() -> None:
    args = arguments()
    spec = json.loads(args.spec.read_text())
    if sha256_file(args.spec) != SPEC_SHA256:
        raise RuntimeError("B52-D12 spec identity mismatch")
    fixture = next((item for item in spec["fixtures"] if item["id"] == args.fixture), None)
    if fixture is None:
        raise RuntimeError("fixture outside frozen D12 roster")
    if args.report.exists() or (args.output_exr and args.output_exr.exists()):
        raise RuntimeError("refusing to overwrite D12 source output")
    if not args.probe_only and args.output_exr is None:
        raise RuntimeError("output EXR required outside probe-only mode")
    if sha256_file(Path(bpy.app.binary_path)) != spec["runtime"]["blender"]["sha256"]:
        raise RuntimeError("Blender executable identity mismatch")
    if bpy.app.version_string != spec["runtime"]["blender"]["version"] or bpy.app.build_hash.decode() != spec["runtime"]["blender"]["buildHash"]:
        raise RuntimeError("Blender version identity mismatch")
    if sha256_file(Path(os.environ["OCIO"])) != spec["runtime"]["ocio"]["sha256"]:
        raise RuntimeError("OCIO identity mismatch")

    started = time.monotonic()
    scene, camera, surface = setup_scene(spec, fixture, args.frame, args.repeat)
    layer = bpy.context.view_layer
    report_body = {
        "schemaVersion": "bfs.blenderProjectiveSubpixelSourceReport.v0.1",
        "experimentId": spec["experimentId"],
        "fixtureId": fixture["id"],
        "frame": args.frame,
        "repeat": args.repeat,
        "pid": os.getpid(),
        "probeOnly": args.probe_only,
        "blender": {"version": bpy.app.version_string, "buildHash": bpy.app.build_hash.decode(), "executableSha256": sha256_file(Path(bpy.app.binary_path))},
        "runtime": {"engine": scene.render.engine, "device": scene.cycles.device, "samples": scene.cycles.samples, "seed": scene.cycles.seed, "adaptiveSampling": scene.cycles.use_adaptive_sampling, "denoising": scene.cycles.use_denoising, "motionBlur": scene.render.use_motion_blur, "threads": scene.render.threads},
        "fixture": fixture,
        "sceneStructure": structure(scene, camera, surface),
        "animationStructure": {"camera": action_rows(camera), "surface": action_rows(surface)},
        "passState": {"viewLayer": layer.name, "Combined": layer.use_pass_combined, "Depth": layer.use_pass_z, "Vector": layer.use_pass_vector, "Object Index": layer.use_pass_object_index, "passAlphaThreshold": layer.pass_alpha_threshold},
    }
    render_seconds = 0.0
    if not args.probe_only:
        args.output_exr.parent.mkdir(parents=True, exist_ok=False)
        render_started = time.monotonic()
        outcome = bpy.ops.render.render(write_still=False)
        if "FINISHED" not in outcome:
            raise RuntimeError(f"D12 source render failed: {sorted(outcome)}")
        render_seconds = time.monotonic() - render_started
        bpy.data.images["Render Result"].save_render(str(args.output_exr), scene=scene)
        if not args.output_exr.is_file():
            raise RuntimeError("D12 source EXR absent")
        report_body["output"] = {"uri": str(args.output_exr), "sha256": sha256_file(args.output_exr), "bytes": args.output_exr.stat().st_size}
    else:
        report_body["output"] = None
    report_body["operationCounts"] = {"blenderProcesses": 1, "blenderRenderCalls": 0 if args.probe_only else 1, "cyclesRayRenders": 0 if args.probe_only else 1, "sourceBlendFilesOpened": 0, "externalAssetsOpened": 0}
    report_body["renderSeconds"] = round(render_seconds, 6)
    report_body["elapsedSeconds"] = round(time.monotonic() - started, 6)
    report = {**report_body, "reportHash": canonical_hash(report_body)}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D12_SOURCE_OK fixture={fixture['id']} frame={args.frame} probe={args.probe_only}", flush=True)


if __name__ == "__main__":
    main()
