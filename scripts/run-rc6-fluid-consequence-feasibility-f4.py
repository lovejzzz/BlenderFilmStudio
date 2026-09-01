#!/usr/bin/env python3
"""RC6 F4 host adapter binding F3 failure and fresh attempt-08 roots."""

import hashlib
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
BASE = Path(__file__).resolve().with_name("run-rc6-fluid-consequence-feasibility-f3.py")
EXPECTED_BASE_SHA256 = "2a7051d10e3bec615095ce0246a626bab324b8c46bdc9e5a78011e2a09c32dbe"
FAILURE_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-01-feasibility-attempt-07/failure-audit.json"
EXPECTED_FAILURE_AUDIT_FILE_SHA256 = "8456264179960d7a51f90deb8d8f90908589b2e3ec003cf8fb2829b17b956a86"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 F4 base host identity mismatch")
if hashlib.sha256(FAILURE_AUDIT.read_bytes()).hexdigest() != EXPECTED_FAILURE_AUDIT_FILE_SHA256:
    raise RuntimeError("RC6 F4 retained F3 failure audit identity mismatch")

source = BASE.read_text(encoding="utf-8")
patches = (
    ("RC6-2026-09-01-feasibility-attempt-07", "RC6-2026-09-01-feasibility-attempt-08", 1),
    ("run-rc6-fluid-consequence-scene-f3.py", "run-rc6-fluid-consequence-scene-f4.py", 1),
)
for before, after, expected_count in patches:
    if source.count(before) != expected_count:
        raise RuntimeError("RC6 F4 host routing target count mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#F4_ATTEMPT08", "exec"), globals(), globals())
