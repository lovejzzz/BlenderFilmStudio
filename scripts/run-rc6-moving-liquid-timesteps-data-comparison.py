#!/usr/bin/env python3
"""Bind the reusable Data comparator to attempt-63 versus attempt-60."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-moving-liquid-subframes-data-comparison.py")
EXPECTED_BASE_SHA256 = "4028edf0b35fba0882d72c12fdb4548ded47ada1eb6920c803617a577fb414c6"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("timesteps Data-comparison runner base identity mismatch")
    source = BASE.read_text(encoding="utf-8")
    replacements = [
        ('"""Copy immutable attempt-61 cache and compare two-subframe Data with attempt-60."""', '"""Copy immutable attempt-63 cache and compare two-timestep Data with attempt-60."""', "docstring"),
        ("RC6-2026-09-02-moving-liquid-subframes-data-comparison-attempt-62", "RC6-2026-09-02-moving-liquid-timesteps-data-comparison-attempt-64", "fresh roots"),
        ("RC6-2026-09-02-moving-liquid-effector-subframes-attempt-61/mantaflow-cache", "RC6-2026-09-02-moving-liquid-solver-timesteps-attempt-63/mantaflow-cache", "source cache"),
        ("experiments/physical-richness/RC6-2026-09-02-moving-liquid-effector-subframes-attempt-61/result.json", "experiments/physical-richness/RC6-2026-09-02-moving-liquid-solver-timesteps-attempt-63/result.json", "current result"),
        ("experiments/physical-richness/RC6-2026-09-02-moving-liquid-effector-subframes-attempt-61/independent-audit.json", "experiments/physical-richness/RC6-2026-09-02-moving-liquid-solver-timesteps-attempt-63/independent-audit.json", "current audit"),
        ('"scripts/audit-rc6-moving-liquid-subframes-data-comparison.py"', '"scripts/audit-rc6-moving-liquid-timesteps-data-comparison.py"', "auditor"),
        ('"specs/ai-native-studio-rc6-moving-liquid-subframes-data-comparison.v0.73.json"', '"specs/ai-native-studio-rc6-moving-liquid-timesteps-data-comparison.v0.75.json"', "spec"),
        ('"--expected-subframes", "2"', '"--expected-subframes", "1"', "subframes binding"),
        ('"--current-label", "subframes-2"', '"--current-label", "timesteps-min-2"', "current label"),
        ('"--baseline-label", "subframes-1"', '"--baseline-label", "timesteps-min-1"', "baseline label"),
        ('"bfs.rc6MovingLiquidSubframesDataComparisonAdmission.v0.1"', '"bfs.rc6MovingLiquidTimestepsDataComparisonAdmission.v0.1"', "admission schema"),
        ('"bfs.rc6MovingLiquidSubframesDataComparisonReceipt.v0.1"', '"bfs.rc6MovingLiquidTimestepsDataComparisonReceipt.v0.1"', "receipt schema"),
        ('"RC6_MOVING_LIQUID_SUBFRAMES_DATA_COMPARISON_AUDIT="', '"RC6_MOVING_LIQUID_TIMESTEPS_DATA_COMPARISON_AUDIT="', "audit marker"),
        ('"RC6_MOVING_LIQUID_SUBFRAMES_DATA_COMPARISON_RUN="', '"RC6_MOVING_LIQUID_TIMESTEPS_DATA_COMPARISON_RUN="', "runner marker"),
    ]
    for before, after, label in replacements:
        expected = 2 if label == "fresh roots" else 1
        if source.count(before) != expected:
            raise RuntimeError(f"timesteps Data-comparison runner {label} target mismatch")
        source = source.replace(before, after)
    if source.count("attempt61") != 4:
        raise RuntimeError("timesteps Data-comparison runner attempt61 key count mismatch")
    source = source.replace("attempt61", "attempt63")
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#TIMESTEPS_DATA_COMPARISON_V01", "exec"), globals(), globals())
