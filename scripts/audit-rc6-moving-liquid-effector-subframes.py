#!/usr/bin/env python3
"""Independently audit the attempt-61 two-subframe moving-liquid test."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-moving-liquid-effector-distance.py")
EXPECTED_BASE_SHA256 = "d97cbf62a45517fe8e1e3c90a1abad6f87d09bae1445d42db716118b83a2200f"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("moving-liquid effector-subframes auditor base identity mismatch")
    source = BASE.read_text(encoding="utf-8")
    constants_before = 'ATTEMPT58_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-data-occupancy-attempt-58/independent-audit.json"\n'
    constants_after = constants_before + (
        'ATTEMPT59_RESULT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-effector-distance-attempt-59/result.json"\n'
        'ATTEMPT59_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-effector-distance-attempt-59/independent-audit.json"\n'
        'ATTEMPT60_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-effector-distance-data-occupancy-attempt-60/independent-audit.json"\n'
    )
    baseline_before = 'sha(ATTEMPT58_AUDIT) == spec["baseline"]["attempt58AuditFileSha256"]'
    baseline_after = baseline_before + ' and sha(ATTEMPT59_RESULT) == spec["baseline"]["attempt59ResultFileSha256"] and sha(ATTEMPT59_AUDIT) == spec["baseline"]["attempt59AuditFileSha256"] and sha(ATTEMPT60_AUDIT) == spec["baseline"]["attempt60AuditFileSha256"]'
    config_before = 'abs(result["configuration"]["cupEffectorSurfaceDistanceCells"] - 2.0) <= 1e-6 and result["configuration"]["cupEffectorSubframes"] == 1'
    config_after = 'abs(result["configuration"]["cupEffectorSurfaceDistanceCells"] - 2.0) <= 1e-6 and result["configuration"]["cupEffectorSubframes"] == 2'
    replacements = [
        (
            '"""Independently audit the attempt-59 2.0-cell moving-liquid test."""',
            '"""Independently audit the attempt-61 two-subframe moving-liquid test."""',
            "docstring",
        ),
        ("RC6-2026-09-02-moving-liquid-effector-distance-attempt-59", "RC6-2026-09-02-moving-liquid-effector-subframes-attempt-61", "fresh roots"),
        (constants_before, constants_after, "new baseline constants"),
        ('"scripts/run-rc6-moving-liquid-effector-distance-scene.py"', '"scripts/run-rc6-moving-liquid-effector-subframes-scene.py"', "scene tool"),
        ('"scripts/run-rc6-moving-liquid-effector-distance.py"', '"scripts/run-rc6-moving-liquid-effector-subframes.py"', "runner"),
        ('"specs/ai-native-studio-rc6-moving-liquid-effector-distance.v0.70.json"', '"specs/ai-native-studio-rc6-moving-liquid-effector-subframes.v0.72.json"', "spec"),
        (config_before, config_after, "configuration check"),
        (baseline_before, baseline_after, "new baseline checks"),
        ('"logs/01-effector-distance.stdout.log"', '"logs/01-effector-subframes.stdout.log"', "stdout log"),
        ('"logs/01-effector-distance.stderr.log"', '"logs/01-effector-subframes.stderr.log"', "stderr log"),
        ('"processes/01-effector-distance.json"', '"processes/01-effector-subframes.json"', "process receipt"),
        ('"bfs.rc6MovingLiquidEffectorDistanceIndependentAudit.v0.1"', '"bfs.rc6MovingLiquidEffectorSubframesIndependentAudit.v0.1"', "audit schema"),
        ('"RC6_MOVING_LIQUID_EFFECTOR_DISTANCE_AUDIT="', '"RC6_MOVING_LIQUID_EFFECTOR_SUBFRAMES_AUDIT="', "audit marker"),
    ]
    for before, after, label in replacements:
        expected = 2 if label == "fresh roots" else 1
        if source.count(before) != expected:
            raise RuntimeError(f"moving-liquid effector-subframes auditor {label} target mismatch")
        source = source.replace(before, after)
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#MOVING_LIQUID_EFFECTOR_SUBFRAMES_V01", "exec"), globals(), globals())
