#!/usr/bin/env python3
"""C1 runner: fresh attempt-23 with identity-before-placement scene tool."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-liquid-source-clearance-matrix.py")
EXPECTED_BASE_SHA256 = "ae0004cb01007b535f27f347d96ced03574e0ba0da5f9c7be128ded83041378c"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 source-clearance C1 runner base identity mismatch")


source = BASE.read_text(encoding="utf-8")
replacements = (
    ("RC6-2026-09-01-source-clearance-attempt-22", "RC6-2026-09-01-source-clearance-c1-attempt-23", "roots"),
    ("scripts/run-rc6-liquid-source-clearance-scene.py", "scripts/run-rc6-liquid-source-clearance-scene-c1.py", "scene tool"),
    ("scripts/audit-rc6-liquid-source-clearance-matrix.py", "scripts/audit-rc6-liquid-source-clearance-matrix-c1.py", "audit tool"),
    ("specs/ai-native-studio-rc6-liquid-source-clearance.v0.22.json", "specs/ai-native-studio-rc6-liquid-source-clearance-c1.v0.23.json", "spec"),
)
for before, after, label in replacements:
    if source.count(before) != 1:
        raise RuntimeError(f"RC6 source-clearance C1 runner {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#SOURCE_CLEARANCE_C1_MATRIX_V01", "exec"), globals(), globals())
