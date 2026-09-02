#!/usr/bin/env python3
"""C4 independent auditor for limited and damped hinge attempt-51."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-slow-tip-bullet-screen.py")
EXPECTED_BASE_SHA256 = "1cda47e2d4f8df1bfbc15d2075044a721afb9b0995c58f388cbe7d9c39c71679"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("slow-tip C4 auditor base identity mismatch")

source = BASE.read_text(encoding="utf-8")
replacements = (
    ("RC6-2026-09-02-slow-tip-bullet-screen-attempt-47", "RC6-2026-09-02-slow-tip-bullet-screen-c4-attempt-51", 2, "roots"),
    ('CELLS = (("D12", 12), ("D16", 16), ("D20", 20), ("D24", 24))', 'CELLS = (("C4D28", 28), ("C4D32", 32), ("C4D36", 36), ("C4D40", 40))', 1, "cells"),
    ('scripts/run-rc6-slow-tip-bullet-screen-scene.py', 'scripts/run-rc6-slow-tip-bullet-screen-c4-scene.py', 1, "scene tool"),
    ('scripts/run-rc6-slow-tip-bullet-screen.py', 'scripts/run-rc6-slow-tip-bullet-screen-c4.py', 1, "runner"),
    ('specs/ai-native-studio-rc6-slow-tip-bullet-screen.v0.55.json', 'specs/ai-native-studio-rc6-slow-tip-bullet-screen-c4.v0.59.json', 1, "spec"),
    ('ballCupSurfaceSeparationMeters', 'actuatorCupSurfaceSeparationMeters', 1, "contact samples"),
    (
        '    peak = max(sample["cupTiltDegrees"] for sample in samples)\n    base_voxel = row["configuration"]["baseVoxelMeters"]',
        '    peak = max(sample["cupTiltDegrees"] for sample in samples)\n    maximum_hinge_drift = max(sample["hingePivotDriftMeters"] for sample in samples)\n    base_voxel = row["configuration"]["baseVoxelMeters"]',
        1,
        "hinge metric derivation",
    ),
    (
        '        and row["metrics"]["requiredEffectorSubframes"] == required\n    )',
        '        and row["metrics"]["requiredEffectorSubframes"] == required\n        and abs(row["metrics"]["maximumHingePivotDriftMeters"] - maximum_hinge_drift) <= 1e-8\n        and row["configuration"]["hingePivotWorldMeters"] == [0.47, 0.0, 0.0]\n        and row["configuration"]["hingeAnchorLocationMeters"] == [0.47, 0.0, -0.08]\n        and abs(abs(row["configuration"]["hingeAxisWorld"][1]) - 1.0) <= 1e-8\n        and row["configuration"]["hingeAngularLimitsDegrees"] == [-60.0, 5.0]\n        and abs(row["configuration"]["cupAngularDamping"] - 0.8) <= 1e-8\n    )',
        1,
        "hinge metrics and configuration recompute",
    ),
    (
        '    checks_recompute &= row["status"] == ("PASS" if all(row["checks"].values()) else "FAIL")',
        '    expected_hinge_stable = maximum_hinge_drift <= 0.005\n    expected_mechanical_stop = peak <= 65.0\n    checks_recompute &= (\n        row["checks"]["hingePivotStableWithinFiveMillimeters"] == expected_hinge_stable\n        and row["checks"]["mechanicalHingeStopHoldsAtMost65Degrees"] == expected_mechanical_stop\n        and row["checks"]["hingeConstraintExact"]\n        and row["status"] == ("PASS" if all(row["checks"].values()) else "FAIL")\n    )',
        1,
        "hinge checks recompute",
    ),
    ('bfs.rc6SlowTipBulletScreenIndependentAudit.v0.1', 'bfs.rc6SlowTipBulletScreenC4IndependentAudit.v0.1', 1, "schema"),
    ('RC6_SLOW_TIP_BULLET_SCREEN_AUDIT=', 'RC6_SLOW_TIP_BULLET_SCREEN_C4_AUDIT=', 1, "marker"),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"slow-tip C4 auditor {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#C4_ATTEMPT51", "exec"), globals(), globals())
