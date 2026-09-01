#!/usr/bin/env python3
"""C2 host adapter binding the retained attempt-02 failure and fresh attempt-03 roots."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-fluid-consequence-feasibility-c1.py")
EXPECTED_BASE_SHA256 = "21a7f80ef03e3f0d1f474a002891e0af31e376e1f3c0835792610fdd9b81f976"
digest = hashlib.sha256(BASE.read_bytes()).hexdigest()
if digest != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 C2 base host tool identity mismatch")

source = BASE.read_text(encoding="utf-8")
patches = (
    ("RC6-2026-09-01-feasibility-attempt-02", "RC6-2026-09-01-feasibility-attempt-03", 2),
    ("run-rc6-fluid-consequence-scene-c1.py", "run-rc6-fluid-consequence-scene-c2.py", 1),
    (
        '        "retainedAttempt01FailureAuditHash": "864aa40aad30c38f54c71a26898ed84e8d209ef88b8068a08556f1b195ecb7df",',
        '        "retainedAttempt01FailureAuditHash": "864aa40aad30c38f54c71a26898ed84e8d209ef88b8068a08556f1b195ecb7df",\n'
        '        "retainedAttempt02FailureAuditHash": "263e10cf8a8362056456b02f66dceec8dbfbd2d641b181abf3975ceed0f6b467",',
        1,
    ),
)
for before, after, expected_count in patches:
    if source.count(before) != expected_count:
        raise RuntimeError("RC6 C2 host correction target count mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#C2_ATTEMPT03", "exec"), globals(), globals())
