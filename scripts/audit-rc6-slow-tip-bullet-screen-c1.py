#!/usr/bin/env python3
"""C1 independent auditor routing exact-surface attempt-48."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-slow-tip-bullet-screen.py")
EXPECTED_BASE_SHA256 = "1cda47e2d4f8df1bfbc15d2075044a721afb9b0995c58f388cbe7d9c39c71679"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("slow-tip C1 auditor base identity mismatch")

source = BASE.read_text(encoding="utf-8")
replacements = (
    ("RC6-2026-09-02-slow-tip-bullet-screen-attempt-47", "RC6-2026-09-02-slow-tip-bullet-screen-c1-attempt-48", 2, "roots"),
    ('CELLS = (("D12", 12), ("D16", 16), ("D20", 20), ("D24", 24))', 'CELLS = (("C1D16", 16), ("C1D20", 20), ("C1D24", 24), ("C1D28", 28))', 1, "cells"),
    ('scripts/run-rc6-slow-tip-bullet-screen-scene.py', 'scripts/run-rc6-slow-tip-bullet-screen-c1-scene.py', 1, "scene tool"),
    ('scripts/run-rc6-slow-tip-bullet-screen.py', 'scripts/run-rc6-slow-tip-bullet-screen-c1.py', 1, "runner"),
    ('specs/ai-native-studio-rc6-slow-tip-bullet-screen.v0.55.json', 'specs/ai-native-studio-rc6-slow-tip-bullet-screen-c1.v0.56.json', 1, "spec"),
    ('ballCupSurfaceSeparationMeters', 'actuatorCupSurfaceSeparationMeters', 1, "contact samples"),
    ('bfs.rc6SlowTipBulletScreenIndependentAudit.v0.1', 'bfs.rc6SlowTipBulletScreenC1IndependentAudit.v0.1', 1, "schema"),
    ('RC6_SLOW_TIP_BULLET_SCREEN_AUDIT=', 'RC6_SLOW_TIP_BULLET_SCREEN_C1_AUDIT=', 1, "marker"),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"slow-tip C1 auditor {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#C1_ATTEMPT48", "exec"), globals(), globals())
