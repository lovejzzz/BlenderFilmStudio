"""Measure ActorSpec performance against scene-owned target sockets."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Euler, Matrix, Vector


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def resolve_below(root: Path, candidate: Path) -> Path:
    resolved_root = root.resolve()
    resolved = candidate.resolve() if candidate.is_absolute() else (resolved_root / candidate).resolve()
    if resolved == resolved_root or resolved_root not in resolved.parents:
        raise RuntimeError(f"Path escapes repository: {candidate}")
    return resolved


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_value(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def rounded(values, digits: int = 7) -> list[float]:
    return [round(float(value), digits) for value in values]


def socket_matrix(rig: bpy.types.Object, pose_bone: bpy.types.PoseBone, socket: dict) -> Matrix:
    offset = socket["offset"]
    local = Matrix.LocRotScale(
        Vector(offset["locationM"]),
        Euler(tuple(math.radians(value) for value in offset["rotationEulerDeg"])),
        Vector(offset["scale"]),
    )
    return rig.matrix_world @ pose_bone.matrix @ local


def gaze_error(rig: bpy.types.Object, bone_name: str, target: bpy.types.Object) -> float:
    pose_bone = rig.pose.bones[bone_name]
    head = rig.matrix_world @ pose_bone.head
    tail = rig.matrix_world @ pose_bone.tail
    tracked = (tail - head).normalized()
    desired = (target.matrix_world.translation - head).normalized()
    return math.degrees(tracked.angle(desired))


def main() -> None:
    args = parse_args()
    root = args.repository_root.resolve()
    wrapper = json.loads(resolve_below(root, args.plan).read_text(encoding="utf-8"))
    if wrapper["planVersion"] != "0.2.0" or sha256_value(wrapper["plan"]) != wrapper["planHash"]:
        raise RuntimeError("A valid BuildPlan v0.2 is required")
    plan = wrapper["plan"]
    if bpy.context.scene.get("bfs_plan_hash") != wrapper["planHash"]:
        raise RuntimeError("Open .blend does not match the supplied BuildPlan")
    actor = plan["actors"][0]
    spec = actor["actorSpec"]
    rig = bpy.data.objects[spec["rig"]["armatureObject"]]
    shape_keys = bpy.data.objects[spec["deformation"]["shapeKeyMesh"]].data.shape_keys
    channel_map = {item["id"]: item["targetKey"] for item in spec["deformation"]["shapeChannels"]}
    semantic_bones = {item["semantic"]: item["bone"] for item in spec["rig"]["bones"]}
    actor_sockets = {item["id"]: item for item in spec["sockets"]}

    facial = []
    for curve in spec["performance"]["facialCurves"]:
        for key in curve["keys"]:
            bpy.context.scene.frame_set(key["frame"])
            bpy.context.view_layer.update()
            actual = float(shape_keys.key_blocks[channel_map[curve["channel"]]].value)
            facial.append({
                "channel": curve["channel"], "frame": key["frame"], "expected": key["value"],
                "actual": round(actual, 7), "absoluteError": round(abs(actual - key["value"]), 7),
            })

    gaze = []
    for key in spec["performance"]["gazeKeys"]:
        bpy.context.scene.frame_set(key["frame"])
        bpy.context.view_layer.update()
        target = bpy.data.objects[f"{key['targetRef']}__{key['targetSocket']}"]
        errors = {name: round(gaze_error(rig, name, target), 7) for name in ("eye.L", "eye.R")}
        gaze.append({
            "frame": key["frame"], "target": key["targetRef"], "socket": key["targetSocket"],
            "targetWorldM": rounded(target.matrix_world.translation), "eyeErrorDeg": errors,
        })

    contacts = []
    for contact in spec["performance"]["contacts"]:
        socket = actor_sockets[contact["effectorSocket"]]
        bone = rig.pose.bones[semantic_bones[socket["boneSemantic"]]]
        target = bpy.data.objects[f"{contact['targetRef']}__{contact['targetSocket']}"]
        samples = []
        actor_positions = []
        for frame in range(contact["frameStart"], contact["frameEnd"] + 1):
            bpy.context.scene.frame_set(frame)
            bpy.context.view_layer.update()
            actor_matrix = socket_matrix(rig, bone, socket)
            target_matrix = target.matrix_world
            position_error = (actor_matrix.translation - target_matrix.translation).length
            rotation_error = math.degrees(actor_matrix.to_quaternion().rotation_difference(target_matrix.to_quaternion()).angle)
            actor_positions.append(actor_matrix.translation.copy())
            samples.append({"frame": frame, "positionErrorM": round(position_error, 9), "rotationErrorDeg": round(rotation_error, 7)})
        origin = actor_positions[0]
        max_slip = max((position - origin).length for position in actor_positions)
        max_position = max(item["positionErrorM"] for item in samples)
        max_rotation = max(item["rotationErrorDeg"] for item in samples)
        contacts.append({
            "id": contact["id"], "target": contact["targetRef"], "targetSocket": contact["targetSocket"],
            "frameStart": contact["frameStart"], "frameEnd": contact["frameEnd"], "sampleCount": len(samples),
            "maximumPositionErrorM": max_position, "positionToleranceM": contact["positionToleranceM"],
            "maximumRotationErrorDeg": max_rotation, "rotationToleranceDeg": contact["rotationToleranceDeg"],
            "maximumSocketSlipM": round(max_slip, 9), "slipToleranceM": spec["acceptance"]["maxFootSlipM"],
            "passed": max_position <= contact["positionToleranceM"] and max_rotation <= contact["rotationToleranceDeg"] and max_slip <= spec["acceptance"]["maxFootSlipM"],
            "samples": samples,
        })

    max_gaze = max(error for item in gaze for error in item["eyeErrorDeg"].values())
    expected_identity = plan["actors"][0]["actorSpec"]["actor"]["assetSha256"]
    checks = [
        {"id": "C01_PLAN_BOUND", "passed": bpy.context.scene.get("bfs_plan_hash") == wrapper["planHash"], "detail": wrapper["planHash"]},
        {"id": "C02_ACTOR_ASSET_BOUND", "passed": bpy.data.objects[actor["assetRef"]].get("bfs_asset_sha256") == expected_identity, "detail": bpy.data.objects[actor["assetRef"]].get("bfs_asset_sha256")},
        {"id": "C03_FACE_TARGETS", "passed": all(item["absoluteError"] <= 1e-6 for item in facial), "detail": {"authoredKeys": len(facial), "maximumAbsoluteError": max(item["absoluteError"] for item in facial)}},
        {"id": "C04_SCENE_GAZE", "passed": max_gaze <= spec["acceptance"]["maxGazeAngularErrorDeg"], "detail": {"maximumDeg": round(max_gaze, 7), "thresholdDeg": spec["acceptance"]["maxGazeAngularErrorDeg"]}},
        {"id": "C05_SCENE_CONTACT", "passed": all(item["passed"] for item in contacts), "detail": [{key: value for key, value in item.items() if key != "samples"} for item in contacts]},
    ]
    report = {
        "documentType": "BFS_COMPILED_ACTOR_SCENE_EVALUATION",
        "evaluationVersion": "0.1.0",
        "blender": {"version": bpy.app.version_string, "buildHash": bpy.app.build_hash.decode("ascii")},
        "shot": plan["shot"]["id"], "planHash": wrapper["planHash"],
        "checks": checks, "allChecksPassed": all(item["passed"] for item in checks),
        "facial": facial, "gaze": gaze, "contacts": contacts,
        "explicitNonClaims": [
            "Target-relative socket agreement does not prove mesh collision or visually plausible contact.",
            "The B03 technical mannequin is not a photoreal human benchmark.",
            "No human acting or facial-readability review has been performed.",
        ],
    }
    output = resolve_below(root, args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_COMPILED_ACTOR_EVALUATION {'OK' if report['allChecksPassed'] else 'FAILED'} {output}")
    if not report["allChecksPassed"]:
        raise RuntimeError("Compiled actor scene evaluation failed: " + ",".join(item["id"] for item in checks if not item["passed"]))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_COMPILED_ACTOR_EVALUATION_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
