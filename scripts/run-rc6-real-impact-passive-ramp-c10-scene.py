#!/usr/bin/env python3
"""C10 adapter reducing only passive ramp rise from 60 mm to 40 mm."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-real-impact-passive-ramp-c9-scene.py")
EXPECTED_BASE_SHA256 = "274327e06de7d9d8c6d5164c4acdd8fd121b92a8843f6ca5a895dd1b6d249afb"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("real-impact C10 scene base identity mismatch")
source = BASE.read_text(encoding="utf-8")
replacements = (
    ("C9 I09 scene adapter", "C10 I09 scene adapter", 1, "description"),
    ('DRIVE_ENDS = {"R60": 9}', 'DRIVE_ENDS = {"R40": 9}', 1, "cell"),
    ("(0.04, -0.20, 0.28)", "(0.04, -0.20, 0.26)", 1, "negative-y ramp end"),
    ("(0.04, 0.20, 0.28)", "(0.04, 0.20, 0.26)", 1, "positive-y ramp end"),
    ('"rampSurfaceEndZ": 0.28', '"rampSurfaceEndZ": 0.26', 1, "surface end"),
    ('"rampRiseMeters": 0.06', '"rampRiseMeters": 0.04', 1, "rise"),
    ("math.atan2(0.06, 0.30)", "math.atan2(0.04, 0.30)", 1, "angle"),
    ("#C9_PASSIVE_RAMP_60MM", "#C10_PASSIVE_RAMP_40MM", 1, "compile identity"),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"real-impact C10 scene {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#C10_PASSIVE_RAMP_40MM", "exec"), globals(), globals())
