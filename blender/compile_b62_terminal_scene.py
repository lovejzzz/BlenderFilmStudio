"""Restricted zero-render compiler for the preregistered B62 terminal scene package."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import struct
import sys

import bpy
from bpy_extras import anim_utils


EXPERIMENT_ID = "B62-T1-E1"
PLAN_SCHEMA = "bfs.b62TerminalScenePackageBuildPlan.v0.1"
SOURCE_MASTER_NAME = "B62_PHASE0_MASTER.blend"
ASSET_COLLECTIONS = ["CHAR_B62_GUARDIAN", "PROP_B62_CONSOLE_CORE", "SET_B62_OBSERVATORY"]
ASSEMBLED_MANIFEST_HASHES = {
    "CHAR_B62_GUARDIAN": "d03a680766dbd454d2913ae74d66f3cdd2a6fd93fb423de2601049dcb3eba416",
    "PROP_B62_CONSOLE_CORE": "31a11b94cbcf0fafb61d301e9ff3dd5ad97d6b7a2424d4cc21c3403921a07b7e",
    "SET_B62_OBSERVATORY": "758f53592659e76f020feabeb1a5694d36e68000e0ce9c5bb0011aa6d93c3ba1",
}
STATE_FRAMES = [138, 143, 144, 150, 288]


def arguments() -> argparse.Namespace:
    tail = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-plan", type=Path, required=True)
    parser.add_argument("--output-scene", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args(tail)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def normalize(value: object) -> object:
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return int(value)
    if isinstance(value, float) and math.isfinite(value):
        return {"$f64be": struct.pack(">d", value).hex()}
    if isinstance(value, list):
        return [normalize(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize(item) for key, item in value.items()}
    return value


def canonical(value: object) -> bytes:
    return json.dumps(normalize(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def valid_self(document: dict, field: str) -> bool:
    if not isinstance(document.get(field), str):
        return False
    return document[field] == sha256_bytes(canonical({key: value for key, value in document.items() if key != field}))


def write_hashed(path: Path, body: dict, field: str) -> dict:
    require(not path.exists(), f"output exists {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {**body, field: sha256_bytes(canonical(body))}
    with path.open("x", encoding="utf-8") as handle:
        json.dump(record, handle, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    return record


def original_name(name: str) -> str:
    return re.sub(r"\.\d{3}$", "", name)


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


def material_signature(material: bpy.types.Material) -> dict:
    if not material.use_nodes or material.node_tree is None:
        return {"useNodes": False, "surfaceRenderMethod": material.surface_render_method}
    nodes = []
    for node in sorted(material.node_tree.nodes, key=lambda item: item.name):
        nodes.append({
            "name": node.name,
            "type": node.bl_idname,
            "inputs": [{"name": socket.name, "default": socket_default(socket)} for socket in node.inputs if not socket.is_linked],
        })
    links = sorted({
        (link.from_node.name, link.from_socket.name, link.to_node.name, link.to_socket.name)
        for link in material.node_tree.links
    })
    return {"useNodes": True, "surfaceRenderMethod": material.surface_render_method, "nodes": nodes, "links": [list(row) for row in links]}


def mesh_signature(obj: bpy.types.Object) -> dict:
    return {
        "vertices": [[round(float(component), 7) for component in vertex.co] for vertex in obj.data.vertices],
        "polygons": [list(polygon.vertices) for polygon in obj.data.polygons],
        "materials": [original_name(material.name) for material in obj.data.materials],
    }


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
    materials = sorted({material for obj in collection.all_objects if obj.type == "MESH" for material in obj.data.materials}, key=lambda item: original_name(item.name))
    manifest = {
        "collection": original_name(collection.name),
        "objects": objects,
        "meshTopologyHashes": mesh_hashes,
        "materials": [original_name(material.name) for material in materials],
        "materialParameterHashes": {original_name(material.name): sha256_bytes(canonical(material_signature(material))) for material in materials},
    }
    manifest["identityHash"] = sha256_bytes(canonical(manifest))
    return manifest


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
                    "keys": [[float(point.co.x), float(point.co.y), point.interpolation] for point in curve.keyframe_points],
                })
        slots.append({"identifier": slot.identifier, "targetIdType": slot.target_id_type, "curves": curves})
    body = {"name": action.name, "slots": slots}
    return {**body, "actionHash": sha256_bytes(canonical(body))}


def action_roster(excluded: set[str] | None = None) -> list[dict]:
    excluded = excluded or set()
    return [action_manifest(action) for action in sorted(bpy.data.actions, key=lambda item: item.name) if action.name not in excluded]


def marker_roster(scene: bpy.types.Scene) -> list[dict]:
    return sorted([
        {"name": marker.name, "frame": int(marker.frame), "camera": marker.camera.name if marker.camera else None}
        for marker in scene.timeline_markers
    ], key=lambda row: (row["frame"], row["name"]))


def render_contract(scene: bpy.types.Scene) -> dict:
    return {
        "engine": scene.render.engine,
        "device": scene.cycles.device,
        "samples": int(scene.cycles.samples),
        "resolution": [int(scene.render.resolution_x), int(scene.render.resolution_y)],
        "resolutionPercentage": int(scene.render.resolution_percentage),
        "fileFormat": scene.render.image_settings.file_format,
        "colorDepth": scene.render.image_settings.color_depth,
        "exrCodec": scene.render.image_settings.exr_codec,
        "filmTransparent": bool(scene.render.film_transparent),
        "motionBlur": bool(scene.render.use_motion_blur),
        "colorManagement": {
            "display": scene.display_settings.display_device,
            "view": scene.view_settings.view_transform,
            "look": scene.view_settings.look,
            "exposure": float(scene.view_settings.exposure),
            "gamma": float(scene.view_settings.gamma),
        },
    }


def critical_state(scene: bpy.types.Scene, excluded_actions: set[str] | None = None) -> dict:
    scene.frame_set(1)
    bpy.context.view_layer.update()
    assets = {}
    for name in ASSET_COLLECTIONS:
        collection = bpy.data.collections.get(name)
        require(collection is not None, f"asset collection missing {name}")
        assets[name] = collection_manifest(collection)
    hand = bpy.data.objects.get("HAND_R_SOCKET")
    touch = bpy.data.objects.get("CONSOLE_TOUCH")
    core = bpy.data.objects.get("B62_CORE")
    warm = bpy.data.objects.get("LIGHT_CORE_WARM")
    require(all(item is not None for item in (hand, touch, core, warm)), "contact/core/light object missing")
    states = []
    for frame in STATE_FRAMES:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        states.append({
            "frame": frame,
            "activation": float(core["bfs_core_activation"]),
            "warmEnergy": float(warm.data.energy),
            "contactDistanceM": float((hand.matrix_world.translation - touch.matrix_world.translation).length),
        })
    scene.frame_set(1)
    bpy.context.view_layer.update()
    state = {
        "rosters": {
            "objects": sorted(obj.name for obj in bpy.data.objects),
            "cameras": sorted(camera.name for camera in bpy.data.cameras),
            "actions": sorted(action.name for action in bpy.data.actions if not excluded_actions or action.name not in excluded_actions),
            "collections": sorted(collection.name for collection in bpy.data.collections),
            "materials": sorted(material.name for material in bpy.data.materials),
            "lights": sorted(light.name for light in bpy.data.lights),
            "meshes": sorted(mesh.name for mesh in bpy.data.meshes),
            "armatures": sorted(armature.name for armature in bpy.data.armatures),
        },
        "markers": marker_roster(scene),
        "activeCamera": scene.camera.name if scene.camera else None,
        "timeline": {"frameStart": int(scene.frame_start), "frameEnd": int(scene.frame_end), "fps": int(scene.render.fps)},
        "render": render_contract(scene),
        "assets": assets,
        "actions": action_roster(excluded_actions),
        "states": states,
        "texts": sorted(text.name for text in bpy.data.texts),
        "externalLibraries": sorted(str(Path(bpy.path.abspath(library.filepath)).resolve()) for library in bpy.data.libraries),
    }
    state["stateHash"] = sha256_bytes(canonical(state))
    return state


def expected_render_contract(plan: dict) -> dict:
    expected = plan["preservation"]["renderContract"]
    return {
        "engine": expected["engine"],
        "device": expected["device"],
        "samples": expected["samples"],
        "resolution": expected["resolution"],
        "resolutionPercentage": expected["resolutionPercentage"],
        "fileFormat": expected["fileFormat"],
        "colorDepth": expected["colorDepth"],
        "exrCodec": expected["exrCodec"],
        "filmTransparent": expected["filmTransparent"],
        "motionBlur": expected["motionBlur"],
        "colorManagement": {key: expected["colorManagement"][key] for key in ["display", "view", "look", "exposure", "gamma"]},
    }


def main() -> None:
    args = arguments()
    plan_path = args.build_plan.resolve(strict=True)
    output_scene = args.output_scene.resolve()
    report_path = args.report.resolve()
    require(not output_scene.exists() and not report_path.exists(), "output already exists")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    require(plan.get("schemaVersion") == PLAN_SCHEMA and plan.get("experimentId") == EXPERIMENT_ID and plan.get("status") == "COMPILED", "BuildPlan identity mismatch")
    require(valid_self(plan, "planHash"), "BuildPlan self hash invalid")
    require(bpy.app.version_string == "5.2.0 LTS" and bpy.app.build_hash.decode("utf-8") == "fbe6228777e7", f"unexpected Blender {bpy.app.version_string}")
    loaded = Path(bpy.data.filepath).resolve(strict=True)
    require(loaded.name == SOURCE_MASTER_NAME and sha256_file(loaded) == plan["sourceMaster"]["sha256"], "loaded source master mismatch")
    require(os.environ.get("OCIO", "").endswith("color/ocio/cg-config-v4.0.0_aces-v2.0_ocio-v2.5.ocio"), "pinned OCIO environment absent")
    scene = bpy.context.scene
    camera_contract = plan["camera"]
    object_name = camera_contract["objectName"]
    data_name = camera_contract["dataName"]
    action_name = camera_contract["actionName"]
    require(bpy.data.objects.get(object_name) is None and bpy.data.cameras.get(data_name) is None and bpy.data.actions.get(action_name) is None, "authorized output ID already exists")
    before = critical_state(scene)
    require(before["timeline"] == {"frameStart": 1, "frameEnd": 288, "fps": 24}, "source timeline mismatch")
    require(before["markers"] == [
        {"name": "SHOT_WIDE_APPROACH", "frame": 1, "camera": "CAM_WIDE_APPROACH"},
        {"name": "SHOT_MEDIUM_CONTACT", "frame": 97, "camera": "CAM_MEDIUM_CONTACT"},
        {"name": "SHOT_CLOSE_REFLECTION", "frame": 193, "camera": "CAM_CLOSE_REFLECTION"},
    ], "source markers mismatch")
    require(before["render"] == expected_render_contract(plan), f"source render contract mismatch {before['render']}")
    require(set(plan["preservation"]["assetIdentityHashes"]) == set(ASSEMBLED_MANIFEST_HASHES), "asset provenance roster mismatch")
    for name, expected_hash in ASSEMBLED_MANIFEST_HASHES.items():
        require(before["assets"][name]["identityHash"] == expected_hash, f"assembled master identity mismatch {name}")
    require(before["texts"] == [] and before["externalLibraries"] == [], "source contains text or linked libraries")

    source = bpy.data.objects.get(camera_contract["sourceCamera"])
    require(source is not None and source.type == "CAMERA", "source camera missing")
    data = source.data.copy()
    data.name = data_name
    data.lens = camera_contract["lensMillimeters"]
    data.clip_start = camera_contract["clipStart"]
    data.clip_end = camera_contract["clipEnd"]
    camera = bpy.data.objects.new(object_name, data)
    scene.collection.objects.link(camera)
    camera.rotation_mode = camera_contract["rotationMode"]
    camera["bfs_experiment_id"] = EXPERIMENT_ID
    camera["bfs_package_id"] = plan["packageId"]
    camera["bfs_source_camera"] = camera_contract["sourceCamera"]
    camera["bfs_plan_hash"] = plan["planHash"]
    samples = camera_contract["samples"]
    require(len(samples) == 96 and [row["frame"] for row in samples] == list(range(193, 289)), "BuildPlan sample roster mismatch")
    for row in samples:
        camera.location = row["location"]
        camera.rotation_quaternion = row["quaternion"]
        camera.keyframe_insert(data_path="location", frame=row["frame"], group="B62_TERMINAL_LOCATION")
        camera.keyframe_insert(data_path="rotation_quaternion", frame=row["frame"], group="B62_TERMINAL_ROTATION")
    require(camera.animation_data and camera.animation_data.action, "terminal camera action missing")
    camera.animation_data.action.name = action_name
    channelbag = anim_utils.animdata_get_channelbag_for_assigned_slot(camera.animation_data)
    require(channelbag is not None, "terminal camera channelbag missing")
    for curve in channelbag.fcurves:
        for point in curve.keyframe_points:
            point.interpolation = camera_contract["interpolation"]
    require(len(channelbag.fcurves) == 7 and all(len(curve.keyframe_points) == 96 for curve in channelbag.fcurves), "terminal camera curve roster mismatch")
    close_marker = scene.timeline_markers.get("SHOT_CLOSE_REFLECTION")
    require(close_marker is not None and close_marker.frame == 193 and close_marker.camera == source, "close marker source mismatch")
    close_marker.camera = camera
    scene.frame_set(1)
    bpy.context.view_layer.update()
    after = critical_state(scene, {action_name})
    require(after["rosters"]["objects"] == sorted(before["rosters"]["objects"] + [object_name]), "object delta mismatch")
    require(after["rosters"]["cameras"] == sorted(before["rosters"]["cameras"] + [data_name]), "camera data delta mismatch")
    require(sorted(action.name for action in bpy.data.actions) == sorted(before["rosters"]["actions"] + [action_name]), "action delta mismatch")
    for key in ["collections", "materials", "lights", "meshes", "armatures"]:
        require(after["rosters"][key] == before["rosters"][key], f"roster drift {key}")
    require(after["actions"] == before["actions"], "existing action drift")
    require(after["assets"] == before["assets"] and after["states"] == before["states"], "asset/contact/core/light state drift")
    require(after["timeline"] == before["timeline"] and after["render"] == before["render"] and after["activeCamera"] == before["activeCamera"], "scene state drift")
    require(after["markers"] == [
        {"name": "SHOT_WIDE_APPROACH", "frame": 1, "camera": "CAM_WIDE_APPROACH"},
        {"name": "SHOT_MEDIUM_CONTACT", "frame": 97, "camera": "CAM_MEDIUM_CONTACT"},
        {"name": "SHOT_CLOSE_REFLECTION", "frame": 193, "camera": object_name},
    ], "compiled marker routing mismatch")
    require(after["texts"] == [] and after["externalLibraries"] == [], "text or linked library introduced")

    output_scene.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output_scene), check_existing=False)
    require(output_scene.is_file() and output_scene.stat().st_size > 0, "derived scene missing")
    require(sha256_file(loaded) == plan["sourceMaster"]["sha256"], "source master changed")
    terminal_action = action_manifest(bpy.data.actions[action_name])
    report = write_hashed(report_path, {
        "schemaVersion": "bfs.b62TerminalSceneCompileReport.v0.1",
        "experimentId": EXPERIMENT_ID,
        "status": "PASS",
        "buildPlan": {"filepath": str(plan_path), "sha256": sha256_file(plan_path), "planHash": plan["planHash"]},
        "source": {"filepath": str(loaded), "sha256": sha256_file(loaded)},
        "derived": {"filepath": str(output_scene), "sha256": sha256_file(output_scene), "bytes": output_scene.stat().st_size},
        "blender": {"version": bpy.app.version_string, "buildHash": bpy.app.build_hash.decode("utf-8")},
        "stateBefore": before,
        "stateAfter": after,
        "terminalCamera": {
            "object": object_name,
            "data": data_name,
            "action": terminal_action,
            "lensMillimeters": float(data.lens),
            "clipStart": float(data.clip_start),
            "clipEnd": float(data.clip_end),
            "sampleCount": len(samples),
        },
        "operations": {"blenderStarts": 1, "sceneSaves": 1, "renderCalls": 0, "modelCalls": 0, "networkCalls": 0, "dockerProcesses": 0},
    }, "reportHash")
    print(f"BFS_B62_T1_COMPILE PASS {len(samples)} {report['derived']['sha256']} {report['reportHash']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B62_T1_COMPILE_ERROR {type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1) from error
