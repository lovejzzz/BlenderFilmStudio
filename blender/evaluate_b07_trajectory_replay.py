"""Evaluate exact B07 baked-trajectory playback."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Quaternion, Vector


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trajectory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def main() -> None:
    args = parse_args()
    bytes_value = args.trajectory.read_bytes()
    trajectory_sha = hashlib.sha256(bytes_value).hexdigest()
    document = json.loads(bytes_value)
    prop = bpy.data.objects[document["targetObject"]]
    maximum_position_error = 0.0
    maximum_rotation_error = 0.0
    rows = []
    for sample in document["samples"]:
        bpy.context.scene.frame_set(sample["frame"])
        bpy.context.view_layer.update()
        position_error = (prop.matrix_world.translation - Vector(sample["locationM"])).length
        expected = Quaternion(sample["rotationQuaternionWxyz"])
        rotation_error = math.degrees(prop.matrix_world.to_quaternion().rotation_difference(expected).angle)
        maximum_position_error = max(maximum_position_error, position_error)
        maximum_rotation_error = max(maximum_rotation_error, rotation_error)
        rows.append({"frame": sample["frame"], "positionErrorM": round(position_error, 12), "rotationErrorDeg": round(rotation_error, 12)})
    shortcuts = {"rigidBody": prop.rigid_body is not None, "parent": prop.parent.name if prop.parent else None, "constraints": len(prop.constraints), "drivers": len(prop.animation_data.drivers) if prop.animation_data else 0}
    checks = [
        {"id": "B07_C01_PINNED_SHA", "pass": prop.get("bfs_trajectory_sha256") == trajectory_sha, "observed": prop.get("bfs_trajectory_sha256"), "threshold": trajectory_sha},
        {"id": "B07_C02_POSITION_REPLAY", "pass": maximum_position_error <= document["acceptance"]["maxReplayPositionErrorM"], "observed": round(maximum_position_error, 12), "threshold": document["acceptance"]["maxReplayPositionErrorM"]},
        {"id": "B07_C03_ROTATION_REPLAY", "pass": maximum_rotation_error <= document["acceptance"]["maxReplayRotationErrorDeg"], "observed": round(maximum_rotation_error, 12), "threshold": document["acceptance"]["maxReplayRotationErrorDeg"]},
        {"id": "B07_C04_NO_PHYSICS_SHORTCUT", "pass": shortcuts == {"rigidBody": False, "parent": None, "constraints": 0, "drivers": 0}, "observed": shortcuts, "threshold": "physics-disabled independent replay"},
    ]
    report = {
        "documentType": "BFS_B07_REPLAY_EVALUATION", "version": "0.1.0", "environment": {"blender": bpy.app.version_string},
        "trajectorySha256": trajectory_sha, "selectionStatus": document["selectionStatus"],
        "measurements": {"maximumPositionErrorM": round(maximum_position_error, 12), "maximumRotationErrorDeg": round(maximum_rotation_error, 12)},
        "checks": checks, "passed": all(item["pass"] for item in checks), "frames": rows,
        "explicitNonClaims": ["Exact replay does not validate or make deterministic the source Bullet solve.", "The source trajectory remains a technical candidate without human approval."],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(f"{json.dumps(report, indent=2)}\n", encoding="utf-8")
    print(f"BFS_B07_REPLAY_EVALUATION {'PASS' if report['passed'] else 'FAIL'} {args.output}")
    if not report["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as error:
        print(f"BFS_B07_REPLAY_EVALUATION_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
