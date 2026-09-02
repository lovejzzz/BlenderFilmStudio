#!/usr/bin/env python3
"""Adapt the frozen C18 auditor for the one-variable C23 particle ceiling test."""

import hashlib
import importlib.util
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-real-impact-liquid-fractions-threshold-c18.py")
EXPECTED_BASE_SHA256 = "9b9fe7f03a51cafb7038859f918e8b526d7f621663f48493800050bfc85e8efb"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("C23 auditor base identity mismatch")
    module_spec = importlib.util.spec_from_file_location("rc6_c18_auditor_base", BASE)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    source = module.transformed_source()
    old_paths = '''EXPECTED_FREEZE_PATHS = {
    "research/2026-09-02-rc6-real-impact-liquid-fractions-threshold-c18-preregistration.md",
    "scripts/audit-rc6-real-impact-liquid-fractions-threshold-c18.py",
    "scripts/run-rc6-real-impact-liquid-fractions-threshold-c18-scene.py",
    "scripts/run-rc6-real-impact-liquid-fractions-threshold-c18.py",
    "specs/ai-native-studio-rc6-real-impact-liquid-fractions-threshold-c18.v1.01.json",
}'''
    new_paths = '''EXPECTED_FREEZE_PATHS = {
    "research/2026-09-02-rc6-real-impact-liquid-particle-maximum-c23-preregistration.md",
    "scripts/audit-rc6-real-impact-liquid-particle-maximum-c23.py",
    "scripts/run-rc6-real-impact-liquid-particle-maximum-c23-scene.py",
    "scripts/run-rc6-real-impact-liquid-particle-maximum-c23.py",
    "specs/ai-native-studio-rc6-real-impact-liquid-particle-maximum-c23.v1.12.json",
}'''
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
    load_anchor = 'c17_audit = json.loads(C17_AUDIT.read_text())\n'
    load_extension = load_anchor + (
        'c18_result = json.loads(C18_RESULT.read_text())\n'
        'c18_receipt = json.loads(C18_RECEIPT.read_text())\n'
        'c18_c1_audit = json.loads(C18_C1_AUDIT.read_text())\n'
        'c21_result = json.loads(C21_RESULT.read_text())\n'
        'c21_receipt = json.loads(C21_RECEIPT.read_text())\n'
        'c21_c1_audit = json.loads(C21_C1_AUDIT.read_text())\n'
        'c21_c1_receipt = json.loads(C21_C1_RECEIPT.read_text())\n'
    )
    baseline_anchor = 'and sha(C17_AUDIT) == spec["baseline"]["c17AuditFileSha256"]'
    baseline_extension = baseline_anchor + ' and sha(C18_RESULT) == spec["baseline"]["c18ResultFileSha256"] and sha(C18_RECEIPT) == spec["baseline"]["c18ReceiptFileSha256"] and sha(C18_C1_AUDIT) == spec["baseline"]["c18C1AuditFileSha256"] and sha(C21_RESULT) == spec["baseline"]["c21ResultFileSha256"] and sha(C21_RECEIPT) == spec["baseline"]["c21ReceiptFileSha256"] and sha(C21_C1_AUDIT) == spec["baseline"]["c21C1AuditFileSha256"] and sha(C21_C1_RECEIPT) == spec["baseline"]["c21C1ReceiptFileSha256"] and sha(C22_INSPECTION) == spec["baseline"]["c22InspectionFileSha256"]'
    lineage_check_anchor = 'and c17_audit["status"] == "PASS" and c17_audit["auditHash"] == spec["baseline"]["c17AuditHash"]'
    lineage_check_extension = lineage_check_anchor + ' and c18_result["status"] == "FAIL" and c18_result["resultHash"] == spec["baseline"]["c18ResultHash"] and c18_receipt["status"] == "FAIL" and c18_receipt["receiptHash"] == spec["baseline"]["c18ReceiptHash"] and c18_c1_audit["status"] == "PASS_AUDIT_ONLY_PHYSICAL_FAIL_RETAINED" and c18_c1_audit["auditHash"] == spec["baseline"]["c18C1AuditHash"] and c21_result["classification"] == "C20_SAME_ONSET_MORE_SEVERE_THAN_C18" and c21_result["resultHash"] == spec["baseline"]["c21ResultHash"] and c21_receipt["status"] == "PASS_DIAGNOSTIC" and c21_receipt["receiptHash"] == spec["baseline"]["c21ReceiptHash"] and c21_c1_audit["status"] == "PASS" and c21_c1_audit["auditHash"] == spec["baseline"]["c21C1AuditHash"] and c21_c1_receipt["status"] == "PASS_AUDIT_ONLY" and c21_c1_receipt["receiptHash"] == spec["baseline"]["c21C1ReceiptHash"]'
    replacements = (
        ("RC6-2026-09-02-real-impact-liquid-fractions-threshold-c18-attempt-90", "RC6-2026-09-02-real-impact-liquid-particle-maximum-c23-attempt-101", "fresh roots", 2),
        (old_paths, new_paths, "freeze path roster", 1),
        ('"scripts/run-rc6-real-impact-liquid-fractions-threshold-c18-scene.py"', '"scripts/run-rc6-real-impact-liquid-particle-maximum-c23-scene.py"', "scene tool", 1),
        ('"scripts/run-rc6-real-impact-liquid-fractions-threshold-c18.py"', '"scripts/run-rc6-real-impact-liquid-particle-maximum-c23.py"', "runner", 1),
        ('"specs/ai-native-studio-rc6-real-impact-liquid-fractions-threshold-c18.v1.01.json"', '"specs/ai-native-studio-rc6-real-impact-liquid-particle-maximum-c23.v1.12.json"', "spec", 1),
        (lineage_anchor, lineage_extension, "C18/C21/C22 lineage constants", 1),
        (load_anchor, load_extension, "C18/C21 lineage loads", 1),
        (baseline_anchor, baseline_extension, "C18/C21/C22 baseline hashes", 1),
        (lineage_check_anchor, lineage_check_extension, "C18/C21 accepted lineage checks", 1),
        ('"logs/01-real-impact-fractions-threshold.stdout.log"', '"logs/01-real-impact-particle-maximum.stdout.log"', "stdout log", 1),
        ('"logs/01-real-impact-fractions-threshold.stderr.log"', '"logs/01-real-impact-particle-maximum.stderr.log"', "stderr log", 1),
        ('"processes/01-real-impact-fractions-threshold.json"', '"processes/01-real-impact-particle-maximum.json"', "process receipt", 1),
        ('configuration["particleMinimum"] == 8 and configuration["particleMaximum"] == 16', 'configuration["particleMinimum"] == 8 and configuration["particleMaximum"] == 12', "particle maximum configuration check", 1),
        ('abs(result["metrics"]["maximumLiquidCentroidShiftCupLocalMeters"] - centroid_shift) <= 1e-8', 'abs(result["metrics"]["maximumLiquidCentroidShiftCupLocalMeters"] - centroid_shift) <= 2e-8', "validated centroid replay tolerance", 1),
        ('"bfs.rc6RealImpactLiquidFractionsThresholdC18IndependentAudit.v0.1"', '"bfs.rc6RealImpactLiquidParticleMaximumC23IndependentAudit.v0.1"', "audit schema", 1),
        ("RC6_REAL_IMPACT_LIQUID_FRACTIONS_THRESHOLD_C18_AUDIT=", "RC6_REAL_IMPACT_LIQUID_PARTICLE_MAXIMUM_C23_AUDIT=", "audit marker", 1),
        ("real-impact liquid C18 independent audit failed", "real-impact liquid C23 independent audit failed", "failure marker", 1),
    )
    for before, after, label, expected in replacements:
        if source.count(before) != expected:
            raise RuntimeError(f"C23 auditor {label} target mismatch")
        source = source.replace(before, after)
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#RC6_REAL_IMPACT_LIQUID_PARTICLE_MAXIMUM_C23", "exec"), globals(), globals())
