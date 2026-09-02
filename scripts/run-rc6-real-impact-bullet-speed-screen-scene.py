#!/usr/bin/env python3
"""Measure one exact-scene basketball impact with Bullet and no Mantaflow."""

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


SOURCE_SHA256 = "9ac79c9c3c0d13273ac20804a3af99884f9465534800c3d9ca2ae8121499e644"
FRAME_START = 1
FRAME_END = 48
FPS = 24
PREVIEW_RESOLUTION = 96
DOMAIN_CENTER = Vector((0.45, 0.0, 0.26))
DOMAIN_DIMENSIONS = Vector((0.90, 0.50, 0.58))
DRIVE_ENDS = {"I08": 8, "I10": 10, "I12": 12}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def self_hash(value, field):
    body = dict(value)
    body.pop(field, None)
    return hashlib.sha256(canonical(body).encode()).hexdigest()


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


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


def world_surface_points(obj):
    return [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]


def cylinder_sphere_gap(cup, ball, cup_radius, cup_half_height, ball_radius):
    point = cup.matrix_world.inverted_safe() @ ball.matrix_world.translation
    radial = math.hypot(point.x, point.y) - cup_radius
    vertical = abs(point.z) - cup_half_height
    outside = math.hypot(max(radial, 0.0), max(vertical, 0.0))
    signed_distance = outside + min(max(radial, vertical), 0.0)
    return signed_distance - ball_radius


def first_frame_at(samples, threshold):
    return next((row["frame"] for row in samples if row["cupTiltDegrees"] >= threshold), None)


parser = argparse.ArgumentParser()
parser.add_argument("--cell-id", required=True)
parser.add_argument("--drive-end-frame", type=int, required=True)
parser.add_argument("--source-blend", type=Path, required=True)
parser.add_argument("--work-root", type=Path, required=True)
parser.add_argument("--evidence-root", type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])

if DRIVE_ENDS.get(args.cell_id) != args.drive_end_frame:
    raise RuntimeError("real-impact cell identity mismatch")
source_blend = args.source_blend.resolve(strict=True)
if sha256(source_blend) != SOURCE_SHA256 or Path(bpy.data.filepath).resolve() != source_blend:
    raise RuntimeError("real-impact accepted source identity mismatch")
work_root = args.work_root.resolve(strict=True)
evidence_root = args.evidence_root.resolve(strict=True)
cell_work = work_root / "cells" / args.cell_id
result_path = evidence_root / "cells" / args.cell_id / "result.json"
if cell_work.exists() or result_path.exists():
    raise RuntimeError("real-impact cell roots are not fresh")
cell_work.mkdir(parents=True, exist_ok=False)
result_path.parent.mkdir(parents=True, exist_ok=False)

scene = bpy.context.scene
required_names = (
    "PHYS_OPEN_TUMBLER",
    "PHYS_BASKETBALL",
    "PHYS_VISIBLE_STRIKER",
    "PHYS_BALL_LANE",
    "PHYS_FLOOR",
    "PHYS_LIQUID_DOMAIN",
    "PHYS_INITIAL_LIQUID_VOLUME",
)
required = {name: bpy.data.objects.get(name) for name in required_names}
if any(value is None for value in required.values()):
    raise RuntimeError("real-impact retained scene roster incomplete")
cup = required["PHYS_OPEN_TUMBLER"]
ball = required["PHYS_BASKETBALL"]
pusher = required["PHYS_VISIBLE_STRIKER"]
domain = required["PHYS_LIQUID_DOMAIN"]
source = required["PHYS_INITIAL_LIQUID_VOLUME"]

rigid_identity = (
    cup.rigid_body is not None
    and cup.rigid_body.type == "ACTIVE"
    and cup.rigid_body.collision_shape == "CYLINDER"
    and abs(cup.rigid_body.mass - 0.34) <= 1e-5
    and abs(cup.rigid_body.friction - 0.75) <= 1e-5
    and ball.rigid_body is not None
    and ball.rigid_body.type == "ACTIVE"
    and ball.rigid_body.collision_shape == "SPHERE"
    and abs(ball.rigid_body.mass - 0.62) <= 1e-5
    and abs(ball.rigid_body.friction - 0.48) <= 1e-5
    and pusher.rigid_body is not None
    and pusher.rigid_body.type == "ACTIVE"
    and pusher.rigid_body.collision_shape == "BOX"
    and pusher.rigid_body.kinematic
)
if not rigid_identity:
    raise RuntimeError("real-impact rigid-body identity mismatch")
if cup.animation_data or ball.animation_data:
    raise RuntimeError("real-impact source gives an outcome body authored animation")

# This is a Bullet-only gate. Remove copied fluid modifiers in memory so no
# Mantaflow evaluation can occur; the source blend and retained caches are not saved.
removed_fluid_modifiers = 0
for obj in bpy.data.objects:
    for modifier in list(obj.modifiers):
        if modifier.type == "FLUID":
            obj.modifiers.remove(modifier)
            removed_fluid_modifiers += 1
