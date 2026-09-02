#!/usr/bin/env python3
"""Correct only the stale C23 verdict token in the frozen C24 analyzer."""

import hashlib
import importlib.util
from pathlib import Path


BASE = Path(__file__).resolve().with_name("analyze-rc6-real-impact-particle-maximum-data-comparison-c24.py")
EXPECTED_BASE_SHA256 = "6098fd80487f8a2b506000469bd33e824688615710aa5238425c168cc0498ecb"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("C24 C1 analyzer base identity mismatch")
    module_spec = importlib.util.spec_from_file_location("rc6_c24_analyzer_base", BASE)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    source = module.transformed_source()
    before = '"FAIL_REAL_IMPACT_LIQUID_PARTICLE_RADIUS_C23"'
    after = '"FAIL_REAL_IMPACT_LIQUID_PARTICLE_MAXIMUM_C23"'
    if source.count(before) != 1:
        raise RuntimeError("C24 C1 exact verdict-token target mismatch")
    return source.replace(before, after)


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#RC6_REAL_IMPACT_PARTICLE_MAXIMUM_DATA_COMPARISON_C24_C1", "exec"), globals(), globals())
