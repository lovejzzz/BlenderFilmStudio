#!/usr/bin/env python3
"""Product-side RC3 zero-render build, reopen and negative actions."""

import argparse
import copy
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


parser = argparse.ArgumentParser()
parser.add_argument("--action", choices=("build", "reopen", "negative"), required=True)
parser.add_argument("--case", choices=("D1", "H1"))
parser.add_argument("--repository-root", type=Path, required=True)
parser.add_argument("--scene-spec-uri")
parser.add_argument("--evidence-root", type=Path, required=True)
parser.add_argument("--work-root", type=Path, required=True)
parser.add_argument("--module-root", type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])

sys.path.insert(0, str(args.module_root.resolve(strict=True)))
import film_studio_physics_action as action

repository = args.repository_root.resolve(strict=True)
evidence = args.evidence_root.resolve(strict=True)
work = args.work_root.resolve(strict=True)


def build():
    inspection = action.inspect_physics_action(repository, args.scene_spec_uri)
    result = action.execute_physics_action(repository, args.scene_spec_uri, inspection["inspectionToken"], bpy.context.scene)
    scene = bpy.context.scene
    scene.frame_set(scene.frame_start)
    bpy.context.preferences.filepaths.file_preview_type = "NONE"
    blend = work / f"RC3_{args.case}_PHYSICS_ACTION.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend), check_existing=False)
    output = {
        "schemaVersion": "bfs.rc3PhysicsActionDevelopmentBuild.v0.1",
        "status": "PASS",
        "case": args.case,
        "inspection": inspection,
        "result": result,
        "blend": {"path": str(blend), "sha256": sha256_file(blend), "bytes": blend.stat().st_size},
        "counts": {"sceneMutatingExecutions": 1, "blendSaves": 1, "renders": 0, "networkCalls": 0},
    }
    write(evidence / f"{args.case}-build.json", output)
    print("RC3_BUILD=" + json.dumps(output, sort_keys=True, separators=(",", ":")))


def reopen():
    expected = json.loads((evidence / f"{args.case}-build.json").read_text(encoding="utf-8"))["result"]
    scene = bpy.context.scene
    stored = json.loads(scene["film_studio_physics_action_result"])
    actor = scene.objects[expected["semanticRoster"]["actor"]]
    targets = [scene.objects[name] for name in expected["semanticRoster"]["targets"]]
    location_deltas, target_tilt_deltas = [], []
    samples = expected["physics"]["samples"]
    for sample in samples:
        scene.frame_set(sample["frame"])
        bpy.context.view_layer.update()
        location_deltas.append((actor.matrix_world.translation - Vector(sample["actorLocation"])).length)
        if "targetTiltDegrees" in sample:
            for target in targets:
                up = target.matrix_world.to_3x3() @ Vector((0, 0, 1))
                observed = math.degrees(math.acos(max(-1, min(1, up.normalized().dot(Vector((0, 0, 1)))))))
                target_tilt_deltas.append(abs(observed - sample["targetTiltDegrees"][target.name]))
    checks = {
        "storedResultExact": stored == expected,
        "storedResultHashExact": scene["film_studio_physics_action_result_hash"] == expected["resultHash"],
        "actorLocationDelta": max(location_deltas) <= 1e-6,
        "targetTiltDelta": not target_tilt_deltas or max(target_tilt_deltas) <= 0.001,
        "postReleaseTransformKeysZero": expected["authority"]["postReleaseTransformKeyframes"] == 0,
        "outcomeFieldsZero": expected["authority"]["authoredOutcomeFields"] == 0,
        "lightAnimationZero": expected["authority"]["lightAnimationChannels"] == 0,
    }
    output = {
        "schemaVersion": "bfs.rc3PhysicsActionDevelopmentReopen.v0.1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "case": args.case,
        "checks": checks,
        "sampleCount": len(samples),
        "maximumActorLocationDeltaMeters": max(location_deltas),
        "maximumTargetTiltDeltaDegrees": max(target_tilt_deltas, default=0),
        "renders": 0,
        "networkCalls": 0,
    }
    write(evidence / f"{args.case}-reopen.json", output)
    print("RC3_REOPEN=" + json.dumps(output, sort_keys=True, separators=(",", ":")))
    if output["status"] != "PASS":
        raise RuntimeError("RC3 reopen mismatch")


