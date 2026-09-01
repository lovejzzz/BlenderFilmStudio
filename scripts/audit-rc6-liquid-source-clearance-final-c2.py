#!/usr/bin/env python3
"""C2 auditor: fresh attempt-27 with final compile-boundary transformation."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-liquid-source-clearance-final.py")
EXPECTED_BASE_SHA256 = "bf15046148dc688f8c379fcc7aa4d877a0e6516e34c19f10d20b88c008e4979d"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 source-clearance final C2 auditor base identity mismatch")


source = BASE.read_text(encoding="utf-8")
replacements = (
    ("RC6-2026-09-01-source-clearance-final-attempt-25", "RC6-2026-09-01-source-clearance-final-c2-attempt-27", 2, "roots"),
    ("scripts/run-rc6-liquid-source-clearance-final-scene.py", "scripts/run-rc6-liquid-source-clearance-final-scene-c2.py", 1, "scene tool"),
    ("scripts/run-rc6-liquid-source-clearance-final.py", "scripts/run-rc6-liquid-source-clearance-final-c2.py", 1, "runner"),
    ("specs/ai-native-studio-rc6-liquid-source-clearance-final.v0.25.json", "specs/ai-native-studio-rc6-liquid-source-clearance-final-c2.v0.27.json", 1, "spec"),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"RC6 source-clearance final C2 auditor {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#SOURCE_CLEARANCE_FINAL_C2_AUDITOR_V01", "exec"), globals(), globals())
