#!/usr/bin/env python3
"""Run one exact-C18 impact-liquid test enabling only water diffusion."""

import hashlib
import importlib.util
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-real-impact-liquid-particle-maximum-c23.py")
EXPECTED_BASE_SHA256 = "4c2d7c705e2cb88180b48cd3fd40e5f33c7815deed98187686600f676cbe89dd"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("C26 runner base identity mismatch")
    module_spec = importlib.util.spec_from_file_location("rc6_c23_runner_base", BASE)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    source = module.transformed_source()
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
    baseline_anchor = '    (C22_INSPECTION, spec["baseline"]["c22InspectionFileSha256"]),\n'
    baseline_extension = baseline_anchor + (
        '    (C23_RESULT, spec["baseline"]["c23ResultFileSha256"]),\n'
        '    (C23_RECEIPT, spec["baseline"]["c23ReceiptFileSha256"]),\n'
        '    (C23_AUDIT, spec["baseline"]["c23AuditFileSha256"]),\n'
        '    (C24_RESULT, spec["baseline"]["c24ResultFileSha256"]),\n'
        '    (C24_RECEIPT, spec["baseline"]["c24ReceiptFileSha256"]),\n'
        '    (C24_AUDIT, spec["baseline"]["c24AuditFileSha256"]),\n'
        '    (C25_INSPECTION, spec["baseline"]["c25InspectionFileSha256"]),\n'
    )
    replacements = (
        ("RC6-2026-09-02-real-impact-liquid-particle-maximum-c23-attempt-101", "RC6-2026-09-02-real-impact-liquid-water-diffusion-c26-attempt-104", "fresh roots", 2),
        ('"scripts/run-rc6-real-impact-liquid-particle-maximum-c23-scene.py"', '"scripts/run-rc6-real-impact-liquid-water-diffusion-c26-scene.py"', "scene tool", 1),
        ('"scripts/audit-rc6-real-impact-liquid-particle-maximum-c23.py"', '"scripts/audit-rc6-real-impact-liquid-water-diffusion-c26.py"', "auditor", 1),
        ('"specs/ai-native-studio-rc6-real-impact-liquid-particle-maximum-c23.v1.12.json"', '"specs/ai-native-studio-rc6-real-impact-liquid-water-diffusion-c26.v1.15.json"', "spec", 1),
        (lineage_anchor, lineage_extension, "C23/C24/C25 lineage constants", 1),
        (baseline_anchor, baseline_extension, "C23/C24/C25 lineage hashes", 1),
        ('"RC6_REAL_IMPACT_LIQUID_PARTICLE_MAXIMUM_C23="', '"RC6_REAL_IMPACT_LIQUID_WATER_DIFFUSION_C26="', "scene marker", 1),
        ('"bfs.rc6RealImpactLiquidParticleMaximumC23Admission.v0.1"', '"bfs.rc6RealImpactLiquidWaterDiffusionC26Admission.v0.1"', "admission schema", 1),
        ('"bfs.rc6RealImpactLiquidParticleMaximumC23Failure.v0.1"', '"bfs.rc6RealImpactLiquidWaterDiffusionC26Failure.v0.1"', "failure schema", 1),
        ('"bfs.rc6RealImpactLiquidParticleMaximumC23Receipt.v0.1"', '"bfs.rc6RealImpactLiquidWaterDiffusionC26Receipt.v0.1"', "receipt schema", 1),
        ('"PASS_REAL_IMPACT_LIQUID_PARTICLE_MAXIMUM_C23"', '"PASS_REAL_IMPACT_LIQUID_WATER_DIFFUSION_C26"', "pass verdict", 1),
        ('"FAIL_REAL_IMPACT_LIQUID_PARTICLE_MAXIMUM_C23"', '"FAIL_REAL_IMPACT_LIQUID_WATER_DIFFUSION_C26"', "fail verdict", 1),
        ('"logs/01-real-impact-particle-maximum.stdout.log"', '"logs/01-real-impact-water-diffusion.stdout.log"', "stdout log", 1),
        ('"logs/01-real-impact-particle-maximum.stderr.log"', '"logs/01-real-impact-water-diffusion.stderr.log"', "stderr log", 1),
        ('"processes/01-real-impact-particle-maximum.json"', '"processes/01-real-impact-water-diffusion.json"', "process receipt", 1),
        ('"RC6_REAL_IMPACT_LIQUID_PARTICLE_MAXIMUM_C23_RUN="', '"RC6_REAL_IMPACT_LIQUID_WATER_DIFFUSION_C26_RUN="', "runner marker", 1),
    )
    for before, after, label, expected in replacements:
        if source.count(before) != expected:
            raise RuntimeError(f"C26 runner {label} target mismatch")
        source = source.replace(before, after)
    source = source.replace("real-impact liquid C23", "real-impact liquid C26")
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#RC6_REAL_IMPACT_LIQUID_WATER_DIFFUSION_C26", "exec"), globals(), globals())
