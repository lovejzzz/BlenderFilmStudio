#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Independent PC6 audit; imports neither product causal module nor helper."""

import hashlib
import json
import math
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "experiments/causal-productization/PC6-2026-09-01-attempt-01"
EXTERNAL = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/PC6-2026-09-01-attempt-01")
SOURCE = EXTERNAL / "source"
PREREG = ROOT / "specs/ai-native-studio-pc6-causal-contract-productization-preregistration.v0.1.json"
FREEZE = ROOT / "specs/ai-native-studio-pc6-causal-contract-productization-tool-freeze.v0.1.json"
SOURCE_HEAD = "5f3b981a6d84fd49d2eaafe35645456bf4d669e5"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def valid_self(value, field):
    expected = value.get(field)
    body = dict(value)
    body.pop(field, None)
    return expected == hashlib.sha256(canonical(body)).hexdigest()


def self_hashed(value, field):
    body = dict(value)
    body.pop(field, None)
    body[field] = hashlib.sha256(canonical(body)).hexdigest()
    return body


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def git(*args):
    result = subprocess.run(["/usr/bin/git", *args], cwd=SOURCE, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr)
    return result.stdout.strip()


prereg = read(PREREG)
freeze = read(FREEZE)
receipt = read(EVIDENCE / "receipt.json")
build = read(EVIDENCE / "build.json")
reopen = read(EVIDENCE / "reopen.json")
negative = read(EVIDENCE / "negative-controls.json")
processes = [read(path) for path in sorted((EVIDENCE / "processes").glob("*.json"))]
checks = []


def gate(identifier, passed, observation=None):
    checks.append({"id": identifier, "pass": bool(passed), "observation": observation})


