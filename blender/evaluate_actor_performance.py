"""Evaluate B03 ActorSpec channels after Blender's dependency graph runs."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from bpy_extras import anim_utils
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def resolve_below(root: Path, candidate: Path) -> Path:
    resolved_root = root.resolve()
    resolved = candidate.resolve() if candidate.is_absolute() else (resolved_root / candidate).resolve()
    if resolved == resolved_root or resolved_root not in resolved.parents:
        raise RuntimeError(f"Path escapes repository: {candidate}")
    return resolved


def rounded(values, digits: int = 7) -> list[float]:
    return [round(float(value), digits) for value in values]


def set_interpolation(animation_data, interpolation_by_frame: dict[int, str]) -> None:
    channelbag = anim_utils.animdata_get_channelbag_for_assigned_slot(animation_data)
    if not channelbag:
        return
    for curve in channelbag.fcurves:
        for point in curve.keyframe_points:
            point.interpolation = interpolation_by_frame.get(round(point.co.x), "BEZIER")


def load_actor(spec: dict, root: Path) -> tuple[dict[str, bpy.types.Object], bpy.types.Object]:
    asset_path = resolve_below(root, Path(spec["actor"]["assetUri"]))
    with bpy.data.libraries.load(str(asset_path), link=False, recursive=True) as (source, target):
        target.collections = [spec["actor"]["assetRef"]]
    collection = target.collections[0]
    bpy.context.scene.collection.children.link(collection)
    objects = {obj.name: obj for obj in collection.all_objects}
    rig = objects[spec["rig"]["armatureObject"]]

    action_spec = spec["performance"]["bodyActions"][0]
    action_path = resolve_below(root, Path(action_spec["uri"]))
    with bpy.data.libraries.load(str(action_path), link=False) as (source, target):
        target.actions = [action_spec["actionName"]]
    animation_data = rig.animation_data_create()
    animation_data.action = target.actions[0]
    animation_data.action_slot = target.actions[0].slots[0]

    shape_mesh = objects[spec["deformation"]["shapeKeyMesh"]]
    shape_keys = shape_mesh.data.shape_keys
    channel_map = {item["id"]: item for item in spec["deformation"]["shapeChannels"]}
    interpolation = {}
    for curve in spec["performance"]["facialCurves"]:
        key_block = shape_keys.key_blocks[channel_map[curve["channel"]]["targetKey"]]
        for key in curve["keys"]:
            key_block.value = key["value"]
            key_block.keyframe_insert(data_path="value", frame=key["frame"], group="BFS_FACE")
            interpolation[key["frame"]] = key["interpolation"]
    set_interpolation(shape_keys.animation_data, interpolation)

    gaze_target = objects["GAZE_TARGET"]
    positions = ((0.0, -3.0, 1.68), (1.15, -2.5, 1.42))
    for index, key in enumerate(spec["performance"]["gazeKeys"]):
        gaze_target.location = positions[min(index, len(positions) - 1)]
        gaze_target.keyframe_insert(data_path="location", frame=key["frame"], group="BFS_GAZE_TARGET")
    return objects, rig


def world_bone_points(rig: bpy.types.Object, pose_bone: bpy.types.PoseBone) -> tuple[Vector, Vector]:
    return rig.matrix_world @ pose_bone.head, rig.matrix_world @ pose_bone.tail


def object_bounds_center(obj: bpy.types.Object, depsgraph: bpy.types.Depsgraph) -> Vector:
    evaluated = obj.evaluated_get(depsgraph)
    corners = [evaluated.matrix_world @ Vector(corner) for corner in evaluated.bound_box]
    return sum(corners, Vector()) / len(corners)


def angular_error_degrees(origin: Vector, direction: Vector, target: Vector) -> float:
    target_direction = (target - origin).normalized()
    return math.degrees(direction.normalized().angle(target_direction))


def main() -> None:
    args = parse_args()
    root = args.repository_root.resolve()
    spec = json.loads(resolve_below(root, args.spec).read_text(encoding="utf-8"))
    objects, rig = load_actor(spec, root)
    scene = bpy.context.scene
    scene.frame_start = spec["performance"]["frameStart"]
    scene.frame_end = spec["performance"]["frameEnd"]
    significant_frames = {scene.frame_start, scene.frame_end}
    for action in spec["performance"]["bodyActions"]:
        significant_frames.update((action["frameStart"], action["frameEnd"]))
    for curve in spec["performance"]["facialCurves"]:
        significant_frames.update(key["frame"] for key in curve["keys"])
    significant_frames.update(key["frame"] for key in spec["performance"]["gazeKeys"])
    for contact in spec["performance"]["contacts"]:
        significant_frames.update((contact["frameStart"], contact["frameEnd"]))

    channel_map = {item["id"]: item["targetKey"] for item in spec["deformation"]["shapeChannels"]}
    shape_keys = objects[spec["deformation"]["shapeKeyMesh"]].data.shape_keys
    gaze_target = objects["GAZE_TARGET"]
    depsgraph = bpy.context.evaluated_depsgraph_get()
    samples = []
    for frame in sorted(significant_frames):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        target_world = gaze_target.matrix_world.translation.copy()
        eye_metrics = {}
        for bone_name, object_name in (("eye.L", "EYE_L"), ("eye.R", "EYE_R")):
            pose_bone = rig.pose.bones[bone_name]
            head, tail = world_bone_points(rig, pose_bone)
            # Blender bones point along local +Y and the benchmark constrains
            # that same axis to the gaze target.
            tracked_direction = tail - head
            eye_metrics[bone_name] = {
                "headWorldM": rounded(head),
                "tailWorldM": rounded(tail),
                "geometryCenterWorldM": rounded(object_bounds_center(objects[object_name], depsgraph)),
                "targetAngularErrorDeg": round(angular_error_degrees(head, tracked_direction, target_world), 7),
            }
        samples.append({
            "frame": frame,
            "headQuaternion": rounded(rig.pose.bones["head"].matrix.to_quaternion()),
            "shapeChannels": {channel: round(float(shape_keys.key_blocks[target].value), 7) for channel, target in channel_map.items()},
            "gazeTargetWorldM": rounded(target_world),
            "eyes": eye_metrics,
        })

    authored_values = []
    samples_by_frame = {sample["frame"]: sample for sample in samples}
    for curve in spec["performance"]["facialCurves"]:
        for key in curve["keys"]:
            actual = samples_by_frame[key["frame"]]["shapeChannels"][curve["channel"]]
            authored_values.append({
                "channel": curve["channel"],
                "frame": key["frame"],
                "expected": key["value"],
                "actual": actual,
                "absoluteError": round(abs(actual - key["value"]), 7),
            })

    semantic_bones = {item["semantic"]: item["bone"] for item in spec["rig"]["bones"]}
    socket_specs = {item["id"]: item for item in spec["sockets"]}
    contact_metrics = []
    for contact in spec["performance"]["contacts"]:
        socket = socket_specs[contact["effectorSocket"]]
        bone = rig.pose.bones[semantic_bones[socket["boneSemantic"]]]
        positions = []
        for frame in range(contact["frameStart"], contact["frameEnd"] + 1):
            scene.frame_set(frame)
            bpy.context.view_layer.update()
            matrix = rig.matrix_world @ bone.matrix
            positions.append(matrix @ Vector(socket["offset"]["locationM"]))
        origin = positions[0]
        max_slip = max((position - origin).length for position in positions)
        contact_metrics.append({
            "id": contact["id"],
            "sampleCount": len(positions),
            "maxSocketSlipM": round(max_slip, 9),
            "thresholdM": spec["acceptance"]["maxFootSlipM"],
            "passesSlipThreshold": max_slip <= spec["acceptance"]["maxFootSlipM"],
            "externalTargetErrorMeasured": False,
        })

    max_gaze_error = max(
        eye["targetAngularErrorDeg"]
        for sample in samples
        for eye in sample["eyes"].values()
    )
    head_start = Vector(samples_by_frame[1]["headQuaternion"])
    head_mid = Vector(samples_by_frame[72]["headQuaternion"])
    checks = [
        {"id": "E01_BODY_ACTION_EVALUATED", "passed": (head_mid - head_start).length > 1e-5, "detail": {"quaternionDelta": round((head_mid - head_start).length, 9)}},
        {"id": "E02_AUTHORED_FACE_VALUES", "passed": all(item["absoluteError"] <= 1e-6 for item in authored_values), "detail": authored_values},
        {"id": "E03_GAZE_THRESHOLD", "passed": max_gaze_error <= spec["acceptance"]["maxGazeAngularErrorDeg"], "detail": {"maximumDeg": round(max_gaze_error, 7), "thresholdDeg": spec["acceptance"]["maxGazeAngularErrorDeg"]}},
        {"id": "E04_FOOT_SLIP", "passed": all(item["passesSlipThreshold"] for item in contact_metrics), "detail": contact_metrics},
    ]
    report = {
        "documentType": "BFS_ACTOR_PERFORMANCE_EVALUATION",
        "evaluationVersion": "0.1.0",
        "blender": {"version": bpy.app.version_string, "buildHash": bpy.app.build_hash.decode("ascii")},
        "actorId": spec["actor"]["id"],
        "checks": checks,
        "allChecksPassed": all(check["passed"] for check in checks),
        "samples": samples,
        "explicitNonClaims": [
            "Socket slip does not measure error against an external scene target.",
            "Channel evaluation does not prove photorealism or natural acting.",
            "The preview mannequin does not test skin, hair, cloth, muscle, or speech realism.",
        ],
    }
    output = resolve_below(root, args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_ACTOR_EVALUATION {'OK' if report['allChecksPassed'] else 'FAILED'} {output}")
    if not report["allChecksPassed"]:
        raise RuntimeError("Actor performance evaluation failed: " + ",".join(check["id"] for check in checks if not check["passed"]))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_ACTOR_EVALUATION_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
