#!/usr/bin/env python3
"""RC6 F2: a visible Bullet striker, solver-resolvable tumbler and contained liquid."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-fluid-consequence-scene.py")
EXPECTED_BASE_SHA256 = "1385897455a451bbc7a012c3acf8e53a819fb121974fa8100ac9b1257bbc07d8"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 F2 base scene tool identity mismatch")

source = BASE.read_text(encoding="utf-8")
replacements = (
    (
        '    scene.world.color = (0.018, 0.022, 0.035)',
        '    scene.world = bpy.data.worlds.new("RC6 World")\n    scene.world.color = (0.018, 0.022, 0.035)',
        "World",
    ),
    (
        '    liquid_mat = material("Liquid", (0.02, 0.22, 0.38), roughness=0.08, transmission=0.28)',
        '    liquid_mat = material("Liquid", (0.015, 0.09, 0.12), roughness=0.04, transmission=0.78)',
        "liquid material",
    ),
    (
        '    cup = create_open_tumbler("PHYS_OPEN_TUMBLER", (0.32, 0, 0.11))',
        '    cup = create_open_tumbler("PHYS_OPEN_TUMBLER", (0.32, 0, 0.14), outer_radius=0.17, height=0.28, thickness=0.05)',
        "resolvable tumbler",
    ),
    (
        '        groove.parent = ball',
        '        groove_world = groove.matrix_world.copy()\n        groove.parent = ball\n        groove.matrix_world = groove_world',
        "groove parenting",
    ),
    (
        '''    rigid_body(floor, "PASSIVE", shape="BOX", friction=0.58, restitution=0.08)
    rigid_body(cup, "ACTIVE", mass=0.34, shape="CONVEX_HULL", friction=0.46, restitution=0.1)
    rigid_body(ball, "ACTIVE", mass=0.62, shape="SPHERE", friction=0.48, restitution=0.38)
    ball.rigid_body.linear_velocity = (5.2, 0.03, 0.0)
    ball.rigid_body.angular_velocity = (0.0, 16.0, 0.4)''',
        '''    rigid_body(floor, "PASSIVE", shape="BOX", friction=0.58, restitution=0.08)
    rigid_body(cup, "ACTIVE", mass=0.34, shape="CONVEX_HULL", friction=0.46, restitution=0.1)
    rigid_body(ball, "ACTIVE", mass=0.62, shape="SPHERE", friction=0.48, restitution=0.38)
    pusher = add_cube("PHYS_VISIBLE_STRIKER", (-1.10, 0.0, 0.13), (0.05, 0.15, 0.13), metal_mat)
    rigid_body(pusher, "ACTIVE", mass=4.0, shape="BOX", friction=0.55, restitution=0.18)
    pusher.rigid_body.kinematic = True
    for striker_frame, striker_x in ((1, -1.10), (4, -0.62), (5, -0.62), (7, -1.10)):
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
        "physical striker",
    ),
    (
        '    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=0.057, depth=0.105, location=(0.32, 0, 0.063))',
        '    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=0.10, depth=0.15, location=(0.32, 0, 0.125))',
        "contained liquid volume",
    ),
    (
        '    domain = add_cube("PHYS_LIQUID_DOMAIN", (0.35, 0, 0.4), (1.05, 0.65, 0.4), liquid_mat)',
        '    domain = add_cube("PHYS_LIQUID_DOMAIN", (0.45, 0, 0.38), (0.85, 0.55, 0.38), liquid_mat)',
        "fluid domain scale",
    ),
    ('    settings.cache_mesh_format = "OPENVDB"', '    settings.cache_mesh_format = "BOBJECT"', "mesh cache"),
    ('    settings.resolution_max = 48', '    settings.resolution_max = 72', "fluid resolution"),
    ('    settings.mesh_particle_radius = 2.0', '    settings.mesh_particle_radius = 1.4', "surface reconstruction"),
    ('        separation = (ball.matrix_world.translation - cup.matrix_world.translation).length - 0.188', '        separation = (ball.matrix_world.translation - cup.matrix_world.translation).length - 0.29', "contact metric"),
    ('        if radial > 0.078 or local.z < -0.12 or local.z > 0.125:', '        if radial > 0.125 or local.z < -0.095 or local.z > 0.145:', "containment metric"),
    ('    cause_low, cause_high = world_bounds((ball, cup))', '    cause_low, cause_high = world_bounds((pusher, ball, cup))', "cause framing"),
    ('    contact_low, contact_high = world_bounds((ball, cup))', '    contact_low, contact_high = world_bounds((pusher, ball, cup))', "contact framing"),
    (
        '        "derivedSpill": spill_frame is not None and spill_frame >= contact_frame,',
        '        "initialContainment": initial_fluid["outsideCupFraction"] <= 0.05,\n        "derivedSpill": spill_frame is not None and spill_frame >= contact_frame,',
        "containment acceptance",
    ),
    (
        '        "noAuthoredOutcomeAuthority": len(cup.animation_data.action.fcurves) == 0 if cup.animation_data and cup.animation_data.action else True,',
        '        "noAuthoredOutcomeAuthority": (len(cup.animation_data.action.fcurves) == 0 if cup.animation_data and cup.animation_data.action else True) and not ball.animation_data,\n        "physicalLauncherAuthority": pusher.rigid_body.kinematic and pusher.animation_data is not None,',
        "authority acceptance",
    ),
    ('settings.resolution_max == 48 and settings.cache_frame_end == 48', 'settings.resolution_max == 72 and settings.cache_frame_end == 48', "resource assertion"),
    (
        '"claimCeiling": "One bounded Bullet-to-Mantaflow feasibility scene; one-way liquid consequence only, not two-way fluid/rigid coupling, narrow-neck bottle flow, production fluid quality or arbitrary scenes."',
        '"claimCeiling": "One bounded visible-striker Bullet-to-Mantaflow feasibility scene with pre-impact containment; one-way liquid consequence only, not two-way coupling, production fluid quality or arbitrary scenes."',
        "claim ceiling",
    ),
)
for before, after, label in replacements:
    if source.count(before) != 1:
        raise RuntimeError(f"RC6 F2 {label} target is not unique")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#F2_PHYSICAL_STRIKER_AND_CONTAINMENT", "exec"), globals(), globals())
