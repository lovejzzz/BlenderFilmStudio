#!/usr/bin/env python3
"""RC6 F7 host adapter binding F6 visual rejection and fresh attempt-11 roots."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-fluid-consequence-feasibility-f6.py")
EXPECTED_BASE_SHA256 = "20237deb2fe4f7ca3320303a866b80b17c7bb25376d5f70bcc5c822fef6201f7"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 F7 base host identity mismatch")

source = BASE.read_text(encoding="utf-8")
patches = (
    (
        "experiments/physical-richness/RC6-2026-09-01-feasibility-attempt-09/failure-audit.json",
        "experiments/physical-richness/RC6-2026-09-01-feasibility-attempt-10/failure-audit.json",
        1,
    ),
    (
        "67242f932c447bee7579ea8986f8b147c27428f6ffaa2475eb8dd562d92e6565",
        "6bde325e66c11d8b8f58d67648afe99b43df3f8489e9a6112edf8c0e5d07498e",
        1,
    ),
    ("RC6-2026-09-01-feasibility-attempt-10", "RC6-2026-09-01-feasibility-attempt-11", 1),
    ("run-rc6-fluid-consequence-scene-f6.py", "run-rc6-fluid-consequence-scene-f7.py", 1),
)
for before, after, expected_count in patches:
    if source.count(before) != expected_count:
        raise RuntimeError("RC6 F7 host routing target count mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#F7_ATTEMPT11", "exec"), globals(), globals())
