#!/usr/bin/env python3
"""Expose active cached FLIP particles and record every one-voxel outlier."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("inspect-rc6-liquid-flip-particle-axis-scene.py")
EXPECTED_BASE_SHA256 = "7723b976d2e78e53f1d83091f80fbc65e24ee279aeb1aa9f1c5bfb50f73a23c9"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 FLIP-particle detail scene base identity mismatch")


source = BASE.read_text(encoding="utf-8")
replacements = (
    (
        '''    if settings.use_flip_particles or len(domain.particle_systems) != 0:
        raise RuntimeError("FLIP particle system was not initially absent")

    settings.use_flip_particles = True
    bpy.context.view_layer.update()
    if not settings.use_flip_particles or len(domain.particle_systems) != 1:
        raise RuntimeError("FLIP particle system creation failed")''',
        '''    initial_use_flip_particles = bool(settings.use_flip_particles)
    initial_particle_system_count = len(domain.particle_systems)
    if initial_particle_system_count not in (0, 1) or (initial_use_flip_particles and initial_particle_system_count != 1):
        raise RuntimeError("FLIP particle initial roster is not safely interpretable")
    exposure_action = "REUSED_EXISTING_ENABLED_SYSTEM"
    if not initial_use_flip_particles:
        settings.use_flip_particles = True
        exposure_action = "ENABLED_IN_MEMORY_WITH_EXISTING_SYSTEM" if initial_particle_system_count == 1 else "ENABLED_IN_MEMORY_AND_CREATED_SYSTEM"
    bpy.context.view_layer.update()
    if not settings.use_flip_particles or len(domain.particle_systems) != 1:
        raise RuntimeError("FLIP particle system exposure failed")''',
        1,
        "initial roster handling",
    ),
    (
        '''        particles = evaluated_domain.particle_systems[0].particles
        world_points = [particle.location.copy() for particle in particles]
        local_points = [world_to_cup @ point for point in world_points]
        plus_one = count_axes(local_points, BASE_VOXEL_METERS)
        strict = count_axes(local_points, 0.0)
        samples.append({
            "frame": frame,
            "aggregate": plus_one,
            "strictInterior": strict,
            "components": [],
            "boundsMinCupLocal": [round(min(point[axis] for point in local_points), 8) for axis in range(3)],
            "boundsMaxCupLocal": [round(max(point[axis] for point in local_points), 8) for axis in range(3)],
        })''',
        '''        particles = list(evaluated_domain.particle_systems[0].particles)
        world_points = [particle.location.copy() for particle in particles]
        local_points = [world_to_cup @ point for point in world_points]
        plus_one = count_axes(local_points, BASE_VOXEL_METERS)
        strict = count_axes(local_points, 0.0)
        outliers = []
        for display_index, (particle, world_point, local_point) in enumerate(zip(particles, world_points, local_points)):
            radial = (local_point.x * local_point.x + local_point.y * local_point.y) ** 0.5
            radial_out = radial > CUP_INNER_RADIUS_METERS + BASE_VOXEL_METERS
            below_out = local_point.z < CUP_INTERIOR_BOTTOM_LOCAL_Z - BASE_VOXEL_METERS
            above_out = local_point.z > CUP_INTERIOR_TOP_LOCAL_Z + BASE_VOXEL_METERS
            if not (radial_out or below_out or above_out):
                continue
            if radial <= 0.15 and -0.22 <= local_point.z < CUP_INTERIOR_BOTTOM_LOCAL_Z:
                physical_region = "INSIDE_CUP_SOLID_FLOOR"
            elif local_point.z < -0.22:
                physical_region = "BELOW_CUP_OUTER_BOTTOM"
            elif 0.09 < radial <= 0.15 and -0.22 <= local_point.z <= 0.22:
                physical_region = "INSIDE_CUP_SOLID_WALL"
            else:
                physical_region = "OUTSIDE_MODELED_CUP_SOLID"
            velocity = particle.velocity.copy()
            detail = {
                "displayIndex": display_index,
                "aliveState": particle.alive_state,
                "birthTime": round(float(particle.birth_time), 8),
                "dieTime": round(float(particle.die_time), 8),
                "lifetime": round(float(particle.lifetime), 8),
                "size": round(float(particle.size), 8),
                "locationWorld": [round(float(value), 8) for value in world_point],
                "locationCupLocal": [round(float(value), 8) for value in local_point],
                "radialCupLocalMeters": round(radial, 8),
                "velocityRna": [round(float(value), 8) for value in velocity],
                "speedRna": round(velocity.length, 8),
                "radialOutsideOneVoxel": radial_out,
                "belowFloorOneVoxel": below_out,
                "aboveRimOneVoxel": above_out,
                "interiorFloorPenetrationMeters": round(max(0.0, CUP_INTERIOR_BOTTOM_LOCAL_Z - local_point.z), 8),
                "oneVoxelEnvelopePenetrationMeters": round(max(0.0, CUP_INTERIOR_BOTTOM_LOCAL_Z - BASE_VOXEL_METERS - local_point.z), 8),
                "physicalRegion": physical_region,
            }
            detail["detailHash"] = self_hash(detail, "detailHash")
            outliers.append(detail)
        if len(outliers) != plus_one["outsideUnionCount"]:
            raise RuntimeError("FLIP particle outlier detail count mismatch")
        samples.append({
            "frame": frame,
            "aggregate": plus_one,
            "strictInterior": strict,
            "components": [],
            "boundsMinCupLocal": [round(min(point[axis] for point in local_points), 8) for axis in range(3)],
            "boundsMaxCupLocal": [round(max(point[axis] for point in local_points), 8) for axis in range(3)],
            "outliersOneVoxel": outliers,
        })''',
        1,
        "outlier detail",
    ),
    (
        '''            "flipParticleSystemInitiallyAbsent": True,
            "flipParticleSystemExposedInMemory": True,
            "displayPercentage": 100,''',
        '''            "initialUseFlipParticles": initial_use_flip_particles,
            "initialParticleSystemCount": initial_particle_system_count,
            "exposureAction": exposure_action,
            "finalUseFlipParticles": bool(settings.use_flip_particles),
            "finalParticleSystemCount": len(domain.particle_systems),
            "displayPercentage": 100,
            "cupOuterRadiusMeters": 0.15,
            "cupOuterBottomLocalZMeters": -0.22,
            "particleAliveSourceRule": "Blender filters PARTICLE_TYPE_DELETE then marks exposed Mantaflow FLIP particles PARS_ALIVE",''',
        1,
        "observed configuration",
    ),
    ("bfs.rc6LiquidFlipParticleAxisDiagnostic.v0.1", "bfs.rc6LiquidFlipParticleDetailDiagnostic.v0.3", 1, "schema"),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"RC6 FLIP-particle detail scene {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#FLIP_PARTICLE_DETAIL_SCENE_V03", "exec"), globals(), globals())
