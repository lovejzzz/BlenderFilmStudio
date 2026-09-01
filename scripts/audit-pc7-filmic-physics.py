#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Independent PC7 audit; imports neither the product module nor product helper."""

import hashlib
import json
import math
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PREREG = ROOT / "specs/ai-native-studio-pc7-filmic-physics-preregistration.v0.1.json"
FREEZE = ROOT / "specs/ai-native-studio-pc7-filmic-physics-tool-freeze.v0.1.json"
FIXTURE = ROOT / "specs/fixtures/causal-studio/PC7_F1.five-domino-filmic-physics.scene-spec.v0.2.json"
EVIDENCE = ROOT / "experiments/filmic-physics/PC7-2026-09-01-attempt-01"
EXTERNAL = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/PC7-2026-09-01-attempt-01")
SOURCE = EXTERNAL / "source"
DEPENDENCY = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PhaseB-workspace/PB.6-2026-08-31-mac-m2max-attempt-01/source/lib/macos_arm64")
SOURCE_HEAD = "c7eece67bff64cbff2de4c6e1aee3248afbca600"
SOURCE_BASE = "5f3b981a6d84fd49d2eaafe35645456bf4d669e5"
DEPENDENCY_HEAD = "a76ef917b4849ba2b1b1deb1a643e131a884a63b"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def js_canonical(value):
    if value is None or isinstance(value, bool) or isinstance(value, str):
        return json.dumps(value, separators=(",", ":"))
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("nonfinite")
        return str(int(value)) if value.is_integer() else json.dumps(value)
    if isinstance(value, list):
        return "[" + ",".join(js_canonical(child) for child in value) + "]"
    if isinstance(value, dict):
        return "{" + ",".join(f"{json.dumps(key)}:{js_canonical(value[key])}" for key in sorted(value)) + "}"
    raise TypeError(type(value))


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


def valid_js_self(value, field):
    expected = value.get(field)
    body = dict(value)
    body.pop(field, None)
    return expected == hashlib.sha256(js_canonical(body).encode()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def git(*args, cwd=SOURCE):
    result = subprocess.run(["/usr/bin/git", *args], cwd=cwd, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr)
    return result.stdout.strip()


def tree_bytes(path):
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file() and not item.is_symlink())


prereg = read(PREREG)
freeze = read(FREEZE)
fixture = read(FIXTURE)
receipt = read(EVIDENCE / "receipt.json")
build = read(EVIDENCE / "build.json")
reopen = read(EVIDENCE / "reopen.json")
negative = read(EVIDENCE / "negative-controls.json")
clip = read(EVIDENCE / "clip-video.json")
processes = [read(path) for path in sorted((EVIDENCE / "processes").glob("*.json"))]
checks = []


def gate(identifier, passed, observation=None):
    checks.append({"id": identifier, "pass": bool(passed), "observation": observation})


gate("A01_FROZEN_INPUT_BINDINGS", valid_self(prereg, "specHash") and valid_self(freeze, "freezeHash") and valid_js_self(fixture, "sceneSpecHash") and freeze["preregistration"]["sha256"] == sha256_file(PREREG) and freeze["fixture"]["sha256"] == sha256_file(FIXTURE))
gate("A02_TOOL_AND_RECEIPT_SELF_HASHES", all(sha256_file(ROOT / row["uri"]) == row["sha256"] for row in freeze["tools"]) and valid_self(receipt, "receiptHash") and valid_self(clip, "clipHash") and len(processes) == 3 and all(valid_self(row, "processHash") for row in processes))
gate("A03_SOURCE_IDENTITY", git("rev-parse", "HEAD") == SOURCE_HEAD and git("status", "--porcelain=v1") == "")
changed = git("diff", "--name-only", f"{SOURCE_BASE}..{SOURCE_HEAD}").splitlines()
numstat = git("diff", "--numstat", f"{SOURCE_BASE}..{SOURCE_HEAD}").splitlines()
gate("A04_ONE_PATH_SOURCE_SCOPE", changed == ["scripts/modules/film_studio_causal.py"] and numstat == ["116\t15\tscripts/modules/film_studio_causal.py"], {"paths": changed, "numstat": numstat})
binary = Path(receipt["build"]["binary"])
installed = binary.parents[1] / "Resources/5.2/scripts/modules/film_studio_causal.py"
gate("A05_CLEAN_NATIVE_PRODUCT_BUILD", receipt["checks"]["cleanNativeBuild"] and binary.is_file() and sha256_file(binary) == receipt["build"]["binarySha256"] and installed.is_file() and sha256_file(installed) == freeze["productSource"]["sha256"])
gate("A06_THREE_PRODUCT_PROCESSES", [row["action"] for row in processes] == ["negative", "build", "reopen"] and all(row["status"] == "PASS" and row["exitCode"] == 0 for row in processes))
expected_cases = ["PATH_ESCAPE", "UNKNOWN_TOP_LEVEL_FIELD", "UNSUPPORTED_FACTORY", "UNSUPPORTED_COLLISION_SHAPE", "TARGET_COUNT_OUT_OF_RANGE", "NONFINITE_NUMBER", "SPEC_EXECUTABLE_AUTHORITY", "FINAL_POSE_AUTHORITY", "UNSUPPORTED_SELECTION", "VARIATION_EXECUTABLE_AUTHORITY", "VARIATION_OUT_OF_RANGE", "INSPECTION_REQUIRED"]
gate("A07_TWELVE_NEGATIVE_CONTROLS", negative["status"] == "PASS" and [row["caseId"] for row in negative["cases"]] == expected_cases and all(row["observed"] == row["expected"] and row["sceneUnchanged"] for row in negative["cases"]))
gate("A08_V1_BACKWARD_COMPATIBILITY", negative["v1Compatibility"] == {"sceneSpecHash": "727f04b669abbe77f29c05902ab20364898d4e921d83e788b89bab877817ae1a", "status": "APPROVED_READY", "targetCount": 4})
gate("A09_PRODUCT_INSPECTION", build["inspection"]["status"] == "APPROVED_READY" and build["inspection"]["sceneSpecHash"] == fixture["sceneSpecHash"] and build["inspection"]["targetCount"] == 5)

