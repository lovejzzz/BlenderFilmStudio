#!/usr/bin/env python3
"""C2 runner: fresh attempt-30 with RNA float32 representation tolerance."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-liquid-final-mesh-only-matrix-c1.py")
EXPECTED_BASE_SHA256 = "a42f2c99e392af89c520af925f041699722a7010516f4cbf5b5297800c95c18e"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 final mesh-only C2 runner base identity mismatch")


source = BASE.read_text(encoding="utf-8")
replacements = (
    ("RC6-2026-09-01-final-mesh-only-c1-attempt-29", "RC6-2026-09-01-final-mesh-only-c2-attempt-30", 1, "roots"),
    ("scripts/run-rc6-liquid-final-mesh-only-scene-c1.py", "scripts/run-rc6-liquid-final-mesh-only-scene-c2.py", 1, "scene tool"),
    ("scripts/audit-rc6-liquid-final-mesh-only-matrix-c1.py", "scripts/audit-rc6-liquid-final-mesh-only-matrix-c2.py", 1, "audit tool"),
    ("specs/ai-native-studio-rc6-liquid-final-mesh-only-c1.v0.29.json", "specs/ai-native-studio-rc6-liquid-final-mesh-only-c2.v0.30.json", 1, "spec"),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"RC6 final mesh-only C2 runner {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#FINAL_MESH_ONLY_C2_RUNNER_V01", "exec"), globals(), globals())
