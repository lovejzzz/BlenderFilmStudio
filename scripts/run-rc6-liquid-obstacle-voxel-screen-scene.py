#!/usr/bin/env python3
"""Bake one data-only static cell and measure FLIP particles against the cup solid."""

import argparse
import bmesh
import hashlib
import json
import sys
import time
from pathlib import Path

import bpy
from mathutils import Vector


LOCAL_DOMAIN_CENTER = (0.32, 0.0, 0.25)
LOCAL_DOMAIN_DIMENSIONS = (0.36, 0.36, 0.5)
EXPECTED_SOURCE_MESH_VOLUME = 0.0013283283766940559
EXPECTED_SOURCE_DIMENSIONS = (0.11, 0.11, 0.14)
SOURCE_BOTTOM_CLEARANCE_METERS = 0.035
CUP_INNER_RADIUS_METERS = 0.09
CUP_OUTER_RADIUS_METERS = 0.15
CUP_INTERIOR_BOTTOM_LOCAL_Z = -0.16
CUP_OUTER_BOTTOM_LOCAL_Z = -0.22
CUP_INTERIOR_TOP_LOCAL_Z = 0.22
CELLS = {
    "preview-baseline": (96, 1.5),
    "preview-effector-plus1": (96, 2.5),
    "review-baseline": (128, 1.5),
}


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
    values = sys.argv[sys.argv.index("--") + 1 :]
    parser = argparse.ArgumentParser()
    parser.add_argument("--cell-id", required=True)
    parser.add_argument("--work-root", required=True)
    parser.add_argument("--evidence-root", required=True)
    parser.add_argument("--resolution", type=int, required=True)
    parser.add_argument("--effector-surface-distance", type=float, required=True)
    return parser.parse_args(values)


def closed_object_mesh_volume(obj):
    mesh = bmesh.new()
    try:
        mesh.from_mesh(obj.data)
        mesh.transform(obj.matrix_world)
        if any(len(edge.link_faces) != 2 for edge in mesh.edges):
            raise RuntimeError(f"source mesh is not closed: {obj.name}")
        return abs(mesh.calc_volume(signed=True))
    finally:
        mesh.free()


def axis_counts(points, margin):
    radial_limit = CUP_INNER_RADIUS_METERS + margin
    bottom_limit = CUP_INTERIOR_BOTTOM_LOCAL_Z - margin
    top_limit = CUP_INTERIOR_TOP_LOCAL_Z + margin
    combinations = {
        "inside": 0,
        "radialOnly": 0,
        "belowOnly": 0,
        "aboveOnly": 0,
        "radialAndBelow": 0,
        "radialAndAbove": 0,
        "belowAndAbove": 0,
        "allThree": 0,
    }
    radial_count = 0
    below_count = 0
    above_count = 0
    for point in points:
        radial = (point.x * point.x + point.y * point.y) ** 0.5 > radial_limit
        below = point.z < bottom_limit
        above = point.z > top_limit
        radial_count += int(radial)
        below_count += int(below)
        above_count += int(above)
        key = {
            (False, False, False): "inside",
            (True, False, False): "radialOnly",
            (False, True, False): "belowOnly",
            (False, False, True): "aboveOnly",
            (True, True, False): "radialAndBelow",
            (True, False, True): "radialAndAbove",
            (False, True, True): "belowAndAbove",
            (True, True, True): "allThree",
        }[(radial, below, above)]
        combinations[key] += 1
    count = len(points)
    outside = count - combinations["inside"]
    return {
        "marginMeters": round(margin, 10),
        "particleCount": count,
        "outsideUnionCount": outside,
        "outsideUnionFraction": round(outside / count, 8),
        "radialCount": radial_count,
        "belowFloorCount": below_count,
        "aboveRimCount": above_count,
        "exclusiveCombinations": combinations,
    }


