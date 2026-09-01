#!/usr/bin/env python3
"""RC6 F3: calibrated high-contact Bullet cause plus bounded Mantaflow consequence."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-fluid-consequence-scene.py")
EXPECTED_BASE_SHA256 = "1385897455a451bbc7a012c3acf8e53a819fb121974fa8100ac9b1257bbc07d8"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 F3 base scene tool identity mismatch")

source = BASE.read_text(encoding="utf-8")
replacements = (
    ('    scene.world.color = (0.018, 0.022, 0.035)', '    scene.world = bpy.data.worlds.new("RC6 World")\n    scene.world.color = (0.018, 0.022, 0.035)', "World"),
    ('    liquid_mat = material("Liquid", (0.02, 0.22, 0.38), roughness=0.08, transmission=0.28)', '    liquid_mat = material("Liquid", (0.012, 0.055, 0.075), roughness=0.035, transmission=0.82)', "water material"),
    ('    floor = add_cube("PHYS_FLOOR", (0.25, 0, -0.04), (2.0, 1.5, 0.04), court_mat)', '    floor = add_cube("PHYS_FLOOR", (0.25, 0, -0.04), (3.0, 1.5, 0.04), court_mat)', "large floor"),
    ('    cup = create_open_tumbler("PHYS_OPEN_TUMBLER", (0.32, 0, 0.11))', '    cup = create_open_tumbler("PHYS_OPEN_TUMBLER", (0.32, 0, 0.22), outer_radius=0.15, height=0.44, thickness=0.06)', "calibrated tumbler"),
    ('    ball = add_uv_sphere("PHYS_BASKETBALL", (-0.88, 0, 0.12), 0.12, ball_mat)', '    ball = add_uv_sphere("PHYS_BASKETBALL", (-0.88, 0, 0.34), 0.12, ball_mat)', "calibrated ball path"),
    ('        groove.parent = ball', '        groove_world = groove.matrix_world.copy()\n        groove.parent = ball\n        groove.matrix_world = groove_world', "groove parenting"),
    (
        '''    rigid_body(floor, "PASSIVE", shape="BOX", friction=0.58, restitution=0.08)
    rigid_body(cup, "ACTIVE", mass=0.34, shape="CONVEX_HULL", friction=0.46, restitution=0.1)
    rigid_body(ball, "ACTIVE", mass=0.62, shape="SPHERE", friction=0.48, restitution=0.38)
    ball.rigid_body.linear_velocity = (5.2, 0.03, 0.0)
    ball.rigid_body.angular_velocity = (0.0, 16.0, 0.4)''',
        '''    lane = add_cube("PHYS_BALL_LANE", (-0.55, 0.0, 0.11), (0.57, 0.22, 0.11), metal_mat)
    rigid_body(floor, "PASSIVE", shape="BOX", friction=0.58, restitution=0.08)
    rigid_body(lane, "PASSIVE", shape="BOX", friction=0.55, restitution=0.08)
    rigid_body(cup, "ACTIVE", mass=0.34, shape="CONVEX_HULL", friction=0.75, restitution=0.05)
    rigid_body(ball, "ACTIVE", mass=0.62, shape="SPHERE", friction=0.48, restitution=0.32)
    pusher = add_cube("PHYS_VISIBLE_STRIKER", (-1.10, 0.0, 0.34), (0.05, 0.15, 0.12), metal_mat)
    rigid_body(pusher, "ACTIVE", mass=4.0, shape="BOX", friction=0.55, restitution=0.12)
    pusher.rigid_body.kinematic = True
    for striker_frame, striker_x in ((1, -1.10), (6, -0.64), (7, -0.64), (9, -1.10)):
        pusher.location.x = striker_x
        pusher.keyframe_insert(data_path="location", frame=striker_frame)
    striker_action = pusher.animation_data.action
    striker_curves = list(striker_action.fcurves) if hasattr(striker_action, "fcurves") else [
        curve for layer in striker_action.layers for strip in layer.strips
        for channelbag in strip.channelbags for curve in channelbag.fcurves
    ]
    for curve in striker_curves:
        for point in curve.keyframe_points:
            point.interpolation = "LINEAR"''',
        "calibrated Bullet cause",
    ),
    ('    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=0.057, depth=0.105, location=(0.32, 0, 0.063))', '    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=0.07, depth=0.16, location=(0.32, 0, 0.15))', "bounded liquid volume"),
    ('    domain = add_cube("PHYS_LIQUID_DOMAIN", (0.35, 0, 0.4), (1.05, 0.65, 0.4), liquid_mat)', '    domain = add_cube("PHYS_LIQUID_DOMAIN", (0.45, 0, 0.45), (1.25, 0.8, 0.45), liquid_mat)', "large fluid domain"),
    ('    settings.cache_mesh_format = "OPENVDB"', '    settings.cache_mesh_format = "BOBJECT"', "mesh cache"),
    ('    settings.resolution_max = 48', '    settings.resolution_max = 96', "fluid resolution"),
    ('    settings.mesh_particle_radius = 2.0', '    settings.mesh_particle_radius = 1.2', "surface reconstruction"),
    ('        if radial > 0.078 or local.z < -0.12 or local.z > 0.125:', '        if radial > 0.095 or local.z < -0.165 or local.z > 0.225:', "containment metric"),
    ('    center_xy = Vector((cup.matrix_world.translation.x, cup.matrix_world.translation.y))', '    center_xy = Vector((0.32, 0.0))', "world-space spread metric"),
    ('        separation = (ball.matrix_world.translation - cup.matrix_world.translation).length - 0.188', '        separation = (ball.matrix_world.translation - cup.matrix_world.translation).length - 0.27', "contact metric"),
    ('    cause_low, cause_high = world_bounds((ball, cup))', '    cause_low, cause_high = world_bounds((pusher, lane, ball, cup))', "cause framing"),
    ('    contact_low, contact_high = world_bounds((ball, cup))', '    contact_low, contact_high = world_bounds((pusher, lane, ball, cup))', "contact framing"),
    (
        '''    peak_tilt = max(row["cupTiltDegrees"] for row in bullet_samples)
    initial_fluid = fluid_samples[0]''',
        '''    peak_tilt = max(row["cupTiltDegrees"] for row in bullet_samples)
    impact_window_peak_tilt = max(row["cupTiltDegrees"] for row in bullet_samples if contact_frame <= row["frame"] <= min(48, contact_frame + 8))
    cup_max_x = max(abs(row["cupLocation"][0]) for row in bullet_samples)
    cup_max_y = max(abs(row["cupLocation"][1]) for row in bullet_samples)
    cup_min_z = min(row["cupLocation"][2] for row in bullet_samples)
    cup_max_z = max(row["cupLocation"][2] for row in bullet_samples)
    initial_fluid = fluid_samples[0]''',
        "bounded Bullet metrics",
    ),
    ('        "bulletCupResponse": peak_tilt >= 45.0,', '        "bulletCupResponse": peak_tilt >= 45.0,\n        "impactWindowCupResponse": impact_window_peak_tilt >= 45.0,\n        "cupStaysOnSet": cup_max_x <= 1.40 and cup_max_y <= 0.25 and cup_min_z >= 0.08 and cup_max_z <= 0.55,', "bounded Bullet acceptance"),
    ('        "derivedSpill": spill_frame is not None and spill_frame >= contact_frame,', '        "initialContainment": initial_fluid["outsideCupFraction"] <= 0.05,\n        "derivedSpill": spill_frame is not None and spill_frame >= contact_frame,', "containment acceptance"),
    ('        "noAuthoredOutcomeAuthority": len(cup.animation_data.action.fcurves) == 0 if cup.animation_data and cup.animation_data.action else True,', '        "noAuthoredOutcomeAuthority": (len(cup.animation_data.action.fcurves) == 0 if cup.animation_data and cup.animation_data.action else True) and not ball.animation_data,\n        "physicalLauncherAuthority": pusher.rigid_body.kinematic and pusher.animation_data is not None,', "authority acceptance"),
    ('settings.resolution_max == 48 and settings.cache_frame_end == 48', 'settings.resolution_max == 96 and settings.cache_frame_end == 48', "resource assertion"),
    ('                "peakCupTiltDegrees": round(peak_tilt, 8),', '                "peakCupTiltDegrees": round(peak_tilt, 8),\n                "impactWindowPeakTiltDegrees": round(impact_window_peak_tilt, 8),\n                "onSetBounds": {"maximumAbsX": round(cup_max_x, 8), "maximumAbsY": round(cup_max_y, 8), "minimumZ": round(cup_min_z, 8), "maximumZ": round(cup_max_z, 8)},', "Bullet receipts"),
    ('"claimCeiling": "One bounded Bullet-to-Mantaflow feasibility scene; one-way liquid consequence only, not two-way fluid/rigid coupling, narrow-neck bottle flow, production fluid quality or arbitrary scenes."', '"claimCeiling": "One bounded calibrated high-contact Bullet-to-Mantaflow scene with on-set and pre-impact-containment gates; one-way liquid consequence only, not two-way coupling or production fluid quality."', "claim ceiling"),
)
for before, after, label in replacements:
    if source.count(before) != 1:
        raise RuntimeError(f"RC6 F3 {label} target is not unique")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#F3_CALIBRATED_CAUSE_AND_BOUNDED_FLUID", "exec"), globals(), globals())
