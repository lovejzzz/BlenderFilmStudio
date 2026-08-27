#!/usr/bin/env python3
"""Exploratory Blender 5.2 controlled-motion Vector Blur calibration.

This probe is intentionally non-formal. It creates a synthetic animated fixture,
renders one multipart Cycles EXR, then evaluates three real Vector Blur shutter
settings through Blender's compositor. Its outputs may inform a later
preregistration but can never be promoted as holdout evidence.
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
    parser.add_argument("--engine", choices=("BLENDER_EEVEE", "CYCLES"), default="BLENDER_EEVEE")
    return parser.parse_args(raw)


def material(name: str, rgba: tuple[float, float, float, float]):
    value = bpy.data.materials.new(name)
    value.diffuse_color = rgba
    value.use_nodes = True
    principled = value.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = rgba
    principled.inputs["Roughness"].default_value = 0.65
    return value


def add_plane(name: str, location: tuple[float, float, float], scale: tuple[float, float, float], surface) -> object:
    bpy.ops.mesh.primitive_plane_add(size=2.0, location=location)
    value = bpy.context.object
    value.name = name
    value.scale = scale
    value.data.materials.append(surface)
    return value


def configure_fixture(output_dir: Path, engine: str) -> dict:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = "BFS_D5_CONTROLLED_MOTION"
    scene.render.engine = engine
    if engine == "CYCLES":
        scene.cycles.device = "CPU"
        scene.cycles.samples = 16
        scene.cycles.use_adaptive_sampling = False
        scene.cycles.use_denoising = False
    scene.render.resolution_x = 512
    scene.render.resolution_y = 288
    scene.render.resolution_percentage = 100
    scene.render.pixel_aspect_x = 1.0
    scene.render.pixel_aspect_y = 1.0
    scene.render.film_transparent = False
    scene.render.use_motion_blur = False
    scene.render.use_compositing = False
    scene.render.use_sequencer = False
    scene.render.use_stamp = False
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 4

    world = bpy.data.worlds.new("BFS_D5_WORLD")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.015, 0.02, 0.03, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.2
    scene.world = world

    camera_data = bpy.data.cameras.new("BFS_D5_CAMERA")
    camera = bpy.data.objects.new("BFS_D5_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    camera.location = (0.0, 0.0, 10.0)
    camera.rotation_euler = (0.0, 0.0, 0.0)
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 10.0
    scene.camera = camera

    light_data = bpy.data.lights.new("BFS_D5_KEY", "AREA")
    light_data.energy = 1200.0
    light_data.shape = "DISK"
    light_data.size = 8.0
    light = bpy.data.objects.new("BFS_D5_KEY", light_data)
    scene.collection.objects.link(light)
    light.location = (-2.0, -2.0, 7.0)

    background = add_plane("BFS_BACKGROUND", (0.0, 0.0, 0.0), (8.9, 5.0, 1.0), material("BFS_BG_MAT", (0.035, 0.12, 0.22, 1.0)))
    mover = add_plane("BFS_MOVER", (0.0, 0.0, 1.0), (0.8, 0.8, 1.0), material("BFS_MOVER_MAT", (0.92, 0.055, 0.02, 1.0)))
    occluder = add_plane("BFS_OCCLUDER", (0.72, 0.0, 2.0), (0.18, 1.45, 1.0), material("BFS_OCCLUDER_MAT", (0.015, 0.018, 0.022, 1.0)))
    for value in (background, mover, occluder):
        value.rotation_euler = (0.0, 0.0, 0.0)

    mover.location.x = -1.0
    mover.keyframe_insert(data_path="location", frame=0, index=0)
    mover.location.x = 0.0
    mover.keyframe_insert(data_path="location", frame=1, index=0)
    mover.location.x = 1.0
    mover.keyframe_insert(data_path="location", frame=2, index=0)
    if mover.animation_data and mover.animation_data.action:
        for layer in mover.animation_data.action.layers:
            for strip in layer.strips:
                for channelbag in strip.channelbags:
                    for curve in channelbag.fcurves:
                        for point in curve.keyframe_points:
                            point.interpolation = "LINEAR"
    scene.frame_start = 0
    scene.frame_end = 2
    scene.frame_set(1)

    layer = bpy.context.view_layer
    layer.name = "BFS_MASTER"
    layer.use_pass_combined = True
    layer.use_pass_z = True
    layer.use_pass_normal = True
    layer.use_pass_vector = True
    layer.use_pass_cryptomatte_object = True
    layer.pass_cryptomatte_depth = 6
    scene.render.image_settings.media_type = "MULTI_LAYER_IMAGE"
    scene.render.image_settings.file_format = "OPEN_EXR_MULTILAYER"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "32"
    scene.render.image_settings.exr_codec = "ZIP"

    started = time.monotonic()
    outcome = bpy.ops.render.render(write_still=False)
    if "FINISHED" not in outcome:
        raise RuntimeError(f"fixture render failed: {sorted(outcome)}")
    source = output_dir / "controlled-motion-source.exr"
    bpy.data.images["Render Result"].save_render(str(source), scene=scene)
    return {
        "engine": scene.render.engine,
        "renderSeconds": round(time.monotonic() - started, 6),
        "source": {"uri": source.name, "sha256": sha256_file(source), "bytes": source.stat().st_size},
        "fixture": {
            "resolution": [512, 288],
            "camera": {"type": "ORTHO", "orthoScale": 10.0},
            "frame": 1,
            "moverXByFrame": {"0": -1.0, "1": 0.0, "2": 1.0},
            "nominalHorizontalPixelsPerFrame": 28.8,
            "occluderCenterX": 0.72,
            "motionBlur": False,
        },
    }


def compositor_outputs(output_dir: Path, source: Path) -> tuple[list[dict], dict]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 512
    scene.render.resolution_y = 288
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.use_compositing = True
    scene.render.compositor_device = "CPU"
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 4
    scene.render.image_settings.file_format = "OPEN_EXR"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "32"
    scene.render.image_settings.exr_codec = "ZIP"
    camera_data = bpy.data.cameras.new("BFS_D5_COMPOSITOR_CAMERA")
    camera = bpy.data.objects.new("BFS_D5_COMPOSITOR_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    camera.location = (0.0, 0.0, 10.0)
    scene.camera = camera

    tree = bpy.data.node_groups.new("BFS_D5_VECTOR_BLUR", "CompositorNodeTree")
    scene.compositing_node_group = tree
    image_node = tree.nodes.new("CompositorNodeImage")
    image_node.name = "BFS_D5_SOURCE"
    image_node.image = bpy.data.images.load(str(source.resolve()), check_existing=False)
    vector_blur = tree.nodes.new("CompositorNodeVecBlur")
    vector_blur.name = "BFS_D5_VECTOR_BLUR"
    vector_blur.inputs["Samples"].default_value = 32
    tree.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    group_output = tree.nodes.new("NodeGroupOutput")
    group_output.name = "BFS_D5_GROUP_OUTPUT"
    tree.links.new(image_node.outputs["Combined"], vector_blur.inputs["Image"])
    tree.links.new(image_node.outputs["Vector"], vector_blur.inputs["Speed"])
    tree.links.new(image_node.outputs["Depth"], vector_blur.inputs["Z"])
    tree.links.new(vector_blur.outputs["Image"], group_output.inputs["Image"])

    outputs = []
    for shutter in (0.25, 0.5, 1.0):
        vector_blur.inputs["Shutter"].default_value = shutter
        target = output_dir / f"vector-blur-shutter-{str(shutter).replace('.', 'p')}.exr"
        scene.render.filepath = str(target)
        started = time.monotonic()
        outcome = bpy.ops.render.render(write_still=True)
        if "FINISHED" not in outcome or not target.is_file():
            raise RuntimeError(f"compositor shutter {shutter} failed")
        outputs.append({
            "shutter": shutter,
            "samples": int(vector_blur.inputs["Samples"].default_value),
            "renderSeconds": round(time.monotonic() - started, 6),
            "uri": target.name,
            "sha256": sha256_file(target),
            "bytes": target.stat().st_size,
        })
    graph = {
        "imageOutputs": [socket.identifier for socket in image_node.outputs],
        "vectorBlurInputs": [{"identifier": socket.identifier, "name": socket.name, "type": socket.type} for socket in vector_blur.inputs],
        "groupOutput": {"identifier": group_output.inputs["Image"].identifier, "name": group_output.inputs["Image"].name},
        "nodeCount": len(tree.nodes),
        "linkCount": len(tree.links),
    }
    return outputs, graph


def main() -> None:
    args = arguments()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    fixture = configure_fixture(output_dir, args.engine)
    outputs, graph = compositor_outputs(output_dir, output_dir / fixture["source"]["uri"])
    report = {
        "schemaVersion": "bfs.controlledMotionVectorBlurExploratoryProbe.v0.1",
        "classification": "EXPLORATORY_NOT_FORMAL_NOT_PROMOTABLE",
        "blender": {
            "version": bpy.app.version_string,
            "buildHash": bpy.app.build_hash.decode("ascii"),
            "buildPlatform": bpy.app.build_platform.decode("ascii"),
        },
        "fixtureRender": fixture,
        "compositorOutputs": outputs,
        "graph": graph,
        "operationCounts": {"blenderProcesses": 1, "fixtureRenderCalls": 1, "compositorRenderCalls": 3, "cyclesRayRenders": 1 if args.engine == "CYCLES" else 0},
        "nonClaims": [
            "This probe is not a preregistered experiment.",
            "The synthetic fixture is not a production shot or human-quality reference.",
            "No adaptive candidate is evaluated or promoted.",
        ],
    }
    path = output_dir / "probe.report.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(f"BFS_B52_D5_CONTROLLED_MOTION_PROBE_OK report={sha256_file(path)}", flush=True)


if __name__ == "__main__":
    main()
