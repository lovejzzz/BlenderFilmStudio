#!/usr/bin/env python3
"""RC6 F3 host adapter binding accepted calibration and fresh attempt-07 roots."""

import hashlib
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
BASE = Path(__file__).resolve().with_name("run-rc6-fluid-consequence-feasibility-f2.py")
EXPECTED_BASE_SHA256 = "d52e1d3d4e932364224b98dde8bd5715472de2faa27cc141fd58cc6d0df6a2c3"
CALIBRATION_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-01-bullet-launcher-calibration-attempt-03/acceptance-audit.json"
EXPECTED_CALIBRATION_AUDIT_FILE_SHA256 = "bee9a42708a47ffd2161ccf818146ef1c9fa0112a7de0ac90a917afea9a93ab0"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 F3 base host identity mismatch")
if hashlib.sha256(CALIBRATION_AUDIT.read_bytes()).hexdigest() != EXPECTED_CALIBRATION_AUDIT_FILE_SHA256:
    raise RuntimeError("RC6 F3 calibration audit identity mismatch")

source = BASE.read_text(encoding="utf-8")
patches = (
    ("RC6-2026-09-01-feasibility-attempt-06", "RC6-2026-09-01-feasibility-attempt-07", 1),
    ("run-rc6-fluid-consequence-scene-f2.py", "run-rc6-fluid-consequence-scene-f3.py", 1),
)
for before, after, expected_count in patches:
    if source.count(before) != expected_count:
        raise RuntimeError("RC6 F3 host routing target count mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#F3_ATTEMPT07", "exec"), globals(), globals())
