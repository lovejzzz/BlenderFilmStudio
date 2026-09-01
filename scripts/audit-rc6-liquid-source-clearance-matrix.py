#!/usr/bin/env python3
"""Independently audit the source-bottom-clearance static liquid matrix."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-liquid-particle-conservation-matrix.py")
EXPECTED_BASE_SHA256 = "d0ce4b86604661e28c5c3a7a3236f5ed726da4d228aff8fe3c9a0152bb5e51f1"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 source-clearance auditor base identity mismatch")


def replace_unique(source, before, after, label):
    count = source.count(before)
    if count != 1:
        raise RuntimeError(f"RC6 source-clearance audit {label} target count is {count}, expected 1")
    return source.replace(before, after)


source = BASE.read_text(encoding="utf-8")
source = replace_unique(
    source,
    'new_root = "RC6-2026-09-01-particle-conservation-attempt-20"',
    'new_root = "RC6-2026-09-01-source-clearance-attempt-22"',
    "root",
)
source = replace_unique(source, '"scripts/run-rc6-liquid-component-diagnostic-scene.py"', '"scripts/run-rc6-liquid-source-clearance-scene.py"', "scene tool")
source = replace_unique(source, '"scripts/run-rc6-liquid-particle-conservation-matrix.py"', '"scripts/run-rc6-liquid-source-clearance-matrix.py"', "runner")
source = replace_unique(source, '"specs/ai-native-studio-rc6-liquid-particle-conservation.v0.20.json"', '"specs/ai-native-studio-rc6-liquid-source-clearance.v0.22.json"', "spec")
source = replace_unique(
    source,
    '    \'CELLS = (("sim-radius-1p0", 1.0), ("sim-radius-1p3", 1.3), ("sim-radius-1p6", 1.6), ("sim-radius-2p0", 2.0))\',',
    '    \'CELLS = (("clearance-20mm", 0.020), ("clearance-25mm", 0.025), ("clearance-30mm", 0.030), ("clearance-35mm", 0.035))\',',
    "cells",
)

exec_anchor = 'exec(compile(source, str(BASE) + "#PARTICLE_CONSERVATION_AUDIT_V01", "exec"), globals(), globals())'
extra = r'''
source = replace_unique(
    source,
    '"--resolution", "96", "--frame-end", "7", "--particle-radius", str(radius), "--particle-number", "2",',
    '"--resolution", "96", "--frame-end", "7", "--particle-radius", "1.6", "--particle-number", "2", "--mesh-particle-radius", "4.5", "--source-bottom-clearance", str(radius),',
    "source-clearance argv",
)
source = replace_unique(
    source,
    '        expected_configuration["particleRadius"] = radius',
    '        expected_configuration["particleRadius"] = 1.6\n        expected_configuration["meshParticleRadius"] = 4.5\n        expected_configuration["sourceBottomClearanceMeters"] = radius\n        expected_configuration["sourceBottomClearanceVoxels"] = round(radius / (0.5 / 96.0), 8)',
    "source-clearance configuration",
)
source = replace_unique(
    source,
    '            "bakedStateExact": baked_path.is_file() and baked_path.stat().st_size == baked["bytes"] and sha(baked_path) == baked["sha256"],',
    """            "bakedStateExact": baked_path.is_file() and baked_path.stat().st_size == baked["bytes"] and sha(baked_path) == baked["sha256"],
            "cacheFramesExact": result.get("cacheFiles") == sorted(
                [f"config/config_{frame:04d}.uni" for frame in range(1, 8)]
                + [f"data/fluid_data_{frame:04d}.vdb" for frame in range(1, 8)]
                + [f"mesh/fluid_mesh_{frame:04d}.bobj.gz" for frame in range(1, 8)]
            ) and sorted(str(path.relative_to(baked_path.parent / "mantaflow-cache")) for path in (baked_path.parent / "mantaflow-cache").rglob("*") if path.is_file()) == sorted(
                [f"config/config_{frame:04d}.uni" for frame in range(1, 8)]
                + [f"data/fluid_data_{frame:04d}.vdb" for frame in range(1, 8)]
                + [f"mesh/fluid_mesh_{frame:04d}.bobj.gz" for frame in range(1, 8)]
            ),""",
    "independent exact cache frame audit",
)
if source.count('row["configuration"]["particleRadius"]') != 2:
    raise RuntimeError("RC6 source-clearance audit particle field count mismatch")
source = source.replace('row["configuration"]["particleRadius"]', 'row["configuration"]["sourceBottomClearanceMeters"]')
source = replace_unique(
    source,
    '"particleRadius": row["configuration"]["sourceBottomClearanceMeters"]',
    '"sourceBottomClearanceMeters": row["configuration"]["sourceBottomClearanceMeters"]',
    "matrix clearance field",
)
source = source.replace("bfs.rc6LiquidParticleConservation", "bfs.rc6LiquidSourceClearance")
source = source.replace("RC6 particle conservation", "RC6 source clearance")
'''
source = replace_unique(source, exec_anchor, extra + "\n" + exec_anchor, "execution injection")

exec(compile(source, str(BASE) + "#SOURCE_CLEARANCE_AUDIT_V01", "exec"), globals(), globals())
