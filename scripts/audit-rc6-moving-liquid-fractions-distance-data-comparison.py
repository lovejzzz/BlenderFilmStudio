#!/usr/bin/env python3
"""Independently audit attempt-69 copied-VDB fractions-distance comparison."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-moving-liquid-subframes-data-comparison.py")
EXPECTED_BASE_SHA256 = "4606fe8cf84a9f2ad69c692743fa78f1abc53f2c5887f8585fc45c4da36d29dc"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("fractions-distance Data-comparison auditor base identity mismatch")
    source = BASE.read_text(encoding="utf-8")
    replacements = [
        ('"""Independently audit attempt-62 copied-VDB subframe comparison."""', '"""Independently audit attempt-69 copied-VDB fractions-distance comparison."""', "docstring"),
        ("RC6-2026-09-02-moving-liquid-subframes-data-comparison-attempt-62", "RC6-2026-09-02-moving-liquid-fractions-distance-data-comparison-attempt-69", "fresh roots"),
        ("RC6-2026-09-02-moving-liquid-effector-subframes-attempt-61/mantaflow-cache", "RC6-2026-09-02-moving-liquid-fractions-distance-attempt-68/mantaflow-cache", "source cache"),
        ("experiments/physical-richness/RC6-2026-09-02-moving-liquid-effector-subframes-attempt-61/result.json", "experiments/physical-richness/RC6-2026-09-02-moving-liquid-fractions-distance-attempt-68/result.json", "current result"),
        ("experiments/physical-richness/RC6-2026-09-02-moving-liquid-effector-subframes-attempt-61/independent-audit.json", "experiments/physical-richness/RC6-2026-09-02-moving-liquid-fractions-distance-attempt-68/independent-audit.json", "current audit"),
        ("experiments/physical-richness/RC6-2026-09-02-moving-liquid-effector-distance-data-occupancy-attempt-60/result.json", "experiments/physical-richness/RC6-2026-09-02-moving-liquid-particle-radius-data-comparison-attempt-66/result.json", "baseline result"),
        ("experiments/physical-richness/RC6-2026-09-02-moving-liquid-effector-distance-data-occupancy-attempt-60/independent-audit.json", "experiments/physical-richness/RC6-2026-09-02-moving-liquid-particle-radius-data-comparison-attempt-66/independent-audit.json", "baseline audit"),
        ('"scripts/run-rc6-moving-liquid-subframes-data-comparison.py"', '"scripts/run-rc6-moving-liquid-fractions-distance-data-comparison.py"', "runner"),
        ('"specs/ai-native-studio-rc6-moving-liquid-subframes-data-comparison.v0.73.json"', '"specs/ai-native-studio-rc6-moving-liquid-fractions-distance-data-comparison.v0.80.json"', "spec"),
        ('"--expected-subframes", "2"', '"--expected-subframes", "1"', "subframes binding"),
        ('"--current-label", "subframes-2"', '"--current-label", "fractions-distance-0p25"', "current label"),
        ('"--baseline-label", "subframes-1"', '"--baseline-label", "fractions-distance-0p5"', "baseline label"),
        ('{"current": "subframes-2", "baseline": "subframes-1"}', '{"current": "fractions-distance-0p25", "baseline": "fractions-distance-0p5"}', "label oracle"),
        ('"bfs.rc6MovingLiquidSubframesDataComparisonIndependentAudit.v0.1"', '"bfs.rc6MovingLiquidFractionsDistanceDataComparisonIndependentAudit.v0.1"', "audit schema"),
        ('"RC6_MOVING_LIQUID_SUBFRAMES_DATA_COMPARISON_AUDIT="', '"RC6_MOVING_LIQUID_FRACTIONS_DISTANCE_DATA_COMPARISON_AUDIT="', "audit marker"),
    ]
    for before, after, label in replacements:
        expected = 2 if label == "fresh roots" else 1
        if source.count(before) != expected:
            raise RuntimeError(f"fractions-distance Data-comparison auditor {label} target mismatch")
        source = source.replace(before, after)
    if source.count("attempt61") != 6 or source.count("attempt60") != 4:
        raise RuntimeError("fractions-distance Data-comparison auditor baseline-key count mismatch")
    source = source.replace("attempt61", "attempt68").replace("attempt60", "attempt66")
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#FRACTIONS_DISTANCE_DATA_COMPARISON_V01", "exec"), globals(), globals())
