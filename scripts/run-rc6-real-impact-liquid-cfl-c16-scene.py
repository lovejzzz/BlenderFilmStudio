#!/usr/bin/env python3
"""Repeat exact C14 while changing only liquid CFL 2.0 to 1.0."""

import hashlib
import importlib.util
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-real-impact-liquid-timestep-max-c14-scene.py")
EXPECTED_BASE_SHA256 = "f15d8291c18888e067309bc463d732258411021196bcc59fbae5d48261aa86f4"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("C16 scene base identity mismatch")
    module_spec = importlib.util.spec_from_file_location("rc6_c14_scene_base", BASE)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    source = module.transformed_source()
    replacements = (
        ("settings.cfl_condition = 2.0", "settings.cfl_condition = 1.0", "CFL assignment", 1),
        ("abs(settings.cfl_condition - 2.0)", "abs(settings.cfl_condition - 1.0)", "CFL check", 1),
        ('"bfs.rc6RealImpactLiquidTimestepMaxC14Result.v0.1"', '"bfs.rc6RealImpactLiquidCflC16Result.v0.1"', "result schema", 1),
        ('"PASS_REAL_IMPACT_LIQUID_TIMESTEP_MAX_C14"', '"PASS_REAL_IMPACT_LIQUID_CFL_C16"', "pass verdict", 1),
        ('"FAIL_REAL_IMPACT_LIQUID_TIMESTEP_MAX_C14"', '"FAIL_REAL_IMPACT_LIQUID_CFL_C16"', "fail verdict", 1),
        ("RC6_REAL_IMPACT_LIQUID_TIMESTEP_MAX_C14=", "RC6_REAL_IMPACT_LIQUID_CFL_C16=", "result marker", 1),
        (
            "One 36-frame Preview-96 same-solve R40 basketball-impact/APIC spill test changing only liquid timesteps_max 4 to 8; no full landing, persistence, final resolution, render, film quality, deformation or generalized liquid claim.",
            "One 36-frame Preview-96 same-solve R40 basketball-impact/APIC spill test changing only liquid CFL 2.0 to 1.0 on the retained timesteps_max 8 baseline; no full landing, persistence, final resolution, render, film quality, deformation or generalized liquid claim.",
            "claim ceiling",
            1,
        ),
    )
    for before, after, label, expected in replacements:
        if source.count(before) != expected:
            raise RuntimeError(f"C16 scene {label} target mismatch")
        source = source.replace(before, after)
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#RC6_REAL_IMPACT_LIQUID_CFL_C16", "exec"), globals(), globals())
