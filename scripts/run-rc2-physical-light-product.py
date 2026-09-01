#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Product-side RC2 build/render and reopen actions."""

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector

import film_studio_physical_performance as direction


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
    return {"frame": frame, "camera": scene.camera.name, "uri": path.name, "sha256": sha256_file(path), "bytes": path.stat().st_size}


def luminance(path, scene, camera, receiver):
    bounds = direction._projected_bounds(scene, camera, [receiver])
    image = bpy.data.images.load(str(path), check_existing=False)
    width, height = image.size
    pixels = list(image.pixels)
    x0, x1 = max(0, int(bounds[0] * width)), min(width, max(1, int(bounds[1] * width)))
    y0, y1 = max(0, int(bounds[2] * height)), min(height, max(1, int(bounds[3] * height)))
    values = []
    for y in range(y0, y1):
        for x in range(x0, x1):
            offset = (y * width + x) * 4
            red, green, blue = pixels[offset:offset + 3]
            values.append(0.2126 * red + 0.7152 * green + 0.0722 * blue)
    bpy.data.images.remove(image)
    return {"meanLinearLuminance": sum(values) / len(values), "sampleCount": len(values), "pixelBounds": [x0, x1, y0, y1]}


def build(repository, spec_uri, evidence, work):
    state = bpy.context.scene.film_studio
    state.causal_repository_root = str(repository)
    state.causal_scene_spec_uri = spec_uri
    if bpy.ops.film_studio.inspect_causal_scene() != {"FINISHED"}:
        raise RuntimeError("RC2 product inspection failed")
    inspection = {"status": state.causal_status, "sceneId": state.causal_scene_id, "specHash": state.causal_scene_spec_hash, "targetCount": state.causal_target_count}
    if bpy.ops.film_studio.execute_causal_scene() != {"FINISHED"}:
        raise RuntimeError("RC2 product execution failed")
    scene = bpy.context.scene
    result = json.loads(scene["film_studio_physical_light_result"])
    if result["status"] != "PASS_EXECUTED":
        raise RuntimeError("RC2 product result did not execute")
    scene.render.resolution_x, scene.render.resolution_y = 960, 540
    scene.render.resolution_percentage = 100
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    bpy.context.preferences.filepaths.file_preview_type = "NONE"
    review = evidence / "review"
    review.mkdir(exist_ok=False)
    stills = []
    for role in ("cause", "contact", "reveal"):
        shot = result["cinematography"][role]
        item = render(scene, scene.objects[shot["camera"]], shot["frame"], review / f"{role}-frame-{shot['frame']:04d}.png")
        item["role"] = role
        stills.append(item)

    reveal = result["cinematography"]["reveal"]
    camera = scene.objects[reveal["camera"]]
    receiver = scene.objects[result["objects"]["receiver"]]
    shutter = scene.objects[result["objects"]["shutter"]]
    actual_path = review / "reveal-actual.png"
    render(scene, camera, reveal["frame"], actual_path)
    actual = luminance(actual_path, scene, camera, receiver)
    closed = shutter.copy(); closed.data = shutter.data.copy(); closed.name = "PHYSICAL_LIGHT_CLOSED_COUNTERFACTUAL"
    scene.collection.objects.link(closed)
    values = list(shutter["film_studio_closed_matrix"])
    closed.matrix_world = Matrix((values[0:4], values[4:8], values[8:12], values[12:16]))
    shutter.hide_render = True
    children = list(shutter.children_recursive)
    for child in children: child.hide_render = True
    control_path = review / "reveal-closed-counterfactual.png"
    render(scene, camera, reveal["frame"], control_path)
    control = luminance(control_path, scene, camera, receiver)
    shutter.hide_render = False
    for child in children: child.hide_render = False
    bpy.data.objects.remove(closed, do_unlink=True)

    clip_start, clip_end = result["review"]["contactClipFrameRangeInclusive"]
    clip_root = evidence / "clip"; clip_root.mkdir(exist_ok=False)
    clip = []
    for frame in range(clip_start, clip_end + 1):
        item = render(scene, None, frame, clip_root / f"frame-{frame:04d}.png")
        item["uri"] = f"clip/{item['uri']}"
        clip.append(item)
    scene.frame_set(scene.frame_start)
    blend = work / "RC2_THE_SIGNAL_GATE.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend), check_existing=False)
    ratio = actual["meanLinearLuminance"] / max(1e-12, control["meanLinearLuminance"])
    output = {
        "schemaVersion": "bfs.rc2PhysicalLightBuild.v0.1", "status": "PASS", "inspection": inspection, "result": result,
        "stills": stills, "clip": {"startFrame": clip_start, "endFrame": clip_end, "frameCount": len(clip), "frames": clip},
        "illuminationCausality": {"actual": actual, "closedShutterCounterfactual": control, "actualToClosedLuminanceRatio": ratio, "closedToActualLuminanceRatio": 1.0 / ratio, "lightEnergyWatts": scene.objects[result["objects"]["staticRevealLight"]].data.energy, "lightAnimationChannels": result["authority"]["lightAnimationChannels"]},
        "blend": {"path": str(blend), "sha256": sha256_file(blend), "bytes": blend.stat().st_size},
        "counts": {"sceneMutatingExecutions": 1, "blendSaves": 1, "reviewStillRenders": 3, "contactClipFrameRenders": len(clip)}, "networkCalls": 0,
    }
    write(evidence / "build.json", output)
    print("RC2_BUILD=" + json.dumps(output, sort_keys=True, separators=(",", ":")))


