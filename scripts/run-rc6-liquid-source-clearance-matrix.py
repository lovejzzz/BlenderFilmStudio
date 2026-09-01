#!/usr/bin/env python3
"""Adapt the signed-topology matrix to scan only source-bottom clearance."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-liquid-particle-conservation-matrix.py")
EXPECTED_BASE_SHA256 = "06141b8484821c0ea08bf48d1c0a5ca2c424acd5ed72a0acc7c79b90d2c07661"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 source-clearance runner base identity mismatch")


def replace_unique(source, before, after, label):
    count = source.count(before)
    if count != 1:
        raise RuntimeError(f"RC6 source-clearance {label} target count is {count}, expected 1")
    return source.replace(before, after)


source = BASE.read_text(encoding="utf-8")
source = replace_unique(
    source,
    'new_root = "RC6-2026-09-01-particle-conservation-attempt-20"',
    'new_root = "RC6-2026-09-01-source-clearance-attempt-22"',
    "root",
)
source = replace_unique(source, '"scripts/run-rc6-liquid-component-diagnostic-scene.py"', '"scripts/run-rc6-liquid-source-clearance-scene.py"', "scene tool")
source = replace_unique(source, '"scripts/audit-rc6-liquid-particle-conservation-matrix.py"', '"scripts/audit-rc6-liquid-source-clearance-matrix.py"', "audit tool")
source = replace_unique(source, '"specs/ai-native-studio-rc6-liquid-particle-conservation.v0.20.json"', '"specs/ai-native-studio-rc6-liquid-source-clearance.v0.22.json"', "spec")
source = replace_unique(
    source,
    '    \'CELLS = (("sim-radius-1p0", 1.0), ("sim-radius-1p3", 1.3), ("sim-radius-1p6", 1.6), ("sim-radius-2p0", 2.0))\',',
    '    \'CELLS = (("clearance-20mm", 0.020), ("clearance-25mm", 0.025), ("clearance-30mm", 0.030), ("clearance-35mm", 0.035))\',',
    "cells",
)

exec_anchor = 'exec(compile(source, str(BASE) + "#PARTICLE_CONSERVATION_V01", "exec"), globals(), globals())'
extra = r'''
source = replace_unique(
    source,
    '"--resolution", "96", "--frame-end", "7", "--particle-radius", str(radius), "--particle-number", "2",',
    '"--resolution", "96", "--frame-end", "7", "--particle-radius", "1.6", "--particle-number", "2", "--mesh-particle-radius", "4.5", "--source-bottom-clearance", str(radius),',
    "source-clearance argv",
)
source = replace_unique(
    source,
    '            expected_configuration["particleRadius"] = radius',
    '            expected_configuration["particleRadius"] = 1.6\n            expected_configuration["meshParticleRadius"] = 4.5\n            expected_configuration["sourceBottomClearanceMeters"] = radius\n            expected_configuration["sourceBottomClearanceVoxels"] = round(radius / (0.5 / 96.0), 8)',
    "source-clearance configuration",
)
source = replace_unique(
    source,
    '            if not baked_path.is_file() or baked_path.stat().st_size != baked["bytes"] or sha(baked_path) != baked["sha256"]:\n                raise RuntimeError(f"{cell_id}: baked-state identity mismatch")',
    """            if not baked_path.is_file() or baked_path.stat().st_size != baked["bytes"] or sha(baked_path) != baked["sha256"]:
                raise RuntimeError(f"{cell_id}: baked-state identity mismatch")
            expected_cache_files = sorted(
                [f"config/config_{frame:04d}.uni" for frame in range(1, 8)]
                + [f"data/fluid_data_{frame:04d}.vdb" for frame in range(1, 8)]
                + [f"mesh/fluid_mesh_{frame:04d}.bobj.gz" for frame in range(1, 8)]
            )
            cache_root = baked_path.parent / "mantaflow-cache"
            actual_cache_files = sorted(str(path.relative_to(cache_root)) for path in cache_root.rglob("*") if path.is_file())
            if result.get("cacheFiles") != expected_cache_files or actual_cache_files != expected_cache_files:
                raise RuntimeError(f"{cell_id}: exact 1-7 cache file roster mismatch")""",
    "exact cache frame enforcement",
)
if source.count('row["configuration"]["particleRadius"]') != 2:
    raise RuntimeError("RC6 source-clearance particle field count mismatch")
source = source.replace('row["configuration"]["particleRadius"]', 'row["configuration"]["sourceBottomClearanceMeters"]')
source = replace_unique(
    source,
    '"particleRadius": row["configuration"]["sourceBottomClearanceMeters"]',
    '"sourceBottomClearanceMeters": row["configuration"]["sourceBottomClearanceMeters"]',
    "matrix clearance field",
)
source = source.replace("bfs.rc6LiquidParticleConservation", "bfs.rc6LiquidSourceClearance")
source = source.replace("RC6 particle conservation", "RC6 source clearance")
source = source.replace("RC6_PARTICLE_CONSERVATION_MATRIX=", "RC6_SOURCE_CLEARANCE_MATRIX=")
'''
source = replace_unique(source, exec_anchor, extra + "\n" + exec_anchor, "execution injection")

exec(compile(source, str(BASE) + "#SOURCE_CLEARANCE_MATRIX_V01", "exec"), globals(), globals())
