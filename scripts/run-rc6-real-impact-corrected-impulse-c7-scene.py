#!/usr/bin/env python3
"""C7 scene adapter: one faster impulse on the corrected 2 mm cup margin."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-real-impact-cup-margin-c6-scene.py")
EXPECTED_BASE_SHA256 = "9fa06814f56eaf366584e8223bc992b00e02a2de7317d076b78395d43127a171"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("real-impact C7 scene base identity mismatch")
source = BASE.read_text(encoding="utf-8")
replacements = (
    ('DRIVE_ENDS = {"M02": 9}', 'DRIVE_ENDS = {"S08": 8}', 1, "single impulse cell"),
    ("C6 I09 scene adapter", "C7 corrected-margin I08 scene adapter", 1, "description"),
    ("#C6_CUP_MARGIN_2MM", "#C7_CORRECTED_MARGIN_I08", 1, "compile identity"),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"real-impact C7 scene {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#C7_CORRECTED_MARGIN_I08", "exec"), globals(), globals())
