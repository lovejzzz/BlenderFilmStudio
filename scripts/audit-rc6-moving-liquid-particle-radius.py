#!/usr/bin/env python3
"""Independently audit the attempt-65 particle-radius moving-liquid test."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-moving-liquid-effector-distance.py")
EXPECTED_BASE_SHA256 = "d97cbf62a45517fe8e1e3c90a1abad6f87d09bae1445d42db716118b83a2200f"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("moving-liquid particle-radius auditor base identity mismatch")
    source = BASE.read_text(encoding="utf-8")
    constants_before = 'ATTEMPT58_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-data-occupancy-attempt-58/independent-audit.json"\n'
    constants_after = constants_before + (
        'ATTEMPT59_RESULT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-effector-distance-attempt-59/result.json"\n'
        'ATTEMPT59_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-effector-distance-attempt-59/independent-audit.json"\n'
        'ATTEMPT60_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-effector-distance-data-occupancy-attempt-60/independent-audit.json"\n'
        'ATTEMPT61_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-effector-subframes-attempt-61/independent-audit.json"\n'
        'ATTEMPT62_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-subframes-data-comparison-attempt-62/independent-audit.json"\n'
        'ATTEMPT63_RESULT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-solver-timesteps-attempt-63/result.json"\n'
        'ATTEMPT63_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-solver-timesteps-attempt-63/independent-audit.json"\n'
        'ATTEMPT64_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-timesteps-data-comparison-attempt-64/independent-audit.json"\n'
        'ATTEMPT20_MATRIX = RESEARCH / "experiments/physical-richness/RC6-2026-09-01-particle-conservation-attempt-20/matrix.json"\n'
    )
    baseline_before = 'sha(ATTEMPT58_AUDIT) == spec["baseline"]["attempt58AuditFileSha256"]'
    baseline_after = baseline_before + ' and sha(ATTEMPT59_RESULT) == spec["baseline"]["attempt59ResultFileSha256"] and sha(ATTEMPT59_AUDIT) == spec["baseline"]["attempt59AuditFileSha256"] and sha(ATTEMPT60_AUDIT) == spec["baseline"]["attempt60AuditFileSha256"] and sha(ATTEMPT61_AUDIT) == spec["baseline"]["attempt61AuditFileSha256"] and sha(ATTEMPT62_AUDIT) == spec["baseline"]["attempt62AuditFileSha256"] and sha(ATTEMPT63_RESULT) == spec["baseline"]["attempt63ResultFileSha256"] and sha(ATTEMPT63_AUDIT) == spec["baseline"]["attempt63AuditFileSha256"] and sha(ATTEMPT64_AUDIT) == spec["baseline"]["attempt64AuditFileSha256"] and sha(ATTEMPT20_MATRIX) == spec["baseline"]["attempt20MatrixFileSha256"]'
    config_before = 'abs(result["configuration"]["particleRadius"] - 1.6) <= 1e-6 and abs(result["configuration"]["meshParticleRadius"] - 2.5) <= 1e-6 and abs(result["configuration"]["cupEffectorSurfaceDistanceCells"] - 2.0) <= 1e-6 and result["configuration"]["cupEffectorSubframes"] == 1'
    config_after = 'abs(result["configuration"]["particleRadius"] - 1.8) <= 1e-6 and abs(result["configuration"]["meshParticleRadius"] - 2.5) <= 1e-6 and abs(result["configuration"]["cupEffectorSurfaceDistanceCells"] - 2.0) <= 1e-6 and result["configuration"]["cupEffectorSubframes"] == 1 and result["configuration"]["timestepsMin"] == 2 and result["configuration"]["timestepsMax"] == 4 and abs(result["configuration"]["cflCondition"] - 2.0) <= 1e-6'
    replacements = [
        ('"""Independently audit the attempt-59 2.0-cell moving-liquid test."""', '"""Independently audit the attempt-65 particle-radius moving-liquid test."""', "docstring"),
        ("RC6-2026-09-02-moving-liquid-effector-distance-attempt-59", "RC6-2026-09-02-moving-liquid-particle-radius-attempt-65", "fresh roots"),
        (constants_before, constants_after, "new baseline constants"),
        ('"scripts/run-rc6-moving-liquid-effector-distance-scene.py"', '"scripts/run-rc6-moving-liquid-particle-radius-scene.py"', "scene tool"),
        ('"scripts/run-rc6-moving-liquid-effector-distance.py"', '"scripts/run-rc6-moving-liquid-particle-radius.py"', "runner"),
        ('"specs/ai-native-studio-rc6-moving-liquid-effector-distance.v0.70.json"', '"specs/ai-native-studio-rc6-moving-liquid-particle-radius.v0.76.json"', "spec"),
        (config_before, config_after, "configuration check"),
        (baseline_before, baseline_after, "new baseline checks"),
        ('"logs/01-effector-distance.stdout.log"', '"logs/01-particle-radius.stdout.log"', "stdout log"),
        ('"logs/01-effector-distance.stderr.log"', '"logs/01-particle-radius.stderr.log"', "stderr log"),
        ('"processes/01-effector-distance.json"', '"processes/01-particle-radius.json"', "process receipt"),
        ('"bfs.rc6MovingLiquidEffectorDistanceIndependentAudit.v0.1"', '"bfs.rc6MovingLiquidParticleRadiusIndependentAudit.v0.1"', "audit schema"),
        ('"RC6_MOVING_LIQUID_EFFECTOR_DISTANCE_AUDIT="', '"RC6_MOVING_LIQUID_PARTICLE_RADIUS_AUDIT="', "audit marker"),
    ]
    for before, after, label in replacements:
        expected = 2 if label == "fresh roots" else 1
        if source.count(before) != expected:
            raise RuntimeError(f"moving-liquid particle-radius auditor {label} target mismatch")
        source = source.replace(before, after)
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#MOVING_LIQUID_PARTICLE_RADIUS_V01", "exec"), globals(), globals())
