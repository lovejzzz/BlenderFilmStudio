#!/usr/bin/env python3
"""Adapt the frozen C23 auditor for the one-variable C26 water diffusion test."""

import hashlib
import importlib.util
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-real-impact-liquid-particle-maximum-c23.py")
EXPECTED_BASE_SHA256 = "5751bb4505b53d22ce90f93b0576443f926e92aa69afa697db00cca656d2d50f"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("C26 auditor base identity mismatch")
    module_spec = importlib.util.spec_from_file_location("rc6_c23_auditor_base", BASE)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    source = module.transformed_source()
    old_paths = '''EXPECTED_FREEZE_PATHS = {
    "research/2026-09-02-rc6-real-impact-liquid-particle-maximum-c23-preregistration.md",
    "scripts/audit-rc6-real-impact-liquid-particle-maximum-c23.py",
    "scripts/run-rc6-real-impact-liquid-particle-maximum-c23-scene.py",
    "scripts/run-rc6-real-impact-liquid-particle-maximum-c23.py",
    "specs/ai-native-studio-rc6-real-impact-liquid-particle-maximum-c23.v1.12.json",
}'''
    new_paths = '''EXPECTED_FREEZE_PATHS = {
    "research/2026-09-02-rc6-real-impact-liquid-water-diffusion-c26-preregistration.md",
    "scripts/audit-rc6-real-impact-liquid-water-diffusion-c26.py",
    "scripts/run-rc6-real-impact-liquid-water-diffusion-c26-scene.py",
    "scripts/run-rc6-real-impact-liquid-water-diffusion-c26.py",
    "specs/ai-native-studio-rc6-real-impact-liquid-water-diffusion-c26.v1.15.json",
}'''
    lineage_anchor = 'C22_INSPECTION = RESEARCH / "research/2026-09-02-rc6-real-impact-particle-maximum-c22-source-inspection.md"\n'
    lineage_extension = lineage_anchor + (
        'C23_RESULT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-particle-maximum-c23-attempt-101/result.json"\n'
        'C23_RECEIPT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-particle-maximum-c23-attempt-101/receipt.json"\n'
        'C23_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-particle-maximum-c23-attempt-101/independent-audit.json"\n'
        'C24_RESULT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-particle-maximum-data-comparison-c24-c1-attempt-103/result.json"\n'
        'C24_RECEIPT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-particle-maximum-data-comparison-c24-c1-attempt-103/receipt.json"\n'
        'C24_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-particle-maximum-data-comparison-c24-c1-attempt-103/independent-audit.json"\n'
        'C25_INSPECTION = RESEARCH / "research/2026-09-02-rc6-real-impact-water-diffusion-c25-source-inspection.md"\n'
    )
    load_anchor = 'c21_c1_receipt = json.loads(C21_C1_RECEIPT.read_text())\n'
    load_extension = load_anchor + (
        'c23_result = json.loads(C23_RESULT.read_text())\n'
        'c23_receipt = json.loads(C23_RECEIPT.read_text())\n'
        'c23_audit = json.loads(C23_AUDIT.read_text())\n'
        'c24_result = json.loads(C24_RESULT.read_text())\n'
        'c24_receipt = json.loads(C24_RECEIPT.read_text())\n'
        'c24_audit = json.loads(C24_AUDIT.read_text())\n'
    )
    baseline_anchor = 'and sha(C22_INSPECTION) == spec["baseline"]["c22InspectionFileSha256"]'
    baseline_extension = baseline_anchor + ' and sha(C23_RESULT) == spec["baseline"]["c23ResultFileSha256"] and sha(C23_RECEIPT) == spec["baseline"]["c23ReceiptFileSha256"] and sha(C23_AUDIT) == spec["baseline"]["c23AuditFileSha256"] and sha(C24_RESULT) == spec["baseline"]["c24ResultFileSha256"] and sha(C24_RECEIPT) == spec["baseline"]["c24ReceiptFileSha256"] and sha(C24_AUDIT) == spec["baseline"]["c24AuditFileSha256"] and sha(C25_INSPECTION) == spec["baseline"]["c25InspectionFileSha256"]'
    lineage_check_anchor = 'and c21_c1_receipt["status"] == "PASS_AUDIT_ONLY" and c21_c1_receipt["receiptHash"] == spec["baseline"]["c21C1ReceiptHash"]'
    lineage_check_extension = lineage_check_anchor + ' and c23_result["status"] == "FAIL" and c23_result["resultHash"] == spec["baseline"]["c23ResultHash"] and c23_receipt["status"] == "FAIL" and c23_receipt["receiptHash"] == spec["baseline"]["c23ReceiptHash"] and c23_audit["status"] == "PASS" and c23_audit["auditHash"] == spec["baseline"]["c23AuditHash"] and c24_result["classification"] == "MIXED_ONSET_AMPLITUDE_RESPONSE" and c24_result["resultHash"] == spec["baseline"]["c24ResultHash"] and c24_receipt["status"] == "PASS_DIAGNOSTIC" and c24_receipt["receiptHash"] == spec["baseline"]["c24ReceiptHash"] and c24_audit["status"] == "PASS" and c24_audit["auditHash"] == spec["baseline"]["c24AuditHash"]'
    replacements = (
        ("RC6-2026-09-02-real-impact-liquid-particle-maximum-c23-attempt-101", "RC6-2026-09-02-real-impact-liquid-water-diffusion-c26-attempt-104", "fresh roots", 2),
        (old_paths, new_paths, "freeze path roster", 1),
        ('"scripts/run-rc6-real-impact-liquid-particle-maximum-c23-scene.py"', '"scripts/run-rc6-real-impact-liquid-water-diffusion-c26-scene.py"', "scene tool", 1),
        ('"scripts/run-rc6-real-impact-liquid-particle-maximum-c23.py"', '"scripts/run-rc6-real-impact-liquid-water-diffusion-c26.py"', "runner", 1),
        ('"specs/ai-native-studio-rc6-real-impact-liquid-particle-maximum-c23.v1.12.json"', '"specs/ai-native-studio-rc6-real-impact-liquid-water-diffusion-c26.v1.15.json"', "spec", 1),
        (lineage_anchor, lineage_extension, "C23/C24/C25 lineage constants", 1),
        (load_anchor, load_extension, "C23/C24 lineage loads", 1),
        (baseline_anchor, baseline_extension, "C23/C24/C25 baseline hashes", 1),
        (lineage_check_anchor, lineage_check_extension, "C23/C24 accepted lineage checks", 1),
        ('"logs/01-real-impact-particle-maximum.stdout.log"', '"logs/01-real-impact-water-diffusion.stdout.log"', "stdout log", 1),
        ('"logs/01-real-impact-particle-maximum.stderr.log"', '"logs/01-real-impact-water-diffusion.stderr.log"', "stderr log", 1),
        ('"processes/01-real-impact-particle-maximum.json"', '"processes/01-real-impact-water-diffusion.json"', "process receipt", 1),
        ('configuration["particleMinimum"] == 8 and configuration["particleMaximum"] == 12', 'configuration["particleMinimum"] == 8 and configuration["particleMaximum"] == 16', "particle baseline restoration", 1),
        (
            'configuration["useFractions"] and abs(configuration["fractionsThreshold"] - 0.10) <= 1e-6',
            'configuration["useFractions"] and configuration["useDiffusion"] and abs(configuration["viscosityBase"] - 1.0) <= 1e-6 and configuration["viscosityExponent"] == 6 and abs(configuration["surfaceTension"]) <= 1e-6 and abs(configuration["fractionsThreshold"] - 0.10) <= 1e-6',
            "water diffusion configuration check",
            1,
        ),
        ('"bfs.rc6RealImpactLiquidParticleMaximumC23IndependentAudit.v0.1"', '"bfs.rc6RealImpactLiquidWaterDiffusionC26IndependentAudit.v0.1"', "audit schema", 1),
        ("RC6_REAL_IMPACT_LIQUID_PARTICLE_MAXIMUM_C23_AUDIT=", "RC6_REAL_IMPACT_LIQUID_WATER_DIFFUSION_C26_AUDIT=", "audit marker", 1),
        ("real-impact liquid C23 independent audit failed", "real-impact liquid C26 independent audit failed", "failure marker", 1),
    )
    for before, after, label, expected in replacements:
        if source.count(before) != expected:
            raise RuntimeError(f"C26 auditor {label} target mismatch")
        source = source.replace(before, after)
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#RC6_REAL_IMPACT_LIQUID_WATER_DIFFUSION_C26", "exec"), globals(), globals())
