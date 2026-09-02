#!/usr/bin/env python3
"""Copy immutable C16 cache and compare its Data/Mesh transition with C14."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-real-impact-c14-transition-c15.py")
EXPECTED_BASE_SHA256 = "c1ddc49988918964c0a0be0b1d289559e1c5f0ed2553c0f29b292a6c15b3394f"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("C17 runner base identity mismatch")
    source = BASE.read_text()
    replacements = (
        ("RC6-2026-09-02-real-impact-c14-transition-c15-attempt-87", "RC6-2026-09-02-real-impact-cfl-data-comparison-c17-attempt-89", "fresh roots", 2),
        ("RC6-2026-09-02-real-impact-liquid-timestep-max-c14-attempt-86", "RC6-2026-09-02-real-impact-liquid-cfl-c16-attempt-88", "C16 cache/evidence", 2),
        ("RC6-2026-09-02-real-impact-data-occupancy-c13-attempt-85", "RC6-2026-09-02-real-impact-c14-transition-c15-attempt-87", "C15 baseline evidence", 1),
        ('"scripts/analyze-rc6-real-impact-c14-transition-c15.py"', '"scripts/analyze-rc6-real-impact-cfl-data-comparison-c17.py"', "analyzer", 1),
        ('"scripts/audit-rc6-real-impact-c14-transition-c15.py"', '"scripts/audit-rc6-real-impact-cfl-data-comparison-c17.py"', "auditor", 1),
        ('"specs/ai-native-studio-rc6-real-impact-c14-transition-c15.v0.98.json"', '"specs/ai-native-studio-rc6-real-impact-cfl-data-comparison-c17.v1.00.json"', "spec", 1),
        ("attempt86", "attempt88", "C16 result keys", 6),
        ("ATTEMPT86", "ATTEMPT88", "C16 result constant", 5),
        ("c13", "c15", "C15 result keys", 4),
        ("C13", "C15", "C15 result constant", 5),
        ('"bfs.rc6RealImpactC14TransitionC15Admission.v0.1"', '"bfs.rc6RealImpactC16DataComparisonC17Admission.v0.1"', "admission schema", 1),
        ('"bfs.rc6RealImpactC14TransitionC15Receipt.v0.1"', '"bfs.rc6RealImpactC16DataComparisonC17Receipt.v0.1"', "receipt schema", 1),
        ('"MEASURED_TRANSITION_ORDER"', '"MEASURED_CFL_DATA_MESH_COMPARISON"', "result status", 1),
        ("RC6_REAL_IMPACT_C14_TRANSITION_C15=", "RC6_REAL_IMPACT_C16_DATA_COMPARISON_C17=", "analyzer marker", 1),
        ("RC6_REAL_IMPACT_C14_TRANSITION_C15_RUN=", "RC6_REAL_IMPACT_C16_DATA_COMPARISON_C17_RUN=", "runner marker", 1),
    )
    for before, after, label, expected in replacements:
        if source.count(before) != expected:
            raise RuntimeError(f"C17 runner {label} target mismatch")
        source = source.replace(before, after)
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#RC6_REAL_IMPACT_C16_DATA_COMPARISON_C17", "exec"), globals(), globals())
