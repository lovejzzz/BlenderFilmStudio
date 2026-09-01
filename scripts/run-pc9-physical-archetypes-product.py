#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Product-side PC9 build, render, save and reopen actions."""

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

import bpy
import film_studio_causal


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def action_fcurves(obj):
    action = obj.animation_data.action if obj.animation_data and obj.animation_data.action else None
    if action is None:
        return []
    if hasattr(action, "fcurves"):
        return list(action.fcurves)
    return [curve for layer in action.layers for strip in layer.strips for bag in strip.channelbags for curve in bag.fcurves]


def authored_frames(obj, paths=None):
    curves = action_fcurves(obj)
    if paths is not None:
        curves = [curve for curve in curves if curve.data_path in paths]
    return sorted({int(round(point.co.x)) for curve in curves for point in curve.keyframe_points})


def set_frame(scene, frame):
    for current in range(scene.frame_start, frame + 1):
        scene.frame_set(current)
        bpy.context.view_layer.update()


def render(scene, camera, frame, path, motion_blur, shutter, position):
    set_frame(scene, frame)
    scene.camera = camera
    scene.render.use_motion_blur = motion_blur
    scene.render.motion_blur_shutter = shutter
    scene.render.motion_blur_position = position
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return {"frame": frame, "uri": path.name, "sha256": sha256_file(path), "bytes": path.stat().st_size}


def build(root, spec_uri, evidence, work):
    state = bpy.context.scene.film_studio
    state.causal_repository_root = str(root)
    state.causal_scene_spec_uri = spec_uri
    if bpy.ops.film_studio.inspect_causal_scene() != {"FINISHED"} or bpy.ops.film_studio.execute_causal_scene() != {"FINISHED"}:
        raise RuntimeError("PC9 product operators failed")
    scene = bpy.context.scene
    result = json.loads(scene["film_studio_causal_result"])
    document = json.loads((root / spec_uri).read_text(encoding="utf-8"))
    actor = bpy.data.objects[result["semanticRoster"]["dynamicActor"][0]]
    targets = [bpy.data.objects[name] for name in result["semanticRoster"]["targets"]]
    actor_frames = authored_frames(actor, {"location", "rotation_euler"})
    target_frames = {target.name: authored_frames(target) for target in targets}
    blur = result["cinematography"]["motionBlur"]
    shutter, position = blur["computedShutterFrames"], blur["position"]
    impact = result["physics"]["motionSelection"]["impactFrame"]
    review_root = evidence / "review"; review_root.mkdir()
    sharp_path = review_root / f"impact-sharp-control-frame-{impact:04d}.png"
    sharp = {"shotId": "IMPACT_SHARP_CONTROL", **render(scene, bpy.data.objects["CAUSAL_CAM_IMPACT"], impact, sharp_path, False, shutter, position)}
    review = []
    for shot_id in ("SETUP", "IMPACT", "AFTERMATH"):
        framing = result["framing"][shot_id]
        path = review_root / f"{shot_id.lower()}-measured-frame-{framing['frame']:04d}.png"
        item = render(scene, bpy.data.objects[f"CAUSAL_CAM_{shot_id}"], framing["frame"], path, True, shutter, position)
        item.update({"shotId": shot_id, "framing": framing}); review.append(item)
    clip_count = document["acceptance"]["impactClipFrameCount"]
    clip_start = impact - 6; clip_end = clip_start + clip_count - 1
    clip_root = evidence / "clip"; clip_root.mkdir(); clip = []
    for frame in range(clip_start, clip_end + 1):
        path = clip_root / f"frame-{frame:04d}.png"
        item = render(scene, bpy.data.objects["CAUSAL_CAM_IMPACT"], frame, path, True, shutter, position)
        item["uri"] = path.relative_to(evidence).as_posix(); clip.append(item)
    blend = work / "PC9_PHYSICAL_ARCHETYPES.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend), check_existing=False)
    output = {
        "schemaVersion": "bfs.pc9PhysicalArchetypesBuild.v0.1", "status": "PASS",
        "physics": result["physics"], "physicalArchetypes": result["physicalArchetypes"], "initialConditions": result["initialConditions"],
        "cinematography": result["cinematography"], "framing": result["framing"], "provenance": result["provenance"], "semanticRoster": result["semanticRoster"],
        "animation": {"actorPoseFrames": actor_frames, "actorPoseFramesAfterRelease": [frame for frame in actor_frames if frame >= document["timeline"]["releaseFrame"]], "targetFrames": target_frames},
        "solverFloat32MassesKg": [target.rigid_body.mass for target in targets],
        "canonicalMassesKg": [target["film_studio_mass_kg"] for target in targets],
        "centerOfMassHeightsMeters": [target["film_studio_center_of_mass_height_m"] for target in targets],
        "refraction": {"screen": [bpy.data.materials[f"MAT_CausalBottleShell_{i:02d}"].use_screen_refraction for i in range(1, 4)], "raytrace": [bpy.data.materials[f"MAT_CausalBottleShell_{i:02d}"].use_raytrace_refraction for i in range(1, 4)]},
        "sharpImpactControl": sharp, "review": review, "clip": {"startFrame": clip_start, "endFrame": clip_end, "frameCount": len(clip), "frames": clip},
        "blend": {"path": str(blend), "sha256": sha256_file(blend), "bytes": blend.stat().st_size}, "renderCalls": 4 + len(clip), "networkCalls": 0,
    }
    write(evidence / "build.json", output)
    print("PC9_BUILD=" + json.dumps(output, sort_keys=True, separators=(",", ":")))


