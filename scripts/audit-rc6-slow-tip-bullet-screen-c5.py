#!/usr/bin/env python3
"""C5 independent auditor for bounded motor attempt-52."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-slow-tip-bullet-screen.py")
EXPECTED_BASE_SHA256 = "1cda47e2d4f8df1bfbc15d2075044a721afb9b0995c58f388cbe7d9c39c71679"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("slow-tip C5 auditor base identity mismatch")

source = BASE.read_text(encoding="utf-8")
replacements = (
    ("RC6-2026-09-02-slow-tip-bullet-screen-attempt-47", "RC6-2026-09-02-slow-tip-bullet-screen-c5-attempt-52", 2, "roots"),
    ('CELLS = (("D12", 12), ("D16", 16), ("D20", 20), ("D24", 24))', 'CELLS = (("C5F48", 48), ("C5F60", 60), ("C5F72", 72), ("C5F96", 96))', 1, "cells"),
    ('scripts/run-rc6-slow-tip-bullet-screen-scene.py', 'scripts/run-rc6-slow-tip-bullet-screen-c5-scene.py', 1, "scene tool"),
    ('scripts/run-rc6-slow-tip-bullet-screen.py', 'scripts/run-rc6-slow-tip-bullet-screen-c5.py', 1, "runner"),
    ('specs/ai-native-studio-rc6-slow-tip-bullet-screen.v0.55.json', 'specs/ai-native-studio-rc6-slow-tip-bullet-screen-c5.v0.60.json', 1, "spec"),
    (
        '    contact = next((sample["frame"] for sample in samples if sample["ballCupSurfaceSeparationMeters"] <= 0.01), None)',
        '    motor_actuation = 1\n    maximum_hinge_drift = max(sample["hingePivotDriftMeters"] for sample in samples)\n    expected_motor_degrees_per_second = 60.0 * 24.0 / (drive_end - 1)',
        1,
        "motor metric derivation",
    ),
    (
        '        and row["metrics"]["contactFrame"] == contact',
        '        and row["metrics"]["motorActuationFrame"] == motor_actuation',
        1,
        "motor actuation metric",
    ),
    (
        '        and row["metrics"]["requiredEffectorSubframes"] == required\n    )',
        '        and row["metrics"]["requiredEffectorSubframes"] == required\n        and abs(row["metrics"]["maximumHingePivotDriftMeters"] - maximum_hinge_drift) <= 1e-8\n        and row["configuration"]["hingePivotWorldMeters"] == [0.47, 0.0, 0.0]\n        and row["configuration"]["hingeAnchorLocationMeters"] == [0.47, 0.0, -0.08]\n        and abs(abs(row["configuration"]["hingeAxisWorld"][1]) - 1.0) <= 1e-8\n        and row["configuration"]["hingeAngularLimitsDegrees"] == [-60.0, 5.0]\n        and abs(row["configuration"]["cupAngularDamping"] - 0.8) <= 1e-8\n        and abs(abs(row["configuration"]["motorAxisWorld"][1]) - 1.0) <= 1e-8\n        and abs(row["configuration"]["motorTargetDegreesPerSecond"] - expected_motor_degrees_per_second) <= 1e-8\n        and abs(row["configuration"]["motorAngularMaximumImpulse"] - 1.0) <= 1e-8\n        and row["configuration"]["candidateDomainDimensionsMeters"] == [0.9, 0.5, 0.58]\n    )',
        1,
        "hinge and motor metrics recompute",
    ),
    (
        '    checks_recompute &= row["status"] == ("PASS" if all(row["checks"].values()) else "FAIL")',
        '    expected_hinge_stable = maximum_hinge_drift <= 0.005\n    expected_mechanical_stop = peak <= 65.0\n    checks_recompute &= (\n        row["checks"]["hingePivotStableWithinFiveMillimeters"] == expected_hinge_stable\n        and row["checks"]["mechanicalHingeStopHoldsAtMost65Degrees"] == expected_mechanical_stop\n        and row["checks"]["hingeAndMotorConstraintsExact"]\n        and row["checks"]["motorActuationAtFrameOne"]\n        and row["checks"]["boundedMotorIsOnlyActuator"]\n        and row["status"] == ("PASS" if all(row["checks"].values()) else "FAIL")\n    )',
        1,
        "hinge and motor checks recompute",
    ),
    ('bfs.rc6SlowTipBulletScreenIndependentAudit.v0.1', 'bfs.rc6SlowTipBulletScreenC5IndependentAudit.v0.1', 1, "schema"),
    ('RC6_SLOW_TIP_BULLET_SCREEN_AUDIT=', 'RC6_SLOW_TIP_BULLET_SCREEN_C5_AUDIT=', 1, "marker"),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"slow-tip C5 auditor {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#C5_ATTEMPT52", "exec"), globals(), globals())
