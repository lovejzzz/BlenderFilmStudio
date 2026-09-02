#!/usr/bin/env python3
"""C2 runner: execute the unchanged screen in fresh attempt-41 roots."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-liquid-obstacle-voxel-screen.py")
EXPECTED_BASE_SHA256 = "9c6921716b903307282d69c020ac7d9cefb82d611226362abfcd367d5bf175f5"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("obstacle-voxel C2 runner base identity mismatch")


source = BASE.read_text(encoding="utf-8")
replacements = (
    ("RC6-2026-09-02-obstacle-voxel-screen-attempt-39", "RC6-2026-09-02-obstacle-voxel-screen-c2-attempt-41", 2, "roots"),
    ("scripts/run-rc6-liquid-obstacle-voxel-screen-scene.py", "scripts/run-rc6-liquid-obstacle-voxel-screen-scene-c2.py", 1, "scene tool"),
    ("scripts/audit-rc6-liquid-obstacle-voxel-screen.py", "scripts/audit-rc6-liquid-obstacle-voxel-screen-c2.py", 1, "auditor"),
    ("specs/ai-native-studio-rc6-liquid-obstacle-voxel-screen.v0.41.json", "specs/ai-native-studio-rc6-liquid-obstacle-voxel-screen-c2.v0.43.json", 1, "spec"),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"obstacle-voxel C2 runner {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#OBSTACLE_VOXEL_SCREEN_C2_RUNNER_V01", "exec"), globals(), globals())
