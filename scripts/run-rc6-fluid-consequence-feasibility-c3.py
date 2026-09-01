#!/usr/bin/env python3
"""C3 host adapter binding attempt-03 and routing to fresh attempt-04 roots."""

import hashlib
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
BASE = Path(__file__).resolve().with_name("run-rc6-fluid-consequence-feasibility-c2.py")
EXPECTED_BASE_SHA256 = "f8af3143b14cb26e7ea736626e371db67d47b85eb2d0387c939f21d4faa60f26"
FAILURE_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-01-feasibility-attempt-03/failure-audit.json"
EXPECTED_FAILURE_AUDIT_FILE_SHA256 = "23d015facd1bfafd51780dacb855598b3256004d3934466a2f5d3a9612377b4b"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 C3 base host adapter identity mismatch")
if hashlib.sha256(FAILURE_AUDIT.read_bytes()).hexdigest() != EXPECTED_FAILURE_AUDIT_FILE_SHA256:
    raise RuntimeError("RC6 C3 retained attempt-03 audit identity mismatch")

source = BASE.read_text(encoding="utf-8")
patches = (
    ("RC6-2026-09-01-feasibility-attempt-03", "RC6-2026-09-01-feasibility-attempt-04", 1),
    ("run-rc6-fluid-consequence-scene-c2.py", "run-rc6-fluid-consequence-scene-c3.py", 1),
)
for before, after, expected_count in patches:
    if source.count(before) != expected_count:
        raise RuntimeError("RC6 C3 host correction target count mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#C3_ATTEMPT04", "exec"), globals(), globals())
