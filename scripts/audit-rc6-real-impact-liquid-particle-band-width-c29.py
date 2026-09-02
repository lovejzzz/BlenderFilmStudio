#!/usr/bin/env python3
"""Adapt the frozen C23 auditor for the one-variable C29 band-width test."""

import hashlib
import importlib.util
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-real-impact-liquid-particle-maximum-c23.py")
EXPECTED_BASE_SHA256 = "5751bb4505b53d22ce90f93b0576443f926e92aa69afa697db00cca656d2d50f"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("C29 auditor base identity mismatch")
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
    "research/2026-09-02-rc6-real-impact-liquid-particle-band-width-c29-preregistration.md",
    "scripts/audit-rc6-real-impact-liquid-particle-band-width-c29.py",
    "scripts/run-rc6-real-impact-liquid-particle-band-width-c29-scene.py",
    "scripts/run-rc6-real-impact-liquid-particle-band-width-c29.py",
    "specs/ai-native-studio-rc6-real-impact-liquid-particle-band-width-c29.v1.19.json",
}'''
    lineage_anchor = 'C22_INSPECTION = RESEARCH / "research/2026-09-02-rc6-real-impact-particle-maximum-c22-source-inspection.md"\n'
    lineage_extension = lineage_anchor + (
        'C26_RESULT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-water-diffusion-c26-attempt-104/result.json"\n'
        'C26_RECEIPT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-water-diffusion-c26-attempt-104/receipt.json"\n'
        'C26_C2_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-water-diffusion-c26-audit-c2-attempt-106/audit.json"\n'
        'C27_RESULT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-water-diffusion-data-comparison-c27-attempt-107/result.json"\n'
        'C27_RECEIPT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-water-diffusion-data-comparison-c27-attempt-107/receipt.json"\n'
        'C27_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-water-diffusion-data-comparison-c27-attempt-107/independent-audit.json"\n'
        'C28_INSPECTION = RESEARCH / "research/2026-09-02-rc6-real-impact-particle-band-width-c28-source-inspection.md"\n'
    )
    load_anchor = 'c21_c1_receipt = json.loads(C21_C1_RECEIPT.read_text())\n'
    load_extension = load_anchor + (
        'c26_result = json.loads(C26_RESULT.read_text())\n'
        'c26_receipt = json.loads(C26_RECEIPT.read_text())\n'
        'c26_c2_audit = json.loads(C26_C2_AUDIT.read_text())\n'
        'c27_result = json.loads(C27_RESULT.read_text())\n'
        'c27_receipt = json.loads(C27_RECEIPT.read_text())\n'
        'c27_audit = json.loads(C27_AUDIT.read_text())\n'
    )
    baseline_anchor = 'and sha(C22_INSPECTION) == spec["baseline"]["c22InspectionFileSha256"]'
    baseline_extension = baseline_anchor + ' and sha(C26_RESULT) == spec["baseline"]["c26ResultFileSha256"] and sha(C26_RECEIPT) == spec["baseline"]["c26ReceiptFileSha256"] and sha(C26_C2_AUDIT) == spec["baseline"]["c26C2AuditFileSha256"] and sha(C27_RESULT) == spec["baseline"]["c27ResultFileSha256"] and sha(C27_RECEIPT) == spec["baseline"]["c27ReceiptFileSha256"] and sha(C27_AUDIT) == spec["baseline"]["c27AuditFileSha256"] and sha(C28_INSPECTION) == spec["baseline"]["c28InspectionFileSha256"]'
    lineage_check_anchor = 'and c21_c1_receipt["status"] == "PASS_AUDIT_ONLY" and c21_c1_receipt["receiptHash"] == spec["baseline"]["c21C1ReceiptHash"]'
    lineage_check_extension = lineage_check_anchor + ' and c26_result["status"] == "FAIL" and c26_result["resultHash"] == spec["baseline"]["c26ResultHash"] and c26_receipt["status"] == "FAIL" and c26_receipt["receiptHash"] == spec["baseline"]["c26ReceiptHash"] and c26_c2_audit["status"] == "PASS_AUDIT_ONLY_PHYSICAL_FAIL_RETAINED" and c26_c2_audit["auditHash"] == spec["baseline"]["c26C2AuditHash"] and c27_result["classification"] == "MIXED_ONSET_AMPLITUDE_RESPONSE" and c27_result["resultHash"] == spec["baseline"]["c27ResultHash"] and c27_receipt["status"] == "PASS_DIAGNOSTIC" and c27_receipt["receiptHash"] == spec["baseline"]["c27ReceiptHash"] and c27_audit["status"] == "PASS" and c27_audit["auditHash"] == spec["baseline"]["c27AuditHash"]'
    replacements = (
        ("RC6-2026-09-02-real-impact-liquid-particle-maximum-c23-attempt-101", "RC6-2026-09-02-real-impact-liquid-particle-band-width-c29-attempt-108", "fresh roots", 2),
        (old_paths, new_paths, "freeze path roster", 1),
        ('"scripts/run-rc6-real-impact-liquid-particle-maximum-c23-scene.py"', '"scripts/run-rc6-real-impact-liquid-particle-band-width-c29-scene.py"', "scene tool", 1),
        ('"scripts/run-rc6-real-impact-liquid-particle-maximum-c23.py"', '"scripts/run-rc6-real-impact-liquid-particle-band-width-c29.py"', "runner", 1),
        ('"specs/ai-native-studio-rc6-real-impact-liquid-particle-maximum-c23.v1.12.json"', '"specs/ai-native-studio-rc6-real-impact-liquid-particle-band-width-c29.v1.19.json"', "spec", 1),
        (lineage_anchor, lineage_extension, "C26/C27/C28 lineage constants", 1),
        (load_anchor, load_extension, "C26/C27 lineage loads", 1),
        (baseline_anchor, baseline_extension, "C26/C27/C28 baseline hashes", 1),
        (lineage_check_anchor, lineage_check_extension, "C26/C27 accepted lineage checks", 1),
        ('"logs/01-real-impact-particle-maximum.stdout.log"', '"logs/01-real-impact-particle-band-width.stdout.log"', "stdout log", 1),
        ('"logs/01-real-impact-particle-maximum.stderr.log"', '"logs/01-real-impact-particle-band-width.stderr.log"', "stderr log", 1),
        ('"processes/01-real-impact-particle-maximum.json"', '"processes/01-real-impact-particle-band-width.json"', "process receipt", 1),
        ('configuration["particleMinimum"] == 8 and configuration["particleMaximum"] == 12', 'configuration["particleMinimum"] == 8 and configuration["particleMaximum"] == 16 and abs(configuration["particleBandWidth"] - 3.0) <= 1e-6', "particle band configuration check", 1),
        ('abs(configuration["particleRadius"] - 1.8) <= 1e-6 and abs(configuration["particleBandWidth"] - 4.0) <= 1e-6', 'abs(configuration["particleRadius"] - 1.8) <= 1e-6 and abs(configuration["particleBandWidth"] - 3.0) <= 1e-6', "particle band baseline replacement", 1),
        ('"bfs.rc6RealImpactLiquidParticleMaximumC23IndependentAudit.v0.1"', '"bfs.rc6RealImpactLiquidParticleBandWidthC29IndependentAudit.v0.1"', "audit schema", 1),
        ("RC6_REAL_IMPACT_LIQUID_PARTICLE_MAXIMUM_C23_AUDIT=", "RC6_REAL_IMPACT_LIQUID_PARTICLE_BAND_WIDTH_C29_AUDIT=", "audit marker", 1),
        ("real-impact liquid C23 independent audit failed", "real-impact liquid C29 independent audit failed", "failure marker", 1),
    )
    for before, after, label, expected in replacements:
        if source.count(before) != expected:
            raise RuntimeError(f"C29 auditor {label} target mismatch")
        source = source.replace(before, after)
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#RC6_REAL_IMPACT_LIQUID_PARTICLE_BAND_WIDTH_C29", "exec"), globals(), globals())
