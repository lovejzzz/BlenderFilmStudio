#!/usr/bin/env python3
"""C5 bounded Bullet motor test rig for the slow-tip screen."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-slow-tip-bullet-screen-scene.py")
EXPECTED_BASE_SHA256 = "8147ed5ed091554a2c2f876ee0b19a1a4bd75346b11a654a3481622c83bed780"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("slow-tip C5 scene base identity mismatch")

source = BASE.read_text(encoding="utf-8")
replacements = (
    ('FRAME_END = 64', 'FRAME_END = 120', "frame window"),
    (
        'CANDIDATE_DOMAIN_CENTER = Vector((0.40, 0.0, 0.26))\nCANDIDATE_DOMAIN_DIMENSIONS = Vector((0.80, 0.50, 0.56))\nDRIVE_ENDS = {"D12": 12, "D16": 16, "D20": 20, "D24": 24}',
        'CANDIDATE_DOMAIN_CENTER = Vector((0.45, 0.0, 0.26))\nCANDIDATE_DOMAIN_DIMENSIONS = Vector((0.90, 0.50, 0.58))\nDRIVE_ENDS = {"C5F48": 48, "C5F60": 60, "C5F72": 72, "C5F96": 96}',
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
        "isolate motorized fixture",
    ),
    (
        '''with bpy.context.temp_override(point_cache=world.point_cache):
    if world.point_cache.is_baked:
        bpy.ops.ptcache.free_bake()''',
        '''with bpy.context.temp_override(point_cache=world.point_cache):
    if world.point_cache.is_baked:
        bpy.ops.ptcache.free_bake()
scene.frame_set(FRAME_START)
bpy.context.view_layer.update()
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
hinge.rigid_body_constraint.use_limit_ang_z = True
hinge.rigid_body_constraint.limit_ang_z_lower = -math.radians(60.0)
hinge.rigid_body_constraint.limit_ang_z_upper = math.radians(5.0)
cup.rigid_body.angular_damping = 0.8
hinge_axis = hinge.matrix_world.to_3x3() @ Vector((0.0, 0.0, 1.0))
hinge_axis_alignment = abs(hinge_axis.normalized().dot(Vector((0.0, 1.0, 0.0))))
hinge_pivot_world = Vector((0.47, 0.0, 0.0))
hinge_pivot_cup_local = cup.matrix_world.inverted() @ hinge_pivot_world
motor_target_degrees_per_second = 60.0 * FPS / (args.drive_end_frame - FRAME_START)
bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0.47, 0.0, 0.0), rotation=(0.0, 0.0, -math.pi / 2.0))
motor = bpy.context.object
motor.name = "PHYS_SLOW_TIP_MOTOR"
bpy.ops.rigidbody.constraint_add(type="MOTOR")
motor.rigid_body_constraint.object1 = cup
motor.rigid_body_constraint.object2 = hinge_anchor
motor.rigid_body_constraint.disable_collisions = True
motor.rigid_body_constraint.enabled = True
motor.rigid_body_constraint.motor_ang_target_velocity = -math.radians(motor_target_degrees_per_second)
motor.rigid_body_constraint.motor_ang_max_impulse = 1.0
motor.rigid_body_constraint.use_motor_ang = True
motor_axis = motor.matrix_world.to_3x3() @ Vector((1.0, 0.0, 0.0))
motor_axis_alignment = abs(motor_axis.normalized().dot(Vector((0.0, 1.0, 0.0))))''',
        "frame-one hinge and bounded motor rig",
    ),
    (
        '''pusher.animation_data_clear()
for frame, x in (
    (FRAME_START, -1.10),
    (args.drive_end_frame, -0.64),
    (args.drive_end_frame + 1, -0.64),
    (args.drive_end_frame + 5, -1.10),
):
    pusher.location = (x, 0.0, 0.34)
    pusher.keyframe_insert(data_path="location", frame=frame)
for curve in action_curves(pusher):
    for point in curve.keyframe_points:
        point.interpolation = "LINEAR"''',
        '''pusher.animation_data_clear()
pusher.location = (-1.10, 0.0, 0.34)
pusher.hide_viewport = True
pusher.hide_render = True
bpy.context.view_layer.update()''',
        "remove penetrating kinematic drive",
    ),
    ("corners = world_corners(cup)", "corners = world_surface_points(cup)", "cup surface samples"),
    (
        '    separation = (ball.matrix_world.translation - cup.matrix_world.translation).length - 0.27',
        '    hinge_pivot_drift = (cup.matrix_world @ hinge_pivot_cup_local - hinge_pivot_world).length',
        "hinge drift",
    ),
    (
        '"ballCupSurfaceSeparationMeters": round(separation, 8),',
        '"hingePivotDriftMeters": round(hinge_pivot_drift, 8),\n            "motorTargetDegreesPerSecond": round(motor_target_degrees_per_second, 8),',
        "motor samples",
    ),
    (
        'first_45 = first_frame_at(samples, 45.0)\npeak_tilt = max(row["cupTiltDegrees"] for row in samples)',
        'first_45 = first_frame_at(samples, 45.0)\nmaximum_hinge_pivot_drift = max(row["hingePivotDriftMeters"] for row in samples)\npeak_tilt = max(row["cupTiltDegrees"] for row in samples)',
        "hinge metric derivation",
    ),
    (
        '    "contactByFrame50": contact_frame is not None and contact_frame <= 50,',
        '    "motorActuationAtFrameOne": motor.rigid_body_constraint.use_motor_ang and FRAME_START == 1,',
        "motor actuation check",
    ),
    (
        '    "solverOwnedCupTiltAtLeast45Degrees": first_45 is not None and peak_tilt >= 45.0,',
        '    "solverOwnedCupTiltAtLeast45Degrees": first_45 is not None and peak_tilt >= 45.0,\n    "mechanicalHingeStopHoldsAtMost65Degrees": peak_tilt <= 65.0,\n    "hingeAndMotorConstraintsExact": hinge.rigid_body_constraint.type == "HINGE" and hinge.rigid_body_constraint.object1 == cup and hinge.rigid_body_constraint.object2 == hinge_anchor and hinge.rigid_body_constraint.enabled and hinge.rigid_body_constraint.use_limit_ang_z and abs(hinge.rigid_body_constraint.limit_ang_z_lower + math.radians(60.0)) <= 1e-6 and abs(hinge.rigid_body_constraint.limit_ang_z_upper - math.radians(5.0)) <= 1e-6 and abs(cup.rigid_body.angular_damping - 0.8) <= 1e-6 and hinge_axis_alignment >= 0.999999 and motor.rigid_body_constraint.type == "MOTOR" and motor.rigid_body_constraint.object1 == cup and motor.rigid_body_constraint.object2 == hinge_anchor and motor.rigid_body_constraint.enabled and motor.rigid_body_constraint.use_motor_ang and abs(motor.rigid_body_constraint.motor_ang_target_velocity + math.radians(motor_target_degrees_per_second)) <= 1e-6 and abs(motor.rigid_body_constraint.motor_ang_max_impulse - 1.0) <= 1e-6 and motor_axis_alignment >= 0.999999,\n    "hingePivotStableWithinFiveMillimeters": maximum_hinge_pivot_drift <= 0.005,',
        "hinge and motor checks",
    ),
    (
        '    "pusherIsOnlyAuthoredActuator": bool(action_curves(pusher)) and pusher.rigid_body.kinematic,',
        '    "boundedMotorIsOnlyActuator": not action_curves(pusher) and pusher.rigid_body.kinematic and motor.rigid_body_constraint.use_motor_ang,',
        "actuator authority check",
    ),
    ('"driveDistanceMeters": 0.46,', '"targetAngularTravelDegrees": 60.0,', "angular travel receipt"),
    ('"meanDriveSpeedMetersPerSecond": round(0.46 * FPS / (args.drive_end_frame - FRAME_START), 8),', '"motorTargetDegreesPerSecond": round(motor_target_degrees_per_second, 8),', "motor speed receipt"),
    (
        '"candidateDomainDimensionsMeters": [float(value) for value in CANDIDATE_DOMAIN_DIMENSIONS],',
        '"candidateDomainDimensionsMeters": [float(value) for value in CANDIDATE_DOMAIN_DIMENSIONS],\n        "hingePivotWorldMeters": [0.47, 0.0, 0.0],\n        "hingeAxisWorld": [round(float(value), 8) for value in hinge_axis.normalized()],\n        "hingeAnchorLocationMeters": [0.47, 0.0, -0.08],\n        "hingeAngularLimitsDegrees": [-60.0, 5.0],\n        "cupAngularDamping": 0.8,\n        "motorAxisWorld": [round(float(value), 8) for value in motor_axis.normalized()],\n        "motorAngularMaximumImpulse": 1.0,',
        "hinge and motor configuration receipt",
    ),
    (
        '"contactFrame": contact_frame,',
        '"motorActuationFrame": FRAME_START,\n        "maximumHingePivotDriftMeters": maximum_hinge_pivot_drift,',
        "motor and hinge metrics receipt",
    ),
    ('bfs.rc6SlowTipBulletScreenCell.v0.1', 'bfs.rc6SlowTipBulletScreenC5Cell.v0.1', "schema"),
    ('RC6_SLOW_TIP_BULLET_SCREEN=', 'RC6_SLOW_TIP_BULLET_SCREEN_C5=', "marker"),
    ('One Bullet-only slow-tip trajectory screen;', 'One C5 hinge-constrained, impulse-bounded Bullet motor slow-tip trajectory screen;', "claim"),
)
for before, after, label in replacements:
    if source.count(before) != 1:
        raise RuntimeError(f"slow-tip C5 scene {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#C5_BOUNDED_MOTOR_RIG", "exec"), globals(), globals())
