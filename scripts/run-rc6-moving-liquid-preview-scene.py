#!/usr/bin/env python3
"""Bake one bounded Preview-96 liquid window on the accepted C5F96 trajectory."""

import argparse
import bmesh
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import bpy
from mathutils import Vector


FRAME_START = 1
FRAME_END = 24
FPS = 24
RESOLUTION = 96
DOMAIN_CENTER = Vector((0.45, 0.0, 0.26))
DOMAIN_DIMENSIONS = Vector((0.90, 0.50, 0.58))
BASE_VOXEL_METERS = 0.90 / 96.0
DRIVE_END_FRAME = 96
MOTOR_DEGREES_PER_SECOND = 60.0 * FPS / (DRIVE_END_FRAME - FRAME_START)
EXPECTED_SOURCE_VOLUME = 0.0013283283766941
CUP_INNER_RADIUS_METERS = 0.09
CUP_INTERIOR_BOTTOM_LOCAL_Z = -0.16
CUP_INTERIOR_TOP_LOCAL_Z = 0.22


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def self_hash(value, field):
    body = dict(value)
    body.pop(field, None)
    return hashlib.sha256(canonical(body).encode()).hexdigest()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_exclusive(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def action_curves(obj):
    if not obj.animation_data or not obj.animation_data.action:
        return []
    action = obj.animation_data.action
    if hasattr(action, "fcurves"):
        return list(action.fcurves)
    return [
        curve
        for layer in action.layers
        for strip in layer.strips
        for channelbag in strip.channelbags
        for curve in channelbag.fcurves
    ]


def tilt_degrees(obj):
    up = obj.matrix_world.to_3x3() @ Vector((0.0, 0.0, 1.0))
    return math.degrees(math.acos(max(-1.0, min(1.0, up.normalized().z))))


def mesh_world_volume(obj):
    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        bm.transform(obj.matrix_world)
        if any(len(edge.link_faces) != 2 for edge in bm.edges):
            raise RuntimeError(f"source mesh is non-manifold: {obj.name}")
        return abs(bm.calc_volume(signed=True))
    finally:
        bm.free()


def fluid_quality(domain, cup):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = domain.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        vertex_count = len(mesh.vertices)
        if vertex_count == 0:
            raise RuntimeError("moving-liquid Preview produced no vertices")
        parent = list(range(vertex_count))

        def find(index):
            while parent[index] != index:
                parent[index] = parent[parent[index]]
                index = parent[index]
            return index

        def union(first, second):
            first_root, second_root = find(first), find(second)
            if first_root != second_root:
                parent[second_root] = first_root

        for edge in mesh.edges:
            union(edge.vertices[0], edge.vertices[1])
        component_sizes = {}
        for index in range(vertex_count):
            root = find(index)
            component_sizes[root] = component_sizes.get(root, 0) + 1
        component_faces = {}
        for polygon in mesh.polygons:
            roots = {find(index) for index in polygon.vertices}
            if len(roots) != 1:
                raise RuntimeError("moving-liquid polygon spans component roots")
            component_faces.setdefault(next(iter(roots)), []).append(polygon)

        world_points = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
        world_to_cup = cup.matrix_world.inverted_safe()
        local_points = [world_to_cup @ point for point in world_points]
        radial_limit = CUP_INNER_RADIUS_METERS + BASE_VOXEL_METERS
        bottom_limit = CUP_INTERIOR_BOTTOM_LOCAL_Z - BASE_VOXEL_METERS
        top_limit = CUP_INTERIOR_TOP_LOCAL_Z + BASE_VOXEL_METERS
        radial_count = sum(math.hypot(point.x, point.y) > radial_limit for point in local_points)
        below_count = sum(point.z < bottom_limit for point in local_points)
        above_count = sum(point.z > top_limit for point in local_points)
        outside_count = sum(
            math.hypot(point.x, point.y) > radial_limit or point.z < bottom_limit or point.z > top_limit
            for point in local_points
        )

        component_details = []
        for root, polygons in component_faces.items():
            indices = sorted({index for polygon in polygons for index in polygon.vertices})
            index_map = {old: new for new, old in enumerate(indices)}
            component = bmesh.new()
            try:
                vertices = [component.verts.new(mesh.vertices[index].co) for index in indices]
                component.verts.ensure_lookup_table()
                for polygon in polygons:
                    component.faces.new([vertices[index_map[index]] for index in polygon.vertices])
                component.normal_update()
                component.transform(evaluated.matrix_world)
                non_manifold = sum(len(edge.link_faces) != 2 for edge in component.edges)
                signed_volume = component.calc_volume(signed=True) if non_manifold == 0 else 0.0
            finally:
                component.free()
            component_details.append(
                {
                    "rootVertexIndex": root,
                    "vertexCount": len(indices),
                    "vertexFraction": round(len(indices) / vertex_count, 8),
                    "nonManifoldEdgeCount": non_manifold,
                    "signedVolumeCubicMeters": round(signed_volume, 10),
                    "absoluteVolumeCubicMeters": round(abs(signed_volume), 10),
                }
            )
        component_details.sort(key=lambda row: (-row["absoluteVolumeCubicMeters"], row["rootVertexIndex"]))

        aggregate = bmesh.new()
        try:
            aggregate.from_mesh(mesh)
            aggregate.transform(evaluated.matrix_world)
            aggregate_non_manifold = sum(len(edge.link_faces) != 2 for edge in aggregate.edges)
            signed_volume = aggregate.calc_volume(signed=True) if aggregate_non_manifold == 0 else 0.0
        finally:
            aggregate.free()
        local_centroid = [sum(point[axis] for point in local_points) / vertex_count for axis in range(3)]
        world_centroid = [sum(point[axis] for point in world_points) / vertex_count for axis in range(3)]
        return {
            "vertexCount": vertex_count,
            "connectedComponentCount": len(component_sizes),
            "positiveBodyCount": sum(row["signedVolumeCubicMeters"] > 1e-10 for row in component_details),
            "largestComponentFraction": round(max(component_sizes.values()) / vertex_count, 8),
            "meshVolumeCubicMeters": round(abs(signed_volume), 10),
            "nonManifoldEdgeCount": aggregate_non_manifold,
            "outsideCupInteriorPlusOneVoxelFraction": round(outside_count / vertex_count, 8),
            "radialOutsideFraction": round(radial_count / vertex_count, 8),
            "belowFloorFraction": round(below_count / vertex_count, 8),
            "aboveRimFraction": round(above_count / vertex_count, 8),
            "centroidCupLocalMeters": [round(value, 8) for value in local_centroid],
            "centroidWorldMeters": [round(value, 8) for value in world_centroid],
            "boundsMinWorld": [round(min(point[axis] for point in world_points), 8) for axis in range(3)],
            "boundsMaxWorld": [round(max(point[axis] for point in world_points), 8) for axis in range(3)],
            "components": component_details,
        }
    finally:
        evaluated.to_mesh_clear()


parser = argparse.ArgumentParser()
parser.add_argument("--work-root", type=Path, required=True)
parser.add_argument("--evidence-root", type=Path, required=True)
parser.add_argument("--trajectory-json", type=Path, required=True)
parser.add_argument("--source-copy", type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
work_root = args.work_root.resolve(strict=True)
evidence_root = args.evidence_root.resolve(strict=True)
trajectory_path = args.trajectory_json.resolve(strict=True)
source_copy = args.source_copy.resolve(strict=True)
if Path(bpy.data.filepath).resolve() != source_copy:
    raise RuntimeError("moving-liquid Preview source-copy path mismatch")
result_path = evidence_root / "result.json"
cache_root = work_root / "mantaflow-cache"
if result_path.exists() or cache_root.exists():
    raise RuntimeError("moving-liquid Preview outputs are not fresh")

trajectory = json.loads(trajectory_path.read_text())
trajectory_samples = {row["frame"]: row for row in trajectory["samples"] if FRAME_START <= row["frame"] <= FRAME_END}
if trajectory.get("cellId") != "C5F96" or trajectory.get("status") != "PASS" or len(trajectory_samples) != FRAME_END:
    raise RuntimeError("moving-liquid Preview accepted trajectory identity mismatch")

required_names = (
    "PHYS_OPEN_TUMBLER",
    "PHYS_BASKETBALL",
    "PHYS_VISIBLE_STRIKER",
    "PHYS_FLOOR",
    "PHYS_LIQUID_DOMAIN",
    "PHYS_INITIAL_LIQUID_VOLUME",
)
objects = {name: bpy.data.objects.get(name) for name in required_names}
if any(value is None for value in objects.values()):
    raise RuntimeError("moving-liquid Preview retained scene roster incomplete")
cup = objects["PHYS_OPEN_TUMBLER"]
ball = objects["PHYS_BASKETBALL"]
pusher = objects["PHYS_VISIBLE_STRIKER"]
domain = objects["PHYS_LIQUID_DOMAIN"]
source = objects["PHYS_INITIAL_LIQUID_VOLUME"]
if cup.animation_data or ball.animation_data:
    raise RuntimeError("moving-liquid Preview source has outcome-body animation")
if cup.rigid_body is None or cup.rigid_body.type != "ACTIVE" or cup.rigid_body.collision_shape != "CYLINDER" or abs(cup.rigid_body.mass - 0.34) > 1e-5:
    raise RuntimeError("moving-liquid Preview cup rigid identity mismatch")
if ball.rigid_body is None or ball.rigid_body.type != "ACTIVE" or pusher.rigid_body is None or not pusher.rigid_body.kinematic:
    raise RuntimeError("moving-liquid Preview actor rigid identity mismatch")

domain_modifier = next((item for item in domain.modifiers if item.type == "FLUID" and item.fluid_type == "DOMAIN"), None)
cup_modifier = next((item for item in cup.modifiers if item.type == "FLUID" and item.fluid_type == "EFFECTOR"), None)
flow_modifier = next((item for item in source.modifiers if item.type == "FLUID" and item.fluid_type == "FLOW"), None)
if domain_modifier is None or cup_modifier is None or flow_modifier is None:
    raise RuntimeError("moving-liquid Preview fluid modifier identity incomplete")
settings = domain_modifier.domain_settings
effector = cup_modifier.effector_settings
flow = flow_modifier.flow_settings
if settings.domain_type != "LIQUID" or settings.simulation_method != "APIC" or flow.flow_behavior != "GEOMETRY":
    raise RuntimeError("moving-liquid Preview fluid semantic identity mismatch")

scene = bpy.context.scene
scene.frame_start = FRAME_START
scene.frame_end = FRAME_END
scene.render.fps = FPS
if not scene.rigidbody_world:
    raise RuntimeError("moving-liquid Preview lacks rigid-body world")
world = scene.rigidbody_world
world.substeps_per_frame = 20
world.solver_iterations = 80
world.point_cache.frame_start = FRAME_START
world.point_cache.frame_end = FRAME_END
with bpy.context.temp_override(point_cache=world.point_cache):
    if world.point_cache.is_baked:
        bpy.ops.ptcache.free_bake()
scene.frame_set(FRAME_START)
bpy.context.view_layer.update()

ball.rigid_body.kinematic = True
pusher.animation_data_clear()
pusher.location = (-1.10, 0.0, 0.34)
pusher.hide_viewport = True
pusher.hide_render = True

bpy.ops.mesh.primitive_cube_add(location=(0.47, 0.0, -0.08))
hinge_anchor = bpy.context.object
hinge_anchor.name = "PHYS_SLOW_TIP_HINGE_ANCHOR"
hinge_anchor.scale = (0.04, 0.04, 0.04)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
bpy.ops.rigidbody.object_add()
hinge_anchor.rigid_body.type = "PASSIVE"
hinge_anchor.rigid_body.collision_shape = "BOX"
bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0.47, 0.0, 0.0), rotation=(math.pi / 2.0, 0.0, 0.0))
hinge = bpy.context.object
hinge.name = "PHYS_SLOW_TIP_HINGE"
bpy.ops.rigidbody.constraint_add(type="HINGE")
hinge.rigid_body_constraint.object1 = cup
hinge.rigid_body_constraint.object2 = hinge_anchor
hinge.rigid_body_constraint.disable_collisions = True
hinge.rigid_body_constraint.enabled = True
hinge.rigid_body_constraint.use_limit_ang_z = True
hinge.rigid_body_constraint.limit_ang_z_lower = -math.radians(60.0)
hinge.rigid_body_constraint.limit_ang_z_upper = math.radians(5.0)
cup.rigid_body.angular_damping = 0.8
hinge_pivot_world = Vector((0.47, 0.0, 0.0))
hinge_pivot_cup_local = cup.matrix_world.inverted() @ hinge_pivot_world

bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0.47, 0.0, 0.0), rotation=(0.0, 0.0, -math.pi / 2.0))
motor = bpy.context.object
motor.name = "PHYS_SLOW_TIP_MOTOR"
bpy.ops.rigidbody.constraint_add(type="MOTOR")
motor.rigid_body_constraint.object1 = cup
motor.rigid_body_constraint.object2 = hinge_anchor
motor.rigid_body_constraint.disable_collisions = True
motor.rigid_body_constraint.enabled = True
motor.rigid_body_constraint.motor_ang_target_velocity = -math.radians(MOTOR_DEGREES_PER_SECOND)
motor.rigid_body_constraint.motor_ang_max_impulse = 1.0
motor.rigid_body_constraint.use_motor_ang = True
bpy.context.view_layer.update()

bullet_started = time.monotonic()
scene.frame_set(FRAME_START)
with bpy.context.temp_override(point_cache=world.point_cache):
    bpy.ops.ptcache.bake(bake=True)
bullet_seconds = time.monotonic() - bullet_started
bullet_samples = []
maximum_location_delta = 0.0
maximum_rotation_delta_degrees = 0.0
maximum_pivot_drift = 0.0
for frame in range(FRAME_START, FRAME_END + 1):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    expected = trajectory_samples[frame]
    expected_location = Vector(expected["cupLocation"])
    expected_rotation = __import__("mathutils").Quaternion(expected["cupRotationQuaternion"])
    location_delta = (cup.matrix_world.translation - expected_location).length
    rotation_delta = math.degrees(cup.matrix_world.to_quaternion().rotation_difference(expected_rotation).angle)
    pivot_drift = (cup.matrix_world @ hinge_pivot_cup_local - hinge_pivot_world).length
    maximum_location_delta = max(maximum_location_delta, location_delta)
    maximum_rotation_delta_degrees = max(maximum_rotation_delta_degrees, rotation_delta)
    maximum_pivot_drift = max(maximum_pivot_drift, pivot_drift)
    bullet_samples.append(
        {
            "frame": frame,
            "cupLocation": [round(value, 8) for value in cup.matrix_world.translation],
            "cupRotationQuaternion": [round(value, 8) for value in cup.matrix_world.to_quaternion()],
            "cupTiltDegrees": round(tilt_degrees(cup), 8),
            "acceptedLocationDeltaMeters": round(location_delta, 10),
            "acceptedRotationDeltaDegrees": round(rotation_delta, 10),
            "hingePivotDriftMeters": round(pivot_drift, 10),
        }
    )

