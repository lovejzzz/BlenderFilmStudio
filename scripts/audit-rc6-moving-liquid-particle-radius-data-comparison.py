#!/usr/bin/env python3
"""Independently audit attempt-66 copied-VDB particle-radius comparison."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-moving-liquid-subframes-data-comparison.py")
EXPECTED_BASE_SHA256 = "4606fe8cf84a9f2ad69c692743fa78f1abc53f2c5887f8585fc45c4da36d29dc"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("particle-radius Data-comparison auditor base identity mismatch")
    source = BASE.read_text(encoding="utf-8")
    replacements = [
        ('"""Independently audit attempt-62 copied-VDB subframe comparison."""', '"""Independently audit attempt-66 copied-VDB particle-radius comparison."""', "docstring"),
        ("RC6-2026-09-02-moving-liquid-subframes-data-comparison-attempt-62", "RC6-2026-09-02-moving-liquid-particle-radius-data-comparison-attempt-66", "fresh roots"),
        ("RC6-2026-09-02-moving-liquid-effector-subframes-attempt-61/mantaflow-cache", "RC6-2026-09-02-moving-liquid-particle-radius-attempt-65/mantaflow-cache", "source cache"),
        ("experiments/physical-richness/RC6-2026-09-02-moving-liquid-effector-subframes-attempt-61/result.json", "experiments/physical-richness/RC6-2026-09-02-moving-liquid-particle-radius-attempt-65/result.json", "current result"),
        ("experiments/physical-richness/RC6-2026-09-02-moving-liquid-effector-subframes-attempt-61/independent-audit.json", "experiments/physical-richness/RC6-2026-09-02-moving-liquid-particle-radius-attempt-65/independent-audit.json", "current audit"),
        ("experiments/physical-richness/RC6-2026-09-02-moving-liquid-effector-distance-data-occupancy-attempt-60/result.json", "experiments/physical-richness/RC6-2026-09-02-moving-liquid-timesteps-data-comparison-attempt-64/result.json", "baseline result"),
        ("experiments/physical-richness/RC6-2026-09-02-moving-liquid-effector-distance-data-occupancy-attempt-60/independent-audit.json", "experiments/physical-richness/RC6-2026-09-02-moving-liquid-timesteps-data-comparison-attempt-64/independent-audit.json", "baseline audit"),
        ('"scripts/run-rc6-moving-liquid-subframes-data-comparison.py"', '"scripts/run-rc6-moving-liquid-particle-radius-data-comparison.py"', "runner"),
        ('"specs/ai-native-studio-rc6-moving-liquid-subframes-data-comparison.v0.73.json"', '"specs/ai-native-studio-rc6-moving-liquid-particle-radius-data-comparison.v0.77.json"', "spec"),
        ('"--expected-subframes", "2"', '"--expected-subframes", "1"', "subframes binding"),
        ('"--current-label", "subframes-2"', '"--current-label", "particle-radius-1p8"', "current label"),
        ('"--baseline-label", "subframes-1"', '"--baseline-label", "particle-radius-1p6"', "baseline label"),
        ('{"current": "subframes-2", "baseline": "subframes-1"}', '{"current": "particle-radius-1p8", "baseline": "particle-radius-1p6"}', "label oracle"),
        ('"bfs.rc6MovingLiquidSubframesDataComparisonIndependentAudit.v0.1"', '"bfs.rc6MovingLiquidParticleRadiusDataComparisonIndependentAudit.v0.1"', "audit schema"),
        ('"RC6_MOVING_LIQUID_SUBFRAMES_DATA_COMPARISON_AUDIT="', '"RC6_MOVING_LIQUID_PARTICLE_RADIUS_DATA_COMPARISON_AUDIT="', "audit marker"),
    ]
    for before, after, label in replacements:
        expected = 2 if label == "fresh roots" else 1
        if source.count(before) != expected:
            raise RuntimeError(f"particle-radius Data-comparison auditor {label} target mismatch")
        source = source.replace(before, after)
    if source.count("attempt61") != 6 or source.count("attempt60") != 4:
        raise RuntimeError("particle-radius Data-comparison auditor baseline-key count mismatch")
    source = source.replace("attempt61", "attempt65").replace("attempt60", "attempt64")
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#PARTICLE_RADIUS_DATA_COMPARISON_V01", "exec"), globals(), globals())
