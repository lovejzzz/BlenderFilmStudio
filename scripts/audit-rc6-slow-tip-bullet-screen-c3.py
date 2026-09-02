#!/usr/bin/env python3
"""C3 independent auditor for explicit-hinge attempt-50."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-slow-tip-bullet-screen.py")
EXPECTED_BASE_SHA256 = "1cda47e2d4f8df1bfbc15d2075044a721afb9b0995c58f388cbe7d9c39c71679"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("slow-tip C3 auditor base identity mismatch")

source = BASE.read_text(encoding="utf-8")
replacements = (
    ("RC6-2026-09-02-slow-tip-bullet-screen-attempt-47", "RC6-2026-09-02-slow-tip-bullet-screen-c3-attempt-50", 2, "roots"),
    ('CELLS = (("D12", 12), ("D16", 16), ("D20", 20), ("D24", 24))', 'CELLS = (("C3D16", 16), ("C3D20", 20), ("C3D24", 24), ("C3D28", 28))', 1, "cells"),
    ('scripts/run-rc6-slow-tip-bullet-screen-scene.py', 'scripts/run-rc6-slow-tip-bullet-screen-c3-scene.py', 1, "scene tool"),
    ('scripts/run-rc6-slow-tip-bullet-screen.py', 'scripts/run-rc6-slow-tip-bullet-screen-c3.py', 1, "runner"),
    ('specs/ai-native-studio-rc6-slow-tip-bullet-screen.v0.55.json', 'specs/ai-native-studio-rc6-slow-tip-bullet-screen-c3.v0.58.json', 1, "spec"),
    ('ballCupSurfaceSeparationMeters', 'actuatorCupSurfaceSeparationMeters', 1, "contact samples"),
    (
        '    peak = max(sample["cupTiltDegrees"] for sample in samples)\n    base_voxel = row["configuration"]["baseVoxelMeters"]',
        '    peak = max(sample["cupTiltDegrees"] for sample in samples)\n    maximum_hinge_drift = max(sample["hingePivotDriftMeters"] for sample in samples)\n    base_voxel = row["configuration"]["baseVoxelMeters"]',
        1,
        "hinge metric derivation",
    ),
    (
        '        and row["metrics"]["requiredEffectorSubframes"] == required\n    )',
        '        and row["metrics"]["requiredEffectorSubframes"] == required\n        and abs(row["metrics"]["maximumHingePivotDriftMeters"] - maximum_hinge_drift) <= 1e-8\n        and row["configuration"]["hingePivotWorldMeters"] == [0.47, 0.0, 0.0]\n        and row["configuration"]["hingeAnchorLocationMeters"] == [0.47, 0.0, -0.08]\n        and abs(abs(row["configuration"]["hingeAxisWorld"][1]) - 1.0) <= 1e-8\n    )',
        1,
        "hinge metrics recompute",
    ),
    (
        '    checks_recompute &= row["status"] == ("PASS" if all(row["checks"].values()) else "FAIL")',
        '    expected_hinge_stable = maximum_hinge_drift <= 0.005\n    checks_recompute &= (\n        row["checks"]["hingePivotStableWithinFiveMillimeters"] == expected_hinge_stable\n        and row["checks"]["hingeConstraintExact"]\n        and row["status"] == ("PASS" if all(row["checks"].values()) else "FAIL")\n    )',
        1,
        "hinge checks recompute",
    ),
    ('bfs.rc6SlowTipBulletScreenIndependentAudit.v0.1', 'bfs.rc6SlowTipBulletScreenC3IndependentAudit.v0.1', 1, "schema"),
    ('RC6_SLOW_TIP_BULLET_SCREEN_AUDIT=', 'RC6_SLOW_TIP_BULLET_SCREEN_C3_AUDIT=', 1, "marker"),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"slow-tip C3 auditor {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#C3_ATTEMPT50", "exec"), globals(), globals())
