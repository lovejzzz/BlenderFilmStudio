#!/usr/bin/env python3
"""C2 auditor: fresh attempt-30 with RNA float32 representation tolerance."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-liquid-final-mesh-only-matrix-c1.py")
EXPECTED_BASE_SHA256 = "4ef8558873c6bdcc1f18925de4e20153a887e401d3fb44c4b43bf3b666bc1b29"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 final mesh-only C2 auditor base identity mismatch")


source = BASE.read_text(encoding="utf-8")
replacements = (
    ("RC6-2026-09-01-final-mesh-only-c1-attempt-29", "RC6-2026-09-01-final-mesh-only-c2-attempt-30", 1, "roots"),
    ("scripts/run-rc6-liquid-final-mesh-only-scene-c1.py", "scripts/run-rc6-liquid-final-mesh-only-scene-c2.py", 1, "scene tool"),
    ("scripts/run-rc6-liquid-final-mesh-only-matrix-c1.py", "scripts/run-rc6-liquid-final-mesh-only-matrix-c2.py", 1, "runner"),
    ("specs/ai-native-studio-rc6-liquid-final-mesh-only-c1.v0.29.json", "specs/ai-native-studio-rc6-liquid-final-mesh-only-c2.v0.30.json", 1, "spec"),
    (
        '"cacheDirectoryRebound": True, "fluidDataBakes": 0,',
        '"cacheDirectoryRebound": True, "rnaFloatTolerance": 1e-6, "fluidDataBakes": 0,',
        1,
        "authority receipt",
    ),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"RC6 final mesh-only C2 auditor {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#FINAL_MESH_ONLY_C2_AUDITOR_V01", "exec"), globals(), globals())