def negative():
    source = json.loads((repository / args.scene_spec_uri).read_text(encoding="utf-8"))
    cases = []

    def reject(name, mutate, reason):
        value = copy.deepcopy(source)
        mutate(value)
        value["physicsActionSpecHash"] = action._self_hash(value, "physicsActionSpecHash")
        observed = None
        try:
            action._validate(value)
        except action.PhysicsActionError as error:
            observed = error.reason
        cases.append({"name": name, "expected": reason, "observed": observed, "passed": observed == reason})

    reject("unknown-top", lambda v: v.update({"surprise": 1}), "UNKNOWN_TOP_LEVEL_FIELD")
    reject("unknown-factory", lambda v: v["nodes"][0].update({"factory": "ANYTHING"}), "UNSUPPORTED_FACTORY")
    reject("duplicate-node", lambda v: v["nodes"][1].update({"id": v["nodes"][0]["id"]}), "DUPLICATE_NODE_ID")
    reject("missing-node-ref", lambda v: v["relations"][0].update({"target": "missing"}), "MISSING_NODE_REFERENCE")
    reject("outcome-final-position", lambda v: v["nodes"][0]["initialCondition"].update({"finalPosition": [0, 0, 0]}), "OUTCOME_AUTHORITY")
    reject("outcome-target-frame", lambda v: v["beats"][0].update({"targetFrame": 9}), "OUTCOME_AUTHORITY")
    reject("manual-contact-frame", lambda v: v["beats"][1].update({"contactFrame": 9}), "OUTCOME_AUTHORITY")
    reject("active-without-mass", lambda v: v["nodes"][0]["rigidBody"].pop("massKg"), "SPEC_SCHEMA")
    reject("passive-release-velocity", lambda v: v["nodes"][1]["initialCondition"].update({"preReleaseVelocityMetersPerSecond": [1, 0, 0]}), "SPEC_SCHEMA")
    reject("missing-constraint-node", lambda v: next(r for r in v["relations"] if r["type"] == "HINGED_TO_WORLD").update({"source": "missing"}), "MISSING_NODE_REFERENCE")
    reject("reversed-hinge", lambda v: next(r for r in v["relations"] if r["type"] == "HINGED_TO_WORLD").update({"limitsDegrees": [90, 10]}), "SPEC_SCHEMA")
    reject("light-animation", lambda v: v["forbidden"].update({"animatedLightPowerOrColor": False}), "AUTHORITY_EXPANSION")
    reject("postprocess-blur", lambda v: v["forbidden"].update({"postprocessMotionBlur": False}), "AUTHORITY_EXPANSION")
    reject("project-branch-authority", lambda v: v["forbidden"].update({"projectOrFixtureBranchInProductCode": False}), "AUTHORITY_EXPANSION")
    reject("unknown-nested", lambda v: v["nodes"][0]["parameters"].update({"extra": 1}), "SPEC_SCHEMA")
    observed = None
    try:
        action._number(float("inf"), 0.001, 1000.0, "massKg")
    except action.PhysicsActionError as error:
        observed = error.reason
    cases.append({"name": "nonfinite", "expected": "SPEC_SCHEMA", "observed": observed, "passed": observed == "SPEC_SCHEMA"})
    output = {"schemaVersion": "bfs.rc3PhysicsActionNegativeControls.v0.1", "status": "PASS" if all(row["passed"] for row in cases) and len(cases) == 16 else "FAIL", "caseCount": len(cases), "passCount": sum(row["passed"] for row in cases), "cases": cases, "sceneMutations": 0, "renders": 0, "networkCalls": 0}
    write(evidence / "negative-controls.json", output)
    print("RC3_NEGATIVE=" + json.dumps(output, sort_keys=True, separators=(",", ":")))
    if output["status"] != "PASS":
        raise RuntimeError("RC3 negative controls failed")


{"build": build, "reopen": reopen, "negative": negative}[args.action]()
