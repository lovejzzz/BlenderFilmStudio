#!/usr/bin/env python3
"""C1 direct-contact and exact-surface correction for the slow-tip screen."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-slow-tip-bullet-screen-scene.py")
EXPECTED_BASE_SHA256 = "8147ed5ed091554a2c2f876ee0b19a1a4bd75346b11a654a3481622c83bed780"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("slow-tip C1 scene base identity mismatch")

source = BASE.read_text(encoding="utf-8")
replacements = (
    (
        'CANDIDATE_DOMAIN_CENTER = Vector((0.40, 0.0, 0.26))\nCANDIDATE_DOMAIN_DIMENSIONS = Vector((0.80, 0.50, 0.56))\nDRIVE_ENDS = {"D12": 12, "D16": 16, "D20": 20, "D24": 24}',
        'CANDIDATE_DOMAIN_CENTER = Vector((0.45, 0.0, 0.26))\nCANDIDATE_DOMAIN_DIMENSIONS = Vector((0.90, 0.50, 0.56))\nDRIVE_ENDS = {"C1D16": 16, "C1D20": 20, "C1D24": 24, "C1D28": 28}',
        "cell and domain roster",
    ),
    (
        'def world_corners(obj):\n    return [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]',
        'def world_surface_points(obj):\n    return [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]',
        "exact surface sampler",
    ),
    (
        'if cup.animation_data or ball.animation_data:\n    raise RuntimeError("slow-tip source gives an outcome body authored animation")',
        'if cup.animation_data or ball.animation_data:\n    raise RuntimeError("slow-tip source gives an outcome body authored animation")\nball.rigid_body.kinematic = True',
        "isolate direct-contact fixture",
    ),
    (
        '''for frame, x in (
    (FRAME_START, -1.10),
    (args.drive_end_frame, -0.64),
    (args.drive_end_frame + 1, -0.64),
    (args.drive_end_frame + 5, -1.10),
):''',
        '''for frame, x in (
    (FRAME_START, -0.05),
    (args.drive_end_frame, 0.24),
    (args.drive_end_frame + 1, 0.24),
    (args.drive_end_frame + 5, -0.05),
):''',
        "direct upper-cup drive",
    ),
    ("corners = world_corners(cup)", "corners = world_surface_points(cup)", "cup surface samples"),
    (
        '    separation = (ball.matrix_world.translation - cup.matrix_world.translation).length - 0.27',
        '    actuator_points = world_surface_points(pusher)\n    separation = low.x - max(point.x for point in actuator_points)',
        "direct contact metric",
    ),
    ('"ballCupSurfaceSeparationMeters": round(separation, 8)', '"actuatorCupSurfaceSeparationMeters": round(separation, 8)', "contact sample name"),
    ('"driveDistanceMeters": 0.46', '"driveDistanceMeters": 0.29', "drive distance receipt"),
    ('round(0.46 * FPS / (args.drive_end_frame - FRAME_START), 8)', 'round(0.29 * FPS / (args.drive_end_frame - FRAME_START), 8)', "drive speed receipt"),
    ('bfs.rc6SlowTipBulletScreenCell.v0.1', 'bfs.rc6SlowTipBulletScreenC1Cell.v0.1', "schema"),
    ('RC6_SLOW_TIP_BULLET_SCREEN=', 'RC6_SLOW_TIP_BULLET_SCREEN_C1=', "marker"),
    ('One Bullet-only slow-tip trajectory screen;', 'One C1 direct-contact Bullet-only slow-tip trajectory screen;', "claim"),
)
for before, after, label in replacements:
    if source.count(before) != 1:
        raise RuntimeError(f"slow-tip C1 scene {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#C1_DIRECT_CONTACT_EXACT_SURFACE", "exec"), globals(), globals())

