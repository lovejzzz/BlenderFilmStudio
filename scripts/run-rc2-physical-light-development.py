#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Development-only RC2 product execution and pixel-causality review."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Matrix


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def render(scene, camera, frame, path):
    scene.frame_set(frame)
    if camera is not None:
        scene.camera = camera
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return {"frame": frame, "uri": path.name, "sha256": sha256_file(path), "bytes": path.stat().st_size}


def mean_receiver_luminance(path, scene, camera, receiver, direction):
    bounds = direction._projected_bounds(scene, camera, [receiver])
    image = bpy.data.images.load(str(path), check_existing=False)
    width, height = image.size
    pixels = list(image.pixels)
    x0 = max(0, min(width - 1, int(bounds[0] * width)))
    x1 = max(x0 + 1, min(width, int(bounds[1] * width)))
    y0 = max(0, min(height - 1, int(bounds[2] * height)))
    y1 = max(y0 + 1, min(height, int(bounds[3] * height)))
    samples = []
    for y in range(y0, y1):
        for x in range(x0, x1):
            offset = (y * width + x) * 4
            red, green, blue = pixels[offset:offset + 3]
            samples.append(0.2126 * red + 0.7152 * green + 0.0722 * blue)
    bpy.data.images.remove(image)
    return {"meanLinearLuminance": sum(samples) / len(samples), "sampleCount": len(samples), "pixelBounds": [x0, x1, y0, y1]}


parser = argparse.ArgumentParser()
parser.add_argument("--source-root", type=Path, required=True)
parser.add_argument("--repository-root", type=Path, required=True)
parser.add_argument("--spec-uri", required=True)
parser.add_argument("--work-root", type=Path, required=True)
parser.add_argument("--evidence-root", type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])

source = args.source_root.resolve(strict=True)
repository = args.repository_root.resolve(strict=True)
work = args.work_root.resolve(strict=True)
evidence = args.evidence_root.resolve(strict=True)
sys.path.insert(0, str(source / "scripts" / "modules"))
import film_studio_physical_light as physical_light
import film_studio_physical_performance as direction

inspection = physical_light.inspect_physical_light(repository, args.spec_uri)
try:
    result = physical_light.execute_physical_light(repository, args.spec_uri, inspection["inspectionToken"], bpy.context.scene)
except physical_light.PhysicalLightError as error:
    scene = bpy.context.scene
    rows = []
    for frame in (1, 45, 50, 55, 70, 144):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        actor = scene.objects.get("PHYSICAL_LIGHT_ROLLING_ACTOR")
        shutter = scene.objects.get("PHYSICAL_LIGHT_SHUTTER")
        rows.append({
            "frame": frame,
            "actorLocation": None if actor is None else list(actor.matrix_world.translation),
            "shutterLocation": None if shutter is None else list(shutter.matrix_world.translation),
            "shutterQuaternion": None if shutter is None else list(shutter.matrix_world.to_quaternion()),
        })
    hinge = scene.objects.get("PHYSICAL_LIGHT_HINGE_CONSTRAINT")
    shutter = scene.objects.get("PHYSICAL_LIGHT_SHUTTER")
    failure = {
        "schemaVersion": "bfs.rc2PhysicalLightDevelopmentFailure.v0.1",
        "status": "FAIL",
        "reason": error.reason,
        "message": str(error),
        "samples": rows,
        "shutterRigidBody": None if shutter is None or shutter.rigid_body is None else {"type": shutter.rigid_body.type, "collisionShape": shutter.rigid_body.collision_shape, "kinematic": shutter.rigid_body.kinematic},
        "hinge": None if hinge is None or hinge.rigid_body_constraint is None else {"type": hinge.rigid_body_constraint.type, "object1": hinge.rigid_body_constraint.object1.name if hinge.rigid_body_constraint.object1 else None, "object2": hinge.rigid_body_constraint.object2.name if hinge.rigid_body_constraint.object2 else None, "enabled": hinge.rigid_body_constraint.enabled},
    }
    write(evidence / "failure.json", failure)
    bpy.ops.wm.save_as_mainfile(filepath=str(work / "RC2_FAILURE.blend"), check_existing=False)
    print("RC2_FAILURE=" + json.dumps(failure, sort_keys=True, separators=(",", ":")))
    raise
