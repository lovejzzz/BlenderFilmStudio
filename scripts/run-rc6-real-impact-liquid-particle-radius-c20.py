#!/usr/bin/env python3
"""Run one exact-C18 impact-liquid test with simulation radius 1.8 to 1.6."""

import hashlib
import importlib.util
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-real-impact-liquid-fractions-threshold-c18.py")
EXPECTED_BASE_SHA256 = "ff238b2708fd3c427aecbaaf6673f255a970b329b5c9d3e36941f873a3943271"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("C20 runner base identity mismatch")
    module_spec = importlib.util.spec_from_file_location("rc6_c18_runner_base", BASE)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    source = module.transformed_source()
    lineage_anchor = 'C17_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-cfl-data-comparison-c17-attempt-89/independent-audit.json"\n'
    lineage_extension = lineage_anchor + (
        'C18_RESULT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-fractions-threshold-c18-attempt-90/result.json"\n'
        'C18_RECEIPT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-fractions-threshold-c18-attempt-90/receipt.json"\n'
        'C18_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-fractions-threshold-c18-attempt-90/independent-audit.json"\n'
        'C18_C1_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-fractions-threshold-c18-audit-c1-attempt-91/audit.json"\n'
        'C19_RESULT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-fractions-threshold-data-comparison-c19-attempt-92/result.json"\n'
        'C19_RECEIPT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-fractions-threshold-data-comparison-c19-attempt-92/receipt.json"\n'
        'C19_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-fractions-threshold-data-comparison-c19-attempt-92/independent-audit.json"\n'
    )
    baseline_anchor = '    (C17_AUDIT, spec["baseline"]["c17AuditFileSha256"]),\n'
    baseline_extension = baseline_anchor + (
        '    (C18_RESULT, spec["baseline"]["c18ResultFileSha256"]),\n'
        '    (C18_RECEIPT, spec["baseline"]["c18ReceiptFileSha256"]),\n'
        '    (C18_AUDIT, spec["baseline"]["c18AuditFileSha256"]),\n'
        '    (C18_C1_AUDIT, spec["baseline"]["c18C1AuditFileSha256"]),\n'
        '    (C19_RESULT, spec["baseline"]["c19ResultFileSha256"]),\n'
        '    (C19_RECEIPT, spec["baseline"]["c19ReceiptFileSha256"]),\n'
        '    (C19_AUDIT, spec["baseline"]["c19AuditFileSha256"]),\n'
    )
    replacements = (
        ("RC6-2026-09-02-real-impact-liquid-fractions-threshold-c18-attempt-90", "RC6-2026-09-02-real-impact-liquid-particle-radius-c20-attempt-93", "fresh roots", 2),
        ('"scripts/run-rc6-real-impact-liquid-fractions-threshold-c18-scene.py"', '"scripts/run-rc6-real-impact-liquid-particle-radius-c20-scene.py"', "scene tool", 1),
        ('"scripts/audit-rc6-real-impact-liquid-fractions-threshold-c18.py"', '"scripts/audit-rc6-real-impact-liquid-particle-radius-c20.py"', "auditor", 1),
        ('"specs/ai-native-studio-rc6-real-impact-liquid-fractions-threshold-c18.v1.01.json"', '"specs/ai-native-studio-rc6-real-impact-liquid-particle-radius-c20.v1.04.json"', "spec", 1),
        (lineage_anchor, lineage_extension, "C18/C19 lineage constants", 1),
        (baseline_anchor, baseline_extension, "C18/C19 lineage hashes", 1),
        ('"RC6_REAL_IMPACT_LIQUID_FRACTIONS_THRESHOLD_C18="', '"RC6_REAL_IMPACT_LIQUID_PARTICLE_RADIUS_C20="', "scene marker", 1),
        ('"bfs.rc6RealImpactLiquidFractionsThresholdC18Admission.v0.1"', '"bfs.rc6RealImpactLiquidParticleRadiusC20Admission.v0.1"', "admission schema", 1),
        ('"bfs.rc6RealImpactLiquidFractionsThresholdC18Failure.v0.1"', '"bfs.rc6RealImpactLiquidParticleRadiusC20Failure.v0.1"', "failure schema", 1),
        ('"bfs.rc6RealImpactLiquidFractionsThresholdC18Receipt.v0.1"', '"bfs.rc6RealImpactLiquidParticleRadiusC20Receipt.v0.1"', "receipt schema", 1),
        ('"PASS_REAL_IMPACT_LIQUID_FRACTIONS_THRESHOLD_C18"', '"PASS_REAL_IMPACT_LIQUID_PARTICLE_RADIUS_C20"', "pass verdict", 1),
        ('"FAIL_REAL_IMPACT_LIQUID_FRACTIONS_THRESHOLD_C18"', '"FAIL_REAL_IMPACT_LIQUID_PARTICLE_RADIUS_C20"', "fail verdict", 1),
        ('"logs/01-real-impact-fractions-threshold.stdout.log"', '"logs/01-real-impact-particle-radius.stdout.log"', "stdout log", 1),
        ('"logs/01-real-impact-fractions-threshold.stderr.log"', '"logs/01-real-impact-particle-radius.stderr.log"', "stderr log", 1),
        ('"processes/01-real-impact-fractions-threshold.json"', '"processes/01-real-impact-particle-radius.json"', "process receipt", 1),
        ('"RC6_REAL_IMPACT_LIQUID_FRACTIONS_THRESHOLD_C18_RUN="', '"RC6_REAL_IMPACT_LIQUID_PARTICLE_RADIUS_C20_RUN="', "runner marker", 1),
    )
    for before, after, label, expected in replacements:
        if source.count(before) != expected:
            raise RuntimeError(f"C20 runner {label} target mismatch")
        source = source.replace(before, after)
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#RC6_REAL_IMPACT_LIQUID_PARTICLE_RADIUS_C20", "exec"), globals(), globals())
