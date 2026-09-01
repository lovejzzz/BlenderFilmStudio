#!/usr/bin/env python3
"""Adapt the frozen RC6 static control to a local domain and source-bound metrics."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-liquid-static-calibration-scene.py")
EXPECTED_BASE_SHA256 = "4ee27ef3e381bbc6275d18044f97194a825b3d935f0b2bc604f09232d26ced48"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 local static base identity mismatch")


def replace_unique(source, before, after, label):
    count = source.count(before)
    if count != 1:
        raise RuntimeError(f"RC6 local static {label} target count is {count}, expected 1")
    return source.replace(before, after)


source = BASE.read_text(encoding="utf-8")

source = replace_unique(
    source,
    '            "preContactOnly": true,',
    '            "preContactOnly": True,',
    "Python boolean literal",
)

source = replace_unique(
    source,
    "def fluid_quality(domain):",
    '''LOCAL_DOMAIN_CENTER = (0.32, 0.0, 0.25)
LOCAL_DOMAIN_DIMENSIONS = (0.36, 0.36, 0.5)
LOCAL_BASE_VOXEL_METERS = 0.5 / 96.0
EXPECTED_SOURCE_MESH_VOLUME = 0.0013283283766940559
EXPECTED_SOURCE_DIMENSIONS = (0.11, 0.11, 0.14)
CUP_INNER_RADIUS_METERS = 0.09
CUP_INTERIOR_BOTTOM_LOCAL_Z = -0.16
CUP_INTERIOR_TOP_LOCAL_Z = 0.22


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def closed_object_mesh_volume(obj):
    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        bm.transform(obj.matrix_world)
        if any(len(edge.link_faces) != 2 for edge in bm.edges):
            raise RuntimeError(f"source mesh is not closed: {obj.name}")
        return abs(bm.calc_volume(signed=True))
    finally:
        bm.free()


def fluid_quality(domain):''',
    "geometry helpers",
)

source = replace_unique(
    source,
    "        return {\n            \"vertexCount\": vertex_count,",
    '''        cup = bpy.data.objects["PHYS_OPEN_TUMBLER"]
        world_to_cup = cup.matrix_world.inverted()
        radial_limit = CUP_INNER_RADIUS_METERS + LOCAL_BASE_VOXEL_METERS
        bottom_limit = CUP_INTERIOR_BOTTOM_LOCAL_Z - LOCAL_BASE_VOXEL_METERS
        top_limit = CUP_INTERIOR_TOP_LOCAL_Z + LOCAL_BASE_VOXEL_METERS
        outside_count = 0
        world_points = []
        for vertex in mesh.vertices:
            world = evaluated.matrix_world @ vertex.co
            local = world_to_cup @ world
            world_points.append(world)
            if (local.x * local.x + local.y * local.y) ** 0.5 > radial_limit or local.z < bottom_limit or local.z > top_limit:
                outside_count += 1
        return {
            "vertexCount": vertex_count,''',
    "cup containment measurement",
)

source = replace_unique(
    source,
    '            "nonManifoldEdgeCount": non_manifold,',
    '''            "nonManifoldEdgeCount": non_manifold,
            "outsideCupInteriorPlusOneVoxelFraction": round(outside_count / vertex_count, 8),
            "boundsMinWorld": [round(min(point[index] for point in world_points), 8) for index in range(3)],
            "boundsMaxWorld": [round(max(point[index] for point in world_points), 8) for index in range(3)],''',
    "quality fields",
)

source = replace_unique(
    source,
    "    settings = domain_modifier.domain_settings\n    if settings.domain_type",
    '''    settings = domain_modifier.domain_settings
    domain.location = LOCAL_DOMAIN_CENTER
    domain.dimensions = LOCAL_DOMAIN_DIMENSIONS
    bpy.ops.object.select_all(action="DESELECT")
    domain.select_set(True)
    bpy.context.view_layer.objects.active = domain
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if max(abs(domain.dimensions[index] - LOCAL_DOMAIN_DIMENSIONS[index]) for index in range(3)) > 1e-6:
        raise RuntimeError("local domain dimensions were not applied exactly")
    if settings.domain_type''',
    "local domain transform",
)

source = replace_unique(
    source,
    "    scene.frame_set(1)\n    bpy.ops.object.select_all(action=\"DESELECT\")",
    '''    scene.frame_set(1)
    bpy.context.view_layer.update()
    source_volume = closed_object_mesh_volume(source)
    source_dimensions = tuple(round(value, 10) for value in source.dimensions)
    if abs(source_volume - EXPECTED_SOURCE_MESH_VOLUME) > 1e-10 or any(abs(source_dimensions[index] - EXPECTED_SOURCE_DIMENSIONS[index]) > 1e-8 for index in range(3)):
        raise RuntimeError("frozen source geometry identity mismatch")
    bpy.ops.object.select_all(action="DESELECT")''',
    "source volume measurement",
)

source = replace_unique(
    source,
    '    drift = [row["meshVolumeCubicMeters"] / initial_volume - 1.0 for row in samples]\n    result = {',
    '''    drift = [row["meshVolumeCubicMeters"] / initial_volume - 1.0 for row in samples]
    source_errors = [row["meshVolumeCubicMeters"] / source_volume - 1.0 for row in samples]
    baked_state_path = work_root / args.cell_id / "baked-state.blend"
    bpy.context.preferences.filepaths.file_preview_type = "NONE"
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(baked_state_path), check_existing=False)
    if not baked_state_path.is_file():
        raise RuntimeError("baked-state blend was not saved")
    result = {''',
    "source errors and baked state",
)

source = replace_unique(
    source,
    '"schemaVersion": "bfs.rc6LiquidStaticCalibrationCell.v0.1"',
    '"schemaVersion": "bfs.rc6LiquidLocalStaticCell.v0.2"',
    "schema version",
)

source = replace_unique(
    source,
    '            "cupEffectorSubframes": 0\n        },',
    '''            "cupEffectorSubframes": 0,
            "domainCenterMeters": list(LOCAL_DOMAIN_CENTER),
            "domainDimensionsMeters": list(LOCAL_DOMAIN_DIMENSIONS),
            "baseVoxelMeters": round(LOCAL_BASE_VOXEL_METERS, 10),
            "sourceDimensionsMeters": list(source_dimensions)
        },''',
    "configuration metrics",
)

source = replace_unique(
    source,
    '            "wallSeconds": round(time.monotonic() - started, 6)\n        },',
    '''            "wallSeconds": round(time.monotonic() - started, 6),
            "sourceMeshVolumeCubicMeters": round(source_volume, 16),
            "maximumAbsoluteSourceVolumeErrorFraction": round(max(abs(value) for value in source_errors), 8),
            "maximumOutsideCupInteriorPlusOneVoxelFraction": max(row["outsideCupInteriorPlusOneVoxelFraction"] for row in samples)
        },''',
    "source-bound metrics",
)

source = replace_unique(
    source,
    '            "sourceFlowBehavior": "GEOMETRY"\n        }',
    '''            "sourceFlowBehavior": "GEOMETRY",
            "blendSaves": 1
        },
        "bakedState": {
            "uri": str(baked_state_path),
            "bytes": baked_state_path.stat().st_size,
            "sha256": file_sha256(baked_state_path)
        }''',
    "baked state receipt",
)

exec(compile(source, str(BASE) + "#LOCAL_DOMAIN_STATIC_V02", "exec"), globals(), globals())