# Rebind the copied domain to a fresh cache before any fluid reset or setting change.
settings.cache_directory = str(cache_root)
settings.cache_type = "REPLAY"
bpy.context.view_layer.update()
settings.cache_type = "MODULAR"
domain.location = DOMAIN_CENTER
domain.dimensions = DOMAIN_DIMENSIONS
bpy.ops.object.select_all(action="DESELECT")
domain.select_set(True)
bpy.context.view_layer.objects.active = domain
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
settings.cache_frame_start = FRAME_START
settings.cache_frame_end = FRAME_END
settings.resolution_max = RESOLUTION
settings.cache_data_format = "OPENVDB"
settings.cache_mesh_format = "BOBJECT"
settings.use_adaptive_timesteps = True
settings.timesteps_min = 1
settings.timesteps_max = 4
settings.cfl_condition = 2.0
settings.particle_number = 2
settings.particle_radius = 1.6
settings.use_mesh = True
settings.mesh_scale = 2
settings.mesh_particle_radius = 2.5
settings.mesh_concave_lower = 0.4
settings.mesh_concave_upper = 3.5
settings.mesh_smoothen_pos = 1
settings.mesh_smoothen_neg = 1
settings.use_fractions = True
settings.delete_in_obstacle = False
settings.use_viscosity = True
settings.viscosity_base = 1.0
settings.viscosity_exponent = 6
flow.surface_distance = 0.0
flow.use_plane_init = False
effector.surface_distance = 2.5
effector.use_plane_init = False
effector.use_effector = True
effector.subframes = 1
scene.frame_set(FRAME_START)
bpy.context.view_layer.update()
source_volume = mesh_world_volume(source)
if abs(source_volume - EXPECTED_SOURCE_VOLUME) > 1e-10:
    raise RuntimeError("moving-liquid Preview source volume mismatch")
