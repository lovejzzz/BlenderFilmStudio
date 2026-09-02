#!/usr/bin/env python3
"""C4 runner routing the limited and damped hinge screen to attempt-51."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-slow-tip-bullet-screen.py")
EXPECTED_BASE_SHA256 = "1e238d2662c7df828b16d7d6c61ff1baac90cf2e44c617ab56da90ec996de8ec"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("slow-tip C4 runner base identity mismatch")

source = BASE.read_text(encoding="utf-8")
replacements = (
    ("RC6-2026-09-02-slow-tip-bullet-screen-attempt-47", "RC6-2026-09-02-slow-tip-bullet-screen-c4-attempt-51", 2, "roots"),
    ('scripts/run-rc6-slow-tip-bullet-screen-scene.py', 'scripts/run-rc6-slow-tip-bullet-screen-c4-scene.py', 1, "scene tool"),
    ('scripts/audit-rc6-slow-tip-bullet-screen.py', 'scripts/audit-rc6-slow-tip-bullet-screen-c4.py', 1, "auditor"),
    ('specs/ai-native-studio-rc6-slow-tip-bullet-screen.v0.55.json', 'specs/ai-native-studio-rc6-slow-tip-bullet-screen-c4.v0.59.json', 1, "spec"),
    ('CELLS = (("D12", 12), ("D16", 16), ("D20", 20), ("D24", 24))', 'CELLS = (("C4D28", 28), ("C4D32", 32), ("C4D36", 36), ("C4D40", 40))', 1, "cells"),
    ('bfs.rc6SlowTipBulletScreen', 'bfs.rc6SlowTipBulletScreenC4', 2, "schemas"),
    ('RC6_SLOW_TIP_BULLET_SCREEN=', 'RC6_SLOW_TIP_BULLET_SCREEN_C4=', 1, "cell marker"),
    ('RC6_SLOW_TIP_BULLET_SCREEN_RUN=', 'RC6_SLOW_TIP_BULLET_SCREEN_C4_RUN=', 1, "run marker"),
    ('The slowest passing Bullet-only cause among four frozen candidates', 'The slowest passing C4 limited and damped hinged Bullet-only cause among four frozen candidates', 1, "claim"),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"slow-tip C4 runner {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#C4_ATTEMPT51", "exec"), globals(), globals())
