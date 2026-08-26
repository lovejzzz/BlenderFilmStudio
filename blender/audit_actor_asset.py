"""Audit a Blender 5.2 actor and motion library against ActorSpec v0.1."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import bpy


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_value(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rounded(values) -> list[float]:
    return [round(float(value), 9) for value in values]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def resolve_below(root: Path, candidate: Path, label: str) -> Path:
    resolved_root = root.resolve()
    resolved = candidate.resolve() if candidate.is_absolute() else (resolved_root / candidate).resolve()
    if resolved == resolved_root or resolved_root not in resolved.parents:
        raise RuntimeError(f"{label} escapes repository root: {candidate}")
    return resolved


def bone_records(rig: bpy.types.Object) -> list[dict]:
    return [
        {
            "name": bone.name,
            "parent": bone.parent.name if bone.parent else None,
            "headLocal": rounded(bone.head_local),
            "tailLocal": rounded(bone.tail_local),
            "matrixLocal": [rounded(row) for row in bone.matrix_local],
            "deform": bone.use_deform,
        }
        for bone in sorted(rig.data.bones, key=lambda item: item.name)
    ]


def topology_record(obj: bpy.types.Object) -> dict:
    return {
        "vertices": [rounded(vertex.co) for vertex in obj.data.vertices],
        "edges": [list(edge.key) for edge in obj.data.edges],
        "polygons": [list(polygon.vertices) for polygon in obj.data.polygons],
    }


def shape_record(obj: bpy.types.Object) -> list[dict]:
    if not obj.data.shape_keys:
        return []
    return [
        {"name": key.name, "points": [rounded(point.co) for point in key.data]}
        for key in obj.data.shape_keys.key_blocks
    ]


def action_curves(action: bpy.types.Action) -> list[dict]:
    result = []
    for layer in action.layers:
        for strip in layer.strips:
            for channelbag in strip.channelbags:
                for curve in channelbag.fcurves:
                    result.append({
                        "slotHandle": channelbag.slot_handle,
                        "dataPath": curve.data_path,
                        "arrayIndex": curve.array_index,
                        "keys": [
                            {
                                "frame": round(float(point.co.x), 9),
                                "value": round(float(point.co.y), 9),
                                "interpolation": point.interpolation,
                            }
                            for point in curve.keyframe_points
                        ],
                    })
    return sorted(result, key=lambda item: (item["slotHandle"], item["dataPath"], item["arrayIndex"]))


def driver_records(ids: list[bpy.types.ID]) -> list[dict]:
    result = []
    for datablock in ids:
        animation_data = getattr(datablock, "animation_data", None)
        if not animation_data:
            continue
        for curve in animation_data.drivers:
            driver = curve.driver
            result.append({
                "owner": datablock.name,
                "dataPath": curve.data_path,
                "arrayIndex": curve.array_index,
                "type": driver.type,
                "expression": driver.expression,
                "isSimpleExpression": driver.is_simple_expression,
                "useSelf": driver.use_self,
                "valid": driver.is_valid,
            })
    return result


def main() -> None:
    args = parse_args()
    root = args.repository_root.resolve()
    spec_path = resolve_below(root, args.spec, "ActorSpec")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    checks = []

    def check(check_id: str, passed: bool, detail: object) -> None:
        checks.append({"id": check_id, "passed": bool(passed), "detail": detail})

    if tuple(bpy.app.version[:3]) != (5, 2, 0):
        raise RuntimeError(f"Blender 5.2.0 required, received {bpy.app.version_string}")

    actor = spec["actor"]
    asset_path = resolve_below(root, Path(actor["assetUri"]), "Actor asset")
    asset_hash = sha256_file(asset_path)
    check("A01_ASSET_HASH", asset_hash == actor["assetSha256"], {"expected": actor["assetSha256"], "actual": asset_hash})
    with bpy.data.libraries.load(str(asset_path), link=False, recursive=True) as (source, target):
        if actor["assetRef"] not in source.collections:
            raise RuntimeError(f"Actor collection {actor['assetRef']} missing from {actor['assetUri']}")
        target.collections = [actor["assetRef"]]
    collection = target.collections[0]
    bpy.context.scene.collection.children.link(collection)
    objects = {obj.name: obj for obj in collection.all_objects}

    rig_spec = spec["rig"]
    rig = objects.get(rig_spec["armatureObject"])
    check("A02_ARMATURE", bool(rig and rig.type == "ARMATURE"), {"object": rig_spec["armatureObject"], "type": rig.type if rig else None})
    if not rig or rig.type != "ARMATURE":
        raise RuntimeError("Actor armature is unavailable")
    mapped_bones = {mapping["semantic"]: mapping for mapping in rig_spec["bones"]}
    bone_names = {bone.name for bone in rig.data.bones}
    missing_bones = [mapping["bone"] for mapping in rig_spec["bones"] if mapping["bone"] not in bone_names]
    deform_mismatches = [mapping["bone"] for mapping in rig_spec["bones"] if mapping["bone"] in bone_names and rig.data.bones[mapping["bone"]].use_deform != mapping["deform"]]
    check("A03_BONE_MAP", not missing_bones and not deform_mismatches, {"missing": missing_bones, "deformMismatches": deform_mismatches})
    rotation_mismatches = [bone.name for bone in rig.pose.bones if bone.rotation_mode != rig_spec["rotationMode"]]
    check("A04_ROTATION_MODE", not rotation_mismatches, {"expected": rig_spec["rotationMode"], "mismatches": rotation_mismatches})

    rest_pose = bone_records(rig)
    rest_hash = sha256_value(rest_pose)
    check("A05_REST_POSE_HASH", rest_hash == rig_spec["restPoseSha256"], {"expected": rig_spec["restPoseSha256"], "actual": rest_hash})

    topology_hashes = {}
    modifier_report = []
    for mesh_spec in spec["deformation"]["meshes"]:
        obj = objects.get(mesh_spec["object"])
        if not obj or obj.type != "MESH":
            topology_hashes[mesh_spec["object"]] = None
            modifier_report.append({"object": mesh_spec["object"], "valid": False, "reason": "mesh missing"})
            continue
        topology_hashes[obj.name] = sha256_value(topology_record(obj))
        modifier = obj.modifiers.get(mesh_spec["armatureModifier"])
        modifier_report.append({
            "object": obj.name,
            "valid": bool(
                modifier and modifier.type == "ARMATURE" and modifier.object == rig
                and modifier.use_deform_preserve_volume == mesh_spec["preserveVolume"]
            ),
            "modifier": modifier.name if modifier else None,
            "preserveVolume": modifier.use_deform_preserve_volume if modifier else None,
        })
    expected_topology = {item["object"]: item["topologySha256"] for item in spec["deformation"]["meshes"]}
    check("A06_TOPOLOGY_HASH", topology_hashes == expected_topology, {"expected": expected_topology, "actual": topology_hashes})
    check("A07_ARMATURE_MODIFIERS", all(item["valid"] for item in modifier_report), modifier_report)

    shape_mesh = objects.get(spec["deformation"]["shapeKeyMesh"])
    shapes = shape_record(shape_mesh) if shape_mesh and shape_mesh.type == "MESH" else []
    shape_hash = sha256_value(shapes)
    shape_names = {item["name"] for item in shapes}
    missing_shapes = [channel["targetKey"] for channel in spec["deformation"]["shapeChannels"] if channel["targetKey"] not in shape_names]
    check("A08_SHAPE_KEY_SET", shape_hash == spec["deformation"]["shapeKeySetSha256"] and not missing_shapes, {"expectedHash": spec["deformation"]["shapeKeySetSha256"], "actualHash": shape_hash, "missing": missing_shapes})

    socket_missing = [socket["id"] for socket in spec["sockets"] if mapped_bones[socket["boneSemantic"]]["bone"] not in bone_names]
    check("A09_SOCKETS", not socket_missing, {"missing": socket_missing, "count": len(spec["sockets"])})

    allowed_constraints = set(rig_spec["allowedConstraints"])
    constraints = []
    for pose_bone in rig.pose.bones:
        for constraint in pose_bone.constraints:
            constraints.append({
                "bone": pose_bone.name,
                "name": constraint.name,
                "type": constraint.type,
                "allowed": constraint.type in allowed_constraints,
                "valid": constraint.is_valid,
                "errorLocation": round(float(constraint.error_location), 9),
                "errorRotation": round(float(constraint.error_rotation), 9),
            })
    check("A10_CONSTRAINT_ALLOWLIST", all(item["allowed"] and item["valid"] for item in constraints), constraints)

    datablocks: list[bpy.types.ID] = list(objects.values())
    datablocks.extend(obj.data for obj in objects.values() if obj.data)
    datablocks.extend(obj.data.shape_keys for obj in objects.values() if obj.type == "MESH" and obj.data.shape_keys)
    drivers = driver_records(datablocks)
    unsafe_drivers = [item for item in drivers if item["type"] == "SCRIPTED" and not item["isSimpleExpression"]]
    check("A11_DRIVER_POLICY", not unsafe_drivers and not rig_spec["driverPolicy"]["allowFullPython"], {"drivers": drivers, "unsafe": unsafe_drivers})

    action_reports = []
    allowed_action_bones = {mapping["bone"] for mapping in rig_spec["bones"]}
    pose_path = re.compile(r'^pose\.bones\["([^"]+)"\]\.(location|rotation_quaternion|rotation_euler|scale)$')
    for action_spec in spec["performance"]["bodyActions"]:
        action_path = resolve_below(root, Path(action_spec["uri"]), f"Body action {action_spec['id']}")
        actual_hash = sha256_file(action_path)
        with bpy.data.libraries.load(str(action_path), link=False) as (source, target):
            target.actions = [action_spec["actionName"]] if action_spec["actionName"] in source.actions else []
        action = target.actions[0] if target.actions else None
        curves = action_curves(action) if action else []
        invalid_paths = []
        invalid_frames = []
        for curve in curves:
            match = pose_path.fullmatch(curve["dataPath"])
            if not match or match.group(1) not in allowed_action_bones:
                invalid_paths.append(curve["dataPath"])
            for key in curve["keys"]:
                if key["frame"] < action_spec["frameStart"] or key["frame"] > action_spec["frameEnd"]:
                    invalid_frames.append(key["frame"])
        action_reports.append({
            "id": action_spec["id"],
            "hashMatch": actual_hash == action_spec["sha256"],
            "actionFound": action is not None,
            "slotCount": len(action.slots) if action else 0,
            "curveCount": len(curves),
            "invalidPaths": invalid_paths,
            "invalidFrames": invalid_frames,
            "curves": curves,
        })
    check("A12_ACTION_LIBRARIES", all(item["hashMatch"] and item["actionFound"] and item["slotCount"] > 0 and item["curveCount"] > 0 and not item["invalidPaths"] and not item["invalidFrames"] for item in action_reports), action_reports)

    identity = {
        "restPoseSha256": rest_hash,
        "topologySha256": dict(sorted(topology_hashes.items())),
        "shapeKeySetSha256": shape_hash,
        "bones": rest_pose,
        "shapeKeys": [item["name"] for item in shapes],
    }
    identity["identitySha256"] = sha256_value(identity)
    generation_report_path = root / "experiments/actor-v0-1/asset-generation.json"
    expected_identity = None
    if generation_report_path.exists():
        expected_identity = json.loads(generation_report_path.read_text(encoding="utf-8"))["identity"]["identitySha256"]
    check("A13_IDENTITY_LOCK", expected_identity is not None and identity["identitySha256"] == expected_identity, {"expected": expected_identity, "actual": identity["identitySha256"]})

    report = {
        "documentType": "BFS_ACTOR_ASSET_AUDIT",
        "auditVersion": "0.1.0",
        "blender": {"version": bpy.app.version_string, "buildHash": bpy.app.build_hash.decode("ascii")},
        "actor": actor["id"],
        "checks": checks,
        "allChecksPassed": all(item["passed"] for item in checks),
        "identity": identity,
        "explicitNonClaims": [
            "Asset conformance does not prove photorealism or performance quality.",
            "External gaze and contact targets require SceneSpec-level validation.",
            "Constraint validity does not prove natural deformation or absence of mesh penetration.",
        ],
    }
    output_path = resolve_below(root, args.output, "Audit output")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_ACTOR_AUDIT_{'OK' if report['allChecksPassed'] else 'FAILED'} {actor['id']} {identity['identitySha256']} {output_path}")
    if not report["allChecksPassed"]:
        failed = [item["id"] for item in checks if not item["passed"]]
        raise RuntimeError(f"Actor audit failed: {', '.join(failed)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_ACTOR_AUDIT_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
