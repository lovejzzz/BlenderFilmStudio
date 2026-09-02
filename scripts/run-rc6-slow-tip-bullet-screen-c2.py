#!/usr/bin/env python3
"""C2 runner routing the passive-stop screen to attempt-49."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-slow-tip-bullet-screen.py")
EXPECTED_BASE_SHA256 = "1e238d2662c7df828b16d7d6c61ff1baac90cf2e44c617ab56da90ec996de8ec"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("slow-tip C2 runner base identity mismatch")

source = BASE.read_text(encoding="utf-8")
replacements = (
    ("RC6-2026-09-02-slow-tip-bullet-screen-attempt-47", "RC6-2026-09-02-slow-tip-bullet-screen-c2-attempt-49", 2, "roots"),
    ('scripts/run-rc6-slow-tip-bullet-screen-scene.py', 'scripts/run-rc6-slow-tip-bullet-screen-c2-scene.py', 1, "scene tool"),
    ('scripts/audit-rc6-slow-tip-bullet-screen.py', 'scripts/audit-rc6-slow-tip-bullet-screen-c2.py', 1, "auditor"),
    ('specs/ai-native-studio-rc6-slow-tip-bullet-screen.v0.55.json', 'specs/ai-native-studio-rc6-slow-tip-bullet-screen-c2.v0.57.json', 1, "spec"),
    ('CELLS = (("D12", 12), ("D16", 16), ("D20", 20), ("D24", 24))', 'CELLS = (("C2D16", 16), ("C2D20", 20), ("C2D24", 24), ("C2D28", 28))', 1, "cells"),
    ('bfs.rc6SlowTipBulletScreen', 'bfs.rc6SlowTipBulletScreenC2', 2, "schemas"),
    ('RC6_SLOW_TIP_BULLET_SCREEN=', 'RC6_SLOW_TIP_BULLET_SCREEN_C2=', 1, "cell marker"),
    ('RC6_SLOW_TIP_BULLET_SCREEN_RUN=', 'RC6_SLOW_TIP_BULLET_SCREEN_C2_RUN=', 1, "run marker"),
    ('The slowest passing Bullet-only cause among four frozen candidates', 'The slowest passing C2 passive-stop Bullet-only cause among four frozen candidates', 1, "claim"),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"slow-tip C2 runner {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#C2_ATTEMPT49", "exec"), globals(), globals())

