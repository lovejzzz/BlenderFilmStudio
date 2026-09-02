#!/usr/bin/env python3
"""C7-C1 auditor with corrected C6-adapter occurrence counts."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-real-impact-cup-margin-c6.py")
EXPECTED_BASE_SHA256 = "497d74fe2e3ef29b17fceb6c7284f741296ddd9570c614e024f5addb9e3e5a90"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("real-impact C7-C1 auditor base identity mismatch")
source = BASE.read_text(encoding="utf-8")
replacements = (
    ("RC6-2026-09-02-real-impact-cup-margin-c6-attempt-77", "RC6-2026-09-02-real-impact-corrected-impulse-c7-c1-attempt-79", 1, "fresh roots"),
    ('CELLS = (("M02", 9),)', 'CELLS = (("S08", 8),)', 1, "cell roster"),
    ("scripts/run-rc6-real-impact-cup-margin-c6-scene.py", "scripts/run-rc6-real-impact-corrected-impulse-c7-c1-scene.py", 1, "scene tool"),
    ("scripts/run-rc6-real-impact-cup-margin-c6.py", "scripts/run-rc6-real-impact-corrected-impulse-c7-c1.py", 1, "runner"),
    ("scripts/audit-rc6-real-impact-cup-margin-c6.py", "scripts/audit-rc6-real-impact-corrected-impulse-c7-c1.py", 1, "auditor commit path"),
    ("specs/ai-native-studio-rc6-real-impact-cup-margin-c6.v0.88.json", "specs/ai-native-studio-rc6-real-impact-corrected-impulse-c7-c1.v0.90.json", 1, "spec"),
    ("research/2026-09-02-rc6-real-impact-cup-margin-c6-preregistration.md", "research/2026-09-02-rc6-real-impact-corrected-impulse-c7-c1-preregistration.md", 1, "preregistration"),
    ("C6 independent auditor adapter", "C7-C1 independent auditor adapter", 1, "description"),
    ("C6_CUP_MARGIN_2MM", "C7_C1_CORRECTED_MARGIN_I08", 1, "compile identity"),
    ("bfs.rc6RealImpactCupMarginC6IndependentAudit.v0.1", "bfs.rc6RealImpactCorrectedImpulseC7C1IndependentAudit.v0.1", 1, "schema"),
    ("RC6_REAL_IMPACT_CUP_MARGIN_C6_AUDIT=", "RC6_REAL_IMPACT_CORRECTED_IMPULSE_C7_C1_AUDIT=", 1, "marker"),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"real-impact C7-C1 auditor {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#C7_C1_CORRECTED_MARGIN_I08", "exec"), globals(), globals())
