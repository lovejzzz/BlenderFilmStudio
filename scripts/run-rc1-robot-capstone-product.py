#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Product-side RC1 physical-performance build and reopen actions."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

import film_studio_physical_performance as performance


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


def build(repository, spec_uri, evidence, work):
    state = bpy.context.scene.film_studio
    state.causal_repository_root = str(repository)
    state.causal_scene_spec_uri = spec_uri
    if bpy.ops.film_studio.inspect_causal_scene() != {"FINISHED"}:
        raise RuntimeError("RC1 product inspection failed")
    inspection = {
        "status": state.causal_status,
        "sceneId": state.causal_scene_id,
        "specHash": state.causal_scene_spec_hash,
        "targetCount": state.causal_target_count,
    }
    if bpy.ops.film_studio.execute_causal_scene() != {"FINISHED"}:
        raise RuntimeError("RC1 product execution failed")
    scene = bpy.context.scene
    result = json.loads(scene["film_studio_physical_performance_result"])
    if result["status"] != "PASS_EXECUTED":
        raise RuntimeError("RC1 product result did not pass")

    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    scene.render.resolution_percentage = 100
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    review = evidence / "review"
    review.mkdir()
    stills = []
    for role in ("wide", "medium", "close"):
        shot = result["cinematography"][role]
        path = review / f"{role}-frame-{shot['frame']:04d}.png"
        item = render(scene, scene.objects[shot["camera"]], shot["frame"], path)
        item["role"] = role
        item["uri"] = path.relative_to(evidence).as_posix()
        stills.append(item)

    original_range = (scene.frame_start, scene.frame_end)
    clip_start, clip_end = result["review"]["contactClipFrameRangeInclusive"]
    clip_root = evidence / "clip"
    clip_root.mkdir()
    clip = []
    for frame in range(clip_start, clip_end + 1):
        path = clip_root / f"frame-{frame:04d}.png"
        item = render(scene, None, frame, path)
        item["uri"] = path.relative_to(evidence).as_posix()
        item["camera"] = scene.camera.name
        clip.append(item)
    scene.frame_start, scene.frame_end = original_range
    scene.frame_set(scene.frame_start)
    blend = work / "RC1_PHYSICAL_PERFORMANCE.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend), check_existing=False)
    output = {
        "schemaVersion": "bfs.rc1RobotCapstoneBuild.v0.1",
        "status": "PASS",
        "inspection": inspection,
        "result": result,
        "stills": stills,
        "clip": {"startFrame": clip_start, "endFrame": clip_end, "frameCount": len(clip), "frames": clip},
        "blend": {"path": str(blend), "sha256": sha256_file(blend), "bytes": blend.stat().st_size},
        "counts": {"sceneMutatingExecutions": 1, "blendSaves": 1, "reviewStillRenders": len(stills), "contactClipFrameRenders": len(clip)},
        "networkCalls": 0,
    }
    write(evidence / "build.json", output)
    print("RC1_BUILD=" + json.dumps(output, sort_keys=True, separators=(",", ":")))


def occupancy(scene, camera, objects):
    x0, x1, y0, y1 = performance._projected_bounds(scene, camera, objects)
    return max(x1 - x0, y1 - y0)


