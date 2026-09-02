#!/usr/bin/env python3
"""Attempt-37 runner: fresh zero-bake detail localization of active particles."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-liquid-containment-axis-diagnostic.py")
EXPECTED_BASE_SHA256 = "572139cb52b7833c37df21aeacc2de0eb0536313e93f1731f754ce1004df4ced"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 FLIP-particle detail runner base identity mismatch")


source = BASE.read_text(encoding="utf-8")
replacements = (
    ("RC6-2026-09-01-containment-axis-attempt-32", "RC6-2026-09-01-flip-particle-detail-attempt-37", 2, "roots"),
    ("scripts/inspect-rc6-liquid-containment-axis-scene.py", "scripts/inspect-rc6-liquid-flip-particle-detail-scene.py", 1, "scene tool"),
    ("scripts/audit-rc6-liquid-containment-axis-diagnostic.py", "scripts/audit-rc6-liquid-flip-particle-detail.py", 1, "auditor"),
    ("specs/ai-native-studio-rc6-liquid-containment-axis.v0.32.json", "specs/ai-native-studio-rc6-liquid-flip-particle-detail.v0.39.json", 1, "spec"),
    ("RC6_CONTAINMENT_AXIS=", "RC6_FLIP_PARTICLE_AXIS=", 1, "scene marker"),
    ("RC6_CONTAINMENT_AXIS_RECEIPT=", "RC6_FLIP_PARTICLE_DETAIL_RECEIPT=", 1, "receipt marker"),
    ("bfs.rc6LiquidContainmentAxisAdmission.v0.1", "bfs.rc6LiquidFlipParticleDetailAdmission.v0.1", 1, "admission schema"),
    ("bfs.rc6LiquidContainmentAxisProcess.v0.1", "bfs.rc6LiquidFlipParticleDetailProcess.v0.1", 1, "process schema"),
    ("bfs.rc6LiquidContainmentAxisReceipt.v0.1", "bfs.rc6LiquidFlipParticleDetailReceipt.v0.1", 1, "receipt schema"),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"RC6 FLIP-particle detail runner {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#FLIP_PARTICLE_DETAIL_RUNNER_V01", "exec"), globals(), globals())
