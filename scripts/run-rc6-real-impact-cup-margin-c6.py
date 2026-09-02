#!/usr/bin/env python3
"""C6 runner adapter for the one-value cup collision-margin test."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-real-impact-bullet-speed-screen.py")
EXPECTED_BASE_SHA256 = "9768dd0328504dba124240ea0b365d58590464892f0116820093d4a7aadb184c"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("real-impact C6 runner base identity mismatch")
source = BASE.read_text(encoding="utf-8")
replacements = (
    ("RC6-2026-09-02-real-impact-bullet-speed-screen-attempt-71", "RC6-2026-09-02-real-impact-cup-margin-c6-attempt-77", 2, "fresh roots"),
    ('CELLS = (("I08", 8), ("I10", 10), ("I12", 12))', 'CELLS = (("M02", 9),)', 1, "cell roster"),
    ("scripts/run-rc6-real-impact-bullet-speed-screen-scene.py", "scripts/run-rc6-real-impact-cup-margin-c6-scene.py", 2, "scene tool"),
    ("scripts/run-rc6-real-impact-bullet-speed-screen.py", "scripts/run-rc6-real-impact-cup-margin-c6.py", 1, "runner commit path"),
    ("scripts/audit-rc6-real-impact-bullet-speed-screen.py", "scripts/audit-rc6-real-impact-cup-margin-c6.py", 2, "auditor"),
    ("specs/ai-native-studio-rc6-real-impact-bullet-speed-screen.v0.82.json", "specs/ai-native-studio-rc6-real-impact-cup-margin-c6.v0.88.json", 2, "spec"),
    ("research/2026-09-02-rc6-real-impact-bullet-speed-screen-preregistration.md", "research/2026-09-02-rc6-real-impact-cup-margin-c6-preregistration.md", 1, "preregistration"),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"real-impact C6 runner {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#C6_CUP_MARGIN_2MM", "exec"), globals(), globals())
