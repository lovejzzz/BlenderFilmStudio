#!/usr/bin/env python3
"""C9 I09 scene adapter with a passive 60 mm rise contact ramp."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-real-impact-bullet-speed-screen-scene.py")
EXPECTED_BASE_SHA256 = "2e3f7814c9fc80cc27cba3dd3f3e7390eebffe8ccbe2b99dc742ae86e2f1994a"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("real-impact C9 scene base identity mismatch")
source = BASE.read_text(encoding="utf-8")
animation_block = '''if cup.animation_data or ball.animation_data:
    raise RuntimeError("real-impact source gives an outcome body authored animation")'''
physical_block = animation_block + '''
source_cup_use_margin = bool(cup.rigid_body.use_margin)
source_cup_collision_margin = float(cup.rigid_body.collision_margin)
if source_cup_use_margin or abs(source_cup_collision_margin - 0.04) > 1e-6:
    raise RuntimeError("real-impact C9 source cup margin identity mismatch")
cup.rigid_body.use_margin = True
cup.rigid_body.collision_margin = 0.002'''
ramp_block = '''source.hide_viewport = True
source.hide_render = True

ramp_vertices = [
    (-0.26, -0.20, 0.20), (0.04, -0.20, 0.20),
    (0.04, 0.20, 0.20), (-0.26, 0.20, 0.20),
    (-0.26, -0.20, 0.22), (0.04, -0.20, 0.28),
    (0.04, 0.20, 0.28), (-0.26, 0.20, 0.22),
]
ramp_faces = [
    (0, 3, 2, 1), (0, 1, 5, 4), (3, 7, 6, 2),
    (0, 4, 7, 3), (1, 2, 6, 5), (4, 5, 6, 7),
]
ramp_mesh = bpy.data.meshes.new("PHYS_CONTACT_RAMP_MESH")
ramp_mesh.from_pydata(ramp_vertices, [], ramp_faces)
ramp_mesh.update()
ramp = bpy.data.objects.new("PHYS_CONTACT_RAMP", ramp_mesh)
scene.collection.objects.link(ramp)
bpy.context.view_layer.objects.active = ramp
ramp.select_set(True)
bpy.ops.rigidbody.object_add()
ramp.select_set(False)
ramp.rigid_body.type = "PASSIVE"
ramp.rigid_body.collision_shape = "CONVEX_HULL"
ramp.rigid_body.friction = 0.55
ramp.rigid_body.restitution = 0.08
ramp.rigid_body.use_margin = True
ramp.rigid_body.collision_margin = 0.002
ramp_exact = (
    ramp.animation_data is None
    and ramp.rigid_body.type == "PASSIVE"
    and ramp.rigid_body.collision_shape == "CONVEX_HULL"
    and abs(ramp.rigid_body.friction - 0.55) <= 1e-6
    and abs(ramp.rigid_body.collision_margin - 0.002) <= 1e-6
    and len(ramp.data.vertices) == 8
    and len(ramp.data.polygons) == 6
)'''
replacements = (
    ('DRIVE_ENDS = {"I08": 8, "I10": 10, "I12": 12}', 'DRIVE_ENDS = {"R60": 9}', 1, "cell roster"),
    (animation_block, physical_block, 1, "corrected margin"),
    ('source.hide_viewport = True\nsource.hide_render = True', ramp_block, 1, "passive ramp"),
    ('peak_tilt = max(row["cupTiltDegrees"] for row in samples)', 'peak_tilt = max(row["cupTiltDegrees"] for row in samples)\ncontact_ball_z = next((row["ballLocation"][2] for row in samples if row["frame"] == contact_frame), None)\nmaximum_ball_z_before_contact = max(row["ballLocation"][2] for row in samples if contact_frame is None or row["frame"] <= contact_frame)', 1, "raised contact metrics"),
    ('"exactRigidBodyIdentity": rigid_identity,', '"exactRigidBodyIdentity": rigid_identity,\n    "cupCollisionMarginExplicitTwoMillimeters": cup.rigid_body.use_margin and abs(cup.rigid_body.collision_margin - 0.002) <= 1e-6,\n    "passiveRampExact": ramp_exact,\n    "solverOwnedRaisedContactAtLeastPoint38Meters": contact_ball_z is not None and contact_ball_z >= 0.38,', 1, "ramp checks"),
    ('"ballCollisionRadiusMeters": round(ball_radius, 8),', '"ballCollisionRadiusMeters": round(ball_radius, 8),\n        "sourceCupUseMargin": source_cup_use_margin,\n        "sourceCupCollisionMarginMeters": round(source_cup_collision_margin, 8),\n        "cupUseMargin": bool(cup.rigid_body.use_margin),\n        "cupCollisionMarginMeters": round(float(cup.rigid_body.collision_margin), 8),\n        "cupFriction": round(float(cup.rigid_body.friction), 8),\n        "rampStartX": -0.26,\n        "rampEndX": 0.04,\n        "rampSurfaceStartZ": 0.22,\n        "rampSurfaceEndZ": 0.28,\n        "rampRiseMeters": 0.06,\n        "rampRunMeters": 0.30,\n        "rampWidthMeters": 0.40,\n        "rampAngleDegrees": round(math.degrees(math.atan2(0.06, 0.30)), 8),', 1, "ramp configuration"),
    ('"derivedContactFrame": contact_frame,', '"derivedContactFrame": contact_frame,\n        "contactBallCenterZMeters": None if contact_ball_z is None else round(contact_ball_z, 8),\n        "maximumBallCenterZMetersBeforeContact": round(maximum_ball_z_before_contact, 8),', 1, "ramp metrics receipt"),
    ('One exact-scene Bullet-only basketball-impact trajectory;', 'One exact-scene Bullet-only basketball-impact trajectory with a passive metric ramp and explicit 2 mm cup margin;', 1, "claim"),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"real-impact C9 scene {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#C9_PASSIVE_RAMP_60MM", "exec"), globals(), globals())
