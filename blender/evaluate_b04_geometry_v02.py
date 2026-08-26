"""Run the preregistered B04 evaluated-mesh distance diagnostic."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import closest_point_on_tri


RAY_DIRECTION = Vector((0.812381, 0.329117, 0.481993)).normalized()
RAY_EPSILON_M = 1e-6


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def evaluated_geometry(obj: bpy.types.Object, depsgraph: bpy.types.Depsgraph) -> tuple[list[Vector], list[tuple[int, int, int]], BVHTree]:
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh(preserve_all_data_layers=False, depsgraph=depsgraph)
    try:
        mesh.calc_loop_triangles()
        vertices = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
        triangles = [tuple(triangle.vertices) for triangle in mesh.loop_triangles]
        tree = BVHTree.FromPolygons(vertices, triangles, all_triangles=True, epsilon=0.0)
        return vertices, triangles, tree
    finally:
        evaluated.to_mesh_clear()


def segment_distance(left_start: Vector, left_end: Vector, right_start: Vector, right_end: Vector) -> float:
    # Closest distance between two finite segments (Real-Time Collision Detection).
    u = left_end - left_start
    v = right_end - right_start
    w = left_start - right_start
    a, b, c = u.dot(u), u.dot(v), v.dot(v)
    d, e = u.dot(w), v.dot(w)
    determinant = a * c - b * b
    s_numerator, s_denominator = determinant, determinant
    t_numerator, t_denominator = determinant, determinant
    if determinant < 1e-15:
        s_numerator, s_denominator = 0.0, 1.0
        t_numerator, t_denominator = e, c
    else:
        s_numerator = b * e - c * d
        t_numerator = a * e - b * d
        if s_numerator < 0.0:
            s_numerator, t_numerator, t_denominator = 0.0, e, c
        elif s_numerator > s_denominator:
            s_numerator, t_numerator, t_denominator = s_denominator, e + b, c
    if t_numerator < 0.0:
        t_numerator = 0.0
        if -d < 0.0:
            s_numerator = 0.0
        elif -d > a:
            s_numerator = s_denominator
        else:
            s_numerator, s_denominator = -d, a
    elif t_numerator > t_denominator:
        t_numerator = t_denominator
        if -d + b < 0.0:
            s_numerator = 0.0
        elif -d + b > a:
            s_numerator = s_denominator
        else:
            s_numerator, s_denominator = -d + b, a
    sc = 0.0 if abs(s_numerator) < 1e-15 else s_numerator / s_denominator
    tc = 0.0 if abs(t_numerator) < 1e-15 else t_numerator / t_denominator
    return (w + sc * u - tc * v).length


def triangle_distance(left: tuple[Vector, Vector, Vector], right: tuple[Vector, Vector, Vector]) -> float:
    distances = []
    for point in left:
        distances.append((point - closest_point_on_tri(point, *right)).length)
    for point in right:
        distances.append((point - closest_point_on_tri(point, *left)).length)
    left_edges = ((left[0], left[1]), (left[1], left[2]), (left[2], left[0]))
    right_edges = ((right[0], right[1]), (right[1], right[2]), (right[2], right[0]))
    distances.extend(segment_distance(*left_edge, *right_edge) for left_edge in left_edges for right_edge in right_edges)
    return min(distances)


def exact_surface_distance(
    left_vertices: list[Vector], left_triangles: list[tuple[int, int, int]], left_tree: BVHTree,
    right_vertices: list[Vector], right_triangles: list[tuple[int, int, int]], right_tree: BVHTree,
) -> tuple[float, int]:
    overlaps = left_tree.overlap(right_tree)
    if overlaps:
        return 0.0, len(overlaps)
    minimum = math.inf
    for left_indices in left_triangles:
        left = tuple(left_vertices[index] for index in left_indices)
        for right_indices in right_triangles:
            right = tuple(right_vertices[index] for index in right_indices)
            minimum = min(minimum, triangle_distance(left, right))
    return minimum, 0


def point_inside(point: Vector, tree: BVHTree) -> bool:
    cursor = point + RAY_DIRECTION * RAY_EPSILON_M
    intersections = []
    for _ in range(256):
        location, _normal, _index, _distance = tree.ray_cast(cursor, RAY_DIRECTION)
        if location is None:
            break
        if not intersections or (location - intersections[-1]).length > RAY_EPSILON_M * 4:
            intersections.append(location.copy())
        cursor = location + RAY_DIRECTION * RAY_EPSILON_M * 4
    return len(intersections) % 2 == 1


def inside_depths(vertices: list[Vector], other_tree: BVHTree) -> list[float]:
    depths = []
    for vertex in vertices:
        if point_inside(vertex, other_tree):
            nearest = other_tree.find_nearest(vertex)
            if nearest and nearest[3] is not None:
                depths.append(float(nearest[3]))
    return depths


def main() -> None:
    args = parse_args()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))["plan"]
    phases = plan["geometryEvaluations"][0]["phases"]
    scene = bpy.context.scene
    depsgraph = bpy.context.evaluated_depsgraph_get()
    hand = bpy.data.objects["HAND_R"]
    prop = bpy.data.objects["PROP_BODY"]
    samples = []
    for frame in range(scene.frame_start, scene.frame_end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        left_vertices, left_triangles, left_tree = evaluated_geometry(hand, depsgraph)
        right_vertices, right_triangles, right_tree = evaluated_geometry(prop, depsgraph)
        surface_distance, overlap_pairs = exact_surface_distance(left_vertices, left_triangles, left_tree, right_vertices, right_triangles, right_tree)
        hand_inside = inside_depths(left_vertices, right_tree)
        prop_inside = inside_depths(right_vertices, left_tree)
        phase = next(item["id"] for item in phases if item["frameStart"] <= frame <= item["frameEnd"])
        samples.append({
            "frame": frame,
            "phase": phase,
            "overlapPairs": overlap_pairs,
            "exactUnsignedSurfaceDistanceM": round(surface_distance, 9),
            "handVerticesInsideProp": len(hand_inside),
            "propVerticesInsideHand": len(prop_inside),
            "maxInsideVertexDepthM": round(max(hand_inside + prop_inside, default=0.0), 9),
        })

    summaries = []
    for phase in phases:
        phase_samples = [sample for sample in samples if sample["phase"] == phase["id"]]
        summaries.append({
            "phase": phase["id"],
            "frames": len(phase_samples),
            "framesWithSurfaceOverlap": sum(sample["overlapPairs"] > 0 for sample in phase_samples),
            "maximumOverlapPairs": max(sample["overlapPairs"] for sample in phase_samples),
            "minimumExactUnsignedSurfaceDistanceM": min(sample["exactUnsignedSurfaceDistanceM"] for sample in phase_samples),
            "maximumInsideVertexDepthM": max(sample["maxInsideVertexDepthM"] for sample in phase_samples),
            "maximumInsideVertexCount": max(sample["handVerticesInsideProp"] + sample["propVerticesInsideHand"] for sample in phase_samples),
        })
    hold = next(item for item in summaries if item["phase"] == "HOLD")
    report = {
        "documentType": "BFS_B04_GEOMETRY_DIAGNOSTIC",
        "diagnosticVersion": "0.2.0",
        "blender": {"version": bpy.app.version_string, "buildHash": bpy.app.build_hash.decode("ascii")},
        "planHash": scene.get("bfs_plan_hash", ""),
        "method": {"space": "EVALUATED_WORLD", "rayDirection": [round(value, 9) for value in RAY_DIRECTION], "rayEpsilonM": RAY_EPSILON_M, "frames": 144},
        "phaseSummaries": summaries,
        "samples": samples,
        "finding": {
            "holdDepthExceedsV01PositionTolerance": hold["maximumInsideVertexDepthM"] > 0.005,
            "v01PositionToleranceM": 0.005,
            "classification": "V01_AUTOMATIC_PASS_INSUFFICIENT_FOR_CONTACT_QUALITY" if hold["maximumInsideVertexDepthM"] > 0.005 else "NO_MATERIAL_INSIDE_VERTEX_DEPTH_DETECTED",
        },
        "explicitNonClaims": [
            "Inside-vertex depth is not exact minimum translation distance, penetration volume, force, pressure, or a signed distance field.",
            "The parity test assumes closed, non-self-intersecting meshes and may fail at degenerate ray/triangle configurations.",
            "Surface crossings can exist without any sampled vertex being inside the opposite mesh.",
            "This diagnostic does not retroactively change the preregistered B04 v0.1 result.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_B04_GEOMETRY_V02 {report['finding']['classification']} {hold['maximumInsideVertexDepthM']:.9f}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B04_GEOMETRY_V02_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
