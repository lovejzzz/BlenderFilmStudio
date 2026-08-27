#!/usr/bin/env python3
"""Development-only Blender 5.2 probe for projective subpixel reprojection.

The output of this script is calibration evidence only. It must not be used in
the future B52-D12 formal decision.
"""

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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def arguments() -> argparse.Namespace:
    raw = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args(raw)


def set_linear_location_keys(owner: bpy.types.Object, values: dict[int, tuple[float, float, float]]) -> None:
    for frame, location in values.items():
        owner.location = location
        owner.keyframe_insert(data_path="location", frame=frame)
    action = owner.animation_data.action
    for layer in action.layers:
        for strip in layer.strips:
            for channelbag in strip.channelbags:
                for curve in channelbag.fcurves:
                    for point in curve.keyframe_points:
                        point.interpolation = "LINEAR"


def smooth_emission_material() -> bpy.types.Material:
    material = bpy.data.materials.new("BFS_D12_DEV_SMOOTH_MATERIAL")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    emission = nodes.new("ShaderNodeEmission")
    texcoord = nodes.new("ShaderNodeTexCoord")
    separate = nodes.new("ShaderNodeSeparateXYZ")
    combine = nodes.new("ShaderNodeCombineColor")

    links.new(texcoord.outputs["Generated"], separate.inputs["Vector"])

    def sine_channel(source: bpy.types.NodeSocket, frequency: float, phase: float, amplitude: float):
        multiply = nodes.new("ShaderNodeMath")
        multiply.operation = "MULTIPLY"
        multiply.inputs[1].default_value = 2.0 * math.pi * frequency
        add_phase = nodes.new("ShaderNodeMath")
        add_phase.operation = "ADD"
        add_phase.inputs[1].default_value = phase
        sine = nodes.new("ShaderNodeMath")
        sine.operation = "SINE"
        scale = nodes.new("ShaderNodeMath")
        scale.operation = "MULTIPLY_ADD"
        scale.inputs[1].default_value = amplitude
        scale.inputs[2].default_value = 0.5
        links.new(source, multiply.inputs[0])
        links.new(multiply.outputs[0], add_phase.inputs[0])
        links.new(add_phase.outputs[0], sine.inputs[0])
        links.new(sine.outputs[0], scale.inputs[0])
        return scale.outputs[0]

    red = sine_channel(separate.outputs["X"], 1.25, 0.17, 0.23)
    green = sine_channel(separate.outputs["Y"], 1.0, 0.43, 0.21)

    mix_uv = nodes.new("ShaderNodeMath")
    mix_uv.operation = "MULTIPLY_ADD"
    mix_uv.inputs[1].default_value = 0.7
    mix_uv.inputs[2].default_value = 0.0
    v_scale = nodes.new("ShaderNodeMath")
    v_scale.operation = "MULTIPLY"
    v_scale.inputs[1].default_value = 0.9
    uv_add = nodes.new("ShaderNodeMath")
    uv_add.operation = "ADD"
    links.new(separate.outputs["X"], mix_uv.inputs[0])
    links.new(separate.outputs["Y"], v_scale.inputs[0])
    links.new(mix_uv.outputs[0], uv_add.inputs[0])
    links.new(v_scale.outputs[0], uv_add.inputs[1])
    blue = sine_channel(uv_add.outputs[0], 0.85, 0.91, 0.19)

    links.new(red, combine.inputs["Red"])
    links.new(green, combine.inputs["Green"])
    links.new(blue, combine.inputs["Blue"])
    links.new(combine.outputs["Color"], emission.inputs["Color"])
    emission.inputs["Strength"].default_value = 1.0
    links.new(emission.outputs["Emission"], output.inputs["Surface"])
    return material


