#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Product-side PC7 validation actions run by the built Film Studio Engine."""

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

import bpy
import film_studio_causal


V1_URI = "specs/fixtures/causal-studio/PC5_G1.domino-four.scene-spec.v0.1.json"


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
        after = sorted(obj.name for obj in bpy.context.scene.objects)
        cases.append({"caseId": case_id, "expected": expected, "observed": observed, "sceneUnchanged": before == after})

    reject("PATH_ESCAPE", "PATH_ESCAPE", uri="../escape.json")
    document = copy.deepcopy(original); document["unexpected"] = True
    reject("UNKNOWN_TOP_LEVEL_FIELD", "UNKNOWN_TOP_LEVEL_FIELD", document=document, recompute=False)
    document = copy.deepcopy(original); document["targetGroup"]["factory"] = "ARBITRARY_MODEL"
    reject("UNSUPPORTED_FACTORY", "UNSUPPORTED_FACTORY", document=document)
    document = copy.deepcopy(original); document["targetGroup"]["rigidBody"]["collisionShape"] = "MESH"
    reject("UNSUPPORTED_COLLISION_SHAPE", "UNSUPPORTED_COLLISION_SHAPE", document=document)
    document = copy.deepcopy(original); document["targetGroup"]["count"] = 17
    reject("TARGET_COUNT_OUT_OF_RANGE", "TARGET_COUNT_OUT_OF_RANGE", document=document)
    document = copy.deepcopy(original); document["dynamicActor"]["radius"] = float("nan")
    reject("NONFINITE_NUMBER", "NONFINITE_NUMBER", document=document, recompute=False)
    document = copy.deepcopy(original); document["forbidden"]["externalModelsOrTextures"] = False
    reject("SPEC_EXECUTABLE_AUTHORITY", "SPEC_EXECUTABLE_AUTHORITY", document=document)
    document = copy.deepcopy(original); document["acceptance"]["targetPoseKeyframes"] = 1
    reject("FINAL_POSE_AUTHORITY", "FINAL_POSE_AUTHORITY", document=document)
    document = copy.deepcopy(original); document["shots"][1]["selection"] = "hand-picked frame 38"
    reject("UNSUPPORTED_SELECTION", "SPEC_SCHEMA", document=document)
    document = copy.deepcopy(original); document["targetGroup"]["deterministicVariation"]["python"] = "import os"
    reject("VARIATION_EXECUTABLE_AUTHORITY", "SPEC_SCHEMA", document=document)
    document = copy.deepcopy(original); document["targetGroup"]["deterministicVariation"]["yawJitterDegreesMaximum"] = 11.0
    reject("VARIATION_OUT_OF_RANGE", "SPEC_SCHEMA", document=document)

    before = sorted(obj.name for obj in bpy.context.scene.objects)
    observed = None
    try:
        film_studio_causal.execute_causal_scene(str(root), spec_uri, "INVALID_INSPECTION_TOKEN")
    except film_studio_causal.CausalContractError as error:
        observed = error.reason
    cases.append({"caseId": "INSPECTION_REQUIRED", "expected": "INSPECTION_REQUIRED", "observed": observed, "sceneUnchanged": before == sorted(obj.name for obj in bpy.context.scene.objects)})
    v1 = film_studio_causal.inspect_causal_scene(str(root), V1_URI)
    status = "PASS" if len(cases) == 12 and all(row["observed"] == row["expected"] and row["sceneUnchanged"] for row in cases) and v1["status"] == "APPROVED_READY" and v1["targetCount"] == 4 else "FAIL"
    result = {"schemaVersion": "bfs.pc7NegativeControls.v0.1", "status": status, "sceneMutations": 0, "cases": cases, "v1Compatibility": {"status": v1["status"], "sceneSpecHash": v1["sceneSpecHash"], "targetCount": v1["targetCount"]}}
    write_json(evidence / "negative-controls.json", result)
    print("PC7_NEGATIVE=" + json.dumps(result, sort_keys=True, separators=(",", ":")))
    if status != "PASS":
        raise RuntimeError("PC7 negative controls failed")


