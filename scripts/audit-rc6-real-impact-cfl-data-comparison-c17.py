#!/usr/bin/env python3
"""Independently adapt C15 audit for the C16-versus-C14 comparison."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-real-impact-c14-transition-c15.py")
EXPECTED_BASE_SHA256 = "a2e9f2ded3cd4d753764df645b74884b07e0c0ec1a807a14d31651f0d38d1dd8"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("C17 auditor base identity mismatch")
    source = BASE.read_text()
    replacements = (
        ('"""Independently audit the copied-cache C15 transition diagnosis."""', '"""Independently audit copied C16 Data/Mesh against retained C14/C15."""', "docstring", 1),
        ("RC6-2026-09-02-real-impact-c14-transition-c15-attempt-87", "RC6-2026-09-02-real-impact-cfl-data-comparison-c17-attempt-89", "fresh roots", 2),
        ("RC6-2026-09-02-real-impact-liquid-timestep-max-c14-attempt-86", "RC6-2026-09-02-real-impact-liquid-cfl-c16-attempt-88", "C16 cache/evidence", 2),
        ("RC6-2026-09-02-real-impact-data-occupancy-c13-attempt-85", "RC6-2026-09-02-real-impact-c14-transition-c15-attempt-87", "C15 baseline evidence", 1),
        ('"scripts/analyze-rc6-real-impact-c14-transition-c15.py"', '"scripts/analyze-rc6-real-impact-cfl-data-comparison-c17.py"', "analyzer", 1),
        ('"scripts/run-rc6-real-impact-c14-transition-c15.py"', '"scripts/run-rc6-real-impact-cfl-data-comparison-c17.py"', "runner", 1),
        ('"specs/ai-native-studio-rc6-real-impact-c14-transition-c15.v0.98.json"', '"specs/ai-native-studio-rc6-real-impact-cfl-data-comparison-c17.v1.00.json"', "spec", 1),
        ("attempt86", "attempt88", "C16 result keys", 17),
        ("ATTEMPT86", "ATTEMPT88", "C16 result constant", 8),
        ("c13", "c15", "C15 result keys", 18),
        ("C13", "C15", "C15 result constant", 8),
        ("c12", "c14", "C14 sample naming", 6),
        ('"MEASURED_TRANSITION_ORDER"', '"MEASURED_CFL_DATA_MESH_COMPARISON"', "result status", 1),
        ('"bfs.rc6RealImpactC14TransitionC15IndependentAudit.v0.1"', '"bfs.rc6RealImpactC16DataComparisonC17IndependentAudit.v0.1"', "audit schema", 1),
        ("RC6_REAL_IMPACT_C14_TRANSITION_C15_AUDIT=", "RC6_REAL_IMPACT_C16_DATA_COMPARISON_C17_AUDIT=", "audit marker", 1),
        ("C15 independent audit failed", "C17 independent audit failed", "failure marker", 1),
    )
    for before, after, label, expected in replacements:
        if source.count(before) != expected:
            raise RuntimeError(f"C17 auditor {label} target mismatch")
        source = source.replace(before, after)
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#RC6_REAL_IMPACT_C16_DATA_COMPARISON_C17", "exec"), globals(), globals())
