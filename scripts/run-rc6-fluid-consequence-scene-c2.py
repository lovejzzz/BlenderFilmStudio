#!/usr/bin/env python3
"""C2 adapter: explicit World plus a two-frame kinematic launch initial condition."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-fluid-consequence-scene.py")
EXPECTED_BASE_SHA256 = "1385897455a451bbc7a012c3acf8e53a819fb121974fa8100ac9b1257bbc07d8"
digest = hashlib.sha256(BASE.read_bytes()).hexdigest()
if digest != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 C2 base scene tool identity mismatch")

source = BASE.read_text(encoding="utf-8")
world_before = "    scene.world.color = (0.018, 0.022, 0.035)"
world_after = "    scene.world = bpy.data.worlds.new(\"RC6 World\")\n    scene.world.color = (0.018, 0.022, 0.035)"
velocity_before = "    ball.rigid_body.linear_velocity = (5.2, 0.03, 0.0)\n    ball.rigid_body.angular_velocity = (0.0, 16.0, 0.4)"
velocity_after = '''    # Two frames define only the launch initial condition; Bullet owns every later outcome.
    ball.rigid_body.kinematic = True
    for launch_frame, launch_location, launch_rotation in (
        (1, (-0.88, 0.0, 0.12), (0.0, 0.0, 0.0)),
        (2, (-0.6633333333333333, 0.00125, 0.12), (0.0, 0.6666666666666666, 0.016666666666666666)),
    ):
        ball.location = launch_location
        ball.rotation_euler = launch_rotation
        ball.keyframe_insert(data_path=\"location\", frame=launch_frame)
        ball.keyframe_insert(data_path=\"rotation_euler\", frame=launch_frame)
    ball.rigid_body.kinematic = True
    ball.keyframe_insert(data_path=\"rigid_body.kinematic\", frame=2)
    ball.rigid_body.kinematic = False
    ball.keyframe_insert(data_path=\"rigid_body.kinematic\", frame=3)
    for curve in action_fcurves(ball):
        for point in curve.keyframe_points:
            point.interpolation = "LINEAR"'''
for before, after, label in (
    (world_before, world_after, "World"),
    (velocity_before, velocity_after, "launch"),
):
    if source.count(before) != 1:
        raise RuntimeError(f"RC6 C2 {label} correction target is not unique")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#C2_WORLD_AND_LAUNCH", "exec"), globals(), globals())