def run_build(root, spec_uri, evidence, work):
    state = bpy.context.scene.film_studio
    state.causal_repository_root = str(root)
    state.causal_scene_spec_uri = spec_uri
    if bpy.ops.film_studio.inspect_causal_scene() != {'FINISHED'}:
        raise RuntimeError("Product inspect operator failed")
    inspection_state = {key: getattr(state, attr) for key, attr in {
        "status": "causal_status", "sceneId": "causal_scene_id", "sceneSpecHash": "causal_scene_spec_hash",
        "actorFactory": "causal_actor_factory", "targetFactory": "causal_target_factory", "targetCount": "causal_target_count",
        "collisionShapes": "causal_collision_shapes", "finalPoseSource": "causal_final_pose_source", "cameraFitSource": "causal_camera_fit_source",
    }.items()}
    if bpy.ops.film_studio.execute_causal_scene() != {'FINISHED'}:
        raise RuntimeError("Product execute operator failed")
    scene = bpy.context.scene
    result = json.loads(scene["film_studio_causal_result"])
    document = json.loads((root / spec_uri).read_text(encoding="utf-8"))
    actor = bpy.data.objects[result["semanticRoster"]["dynamicActor"][0]]
    targets = [bpy.data.objects[name] for name in result["semanticRoster"]["targets"]]
    release = document["timeline"]["releaseFrame"]
    actor_pose_frames = authored_frames(actor, {"location", "rotation_euler"})
    target_frames = {target.name: authored_frames(target) for target in targets}
    review_root = evidence / "review"
    review_root.mkdir()
    review = []
    for shot_id in ("SETUP", "IMPACT", "AFTERMATH"):
        framing = result["framing"][shot_id]
        scene.frame_set(framing["frame"])
        scene.camera = bpy.data.objects[f"CAUSAL_CAM_{shot_id}"]
        path = review_root / f"{shot_id.lower()}-frame-{framing['frame']:04d}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        review.append({"shotId": shot_id, "frame": framing["frame"], "uri": path.relative_to(evidence).as_posix(), "sha256": sha256_file(path), "bytes": path.stat().st_size, "framing": framing})
    impact = result["physics"]["motionSelection"]["impactFrame"]
    clip_count = document["acceptance"]["impactClipFrameCount"]
    clip_start = max(scene.frame_start, impact - 6)
    clip_end = clip_start + clip_count - 1
    if clip_end > scene.frame_end:
        clip_end = scene.frame_end
        clip_start = clip_end - clip_count + 1
    clip_root = evidence / "clip"
    clip_root.mkdir()
    clip = []
    scene.camera = bpy.data.objects["CAUSAL_CAM_IMPACT"]
    for frame in range(clip_start, clip_end + 1):
        scene.frame_set(frame)
        path = clip_root / f"frame-{frame:04d}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        clip.append({"frame": frame, "uri": path.relative_to(evidence).as_posix(), "sha256": sha256_file(path), "bytes": path.stat().st_size})
    blend = work / "PC7_FILMIC_PHYSICS.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend), check_existing=False)
    output = {
        "schemaVersion": "bfs.pc7FilmicPhysicsBuild.v0.1", "status": "PASS", "inspection": inspection_state,
        "productStatus": state.causal_status, "productSummary": state.causal_result_summary,
        "physics": result["physics"], "initialConditions": result["initialConditions"], "framing": result["framing"],
        "provenance": result["provenance"], "semanticRoster": result["semanticRoster"],
        "animation": {"actorPoseFrames": actor_pose_frames, "actorPoseFramesAfterRelease": [frame for frame in actor_pose_frames if frame >= release], "targetFrames": target_frames},
        "review": review, "clip": {"startFrame": clip_start, "endFrame": clip_end, "frameCount": len(clip), "frames": clip},
        "blend": {"path": str(blend), "sha256": sha256_file(blend), "bytes": blend.stat().st_size},
        "renderCalls": len(review) + len(clip), "networkCalls": 0,
    }
    write_json(evidence / "build.json", output)
    print("PC7_BUILD=" + json.dumps(output, sort_keys=True, separators=(",", ":")))


def run_reopen(root, spec_uri, evidence):
    scene = bpy.context.scene
    saved = json.loads(scene["film_studio_causal_result"])
    document = json.loads((root / spec_uri).read_text(encoding="utf-8"))
    actor = bpy.data.objects[saved["semanticRoster"]["dynamicActor"][0]]
    targets = [bpy.data.objects[name] for name in saved["semanticRoster"]["targets"]]
    physics = film_studio_causal._simulate(scene, actor, targets, document)
    expected = saved["physics"]
    response_exact = physics["targetResponseFrames"] == expected["targetResponseFrames"]
    motion_exact = physics["motionSelection"] == expected["motionSelection"]
    tilt_delta = {name: abs(physics["finalTiltDegrees"][name] - expected["finalTiltDegrees"][name]) for name in physics["finalTiltDegrees"]}
    result = {
        "schemaVersion": "bfs.pc7FilmicPhysicsReopen.v0.1",
        "status": "PASS" if response_exact and motion_exact and max(tilt_delta.values()) <= document["acceptance"]["reopenFinalTiltToleranceDegrees"] else "FAIL",
        "responseFramesExact": response_exact, "motionSelectionExact": motion_exact, "finalTiltDeltaDegrees": tilt_delta,
        "physics": physics, "storedFinalPoseSource": saved["provenance"]["finalPoseSource"], "networkCalls": 0,
    }
    write_json(evidence / "reopen.json", result)
    print("PC7_REOPEN=" + json.dumps(result, sort_keys=True, separators=(",", ":")))
    if result["status"] != "PASS":
        raise RuntimeError("PC7 reopen mismatch")


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
