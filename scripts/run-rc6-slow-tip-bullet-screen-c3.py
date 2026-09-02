#!/usr/bin/env python3
"""C3 runner routing the explicit-hinge screen to attempt-50."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-slow-tip-bullet-screen.py")
EXPECTED_BASE_SHA256 = "1e238d2662c7df828b16d7d6c61ff1baac90cf2e44c617ab56da90ec996de8ec"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("slow-tip C3 runner base identity mismatch")

source = BASE.read_text(encoding="utf-8")
replacements = (
    ("RC6-2026-09-02-slow-tip-bullet-screen-attempt-47", "RC6-2026-09-02-slow-tip-bullet-screen-c3-attempt-50", 2, "roots"),
    ('scripts/run-rc6-slow-tip-bullet-screen-scene.py', 'scripts/run-rc6-slow-tip-bullet-screen-c3-scene.py', 1, "scene tool"),
    ('scripts/audit-rc6-slow-tip-bullet-screen.py', 'scripts/audit-rc6-slow-tip-bullet-screen-c3.py', 1, "auditor"),
    ('specs/ai-native-studio-rc6-slow-tip-bullet-screen.v0.55.json', 'specs/ai-native-studio-rc6-slow-tip-bullet-screen-c3.v0.58.json', 1, "spec"),
    ('CELLS = (("D12", 12), ("D16", 16), ("D20", 20), ("D24", 24))', 'CELLS = (("C3D16", 16), ("C3D20", 20), ("C3D24", 24), ("C3D28", 28))', 1, "cells"),
    ('bfs.rc6SlowTipBulletScreen', 'bfs.rc6SlowTipBulletScreenC3', 2, "schemas"),
    ('RC6_SLOW_TIP_BULLET_SCREEN=', 'RC6_SLOW_TIP_BULLET_SCREEN_C3=', 1, "cell marker"),
    ('RC6_SLOW_TIP_BULLET_SCREEN_RUN=', 'RC6_SLOW_TIP_BULLET_SCREEN_C3_RUN=', 1, "run marker"),
    ('The slowest passing Bullet-only cause among four frozen candidates', 'The slowest passing C3 hinged Bullet-only cause among four frozen candidates', 1, "claim"),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"slow-tip C3 runner {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#C3_ATTEMPT50", "exec"), globals(), globals())

