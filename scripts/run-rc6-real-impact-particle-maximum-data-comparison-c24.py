#!/usr/bin/env python3
"""Copy immutable C23 cache and compare its Data/Mesh onset with C18."""

import hashlib
import importlib.util
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-real-impact-particle-radius-data-comparison-c21.py")
EXPECTED_BASE_SHA256 = "5f44c415e959d637d90704df10a076b0e3062ec95718f8fed184cc412f1e3289"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("C24 runner base identity mismatch")
    module_spec = importlib.util.spec_from_file_location("rc6_c21_runner_base", BASE)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    source = module.transformed_source()
    replacements = (
        ("RC6-2026-09-02-real-impact-particle-radius-data-comparison-c21-attempt-99", "RC6-2026-09-02-real-impact-particle-maximum-data-comparison-c24-attempt-102", "fresh roots", 2),
        ("RC6-2026-09-02-real-impact-liquid-particle-radius-c20-c1-attempt-94", "RC6-2026-09-02-real-impact-liquid-particle-maximum-c23-attempt-101", "C23 cache/evidence", 2),
        ("RC6-2026-09-02-real-impact-liquid-particle-radius-c20-c5-audit-attempt-98/audit.json", "RC6-2026-09-02-real-impact-liquid-particle-maximum-c23-attempt-101/independent-audit.json", "C23 accepted audit", 1),
        ("RC6-2026-09-02-real-impact-liquid-particle-radius-c20-c5-audit-attempt-98/receipt.json", "RC6-2026-09-02-real-impact-liquid-particle-maximum-c23-attempt-101/receipt.json", "C23 receipt", 1),
        ("particle-radius-data-comparison-c21", "particle-maximum-data-comparison-c24", "tool/spec paths", 3),
        ("v1.10.json", "v1.13.json", "spec version", 1),
        ("attempt94", "attempt101", "C23 baseline keys", 10),
        ("ATTEMPT94", "ATTEMPT101", "C23 constant names", 5),
        ("C20_C5", "C23_ACCEPTED", "C23 accepted constants", 6),
        ("c20_c5", "c23_accepted", "C23 accepted values", 6),
        ("attempt101C5", "attempt101Accepted", "C23 accepted baseline keys", 4),
        ("C20", "C23", "C23 labels", 2),
        ("C21", "C24", "C24 labels", 22),
        ("PARTICLE_RADIUS_DATA_COMPARISON", "PARTICLE_MAXIMUM_DATA_COMPARISON", "marker naming", 2),
        ("ParticleRadiusDataComparison", "ParticleMaximumDataComparison", "schema naming", 2),
        ("--attempt101-result", "--attempt101-result", "argument stability", 1),
    )
    for before, after, label, expected in replacements:
        if source.count(before) != expected:
            raise RuntimeError(f"C24 runner {label} target mismatch: {source.count(before)} != {expected}")
        source = source.replace(before, after)
    old = 'c23_accepted_receipt["status"] != "PASS"'
    if source.count(old) != 1:
        raise RuntimeError("C24 runner C23 receipt-status target mismatch")
    source = source.replace(old, 'c23_accepted_receipt["status"] != "FAIL"')
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#RC6_REAL_IMPACT_PARTICLE_MAXIMUM_DATA_COMPARISON_C24", "exec"), globals(), globals())