scene = bpy.context.scene
scene.render.image_settings.media_type = "IMAGE"
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
bpy.context.preferences.filepaths.file_preview_type = "NONE"

review = evidence / "review"
review.mkdir(parents=True, exist_ok=False)
stills = []
for role in ("cause", "contact", "reveal"):
    shot = result["cinematography"][role]
    path = review / f"{role}-frame-{shot['frame']:04d}.png"
    item = render(scene, scene.objects[shot["camera"]], shot["frame"], path)
    item["role"] = role
    stills.append(item)

reveal = result["cinematography"]["reveal"]
camera = scene.objects[reveal["camera"]]
receiver = scene.objects[result["objects"]["receiver"]]
shutter = scene.objects[result["objects"]["shutter"]]
scene.frame_set(reveal["frame"])
bpy.context.view_layer.update()
actual_path = review / "reveal-actual.png"
render(scene, camera, reveal["frame"], actual_path)
actual_luminance = mean_receiver_luminance(actual_path, scene, camera, receiver, direction)

closed = shutter.copy()
closed.data = shutter.data.copy()
closed.name = "PHYSICAL_LIGHT_CLOSED_COUNTERFACTUAL"
scene.collection.objects.link(closed)
values = list(shutter["film_studio_closed_matrix"])
closed.matrix_world = Matrix((values[0:4], values[4:8], values[8:12], values[12:16]))
shutter.hide_render = True
shutter_children = list(shutter.children_recursive)
for child in shutter_children:
    child.hide_render = True
control_path = review / "reveal-closed-counterfactual.png"
render(scene, camera, reveal["frame"], control_path)
control_luminance = mean_receiver_luminance(control_path, scene, camera, receiver, direction)
shutter.hide_render = False
for child in shutter_children:
    child.hide_render = False
bpy.data.objects.remove(closed, do_unlink=True)

clip_start, clip_end = result["review"]["contactClipFrameRangeInclusive"]
clip_directory = review / "contact-clip-frames"
clip_directory.mkdir(parents=True, exist_ok=False)
clip_frames = []
for frame in range(clip_start, clip_end + 1):
    item = render(scene, None, frame, clip_directory / f"frame-{frame:04d}.png")
    item["camera"] = scene.camera.name
    clip_frames.append(item)

scene.frame_set(scene.frame_start)
blend = work / "RC2_THE_SIGNAL_GATE.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend), check_existing=False)
ratio = actual_luminance["meanLinearLuminance"] / max(1e-12, control_luminance["meanLinearLuminance"])
output = {
    "schemaVersion": "bfs.rc2PhysicalLightDevelopment.v0.1",
    "status": "PASS_EXECUTED",
    "inspection": inspection,
    "result": result,
    "stills": stills,
    "contactClipFrames": {
        "cameraMode": "TIMELINE_MARKER_CAUSE_CONTACT_REVEAL",
        "frameRangeInclusive": [clip_start, clip_end],
        "frameCount": len(clip_frames),
        "frames": clip_frames,
    },
    "illuminationCausality": {
        "actual": actual_luminance,
        "closedShutterCounterfactual": control_luminance,
        "actualToClosedLuminanceRatio": ratio,
        "closedToActualLuminanceRatio": 1.0 / ratio,
        "lightEnergyWatts": scene.objects[result["objects"]["staticRevealLight"]].data.energy,
        "lightAnimationChannels": result["authority"]["lightAnimationChannels"],
    },
    "blend": {"path": str(blend), "sha256": sha256_file(blend), "bytes": blend.stat().st_size},
}
write(evidence / "development.json", output)
print("RC2_DEVELOPMENT=" + json.dumps(output, sort_keys=True, separators=(",", ":")))
