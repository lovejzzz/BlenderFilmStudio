#!/usr/bin/env python3
"""C5-C1 runner routing the sentinel correction to attempt-53."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-slow-tip-bullet-screen-c5.py")
EXPECTED_BASE_SHA256 = "7c1f5d919dca2e74211278b4c6378fea42bfe50785dd0139423fa264bad0438d"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("slow-tip C5-C1 runner base identity mismatch")

source = BASE.read_text(encoding="utf-8")
replacements = (
    ("RC6-2026-09-02-slow-tip-bullet-screen-c5-attempt-52", "RC6-2026-09-02-slow-tip-bullet-screen-c5-c1-attempt-53", 2, "roots"),
    ("scripts/run-rc6-slow-tip-bullet-screen-c5-scene.py", "scripts/run-rc6-slow-tip-bullet-screen-c5-c1-scene.py", 1, "scene tool"),
    ("scripts/audit-rc6-slow-tip-bullet-screen-c5.py", "scripts/audit-rc6-slow-tip-bullet-screen-c5-c1.py", 1, "auditor"),
    ("specs/ai-native-studio-rc6-slow-tip-bullet-screen-c5.v0.60.json", "specs/ai-native-studio-rc6-slow-tip-bullet-screen-c5-c1.v0.61.json", 1, "spec"),
    ("bfs.rc6SlowTipBulletScreenC5", "bfs.rc6SlowTipBulletScreenC5C1", 1, "schemas"),
    ("RC6_SLOW_TIP_BULLET_SCREEN_C5=", "RC6_SLOW_TIP_BULLET_SCREEN_C5_C1=", 1, "cell marker"),
    ("RC6_SLOW_TIP_BULLET_SCREEN_C5_RUN=", "RC6_SLOW_TIP_BULLET_SCREEN_C5_C1_RUN=", 1, "run marker"),
    ("#C5_ATTEMPT52", "#C5_C1_ATTEMPT53", 1, "compile tag"),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"slow-tip C5-C1 runner {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#C5_C1_ATTEMPT53", "exec"), globals(), globals())
