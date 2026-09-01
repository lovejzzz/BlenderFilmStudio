#!/usr/bin/env python3
"""Measure liquid-particle conservation with signed component diagnostics."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-liquid-local-static-scene.py")
EXPECTED_BASE_SHA256 = "d44f1a446090908ede2d53773dcb8ab5a4745f728768bddfecbfc7db4be912f4"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 component diagnostic base identity mismatch")


source = BASE.read_text(encoding="utf-8")
anchor = 'exec(compile(source, str(BASE) + "#LOCAL_DOMAIN_STATIC_V02", "exec"), globals(), globals())'
if source.count(anchor) != 1:
    raise RuntimeError("RC6 component diagnostic execution anchor mismatch")

injection = r'''
source = replace_unique(
    source,
    "    args = arguments()\n    work_root = Path(args.work_root).resolve()",
    """    args = arguments()
    allowed = {\"sim-radius-1p0\": 1.0, \"sim-radius-1p3\": 1.3, \"sim-radius-1p6\": 1.6, \"sim-radius-2p0\": 2.0}
    if args.cell_id not in allowed or abs(args.particle_radius - allowed[args.cell_id]) > 1e-12:
        raise RuntimeError(\"particle-conservation cell identity mismatch\")
    work_root = Path(args.work_root).resolve()""",
    "diagnostic cell identity",
)

source = replace_unique(
    source,
    "    if args.particle_radius not in {1.0, 1.1, 1.2, 1.3}:",
    "    if args.particle_radius not in {1.0, 1.3, 1.6, 2.0}:",
    "particle-conservation radius roster",
)

source = replace_unique(
    source,
    """    settings = domain_modifier.domain_settings
    domain.location = LOCAL_DOMAIN_CENTER""",
    """    settings = domain_modifier.domain_settings
    flow_settings = flow_modifier.flow_settings
    flow_settings.surface_distance = 0.0
    domain.location = LOCAL_DOMAIN_CENTER""",
    "solid source initialization",
)

source = replace_unique(
    source,
    "    settings.mesh_particle_radius = 2.0",
    "    settings.mesh_particle_radius = 3.0",
    "mesh reconstruction radius",
)

source = replace_unique(
    source,
    """            if (local.x * local.x + local.y * local.y) ** 0.5 > radial_limit or local.z < bottom_limit or local.z > top_limit:
                outside_count += 1
        return {""",
    """            if (local.x * local.x + local.y * local.y) ** 0.5 > radial_limit or local.z < bottom_limit or local.z > top_limit:
                outside_count += 1
        component_faces = {}
        for polygon in mesh.polygons:
            roots = {find(index) for index in polygon.vertices}
            if len(roots) != 1:
                raise RuntimeError(\"polygon spans connected-component roots\")
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
            outside = 0
            for point in points:
                local = world_to_cup @ point
                if (local.x * local.x + local.y * local.y) ** 0.5 > radial_limit or local.z < bottom_limit or local.z > top_limit:
                    outside += 1
            component_details.append({
                \"rootVertexIndex\": root,
                \"vertexCount\": len(indices),
                \"vertexFraction\": round(len(indices) / vertex_count, 8),
                \"polygonCount\": len(polygons),
                \"nonManifoldEdgeCount\": component_non_manifold,
                \"signedVolumeCubicMeters\": round(signed_volume, 10),
                \"absoluteVolumeCubicMeters\": round(abs(signed_volume), 10),
                \"surfaceAreaSquareMeters\": round(sum(polygon.area for polygon in polygons), 10),
                \"outsideCupInteriorPlusOneVoxelFraction\": round(outside / len(indices), 8),
                \"centroidWorld\": [round(sum(point[index] for point in points) / len(points), 8) for index in range(3)],
                \"boundsMinWorld\": [round(min(point[index] for point in points), 8) for index in range(3)],
                \"boundsMaxWorld\": [round(max(point[index] for point in points), 8) for index in range(3)],
            })
        component_details.sort(key=lambda row: (-row[\"absoluteVolumeCubicMeters\"], row[\"rootVertexIndex\"]))
        return {""",
    "component geometry",
)

source = replace_unique(
    source,
    '            "nonManifoldEdgeCount": non_manifold,',
    '            "nonManifoldEdgeCount": non_manifold,\n            "components": component_details,',
    "component result field",
)

source = replace_unique(
    source,
    '    bpy.context.preferences.filepaths.file_preview_type = "NONE"\n    scene.frame_set(1)\n    bpy.ops.wm.save_as_mainfile',
    '    bpy.context.preferences.filepaths.file_preview_type = "NONE"\n    scene.frame_set(1)\n    settings.cache_directory = "//mantaflow-cache"\n    bpy.ops.wm.save_as_mainfile',
    "relative cache persistence",
)

source = replace_unique(
    source,
    '"schemaVersion": "bfs.rc6LiquidLocalStaticCell.v0.2"',
    '"schemaVersion": "bfs.rc6LiquidParticleConservationCell.v0.1"',
    "diagnostic schema",
)

source = replace_unique(
    source,
    '            "sourceDimensionsMeters": list(source_dimensions)\n        },',
    '            "sourceDimensionsMeters": list(source_dimensions),\n            "flowVolumeDensityObserved": round(flow_settings.volume_density, 8),\n            "flowSurfaceDistanceCells": 0.0\n        },',
    "source initialization receipt",
)

source = replace_unique(
    source,
    '            "meshParticleRadius": 2.0,',
    '            "meshParticleRadius": 3.0,',
    "mesh radius receipt",
)
'''

source = source.replace(anchor, injection + "\n" + anchor)
exec(compile(source, str(BASE) + "#COMPONENT_DIAGNOSTIC_V01", "exec"), globals(), globals())
