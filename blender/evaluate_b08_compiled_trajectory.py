"""Evaluate SceneSpec v0.5 trajectory replay inside a compiled B08 scene."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from bpy_extras import anim_utils
from mathutils import Quaternion, Vector


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def main() -> None:
    args = parse_args()
    wrapper = json.loads(args.plan.read_text(encoding="utf-8"))
    binding = wrapper["plan"]["trajectories"][0]
    spec = binding["trajectorySpec"]
    objects = bpy.data.collections[binding["assetRef"]].all_objects
    prop = next((item for item in objects if item.name == binding["objectRef"]), None)
    if prop is None:
        raise RuntimeError("Compiled B08 trajectory target is missing")
    rows = []
    maximum_position_error = 0.0
    maximum_rotation_error = 0.0
    for sample in spec["samples"]:
        bpy.context.scene.frame_set(sample["frame"])
        bpy.context.view_layer.update()
        position_error = (prop.matrix_world.translation - Vector(sample["locationM"])).length
        expected = Quaternion(sample["rotationQuaternionWxyz"])
        expected.normalize()
        rotation_error = math.degrees(prop.matrix_world.to_quaternion().rotation_difference(expected).angle)
        maximum_position_error = max(maximum_position_error, position_error)
        maximum_rotation_error = max(maximum_rotation_error, rotation_error)
        rows.append({"frame": sample["frame"], "positionErrorM": round(position_error, 12), "rotationErrorDeg": round(rotation_error, 12)})
    animation = prop.animation_data
    bag = anim_utils.animdata_get_channelbag_for_assigned_slot(animation) if animation and animation.action else None
    curves = list(bag.fcurves) if bag else []
    paths = sorted({curve.data_path for curve in curves})
    key_counts = sorted(len(curve.keyframe_points) for curve in curves)
    interpolations = sorted({point.interpolation for curve in curves for point in curve.keyframe_points})
    shortcuts = {
        "rigidBody": prop.rigid_body is not None,
        "constraints": len(prop.constraints),
        "drivers": len(animation.drivers) if animation else 0,
    }
    expected_sha = binding["verifiedTrajectorySpecSha256"]
    checks = [
        {"id": "B08_C01_PLAN_PIN", "pass": bpy.context.scene.get("bfs_plan_hash") == wrapper["planHash"], "observed": bpy.context.scene.get("bfs_plan_hash"), "threshold": wrapper["planHash"]},
        {"id": "B08_C02_TRAJECTORY_PIN", "pass": prop.get("bfs_trajectory_sha256") == expected_sha, "observed": prop.get("bfs_trajectory_sha256"), "threshold": expected_sha},
        {"id": "B08_C03_SOURCE_PIN", "pass": prop.get("bfs_source_evaluation_sha256") == binding["verifiedSourceEvaluationSha256"], "observed": prop.get("bfs_source_evaluation_sha256"), "threshold": binding["verifiedSourceEvaluationSha256"]},
        {"id": "B08_C04_POSITION_REPLAY", "pass": maximum_position_error <= spec["acceptance"]["maxReplayPositionErrorM"], "observed": round(maximum_position_error, 12), "threshold": spec["acceptance"]["maxReplayPositionErrorM"]},
        {"id": "B08_C05_ROTATION_REPLAY", "pass": maximum_rotation_error <= spec["acceptance"]["maxReplayRotationErrorDeg"], "observed": round(maximum_rotation_error, 12), "threshold": spec["acceptance"]["maxReplayRotationErrorDeg"]},
        {"id": "B08_C06_NO_RUNTIME_SHORTCUT", "pass": shortcuts == {"rigidBody": False, "constraints": 0, "drivers": 0}, "observed": shortcuts, "threshold": "no rigid body, constraints, or drivers"},
        {"id": "B08_C07_AUTHORED_KEYS", "pass": paths == ["location", "rotation_quaternion"] and len(curves) == 7 and key_counts == [132] * 7 and interpolations == ["LINEAR"], "observed": {"paths": paths, "curves": len(curves), "keyCounts": key_counts, "interpolations": interpolations}, "threshold": "7 transform curves × 132 LINEAR keys"},
        {"id": "B08_C08_STATUS_PRESERVED", "pass": prop.get("bfs_selection_status") == spec["selectionStatus"] == "TECHNICAL_CANONICAL_CANDIDATE_NOT_HUMAN_APPROVED", "observed": prop.get("bfs_selection_status"), "threshold": "TECHNICAL_CANONICAL_CANDIDATE_NOT_HUMAN_APPROVED"},
    ]
    report = {
        "documentType": "BFS_B08_COMPILED_TRAJECTORY_EVALUATION",
        "version": "0.1.0",
        "environment": {"blender": bpy.app.version_string, "buildHash": bpy.app.build_hash.decode("ascii")},
        "planHash": wrapper["planHash"],
        "trajectorySha256": expected_sha,
        "selectionStatus": spec["selectionStatus"],
        "measurements": {"maximumPositionErrorM": round(maximum_position_error, 12), "maximumRotationErrorDeg": round(maximum_rotation_error, 12), "evaluatedFrames": len(rows)},
        "checks": checks,
        "passed": all(item["pass"] for item in checks),
        "frames": rows,
        "explicitNonClaims": ["Compiled replay does not validate or make deterministic the source Bullet solve.", "The source trajectory remains a technical candidate without human approval."],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_B08_EVALUATION {'PASS' if report['passed'] else 'FAIL'} {args.output}")
    if not report["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as error:
        print(f"BFS_B08_EVALUATION_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
