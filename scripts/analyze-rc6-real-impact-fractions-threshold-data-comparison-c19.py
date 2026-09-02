#!/usr/bin/env python3
"""Adapt C17 analysis to compare copied C18 Data/Mesh with C14."""

import hashlib
import importlib.util
from pathlib import Path


BASE = Path(__file__).resolve().with_name("analyze-rc6-real-impact-cfl-data-comparison-c17.py")
EXPECTED_BASE_SHA256 = "c5e6d190ec75db2fe4f82c77fd74f9ea866ed2494cc0a5bdf322fc476e0e4bf7"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("C19 analyzer base identity mismatch")
    module_spec = importlib.util.spec_from_file_location("rc6_c17_analyzer_base", BASE)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    source = module.transformed_source()
    replacements = (
        ('"""Measure copied C16 Data support and transition order against retained C14/C15."""', '"""Measure copied C18 Data support and transition order against retained C14/C15."""', "docstring", 1),
        ("attempt88", "attempt90", "C18 result binding", 8),
        ('"FAIL_REAL_IMPACT_LIQUID_CFL_C16"', '"FAIL_REAL_IMPACT_LIQUID_FRACTIONS_THRESHOLD_C18"', "C18 verdict", 1),
        ('"bfs.rc6RealImpactC16DataComparisonC17Result.v0.1"', '"bfs.rc6RealImpactFractionsThresholdDataComparisonC19Result.v0.1"', "result schema", 1),
        ('"MEASURED_CFL_DATA_MESH_COMPARISON"', '"MEASURED_FRACTIONS_THRESHOLD_DATA_MESH_COMPARISON"', "result status", 2),
        ('"Saved terminal substep is diagnostic metadata, not a solver-step count. Occupied Data support is not exact liquid mass. C16-versus-C14 transition order localizes the regression layer without proving a mechanism or repair."', '"Saved terminal substep is diagnostic metadata, not a solver-step count. Occupied Data support is not exact liquid mass. C18-versus-C14 transition order measures where the threshold response begins without proving a mechanism or repair."', "interpretation", 1),
        ("RC6_REAL_IMPACT_C16_DATA_COMPARISON_C17=", "RC6_REAL_IMPACT_FRACTIONS_THRESHOLD_DATA_COMPARISON_C19=", "result marker", 1),
        ("C17 analysis harness failed", "C19 analysis harness failed", "failure marker", 1),
    )
    for before, after, label, expected in replacements:
        if source.count(before) != expected:
            raise RuntimeError(f"C19 analyzer {label} target mismatch")
        source = source.replace(before, after)
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#RC6_REAL_IMPACT_FRACTIONS_THRESHOLD_DATA_COMPARISON_C19", "exec"), globals(), globals())
