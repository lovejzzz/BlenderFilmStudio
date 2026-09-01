#!/usr/bin/env python3
"""C4 host adapter binding attempt-04 and routing to fresh attempt-05 roots."""

import hashlib
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
BASE = Path(__file__).resolve().with_name("run-rc6-fluid-consequence-feasibility-c3.py")
EXPECTED_BASE_SHA256 = "6ac233931b6753ba9daac31b943b2d1c516c8d4e35409be21b206bb962759059"
FAILURE_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-01-feasibility-attempt-04/failure-audit.json"
EXPECTED_FAILURE_AUDIT_FILE_SHA256 = "50c0d1bdcaa501971fc23c266339c9125d519299a54d487860bfa1467e96768b"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 C4 base host adapter identity mismatch")
if hashlib.sha256(FAILURE_AUDIT.read_bytes()).hexdigest() != EXPECTED_FAILURE_AUDIT_FILE_SHA256:
    raise RuntimeError("RC6 C4 retained attempt-04 audit identity mismatch")

source = BASE.read_text(encoding="utf-8")
patches = (
    ("RC6-2026-09-01-feasibility-attempt-04", "RC6-2026-09-01-feasibility-attempt-05", 1),
    ("run-rc6-fluid-consequence-scene-c3.py", "run-rc6-fluid-consequence-scene-c4.py", 1),
)
for before, after, expected_count in patches:
    if source.count(before) != expected_count:
        raise RuntimeError("RC6 C4 host correction target count mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#C4_ATTEMPT05", "exec"), globals(), globals())
