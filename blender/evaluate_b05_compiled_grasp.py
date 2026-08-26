"""Evaluate the pre-registered B05 SceneSpec v0.4 compiled grasp."""

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
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def rounded_vector(value: Vector) -> list[float]:
    return [round(component, 9) for component in value]


def joint_angle(pose_bone: bpy.types.PoseBone, axis: str) -> float:
    if pose_bone.parent:
        rest_relative = pose_bone.parent.bone.matrix_local.inverted() @ pose_bone.bone.matrix_local
        pose_relative = pose_bone.parent.matrix.inverted() @ pose_bone.matrix
    else:
        rest_relative = pose_bone.bone.matrix_local
        pose_relative = pose_bone.matrix
    delta = rest_relative.inverted() @ pose_relative
    return math.degrees(getattr(delta.to_euler("XYZ"), axis.lower()))


def world_tail(armature: bpy.types.Object, bone_name: str) -> Vector:
    return armature.matrix_world @ armature.pose.bones[bone_name].tail


def parent_chain(obj: bpy.types.Object) -> list[str]:
    chain = []
    current = obj.parent
    while current is not None:
        chain.append(current.name)
        current = current.parent
    return chain


def evaluated_centroid(obj: bpy.types.Object, depsgraph: bpy.types.Depsgraph) -> Vector:
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        if not mesh.vertices:
            raise RuntimeError(f"Evaluated mesh has no vertices: {obj.name}")
        local = sum((vertex.co for vertex in mesh.vertices), Vector()) / len(mesh.vertices)
        return evaluated.matrix_world @ local
    finally:
        evaluated.to_mesh_clear()


def check(checks: list[dict], identifier: str, passed: bool, observed, threshold) -> None:
    checks.append({"id": identifier, "pass": bool(passed), "observed": observed, "threshold": threshold})