domain.hide_viewport = True
domain.hide_render = True
source.hide_viewport = True
source.hide_render = True

scene.frame_start = FRAME_START
scene.frame_end = FRAME_END
scene.render.fps = FPS
scene.frame_set(FRAME_START)
if not scene.rigidbody_world:
    raise RuntimeError("real-impact source lacks rigid-body world")
world = scene.rigidbody_world
world.substeps_per_frame = 20
world.solver_iterations = 80
world.point_cache.frame_start = FRAME_START
world.point_cache.frame_end = FRAME_END
with bpy.context.temp_override(point_cache=world.point_cache):
    if world.point_cache.is_baked:
        bpy.ops.ptcache.free_bake()

pusher.animation_data_clear()
for frame, x in (
    (FRAME_START, -1.10),
    (args.drive_end_frame, -0.64),
    (args.drive_end_frame + 1, -0.64),
    (args.drive_end_frame + 3, -1.10),
):
    pusher.location = (x, 0.0, 0.34)
    pusher.keyframe_insert(data_path="location", frame=frame)
for curve in action_curves(pusher):
    for point in curve.keyframe_points:
        point.interpolation = "LINEAR"

scene.frame_set(FRAME_START)
with bpy.context.temp_override(point_cache=world.point_cache):
    bpy.ops.ptcache.bake(bake=True)

cup_local_points = [vertex.co.copy() for vertex in cup.data.vertices]
ball_local_points = [vertex.co.copy() for vertex in ball.data.vertices]
cup_radius = max(math.hypot(point.x, point.y) for point in cup_local_points)
cup_half_height = max(abs(point.z) for point in cup_local_points)
ball_radius = max(point.length for point in ball_local_points)
base_voxel = max(DOMAIN_DIMENSIONS) / PREVIEW_RESOLUTION
domain_low = DOMAIN_CENTER - DOMAIN_DIMENSIONS * 0.5
domain_high = DOMAIN_CENTER + DOMAIN_DIMENSIONS * 0.5
samples = []
previous_points = None
previous_cup_location = None
previous_cup_rotation = None
maximum_surface_displacement = 0.0
maximum_origin_displacement = 0.0
maximum_rotation_delta = 0.0
minimum_bounds = Vector((math.inf, math.inf, math.inf))
maximum_bounds = Vector((-math.inf, -math.inf, -math.inf))
contact_frame = None

for frame in range(FRAME_START, FRAME_END + 1):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    points = world_surface_points(cup)
    low = Vector(tuple(min(point[axis] for point in points) for axis in range(3)))
    high = Vector(tuple(max(point[axis] for point in points) for axis in range(3)))
    for axis in range(3):
        minimum_bounds[axis] = min(minimum_bounds[axis], low[axis])
        maximum_bounds[axis] = max(maximum_bounds[axis], high[axis])
    surface_displacement = 0.0 if previous_points is None else max(
        (points[index] - previous_points[index]).length for index in range(len(points))
    )
    cup_location = cup.matrix_world.translation.copy()
    cup_rotation = cup.matrix_world.to_quaternion()
    origin_displacement = 0.0 if previous_cup_location is None else (cup_location - previous_cup_location).length
    rotation_delta = 0.0 if previous_cup_rotation is None else math.degrees(previous_cup_rotation.rotation_difference(cup_rotation).angle)
    maximum_surface_displacement = max(maximum_surface_displacement, surface_displacement)
    maximum_origin_displacement = max(maximum_origin_displacement, origin_displacement)
    maximum_rotation_delta = max(maximum_rotation_delta, rotation_delta)
    previous_points = points
    previous_cup_location = cup_location
    previous_cup_rotation = cup_rotation
    separation = cylinder_sphere_gap(cup, ball, cup_radius, cup_half_height, ball_radius)
    if contact_frame is None and separation <= 0.01:
        contact_frame = frame
    samples.append(
        {
            "frame": frame,
            "ballLocation": [round(float(value), 8) for value in ball.matrix_world.translation],
            "cupLocation": [round(float(value), 8) for value in cup_location],
            "cupRotationQuaternion": [round(float(value), 8) for value in cup_rotation],
            "cupTiltDegrees": round(tilt_degrees(cup), 8),
            "cupBoundsMin": [round(float(value), 8) for value in low],
            "cupBoundsMax": [round(float(value), 8) for value in high],
            "cupSurfaceDisplacementFromPriorFrameMeters": round(surface_displacement, 8),
            "cupOriginDisplacementFromPriorFrameMeters": round(origin_displacement, 8),
            "cupRotationDeltaFromPriorFrameDegrees": round(rotation_delta, 8),
            "ballCupCollisionSurfaceSeparationMeters": round(separation, 8),
        }
    )

