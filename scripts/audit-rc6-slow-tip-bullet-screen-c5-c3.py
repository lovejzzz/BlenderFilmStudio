#!/usr/bin/env python3
"""C5-C3 independent auditor routing the full attempt-55 evidence."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-slow-tip-bullet-screen-c5-c2.py")
EXPECTED_BASE_SHA256 = "22c406a7e9eccef2538df93dcdf2ae75db9ecf43978968918b3fb4de6aac5c5d"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("slow-tip C5-C3 auditor base identity mismatch")

source = BASE.read_text(encoding="utf-8")
replacements = (
    ("RC6-2026-09-02-slow-tip-bullet-screen-c5-c2-attempt-54", "RC6-2026-09-02-slow-tip-bullet-screen-c5-c3-attempt-55", 1, "fresh roots"),
    ("scripts/run-rc6-slow-tip-bullet-screen-c5-c2.py", "scripts/run-rc6-slow-tip-bullet-screen-c5-c3.py", 1, "runner"),
    ("specs/ai-native-studio-rc6-slow-tip-bullet-screen-c5-c2.v0.62.json", "specs/ai-native-studio-rc6-slow-tip-bullet-screen-c5-c3.v0.64.json", 1, "spec"),
    ("bfs.rc6SlowTipBulletScreenC5C2IndependentAudit.v0.1", "bfs.rc6SlowTipBulletScreenC5C3IndependentAudit.v0.1", 1, "schema"),
    ("RC6_SLOW_TIP_BULLET_SCREEN_C5_C2_AUDIT=", "RC6_SLOW_TIP_BULLET_SCREEN_C5_C3_AUDIT=", 1, "marker"),
    ("#C5_C2_ATTEMPT54", "#C5_C3_ATTEMPT55", 2, "compile tag"),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"slow-tip C5-C3 auditor {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#C5_C3_ATTEMPT55", "exec"), globals(), globals())
