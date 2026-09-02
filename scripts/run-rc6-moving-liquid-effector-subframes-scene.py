#!/usr/bin/env python3
"""Change only moving-cup effector subframes from 1 to 2 on the 2.0-cell baseline."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-moving-liquid-preview-scene.py")
EXPECTED_BASE_SHA256 = "ac6531b62b0c329d69dd969f650f6b2345199343f803d1ee63dae11813237a36"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("moving-liquid effector-subframes scene base identity mismatch")
    source = BASE.read_text(encoding="utf-8")
    replacements = [
        ("effector.surface_distance = 2.5", "effector.surface_distance = 2.0", "effector distance"),
        ("effector.subframes = 1", "effector.subframes = 2", "effector subframes"),
        ('"cupEffectorSurfaceDistanceCells": 2.5,', '"cupEffectorSurfaceDistanceCells": 2.0,', "distance receipt"),
        ('"cupEffectorSubframes": 1,', '"cupEffectorSubframes": 2,', "subframes receipt"),
        ("and effector.subframes == 1,", "and abs(effector.surface_distance - 2.0) <= 1e-6 and effector.subframes == 2,", "configuration check"),
        ("bfs.rc6MovingLiquidPreviewResult.v0.1", "bfs.rc6MovingLiquidEffectorSubframesResult.v0.1", "schema"),
        ("RC6_MOVING_LIQUID_PREVIEW=", "RC6_MOVING_LIQUID_EFFECTOR_SUBFRAMES=", "marker"),
        (
            "One 24-frame Preview-96 moving-liquid gate on the exact accepted C5F96 slow trajectory; no full tip, spill, impact, persistence, render or film-quality claim.",
            "One 24-frame Preview-96 single-variable effector-subframes test on exact C5F96 motion at 2.0-cell distance; no full tip, spill, impact, persistence, render or film-quality claim.",
            "claim ceiling",
        ),
    ]
    for before, after, label in replacements:
        if source.count(before) != 1:
            raise RuntimeError(f"moving-liquid effector-subframes {label} target mismatch")
        source = source.replace(before, after)
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#MOVING_LIQUID_EFFECTOR_SUBFRAMES_V01", "exec"), globals(), globals())
