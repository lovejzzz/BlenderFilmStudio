#!/usr/bin/env python3
"""Copy immutable C18 cache and compare its Data/Mesh transition with C14."""

import hashlib
import importlib.util
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-real-impact-cfl-data-comparison-c17.py")
EXPECTED_BASE_SHA256 = "568584065a324a4690b765f7f0880ca98e47886d2573cb6f1418efede20293b4"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("C19 runner base identity mismatch")
    module_spec = importlib.util.spec_from_file_location("rc6_c17_runner_base", BASE)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    source = module.transformed_source()
    replacements = (
        ('"""Copy immutable C14 cache and run one zero-Blender transition diagnosis."""', '"""Copy immutable C18 cache and compare its Data/Mesh transition with C14."""', "docstring", 1),
        ("RC6-2026-09-02-real-impact-cfl-data-comparison-c17-attempt-89", "RC6-2026-09-02-real-impact-fractions-threshold-data-comparison-c19-attempt-92", "fresh roots", 2),
        ("RC6-2026-09-02-real-impact-liquid-cfl-c16-attempt-88", "RC6-2026-09-02-real-impact-liquid-fractions-threshold-c18-attempt-90", "C18 cache/evidence", 2),
        ('"scripts/analyze-rc6-real-impact-cfl-data-comparison-c17.py"', '"scripts/analyze-rc6-real-impact-fractions-threshold-data-comparison-c19.py"', "analyzer", 1),
        ('"scripts/audit-rc6-real-impact-cfl-data-comparison-c17.py"', '"scripts/audit-rc6-real-impact-fractions-threshold-data-comparison-c19.py"', "auditor", 1),
        ('"specs/ai-native-studio-rc6-real-impact-cfl-data-comparison-c17.v1.00.json"', '"specs/ai-native-studio-rc6-real-impact-fractions-threshold-data-comparison-c19.v1.03.json"', "spec", 1),
        ("attempt88", "attempt90", "C18 result keys", 6),
        ("ATTEMPT88", "ATTEMPT90", "C18 result constant", 5),
        ('"bfs.rc6RealImpactC16DataComparisonC17Admission.v0.1"', '"bfs.rc6RealImpactFractionsThresholdDataComparisonC19Admission.v0.1"', "admission schema", 1),
        ('"bfs.rc6RealImpactC16DataComparisonC17Receipt.v0.1"', '"bfs.rc6RealImpactFractionsThresholdDataComparisonC19Receipt.v0.1"', "receipt schema", 1),
        ('"MEASURED_CFL_DATA_MESH_COMPARISON"', '"MEASURED_FRACTIONS_THRESHOLD_DATA_MESH_COMPARISON"', "result status", 1),
        ("RC6_REAL_IMPACT_C16_DATA_COMPARISON_C17=", "RC6_REAL_IMPACT_FRACTIONS_THRESHOLD_DATA_COMPARISON_C19=", "analyzer marker", 1),
        ("RC6_REAL_IMPACT_C16_DATA_COMPARISON_C17_RUN=", "RC6_REAL_IMPACT_FRACTIONS_THRESHOLD_DATA_COMPARISON_C19_RUN=", "runner marker", 1),
    )
    for before, after, label, expected in replacements:
        if source.count(before) != expected:
            raise RuntimeError(f"C19 runner {label} target mismatch")
        source = source.replace(before, after)
    constant_anchor = 'C15_ROOT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-c14-transition-c15-attempt-87"\n'
    constant_extension = constant_anchor + 'C18_C1_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-fractions-threshold-c18-audit-c1-attempt-91/audit.json"\n'
    path_anchor = '    ATTEMPT90_ROOT / "independent-audit.json": spec["baseline"]["attempt90AuditFileSha256"],\n'
    path_extension = path_anchor + '    C18_C1_AUDIT: spec["baseline"]["attempt90C1AuditFileSha256"],\n'
    admission_anchor = 'source_manifest_before = manifest(SOURCE_CACHE)\n'
    admission_extension = 'c18_c1_audit = json.loads(C18_C1_AUDIT.read_text())\nif c18_c1_audit["status"] != "PASS_AUDIT_ONLY_PHYSICAL_FAIL_RETAINED" or c18_c1_audit["auditHash"] != spec["baseline"]["attempt90C1AuditHash"]:\n    raise RuntimeError("C19 C18 C1 audit binding mismatch")\n' + admission_anchor
    for before, after, label in ((constant_anchor, constant_extension, "C1 constant"), (path_anchor, path_extension, "C1 file hash"), (admission_anchor, admission_extension, "C1 status")):
        if source.count(before) != 1:
            raise RuntimeError(f"C19 runner {label} target mismatch")
        source = source.replace(before, after)
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#RC6_REAL_IMPACT_FRACTIONS_THRESHOLD_DATA_COMPARISON_C19", "exec"), globals(), globals())
