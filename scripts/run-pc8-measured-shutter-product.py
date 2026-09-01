#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Product-side PC8 measured-shutter validation actions."""

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

import bpy
import film_studio_causal


V2_URI = "specs/fixtures/causal-studio/PC7_F1.five-domino-filmic-physics.scene-spec.v0.2.json"
RETIRED_V3_URI = "specs/fixtures/causal-studio/PC8_F1.measured-shutter-filmic-physics.scene-spec.v0.3.json"


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def action_fcurves(obj):
    action = obj.animation_data.action if obj.animation_data and obj.animation_data.action else None
    if action is None:
        return []
    if hasattr(action, "fcurves"):
        return list(action.fcurves)
    return [curve for layer in action.layers for strip in layer.strips for bag in strip.channelbags for curve in bag.fcurves]


def authored_frames(obj, data_paths=None):
    curves = action_fcurves(obj)
    if data_paths is not None:
        curves = [curve for curve in curves if curve.data_path in data_paths]
    return sorted({int(round(point.co.x)) for curve in curves for point in curve.keyframe_points})


def run_negative(root, spec_uri, evidence):
    original = json.loads((root / spec_uri).read_text(encoding="utf-8"))
    negative_root = evidence / "negative"
    negative_root.mkdir()
    cases = []

    def reject(case_id, expected, document=None, uri=None, recompute=True):
        before = sorted(obj.name for obj in bpy.context.scene.objects)
        if document is not None:
            if recompute:
                document["sceneSpecHash"] = film_studio_causal._self_hash(document, "sceneSpecHash")
            path = negative_root / f"{case_id.lower()}.json"
            path.write_text(json.dumps(document, indent=2, allow_nan=True) + "\n", encoding="utf-8")
            uri = path.relative_to(root).as_posix()
        observed = None
        try:
            film_studio_causal.inspect_causal_scene(str(root), uri)
        except film_studio_causal.CausalContractError as error:
            observed = error.reason
        cases.append({"caseId": case_id, "expected": expected, "observed": observed, "sceneUnchanged": before == sorted(obj.name for obj in bpy.context.scene.objects)})

    reject("PATH_ESCAPE", "PATH_ESCAPE", uri="../escape.json")
    reject("RETIRED_V03", "UNKNOWN_TOP_LEVEL_FIELD", uri=RETIRED_V3_URI)
    document = copy.deepcopy(original); document["unexpected"] = True
    reject("UNKNOWN_TOP_LEVEL_FIELD", "UNKNOWN_TOP_LEVEL_FIELD", document=document, recompute=False)
    document = copy.deepcopy(original); document["cinematography"]["motionBlur"]["shutterFrames"] = 0.3
    reject("MANUAL_SHUTTER_FIELD", "SPEC_SCHEMA", document=document)
    document = copy.deepcopy(original); document["cinematography"]["motionBlur"]["strategy"] = "MANUAL"
    reject("UNSUPPORTED_STRATEGY", "SPEC_SCHEMA", document=document)
    document = copy.deepcopy(original); document["cinematography"]["motionBlur"]["semanticRoles"] = ["target_group"]
    reject("MISSING_ACTOR_ROLE", "SPEC_SCHEMA", document=document)
    document = copy.deepcopy(original); document["cinematography"]["motionBlur"]["measurementResolution"] = [1920, 1080]
    reject("UNBOUND_RESOLUTION", "SPEC_SCHEMA", document=document)
    document = copy.deepcopy(original); document["cinematography"]["motionBlur"]["targetBlurPixels"] = 25.0
    reject("BLUR_TARGET_OUT_OF_RANGE", "SPEC_SCHEMA", document=document)
    document = copy.deepcopy(original); document["cinematography"]["motionBlur"]["minimumShutterFrames"] = 0.7
    reject("REVERSED_SHUTTER_BOUNDS", "SPEC_SCHEMA", document=document)
    document = copy.deepcopy(original); document["targetGroup"]["deterministicVariation"]["basisSceneSpecHash"] = "python"
    reject("INVALID_VARIATION_BASIS", "SPEC_SCHEMA", document=document)
    document = copy.deepcopy(original); document["forbidden"]["manualShutterValue"] = False
    reject("MANUAL_SHUTTER_AUTHORITY", "SPEC_EXECUTABLE_AUTHORITY", document=document)
    document = copy.deepcopy(original); document["forbidden"]["compositorOrPostprocessBlur"] = False
    reject("POSTPROCESS_BLUR_AUTHORITY", "SPEC_EXECUTABLE_AUTHORITY", document=document)
    document = copy.deepcopy(original); document["forbidden"]["effectCoverForWeakerPrimaryPhysics"] = False
    reject("EFFECT_COVER_AUTHORITY", "SPEC_EXECUTABLE_AUTHORITY", document=document)
    document = copy.deepcopy(original); document["acceptance"]["targetPoseKeyframes"] = 1
    reject("FINAL_POSE_AUTHORITY", "FINAL_POSE_AUTHORITY", document=document)
    document = copy.deepcopy(original); document["targetGroup"]["deterministicVariation"]["python"] = "import os"
    reject("VARIATION_EXECUTABLE_AUTHORITY", "SPEC_SCHEMA", document=document)
    before = sorted(obj.name for obj in bpy.context.scene.objects)
    observed = None
    try:
        film_studio_causal.execute_causal_scene(str(root), spec_uri, "INVALID_INSPECTION_TOKEN")
    except film_studio_causal.CausalContractError as error:
        observed = error.reason
    cases.append({"caseId": "INSPECTION_REQUIRED", "expected": "INSPECTION_REQUIRED", "observed": observed, "sceneUnchanged": before == sorted(obj.name for obj in bpy.context.scene.objects)})
    v2 = film_studio_causal.inspect_causal_scene(str(root), V2_URI)
    status = "PASS" if len(cases) == 16 and all(row["observed"] == row["expected"] and row["sceneUnchanged"] for row in cases) and v2["status"] == "APPROVED_READY" and v2["targetCount"] == 5 else "FAIL"
    result = {"schemaVersion": "bfs.pc8NegativeControls.v0.1", "status": status, "sceneMutations": 0, "cases": cases, "v2Compatibility": {"status": v2["status"], "sceneSpecHash": v2["sceneSpecHash"], "targetCount": v2["targetCount"]}}
    write_json(evidence / "negative-controls.json", result)
    print("PC8_NEGATIVE=" + json.dumps(result, sort_keys=True, separators=(",", ":")))
    if status != "PASS":
        raise RuntimeError("PC8 negative controls failed")


