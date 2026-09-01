#!/usr/bin/env python3
"""Zero-render Bullet calibration for an on-set, high-contact ball-to-tumbler impact."""

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def self_hash(value, field):
    copy = dict(value)
    copy.pop(field, None)
    return hashlib.sha256(canonical(copy).encode()).hexdigest()


def add_cube(name, location, scale):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj


def add_body(obj, kind, shape, mass, friction, restitution):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.rigidbody.object_add()
    obj.rigid_body.type = kind
    obj.rigid_body.collision_shape = shape
    obj.rigid_body.mass = mass
    obj.rigid_body.friction = friction
    obj.rigid_body.restitution = restitution
    obj.rigid_body.linear_damping = 0.04
    obj.rigid_body.angular_damping = 0.06
    obj.select_set(False)


def action_curves(obj):
    action = obj.animation_data.action
    if hasattr(action, "fcurves"):
        return list(action.fcurves)
    return [curve for layer in action.layers for strip in layer.strips for channelbag in strip.channelbags for curve in channelbag.fcurves]


def tilt(obj):
    up = obj.matrix_world.to_3x3() @ Vector((0, 0, 1))
    return math.degrees(math.acos(max(-1.0, min(1.0, up.normalized().dot(Vector((0, 0, 1)))))))


def run_variant(variant):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end, scene.render.fps = 1, 24, 24
    floor = add_cube("FLOOR", (0.4, 0.0, -0.05), (3.0, 1.2, 0.05))
    lane = add_cube("BALL_LANE", (-0.42, 0.0, 0.05), (0.70, 0.22, 0.05))
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=0.12, location=(-0.88, 0.0, 0.22))
    ball = bpy.context.object
    ball.name = "BALL"
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=0.17, depth=0.28, location=(0.32, 0.0, 0.14))
    cup = bpy.context.object
    cup.name = "TUMBLER_PROXY"
    pusher = add_cube("VISIBLE_STRIKER", (-1.10, 0.0, 0.22), (0.05, 0.15, 0.12))
    add_body(floor, "PASSIVE", "BOX", 1.0, 0.65, 0.05)
    add_body(lane, "PASSIVE", "BOX", 1.0, 0.55, 0.08)
    add_body(ball, "ACTIVE", "SPHERE", 0.62, 0.48, 0.32)
    add_body(cup, "ACTIVE", "CYLINDER", variant["cupMass"], variant["cupFriction"], 0.05)
    add_body(pusher, "ACTIVE", "BOX", 4.0, 0.55, 0.12)
    pusher.rigid_body.kinematic = True
    end = variant["driveEndFrame"]
    for frame, x in ((1, -1.10), (end, -0.64), (end + 1, -0.64), (end + 3, -1.10)):
        pusher.location.x = x
        pusher.keyframe_insert(data_path="location", frame=frame)
    for curve in action_curves(pusher):
        for point in curve.keyframe_points:
            point.interpolation = "LINEAR"
    scene.rigidbody_world.substeps_per_frame = 20
    scene.rigidbody_world.solver_iterations = 80
    scene.rigidbody_world.point_cache.frame_start = 1
    scene.rigidbody_world.point_cache.frame_end = 24
    with bpy.context.temp_override(point_cache=scene.rigidbody_world.point_cache):
        bpy.ops.ptcache.bake(bake=True)
    samples = []
    contact = None
    for frame in range(1, 25):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        gap = (ball.matrix_world.translation - cup.matrix_world.translation).length - 0.29
        cup_tilt = tilt(cup)
        if contact is None and (gap <= 0.01 or cup_tilt >= 1.0):
            contact = frame
        samples.append({
            "frame": frame,
            "ball": [round(v, 7) for v in ball.matrix_world.translation],
            "cup": [round(v, 7) for v in cup.matrix_world.translation],
            "cupTiltDegrees": round(cup_tilt, 7),
            "contactGapMeters": round(gap, 7),
        })
    contact = contact or 24
    window = [row for row in samples if contact <= row["frame"] <= min(24, contact + 8)]
    window_peak = max(row["cupTiltDegrees"] for row in window)
    peak = max(row["cupTiltDegrees"] for row in samples)
    cup_x = max(abs(row["cup"][0]) for row in samples)
    cup_min_z = min(row["cup"][2] for row in samples)
    checks = {
        "contactByFrame12": contact <= 12,
        "impactWindowTilt": window_peak >= 45.0,
        "cupStaysOnSetX": cup_x <= 1.40,
        "cupDoesNotFall": cup_min_z >= 0.08,
        "ballUnanimated": ball.animation_data is None,
        "strikerIsSoleActuator": pusher.rigid_body.kinematic and pusher.animation_data is not None,
    }
    return {
        "id": variant["id"],
        "inputs": variant,
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "contactFrame": contact,
        "impactWindowPeakTiltDegrees": round(window_peak, 7),
        "peakTiltDegrees": round(peak, 7),
        "maximumAbsoluteCupX": round(cup_x, 7),
        "minimumCupZ": round(cup_min_z, 7),
        "samples": samples,
    }


parser = argparse.ArgumentParser()
parser.add_argument("--evidence-root", type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
root = args.evidence_root.resolve()
root.mkdir(parents=True, exist_ok=False)
variants = [
    {"id": "P01", "driveEndFrame": 5, "cupMass": 0.34, "cupFriction": 0.65},
    {"id": "P02", "driveEndFrame": 6, "cupMass": 0.34, "cupFriction": 0.75},
    {"id": "P03", "driveEndFrame": 7, "cupMass": 0.34, "cupFriction": 0.85},
    {"id": "P04", "driveEndFrame": 6, "cupMass": 0.50, "cupFriction": 0.85},
    {"id": "P05", "driveEndFrame": 7, "cupMass": 0.25, "cupFriction": 0.85},
    {"id": "P06", "driveEndFrame": 8, "cupMass": 0.25, "cupFriction": 0.95}
]
results = [run_variant(variant) for variant in variants]
passing = [row for row in results if row["status"] == "PASS"]
selected = max(passing, key=lambda row: row["impactWindowPeakTiltDegrees"] - row["maximumAbsoluteCupX"] * 5.0)["id"] if passing else None
output = {
    "schemaVersion": "bfs.rc6BulletLauncherCalibration.v0.1",
    "status": "PASS" if selected else "FAIL",
    "selectedVariant": selected,
    "variants": results,
    "counts": {"blenderStarts": 1, "bulletBakes": 6, "renders": 0, "saves": 0, "networkCalls": 0},
    "claimCeiling": "Six bounded Bullet-only launcher calibrations; no fluid behavior or final cinematography claim.",
}
output["resultHash"] = self_hash(output, "resultHash")
(root / "result.json").write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print("RC6_BULLET_CALIBRATION=" + canonical({"status": output["status"], "selectedVariant": selected, "resultHash": output["resultHash"]}))
if output["status"] != "PASS":
    raise RuntimeError("RC6 Bullet launcher calibration found no passing variant")
