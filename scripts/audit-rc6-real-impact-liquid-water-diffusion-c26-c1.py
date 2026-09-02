#!/usr/bin/env python3
"""Audit-only closure for immutable C26 attempt-104's one-comma claim mismatch."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-real-impact-liquid-fractions-threshold-c18-c1.py")
EXPECTED_BASE_SHA256 = "5b922d52d2db6a3ee19a1159b93ed992dfb5cbc0a028087d779654545b3eded0"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("C26 C1 audit base identity mismatch")
    source = BASE.read_text(encoding="utf-8")
    replacements = (
        ("Audit-only closure for the immutable C18 attempt-90 claim wording mismatch.", "Audit-only closure for immutable C26 attempt-104's one-comma claim mismatch.", "module claim", 1),
        ("ai-native-studio-rc6-real-impact-liquid-fractions-threshold-c18-audit-c1.v1.02.json", "ai-native-studio-rc6-real-impact-liquid-water-diffusion-c26-audit-c1.v1.16.json", "spec path", 1),
        ("RC6-2026-09-02-real-impact-liquid-fractions-threshold-c18-attempt-90", "RC6-2026-09-02-real-impact-liquid-water-diffusion-c26-attempt-104", "retained roots", 2),
        ("RC6-2026-09-02-real-impact-liquid-fractions-threshold-c18-audit-c1-attempt-91", "RC6-2026-09-02-real-impact-liquid-water-diffusion-c26-audit-c1-attempt-105", "fresh evidence", 1),
        ("ai-native-studio-rc6-real-impact-liquid-fractions-threshold-c18.v1.01.json", "ai-native-studio-rc6-real-impact-liquid-water-diffusion-c26.v1.15.json", "base spec", 1),
        ("audit-rc6-real-impact-liquid-fractions-threshold-c18.py", "audit-rc6-real-impact-liquid-water-diffusion-c26.py", "base auditor", 1),
        ('spec["retainedAttempt90"]', 'spec["retainedAttempt104"]', "retained key", 5),
        ('"processes/01-real-impact-fractions-threshold.json"', '"processes/01-real-impact-water-diffusion.json"', "process receipt", 1),
        (
            'producer_normalized = result["claimCeiling"].replace("fractional-obstacle threshold", "fractions_threshold").replace("on the retained C14 CFL2/timesteps2/8 baseline", "on exact C14 CFL2/timesteps2/8")',
            'producer_normalized = result["claimCeiling"].replace("exact C18, while", "exact C18 while")',
            "one-comma normalization",
            1,
        ),
        ('"bfs.rc6RealImpactLiquidFractionsThresholdC18AuditC1.v0.1"', '"bfs.rc6RealImpactLiquidWaterDiffusionC26AuditC1.v0.1"', "audit schema", 1),
        (
            '"The producer and preregistered claim ceilings differ only by exact parameter/baseline naming; scope and prohibited claims are identical."',
            '"The producer and preregistered claim ceilings differ only by the comma after exact C18; scope and prohibited claims are identical."',
            "claim finding",
            1,
        ),
        ("RC6_REAL_IMPACT_LIQUID_FRACTIONS_THRESHOLD_C18_AUDIT_C1=", "RC6_REAL_IMPACT_LIQUID_WATER_DIFFUSION_C26_AUDIT_C1=", "result marker", 1),
        ("C18 C1", "C26 C1", "diagnostic labels", 4),
    )
    for before, after, label, expected in replacements:
        if source.count(before) != expected:
            raise RuntimeError(f"C26 C1 {label} target mismatch: {source.count(before)} != {expected}")
        source = source.replace(before, after)
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#RC6_REAL_IMPACT_LIQUID_WATER_DIFFUSION_C26_C1", "exec"), globals(), globals())
