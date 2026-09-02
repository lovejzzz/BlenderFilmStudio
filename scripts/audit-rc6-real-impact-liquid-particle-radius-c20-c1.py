#!/usr/bin/env python3
"""Audit the fresh-root C20 repeat and retained restart interruption independently."""

import hashlib
import importlib.util
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-real-impact-liquid-particle-radius-c20.py")
EXPECTED_BASE_SHA256 = "24f313bc64b678b62e41aaba8b45be511d7af56a5ee213a15f4e2183ca21954f"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("C20 C1 auditor base identity mismatch")
    module_spec = importlib.util.spec_from_file_location("rc6_c20_auditor_base", BASE)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    source = module.transformed_source()
    old_paths = '''EXPECTED_FREEZE_PATHS = {
    "research/2026-09-02-rc6-real-impact-liquid-particle-radius-c20-preregistration.md",
    "research/2026-09-02-rc6-real-impact-particle-radius-c20-source-inspection.md",
    "scripts/audit-rc6-real-impact-liquid-particle-radius-c20.py",
    "scripts/run-rc6-real-impact-liquid-particle-radius-c20-scene.py",
    "scripts/run-rc6-real-impact-liquid-particle-radius-c20.py",
    "specs/ai-native-studio-rc6-real-impact-liquid-particle-radius-c20.v1.04.json",
}'''
    new_paths = '''EXPECTED_FREEZE_PATHS = {
    "research/2026-09-02-rc6-real-impact-liquid-particle-radius-c20-c1-preregistration.md",
    "scripts/audit-rc6-real-impact-liquid-particle-radius-c20-c1.py",
    "scripts/run-rc6-real-impact-liquid-particle-radius-c20-c1.py",
    "specs/ai-native-studio-rc6-real-impact-liquid-particle-radius-c20-c1.v1.05.json",
}'''
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
    load_anchor = 'c19_audit = json.loads(C19_AUDIT.read_text())\n'
    load_extension = load_anchor + (
        'attempt93_admission = json.loads(ATTEMPT93_ADMISSION.read_text())\n'
        'attempt93_interruption = json.loads(ATTEMPT93_INTERRUPTION.read_text())\n'
    )
    baseline_anchor = 'and sha(C19_AUDIT) == spec["baseline"]["c19AuditFileSha256"]'
    baseline_extension = baseline_anchor + ' and sha(ATTEMPT93_ADMISSION) == spec["baseline"]["attempt93AdmissionFileSha256"] and sha(ATTEMPT93_INTERRUPTION) == spec["baseline"]["attempt93InterruptionFileSha256"]'
    lineage_anchor_check = 'and c19_audit["status"] == "PASS" and c19_audit["auditHash"] == spec["baseline"]["c19AuditHash"]'
    lineage_extension_check = lineage_anchor_check + ' and attempt93_admission["status"] == "PASS" and attempt93_interruption["status"] == "INTERRUPTED_BY_OWNER_REQUESTED_CODEX_RESTART" and attempt93_interruption["scientificVerdict"] is None'
    checks_anchor = '    "admissionExact": admission["status"] == "PASS"'
    checks_extension = '    "retainedAttempt93Exact": interrupted_work_snapshot(ATTEMPT93_WORK) == spec["baseline"]["attempt93WorkSnapshot"],\n' + checks_anchor
    replacements = (
        ("RC6-2026-09-02-real-impact-liquid-particle-radius-c20-attempt-93", "RC6-2026-09-02-real-impact-liquid-particle-radius-c20-c1-attempt-94", "fresh roots", 2),
        (old_paths, new_paths, "freeze path roster", 1),
        ('"scripts/run-rc6-real-impact-liquid-particle-radius-c20.py"', '"scripts/run-rc6-real-impact-liquid-particle-radius-c20-c1.py"', "runner", 1),
        ('"specs/ai-native-studio-rc6-real-impact-liquid-particle-radius-c20.v1.04.json"', '"specs/ai-native-studio-rc6-real-impact-liquid-particle-radius-c20-c1.v1.05.json"', "spec", 1),
        (lineage_anchor, lineage_extension, "attempt-93 lineage constants", 1),
        (function_anchor, function_extension, "retained-work snapshot helper", 1),
        (load_anchor, load_extension, "attempt-93 evidence loads", 1),
        (baseline_anchor, baseline_extension, "attempt-93 evidence hashes", 1),
        (lineage_anchor_check, lineage_extension_check, "attempt-93 evidence semantics", 1),
        (checks_anchor, checks_extension, "attempt-93 work-root check", 1),
        ('"bfs.rc6RealImpactLiquidParticleRadiusC20IndependentAudit.v0.1"', '"bfs.rc6RealImpactLiquidParticleRadiusC20C1IndependentAudit.v0.1"', "audit schema", 1),
        ("RC6_REAL_IMPACT_LIQUID_PARTICLE_RADIUS_C20_AUDIT=", "RC6_REAL_IMPACT_LIQUID_PARTICLE_RADIUS_C20_C1_AUDIT=", "audit marker", 1),
        ("real-impact liquid C20 independent audit failed", "real-impact liquid C20 C1 independent audit failed", "failure marker", 1),
    )
    for before, after, label, expected in replacements:
        if source.count(before) != expected:
            raise RuntimeError(f"C20 C1 auditor {label} target mismatch")
        source = source.replace(before, after)
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#RC6_REAL_IMPACT_LIQUID_PARTICLE_RADIUS_C20_C1", "exec"), globals(), globals())
