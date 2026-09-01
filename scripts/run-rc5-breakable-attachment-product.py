#!/usr/bin/env python3
"""Bounded RC5 product actions inside the accepted Film Studio binary."""

import argparse
import copy
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


RC4_RESULT_HASH = "016ccd803ef9aecc0bce6e0dd91d98472b7a6b6304e1c083e236058e39dc5925"


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


parser = argparse.ArgumentParser()
parser.add_argument("--action", choices=("build", "reopen", "regress-negative", "render"), required=True)
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

expected_module = args.module_root.resolve(strict=True) / "film_studio_physics_action.py"
if Path(action.__file__).resolve() != expected_module:
    raise RuntimeError("candidate physics-action module was not loaded from the exact product source")

repository = args.repository_root.resolve(strict=True)
evidence = args.evidence_root.resolve(strict=True)
work = args.work_root.resolve(strict=True)
blend = work / "RC5_B1_BREAKABLE_ATTACHMENT.blend"


def build():
    inspection = action.inspect_physics_action(repository, args.scene_spec_uri)
    result = action.execute_physics_action(repository, args.scene_spec_uri, inspection["inspectionToken"], bpy.context.scene)
    physics = result["physics"]
    attachment = physics["breakableAttachment"]
    contact = physics["contactFrame"]
    checks = {
        "v04Contract": inspection["contractVersion"] == "bfs.filmStudioPhysicsAction.v0.3" and result["schemaVersion"] == "bfs.physicsActionResult.v0.3",
        "activeBodies": result["mechanism"]["activeRigidBodyCount"] == 5,
        "breakableConstraint": result["mechanism"]["rigidBodyConstraintCount"] == result["mechanism"]["breakableFixedConstraintCount"] == 1,
        "constraintConfiguration": attachment["constraintType"] == "FIXED" and attachment["breakingEnabled"] is True and attachment["breakingImpulseThreshold"] == 0.02 and attachment["solverIterations"] == 80 and attachment["attachedBodyCollisionsDisabled"] is True,
        "derivedAttachmentTarget": attachment["attachmentTargetDerivation"]["policy"] == "MINIMUM_DISTANCE_TO_INITIATOR_RELEASE_RAY" and attachment["attachmentTargetDerivation"]["source"] == "METRIC_INITIAL_CONDITIONS_BEFORE_SCENE_MUTATION" and attachment["attachmentTargetDerivation"]["physicalVariationBasisSpecHash"] == "bac28a88028ffaed0b09685059e63c1f4cf23c2ad1b2a79901f54e699d4b1e34" and attachment["attachmentTarget"] == f"CAUSAL_TARGET_{attachment['attachmentTargetDerivation']['selectedMemberIndex'] + 1:03d}",
        "moldedGlassContactGeometry": result["mechanism"]["contactGeometry"]["preset"] == "MOLDED_HOUSEHOLD_GLASS_WITH_CONTACT_OVALITY" and result["mechanism"]["contactGeometry"]["radialAmplitudeMeters"] == 0.00045 and result["mechanism"]["contactGeometry"]["harmonicLobes"] == 2 and result["mechanism"]["contactGeometry"]["visibleMeshIsCollisionHullSource"] is True and result["mechanism"]["contactGeometry"]["solverSleep"] is False,
        "solverAuthority": result["authority"]["postReleaseTransformKeyframes"] == result["authority"]["authoredOutcomeFields"] == result["authority"]["authoredContactResponsePeakOrFinalFrames"] == result["authority"]["authoredBreakFrames"] == result["authority"]["authoredDetachedPoses"] == result["authority"]["authoredDetachmentVelocities"] == 0,
        "staticLights": result["authority"]["lightAnimationChannels"] == 0,
        "bottleResponse": physics["respondingTargetCount"] >= 2,
        "attachedBeforeContact": attachment["maximumPrecontactAttachmentSeparationMeters"] <= 0.005,
        "derivedDetachmentWindow": attachment["detachmentFrame"] is not None and contact <= attachment["detachmentFrame"] <= contact + 12,
        "detachedSeparation": 0.035 <= attachment["maximumAttachmentSeparationMeters"] <= 1.2,
        "capAngularResponse": attachment["maximumAngularResponseDegrees"] >= 15.0,
        "capFloorPenetration": attachment["maximumFloorPenetrationMeters"] <= 0.005,
        "continuousCapMotion": attachment["continuousMotionForThreeFramesFromDetachment"] is True,
        "settledWindow": physics["settledWindowFrameCount"] == 10 and result["cinematography"]["effect"]["frame"] == physics["settledGroupFrame"],
        "reviewRoster": result["review"]["contactClipFrameRangeInclusive"][1] - result["review"]["contactClipFrameRangeInclusive"][0] + 1 == 48 and len(result["semanticRoster"]["secondary"]) == 1,
    }
    bpy.context.preferences.filepaths.file_preview_type = "NONE"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend), check_existing=False)
    output = {
        "schemaVersion": "bfs.rc5BreakableAttachmentBuild.v0.1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "inspection": inspection,
        "result": result,
        "checks": checks,
        "checkCount": len(checks),
        "passCount": sum(checks.values()),
        "blend": {"path": str(blend), "sha256": sha(blend), "bytes": blend.stat().st_size},
        "counts": {"rc5SceneBuilds": 1, "blendSaves": 1, "renders": 0, "networkCalls": 0},
    }
    write(evidence / "B1-build.json", output)
    print("RC5_BUILD=" + json.dumps(output, sort_keys=True, separators=(",", ":")))
    if output["status"] != "PASS":
        raise RuntimeError("RC5 machine acceptance failed")


