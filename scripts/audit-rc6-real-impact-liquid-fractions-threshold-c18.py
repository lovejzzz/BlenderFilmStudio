#!/usr/bin/env python3
"""Adapt the frozen C16 auditor for the one-variable C18 threshold test."""

import hashlib
import importlib.util
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-real-impact-liquid-cfl-c16.py")
EXPECTED_BASE_SHA256 = "04b402a212fded464a8140a69906067e24247e2559c7bbbf6cb05d1401fabeed"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("C18 auditor base identity mismatch")
    module_spec = importlib.util.spec_from_file_location("rc6_c16_auditor_base", BASE)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    source = module.transformed_source()
    old_paths = '''EXPECTED_FREEZE_PATHS = {
    "research/2026-09-02-rc6-real-impact-liquid-cfl-c16-preregistration.md",
    "scripts/audit-rc6-real-impact-liquid-cfl-c16.py",
    "scripts/run-rc6-real-impact-liquid-cfl-c16-scene.py",
    "scripts/run-rc6-real-impact-liquid-cfl-c16.py",
    "specs/ai-native-studio-rc6-real-impact-liquid-cfl-c16.v0.99.json",
}'''
    new_paths = '''EXPECTED_FREEZE_PATHS = {
    "research/2026-09-02-rc6-real-impact-liquid-fractions-threshold-c18-preregistration.md",
    "scripts/audit-rc6-real-impact-liquid-fractions-threshold-c18.py",
    "scripts/run-rc6-real-impact-liquid-fractions-threshold-c18-scene.py",
    "scripts/run-rc6-real-impact-liquid-fractions-threshold-c18.py",
    "specs/ai-native-studio-rc6-real-impact-liquid-fractions-threshold-c18.v1.01.json",
}'''
    lineage_anchor = 'C15_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-c14-transition-c15-attempt-87/independent-audit.json"\n'
    lineage_extension = lineage_anchor + (
        'C16_RESULT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-cfl-c16-attempt-88/result.json"\n'
        'C16_RECEIPT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-cfl-c16-attempt-88/receipt.json"\n'
        'C16_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-cfl-c16-attempt-88/independent-audit.json"\n'
        'C17_RESULT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-cfl-data-comparison-c17-attempt-89/result.json"\n'
        'C17_RECEIPT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-cfl-data-comparison-c17-attempt-89/receipt.json"\n'
        'C17_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-cfl-data-comparison-c17-attempt-89/independent-audit.json"\n'
    )
    load_anchor = 'c15_audit = json.loads(C15_AUDIT.read_text())\n'
    load_extension = load_anchor + (
        'c16_result = json.loads(C16_RESULT.read_text())\n'
        'c16_receipt = json.loads(C16_RECEIPT.read_text())\n'
        'c16_audit = json.loads(C16_AUDIT.read_text())\n'
        'c17_result = json.loads(C17_RESULT.read_text())\n'
        'c17_receipt = json.loads(C17_RECEIPT.read_text())\n'
        'c17_audit = json.loads(C17_AUDIT.read_text())\n'
    )
    baseline_anchor = 'and sha(C15_AUDIT) == spec["baseline"]["c15AuditFileSha256"]'
    baseline_extension = baseline_anchor + ' and sha(C16_RESULT) == spec["baseline"]["c16ResultFileSha256"] and sha(C16_RECEIPT) == spec["baseline"]["c16ReceiptFileSha256"] and sha(C16_AUDIT) == spec["baseline"]["c16AuditFileSha256"] and sha(C17_RESULT) == spec["baseline"]["c17ResultFileSha256"] and sha(C17_RECEIPT) == spec["baseline"]["c17ReceiptFileSha256"] and sha(C17_AUDIT) == spec["baseline"]["c17AuditFileSha256"]'
    lineage_check_anchor = 'and c15_audit["status"] == "PASS" and c15_audit["auditHash"] == spec["baseline"]["c15AuditHash"]'
    lineage_check_extension = lineage_check_anchor + ' and c16_result["resultHash"] == spec["baseline"]["c16ResultHash"] and c16_result["status"] == "FAIL" and c16_receipt["receiptHash"] == spec["baseline"]["c16ReceiptHash"] and c16_audit["status"] == "PASS" and c16_audit["auditHash"] == spec["baseline"]["c16AuditHash"] and c17_result["classification"] == "DATA_MESH_EXPANSION_WITHOUT_PRIOR_CUP_INTRUSION" and c17_result["resultHash"] == spec["baseline"]["c17ResultHash"] and c17_receipt["receiptHash"] == spec["baseline"]["c17ReceiptHash"] and c17_audit["status"] == "PASS" and c17_audit["auditHash"] == spec["baseline"]["c17AuditHash"]'
    replacements = (
        ("RC6-2026-09-02-real-impact-liquid-cfl-c16-attempt-88", "RC6-2026-09-02-real-impact-liquid-fractions-threshold-c18-attempt-90", "fresh roots", 2),
        (old_paths, new_paths, "freeze path roster", 1),
        ('"scripts/run-rc6-real-impact-liquid-cfl-c16-scene.py"', '"scripts/run-rc6-real-impact-liquid-fractions-threshold-c18-scene.py"', "scene tool", 1),
        ('"scripts/run-rc6-real-impact-liquid-cfl-c16.py"', '"scripts/run-rc6-real-impact-liquid-fractions-threshold-c18.py"', "runner", 1),
        ('"specs/ai-native-studio-rc6-real-impact-liquid-cfl-c16.v0.99.json"', '"specs/ai-native-studio-rc6-real-impact-liquid-fractions-threshold-c18.v1.01.json"', "spec", 1),
        (lineage_anchor, lineage_extension, "C16/C17 lineage constants", 1),
        (load_anchor, load_extension, "C16/C17 lineage loads", 1),
        (baseline_anchor, baseline_extension, "C16/C17 baseline hashes", 1),
        (lineage_check_anchor, lineage_check_extension, "C16/C17 lineage checks", 1),
        ('"logs/01-real-impact-cfl.stdout.log"', '"logs/01-real-impact-fractions-threshold.stdout.log"', "stdout log", 1),
        ('"logs/01-real-impact-cfl.stderr.log"', '"logs/01-real-impact-fractions-threshold.stderr.log"', "stderr log", 1),
        ('"processes/01-real-impact-cfl.json"', '"processes/01-real-impact-fractions-threshold.json"', "process receipt", 1),
        ('abs(configuration["fractionsThreshold"] - 0.05)', 'abs(configuration["fractionsThreshold"] - 0.10)', "threshold configuration check", 1),
        ('abs(configuration["cflCondition"] - 1.0)', 'abs(configuration["cflCondition"] - 2.0)', "CFL baseline check", 1),
        ('"bfs.rc6RealImpactLiquidCflC16IndependentAudit.v0.1"', '"bfs.rc6RealImpactLiquidFractionsThresholdC18IndependentAudit.v0.1"', "audit schema", 1),
        ("RC6_REAL_IMPACT_LIQUID_CFL_C16_AUDIT=", "RC6_REAL_IMPACT_LIQUID_FRACTIONS_THRESHOLD_C18_AUDIT=", "audit marker", 1),
        ("real-impact liquid C16 independent audit failed", "real-impact liquid C18 independent audit failed", "failure marker", 1),
    )
    for before, after, label, expected in replacements:
        if source.count(before) != expected:
            raise RuntimeError(f"C18 auditor {label} target mismatch")
        source = source.replace(before, after)
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#RC6_REAL_IMPACT_LIQUID_FRACTIONS_THRESHOLD_C18", "exec"), globals(), globals())
