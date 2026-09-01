#!/usr/bin/env python3
"""C2: rebind copied cache and compare reopened RNA floats at float32 precision."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-liquid-final-mesh-only-scene.py")
EXPECTED_BASE_SHA256 = "2e68cb021c860066a1ec24d301fc3684fdee7c94b13077744b68bf6f6bdd4a0c"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 final mesh-only C2 scene base identity mismatch")


source = BASE.read_text(encoding="utf-8")
replacements = (
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
        "if abs(settings.particle_radius - 1.6) > 1e-12 or settings.particle_number != 2:",
        "if abs(settings.particle_radius - 1.6) > 1e-6 or settings.particle_number != 2:",
        "RNA float32 tolerance",
    ),
    (
        '            "retainedDataCopied": True,\n            "fluidDataBakes": 0,',
        '            "retainedDataCopied": True,\n            "cacheDirectoryRebound": True,\n            "rnaFloatTolerance": 1e-6,\n            "fluidDataBakes": 0,',
        "cache authority receipt",
    ),
    ("bfs.rc6LiquidFinalMeshOnlyCell.v0.1", "bfs.rc6LiquidFinalMeshOnlyCell.v0.3", "schema"),
)
for before, after, label in replacements:
    if source.count(before) != 1:
        raise RuntimeError(f"RC6 final mesh-only C2 scene {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#FINAL_MESH_ONLY_C2_V03", "exec"), globals(), globals())
