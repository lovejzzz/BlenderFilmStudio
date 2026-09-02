#!/usr/bin/env python3
"""Repeat C20 once in fresh roots after the owner-requested restart interruption."""

import hashlib
import importlib.util
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-real-impact-liquid-particle-radius-c20.py")
EXPECTED_BASE_SHA256 = "3f87863083c7333fd64f2bc2aea82223159b33c54541eb2ba1b72bbc11849b0f"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("C20 C1 runner base identity mismatch")
    module_spec = importlib.util.spec_from_file_location("rc6_c20_runner_base", BASE)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    source = module.transformed_source()
    lineage_anchor = 'C19_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-fractions-threshold-data-comparison-c19-attempt-92/independent-audit.json"\n'
    lineage_extension = lineage_anchor + (
        'ATTEMPT93_WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-real-impact-liquid-particle-radius-c20-" + "attempt-93")\n'
        'ATTEMPT93_ADMISSION = RESEARCH / ("experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-particle-radius-c20-" + "attempt-93/admission.json")\n'
        'ATTEMPT93_INTERRUPTION = RESEARCH / ("experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-particle-radius-c20-" + "attempt-93/interruption.json")\n'
    )
    function_anchor = 'def canonical(value):\n'
    function_extension = '''def interrupted_work_snapshot(root):
    files = [path for path in root.rglob("*") if path.is_file()]
    lines = sorted(sha(path) + str(path.relative_to(root)) for path in files)
    return {
        "fileCount": len(files),
        "totalBytes": sum(path.stat().st_size for path in files),
        "sortedSha256PathLinesHash": hashlib.sha256(("\\n".join(lines) + "\\n").encode()).hexdigest(),
    }


def canonical(value):
'''
    baseline_anchor = '    (C19_AUDIT, spec["baseline"]["c19AuditFileSha256"]),\n'
    baseline_extension = baseline_anchor + (
        '    (ATTEMPT93_ADMISSION, spec["baseline"]["attempt93AdmissionFileSha256"]),\n'
        '    (ATTEMPT93_INTERRUPTION, spec["baseline"]["attempt93InterruptionFileSha256"]),\n'
    )
    retained_anchor = 'static_before = manifest(STATIC_CACHE)\n'
    retained_extension = '''attempt93_admission = json.loads(ATTEMPT93_ADMISSION.read_text())
attempt93_interruption = json.loads(ATTEMPT93_INTERRUPTION.read_text())
if (
    attempt93_admission["status"] != "PASS"
    or attempt93_interruption["status"] != "INTERRUPTED_BY_OWNER_REQUESTED_CODEX_RESTART"
    or attempt93_interruption["scientificVerdict"] is not None
    or interrupted_work_snapshot(ATTEMPT93_WORK) != spec["baseline"]["attempt93WorkSnapshot"]
):
    raise RuntimeError("C20 C1 retained attempt-93 drift")
static_before = manifest(STATIC_CACHE)
'''
    replacements = (
        ("RC6-2026-09-02-real-impact-liquid-particle-radius-c20-attempt-93", "RC6-2026-09-02-real-impact-liquid-particle-radius-c20-c1-attempt-94", "fresh roots", 2),
        ('"scripts/audit-rc6-real-impact-liquid-particle-radius-c20.py"', '"scripts/audit-rc6-real-impact-liquid-particle-radius-c20-c1.py"', "auditor", 1),
        ('"specs/ai-native-studio-rc6-real-impact-liquid-particle-radius-c20.v1.04.json"', '"specs/ai-native-studio-rc6-real-impact-liquid-particle-radius-c20-c1.v1.05.json"', "spec", 1),
        (lineage_anchor, lineage_extension, "attempt-93 lineage constants", 1),
        (function_anchor, function_extension, "retained-work snapshot helper", 1),
        (baseline_anchor, baseline_extension, "attempt-93 baseline hashes", 1),
        (retained_anchor, retained_extension, "attempt-93 retained-root check", 1),
        ('"bfs.rc6RealImpactLiquidParticleRadiusC20Admission.v0.1"', '"bfs.rc6RealImpactLiquidParticleRadiusC20C1Admission.v0.1"', "admission schema", 1),
        ('"bfs.rc6RealImpactLiquidParticleRadiusC20Failure.v0.1"', '"bfs.rc6RealImpactLiquidParticleRadiusC20C1Failure.v0.1"', "failure schema", 1),
        ('"bfs.rc6RealImpactLiquidParticleRadiusC20Receipt.v0.1"', '"bfs.rc6RealImpactLiquidParticleRadiusC20C1Receipt.v0.1"', "receipt schema", 1),
        ('"RC6_REAL_IMPACT_LIQUID_PARTICLE_RADIUS_C20_RUN="', '"RC6_REAL_IMPACT_LIQUID_PARTICLE_RADIUS_C20_C1_RUN="', "runner marker", 1),
    )
    for before, after, label, expected in replacements:
        if source.count(before) != expected:
            raise RuntimeError(f"C20 C1 runner {label} target mismatch")
        source = source.replace(before, after)
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#RC6_REAL_IMPACT_LIQUID_PARTICLE_RADIUS_C20_C1", "exec"), globals(), globals())
