#!/usr/bin/env python3
"""Change only moving-cup effector distance from 2.5 to 2.0 cells."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-moving-liquid-preview-scene.py")
EXPECTED_BASE_SHA256 = "ac6531b62b0c329d69dd969f650f6b2345199343f803d1ee63dae11813237a36"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("moving-liquid effector-distance scene base identity mismatch")


source = BASE.read_text(encoding="utf-8")
replacements = [
    ("effector.surface_distance = 2.5", "effector.surface_distance = 2.0", "effector assignment"),
    ('"cupEffectorSurfaceDistanceCells": 2.5,', '"cupEffectorSurfaceDistanceCells": 2.0,', "receipt setting"),
    ("and effector.subframes == 1,", "and abs(effector.surface_distance - 2.0) <= 1e-6 and effector.subframes == 1,", "configuration check"),
    ("bfs.rc6MovingLiquidPreviewResult.v0.1", "bfs.rc6MovingLiquidEffectorDistanceResult.v0.1", "schema"),
    ("RC6_MOVING_LIQUID_PREVIEW=", "RC6_MOVING_LIQUID_EFFECTOR_DISTANCE=", "marker"),
    (
        "One 24-frame Preview-96 moving-liquid gate on the exact accepted C5F96 slow trajectory; no full tip, spill, impact, persistence, render or film-quality claim.",
        "One 24-frame Preview-96 single-variable effector-distance test on exact C5F96 motion; no full tip, spill, impact, persistence, render or film-quality claim.",
        "claim ceiling",
    ),
]
for before, after, label in replacements:
    if source.count(before) != 1:
        raise RuntimeError(f"moving-liquid effector-distance {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#MOVING_LIQUID_EFFECTOR_DISTANCE_V01", "exec"), globals(), globals())
