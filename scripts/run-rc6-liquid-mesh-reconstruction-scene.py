#!/usr/bin/env python3
"""Vary mesh reconstruction radius with simulation conservation fixed at 1.6."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-liquid-component-diagnostic-scene.py")
EXPECTED_BASE_SHA256 = "581752d5407f4688a3298badffdbe3099782bcee7d865b2de50f9f4f89d68142"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 mesh-reconstruction scene base identity mismatch")


def replace_unique(source, before, after, label):
    count = source.count(before)
    if count != 1:
        raise RuntimeError(f"RC6 mesh-reconstruction {label} target count is {count}, expected 1")
    return source.replace(before, after)


source = BASE.read_text(encoding="utf-8")
injection_anchor = "injection = r'''\nsource = replace_unique("
injection_prefix = """injection = r'''
source = replace_unique(
    source,
    '    parser.add_argument("--particle-number", type=int, required=True)\\n    return parser.parse_args(values)',
    '    parser.add_argument("--particle-number", type=int, required=True)\\n    parser.add_argument("--mesh-particle-radius", type=float, required=True)\\n    return parser.parse_args(values)',
    "mesh-radius argument",
)

source = replace_unique(
    source,
    '        bpy.ops.fluid.bake_data()\\n        bpy.ops.fluid.bake_mesh()\\n\\n    samples = []',
    (
        '        bpy.ops.fluid.bake_data()\\n'
        '        bpy.ops.fluid.bake_mesh()\\n\\n'
        '    if scene.frame_start != 1 or scene.frame_end != args.frame_end or settings.cache_frame_start != 1 or settings.cache_frame_end != args.frame_end:\\n'
        '        raise RuntimeError("mesh-reconstruction cache range changed during bake")\\n'
        '    cache_files = sorted(str(path.relative_to(cache_root)) for path in cache_root.rglob("*") if path.is_file())\\n'
        '    expected_cache_files = sorted(\\n'
        '        [f"config/config_{frame:04d}.uni" for frame in range(1, args.frame_end + 1)]\\n'
        '        + [f"data/fluid_data_{frame:04d}.vdb" for frame in range(1, args.frame_end + 1)]\\n'
        '        + [f"mesh/fluid_mesh_{frame:04d}.bobj.gz" for frame in range(1, args.frame_end + 1)]\\n'
        '    )\\n'
        '    if cache_files != expected_cache_files:\\n'
        '        raise RuntimeError(f"mesh-reconstruction cache file roster mismatch: {cache_files}")\\n\\n'
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
    '    allowed = {\\"mesh-radius-4p0\\": 4.0, \\"mesh-radius-4p5\\": 4.5, \\"mesh-radius-4p75\\": 4.75, \\"mesh-radius-5p0\\": 5.0}',
    "cell roster",
)
source = replace_unique(
    source,
    '    if args.cell_id not in allowed or abs(args.particle_radius - allowed[args.cell_id]) > 1e-12:',
    '    if args.cell_id not in allowed or abs(args.particle_radius - 1.6) > 1e-12 or abs(args.mesh_particle_radius - allowed[args.cell_id]) > 1e-12:',
    "cell identity",
)
source = replace_unique(
    source,
    '        raise RuntimeError(\\"particle-conservation cell identity mismatch\\")',
    '        raise RuntimeError(\\"mesh-reconstruction cell identity mismatch\\")',
    "cell error",
)
source = replace_unique(
    source,
    '    "    settings.mesh_particle_radius = 3.0",',
    '    "    settings.mesh_particle_radius = args.mesh_particle_radius",',
    "dynamic mesh radius",
)
source = replace_unique(
    source,
    '    \'"schemaVersion": "bfs.rc6LiquidParticleConservationCell.v0.1"\',',
    '    \'"schemaVersion": "bfs.rc6LiquidMeshReconstructionCell.v0.1"\',',
    "schema",
)
source = replace_unique(
    source,
    '    \'            "meshParticleRadius": 3.0,\',',
    '    \'            "meshParticleRadius": args.mesh_particle_radius,\',',
    "mesh-radius receipt",
)

exec(compile(source, str(BASE) + "#MESH_RECONSTRUCTION_V01", "exec"), globals(), globals())