gate("A01_PREREGISTRATION_BINDING", prereg["specHash"] == freeze["preregistration"]["specHash"] and receipt["preregistration"]["sha256"] == sha256_file(PREREG))
gate("A01B_TOOL_FREEZE_BINDING", valid_self(freeze, "freezeHash") and freeze["preregistration"]["sha256"] == sha256_file(PREREG) and all(sha256_file(ROOT / row["uri"]) == row["sha256"] for row in freeze["tools"]))
gate("A02_RECEIPT_AND_PROCESS_SELF_HASHES", valid_self(receipt, "receiptHash") and len(processes) == 3 and all(valid_self(row, "processHash") for row in processes))
gate("A03_SOURCE_IDENTITY", git("rev-parse", "HEAD") == SOURCE_HEAD and git("status", "--porcelain=v1") == "")
changed = git("diff", "--name-only", f"{prereg['baseline']['sourceCommit']}..{SOURCE_HEAD}").splitlines()
gate("A04_THREE_PATH_SOURCE_SCOPE", changed == prereg["authorizedProductIncrement"]["paths"], changed)
gate("A05_CLEAN_NATIVE_PRODUCT_BUILD", receipt["checks"]["cleanNativeBuild"] and Path(receipt["build"]["binary"]).is_file() and sha256_file(Path(receipt["build"]["binary"])) == receipt["build"]["binarySha256"])
gate("A06_THREE_PRODUCT_PROCESSES", [row["action"] for row in processes] == ["negative", "build", "reopen"] and all(row["status"] == "PASS" and row["exitCode"] == 0 for row in processes))
expected_reasons = ["PATH_ESCAPE", "UNKNOWN_TOP_LEVEL_FIELD", "UNSUPPORTED_FACTORY", "UNSUPPORTED_COLLISION_SHAPE", "TARGET_COUNT_OUT_OF_RANGE", "NONFINITE_NUMBER", "SPEC_EXECUTABLE_AUTHORITY", "FINAL_POSE_AUTHORITY", "INSPECTION_REQUIRED"]
gate("A07_NINE_NEGATIVE_CONTROLS", negative["status"] == "PASS" and [row["expected"] for row in negative["cases"]] == expected_reasons and all(row["observed"] == row["expected"] and row["sceneUnchanged"] for row in negative["cases"]))
gate("A08_PRODUCT_UI_INSPECTION", build["inspection"]["status"] == "APPROVED_READY" and build["inspection"]["targetCount"] == 4)
gate("A09_ALLOWLIST_FACTORIES", build["inspection"]["actorFactory"] == "GROOVED_SPHERE" and build["inspection"]["targetFactory"] == "BEVELED_DOMINO_BLOCK")
gate("A10_COLLISION_SHAPES", build["inspection"]["collisionShapes"] == "SPHERE / BOX")
gate("A11_BULLET_FINAL_POSE_PROVENANCE", build["provenance"] == {"finalPoseSource": "BLENDER_BULLET_RIGID_BODY", "networkCalls": 0, "postReleaseActorPoseKeyframes": 0, "sceneSpecExecutableAuthority": 0, "targetPoseKeyframes": 0})
gate("A12_NO_FINAL_POSE_KEYS", build["animation"]["actorPoseFramesAfterRelease"] == [] and all(frames == [] for frames in build["animation"]["targetFrames"].values()))
responses = build["physics"]["targetResponseFrames"]
gate("A13_ALL_FOUR_RESPOND", len(responses) == 4 and all(isinstance(frame, int) for frame in responses.values()), responses)
tilts = build["physics"]["finalTiltDegrees"]
gate("A14_ALL_FOUR_TILT", len(tilts) == 4 and all(math.isfinite(value) and value >= prereg["positiveValidation"]["requiredFinalTiltDegreesMinimumEach"] for value in tilts.values()), tilts)
framing = build["framing"]
gate("A15_EVALUATED_RESULT_FRAMING", list(framing) == ["AFTERMATH", "IMPACT", "SETUP"] and all(row["source"] == "EVALUATED_FRAME_SEMANTIC_WORLD_BOUNDS" for row in framing.values()))
review = build["review"]
gate("A16_THREE_BOUND_REVIEW_IMAGES", [row["shotId"] for row in review] == ["SETUP", "IMPACT", "AFTERMATH"] and all((EVIDENCE / row["uri"]).is_file() and sha256_file(EVIDENCE / row["uri"]) == row["sha256"] for row in review))
gate("A17_REOPEN_EXACT", reopen["status"] == "PASS" and reopen["responseFramesExact"] and max(reopen["finalTiltDeltaDegrees"].values()) <= prereg["positiveValidation"]["reopenFinalTiltToleranceDegrees"])
gate("A18_RESOURCE_CEILINGS", receipt["checks"]["resourceCeilings"] and receipt["resources"]["workspaceBytes"] <= prereg["resourceCeilings"]["workspaceBytes"] and receipt["resources"]["evidenceBytesBeforeReceipt"] <= prereg["resourceCeilings"]["evidenceBytes"])
gate("A19_FORBIDDEN_COUNTS", receipt["counters"]["networkCalls"] == receipt["counters"]["engineRemoteWrites"] == receipt["counters"]["releases"] == receipt["counters"]["signing"] == receipt["counters"]["notarization"] == 0)
gate("A20_CLAIM_CEILING", "one allowlisted declarative scene" in receipt["claim"] and receipt["status"] == "PASS")
passed = sum(row["pass"] for row in checks)
body = {
    "schemaVersion": "bfs.pc6CausalProductizationIndependentAudit.v0.1",
    "status": "PASS" if passed == len(checks) else "FAIL",
    "machineVerdict": "PASS" if passed == len(checks) else "FAIL",
    "visualVerdict": "PENDING_DIRECT_SCREENSHOT_REVIEW",
    "overallVerdict": "PENDING_DIRECT_SCREENSHOT_REVIEW",
    "checkPassed": passed,
    "checkTotal": len(checks),
    "checks": checks,
    "bindings": {"receiptSha256": sha256_file(EVIDENCE / "receipt.json"), "receiptHash": receipt["receiptHash"], "sourceHead": SOURCE_HEAD},
}
audit = self_hashed(body, "auditHash")
(EVIDENCE / "independent-audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(f"PC6_AUDIT {audit['status']} {passed}/{len(checks)} {audit['auditHash']}")
if audit["status"] != "PASS":
    raise SystemExit(1)
