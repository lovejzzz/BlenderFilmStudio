#!/usr/bin/env python3
"""Run one exact-C14 impact-liquid test with fractions threshold 0.05 to 0.10."""

import hashlib
import importlib.util
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-real-impact-liquid-cfl-c16.py")
EXPECTED_BASE_SHA256 = "84b2d82349f702da0e63c98aeea4b254c3940adf19fa54fe40c4ccd3a7dd4016"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("C18 runner base identity mismatch")
    module_spec = importlib.util.spec_from_file_location("rc6_c16_runner_base", BASE)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    source = module.transformed_source()
    lineage_anchor = 'C15_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-c14-transition-c15-attempt-87/independent-audit.json"\n'
    lineage_extension = lineage_anchor + (
        'C16_RESULT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-cfl-c16-attempt-88/result.json"\n'
        'C16_RECEIPT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-cfl-c16-attempt-88/receipt.json"\n'
        'C16_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-cfl-c16-attempt-88/independent-audit.json"\n'
        'C17_RESULT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-cfl-data-comparison-c17-attempt-89/result.json"\n'
        'C17_RECEIPT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-cfl-data-comparison-c17-attempt-89/receipt.json"\n'
        'C17_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-cfl-data-comparison-c17-attempt-89/independent-audit.json"\n'
    )
    baseline_anchor = '    (C15_AUDIT, spec["baseline"]["c15AuditFileSha256"]),\n'
    baseline_extension = baseline_anchor + (
        '    (C16_RESULT, spec["baseline"]["c16ResultFileSha256"]),\n'
        '    (C16_RECEIPT, spec["baseline"]["c16ReceiptFileSha256"]),\n'
        '    (C16_AUDIT, spec["baseline"]["c16AuditFileSha256"]),\n'
        '    (C17_RESULT, spec["baseline"]["c17ResultFileSha256"]),\n'
        '    (C17_RECEIPT, spec["baseline"]["c17ReceiptFileSha256"]),\n'
        '    (C17_AUDIT, spec["baseline"]["c17AuditFileSha256"]),\n'
    )
    replacements = (
        ("RC6-2026-09-02-real-impact-liquid-cfl-c16-attempt-88", "RC6-2026-09-02-real-impact-liquid-fractions-threshold-c18-attempt-90", "fresh roots", 2),
        ('"scripts/run-rc6-real-impact-liquid-cfl-c16-scene.py"', '"scripts/run-rc6-real-impact-liquid-fractions-threshold-c18-scene.py"', "scene tool", 1),
        ('"scripts/audit-rc6-real-impact-liquid-cfl-c16.py"', '"scripts/audit-rc6-real-impact-liquid-fractions-threshold-c18.py"', "auditor", 1),
        ('"specs/ai-native-studio-rc6-real-impact-liquid-cfl-c16.v0.99.json"', '"specs/ai-native-studio-rc6-real-impact-liquid-fractions-threshold-c18.v1.01.json"', "spec", 1),
        (lineage_anchor, lineage_extension, "C16/C17 lineage constants", 1),
        (baseline_anchor, baseline_extension, "C16/C17 lineage hashes", 1),
        ('"RC6_REAL_IMPACT_LIQUID_CFL_C16="', '"RC6_REAL_IMPACT_LIQUID_FRACTIONS_THRESHOLD_C18="', "scene marker", 1),
        ('"bfs.rc6RealImpactLiquidCflC16Admission.v0.1"', '"bfs.rc6RealImpactLiquidFractionsThresholdC18Admission.v0.1"', "admission schema", 1),
        ('"bfs.rc6RealImpactLiquidCflC16Failure.v0.1"', '"bfs.rc6RealImpactLiquidFractionsThresholdC18Failure.v0.1"', "failure schema", 1),
        ('"bfs.rc6RealImpactLiquidCflC16Receipt.v0.1"', '"bfs.rc6RealImpactLiquidFractionsThresholdC18Receipt.v0.1"', "receipt schema", 1),
        ('"PASS_REAL_IMPACT_LIQUID_CFL_C16"', '"PASS_REAL_IMPACT_LIQUID_FRACTIONS_THRESHOLD_C18"', "pass verdict", 1),
        ('"FAIL_REAL_IMPACT_LIQUID_CFL_C16"', '"FAIL_REAL_IMPACT_LIQUID_FRACTIONS_THRESHOLD_C18"', "fail verdict", 1),
        ('"logs/01-real-impact-cfl.stdout.log"', '"logs/01-real-impact-fractions-threshold.stdout.log"', "stdout log", 1),
        ('"logs/01-real-impact-cfl.stderr.log"', '"logs/01-real-impact-fractions-threshold.stderr.log"', "stderr log", 1),
        ('"processes/01-real-impact-cfl.json"', '"processes/01-real-impact-fractions-threshold.json"', "process receipt", 1),
        ('"RC6_REAL_IMPACT_LIQUID_CFL_C16_RUN="', '"RC6_REAL_IMPACT_LIQUID_FRACTIONS_THRESHOLD_C18_RUN="', "runner marker", 1),
    )
    for before, after, label, expected in replacements:
        if source.count(before) != expected:
            raise RuntimeError(f"C18 runner {label} target mismatch")
        source = source.replace(before, after)
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#RC6_REAL_IMPACT_LIQUID_FRACTIONS_THRESHOLD_C18", "exec"), globals(), globals())
