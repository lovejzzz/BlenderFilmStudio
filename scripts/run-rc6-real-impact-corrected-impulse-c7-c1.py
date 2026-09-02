#!/usr/bin/env python3
"""C7-C1 runner with corrected C6-adapter occurrence counts."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-real-impact-cup-margin-c6.py")
EXPECTED_BASE_SHA256 = "4b02c07ed0f36b663195253a34e4c07c59bcacedd21a181389be16feae2c0647"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("real-impact C7-C1 runner base identity mismatch")
source = BASE.read_text(encoding="utf-8")
replacements = (
    ("RC6-2026-09-02-real-impact-cup-margin-c6-attempt-77", "RC6-2026-09-02-real-impact-corrected-impulse-c7-c1-attempt-79", 1, "fresh roots"),
    ('CELLS = (("M02", 9),)', 'CELLS = (("S08", 8),)', 1, "cell roster"),
    ("scripts/run-rc6-real-impact-cup-margin-c6-scene.py", "scripts/run-rc6-real-impact-corrected-impulse-c7-c1-scene.py", 1, "scene tool"),
    ("scripts/run-rc6-real-impact-cup-margin-c6.py", "scripts/run-rc6-real-impact-corrected-impulse-c7-c1.py", 1, "runner commit path"),
    ("scripts/audit-rc6-real-impact-cup-margin-c6.py", "scripts/audit-rc6-real-impact-corrected-impulse-c7-c1.py", 1, "auditor"),
    ("specs/ai-native-studio-rc6-real-impact-cup-margin-c6.v0.88.json", "specs/ai-native-studio-rc6-real-impact-corrected-impulse-c7-c1.v0.90.json", 1, "spec"),
    ("research/2026-09-02-rc6-real-impact-cup-margin-c6-preregistration.md", "research/2026-09-02-rc6-real-impact-corrected-impulse-c7-c1-preregistration.md", 1, "preregistration"),
    ("C6 runner adapter", "C7-C1 runner adapter", 1, "description"),
    ("C6_CUP_MARGIN_2MM", "C7_C1_CORRECTED_MARGIN_I08", 1, "compile identity"),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"real-impact C7-C1 runner {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#C7_C1_CORRECTED_MARGIN_I08", "exec"), globals(), globals())
