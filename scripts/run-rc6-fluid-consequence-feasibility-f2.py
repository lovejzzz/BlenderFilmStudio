#!/usr/bin/env python3
"""RC6 F2 host adapter binding F1 failure and fresh attempt-06 roots."""

import hashlib
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
BASE = Path(__file__).resolve().with_name("run-rc6-fluid-consequence-feasibility-c4.py")
EXPECTED_BASE_SHA256 = "8303a90ac33076b78b40c73b3a1b0f99434b5ca369b920ccb837166b381e5665"
FAILURE_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-01-feasibility-attempt-05/failure-audit.json"
EXPECTED_FAILURE_AUDIT_FILE_SHA256 = "2ee61761764e5d803246ce5eb0e7f130b2fc30cef815a7db6ce529395819604d"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 F2 base host adapter identity mismatch")
if hashlib.sha256(FAILURE_AUDIT.read_bytes()).hexdigest() != EXPECTED_FAILURE_AUDIT_FILE_SHA256:
    raise RuntimeError("RC6 F2 retained attempt-05 audit identity mismatch")

source = BASE.read_text(encoding="utf-8")
patches = (
    ("RC6-2026-09-01-feasibility-attempt-05", "RC6-2026-09-01-feasibility-attempt-06", 1),
    ("run-rc6-fluid-consequence-scene-c4.py", "run-rc6-fluid-consequence-scene-f2.py", 1),
)
for before, after, expected_count in patches:
    if source.count(before) != expected_count:
        raise RuntimeError("RC6 F2 host routing target count mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#F2_ATTEMPT06", "exec"), globals(), globals())
