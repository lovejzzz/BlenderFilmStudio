#!/usr/bin/env python3
"""Run one exact-C18 impact-liquid test with particle band width 4 to 3."""

import hashlib
import importlib.util
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-real-impact-liquid-particle-maximum-c23.py")
EXPECTED_BASE_SHA256 = "4c2d7c705e2cb88180b48cd3fd40e5f33c7815deed98187686600f676cbe89dd"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("C29 runner base identity mismatch")
    module_spec = importlib.util.spec_from_file_location("rc6_c23_runner_base", BASE)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    source = module.transformed_source()
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
    baseline_anchor = '    (C22_INSPECTION, spec["baseline"]["c22InspectionFileSha256"]),\n'
    baseline_extension = baseline_anchor + (
        '    (C26_RESULT, spec["baseline"]["c26ResultFileSha256"]),\n'
        '    (C26_RECEIPT, spec["baseline"]["c26ReceiptFileSha256"]),\n'
        '    (C26_C2_AUDIT, spec["baseline"]["c26C2AuditFileSha256"]),\n'
        '    (C27_RESULT, spec["baseline"]["c27ResultFileSha256"]),\n'
        '    (C27_RECEIPT, spec["baseline"]["c27ReceiptFileSha256"]),\n'
        '    (C27_AUDIT, spec["baseline"]["c27AuditFileSha256"]),\n'
        '    (C28_INSPECTION, spec["baseline"]["c28InspectionFileSha256"]),\n'
    )
    replacements = (
        ("RC6-2026-09-02-real-impact-liquid-particle-maximum-c23-attempt-101", "RC6-2026-09-02-real-impact-liquid-particle-band-width-c29-attempt-108", "fresh roots", 2),
        ('"scripts/run-rc6-real-impact-liquid-particle-maximum-c23-scene.py"', '"scripts/run-rc6-real-impact-liquid-particle-band-width-c29-scene.py"', "scene tool", 1),
        ('"scripts/audit-rc6-real-impact-liquid-particle-maximum-c23.py"', '"scripts/audit-rc6-real-impact-liquid-particle-band-width-c29.py"', "auditor", 1),
        ('"specs/ai-native-studio-rc6-real-impact-liquid-particle-maximum-c23.v1.12.json"', '"specs/ai-native-studio-rc6-real-impact-liquid-particle-band-width-c29.v1.19.json"', "spec", 1),
        (lineage_anchor, lineage_extension, "C26/C27/C28 lineage constants", 1),
        (baseline_anchor, baseline_extension, "C26/C27/C28 lineage hashes", 1),
        ('"RC6_REAL_IMPACT_LIQUID_PARTICLE_MAXIMUM_C23="', '"RC6_REAL_IMPACT_LIQUID_PARTICLE_BAND_WIDTH_C29="', "scene marker", 1),
        ('"bfs.rc6RealImpactLiquidParticleMaximumC23Admission.v0.1"', '"bfs.rc6RealImpactLiquidParticleBandWidthC29Admission.v0.1"', "admission schema", 1),
        ('"bfs.rc6RealImpactLiquidParticleMaximumC23Failure.v0.1"', '"bfs.rc6RealImpactLiquidParticleBandWidthC29Failure.v0.1"', "failure schema", 1),
        ('"bfs.rc6RealImpactLiquidParticleMaximumC23Receipt.v0.1"', '"bfs.rc6RealImpactLiquidParticleBandWidthC29Receipt.v0.1"', "receipt schema", 1),
        ('"PASS_REAL_IMPACT_LIQUID_PARTICLE_MAXIMUM_C23"', '"PASS_REAL_IMPACT_LIQUID_PARTICLE_BAND_WIDTH_C29"', "pass verdict", 1),
        ('"FAIL_REAL_IMPACT_LIQUID_PARTICLE_MAXIMUM_C23"', '"FAIL_REAL_IMPACT_LIQUID_PARTICLE_BAND_WIDTH_C29"', "fail verdict", 1),
        ('"logs/01-real-impact-particle-maximum.stdout.log"', '"logs/01-real-impact-particle-band-width.stdout.log"', "stdout log", 1),
        ('"logs/01-real-impact-particle-maximum.stderr.log"', '"logs/01-real-impact-particle-band-width.stderr.log"', "stderr log", 1),
        ('"processes/01-real-impact-particle-maximum.json"', '"processes/01-real-impact-particle-band-width.json"', "process receipt", 1),
        ('"RC6_REAL_IMPACT_LIQUID_PARTICLE_MAXIMUM_C23_RUN="', '"RC6_REAL_IMPACT_LIQUID_PARTICLE_BAND_WIDTH_C29_RUN="', "runner marker", 1),
    )
    for before, after, label, expected in replacements:
        if source.count(before) != expected:
            raise RuntimeError(f"C29 runner {label} target mismatch")
        source = source.replace(before, after)
    source = source.replace("real-impact liquid C23", "real-impact liquid C29")
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#RC6_REAL_IMPACT_LIQUID_PARTICLE_BAND_WIDTH_C29", "exec"), globals(), globals())
