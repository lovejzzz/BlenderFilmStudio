#!/usr/bin/env python3
"""C9 runner adapter for one passive contact-ramp test."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-real-impact-bullet-speed-screen.py")
EXPECTED_BASE_SHA256 = "9768dd0328504dba124240ea0b365d58590464892f0116820093d4a7aadb184c"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("real-impact C9 runner base identity mismatch")
source = BASE.read_text(encoding="utf-8")
replacements = (
    ("RC6-2026-09-02-real-impact-bullet-speed-screen-attempt-71", "RC6-2026-09-02-real-impact-passive-ramp-c9-attempt-81", 2, "fresh roots"),
    ('CELLS = (("I08", 8), ("I10", 10), ("I12", 12))', 'CELLS = (("R60", 9),)', 1, "cell roster"),
    ("scripts/run-rc6-real-impact-bullet-speed-screen-scene.py", "scripts/run-rc6-real-impact-passive-ramp-c9-scene.py", 2, "scene tool"),
    ("scripts/run-rc6-real-impact-bullet-speed-screen.py", "scripts/run-rc6-real-impact-passive-ramp-c9.py", 1, "runner commit path"),
    ("scripts/audit-rc6-real-impact-bullet-speed-screen.py", "scripts/audit-rc6-real-impact-passive-ramp-c9.py", 2, "auditor"),
    ("specs/ai-native-studio-rc6-real-impact-bullet-speed-screen.v0.82.json", "specs/ai-native-studio-rc6-real-impact-passive-ramp-c9.v0.92.json", 2, "spec"),
    ("research/2026-09-02-rc6-real-impact-bullet-speed-screen-preregistration.md", "research/2026-09-02-rc6-real-impact-passive-ramp-c9-preregistration.md", 1, "preregistration"),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"real-impact C9 runner {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#C9_PASSIVE_RAMP_60MM", "exec"), globals(), globals())
