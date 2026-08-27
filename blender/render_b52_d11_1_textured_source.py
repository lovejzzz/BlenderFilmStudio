#!/usr/bin/env python3
"""Render one preregistered B52-D11.1 real-textured multipart source cell."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import sys
import time
from pathlib import Path

import bpy


SPEC_SHA256 = "c4cb343672f53660d7c4ab69ccd489e00bb211e4aa1f489429f7a626ee48c42a"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", value))[0]


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


def texture_pair(spec: dict, label: str) -> tuple[list[float], list[float]]:
    materials = spec["scene"]["textureConstruction"]["materials"]
    mapping = {
        "BACKGROUND_CHECKER": ("BACKGROUND_A", "BACKGROUND_B"),
        "FOREGROUND_CHECKER": ("FOREGROUND_A", "FOREGROUND_B"),
        "STATIC_CHECKER": ("STATIC_A", "STATIC_B"),
    }
    first, second = mapping[label]
    return materials[first], materials[second]


def add_tessellated_surface(spec: dict, item: dict):
    width, height = (float(v) for v in item["sizeWorld"])
    cell = spec["scene"]["textureConstruction"][
        "backgroundCellWorld" if item["texture"] == "BACKGROUND_CHECKER" else "foregroundCellWorld"
    ]
    columns = round(width / float(cell[0]))
    rows = round(height / float(cell[1]))
    if abs(columns * float(cell[0]) - width) > 1e-9 or abs(rows * float(cell[1]) - height) > 1e-9:
        raise RuntimeError(f"non-integral D11 texture grid for {item['name']}")
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
    mesh = bpy.data.meshes.new(f"{item['name']}_MESH")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    owner = bpy.data.objects.new(item["name"], mesh)
    bpy.context.scene.collection.objects.link(owner)
    owner.location = tuple(item["location"] if "location" in item else item["locationByFrame"]["0"])
    owner.pass_index = int(item["passIndex"])
    colors = texture_pair(spec, item["texture"])
    for index, color in enumerate(colors):
        mesh.materials.append(emission_material(f"{item['name']}_MAT_{index}", color))
    for index, polygon in enumerate(mesh.polygons):
        row, column = divmod(index, columns)
        polygon.material_index = (row + column) % 2
    return owner


def set_linear_location_keys(owner: object, values: dict[str, list[float]]) -> None:
    for frame_text, location in values.items():
        owner.location = tuple(location)
        owner.keyframe_insert(data_path="location", frame=int(frame_text))
    action = owner.animation_data.action if owner.animation_data and owner.animation_data.action else None
    if action is None:
        raise RuntimeError("Blender 5.2 failed to create the frozen D11 Action")
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
                    rows.append(
                        {
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
                        }
                    )
    return sorted(rows, key=lambda row: (row["dataPath"], row["arrayIndex"]))


def mesh_row(owner: object) -> dict:
    mesh = owner.data
    return {
        "name": owner.name,
        "type": owner.type,
        "location": [float(v) for v in owner.location],
        "sizeWorld": [f32(owner.dimensions.x), f32(owner.dimensions.y)],
        "passIndex": int(owner.pass_index),
        "mesh": {
            "name": mesh.name,
            "vertices": len(mesh.vertices),
            "edges": len(mesh.edges),
            "polygons": len(mesh.polygons),
            "polygonMaterialIndices": [int(p.material_index) for p in mesh.polygons],
        },
        "materials": [
            {
                "name": material.name,
                "emissionColor": [float(v) for v in material.node_tree.nodes.get("Emission").inputs["Color"].default_value],
                "emissionStrength": float(material.node_tree.nodes.get("Emission").inputs["Strength"].default_value),
            }
            for material in mesh.materials
        ],
    }


def main() -> None:
    args = arguments()
    spec = json.loads(args.spec.read_text())
    if sha256_file(args.spec) != SPEC_SHA256:
        raise RuntimeError("B52-D11.1 spec identity mismatch")
    fixture = next((item for item in spec["fixtures"] if item["id"] == args.fixture), None)
    if fixture is None:
        raise RuntimeError("fixture outside frozen D11 roster")
    if args.output_exr.exists() or args.report.exists() or args.output_exr.parent.exists():
        raise RuntimeError("refusing to overwrite D11 source cell")
    if sha256_file(Path(bpy.app.binary_path)) != spec["runtime"]["blender"]["sha256"]:
        raise RuntimeError("Blender executable identity mismatch")
    if bpy.app.version_string != spec["runtime"]["blender"]["version"] or bpy.app.build_hash.decode() != spec["runtime"]["blender"]["buildHash"]:
        raise RuntimeError("Blender version identity mismatch")
    if sha256_file(Path(os.environ["OCIO"])) != spec["runtime"]["ocio"]["sha256"]:
        raise RuntimeError("OCIO identity mismatch")

    started = time.monotonic()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = f"BFS_D111_{args.fixture}_F{args.frame}_R{args.repeat}"
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

    world = bpy.data.worlds.new("BFS_D111_WORLD")
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
    camera_data.dof.use_dof = render["depthOfField"]
    scene.camera = camera

    objects = {item["name"]: add_tessellated_surface(spec, item) for item in fixture["objects"]}
    for item in fixture["objects"]:
        if "locationByFrame" in item:
            set_linear_location_keys(objects[item["name"]], item["locationByFrame"])
    if "cameraByFrame" in fixture:
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
        "camera": {
            "name": camera.name,
            "location": [float(v) for v in camera.location],
            "rotationEuler": [float(v) for v in camera.rotation_euler],
            "type": camera.data.type,
            "orthoScale": float(camera.data.ortho_scale),
        },
        "objects": sorted([mesh_row(value) for value in objects.values()], key=lambda row: row["name"]),
    }
    animation_structure = {
        "camera": action_rows(camera),
        "objects": {name: action_rows(owner) for name, owner in sorted(objects.items())},
    }

    args.output_exr.parent.mkdir(parents=True, exist_ok=False)
    render_started = time.monotonic()
    outcome = bpy.ops.render.render(write_still=False)
    if "FINISHED" not in outcome:
        raise RuntimeError(f"D11 source render failed: {sorted(outcome)}")
    render_seconds = time.monotonic() - render_started
    bpy.data.images["Render Result"].save_render(str(args.output_exr), scene=scene)
    if not args.output_exr.is_file():
        raise RuntimeError("D11 source EXR absent")

    body = {
        "schemaVersion": "bfs.blenderNearestIntegerTemporalRecoverySourceReport.v0.1",
        "experimentId": spec["experimentId"],
        "fixtureId": args.fixture,
        "frame": args.frame,
        "frameRole": "previous" if args.frame == spec["scene"]["previousFrame"] else "current",
        "repeat": args.repeat,
        "pid": os.getpid(),
        "blender": {
            "version": bpy.app.version_string,
            "buildHash": bpy.app.build_hash.decode(),
            "buildPlatform": bpy.app.build_platform.decode(),
            "executableSha256": sha256_file(Path(bpy.app.binary_path)),
        },
        "runtime": {
            "engine": scene.render.engine,
            "device": scene.cycles.device,
            "samples": scene.cycles.samples,
            "seed": scene.cycles.seed,
            "animatedSeed": scene.cycles.use_animated_seed,
            "adaptiveSampling": scene.cycles.use_adaptive_sampling,
            "denoising": scene.cycles.use_denoising,
            "motionBlur": scene.render.use_motion_blur,
            "depthOfField": camera.data.dof.use_dof,
            "persistentData": scene.render.use_persistent_data,
            "threadsMode": scene.render.threads_mode,
            "threads": scene.render.threads,
        },
        "fixture": fixture,
        "sceneStructure": scene_structure,
        "animationStructure": animation_structure,
        "passState": {
            "viewLayer": layer.name,
            "Combined": layer.use_pass_combined,
            "Depth": layer.use_pass_z,
            "Vector": layer.use_pass_vector,
            "Object Index": layer.use_pass_object_index,
            "passAlphaThreshold": layer.pass_alpha_threshold,
        },
        "output": {"uri": str(args.output_exr), "sha256": sha256_file(args.output_exr), "bytes": args.output_exr.stat().st_size},
        "operationCounts": {
            "blenderProcesses": 1,
            "blenderRenderCalls": 1,
            "cyclesRayRenders": 1,
            "sourceBlendFilesOpened": 0,
            "externalAssetsOpened": 0,
        },
        "renderSeconds": round(render_seconds, 6),
        "elapsedSeconds": round(time.monotonic() - started, 6),
    }
    report = {**body, "reportHash": canonical_hash(body)}
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D11_1_SOURCE_OK fixture={args.fixture} frame={args.frame} repeat={args.repeat} exr={body['output']['sha256']}", flush=True)


if __name__ == "__main__":
    main()
