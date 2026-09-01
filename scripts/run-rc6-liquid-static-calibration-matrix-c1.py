#!/usr/bin/env python3
"""C1: bind v0.14 preflight failure and route unchanged matrix to attempt 15."""

import hashlib
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
BASE = Path(__file__).resolve().with_name("run-rc6-liquid-static-calibration-matrix.py")
EXPECTED_BASE_SHA256 = "5a90b25ae55db94bde4882a9c194388bf87fbb24c8960e3b929bd9db4e3cf9e0"
FAILURE_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-01-static-calibration-attempt-14/failure-audit.json"
EXPECTED_FAILURE_AUDIT_SHA256 = "80fc52daeb18cd0f6159acc31fe3c7ff2a099b9b26fab5a346fc97244755d1da"


def file_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


if file_sha(BASE) != EXPECTED_BASE_SHA256:
    raise RuntimeError("static calibration C1 base identity mismatch")
if file_sha(FAILURE_AUDIT) != EXPECTED_FAILURE_AUDIT_SHA256:
    raise RuntimeError("static calibration C1 retained failure identity mismatch")

source = BASE.read_text(encoding="utf-8")
old_root = "RC6-2026-09-01-static-calibration-attempt-14"
new_root = "RC6-2026-09-01-static-calibration-attempt-15"
if source.count(old_root) != 2:
    raise RuntimeError("static calibration C1 root targets are not exact")
source = source.replace(old_root, new_root)
old_spec = "ai-native-studio-rc6-liquid-static-calibration.v0.14.json"
new_spec = "ai-native-studio-rc6-liquid-static-calibration-c1.v0.15.json"
if source.count(old_spec) != 1:
    raise RuntimeError("static calibration C1 spec target is not exact")
source = source.replace(old_spec, new_spec)
exec(compile(source, str(BASE) + "#C1_ATTEMPT15", "exec"), globals(), globals())