first_5 = first_frame_at(samples, 5.0)
first_45 = first_frame_at(samples, 45.0)
peak_tilt = max(row["cupTiltDegrees"] for row in samples)
required_effector_subframes = max(1, math.ceil(maximum_surface_displacement / base_voxel))
domain_contains_cup = all(
    minimum_bounds[axis] >= domain_low[axis] + base_voxel
    and maximum_bounds[axis] <= domain_high[axis] - base_voxel
    for axis in range(3)
)
animated_rigid_bodies = sorted(
    obj.name for obj in bpy.data.objects if obj.rigid_body is not None and action_curves(obj)
)
checks = {
    "exactAcceptedSource": True,
    "exactRigidBodyIdentity": rigid_identity,
    "bulletOnlyNoFluidModifiers": removed_fluid_modifiers >= 3
    and not any(modifier.type == "FLUID" for obj in bpy.data.objects for modifier in obj.modifiers),
    "noInitialBallCupPenetration": samples[0]["ballCupCollisionSurfaceSeparationMeters"] >= 0.01,
    "derivedContactLeavesTwelveFrameResponseWindow": contact_frame is not None and contact_frame <= 36,
    "solverOwnedCupTiltAtLeast45ByFrame48": first_45 is not None and peak_tilt >= 45.0,
    "responseFollowsDerivedContact": contact_frame is not None
    and first_5 is not None
    and first_45 is not None
    and first_5 >= contact_frame - 1
    and first_45 >= contact_frame,
    "cupRemainsOnFloor": minimum_bounds.z >= -0.005,
    "cupContainedByAcceptedPreviewDomainWithOneVoxelMargin": domain_contains_cup,
    "derivedEffectorSubframesWithinEight": required_effector_subframes <= 8,
    "noOutcomeBodyAnimation": not cup.animation_data and not ball.animation_data,
    "pusherIsOnlyAuthoredRigidActuator": animated_rigid_bodies == ["PHYS_VISIBLE_STRIKER"],
}
result = {
    "schemaVersion": "bfs.rc6RealImpactBulletSpeedScreenCell.v0.1",
    "status": "PASS" if all(checks.values()) else "FAIL",
    "cellId": args.cell_id,
    "configuration": {
        "driveEndFrame": args.drive_end_frame,
        "driveDistanceMeters": 0.46,
        "meanDriveSpeedMetersPerSecond": round(0.46 * FPS / (args.drive_end_frame - FRAME_START), 8),
        "frameStart": FRAME_START,
        "frameEnd": FRAME_END,
        "fps": FPS,
        "bulletSubstepsPerFrame": 20,
        "bulletSolverIterations": 80,
        "previewResolution": PREVIEW_RESOLUTION,
        "acceptedDomainCenterMeters": [float(value) for value in DOMAIN_CENTER],
        "acceptedDomainDimensionsMeters": [float(value) for value in DOMAIN_DIMENSIONS],
        "baseVoxelMeters": round(base_voxel, 10),
        "cupCollisionRadiusMeters": round(cup_radius, 8),
        "cupCollisionHalfHeightMeters": round(cup_half_height, 8),
        "ballCollisionRadiusMeters": round(ball_radius, 8),
    },
    "metrics": {
        "derivedContactFrame": contact_frame,
        "firstFiveDegreeFrame": first_5,
        "firstFortyFiveDegreeFrame": first_45,
        "peakCupTiltDegrees": round(peak_tilt, 8),
        "maximumCupSurfaceDisplacementPerFrameMeters": round(maximum_surface_displacement, 8),
        "maximumCupOriginDisplacementPerFrameMeters": round(maximum_origin_displacement, 8),
        "maximumCupRotationDeltaPerFrameDegrees": round(maximum_rotation_delta, 8),
        "requiredEffectorSubframes": required_effector_subframes,
        "sweptCupBoundsMin": [round(float(value), 8) for value in minimum_bounds],
        "sweptCupBoundsMax": [round(float(value), 8) for value in maximum_bounds],
    },
    "checks": checks,
    "samples": samples,
    "counts": {
        "blenderStarts": 1,
        "bulletBakes": 1,
        "fluidDataBakes": 0,
        "fluidMeshBakes": 0,
        "renders": 0,
        "blendSaves": 0,
        "networkCalls": 0,
        "engineRemoteWrites": 0,
    },
    "claimCeiling": "One exact-scene Bullet-only basketball-impact trajectory; no liquid, cache persistence, render, cinematography or finished-film claim.",
}
result["resultHash"] = self_hash(result, "resultHash")
with result_path.open("x", encoding="utf-8") as handle:
    json.dump(result, handle, indent=2, sort_keys=True)
    handle.write("\n")
print(
    "RC6_REAL_IMPACT_BULLET_SPEED_SCREEN="
    + canonical({"cellId": args.cell_id, "status": result["status"], "resultHash": result["resultHash"]})
)
