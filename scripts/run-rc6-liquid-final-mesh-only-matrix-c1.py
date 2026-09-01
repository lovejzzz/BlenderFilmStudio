#!/usr/bin/env python3
"""C1 runner: fresh attempt-29 with explicit copied-cache rebinding."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-liquid-final-mesh-only-matrix.py")
EXPECTED_BASE_SHA256 = "62bef5b16268b1870cbf2eebde32463fd7f2295a9f8a1c8fef6f4271a7d63df6"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 final mesh-only C1 runner base identity mismatch")


source = BASE.read_text(encoding="utf-8")
replacements = (
    ("RC6-2026-09-01-final-mesh-only-attempt-28", "RC6-2026-09-01-final-mesh-only-c1-attempt-29", 2, "roots"),
    ("scripts/run-rc6-liquid-final-mesh-only-scene.py", "scripts/run-rc6-liquid-final-mesh-only-scene-c1.py", 1, "scene tool"),
    ("scripts/audit-rc6-liquid-final-mesh-only-matrix.py", "scripts/audit-rc6-liquid-final-mesh-only-matrix-c1.py", 1, "audit tool"),
    ("specs/ai-native-studio-rc6-liquid-final-mesh-only.v0.28.json", "specs/ai-native-studio-rc6-liquid-final-mesh-only-c1.v0.29.json", 1, "spec"),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"RC6 final mesh-only C1 runner {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#FINAL_MESH_ONLY_C1_RUNNER_V01", "exec"), globals(), globals())