def reopen(evidence):
    scene = bpy.context.scene
    build_result = json.loads((evidence / "build.json").read_text(encoding="utf-8"))
    expected = build_result["result"]
    stored = json.loads(scene["film_studio_physical_light_result"])
    actor = scene.objects[expected["objects"]["actor"]]
    shutter = scene.objects[expected["objects"]["shutter"]]
    samples = expected["physics"]["samples"]
    scene.frame_set(samples[0]["frame"]); bpy.context.view_layer.update()
    initial_shutter = shutter.matrix_world.to_quaternion().copy()
    location_deltas, actor_angle_deltas, shutter_angle_deltas = [], [], []
    for sample in samples:
        scene.frame_set(sample["frame"]); bpy.context.view_layer.update()
        location_deltas.append((actor.matrix_world.translation - Vector(sample["actorLocation"])).length)
        actor_angle_deltas.append(math.degrees(Quaternion(sample["actorQuaternion"]).rotation_difference(actor.matrix_world.to_quaternion()).angle))
        observed = math.degrees(initial_shutter.rotation_difference(shutter.matrix_world.to_quaternion()).angle)
        shutter_angle_deltas.append(abs(observed - sample["shutterAngleDegrees"]))
    checks = {
        "storedResultExact": stored == expected,
        "storedResultHashExact": scene["film_studio_physical_light_result_hash"] == expected["resultHash"],
        "actorLocationDelta": max(location_deltas) <= 1e-6,
        "actorAngleDelta": max(actor_angle_deltas) <= 0.001,
        "shutterAngleDelta": max(shutter_angle_deltas) <= 0.001,
        "actorPoseKeysZero": expected["authority"]["actorPoseKeyframesAfterRelease"] == 0,
        "shutterPoseKeysZero": expected["authority"]["shutterPoseKeyframesAfterContact"] == 0,
        "lightAnimationZero": expected["authority"]["lightAnimationChannels"] == 0,
    }
    output = {"schemaVersion": "bfs.rc2PhysicalLightReopen.v0.1", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "sampleCount": len(samples), "maximumActorLocationDeltaMeters": max(location_deltas), "maximumActorAngleDeltaDegrees": max(actor_angle_deltas), "maximumShutterAngleDeltaDegrees": max(shutter_angle_deltas), "networkCalls": 0}
    write(evidence / "reopen.json", output)
    print("RC2_REOPEN=" + json.dumps(output, sort_keys=True, separators=(",", ":")))
    if output["status"] != "PASS": raise RuntimeError("RC2 reopen mismatch")


parser = argparse.ArgumentParser()
parser.add_argument("--action", choices=("build", "reopen"), required=True)
parser.add_argument("--repository-root", type=Path, required=True)
parser.add_argument("--scene-spec-uri", required=True)
parser.add_argument("--evidence-root", type=Path, required=True)
parser.add_argument("--work-root", type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
repository = args.repository_root.resolve(strict=True); evidence = args.evidence_root.resolve(strict=True); work = args.work_root.resolve(strict=True)
build(repository, args.scene_spec_uri, evidence, work) if args.action == "build" else reopen(evidence)
