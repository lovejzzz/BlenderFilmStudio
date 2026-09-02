#!/usr/bin/env python3
"""Repeat exact C18 while changing only simulation particle radius 1.8 to 1.6."""

import hashlib
import importlib.util
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-real-impact-liquid-fractions-threshold-c18-scene.py")
EXPECTED_BASE_SHA256 = "b756dc5a72fa42fb7c9c87793de371bfbcd8b6a363f1a180ba394bb98d64e586"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("C20 scene base identity mismatch")
    module_spec = importlib.util.spec_from_file_location("rc6_c18_scene_base", BASE)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    source = module.transformed_source()
    old_claim = "One 36-frame Preview-96 same-solve R40 basketball-impact/APIC spill test changing only fractional-obstacle threshold 0.05 to 0.10 on the retained C14 CFL2/timesteps2/8 baseline; no full landing, persistence, final resolution, render, film quality, deformation or generalized liquid claim."
    new_claim = "One 36-frame Preview-96 same-solve R40 basketball-impact/APIC spill test changing only simulation particle_radius 1.8 to 1.6 on the retained C18 fractions_threshold0.10/CFL2/timesteps2/8 baseline; no full landing, persistence, final resolution, render, film quality, deformation or generalized liquid claim."
    replacements = (
        ("settings.particle_radius = 1.8", "settings.particle_radius = 1.6", "particle radius assignment", 1),
        ("abs(settings.particle_radius - 1.8)", "abs(settings.particle_radius - 1.6)", "particle radius check", 1),
        ('"bfs.rc6RealImpactLiquidFractionsThresholdC18Result.v0.1"', '"bfs.rc6RealImpactLiquidParticleRadiusC20Result.v0.1"', "result schema", 1),
        ('"PASS_REAL_IMPACT_LIQUID_FRACTIONS_THRESHOLD_C18"', '"PASS_REAL_IMPACT_LIQUID_PARTICLE_RADIUS_C20"', "pass verdict", 1),
        ('"FAIL_REAL_IMPACT_LIQUID_FRACTIONS_THRESHOLD_C18"', '"FAIL_REAL_IMPACT_LIQUID_PARTICLE_RADIUS_C20"', "fail verdict", 1),
        ("RC6_REAL_IMPACT_LIQUID_FRACTIONS_THRESHOLD_C18=", "RC6_REAL_IMPACT_LIQUID_PARTICLE_RADIUS_C20=", "result marker", 1),
        (old_claim, new_claim, "claim ceiling", 1),
    )
    for before, after, label, expected in replacements:
        if source.count(before) != expected:
            raise RuntimeError(f"C20 scene {label} target mismatch")
        source = source.replace(before, after)
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#RC6_REAL_IMPACT_LIQUID_PARTICLE_RADIUS_C20", "exec"), globals(), globals())
