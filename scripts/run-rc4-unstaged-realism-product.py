#!/usr/bin/env python3
"""Bounded RC4 product actions inside the accepted Film Studio binary."""

import argparse
import copy
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


parser = argparse.ArgumentParser()
parser.add_argument("--action", choices=("build", "reopen", "regress", "negative", "render"), required=True)
parser.add_argument("--repository-root", type=Path, required=True)
parser.add_argument("--scene-spec-uri", required=True)
parser.add_argument("--evidence-root", type=Path, required=True)
parser.add_argument("--work-root", type=Path, required=True)
parser.add_argument("--module-root", type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])

sys.path.insert(0, str(args.module_root.resolve(strict=True)))
sys.modules.pop("film_studio_physics_action", None)
sys.modules.pop("film_studio_physical_look", None)
import film_studio_physics_action as action

if Path(action.__file__).resolve() != args.module_root.resolve(strict=True) / "film_studio_physics_action.py":
    raise RuntimeError("candidate physics-action module was not loaded from the frozen module root")

repository = args.repository_root.resolve(strict=True)
evidence = args.evidence_root.resolve(strict=True)
work = args.work_root.resolve(strict=True)
blend = work / "RC4_R1_UNSTAGED_PHYSICAL_REALISM.blend"


def build():
    inspection = action.inspect_physics_action(repository, args.scene_spec_uri)
    result = action.execute_physics_action(repository, args.scene_spec_uri, inspection["inspectionToken"], bpy.context.scene)
    bpy.context.preferences.filepaths.file_preview_type = "NONE"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend), check_existing=False)
    output = {
        "schemaVersion": "bfs.rc4UnstagedRealismBuild.v0.1",
        "status": "PASS",
        "inspection": inspection,
        "result": result,
        "blend": {"path": str(blend), "sha256": sha(blend), "bytes": blend.stat().st_size},
        "counts": {"sceneMutations": 1, "blendSaves": 1, "renders": 0, "networkCalls": 0},
    }
    write(evidence / "R1-build.json", output)
    print("RC4_BUILD=" + json.dumps(output, sort_keys=True, separators=(",", ":")))


def tilt(obj):
    up = obj.matrix_world.to_3x3() @ Vector((0, 0, 1))
    return math.degrees(math.acos(max(-1, min(1, up.normalized().dot(Vector((0, 0, 1)))))))


def reopen():
    expected = json.loads((evidence / "R1-build.json").read_text(encoding="utf-8"))["result"]
    scene = bpy.context.scene
    stored = json.loads(scene["film_studio_physics_action_result"])
    actor = scene.objects[expected["semanticRoster"]["actor"]]
    targets = [scene.objects[name] for name in expected["semanticRoster"]["targets"]]
    location_deltas, tilt_deltas = [], []
    for sample in expected["physics"]["samples"]:
        scene.frame_set(sample["frame"])
        bpy.context.view_layer.update()
        location_deltas.append((actor.matrix_world.translation - Vector(sample["actorLocation"])).length)
        for target in targets:
            tilt_deltas.append(abs(tilt(target) - sample["targetTiltDegrees"][target.name]))
    checks = {
        "storedResultExact": stored == expected,
        "storedResultHashExact": scene["film_studio_physics_action_result_hash"] == expected["resultHash"],
        "actorLocationDelta": max(location_deltas) <= 1e-6,
        "targetTiltDelta": max(tilt_deltas) <= 0.001,
        "solverAuthority": expected["authority"]["postReleaseTransformKeyframes"] == 0 and expected["authority"]["authoredOutcomeFields"] == 0 and expected["authority"]["authoredContactResponsePeakOrFinalFrames"] == 0,
        "staticLights": expected["authority"]["lightAnimationChannels"] == 0,
    }
    output = {
        "schemaVersion": "bfs.rc4UnstagedRealismReopen.v0.1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "sampleCount": len(expected["physics"]["samples"]),
        "maximumActorLocationDeltaMeters": max(location_deltas),
        "maximumTargetTiltDeltaDegrees": max(tilt_deltas),
        "counts": {"sceneMutations": 0, "blendSaves": 0, "renders": 0, "networkCalls": 0},
    }
    write(evidence / "R1-reopen.json", output)
    if output["status"] != "PASS":
        raise RuntimeError("RC4 save/reopen mismatch")


