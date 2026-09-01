#!/usr/bin/env python3
"""C1 auditor: fresh attempt-23 with identity-before-placement scene tool."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-liquid-source-clearance-matrix.py")
EXPECTED_BASE_SHA256 = "23ec516e68cb397c2c43986da8cc1359b051a103fa76754f16497a17397fd9fa"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 source-clearance C1 auditor base identity mismatch")


source = BASE.read_text(encoding="utf-8")
replacements = (
    ("RC6-2026-09-01-source-clearance-attempt-22", "RC6-2026-09-01-source-clearance-c1-attempt-23", "roots"),
    ("scripts/run-rc6-liquid-source-clearance-scene.py", "scripts/run-rc6-liquid-source-clearance-scene-c1.py", "scene tool"),
    ("scripts/run-rc6-liquid-source-clearance-matrix.py", "scripts/run-rc6-liquid-source-clearance-matrix-c1.py", "runner"),
    ("specs/ai-native-studio-rc6-liquid-source-clearance.v0.22.json", "specs/ai-native-studio-rc6-liquid-source-clearance-c1.v0.23.json", "spec"),
)
for before, after, label in replacements:
    if source.count(before) != 1:
        raise RuntimeError(f"RC6 source-clearance C1 auditor {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#SOURCE_CLEARANCE_C1_AUDIT_V01", "exec"), globals(), globals())
