#!/usr/bin/env python3
"""C2 runner: fresh attempt-27 with final compile-boundary transformation."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-liquid-source-clearance-final.py")
EXPECTED_BASE_SHA256 = "d849d0e4161349e1269e6ee02aae30a0e168f5c07b25ca36959c5d52d9dee427"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 source-clearance final C2 runner base identity mismatch")


source = BASE.read_text(encoding="utf-8")
replacements = (
    ("RC6-2026-09-01-source-clearance-final-attempt-25", "RC6-2026-09-01-source-clearance-final-c2-attempt-27", 2, "roots"),
    ("scripts/run-rc6-liquid-source-clearance-final-scene.py", "scripts/run-rc6-liquid-source-clearance-final-scene-c2.py", 1, "scene tool"),
    ("scripts/audit-rc6-liquid-source-clearance-final.py", "scripts/audit-rc6-liquid-source-clearance-final-c2.py", 1, "audit tool"),
    ("specs/ai-native-studio-rc6-liquid-source-clearance-final.v0.25.json", "specs/ai-native-studio-rc6-liquid-source-clearance-final-c2.v0.27.json", 1, "spec"),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"RC6 source-clearance final C2 runner {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#SOURCE_CLEARANCE_FINAL_C2_RUNNER_V01", "exec"), globals(), globals())
