#!/usr/bin/env python3
"""Render one preregistered B52-D5 controlled-motion multipart source."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import bpy


SPEC_SHA256 = "5c2e6564650d6ab6d98f6bb7d91da4304c1cfeece4601871ed74fe5fd5521e01"


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
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--repeat", type=int, required=True)
    parser.add_argument("--output-exr", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args(argv)


def material(name: str, rgba: list[float]):
    value = bpy.data.materials.new(name)
    value.diffuse_color = tuple(rgba)
    value.use_nodes = True
    principled = value.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = tuple(rgba)
    principled.inputs["Roughness"].default_value = 0.65
    return value


def add_plane(item: dict) -> object:
    bpy.ops.mesh.primitive_plane_add(size=2.0, location=tuple(item["location"]))
    value = bpy.context.object
    value.name = item["id"]
    value.scale = tuple(item["scale"])
    value.data.name = f"{item['id']}_MESH"
    value.data.materials.append(material(f"{item['id']}_MAT", item["baseColor"]))
    return value


def action_curves(owner: object) -> list[dict]:
    action = owner.animation_data.action if owner.animation_data and owner.animation_data.action else None
    rows: list[dict] = []
    if action is None:
        return rows
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
                            {
                                "frame": float(point.co.x),
                                "value": float(point.co.y),
                                "interpolation": point.interpolation,
                            }
                            for point in curve.keyframe_points
                        ],
                    })
    return rows


def set_linear_keyframes(owner: object, values: dict[str, float]) -> None:
    for frame_text, value in values.items():
        owner.location.x = float(value)
        owner.keyframe_insert(data_path="location", frame=int(frame_text), index=0)
    action = owner.animation_data.action if owner.animation_data and owner.animation_data.action else None
    if action is None:
        raise RuntimeError("Blender 5.2 failed to create a layered Action")
    for layer in action.layers:
        for strip in layer.strips:
            for channelbag in strip.channelbags:
                for curve in channelbag.fcurves:
                    for point in curve.keyframe_points:
                        point.interpolation = "LINEAR"


def main() -> None:
    args = arguments()
    started = time.monotonic()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    if sha256_file(args.spec) != SPEC_SHA256:
        raise RuntimeError("B52-D5 spec hash mismatch")
    fixture = next((item for item in spec["fixtures"] if item["id"] == args.fixture), None)
    if fixture is None or args.repeat not in (1, 2):
        raise RuntimeError("fixture or repeat outside preregistered source matrix")
    if args.output_exr.exists() or args.report.exists():
        raise RuntimeError("refusing to overwrite B52-D5 source output")
    ocio = Path(os.environ["OCIO"])
    executable = Path(bpy.app.binary_path)
    if sha256_file(ocio) != spec["runtime"]["ocio"]["sha256"]:
        raise RuntimeError("OCIO identity mismatch inside Blender")
    if sha256_file(executable) != spec["runtime"]["blenderExecutableSha256"]:
        raise RuntimeError("Blender executable identity mismatch inside Blender")
    if bpy.app.version_string != spec["runtime"]["version"] or bpy.app.build_hash.decode("ascii") != spec["runtime"]["buildHash"]:
        raise RuntimeError("Blender runtime version mismatch")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = f"BFS_D5_{args.fixture}"
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
    scene.render.pixel_aspect_x = 1.0
    scene.render.pixel_aspect_y = 1.0
    scene.render.film_transparent = False
    scene.render.use_motion_blur = render["motionBlur"]
    scene.render.use_persistent_data = render["persistentData"]
    scene.render.use_compositing = False
    scene.render.use_sequencer = False
    scene.render.use_stamp = False
    scene.render.threads_mode = render["threadsMode"]
    scene.render.threads = render["threads"]
    scene.frame_start, scene.frame_end = spec["fixtureCommon"]["frameRange"]

    common = spec["fixtureCommon"]
    world = bpy.data.worlds.new("BFS_D5_WORLD")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = tuple(common["world"]["color"])
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = common["world"]["strength"]
    scene.world = world

    camera_spec = common["camera"]
    camera_data = bpy.data.cameras.new("BFS_D5_CAMERA_DATA")
    camera = bpy.data.objects.new("BFS_D5_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    camera.location = tuple(camera_spec["location"])
    camera.rotation_euler = tuple(camera_spec["rotationEuler"])
    camera_data.type = camera_spec["type"]
    camera_data.ortho_scale = camera_spec["orthoScale"]
    scene.camera = camera

    light_spec = common["keyLight"]
    light_data = bpy.data.lights.new("BFS_D5_KEY_DATA", light_spec["type"])
    light_data.energy = light_spec["energy"]
    light_data.shape = light_spec["shape"]
    light_data.size = light_spec["size"]
    light = bpy.data.objects.new("BFS_D5_KEY", light_data)
    scene.collection.objects.link(light)
    light.location = tuple(light_spec["location"])

    objects = {item["id"]: add_plane(item) for item in common["geometry"]}
    if fixture["moverXByFrame"] is not None:
        set_linear_keyframes(objects["BFS_MOVER"], fixture["moverXByFrame"])
    if fixture["cameraXByFrame"] is not None:
        set_linear_keyframes(camera, fixture["cameraXByFrame"])
    scene.frame_set(common["evaluationFrame"])

    layer = bpy.context.view_layer
    layer.name = "BFS_MASTER"
    layer.use_pass_combined = True
    layer.use_pass_z = True
    layer.use_pass_normal = True
    layer.use_pass_vector = True
    layer.use_pass_cryptomatte_object = True
    layer.use_pass_cryptomatte_material = False
    layer.use_pass_cryptomatte_asset = False
    layer.pass_cryptomatte_depth = 6
    layer.cycles.pass_debug_sample_count = True
    scene.render.image_settings.media_type = "MULTI_LAYER_IMAGE"
    scene.render.image_settings.file_format = render["fileFormat"]
    scene.render.image_settings.color_mode = render["colorMode"]
    scene.render.image_settings.color_depth = render["colorDepth"]
    scene.render.image_settings.exr_codec = render["exrCodec"]

    fixture_structure = {
        "sceneName": scene.name,
        "objects": sorted([
            {
                "name": value.name,
                "type": value.type,
                "location": [round(float(component), 6) for component in value.location],
                "scale": [round(float(component), 6) for component in value.scale],
            }
            for value in [*objects.values(), camera, light]
        ], key=lambda item: item["name"]),
        "moverAction": action_curves(objects["BFS_MOVER"]),
        "cameraAction": action_curves(camera),
    }
    args.output_exr.parent.mkdir(parents=True, exist_ok=False)
    render_started = time.monotonic()
    outcome = bpy.ops.render.render(write_still=False)
    if "FINISHED" not in outcome:
        raise RuntimeError(f"Cycles source render failed: {sorted(outcome)}")
    render_seconds = time.monotonic() - render_started
    bpy.data.images["Render Result"].save_render(str(args.output_exr), scene=scene)
    if not args.output_exr.is_file():
        raise RuntimeError("B52-D5 source EXR absent")

    body = {
        "schemaVersion": "bfs.controlledMotionVectorBlurSourceReport.v0.1",
        "experimentId": spec["experimentId"],
        "fixtureId": args.fixture,
        "repeat": args.repeat,
        "pid": os.getpid(),
        "blender": {"version": bpy.app.version_string, "buildHash": bpy.app.build_hash.decode("ascii"), "buildPlatform": bpy.app.build_platform.decode("ascii")},
        "runtime": {
            "engine": scene.render.engine, "device": scene.cycles.device, "samples": scene.cycles.samples,
            "seed": scene.cycles.seed, "animatedSeed": scene.cycles.use_animated_seed,
            "adaptiveSampling": scene.cycles.use_adaptive_sampling, "denoising": scene.cycles.use_denoising,
            "motionBlur": scene.render.use_motion_blur, "persistentData": scene.render.use_persistent_data,
            "threadsMode": scene.render.threads_mode, "threads": scene.render.threads,
        },
        "fixture": fixture,
        "fixtureStructure": fixture_structure,
        "passState": {
            "viewLayer": layer.name, "Combined": layer.use_pass_combined, "Depth": layer.use_pass_z,
            "Normal": layer.use_pass_normal, "Vector": layer.use_pass_vector,
            "CryptoObject": layer.use_pass_cryptomatte_object, "cryptomatteDepth": layer.pass_cryptomatte_depth,
            "sampleCount": bool(layer.cycles.pass_debug_sample_count),
        },
        "output": {"uri": str(args.output_exr), "sha256": sha256_file(args.output_exr), "bytes": args.output_exr.stat().st_size},
        "operationCounts": {"blenderProcesses": 1, "blenderRenderCalls": 1, "cyclesRayRenders": 1, "sourceBlendFilesOpened": 0, "externalAssetsOpened": 0},
        "renderSeconds": round(render_seconds, 6),
        "elapsedSeconds": round(time.monotonic() - started, 6),
    }
    report = {**body, "reportHash": canonical_hash(body)}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(f"BFS_B52_D5_SOURCE_OK fixture={args.fixture} repeat={args.repeat} output={body['output']['sha256']}", flush=True)


if __name__ == "__main__":
    main()