def set_frame_sequential(scene, frame):
    for current in range(scene.frame_start, frame + 1):
        scene.frame_set(current)
        bpy.context.view_layer.update()


def render(scene, camera, frame, path, motion_blur, shutter, position):
    set_frame_sequential(scene, frame)
    scene.camera = camera
    scene.render.use_motion_blur = motion_blur
    scene.render.motion_blur_shutter = shutter
    scene.render.motion_blur_position = position
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return {"frame": frame, "uri": path.relative_to(path.parents[1]).as_posix(), "sha256": sha256_file(path), "bytes": path.stat().st_size}


def run_build(root, spec_uri, evidence, work):
    state = bpy.context.scene.film_studio
    state.causal_repository_root = str(root)
    state.causal_scene_spec_uri = spec_uri
    if bpy.ops.film_studio.inspect_causal_scene() != {'FINISHED'} or bpy.ops.film_studio.execute_causal_scene() != {'FINISHED'}:
        raise RuntimeError("PC8 product operators failed")
    scene = bpy.context.scene
    result = json.loads(scene["film_studio_causal_result"])
    document = json.loads((root / spec_uri).read_text(encoding="utf-8"))
    actor = bpy.data.objects[result["semanticRoster"]["dynamicActor"][0]]
    targets = [bpy.data.objects[name] for name in result["semanticRoster"]["targets"]]
    actor_pose_frames = authored_frames(actor, {"location", "rotation_euler"})
    target_frames = {target.name: authored_frames(target) for target in targets}
    release = document["timeline"]["releaseFrame"]
    motion_blur = result["cinematography"]["motionBlur"]
    shutter = motion_blur["computedShutterFrames"]
    position = motion_blur["position"]
    impact = result["physics"]["motionSelection"]["impactFrame"]
    review_root = evidence / "review"
    review_root.mkdir()
    sharp_path = review_root / f"impact-sharp-control-frame-{impact:04d}.png"
    sharp = render(scene, bpy.data.objects["CAUSAL_CAM_IMPACT"], impact, sharp_path, False, shutter, position)
    sharp["shotId"] = "IMPACT_SHARP_CONTROL"
    review = []
    for shot_id in ("SETUP", "IMPACT", "AFTERMATH"):
        framing = result["framing"][shot_id]
        path = review_root / f"{shot_id.lower()}-measured-frame-{framing['frame']:04d}.png"
        item = render(scene, bpy.data.objects[f"CAUSAL_CAM_{shot_id}"], framing["frame"], path, True, shutter, position)
        item.update({"shotId": shot_id, "framing": framing})
        review.append(item)
    clip_count = document["acceptance"]["impactClipFrameCount"]
    clip_start = impact - 6
    clip_end = clip_start + clip_count - 1
    clip_root = evidence / "clip"
    clip_root.mkdir()
    clip = []
    for frame in range(clip_start, clip_end + 1):
        path = clip_root / f"frame-{frame:04d}.png"
        item = render(scene, bpy.data.objects["CAUSAL_CAM_IMPACT"], frame, path, True, shutter, position)
        item["uri"] = path.relative_to(evidence).as_posix()
        clip.append(item)
    blend = work / "PC8_MEASURED_SHUTTER.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend), check_existing=False)
    output = {
        "schemaVersion": "bfs.pc8MeasuredShutterBuild.v0.1", "status": "PASS", "physics": result["physics"],
        "initialConditions": result["initialConditions"], "cinematography": result["cinematography"], "framing": result["framing"],
        "provenance": result["provenance"], "semanticRoster": result["semanticRoster"],
        "animation": {"actorPoseFrames": actor_pose_frames, "actorPoseFramesAfterRelease": [frame for frame in actor_pose_frames if frame >= release], "targetFrames": target_frames},
        "sharpImpactControl": sharp, "review": review, "clip": {"startFrame": clip_start, "endFrame": clip_end, "frameCount": len(clip), "frames": clip},
        "blend": {"path": str(blend), "sha256": sha256_file(blend), "bytes": blend.stat().st_size},
        "renderCalls": 4 + len(clip), "networkCalls": 0,
    }
    write_json(evidence / "build.json", output)
    print("PC8_BUILD=" + json.dumps(output, sort_keys=True, separators=(",", ":")))


