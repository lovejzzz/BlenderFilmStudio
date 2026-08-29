"""Independent zero-render Blender audit for B62-P0-E1.

This file intentionally imports no B62 generator, renderer, runner, or Node
auditor.  It reopens the binary evidence and rederives the semantic checks.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys

import bpy
from bpy_extras import anim_utils
import numpy
import OpenImageIO as oiio


REQUIRED_BONES = [
    "root", "pelvis", "spine", "chest", "neck", "head",
    "upper_arm.L", "forearm.L", "hand.L", "upper_arm.R", "forearm.R", "hand.R",
    "thigh.L", "shin.L", "foot.L", "thigh.R", "shin.R", "foot.R",
]
ASSETS = ["CHAR_B62_GUARDIAN", "SET_B62_OBSERVATORY", "PROP_B62_CONSOLE_CORE"]
CALIBRATION = [("WIDE_APPROACH", 48), ("MEDIUM_CONTACT", 144), ("CLOSE_REFLECTION", 240)]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--formal-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def normalize_numbers(value: object) -> object:
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return int(value)
    if isinstance(value, list):
        return [normalize_numbers(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize_numbers(item) for key, item in value.items()}
    return value


def canonical(value: object) -> bytes:
    return json.dumps(normalize_numbers(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def valid_self_hash(document: dict, field: str) -> bool:
    return document.get(field) == sha256_bytes(canonical({key: value for key, value in document.items() if key != field}))


def write_hashed(path: Path, body: dict, field: str) -> dict:
    record = {**body, field: sha256_bytes(canonical(body))}
    with path.open("x", encoding="utf-8") as handle:
        json.dump(record, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    return record


def png_size(path: Path) -> tuple[int, int]:
    header = path.read_bytes()[:24]
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        return 0, 0
    return int.from_bytes(header[16:20], "big"), int.from_bytes(header[20:24], "big")


def decode_combined(path: Path) -> dict:
    image_input = oiio.ImageInput.open(str(path))
    if image_input is None:
        raise RuntimeError(f"Could not open EXR: {path}")
    try:
        candidates = []
        subimage = 0
        while image_input.seek_subimage(subimage, 0):
            spec = image_input.spec()
            names = list(spec.channelnames)
            positions = {name: index for index, name in enumerate(names)}
            for name in names:
                if name.endswith(".R") and name[:-2].split(".")[-1] == "Combined":
                    prefix = name[:-2]
                    wanted = [f"{prefix}.{channel}" for channel in "RGBA"]
                    if all(channel in positions for channel in wanted):
                        candidates.append((subimage, spec.width, spec.height, spec.nchannels, [positions[channel] for channel in wanted]))
            subimage += 1
        if len(candidates) != 1:
            raise RuntimeError(f"Combined channel candidate count is {len(candidates)}")
        subimage, width, height, channels, indices = candidates[0]
        pixels = image_input.read_image(subimage, 0, 0, channels, oiio.FLOAT)
        array = numpy.asarray(pixels)
        values = numpy.ascontiguousarray(array[..., indices], dtype=numpy.dtype("<f4"))
        finite = numpy.isfinite(values)
        minima = [float(value) for value in values.min(axis=(0, 1))]
        maxima = [float(value) for value in values.max(axis=(0, 1))]
        return {
            "width": width,
            "height": height,
            "pixelFormat": str(image_input.spec().format),
            "compression": image_input.spec().getattribute("compression"),
            "sha256": sha256_bytes(values.tobytes(order="C")),
            "nonFiniteCount": int(values.size - finite.sum()),
            "rgbDynamicRange": max(maxima[:3]) - min(minima[:3]),
        }
    finally:
        image_input.close()


def animation_driver_count() -> int:
    count = 0
    collections = [
        bpy.data.objects, bpy.data.meshes, bpy.data.materials, bpy.data.node_groups,
        bpy.data.armatures, bpy.data.cameras, bpy.data.lights, bpy.data.worlds,
    ]
    for datablocks in collections:
        for datablock in datablocks:
            animation = getattr(datablock, "animation_data", None)
            if animation:
                count += len(animation.drivers)
    return count


def original_name(name: str) -> str:
    return re.sub(r"\.\d{3}$", "", name)


def mesh_signature(obj: bpy.types.Object) -> dict:
    return {
        "vertices": [[round(float(component), 7) for component in vertex.co] for vertex in obj.data.vertices],
        "polygons": [list(polygon.vertices) for polygon in obj.data.polygons],
        "materials": [original_name(material.name) for material in obj.data.materials],
    }


def socket_default(socket: bpy.types.NodeSocket) -> object:
    if not hasattr(socket, "default_value"):
        return None
    value = socket.default_value
    if isinstance(value, (bool, int, float, str)):
        return value
    try:
        return [float(component) for component in value]
    except (TypeError, ValueError):
        return str(value)


def material_signature(mat: bpy.types.Material) -> dict:
    if not mat.use_nodes or mat.node_tree is None:
        return {"useNodes": False, "surfaceRenderMethod": mat.surface_render_method}
    nodes = []
    for node in sorted(mat.node_tree.nodes, key=lambda item: item.name):
        nodes.append({
            "name": node.name,
            "type": node.bl_idname,
            "inputs": [{"name": socket.name, "default": socket_default(socket)} for socket in node.inputs if not socket.is_linked],
        })
    links = sorted({
        (link.from_node.name, link.from_socket.name, link.to_node.name, link.to_socket.name)
        for link in mat.node_tree.links
    })
    return {"useNodes": True, "surfaceRenderMethod": mat.surface_render_method, "nodes": nodes, "links": [list(row) for row in links]}


def collection_manifest(collection: bpy.types.Collection) -> dict:
    objects = []
    mesh_hashes = {}
    for obj in sorted(collection.all_objects, key=lambda item: original_name(item.name)):
        name = original_name(obj.name)
        objects.append({
            "name": name,
            "type": obj.type,
            "parent": original_name(obj.parent.name) if obj.parent else None,
            "parentType": obj.parent_type,
            "parentBone": obj.parent_bone,
            "constraints": [constraint.type for constraint in obj.constraints],
            "modifiers": [modifier.type for modifier in obj.modifiers],
        })
        if obj.type == "MESH":
            mesh_hashes[name] = sha256_bytes(canonical(mesh_signature(obj)))
    used_materials = sorted({material for obj in collection.all_objects if obj.type == "MESH" for material in obj.data.materials}, key=lambda item: original_name(item.name))
    manifest = {
        "collection": original_name(collection.name),
        "objects": objects,
        "meshTopologyHashes": mesh_hashes,
        "materials": [original_name(material.name) for material in used_materials],
        "materialParameterHashes": {original_name(material.name): sha256_bytes(canonical(material_signature(material))) for material in used_materials},
    }
    manifest["identityHash"] = sha256_bytes(canonical(manifest))
    return manifest


def rig_manifest(rig: bpy.types.Object) -> dict:
    bones = [{
        "name": bone.name,
        "parent": bone.parent.name if bone.parent else None,
        "head": [round(float(value), 7) for value in bone.head_local],
        "tail": [round(float(value), 7) for value in bone.tail_local],
    } for bone in sorted(rig.data.bones, key=lambda item: item.name)]
    return {"object": original_name(rig.name), "bones": bones, "restPoseHash": sha256_bytes(canonical(bones))}


def action_manifest(action: bpy.types.Action) -> dict:
    slots = []
    for slot in action.slots:
        channelbag = anim_utils.action_get_channelbag_for_slot(action, slot)
        curves = []
        if channelbag:
            for curve in sorted(channelbag.fcurves, key=lambda item: (item.data_path, item.array_index)):
                curves.append({
                    "dataPath": curve.data_path,
                    "arrayIndex": curve.array_index,
                    "keys": [{"co": [round(float(value), 7) for value in point.co], "interpolation": point.interpolation} for point in curve.keyframe_points],
                })
        slots.append({"identifier": slot.identifier, "targetIdType": slot.target_id_type, "curves": curves})
    body = {"name": original_name(action.name), "slots": slots}
    return {**body, "actionKeyHash": sha256_bytes(canonical(body))}


def inspect_motion_library(path: Path, expected: dict) -> dict:
    before_actions = set(bpy.data.actions)
    with bpy.data.libraries.load(str(path), link=False, recursive=True) as (source, target):
        if source.actions != ["B62_GUARDIAN_PERFORMANCE"]:
            raise RuntimeError(f"Motion action roster drift: {source.actions}")
        target.actions = ["B62_GUARDIAN_PERFORMANCE"]
    action = target.actions[0]
    derived = action_manifest(action)
    result = {
        "sha256": sha256_file(path),
        "derived": derived,
        "matchesGeneration": derived == expected,
    }
    for item in set(bpy.data.actions) - before_actions:
        bpy.data.actions.remove(item)
    return result


def inspect_asset_library(path: Path, asset_id: str, expected_manifest: dict) -> dict:
    before_objects = set(bpy.data.objects)
    before_collections = set(bpy.data.collections)
    before_texts = set(bpy.data.texts)
    before_libraries = set(bpy.data.libraries)
    with bpy.data.libraries.load(str(path), link=False, recursive=True) as (source, target):
        if source.collections != [asset_id]:
            raise RuntimeError(f"Asset collection roster drift for {asset_id}: {source.collections}")
        target.collections = [asset_id]
    collection = target.collections[0]
    objects = sorted(collection.all_objects, key=lambda item: item.name)
    derived_manifest = collection_manifest(collection)
    armatures = [obj for obj in objects if obj.type == "ARMATURE"]
    derived_rig = rig_manifest(armatures[0]) if len(armatures) == 1 else None
    findings = []
    for obj in objects:
        if obj.constraints:
            findings.append(f"{obj.name}:OBJECT_CONSTRAINTS")
        if obj.modifiers:
            findings.append(f"{obj.name}:MODIFIERS")
        if obj.rigid_body or obj.rigid_body_constraint:
            findings.append(f"{obj.name}:RIGID_BODY")
        animation = getattr(obj, "animation_data", None)
        if animation and animation.drivers:
            findings.append(f"{obj.name}:DRIVERS")
        if obj.type == "ARMATURE":
            for bone in obj.pose.bones:
                if bone.constraints:
                    findings.append(f"{obj.name}.{bone.name}:POSE_CONSTRAINTS")
    new_texts = set(bpy.data.texts) - before_texts
    new_libraries = set(bpy.data.libraries) - before_libraries
    if new_texts:
        findings.append("TEXT_DATABLOCK")
    if new_libraries:
        findings.append("EXTERNAL_LIBRARY")
    result = {
        "assetId": asset_id,
        "sha256": sha256_file(path),
        "objectCount": len(objects),
        "objects": [{"name": obj.name, "type": obj.type} for obj in objects],
        "findings": sorted(findings),
        "derivedManifest": derived_manifest,
        "identityMatchesGeneration": derived_manifest.get("identityHash") == expected_manifest.get("identityHash"),
        "topologyMatchesGeneration": derived_manifest.get("meshTopologyHashes") == expected_manifest.get("meshTopologyHashes"),
        "rig": derived_rig,
        "rigMatchesGeneration": derived_rig == expected_manifest.get("rig") if asset_id == "CHAR_B62_GUARDIAN" else derived_rig is None,
    }
    for obj in set(bpy.data.objects) - before_objects:
        bpy.data.objects.remove(obj, do_unlink=True)
    for collection_item in set(bpy.data.collections) - before_collections:
        bpy.data.collections.remove(collection_item)
    return result


def main() -> None:
    args = parse_args()
    repository_root = args.repository_root.resolve(strict=True)
    formal_root = args.formal_root.resolve(strict=True)
    output = args.output.resolve()
    if output.exists():
        raise RuntimeError("Audit output already exists")
    if Path(bpy.data.filepath).resolve() != (formal_root / "scene/B62_PHASE0_MASTER.blend").resolve():
        raise RuntimeError("Independent auditor did not load the B62 master")
    generation_path = formal_root / "reports/generation-report.json"
    generation = json.loads(generation_path.read_text(encoding="utf-8"))
    generation_valid = valid_self_hash(generation, "reportHash")
    scene = bpy.data.scenes.get("B62_PHASE0_MASTER")
    if scene is None:
        raise RuntimeError("Master scene is absent")

    marker_rows = [{"name": marker.name, "frame": marker.frame, "camera": marker.camera.name if marker.camera else None, "lens": marker.camera.data.lens if marker.camera else None} for marker in scene.timeline_markers]
    expected_markers = [
        {"name": "SHOT_WIDE_APPROACH", "frame": 1, "camera": "CAM_WIDE_APPROACH", "lens": 35.0},
        {"name": "SHOT_MEDIUM_CONTACT", "frame": 97, "camera": "CAM_MEDIUM_CONTACT", "lens": 65.0},
        {"name": "SHOT_CLOSE_REFLECTION", "frame": 193, "camera": "CAM_CLOSE_REFLECTION", "lens": 100.0},
    ]
    rig = bpy.data.objects.get("RIG_B62_GUARDIAN")
    bones = sorted(bone.name for bone in rig.data.bones) if rig and rig.type == "ARMATURE" else []
    required_objects = [
        "B62_HELMET", "B62_VISOR", "B62_EYE_SLIT", "B62_CHEST_PLATE", "B62_SHOULDER_L", "B62_SHOULDER_R",
        "B62_HAND_L", "B62_HAND_R", "B62_FOOT_L", "B62_FOOT_R", "B62_CORE", "B62_CONSOLE_SURFACE",
    ]
    required_materials = ["MAT_B62_ARMOR", "MAT_B62_VISOR", "MAT_B62_EYE", "MAT_B62_CORE", "MAT_B62_VOLUME"]
    expected_camera_ranges = {
        "CAM_WIDE_APPROACH": (1.0, 96.0),
        "CAM_MEDIUM_CONTACT": (97.0, 192.0),
        "CAM_CLOSE_REFLECTION": (193.0, 288.0),
    }
    camera_animation = {}
    for name, expected_range in expected_camera_ranges.items():
        camera = bpy.data.objects.get(name)
        action = camera.animation_data.action if camera and camera.animation_data else None
        camera_animation[name] = {
            "hasAction": action is not None,
            "frameRange": [float(value) for value in action.frame_range] if action else None,
            "expectedFrameRange": list(expected_range),
        }

    hand = bpy.data.objects.get("HAND_R_SOCKET")
    touch = bpy.data.objects.get("CONSOLE_TOUCH")
    core = bpy.data.objects.get("B62_CORE")
    warm = bpy.data.objects.get("LIGHT_CORE_WARM")
    if any(item is None for item in (hand, touch, core, warm)):
        raise RuntimeError("Contact or core state objects are absent")
    state_rows = []
    for frame in (138, 143, 144, 150, 288):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        state_rows.append({
            "frame": frame,
            "activation": float(core["bfs_core_activation"]),
            "warmEnergy": float(warm.data.energy),
            "contactDistanceM": float((hand.matrix_world.translation - touch.matrix_world.translation).length),
        })
    contact_distance = next(row["contactDistanceM"] for row in state_rows if row["frame"] == 144)

    asset_rows = []
    for asset_id in ASSETS:
        asset_path = formal_root / f"assets/{asset_id}.blend"
        asset_rows.append(inspect_asset_library(asset_path, asset_id, generation["manifests"][asset_id]))
    motion_row = inspect_motion_library(formal_root / "motion/B62_GUARDIAN_PERFORMANCE.blend", generation["motionAction"])

    animatic_dir = formal_root / "animatic"
    animatic_files = sorted(animatic_dir.glob("frame-*.png"))
    animatic_report_path = animatic_dir / "animatic-render-report.json"
    animatic_report = json.loads(animatic_report_path.read_text(encoding="utf-8")) if animatic_report_path.is_file() else {}
    animatic_roster = [path.name for path in animatic_files]
    expected_roster = [f"frame-{frame:04d}.png" for frame in range(1, 289)]
    png_dimensions_exact = len(animatic_files) == 288 and all(png_size(path) == (640, 360) for path in animatic_files)

    calibration_rows = []
    for shot, frame in CALIBRATION:
        stem = f"{shot}-{frame:04d}"
        exr = formal_root / f"calibration/{stem}.exr"
        png = formal_root / f"calibration/{stem}.png"
        report_path = formal_root / f"calibration/{stem}.pixel.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        decoded = decode_combined(exr)
        calibration_rows.append({
            "shot": shot,
            "frame": frame,
            "reportSelfHashValid": valid_self_hash(report, "reportHash"),
            "exrShaExact": report.get("exr", {}).get("sha256") == sha256_file(exr),
            "pngShaExact": report.get("png", {}).get("sha256") == sha256_file(png),
            "pngDimensionsExact": png_size(png) == (1920, 1080),
            "decoded": decoded,
            "decodedMatchesReport": decoded["sha256"] == report.get("decodedCombined", {}).get("sha256"),
            "settings": report.get("settings"),
        })

    checks = {
        "generationReportSelfHashValid": generation_valid,
        "masterTimelineExact": scene.frame_start == 1 and scene.frame_end == 288 and scene.render.fps == 24,
        "markerCameraLensExact": marker_rows == expected_markers,
        "cameraTransformsAnimatedExact": all(row["hasAction"] and row["frameRange"] == row["expectedFrameRange"] for row in camera_animation.values()),
        "requiredBonesExact": all(name in bones for name in REQUIRED_BONES) and len(bones) == len(REQUIRED_BONES),
        "requiredObjectsPresent": all(bpy.data.objects.get(name) is not None for name in required_objects),
        "requiredMaterialsPresent": all(bpy.data.materials.get(name) is not None for name in required_materials),
        "masterTextBlocksZero": len(bpy.data.texts) == 0,
        "masterDriversZero": animation_driver_count() == 0,
        "masterExternalLibrariesZero": len(bpy.data.libraries) == 0,
        "assetLibrariesSafe": all(len(row["findings"]) == 0 for row in asset_rows),
        "assetIdentityAndTopologyExact": all(row["identityMatchesGeneration"] and row["topologyMatchesGeneration"] and row["rigMatchesGeneration"] for row in asset_rows),
        "motionActionKeyDigestExact": motion_row["matchesGeneration"],
        "rightHandContactWithinTwoCm": contact_distance <= 0.02,
        "coreCausalStateExact": [row["activation"] for row in state_rows] == [0.0, 0.0, 0.5, 1.0, 1.0],
        "warmLightMonotonicAndHeld": state_rows[0]["warmEnergy"] == state_rows[1]["warmEnergy"] == 0 and 0 < state_rows[2]["warmEnergy"] < state_rows[3]["warmEnergy"] == state_rows[4]["warmEnergy"],
        "animaticRosterExact": animatic_roster == expected_roster,
        "animaticPngDimensionsExact": png_dimensions_exact,
        "animaticReportSelfHashValid": valid_self_hash(animatic_report, "reportHash"),
        "calibrationTriplesExact": len(calibration_rows) == 3 and all(row["reportSelfHashValid"] and row["exrShaExact"] and row["pngShaExact"] and row["pngDimensionsExact"] and row["decodedMatchesReport"] for row in calibration_rows),
        "calibrationPixelsFiniteDynamic": all(row["decoded"]["width"] == 1920 and row["decoded"]["height"] == 1080 and row["decoded"]["nonFiniteCount"] == 0 and row["decoded"]["rgbDynamicRange"] > 1e-6 for row in calibration_rows),
        "calibrationExrStorageExact": all(row["decoded"]["pixelFormat"] == "half" and row["decoded"]["compression"].lower() == "zip" for row in calibration_rows),
        "calibrationSettingsExact": all(row["settings"] and row["settings"]["engine"] == "CYCLES" and row["settings"]["device"] == "CPU" and row["settings"]["samples"] == 64 and row["settings"]["seed"] == 62001 and row["settings"]["animatedSeed"] is False for row in calibration_rows),
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    audit = write_hashed(output, {
        "schemaVersion": "bfs.b62Phase0BlenderAudit.v0.1",
        "experimentId": "B62-P0-E1",
        "status": status,
        "checks": checks,
        "markers": marker_rows,
        "cameraAnimation": camera_animation,
        "bones": bones,
        "assetLibraries": asset_rows,
        "motionLibrary": motion_row,
        "coreState": state_rows,
        "calibration": calibration_rows,
        "operations": {"blenderStarts": 1, "renderCalls": 0, "modelCalls": 0, "networkCalls": 0, "dockerProcesses": 0},
        "claimBoundary": {"formal288FrameRender": False, "cinematicQuality": False, "humanReview": False},
    }, "auditHash")
    if status != "PASS":
        failed = [name for name, value in checks.items() if not value]
        raise RuntimeError(f"Independent Blender audit failed: {failed}")
    print(f"BFS_B62_PHASE0_BLENDER_AUDIT_OK {len(checks)} {audit['auditHash']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B62_PHASE0_BLENDER_AUDIT_ERROR {type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1) from error
