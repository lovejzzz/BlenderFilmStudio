#!/usr/bin/env python3
"""Run one exact-C14 impact-liquid test with CFL 2.0 to 1.0."""

import hashlib
import importlib.util
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-real-impact-liquid-timestep-max-c14.py")
EXPECTED_BASE_SHA256 = "06fbf142143a4e967602a2eae30336e8d4e8cb2f85d6e4e96102892029b82452"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("C16 runner base identity mismatch")
    module_spec = importlib.util.spec_from_file_location("rc6_c14_runner_base", BASE)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    source = module.transformed_source()
    lineage_anchor = 'C13_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-data-occupancy-c13-attempt-85/independent-audit.json"\n'
    lineage_extension = lineage_anchor + (
        'C14_RESULT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-timestep-max-c14-attempt-86/result.json"\n'
        'C14_RECEIPT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-timestep-max-c14-attempt-86/receipt.json"\n'
        'C14_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-timestep-max-c14-attempt-86/independent-audit.json"\n'
        'C15_RESULT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-c14-transition-c15-attempt-87/result.json"\n'
        'C15_RECEIPT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-c14-transition-c15-attempt-87/receipt.json"\n'
        'C15_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-c14-transition-c15-attempt-87/independent-audit.json"\n'
    )
    baseline_anchor = '    (C13_AUDIT, spec["baseline"]["c13AuditFileSha256"]),\n'
    baseline_extension = baseline_anchor + (
        '    (C14_RESULT, spec["baseline"]["c14ResultFileSha256"]),\n'
        '    (C14_RECEIPT, spec["baseline"]["c14ReceiptFileSha256"]),\n'
        '    (C14_AUDIT, spec["baseline"]["c14AuditFileSha256"]),\n'
        '    (C15_RESULT, spec["baseline"]["c15ResultFileSha256"]),\n'
        '    (C15_RECEIPT, spec["baseline"]["c15ReceiptFileSha256"]),\n'
        '    (C15_AUDIT, spec["baseline"]["c15AuditFileSha256"]),\n'
    )
    replacements = (
        ("RC6-2026-09-02-real-impact-liquid-timestep-max-c14-attempt-86", "RC6-2026-09-02-real-impact-liquid-cfl-c16-attempt-88", "fresh roots", 2),
        ('"scripts/run-rc6-real-impact-liquid-timestep-max-c14-scene.py"', '"scripts/run-rc6-real-impact-liquid-cfl-c16-scene.py"', "scene tool", 1),
        ('"scripts/audit-rc6-real-impact-liquid-timestep-max-c14.py"', '"scripts/audit-rc6-real-impact-liquid-cfl-c16.py"', "auditor", 1),
        ('"specs/ai-native-studio-rc6-real-impact-liquid-timestep-max-c14.v0.97.json"', '"specs/ai-native-studio-rc6-real-impact-liquid-cfl-c16.v0.99.json"', "spec", 1),
        (lineage_anchor, lineage_extension, "C14/C15 lineage constants", 1),
        (baseline_anchor, baseline_extension, "C14/C15 lineage hashes", 1),
        ('"RC6_REAL_IMPACT_LIQUID_TIMESTEP_MAX_C14="', '"RC6_REAL_IMPACT_LIQUID_CFL_C16="', "scene marker", 1),
        ('"bfs.rc6RealImpactLiquidTimestepMaxC14Admission.v0.1"', '"bfs.rc6RealImpactLiquidCflC16Admission.v0.1"', "admission schema", 1),
        ('"bfs.rc6RealImpactLiquidTimestepMaxC14Failure.v0.1"', '"bfs.rc6RealImpactLiquidCflC16Failure.v0.1"', "failure schema", 1),
        ('"bfs.rc6RealImpactLiquidTimestepMaxC14Receipt.v0.1"', '"bfs.rc6RealImpactLiquidCflC16Receipt.v0.1"', "receipt schema", 1),
        ('"PASS_REAL_IMPACT_LIQUID_TIMESTEP_MAX_C14"', '"PASS_REAL_IMPACT_LIQUID_CFL_C16"', "pass verdict", 1),
        ('"FAIL_REAL_IMPACT_LIQUID_TIMESTEP_MAX_C14"', '"FAIL_REAL_IMPACT_LIQUID_CFL_C16"', "fail verdict", 1),
        ('"logs/01-real-impact-timestep-max.stdout.log"', '"logs/01-real-impact-cfl.stdout.log"', "stdout log", 1),
        ('"logs/01-real-impact-timestep-max.stderr.log"', '"logs/01-real-impact-cfl.stderr.log"', "stderr log", 1),
        ('"processes/01-real-impact-timestep-max.json"', '"processes/01-real-impact-cfl.json"', "process receipt", 1),
        ('"RC6_REAL_IMPACT_LIQUID_TIMESTEP_MAX_C14_RUN="', '"RC6_REAL_IMPACT_LIQUID_CFL_C16_RUN="', "runner marker", 1),
    )
    for before, after, label, expected in replacements:
        if source.count(before) != expected:
            raise RuntimeError(f"C16 runner {label} target mismatch")
        source = source.replace(before, after)
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#RC6_REAL_IMPACT_LIQUID_CFL_C16", "exec"), globals(), globals())
