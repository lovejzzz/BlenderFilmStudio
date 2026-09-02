#!/usr/bin/env python3
"""Copy immutable attempt-68 cache and compare fractions distance 0.25 with 0.5."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-moving-liquid-subframes-data-comparison.py")
EXPECTED_BASE_SHA256 = "4028edf0b35fba0882d72c12fdb4548ded47ada1eb6920c803617a577fb414c6"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("fractions-distance Data-comparison runner base identity mismatch")
    source = BASE.read_text(encoding="utf-8")
    replacements = [
        ('"""Copy immutable attempt-61 cache and compare two-subframe Data with attempt-60."""', '"""Copy immutable attempt-68 cache and compare fractions distance 0.25 with 0.5."""', "docstring"),
        ("RC6-2026-09-02-moving-liquid-subframes-data-comparison-attempt-62", "RC6-2026-09-02-moving-liquid-fractions-distance-data-comparison-attempt-69", "fresh roots"),
        ("RC6-2026-09-02-moving-liquid-effector-subframes-attempt-61/mantaflow-cache", "RC6-2026-09-02-moving-liquid-fractions-distance-attempt-68/mantaflow-cache", "source cache"),
        ("experiments/physical-richness/RC6-2026-09-02-moving-liquid-effector-subframes-attempt-61/result.json", "experiments/physical-richness/RC6-2026-09-02-moving-liquid-fractions-distance-attempt-68/result.json", "current result"),
        ("experiments/physical-richness/RC6-2026-09-02-moving-liquid-effector-subframes-attempt-61/independent-audit.json", "experiments/physical-richness/RC6-2026-09-02-moving-liquid-fractions-distance-attempt-68/independent-audit.json", "current audit"),
        ("experiments/physical-richness/RC6-2026-09-02-moving-liquid-effector-distance-data-occupancy-attempt-60/result.json", "experiments/physical-richness/RC6-2026-09-02-moving-liquid-particle-radius-data-comparison-attempt-66/result.json", "baseline result"),
        ("experiments/physical-richness/RC6-2026-09-02-moving-liquid-effector-distance-data-occupancy-attempt-60/independent-audit.json", "experiments/physical-richness/RC6-2026-09-02-moving-liquid-particle-radius-data-comparison-attempt-66/independent-audit.json", "baseline audit"),
        ('"scripts/audit-rc6-moving-liquid-subframes-data-comparison.py"', '"scripts/audit-rc6-moving-liquid-fractions-distance-data-comparison.py"', "auditor"),
        ('"specs/ai-native-studio-rc6-moving-liquid-subframes-data-comparison.v0.73.json"', '"specs/ai-native-studio-rc6-moving-liquid-fractions-distance-data-comparison.v0.80.json"', "spec"),
        ('"--expected-subframes", "2"', '"--expected-subframes", "1"', "subframes binding"),
        ('"--current-label", "subframes-2"', '"--current-label", "fractions-distance-0p25"', "current label"),
        ('"--baseline-label", "subframes-1"', '"--baseline-label", "fractions-distance-0p5"', "baseline label"),
        ('"bfs.rc6MovingLiquidSubframesDataComparisonAdmission.v0.1"', '"bfs.rc6MovingLiquidFractionsDistanceDataComparisonAdmission.v0.1"', "admission schema"),
        ('"bfs.rc6MovingLiquidSubframesDataComparisonReceipt.v0.1"', '"bfs.rc6MovingLiquidFractionsDistanceDataComparisonReceipt.v0.1"', "receipt schema"),
        ('"RC6_MOVING_LIQUID_SUBFRAMES_DATA_COMPARISON_AUDIT="', '"RC6_MOVING_LIQUID_FRACTIONS_DISTANCE_DATA_COMPARISON_AUDIT="', "audit marker"),
        ('"RC6_MOVING_LIQUID_SUBFRAMES_DATA_COMPARISON_RUN="', '"RC6_MOVING_LIQUID_FRACTIONS_DISTANCE_DATA_COMPARISON_RUN="', "runner marker"),
    ]
    for before, after, label in replacements:
        expected = 2 if label == "fresh roots" else 1
        if source.count(before) != expected:
            raise RuntimeError(f"fractions-distance Data-comparison runner {label} target mismatch")
        source = source.replace(before, after)
    if source.count("attempt61") != 4 or source.count("attempt60") != 3:
        raise RuntimeError("fractions-distance Data-comparison runner baseline-key count mismatch")
    source = source.replace("attempt61", "attempt68").replace("attempt60", "attempt66")
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#FRACTIONS_DISTANCE_DATA_COMPARISON_V01", "exec"), globals(), globals())