context = {"object": domain, "active_object": domain, "selected_objects": [domain], "selected_editable_objects": [domain]}
data_started = time.monotonic()
with bpy.context.temp_override(**context):
    if "FINISHED" not in bpy.ops.fluid.bake_data():
        raise RuntimeError("moving-liquid Preview Data bake did not finish")
data_seconds = time.monotonic() - data_started
mesh_started = time.monotonic()
with bpy.context.temp_override(**context):
    if "FINISHED" not in bpy.ops.fluid.bake_mesh():
        raise RuntimeError("moving-liquid Preview Mesh bake did not finish")
mesh_seconds = time.monotonic() - mesh_started

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
    raise RuntimeError("moving-liquid Preview initial mesh volume is zero")
for row in fluid_samples:
    row["temporalVolumeDriftFraction"] = round(row["meshVolumeCubicMeters"] / initial_volume - 1.0, 8)
initial_centroid = Vector(fluid_samples[0]["centroidCupLocalMeters"])
maximum_centroid_shift = max((Vector(row["centroidCupLocalMeters"]) - initial_centroid).length for row in fluid_samples)

expected_cache_files = sorted(
    [f"config/config_{frame:04d}.uni" for frame in range(FRAME_START, FRAME_END + 1)]
    + [f"data/fluid_data_{frame:04d}.vdb" for frame in range(FRAME_START, FRAME_END + 1)]
    + [f"mesh/fluid_mesh_{frame:04d}.bobj.gz" for frame in range(FRAME_START, FRAME_END + 1)]
)
actual_cache_files = sorted(str(path.relative_to(cache_root)) for path in cache_root.rglob("*") if path.is_file())
maximum_source_error = max(abs(row["sourceVolumeErrorFraction"]) for row in fluid_samples)
maximum_temporal_drift = max(abs(row["temporalVolumeDriftFraction"]) for row in fluid_samples)
checks = {
    "exactAcceptedC5F96Trajectory": maximum_location_delta <= 1e-5 and maximum_rotation_delta_degrees <= 1e-4,
    "solverOwnedCupMotionPresent": bullet_samples[-1]["cupTiltDegrees"] >= 14.0 and not action_curves(cup),
    "hingeAndMotorExact": hinge.rigid_body_constraint.type == "HINGE" and motor.rigid_body_constraint.type == "MOTOR" and abs(motor.rigid_body_constraint.motor_ang_target_velocity + math.radians(MOTOR_DEGREES_PER_SECOND)) <= 1e-6 and abs(motor.rigid_body_constraint.motor_ang_max_impulse - 1.0) <= 1e-6,
    "hingePivotStable": maximum_pivot_drift <= 0.005,
    "exactCacheFrameRoster": actual_cache_files == expected_cache_files,
    "liquidMeshEveryFrame": all(row["vertexCount"] > 0 for row in fluid_samples),
    "sourceRelativeVolumeWithin25Percent": maximum_source_error <= 0.25,
    "temporalVolumeDriftWithin15Percent": maximum_temporal_drift <= 0.15,
    "onePositiveLiquidBody": min(row["positiveBodyCount"] for row in fluid_samples) == 1 and max(row["positiveBodyCount"] for row in fluid_samples) == 1,
    "manifoldEveryFrame": max(row["nonManifoldEdgeCount"] for row in fluid_samples) == 0,
    "largestComponentAtLeastHalf": min(row["largestComponentFraction"] for row in fluid_samples) >= 0.5,
    "containedWithinCupPlusOneVoxel": max(row["outsideCupInteriorPlusOneVoxelFraction"] for row in fluid_samples) <= 0.05,
    "belowFloorWithinOnePercent": max(row["belowFloorFraction"] for row in fluid_samples) <= 0.01,
    "movingLiquidRelativeToCup": maximum_centroid_shift >= 0.002,
    "singleInitialGeometryFlow": flow.flow_behavior == "GEOMETRY" and not source.animation_data,
    "zeroOutcomePoseAuthority": not action_curves(cup) and not action_curves(ball) and not action_curves(pusher),
    "previewTierExact": settings.resolution_max == RESOLUTION and settings.cache_frame_start == FRAME_START and settings.cache_frame_end == FRAME_END and abs(settings.particle_radius - 1.6) <= 1e-6 and abs(settings.mesh_particle_radius - 2.5) <= 1e-6 and effector.subframes == 1,
}
result = {
    "schemaVersion": "bfs.rc6MovingLiquidPreviewResult.v0.1",
    "status": "PASS" if all(checks.values()) else "FAIL",
    "verdict": "PASS_MOVING_LIQUID_PREVIEW" if all(checks.values()) else "FAIL_MOVING_LIQUID_PREVIEW",
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
        "meshParticleRadius": 2.5,
        "meshPhysicalRadiusContextMeters": round(2.5 * BASE_VOXEL_METERS, 10),
        "cupEffectorSurfaceDistanceCells": 2.5,
        "cupEffectorSubframes": 1,
        "sourceMeshVolumeCubicMeters": source_volume,
    },
    "metrics": {
        "maximumAcceptedTrajectoryLocationDeltaMeters": maximum_location_delta,
        "maximumAcceptedTrajectoryRotationDeltaDegrees": maximum_rotation_delta_degrees,
        "maximumHingePivotDriftMeters": maximum_pivot_drift,
        "maximumAbsoluteSourceVolumeErrorFraction": maximum_source_error,
        "maximumAbsoluteTemporalVolumeDriftFraction": maximum_temporal_drift,
        "maximumPositiveBodyCount": max(row["positiveBodyCount"] for row in fluid_samples),
        "maximumConnectedComponentCount": max(row["connectedComponentCount"] for row in fluid_samples),
        "maximumNonManifoldEdgeCount": max(row["nonManifoldEdgeCount"] for row in fluid_samples),
        "minimumLargestComponentFraction": min(row["largestComponentFraction"] for row in fluid_samples),
        "maximumOutsideCupInteriorPlusOneVoxelFraction": max(row["outsideCupInteriorPlusOneVoxelFraction"] for row in fluid_samples),
        "maximumRadialOutsideFraction": max(row["radialOutsideFraction"] for row in fluid_samples),
        "maximumBelowFloorFraction": max(row["belowFloorFraction"] for row in fluid_samples),
        "maximumAboveRimFraction": max(row["aboveRimFraction"] for row in fluid_samples),
        "maximumLiquidCentroidShiftCupLocalMeters": maximum_centroid_shift,
        "bulletBakeSeconds": bullet_seconds,
        "fluidDataBakeSeconds": data_seconds,
        "fluidMeshBakeSeconds": mesh_seconds,
    },
    "bulletSamples": bullet_samples,
    "fluidSamples": fluid_samples,
    "cache": {"root": str(cache_root), "fileCount": len(actual_cache_files), "files": actual_cache_files},
    "checks": checks,
    "checkCount": len(checks),
    "passCount": sum(checks.values()),
    "counts": {"blenderStarts": 1, "bulletBakes": 1, "fluidDataBakes": 1, "fluidMeshBakes": 1, "renders": 0, "blendSaves": 0, "networkCalls": 0, "engineRemoteWrites": 0},
    "claimCeiling": "One 24-frame Preview-96 moving-liquid gate on the exact accepted C5F96 slow trajectory; no full tip, spill, impact, persistence, render or film-quality claim.",
}
result["resultHash"] = self_hash(result, "resultHash")
write_exclusive(result_path, result)
print("RC6_MOVING_LIQUID_PREVIEW=" + canonical({"status": result["status"], "resultHash": result["resultHash"], "metrics": result["metrics"]}), flush=True)
if result["status"] != "PASS":
    raise RuntimeError("moving-liquid Preview thresholds failed")
