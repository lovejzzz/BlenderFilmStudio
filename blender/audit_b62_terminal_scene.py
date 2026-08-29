"""Independent zero-render reopen audit for the B62 terminal production scene."""

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
    parser.add_argument("--compile-report", type=Path, required=True)
    parser.add_argument("--derived-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
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
    return isinstance(document.get(field), str) and document[field] == sha256_bytes(canonical({key: value for key, value in document.items() if key != field}))


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
    nodes = [{
        "name": node.name,
        "type": node.bl_idname,
        "inputs": [{"name": socket.name, "default": socket_default(socket)} for socket in node.inputs if not socket.is_linked],
    } for node in sorted(material.node_tree.nodes, key=lambda item: item.name)]
    links = sorted({(link.from_node.name, link.from_socket.name, link.to_node.name, link.to_socket.name) for link in material.node_tree.links})
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
    body = {
        "collection": original_name(collection.name),
        "objects": objects,
        "meshTopologyHashes": mesh_hashes,
        "materials": [original_name(material.name) for material in materials],
        "materialParameterHashes": {original_name(material.name): sha256_bytes(canonical(material_signature(material))) for material in materials},
    }
    body["identityHash"] = sha256_bytes(canonical(body))
    return body


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


def marker_roster(scene: bpy.types.Scene) -> list[dict]:
    return sorted([{"name": marker.name, "frame": int(marker.frame), "camera": marker.camera.name if marker.camera else None} for marker in scene.timeline_markers], key=lambda row: (row["frame"], row["name"]))


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


def state_snapshot(scene: bpy.types.Scene, excluded_action: str) -> dict:
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
        states.append({"frame": frame, "activation": float(core["bfs_core_activation"]), "warmEnergy": float(warm.data.energy), "contactDistanceM": float((hand.matrix_world.translation - touch.matrix_world.translation).length)})
    scene.frame_set(1)
    bpy.context.view_layer.update()
    state = {
        "rosters": {
            "objects": sorted(obj.name for obj in bpy.data.objects),
            "cameras": sorted(camera.name for camera in bpy.data.cameras),
            "actions": sorted(action.name for action in bpy.data.actions if action.name != excluded_action),
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
        "actions": [action_manifest(action) for action in sorted(bpy.data.actions, key=lambda item: item.name) if action.name != excluded_action],
        "states": states,
        "texts": sorted(text.name for text in bpy.data.texts),
        "externalLibraries": sorted(str(Path(bpy.path.abspath(library.filepath)).resolve()) for library in bpy.data.libraries),
    }
    state["stateHash"] = sha256_bytes(canonical(state))
    return state


def maximum_pose_error(scene: bpy.types.Scene, camera: bpy.types.Object, samples: list[dict]) -> tuple[float, list[dict]]:
    maximum = 0.0
    rows = []
    for expected in samples:
        scene.frame_set(expected["frame"])
        bpy.context.view_layer.update()
        location = [float(value) for value in camera.location]
        quaternion = [float(value) for value in camera.rotation_quaternion]
        location_error = max(abs(observed - wanted) for observed, wanted in zip(location, expected["location"]))
        direct = max(abs(observed - wanted) for observed, wanted in zip(quaternion, expected["quaternion"]))
        negated = max(abs(observed + wanted) for observed, wanted in zip(quaternion, expected["quaternion"]))
        quaternion_error = min(direct, negated)
        maximum = max(maximum, location_error, quaternion_error)
        rows.append({"frame": expected["frame"], "locationError": location_error, "quaternionError": quaternion_error})
    return maximum, rows


def main() -> None:
    args = arguments()
    plan_path = args.build_plan.resolve(strict=True)
    compile_report_path = args.compile_report.resolve(strict=True)
    output_path = args.output.resolve()
    require(not output_path.exists(), "audit output exists")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    compile_report = json.loads(compile_report_path.read_text(encoding="utf-8"))
    require(plan.get("schemaVersion") == PLAN_SCHEMA and valid_self(plan, "planHash"), "BuildPlan invalid")
    require(compile_report.get("status") == "PASS" and valid_self(compile_report, "reportHash"), "compile report invalid")
    require(bpy.app.version_string == "5.2.0 LTS" and bpy.app.build_hash.decode("utf-8") == "fbe6228777e7", "Blender runtime mismatch")
    loaded = Path(bpy.data.filepath).resolve(strict=True)
    require(sha256_file(loaded) == args.derived_sha256 == compile_report["derived"]["sha256"], "derived scene identity mismatch")
    require(os.environ.get("OCIO", "").endswith("color/ocio/cg-config-v4.0.0_aces-v2.0_ocio-v2.5.ocio"), "pinned OCIO environment absent")
    scene = bpy.context.scene
    contract = plan["camera"]
    camera = bpy.data.objects.get(contract["objectName"])
    require(camera is not None and camera.type == "CAMERA" and camera.data.name == contract["dataName"], "terminal camera missing")
    require(camera.rotation_mode == "QUATERNION" and camera.animation_data and camera.animation_data.action and camera.animation_data.action.name == contract["actionName"], "terminal animation assignment mismatch")
    optical_plan_tolerance = 1e-6
    optical_compile_tolerance = 1e-9
    optical_rows = []
    for name, observed, planned, compiled in [
        ("lensMillimeters", float(camera.data.lens), contract["lensMillimeters"], compile_report["terminalCamera"]["lensMillimeters"]),
        ("clipStart", float(camera.data.clip_start), contract["clipStart"], compile_report["terminalCamera"]["clipStart"]),
        ("clipEnd", float(camera.data.clip_end), contract["clipEnd"], compile_report["terminalCamera"]["clipEnd"]),
    ]:
        optical_rows.append({"name": name, "observed": observed, "planned": planned, "compiledObservation": compiled, "planAbsoluteError": abs(observed - planned), "compileAbsoluteError": abs(observed - compiled)})
    require(all(row["planAbsoluteError"] <= optical_plan_tolerance and row["compileAbsoluteError"] <= optical_compile_tolerance for row in optical_rows), f"camera optical contract mismatch {optical_rows}")
    require(camera.get("bfs_experiment_id") == EXPERIMENT_ID and camera.get("bfs_package_id") == plan["packageId"] and camera.get("bfs_source_camera") == contract["sourceCamera"] and camera.get("bfs_plan_hash") == plan["planHash"], "camera provenance mismatch")
    action = camera.animation_data.action
    channelbag = anim_utils.animdata_get_channelbag_for_assigned_slot(camera.animation_data)
    require(channelbag is not None and len(channelbag.fcurves) == 7 and all(len(curve.keyframe_points) == 96 for curve in channelbag.fcurves), "curve/key roster mismatch")
    expected_curves = {("location", index) for index in range(3)} | {("rotation_quaternion", index) for index in range(4)}
    observed_curves = {(curve.data_path, curve.array_index) for curve in channelbag.fcurves}
    require(observed_curves == expected_curves and all(point.interpolation == "LINEAR" for curve in channelbag.fcurves for point in curve.keyframe_points), "curve channel/interpolation mismatch")
    maximum_error, pose_rows = maximum_pose_error(scene, camera, contract["samples"])
    require(maximum_error <= 1e-6, f"camera bake error {maximum_error}")
    scene.frame_set(1)
    bpy.context.view_layer.update()
    observed_state = state_snapshot(scene, contract["actionName"])
    require(observed_state == compile_report["stateAfter"], "fresh reopen state differs from compile report")
    require(compile_report["stateBefore"]["actions"] == observed_state["actions"], "existing actions changed")
    require(compile_report["stateBefore"]["assets"] == observed_state["assets"] and compile_report["stateBefore"]["states"] == observed_state["states"], "asset/contact/core/light state changed")
    require(observed_state["timeline"] == {"frameStart": 1, "frameEnd": 288, "fps": 24}, "timeline mismatch")
    require(observed_state["markers"] == [
        {"name": "SHOT_WIDE_APPROACH", "frame": 1, "camera": "CAM_WIDE_APPROACH"},
        {"name": "SHOT_MEDIUM_CONTACT", "frame": 97, "camera": "CAM_MEDIUM_CONTACT"},
        {"name": "SHOT_CLOSE_REFLECTION", "frame": 193, "camera": contract["objectName"]},
    ], "marker routing mismatch")
    expected_render = plan["preservation"]["renderContract"]
    expected_render_reduced = {**expected_render, "colorManagement": {key: expected_render["colorManagement"][key] for key in ["display", "view", "look", "exposure", "gamma"]}}
    require(observed_state["render"] == expected_render_reduced, "render/color contract mismatch")
    require(set(plan["preservation"]["assetIdentityHashes"]) == set(ASSEMBLED_MANIFEST_HASHES), "asset provenance roster mismatch")
    for name, expected_hash in ASSEMBLED_MANIFEST_HASHES.items():
        require(observed_state["assets"][name]["identityHash"] == expected_hash, f"assembled master identity mismatch {name}")
    require(observed_state["texts"] == [] and observed_state["externalLibraries"] == [], "text or linked library present")
    terminal_manifest = action_manifest(action)
    require(terminal_manifest == compile_report["terminalCamera"]["action"], "terminal action manifest mismatch")
    checks = {
        "runtimeExact": True,
        "derivedSceneHashExact": True,
        "planAndCompileReportSelfHashesValid": True,
        "authorizedIdDeltaExact": True,
        "markerRoutingExact": True,
        "cameraOpticsAndProvenanceExact": True,
        "curveKeyAndInterpolationRosterExact": True,
        "all96PosesWithinTolerance": True,
        "existingActionsPreserved": True,
        "assetIdentityPreserved": True,
        "contactCoreAndLightStatePreserved": True,
        "timelineRenderAndColorContractPreserved": True,
        "textsAndExternalLibrariesZero": True,
        "renderCallsZero": True,
    }
    report = write_hashed(output_path, {
        "schemaVersion": "bfs.b62TerminalSceneIndependentAudit.v0.1",
        "experimentId": EXPERIMENT_ID,
        "status": "PASS",
        "checks": checks,
        "derived": {"filepath": str(loaded), "sha256": sha256_file(loaded), "bytes": loaded.stat().st_size},
        "buildPlan": {"filepath": str(plan_path), "sha256": sha256_file(plan_path), "planHash": plan["planHash"]},
        "compileReport": {"filepath": str(compile_report_path), "sha256": sha256_file(compile_report_path), "reportHash": compile_report["reportHash"]},
        "observedState": observed_state,
        "terminalAction": terminal_manifest,
        "poseTolerance": 1e-6,
        "maximumPoseError": maximum_error,
        "poseRows": pose_rows,
        "opticalPlanToleranceAbsolute": optical_plan_tolerance,
        "opticalCompileToleranceAbsolute": optical_compile_tolerance,
        "opticalRows": optical_rows,
        "operations": {"blenderStarts": 1, "sceneSaves": 0, "renderCalls": 0, "modelCalls": 0, "networkCalls": 0, "dockerProcesses": 0},
    }, "reportHash")
    print(f"BFS_B62_T1_INDEPENDENT PASS {len(pose_rows)} {maximum_error:.9g} {report['reportHash']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B62_T1_INDEPENDENT_ERROR {type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1) from error
