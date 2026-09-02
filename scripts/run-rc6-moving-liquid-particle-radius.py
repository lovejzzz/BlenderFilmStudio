#!/usr/bin/env python3
"""Run one 24-frame moving-liquid test with only particle_radius at 1.8."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-moving-liquid-effector-distance.py")
EXPECTED_BASE_SHA256 = "5237861edf167e647e3543bb1c3176be5d70dc52eb850497835a584348782d5e"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("moving-liquid particle-radius runner base identity mismatch")
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
    baseline_before = '    (ATTEMPT58_AUDIT, spec["baseline"]["attempt58AuditFileSha256"]),\n'
    baseline_after = baseline_before + (
        '    (ATTEMPT59_RESULT, spec["baseline"]["attempt59ResultFileSha256"]),\n'
        '    (ATTEMPT59_AUDIT, spec["baseline"]["attempt59AuditFileSha256"]),\n'
        '    (ATTEMPT60_AUDIT, spec["baseline"]["attempt60AuditFileSha256"]),\n'
        '    (ATTEMPT61_AUDIT, spec["baseline"]["attempt61AuditFileSha256"]),\n'
        '    (ATTEMPT62_AUDIT, spec["baseline"]["attempt62AuditFileSha256"]),\n'
        '    (ATTEMPT63_RESULT, spec["baseline"]["attempt63ResultFileSha256"]),\n'
        '    (ATTEMPT63_AUDIT, spec["baseline"]["attempt63AuditFileSha256"]),\n'
        '    (ATTEMPT64_AUDIT, spec["baseline"]["attempt64AuditFileSha256"]),\n'
        '    (ATTEMPT20_MATRIX, spec["baseline"]["attempt20MatrixFileSha256"]),\n'
    )
    replacements = [
        ('"""Run one 24-frame moving-liquid test with only effector distance at 2.0."""', '"""Run one 24-frame moving-liquid test with only particle_radius at 1.8."""', "docstring"),
        ("RC6-2026-09-02-moving-liquid-effector-distance-attempt-59", "RC6-2026-09-02-moving-liquid-particle-radius-attempt-65", "fresh roots"),
        (constants_before, constants_after, "new baseline constants"),
        ('"scripts/run-rc6-moving-liquid-effector-distance-scene.py"', '"scripts/run-rc6-moving-liquid-particle-radius-scene.py"', "scene tool"),
        ('"scripts/audit-rc6-moving-liquid-effector-distance.py"', '"scripts/audit-rc6-moving-liquid-particle-radius.py"', "auditor"),
        ('"specs/ai-native-studio-rc6-moving-liquid-effector-distance.v0.70.json"', '"specs/ai-native-studio-rc6-moving-liquid-particle-radius.v0.76.json"', "spec"),
        (baseline_before, baseline_after, "new baseline checks"),
        ('"RC6_MOVING_LIQUID_EFFECTOR_DISTANCE="', '"RC6_MOVING_LIQUID_PARTICLE_RADIUS="', "process marker"),
        ('"RC6_MOVING_LIQUID_EFFECTOR_DISTANCE_RUN="', '"RC6_MOVING_LIQUID_PARTICLE_RADIUS_RUN="', "runner marker"),
        ('"bfs.rc6MovingLiquidEffectorDistanceAdmission.v0.1"', '"bfs.rc6MovingLiquidParticleRadiusAdmission.v0.1"', "admission schema"),
        ('"bfs.rc6MovingLiquidEffectorDistanceFailure.v0.1"', '"bfs.rc6MovingLiquidParticleRadiusFailure.v0.1"', "failure schema"),
        ('"bfs.rc6MovingLiquidEffectorDistanceReceipt.v0.1"', '"bfs.rc6MovingLiquidParticleRadiusReceipt.v0.1"', "receipt schema"),
        ('"PASS_MOVING_LIQUID_EFFECTOR_DISTANCE"', '"PASS_MOVING_LIQUID_PARTICLE_RADIUS"', "pass verdict"),
        ('"FAIL_MOVING_LIQUID_EFFECTOR_DISTANCE"', '"FAIL_MOVING_LIQUID_PARTICLE_RADIUS"', "fail verdict"),
        ('"logs/01-effector-distance.stdout.log"', '"logs/01-particle-radius.stdout.log"', "stdout log"),
        ('"logs/01-effector-distance.stderr.log"', '"logs/01-particle-radius.stderr.log"', "stderr log"),
        ('"processes/01-effector-distance.json"', '"processes/01-particle-radius.json"', "process receipt"),
    ]
    for before, after, label in replacements:
        expected = 2 if label == "fresh roots" else 1
        if source.count(before) != expected:
            raise RuntimeError(f"moving-liquid particle-radius runner {label} target mismatch")
        source = source.replace(before, after)
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#MOVING_LIQUID_PARTICLE_RADIUS_V01", "exec"), globals(), globals())
