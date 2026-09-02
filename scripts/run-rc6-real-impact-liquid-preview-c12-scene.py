#!/usr/bin/env python3
"""Bake one same-solve R40 Bullet + APIC impact-liquid Preview window."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-moving-liquid-preview-scene.py")
EXPECTED_BASE_SHA256 = "ac6531b62b0c329d69dd969f650f6b2345199343f803d1ee63dae11813237a36"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("real-impact liquid C12 scene base identity mismatch")
    source = BASE.read_text(encoding="utf-8")

    replacements = (
        ("FRAME_END = 24", "FRAME_END = 36", "event-window end"),
        ("DOMAIN_CENTER = Vector((0.45, 0.0, 0.26))", "DOMAIN_CENTER = Vector((0.57, 0.0, 0.26))", "shifted domain"),
        ("DRIVE_END_FRAME = 96", "DRIVE_END_FRAME = 9", "impact actuator timing"),
        (
            "MOTOR_DEGREES_PER_SECOND = 60.0 * FPS / (DRIVE_END_FRAME - FRAME_START)",
            "MOTOR_DEGREES_PER_SECOND = 0.0\nCUP_OUTER_RADIUS_METERS = 0.15\nCUP_OUTER_BOTTOM_LOCAL_Z = -0.22\nRAMP_START_X = -0.26\nRAMP_END_X = 0.04\nRAMP_HALF_WIDTH = 0.20\nRAMP_BASE_Z = 0.20\nRAMP_SURFACE_START_Z = 0.22\nRAMP_SURFACE_END_Z = 0.26\nSIGNIFICANT_SPILL_FRACTION = 0.05",
            "impact constants",
        ),
        (
            'if trajectory.get("cellId") != "C5F96" or trajectory.get("status") != "PASS" or len(trajectory_samples) != FRAME_END:\n    raise RuntimeError("moving-liquid Preview accepted trajectory identity mismatch")',
            'if trajectory.get("cellId") != "R40" or trajectory.get("status") != "FAIL" or trajectory.get("resultHash") != "9deeebd3669203df9e62c728e679335dc43de0722d67add508588b1c1aa2842d" or len(trajectory_samples) != FRAME_END:\n    raise RuntimeError("real-impact liquid C12 retained R40 trajectory identity mismatch")',
            "R40 identity",
        ),
        (
            'source = objects["PHYS_INITIAL_LIQUID_VOLUME"]',
            'source = objects["PHYS_INITIAL_LIQUID_VOLUME"]\nfloor = objects["PHYS_FLOOR"]',
            "floor binding",
        ),
        (
            'flow_modifier = next((item for item in source.modifiers if item.type == "FLUID" and item.fluid_type == "FLOW"), None)',
            'flow_modifier = next((item for item in source.modifiers if item.type == "FLUID" and item.fluid_type == "FLOW"), None)\nfloor_modifier = next((item for item in floor.modifiers if item.type == "FLUID" and item.fluid_type == "EFFECTOR"), None)',
            "floor modifier binding",
        ),
        (
            "if domain_modifier is None or cup_modifier is None or flow_modifier is None:",
            "if domain_modifier is None or cup_modifier is None or flow_modifier is None or floor_modifier is None:",
            "complete source fluid roster",
        ),
        (
            "effector = cup_modifier.effector_settings\nflow = flow_modifier.flow_settings",
            "effector = cup_modifier.effector_settings\nflow = flow_modifier.flow_settings\nfloor_effector = floor_modifier.effector_settings",
            "floor settings binding",
        ),
        ("settings.timesteps_min = 1", "settings.timesteps_min = 2", "accepted minimum timesteps"),
        (
            "settings.particle_number = 2",
            "settings.particle_number = 2\nsettings.particle_min = 8\nsettings.particle_max = 16\nsettings.particle_band_width = 4.0",
            "accepted particle sampling",
        ),
        ("settings.particle_radius = 1.6", "settings.particle_radius = 1.8", "accepted simulation radius"),
        (
            "settings.use_fractions = True",
            "settings.use_fractions = True\nsettings.fractions_threshold = 0.05\nsettings.fractions_distance = 0.25",
            "accepted fractional obstacle settings",
        ),
        ("effector.surface_distance = 2.5", "effector.surface_distance = 2.0", "accepted cup effector distance"),
        ("effector.subframes = 1", "effector.subframes = 8", "derived impact effector subframes"),
    )
    for before, after, label in replacements:
        if source.count(before) != 1:
            raise RuntimeError(f"real-impact liquid C12 {label} target mismatch")
        source = source.replace(before, after)

    helper_anchor = "\ndef mesh_world_volume(obj):"
    helper = '''
def cylinder_sphere_gap(cup, ball):
    point = cup.matrix_world.inverted_safe() @ ball.matrix_world.translation
    radial = math.hypot(point.x, point.y) - CUP_OUTER_RADIUS_METERS
    vertical = abs(point.z) - 0.22
    outside = math.hypot(max(radial, 0.0), max(vertical, 0.0))
    signed_distance = outside + min(max(radial, vertical), 0.0)
    return signed_distance - 0.12000014


def first_tilt_frame(samples, threshold):
    return next((row["frame"] for row in samples if row["cupTiltDegrees"] >= threshold), None)
'''
    if source.count(helper_anchor) != 1:
        raise RuntimeError("real-impact liquid C12 helper anchor mismatch")
    source = source.replace(helper_anchor, helper + helper_anchor)

    quality_anchor = '''        outside_count = sum(
            math.hypot(point.x, point.y) > radial_limit or point.z < bottom_limit or point.z > top_limit
            for point in local_points
        )'''
    quality_extension = quality_anchor + '''
        world_below_floor_count = sum(point.z < -BASE_VOXEL_METERS for point in world_points)
        cup_solid_count = 0
        ramp_solid_count = 0
        domain_low = DOMAIN_CENTER - DOMAIN_DIMENSIONS * 0.5 + Vector((BASE_VOXEL_METERS,) * 3)
        domain_high = DOMAIN_CENTER + DOMAIN_DIMENSIONS * 0.5 - Vector((BASE_VOXEL_METERS,) * 3)
        domain_outside_count = 0
        for local, world_point in zip(local_points, world_points):
            radial = math.hypot(local.x, local.y)
            deep_side = (
                CUP_INNER_RADIUS_METERS + BASE_VOXEL_METERS < radial < CUP_OUTER_RADIUS_METERS - BASE_VOXEL_METERS
                and CUP_INTERIOR_BOTTOM_LOCAL_Z + BASE_VOXEL_METERS < local.z < CUP_INTERIOR_TOP_LOCAL_Z - BASE_VOXEL_METERS
            )
            deep_floor = (
                radial < CUP_OUTER_RADIUS_METERS - BASE_VOXEL_METERS
                and CUP_OUTER_BOTTOM_LOCAL_Z + BASE_VOXEL_METERS < local.z < CUP_INTERIOR_BOTTOM_LOCAL_Z - BASE_VOXEL_METERS
            )
            cup_solid_count += deep_side or deep_floor
            if RAMP_START_X + BASE_VOXEL_METERS < world_point.x < RAMP_END_X - BASE_VOXEL_METERS and abs(world_point.y) < RAMP_HALF_WIDTH - BASE_VOXEL_METERS:
                alpha = (world_point.x - RAMP_START_X) / (RAMP_END_X - RAMP_START_X)
                ramp_top = RAMP_SURFACE_START_Z + alpha * (RAMP_SURFACE_END_Z - RAMP_SURFACE_START_Z)
                ramp_solid_count += RAMP_BASE_Z + BASE_VOXEL_METERS < world_point.z < ramp_top - BASE_VOXEL_METERS
            domain_outside_count += any(world_point[axis] < domain_low[axis] or world_point[axis] > domain_high[axis] for axis in range(3))'''
    if source.count(quality_anchor) != 1:
        raise RuntimeError("real-impact liquid C12 quality anchor mismatch")
    source = source.replace(quality_anchor, quality_extension)

    return_anchor = '''            "aboveRimFraction": round(above_count / vertex_count, 8),'''
    return_extension = return_anchor + '''
            "worldBelowFloorFraction": round(world_below_floor_count / vertex_count, 8),
            "cupSolidIntrusionFraction": round(cup_solid_count / vertex_count, 8),
            "rampSolidIntrusionFraction": round(ramp_solid_count / vertex_count, 8),
            "domainOutsideOneVoxelInsetFraction": round(domain_outside_count / vertex_count, 8),
            "totalPositiveComponentVolumeCubicMeters": round(sum(max(0.0, row["signedVolumeCubicMeters"]) for row in component_details), 10),'''
    if source.count(return_anchor) != 1:
        raise RuntimeError("real-impact liquid C12 quality return anchor mismatch")
    source = source.replace(return_anchor, return_extension)

    physical_start = source.index("ball.rigid_body.kinematic = True")
    physical_end = source.index("\nbullet_started = time.monotonic()", physical_start)
    physical_block = '''source_cup_use_margin = bool(cup.rigid_body.use_margin)
source_cup_collision_margin = float(cup.rigid_body.collision_margin)
if source_cup_use_margin or abs(source_cup_collision_margin - 0.04) > 1e-6:
    raise RuntimeError("real-impact liquid C12 source cup margin identity mismatch")
cup.rigid_body.use_margin = True
cup.rigid_body.collision_margin = 0.002
ball.rigid_body.kinematic = False

pusher.animation_data_clear()
for frame, x in ((1, -1.10), (9, -0.64), (10, -0.64), (12, -1.10)):
    pusher.location = (x, 0.0, 0.34)
    pusher.keyframe_insert(data_path="location", frame=frame)
for curve in action_curves(pusher):
    for point in curve.keyframe_points:
        point.interpolation = "LINEAR"

ramp_vertices = [
    (-0.26, -0.20, 0.20), (0.04, -0.20, 0.20),
    (0.04, 0.20, 0.20), (-0.26, 0.20, 0.20),
    (-0.26, -0.20, 0.22), (0.04, -0.20, 0.26),
    (0.04, 0.20, 0.26), (-0.26, 0.20, 0.22),
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
ramp_fluid = ramp.modifiers.new(name="Effector Fluid", type="FLUID")
ramp_fluid.fluid_type = "EFFECTOR"
bpy.context.view_layer.update()
ramp_effector = ramp_fluid.effector_settings
if ramp_effector is None:
    raise RuntimeError("real-impact liquid C12 ramp effector unavailable")
for static_effector in (floor_effector, ramp_effector):
    static_effector.surface_distance = 2.0
    static_effector.use_plane_init = False
    static_effector.use_effector = True
    static_effector.subframes = 0
ramp_exact = (
    ramp.animation_data is None
    and ramp.rigid_body.type == "PASSIVE"
    and ramp.rigid_body.collision_shape == "CONVEX_HULL"
    and abs(ramp.rigid_body.friction - 0.55) <= 1e-6
    and abs(ramp.rigid_body.collision_margin - 0.002) <= 1e-6
    and len(ramp.data.vertices) == 8
    and len(ramp.data.polygons) == 6
)
bpy.context.view_layer.update()
'''
    source = source[:physical_start] + physical_block + source[physical_end:]

    bullet_start = source.index("bullet_started = time.monotonic()")
    bullet_end = source.index("\n# Rebind the copied domain", bullet_start)
    bullet_block = '''bullet_started = time.monotonic()
scene.frame_set(FRAME_START)
with bpy.context.temp_override(point_cache=world.point_cache):
    bpy.ops.ptcache.bake(bake=True)
bullet_seconds = time.monotonic() - bullet_started
bullet_samples = []
maximum_location_delta = 0.0
maximum_rotation_delta_degrees = 0.0
maximum_ball_location_delta = 0.0
maximum_surface_displacement = 0.0
previous_points = None
contact_frame = None
for frame in range(FRAME_START, FRAME_END + 1):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    expected = trajectory_samples[frame]
    expected_location = Vector(expected["cupLocation"])
    expected_rotation = __import__("mathutils").Quaternion(expected["cupRotationQuaternion"])
    expected_ball_location = Vector(expected["ballLocation"])
    location_delta = (cup.matrix_world.translation - expected_location).length
    rotation_delta = math.degrees(cup.matrix_world.to_quaternion().rotation_difference(expected_rotation).angle)
    ball_delta = (ball.matrix_world.translation - expected_ball_location).length
    points = [cup.matrix_world @ vertex.co for vertex in cup.data.vertices]
    surface_displacement = 0.0 if previous_points is None else max((points[index] - previous_points[index]).length for index in range(len(points)))
    previous_points = points
    separation = cylinder_sphere_gap(cup, ball)
    if contact_frame is None and separation <= 0.01:
        contact_frame = frame
    maximum_location_delta = max(maximum_location_delta, location_delta)
    maximum_rotation_delta_degrees = max(maximum_rotation_delta_degrees, rotation_delta)
    maximum_ball_location_delta = max(maximum_ball_location_delta, ball_delta)
    maximum_surface_displacement = max(maximum_surface_displacement, surface_displacement)
    bullet_samples.append({
        "frame": frame,
        "cupLocation": [round(value, 8) for value in cup.matrix_world.translation],
        "cupRotationQuaternion": [round(value, 8) for value in cup.matrix_world.to_quaternion()],
        "cupTiltDegrees": round(tilt_degrees(cup), 8),
        "ballLocation": [round(value, 8) for value in ball.matrix_world.translation],
        "ballCupCollisionSurfaceSeparationMeters": round(separation, 8),
        "cupSurfaceDisplacementFromPriorFrameMeters": round(surface_displacement, 8),
        "acceptedCupLocationDeltaMeters": round(location_delta, 10),
        "acceptedCupRotationDeltaDegrees": round(rotation_delta, 10),
        "acceptedBallLocationDeltaMeters": round(ball_delta, 10),
    })
first_seventy_frame = first_tilt_frame(bullet_samples, 70.0)
required_effector_subframes = max(1, math.ceil(maximum_surface_displacement / BASE_VOXEL_METERS))
animated_rigid_bodies = sorted(obj.name for obj in bpy.data.objects if obj.rigid_body is not None and action_curves(obj))
'''
    source = source[:bullet_start] + bullet_block + source[bullet_end:]

    tail_start = source.index("fluid_samples = []")
    tail = '''post_fluid_bullet_samples = []
maximum_post_fluid_cup_location_delta = 0.0
maximum_post_fluid_cup_rotation_delta_degrees = 0.0
maximum_post_fluid_ball_location_delta = 0.0
for frame in range(FRAME_START, FRAME_END + 1):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    expected = trajectory_samples[frame]
    location_delta = (cup.matrix_world.translation - Vector(expected["cupLocation"])).length
    rotation_delta = math.degrees(cup.matrix_world.to_quaternion().rotation_difference(__import__("mathutils").Quaternion(expected["cupRotationQuaternion"])).angle)
    ball_delta = (ball.matrix_world.translation - Vector(expected["ballLocation"])).length
    maximum_post_fluid_cup_location_delta = max(maximum_post_fluid_cup_location_delta, location_delta)
    maximum_post_fluid_cup_rotation_delta_degrees = max(maximum_post_fluid_cup_rotation_delta_degrees, rotation_delta)
    maximum_post_fluid_ball_location_delta = max(maximum_post_fluid_ball_location_delta, ball_delta)
    post_fluid_bullet_samples.append({
        "frame": frame,
        "cupLocation": [round(value, 8) for value in cup.matrix_world.translation],
        "cupRotationQuaternion": [round(value, 8) for value in cup.matrix_world.to_quaternion()],
        "ballLocation": [round(value, 8) for value in ball.matrix_world.translation],
        "acceptedCupLocationDeltaMeters": round(location_delta, 10),
        "acceptedCupRotationDeltaDegrees": round(rotation_delta, 10),
        "acceptedBallLocationDeltaMeters": round(ball_delta, 10),
    })

fluid_samples = []
for frame in range(FRAME_START, FRAME_END + 1):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    row = fluid_quality(domain, cup)
    row["frame"] = frame
    row["cupTiltDegrees"] = round(tilt_degrees(cup), 8)
    row["sourceVolumeErrorFraction"] = round(row["meshVolumeCubicMeters"] / source_volume - 1.0, 8)
    fluid_samples.append(row)
initial_volume = fluid_samples[0]["meshVolumeCubicMeters"]
if initial_volume <= 0.0:
    raise RuntimeError("real-impact liquid C12 initial mesh volume is zero")
for row in fluid_samples:
    row["temporalVolumeDriftFraction"] = round(row["meshVolumeCubicMeters"] / initial_volume - 1.0, 8)

initial_centroid = Vector(fluid_samples[0]["centroidCupLocalMeters"])
maximum_centroid_shift = max((Vector(row["centroidCupLocalMeters"]) - initial_centroid).length for row in fluid_samples)
precontact_maximum_exterior = max(row["outsideCupInteriorPlusOneVoxelFraction"] for row in fluid_samples if row["frame"] < contact_frame)
first_significant_spill_frame = next((row["frame"] for row in fluid_samples if row["frame"] > contact_frame and row["outsideCupInteriorPlusOneVoxelFraction"] >= SIGNIFICANT_SPILL_FRACTION), None)
postcontact_maximum_exterior = max(row["outsideCupInteriorPlusOneVoxelFraction"] for row in fluid_samples if row["frame"] > contact_frame)
final_exterior_fraction = fluid_samples[-1]["outsideCupInteriorPlusOneVoxelFraction"]

expected_cache_files = sorted(
    [f"config/config_{frame:04d}.uni" for frame in range(FRAME_START, FRAME_END + 1)]
    + [f"data/fluid_data_{frame:04d}.vdb" for frame in range(FRAME_START, FRAME_END + 1)]
    + [f"mesh/fluid_mesh_{frame:04d}.bobj.gz" for frame in range(FRAME_START, FRAME_END + 1)]
)
actual_cache_files = sorted(str(path.relative_to(cache_root)) for path in cache_root.rglob("*") if path.is_file())
maximum_source_error = max(abs(row["sourceVolumeErrorFraction"]) for row in fluid_samples)
maximum_temporal_drift = max(abs(row["temporalVolumeDriftFraction"]) for row in fluid_samples)
maximum_world_below_floor = max(row["worldBelowFloorFraction"] for row in fluid_samples)
maximum_cup_solid_intrusion = max(row["cupSolidIntrusionFraction"] for row in fluid_samples)
maximum_ramp_solid_intrusion = max(row["rampSolidIntrusionFraction"] for row in fluid_samples)
maximum_domain_outside = max(row["domainOutsideOneVoxelInsetFraction"] for row in fluid_samples)
maximum_positive_bodies = max(row["positiveBodyCount"] for row in fluid_samples)
minimum_positive_bodies = min(row["positiveBodyCount"] for row in fluid_samples)
maximum_components = max(row["connectedComponentCount"] for row in fluid_samples)
minimum_largest_component = min(row["largestComponentFraction"] for row in fluid_samples)

pusher_keyframes = sorted({round(point.co.x) for curve in action_curves(pusher) for point in curve.keyframe_points})
support_effectors_exact = (
    floor_modifier.fluid_type == "EFFECTOR"
    and ramp_fluid.fluid_type == "EFFECTOR"
    and floor.rigid_body is not None and floor.rigid_body.type == "PASSIVE"
    and ramp.rigid_body is not None and ramp.rigid_body.type == "PASSIVE"
    and all(abs(item.surface_distance - 2.0) <= 1e-6 and item.use_effector and not item.use_plane_init and item.subframes == 0 for item in (floor_effector, ramp_effector))
)
checks = {
    "exactRetainedR40SameSolveBeforeFluid": maximum_location_delta <= 1e-5 and maximum_rotation_delta_degrees <= 1e-4 and maximum_ball_location_delta <= 1e-5,
    "exactRetainedR40SameSolveAfterFluid": maximum_post_fluid_cup_location_delta <= 1e-5 and maximum_post_fluid_cup_rotation_delta_degrees <= 1e-4 and maximum_post_fluid_ball_location_delta <= 1e-5,
    "derivedCausalEventWindowExact": contact_frame == 19 and first_seventy_frame == 36,
    "derivedEffectorSubframesExact": required_effector_subframes == 8 and effector.subframes == 8,
    "cupCollisionMarginExplicitTwoMillimeters": cup.rigid_body.use_margin and abs(cup.rigid_body.collision_margin - 0.002) <= 1e-6,
    "passiveRampExact": ramp_exact,
    "floorAndRampStaticFluidEffectorsExact": support_effectors_exact,
    "pusherOnlyAuthoredRigidActuator": animated_rigid_bodies == ["PHYS_VISIBLE_STRIKER"] and pusher_keyframes == [1, 9, 10, 12],
    "zeroBallCupOutcomePoseAuthority": not action_curves(cup) and not action_curves(ball),
    "exactCacheFrameRoster": actual_cache_files == expected_cache_files,
    "liquidMeshEveryFrame": len(fluid_samples) == 36 and all(row["vertexCount"] > 0 for row in fluid_samples),
    "sourceRelativeVolumeWithin25Percent": maximum_source_error <= 0.25,
    "temporalVolumeDriftWithin15Percent": maximum_temporal_drift <= 0.15,
    "positiveLiquidBodiesBounded": minimum_positive_bodies >= 1 and maximum_positive_bodies <= 16,
    "manifoldEveryFrame": max(row["nonManifoldEdgeCount"] for row in fluid_samples) == 0,
    "largestComponentAtLeastHalf": minimum_largest_component >= 0.5,
    "connectedComponentsBounded": maximum_components <= 32,
    "precontactLiquidContained": precontact_maximum_exterior < SIGNIFICANT_SPILL_FRACTION,
    "significantSpillDerivedAfterContact": first_significant_spill_frame is not None and first_significant_spill_frame > contact_frame and postcontact_maximum_exterior >= SIGNIFICANT_SPILL_FRACTION,
    "spillPersistsAtEventBoundary": final_exterior_fraction >= SIGNIFICANT_SPILL_FRACTION,
    "impactMovesLiquidRelativeToCup": maximum_centroid_shift >= 0.025,
    "worldFloorIntrusionWithinOnePercent": maximum_world_below_floor <= 0.01,
    "cupSolidIntrusionWithinOnePercent": maximum_cup_solid_intrusion <= 0.01,
    "rampSolidIntrusionWithinOnePercent": maximum_ramp_solid_intrusion <= 0.01,
    "liquidInsideDomainOneVoxelInset": maximum_domain_outside == 0.0,
    "singleInitialGeometryFlow": flow.flow_behavior == "GEOMETRY" and not source.animation_data,
    "previewTierExact": (
        settings.resolution_max == 96 and settings.cache_frame_start == 1 and settings.cache_frame_end == 36
        and settings.simulation_method == "APIC" and settings.timesteps_min == 2 and settings.timesteps_max == 4
        and abs(settings.cfl_condition - 2.0) <= 1e-6 and settings.particle_number == 2
        and settings.particle_min == 8 and settings.particle_max == 16
        and abs(settings.particle_radius - 1.8) <= 1e-6 and abs(settings.particle_band_width - 4.0) <= 1e-6
        and settings.use_fractions and abs(settings.fractions_threshold - 0.05) <= 1e-6
        and abs(settings.fractions_distance - 0.25) <= 1e-6 and abs(settings.mesh_particle_radius - 2.5) <= 1e-6
        and abs(effector.surface_distance - 2.0) <= 1e-6 and effector.subframes == 8
    ),
}
result = {
    "schemaVersion": "bfs.rc6RealImpactLiquidPreviewC12Result.v0.1",
    "status": "PASS" if all(checks.values()) else "FAIL",
    "verdict": "PASS_REAL_IMPACT_LIQUID_PREVIEW" if all(checks.values()) else "FAIL_REAL_IMPACT_LIQUID_PREVIEW",
    "configuration": {
        "frameStart": 1, "frameEnd": 36, "fps": 24, "resolutionMax": 96,
        "domainCenterMeters": [float(value) for value in DOMAIN_CENTER],
        "domainDimensionsMeters": [float(value) for value in DOMAIN_DIMENSIONS],
        "baseVoxelMeters": BASE_VOXEL_METERS,
        "trajectoryCellId": "R40", "driveEndFrame": 9,
        "bulletSubstepsPerFrame": 20, "bulletSolverIterations": 80,
        "cupCollisionMarginMeters": float(cup.rigid_body.collision_margin),
        "cupFriction": float(cup.rigid_body.friction),
        "rampRunMeters": 0.30, "rampRiseMeters": 0.04,
        "rampSurfaceStartZ": 0.22, "rampSurfaceEndZ": 0.26,
        "simulationMethod": settings.simulation_method,
        "particleNumber": int(settings.particle_number), "particleMinimum": int(settings.particle_min),
        "particleMaximum": int(settings.particle_max), "particleRadius": float(settings.particle_radius),
        "particleBandWidth": float(settings.particle_band_width), "meshParticleRadius": float(settings.mesh_particle_radius),
        "meshScale": int(settings.mesh_scale), "meshConcaveLower": float(settings.mesh_concave_lower),
        "meshConcaveUpper": float(settings.mesh_concave_upper), "meshSmoothenPos": int(settings.mesh_smoothen_pos),
        "meshSmoothenNeg": int(settings.mesh_smoothen_neg), "fractionsThreshold": float(settings.fractions_threshold),
        "fractionsDistance": float(settings.fractions_distance), "cupEffectorSurfaceDistanceCells": float(effector.surface_distance),
        "cupEffectorSubframes": int(effector.subframes), "staticSupportEffectorSurfaceDistanceCells": 2.0,
        "staticSupportEffectorSubframes": 0, "timestepsMin": int(settings.timesteps_min),
        "timestepsMax": int(settings.timesteps_max), "cflCondition": float(settings.cfl_condition),
        "sourceMeshVolumeCubicMeters": source_volume, "significantSpillFraction": SIGNIFICANT_SPILL_FRACTION,
    },
    "provenance": {
        "animatedRigidBodies": animated_rigid_bodies,
        "pusherKeyframes": pusher_keyframes,
        "cupActionCurveCount": len(action_curves(cup)),
        "ballActionCurveCount": len(action_curves(ball)),
        "sourceCupUseMargin": source_cup_use_margin,
        "sourceCupCollisionMarginMeters": source_cup_collision_margin,
        "floorAndRampStaticFluidEffectorsExact": support_effectors_exact,
    },
    "metrics": {
        "derivedContactFrame": contact_frame, "derivedFirstSeventyDegreeFrame": first_seventy_frame,
        "maximumCupSurfaceDisplacementPerFrameMeters": maximum_surface_displacement,
        "requiredEffectorSubframes": required_effector_subframes,
        "maximumR40CupLocationDeltaBeforeFluidMeters": maximum_location_delta,
        "maximumR40CupRotationDeltaBeforeFluidDegrees": maximum_rotation_delta_degrees,
        "maximumR40BallLocationDeltaBeforeFluidMeters": maximum_ball_location_delta,
        "maximumR40CupLocationDeltaAfterFluidMeters": maximum_post_fluid_cup_location_delta,
        "maximumR40CupRotationDeltaAfterFluidDegrees": maximum_post_fluid_cup_rotation_delta_degrees,
        "maximumR40BallLocationDeltaAfterFluidMeters": maximum_post_fluid_ball_location_delta,
        "maximumAbsoluteSourceVolumeErrorFraction": maximum_source_error,
        "maximumAbsoluteTemporalVolumeDriftFraction": maximum_temporal_drift,
        "minimumPositiveBodyCount": minimum_positive_bodies, "maximumPositiveBodyCount": maximum_positive_bodies,
        "maximumConnectedComponentCount": maximum_components, "minimumLargestComponentFraction": minimum_largest_component,
        "precontactMaximumExteriorFraction": precontact_maximum_exterior,
        "firstSignificantSpillFrame": first_significant_spill_frame,
        "postcontactMaximumExteriorFraction": postcontact_maximum_exterior,
        "frame36ExteriorFraction": final_exterior_fraction,
        "maximumLiquidCentroidShiftCupLocalMeters": maximum_centroid_shift,
        "maximumWorldBelowFloorFraction": maximum_world_below_floor,
        "maximumCupSolidIntrusionFraction": maximum_cup_solid_intrusion,
        "maximumRampSolidIntrusionFraction": maximum_ramp_solid_intrusion,
        "maximumDomainOutsideOneVoxelInsetFraction": maximum_domain_outside,
        "bulletBakeSeconds": bullet_seconds, "fluidDataBakeSeconds": data_seconds, "fluidMeshBakeSeconds": mesh_seconds,
    },
    "bulletSamples": bullet_samples,
    "postFluidBulletSamples": post_fluid_bullet_samples,
    "fluidSamples": fluid_samples,
    "cache": {"root": str(cache_root), "fileCount": len(actual_cache_files), "files": actual_cache_files},
    "checks": checks, "checkCount": len(checks), "passCount": sum(checks.values()),
    "counts": {"blenderStarts": 1, "bulletBakes": 1, "fluidDataBakes": 1, "fluidMeshBakes": 1, "renders": 0, "blendSaves": 0, "networkCalls": 0, "engineRemoteWrites": 0},
    "claimCeiling": "One 36-frame Preview-96 same-solve R40 basketball-impact/APIC spill result with explicit floor/ramp effectors; no full landing, persistence, final resolution, render, film quality, deformation or generalized liquid claim.",
}
result["resultHash"] = self_hash(result, "resultHash")
write_exclusive(result_path, result)
print("RC6_REAL_IMPACT_LIQUID_PREVIEW=" + canonical({"status": result["status"], "resultHash": result["resultHash"], "metrics": result["metrics"]}), flush=True)
'''
    source = source[:tail_start] + tail
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#RC6_REAL_IMPACT_LIQUID_PREVIEW_C12", "exec"), globals(), globals())
