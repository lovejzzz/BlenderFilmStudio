#!/usr/bin/env python3
"""C6 I09 scene adapter with one explicit 2 mm cup collision margin."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-real-impact-bullet-speed-screen-scene.py")
EXPECTED_BASE_SHA256 = "2e3f7814c9fc80cc27cba3dd3f3e7390eebffe8ccbe2b99dc742ae86e2f1994a"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("real-impact C6 scene base identity mismatch")
source = BASE.read_text(encoding="utf-8")
animation_block = '''if cup.animation_data or ball.animation_data:
    raise RuntimeError("real-impact source gives an outcome body authored animation")'''
margin_block = animation_block + '''
source_cup_use_margin = bool(cup.rigid_body.use_margin)
source_cup_collision_margin = float(cup.rigid_body.collision_margin)
if source_cup_use_margin or abs(source_cup_collision_margin - 0.04) > 1e-6:
    raise RuntimeError("real-impact C6 source cup margin identity mismatch")
cup.rigid_body.use_margin = True
cup.rigid_body.collision_margin = 0.002'''
replacements = (
    ('DRIVE_ENDS = {"I08": 8, "I10": 10, "I12": 12}', 'DRIVE_ENDS = {"M02": 9}', 1, "cell roster"),
    (animation_block, margin_block, 1, "explicit cup margin"),
    ('"exactRigidBodyIdentity": rigid_identity,', '"exactRigidBodyIdentity": rigid_identity,\n    "cupCollisionMarginExplicitTwoMillimeters": cup.rigid_body.use_margin and abs(cup.rigid_body.collision_margin - 0.002) <= 1e-6,', 1, "margin check"),
    ('"ballCollisionRadiusMeters": round(ball_radius, 8),', '"ballCollisionRadiusMeters": round(ball_radius, 8),\n        "sourceCupUseMargin": source_cup_use_margin,\n        "sourceCupCollisionMarginMeters": round(source_cup_collision_margin, 8),\n        "cupUseMargin": bool(cup.rigid_body.use_margin),\n        "cupCollisionMarginMeters": round(float(cup.rigid_body.collision_margin), 8),', 1, "margin receipt"),
    ('One exact-scene Bullet-only basketball-impact trajectory;', 'One exact-scene Bullet-only basketball-impact trajectory with explicit 2 mm cup collision margin;', 1, "claim"),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"real-impact C6 scene {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#C6_CUP_MARGIN_2MM", "exec"), globals(), globals())
