#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Verify that a saved RC2 Bullet result round-trips without transform drift."""

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Quaternion, Vector


parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])

scene = bpy.context.scene
result = json.loads(scene["film_studio_physical_light_result"])
actor = scene.objects[result["objects"]["actor"]]
shutter = scene.objects[result["objects"]["shutter"]]
samples = result["physics"]["samples"]

scene.frame_set(samples[0]["frame"])
bpy.context.view_layer.update()
initial_shutter = shutter.matrix_world.to_quaternion().copy()

max_actor_location_delta = 0.0
max_actor_angle_delta_degrees = 0.0
max_shutter_angle_delta_degrees = 0.0
worst = {"actorLocationFrame": None, "actorAngleFrame": None, "shutterAngleFrame": None}
for sample in samples:
    frame = sample["frame"]
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    location_delta = (actor.matrix_world.translation - Vector(sample["actorLocation"])).length
    expected_actor = Quaternion(sample["actorQuaternion"])
    actor_angle_delta = math.degrees(expected_actor.rotation_difference(actor.matrix_world.to_quaternion()).angle)
    shutter_angle = math.degrees(initial_shutter.rotation_difference(shutter.matrix_world.to_quaternion()).angle)
    shutter_angle_delta = abs(shutter_angle - sample["shutterAngleDegrees"])
    if location_delta > max_actor_location_delta:
        max_actor_location_delta = location_delta
        worst["actorLocationFrame"] = frame
    if actor_angle_delta > max_actor_angle_delta_degrees:
        max_actor_angle_delta_degrees = actor_angle_delta
        worst["actorAngleFrame"] = frame
    if shutter_angle_delta > max_shutter_angle_delta_degrees:
        max_shutter_angle_delta_degrees = shutter_angle_delta
        worst["shutterAngleFrame"] = frame

thresholds = {"maxActorLocationDeltaMeters": 1e-6, "maxActorAngleDeltaDegrees": 0.001, "maxShutterAngleDeltaDegrees": 0.001}
measurements = {
    "maxActorLocationDeltaMeters": max_actor_location_delta,
    "maxActorAngleDeltaDegrees": max_actor_angle_delta_degrees,
    "maxShutterAngleDeltaDegrees": max_shutter_angle_delta_degrees,
}
checks = {key: measurements[key] <= value for key, value in thresholds.items()}
receipt = {
    "schemaVersion": "bfs.rc2PhysicalLightReopenDevelopment.v0.1",
    "status": "PASS" if all(checks.values()) else "FAIL",
    "sourceResultHash": result["resultHash"],
    "sampleCount": len(samples),
    "thresholds": thresholds,
    "measurements": measurements,
    "checks": checks,
    "worstFrames": worst,
}
args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print("RC2_REOPEN=" + json.dumps(receipt, sort_keys=True, separators=(",", ":")))
if receipt["status"] != "PASS":
    raise SystemExit(1)
