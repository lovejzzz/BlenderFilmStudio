#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Independent PC9 evidence auditor."""

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "experiments/physical-archetypes/PC9-2026-09-01-attempt-01"
FREEZE = ROOT / "specs/ai-native-studio-pc9-physical-archetypes-tool-freeze.v0.1.json"
SOURCE = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/PC9-2026-09-01-attempt-01/source")
EXTERNAL = SOURCE.parent


def canonical(value): return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024): digest.update(chunk)
    return digest.hexdigest()
def valid_self(value, field):
    body = dict(value); expected = body.pop(field, None)
    return expected == hashlib.sha256(canonical(body)).hexdigest()
def tree_bytes(path): return sum(item.stat().st_size for item in path.rglob("*") if item.is_file() and not item.is_symlink())
def git(*args):
    result = subprocess.run(["/usr/bin/git", *args], cwd=SOURCE, text=True, capture_output=True)
    return result.stdout.strip() if result.returncode == 0 else None
def add(rows, name, passed, observed): rows.append({"name": name, "status": "PASS" if passed else "FAIL", "observed": observed})


freeze = json.loads(FREEZE.read_text()); receipt = json.loads((EVIDENCE / "receipt.json").read_text()); build = json.loads((EVIDENCE / "build.json").read_text()); negative = json.loads((EVIDENCE / "negative-controls.json").read_text()); compat = json.loads((EVIDENCE / "backward-compatibility.json").read_text()); reopen = json.loads((EVIDENCE / "reopen.json").read_text()); clip = json.loads((EVIDENCE / "clip-video.json").read_text())
processes = [json.loads(path.read_text()) for path in sorted((EVIDENCE / "processes").glob("*.json"))]
checks = []
add(checks, "RECEIPT_SELF_HASH", valid_self(receipt, "receiptHash"), receipt["receiptHash"])
add(checks, "PROCESS_SELF_HASHES", len(processes) == 3 and all(valid_self(row, "processHash") for row in processes), [row.get("processHash") for row in processes])
add(checks, "CLIP_SELF_HASH", valid_self(clip, "clipHash"), clip["clipHash"])
add(checks, "FREEZE_BINDINGS", all(sha256_file(ROOT / row["uri"]) == row["sha256"] for row in freeze["bindings"]), len(freeze["bindings"]))
add(checks, "SOURCE_HEAD", git("rev-parse", "HEAD") == receipt["source"]["head"], git("rev-parse", "HEAD"))
add(checks, "SOURCE_CLEAN", git("status", "--porcelain=v1") == "", git("status", "--porcelain=v1"))
add(checks, "SOURCE_SCOPE", receipt["source"]["paths"] == ["scripts/modules/film_studio_causal.py"] and receipt["source"]["additions"] == 319 and receipt["source"]["deletions"] == 38, receipt["source"])
binary = Path(receipt["build"]["binary"])
add(checks, "BINARY_HASH", binary.is_file() and sha256_file(binary) == receipt["build"]["binarySha256"], receipt["build"]["binarySha256"])
installed = binary.parents[1] / "Resources/5.2/scripts/modules/film_studio_causal.py"
add(checks, "INSTALLED_MODULE", installed.is_file() and sha256_file(installed) == freeze["productSource"]["sha256"], str(installed))
add(checks, "NEGATIVE_CONTROLS", negative["status"] == "PASS" and negative["caseCount"] == 29 and all(row["observed"] == row["expected"] and row["sceneUnchanged"] for row in negative["cases"]), negative["caseCount"])
add(checks, "BACKWARD_COMPATIBILITY", compat["status"] == "PASS" and all(compat["checks"].values()), compat["checks"])
add(checks, "PROCESS_STATUS", all(row["status"] == "PASS" and row["exitCode"] == 0 for row in processes), [row["name"] for row in processes])
add(checks, "TARGET_RESPONSES", all(value is not None for value in build["physics"]["targetResponseFrames"].values()), build["physics"]["targetResponseFrames"])
tilts = list(build["physics"]["finalTiltDegrees"].values())
add(checks, "FINAL_TILTS", min(tilts) >= 25 and sum(value >= 60 for value in tilts) >= 2, tilts)
add(checks, "IMPACT_ACTIVE", build["physics"]["motionSelection"]["impactActiveTargetCount"] >= 3, build["physics"]["motionSelection"])
targets = build["physicalArchetypes"]["targets"]
add(checks, "MASS_COM_FILL", [row["derivedMassKg"] for row in targets] == [0.10685, 0.30645, 0.4811] and [row["derivedCenterOfMassHeightMeters"] for row in targets] == [0.05469894, 0.06743313, 0.0964538] and [row["fillFraction"] for row in targets] == [0.15, 0.55, 0.9], targets)
add(checks, "VISIBLE_HULL", all(row["collisionShape"] == "CONVEX_HULL" and row["visibleBodyIsCollisionHullSource"] and row["detailObjectCount"] >= 4 for row in targets), [row["collisionShape"] for row in targets])
add(checks, "POSE_AUTHORITY", build["animation"]["actorPoseFramesAfterRelease"] == [] and all(not frames for frames in build["animation"]["targetFrames"].values()), build["animation"])
blur = build["cinematography"]["motionBlur"]
add(checks, "MEASURED_NATIVE_BLUR", blur["nativeTransformMotionBlur"] and not blur["compositorOrPostprocessBlur"] and 8 <= blur["medianPixelsPerFrame"] <= 80 and 0.08 <= blur["computedShutterFrames"] <= 0.5, blur)
add(checks, "REFRACTION", all(build["refraction"]["screen"]) and all(build["refraction"]["raytrace"]), build["refraction"])
add(checks, "REVIEW_HASHES", len(build["review"]) == 3 and all((EVIDENCE / "review" / row["uri"]).is_file() and sha256_file(EVIDENCE / "review" / row["uri"]) == row["sha256"] for row in build["review"]), build["review"])
add(checks, "SHARP_CONTROL", (EVIDENCE / "review" / build["sharpImpactControl"]["uri"]).is_file() and build["sharpImpactControl"]["sha256"] != next(row["sha256"] for row in build["review"] if row["shotId"] == "IMPACT"), build["sharpImpactControl"])
add(checks, "CLIP_FRAMES", build["clip"]["frameCount"] == 24 and clip["frames"] == 24 and clip["width"] == 960 and clip["height"] == 540, clip)
add(checks, "REOPEN_EXACT", reopen["status"] == "PASS" and all(reopen["checks"].values()), reopen["checks"])
add(checks, "RECEIPT_CHECKS", receipt["status"] == "PASS" and all(receipt["checks"].values()), receipt["checks"])
add(checks, "COUNTERS", receipt["counters"] == {"binaryDistribution": 0, "blendSaves": 1, "cleanBuilds": 1, "engineRemoteWrites": 0, "forcePushes": 0, "impactClipFrameRenders": 24, "networkCalls": 0, "notarization": 0, "productReviewStillRenders": 3, "productStarts": 3, "releases": 0, "reopens": 1, "sceneMutatingExecutions": 1, "sharpImpactControlRenders": 1, "signing": 0, "tags": 0}, receipt["counters"])
add(checks, "RESOURCES", tree_bytes(EXTERNAL) <= 53687091200 and tree_bytes(EVIDENCE) <= 335544320, {"workspace": tree_bytes(EXTERNAL), "evidence": tree_bytes(EVIDENCE)})
passed = sum(row["status"] == "PASS" for row in checks)
body = {"schemaVersion": "bfs.pc9PhysicalArchetypesIndependentAudit.v0.1", "status": "PASS" if passed == len(checks) else "FAIL", "checkPassed": passed, "checkTotal": len(checks), "checks": checks, "receipt": {"sha256": sha256_file(EVIDENCE / "receipt.json"), "receiptHash": receipt["receiptHash"]}, "networkCalls": 0, "engineRemoteWrites": 0}
body["auditHash"] = hashlib.sha256(canonical(body)).hexdigest()
(EVIDENCE / "audit.json").write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")
print(f"PC9_AUDIT {body['status']} {passed}/{len(checks)} {body['auditHash']}")
if body["status"] != "PASS": raise SystemExit(1)
