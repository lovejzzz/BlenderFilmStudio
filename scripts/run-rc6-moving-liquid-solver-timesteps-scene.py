#!/usr/bin/env python3
"""Change only fluid-domain minimum timesteps from 1 to 2 on attempt-59 physics."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-moving-liquid-preview-scene.py")
EXPECTED_BASE_SHA256 = "ac6531b62b0c329d69dd969f650f6b2345199343f803d1ee63dae11813237a36"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("moving-liquid solver-timesteps scene base identity mismatch")
    source = BASE.read_text(encoding="utf-8")
    replacements = [
        ("settings.timesteps_min = 1", "settings.timesteps_min = 2", "minimum timesteps"),
        ("effector.surface_distance = 2.5", "effector.surface_distance = 2.0", "effector distance baseline"),
        ('"cupEffectorSurfaceDistanceCells": 2.5,', '"cupEffectorSurfaceDistanceCells": 2.0,', "distance receipt"),
        (
            '"cupEffectorSubframes": 1,',
            '"cupEffectorSubframes": 1,\n        "timestepsMin": 2,\n        "timestepsMax": 4,\n        "cflCondition": 2.0,',
            "solver receipt fields",
        ),
        (
            "and effector.subframes == 1,",
            "and abs(effector.surface_distance - 2.0) <= 1e-6 and effector.subframes == 1 and settings.timesteps_min == 2 and settings.timesteps_max == 4 and abs(settings.cfl_condition - 2.0) <= 1e-6,",
            "configuration check",
        ),
        ("bfs.rc6MovingLiquidPreviewResult.v0.1", "bfs.rc6MovingLiquidSolverTimestepsResult.v0.1", "schema"),
        ("RC6_MOVING_LIQUID_PREVIEW=", "RC6_MOVING_LIQUID_SOLVER_TIMESTEPS=", "marker"),
        (
            "One 24-frame Preview-96 moving-liquid gate on the exact accepted C5F96 slow trajectory; no full tip, spill, impact, persistence, render or film-quality claim.",
            "One 24-frame Preview-96 single-variable minimum-solver-timesteps test on exact C5F96 motion at 2.0-cell distance and one effector subframe; no full tip, spill, impact, persistence, render or film-quality claim.",
            "claim ceiling",
        ),
    ]
    for before, after, label in replacements:
        if source.count(before) != 1:
            raise RuntimeError(f"moving-liquid solver-timesteps {label} target mismatch")
        source = source.replace(before, after)
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#MOVING_LIQUID_SOLVER_TIMESTEPS_V01", "exec"), globals(), globals())
