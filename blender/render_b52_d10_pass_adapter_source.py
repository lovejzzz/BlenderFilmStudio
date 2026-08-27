#!/usr/bin/env python3
"""Render one frozen B52-D10 Blender multipart source cell."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import bpy


SPEC_SHA256 = "147338ae39b9c025a8f2a4921da55b15f8c16f339f34c711502dc3c94ca03566"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def arguments() -> argparse.Namespace:
    raw = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--frame", type=int, choices=(0, 1), required=True)
    parser.add_argument("--repeat", type=int, choices=(1, 2), required=True)
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
    value.pass_index = int(item["passIndex"])
    value.data.materials.append(emission_material(f"{item['name']}_MAT", item["emission"]))
    return value


def set_linear_location_keys(owner: object, values: dict[str, list[float]]) -> None:
    for frame_text, location in values.items():
        owner.location = tuple(location)
        owner.keyframe_insert(data_path="location", frame=int(frame_text))
    action = owner.animation_data.action if owner.animation_data and owner.animation_data.action else None
    if action is None:
        raise RuntimeError("Blender 5.2 failed to create the frozen Action")
    for layer in action.layers:
        for strip in layer.strips:
            for channelbag in strip.channelbags:
                for curve in channelbag.fcurves:
                    for point in curve.keyframe_points:
                        point.interpolation = "LINEAR"


def action_rows(owner: object) -> list[dict]:
    action = owner.animation_data.action if owner.animation_data and owner.animation_data.action else None
    if action is None:
        return []
    rows = []
    for layer_index, layer in enumerate(action.layers):
        for strip_index, strip in enumerate(layer.strips):
            for bag_index, channelbag in enumerate(strip.channelbags):
                for curve in channelbag.fcurves:
                    rows.append({
                        "layerIndex": layer_index,
                        "stripIndex": strip_index,
                        "channelBagIndex": bag_index,
                        "dataPath": curve.data_path,
                        "arrayIndex": curve.array_index,
                        "keyframes": [
                            {"frame": float(point.co.x), "value": float(point.co.y), "interpolation": point.interpolation}
                            for point in curve.keyframe_points
                        ],
                    })
    return sorted(rows, key=lambda row: (row["dataPath"], row["arrayIndex"]))


def main() -> None:
    args = arguments()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    if sha256_file(args.spec) != SPEC_SHA256:
        raise RuntimeError("B52-D10 spec identity mismatch")
    fixture = next((item for item in spec["fixtures"] if item["id"] == args.fixture), None)
    if fixture is None:
        raise RuntimeError("fixture outside frozen D10 roster")
    if args.output_exr.exists() or args.report.exists() or args.output_exr.parent.exists():
        raise RuntimeError("refusing to overwrite D10 source cell")
    if sha256_file(Path(bpy.app.binary_path)) != spec["runtime"]["blender"]["sha256"]:
        raise RuntimeError("Blender executable identity mismatch")
    if bpy.app.version_string != spec["runtime"]["blender"]["version"] or bpy.app.build_hash.decode("ascii") != spec["runtime"]["blender"]["buildHash"]:
        raise RuntimeError("Blender version identity mismatch")
    ocio = Path(os.environ["OCIO"])
    if sha256_file(ocio) != spec["runtime"]["ocio"]["sha256"]:
        raise RuntimeError("OCIO identity mismatch")

    started = time.monotonic()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = f"BFS_D10_{args.fixture}_F{args.frame}_R{args.repeat}"
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

    world = bpy.data.worlds.new("BFS_D10_WORLD")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0
    scene.world = world

    camera_spec = spec["scene"]["camera"]
    camera_data = bpy.data.cameras.new(f"{camera_spec['name']}_DATA")
    camera = bpy.data.objects.new(camera_spec["name"], camera_data)
    scene.collection.objects.link(camera)
    camera.location = tuple(camera_spec["location"])
    camera.rotation_euler = tuple(camera_spec["rotationEuler"])
    camera_data.type = camera_spec["type"]
    camera_data.ortho_scale = camera_spec["orthoScale"]
    scene.camera = camera

    objects = {item["name"]: add_plane(item) for item in spec["scene"]["objects"]}
    if fixture["moverByFrame"] is not None:
        set_linear_location_keys(objects["BFS_MOVER"], fixture["moverByFrame"])
    if fixture["cameraByFrame"] is not None:
        set_linear_location_keys(camera, fixture["cameraByFrame"])
    scene.frame_set(args.frame)
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

    scene_structure = {
        "sceneName": scene.name,
        "frame": scene.frame_current,
        "camera": {"name": camera.name, "location": [float(v) for v in camera.location], "rotationEuler": [float(v) for v in camera.rotation_euler], "type": camera.data.type, "orthoScale": float(camera.data.ortho_scale)},
        "objects": sorted([
            {"name": value.name, "type": value.type, "location": [float(v) for v in value.location], "scale": [float(v) for v in value.scale], "passIndex": int(value.pass_index)}
            for value in objects.values()
        ], key=lambda item: item["name"]),
    }
    animation_structure = {"camera": action_rows(camera), "mover": action_rows(objects["BFS_MOVER"])}

    args.output_exr.parent.mkdir(parents=True, exist_ok=False)
    render_started = time.monotonic()
    outcome = bpy.ops.render.render(write_still=False)
    if "FINISHED" not in outcome:
        raise RuntimeError(f"D10 source render failed: {sorted(outcome)}")
    render_seconds = time.monotonic() - render_started
    bpy.data.images["Render Result"].save_render(str(args.output_exr), scene=scene)
    if not args.output_exr.is_file():
        raise RuntimeError("D10 source EXR absent")

    body = {
        "schemaVersion": "bfs.blenderMultipartTemporalAdapterSourceReport.v0.1",
        "experimentId": spec["experimentId"],
        "fixtureId": args.fixture,
        "frame": args.frame,
        "frameRole": "previous" if args.frame == spec["scene"]["previousFrame"] else "current",
        "repeat": args.repeat,
        "pid": os.getpid(),
        "blender": {"version": bpy.app.version_string, "buildHash": bpy.app.build_hash.decode("ascii"), "buildPlatform": bpy.app.build_platform.decode("ascii"), "executableSha256": sha256_file(Path(bpy.app.binary_path))},
        "runtime": {"engine": scene.render.engine, "device": scene.cycles.device, "samples": scene.cycles.samples, "seed": scene.cycles.seed, "animatedSeed": scene.cycles.use_animated_seed, "adaptiveSampling": scene.cycles.use_adaptive_sampling, "denoising": scene.cycles.use_denoising, "motionBlur": scene.render.use_motion_blur, "persistentData": scene.render.use_persistent_data, "threadsMode": scene.render.threads_mode, "threads": scene.render.threads},
        "fixture": fixture,
        "sceneStructure": scene_structure,
        "animationStructure": animation_structure,
        "passState": {"viewLayer": layer.name, "Combined": layer.use_pass_combined, "Depth": layer.use_pass_z, "Vector": layer.use_pass_vector, "Object Index": layer.use_pass_object_index, "passAlphaThreshold": layer.pass_alpha_threshold},
        "output": {"uri": str(args.output_exr), "sha256": sha256_file(args.output_exr), "bytes": args.output_exr.stat().st_size},
        "operationCounts": {"blenderProcesses": 1, "blenderRenderCalls": 1, "cyclesRayRenders": 1, "sourceBlendFilesOpened": 0, "externalAssetsOpened": 0},
        "renderSeconds": round(render_seconds, 6),
        "elapsedSeconds": round(time.monotonic() - started, 6),
    }
    report = {**body, "reportHash": canonical_hash(body)}
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(f"BFS_B52_D10_SOURCE_OK fixture={args.fixture} frame={args.frame} repeat={args.repeat} exr={body['output']['sha256']}", flush=True)


if __name__ == "__main__":
    main()