def tilt(obj):
    up = obj.matrix_world.to_3x3() @ Vector((0, 0, 1))
    return math.degrees(math.acos(max(-1, min(1, up.normalized().dot(Vector((0, 0, 1)))))))


def reopen():
    expected = json.loads((evidence / "B1-build.json").read_text(encoding="utf-8"))["result"]
    scene = bpy.context.scene
    stored = json.loads(scene["film_studio_physics_action_result"])
    actor = scene.objects[expected["semanticRoster"]["actor"]]
    targets = [scene.objects[name] for name in expected["semanticRoster"]["targets"]]
    cap = scene.objects[expected["semanticRoster"]["secondary"][0]]
    location_deltas, tilt_deltas, cap_location_deltas, cap_angular_deltas = [], [], [], []
    scene.frame_set(scene.frame_start)
    bpy.context.view_layer.update()
    initial_cap_rotation = cap.matrix_world.to_quaternion().copy()
    for sample in expected["physics"]["samples"]:
        scene.frame_set(sample["frame"])
        bpy.context.view_layer.update()
        location_deltas.append((actor.matrix_world.translation - Vector(sample["actorLocation"])).length)
        for target in targets:
            tilt_deltas.append(abs(tilt(target) - sample["targetTiltDegrees"][target.name]))
        cap_location_deltas.append((cap.matrix_world.translation - Vector(sample["capLocation"])).length)
        angular = math.degrees(initial_cap_rotation.rotation_difference(cap.matrix_world.to_quaternion()).angle)
        cap_angular_deltas.append(abs(angular - sample["capAngularResponseDegrees"]))
    checks = {
        "storedResultExact": stored == expected,
        "storedResultHashExact": scene["film_studio_physics_action_result_hash"] == expected["resultHash"],
        "actorLocationDelta": max(location_deltas) <= 0.0000001,
        "targetTiltDelta": max(tilt_deltas) <= 0.001,
        "capLocationDelta": max(cap_location_deltas) <= 0.0000001,
        "capAngularDelta": max(cap_angular_deltas) <= 0.001,
        "solverAuthority": expected["authority"]["postReleaseTransformKeyframes"] == expected["authority"]["authoredBreakFrames"] == expected["authority"]["authoredDetachedPoses"] == expected["authority"]["authoredDetachmentVelocities"] == 0,
    }
    output = {
        "schemaVersion": "bfs.rc5BreakableAttachmentReopen.v0.1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "sampleCount": len(expected["physics"]["samples"]),
        "maximumActorLocationDeltaMeters": max(location_deltas),
        "maximumTargetTiltDeltaDegrees": max(tilt_deltas),
        "maximumCapLocationDeltaMeters": max(cap_location_deltas),
        "maximumCapAngularDeltaDegrees": max(cap_angular_deltas),
        "counts": {"sceneMutations": 0, "blendSaves": 0, "renders": 0, "networkCalls": 0},
    }
    write(evidence / "B1-reopen.json", output)
    if output["status"] != "PASS":
        raise RuntimeError("RC5 save/reopen mismatch")


