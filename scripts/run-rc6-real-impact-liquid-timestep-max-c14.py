#!/usr/bin/env python3
"""Run one exact-C12 impact-liquid test with timesteps_max 4 to 8."""

import hashlib
import importlib.util
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-real-impact-liquid-preview-c12.py")
EXPECTED_BASE_SHA256 = "e9ffec45491f4a59982182a76aac72fc80763f2be83a36a1cd3c71c77f416327"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("C14 runner base identity mismatch")
    module_spec = importlib.util.spec_from_file_location("rc6_c12_runner_base", BASE)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    source = module.transformed_source()
    lineage_anchor = (
        'C11_AUDIT = RESEARCH / "experiments/physical-richness/'
        'RC6-2026-09-02-real-impact-event-window-c11-attempt-83/event-window-audit.json"\n'
    )
    lineage_extension = lineage_anchor + (
        'C12_RESULT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-preview-c12-attempt-84/result.json"\n'
        'C12_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-preview-c12-attempt-84/independent-audit.json"\n'
        'C13_RESULT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-data-occupancy-c13-attempt-85/result.json"\n'
        'C13_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-data-occupancy-c13-attempt-85/independent-audit.json"\n'
    )
    baseline_anchor = '    (C11_AUDIT, spec["baseline"]["c11AuditFileSha256"]),\n'
    baseline_extension = baseline_anchor + (
        '    (C12_RESULT, spec["baseline"]["c12ResultFileSha256"]),\n'
        '    (C12_AUDIT, spec["baseline"]["c12AuditFileSha256"]),\n'
        '    (C13_RESULT, spec["baseline"]["c13ResultFileSha256"]),\n'
        '    (C13_AUDIT, spec["baseline"]["c13AuditFileSha256"]),\n'
    )
    replacements = (
        ("RC6-2026-09-02-real-impact-liquid-preview-c12-attempt-84", "RC6-2026-09-02-real-impact-liquid-timestep-max-c14-attempt-86", "fresh roots", 2),
        ('"scripts/run-rc6-real-impact-liquid-preview-c12-scene.py"', '"scripts/run-rc6-real-impact-liquid-timestep-max-c14-scene.py"', "scene tool", 1),
        ('"scripts/audit-rc6-real-impact-liquid-preview-c12.py"', '"scripts/audit-rc6-real-impact-liquid-timestep-max-c14.py"', "auditor", 1),
        ('"specs/ai-native-studio-rc6-real-impact-liquid-preview-c12.v0.95.json"', '"specs/ai-native-studio-rc6-real-impact-liquid-timestep-max-c14.v0.97.json"', "spec", 1),
        (lineage_anchor, lineage_extension, "diagnostic lineage constants", 1),
        (baseline_anchor, baseline_extension, "diagnostic lineage hashes", 1),
        ('"RC6_REAL_IMPACT_LIQUID_PREVIEW="', '"RC6_REAL_IMPACT_LIQUID_TIMESTEP_MAX_C14="', "scene marker", 1),
        ('"bfs.rc6RealImpactLiquidPreviewC12Admission.v0.1"', '"bfs.rc6RealImpactLiquidTimestepMaxC14Admission.v0.1"', "admission schema", 1),
        ('"bfs.rc6RealImpactLiquidPreviewC12Failure.v0.1"', '"bfs.rc6RealImpactLiquidTimestepMaxC14Failure.v0.1"', "failure schema", 1),
        ('"bfs.rc6RealImpactLiquidPreviewC12Receipt.v0.1"', '"bfs.rc6RealImpactLiquidTimestepMaxC14Receipt.v0.1"', "receipt schema", 1),
        ('"PASS_REAL_IMPACT_LIQUID_PREVIEW"', '"PASS_REAL_IMPACT_LIQUID_TIMESTEP_MAX_C14"', "pass verdict", 1),
        ('"FAIL_REAL_IMPACT_LIQUID_PREVIEW"', '"FAIL_REAL_IMPACT_LIQUID_TIMESTEP_MAX_C14"', "fail verdict", 1),
        ('"logs/01-real-impact-liquid.stdout.log"', '"logs/01-real-impact-timestep-max.stdout.log"', "stdout log", 1),
        ('"logs/01-real-impact-liquid.stderr.log"', '"logs/01-real-impact-timestep-max.stderr.log"', "stderr log", 1),
        ('"processes/01-real-impact-liquid.json"', '"processes/01-real-impact-timestep-max.json"', "process receipt", 1),
        ('"RC6_REAL_IMPACT_LIQUID_PREVIEW_C12_RUN="', '"RC6_REAL_IMPACT_LIQUID_TIMESTEP_MAX_C14_RUN="', "runner marker", 1),
    )
    for before, after, label, expected in replacements:
        if source.count(before) != expected:
            raise RuntimeError(f"C14 runner {label} target mismatch")
        source = source.replace(before, after)
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#RC6_REAL_IMPACT_LIQUID_TIMESTEP_MAX_C14", "exec"), globals(), globals())
