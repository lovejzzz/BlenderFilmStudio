#!/usr/bin/env python3
"""C2 auditor for the coherent-roster obstacle level-set screen."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-liquid-obstacle-voxel-screen.py")
EXPECTED_BASE_SHA256 = "24ccdf95edf4a2fe4eb2b9face1f6075bd3039262f52f983e419b9b3cd28d622"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("obstacle-voxel C2 auditor base identity mismatch")


source = BASE.read_text(encoding="utf-8")
replacements = (
    ("RC6-2026-09-02-obstacle-voxel-screen-attempt-39", "RC6-2026-09-02-obstacle-voxel-screen-c2-attempt-41", 2, "roots"),
    ("scripts/run-rc6-liquid-obstacle-voxel-screen-scene.py", "scripts/run-rc6-liquid-obstacle-voxel-screen-scene-c2.py", 1, "scene tool"),
    ("scripts/run-rc6-liquid-obstacle-voxel-screen.py", "scripts/run-rc6-liquid-obstacle-voxel-screen-c2.py", 1, "runner"),
    ("specs/ai-native-studio-rc6-liquid-obstacle-voxel-screen.v0.41.json", "specs/ai-native-studio-rc6-liquid-obstacle-voxel-screen-c2.v0.43.json", 1, "spec"),
    ("bfs.rc6LiquidObstacleVoxelScreenIndependentAudit.v0.1", "bfs.rc6LiquidObstacleVoxelScreenC2IndependentAudit.v0.1", 1, "schema"),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"obstacle-voxel C2 auditor {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#OBSTACLE_VOXEL_SCREEN_C2_AUDITOR_V01", "exec"), globals(), globals())