variation = fixture["targetGroup"]["deterministicVariation"]
derived = []
for index, position in enumerate(fixture["targetGroup"]["initialPositions"], 1):
    def sample(channel):
        token = f"{fixture['sceneSpecHash']}:{variation['seed']}:{index}:{channel}".encode()
        integer = int.from_bytes(hashlib.sha256(token).digest()[:8], "big")
        return integer / (2 ** 64 - 1) * 2.0 - 1.0
    row = {
        "target": f"CAUSAL_TARGET_{index:03d}",
        "positionX": round(position[0] + sample("position-x") * variation["positionJitterMetersMaximum"], 8),
        "positionY": round(position[1] + sample("position-y") * variation["positionJitterMetersMaximum"], 8),
        "yawDegrees": round(sample("yaw") * variation["yawJitterDegreesMaximum"], 8),
        "friction": round(max(0.0, min(1.0, fixture["targetGroup"]["rigidBody"]["friction"] + sample("friction") * variation["frictionJitterMaximum"])), 8),
        "restitution": round(max(0.0, min(1.0, fixture["targetGroup"]["rigidBody"]["restitution"] + sample("restitution") * variation["restitutionJitterMaximum"])), 8),
    }
    derived.append(row)
gate("A10_INDEPENDENT_DETERMINISTIC_INITIAL_VARIATION", build["initialConditions"] == {"source": "SHA256_SCENE_HASH_SEED_TARGET_INDEX_CHANNEL", "targets": derived}, derived)
gate("A11_BULLET_FINAL_POSE_PROVENANCE", build["provenance"] == {"finalPoseSource": "BLENDER_BULLET_RIGID_BODY", "networkCalls": 0, "postReleaseActorPoseKeyframes": 0, "sceneSpecExecutableAuthority": 0, "targetPoseKeyframes": 0})
gate("A12_NO_FINAL_POSE_KEYS", build["animation"]["actorPoseFramesAfterRelease"] == [] and all(frames == [] for frames in build["animation"]["targetFrames"].values()))
responses = build["physics"]["targetResponseFrames"]
gate("A13_ALL_FIVE_RESPOND", len(responses) == 5 and all(isinstance(frame, int) for frame in responses.values()), responses)
tilts = build["physics"]["finalTiltDegrees"]
gate("A14_ALL_FIVE_TILT", len(tilts) == 5 and all(math.isfinite(value) and value >= fixture["acceptance"]["targetTiltDegreesAtFinalMinimumEach"] for value in tilts.values()), tilts)
samples = build["physics"]["motionSamples"]
first = build["physics"]["firstTargetResponseFrame"]
minimum = first + fixture["acceptance"]["impactFrameAfterFirstResponseMinimum"]
expected_impact = max((row for row in samples if row["frame"] >= minimum), key=lambda row: (row["activeTargetCount"], row["aggregateAngularStepDegrees"], -row["frame"]))
selection = build["physics"]["motionSelection"]
impact_exact = selection["impactFrame"] == expected_impact["frame"] and selection["impactActiveTargetCount"] == expected_impact["activeTargetCount"] and selection["impactAggregateAngularStepDegrees"] == expected_impact["aggregateAngularStepDegrees"] and selection["impactTargetAngularStepDegrees"] == expected_impact["targetAngularStepDegrees"]
gate("A15_INDEPENDENT_IMPACT_SELECTION", impact_exact and selection["impactRule"] == "MAX_ACTIVE_TARGETS_THEN_AGGREGATE_ANGULAR_STEP_THEN_EARLIEST", expected_impact)
gate("A16_PROPAGATED_IMPACT_THRESHOLD", selection["impactActiveTargetCount"] >= fixture["acceptance"]["impactActiveTargetCountMinimum"] and selection["impactFrame"] - first >= fixture["acceptance"]["impactFrameAfterFirstResponseMinimum"], selection)
settle_count = fixture["acceptance"]["settleConsecutiveFrames"]
settle_limit = fixture["acceptance"]["settleAngularStepDegreesMaximum"]
settle_start = max(responses.values())
expected_aftermath = fixture["timeline"]["frameEnd"]
for offset, row in enumerate(samples):
    window = samples[offset:offset + settle_count]
    if row["frame"] >= settle_start and len(window) == settle_count and all(child["aggregateAngularStepDegrees"] <= settle_limit for child in window):
        expected_aftermath = row["frame"]
        break
