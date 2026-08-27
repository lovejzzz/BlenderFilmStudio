#!/usr/bin/env python3
"""Render one non-formal Blender 5.2 pass-adapter semantics probe source.

The probe deliberately uses asymmetric previous/current/next motion so the two
Vector channel pairs can be identified.  Outputs are development observations
only and must never be promoted to holdout evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view


FIXTURES = {
    "OBJECT_ASYMMETRIC_XY": {
        "moverByFrame": {
            "0": [-0.50, 0.25, 1.0],
            "1": [0.00, 0.00, 1.0],
            "2": [1.25, -0.75, 1.0],
        },
        "cameraByFrame": None,
    },
    "CAMERA_ASYMMETRIC_XY": {
        "moverByFrame": None,
        "cameraByFrame": {
            "0": [-0.40, 0.20, 10.0],
            "1": [0.00, 0.00, 10.0],
            "2": [0.80, -0.60, 10.0],
        },
    },
    "STATIC_DEPTH_OWNERSHIP": {
        "moverByFrame": None,
        "cameraByFrame": None,
    },
}

GEOMETRY = (
    {"name": "BFS_BACKGROUND", "location": [0.0, 0.0, 0.0], "scale": [6.0, 4.0, 1.0], "passIndex": 11, "color": [0.03, 0.08, 0.16, 1.0]},
    {"name": "BFS_MOVER", "location": [0.0, 0.0, 1.0], "scale": [0.65, 0.55, 1.0], "passIndex": 22, "color": [0.90, 0.04, 0.02, 1.0]},
    {"name": "BFS_NEAR", "location": [1.85, 0.35, 2.0], "scale": [0.42, 0.90, 1.0], "passIndex": 33, "color": [0.02, 0.70, 0.16, 1.0]},
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def arguments() -> argparse.Namespace:
    raw = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", choices=tuple(FIXTURES), required=True)
    parser.add_argument("--output-exr", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args(raw)


def emission_material(name: str, rgba: list[float]):
    material = bpy.data.materials.new(name)
    material.diffuse_color = tuple(rgba)
    material.use_nodes = True
    tree = material.node_tree
    tree.nodes.clear()
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    emission = tree.nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = tuple(rgba)
    emission.inputs["Strength"].default_value = 1.0
    tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])
    return material


def add_plane(item: dict) -> object:
    bpy.ops.mesh.primitive_plane_add(size=2.0, location=tuple(item["location"]))
    value = bpy.context.object
    value.name = item["name"]
    value.data.name = f"{item['name']}_MESH"
    value.scale = tuple(item["scale"])
    value.pass_index = item["passIndex"]
    value.data.materials.append(emission_material(f"{item['name']}_MAT", item["color"]))
    return value


def set_linear_location_keys(owner: object, values: dict[str, list[float]]) -> None:
    for frame_text, location in values.items():
        owner.location = tuple(location)
        owner.keyframe_insert(data_path="location", frame=int(frame_text))
    action = owner.animation_data.action if owner.animation_data and owner.animation_data.action else None
    if action is None:
        raise RuntimeError("Blender 5.2 did not create an Action")
    for layer in action.layers:
        for strip in layer.strips:
            for channelbag in strip.channelbags:
                for curve in channelbag.fcurves:
                    for point in curve.keyframe_points:
                        point.interpolation = "LINEAR"


def projection_rows(scene: bpy.types.Scene, camera: bpy.types.Object, objects: dict[str, object]) -> list[dict]:
    rows = []
    width = scene.render.resolution_x * scene.render.resolution_percentage / 100.0
    height = scene.render.resolution_y * scene.render.resolution_percentage / 100.0
    for frame in (0, 1, 2):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        for name, value in sorted(objects.items()):
            world = value.matrix_world.translation.copy()
            ndc = world_to_camera_view(scene, camera, world)
            camera_space = camera.matrix_world.inverted() @ world
            rows.append({
                "frame": frame,
                "object": name,
                "objectLocation": [float(component) for component in value.location],
                "cameraLocation": [float(component) for component in camera.location],
                "screenPx": [float(ndc.x * width), float(ndc.y * height)],
                "cameraDepth": float(-camera_space.z),
            })
    return rows


def main() -> None:
    args = arguments()
    if args.output_exr.exists() or args.report.exists():
        raise RuntimeError("refusing to overwrite D10 development output")
    started = time.monotonic()
    fixture = FIXTURES[args.fixture]

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = f"BFS_D10_{args.fixture}"
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 1
    scene.cycles.seed = 20260827
    scene.cycles.use_animated_seed = False
    scene.cycles.use_adaptive_sampling = False
    scene.cycles.use_denoising = False
    scene.render.resolution_x = 192
    scene.render.resolution_y = 108
    scene.render.resolution_percentage = 100
    scene.render.pixel_aspect_x = 1.0
    scene.render.pixel_aspect_y = 1.0
    scene.render.film_transparent = False
    scene.render.use_motion_blur = False
    scene.render.use_compositing = False
    scene.render.use_sequencer = False
    scene.render.use_stamp = False
    scene.render.use_persistent_data = False
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 4
    scene.frame_start = 0
    scene.frame_end = 2

    world = bpy.data.worlds.new("BFS_D10_WORLD")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0
    scene.world = world

    camera_data = bpy.data.cameras.new("BFS_D10_CAMERA_DATA")
    camera = bpy.data.objects.new("BFS_D10_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    camera.location = (0.0, 0.0, 10.0)
    camera.rotation_euler = (0.0, 0.0, 0.0)
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 8.0
    scene.camera = camera

    objects = {item["name"]: add_plane(item) for item in GEOMETRY}
    if fixture["moverByFrame"] is not None:
        set_linear_location_keys(objects["BFS_MOVER"], fixture["moverByFrame"])
    if fixture["cameraByFrame"] is not None:
        set_linear_location_keys(camera, fixture["cameraByFrame"])

    projections = projection_rows(scene, camera, objects)
    scene.frame_set(1)
    bpy.context.view_layer.update()

    layer = bpy.context.view_layer
    layer.name = "BFS_MASTER"
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

    args.output_exr.parent.mkdir(parents=True, exist_ok=False)
    render_started = time.monotonic()
    outcome = bpy.ops.render.render(write_still=False)
    if "FINISHED" not in outcome:
        raise RuntimeError(f"D10 development render failed: {sorted(outcome)}")
    render_seconds = time.monotonic() - render_started
    bpy.data.images["Render Result"].save_render(str(args.output_exr), scene=scene)
    if not args.output_exr.is_file():
        raise RuntimeError("D10 development EXR absent")

    body = {
        "schemaVersion": "bfs.b52D10PassAdapterDevelopmentSource.v0.1",
        "classification": "EXPLORATORY_NOT_FORMAL_NOT_PROMOTABLE",
        "fixtureId": args.fixture,
        "fixture": fixture,
        "blender": {
            "version": bpy.app.version_string,
            "buildHash": bpy.app.build_hash.decode("ascii"),
            "buildPlatform": bpy.app.build_platform.decode("ascii"),
            "executable": bpy.app.binary_path,
            "executableSha256": sha256_file(Path(bpy.app.binary_path)),
        },
        "render": {
            "engine": scene.render.engine,
            "device": scene.cycles.device,
            "samples": scene.cycles.samples,
            "resolution": [scene.render.resolution_x, scene.render.resolution_y],
            "motionBlur": scene.render.use_motion_blur,
            "passAlphaThreshold": layer.pass_alpha_threshold,
            "passes": {"Combined": layer.use_pass_combined, "Depth": layer.use_pass_z, "Vector": layer.use_pass_vector, "IndexOB": layer.use_pass_object_index},
        },
        "geometry": [
            {"name": value.name, "passIndex": value.pass_index, "location": [float(c) for c in value.location], "scale": [float(c) for c in value.scale]}
            for value in sorted(objects.values(), key=lambda item: item.name)
        ],
        "projections": projections,
        "output": {"uri": str(args.output_exr), "sha256": sha256_file(args.output_exr), "bytes": args.output_exr.stat().st_size},
        "operationCounts": {"blenderProcesses": 1, "blenderRenderCalls": 1, "cyclesRayRenders": 1, "externalAssetsOpened": 0},
        "renderSeconds": round(render_seconds, 6),
        "elapsedSeconds": round(time.monotonic() - started, 6),
        "nonClaims": [
            "This development probe is not preregistered holdout evidence.",
            "The projection oracle is derived through Blender and is suitable only for channel-mapping derivation.",
            "No perspective, transparency, deformation, motion blur, Cryptomatte or production-shot claim is made.",
        ],
    }
    report = {**body, "reportHash": canonical_hash(body)}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(f"BFS_B52_D10_SOURCE_OK fixture={args.fixture} exr={body['output']['sha256']}", flush=True)


if __name__ == "__main__":
    main()
