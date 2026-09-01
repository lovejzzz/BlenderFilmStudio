#!/usr/bin/env python3
"""Vary source-to-cup-floor clearance with liquid solver and mesh settings fixed."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-liquid-component-diagnostic-scene.py")
EXPECTED_BASE_SHA256 = "581752d5407f4688a3298badffdbe3099782bcee7d865b2de50f9f4f89d68142"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 source-clearance scene base identity mismatch")


def replace_unique(source, before, after, label):
    count = source.count(before)
    if count != 1:
        raise RuntimeError(f"RC6 source-clearance {label} target count is {count}, expected 1")
    return source.replace(before, after)


source = BASE.read_text(encoding="utf-8")
injection_anchor = "injection = r'''\nsource = replace_unique("
injection_prefix = """injection = r'''
source = replace_unique(
    source,
    '    parser.add_argument("--particle-number", type=int, required=True)\\n    return parser.parse_args(values)',
    '    parser.add_argument("--particle-number", type=int, required=True)\\n    parser.add_argument("--mesh-particle-radius", type=float, required=True)\\n    parser.add_argument("--source-bottom-clearance", type=float, required=True)\\n    return parser.parse_args(values)',
    "source-clearance arguments",
)

source = replace_unique(
    source,
    'import bpy\\n',
    'import bpy\\nfrom mathutils import Vector\\n',
    "world-space vector import",
)

source = replace_unique(
    source,
    '    scene.frame_set(1)\\n    bpy.context.view_layer.update()\\n    source_volume = closed_object_mesh_volume(source)',
    (
        '    scene.frame_set(1)\\n'
        '    bpy.context.view_layer.update()\\n'
        '    inner_floor_world_z = (cup.matrix_world @ Vector((0.0, 0.0, CUP_INTERIOR_BOTTOM_LOCAL_Z))).z\\n'
        '    source.location.z = inner_floor_world_z + source.dimensions.z * 0.5 + args.source_bottom_clearance\\n'
        '    bpy.context.view_layer.update()\\n'
        '    actual_source_bottom_clearance = source.matrix_world.translation.z - source.dimensions.z * 0.5 - inner_floor_world_z\\n'
        '    if abs(actual_source_bottom_clearance - args.source_bottom_clearance) > 1e-8:\\n'
        '        raise RuntimeError("source-bottom clearance placement mismatch")\\n'
        '    source_volume = closed_object_mesh_volume(source)'
    ),
    "derived source placement",
)

source = replace_unique(
    source,
    '        bpy.ops.fluid.bake_data()\\n        bpy.ops.fluid.bake_mesh()\\n\\n    samples = []',
    (
        '        bpy.ops.fluid.bake_data()\\n'
        '        bpy.ops.fluid.bake_mesh()\\n\\n'
        '    if scene.frame_start != 1 or scene.frame_end != args.frame_end or settings.cache_frame_start != 1 or settings.cache_frame_end != args.frame_end:\\n'
        '        raise RuntimeError("source-clearance cache range changed during bake")\\n'
        '    cache_files = sorted(str(path.relative_to(cache_root)) for path in cache_root.rglob("*") if path.is_file())\\n'
        '    expected_cache_files = sorted(\\n'
        '        [f"config/config_{frame:04d}.uni" for frame in range(1, args.frame_end + 1)]\\n'
        '        + [f"data/fluid_data_{frame:04d}.vdb" for frame in range(1, args.frame_end + 1)]\\n'
        '        + [f"mesh/fluid_mesh_{frame:04d}.bobj.gz" for frame in range(1, args.frame_end + 1)]\\n'
        '    )\\n'
        '    if cache_files != expected_cache_files:\\n'
        '        raise RuntimeError(f"source-clearance cache file roster mismatch: {cache_files}")\\n\\n'
        '    samples = []'
    ),
    "exact cache frame roster",
)

source = replace_unique(
    source,
    '        "samples": samples,',
    '        "samples": samples,\\n        "cacheFiles": cache_files,',
    "cache roster receipt",
)

source = replace_unique("""
source = replace_unique(source, injection_anchor, injection_prefix, "injection prefix")
source = replace_unique(
    source,
    '    allowed = {\\"sim-radius-1p0\\": 1.0, \\"sim-radius-1p3\\": 1.3, \\"sim-radius-1p6\\": 1.6, \\"sim-radius-2p0\\": 2.0}',
    '    allowed = {\\"clearance-20mm\\": 0.020, \\"clearance-25mm\\": 0.025, \\"clearance-30mm\\": 0.030, \\"clearance-35mm\\": 0.035}',
    "cell roster",
)
source = replace_unique(
    source,
    '    if args.cell_id not in allowed or abs(args.particle_radius - allowed[args.cell_id]) > 1e-12:',
    '    if args.cell_id not in allowed or abs(args.particle_radius - 1.6) > 1e-12 or abs(args.mesh_particle_radius - 4.5) > 1e-12 or abs(args.source_bottom_clearance - allowed[args.cell_id]) > 1e-12:',
    "cell identity",
)
source = replace_unique(
    source,
    '        raise RuntimeError(\\"particle-conservation cell identity mismatch\\")',
    '        raise RuntimeError(\\"source-clearance cell identity mismatch\\")',
    "cell error",
)
source = replace_unique(
    source,
    '    "    settings.mesh_particle_radius = 3.0",',
    '    "    settings.mesh_particle_radius = 4.5",',
    "fixed mesh radius",
)
source = replace_unique(
    source,
    '    \'"schemaVersion": "bfs.rc6LiquidParticleConservationCell.v0.1"\',',
    '    \'"schemaVersion": "bfs.rc6LiquidSourceClearanceCell.v0.1"\',',
    "schema",
)
source = replace_unique(
    source,
    '    \'            "meshParticleRadius": 3.0,\',',
    '    \'            "meshParticleRadius": 4.5,\',',
    "mesh-radius receipt",
)
source = replace_unique(
    source,
    '    \'            "sourceDimensionsMeters": list(source_dimensions),\\n            "flowVolumeDensityObserved": round(flow_settings.volume_density, 8),\\n            "flowSurfaceDistanceCells": 0.0\\n        },\',',
    '    \'            "sourceDimensionsMeters": list(source_dimensions),\\n            "sourceBottomClearanceMeters": round(actual_source_bottom_clearance, 10),\\n            "sourceBottomClearanceVoxels": round(actual_source_bottom_clearance / LOCAL_BASE_VOXEL_METERS, 8),\\n            "flowVolumeDensityObserved": round(flow_settings.volume_density, 8),\\n            "flowSurfaceDistanceCells": 0.0\\n        },\',',
    "clearance receipt",
)

exec(compile(source, str(BASE) + "#SOURCE_CLEARANCE_V01", "exec"), globals(), globals())