def main() -> None:
    args = arguments()
    if args.output_dir.exists():
        raise RuntimeError("refusing to overwrite D12 development probe")
    args.output_dir.mkdir(parents=True, exist_ok=False)

    started = time.monotonic()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = "BFS_D12_DEV_PROJECTIVE_SUBPIXEL"
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 1
    scene.cycles.seed = 12052
    scene.cycles.use_animated_seed = False
    scene.cycles.use_adaptive_sampling = False
    scene.cycles.use_denoising = False
    scene.render.resolution_x = 101
    scene.render.resolution_y = 61
    scene.render.resolution_percentage = 100
    scene.render.pixel_aspect_x = 1.0
    scene.render.pixel_aspect_y = 1.0
    scene.render.film_transparent = False
    scene.render.use_motion_blur = False
    scene.render.use_persistent_data = False
    scene.render.use_compositing = False
    scene.render.use_sequencer = False
    scene.render.use_stamp = False
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 4
    scene.frame_start = 0
    scene.frame_end = 2

    world = bpy.data.worlds.new("BFS_D12_DEV_WORLD")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0
    scene.world = world

    camera_data = bpy.data.cameras.new("BFS_D12_DEV_CAMERA_DATA")
    camera = bpy.data.objects.new("BFS_D12_DEV_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    camera.location = (0.0, 0.0, 10.0)
    camera.rotation_euler = (0.0, 0.0, 0.0)
    camera_data.type = "PERSP"
    camera_data.lens = 50.0
    camera_data.sensor_width = 36.0
    camera_data.sensor_fit = "HORIZONTAL"
    camera_data.dof.use_dof = False
    scene.camera = camera

    bpy.ops.mesh.primitive_grid_add(x_subdivisions=65, y_subdivisions=41, size=2.0)
    surface = bpy.context.object
    surface.name = "BFS_D12_DEV_SURFACE"
    surface.scale = (5.0, 3.0, 1.0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    surface.pass_index = 8120
    surface.data.materials.append(smooth_emission_material())
    set_linear_location_keys(
        surface,
        {
            0: (-0.040, 0.030, 0.000),
            1: (0.015, -0.025, 0.180),
            2: (0.060, 0.020, 0.360),
        },
    )

    layer = bpy.context.view_layer
    layer.name = "BFS_D12_DEV_LAYER"
    layer.use_pass_combined = True
    layer.use_pass_z = True
    layer.use_pass_vector = True
    layer.use_pass_object_index = True
    layer.pass_alpha_threshold = 0.5
    scene.render.image_settings.media_type = "MULTI_LAYER_IMAGE"
    scene.render.image_settings.file_format = "OPEN_EXR_MULTILAYER"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "32"
    scene.render.image_settings.exr_codec = "ZIP"

    outputs = []
    for frame in (0, 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        target = args.output_dir / f"frame-{frame}.exr"
        render_started = time.monotonic()
        outcome = bpy.ops.render.render(write_still=False)
        if "FINISHED" not in outcome:
            raise RuntimeError(f"development render failed: {sorted(outcome)}")
        bpy.data.images["Render Result"].save_render(str(target), scene=scene)
        outputs.append(
            {
                "frame": frame,
                "uri": str(target),
                "sha256": sha256_file(target),
                "bytes": target.stat().st_size,
                "renderSeconds": round(time.monotonic() - render_started, 6),
            }
        )

    report = {
        "schemaVersion": "bfs.projectiveSubpixelDevelopmentSource.v0.1",
        "status": "DEVELOPMENT_ONLY",
        "pid": os.getpid(),
        "blender": {
            "version": bpy.app.version_string,
            "buildHash": bpy.app.build_hash.decode(),
            "executableSha256": sha256_file(Path(bpy.app.binary_path)),
        },
        "resolution": [scene.render.resolution_x, scene.render.resolution_y],
        "camera": {"type": camera_data.type, "lens": camera_data.lens, "sensorWidth": camera_data.sensor_width},
        "trajectory": {"0": [-0.040, 0.030, 0.000], "1": [0.015, -0.025, 0.180], "2": [0.060, 0.020, 0.360]},
        "outputs": outputs,
        "elapsedSeconds": round(time.monotonic() - started, 6),
        "nonClaims": ["not preregistered", "not fresh holdout", "not a scientific verdict"],
    }
    (args.output_dir / "source.report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"BFS_B52_D12_DEV_SOURCE_OK outputs={len(outputs)}", flush=True)


if __name__ == "__main__":
    main()
