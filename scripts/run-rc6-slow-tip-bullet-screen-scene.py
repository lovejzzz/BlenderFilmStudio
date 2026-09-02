#!/usr/bin/env python3
"""Measure slow Bullet-owned tumbler trajectories without running Mantaflow."""

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
FRAME_END = 64
FPS = 24
PREVIEW_RESOLUTION = 96
CANDIDATE_DOMAIN_CENTER = Vector((0.40, 0.0, 0.26))
CANDIDATE_DOMAIN_DIMENSIONS = Vector((0.80, 0.50, 0.56))
DRIVE_ENDS = {"D12": 12, "D16": 16, "D20": 20, "D24": 24}


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


def world_corners(obj):
    return [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]


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
    raise RuntimeError("slow-tip cell identity mismatch")
source_blend = args.source_blend.resolve(strict=True)
if sha256(source_blend) != SOURCE_SHA256 or Path(bpy.data.filepath).resolve() != source_blend:
    raise RuntimeError("slow-tip accepted source identity mismatch")
work_root = args.work_root.resolve(strict=True)
evidence_root = args.evidence_root.resolve(strict=True)
cell_work = work_root / "cells" / args.cell_id
result_path = evidence_root / "cells" / args.cell_id / "result.json"
if cell_work.exists() or result_path.exists():
    raise RuntimeError("slow-tip cell roots are not fresh")
cell_work.mkdir(parents=True, exist_ok=False)
result_path.parent.mkdir(parents=True, exist_ok=False)

scene = bpy.context.scene
required = {
    name: bpy.data.objects.get(name)
    for name in (
        "PHYS_OPEN_TUMBLER",
        "PHYS_BASKETBALL",
        "PHYS_VISIBLE_STRIKER",
        "PHYS_BALL_LANE",
        "PHYS_FLOOR",
        "PHYS_LIQUID_DOMAIN",
        "PHYS_INITIAL_LIQUID_VOLUME",
    )
}
if any(value is None for value in required.values()):
    raise RuntimeError("slow-tip retained scene roster incomplete")
cup = required["PHYS_OPEN_TUMBLER"]
ball = required["PHYS_BASKETBALL"]
pusher = required["PHYS_VISIBLE_STRIKER"]
domain = required["PHYS_LIQUID_DOMAIN"]
source = required["PHYS_INITIAL_LIQUID_VOLUME"]

if (
    cup.rigid_body is None
    or cup.rigid_body.type != "ACTIVE"
    or cup.rigid_body.collision_shape != "CYLINDER"
    or abs(cup.rigid_body.mass - 0.34) > 1e-5
    or ball.rigid_body is None
    or ball.rigid_body.type != "ACTIVE"
    or ball.rigid_body.collision_shape != "SPHERE"
    or pusher.rigid_body is None
    or not pusher.rigid_body.kinematic
):
    raise RuntimeError("slow-tip rigid-body identity mismatch")
if cup.animation_data or ball.animation_data:
    raise RuntimeError("slow-tip source gives an outcome body authored animation")

# The screen measures Bullet only. Removing copied modifiers prevents accidental
# fluid evaluation while leaving the accepted source file and retained cache untouched.
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
    raise RuntimeError("slow-tip source lacks rigid-body world")
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
    (args.drive_end_frame + 5, -1.10),
):
    pusher.location = (x, 0.0, 0.34)
    pusher.keyframe_insert(data_path="location", frame=frame)
for curve in action_curves(pusher):
    for point in curve.keyframe_points:
        point.interpolation = "LINEAR"

scene.frame_set(FRAME_START)
with bpy.context.temp_override(point_cache=world.point_cache):
    bpy.ops.ptcache.bake(bake=True)

base_voxel = max(CANDIDATE_DOMAIN_DIMENSIONS) / PREVIEW_RESOLUTION
domain_low = CANDIDATE_DOMAIN_CENTER - CANDIDATE_DOMAIN_DIMENSIONS * 0.5
domain_high = CANDIDATE_DOMAIN_CENTER + CANDIDATE_DOMAIN_DIMENSIONS * 0.5
samples = []
previous_corners = None
maximum_surface_displacement = 0.0
minimum_bounds = Vector((math.inf, math.inf, math.inf))
maximum_bounds = Vector((-math.inf, -math.inf, -math.inf))
contact_frame = None

