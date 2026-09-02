#!/usr/bin/env python3
"""Copy immutable C20 cache and compare its Data/Mesh onset with C18."""

import hashlib
import importlib.util
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-real-impact-fractions-threshold-data-comparison-c19.py")
EXPECTED_BASE_SHA256 = "163251a256075718fb175c896427afa59589a512be165a27d8d7158856935211"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("C21 runner base identity mismatch")
    module_spec = importlib.util.spec_from_file_location("rc6_c19_runner_base", BASE)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    source = module.transformed_source()
    replacements = (
        ('"""Copy immutable C18 cache and compare its Data/Mesh transition with C14."""', '"""Copy immutable C20 cache and compare its Data/Mesh onset and amplitude with C18."""', "docstring", 1),
        ("RC6-2026-09-02-real-impact-fractions-threshold-data-comparison-c19-attempt-92", "RC6-2026-09-02-real-impact-particle-radius-data-comparison-c21-attempt-99", "fresh roots", 2),
        ("RC6-2026-09-02-real-impact-liquid-fractions-threshold-c18-attempt-90", "RC6-2026-09-02-real-impact-liquid-particle-radius-c20-c1-attempt-94", "C20 cache/evidence", 2),
        ('C15_ROOT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-c14-transition-c15-attempt-87"', 'C19_ROOT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-fractions-threshold-data-comparison-c19-attempt-92"', "C19 root", 1),
        ('C18_C1_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-fractions-threshold-c18-audit-c1-attempt-91/audit.json"', 'C20_C5_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-particle-radius-c20-c5-audit-attempt-98/audit.json"', "C20 C5 audit", 1),
        ('"scripts/analyze-rc6-real-impact-fractions-threshold-data-comparison-c19.py"', '"scripts/analyze-rc6-real-impact-particle-radius-data-comparison-c21.py"', "analyzer", 1),
        ('"scripts/audit-rc6-real-impact-fractions-threshold-data-comparison-c19.py"', '"scripts/audit-rc6-real-impact-particle-radius-data-comparison-c21.py"', "auditor", 1),
        ('"specs/ai-native-studio-rc6-real-impact-fractions-threshold-data-comparison-c19.v1.03.json"', '"specs/ai-native-studio-rc6-real-impact-particle-radius-data-comparison-c21.v1.10.json"', "spec", 1),
        ("attempt90", "attempt94", "C20 result keys", 8),
        ("ATTEMPT90", "ATTEMPT94", "C20 result constant", 5),
        ("C15_ROOT", "C19_ROOT", "C19 constant uses", 4),
        ("c15", "c19", "C19 baseline keys", 4),
        ("C15", "C21", "C21 diagnostics", 16),
        ("C18_C1_AUDIT", "C20_C5_AUDIT", "C20 audit uses", 2),
        ("c18_c1_audit", "c20_c5_audit", "C20 audit value", 3),
        ("attempt94C1", "attempt94C5", "C20 C5 baseline keys", 2),
        ('"PASS_AUDIT_ONLY_PHYSICAL_FAIL_RETAINED"', '"PASS"', "C20 C5 audit status", 1),
        ('"bfs.rc6RealImpactFractionsThresholdDataComparisonC19Admission.v0.1"', '"bfs.rc6RealImpactParticleRadiusDataComparisonC21Admission.v0.1"', "admission schema", 1),
        ('"bfs.rc6RealImpactFractionsThresholdDataComparisonC19Receipt.v0.1"', '"bfs.rc6RealImpactParticleRadiusDataComparisonC21Receipt.v0.1"', "receipt schema", 1),
        ('"MEASURED_FRACTIONS_THRESHOLD_DATA_MESH_COMPARISON"', '"MEASURED_PARTICLE_RADIUS_DATA_MESH_COMPARISON"', "result status", 1),
        ("RC6_REAL_IMPACT_FRACTIONS_THRESHOLD_DATA_COMPARISON_C19=", "RC6_REAL_IMPACT_PARTICLE_RADIUS_DATA_COMPARISON_C21=", "analyzer marker", 1),
        ("RC6_REAL_IMPACT_FRACTIONS_THRESHOLD_DATA_COMPARISON_C19_RUN=", "RC6_REAL_IMPACT_PARTICLE_RADIUS_DATA_COMPARISON_C21_RUN=", "runner marker", 1),
    )
    for before, after, label, expected in replacements:
        if source.count(before) != expected:
            raise RuntimeError(f"C21 runner {label} target mismatch: {source.count(before)} != {expected}")
        source = source.replace(before, after)
    constant_anchor = 'C20_C5_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-particle-radius-c20-c5-audit-attempt-98/audit.json"\n'
    constant_extension = constant_anchor + 'C20_C5_RECEIPT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-particle-radius-c20-c5-audit-attempt-98/receipt.json"\n'
    path_anchor = '    C20_C5_AUDIT: spec["baseline"]["attempt94C5AuditFileSha256"],\n'
    path_extension = path_anchor + '    C20_C5_RECEIPT: spec["baseline"]["attempt94C5ReceiptFileSha256"],\n'
    load_anchor = 'c20_c5_audit = json.loads(C20_C5_AUDIT.read_text())\n'
    load_extension = load_anchor + 'c20_c5_receipt = json.loads(C20_C5_RECEIPT.read_text())\n'
    status_anchor = 'if c20_c5_audit["status"] != "PASS" or c20_c5_audit["auditHash"] != spec["baseline"]["attempt94C5AuditHash"]:\n    raise RuntimeError("C19 C18 C1 audit binding mismatch")\n'
    status_extension = 'if c20_c5_audit["status"] != "PASS" or c20_c5_audit["auditHash"] != spec["baseline"]["attempt94C5AuditHash"] or c20_c5_receipt["status"] != "PASS" or c20_c5_receipt["receiptHash"] != spec["baseline"]["attempt94C5ReceiptHash"]:\n    raise RuntimeError("C21 C20 C5 closure binding mismatch")\n'
    freeze_anchor = 'tool_hashes = {row["uri"]: row["sha256"] for row in spec["tools"]}\n'
    freeze_extension = '''head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.strip()
parent = subprocess.run(["git", "rev-parse", "HEAD^"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.strip()
freeze_paths = set(subprocess.run(["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.splitlines())
if parent != spec["researchParentBeforePreregistration"] or freeze_paths != set(spec["freezePaths"]):
    raise RuntimeError("C21 freeze commit mismatch")
''' + freeze_anchor
    receipt_head_old = '"researchExecutionCommit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.strip(),'
    receipt_head_new = '"researchExecutionCommit": head,'
    for before, after, label in (
        (constant_anchor, constant_extension, "C5 receipt constant"),
        (path_anchor, path_extension, "C5 receipt hash"),
        (load_anchor, load_extension, "C5 receipt load"),
        (status_anchor, status_extension, "C5 closure status"),
        (freeze_anchor, freeze_extension, "freeze commit"),
        (receipt_head_old, receipt_head_new, "receipt execution commit"),
    ):
        if source.count(before) != 1:
            raise RuntimeError(f"C21 runner {label} target mismatch: {source.count(before)}")
        source = source.replace(before, after)
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#RC6_REAL_IMPACT_PARTICLE_RADIUS_DATA_COMPARISON_C21", "exec"), globals(), globals())
