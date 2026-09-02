#!/usr/bin/env python3
"""C3 explicit Bullet hinge correction for the slow-tip screen."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-slow-tip-bullet-screen-scene.py")
EXPECTED_BASE_SHA256 = "8147ed5ed091554a2c2f876ee0b19a1a4bd75346b11a654a3481622c83bed780"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("slow-tip C3 scene base identity mismatch")

source = BASE.read_text(encoding="utf-8")
replacements = (
    (
        'CANDIDATE_DOMAIN_CENTER = Vector((0.40, 0.0, 0.26))\nCANDIDATE_DOMAIN_DIMENSIONS = Vector((0.80, 0.50, 0.56))\nDRIVE_ENDS = {"D12": 12, "D16": 16, "D20": 20, "D24": 24}',
        'CANDIDATE_DOMAIN_CENTER = Vector((0.45, 0.0, 0.26))\nCANDIDATE_DOMAIN_DIMENSIONS = Vector((0.90, 0.50, 0.56))\nDRIVE_ENDS = {"C3D16": 16, "C3D20": 20, "C3D24": 24, "C3D28": 28}',
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
bpy.ops.mesh.primitive_cube_add(location=(0.47, 0.0, -0.08))
hinge_anchor = bpy.context.object
hinge_anchor.name = "PHYS_SLOW_TIP_HINGE_ANCHOR"
hinge_anchor.scale = (0.04, 0.04, 0.04)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
bpy.ops.rigidbody.object_add()
hinge_anchor.rigid_body.type = "PASSIVE"
hinge_anchor.rigid_body.collision_shape = "BOX"
bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0.47, 0.0, 0.0), rotation=(math.pi / 2.0, 0.0, 0.0))
hinge = bpy.context.object
hinge.name = "PHYS_SLOW_TIP_HINGE"
bpy.ops.rigidbody.constraint_add(type="HINGE")
hinge.rigid_body_constraint.object1 = cup
hinge.rigid_body_constraint.object2 = hinge_anchor
hinge.rigid_body_constraint.disable_collisions = True
hinge.rigid_body_constraint.enabled = True
hinge_axis = hinge.matrix_world.to_3x3() @ Vector((0.0, 0.0, 1.0))
hinge_axis_alignment = abs(hinge_axis.normalized().dot(Vector((0.0, 1.0, 0.0))))
hinge_pivot_world = Vector((0.47, 0.0, 0.0))
hinge_pivot_cup_local = cup.matrix_world.inverted() @ hinge_pivot_world''',
        "explicit hinge rig",
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
        '    actuator_points = world_surface_points(pusher)\n    separation = low.x - max(point.x for point in actuator_points)\n    hinge_pivot_drift = (cup.matrix_world @ hinge_pivot_cup_local - hinge_pivot_world).length',
        "direct contact and hinge drift",
    ),
    (
        '"ballCupSurfaceSeparationMeters": round(separation, 8),',
        '"actuatorCupSurfaceSeparationMeters": round(separation, 8),\n            "hingePivotDriftMeters": round(hinge_pivot_drift, 8),',
        "contact and hinge samples",
    ),
    (
        'first_45 = first_frame_at(samples, 45.0)\npeak_tilt = max(row["cupTiltDegrees"] for row in samples)',
        'first_45 = first_frame_at(samples, 45.0)\nmaximum_hinge_pivot_drift = max(row["hingePivotDriftMeters"] for row in samples)\npeak_tilt = max(row["cupTiltDegrees"] for row in samples)',
        "hinge metric derivation",
    ),
    (
        '    "solverOwnedCupTiltAtLeast45Degrees": first_45 is not None and peak_tilt >= 45.0,',
        '    "solverOwnedCupTiltAtLeast45Degrees": first_45 is not None and peak_tilt >= 45.0,\n    "hingeConstraintExact": hinge.rigid_body_constraint.type == "HINGE" and hinge.rigid_body_constraint.object1 == cup and hinge.rigid_body_constraint.object2 == hinge_anchor and hinge.rigid_body_constraint.enabled and hinge_axis_alignment >= 0.999999,\n    "hingePivotStableWithinFiveMillimeters": maximum_hinge_pivot_drift <= 0.005,',
        "hinge checks",
    ),
    ('"driveDistanceMeters": 0.46', '"driveDistanceMeters": 0.29', "drive distance receipt"),
    ('round(0.46 * FPS / (args.drive_end_frame - FRAME_START), 8)', 'round(0.29 * FPS / (args.drive_end_frame - FRAME_START), 8)', "drive speed receipt"),
    (
        '"candidateDomainDimensionsMeters": [float(value) for value in CANDIDATE_DOMAIN_DIMENSIONS],',
        '"candidateDomainDimensionsMeters": [float(value) for value in CANDIDATE_DOMAIN_DIMENSIONS],\n        "hingePivotWorldMeters": [0.47, 0.0, 0.0],\n        "hingeAxisWorld": [round(float(value), 8) for value in hinge_axis.normalized()],\n        "hingeAnchorLocationMeters": [0.47, 0.0, -0.08],',
        "hinge configuration receipt",
    ),
    (
        '"contactFrame": contact_frame,',
        '"contactFrame": contact_frame,\n        "maximumHingePivotDriftMeters": maximum_hinge_pivot_drift,',
        "hinge metrics receipt",
    ),
    ('bfs.rc6SlowTipBulletScreenCell.v0.1', 'bfs.rc6SlowTipBulletScreenC3Cell.v0.1', "schema"),
    ('RC6_SLOW_TIP_BULLET_SCREEN=', 'RC6_SLOW_TIP_BULLET_SCREEN_C3=', "marker"),
    ('One Bullet-only slow-tip trajectory screen;', 'One C3 hinged Bullet-only slow-tip trajectory screen;', "claim"),
)
for before, after, label in replacements:
    if source.count(before) != 1:
        raise RuntimeError(f"slow-tip C3 scene {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#C3_EXPLICIT_HINGE", "exec"), globals(), globals())

