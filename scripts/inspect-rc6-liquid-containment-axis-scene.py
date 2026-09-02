#!/usr/bin/env python3
"""Read one copied baked liquid surface and classify containment by axis."""

import argparse
import hashlib
import json
from pathlib import Path

import bmesh
import bpy


BASE_VOXEL_METERS = 0.5 / 192.0
CUP_INNER_RADIUS_METERS = 0.09
CUP_INTERIOR_BOTTOM_LOCAL_Z = -0.16
CUP_INTERIOR_TOP_LOCAL_Z = 0.22


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def self_hash(value, field):
    body = dict(value)
    body.pop(field, None)
    return hashlib.sha256(canonical(body).encode()).hexdigest()


def write_exclusive(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def arguments():
    values = []
    if "--" in __import__("sys").argv:
        values = __import__("sys").argv[__import__("sys").argv.index("--") + 1 :]
    parser = argparse.ArgumentParser()
    parser.add_argument("--work-root", required=True)
    parser.add_argument("--evidence-root", required=True)
    parser.add_argument("--retained-candidate-manifest-hash", required=True)
    return parser.parse_args(values)


def expected_cache_files():
    return sorted(
        [f"config/config_{frame:04d}.uni" for frame in range(1, 8)]
        + [f"data/fluid_data_{frame:04d}.vdb" for frame in range(1, 8)]
        + [f"mesh/fluid_mesh_{frame:04d}.bobj.gz" for frame in range(1, 8)]
    )


def count_axes(local_points):
    radial_limit = CUP_INNER_RADIUS_METERS + BASE_VOXEL_METERS
    bottom_limit = CUP_INTERIOR_BOTTOM_LOCAL_Z - BASE_VOXEL_METERS
    top_limit = CUP_INTERIOR_TOP_LOCAL_Z + BASE_VOXEL_METERS
    combinations = {name: 0 for name in ("inside", "radialOnly", "belowOnly", "aboveOnly", "radialAndBelow", "radialAndAbove", "belowAndAbove", "allThree")}
    radial = below = above = outside = 0
    for point in local_points:
        is_radial = (point.x * point.x + point.y * point.y) ** 0.5 > radial_limit
        is_below = point.z < bottom_limit
        is_above = point.z > top_limit
        radial += is_radial
        below += is_below
        above += is_above
        outside += is_radial or is_below or is_above
        key = {
            (False, False, False): "inside",
            (True, False, False): "radialOnly",
            (False, True, False): "belowOnly",
            (False, False, True): "aboveOnly",
            (True, True, False): "radialAndBelow",
            (True, False, True): "radialAndAbove",
            (False, True, True): "belowAndAbove",
            (True, True, True): "allThree",
        }[(is_radial, is_below, is_above)]
        combinations[key] += 1
    count = len(local_points)
    return {
        "vertexCount": count,
        "radialCount": radial,
        "belowFloorCount": below,
        "aboveRimCount": above,
        "outsideUnionCount": outside,
        "radialFraction": round(radial / count, 8),
        "belowFloorFraction": round(below / count, 8),
        "aboveRimFraction": round(above / count, 8),
        "outsideUnionFraction": round(outside / count, 8),
        "exclusiveCombinations": combinations,
    }


def measure_frame(domain, cup):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = domain.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        if not mesh.vertices:
            raise RuntimeError("axis diagnostic evaluated an empty liquid mesh")
        parent = list(range(len(mesh.vertices)))

        def find(index):
            while parent[index] != index:
                parent[index] = parent[parent[index]]
                index = parent[index]
            return index

        def union(first, second):
            left, right = find(first), find(second)
            if left != right:
                parent[right] = left

        for edge in mesh.edges:
            union(edge.vertices[0], edge.vertices[1])
        world_to_cup = cup.matrix_world.inverted()
        world_points = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
        local_points = [world_to_cup @ point for point in world_points]
        aggregate_axes = count_axes(local_points)

        component_faces = {}
        for polygon in mesh.polygons:
            roots = {find(index) for index in polygon.vertices}
            if len(roots) != 1:
                raise RuntimeError("axis diagnostic polygon spans component roots")
            component_faces.setdefault(next(iter(roots)), []).append(polygon)
        components = []
        for root, polygons in component_faces.items():
            indices = sorted({index for polygon in polygons for index in polygon.vertices})
            index_map = {old: new for new, old in enumerate(indices)}
            component_mesh = bmesh.new()
            try:
                vertices = [component_mesh.verts.new(mesh.vertices[index].co) for index in indices]
                component_mesh.verts.ensure_lookup_table()
                for polygon in polygons:
                    component_mesh.faces.new([vertices[index_map[index]] for index in polygon.vertices])
                component_mesh.normal_update()
                component_mesh.transform(evaluated.matrix_world)
                non_manifold = sum(1 for edge in component_mesh.edges if len(edge.link_faces) != 2)
                signed_volume = component_mesh.calc_volume(signed=True) if non_manifold == 0 else 0.0
            finally:
                component_mesh.free()
            axes = count_axes([local_points[index] for index in indices])
            axes.update({
                "rootVertexIndex": root,
                "signedVolumeCubicMeters": round(signed_volume, 10),
                "nonManifoldEdgeCount": non_manifold,
                "boundsMinCupLocal": [round(min(local_points[index][axis] for index in indices), 8) for axis in range(3)],
                "boundsMaxCupLocal": [round(max(local_points[index][axis] for index in indices), 8) for axis in range(3)],
            })
            components.append(axes)
        components.sort(key=lambda row: (-abs(row["signedVolumeCubicMeters"]), row["rootVertexIndex"]))
        return {"aggregate": aggregate_axes, "components": components}
    finally:
        evaluated.to_mesh_clear()


def main():
    args = arguments()
    work_root = Path(args.work_root).resolve()
    evidence_root = Path(args.evidence_root).resolve()
    candidate_root = work_root / "axis-control"
    expected_blend = candidate_root / "mesh-reconstructed-state.blend"
    cache_root = candidate_root / "mantaflow-cache"
    if Path(bpy.data.filepath).resolve() != expected_blend:
        raise RuntimeError("axis diagnostic copied blend path mismatch")
    cache_files = sorted(str(path.relative_to(cache_root)) for path in cache_root.rglob("*") if path.is_file())
    if cache_files != expected_cache_files():
        raise RuntimeError("axis diagnostic cache roster mismatch")

    scene = bpy.context.scene
    domain = bpy.data.objects.get("PHYS_LIQUID_DOMAIN")
    cup = bpy.data.objects.get("PHYS_OPEN_TUMBLER")
    if domain is None or cup is None:
        raise RuntimeError("axis diagnostic scene identity incomplete")
    modifier = next((item for item in domain.modifiers if item.type == "FLUID" and item.fluid_type == "DOMAIN"), None)
    cup_modifier = next((item for item in cup.modifiers if item.type == "FLUID" and item.fluid_type == "EFFECTOR"), None)
    if modifier is None:
        raise RuntimeError("axis diagnostic domain modifier missing")
    if cup_modifier is None:
        raise RuntimeError("axis diagnostic cup effector modifier missing")
    settings = modifier.domain_settings
    if Path(bpy.path.abspath(settings.cache_directory)).resolve() != cache_root:
        raise RuntimeError("axis diagnostic relative cache root mismatch")
    if settings.cache_type != "MODULAR" or not settings.has_cache_baked_data or not settings.has_cache_baked_mesh:
        raise RuntimeError("axis diagnostic baked flags mismatch")
    if settings.resolution_max != 192 or settings.cache_frame_start != 1 or settings.cache_frame_end != 7:
        raise RuntimeError("axis diagnostic frozen range mismatch")
    if abs(settings.particle_radius - 1.6) > 1e-6 or settings.particle_number != 2 or abs(settings.mesh_particle_radius - 9.0) > 1e-6:
        raise RuntimeError("axis diagnostic frozen particle setting mismatch")
    if abs(settings.mesh_concave_lower - 0.4) > 1e-6 or abs(settings.mesh_concave_upper - 3.5) > 1e-6 or settings.mesh_smoothen_pos != 1 or settings.mesh_smoothen_neg != 1:
        raise RuntimeError("axis diagnostic frozen reconstruction setting mismatch")

    radial_z_histogram = {}
    for vertex in cup.data.vertices:
        radial = round((vertex.co.x * vertex.co.x + vertex.co.y * vertex.co.y) ** 0.5, 8)
        z_value = round(vertex.co.z, 8)
        key = f"{radial:.8f}@{z_value:.8f}"
        radial_z_histogram[key] = radial_z_histogram.get(key, 0) + 1
    samples = []
    for frame in range(1, 8):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        row = measure_frame(domain, cup)
        row["frame"] = frame
        samples.append(row)

    result = {
        "schemaVersion": "bfs.rc6LiquidContainmentAxisDiagnostic.v0.1",
        "status": "MEASURED_READ_ONLY",
        "cellId": "axis-control",
        "configuration": {
            "frameStart": 1,
            "frameEnd": 7,
            "resolutionMax": 192,
            "baseVoxelMeters": round(BASE_VOXEL_METERS, 10),
            "radialLimitCupLocalMeters": round(CUP_INNER_RADIUS_METERS + BASE_VOXEL_METERS, 10),
            "bottomLimitCupLocalMeters": round(CUP_INTERIOR_BOTTOM_LOCAL_Z - BASE_VOXEL_METERS, 10),
            "topLimitCupLocalMeters": round(CUP_INTERIOR_TOP_LOCAL_Z + BASE_VOXEL_METERS, 10),
            "particleRadius": 1.6,
            "meshParticleRadius": 9.0,
            "meshConcaveLower": 0.4,
            "meshConcaveUpper": 3.5,
            "meshSmoothenPos": 1,
            "meshSmoothenNeg": 1,
            "cupRawMeshRadialZHistogram": radial_z_histogram,
            "cupEffectorSurfaceDistance": round(cup_modifier.effector_settings.surface_distance, 8),
        },
        "samples": samples,
        "cacheFiles": cache_files,
        "retainedCandidateManifestHash": args.retained_candidate_manifest_hash,
        "authority": {
            "copiedCandidateReadOnly": True,
            "fluidDataBakes": 0,
            "fluidMeshBakes": 0,
            "blendSaves": 0,
            "renderCalls": 0,
            "networkCalls": 0,
            "engineRemoteWrites": 0,
        },
    }
    result["resultHash"] = self_hash(result, "resultHash")
    write_exclusive(evidence_root / "cells/axis-control/result.json", result)
    print("RC6_CONTAINMENT_AXIS=" + canonical({"status": result["status"], "resultHash": result["resultHash"]}), flush=True)


if __name__ == "__main__":
    main()
