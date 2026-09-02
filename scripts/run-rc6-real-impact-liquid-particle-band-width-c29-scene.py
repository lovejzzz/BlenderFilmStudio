#!/usr/bin/env python3
"""Repeat exact C18 while changing only particle band width 4 to 3."""

import hashlib
import importlib.util
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-real-impact-liquid-fractions-threshold-c18-scene.py")
EXPECTED_BASE_SHA256 = "b756dc5a72fa42fb7c9c87793de371bfbcd8b6a363f1a180ba394bb98d64e586"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("C29 scene base identity mismatch")
    module_spec = importlib.util.spec_from_file_location("rc6_c18_scene_base", BASE)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    source = module.transformed_source()
    replacements = (
        ("settings.particle_band_width = 4.0", "settings.particle_band_width = 3.0", "particle band width assignment", 1),
        ("abs(settings.particle_band_width - 4.0)", "abs(settings.particle_band_width - 3.0)", "particle band width check", 1),
        ('"bfs.rc6RealImpactLiquidFractionsThresholdC18Result.v0.1"', '"bfs.rc6RealImpactLiquidParticleBandWidthC29Result.v0.1"', "result schema", 1),
        ('"PASS_REAL_IMPACT_LIQUID_FRACTIONS_THRESHOLD_C18"', '"PASS_REAL_IMPACT_LIQUID_PARTICLE_BAND_WIDTH_C29"', "pass verdict", 1),
        ('"FAIL_REAL_IMPACT_LIQUID_FRACTIONS_THRESHOLD_C18"', '"FAIL_REAL_IMPACT_LIQUID_PARTICLE_BAND_WIDTH_C29"', "fail verdict", 1),
        ("RC6_REAL_IMPACT_LIQUID_FRACTIONS_THRESHOLD_C18=", "RC6_REAL_IMPACT_LIQUID_PARTICLE_BAND_WIDTH_C29=", "result marker", 1),
        (
            "One 36-frame Preview-96 same-solve R40 basketball-impact/APIC spill test changing only fractional-obstacle threshold 0.05 to 0.10 on the retained C14 CFL2/timesteps2/8 baseline; no full landing, persistence, final resolution, render, film quality, deformation or generalized liquid claim.",
            "One 36-frame Preview-96 same-solve R40 basketball-impact/APIC spill test changing only particle_band_width 4.0 to 3.0 on exact C18 radius1.8/fractions-threshold0.10/CFL2/timesteps2/8 baseline; this tests high-speed regime sensitivity and does not replace the accepted slow-tip width4.0 result; no full landing, persistence, final resolution, render, film quality, deformation or generalized liquid claim.",
            "claim ceiling",
            1,
        ),
    )
    for before, after, label, expected in replacements:
        if source.count(before) != expected:
            raise RuntimeError(f"C29 scene {label} target mismatch")
        source = source.replace(before, after)
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#RC6_REAL_IMPACT_LIQUID_PARTICLE_BAND_WIDTH_C29", "exec"), globals(), globals())