def regress():
    cases = []
    for case, uri, topology, active, constraints in (
        ("D1", "specs/fixtures/physics-action/RC3_D1.signal-gate.physics-action-spec.v0.3.json", "HINGE_LIGHT", 2, 1),
        ("H1", "specs/fixtures/physics-action/RC3_H1.ball-three-bottles.physics-action-spec.v0.2.json", "GROUP_RESPONSE", 4, 0),
    ):
        inspection = action.inspect_physics_action(repository, uri)
        result = action.execute_physics_action(repository, uri, inspection["inspectionToken"], bpy.context.scene)
        checks = {
            "topology": result["topology"] == topology,
            "activeBodies": result["mechanism"]["activeRigidBodyCount"] == active,
            "constraints": result["mechanism"]["rigidBodyConstraintCount"] == constraints,
            "derivedContact": result["physics"]["contactFrame"] is not None,
            "derivedResponse": result["physics"]["firstResponseDelayFrames"] <= 2,
            "solverAuthority": result["authority"]["postReleaseTransformKeyframes"] == result["authority"]["authoredOutcomeFields"] == result["authority"]["lightAnimationChannels"] == 0,
        }
        cases.append({"case": case, "uri": uri, "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "resultHash": result["resultHash"]})
    output = {"schemaVersion": "bfs.rc4Regression.v0.1", "status": "PASS" if all(row["status"] == "PASS" for row in cases) else "FAIL", "cases": cases, "counts": {"sceneMutations": 2, "blendSaves": 0, "renders": 0, "networkCalls": 0}}
    write(evidence / "regressions.json", output)
    if output["status"] != "PASS":
        raise RuntimeError("RC4 regression")


def negative():
    source = json.loads((repository / args.scene_spec_uri).read_text(encoding="utf-8"))
    cases = []

    def reject(name, mutate, reason, value=None):
        candidate = copy.deepcopy(source if value is None else value)
        mutate(candidate)
        candidate["physicsActionSpecHash"] = action._self_hash(candidate, "physicsActionSpecHash")
        observed = None
        try:
            action._validate(candidate)
        except action.PhysicsActionError as error:
            observed = error.reason
        cases.append({"name": name, "expected": reason, "observed": observed, "passed": observed == reason})

    reject("unknown-top", lambda value: value.update({"surprise": 1}), "UNKNOWN_TOP_LEVEL_FIELD")
    reject("authored-final-position", lambda value: value["nodes"][0]["initialCondition"].update({"finalPosition": [0, 0, 0]}), "OUTCOME_AUTHORITY")
    reject("authored-effect-frame", lambda value: value["beats"][2].update({"targetFrame": 99}), "OUTCOME_AUTHORITY")
    reject("invalid-review-resolution", lambda value: value["cinematography"].update({"reviewResolution": [1920, 1080]}), "SPEC_SCHEMA")
    reject("unbounded-variation", lambda value: value["nodes"][1]["parameters"].update({"positionJitterMetersMaximum": 1}), "SPEC_SCHEMA")
    d1 = json.loads((repository / "specs/fixtures/physics-action/RC3_D1.signal-gate.physics-action-spec.v0.3.json").read_text(encoding="utf-8"))
    reject("settled-beat-without-response-group", lambda value: value["beats"][2].update({"deriveFrom": "SETTLED_GROUP_RESPONSE", "node": "gate", "afterBeat": "contact"}), "BEAT_DEPENDENCY", d1)
    output = {"schemaVersion": "bfs.rc4NegativeControls.v0.1", "status": "PASS" if all(row["passed"] for row in cases) else "FAIL", "caseCount": len(cases), "passCount": sum(row["passed"] for row in cases), "cases": cases, "counts": {"sceneMutations": 0, "blendSaves": 0, "renders": 0, "networkCalls": 0}}
    write(evidence / "negative-controls.json", output)
    if output["status"] != "PASS":
        raise RuntimeError("RC4 negative controls")


def render_one(scene, camera, frame, path):
    scene.frame_set(frame)
    scene.camera = camera
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return {"frame": frame, "camera": camera.name, "path": str(path), "sha256": sha(path), "bytes": path.stat().st_size}


def render():
    scene = bpy.context.scene
    result = json.loads(scene["film_studio_physics_action_result"])
    width, height = result["review"]["resolution"]
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = width, height, 100
    scene.render.image_settings.file_format, scene.render.image_settings.color_mode = "PNG", "RGBA"
    scene.render.image_settings.color_depth = "8"
    bpy.context.preferences.filepaths.file_preview_type = "NONE"
    still_root, clip_root = evidence / "stills", evidence / "clip"
    still_root.mkdir(exist_ok=False)
    clip_root.mkdir(exist_ok=False)
    stills = []
    for role in ("cause", "contact", "effect"):
        shot = result["cinematography"][role]
        row = render_one(scene, scene.objects[shot["camera"]], shot["frame"], still_root / f"{role}-frame-{shot['frame']:04d}.png")
        row["role"] = role
        stills.append(row)
    start, end = result["review"]["contactClipFrameRangeInclusive"]
    camera = scene.objects[result["cinematography"]["contact"]["camera"]]
    frames = [render_one(scene, camera, frame, clip_root / f"frame-{frame:04d}.png") for frame in range(start, end + 1)]
    output = {"schemaVersion": "bfs.rc4VisualRender.v0.1", "status": "PASS_RENDER_COMPLETE", "resultHash": result["resultHash"], "resolution": [width, height], "stills": stills, "clip": {"startFrame": start, "endFrame": end, "frameCount": len(frames), "camera": camera.name, "frames": frames}, "counts": {"sceneMutations": 0, "blendSaves": 0, "reviewStills": len(stills), "clipFrames": len(frames), "networkCalls": 0}}
    write(evidence / "render.json", output)


{"build": build, "reopen": reopen, "regress": regress, "negative": negative, "render": render}[args.action]()