def reopen(repository, spec_uri, evidence):
    scene = bpy.context.scene
    build_result = json.loads((evidence / "build.json").read_text(encoding="utf-8"))
    expected = build_result["result"]
    stored = json.loads(scene["film_studio_physical_performance_result"])
    document = json.loads((repository / spec_uri).read_text(encoding="utf-8"))
    bindings = document["semanticBindings"]
    plunger = scene.objects[expected["mechanism"]["objects"]["plunger"]]
    rest = Vector(plunger["film_studio_rest_location"])
    normal = Vector(plunger["film_studio_travel_axis"])
    samples = {row["frame"]: row for row in expected["physics"]["samples"]}
    deltas = []
    for frame in range(scene.frame_start, scene.frame_end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        observed = -(plunger.matrix_world.translation - rest).dot(normal)
        deltas.append(abs(observed - samples[frame]["axisCoordinateMeters"]))

    medium = expected["cinematography"]["medium"]
    scene.frame_set(medium["frame"])
    hidden_hand = scene.objects[bindings["visibleHandBody"]]
    hand_radius = hidden_hand.dimensions.length * 1.5
    hand_visuals = [obj for obj in scene.objects if obj.type == "MESH" and not obj.hide_render and obj.get("bfs_pc4_system") == "hand" and (obj.matrix_world.translation - hidden_hand.matrix_world.translation).length <= hand_radius]
    medium_objects = hand_visuals + [scene.objects[expected["mechanism"]["objects"][key]] for key in ("housing", "plunger")]
    observed_medium = occupancy(scene, scene.objects[medium["camera"]], medium_objects)

    close = expected["cinematography"]["close"]
    scene.frame_set(close["frame"])
    close_objects = [scene.objects[bindings["faceplate"]]] + [scene.objects[row["object"]] for row in bindings["facialLandmarks"]]
    observed_close = occupancy(scene, scene.objects[close["camera"]], close_objects)
    camera_deltas = {}
    for role in ("medium", "close"):
        shot = expected["cinematography"][role]
        camera_deltas[role] = (scene.objects[shot["camera"]].location - Vector(shot["cameraLocation"])).length

    wide = expected["cinematography"]["wide"]
    scene.frame_set(wide["frame"])
    wide_camera = scene.objects[wide["camera"]]
    observed_layers = [row["object"] for row in bindings["environmentLayers"] if performance._overlaps_frame(scene, wide_camera, scene.objects[row["object"]])]
    checks = {
        "storedResultExact": stored == expected,
        "storedResultHashExact": scene["film_studio_physical_performance_result_hash"] == expected["resultHash"],
        "storedSpecHashExact": scene["film_studio_physical_performance_spec_hash"] == expected["performanceSpecHash"],
        "generatedObjectCountExact": sum(obj.get("film_studio_physical_performance") == performance.GENERATED_TAG for obj in scene.objects) == 9,
        "postContactMechanismPoseKeyframesZero": performance._mechanism_pose_keyframes(plunger) == 0,
        "physicsAxisCoordinatesExact": max(deltas) <= 1e-7,
        "cameraLocationsExact": max(camera_deltas.values()) <= 1e-7,
        "mediumOccupancyExact": abs(observed_medium - medium["occupancy"]) <= 1e-7,
        "closeOccupancyExact": abs(observed_close - close["occupancy"]) <= 1e-7,
        "wideEnvironmentLayersExact": observed_layers == wide["visibleEnvironmentLayers"],
    }
    output = {
        "schemaVersion": "bfs.rc1RobotCapstoneReopen.v0.1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "maximumPhysicsAxisCoordinateDeltaMeters": max(deltas),
        "cameraLocationDeltasMeters": camera_deltas,
        "observedMediumOccupancy": observed_medium,
        "observedCloseOccupancy": observed_close,
        "observedWideEnvironmentLayers": observed_layers,
        "networkCalls": 0,
    }
    write(evidence / "reopen.json", output)
    print("RC1_REOPEN=" + json.dumps(output, sort_keys=True, separators=(",", ":")))
    if output["status"] != "PASS":
        raise RuntimeError("RC1 reopen mismatch")


parser = argparse.ArgumentParser()
parser.add_argument("--action", choices=("build", "reopen"), required=True)
parser.add_argument("--repository-root", type=Path, required=True)
parser.add_argument("--scene-spec-uri", required=True)
parser.add_argument("--evidence-root", type=Path, required=True)
parser.add_argument("--work-root", type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
repository = args.repository_root.resolve(strict=True)
evidence_root = args.evidence_root.resolve(strict=True)
work_root = args.work_root.resolve(strict=True)
build(repository, args.scene_spec_uri, evidence_root, work_root) if args.action == "build" else reopen(repository, args.scene_spec_uri, evidence_root)
