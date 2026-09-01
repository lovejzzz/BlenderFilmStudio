#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Development-only PC9 compatibility, authority and reopen checks."""

import argparse
import copy
import importlib
import json
import sys
from pathlib import Path

import bpy


V1 = "specs/fixtures/causal-studio/PC5_G1.domino-four.scene-spec.v0.1.json"
V2 = "specs/fixtures/causal-studio/PC7_F1.five-domino-filmic-physics.scene-spec.v0.2.json"
V4 = "specs/fixtures/causal-studio/PC8_F1.measured-shutter-filmic-physics.scene-spec.v0.4.json"
PC8_BUILD = "experiments/measured-shutter/PC8-2026-09-01-attempt-01/build.json"


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", choices=("negative", "compat", "reopen"), required=True)
    parser.add_argument("--module-root", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--scene-spec-uri", required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def load_module(root):
    sys.modules.pop("film_studio_causal", None)
    sys.path.insert(0, str(root.resolve(strict=True)))
    return importlib.import_module("film_studio_causal")


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def negative(module, root, fixture_uri, evidence):
    original = json.loads((root / fixture_uri).read_text(encoding="utf-8"))
    attacks = evidence / "attacks"
    attacks.mkdir(parents=True, exist_ok=False)
    cases = []

    def reject(case_id, expected, mutate=None, uri=None, recompute=True):
        document = copy.deepcopy(original)
        if mutate is not None:
            mutate(document)
            if recompute:
                document["sceneSpecHash"] = module._self_hash(document, "sceneSpecHash")
            path = attacks / f"{case_id.lower()}.json"
            write(path, document)
            uri = path.relative_to(root).as_posix()
        before = sorted(obj.name for obj in bpy.context.scene.objects)
        observed = None
        try:
            module.inspect_causal_scene(str(root), uri)
        except module.CausalContractError as error:
            observed = error.reason
        cases.append({"caseId": case_id, "expected": expected, "observed": observed, "sceneUnchanged": before == sorted(obj.name for obj in bpy.context.scene.objects)})

    reject("PATH_ESCAPE", "PATH_ESCAPE", uri="../escape.json")
    reject("UNKNOWN_TOP_LEVEL_FIELD", "UNKNOWN_TOP_LEVEL_FIELD", lambda d: d.update({"python": "import os"}), recompute=False)
    reject("MANUAL_SHUTTER_FIELD", "SPEC_SCHEMA", lambda d: d["cinematography"]["motionBlur"].update({"shutterFrames": 0.3}))
    reject("UNSUPPORTED_BLUR_STRATEGY", "SPEC_SCHEMA", lambda d: d["cinematography"]["motionBlur"].update({"strategy": "MANUAL"}))
    reject("MISSING_ACTOR_ROLE", "SPEC_SCHEMA", lambda d: d["cinematography"]["motionBlur"].update({"semanticRoles": ["target_group"]}))
    reject("UNBOUND_RESOLUTION", "SPEC_SCHEMA", lambda d: d["cinematography"]["motionBlur"].update({"measurementResolution": [1920, 1080]}))
    reject("BLUR_TARGET_OUT_OF_RANGE", "SPEC_SCHEMA", lambda d: d["cinematography"]["motionBlur"].update({"targetBlurPixels": 25.0}))
    reject("REVERSED_SHUTTER_BOUNDS", "SPEC_SCHEMA", lambda d: d["cinematography"]["motionBlur"].update({"minimumShutterFrames": 0.7}))
    reject("INVALID_VARIATION_BASIS", "SPEC_SCHEMA", lambda d: d["targetGroup"]["deterministicVariation"].update({"basisSceneSpecHash": "python"}))
    reject("MANUAL_SHUTTER_AUTHORITY", "SPEC_EXECUTABLE_AUTHORITY", lambda d: d["forbidden"].update({"manualShutterValue": False}))
    reject("POSTPROCESS_BLUR_AUTHORITY", "SPEC_EXECUTABLE_AUTHORITY", lambda d: d["forbidden"].update({"compositorOrPostprocessBlur": False}))
    reject("EFFECT_COVER_AUTHORITY", "SPEC_EXECUTABLE_AUTHORITY", lambda d: d["forbidden"].update({"effectCoverForWeakerPrimaryPhysics": False}))
    reject("FINAL_POSE_AUTHORITY", "FINAL_POSE_AUTHORITY", lambda d: d["acceptance"].update({"targetPoseKeyframes": 1}))
    reject("VARIATION_EXECUTABLE_AUTHORITY", "SPEC_SCHEMA", lambda d: d["targetGroup"]["deterministicVariation"].update({"python": "import os"}))
    reject("MANUAL_TARGET_MASS", "SPEC_SCHEMA", lambda d: d["targetGroup"]["physicalArchetype"].update({"massKg": [1, 1, 1]}))
    reject("MANUAL_TARGET_COM", "SPEC_SCHEMA", lambda d: d["targetGroup"]["physicalArchetype"].update({"centerOfMassHeightsMeters": [0.1, 0.1, 0.1]}))
    reject("INVALID_MASS_STRATEGY", "SPEC_SCHEMA", lambda d: d["targetGroup"]["physicalArchetype"].update({"massStrategy": "MANUAL"}))
    reject("INVALID_COM_STRATEGY", "SPEC_SCHEMA", lambda d: d["targetGroup"]["physicalArchetype"].update({"centerOfMassStrategy": "MANUAL"}))
    reject("MISMATCH_DERIVED_MASS", "SPEC_SCHEMA", lambda d: d["acceptance"].update({"derivedMassesKgExact": [0.1, 0.2, 0.3]}))
    reject("NONMETRIC_ACCEPTANCE", "SPEC_SCHEMA", lambda d: d["acceptance"].update({"metricScaleRequired": False}))
    reject("COLLISION_VISIBLE_MISMATCH", "SPEC_SCHEMA", lambda d: d["acceptance"].update({"collisionShapeMustMatchVisibleBottleHull": False}))
    reject("LIQUID_SIMULATION_CLAIM", "SPEC_EXECUTABLE_AUTHORITY", lambda d: d["forbidden"].update({"liquidSimulationClaim": False}))
    reject("DECORATIVE_COLLISION_PROXY", "SPEC_EXECUTABLE_AUTHORITY", lambda d: d["forbidden"].update({"decorativeCollisionProxyThatDiffersFromVisibleBottle": False}))
    reject("BOX_BOTTLE_COLLISION", "UNSUPPORTED_COLLISION_SHAPE", lambda d: d["targetGroup"]["rigidBody"].update({"collisionShape": "BOX"}))
    reject("MISSING_FILL_FRACTIONS", "SPEC_SCHEMA", lambda d: d["targetGroup"]["physicalArchetype"].pop("fillFractions"))
    reject("DUPLICATE_FILL_LEVEL", "SPEC_SCHEMA", lambda d: d["targetGroup"]["physicalArchetype"].update({"fillFractions": [0.15, 0.15, 0.9]}))
    reject("FILL_OUT_OF_RANGE", "SPEC_SCHEMA", lambda d: d["targetGroup"]["physicalArchetype"].update({"fillFractions": [0.0, 0.55, 0.9]}))
    reject("PHYSICAL_BASIS_MISMATCH", "SPEC_HASH", lambda d: d["targetGroup"]["deterministicVariation"].update({"basisSceneSpecHash": "0" * 64}))
    before = sorted(obj.name for obj in bpy.context.scene.objects)
    observed = None
    try:
        module.execute_causal_scene(str(root), fixture_uri, "INVALID")
    except module.CausalContractError as error:
        observed = error.reason
    cases.append({"caseId": "INSPECTION_REQUIRED", "expected": "INSPECTION_REQUIRED", "observed": observed, "sceneUnchanged": before == sorted(obj.name for obj in bpy.context.scene.objects)})
    passed = all(row["observed"] == row["expected"] and row["sceneUnchanged"] for row in cases)
    result = {"schemaVersion": "bfs.pc9DevelopmentNegativeControls.v0.1", "status": "PASS" if passed else "FAIL", "caseCount": len(cases), "cases": cases, "networkCalls": 0}
    write(evidence / "negative-controls.json", result)
    if not passed:
        raise RuntimeError("PC9 negative controls failed")


def compat(module, root, evidence):
    inspections = {uri: module.inspect_causal_scene(str(root), uri) for uri in (V1, V2, V4)}
    accepted = json.loads((root / PC8_BUILD).read_text(encoding="utf-8"))
    inspection = inspections[V4]
    current = module.execute_causal_scene(str(root), V4, inspection["inspectionToken"])
    checks = {
        "v1Inspect": inspections[V1]["status"] == "APPROVED_READY" and inspections[V1]["targetCount"] == 4,
        "v2Inspect": inspections[V2]["status"] == "APPROVED_READY" and inspections[V2]["targetCount"] == 5,
        "v4Inspect": inspections[V4]["status"] == "APPROVED_READY" and inspections[V4]["targetCount"] == 5,
        "v4PhysicsExact": current["physics"] == accepted["physics"],
        "v4InitialConditionsExact": current["initialConditions"] == accepted["initialConditions"],
        "v4MotionBlurExact": current["cinematography"] == accepted["cinematography"],
        "v4PoseAuthorityExact": current["provenance"] == accepted["provenance"],
    }
    result = {
        "schemaVersion": "bfs.pc9DevelopmentBackwardCompatibility.v0.1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "inspections": inspections,
        "v4CinematographyComparison": {"accepted": accepted["cinematography"], "observed": current["cinematography"]},
        "networkCalls": 0,
    }
    write(evidence / "backward-compatibility.json", result)
    if result["status"] != "PASS":
        raise RuntimeError("PC9 backward compatibility failed")


def reopen(module, root, fixture_uri, evidence):
    scene = bpy.context.scene
    saved = json.loads(scene["film_studio_causal_result"])
    document = json.loads((root / fixture_uri).read_text(encoding="utf-8"))
    actor = bpy.data.objects[saved["semanticRoster"]["dynamicActor"][0]]
    targets = [bpy.data.objects[name] for name in saved["semanticRoster"]["targets"]]
    physics = module._simulate(scene, actor, targets, document)
    measured = module._configure_measured_shutter(scene, bpy.data.objects["CAUSAL_CAM_IMPACT"], [actor, *targets], physics["motionSelection"]["impactFrame"], document)
    masses = [round(target.rigid_body.mass, 8) for target in targets]
    centers = [round(target["film_studio_center_of_mass_height_m"], 8) for target in targets]
    glass = [bpy.data.materials[f"MAT_CausalBottleShell_{index:02d}"] for index in range(1, 4)]
    checks = {
        "physicsExact": physics == saved["physics"],
        "motionBlurExact": measured == saved["cinematography"]["motionBlur"],
        "physicalArchetypesExact": saved["physicalArchetypes"]["targets"] == saved["initialConditions"]["targets"],
        "massesExact": masses == document["acceptance"]["derivedMassesKgExact"],
        "centersOfMassExact": centers == document["acceptance"]["derivedCenterOfMassHeightsMetersExact"],
        "screenRefractionExact": all(material.use_screen_refraction for material in glass),
        "raytraceRefractionExact": all(material.use_raytrace_refraction for material in glass),
        "targetPoseAuthorityZero": saved["provenance"]["targetPoseKeyframes"] == 0,
        "postReleaseActorPoseAuthorityZero": saved["provenance"]["postReleaseActorPoseKeyframes"] == 0,
    }
    result = {"schemaVersion": "bfs.pc9DevelopmentReopen.v0.1", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "massesKg": masses, "centerOfMassHeightsMeters": centers, "networkCalls": 0}
    write(evidence / "reopen.json", result)
    if result["status"] != "PASS":
        raise RuntimeError("PC9 reopen failed")


args = arguments()
repository = args.repository_root.resolve(strict=True)
evidence_root = args.evidence_root.resolve()
evidence_root.mkdir(parents=True, exist_ok=args.action != "negative")
causal = load_module(args.module_root)
if args.action == "negative":
    negative(causal, repository, args.scene_spec_uri, evidence_root)
elif args.action == "compat":
    compat(causal, repository, evidence_root)
else:
    reopen(causal, repository, args.scene_spec_uri, evidence_root)
print(f"PC9_DEVELOPMENT_{args.action.upper()}=PASS")