def main() -> None:
    args = parse_args()
    wrapper = json.loads(args.plan.read_text(encoding="utf-8"))
    plan = wrapper["plan"]
    binding = plan["grasps"][0]
    spec = binding["graspSpec"]
    scene = bpy.context.scene
    rig = bpy.data.objects[binding["armatureObject"]]
    prop_object = bpy.data.objects[binding["propObject"]]
    prop_root = bpy.data.objects[binding["propAssetRef"]]
    actor_root = bpy.data.objects[binding["actorAssetRef"]]
    frame_object = bpy.data.objects[f"{binding['id']}__TRANSPORT_FRAME"]

    contact_by_finger = {item["fingerRef"]: item for item in spec["contactPatches"]}
    terminal_by_finger = {item["id"]: item["bones"][-1]["boneSemantic"] for item in spec["fingerChains"]}
    target_by_finger = {
        item["id"]: bpy.data.objects[f"{binding['id']}__{contact_by_finger[item['id']]['id']}"]
        for item in spec["fingerChains"]
    }
    expected_objects = [binding["armatureObject"], binding["propObject"], binding["actorAssetRef"], binding["propAssetRef"], frame_object.name]
    expected_objects.extend(item.name for item in target_by_finger.values())
    missing_objects = [name for name in expected_objects if name not in bpy.data.objects]

    joint_rows = []
    maximum_joint_violation = 0.0
    maximum_length_ratio_error = 0.0
    maximum_segment_alignment_error = 0.0
    joint_configuration_ok = True
    for frame in range(scene.frame_start, scene.frame_end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        for finger in spec["fingerChains"]:
            for bone_spec in finger["bones"]:
                pose_bone = rig.pose.bones[bone_spec["boneSemantic"]]
                axis = bone_spec["rotationAxis"]
                angle = joint_angle(pose_bone, axis)
                violation = max(bone_spec["minimumDeg"] - angle, angle - bone_spec["maximumDeg"], 0.0)
                length_ratio = (pose_bone.tail - pose_bone.head).length / pose_bone.bone.length
                maximum_joint_violation = max(maximum_joint_violation, violation)
                maximum_length_ratio_error = max(maximum_length_ratio_error, abs(length_ratio - 1.0))
                mesh_object = bpy.data.objects[f"MESH_{bone_spec['boneSemantic']}"]
                bone_midpoint = rig.matrix_world @ ((pose_bone.head + pose_bone.tail) / 2)
                segment_alignment_error = (evaluated_centroid(mesh_object, depsgraph) - bone_midpoint).length
                maximum_segment_alignment_error = max(maximum_segment_alignment_error, segment_alignment_error)
                enabled_limits = {candidate: getattr(pose_bone, f"use_ik_limit_{candidate.lower()}") for candidate in "XYZ"}
                locked_axes = {candidate: getattr(pose_bone, f"lock_ik_{candidate.lower()}") for candidate in "XYZ"}
                joint_configuration_ok = joint_configuration_ok and enabled_limits[axis] and all(locked_axes[candidate] for candidate in "XYZ" if candidate != axis)
                joint_rows.append({
                    "frame": frame, "finger": finger["id"], "bone": pose_bone.name, "axis": axis,
                    "angleDeg": round(angle, 9), "violationDeg": round(violation, 9), "lengthRatio": round(length_ratio, 12),
                    "segmentAlignmentErrorM": round(segment_alignment_error, 9),
                })

    closure_distances = []
    for frame in range(spec["phases"]["closure"]["start"], spec["phases"]["closure"]["end"] + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        distance = sum((world_tail(rig, terminal_by_finger[finger]) - target_by_finger[finger].matrix_world.translation).length for finger in terminal_by_finger)
        closure_distances.append(distance)
    closure_monotonic = all(right <= left + 0.0001 for left, right in zip(closure_distances, closure_distances[1:])) and closure_distances[-1] < closure_distances[0]

    separation_values = []
    contact_relative = {finger: [] for finger in terminal_by_finger}
    active_contacts_per_frame = []
    hold_start = spec["phases"]["hold"]["start"]
    hold_end = spec["phases"]["hold"]["end"]
    for frame in range(hold_start, hold_end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        active = 0
        for finger, terminal in terminal_by_finger.items():
            contact = contact_by_finger[finger]
            surface = prop_object.matrix_world @ Vector(contact["targetPointLocalM"])
            tip = world_tail(rig, terminal)
            separation = (tip - surface).length
            separation_values.append(separation)
            contact_relative[finger].append(tip - surface)
            if contact["separationRangeM"]["minimum"] <= separation <= contact["separationRangeM"]["maximum"]:
                active += 1
        active_contacts_per_frame.append(active)
    separation_minimum = min(separation_values)
    separation_maximum = max(separation_values)
    relative_drift = max((value - values[0]).length for values in contact_relative.values() for value in values)

    scene.frame_set(hold_start)
    bpy.context.view_layer.update()
    prop_hold_start = prop_object.matrix_world.translation.copy()
    scene.frame_set(hold_end)
    bpy.context.view_layer.update()
    prop_hold_end = prop_object.matrix_world.translation.copy()
    transport = (prop_hold_end - prop_hold_start).length

    acquire = spec["phases"]["closure"]["end"]
    release = spec["phases"]["release"]["end"]
    positions = {}
    for frame in (acquire - 1, acquire, release - 1, release):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        positions[frame] = prop_object.matrix_world.translation.copy()
    acquire_pop = (positions[acquire] - positions[acquire - 1]).length
    release_pop = (positions[release] - positions[release - 1]).length

    ik_contract_rows = []
    ik_contract_ok = True
    all_bone_stretch_zero = True
    for finger in spec["fingerChains"]:
        terminal = rig.pose.bones[finger["bones"][-1]["boneSemantic"]]
        constraint = terminal.constraints.get(f"BFS_GRASP_IK_{finger['id']}")
        valid = bool(constraint and constraint.type == "IK" and constraint.chain_count == len(finger["bones"]) and not constraint.use_stretch and constraint.target == target_by_finger[finger["id"]])
        ik_contract_ok = ik_contract_ok and valid
        all_bone_stretch_zero = all_bone_stretch_zero and all(rig.pose.bones[bone["boneSemantic"]].ik_stretch == 0 for bone in finger["bones"])
        influences = {}
        for frame in (acquire, hold_start, hold_end):
            scene.frame_set(frame)
            influences[str(frame)] = round(constraint.influence if constraint else -1, 9)
        ik_contract_ok = ik_contract_ok and all(value >= 0.999999 for value in influences.values())
        ik_contract_rows.append({"finger": finger["id"], "valid": valid, "influences": influences})

    normals = [Vector(item["targetNormalLocal"]) for item in spec["contactPatches"]]
    opposing_angle = max(math.degrees(a.angle(b)) for index, a in enumerate(normals) for b in normals[index + 1 :])
    prop_constraint = prop_root.constraints.get(f"BFS_GRASP_PROP_{binding['id']}")
    attachment_states = {}
    for frame in (acquire - 1, acquire, hold_end, release):
        scene.frame_set(frame)
        attachment_states[str(frame)] = round(prop_constraint.influence if prop_constraint else -1, 9)
    attachment_contract_ok = bool(
        prop_constraint and prop_constraint.type == "CHILD_OF" and prop_constraint.target == rig
        and prop_constraint.subtarget == spec["palmSocket"]
        and attachment_states == {str(acquire - 1): 0.0, str(acquire): 1.0, str(hold_end): 1.0, str(release): 0.0}
    )

    actor_ancestors = set(parent_chain(rig))
    prop_ancestors = set(parent_chain(prop_object))
    shared_non_scene_carriers = sorted(actor_ancestors & prop_ancestors)
    independent_transport = frame_object.parent is None and all(target.parent == frame_object for target in target_by_finger.values())
    no_shared_carrier = not shared_non_scene_carriers and prop_root.parent is None and actor_root != prop_root and independent_transport

    checks = []
    check(checks, "B05_C01_EXPECTED_OBJECTS", not missing_objects, missing_objects, "none missing")
    check(checks, "B05_C02_IK_CONTRACT", ik_contract_ok, ik_contract_rows, "2 declared two-bone IK chains, influence=1 during HOLD, no stretch")
    check(checks, "B05_C03_JOINT_CONFIGURATION", joint_configuration_ok, joint_configuration_ok, "declared axis limit enabled; other axes locked")
    check(checks, "B05_C04_JOINT_LIMITS", maximum_joint_violation <= spec["acceptance"]["maxJointLimitViolationDeg"], round(maximum_joint_violation, 9), spec["acceptance"]["maxJointLimitViolationDeg"])
    check(checks, "B05_C05_BONE_LENGTH", all_bone_stretch_zero and maximum_length_ratio_error <= 0.0001, round(maximum_length_ratio_error, 12), "<=0.0001 and ik_stretch=0")
    check(checks, "B05_C06_CLOSURE_MONOTONIC", closure_monotonic, [round(value, 9) for value in closure_distances], "non-increasing within 0.0001m and final < initial")
    check(checks, "B05_C07_ACTIVE_CONTACTS", min(active_contacts_per_frame) >= spec["acceptance"]["minimumActiveContacts"], min(active_contacts_per_frame), spec["acceptance"]["minimumActiveContacts"])
    check(checks, "B05_C08_SURFACE_SEPARATION", all(contact["separationRangeM"]["minimum"] <= value <= contact["separationRangeM"]["maximum"] for contact in spec["contactPatches"] for value in separation_values), {"minimumM": round(separation_minimum, 9), "maximumM": round(separation_maximum, 9)}, "each declared contact range")
    check(checks, "B05_C09_OPPOSING_NORMALS", opposing_angle >= spec["acceptance"]["minimumOpposingNormalAngleDeg"], round(opposing_angle, 9), spec["acceptance"]["minimumOpposingNormalAngleDeg"])
    check(checks, "B05_C10_HOLD_DRIFT", relative_drift <= spec["acceptance"]["maxHoldDriftM"], round(relative_drift, 9), spec["acceptance"]["maxHoldDriftM"])
    check(checks, "B05_C11_TRANSPORT", transport >= 0.299, round(transport, 9), ">=0.299m")
    check(checks, "B05_C12_SWITCH_POP", max(acquire_pop, release_pop) <= 0.001, {"acquireM": round(acquire_pop, 9), "releaseM": round(release_pop, 9)}, "<=0.001m")
    check(checks, "B05_C13_ATTACHMENT_CONTRACT", attachment_contract_ok, attachment_states, "0→1 HOLD→0 Child Of palm")
    check(checks, "B05_C14_NO_SHARED_CARRIER", no_shared_carrier, {"sharedAncestors": shared_non_scene_carriers, "actorAncestors": sorted(actor_ancestors), "propAncestors": sorted(prop_ancestors), "independentTransport": independent_transport}, "no shared non-scene parent/carrier")
    check(checks, "B05_C15_VISIBLE_MESH_FOLLOWS_POSE", maximum_segment_alignment_error <= 0.001, round(maximum_segment_alignment_error, 9), "<=0.001m evaluated segment centroid to pose-bone midpoint")

    report = {
        "documentType": "BFS_B05_COMPILED_GRASP_EVALUATION",
        "version": "0.1.0",
        "environment": {"blender": bpy.app.version_string},
        "buildPlan": {"version": wrapper["planVersion"], "hash": wrapper["planHash"]},
        "missingObjects": missing_objects,
        "measurements": {
            "maximumJointLimitViolationDeg": round(maximum_joint_violation, 9),
            "maximumBoneLengthRatioError": round(maximum_length_ratio_error, 12),
            "maximumVisibleSegmentAlignmentErrorM": round(maximum_segment_alignment_error, 9),
            "holdSurfaceSeparationMinimumM": round(separation_minimum, 9),
            "holdSurfaceSeparationMaximumM": round(separation_maximum, 9),
            "minimumActiveContacts": min(active_contacts_per_frame),
            "opposingNormalAngleDeg": round(opposing_angle, 9),
            "holdRelativeDriftM": round(relative_drift, 9),
            "holdTransportM": round(transport, 9),
            "acquirePopM": round(acquire_pop, 9),
            "releasePopM": round(release_pop, 9),
            "closureDistancesM": [round(value, 9) for value in closure_distances],
        },
        "checks": checks,
        "allMachineChecksPassed": all(item["pass"] for item in checks),
        "jointSamples": joint_rows,
        "humanReview": {"status": "PENDING", "requiredAuthenticIndependentResponses": 3, "received": 0},
        "explicitNonClaims": [
            "This is deterministic kinematic IK, not force closure, frictional support, collision response, or dynamics.",
            "The technical gripper does not establish photoreal anatomy, skin deformation, material credibility, or human performance quality.",
            "Visibility and authentic human review are separate unresolved gates.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(f"{json.dumps(report, indent=2)}\n", encoding="utf-8")
    print(f"BFS_B05_COMPILED_GRASP_EVALUATION {'PASS' if report['allMachineChecksPassed'] else 'FAIL'} {args.output}")
    if not report["allMachineChecksPassed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as error:
        print(f"BFS_B05_COMPILED_GRASP_EVALUATION_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
