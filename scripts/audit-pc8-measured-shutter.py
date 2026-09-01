#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Independent no-Blender audit for PC8 measured shutter."""

import hashlib
import json
import math
import statistics
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PREREG = ROOT / "specs/ai-native-studio-pc8-measured-shutter-c1-preregistration.v0.2.json"
FREEZE = ROOT / "specs/ai-native-studio-pc8-measured-shutter-tool-freeze.v0.1.json"
FIXTURE = ROOT / "specs/fixtures/causal-studio/PC8_F1.measured-shutter-filmic-physics.scene-spec.v0.4.json"
PC7_BUILD = ROOT / "experiments/filmic-physics/PC7-2026-09-01-attempt-01/build.json"
EVIDENCE = ROOT / "experiments/measured-shutter/PC8-2026-09-01-attempt-01"
SOURCE = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/PC8-2026-09-01-attempt-01/source")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def valid_self(value, field):
    body = dict(value); expected = body.pop(field, None)
    return expected == hashlib.sha256(canonical(body)).hexdigest()


def self_hashed(value, field):
    body = dict(value); body.pop(field, None)
    body[field] = hashlib.sha256(canonical(body)).hexdigest()
    return body


def git(*args):
    result = subprocess.run(["/usr/bin/git", *args], cwd=SOURCE, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr)
    return result.stdout.strip()


def independent_variation(document):
    variation = document["targetGroup"]["deterministicVariation"]
    basis = variation["basisSceneSpecHash"]
    output = []
    for index, position in enumerate(document["targetGroup"]["initialPositions"], 1):
        def sample(channel):
            token = f"{basis}:{variation['seed']}:{index}:{channel}".encode()
            integer = int.from_bytes(hashlib.sha256(token).digest()[:8], "big")
            return integer / (2 ** 64 - 1) * 2.0 - 1.0
        body = document["targetGroup"]["rigidBody"]
        row = {
            "target": f"CAUSAL_TARGET_{index:03d}",
            "positionX": position[0] + sample("position-x") * variation["positionJitterMetersMaximum"],
            "positionY": position[1] + sample("position-y") * variation["positionJitterMetersMaximum"],
            "yawDegrees": sample("yaw") * variation["yawJitterDegreesMaximum"],
            "friction": max(0.0, min(1.0, body["friction"] + sample("friction") * variation["frictionJitterMaximum"])),
            "restitution": max(0.0, min(1.0, body["restitution"] + sample("restitution") * variation["restitutionJitterMaximum"])),
        }
        output.append({key: round(value, 8) if isinstance(value, float) else value for key, value in row.items()})
    return output


def check(checks, check_id, passed, observation=None):
    checks.append({"id": check_id, "pass": bool(passed), "observation": observation})


