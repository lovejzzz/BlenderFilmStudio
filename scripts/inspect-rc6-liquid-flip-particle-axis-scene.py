#!/usr/bin/env python3
"""Expose cached FLIP particles in memory and classify their cup-local positions."""

import argparse
import hashlib
import json
from pathlib import Path

import bpy


BASE_VOXEL_METERS = 0.5 / 192.0
CUP_INNER_RADIUS_METERS = 0.09
CUP_INTERIOR_BOTTOM_LOCAL_Z = -0.16
CUP_INTERIOR_TOP_LOCAL_Z = 0.22


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def self_hash(value, field):
    body = dict(value)
    body.pop(field, None)
    return hashlib.sha256(canonical(body).encode()).hexdigest()


def write_exclusive(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def arguments():
    values = []
    if "--" in __import__("sys").argv:
        values = __import__("sys").argv[__import__("sys").argv.index("--") + 1 :]
    parser = argparse.ArgumentParser()
    parser.add_argument("--work-root", required=True)
    parser.add_argument("--evidence-root", required=True)
    parser.add_argument("--retained-candidate-manifest-hash", required=True)
    return parser.parse_args(values)


def expected_cache_files():
    return sorted(
        [f"config/config_{frame:04d}.uni" for frame in range(1, 8)]
        + [f"data/fluid_data_{frame:04d}.vdb" for frame in range(1, 8)]
        + [f"mesh/fluid_mesh_{frame:04d}.bobj.gz" for frame in range(1, 8)]
    )


def count_axes(local_points, margin):
    radial_limit = CUP_INNER_RADIUS_METERS + margin
    bottom_limit = CUP_INTERIOR_BOTTOM_LOCAL_Z - margin
    top_limit = CUP_INTERIOR_TOP_LOCAL_Z + margin
    combinations = {name: 0 for name in ("inside", "radialOnly", "belowOnly", "aboveOnly", "radialAndBelow", "radialAndAbove", "belowAndAbove", "allThree")}
    radial = below = above = outside = 0
    for point in local_points:
        is_radial = (point.x * point.x + point.y * point.y) ** 0.5 > radial_limit
        is_below = point.z < bottom_limit
        is_above = point.z > top_limit
        radial += is_radial
        below += is_below
        above += is_above
        outside += is_radial or is_below or is_above
        key = {
            (False, False, False): "inside", (True, False, False): "radialOnly",
            (False, True, False): "belowOnly", (False, False, True): "aboveOnly",
            (True, True, False): "radialAndBelow", (True, False, True): "radialAndAbove",
            (False, True, True): "belowAndAbove", (True, True, True): "allThree",
        }[(is_radial, is_below, is_above)]
        combinations[key] += 1
    count = len(local_points)
    if count == 0:
        raise RuntimeError("FLIP particle axis diagnostic found zero particles")
    return {
        "vertexCount": count,
        "particleCount": count,
        "radialCount": radial,
        "belowFloorCount": below,
        "aboveRimCount": above,
        "outsideUnionCount": outside,
        "radialFraction": round(radial / count, 8),
        "belowFloorFraction": round(below / count, 8),
        "aboveRimFraction": round(above / count, 8),
        "outsideUnionFraction": round(outside / count, 8),
        "exclusiveCombinations": combinations,
        "marginMeters": round(margin, 10),
    }


def main():
    args = arguments()
    work_root = Path(args.work_root).resolve()
    evidence_root = Path(args.evidence_root).resolve()
    candidate_root = work_root / "axis-control"
    expected_blend = candidate_root / "mesh-reconstructed-state.blend"
    cache_root = candidate_root / "mantaflow-cache"
    if Path(bpy.data.filepath).resolve() != expected_blend:
        raise RuntimeError("FLIP particle copied blend path mismatch")
    cache_files = sorted(str(path.relative_to(cache_root)) for path in cache_root.rglob("*") if path.is_file())
    if cache_files != expected_cache_files():
        raise RuntimeError("FLIP particle cache roster mismatch")

    scene = bpy.context.scene
    domain = bpy.data.objects.get("PHYS_LIQUID_DOMAIN")
    cup = bpy.data.objects.get("PHYS_OPEN_TUMBLER")
    if domain is None or cup is None:
        raise RuntimeError("FLIP particle scene identity incomplete")
    modifier = next((item for item in domain.modifiers if item.type == "FLUID" and item.fluid_type == "DOMAIN"), None)
    cup_modifier = next((item for item in cup.modifiers if item.type == "FLUID" and item.fluid_type == "EFFECTOR"), None)
    if modifier is None or cup_modifier is None:
        raise RuntimeError("FLIP particle modifier identity incomplete")
    settings = modifier.domain_settings
    if Path(bpy.path.abspath(settings.cache_directory)).resolve() != cache_root:
        raise RuntimeError("FLIP particle relative cache root mismatch")
    if settings.cache_type != "MODULAR" or not settings.has_cache_baked_data or not settings.has_cache_baked_mesh:
        raise RuntimeError("FLIP particle baked flags mismatch")
    if settings.resolution_max != 192 or settings.cache_frame_start != 1 or settings.cache_frame_end != 7:
        raise RuntimeError("FLIP particle frozen range mismatch")
    if abs(settings.particle_radius - 1.6) > 1e-6 or settings.particle_number != 2 or abs(settings.mesh_particle_radius - 9.0) > 1e-6:
        raise RuntimeError("FLIP particle frozen setting mismatch")
    if settings.use_flip_particles or len(domain.particle_systems) != 0:
        raise RuntimeError("FLIP particle system was not initially absent")

    settings.use_flip_particles = True
    bpy.context.view_layer.update()
    if not settings.use_flip_particles or len(domain.particle_systems) != 1:
        raise RuntimeError("FLIP particle system creation failed")
    particle_system = domain.particle_systems[0]
    particle_system.settings.display_percentage = 100
    if particle_system.settings.display_percentage != 100:
        raise RuntimeError("FLIP particle display percentage mismatch")

    world_to_cup = cup.matrix_world.inverted()
    samples = []
    for frame in range(1, 8):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        evaluated_domain = domain.evaluated_get(depsgraph)
        if len(evaluated_domain.particle_systems) != 1:
            raise RuntimeError("FLIP particle evaluated system count mismatch")
        particles = evaluated_domain.particle_systems[0].particles
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
        })

    result = {
        "schemaVersion": "bfs.rc6LiquidFlipParticleAxisDiagnostic.v0.1",
        "status": "MEASURED_READ_ONLY",
        "cellId": "axis-control",
        "configuration": {
            "frameStart": 1, "frameEnd": 7, "resolutionMax": 192,
            "baseVoxelMeters": round(BASE_VOXEL_METERS, 10),
            "particleRadius": 1.6, "particleNumber": 2,
            "meshParticleRadius": 9.0,
            "cupInnerRadiusMeters": CUP_INNER_RADIUS_METERS,
            "cupInteriorBottomLocalZMeters": CUP_INTERIOR_BOTTOM_LOCAL_Z,
            "cupInteriorTopLocalZMeters": CUP_INTERIOR_TOP_LOCAL_Z,
            "cupEffectorSurfaceDistance": round(cup_modifier.effector_settings.surface_distance, 8),
            "flipParticleSystemInitiallyAbsent": True,
            "flipParticleSystemExposedInMemory": True,
            "displayPercentage": 100,
            "particleCoordinateConvention": "Blender Particle.location world-space converted by cup.matrix_world.inverted",
        },
        "samples": samples,
        "cacheFiles": cache_files,
        "retainedCandidateManifestHash": args.retained_candidate_manifest_hash,
        "authority": {
            "copiedCandidateInMemoryFlipExposure": True,
            "fluidDataBakes": 0, "fluidMeshBakes": 0, "blendSaves": 0,
            "renderCalls": 0, "networkCalls": 0, "engineRemoteWrites": 0,
        },
    }
    result["resultHash"] = self_hash(result, "resultHash")
    write_exclusive(evidence_root / "cells/axis-control/result.json", result)
    print("RC6_FLIP_PARTICLE_AXIS=" + canonical({"status": result["status"], "resultHash": result["resultHash"]}), flush=True)


if __name__ == "__main__":
    main()
