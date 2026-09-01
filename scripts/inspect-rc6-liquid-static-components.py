#!/usr/bin/env python3
"""Inspect retained Mantaflow components without baking or rendering."""

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


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
    values = sys.argv[sys.argv.index("--") + 1 :]
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-root", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args(values)


def object_volume(obj):
    mesh = obj.data.copy()
    mesh.transform(obj.matrix_world)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    volume = abs(bm.calc_volume(signed=True))
    bm.free()
    bpy.data.meshes.remove(mesh)
    return volume


def component_metrics(domain, cup):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = domain.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        count = len(mesh.vertices)
        parent = list(range(count))
        sizes = [1] * count

        def find(index):
            while parent[index] != index:
                parent[index] = parent[parent[index]]
                index = parent[index]
            return index

        def union(a, b):
            root_a, root_b = find(a), find(b)
            if root_a == root_b:
                return
            if sizes[root_a] < sizes[root_b]:
                root_a, root_b = root_b, root_a
            parent[root_b] = root_a
            sizes[root_a] += sizes[root_b]

        for edge in mesh.edges:
            union(edge.vertices[0], edge.vertices[1])
        groups = {}
        for index in range(count):
            groups.setdefault(find(index), []).append(index)
        world = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
        cup_inverse = cup.matrix_world.inverted_safe()
        rows = []
        for root, indices in groups.items():
            index_set = set(indices)
            signed_volume = 0.0
            surface_area = 0.0
            polygon_count = 0
            for polygon in mesh.polygons:
                vertices = list(polygon.vertices)
                if not vertices or vertices[0] not in index_set:
                    continue
                polygon_count += 1
                p0 = world[vertices[0]]
                for offset in range(1, len(vertices) - 1):
                    p1, p2 = world[vertices[offset]], world[vertices[offset + 1]]
                    signed_volume += p0.dot(p1.cross(p2)) / 6.0
                    surface_area += (p1 - p0).cross(p2 - p0).length * 0.5
            points = [world[index] for index in indices]
            local_points = [cup_inverse @ point for point in points]
            outside = sum(1 for point in local_points if math.hypot(point.x, point.y) > 0.063 or point.z < -0.105 or point.z > 0.11)
            low = Vector((min(point.x for point in points), min(point.y for point in points), min(point.z for point in points)))
            high = Vector((max(point.x for point in points), max(point.y for point in points), max(point.z for point in points)))
            center = sum(points, Vector()) / len(points)
            rows.append({
                "vertexCount": len(indices),
                "vertexFraction": round(len(indices) / count, 8),
                "polygonCount": polygon_count,
                "volumeCubicMeters": round(abs(signed_volume), 10),
                "surfaceAreaSquareMeters": round(surface_area, 10),
                "meanVertexWorld": [round(value, 8) for value in center],
                "boundsMinWorld": [round(value, 8) for value in low],
                "boundsMaxWorld": [round(value, 8) for value in high],
                "outsideExactCupInteriorFraction": round(outside / len(indices), 8),
            })
        rows.sort(key=lambda row: (-row["volumeCubicMeters"], -row["vertexCount"]))
        return rows
    finally:
        evaluated.to_mesh_clear()


def main():
    args = arguments()
    cache_root = Path(args.cache_root).resolve()
    output = Path(args.output).resolve()
    if not cache_root.is_dir() or output.exists():
        raise RuntimeError("component diagnostic input or output identity mismatch")
    scene = bpy.context.scene
    domain = bpy.data.objects["PHYS_LIQUID_DOMAIN"]
    cup = bpy.data.objects["PHYS_OPEN_TUMBLER"]
    source = bpy.data.objects["PHYS_INITIAL_LIQUID_VOLUME"]
    modifier = next(item for item in domain.modifiers if item.type == "FLUID" and item.fluid_type == "DOMAIN")
    settings = modifier.domain_settings
    settings.cache_type = "MODULAR"
    settings.cache_directory = str(cache_root)
    settings.cache_frame_start = 1
    settings.cache_frame_end = 7
    settings.resolution_max = 192
    settings.particle_number = 2
    settings.particle_radius = 1.3
    settings.mesh_scale = 2
    settings.mesh_particle_radius = 2.0

    frames = []
    for frame in (1, 7):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        frames.append({"frame": frame, "components": component_metrics(domain, cup)})
    domain_longest = max(domain.dimensions)
    voxel = domain_longest / settings.resolution_max
    source_volume = object_volume(source)
    report = {
        "schemaVersion": "bfs.rc6LiquidStaticComponentDiagnostic.v0.1",
        "status": "PASS",
        "frames": frames,
        "sourceGeometry": {
            "meshVolumeCubicMeters": round(source_volume, 10),
            "analyticalCylinderVolumeCubicMeters": round(math.pi * 0.057**2 * 0.105, 10),
            "radiusMeters": 0.057,
            "depthMeters": 0.105,
            "radialClearanceToCupInteriorMeters": 0.006,
            "bottomClearanceMeters": 0.0055
        },
        "geometryResolution": {
            "domainLongestDimensionMeters": round(domain_longest, 8),
            "resolutionMax": settings.resolution_max,
            "baseVoxelMeters": round(voxel, 10),
            "cupWallThicknessMeters": 0.005,
            "cupWallThicknessVoxels": round(0.005 / voxel, 8),
            "sourceRadialClearanceVoxels": round(0.006 / voxel, 8),
            "sourceBottomClearanceVoxels": round(0.0055 / voxel, 8),
            "sourceDiameterVoxels": round(0.114 / voxel, 8),
            "sourceDepthVoxels": round(0.105 / voxel, 8)
        },
        "authority": {"fluidDataBakes": 0, "fluidMeshBakes": 0, "renderCalls": 0, "networkCalls": 0, "engineRemoteWrites": 0}
    }
    report["reportHash"] = self_hash(report, "reportHash")
    write_exclusive(output, report)
    print("RC6_COMPONENT_DIAGNOSTIC=" + canonical({"status": report["status"], "reportHash": report["reportHash"]}), flush=True)


if __name__ == "__main__":
    main()
