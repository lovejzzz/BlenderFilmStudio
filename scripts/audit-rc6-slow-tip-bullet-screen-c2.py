#!/usr/bin/env python3
"""C2 independent auditor for the passive toe-stop attempt-49."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-slow-tip-bullet-screen.py")
EXPECTED_BASE_SHA256 = "1cda47e2d4f8df1bfbc15d2075044a721afb9b0995c58f388cbe7d9c39c71679"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("slow-tip C2 auditor base identity mismatch")

source = BASE.read_text(encoding="utf-8")
replacements = (
    ("RC6-2026-09-02-slow-tip-bullet-screen-attempt-47", "RC6-2026-09-02-slow-tip-bullet-screen-c2-attempt-49", 2, "roots"),
    ('CELLS = (("D12", 12), ("D16", 16), ("D20", 20), ("D24", 24))', 'CELLS = (("C2D16", 16), ("C2D20", 20), ("C2D24", 24), ("C2D28", 28))', 1, "cells"),
    ('scripts/run-rc6-slow-tip-bullet-screen-scene.py', 'scripts/run-rc6-slow-tip-bullet-screen-c2-scene.py', 1, "scene tool"),
    ('scripts/run-rc6-slow-tip-bullet-screen.py', 'scripts/run-rc6-slow-tip-bullet-screen-c2.py', 1, "runner"),
    ('specs/ai-native-studio-rc6-slow-tip-bullet-screen.v0.55.json', 'specs/ai-native-studio-rc6-slow-tip-bullet-screen-c2.v0.57.json', 1, "spec"),
    ('ballCupSurfaceSeparationMeters', 'actuatorCupSurfaceSeparationMeters', 1, "contact samples"),
    (
        '    peak = max(sample["cupTiltDegrees"] for sample in samples)\n    base_voxel = row["configuration"]["baseVoxelMeters"]',
        '    peak = max(sample["cupTiltDegrees"] for sample in samples)\n    toe_contact = next((sample["frame"] for sample in samples if sample["cupToeStopSurfaceSeparationMeters"] <= 0.001), None)\n    initial_toe_gap = samples[0]["cupToeStopSurfaceSeparationMeters"]\n    base_voxel = row["configuration"]["baseVoxelMeters"]',
        1,
        "stop metric derivation",
    ),
    (
        '        and row["metrics"]["requiredEffectorSubframes"] == required\n    )',
        '        and row["metrics"]["requiredEffectorSubframes"] == required\n        and row["metrics"]["toeStopContactFrame"] == toe_contact\n        and abs(row["metrics"]["initialToeStopClearanceMeters"] - initial_toe_gap) <= 1e-8\n        and row["configuration"]["toeStopLocationMeters"] == [0.485, 0.0, 0.02]\n        and row["configuration"]["toeStopDimensionsMeters"] == [0.02, 0.38, 0.04]\n    )',
        1,
        "stop metrics recompute",
    ),
    (
        '    checks_recompute &= row["status"] == ("PASS" if all(row["checks"].values()) else "FAIL")',
        '    expected_initial = 0.004 <= initial_toe_gap <= 0.006\n    expected_contact = toe_contact is not None and first_45 is not None and toe_contact <= first_45\n    checks_recompute &= (\n        row["checks"]["toeStopInitialClearance"] == expected_initial\n        and row["checks"]["passiveToeStopContactBeforeFortyFive"] == expected_contact\n        and row["status"] == ("PASS" if all(row["checks"].values()) else "FAIL")\n    )',
        1,
        "stop checks recompute",
    ),
    ('bfs.rc6SlowTipBulletScreenIndependentAudit.v0.1', 'bfs.rc6SlowTipBulletScreenC2IndependentAudit.v0.1', 1, "schema"),
    ('RC6_SLOW_TIP_BULLET_SCREEN_AUDIT=', 'RC6_SLOW_TIP_BULLET_SCREEN_C2_AUDIT=', 1, "marker"),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"slow-tip C2 auditor {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#C2_ATTEMPT49", "exec"), globals(), globals())
