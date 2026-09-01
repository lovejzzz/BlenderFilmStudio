#!/usr/bin/env python3
"""Rebuild copied resolution-192 liquid data with one concavity variable."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-liquid-final-mesh-only-scene.py")
EXPECTED_BASE_SHA256 = "2e68cb021c860066a1ec24d301fc3684fdee7c94b13077744b68bf6f6bdd4a0c"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 liquid mesh concavity scene base identity mismatch")


source = BASE.read_text(encoding="utf-8")
replacements = (
    (
        '"""Rebuild only a copied Mantaflow liquid mesh and measure signed topology."""',
        '"""Rebuild copied liquid data at fixed radius while varying only upper concavity."""',
        "docstring",
    ),
    (
        '''ALLOWED = {
    "mesh-radius-8p0": 8.0,
    "mesh-radius-9p0": 9.0,
    "mesh-radius-9p5": 9.5,
    "mesh-radius-10p0": 10.0,
}''',
        '''ALLOWED = {
    "concavity-upper-3p50": 3.5,
    "concavity-upper-2p75": 2.75,
    "concavity-upper-2p00": 2.0,
    "concavity-upper-1p25": 1.25,
}''',
        "cell roster",
    ),
    (
        '    parser.add_argument("--mesh-particle-radius", type=float, required=True)\n    parser.add_argument("--retained-data-manifest-hash", required=True)',
        '    parser.add_argument("--mesh-particle-radius", type=float, required=True)\n    parser.add_argument("--mesh-concave-upper", type=float, required=True)\n    parser.add_argument("--retained-data-manifest-hash", required=True)',
        "arguments",
    ),
    (
        '    if args.cell_id not in ALLOWED or abs(args.mesh_particle_radius - ALLOWED[args.cell_id]) > 1e-12:\n        raise RuntimeError("mesh-only cell identity mismatch")',
        '    if args.cell_id not in ALLOWED or abs(args.mesh_particle_radius - 9.0) > 1e-12 or abs(args.mesh_concave_upper - ALLOWED[args.cell_id]) > 1e-12:\n        raise RuntimeError("mesh-only concavity cell identity mismatch")',
        "cell identity",
    ),
    (
        '''    resolved_cache = Path(bpy.path.abspath(settings.cache_directory)).resolve()
    if resolved_cache != cache_root:
        raise RuntimeError("mesh-only relative cache resolution mismatch")
    if settings.cache_type != "MODULAR" or not settings.has_cache_baked_data or not settings.has_cache_baked_mesh:''',
        '''    settings.cache_directory = str(cache_root)
    resolved_cache = Path(bpy.path.abspath(settings.cache_directory)).resolve()
    if resolved_cache != cache_root:
        raise RuntimeError("mesh-only explicit cache rebind mismatch")
    if settings.cache_type != "MODULAR" or not settings.has_cache_baked_data or not settings.has_cache_baked_mesh:''',
        "cache rebind",
    ),
    (
        'if abs(settings.particle_radius - 1.6) > 1e-12 or settings.particle_number != 2:',
        'if abs(settings.particle_radius - 1.6) > 1e-6 or settings.particle_number != 2:',
        "RNA float32 tolerance",
    ),
    (
        '''    if any(abs(source.dimensions[index] - EXPECTED_SOURCE_DIMENSIONS[index]) > 1e-8 for index in range(3)):
        raise RuntimeError("mesh-only source dimensions mismatch")''',
        '''    if any(abs(source.dimensions[index] - EXPECTED_SOURCE_DIMENSIONS[index]) > 1e-8 for index in range(3)):
        raise RuntimeError("mesh-only source dimensions mismatch")
    if abs(settings.mesh_particle_radius - 4.5) > 1e-6 or abs(settings.mesh_concave_lower - 0.4) > 1e-6 or abs(settings.mesh_concave_upper - 3.5) > 1e-6 or settings.mesh_smoothen_pos != 1 or settings.mesh_smoothen_neg != 1:
        raise RuntimeError("mesh-only retained reconstruction defaults mismatch")''',
        "retained reconstruction defaults",
    ),
    (
        '    settings.mesh_particle_radius = args.mesh_particle_radius',
        '    settings.mesh_particle_radius = 9.0\n    settings.mesh_concave_upper = args.mesh_concave_upper\n    if abs(settings.mesh_particle_radius - 9.0) > 1e-6 or abs(settings.mesh_concave_upper - args.mesh_concave_upper) > 1e-6:\n        raise RuntimeError("mesh-only concavity setting readback mismatch")',
        "single-variable setting",
    ),
    (
        '            "meshParticleRadius": args.mesh_particle_radius,',
        '            "meshParticleRadius": 9.0,\n            "meshConcaveLower": 0.4,\n            "meshConcaveUpper": args.mesh_concave_upper,\n            "meshSmoothenPos": 1,\n            "meshSmoothenNeg": 1,',
        "configuration receipt",
    ),
    (
        '            "retainedDataCopied": True,\n            "fluidDataBakes": 0,',
        '            "retainedDataCopied": True,\n            "cacheDirectoryRebound": True,\n            "rnaFloatTolerance": 1e-6,\n            "singleReconstructionVariable": "mesh_concave_upper",\n            "fluidDataBakes": 0,',
        "authority receipt",
    ),
    ("bfs.rc6LiquidFinalMeshOnlyCell.v0.1", "bfs.rc6LiquidMeshConcavityCell.v0.1", "schema"),
)
for before, after, label in replacements:
    if source.count(before) != 1:
        raise RuntimeError(f"RC6 liquid mesh concavity scene {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#LIQUID_MESH_CONCAVITY_V01", "exec"), globals(), globals())
