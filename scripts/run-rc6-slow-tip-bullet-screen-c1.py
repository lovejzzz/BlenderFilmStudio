#!/usr/bin/env python3
"""C1 runner routing the frozen direct-contact screen to attempt-48."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-slow-tip-bullet-screen.py")
EXPECTED_BASE_SHA256 = "1e238d2662c7df828b16d7d6c61ff1baac90cf2e44c617ab56da90ec996de8ec"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("slow-tip C1 runner base identity mismatch")

source = BASE.read_text(encoding="utf-8")
replacements = (
    ("RC6-2026-09-02-slow-tip-bullet-screen-attempt-47", "RC6-2026-09-02-slow-tip-bullet-screen-c1-attempt-48", 2, "roots"),
    ('scripts/run-rc6-slow-tip-bullet-screen-scene.py', 'scripts/run-rc6-slow-tip-bullet-screen-c1-scene.py', 1, "scene tool"),
    ('scripts/audit-rc6-slow-tip-bullet-screen.py', 'scripts/audit-rc6-slow-tip-bullet-screen-c1.py', 1, "auditor"),
    ('specs/ai-native-studio-rc6-slow-tip-bullet-screen.v0.55.json', 'specs/ai-native-studio-rc6-slow-tip-bullet-screen-c1.v0.56.json', 1, "spec"),
    ('CELLS = (("D12", 12), ("D16", 16), ("D20", 20), ("D24", 24))', 'CELLS = (("C1D16", 16), ("C1D20", 20), ("C1D24", 24), ("C1D28", 28))', 1, "cells"),
    ('bfs.rc6SlowTipBulletScreen', 'bfs.rc6SlowTipBulletScreenC1', 2, "schemas"),
    ('RC6_SLOW_TIP_BULLET_SCREEN=', 'RC6_SLOW_TIP_BULLET_SCREEN_C1=', 1, "cell marker"),
    ('RC6_SLOW_TIP_BULLET_SCREEN_RUN=', 'RC6_SLOW_TIP_BULLET_SCREEN_C1_RUN=', 1, "run marker"),
    ('The slowest passing Bullet-only cause among four frozen candidates', 'The slowest passing C1 direct-contact Bullet-only cause among four frozen candidates', 1, "claim"),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"slow-tip C1 runner {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#C1_ATTEMPT48", "exec"), globals(), globals())
