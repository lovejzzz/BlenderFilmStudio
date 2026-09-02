#!/usr/bin/env python3
"""Adapt the frozen C21 analyzer for C26 Water diffusion versus C18."""

import hashlib
import importlib.util
from pathlib import Path


BASE = Path(__file__).resolve().with_name("analyze-rc6-real-impact-particle-radius-data-comparison-c21.py")
EXPECTED_BASE_SHA256 = "3d2c4b91bc0600e8e32e89250e42cdd34d70dc11ce05940c443431b0282ecd41"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("C27 analyzer base identity mismatch")
    module_spec = importlib.util.spec_from_file_location("rc6_c21_analyzer_base", BASE)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    source = module.transformed_source()
    replacements = (
        ("attempt94", "attempt104", "current attempt", 8),
        ("C20", "C26", "current experiment", 6),
        ("C21", "C27", "diagnostic gate", 7),
        ("PARTICLE_RADIUS", "WATER_DIFFUSION", "status tokens", 4),
        ("ParticleRadius", "WaterDiffusion", "schema token", 1),
    )
    for before, after, label, expected in replacements:
        if source.count(before) != expected:
            raise RuntimeError(f"C27 analyzer {label} target mismatch: {source.count(before)} != {expected}")
        source = source.replace(before, after)
    old = "C26-versus-C18 onset and amplitude test whether the smaller simulation radius changes failure timing, severity or both without proving one internal operation."
    new = "C26-versus-C18 onset and amplitude test whether Water-preset velocity diffusion changes failure timing, severity or both without proving one internal operation."
    if source.count(old) != 1:
        raise RuntimeError("C27 analyzer interpretation target mismatch")
    return source.replace(old, new)


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#RC6_REAL_IMPACT_WATER_DIFFUSION_DATA_COMPARISON_C27", "exec"), globals(), globals())