def main():
    args = arguments()
    expected = CELLS.get(args.cell_id)
    if expected is None or args.resolution != expected[0] or abs(args.effector_surface_distance - expected[1]) > 1e-12:
        raise RuntimeError("obstacle-voxel cell identity mismatch")
    base_voxel = max(LOCAL_DOMAIN_DIMENSIONS) / args.resolution
    work_root = Path(args.work_root).resolve()
    evidence_root = Path(args.evidence_root).resolve()
    cell_root = work_root / args.cell_id
    cache_root = cell_root / "mantaflow-cache"
    result_path = evidence_root / "cells" / args.cell_id / "result.json"
    if cell_root.exists() or result_path.exists():
        raise RuntimeError("obstacle-voxel cell roots are not fresh")
    cell_root.mkdir(parents=True, exist_ok=False)

    scene = bpy.context.scene
    domain = bpy.data.objects.get("PHYS_LIQUID_DOMAIN")
    cup = bpy.data.objects.get("PHYS_OPEN_TUMBLER")
    source = bpy.data.objects.get("PHYS_INITIAL_LIQUID_VOLUME")
    if domain is None or cup is None or source is None:
        raise RuntimeError("retained RC6 scene identity is incomplete")
    domain_modifier = next((item for item in domain.modifiers if item.type == "FLUID" and item.fluid_type == "DOMAIN"), None)
    cup_modifier = next((item for item in cup.modifiers if item.type == "FLUID" and item.fluid_type == "EFFECTOR"), None)
    flow_modifier = next((item for item in source.modifiers if item.type == "FLUID" and item.fluid_type == "FLOW"), None)
    if domain_modifier is None or cup_modifier is None or flow_modifier is None:
        raise RuntimeError("retained RC6 fluid modifier identity is incomplete")
    settings = domain_modifier.domain_settings
    flow_settings = flow_modifier.flow_settings
    effector_settings = cup_modifier.effector_settings
    if settings.domain_type != "LIQUID" or settings.simulation_method != "APIC" or flow_settings.flow_behavior != "GEOMETRY":
        raise RuntimeError("retained RC6 fluid semantic identity mismatch")

    domain.location = LOCAL_DOMAIN_CENTER
    domain.dimensions = LOCAL_DOMAIN_DIMENSIONS
    bpy.ops.object.select_all(action="DESELECT")
    domain.select_set(True)
    bpy.context.view_layer.objects.active = domain
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if max(abs(domain.dimensions[index] - LOCAL_DOMAIN_DIMENSIONS[index]) for index in range(3)) > 1e-6:
        raise RuntimeError("local domain dimensions were not applied exactly")

    scene.frame_start = 1
    scene.frame_end = 7
    scene.frame_set(1)
    bpy.context.view_layer.update()
    source_volume = closed_object_mesh_volume(source)
    source_dimensions = tuple(round(value, 10) for value in source.dimensions)
    if abs(source_volume - EXPECTED_SOURCE_MESH_VOLUME) > 1e-10 or any(abs(source_dimensions[index] - EXPECTED_SOURCE_DIMENSIONS[index]) > 1e-8 for index in range(3)):
        raise RuntimeError("frozen source geometry identity mismatch")
    inner_floor_world_z = (cup.matrix_world @ Vector((0.0, 0.0, CUP_INTERIOR_BOTTOM_LOCAL_Z))).z
    source.location.z = inner_floor_world_z + source.dimensions.z * 0.5 + SOURCE_BOTTOM_CLEARANCE_METERS
    bpy.context.view_layer.update()
    measured_clearance = source.matrix_world.translation.z - source.dimensions.z * 0.5 - inner_floor_world_z
    if abs(measured_clearance - SOURCE_BOTTOM_CLEARANCE_METERS) > 1e-8:
        raise RuntimeError("source-bottom clearance placement mismatch")

    initial_use_flip_particles = bool(settings.use_flip_particles)
    initial_particle_system_count = len(domain.particle_systems)
    settings.cache_type = "MODULAR"
    settings.cache_directory = str(cache_root)
    settings.cache_frame_start = 1
    settings.cache_frame_end = 7
    settings.resolution_max = args.resolution
    settings.use_adaptive_timesteps = True
    settings.timesteps_min = 1
    settings.timesteps_max = 4
    settings.cfl_condition = 2.0
    settings.particle_number = 2
    settings.particle_radius = 1.6
    settings.use_mesh = False
    settings.use_flip_particles = True
    settings.use_fractions = True
    settings.delete_in_obstacle = False
    settings.use_viscosity = True
    settings.viscosity_base = 1.0
    settings.viscosity_exponent = 6
    flow_settings.surface_distance = 0.0
    effector_settings.surface_distance = args.effector_surface_distance
    effector_settings.use_plane_init = False
    effector_settings.use_effector = True
    effector_settings.subframes = 0
    bpy.context.view_layer.update()
    if len(domain.particle_systems) != 1:
        raise RuntimeError("FLIP particle system was not exposed before bake")
    domain.particle_systems[0].settings.display_percentage = 100

    started = time.monotonic()
    scene.frame_set(1)
    bpy.ops.object.select_all(action="DESELECT")
    domain.select_set(True)
    bpy.context.view_layer.objects.active = domain
    with bpy.context.temp_override(object=domain, active_object=domain, selected_objects=[domain], selected_editable_objects=[domain]):
        bpy.ops.fluid.bake_data()

    cache_files = sorted(str(path.relative_to(cache_root)) for path in cache_root.rglob("*") if path.is_file())
    expected_cache_files = sorted(
        [f"config/config_{frame:04d}.uni" for frame in range(1, 8)]
        + [f"data/fluid_data_{frame:04d}.vdb" for frame in range(1, 8)]
    )
    if cache_files != expected_cache_files:
        raise RuntimeError(f"obstacle-voxel cache file roster mismatch: {cache_files}")

    samples = []
    world_to_cup = cup.matrix_world.inverted()
    for frame in range(1, 8):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        evaluated_domain = domain.evaluated_get(bpy.context.evaluated_depsgraph_get())
        if len(evaluated_domain.particle_systems) != 1:
            raise RuntimeError(f"frame {frame}: evaluated FLIP particle system missing")
        particles = list(evaluated_domain.particle_systems[0].particles)
        if not particles:
            raise RuntimeError(f"frame {frame}: evaluated FLIP particles empty")
        local_points = [world_to_cup @ particle.location for particle in particles]
        strict = axis_counts(local_points, 0.0)
        one_voxel = axis_counts(local_points, base_voxel)
        outliers = []
        for display_index, (particle, local) in enumerate(zip(particles, local_points)):
            radial = (local.x * local.x + local.y * local.y) ** 0.5
            radial_out = radial > CUP_INNER_RADIUS_METERS + base_voxel
            below_out = local.z < CUP_INTERIOR_BOTTOM_LOCAL_Z - base_voxel
            above_out = local.z > CUP_INTERIOR_TOP_LOCAL_Z + base_voxel
            if not (radial_out or below_out or above_out):
                continue
            if radial <= CUP_OUTER_RADIUS_METERS and CUP_OUTER_BOTTOM_LOCAL_Z <= local.z < CUP_INTERIOR_BOTTOM_LOCAL_Z:
                region = "INSIDE_CUP_SOLID_FLOOR"
            elif local.z < CUP_OUTER_BOTTOM_LOCAL_Z:
                region = "BELOW_CUP_OUTER_BOTTOM"
            elif CUP_INNER_RADIUS_METERS < radial <= CUP_OUTER_RADIUS_METERS and CUP_OUTER_BOTTOM_LOCAL_Z <= local.z <= CUP_INTERIOR_TOP_LOCAL_Z:
                region = "INSIDE_CUP_SOLID_WALL"
            else:
                region = "OUTSIDE_MODELED_CUP_SOLID"
            velocity = particle.velocity.copy()
            detail = {
                "displayIndex": display_index,
                "aliveState": particle.alive_state,
                "locationCupLocal": [round(float(value), 8) for value in local],
                "speedRna": round(float(velocity.length), 8),
                "physicalRegion": region,
                "radialOutsideOneVoxel": radial_out,
                "belowFloorOneVoxel": below_out,
                "aboveRimOneVoxel": above_out,
                "interiorFloorPenetrationMeters": round(max(0.0, CUP_INTERIOR_BOTTOM_LOCAL_Z - local.z), 8),
            }
            detail["detailHash"] = self_hash(detail, "detailHash")
            outliers.append(detail)
        if len(outliers) != one_voxel["outsideUnionCount"]:
            raise RuntimeError(f"frame {frame}: outlier detail count mismatch")
        samples.append({
            "frame": frame,
            "strictInterior": strict,
            "oneVoxelEnvelope": one_voxel,
            "outliersOneVoxel": outliers,
            "boundsMinCupLocal": [round(min(point[axis] for point in local_points), 8) for axis in range(3)],
            "boundsMaxCupLocal": [round(max(point[axis] for point in local_points), 8) for axis in range(3)],
        })

    details = [detail for sample in samples for detail in sample["outliersOneVoxel"]]
    result = {
        "schemaVersion": "bfs.rc6LiquidObstacleVoxelScreenCell.v0.1",
        "status": "MEASURED_DATA_ONLY",
        "cellId": args.cell_id,
        "configuration": {
            "frameStart": 1,
            "frameEnd": 7,
            "resolutionMax": args.resolution,
            "baseVoxelMeters": round(base_voxel, 10),
            "domainCenterMeters": list(LOCAL_DOMAIN_CENTER),
            "domainDimensionsMeters": list(LOCAL_DOMAIN_DIMENSIONS),
            "sourceDimensionsMeters": list(source_dimensions),
            "sourceMeshVolumeCubicMeters": round(source_volume, 16),
            "sourceBottomClearanceMeters": round(measured_clearance, 10),
            "simulationMethod": "APIC",
            "useAdaptiveTimesteps": True,
            "timestepsMin": 1,
            "timestepsMax": 4,
            "cflCondition": 2.0,
            "particleNumber": 2,
            "particleRadius": 1.6,
            "useMesh": False,
            "useFlipParticles": True,
            "initialUseFlipParticles": initial_use_flip_particles,
            "initialParticleSystemCount": initial_particle_system_count,
            "finalParticleSystemCount": len(domain.particle_systems),
            "displayPercentage": 100,
            "useFractions": True,
            "deleteInObstacle": False,
            "waterViscosityBase": 1.0,
            "waterViscosityExponent": 6,
            "flowSurfaceDistanceCells": 0.0,
            "cupEffectorSurfaceDistanceCells": round(float(effector_settings.surface_distance), 8),
            "cupEffectorIsPlanar": bool(effector_settings.use_plane_init),
            "cupEffectorEnabled": bool(effector_settings.use_effector),
            "cupEffectorSubframes": 0,
        },
        "metrics": {
            "maximumOneVoxelOutlierCount": max(sample["oneVoxelEnvelope"]["outsideUnionCount"] for sample in samples),
            "maximumOneVoxelOutlierFraction": max(sample["oneVoxelEnvelope"]["outsideUnionFraction"] for sample in samples),
            "maximumStrictOutlierCount": max(sample["strictInterior"]["outsideUnionCount"] for sample in samples),
            "framesWithOneVoxelOutliers": [sample["frame"] for sample in samples if sample["oneVoxelEnvelope"]["outsideUnionCount"]],
            "maximumInteriorFloorPenetrationMeters": max([detail["interiorFloorPenetrationMeters"] for detail in details] or [0.0]),
            "outlierPhysicalRegions": sorted({detail["physicalRegion"] for detail in details}),
            "wallSeconds": round(time.monotonic() - started, 6),
        },
        "samples": samples,
        "cacheFiles": cache_files,
        "authority": {
            "fluidDataBakes": 1,
            "fluidMeshBakes": 0,
            "blendSaves": 0,
            "renderCalls": 0,
            "networkCalls": 0,
            "engineRemoteWrites": 0,
        },
    }
    result["resultHash"] = self_hash(result, "resultHash")
    write_exclusive(result_path, result)
    print("RC6_OBSTACLE_VOXEL_SCREEN=" + canonical({"cellId": args.cell_id, "resultHash": result["resultHash"], "metrics": result["metrics"]}), flush=True)


if __name__ == "__main__":
    main()
