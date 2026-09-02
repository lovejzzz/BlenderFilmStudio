#!/usr/bin/env python3
"""Repeat exact C12 while changing only liquid timesteps_max 4 to 8."""

import hashlib
import importlib.util
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-real-impact-liquid-preview-c12-scene.py")
EXPECTED_BASE_SHA256 = "d6da065f90cc48e2cd97cf49488d7fe658ab3e66edfddc07f8c9968df78e4bfb"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("C14 scene base identity mismatch")
    module_spec = importlib.util.spec_from_file_location("rc6_c12_scene_base", BASE)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    source = module.transformed_source()
    replacements = (
        ("settings.timesteps_max = 4", "settings.timesteps_max = 8", "timestep maximum assignment", 1),
        ("settings.timesteps_max == 4", "settings.timesteps_max == 8", "timestep maximum check", 1),
        ('"bfs.rc6RealImpactLiquidPreviewC12Result.v0.1"', '"bfs.rc6RealImpactLiquidTimestepMaxC14Result.v0.1"', "result schema", 1),
        ('"PASS_REAL_IMPACT_LIQUID_PREVIEW"', '"PASS_REAL_IMPACT_LIQUID_TIMESTEP_MAX_C14"', "pass verdict", 1),
        ('"FAIL_REAL_IMPACT_LIQUID_PREVIEW"', '"FAIL_REAL_IMPACT_LIQUID_TIMESTEP_MAX_C14"', "fail verdict", 1),
        ("RC6_REAL_IMPACT_LIQUID_PREVIEW=", "RC6_REAL_IMPACT_LIQUID_TIMESTEP_MAX_C14=", "result marker", 1),
        (
            "One 36-frame Preview-96 same-solve R40 basketball-impact/APIC spill result with explicit floor/ramp effectors; no full landing, persistence, final resolution, render, film quality, deformation or generalized liquid claim.",
            "One 36-frame Preview-96 same-solve R40 basketball-impact/APIC spill test changing only liquid timesteps_max 4 to 8; no full landing, persistence, final resolution, render, film quality, deformation or generalized liquid claim.",
            "claim ceiling",
            1,
        ),
    )
    for before, after, label, expected in replacements:
        if source.count(before) != expected:
            raise RuntimeError(f"C14 scene {label} target mismatch")
        source = source.replace(before, after)
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#RC6_REAL_IMPACT_LIQUID_TIMESTEP_MAX_C14", "exec"), globals(), globals())
