#!/usr/bin/env python3
"""C2 passive toe-stop correction for the direct-contact slow-tip screen."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-slow-tip-bullet-screen-scene.py")
EXPECTED_BASE_SHA256 = "8147ed5ed091554a2c2f876ee0b19a1a4bd75346b11a654a3481622c83bed780"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("slow-tip C2 scene base identity mismatch")

source = BASE.read_text(encoding="utf-8")
replacements = (
    (
        'CANDIDATE_DOMAIN_CENTER = Vector((0.40, 0.0, 0.26))\nCANDIDATE_DOMAIN_DIMENSIONS = Vector((0.80, 0.50, 0.56))\nDRIVE_ENDS = {"D12": 12, "D16": 16, "D20": 20, "D24": 24}',
        'CANDIDATE_DOMAIN_CENTER = Vector((0.45, 0.0, 0.26))\nCANDIDATE_DOMAIN_DIMENSIONS = Vector((0.90, 0.50, 0.56))\nDRIVE_ENDS = {"C2D16": 16, "C2D20": 20, "C2D24": 24, "C2D28": 28}',
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
        '''domain.hide_viewport = True
domain.hide_render = True
source.hide_viewport = True
source.hide_render = True''',
        '''domain.hide_viewport = True
domain.hide_render = True
source.hide_viewport = True
source.hide_render = True
bpy.ops.mesh.primitive_cube_add(location=(0.485, 0.0, 0.02))
toe_stop = bpy.context.object
toe_stop.name = "PHYS_SLOW_TIP_TOE_STOP"
toe_stop.scale = (0.01, 0.19, 0.02)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
bpy.ops.rigidbody.object_add()
toe_stop.rigid_body.type = "PASSIVE"
toe_stop.rigid_body.collision_shape = "BOX"
toe_stop.rigid_body.friction = 0.9
toe_stop.rigid_body.restitution = 0.02''',
        "passive toe stop",
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
        '    actuator_points = world_surface_points(pusher)\n    separation = low.x - max(point.x for point in actuator_points)\n    toe_gap = min(point.x for point in world_surface_points(toe_stop)) - high.x',
        "direct and stop contact metrics",
    ),
    (
        '"ballCupSurfaceSeparationMeters": round(separation, 8),',
        '"actuatorCupSurfaceSeparationMeters": round(separation, 8),\n            "cupToeStopSurfaceSeparationMeters": round(toe_gap, 8),',
        "contact samples",
    ),
    (
        'first_45 = first_frame_at(samples, 45.0)\npeak_tilt = max(row["cupTiltDegrees"] for row in samples)',
        'first_45 = first_frame_at(samples, 45.0)\ntoe_stop_contact_frame = next((row["frame"] for row in samples if row["cupToeStopSurfaceSeparationMeters"] <= 0.001), None)\ninitial_toe_gap = samples[0]["cupToeStopSurfaceSeparationMeters"]\npeak_tilt = max(row["cupTiltDegrees"] for row in samples)',
        "stop event derivation",
    ),
    (
        '    "solverOwnedCupTiltAtLeast45Degrees": first_45 is not None and peak_tilt >= 45.0,',
        '    "solverOwnedCupTiltAtLeast45Degrees": first_45 is not None and peak_tilt >= 45.0,\n    "toeStopInitialClearance": 0.004 <= initial_toe_gap <= 0.006,\n    "passiveToeStopContactBeforeFortyFive": toe_stop.rigid_body.type == "PASSIVE" and toe_stop_contact_frame is not None and first_45 is not None and toe_stop_contact_frame <= first_45,',
        "stop checks",
    ),
    ('"driveDistanceMeters": 0.46', '"driveDistanceMeters": 0.29', "drive distance receipt"),
    ('round(0.46 * FPS / (args.drive_end_frame - FRAME_START), 8)', 'round(0.29 * FPS / (args.drive_end_frame - FRAME_START), 8)', "drive speed receipt"),
    (
        '"candidateDomainDimensionsMeters": [float(value) for value in CANDIDATE_DOMAIN_DIMENSIONS],',
        '"candidateDomainDimensionsMeters": [float(value) for value in CANDIDATE_DOMAIN_DIMENSIONS],\n        "toeStopLocationMeters": [0.485, 0.0, 0.02],\n        "toeStopDimensionsMeters": [0.02, 0.38, 0.04],',
        "stop configuration receipt",
    ),
    (
        '"contactFrame": contact_frame,',
        '"contactFrame": contact_frame,\n        "toeStopContactFrame": toe_stop_contact_frame,\n        "initialToeStopClearanceMeters": initial_toe_gap,',
        "stop metrics receipt",
    ),
    ('bfs.rc6SlowTipBulletScreenCell.v0.1', 'bfs.rc6SlowTipBulletScreenC2Cell.v0.1', "schema"),
    ('RC6_SLOW_TIP_BULLET_SCREEN=', 'RC6_SLOW_TIP_BULLET_SCREEN_C2=', "marker"),
    ('One Bullet-only slow-tip trajectory screen;', 'One C2 passive-stop Bullet-only slow-tip trajectory screen;', "claim"),
)
for before, after, label in replacements:
    if source.count(before) != 1:
        raise RuntimeError(f"slow-tip C2 scene {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#C2_PASSIVE_TOE_STOP", "exec"), globals(), globals())

