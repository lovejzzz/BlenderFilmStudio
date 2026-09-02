#!/usr/bin/env python3
"""Adapt C21 analysis to compare copied C23 Data/Mesh with retained C18."""

import hashlib
import importlib.util
from pathlib import Path


BASE = Path(__file__).resolve().with_name("analyze-rc6-real-impact-particle-radius-data-comparison-c21.py")
EXPECTED_BASE_SHA256 = "3d2c4b91bc0600e8e32e89250e42cdd34d70dc11ce05940c443431b0282ecd41"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("C24 analyzer base identity mismatch")
    module_spec = importlib.util.spec_from_file_location("rc6_c21_analyzer_base", BASE)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    source = module.transformed_source()
    replacements = (
        ("attempt94", "attempt101", "C23 result binding", 8),
        ("C20", "C23", "C23 labels", 6),
        ("C21", "C24", "C24 labels", 7),
        ("PARTICLE_RADIUS_DATA_COMPARISON", "PARTICLE_MAXIMUM_DATA_COMPARISON", "marker naming", 1),
        ("ParticleRadiusDataComparison", "ParticleMaximumDataComparison", "schema naming", 1),
        ("smaller simulation radius", "lower per-cell particle ceiling", "interpretation naming", 1),
    )
    for before, after, label, expected in replacements:
        if source.count(before) != expected:
            raise RuntimeError(f"C24 analyzer {label} target mismatch: {source.count(before)} != {expected}")
        source = source.replace(before, after)
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#RC6_REAL_IMPACT_PARTICLE_MAXIMUM_DATA_COMPARISON_C24", "exec"), globals(), globals())
