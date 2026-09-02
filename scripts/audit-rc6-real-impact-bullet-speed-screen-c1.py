#!/usr/bin/env python3
"""C1 independent auditor adapter for corrected Python-canonical identity."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-real-impact-bullet-speed-screen.py")
EXPECTED_BASE_SHA256 = "9bc233e999aee4a6e4df83b31be233fbbad57103013701562355d49dff2a76a4"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("real-impact C1 auditor base identity mismatch")

source = BASE.read_text(encoding="utf-8")
replacements = (
    ("RC6-2026-09-02-real-impact-bullet-speed-screen-attempt-71", "RC6-2026-09-02-real-impact-bullet-speed-screen-c1-attempt-72", 2, "fresh roots"),
    ("scripts/run-rc6-real-impact-bullet-speed-screen-scene.py", "scripts/run-rc6-real-impact-bullet-speed-screen-c1-scene.py", 2, "scene tool"),
    ("scripts/run-rc6-real-impact-bullet-speed-screen.py", "scripts/run-rc6-real-impact-bullet-speed-screen-c1.py", 2, "runner"),
    ("scripts/audit-rc6-real-impact-bullet-speed-screen.py", "scripts/audit-rc6-real-impact-bullet-speed-screen-c1.py", 1, "auditor commit path"),
    ("specs/ai-native-studio-rc6-real-impact-bullet-speed-screen.v0.82.json", "specs/ai-native-studio-rc6-real-impact-bullet-speed-screen-c1.v0.83.json", 2, "spec"),
    ("research/2026-09-02-rc6-real-impact-bullet-speed-screen-preregistration.md", "research/2026-09-02-rc6-real-impact-bullet-speed-screen-c1-correction.md", 1, "correction record"),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"real-impact C1 auditor {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#C1_HASH_SEMANTICS", "exec"), globals(), globals())