def reopen(root, spec_uri, evidence):
    scene = bpy.context.scene
    saved = json.loads(scene["film_studio_causal_result"])
    document = json.loads((root / spec_uri).read_text(encoding="utf-8"))
    actor = bpy.data.objects[saved["semanticRoster"]["dynamicActor"][0]]
    targets = [bpy.data.objects[name] for name in saved["semanticRoster"]["targets"]]
    physics = film_studio_causal._simulate(scene, actor, targets, document)
    measured = film_studio_causal._configure_measured_shutter(scene, bpy.data.objects["CAUSAL_CAM_IMPACT"], [actor, *targets], physics["motionSelection"]["impactFrame"], document)
    expected = document["acceptance"]["derivedMassesKgExact"]
    expected_solver = [struct.unpack("f", struct.pack("f", value))[0] for value in expected]
    checks = {
        "physicsExact": physics == saved["physics"], "motionBlurExact": measured == saved["cinematography"]["motionBlur"],
        "physicalArchetypesExact": saved["physicalArchetypes"]["targets"] == saved["initialConditions"]["targets"],
        "canonicalMassesExact": [target["film_studio_mass_kg"] for target in targets] == expected,
        "solverFloat32MassesExact": [target.rigid_body.mass for target in targets] == expected_solver,
        "centersOfMassExact": [target["film_studio_center_of_mass_height_m"] for target in targets] == document["acceptance"]["derivedCenterOfMassHeightsMetersExact"],
        "screenRefractionExact": all(bpy.data.materials[f"MAT_CausalBottleShell_{i:02d}"].use_screen_refraction for i in range(1, 4)),
        "raytraceRefractionExact": all(bpy.data.materials[f"MAT_CausalBottleShell_{i:02d}"].use_raytrace_refraction for i in range(1, 4)),
        "poseAuthorityZero": saved["provenance"]["targetPoseKeyframes"] == saved["provenance"]["postReleaseActorPoseKeyframes"] == 0,
    }
    result = {"schemaVersion": "bfs.pc9PhysicalArchetypesReopen.v0.1", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "networkCalls": 0}
    write(evidence / "reopen.json", result)
    print("PC9_REOPEN=" + json.dumps(result, sort_keys=True, separators=(",", ":")))
    if result["status"] != "PASS": raise RuntimeError("PC9 reopen mismatch")


parser = argparse.ArgumentParser()
parser.add_argument("--action", choices=("build", "reopen"), required=True)
parser.add_argument("--repository-root", required=True); parser.add_argument("--scene-spec-uri", required=True)
parser.add_argument("--evidence-root", required=True); parser.add_argument("--work-root", required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
repository = Path(args.repository_root).resolve(); evidence = Path(args.evidence_root).resolve(); work = Path(args.work_root).resolve()
build(repository, args.scene_spec_uri, evidence, work) if args.action == "build" else reopen(repository, args.scene_spec_uri, evidence)
