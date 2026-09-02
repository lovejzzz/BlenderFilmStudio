#!/usr/bin/env python3
"""Copy immutable C29 cache and compare its Data/Mesh response with C18."""

import hashlib
import importlib.util
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-real-impact-water-diffusion-data-comparison-c27.py")
EXPECTED_BASE_SHA256 = "b0ef7a5555fd11a708ec2f3fc05378d9942da6ed5c0034788c7b2b3bf42504b6"


def replace_exact(source, before, after, label, expected=1):
    count = source.count(before)
    if count != expected:
        raise RuntimeError(f"C30 runner {label} target mismatch: {count} != {expected}")
    return source.replace(before, after)


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("C30 runner base identity mismatch")
    module_spec = importlib.util.spec_from_file_location("rc6_c27_runner_base", BASE)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    source = module.transformed_source()

    source = replace_exact(source, 'C26_C2_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-water-diffusion-c26-audit-c2-attempt-106/audit.json"\n', '', "remove inapplicable C2 constant")
    source = replace_exact(source, '    C26_C2_AUDIT: spec["baseline"]["attempt104C2AuditFileSha256"],\n', '', "remove C2 hash path")
    source = replace_exact(source, 'c26_c2_audit = json.loads(C26_C2_AUDIT.read_text())\n', '', "remove C2 load")
    source = replace_exact(source, 'if c26_c2_audit["status"] != "PASS_AUDIT_ONLY_PHYSICAL_FAIL_RETAINED" or c26_c2_audit["auditHash"] != spec["baseline"]["attempt104C2AuditHash"]:\n    raise RuntimeError("C27 C26 C2 closure binding mismatch")\n', '', "remove C2 closure check")

    replacements = (
        ("RC6-2026-09-02-real-impact-water-diffusion-data-comparison-c27-attempt-107", "RC6-2026-09-02-real-impact-particle-band-width-data-comparison-c30-attempt-109", "fresh roots", 2),
        ("RC6-2026-09-02-real-impact-liquid-water-diffusion-c26-attempt-104", "RC6-2026-09-02-real-impact-liquid-particle-band-width-c29-attempt-108", "C29 cache/evidence", 2),
        ("scripts/analyze-rc6-real-impact-water-diffusion-data-comparison-c27.py", "scripts/analyze-rc6-real-impact-particle-band-width-data-comparison-c30.py", "analyzer path", 1),
        ("scripts/audit-rc6-real-impact-water-diffusion-data-comparison-c27.py", "scripts/audit-rc6-real-impact-particle-band-width-data-comparison-c30.py", "auditor path", 1),
        ("specs/ai-native-studio-rc6-real-impact-water-diffusion-data-comparison-c27.v1.18.json", "specs/ai-native-studio-rc6-real-impact-particle-band-width-data-comparison-c30.v1.20.json", "spec path", 1),
        ("ATTEMPT104", "ATTEMPT108", "attempt constant", 5),
        ("attempt104", "attempt108", "attempt fields", 6),
        ("C26", "C29", "experiment labels", 1),
        ("C27", "C30", "diagnostic labels", 21),
        ("WATER_DIFFUSION", "PARTICLE_BAND_WIDTH", "status tokens", 3),
        ("WaterDiffusion", "ParticleBandWidth", "schema tokens", 2),
    )
    for before, after, label, expected in replacements:
        source = replace_exact(source, before, after, label, expected)
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#RC6_REAL_IMPACT_PARTICLE_BAND_WIDTH_DATA_COMPARISON_C30", "exec"), globals(), globals())
