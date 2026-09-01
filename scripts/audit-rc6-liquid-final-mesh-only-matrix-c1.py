#!/usr/bin/env python3
"""C1 auditor: fresh attempt-29 with explicit copied-cache rebinding."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-liquid-final-mesh-only-matrix.py")
EXPECTED_BASE_SHA256 = "f8eba28d1f0c9bdc60c6f19943333cade6b6e02853400518cbe1b1d018b1068d"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 final mesh-only C1 auditor base identity mismatch")


source = BASE.read_text(encoding="utf-8")
replacements = (
    ("RC6-2026-09-01-final-mesh-only-attempt-28", "RC6-2026-09-01-final-mesh-only-c1-attempt-29", 2, "roots"),
    ("scripts/run-rc6-liquid-final-mesh-only-scene.py", "scripts/run-rc6-liquid-final-mesh-only-scene-c1.py", 1, "scene tool"),
    ("scripts/run-rc6-liquid-final-mesh-only-matrix.py", "scripts/run-rc6-liquid-final-mesh-only-matrix-c1.py", 1, "runner"),
    ("specs/ai-native-studio-rc6-liquid-final-mesh-only.v0.28.json", "specs/ai-native-studio-rc6-liquid-final-mesh-only-c1.v0.29.json", 1, "spec"),
    (
        '{"retainedDataCopied": True, "fluidDataBakes": 0, "fluidMeshBakes": 1, "blendSaves": 1, "renderCalls": 0, "networkCalls": 0, "engineRemoteWrites": 0}',
        '{"retainedDataCopied": True, "cacheDirectoryRebound": True, "fluidDataBakes": 0, "fluidMeshBakes": 1, "blendSaves": 1, "renderCalls": 0, "networkCalls": 0, "engineRemoteWrites": 0}',
        1,
        "authority receipt",
    ),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"RC6 final mesh-only C1 auditor {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#FINAL_MESH_ONLY_C1_AUDITOR_V01", "exec"), globals(), globals())
