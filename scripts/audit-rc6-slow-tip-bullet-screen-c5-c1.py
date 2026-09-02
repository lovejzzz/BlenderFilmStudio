#!/usr/bin/env python3
"""C5-C1 independent auditor for attempt-53."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-slow-tip-bullet-screen-c5.py")
EXPECTED_BASE_SHA256 = "36dda7c8d45f23d1b46ca001b19471640463007998faa02c37bc89d55402ae2c"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("slow-tip C5-C1 auditor base identity mismatch")

source = BASE.read_text(encoding="utf-8")
replacements = (
    ("RC6-2026-09-02-slow-tip-bullet-screen-c5-attempt-52", "RC6-2026-09-02-slow-tip-bullet-screen-c5-c1-attempt-53", 2, "roots"),
    ("scripts/run-rc6-slow-tip-bullet-screen-c5-scene.py", "scripts/run-rc6-slow-tip-bullet-screen-c5-c1-scene.py", 1, "scene tool"),
    ("scripts/run-rc6-slow-tip-bullet-screen-c5.py", "scripts/run-rc6-slow-tip-bullet-screen-c5-c1.py", 1, "runner"),
    ("specs/ai-native-studio-rc6-slow-tip-bullet-screen-c5.v0.60.json", "specs/ai-native-studio-rc6-slow-tip-bullet-screen-c5-c1.v0.61.json", 1, "spec"),
    ("bfs.rc6SlowTipBulletScreenC5IndependentAudit.v0.1", "bfs.rc6SlowTipBulletScreenC5C1IndependentAudit.v0.1", 1, "schema"),
    ("RC6_SLOW_TIP_BULLET_SCREEN_C5_AUDIT=", "RC6_SLOW_TIP_BULLET_SCREEN_C5_C1_AUDIT=", 1, "marker"),
    ("#C5_ATTEMPT52", "#C5_C1_ATTEMPT53", 1, "compile tag"),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"slow-tip C5-C1 auditor {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#C5_C1_ATTEMPT53", "exec"), globals(), globals())
