#!/usr/bin/env python3
"""Adapt the frozen C14 auditor for the one-variable C16 CFL repeat."""

import hashlib
import importlib.util
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-real-impact-liquid-timestep-max-c14.py")
EXPECTED_BASE_SHA256 = "b6911e86b72229500cf958543ca0b16062efad4b0693704da0392c9a4ccd3e59"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("C16 auditor base identity mismatch")
    module_spec = importlib.util.spec_from_file_location("rc6_c14_auditor_base", BASE)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    source = module.transformed_source()
    old_paths = '''EXPECTED_FREEZE_PATHS = {
    "research/2026-09-02-rc6-real-impact-liquid-timestep-max-c14-preregistration.md",
    "research/2026-09-02-rc6-real-impact-timestep-source-inspection.md",
    "research/lab-journal.md",
    "scripts/audit-rc6-real-impact-liquid-timestep-max-c14.py",
    "scripts/run-rc6-real-impact-liquid-timestep-max-c14-scene.py",
    "scripts/run-rc6-real-impact-liquid-timestep-max-c14.py",
    "specs/ai-native-studio-rc6-real-impact-liquid-timestep-max-c14.v0.97.json",
}'''
    new_paths = '''EXPECTED_FREEZE_PATHS = {
    "research/2026-09-02-rc6-real-impact-liquid-cfl-c16-preregistration.md",
    "scripts/audit-rc6-real-impact-liquid-cfl-c16.py",
    "scripts/run-rc6-real-impact-liquid-cfl-c16-scene.py",
    "scripts/run-rc6-real-impact-liquid-cfl-c16.py",
    "specs/ai-native-studio-rc6-real-impact-liquid-cfl-c16.v0.99.json",
}'''
    lineage_anchor = 'C13_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-data-occupancy-c13-attempt-85/independent-audit.json"\n'
    lineage_extension = lineage_anchor + (
        'C14_RESULT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-timestep-max-c14-attempt-86/result.json"\n'
        'C14_RECEIPT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-timestep-max-c14-attempt-86/receipt.json"\n'
        'C14_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-timestep-max-c14-attempt-86/independent-audit.json"\n'
        'C15_RESULT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-c14-transition-c15-attempt-87/result.json"\n'
        'C15_RECEIPT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-c14-transition-c15-attempt-87/receipt.json"\n'
        'C15_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-c14-transition-c15-attempt-87/independent-audit.json"\n'
    )
    load_anchor = 'c13_audit = json.loads(C13_AUDIT.read_text())\n'
    load_extension = load_anchor + (
        'c14_result = json.loads(C14_RESULT.read_text())\n'
        'c14_receipt = json.loads(C14_RECEIPT.read_text())\n'
        'c14_audit = json.loads(C14_AUDIT.read_text())\n'
        'c15_result = json.loads(C15_RESULT.read_text())\n'
        'c15_receipt = json.loads(C15_RECEIPT.read_text())\n'
        'c15_audit = json.loads(C15_AUDIT.read_text())\n'
    )
    baseline_anchor = 'and sha(C13_AUDIT) == spec["baseline"]["c13AuditFileSha256"]'
    baseline_extension = baseline_anchor + ' and sha(C14_RESULT) == spec["baseline"]["c14ResultFileSha256"] and sha(C14_RECEIPT) == spec["baseline"]["c14ReceiptFileSha256"] and sha(C14_AUDIT) == spec["baseline"]["c14AuditFileSha256"] and sha(C15_RESULT) == spec["baseline"]["c15ResultFileSha256"] and sha(C15_RECEIPT) == spec["baseline"]["c15ReceiptFileSha256"] and sha(C15_AUDIT) == spec["baseline"]["c15AuditFileSha256"]'
    lineage_check_anchor = 'and c13_audit["status"] == "PASS" and c13_audit["auditHash"] == spec["baseline"]["c13AuditHash"]'
    lineage_check_extension = lineage_check_anchor + ' and c14_result["resultHash"] == spec["baseline"]["c14ResultHash"] and c14_result["status"] == "FAIL" and c14_receipt["receiptHash"] == spec["baseline"]["c14ReceiptHash"] and c14_audit["status"] == "PASS" and c14_audit["auditHash"] == spec["baseline"]["c14AuditHash"] and c15_result["classification"] == "TRANSITION_ORDER_INCONCLUSIVE" and c15_result["resultHash"] == spec["baseline"]["c15ResultHash"] and c15_receipt["receiptHash"] == spec["baseline"]["c15ReceiptHash"] and c15_audit["status"] == "PASS" and c15_audit["auditHash"] == spec["baseline"]["c15AuditHash"]'
    replacements = (
        ("RC6-2026-09-02-real-impact-liquid-timestep-max-c14-attempt-86", "RC6-2026-09-02-real-impact-liquid-cfl-c16-attempt-88", "fresh roots", 2),
        (old_paths, new_paths, "freeze path roster", 1),
        ('"scripts/run-rc6-real-impact-liquid-timestep-max-c14-scene.py"', '"scripts/run-rc6-real-impact-liquid-cfl-c16-scene.py"', "scene tool", 1),
        ('"scripts/run-rc6-real-impact-liquid-timestep-max-c14.py"', '"scripts/run-rc6-real-impact-liquid-cfl-c16.py"', "runner", 1),
        ('"specs/ai-native-studio-rc6-real-impact-liquid-timestep-max-c14.v0.97.json"', '"specs/ai-native-studio-rc6-real-impact-liquid-cfl-c16.v0.99.json"', "spec", 1),
        (lineage_anchor, lineage_extension, "C14/C15 lineage constants", 1),
        (load_anchor, load_extension, "C14/C15 lineage loads", 1),
        (baseline_anchor, baseline_extension, "C14/C15 baseline hashes", 1),
        (lineage_check_anchor, lineage_check_extension, "C14/C15 lineage checks", 1),
        ('"logs/01-real-impact-timestep-max.stdout.log"', '"logs/01-real-impact-cfl.stdout.log"', "stdout log", 1),
        ('"logs/01-real-impact-timestep-max.stderr.log"', '"logs/01-real-impact-cfl.stderr.log"', "stderr log", 1),
        ('"processes/01-real-impact-timestep-max.json"', '"processes/01-real-impact-cfl.json"', "process receipt", 1),
        ('abs(configuration["cflCondition"] - 2.0)', 'abs(configuration["cflCondition"] - 1.0)', "CFL configuration check", 1),
        ('"bfs.rc6RealImpactLiquidTimestepMaxC14IndependentAudit.v0.1"', '"bfs.rc6RealImpactLiquidCflC16IndependentAudit.v0.1"', "audit schema", 1),
        ("RC6_REAL_IMPACT_LIQUID_TIMESTEP_MAX_C14_AUDIT=", "RC6_REAL_IMPACT_LIQUID_CFL_C16_AUDIT=", "audit marker", 1),
        ("real-impact liquid C14 independent audit failed", "real-impact liquid C16 independent audit failed", "failure marker", 1),
    )
    for before, after, label, expected in replacements:
        if source.count(before) != expected:
            raise RuntimeError(f"C16 auditor {label} target mismatch")
        source = source.replace(before, after)
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#RC6_REAL_IMPACT_LIQUID_CFL_C16", "exec"), globals(), globals())
