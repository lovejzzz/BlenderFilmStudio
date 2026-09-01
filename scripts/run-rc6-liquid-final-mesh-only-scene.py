#!/usr/bin/env python3
"""Rebuild only a copied Mantaflow liquid mesh and measure signed topology."""

import argparse
import hashlib
import json
import time
from pathlib import Path

import bmesh
import bpy


EXPECTED_SOURCE_VOLUME = 0.0013283283766941
EXPECTED_SOURCE_DIMENSIONS = (0.1099999994, 0.1099999994, 0.1400000006)
BASE_VOXEL_METERS = 0.5 / 192.0
CUP_INNER_RADIUS_METERS = 0.09
CUP_INTERIOR_BOTTOM_LOCAL_Z = -0.16
CUP_INTERIOR_TOP_LOCAL_Z = 0.22
ALLOWED = {
    "mesh-radius-8p0": 8.0,
    "mesh-radius-9p0": 9.0,
    "mesh-radius-9p5": 9.5,
    "mesh-radius-10p0": 10.0,
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def self_hash(value, field):
    body = dict(value)
    body.pop(field, None)
    return hashlib.sha256(canonical(body).encode()).hexdigest()


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


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
    parser.add_argument("--cell-id", required=True)
    parser.add_argument("--work-root", required=True)
    parser.add_argument("--evidence-root", required=True)
    parser.add_argument("--mesh-particle-radius", type=float, required=True)
    parser.add_argument("--retained-data-manifest-hash", required=True)
    return parser.parse_args(values)


def cache_files(cache_root):
    return sorted(str(path.relative_to(cache_root)) for path in cache_root.rglob("*") if path.is_file())


def expected_data_files():
    return sorted(
        [f"config/config_{frame:04d}.uni" for frame in range(1, 8)]
        + [f"data/fluid_data_{frame:04d}.vdb" for frame in range(1, 8)]
    )


def expected_all_files():
    return sorted(expected_data_files() + [f"mesh/fluid_mesh_{frame:04d}.bobj.gz" for frame in range(1, 8)])


def fluid_quality(domain, cup):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = domain.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        vertex_count = len(mesh.vertices)
        if vertex_count == 0:
            raise RuntimeError("mesh-only reconstruction produced no vertices")
        parent = list(range(vertex_count))

        def find(index):
            while parent[index] != index:
                parent[index] = parent[parent[index]]
                index = parent[index]
            return index

        def union(first, second):
            root_first = find(first)
            root_second = find(second)
            if root_first != root_second:
                parent[root_second] = root_first

        for edge in mesh.edges:
            union(edge.vertices[0], edge.vertices[1])
        components = {}
        for index in range(vertex_count):
            root = find(index)
            components[root] = components.get(root, 0) + 1

        world_to_cup = cup.matrix_world.inverted()
        radial_limit = CUP_INNER_RADIUS_METERS + BASE_VOXEL_METERS
        bottom_limit = CUP_INTERIOR_BOTTOM_LOCAL_Z - BASE_VOXEL_METERS
        top_limit = CUP_INTERIOR_TOP_LOCAL_Z + BASE_VOXEL_METERS
        world_points = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
        outside_count = 0
        for point in world_points:
            local = world_to_cup @ point
            if (local.x * local.x + local.y * local.y) ** 0.5 > radial_limit or local.z < bottom_limit or local.z > top_limit:
                outside_count += 1

        component_faces = {}
        for polygon in mesh.polygons:
            roots = {find(index) for index in polygon.vertices}
            if len(roots) != 1:
                raise RuntimeError("polygon spans component roots")
            component_faces.setdefault(next(iter(roots)), []).append(polygon)
        component_details = []
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
                component_non_manifold = sum(1 for edge in component_mesh.edges if len(edge.link_faces) != 2)
                signed_volume = component_mesh.calc_volume(signed=True) if component_non_manifold == 0 else 0.0
            finally:
                component_mesh.free()
            points = [world_points[index] for index in indices]
            component_outside = 0
            for point in points:
                local = world_to_cup @ point
                if (local.x * local.x + local.y * local.y) ** 0.5 > radial_limit or local.z < bottom_limit or local.z > top_limit:
                    component_outside += 1
            component_details.append({
                "rootVertexIndex": root,
                "vertexCount": len(indices),
                "vertexFraction": round(len(indices) / vertex_count, 8),
                "polygonCount": len(polygons),
                "nonManifoldEdgeCount": component_non_manifold,
                "signedVolumeCubicMeters": round(signed_volume, 10),
                "absoluteVolumeCubicMeters": round(abs(signed_volume), 10),
                "surfaceAreaSquareMeters": round(sum(polygon.area for polygon in polygons), 10),
                "outsideCupInteriorPlusOneVoxelFraction": round(component_outside / len(indices), 8),
                "centroidWorld": [round(sum(point[axis] for point in points) / len(points), 8) for axis in range(3)],
                "boundsMinWorld": [round(min(point[axis] for point in points), 8) for axis in range(3)],
                "boundsMaxWorld": [round(max(point[axis] for point in points), 8) for axis in range(3)],
            })
        component_details.sort(key=lambda row: (-row["absoluteVolumeCubicMeters"], row["rootVertexIndex"]))

        aggregate = bmesh.new()
        try:
            aggregate.from_mesh(mesh)
            aggregate.transform(evaluated.matrix_world)
            non_manifold = sum(1 for edge in aggregate.edges if len(edge.link_faces) != 2)
            volume = abs(aggregate.calc_volume(signed=True)) if non_manifold == 0 else 0.0
        finally:
            aggregate.free()
        return {
            "vertexCount": vertex_count,
            "connectedComponentCount": len(components),
            "largestComponentFraction": round(max(components.values()) / vertex_count, 8),
            "meshVolumeCubicMeters": round(volume, 10),
            "meshSurfaceAreaSquareMeters": round(sum(face.area for face in mesh.polygons), 10),
            "nonManifoldEdgeCount": non_manifold,
            "outsideCupInteriorPlusOneVoxelFraction": round(outside_count / vertex_count, 8),
            "boundsMinWorld": [round(min(point[axis] for point in world_points), 8) for axis in range(3)],
            "boundsMaxWorld": [round(max(point[axis] for point in world_points), 8) for axis in range(3)],
            "components": component_details,
        }
    finally:
        evaluated.to_mesh_clear()


def main():
    args = arguments()
    if args.cell_id not in ALLOWED or abs(args.mesh_particle_radius - ALLOWED[args.cell_id]) > 1e-12:
        raise RuntimeError("mesh-only cell identity mismatch")
    work_root = Path(args.work_root).resolve()
    evidence_root = Path(args.evidence_root).resolve()
    candidate_root = work_root / args.cell_id
    cache_root = candidate_root / "mantaflow-cache"
    expected_blend = candidate_root / "copied-baked-state.blend"
    if Path(bpy.data.filepath).resolve() != expected_blend:
        raise RuntimeError("mesh-only copied blend path mismatch")
    if cache_files(cache_root) != expected_all_files():
        raise RuntimeError("mesh-only initial cache roster mismatch")

    scene = bpy.context.scene
    domain = bpy.data.objects.get("PHYS_LIQUID_DOMAIN")
    cup = bpy.data.objects.get("PHYS_OPEN_TUMBLER")
    source = bpy.data.objects.get("PHYS_INITIAL_LIQUID_VOLUME")
    if domain is None or cup is None or source is None:
        raise RuntimeError("mesh-only scene identity incomplete")
    domain_modifier = next((item for item in domain.modifiers if item.type == "FLUID" and item.fluid_type == "DOMAIN"), None)
    if domain_modifier is None:
        raise RuntimeError("mesh-only domain modifier missing")
    settings = domain_modifier.domain_settings
    resolved_cache = Path(bpy.path.abspath(settings.cache_directory)).resolve()
    if resolved_cache != cache_root:
        raise RuntimeError("mesh-only relative cache resolution mismatch")
    if settings.cache_type != "MODULAR" or not settings.has_cache_baked_data or not settings.has_cache_baked_mesh:
        raise RuntimeError("mesh-only initial baked flags mismatch")
    if settings.resolution_max != 192 or settings.cache_frame_start != 1 or settings.cache_frame_end != 7:
        raise RuntimeError("mesh-only frozen resolution or frame range mismatch")
    if abs(settings.particle_radius - 1.6) > 1e-12 or settings.particle_number != 2:
        raise RuntimeError("mesh-only frozen simulation setting mismatch")
    if any(abs(source.dimensions[index] - EXPECTED_SOURCE_DIMENSIONS[index]) > 1e-8 for index in range(3)):
        raise RuntimeError("mesh-only source dimensions mismatch")

    started = time.monotonic()
    scene.frame_start = 1
    scene.frame_end = 7
    scene.frame_set(1)
    bpy.ops.object.select_all(action="DESELECT")
    domain.select_set(True)
    bpy.context.view_layer.objects.active = domain
    context = {
        "object": domain,
        "active_object": domain,
        "selected_objects": [domain],
        "selected_editable_objects": [domain],
    }
    with bpy.context.temp_override(**context):
        if "FINISHED" not in bpy.ops.fluid.free_mesh():
            raise RuntimeError("mesh-only free_mesh did not finish")
    if not settings.has_cache_baked_data or settings.has_cache_baked_mesh:
        raise RuntimeError("mesh-only flags after free mismatch")
    if cache_files(cache_root) != expected_data_files():
        raise RuntimeError("mesh-only free changed data roster or retained mesh")
    settings.mesh_particle_radius = args.mesh_particle_radius
    with bpy.context.temp_override(**context):
        if "FINISHED" not in bpy.ops.fluid.bake_mesh():
            raise RuntimeError("mesh-only bake_mesh did not finish")
    if not settings.has_cache_baked_data or not settings.has_cache_baked_mesh:
        raise RuntimeError("mesh-only flags after bake mismatch")
    final_cache_files = cache_files(cache_root)
    if final_cache_files != expected_all_files():
        raise RuntimeError("mesh-only final cache roster mismatch")

    samples = []
    for frame in range(1, 8):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        row = fluid_quality(domain, cup)
        row["frame"] = frame
        samples.append(row)
    initial_volume = samples[0]["meshVolumeCubicMeters"]
    if initial_volume <= 0:
        raise RuntimeError("mesh-only initial volume is not positive")
    drift = [row["meshVolumeCubicMeters"] / initial_volume - 1.0 for row in samples]
    source_errors = [row["meshVolumeCubicMeters"] / EXPECTED_SOURCE_VOLUME - 1.0 for row in samples]

    output_blend = candidate_root / "mesh-reconstructed-state.blend"
    bpy.context.preferences.filepaths.file_preview_type = "NONE"
    settings.cache_directory = "//mantaflow-cache"
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(output_blend), check_existing=False)
    if not output_blend.is_file():
        raise RuntimeError("mesh-only output blend missing")
    result = {
        "schemaVersion": "bfs.rc6LiquidFinalMeshOnlyCell.v0.1",
        "status": "MEASURED",
        "cellId": args.cell_id,
        "configuration": {
            "frameStart": 1,
            "frameEnd": 7,
            "resolutionMax": 192,
            "baseVoxelMeters": round(BASE_VOXEL_METERS, 10),
            "particleNumber": 2,
            "particleRadius": 1.6,
            "meshScale": settings.mesh_scale,
            "meshParticleRadius": args.mesh_particle_radius,
            "sourceBottomClearanceMeters": 0.0350000039,
            "sourceBottomClearanceVoxels": 13.44000149,
            "sourceDimensionsMeters": list(EXPECTED_SOURCE_DIMENSIONS),
            "retainedDataManifestHash": args.retained_data_manifest_hash,
        },
        "metrics": {
            "initialVolumeCubicMeters": initial_volume,
            "finalVolumeCubicMeters": samples[-1]["meshVolumeCubicMeters"],
            "sourceMeshVolumeCubicMeters": EXPECTED_SOURCE_VOLUME,
            "maximumAbsoluteSourceVolumeErrorFraction": round(max(abs(value) for value in source_errors), 8),
            "maximumAbsoluteVolumeDriftFraction": round(max(abs(value) for value in drift), 8),
            "maximumConnectedComponentCount": max(row["connectedComponentCount"] for row in samples),
            "minimumLargestComponentFraction": min(row["largestComponentFraction"] for row in samples),
            "maximumNonManifoldEdgeCount": max(row["nonManifoldEdgeCount"] for row in samples),
            "maximumOutsideCupInteriorPlusOneVoxelFraction": max(row["outsideCupInteriorPlusOneVoxelFraction"] for row in samples),
            "wallSeconds": round(time.monotonic() - started, 6),
        },
        "samples": samples,
        "cacheFiles": final_cache_files,
        "authority": {
            "retainedDataCopied": True,
            "fluidDataBakes": 0,
            "fluidMeshBakes": 1,
            "blendSaves": 1,
            "renderCalls": 0,
            "networkCalls": 0,
            "engineRemoteWrites": 0,
        },
        "bakedState": {"uri": str(output_blend), "bytes": output_blend.stat().st_size, "sha256": sha(output_blend)},
    }
    result["resultHash"] = self_hash(result, "resultHash")
    write_exclusive(evidence_root / "cells" / args.cell_id / "result.json", result)
    print("RC6_FINAL_MESH_ONLY=" + canonical({"cellId": args.cell_id, "resultHash": result["resultHash"], "metrics": result["metrics"]}), flush=True)


if __name__ == "__main__":
    main()
