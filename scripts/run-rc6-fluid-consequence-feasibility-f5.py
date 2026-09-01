#!/usr/bin/env python3
"""RC6 F5 host adapter binding attempt-08 and fresh attempt-09 roots."""

import hashlib
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
BASE = Path(__file__).resolve().with_name("run-rc6-fluid-consequence-feasibility-f4.py")
EXPECTED_BASE_SHA256 = "cce4a984ef845e166e1908dced44ff11f11c821a152e1736c95646dae597d5c7"
FAILURE_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-01-feasibility-attempt-08/failure-audit.json"
EXPECTED_FAILURE_AUDIT_FILE_SHA256 = "9381037137120621bd3eb89b8363ff916371e2e65eb5018a2c54dc957d126da3"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 F5 base host identity mismatch")
if hashlib.sha256(FAILURE_AUDIT.read_bytes()).hexdigest() != EXPECTED_FAILURE_AUDIT_FILE_SHA256:
    raise RuntimeError("RC6 F5 retained attempt-08 audit identity mismatch")
source = BASE.read_text(encoding="utf-8")
patches = (
    ("RC6-2026-09-01-feasibility-attempt-08", "RC6-2026-09-01-feasibility-attempt-09", 1),
    ("run-rc6-fluid-consequence-scene-f4.py", "run-rc6-fluid-consequence-scene-f5.py", 1),
)
for before, after, expected_count in patches:
    if source.count(before) != expected_count:
        raise RuntimeError("RC6 F5 host routing target count mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#F5_ATTEMPT09", "exec"), globals(), globals())