def regress_negative():
    regressions = []
    for case, uri, expected_hash in (
        ("RC4", "specs/fixtures/physics-action/RC4_R1.unstaged-basketball-three-glass-bottles.physics-action-spec.v0.1.json", RC4_RESULT_HASH),
        ("D1", "specs/fixtures/physics-action/RC3_D1.signal-gate.physics-action-spec.v0.3.json", None),
        ("H1", "specs/fixtures/physics-action/RC3_H1.ball-three-bottles.physics-action-spec.v0.2.json", None),
    ):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        inspection = action.inspect_physics_action(repository, uri)
        result = action.execute_physics_action(repository, uri, inspection["inspectionToken"], bpy.context.scene)
        checks = {
            "derivedContact": result["physics"]["contactFrame"] is not None,
            "solverAuthority": result["authority"]["postReleaseTransformKeyframes"] == result["authority"]["authoredOutcomeFields"] == result["authority"]["lightAnimationChannels"] == 0,
            "exactRc4HashWhenRequired": expected_hash is None or result["resultHash"] == expected_hash,
        }
        regressions.append({"case": case, "uri": uri, "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "resultHash": result["resultHash"]})

    source = json.loads((repository / args.scene_spec_uri).read_text(encoding="utf-8"))
    negatives = []

    def reject(name, mutate, reason):
        candidate = copy.deepcopy(source)
        mutate(candidate)
        candidate["physicsActionSpecHash"] = action._self_hash(candidate, "physicsActionSpecHash")
        observed = None
        try:
            action._validate(candidate)
        except action.PhysicsActionError as error:
            observed = error.reason
        negatives.append({"name": name, "expected": reason, "observed": observed, "passed": observed == reason})

    reject("unknown-top-level", lambda value: value.update({"surprise": 1}), "UNKNOWN_TOP_LEVEL_FIELD")
    reject("authored-final-position", lambda value: value["nodes"][0]["initialCondition"].update({"finalPosition": [0, 0, 0]}), "OUTCOME_AUTHORITY")
    reject("authored-break-frame", lambda value: value["relations"][4].update({"breakFrame": 20}), "OUTCOME_AUTHORITY")
    reject("authored-detached-pose", lambda value: value["nodes"][2].update({"detachedPose": [0, 0, 0]}), "OUTCOME_AUTHORITY")
    reject("authored-detachment-velocity", lambda value: value["nodes"][2].update({"detachmentVelocity": [1, 0, 0]}), "OUTCOME_AUTHORITY")
    reject("unsupported-factory", lambda value: value["nodes"][2].update({"factory": "ARBITRARY_CAP"}), "UNSUPPORTED_FACTORY")
    reject("unsupported-relation", lambda value: value["relations"][4].update({"type": "EXPLODES_AT"}), "UNSUPPORTED_RELATION")
    reject("collisions-enabled", lambda value: value["relations"][4].update({"disableCollisions": False}), "SPEC_SCHEMA")
    reject("zero-break-threshold", lambda value: value["relations"][4].update({"breakingImpulseThreshold": 0}), "SPEC_SCHEMA")
    reject("unsupported-target-policy", lambda value: value["nodes"][2]["parameters"].update({"targetMemberPolicy": "OBSERVED_MEMBER_INDEX"}), "SPEC_SCHEMA")
    reject("unsupported-cap-material", lambda value: value["nodes"][2]["parameters"].update({"materialPreset": "MAGIC_CAP"}), "SPEC_SCHEMA")
    reject("v01-schema-with-breakable-cap", lambda value: (value.pop("physicalVariationBasisSpecHash"), value.update({"$schema": "bfs.physicsActionSpec.v0.1", "schemaVersion": "bfs.physicsActionSpec.v0.1"})), "UNSUPPORTED_FACTORY")

    checks = {
        "threeRegressionExecutions": len(regressions) == 3,
        "regressionsPass": all(row["status"] == "PASS" for row in regressions),
        "twelveNegativeControls": len(negatives) == 12,
        "allNegativesReject": all(row["passed"] for row in negatives),
    }
    output = {
        "schemaVersion": "bfs.rc5RegressionNegative.v0.1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "regressions": regressions,
        "negativeControls": negatives,
        "counts": {"regressionSceneExecutions": 3, "negativeSceneMutations": 0, "renders": 0, "networkCalls": 0},
    }
    write(evidence / "regression-negative.json", output)
    if output["status"] != "PASS":
        raise RuntimeError("RC5 regression or negative control failed")


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
    removed_markers = [{"name": marker.name, "frame": marker.frame, "camera": None if marker.camera is None else marker.camera.name} for marker in scene.timeline_markers]
    for marker in list(scene.timeline_markers):
        scene.timeline_markers.remove(marker)
    start, end = result["review"]["contactClipFrameRangeInclusive"]
    camera = scene.objects[result["cinematography"]["contact"]["camera"]]
    frames = [render_one(scene, camera, frame, clip_root / f"frame-{frame:04d}.png") for frame in range(start, end + 1)]
    output = {
        "schemaVersion": "bfs.rc5VisualRender.v0.1",
        "status": "PASS_RENDER_COMPLETE",
        "resultHash": result["resultHash"],
        "resolution": [width, height],
        "stills": stills,
        "clip": {"startFrame": start, "endFrame": end, "frameCount": len(frames), "camera": camera.name, "cameraPolicy": "FIXED_CONTACT_CAMERA_WITH_TIMELINE_MARKERS_REMOVED_AFTER_STILLS", "removedTimelineMarkers": removed_markers, "frames": frames},
        "counts": {"sceneMutations": 0, "reviewConfigurationMutations": len(removed_markers), "blendSaves": 0, "reviewStills": len(stills), "clipFrames": len(frames), "networkCalls": 0},
    }
    write(evidence / "render.json", output)


{"build": build, "reopen": reopen, "regress-negative": regress_negative, "render": render}[args.action]()
