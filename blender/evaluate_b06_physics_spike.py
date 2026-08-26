"""Evaluate the pre-registered B06 contact-driven rigid-body spike."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def rounded(value: Vector) -> list[float]:
    return [round(component, 9) for component in value]


def main() -> None:
    args = parse_args()
    scene = bpy.context.scene
    prop = bpy.data.objects["B06_PROP"]
    left = bpy.data.objects["B06_LEFT"]
    right = bpy.data.objects["B06_RIGHT"]
    rows = []
    for frame in range(1, 133):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        prop_location = prop.matrix_world.translation.copy()
        left_location = left.matrix_world.translation.copy()
        right_location = right.matrix_world.translation.copy()
        midpoint = (left_location + right_location) / 2
        rows.append({
            "frame": frame,
            "propCentreWorldM": rounded(prop_location),
            "leftCentreWorldM": rounded(left_location),
            "rightCentreWorldM": rounded(right_location),
            "colliderMidpointWorldM": rounded(midpoint),
            "propMidpointDriftM": round((prop_location - midpoint).length, 9),
            "propKinematic": bool(prop.rigid_body.kinematic),
            "propRotationQuaternion": [round(value, 9) for value in prop.matrix_world.to_quaternion()],
        })

    by_frame = {row["frame"]: row for row in rows}
    hold = [row for row in rows if 49 <= row["frame"] <= 108]
    transport = by_frame[108]["propCentreWorldM"][2] - by_frame[49]["propCentreWorldM"][2]
    maximum_drift = max(row["propMidpointDriftM"] for row in hold)
    start_rotation = prop.matrix_world.to_quaternion()
    scene.frame_set(49)
    bpy.context.view_layer.update()
    rotation_49 = prop.matrix_world.to_quaternion().copy()
    scene.frame_set(108)
    bpy.context.view_layer.update()
    rotation_108 = prop.matrix_world.to_quaternion().copy()
    rotation_change = math.degrees(rotation_49.rotation_difference(rotation_108).angle)
    release_fall = by_frame[112]["propCentreWorldM"][2] - by_frame[132]["propCentreWorldM"][2]
    maximum_axis_escape = max(abs(row["propCentreWorldM"][0] - row["colliderMidpointWorldM"][0]) for row in hold)
    maximum_collider_step = max(
        math.dist(rows[index - 1][field], rows[index][field])
        for index in range(1, len(rows))
        for field in ("leftCentreWorldM", "rightCentreWorldM")
    )

    transform_paths = []
    if prop.animation_data and prop.animation_data.action:
        from bpy_extras import anim_utils
        bag = anim_utils.animdata_get_channelbag_for_assigned_slot(prop.animation_data)
        if bag:
            transform_paths = sorted({curve.data_path for curve in bag.fcurves if curve.data_path in {"location", "rotation_euler", "rotation_quaternion", "scale"}})
    forbidden_shortcuts = {
        "parent": prop.parent.name if prop.parent else None,
        "constraints": [constraint.name for constraint in prop.constraints],
        "rigidBodyConstraintObjects": sorted(obj.name for obj in bpy.data.objects if obj.rigid_body_constraint is not None),
        "drivers": len(prop.animation_data.drivers) if prop.animation_data else 0,
        "transformAnimationPaths": transform_paths,
    }
    left_action = left.animation_data.action if left.animation_data else None
    right_action = right.animation_data.action if right.animation_data else None
    independent_colliders = bool(left_action and right_action and left_action != right_action and left.rigid_body and right.rigid_body)
    maximum_collision_margin = max(prop.rigid_body.collision_margin, left.rigid_body.collision_margin, right.rigid_body.collision_margin)

    checks = [
        {"id": "B06_C01_NO_SHORTCUT", "pass": forbidden_shortcuts == {"parent": None, "constraints": [], "rigidBodyConstraintObjects": [], "drivers": 0, "transformAnimationPaths": []}, "observed": forbidden_shortcuts, "threshold": "none"},
        {"id": "B06_C02_PROP_DYNAMIC", "pass": all(not row["propKinematic"] for row in rows if 49 <= row["frame"] <= 132), "observed": sorted({row["propKinematic"] for row in rows if 49 <= row["frame"] <= 132}), "threshold": [False]},
        {"id": "B06_C03_INDEPENDENT_COLLIDERS", "pass": independent_colliders, "observed": {"leftAction": left_action.name if left_action else None, "rightAction": right_action.name if right_action else None}, "threshold": "distinct animation actions"},
        {"id": "B06_C04_VERTICAL_TRANSPORT", "pass": transport >= 0.25, "observed": round(transport, 9), "threshold": ">=0.25m"},
        {"id": "B06_C05_HOLD_MIDPOINT_DRIFT", "pass": maximum_drift <= 0.03, "observed": round(maximum_drift, 9), "threshold": "<=0.03m"},
        {"id": "B06_C06_HOLD_ROTATION", "pass": rotation_change <= 10, "observed": round(rotation_change, 9), "threshold": "<=10deg"},
        {"id": "B06_C07_BETWEEN_COLLIDERS", "pass": maximum_axis_escape <= 0.02, "observed": round(maximum_axis_escape, 9), "threshold": "<=0.02m centre-axis escape"},
        {"id": "B06_C08_RELEASE_FALL", "pass": release_fall >= 0.03, "observed": round(release_fall, 9), "threshold": ">=0.03m by frame132"},
        {"id": "B06_C09_SOLVER_BUDGET", "pass": scene.rigidbody_world.substeps_per_frame >= 240 and scene.rigidbody_world.solver_iterations >= 40, "observed": {"substepsPerFrame": scene.rigidbody_world.substeps_per_frame, "solverIterations": scene.rigidbody_world.solver_iterations}, "threshold": {"substepsPerFrame": 240, "solverIterations": 40}},
        {"id": "B06_C10_COLLISION_MARGIN", "pass": maximum_collision_margin <= 0.001, "observed": round(maximum_collision_margin, 9), "threshold": "<=0.001m declared contact gap"},
        {"id": "B06_C11_COLLIDER_STEP", "pass": maximum_collider_step <= 0.01, "observed": round(maximum_collider_step, 9), "threshold": "<=0.01m per frame"},
    ]
    report = {
        "documentType": "BFS_B06_PHYSICS_SPIKE_EVALUATION", "version": "0.1.0",
        "environment": {"blender": bpy.app.version_string},
        "measurements": {"verticalTransportM": round(transport, 9), "maximumHoldMidpointDriftM": round(maximum_drift, 9), "holdRotationChangeDeg": round(rotation_change, 9), "maximumCentreAxisEscapeM": round(maximum_axis_escape, 9), "releaseFallM": round(release_fall, 9), "maximumCollisionMarginM": round(maximum_collision_margin, 9), "maximumColliderStepM": round(maximum_collider_step, 9)},
        "checks": checks, "passed": all(item["pass"] for item in checks), "trajectory": rows,
        "explicitNonClaims": [
            "This Bullet rigid-body spike does not establish human grasp realism, force closure, measured friction, skin deformation, pressure, tendon force, or generalization.",
            "A passing trajectory would be specific to the declared geometry, solver budget, time step, margin, friction, and motion profile.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(f"{json.dumps(report, indent=2)}\n", encoding="utf-8")
    print(f"BFS_B06_PHYSICS_EVALUATION {'PASS' if report['passed'] else 'FAIL'} {args.output}")
    if not report["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as error:
        print(f"BFS_B06_PHYSICS_EVALUATION_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
