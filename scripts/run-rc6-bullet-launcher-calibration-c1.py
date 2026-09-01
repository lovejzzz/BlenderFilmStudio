#!/usr/bin/env python3
"""C1 calibration adapter: remove lane overlap and gate airborne/lateral false positives."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-bullet-launcher-calibration.py")
EXPECTED_BASE_SHA256 = "26aea9a40e521b8c2c58f7ffbe047ef03f5b4ebc0be50a887e28564c31bb7154"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 calibration C1 base identity mismatch")

source = BASE.read_text(encoding="utf-8")
replacements = (
    (
        '    lane = add_cube("BALL_LANE", (-0.42, 0.0, 0.05), (0.70, 0.22, 0.05))',
        '    lane = add_cube("BALL_LANE", (-0.55, 0.0, 0.05), (0.57, 0.22, 0.05))',
        "lane clearance",
    ),
    (
        '        if contact is None and (gap <= 0.01 or cup_tilt >= 1.0):',
        '        if contact is None and gap <= 0.01:',
        "contact definition",
    ),
    (
        '''    cup_x = max(abs(row["cup"][0]) for row in samples)
    cup_min_z = min(row["cup"][2] for row in samples)''',
        '''    cup_x = max(abs(row["cup"][0]) for row in samples)
    cup_y = max(abs(row["cup"][1]) for row in samples)
    cup_min_z = min(row["cup"][2] for row in samples)
    cup_max_z = max(row["cup"][2] for row in samples)''',
        "bounded motion measurements",
    ),
    (
        '''        "cupDoesNotFall": cup_min_z >= 0.08,
        "ballUnanimated": ball.animation_data is None,''',
        '''        "cupDoesNotFall": cup_min_z >= 0.08,
        "cupDoesNotLift": cup_max_z <= 0.45,
        "cupStaysNearLaneY": cup_y <= 0.25,
        "ballUnanimated": ball.animation_data is None,''',
        "bounded motion gates",
    ),
    (
        '''        "maximumAbsoluteCupX": round(cup_x, 7),
        "minimumCupZ": round(cup_min_z, 7),''',
        '''        "maximumAbsoluteCupX": round(cup_x, 7),
        "maximumAbsoluteCupY": round(cup_y, 7),
        "minimumCupZ": round(cup_min_z, 7),
        "maximumCupZ": round(cup_max_z, 7),''',
        "bounded motion receipts",
    ),
)
for before, after, label in replacements:
    if source.count(before) != 1:
        raise RuntimeError(f"RC6 calibration C1 {label} target is not unique")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#C1_NO_OVERLAP_AND_BOUNDED_CUP", "exec"), globals(), globals())
