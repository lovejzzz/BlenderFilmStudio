#!/usr/bin/env python3
"""C10 runner adapter for the single 40 mm passive-ramp test."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-real-impact-passive-ramp-c9.py")
EXPECTED_BASE_SHA256 = "d02eb5439486010429ca7667337a56327f31e1b71bf2c54cb5989ecb1bc59ee7"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("real-impact C10 runner base identity mismatch")
source = BASE.read_text(encoding="utf-8")
replacements = (
    ("RC6-2026-09-02-real-impact-passive-ramp-c9-attempt-81", "RC6-2026-09-02-real-impact-passive-ramp-c10-attempt-82", 1, "fresh roots"),
    ('CELLS = (("R60", 9),)', 'CELLS = (("R40", 9),)', 1, "cell roster"),
    ("scripts/run-rc6-real-impact-passive-ramp-c9-scene.py", "scripts/run-rc6-real-impact-passive-ramp-c10-scene.py", 1, "scene tool"),
    ("scripts/run-rc6-real-impact-passive-ramp-c9.py", "scripts/run-rc6-real-impact-passive-ramp-c10.py", 1, "runner"),
    ("scripts/audit-rc6-real-impact-passive-ramp-c9.py", "scripts/audit-rc6-real-impact-passive-ramp-c10.py", 1, "auditor"),
    ("specs/ai-native-studio-rc6-real-impact-passive-ramp-c9.v0.92.json", "specs/ai-native-studio-rc6-real-impact-passive-ramp-c10.v0.93.json", 1, "spec"),
    ("research/2026-09-02-rc6-real-impact-passive-ramp-c9-preregistration.md", "research/2026-09-02-rc6-real-impact-passive-ramp-c10-preregistration.md", 1, "preregistration"),
    ("#C9_PASSIVE_RAMP_60MM", "#C10_PASSIVE_RAMP_40MM", 1, "compile identity"),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"real-impact C10 runner {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#C10_PASSIVE_RAMP_40MM", "exec"), globals(), globals())
