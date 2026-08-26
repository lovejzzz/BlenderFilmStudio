"""Evaluate the preregistered B05 two-finger IK feasibility scene."""

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


def joint_angle_z(pose_bone: bpy.types.PoseBone) -> float:
    if pose_bone.parent:
        rest_relative = pose_bone.parent.bone.matrix_local.inverted() @ pose_bone.bone.matrix_local
        pose_relative = pose_bone.parent.matrix.inverted() @ pose_bone.matrix
    else:
        rest_relative = pose_bone.bone.matrix_local
        pose_relative = pose_bone.matrix
    delta = rest_relative.inverted() @ pose_relative
    return math.degrees(delta.to_euler("XYZ").z)


def world_tail(armature: bpy.types.Object, bone_name: str) -> Vector:
    return armature.matrix_world @ armature.pose.bones[bone_name].tail


def main() -> None:
    args = parse_args()
    scene = bpy.context.scene
    armature = bpy.data.objects["B05_GRIPPER"]
    prop = bpy.data.objects["PROP_BODY"]
    bones = ["thumb.1", "thumb.2", "index.1", "index.2"]
    expected = ["B05_CARRIER", "B05_GRIPPER", "PROP_BODY", "TARGET_THUMB", "TARGET_INDEX", "TIP_THUMB", "TIP_INDEX"]
    missing = [name for name in expected if name not in bpy.data.objects]
    frame_rows = []
    maximum_joint_violation = 0.0
    maximum_length_ratio_error = 0.0
    maximum_target_error = 0.0
    for frame in range(1, 121):
        scene.frame_set(frame)
        joints = []
        for name in bones:
            pose_bone = armature.pose.bones[name]
            angle = joint_angle_z(pose_bone)
            minimum = math.degrees(pose_bone.ik_min_z)
            maximum = math.degrees(pose_bone.ik_max_z)
            violation = max(minimum - angle, angle - maximum, 0)
            length_ratio = (pose_bone.tail - pose_bone.head).length / pose_bone.bone.length
            maximum_joint_violation = max(maximum_joint_violation, violation)
            maximum_length_ratio_error = max(maximum_length_ratio_error, abs(length_ratio - 1))
            joints.append({"bone": name, "angleDeg": round(angle, 9), "minimumDeg": round(minimum, 9), "maximumDeg": round(maximum, 9), "violationDeg": round(violation, 9), "lengthRatio": round(length_ratio, 12)})
        tips = {}
        for finger in ("thumb", "index"):
            tail = world_tail(armature, f"{finger}.2")
            target = bpy.data.objects[f"TARGET_{finger.upper()}"].matrix_world.translation
            target_error = (tail - target).length
            maximum_target_error = max(maximum_target_error, target_error if 49 <= frame <= 108 else 0)
            tips[finger] = {"worldM": [round(value, 9) for value in tail], "targetErrorM": round(target_error, 9)}
        frame_rows.append({"frame": frame, "joints": joints, "tips": tips, "propCentreWorldM": [round(value, 9) for value in prop.matrix_world.translation]})

    hold_rows = [row for row in frame_rows if 49 <= row["frame"] <= 108]
    separations = {"thumb": [], "index": []}
    relative = {"thumb": [], "index": []}
    for row in hold_rows:
        prop_centre = Vector(row["propCentreWorldM"])
        for finger, side in (("thumb", -1), ("index", 1)):
            tip = Vector(row["tips"][finger]["worldM"])
            face = prop_centre + Vector((0.05 * side, 0, 0))
            separations[finger].append((tip - face).length - 0.01)
            relative[finger].append(tip - prop_centre)
    separation_minimum = min(value for values in separations.values() for value in values)
    separation_maximum = max(value for values in separations.values() for value in values)
    relative_drift = max((value - values[0]).length for values in relative.values() for value in values)
    transport = (Vector(hold_rows[-1]["propCentreWorldM"]) - Vector(hold_rows[0]["propCentreWorldM"])).length

    closure_distances = []
    hold_targets = {"thumb": Vector((-0.061, 0, 0)), "index": Vector((0.061, 0, 0))}
    carrier = bpy.data.objects["B05_CARRIER"]
    for frame in range(37, 49):
        scene.frame_set(frame)
        inverse = carrier.matrix_world.inverted()
        closure_distances.append(sum(((inverse @ world_tail(armature, f"{finger}.2")) - target).length for finger, target in hold_targets.items()))
    closure_monotonic = all(right <= left + 1e-9 for left, right in zip(closure_distances, closure_distances[1:])) and closure_distances[-1] < closure_distances[0]
    constraints = {finger: armature.pose.bones[f"{finger}.2"].constraints.get(f"IK_{finger.upper()}") for finger in ("thumb", "index")}
    ik_contract = all(item and item.type == "IK" and item.chain_count == 2 and not item.use_stretch for item in constraints.values())
    all_bone_stretch_zero = all(armature.pose.bones[name].ik_stretch == 0 for name in bones)
    gates = {
        "expectedObjectsPresent": not missing,
        "ikContractPresent": ik_contract,
        "allBoneStretchZero": all_bone_stretch_zero,
        "maximumLengthRatioErrorAtMost1e6": maximum_length_ratio_error <= 1e-6,
        "maximumJointViolationAtMost01Deg": maximum_joint_violation <= 0.1,
        "holdSeparationInRange": separation_minimum >= 0.0005 and separation_maximum <= 0.0015,
        "holdRelativeDriftAtMost0001M": relative_drift <= 0.0001,
        "holdTransportAtLeast0299M": transport >= 0.299,
        "closureMonotonic": closure_monotonic,
        "holdTargetErrorAtMost0001M": maximum_target_error <= 0.0001,
    }
    report = {
        "documentType": "BFS_B05_IK_FEASIBILITY_EVALUATION",
        "version": "0.1.0",
        "environment": {"blender": bpy.app.version_string},
        "missingObjects": missing,
        "measurements": {
            "maximumJointLimitViolationDeg": round(maximum_joint_violation, 9),
            "maximumLengthRatioError": round(maximum_length_ratio_error, 12),
            "maximumHoldTargetErrorM": round(maximum_target_error, 9),
            "holdSurfaceSeparationMinimumM": round(separation_minimum, 9),
            "holdSurfaceSeparationMaximumM": round(separation_maximum, 9),
            "holdRelativeDriftM": round(relative_drift, 9),
            "holdTransportM": round(transport, 9),
            "closureDistancesM": [round(value, 9) for value in closure_distances],
        },
        "gates": gates,
        "passed": all(gates.values()),
        "frames": frame_rows,
        "explicitNonClaims": [
            "The common carrier means this is not contact-driven support or dynamics.",
            "This spike does not establish force closure, friction, anatomy, skin deformation, weight or visual credibility.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(f"{json.dumps(report, indent=2)}\n", encoding="utf-8")
    print(f"BFS_B05_IK_EVALUATION {'PASS' if report['passed'] else 'FAIL'} {args.output}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B05_IK_EVALUATION_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
