#!/usr/bin/env python3
"""RC6 F7 C1: correct overlapping host routing and use fresh attempt-12 roots."""

import hashlib
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
BASE = Path(__file__).resolve().with_name("run-rc6-fluid-consequence-feasibility-f7.py")
EXPECTED_BASE_SHA256 = "97359990db2cb68aabdece6de1ece6008431ae700fd213118930b0b7610d2833"
FAILURE_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-01-feasibility-attempt-11/failure-audit.json"
EXPECTED_FAILURE_AUDIT_FILE_SHA256 = "32760e1f4d6a6230a066255f052b597ddab304fef25769567f709ac1bc887eca"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 F7 C1 base host identity mismatch")
if hashlib.sha256(FAILURE_AUDIT.read_bytes()).hexdigest() != EXPECTED_FAILURE_AUDIT_FILE_SHA256:
    raise RuntimeError("RC6 F7 C1 retained attempt-11 audit identity mismatch")

source = BASE.read_text(encoding="utf-8")
old_loop = '''for before, after, expected_count in patches:
    if source.count(before) != expected_count:
        raise RuntimeError("RC6 F7 host routing target count mismatch")
    source = source.replace(before, after)'''
new_loop = '''for before, after, expected_count in patches:
    if source.count(before) != expected_count:
        raise RuntimeError("RC6 F7 C1 host routing target count mismatch")
for before, after, _expected_count in reversed(patches):
    source = source.replace(before, after)'''
if source.count(old_loop) != 1:
    raise RuntimeError("RC6 F7 C1 loop correction target is not unique")
source = source.replace(old_loop, new_loop)
old_root = '"RC6-2026-09-01-feasibility-attempt-11", 1)'
new_root = '"RC6-2026-09-01-feasibility-attempt-12", 1)'
if source.count(old_root) != 1:
    raise RuntimeError("RC6 F7 C1 fresh-root target is not unique")
source = source.replace(old_root, new_root)
exec(compile(source, str(BASE) + "#F7_C1_ATTEMPT12", "exec"), globals(), globals())
