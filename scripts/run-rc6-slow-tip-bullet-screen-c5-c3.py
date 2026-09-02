#!/usr/bin/env python3
"""C5-C3 runner correcting only the unchanged scene marker binding."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-slow-tip-bullet-screen-c5-c2.py")
EXPECTED_BASE_SHA256 = "a3407a481531d077ae9cd5d702560d23f4728d19dfc5a51972b1a745aae567bf"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("slow-tip C5-C3 runner base identity mismatch")

source = BASE.read_text(encoding="utf-8")
replacements = (
    ("RC6-2026-09-02-slow-tip-bullet-screen-c5-c2-attempt-54", "RC6-2026-09-02-slow-tip-bullet-screen-c5-c3-attempt-55", 1, "fresh roots"),
    ("scripts/audit-rc6-slow-tip-bullet-screen-c5-c2.py", "scripts/audit-rc6-slow-tip-bullet-screen-c5-c3.py", 1, "auditor"),
    ("specs/ai-native-studio-rc6-slow-tip-bullet-screen-c5-c2.v0.62.json", "specs/ai-native-studio-rc6-slow-tip-bullet-screen-c5-c3.v0.64.json", 1, "spec"),
    ("bfs.rc6SlowTipBulletScreenC5C2", "bfs.rc6SlowTipBulletScreenC5C3", 1, "schemas"),
    ("RC6_SLOW_TIP_BULLET_SCREEN_C5_C2=", "RC6_SLOW_TIP_BULLET_SCREEN_C5=", 1, "actual unchanged scene marker"),
    ("RC6_SLOW_TIP_BULLET_SCREEN_C5_C2_RUN=", "RC6_SLOW_TIP_BULLET_SCREEN_C5_C3_RUN=", 1, "run marker"),
    ("#C5_C2_ATTEMPT54", "#C5_C3_ATTEMPT55", 2, "compile tag"),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"slow-tip C5-C3 runner {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#C5_C3_ATTEMPT55", "exec"), globals(), globals())
