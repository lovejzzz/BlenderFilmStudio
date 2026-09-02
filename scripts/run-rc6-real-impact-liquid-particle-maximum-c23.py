#!/usr/bin/env python3
"""Run one exact-C18 impact-liquid test with particle maximum 16 to 12."""

import hashlib
import importlib.util
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-real-impact-liquid-fractions-threshold-c18.py")
EXPECTED_BASE_SHA256 = "ff238b2708fd3c427aecbaaf6673f255a970b329b5c9d3e36941f873a3943271"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("C23 runner base identity mismatch")
    module_spec = importlib.util.spec_from_file_location("rc6_c18_runner_base", BASE)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    source = module.transformed_source()
    lineage_anchor = 'C17_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-cfl-data-comparison-c17-attempt-89/independent-audit.json"\n'
    lineage_extension = lineage_anchor + (
        'C18_RESULT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-fractions-threshold-c18-attempt-90/result.json"\n'
        'C18_RECEIPT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-fractions-threshold-c18-attempt-90/receipt.json"\n'
        'C18_C1_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-fractions-threshold-c18-audit-c1-attempt-91/audit.json"\n'
        'C21_RESULT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-particle-radius-data-comparison-c21-attempt-99/result.json"\n'
        'C21_RECEIPT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-particle-radius-data-comparison-c21-attempt-99/receipt.json"\n'
        'C21_C1_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-particle-radius-data-comparison-c21-c1-audit-attempt-100/audit.json"\n'
        'C21_C1_RECEIPT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-particle-radius-data-comparison-c21-c1-audit-attempt-100/receipt.json"\n'
        'C22_INSPECTION = RESEARCH / "research/2026-09-02-rc6-real-impact-particle-maximum-c22-source-inspection.md"\n'
    )
    baseline_anchor = '    (C17_AUDIT, spec["baseline"]["c17AuditFileSha256"]),\n'
    baseline_extension = baseline_anchor + (
        '    (C18_RESULT, spec["baseline"]["c18ResultFileSha256"]),\n'
        '    (C18_RECEIPT, spec["baseline"]["c18ReceiptFileSha256"]),\n'
        '    (C18_C1_AUDIT, spec["baseline"]["c18C1AuditFileSha256"]),\n'
        '    (C21_RESULT, spec["baseline"]["c21ResultFileSha256"]),\n'
        '    (C21_RECEIPT, spec["baseline"]["c21ReceiptFileSha256"]),\n'
        '    (C21_C1_AUDIT, spec["baseline"]["c21C1AuditFileSha256"]),\n'
        '    (C21_C1_RECEIPT, spec["baseline"]["c21C1ReceiptFileSha256"]),\n'
        '    (C22_INSPECTION, spec["baseline"]["c22InspectionFileSha256"]),\n'
    )
    replacements = (
        ("RC6-2026-09-02-real-impact-liquid-fractions-threshold-c18-attempt-90", "RC6-2026-09-02-real-impact-liquid-particle-maximum-c23-attempt-101", "fresh roots", 2),
        ('"scripts/run-rc6-real-impact-liquid-fractions-threshold-c18-scene.py"', '"scripts/run-rc6-real-impact-liquid-particle-maximum-c23-scene.py"', "scene tool", 1),
        ('"scripts/audit-rc6-real-impact-liquid-fractions-threshold-c18.py"', '"scripts/audit-rc6-real-impact-liquid-particle-maximum-c23.py"', "auditor", 1),
        ('"specs/ai-native-studio-rc6-real-impact-liquid-fractions-threshold-c18.v1.01.json"', '"specs/ai-native-studio-rc6-real-impact-liquid-particle-maximum-c23.v1.12.json"', "spec", 1),
        (lineage_anchor, lineage_extension, "C18/C21/C22 lineage constants", 1),
        (baseline_anchor, baseline_extension, "C18/C21/C22 lineage hashes", 1),
        ('"RC6_REAL_IMPACT_LIQUID_FRACTIONS_THRESHOLD_C18="', '"RC6_REAL_IMPACT_LIQUID_PARTICLE_MAXIMUM_C23="', "scene marker", 1),
        ('"bfs.rc6RealImpactLiquidFractionsThresholdC18Admission.v0.1"', '"bfs.rc6RealImpactLiquidParticleMaximumC23Admission.v0.1"', "admission schema", 1),
        ('"bfs.rc6RealImpactLiquidFractionsThresholdC18Failure.v0.1"', '"bfs.rc6RealImpactLiquidParticleMaximumC23Failure.v0.1"', "failure schema", 1),
        ('"bfs.rc6RealImpactLiquidFractionsThresholdC18Receipt.v0.1"', '"bfs.rc6RealImpactLiquidParticleMaximumC23Receipt.v0.1"', "receipt schema", 1),
        ('"PASS_REAL_IMPACT_LIQUID_FRACTIONS_THRESHOLD_C18"', '"PASS_REAL_IMPACT_LIQUID_PARTICLE_MAXIMUM_C23"', "pass verdict", 1),
        ('"FAIL_REAL_IMPACT_LIQUID_FRACTIONS_THRESHOLD_C18"', '"FAIL_REAL_IMPACT_LIQUID_PARTICLE_MAXIMUM_C23"', "fail verdict", 1),
        ('"logs/01-real-impact-fractions-threshold.stdout.log"', '"logs/01-real-impact-particle-maximum.stdout.log"', "stdout log", 1),
        ('"logs/01-real-impact-fractions-threshold.stderr.log"', '"logs/01-real-impact-particle-maximum.stderr.log"', "stderr log", 1),
        ('"processes/01-real-impact-fractions-threshold.json"', '"processes/01-real-impact-particle-maximum.json"', "process receipt", 1),
        ('"RC6_REAL_IMPACT_LIQUID_FRACTIONS_THRESHOLD_C18_RUN="', '"RC6_REAL_IMPACT_LIQUID_PARTICLE_MAXIMUM_C23_RUN="', "runner marker", 1),
    )
    for before, after, label, expected in replacements:
        if source.count(before) != expected:
            raise RuntimeError(f"C23 runner {label} target mismatch")
        source = source.replace(before, after)
    source = source.replace("real-impact liquid C12", "real-impact liquid C23")
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#RC6_REAL_IMPACT_LIQUID_PARTICLE_MAXIMUM_C23", "exec"), globals(), globals())