for frame in range(FRAME_START, FRAME_END + 1):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    corners = world_corners(cup)
    low = Vector(tuple(min(point[axis] for point in corners) for axis in range(3)))
    high = Vector(tuple(max(point[axis] for point in corners) for axis in range(3)))
    for axis in range(3):
        minimum_bounds[axis] = min(minimum_bounds[axis], low[axis])
        maximum_bounds[axis] = max(maximum_bounds[axis], high[axis])
    surface_displacement = 0.0 if previous_corners is None else max(
        (corners[index] - previous_corners[index]).length for index in range(len(corners))
    )
    maximum_surface_displacement = max(maximum_surface_displacement, surface_displacement)
    previous_corners = corners
    separation = (ball.matrix_world.translation - cup.matrix_world.translation).length - 0.27
    if contact_frame is None and separation <= 0.01:
        contact_frame = frame
    samples.append(
        {
            "frame": frame,
            "ballLocation": [round(float(value), 8) for value in ball.matrix_world.translation],
            "cupLocation": [round(float(value), 8) for value in cup.matrix_world.translation],
            "cupRotationQuaternion": [round(float(value), 8) for value in cup.matrix_world.to_quaternion()],
            "cupTiltDegrees": round(tilt_degrees(cup), 8),
            "cupBoundsMin": [round(float(value), 8) for value in low],
            "cupBoundsMax": [round(float(value), 8) for value in high],
            "surfaceDisplacementFromPriorFrameMeters": round(surface_displacement, 8),
            "ballCupSurfaceSeparationMeters": round(separation, 8),
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
slow_tilt_span = None if first_5 is None or first_45 is None else first_45 - first_5
checks = {
    "exactAcceptedSource": True,
    "bulletOnlyNoFluidModifiers": removed_fluid_modifiers >= 3
    and not any(modifier.type == "FLUID" for obj in bpy.data.objects for modifier in obj.modifiers),
    "contactByFrame50": contact_frame is not None and contact_frame <= 50,
    "solverOwnedCupTiltAtLeast45Degrees": first_45 is not None and peak_tilt >= 45.0,
    "slowTiltSpansAtLeastFourFrames": slow_tilt_span is not None and slow_tilt_span >= 4,
    "cupRemainsOnFloor": minimum_bounds.z >= -0.005,
    "cupContainedByCandidateDomainWithOneVoxelMargin": domain_contains_cup,
    "derivedEffectorSubframesWithinTen": required_effector_subframes <= 10,
    "noOutcomeBodyAnimation": not cup.animation_data and not ball.animation_data,
    "pusherIsOnlyAuthoredActuator": bool(action_curves(pusher)) and pusher.rigid_body.kinematic,
}
result = {
    "schemaVersion": "bfs.rc6SlowTipBulletScreenCell.v0.1",
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
        "candidateDomainCenterMeters": [float(value) for value in CANDIDATE_DOMAIN_CENTER],
        "candidateDomainDimensionsMeters": [float(value) for value in CANDIDATE_DOMAIN_DIMENSIONS],
        "baseVoxelMeters": round(base_voxel, 10),
    },
    "metrics": {
        "contactFrame": contact_frame,
        "firstFiveDegreeFrame": first_5,
        "firstFortyFiveDegreeFrame": first_45,
        "slowTiltSpanFrames": slow_tilt_span,
        "peakCupTiltDegrees": round(peak_tilt, 8),
        "maximumCupSurfaceDisplacementPerFrameMeters": round(maximum_surface_displacement, 8),
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
    "claimCeiling": "One Bullet-only slow-tip trajectory screen; no liquid behavior, persistence, render or finished-film claim.",
}
result["resultHash"] = self_hash(result, "resultHash")
with result_path.open("x", encoding="utf-8") as handle:
    json.dump(result, handle, indent=2, sort_keys=True)
    handle.write("\n")
print("RC6_SLOW_TIP_BULLET_SCREEN=" + canonical({"cellId": args.cell_id, "status": result["status"], "resultHash": result["resultHash"]}))

