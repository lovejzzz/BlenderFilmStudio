#!/usr/bin/env python3
"""Render one B52-D12.10-P1 owner-token pass cell in Blender 5.2."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import bpy


SPEC_SHA256 = "7eb76c00baad8cbc4f996ec7a139e6a3cb1fd90c1c02391a531d8c2637abd4be"


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canon(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def arguments() -> argparse.Namespace:
    raw = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--frame", type=int, choices=(0, 1), required=True)
    parser.add_argument("--display-cell", required=True)
    parser.add_argument("--repeat", type=int, choices=(1, 2), required=True)
    parser.add_argument("--output-exr", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--probe-only", action="store_true")
    return parser.parse_args(raw)


def material_for(owner: dict, aov_name: str) -> bpy.types.Material:
    material = bpy.data.materials.new(owner["materialName"])
    material.pass_index = int(owner["materialIndex"])
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    output.name = f"{owner['analyticOwnerId']}_OUTPUT"
    emission = nodes.new("ShaderNodeEmission")
    emission.name = f"{owner['analyticOwnerId']}_EMISSION"
    color = (0.12, 0.32, 0.72, 1.0) if owner["analyticOwnerId"].endswith("BACKGROUND") else (0.84, 0.18, 0.08, 1.0)
    emission.inputs["Color"].default_value = color
    emission.inputs["Strength"].default_value = 1.0
    aov = nodes.new("ShaderNodeOutputAOV")
    aov.name = f"{owner['analyticOwnerId']}_OWNER_AOV"
    aov.aov_name = aov_name
    aov.inputs["Value"].default_value = float(owner["customAovValue"])
    links.new(emission.outputs["Emission"], output.inputs["Surface"])
    return material


def surface(owner: dict, frame: int, aov_name: str) -> bpy.types.Object:
    width, height = map(float, owner["sizeWorld"])
    mesh = bpy.data.meshes.new(f"{owner['objectName']}_MESH")
    mesh.from_pydata(
        [(-width / 2, -height / 2, 0.0), (width / 2, -height / 2, 0.0), (width / 2, height / 2, 0.0), (-width / 2, height / 2, 0.0)],
        [],
        [(0, 1, 2, 3)],
    )
    mesh.update()
    obj = bpy.data.objects.new(owner["objectName"], mesh)
    obj.location = tuple(owner["locationByFrame"][str(frame)])
    obj.pass_index = int(owner["objectIndex"])
    mesh.materials.append(material_for(owner, aov_name))
    bpy.context.scene.collection.objects.link(obj)
    return obj


def setup(spec: dict, frame: int, display: dict, repeat: int):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    contract = spec["sceneContract"]
    scene.name = f"BFS_D1210_P1_F{frame}_{display['id']}_R{repeat}"
    scene.render.engine = contract["engine"]
    scene.cycles.device = contract["device"]
    scene.cycles.samples = int(contract["samples"])
    scene.cycles.seed = int(contract["seed"])
    scene.cycles.use_animated_seed = False
    scene.cycles.use_adaptive_sampling = bool(contract["adaptiveSampling"])
    scene.cycles.use_denoising = bool(contract["denoise"])
    scene.render.resolution_x, scene.render.resolution_y = contract["resolution"]
    scene.render.resolution_percentage = 100
    scene.render.pixel_aspect_x = 1.0
    scene.render.pixel_aspect_y = 1.0
    scene.render.film_transparent = bool(contract["transparentFilm"])
    scene.render.use_motion_blur = False
    scene.render.use_persistent_data = False
    scene.render.use_compositing = False
    scene.render.use_sequencer = False
    scene.render.use_stamp = False
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 4
    scene.display_settings.display_device = display["displayDevice"]
    scene.view_settings.view_transform = display["viewTransform"]
    scene.view_settings.look = display["look"]
    scene.view_settings.exposure = float(display["exposure"])
    scene.view_settings.gamma = float(display["gamma"])

    world = bpy.data.worlds.new("BFS_D1210_P1_WORLD")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0
    scene.world = world

    camera_spec = contract["camera"]
    camera_data = bpy.data.cameras.new("BFS_D1210_P1_CAMERA_DATA")
    camera_data.type = camera_spec["type"]
    camera_data.ortho_scale = float(camera_spec["orthoScaleWorld"])
    camera_data.clip_start = 0.1
    camera_data.clip_end = 100.0
    camera = bpy.data.objects.new("BFS_D1210_P1_CAMERA", camera_data)
    camera.location = tuple(camera_spec["location"])
    camera.rotation_euler = tuple(camera_spec["rotationEuler"])
    scene.collection.objects.link(camera)
    scene.camera = camera

    owners = [surface(owner, frame, contract["customAovName"]) for owner in contract["owners"]]
    layer = bpy.context.view_layer
    layer.name = contract["viewLayerName"]
    layer.use_pass_combined = True
    layer.use_pass_object_index = True
    layer.use_pass_material_index = True
    aov = layer.aovs.add()
    aov.name = contract["customAovName"]
    aov.type = contract["customAovType"]

    output = contract["output"]
    scene.render.image_settings.media_type = "MULTI_LAYER_IMAGE"
    scene.render.image_settings.file_format = output["fileFormat"]
    scene.render.image_settings.color_mode = output["colorMode"]
    scene.render.image_settings.color_depth = output["colorDepth"]
    scene.render.image_settings.exr_codec = output["compression"]
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    return scene, camera, owners, layer, aov


def owner_row(owner: bpy.types.Object) -> dict:
    material = owner.data.materials[0]
    aov_node = next(node for node in material.node_tree.nodes if node.bl_idname == "ShaderNodeOutputAOV")
    return {
        "analyticOwnerId": owner.name,
        "objectIndex": int(owner.pass_index),
        "materialIndex": int(material.pass_index),
        "customAovName": aov_node.aov_name,
        "customAovValue": float(aov_node.inputs["Value"].default_value),
        "location": [float(value) for value in owner.location],
        "vertices": len(owner.data.vertices),
        "polygons": len(owner.data.polygons),
        "materialName": material.name,
        "nodeTypes": sorted(node.bl_idname for node in material.node_tree.nodes),
    }


def main() -> None:
    args = arguments()
    spec = json.loads(args.spec.read_text())
    if sha_file(args.spec) != SPEC_SHA256:
        raise RuntimeError("D12.10-P1 spec identity mismatch")
    display = next((row for row in spec["sceneContract"]["displayCells"] if row["id"] == args.display_cell), None)
    if display is None or args.report.exists() or (args.output_exr and args.output_exr.exists()):
        raise RuntimeError("D12.10-P1 cell or output freshness mismatch")
    if not args.probe_only and args.output_exr is None:
        raise RuntimeError("D12.10-P1 formal EXR path required")
    if sha_file(Path(bpy.app.binary_path)) != spec["runtime"]["blender"]["sha256"] or bpy.app.version_string != spec["runtime"]["blender"]["version"] or bpy.app.build_hash.decode() != spec["runtime"]["blender"]["buildHash"]:
        raise RuntimeError("D12.10-P1 Blender runtime identity mismatch")
    if sha_file(Path(os.environ["OCIO"])) != spec["runtime"]["ocio"]["sha256"]:
        raise RuntimeError("D12.10-P1 OCIO identity mismatch")

    started = time.monotonic()
    scene, camera, owners, layer, aov = setup(spec, args.frame, display, args.repeat)
    owner_rows = [owner_row(owner) for owner in owners]
    body = {
        "schemaVersion": "bfs.blenderOwnerTokenPassSourceReport.v0.1",
        "experimentId": spec["experimentId"],
        "frame": args.frame,
        "displayCell": args.display_cell,
        "repeat": args.repeat,
        "pid": os.getpid(),
        "probeOnly": args.probe_only,
        "runtime": {
            "blender": bpy.app.version_string,
            "buildHash": bpy.app.build_hash.decode(),
            "executableSha256": sha_file(Path(bpy.app.binary_path)),
            "engine": scene.render.engine,
            "device": scene.cycles.device,
            "samples": int(scene.cycles.samples),
            "seed": int(scene.cycles.seed),
            "numpyAvailable": False,
        },
        "scene": {
            "name": scene.name,
            "resolution": [scene.render.resolution_x, scene.render.resolution_y],
            "camera": {
                "type": camera.data.type,
                "orthoScaleWorld": float(camera.data.ortho_scale),
                "location": [float(value) for value in camera.location],
                "rotationEuler": [float(value) for value in camera.rotation_euler],
            },
            "owners": owner_rows,
            "objectCount": len(bpy.data.objects),
            "materialCount": len(bpy.data.materials),
        },
        "display": {
            "displayDevice": scene.display_settings.display_device,
            "viewTransform": scene.view_settings.view_transform,
            "look": scene.view_settings.look,
            "exposure": float(scene.view_settings.exposure),
            "gamma": float(scene.view_settings.gamma),
        },
        "passState": {
            "viewLayer": layer.name,
            "Combined": bool(layer.use_pass_combined),
            "Object Index": bool(layer.use_pass_object_index),
            "Material Index": bool(layer.use_pass_material_index),
            "aovs": [{"name": row.name, "type": row.type, "isValid": bool(row.is_valid)} for row in layer.aovs],
            "registeredAov": {"name": aov.name, "type": aov.type, "isValid": bool(aov.is_valid)},
            "materialPassIndexRange": [int(bpy.types.Material.bl_rna.properties["pass_index"].hard_min), int(bpy.types.Material.bl_rna.properties["pass_index"].hard_max)],
            "viewLayerAovFunctions": sorted(item.identifier for item in layer.aovs.bl_rna.functions),
            "outputAovNodeAvailable": hasattr(bpy.types, "ShaderNodeOutputAOV"),
        },
    }
    render_seconds = 0.0
    if not args.probe_only:
        args.output_exr.parent.mkdir(parents=True, exist_ok=False)
        tick = time.monotonic()
        outcome = bpy.ops.render.render(write_still=False)
        if "FINISHED" not in outcome:
            raise RuntimeError(f"D12.10-P1 render failed: {sorted(outcome)}")
        render_seconds = time.monotonic() - tick
        bpy.data.images["Render Result"].save_render(str(args.output_exr), scene=scene)
        body["output"] = {"uri": str(args.output_exr), "sha256": sha_file(args.output_exr), "bytes": args.output_exr.stat().st_size}
    else:
        body["output"] = None
    body["operationCounts"] = {"blenderProcesses": 1, "blenderRenderCalls": 0 if args.probe_only else 1, "cyclesRayRenders": 0 if args.probe_only else 1, "modelCalls": 0, "networkCalls": 0}
    body["renderSeconds"] = round(render_seconds, 6)
    body["elapsedSeconds"] = round(time.monotonic() - started, 6)
    report = {**body, "reportHash": canon(body)}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D1210_P1_SOURCE_OK frame={args.frame} display={args.display_cell} repeat={args.repeat} probe={args.probe_only}")


if __name__ == "__main__":
    main()
