#!/usr/bin/env python3
"""Copy immutable C26 cache and compare its Data/Mesh response with C18."""

import hashlib
import importlib.util
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-real-impact-particle-radius-data-comparison-c21.py")
EXPECTED_BASE_SHA256 = "5f44c415e959d637d90704df10a076b0e3062ec95718f8fed184cc412f1e3289"


def replace_exact(source, before, after, label, expected=1):
    count = source.count(before)
    if count != expected:
        raise RuntimeError(f"C27 runner {label} target mismatch: {count} != {expected}")
    return source.replace(before, after)


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("C27 runner base identity mismatch")
    module_spec = importlib.util.spec_from_file_location("rc6_c21_runner_base", BASE)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    source = module.transformed_source()

    source = replace_exact(source, "RC6-2026-09-02-real-impact-particle-radius-data-comparison-c21-attempt-99", "RC6-2026-09-02-real-impact-water-diffusion-data-comparison-c27-attempt-107", "fresh roots", 2)
    source = replace_exact(source, "RC6-2026-09-02-real-impact-liquid-particle-radius-c20-c1-attempt-94", "RC6-2026-09-02-real-impact-liquid-water-diffusion-c26-attempt-104", "C26 cache/evidence", 2)
    source = replace_exact(source, 'C20_C5_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-particle-radius-c20-c5-audit-attempt-98/audit.json"', 'C26_C2_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-water-diffusion-c26-audit-c2-attempt-106/audit.json"', "C26 C2 audit constant")
    source = replace_exact(source, 'C20_C5_RECEIPT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-particle-radius-c20-c5-audit-attempt-98/receipt.json"\n', "", "remove inapplicable C5 receipt")
    source = replace_exact(source, '    C20_C5_AUDIT: spec["baseline"]["attempt94C5AuditFileSha256"],\n', '    C26_C2_AUDIT: spec["baseline"]["attempt104C2AuditFileSha256"],\n', "C2 audit hash field")
    source = replace_exact(source, '    C20_C5_RECEIPT: spec["baseline"]["attempt94C5ReceiptFileSha256"],\n', "", "remove C5 receipt hash field")
    source = replace_exact(source, 'c20_c5_audit = json.loads(C20_C5_AUDIT.read_text())\n', 'c26_c2_audit = json.loads(C26_C2_AUDIT.read_text())\n', "C2 audit load")
    source = replace_exact(source, 'c20_c5_receipt = json.loads(C20_C5_RECEIPT.read_text())\n', "", "remove C5 receipt load")
    old_status = 'if c20_c5_audit["status"] != "PASS" or c20_c5_audit["auditHash"] != spec["baseline"]["attempt94C5AuditHash"] or c20_c5_receipt["status"] != "PASS" or c20_c5_receipt["receiptHash"] != spec["baseline"]["attempt94C5ReceiptHash"]:\n    raise RuntimeError("C21 C20 C5 closure binding mismatch")\n'
    new_status = 'if c26_c2_audit["status"] != "PASS_AUDIT_ONLY_PHYSICAL_FAIL_RETAINED" or c26_c2_audit["auditHash"] != spec["baseline"]["attempt104C2AuditHash"]:\n    raise RuntimeError("C27 C26 C2 closure binding mismatch")\n'
    source = replace_exact(source, old_status, new_status, "C2 closure status")

    replacements = (
        ("scripts/analyze-rc6-real-impact-particle-radius-data-comparison-c21.py", "scripts/analyze-rc6-real-impact-water-diffusion-data-comparison-c27.py", "analyzer path", 1),
        ("scripts/audit-rc6-real-impact-particle-radius-data-comparison-c21.py", "scripts/audit-rc6-real-impact-water-diffusion-data-comparison-c27.py", "auditor path", 1),
        ("specs/ai-native-studio-rc6-real-impact-particle-radius-data-comparison-c21.v1.10.json", "specs/ai-native-studio-rc6-real-impact-water-diffusion-data-comparison-c27.v1.18.json", "spec path", 1),
        ("ATTEMPT94", "ATTEMPT104", "attempt constant", 5),
        ("attempt94", "attempt104", "attempt fields", 6),
        ("C20", "C26", "experiment labels", 1),
        ("c20", "c26", "experiment variables", 0),
        ("C21", "C27", "diagnostic labels", 21),
        ("c21", "c27", "diagnostic paths", 0),
        ("PARTICLE_RADIUS", "WATER_DIFFUSION", "status tokens", 3),
        ("ParticleRadius", "WaterDiffusion", "schema tokens", 2),
    )
    for before, after, label, expected in replacements:
        source = replace_exact(source, before, after, label, expected)
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#RC6_REAL_IMPACT_WATER_DIFFUSION_DATA_COMPARISON_C27", "exec"), globals(), globals())
