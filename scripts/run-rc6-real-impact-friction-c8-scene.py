#!/usr/bin/env python3
"""C8 I09 scene adapter with explicit 2 mm margin and cup friction 0.80."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-real-impact-bullet-speed-screen-scene.py")
EXPECTED_BASE_SHA256 = "2e3f7814c9fc80cc27cba3dd3f3e7390eebffe8ccbe2b99dc742ae86e2f1994a"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("real-impact C8 scene base identity mismatch")
source = BASE.read_text(encoding="utf-8")
animation_block = '''if cup.animation_data or ball.animation_data:
    raise RuntimeError("real-impact source gives an outcome body authored animation")'''
physics_block = animation_block + '''
source_cup_use_margin = bool(cup.rigid_body.use_margin)
source_cup_collision_margin = float(cup.rigid_body.collision_margin)
source_cup_friction = float(cup.rigid_body.friction)
source_floor_friction = float(floor.rigid_body.friction)
if source_cup_use_margin or abs(source_cup_collision_margin - 0.04) > 1e-6:
    raise RuntimeError("real-impact C8 source cup margin identity mismatch")
if abs(source_cup_friction - 0.75) > 1e-6 or abs(source_floor_friction - 0.58) > 1e-6:
    raise RuntimeError("real-impact C8 source floor-friction identity mismatch")
cup.rigid_body.use_margin = True
cup.rigid_body.collision_margin = 0.002
cup.rigid_body.friction = 0.80
combined_floor_friction = float(cup.rigid_body.friction * floor.rigid_body.friction)'''
replacements = (
    ('DRIVE_ENDS = {"I08": 8, "I10": 10, "I12": 12}', 'DRIVE_ENDS = {"F80": 9}', 1, "cell roster"),
    ('source = required["PHYS_INITIAL_LIQUID_VOLUME"]', 'source = required["PHYS_INITIAL_LIQUID_VOLUME"]\nfloor = required["PHYS_FLOOR"]', 1, "floor binding"),
    (animation_block, physics_block, 1, "corrected physical inputs"),
    ('"exactRigidBodyIdentity": rigid_identity,', '"exactRigidBodyIdentity": rigid_identity,\n    "cupCollisionMarginExplicitTwoMillimeters": cup.rigid_body.use_margin and abs(cup.rigid_body.collision_margin - 0.002) <= 1e-6,\n    "cupFrictionExplicitPointEight": abs(cup.rigid_body.friction - 0.80) <= 1e-6,', 1, "physical checks"),
    ('"ballCollisionRadiusMeters": round(ball_radius, 8),', '"ballCollisionRadiusMeters": round(ball_radius, 8),\n        "sourceCupUseMargin": source_cup_use_margin,\n        "sourceCupCollisionMarginMeters": round(source_cup_collision_margin, 8),\n        "cupUseMargin": bool(cup.rigid_body.use_margin),\n        "cupCollisionMarginMeters": round(float(cup.rigid_body.collision_margin), 8),\n        "sourceCupFriction": round(source_cup_friction, 8),\n        "cupFriction": round(float(cup.rigid_body.friction), 8),\n        "floorFriction": round(source_floor_friction, 8),\n        "combinedFloorFriction": round(combined_floor_friction, 8),', 1, "physical receipt"),
    ('One exact-scene Bullet-only basketball-impact trajectory;', 'One exact-scene Bullet-only basketball-impact trajectory with explicit 2 mm cup margin and source-derived 0.80 cup friction;', 1, "claim"),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"real-impact C8 scene {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#C8_FRICTION_080", "exec"), globals(), globals())
