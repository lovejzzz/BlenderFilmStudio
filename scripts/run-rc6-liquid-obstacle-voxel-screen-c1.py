#!/usr/bin/env python3
"""C1 runner: repeat the unchanged three-cell screen in fresh attempt-40 roots."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-liquid-obstacle-voxel-screen.py")
EXPECTED_BASE_SHA256 = "9c6921716b903307282d69c020ac7d9cefb82d611226362abfcd367d5bf175f5"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("obstacle-voxel C1 runner base identity mismatch")


source = BASE.read_text(encoding="utf-8")
replacements = (
    ("RC6-2026-09-02-obstacle-voxel-screen-attempt-39", "RC6-2026-09-02-obstacle-voxel-screen-c1-attempt-40", 2, "roots"),
    ("scripts/run-rc6-liquid-obstacle-voxel-screen-scene.py", "scripts/run-rc6-liquid-obstacle-voxel-screen-scene-c1.py", 1, "scene tool"),
    ("scripts/audit-rc6-liquid-obstacle-voxel-screen.py", "scripts/audit-rc6-liquid-obstacle-voxel-screen-c1.py", 1, "auditor"),
    ("specs/ai-native-studio-rc6-liquid-obstacle-voxel-screen.v0.41.json", "specs/ai-native-studio-rc6-liquid-obstacle-voxel-screen-c1.v0.42.json", 1, "spec"),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"obstacle-voxel C1 runner {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#OBSTACLE_VOXEL_SCREEN_C1_RUNNER_V01", "exec"), globals(), globals())
