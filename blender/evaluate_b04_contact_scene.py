"""Evaluate the preregistered B04 pickup metrics from a compiled Blender scene."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Euler, Matrix
from mathutils.bvhtree import BVHTree


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def rounded(values) -> list[float]:
    return [round(float(value), 9) for value in values]


def transform_matrix(transform: dict) -> Matrix:
    return (
        Matrix.Translation(transform["locationM"])
        @ Euler([math.radians(value) for value in transform["rotationEulerDeg"]], "XYZ").to_matrix().to_4x4()
        @ Matrix.Diagonal((*transform["scale"], 1.0))
    )


def angle_deg(left: Matrix, right: Matrix) -> float:
    relative = left.to_quaternion().rotation_difference(right.to_quaternion())
    return math.degrees(relative.angle)


def evaluated_bvh(obj: bpy.types.Object, depsgraph: bpy.types.Depsgraph) -> tuple[BVHTree, list]:
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh(preserve_all_data_layers=False, depsgraph=depsgraph)
    try:
        vertices = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
        polygons = [list(polygon.vertices) for polygon in mesh.polygons]
        return BVHTree.FromPolygons(vertices, polygons, all_triangles=False, epsilon=0.0), vertices
    finally:
        evaluated.to_mesh_clear()


def proximity_sample(left_tree: BVHTree, left_vertices: list, right_tree: BVHTree, right_vertices: list) -> float:
    distances = []
    for vertex in left_vertices:
        nearest = right_tree.find_nearest(vertex)
        if nearest:
            distances.append(nearest[3])
    for vertex in right_vertices:
        nearest = left_tree.find_nearest(vertex)
        if nearest:
            distances.append(nearest[3])
    return min(distances) if distances else math.inf


def check(check_id: str, passed: bool, measured, threshold, detail: str) -> dict:
    return {"id": check_id, "pass": bool(passed), "measured": measured, "threshold": threshold, "detail": detail}


def main() -> None:
    args = parse_args()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))["plan"]
    scene = bpy.context.scene
    depsgraph = bpy.context.evaluated_depsgraph_get()
    actor = plan["actors"][0]
    actor_spec = actor["actorSpec"]
    actor_collection = bpy.data.collections[actor["assetRef"]]
    actor_objects = {obj.name: obj for obj in actor_collection.all_objects}
    rig = actor_objects[actor_spec["rig"]["armatureObject"]]
    prop_root = bpy.data.objects["PROP_B04"]
    prop_collection = bpy.data.collections["PROP_B04"]
    prop_objects = {obj.name: obj for obj in prop_collection.all_objects}
    hand = actor_objects["HAND_R"]
    prop = prop_objects["PROP_BODY"]
    grip = bpy.data.objects["PROP_PICKUP__GRIP"]
    attachment = prop_root.constraints["PROP_TO_RIGHT_HAND"]
    socket_spec = next(item for item in actor_spec["sockets"] if item["id"] == "PALM_R")
    bone_name = next(item["bone"] for item in actor_spec["rig"]["bones"] if item["semantic"] == socket_spec["boneSemantic"])
    socket_offset = transform_matrix(socket_spec["offset"])

    samples = []
    overlap_by_phase = {phase["id"]: 0 for phase in plan["geometryEvaluations"][0]["phases"]}
    max_overlap_by_phase = {phase["id"]: 0 for phase in plan["geometryEvaluations"][0]["phases"]}
    clearances = {}
    for frame in range(scene.frame_start, scene.frame_end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        evaluated_rig = rig.evaluated_get(depsgraph)
        palm_matrix = evaluated_rig.matrix_world @ evaluated_rig.pose.bones[bone_name].matrix @ socket_offset
        grip_matrix = grip.evaluated_get(depsgraph).matrix_world.copy()
        prop_matrix = prop.evaluated_get(depsgraph).matrix_world.copy()
        position_error = (palm_matrix.translation - grip_matrix.translation).length
        rotation_error = angle_deg(palm_matrix, grip_matrix)
        phase = next(item["id"] for item in plan["geometryEvaluations"][0]["phases"] if item["frameStart"] <= frame <= item["frameEnd"])
        left_tree, left_vertices = evaluated_bvh(hand, depsgraph)
        right_tree, right_vertices = evaluated_bvh(prop, depsgraph)
        overlap_count = len(left_tree.overlap(right_tree))
        overlap_by_phase[phase] += overlap_count
        max_overlap_by_phase[phase] = max(max_overlap_by_phase[phase], overlap_count)
        if frame in {1, 144}:
            clearances[str(frame)] = proximity_sample(left_tree, left_vertices, right_tree, right_vertices)
        samples.append({
            "frame": frame,
            "phase": phase,
            "influence": round(float(attachment.influence), 9),
            "palmLocationM": rounded(palm_matrix.translation),
            "gripLocationM": rounded(grip_matrix.translation),
            "propLocationM": rounded(prop_matrix.translation),
            "palmRotationQuaternion": rounded(palm_matrix.to_quaternion()),
            "gripRotationQuaternion": rounded(grip_matrix.to_quaternion()),
            "positionErrorM": round(position_error, 9),
            "rotationErrorDeg": round(rotation_error, 9),
            "overlapPairs": overlap_count,
        })

    held = [item for item in samples if item["phase"] == "HOLD"]
    relative_matrices = []
    for frame in range(49, 109):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        evaluated_rig = rig.evaluated_get(depsgraph)
        palm_matrix = evaluated_rig.matrix_world @ evaluated_rig.pose.bones[bone_name].matrix @ socket_offset
        grip_matrix = grip.evaluated_get(depsgraph).matrix_world.copy()
        relative_matrices.append(palm_matrix.inverted() @ grip_matrix)
    baseline_relative = relative_matrices[0]
    relative_position_drift = max((matrix.translation - baseline_relative.translation).length for matrix in relative_matrices)
    relative_rotation_drift = max(angle_deg(matrix, baseline_relative) for matrix in relative_matrices)
    transport = sum((left - right) ** 2 for left, right in zip(held[-1]["propLocationM"], held[0]["propLocationM"])) ** 0.5
    approach_distances = [
        math.sqrt(sum((left - right) ** 2 for left, right in zip(item["palmLocationM"], item["gripLocationM"])))
        for item in samples if 25 <= item["frame"] <= 36
    ]
    approach_monotonic = all(right <= left + 1e-9 for left, right in zip(approach_distances, approach_distances[1:])) and approach_distances[-1] < approach_distances[0]
    acquire_step = math.sqrt(sum((a - b) ** 2 for a, b in zip(samples[47]["propLocationM"], samples[46]["propLocationM"])))
    release_step = math.sqrt(sum((a - b) ** 2 for a, b in zip(samples[108]["propLocationM"], samples[107]["propLocationM"])))
    hold_max_position = max(item["positionErrorM"] for item in held)
    hold_max_rotation = max(item["rotationErrorDeg"] for item in held)
    influence_samples = {str(frame): samples[frame - 1]["influence"] for frame in (1, 47, 48, 49, 108, 109, 144)}

    checks = [
        check("B04_C01_CONSTRAINT_BINDING", attachment.type == "CHILD_OF" and attachment.target == rig and attachment.subtarget == bone_name, {"type": attachment.type, "target": attachment.target.name if attachment.target else None, "subtarget": attachment.subtarget}, "CHILD_OF → RIG_LEAD.hand.R", "Restricted constraint resolves to the declared actor hand."),
        check("B04_C02_INFLUENCE_STATES", influence_samples == {"1": 0.0, "47": 0.0, "48": 1.0, "49": 1.0, "108": 1.0, "109": 0.0, "144": 0.0}, influence_samples, "0 / 0 / 1 / 1 / 1 / 0 / 0", "Evaluated parent-switch states match the contract."),
        check("B04_C03_APPROACH_MONOTONIC", approach_monotonic, [round(value, 9) for value in approach_distances], "non-increasing with strict net decrease", "Final twelve APPROACH frames move toward the real prop socket."),
        check("B04_C04_HOLD_POSITION", hold_max_position <= 0.005, hold_max_position, "<= 0.005 m", "Maximum evaluated palm-to-grip position error during HOLD."),
        check("B04_C05_HOLD_ROTATION", hold_max_rotation <= 3.0, hold_max_rotation, "<= 3 deg", "Maximum evaluated palm-to-grip rotation error during HOLD."),
        check("B04_C06_RELATIVE_DRIFT", relative_position_drift <= 0.005 and relative_rotation_drift <= 3.0, {"positionM": round(relative_position_drift, 9), "rotationDeg": round(relative_rotation_drift, 9)}, "<= 0.005 m and <= 3 deg", "Held relative transform remains stable."),
        check("B04_C07_TRANSPORT", transport >= 0.30, round(transport, 9), ">= 0.30 m", "Visible prop transport during HOLD."),
        check("B04_C08_SWITCH_POP", acquire_step <= 0.01 and release_step <= 0.01, {"acquireM": round(acquire_step, 9), "releaseM": round(release_step, 9)}, "<= 0.01 m", "Prop discontinuity across acquire and release switches."),
        check("B04_C09_CLEAR_PHASE_OVERLAP", max_overlap_by_phase["APPROACH"] == 0 and max_overlap_by_phase["RETREAT"] == 0, max_overlap_by_phase, "APPROACH=0 and RETREAT=0 pairs", "BVH source-polygon face-pair overlap is evaluated every frame."),
        check("B04_C10_ENDPOINT_CLEARANCE", clearances["1"] >= 0.05 and clearances["144"] >= 0.05, {key: round(value, 9) for key, value in clearances.items()}, ">= 0.05 m", "Vertex-to-surface proximity samples at endpoints."),
    ]
    report = {
        "documentType": "BFS_B04_CONTACT_EVALUATION",
        "evaluationVersion": "0.1.0",
        "blender": {"version": bpy.app.version_string, "buildHash": bpy.app.build_hash.decode("ascii")},
        "planHash": plan and bpy.context.scene.get("bfs_plan_hash", ""),
        "checks": checks,
        "allMachineChecksPassed": all(item["pass"] for item in checks),
        "geometry": {"overlapPairTotals": overlap_by_phase, "maxOverlapPairsPerFrame": max_overlap_by_phase, "endpointClearanceSamplesM": {key: round(value, 9) for key, value in clearances.items()}},
        "samples": samples,
        "humanReview": {"status": "PENDING", "required": True},
        "explicitNonClaims": [
            "The v0.1 BVH receives source polygons without explicit tessellation; overlap pairs are face-index pairs, not penetration depth or contact pressure.",
            "Vertex-to-surface proximity is a sampled clearance estimate, not an exact signed distance.",
            "Machine checks cannot establish anatomical grasp quality or believable weight.",
            "Human review remains pending and B04 is not complete while it is pending.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_B04_EVALUATION {'PASS' if report['allMachineChecksPassed'] else 'FAIL'} {sum(item['pass'] for item in checks)}/{len(checks)}")
    if not report["allMachineChecksPassed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
