#!/usr/bin/env python3
"""C5-C2 independent auditor correcting only C5-C1 outer routing."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-slow-tip-bullet-screen-c5-c1.py")
EXPECTED_BASE_SHA256 = "f8689305b69f797a19cc32e059e90c1df68280612b8e918ebfe6b7348e064422"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("slow-tip C5-C2 auditor base identity mismatch")

source = BASE.read_text(encoding="utf-8")
replacements = (
    (
        '("RC6-2026-09-02-slow-tip-bullet-screen-c5-attempt-52", "RC6-2026-09-02-slow-tip-bullet-screen-c5-c1-attempt-53", 2, "roots"),',
        '("RC6-2026-09-02-slow-tip-bullet-screen-c5-attempt-52", "RC6-2026-09-02-slow-tip-bullet-screen-c5-c2-attempt-54", 1, "roots"),',
        1,
        "root count and fresh destination",
    ),
    ("scripts/run-rc6-slow-tip-bullet-screen-c5-c1.py", "scripts/run-rc6-slow-tip-bullet-screen-c5-c2.py", 1, "runner"),
    ("specs/ai-native-studio-rc6-slow-tip-bullet-screen-c5-c1.v0.61.json", "specs/ai-native-studio-rc6-slow-tip-bullet-screen-c5-c2.v0.62.json", 1, "spec"),
    ("bfs.rc6SlowTipBulletScreenC5C1IndependentAudit.v0.1", "bfs.rc6SlowTipBulletScreenC5C2IndependentAudit.v0.1", 1, "schema"),
    ("RC6_SLOW_TIP_BULLET_SCREEN_C5_C1_AUDIT=", "RC6_SLOW_TIP_BULLET_SCREEN_C5_C2_AUDIT=", 1, "marker"),
    ("#C5_C1_ATTEMPT53", "#C5_C2_ATTEMPT54", 2, "compile tag"),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"slow-tip C5-C2 auditor {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#C5_C2_ATTEMPT54", "exec"), globals(), globals())
