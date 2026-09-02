#!/usr/bin/env python3
"""Adapt frozen C15 analysis to compare copied C16 Data/Mesh with C14."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("analyze-rc6-real-impact-c14-transition-c15.py")
EXPECTED_BASE_SHA256 = "b7560b82055aea2e6c063f0c2bb4d613119be7bacf29e451c05cc53402a5b903"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("C17 analyzer base identity mismatch")
    source = BASE.read_text()
    replacements = (
        ('"""Measure copied C14 Data support and transition order against C12/C13."""', '"""Measure copied C16 Data support and transition order against retained C14/C15."""', "docstring", 1),
        ("attempt86", "attempt88", "C16 result binding", 8),
        ("c13", "c15", "C15 baseline binding", 10),
        ("c12", "c14", "C14 sample naming", 6),
        ('"FAIL_REAL_IMPACT_LIQUID_TIMESTEP_MAX_C14"', '"FAIL_REAL_IMPACT_LIQUID_CFL_C16"', "C16 verdict", 1),
        ('c15["classification"] == "DATA_SUPPORT_EXPANDS_WITH_MESH_MESH_ONLY_CAUSE_REJECTED"', 'c15["classification"] == "TRANSITION_ORDER_INCONCLUSIVE"', "C15 classification", 1),
        ('"bfs.rc6RealImpactC14TransitionC15Result.v0.1"', '"bfs.rc6RealImpactC16DataComparisonC17Result.v0.1"', "result schema", 1),
        ('"MEASURED_TRANSITION_ORDER"', '"MEASURED_CFL_DATA_MESH_COMPARISON"', "result status", 2),
        ('"Saved terminal substep is diagnostic metadata, not a solver-step count. Occupied Data support is not exact liquid mass. Transition order localizes the next layer without proving a repair."', '"Saved terminal substep is diagnostic metadata, not a solver-step count. Occupied Data support is not exact liquid mass. C16-versus-C14 transition order localizes the regression layer without proving a mechanism or repair."', "interpretation", 1),
        ("RC6_REAL_IMPACT_C14_TRANSITION_C15=", "RC6_REAL_IMPACT_C16_DATA_COMPARISON_C17=", "result marker", 1),
        ("C15 analysis harness failed", "C17 analysis harness failed", "failure marker", 1),
    )
    for before, after, label, expected in replacements:
        if source.count(before) != expected:
            raise RuntimeError(f"C17 analyzer {label} target mismatch")
        source = source.replace(before, after)
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#RC6_REAL_IMPACT_C16_DATA_COMPARISON_C17", "exec"), globals(), globals())