prereg = json.loads(PREREG.read_text()); freeze = json.loads(FREEZE.read_text()); fixture = json.loads(FIXTURE.read_text())
receipt = json.loads((EVIDENCE / "receipt.json").read_text()); build = json.loads((EVIDENCE / "build.json").read_text()); reopen = json.loads((EVIDENCE / "reopen.json").read_text()); negative = json.loads((EVIDENCE / "negative-controls.json").read_text()); clip = json.loads((EVIDENCE / "clip-video.json").read_text()); pc7 = json.loads(PC7_BUILD.read_text())
processes = [json.loads(path.read_text()) for path in sorted((EVIDENCE / "processes").glob("*.json"))]
checks = []
check(checks, "A01_FROZEN_SELF_HASHES", valid_self(prereg, "specHash") and valid_self(freeze, "freezeHash") and receipt["receiptHash"] and valid_self(receipt, "receiptHash"))
check(checks, "A02_FROZEN_FILE_BINDINGS", freeze["preregistration"]["sha256"] == sha256_file(PREREG) and freeze["fixture"]["sha256"] == sha256_file(FIXTURE) and all(sha256_file(ROOT / row["uri"]) == row["sha256"] for row in freeze["tools"]))
check(checks, "A03_SOURCE_IDENTITY", git("rev-parse", "HEAD") == freeze["productSource"]["commit"] and git("status", "--porcelain=v1") == "")
paths = git("diff", "--name-only", f"{receipt['source']['baseline']}..{receipt['source']['head']}").splitlines(); numstat = git("diff", "--numstat", f"{receipt['source']['baseline']}..{receipt['source']['head']}").splitlines()
check(checks, "A04_ONE_PATH_SOURCE_SCOPE", paths == ["scripts/modules/film_studio_causal.py"] and numstat == ["120\t16\tscripts/modules/film_studio_causal.py"], {"paths": paths, "numstat": numstat})
source_text = (SOURCE / "scripts/modules/film_studio_causal.py").read_text()
check(checks, "A05_GENERIC_SOURCE_NO_FIXTURE_BRANCH", not any(token in source_text for token in ("PC7-F1", "PC8-F1", "690c35c3", "3d97a1b8", "b1bcabc7")))
check(checks, "A06_NO_NEW_FINAL_POSE_INSERTION", source_text.count("keyframe_insert") == 4 and "target.keyframe_insert" not in source_text)
check(checks, "A07_CLEAN_NATIVE_PRODUCT_BUILD", receipt["checks"]["cleanNativeBuild"] and Path(receipt["build"]["binary"]).is_file() and sha256_file(Path(receipt["build"]["binary"])) == receipt["build"]["binarySha256"])
check(checks, "A08_THREE_PRODUCT_PROCESSES", len(processes) == 3 and [row["action"] for row in processes] == ["negative", "build", "reopen"] and all(valid_self(row, "processHash") and row["status"] == "PASS" for row in processes))
log_exact = all(sha256_file(EVIDENCE / "logs" / f"{row['index']:02d}-{row['name']}.stdout.log") == row["stdoutSha256"] and sha256_file(EVIDENCE / "logs" / f"{row['index']:02d}-{row['name']}.stderr.log") == row["stderrSha256"] for row in processes)
check(checks, "A09_PROCESS_LOG_BINDINGS", log_exact)
check(checks, "A10_SIXTEEN_NEGATIVE_CONTROLS", negative["status"] == "PASS" and len(negative["cases"]) == 16 and all(row["observed"] == row["expected"] and row["sceneUnchanged"] for row in negative["cases"]))
check(checks, "A11_V2_COMPATIBILITY", negative["v2Compatibility"]["status"] == "APPROVED_READY" and negative["v2Compatibility"]["sceneSpecHash"] == "b1bcabc70da6ec0b32d00d21a54cc56bf38dc4d485ee3136e32bece8b2e19978")
derived = independent_variation(fixture)
check(checks, "A12_INDEPENDENT_VARIATION_BASIS", fixture["targetGroup"]["deterministicVariation"]["basisSceneSpecHash"] == prereg["variationIdentityRule"]["basisSceneSpecHash"] and build["initialConditions"]["targets"] == derived, derived)
check(checks, "A13_PC7_INITIAL_CONDITIONS_EXACT", build["initialConditions"]["targets"] == pc7["initialConditions"]["targets"])
check(checks, "A14_PC7_PRIMARY_PHYSICS_EXACT", build["physics"] == pc7["physics"])
check(checks, "A15_SOLVER_ONLY_FINAL_POSES", build["provenance"]["finalPoseSource"] == "BLENDER_BULLET_RIGID_BODY" and build["animation"]["actorPoseFramesAfterRelease"] == [] and all(not frames for frames in build["animation"]["targetFrames"].values()))
blur = build["cinematography"]["motionBlur"]; speeds = list(blur["objectPixelsPerFrame"].values()); median = statistics.median(speeds)
check(checks, "A16_INDEPENDENT_MEDIAN", math.isclose(median, blur["medianPixelsPerFrame"], abs_tol=1e-8), median)
spec_blur = fixture["cinematography"]["motionBlur"]; expected_unclamped = spec_blur["targetBlurPixels"] / median; expected_shutter = round(max(spec_blur["minimumShutterFrames"], min(spec_blur["maximumShutterFrames"], expected_unclamped)), 8)
check(checks, "A17_INDEPENDENT_SHUTTER", expected_shutter == blur["computedShutterFrames"] and blur["position"] == "CENTER", {"expected": expected_shutter, "observed": blur["computedShutterFrames"]})
motion_range = fixture["acceptance"]["measuredMedianMotionPixelsPerFrameRange"]; shutter_range = fixture["acceptance"]["computedShutterFramesRange"]
check(checks, "A18_FROZEN_MOTION_AND_SHUTTER_RANGES", motion_range[0] <= median <= motion_range[1] and shutter_range[0] <= expected_shutter <= shutter_range[1])
check(checks, "A19_TARGET_BLUR_ERROR", blur["targetErrorPixels"] <= fixture["acceptance"]["computedBlurTargetErrorPixelsMaximum"] and math.isclose(blur["achievedMedianBlurPixels"], median * expected_shutter, abs_tol=1e-8))
check(checks, "A20_NATIVE_TRANSFORM_BLUR_ONLY", blur["nativeTransformMotionBlur"] is True and blur["compositorOrPostprocessBlur"] is False)
sharp_path = EVIDENCE / build["sharpImpactControl"]["uri"]; impact = next(row for row in build["review"] if row["shotId"] == "IMPACT"); impact_path = EVIDENCE / impact["uri"]
check(checks, "A21_BOUND_SHARP_BLURRED_AB", sharp_path.is_file() and impact_path.is_file() and sha256_file(sharp_path) == build["sharpImpactControl"]["sha256"] and sha256_file(impact_path) == impact["sha256"] and build["sharpImpactControl"]["sha256"] != impact["sha256"])
check(checks, "A22_THREE_PRODUCT_STILLS", len(build["review"]) == 3 and {row["shotId"] for row in build["review"]} == {"SETUP", "IMPACT", "AFTERMATH"} and all(sha256_file(EVIDENCE / row["uri"]) == row["sha256"] for row in build["review"]))
check(checks, "A23_TWENTY_FOUR_FRAME_CLIP", build["clip"]["frameCount"] == 24 and len(build["clip"]["frames"]) == 24 and len({row["sha256"] for row in build["clip"]["frames"]}) >= 12 and all(sha256_file(EVIDENCE / row["uri"]) == row["sha256"] for row in build["clip"]["frames"]))
check(checks, "A24_BOUND_VIDEO", valid_self(clip, "clipHash") and clip["frames"] == 24 and clip["width"] == 960 and clip["height"] == 540 and clip["fps"] == "24/1" and sha256_file(EVIDENCE / clip["uri"]) == clip["sha256"])
check(checks, "A25_REOPEN_EXACT", reopen["status"] == "PASS" and reopen["physicsExact"] and reopen["motionBlurExact"] and max(reopen["finalTiltDeltaDegrees"].values()) == 0.0)
check(checks, "A26_RESOURCE_AND_OPERATION_CEILINGS", receipt["checks"]["resourceCeilings"] and receipt["counters"] == {"binaryDistribution": 0, "blendSaves": 1, "cleanBuilds": 1, "engineRemoteWrites": 0, "forcePushes": 0, "impactClipFrameRenders": 24, "networkCalls": 0, "notarization": 0, "productReviewStillRenders": 3, "productStarts": 3, "releases": 0, "reopens": 1, "sceneMutatingExecutions": 1, "sharpImpactControlRenders": 1, "signing": 0, "tags": 0})
check(checks, "A27_RECEIPT_ALL_CHECKS", receipt["status"] == "PASS" and all(receipt["checks"].values()))

passed = sum(row["pass"] for row in checks); status = "PASS" if passed == len(checks) else "FAIL"
audit = self_hashed({"schemaVersion": "bfs.pc8MeasuredShutterIndependentAudit.v0.1", "status": status, "checkPassed": passed, "checkTotal": len(checks), "bindings": {"receiptHash": receipt["receiptHash"], "sourceHead": receipt["source"]["head"], "fixtureHash": fixture["sceneSpecHash"]}, "checks": checks}, "auditHash")
(EVIDENCE / "independent-audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n")
print(f"PC8_AUDIT {status} {passed}/{len(checks)} {audit['auditHash']}")
if status != "PASS":
    raise SystemExit(1)