def run_reopen(root, spec_uri, evidence):
    scene = bpy.context.scene
    saved = json.loads(scene["film_studio_causal_result"])
    document = json.loads((root / spec_uri).read_text(encoding="utf-8"))
    actor = bpy.data.objects[saved["semanticRoster"]["dynamicActor"][0]]
    targets = [bpy.data.objects[name] for name in saved["semanticRoster"]["targets"]]
    physics = film_studio_causal._simulate(scene, actor, targets, document)
    measured = film_studio_causal._configure_measured_shutter(scene, bpy.data.objects["CAUSAL_CAM_IMPACT"], [actor, *targets], physics["motionSelection"]["impactFrame"], document)
    expected_physics = saved["physics"]
    expected_blur = saved["cinematography"]["motionBlur"]
    tilt_delta = {name: abs(physics["finalTiltDegrees"][name] - expected_physics["finalTiltDegrees"][name]) for name in physics["finalTiltDegrees"]}
    exact = physics["targetResponseFrames"] == expected_physics["targetResponseFrames"] and physics["motionSelection"] == expected_physics["motionSelection"] and measured == expected_blur and max(tilt_delta.values()) == 0.0
    result = {"schemaVersion": "bfs.pc8MeasuredShutterReopen.v0.1", "status": "PASS" if exact else "FAIL", "physicsExact": physics == expected_physics, "motionBlurExact": measured == expected_blur, "finalTiltDeltaDegrees": tilt_delta, "networkCalls": 0}
    write_json(evidence / "reopen.json", result)
    print("PC8_REOPEN=" + json.dumps(result, sort_keys=True, separators=(",", ":")))
    if result["status"] != "PASS":
        raise RuntimeError("PC8 reopen mismatch")


parser = argparse.ArgumentParser()
parser.add_argument("--action", choices=("negative", "build", "reopen"), required=True)
parser.add_argument("--repository-root", required=True)
parser.add_argument("--scene-spec-uri", required=True)
parser.add_argument("--evidence-root", required=True)
parser.add_argument("--work-root", required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
repository_root = Path(args.repository_root).resolve()
evidence_root = Path(args.evidence_root).resolve()
work_root = Path(args.work_root).resolve()
if args.action == "negative":
    run_negative(repository_root, args.scene_spec_uri, evidence_root)
elif args.action == "build":
    run_build(repository_root, args.scene_spec_uri, evidence_root, work_root)
else:
    run_reopen(repository_root, args.scene_spec_uri, evidence_root)
