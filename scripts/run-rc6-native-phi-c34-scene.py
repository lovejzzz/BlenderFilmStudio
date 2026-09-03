#!/usr/bin/env python3
"""Bake exact C29 Data once with resumable native fields; never bake Mesh."""

import hashlib
import importlib.util
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-real-impact-liquid-particle-band-width-c29-scene.py")
EXPECTED_BASE_SHA256 = "1cf1adf4dee9bd2bb7e618b0c80ed931510ae847114202fbdfe35649adb97358"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("C34 exact C29 scene identity mismatch")
    module_spec = importlib.util.spec_from_file_location("rc6_c29_scene", BASE)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    source = module.transformed_source()

    anchor = 'settings.cache_data_format = "OPENVDB"'
    replacement = anchor + "\nsettings.cache_resumable = True"
    if source.count(anchor) != 1:
        raise RuntimeError("C34 resumable setting anchor mismatch")
    source = source.replace(anchor, replacement)

    tail_start = source.index("data_started = time.monotonic()")
    tail = r'''data_started = time.monotonic()
with bpy.context.temp_override(**context):
    if "FINISHED" not in bpy.ops.fluid.bake_data():
        raise RuntimeError("C34 Data bake did not finish")
data_seconds = time.monotonic() - data_started

post_fluid_bullet_samples = []
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

expected_cache_files = sorted(
    [f"config/config_{frame:04d}.uni" for frame in range(FRAME_START, FRAME_END + 1)]
    + [f"data/fluid_data_{frame:04d}.vdb" for frame in range(FRAME_START, FRAME_END + 1)]
)
actual_cache_files = sorted(str(path.relative_to(cache_root)) for path in cache_root.rglob("*") if path.is_file())
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
    "exactDataOnlyCacheFrameRoster": actual_cache_files == expected_cache_files,
    "resumableNativeExportEnabled": bool(settings.cache_resumable),
    "noMeshDirectoryOrFiles": not (cache_root / "mesh").exists() and not any(path.suffix in {".bobj", ".gz"} for path in cache_root.rglob("*")),
    "singleInitialGeometryFlow": flow.flow_behavior == "GEOMETRY" and not source.animation_data,
    "exactC29PreviewConfiguration": (
        settings.resolution_max == 96 and settings.cache_frame_start == 1 and settings.cache_frame_end == 36
        and all(abs(float(DOMAIN_CENTER[index]) - expected) <= 1e-6 for index, expected in enumerate((0.57, 0.0, 0.26)))
        and all(abs(float(DOMAIN_DIMENSIONS[index]) - expected) <= 1e-6 for index, expected in enumerate((0.9, 0.5, 0.58)))
        and settings.simulation_method == "APIC" and settings.timesteps_min == 2 and settings.timesteps_max == 8
        and abs(settings.cfl_condition - 2.0) <= 1e-6 and settings.particle_number == 2
        and settings.particle_min == 8 and settings.particle_max == 16
        and abs(settings.particle_radius - 1.8) <= 1e-6 and abs(settings.particle_band_width - 3.0) <= 1e-6
        and settings.use_fractions and abs(settings.fractions_threshold - 0.10) <= 1e-6
        and abs(settings.fractions_distance - 0.25) <= 1e-6 and abs(settings.mesh_particle_radius - 2.5) <= 1e-6
        and abs(effector.surface_distance - 2.0) <= 1e-6 and effector.subframes == 8
        and settings.cache_type == "MODULAR" and settings.cache_data_format == "OPENVDB"
    ),
}
result = {
    "schemaVersion": "bfs.rc6NativePhiC34SceneResult.v1",
    "status": "PASS_DATA_BAKE" if all(checks.values()) else "FAIL",
    "configuration": {
        "frameStart": 1, "frameEnd": 36, "fps": 24, "resolutionMax": 96,
        "domainCenterMeters": [float(value) for value in DOMAIN_CENTER],
        "domainDimensionsMeters": [float(value) for value in DOMAIN_DIMENSIONS],
        "baseVoxelMeters": BASE_VOXEL_METERS, "trajectoryCellId": "R40", "driveEndFrame": 9,
        "bulletSubstepsPerFrame": 20, "bulletSolverIterations": 80,
        "cupUseMargin": bool(cup.rigid_body.use_margin), "cupCollisionMarginMeters": float(cup.rigid_body.collision_margin),
        "cupFriction": float(cup.rigid_body.friction), "simulationMethod": settings.simulation_method,
        "particleNumber": int(settings.particle_number), "particleMinimum": int(settings.particle_min),
        "particleMaximum": int(settings.particle_max), "particleRadius": float(settings.particle_radius),
        "particleBandWidth": float(settings.particle_band_width), "meshParticleRadius": float(settings.mesh_particle_radius),
        "meshScale": int(settings.mesh_scale), "meshConcaveLower": float(settings.mesh_concave_lower),
        "meshConcaveUpper": float(settings.mesh_concave_upper), "meshSmoothenPos": int(settings.mesh_smoothen_pos),
        "meshSmoothenNeg": int(settings.mesh_smoothen_neg), "fractionsThreshold": float(settings.fractions_threshold),
        "fractionsDistance": float(settings.fractions_distance), "cupEffectorSurfaceDistanceCells": float(effector.surface_distance),
        "cupEffectorSubframes": int(effector.subframes), "timestepsMin": int(settings.timesteps_min),
        "timestepsMax": int(settings.timesteps_max), "cflCondition": float(settings.cfl_condition),
        "useFractions": bool(settings.use_fractions), "deleteInObstacle": bool(settings.delete_in_obstacle),
        "sourceMeshVolumeCubicMeters": source_volume, "cacheType": settings.cache_type,
        "cacheDataFormat": settings.cache_data_format, "cacheResumable": bool(settings.cache_resumable),
        "useMeshConfiguredButNotBaked": bool(settings.use_mesh),
    },
    "provenance": {
        "animatedRigidBodies": animated_rigid_bodies, "pusherKeyframes": pusher_keyframes,
        "cupActionCurveCount": len(action_curves(cup)), "ballActionCurveCount": len(action_curves(ball)),
        "sourceCupUseMargin": source_cup_use_margin, "sourceCupCollisionMarginMeters": source_cup_collision_margin,
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
        "bulletBakeSeconds": bullet_seconds, "fluidDataBakeSeconds": data_seconds,
    },
    "bulletSamples": bullet_samples, "postFluidBulletSamples": post_fluid_bullet_samples,
    "cache": {"root": str(cache_root), "fileCount": len(actual_cache_files), "files": actual_cache_files},
    "checks": checks, "checkCount": len(checks), "passCount": sum(checks.values()),
    "counts": {"blenderStarts": 1, "bulletBakes": 1, "fluidDataBakes": 1, "fluidMeshBakes": 0, "renders": 0, "blendSaves": 0, "nativeBuilds": 0, "networkCalls": 0, "engineSourceEdits": 0, "engineRemoteWrites": 0},
    "claimCeiling": "Exact-C29 uninterrupted Preview-96 Data-only bake with resumable native fields. No Mesh, render, physical PASS, exact mass, solver-operation cause, product default or film-quality claim.",
}
result["resultHash"] = self_hash(result, "resultHash")
write_exclusive(result_path, result)
print("RC6_NATIVE_PHI_C34_SCENE=" + canonical({"status": result["status"], "resultHash": result["resultHash"], "metrics": result["metrics"]}), flush=True)
if result["status"] != "PASS_DATA_BAKE":
    raise RuntimeError("C34 scene checks failed")
'''
    return source[:tail_start] + tail


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#RC6_NATIVE_PHI_C34", "exec"), globals(), globals())
