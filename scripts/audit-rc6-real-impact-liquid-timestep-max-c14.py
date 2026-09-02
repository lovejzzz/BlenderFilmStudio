#!/usr/bin/env python3
"""Adapt the frozen C12 auditor for the one-variable C14 repeat."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-real-impact-liquid-preview-c12.py")
EXPECTED_BASE_SHA256 = "a59ec439ecfb53d124c48935bd89df5e6795aa57608a5f33ed84eb259bc5bc94"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("C14 auditor base identity mismatch")
    source = BASE.read_text(encoding="utf-8")
    old_paths = '''EXPECTED_FREEZE_PATHS = {
    "research/2026-09-02-rc6-real-impact-liquid-preview-c12-preregistration.md",
    "research/lab-journal.md",
    "scripts/audit-rc6-real-impact-liquid-preview-c12.py",
    "scripts/run-rc6-real-impact-liquid-preview-c12-scene.py",
    "scripts/run-rc6-real-impact-liquid-preview-c12.py",
    "specs/ai-native-studio-rc6-real-impact-liquid-preview-c12.v0.95.json",
}'''
    new_paths = '''EXPECTED_FREEZE_PATHS = {
    "research/2026-09-02-rc6-real-impact-liquid-timestep-max-c14-preregistration.md",
    "research/2026-09-02-rc6-real-impact-timestep-source-inspection.md",
    "research/lab-journal.md",
    "scripts/audit-rc6-real-impact-liquid-timestep-max-c14.py",
    "scripts/run-rc6-real-impact-liquid-timestep-max-c14-scene.py",
    "scripts/run-rc6-real-impact-liquid-timestep-max-c14.py",
    "specs/ai-native-studio-rc6-real-impact-liquid-timestep-max-c14.v0.97.json",
}'''
    lineage_anchor = 'C11_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-event-window-c11-attempt-83/event-window-audit.json"\n'
    lineage_extension = lineage_anchor + (
        'C12_RESULT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-preview-c12-attempt-84/result.json"\n'
        'C12_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-preview-c12-attempt-84/independent-audit.json"\n'
        'C13_RESULT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-data-occupancy-c13-attempt-85/result.json"\n'
        'C13_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-data-occupancy-c13-attempt-85/independent-audit.json"\n'
    )
    load_anchor = 'c11_audit = json.loads(C11_AUDIT.read_text())\n'
    load_extension = load_anchor + (
        'c12_result = json.loads(C12_RESULT.read_text())\n'
        'c12_audit = json.loads(C12_AUDIT.read_text())\n'
        'c13_result = json.loads(C13_RESULT.read_text())\n'
        'c13_audit = json.loads(C13_AUDIT.read_text())\n'
    )
    baseline_anchor = 'and sha(C11_AUDIT) == spec["baseline"]["c11AuditFileSha256"]'
    baseline_extension = baseline_anchor + ' and sha(C12_RESULT) == spec["baseline"]["c12ResultFileSha256"] and sha(C12_AUDIT) == spec["baseline"]["c12AuditFileSha256"] and sha(C13_RESULT) == spec["baseline"]["c13ResultFileSha256"] and sha(C13_AUDIT) == spec["baseline"]["c13AuditFileSha256"]'
    lineage_check_anchor = 'and c11_audit["auditHash"] == spec["baseline"]["c11AuditHash"]'
    lineage_check_extension = lineage_check_anchor + ' and c12_result["resultHash"] == spec["baseline"]["c12ResultHash"] and c12_result["status"] == "FAIL" and c12_audit["status"] == "PASS" and c12_audit["auditHash"] == spec["baseline"]["c12AuditHash"] and c13_result["classification"] == "DATA_SUPPORT_EXPANDS_WITH_MESH_MESH_ONLY_CAUSE_REJECTED" and c13_audit["status"] == "PASS" and c13_audit["auditHash"] == spec["baseline"]["c13AuditHash"]'
    replacements = (
        ("RC6-2026-09-02-real-impact-liquid-preview-c12-attempt-84", "RC6-2026-09-02-real-impact-liquid-timestep-max-c14-attempt-86", "fresh roots", 2),
        (old_paths, new_paths, "freeze path roster", 1),
        ('"scripts/run-rc6-real-impact-liquid-preview-c12-scene.py"', '"scripts/run-rc6-real-impact-liquid-timestep-max-c14-scene.py"', "scene tool", 1),
        ('"scripts/run-rc6-real-impact-liquid-preview-c12.py"', '"scripts/run-rc6-real-impact-liquid-timestep-max-c14.py"', "runner", 1),
        ('"specs/ai-native-studio-rc6-real-impact-liquid-preview-c12.v0.95.json"', '"specs/ai-native-studio-rc6-real-impact-liquid-timestep-max-c14.v0.97.json"', "spec", 1),
        (lineage_anchor, lineage_extension, "diagnostic lineage constants", 1),
        (load_anchor, load_extension, "diagnostic lineage loads", 1),
        (baseline_anchor, baseline_extension, "diagnostic baseline hashes", 1),
        (lineage_check_anchor, lineage_check_extension, "diagnostic lineage checks", 1),
        ('"logs/01-real-impact-liquid.stdout.log"', '"logs/01-real-impact-timestep-max.stdout.log"', "stdout log", 1),
        ('"logs/01-real-impact-liquid.stderr.log"', '"logs/01-real-impact-timestep-max.stderr.log"', "stderr log", 1),
        ('"processes/01-real-impact-liquid.json"', '"processes/01-real-impact-timestep-max.json"', "process receipt", 1),
        ('configuration["timestepsMax"] == 4', 'configuration["timestepsMax"] == 8', "timestep maximum check", 1),
        ('"bfs.rc6RealImpactLiquidPreviewC12IndependentAudit.v0.1"', '"bfs.rc6RealImpactLiquidTimestepMaxC14IndependentAudit.v0.1"', "audit schema", 1),
        ("RC6_REAL_IMPACT_LIQUID_PREVIEW_C12_AUDIT=", "RC6_REAL_IMPACT_LIQUID_TIMESTEP_MAX_C14_AUDIT=", "audit marker", 1),
        ("real-impact liquid C12 independent audit failed", "real-impact liquid C14 independent audit failed", "failure marker", 1),
    )
    for before, after, label, expected in replacements:
        if source.count(before) != expected:
            raise RuntimeError(f"C14 auditor {label} target mismatch")
        source = source.replace(before, after)
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#RC6_REAL_IMPACT_LIQUID_TIMESTEP_MAX_C14", "exec"), globals(), globals())