gate("A17_INDEPENDENT_SETTLED_AFTERMATH", selection["aftermathFrame"] == expected_aftermath and selection["aftermathRule"] == "FIRST_POST_RESPONSE_SETTLED_WINDOW_ELSE_FRAME_END", expected_aftermath)
framing = build["framing"]
gate("A18_EVALUATED_MOTION_AND_BOUNDS_FRAMING", framing["IMPACT"]["frame"] == selection["impactFrame"] and framing["AFTERMATH"]["frame"] == selection["aftermathFrame"] and all(row["source"] == "EVALUATED_FRAME_SEMANTIC_WORLD_BOUNDS" for row in framing.values()))
gate("A19_THREE_BOUND_REVIEW_STILLS", [row["shotId"] for row in build["review"]] == ["SETUP", "IMPACT", "AFTERMATH"] and all((EVIDENCE / row["uri"]).is_file() and sha256_file(EVIDENCE / row["uri"]) == row["sha256"] for row in build["review"]))
clip_frames = build["clip"]["frames"]
gate("A20_TWENTY_FOUR_DYNAMIC_CLIP_FRAMES", len(clip_frames) == build["clip"]["frameCount"] == 24 and len({row["sha256"] for row in clip_frames}) >= 12 and all((EVIDENCE / row["uri"]).is_file() and sha256_file(EVIDENCE / row["uri"]) == row["sha256"] for row in clip_frames))
gate("A21_BOUND_960X540_24FPS_VIDEO", clip["status"] == "PASS" and clip["frames"] == 24 and clip["width"] == 960 and clip["height"] == 540 and clip["fps"] == "24/1" and (EVIDENCE / clip["uri"]).is_file() and sha256_file(EVIDENCE / clip["uri"]) == clip["sha256"])
gate("A22_REOPEN_EXACT", reopen["status"] == "PASS" and reopen["responseFramesExact"] and reopen["motionSelectionExact"] and max(reopen["finalTiltDeltaDegrees"].values()) <= fixture["acceptance"]["reopenFinalTiltToleranceDegrees"])
gate("A23_DEPENDENCY_RETAINED", git("rev-parse", "HEAD", cwd=DEPENDENCY) == DEPENDENCY_HEAD and git("status", "--porcelain=v1", cwd=DEPENDENCY) == "")
gate("A24_RESOURCE_CEILINGS", receipt["checks"]["resourceCeilings"] and tree_bytes(EXTERNAL) <= prereg["resourceCeilings"]["workspaceBytes"] and tree_bytes(EVIDENCE) <= prereg["resourceCeilings"]["evidenceBytes"])
gate("A25_FORBIDDEN_COUNTS", receipt["counters"]["networkCalls"] == receipt["counters"]["engineRemoteWrites"] == receipt["counters"]["forcePushes"] == receipt["counters"]["tags"] == receipt["counters"]["releases"] == receipt["counters"]["binaryDistribution"] == receipt["counters"]["signing"] == receipt["counters"]["notarization"] == 0)
gate("A26_EXACT_OPERATION_COUNTS", receipt["counters"]["cleanBuilds"] == 1 and receipt["counters"]["productStarts"] == 3 and receipt["counters"]["sceneMutatingExecutions"] == 1 and receipt["counters"]["reviewStillRenders"] == 3 and receipt["counters"]["impactClipFrameRenders"] == 24)
source_text = (SOURCE / "scripts/modules/film_studio_causal.py").read_text(encoding="utf-8")
gate("A27_GENERIC_SOURCE_NO_FIXTURE_BRANCH", fixture["sceneId"] not in source_text and "PC7-F1" not in source_text and "hand-picked frame" not in source_text)
passed = sum(row["pass"] for row in checks)
body = {
    "schemaVersion": "bfs.pc7FilmicPhysicsIndependentAudit.v0.1", "status": "PASS" if passed == len(checks) else "FAIL",
    "machineVerdict": "PASS" if passed == len(checks) else "FAIL", "visualVerdict": "PENDING_DIRECT_STILL_AND_CLIP_REVIEW", "overallVerdict": "PENDING_DIRECT_STILL_AND_CLIP_REVIEW",
    "checkPassed": passed, "checkTotal": len(checks), "checks": checks,
    "bindings": {"receiptSha256": sha256_file(EVIDENCE / "receipt.json"), "receiptHash": receipt["receiptHash"], "sourceHead": SOURCE_HEAD, "fixtureHash": fixture["sceneSpecHash"]},
}
audit = dict(body)
audit["auditHash"] = hashlib.sha256(canonical(body)).hexdigest()
(EVIDENCE / "independent-audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(f"PC7_AUDIT {audit['status']} {passed}/{len(checks)} {audit['auditHash']}")
if audit["status"] != "PASS":
    raise SystemExit(1)
