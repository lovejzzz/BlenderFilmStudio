#!/usr/bin/env python3
"""C2 audit-only closure correcting exactly two inherited C18 log paths."""

import hashlib
import importlib.util
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-real-impact-liquid-water-diffusion-c26-c1.py")
EXPECTED_BASE_SHA256 = "7abefb7c3ad30e7dee4d88402ad3c587bf4151b71bd2c3b9fa3b6b99c611e884"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("C26 C2 audit base identity mismatch")
    module_spec = importlib.util.spec_from_file_location("rc6_c26_c1_audit_base", BASE)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    source = module.transformed_source()
    base_anchor = 'BASE_AUDITOR = RESEARCH / "scripts/audit-rc6-real-impact-liquid-water-diffusion-c26.py"\n'
    base_extension = base_anchor + (
        'C1_SPEC = RESEARCH / "specs/ai-native-studio-rc6-real-impact-liquid-water-diffusion-c26-audit-c1.v1.16.json"\n'
        'C1_TOOL = RESEARCH / "scripts/audit-rc6-real-impact-liquid-water-diffusion-c26-c1.py"\n'
        'C1_ROOT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-water-diffusion-c26-audit-c1-attempt-105"\n'
    )
    check_anchor = 'check("baseFilesExact", sha(BASE_SPEC) == spec["baseFreeze"]["specFileSha256"] and sha(BASE_AUDITOR) == spec["baseFreeze"]["auditorFileSha256"], checks)\n'
    check_extension = check_anchor + 'check("c1PreRootFailureBound", sha(C1_SPEC) == spec["retainedC1"]["specFileSha256"] and sha(C1_TOOL) == spec["retainedC1"]["toolFileSha256"] and not C1_ROOT.exists(), checks)\n'
    replacements = (
        ("ai-native-studio-rc6-real-impact-liquid-water-diffusion-c26-audit-c1.v1.16.json", "ai-native-studio-rc6-real-impact-liquid-water-diffusion-c26-audit-c2.v1.17.json", "spec path", 1),
        ("RC6-2026-09-02-real-impact-liquid-water-diffusion-c26-audit-c1-attempt-105", "RC6-2026-09-02-real-impact-liquid-water-diffusion-c26-audit-c2-attempt-106", "fresh root", 1),
        ('"logs/01-real-impact-fractions-threshold.stdout.log"', '"logs/01-real-impact-water-diffusion.stdout.log"', "stdout path", 1),
        ('"logs/01-real-impact-fractions-threshold.stderr.log"', '"logs/01-real-impact-water-diffusion.stderr.log"', "stderr path", 1),
        (base_anchor, base_extension, "C1 constants", 1),
        (check_anchor, check_extension, "C1 retained check", 1),
        ('"bfs.rc6RealImpactLiquidWaterDiffusionC26AuditC1.v0.1"', '"bfs.rc6RealImpactLiquidWaterDiffusionC26AuditC2.v0.1"', "audit schema", 1),
        ("RC6_REAL_IMPACT_LIQUID_WATER_DIFFUSION_C26_AUDIT_C1=", "RC6_REAL_IMPACT_LIQUID_WATER_DIFFUSION_C26_AUDIT_C2=", "result marker", 1),
    )
    for before, after, label, expected in replacements:
        if source.count(before) != expected:
            raise RuntimeError(f"C26 C2 {label} target mismatch: {source.count(before)} != {expected}")
        source = source.replace(before, after)
    source = source.replace("C26 C1", "C26 C2")
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#RC6_REAL_IMPACT_LIQUID_WATER_DIFFUSION_C26_C2", "exec"), globals(), globals())
