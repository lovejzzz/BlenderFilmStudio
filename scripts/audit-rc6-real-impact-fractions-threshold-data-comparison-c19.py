#!/usr/bin/env python3
"""Independently audit copied C18 Data/Mesh against retained C14/C15."""

import hashlib
import importlib.util
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-real-impact-cfl-data-comparison-c17.py")
EXPECTED_BASE_SHA256 = "bb1f59db662d563be0c9ab6035e99a905a53979487bd563b76d63016f94f3a6a"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("C19 auditor base identity mismatch")
    module_spec = importlib.util.spec_from_file_location("rc6_c17_auditor_base", BASE)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    source = module.transformed_source()
    replacements = (
        ('"""Independently audit copied C16 Data/Mesh against retained C14/C15."""', '"""Independently audit copied C18 Data/Mesh against retained C14/C15."""', "docstring", 1),
        ("RC6-2026-09-02-real-impact-cfl-data-comparison-c17-attempt-89", "RC6-2026-09-02-real-impact-fractions-threshold-data-comparison-c19-attempt-92", "fresh roots", 2),
        ("RC6-2026-09-02-real-impact-liquid-cfl-c16-attempt-88", "RC6-2026-09-02-real-impact-liquid-fractions-threshold-c18-attempt-90", "C18 cache/evidence", 2),
        ('"scripts/analyze-rc6-real-impact-cfl-data-comparison-c17.py"', '"scripts/analyze-rc6-real-impact-fractions-threshold-data-comparison-c19.py"', "analyzer", 1),
        ('"scripts/run-rc6-real-impact-cfl-data-comparison-c17.py"', '"scripts/run-rc6-real-impact-fractions-threshold-data-comparison-c19.py"', "runner", 1),
        ('"specs/ai-native-studio-rc6-real-impact-cfl-data-comparison-c17.v1.00.json"', '"specs/ai-native-studio-rc6-real-impact-fractions-threshold-data-comparison-c19.v1.03.json"', "spec", 1),
        ("attempt88", "attempt90", "C18 result keys", 17),
        ("ATTEMPT88", "ATTEMPT90", "C18 result constant", 8),
        ('"MEASURED_CFL_DATA_MESH_COMPARISON"', '"MEASURED_FRACTIONS_THRESHOLD_DATA_MESH_COMPARISON"', "result status", 1),
        ('"bfs.rc6RealImpactC16DataComparisonC17IndependentAudit.v0.1"', '"bfs.rc6RealImpactFractionsThresholdDataComparisonC19IndependentAudit.v0.1"', "audit schema", 1),
        ("RC6_REAL_IMPACT_C16_DATA_COMPARISON_C17_AUDIT=", "RC6_REAL_IMPACT_FRACTIONS_THRESHOLD_DATA_COMPARISON_C19_AUDIT=", "audit marker", 1),
        ("C17 independent audit failed", "C19 independent audit failed", "failure marker", 1),
    )
    for before, after, label, expected in replacements:
        if source.count(before) != expected:
            raise RuntimeError(f"C19 auditor {label} target mismatch")
        source = source.replace(before, after)
    constant_anchor = 'C15_ROOT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-c14-transition-c15-attempt-87"\n'
    constant_extension = constant_anchor + 'C18_C1_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-fractions-threshold-c18-audit-c1-attempt-91/audit.json"\n'
    load_anchor = 'attempt90_audit = json.loads((ATTEMPT90_ROOT / "independent-audit.json").read_text())\n'
    load_extension = load_anchor + 'c18_c1_audit = json.loads(C18_C1_AUDIT.read_text())\n'
    evidence_anchor = 'and attempt90_audit["auditHash"] == spec["baseline"]["attempt90AuditHash"] and attempt90_audit["status"] == "PASS"'
    evidence_extension = 'and attempt90_audit["auditHash"] == spec["baseline"]["attempt90AuditHash"] and attempt90_audit["status"] == "FAIL" and sha(C18_C1_AUDIT) == spec["baseline"]["attempt90C1AuditFileSha256"] and c18_c1_audit["auditHash"] == spec["baseline"]["attempt90C1AuditHash"] and c18_c1_audit["status"] == "PASS_AUDIT_ONLY_PHYSICAL_FAIL_RETAINED"'
    for before, after, label in ((constant_anchor, constant_extension, "C1 constant"), (load_anchor, load_extension, "C1 load"), (evidence_anchor, evidence_extension, "C1 evidence status")):
        if source.count(before) != 1:
            raise RuntimeError(f"C19 auditor {label} target mismatch")
        source = source.replace(before, after)
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#RC6_REAL_IMPACT_FRACTIONS_THRESHOLD_DATA_COMPARISON_C19", "exec"), globals(), globals())
