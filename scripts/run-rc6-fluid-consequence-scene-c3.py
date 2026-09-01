#!/usr/bin/env python3
"""C3 adapter: inline Blender-version-compatible launch F-curve traversal."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-fluid-consequence-scene-c2.py")
EXPECTED_BASE_SHA256 = "3fdbaaeb6827d93c65f3722cb3a19c883b730f0b5841cb659bafc5ecd1e20d90"
digest = hashlib.sha256(BASE.read_bytes()).hexdigest()
if digest != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 C3 base scene adapter identity mismatch")

source = BASE.read_text(encoding="utf-8")
before = '''    for curve in action_fcurves(ball):
        for point in curve.keyframe_points:
            point.interpolation = "LINEAR"'''
after = '''    launch_action = ball.animation_data.action
    launch_curves = list(launch_action.fcurves) if hasattr(launch_action, "fcurves") else [
        curve
        for layer in launch_action.layers
        for strip in layer.strips
        for channelbag in strip.channelbags
        for curve in channelbag.fcurves
    ]
    for curve in launch_curves:
        for point in curve.keyframe_points:
            point.interpolation = "LINEAR"'''
if source.count(before) != 1:
    raise RuntimeError("RC6 C3 interpolation correction target is not unique")
source = source.replace(before, after)
exec(compile(source, str(BASE) + "#C3_INLINE_ACTION_CURVES", "exec"), globals(), globals())
