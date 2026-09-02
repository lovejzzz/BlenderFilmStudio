#!/usr/bin/env python3
"""Adapt the frozen attempt-56 scene to Data-only full FLIP-particle diagnosis."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-moving-liquid-preview-scene.py")
EXPECTED_BASE_SHA256 = "ac6531b62b0c329d69dd969f650f6b2345199343f803d1ee63dae11813237a36"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("moving-liquid Data diagnostic scene base identity mismatch")


source = BASE.read_text(encoding="utf-8")


def replace_once(before, after, label):
    global source
    if source.count(before) != 1:
        raise RuntimeError(f"moving-liquid Data diagnostic {label} target mismatch")
    source = source.replace(before, after)


def replace_span(start, end, replacement, label):
    global source
    if source.count(start) != 1 or source.count(end) != 1:
        raise RuntimeError(f"moving-liquid Data diagnostic {label} span mismatch")
    first = source.index(start)
    last = source.index(end, first)
    source = source[:first] + replacement + source[last:]


def replace_span_inclusive(start, end, replacement, label):
    global source
    if source.count(start) != 1 or source.count(end) != 1:
        raise RuntimeError(f"moving-liquid Data diagnostic {label} inclusive span mismatch")
    first = source.index(start)
    last = source.index(end, first) + len(end)
    source = source[:first] + replacement + source[last:]


particle_helper = '''def particle_quality(domain, cup):
    evaluated = domain.evaluated_get(bpy.context.evaluated_depsgraph_get())
    if len(evaluated.particle_systems) != 1:
        raise RuntimeError("moving-liquid Data diagnostic evaluated FLIP roster mismatch")
    particles = list(evaluated.particle_systems[0].particles)
    if not particles:
        raise RuntimeError("moving-liquid Data diagnostic produced zero FLIP particles")
    states = {}
    for particle in particles:
        states[particle.alive_state] = states.get(particle.alive_state, 0) + 1
    alive = [particle for particle in particles if particle.alive_state == "ALIVE"]
    if not alive:
        raise RuntimeError("moving-liquid Data diagnostic produced zero ALIVE particles")
    world_to_cup = cup.matrix_world.inverted_safe()
    local_points = [world_to_cup @ particle.location for particle in alive]
    radial_limit = CUP_INNER_RADIUS_METERS + BASE_VOXEL_METERS
    bottom_limit = CUP_INTERIOR_BOTTOM_LOCAL_Z - BASE_VOXEL_METERS
    top_limit = CUP_INTERIOR_TOP_LOCAL_Z + BASE_VOXEL_METERS
    radial = sum(math.hypot(point.x, point.y) > radial_limit for point in local_points)
    below = sum(point.z < bottom_limit for point in local_points)
    above = sum(point.z > top_limit for point in local_points)
    outside = sum(
        math.hypot(point.x, point.y) > radial_limit or point.z < bottom_limit or point.z > top_limit
        for point in local_points
    )
    speeds = [particle.velocity.length for particle in alive]
    count = len(alive)
    return {
        "particleCount": len(particles),
        "aliveParticleCount": count,
        "aliveStateCounts": states,
        "outsideCupInteriorPlusOneVoxelCount": outside,
        "outsideCupInteriorPlusOneVoxelFraction": round(outside / count, 10),
        "radialOutsideCount": radial,
        "radialOutsideFraction": round(radial / count, 10),
        "belowFloorCount": below,
        "belowFloorFraction": round(below / count, 10),
        "aboveRimCount": above,
        "aboveRimFraction": round(above / count, 10),
        "centroidCupLocalMeters": [round(sum(point[axis] for point in local_points) / count, 10) for axis in range(3)],
        "boundsMinCupLocalMeters": [round(min(point[axis] for point in local_points), 10) for axis in range(3)],
        "boundsMaxCupLocalMeters": [round(max(point[axis] for point in local_points), 10) for axis in range(3)],
        "maximumRnaSpeedMetersPerSecond": round(max(speeds), 10),
        "meanRnaSpeedMetersPerSecond": round(sum(speeds) / count, 10),
    }


'''
replace_once("parser = argparse.ArgumentParser()\n", particle_helper + "parser = argparse.ArgumentParser()\n", "particle helper")
replace_once(
    '''flow = flow_modifier.flow_settings
if settings.domain_type != "LIQUID" or settings.simulation_method != "APIC" or flow.flow_behavior != "GEOMETRY":''',
    '''flow = flow_modifier.flow_settings
initial_use_flip_particles = bool(settings.use_flip_particles)
initial_particle_system_count = len(domain.particle_systems)
if not initial_use_flip_particles or initial_particle_system_count != 1:
    raise RuntimeError("moving-liquid Data diagnostic source FLIP roster mismatch")
if settings.domain_type != "LIQUID" or settings.simulation_method != "APIC" or flow.flow_behavior != "GEOMETRY":''',
    "initial FLIP roster",
)
replace_once("settings.use_mesh = True\n", "settings.use_mesh = False\n", "disable Mesh")
replace_once(
    '''data_started = time.monotonic()
with bpy.context.temp_override(**context):
    if "FINISHED" not in bpy.ops.fluid.bake_data():
        raise RuntimeError("moving-liquid Preview Data bake did not finish")
data_seconds = time.monotonic() - data_started
mesh_started = time.monotonic()
with bpy.context.temp_override(**context):
    if "FINISHED" not in bpy.ops.fluid.bake_mesh():
        raise RuntimeError("moving-liquid Preview Mesh bake did not finish")
mesh_seconds = time.monotonic() - mesh_started
''',
    '''domain.particle_systems[0].settings.display_percentage = 100
data_started = time.monotonic()
with bpy.context.temp_override(**context):
    if "FINISHED" not in bpy.ops.fluid.bake_data():
        raise RuntimeError("moving-liquid Data diagnostic Data bake did not finish")
data_seconds = time.monotonic() - data_started
if len(domain.particle_systems) != 1:
    raise RuntimeError("moving-liquid Data diagnostic post-bake FLIP roster mismatch")
domain.particle_systems[0].settings.display_percentage = 100
mesh_seconds = 0.0
''',
    "Data-only bake",
)

sample_block = '''particle_samples = []
for frame in range(FRAME_START, FRAME_END + 1):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    row = particle_quality(domain, cup)
    row["frame"] = frame
    row["cupTiltDegrees"] = round(tilt_degrees(cup), 8)
    particle_samples.append(row)
initial_alive_count = particle_samples[0]["aliveParticleCount"]
initial_centroid = Vector(particle_samples[0]["centroidCupLocalMeters"])
for row in particle_samples:
    row["aliveCountRatioToFrame1"] = round(row["aliveParticleCount"] / initial_alive_count, 10)
    row["aliveCountDriftFraction"] = round(row["aliveParticleCount"] / initial_alive_count - 1.0, 10)
    row["constantMassParticleVolumeProxyCubicMeters"] = round(source_volume * row["aliveParticleCount"] / initial_alive_count, 12)
maximum_centroid_shift = max((Vector(row["centroidCupLocalMeters"]) - initial_centroid).length for row in particle_samples)

'''
replace_span("fluid_samples = []\n", "expected_cache_files = sorted(\n", sample_block, "particle samples")
replace_once(
    '''    + [f"mesh/fluid_mesh_{frame:04d}.bobj.gz" for frame in range(FRAME_START, FRAME_END + 1)]
''',
    "",
    "Data-only cache roster",
)

diagnostic_tail = '''minimum_alive_ratio = min(row["aliveCountRatioToFrame1"] for row in particle_samples)
maximum_alive_count_drift = max(abs(row["aliveCountDriftFraction"]) for row in particle_samples)
maximum_particle_outside_fraction = max(row["outsideCupInteriorPlusOneVoxelFraction"] for row in particle_samples)
if maximum_particle_outside_fraction > 0.01:
    classification = "DATA_PARTICLE_CONTAINMENT_FAILURE"
elif maximum_alive_count_drift > 0.15:
    classification = "DATA_PARTICLE_COUNT_DRIFT_SIGNAL"
else:
    classification = "DATA_PARTICLE_COUNT_STABLE_SURFACE_RECONSTRUCTION_SUSPECTED"
checks = {
    "exactAcceptedC5F96Trajectory": maximum_location_delta <= 1e-5 and maximum_rotation_delta_degrees <= 1e-4,
    "solverOwnedCupMotionPresent": bullet_samples[-1]["cupTiltDegrees"] >= 14.0 and not action_curves(cup),
    "hingeAndMotorExact": hinge.rigid_body_constraint.type == "HINGE" and motor.rigid_body_constraint.type == "MOTOR" and abs(motor.rigid_body_constraint.motor_ang_target_velocity + math.radians(MOTOR_DEGREES_PER_SECOND)) <= 1e-6 and abs(motor.rigid_body_constraint.motor_ang_max_impulse - 1.0) <= 1e-6,
    "hingePivotStable": maximum_pivot_drift <= 0.005,
    "exactDataCacheFrameRoster": actual_cache_files == expected_cache_files and len(actual_cache_files) == 48,
    "singleFlipParticleSystemEveryFrame": len(particle_samples) == 24 and all(row["particleCount"] > 0 and row["aliveParticleCount"] > 0 for row in particle_samples),
    "allParticleStatesBound": all(sum(row["aliveStateCounts"].values()) == row["particleCount"] for row in particle_samples),
    "particleCountProxyMeasured": initial_alive_count > 0 and minimum_alive_ratio > 0.0,
    "singleInitialGeometryFlow": flow.flow_behavior == "GEOMETRY" and not source.animation_data,
    "zeroOutcomePoseAuthority": not action_curves(cup) and not action_curves(ball) and not action_curves(pusher),
    "previewDataTierExact": settings.resolution_max == RESOLUTION and settings.cache_frame_start == FRAME_START and settings.cache_frame_end == FRAME_END and abs(settings.particle_radius - 1.6) <= 1e-6 and not settings.use_mesh and effector.subframes == 1,
}
result = {
    "schemaVersion": "bfs.rc6MovingLiquidDataDiagnosticResult.v0.1",
    "status": "MEASURED_DATA_ONLY" if all(checks.values()) else "FAIL_HARNESS",
    "classification": classification if all(checks.values()) else "INCONCLUSIVE_HARNESS_FAILURE",
    "configuration": {
        "frameStart": FRAME_START,
        "frameEnd": FRAME_END,
        "resolutionMax": RESOLUTION,
        "domainCenterMeters": [float(value) for value in DOMAIN_CENTER],
        "domainDimensionsMeters": [float(value) for value in DOMAIN_DIMENSIONS],
        "baseVoxelMeters": BASE_VOXEL_METERS,
        "trajectoryCellId": "C5F96",
        "driveEndFrame": DRIVE_END_FRAME,
        "motorTargetDegreesPerSecond": round(MOTOR_DEGREES_PER_SECOND, 8),
        "particleNumber": 2,
        "particleRadius": 1.6,
        "useMesh": False,
        "useFlipParticles": bool(settings.use_flip_particles),
        "initialUseFlipParticles": initial_use_flip_particles,
        "initialParticleSystemCount": initial_particle_system_count,
        "finalParticleSystemCount": len(domain.particle_systems),
        "displayPercentage": domain.particle_systems[0].settings.display_percentage,
        "cupEffectorSurfaceDistanceCells": 2.5,
        "cupEffectorSubframes": 1,
        "sourceMeshVolumeCubicMeters": source_volume,
    },
    "metrics": {
        "initialAliveParticleCount": initial_alive_count,
        "finalAliveParticleCount": particle_samples[-1]["aliveParticleCount"],
        "minimumAliveCountRatioToFrame1": minimum_alive_ratio,
        "maximumAbsoluteAliveCountDriftFraction": maximum_alive_count_drift,
        "maximumParticleOutsideCupPlusOneVoxelFraction": maximum_particle_outside_fraction,
        "maximumRadialOutsideFraction": max(row["radialOutsideFraction"] for row in particle_samples),
        "maximumBelowFloorFraction": max(row["belowFloorFraction"] for row in particle_samples),
        "maximumAboveRimFraction": max(row["aboveRimFraction"] for row in particle_samples),
        "maximumParticleCentroidShiftCupLocalMeters": maximum_centroid_shift,
        "maximumAcceptedTrajectoryLocationDeltaMeters": maximum_location_delta,
        "maximumAcceptedTrajectoryRotationDeltaDegrees": maximum_rotation_delta_degrees,
        "maximumHingePivotDriftMeters": maximum_pivot_drift,
        "bulletBakeSeconds": bullet_seconds,
        "fluidDataBakeSeconds": data_seconds,
        "fluidMeshBakeSeconds": mesh_seconds,
    },
    "bulletSamples": bullet_samples,
    "particleSamples": particle_samples,
    "cache": {"root": str(cache_root), "fileCount": len(actual_cache_files), "files": actual_cache_files},
    "checks": checks,
    "checkCount": len(checks),
    "passCount": sum(checks.values()),
    "interpretationRules": {
        "particleContainmentFailure": "maximum one-voxel particle exterior fraction exceeds 1%",
        "particleCountDriftSignal": "absolute ALIVE count drift from frame 1 exceeds 15%; count is a constant-per-particle mass proxy, not an exact geometric volume",
        "surfaceReconstructionSuspected": "particle containment passes and ALIVE count stays within 15% while retained attempt-56 Mesh volume drift exceeded 15%",
    },
    "counts": {"blenderStarts": 1, "bulletBakes": 1, "fluidDataBakes": 1, "fluidMeshBakes": 0, "renders": 0, "blendSaves": 0, "networkCalls": 0, "engineRemoteWrites": 0},
    "claimCeiling": "One 24-frame Preview-96 Data-only FLIP-particle diagnosis on exact attempt-56 physics. Particle count is a mass proxy, not exact volume. No moving-liquid PASS, parameter correction, full tip, spill, impact, persistence, render or film-quality claim.",
}
result["resultHash"] = self_hash(result, "resultHash")
write_exclusive(result_path, result)
print("RC6_MOVING_LIQUID_DATA_DIAGNOSTIC=" + canonical({"status": result["status"], "classification": result["classification"], "resultHash": result["resultHash"], "metrics": result["metrics"]}), flush=True)
if result["status"] != "MEASURED_DATA_ONLY":
    raise RuntimeError("moving-liquid Data diagnostic harness checks failed")
'''
replace_span_inclusive(
    "maximum_source_error =",
    'if result["status"] != "PASS":\n    raise RuntimeError("moving-liquid Preview thresholds failed")',
    diagnostic_tail,
    "diagnostic result",
)
source = source.replace('"""Bake one bounded Preview-96 liquid window on the accepted C5F96 trajectory."""', '"""Bake one Data-only FLIP diagnostic on the accepted C5F96 trajectory."""', 1)
exec(compile(source, str(BASE) + "#MOVING_LIQUID_DATA_DIAGNOSTIC_V01", "exec"), globals(), globals())
