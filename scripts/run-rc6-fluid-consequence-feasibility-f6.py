#!/usr/bin/env python3
"""RC6 F6 host adapter binding F5 failure and fresh attempt-10 roots."""

import hashlib
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
BASE = Path(__file__).resolve().with_name("run-rc6-fluid-consequence-feasibility-f5.py")
EXPECTED_BASE_SHA256 = "0e13ea1e444cbf3a12150bb69265e5622419df6441da391b992cc3a09d6e8f48"
FAILURE_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-01-feasibility-attempt-09/failure-audit.json"
EXPECTED_FAILURE_AUDIT_FILE_SHA256 = "67242f932c447bee7579ea8986f8b147c27428f6ffaa2475eb8dd562d92e6565"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 F6 base host identity mismatch")
if hashlib.sha256(FAILURE_AUDIT.read_bytes()).hexdigest() != EXPECTED_FAILURE_AUDIT_FILE_SHA256:
    raise RuntimeError("RC6 F6 retained F5 audit identity mismatch")
source = BASE.read_text(encoding="utf-8")
patches = (
    ("RC6-2026-09-01-feasibility-attempt-09", "RC6-2026-09-01-feasibility-attempt-10", 1),
    ("run-rc6-fluid-consequence-scene-f5.py", "run-rc6-fluid-consequence-scene-f6.py", 1),
)
for before, after, expected_count in patches:
    if source.count(before) != expected_count:
        raise RuntimeError("RC6 F6 host routing target count mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#F6_ATTEMPT10", "exec"), globals(), globals())
