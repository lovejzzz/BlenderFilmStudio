#!/usr/bin/env python3
"""Independent host-side audit for the frozen RC1 robot-capstone attempt."""

import hashlib
import json
import math
import subprocess
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
WORKSPACE = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC1-2026-09-01-attempt-01")
EVIDENCE = RESEARCH / "experiments/robot-capstone/RC1-2026-09-01-attempt-01"
PRODUCT_COMMIT = "0e84ef3b6f79521b4f21a9d12a180dfd9713aab4"
PRODUCT_PARENT = "b8f65c8a6935dcbe4f47a4d070e1a971dc21563b"
AUTHORIZED_PATHS = {"scripts/modules/film_studio_physical_performance.py", "scripts/startup/bl_operators/film_studio_workspace.py"}
FORBIDDEN_TOKENS = ("RC1", "B62_", "PC4_", "GUARDIAN", "d658ff", "19deab", "e4dec4")


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def self_hash(value, field):
    body = dict(value)
    body.pop(field, None)
    return hashlib.sha256(canonical(body).encode("utf-8")).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def load(name):
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))


def output(argv, cwd=None):
    return subprocess.check_output(argv, cwd=cwd, text=True).strip()


def evidence_rows(excluded):
    rows = []
    for path in sorted(EVIDENCE.rglob("*")):
        if path.is_file() and path.name not in excluded:
            rows.append({"uri": path.relative_to(EVIDENCE).as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return rows


def main():
    receipt = load("receipt.json")
    build = load("build.json")
    result = build["result"]
    physics = result["physics"]
    cinema = result["cinematography"]
    reopen = load("reopen.json")
    negative = load("negative-controls.json")
    compatibility = load("backward-compatibility.json")
    review = load("direct-visual-review.json")
    clip_video = load("clip-video.json")
    source = WORKSPACE / "source"
    binary = Path(receipt["binary"]["path"])
    installed_module = Path(receipt["installedModule"]["path"])

    changed_paths = set(output(["git", "diff", "--name-only", PRODUCT_PARENT, PRODUCT_COMMIT], source).splitlines())
    numstat = output(["git", "diff", "--numstat", PRODUCT_PARENT, PRODUCT_COMMIT], source).splitlines()
    additions = sum(int(row.split("\t")[0]) for row in numstat)
    deletions = sum(int(row.split("\t")[1]) for row in numstat)
    patch = output(["git", "diff", "--unified=0", PRODUCT_PARENT, PRODUCT_COMMIT, "--", *sorted(AUTHORIZED_PATHS)], source)
    added_product_lines = [line[1:] for line in patch.splitlines() if line.startswith("+") and not line.startswith("+++")]
    forbidden_hits = [token for token in FORBIDDEN_TOKENS if any(token in line for line in added_product_lines)]
    process_receipts = [json.loads(path.read_text(encoding="utf-8")) for path in sorted((EVIDENCE / "processes").glob("*.json"))]
    clip_frames = sorted((EVIDENCE / "clip").glob("frame-*.png"))
    stills = build["stills"]
    finite_physics = all(math.isfinite(physics[key]) for key in ("evaluatedMomentumTransferKgMPerSecond", "peakKineticEnergyJoule", "peakSpringEnergyJoule"))
    direct_answers = review.get("answers", [])

    checks = {
        "receiptPendingReviewAudit": receipt["status"] == "PASS_PENDING_DIRECT_VISUAL_AND_INDEPENDENT_AUDIT",
        "productCommitExact": output(["git", "rev-parse", "HEAD"], source) == PRODUCT_COMMIT,
        "productSourceClean": output(["git", "status", "--porcelain"], source) == "",
        "sourceScopeExact": changed_paths == AUTHORIZED_PATHS,
        "sourceSizeWithinCeiling": additions <= 900 and deletions <= 260,
        "noProjectSpecificProductBranch": not forbidden_hits,
        "binaryHashExact": sha256_file(binary) == receipt["binary"]["sha256"],
        "installedModuleHashExact": sha256_file(installed_module) == receipt["installedModule"]["sha256"] == sha256_file(source / "scripts/modules/film_studio_physical_performance.py"),
        "processCountExact": len(process_receipts) == 8 and all(row["exitCode"] == 0 for row in process_receipts),
        "cleanBuildCountExact": receipt["counts"]["cleanNativeBuilds"] == 1,
        "productStartCountExact": receipt["counts"]["productStarts"] == 3,
        "forbiddenCountersZero": all(receipt["counts"][key] == 0 for key in ("networkCalls", "engineRemoteWrites", "forcePushes", "tags", "releases", "binaryDistribution", "signing", "notarization")),
        "pc9NegativeControlsExact": negative["status"] == "PASS" and all(row["observed"] == row["expected"] and row["sceneUnchanged"] for row in negative["cases"]),
        "pc8CompatibilityExact": compatibility["status"] == "PASS" and all(compatibility["checks"].values()),
        "semanticExecutionPass": result["status"] == "PASS_EXECUTED" and build["inspection"]["status"] == "APPROVED_READY",
        "contactDerived": result["contact"]["source"].startswith("EVALUATED_CLOSEST_APPROACH") and physics["contactFrame"] <= result["contact"]["anchorFrame"],
        "physicalRosterExact": result["mechanism"]["kinematicHandColliderCount"] == 1 and result["mechanism"]["activeMechanismRigidBodyCount"] == 1 and result["mechanism"]["springConstraintCount"] == 1,
        "initialPenetrationWithinCeiling": result["mechanism"]["initialPenetrationMeters"] <= 0.001,
        "peakDisplacementWithinRange": 0.025 <= physics["peakDisplacementMeters"] <= 0.05,
        "responseWithinTwoFrames": 0 <= physics["firstResponseDelayFrames"] <= 2,
        "directionReversalMeasured": physics["directionReversalFrame"] is not None and physics["directionReversalFrame"] > physics["peakFrame"],
        "settledResidualWithinCeiling": physics["settledWindowStartFrame"] is not None and physics["settledResidualMaximumMeters"] <= 0.002,
        "mechanismPoseAuthorityZero": result["mechanism"]["postContactMechanismPoseKeyframes"] == 0 and result["mechanism"]["finalPoseSource"] == "BLENDER_BULLET_RIGID_BODY_AND_CONSTRAINT",
        "finitePhysicalReceipts": finite_physics and physics["evaluatedMomentumTransferKgMPerSecond"] > 0 and physics["peakKineticEnergyJoule"] > 0 and physics["peakSpringEnergyJoule"] > 0,
        "mediumOccupancyWithinRange": 0.48 <= cinema["medium"]["occupancy"] <= 0.72,
        "wideEnvironmentLayersVisible": cinema["wide"]["visibleEnvironmentLayerCount"] >= 3,
        "closeFacialLandmarksVisible": cinema["close"]["visibleFacialLandmarkCount"] >= 4,
        "closeFeatureDominanceWithinCeiling": cinema["close"]["largestLandmarkFaceAreaRatio"] <= 0.35,
        "nativeMeasuredMotionBlur": cinema["motionBlur"]["nativeTransformMotionBlur"] is True and cinema["motionBlur"]["compositorOrPostprocessBlur"] is False and cinema["motionBlur"]["achievedMedianBlurPixels"] > 0,
        "stillCountAndHashesExact": len(stills) == 3 and all(sha256_file(EVIDENCE / row["uri"]) == row["sha256"] for row in stills),
        "clipCountAndHashesExact": len(clip_frames) == 48 and build["clip"]["frameCount"] == 48 and all(sha256_file(EVIDENCE / row["uri"]) == row["sha256"] for row in build["clip"]["frames"]),
        "clipVideoExact": clip_video["status"] == "PASS" and sha256_file(Path(clip_video["path"])) == clip_video["sha256"] and clip_video["probe"]["streams"][0]["nb_frames"] == "48",
        "saveReopenExact": reopen["status"] == "PASS" and all(reopen["checks"].values()),
        "directVisualNineOfNine": review["status"] == "PASS" and len(direct_answers) == 9 and all(row["answer"] == "YES" for row in direct_answers),
        "resourceCeilings": receipt["resources"]["workspaceBytes"] <= 50 * 1024**3 and receipt["resources"]["evidenceBytes"] <= 512 * 1024**2 and receipt["resources"]["freeBytesAfter"] >= 100 * 1024**3,
    }
    snapshot = evidence_rows({"independent-audit.json", "root-manifest.json"})
    audit = {
        "schemaVersion": "bfs.rc1RobotCapstoneIndependentAudit.v0.1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "checkCount": len(checks),
        "passCount": sum(checks.values()),
        "sourceScope": {"paths": sorted(changed_paths), "additions": additions, "deletions": deletions, "forbiddenTokenHits": forbidden_hits},
        "evidenceSnapshotHash": hashlib.sha256(canonical(snapshot).encode("utf-8")).hexdigest(),
        "claimCeiling": "One hybrid authored-intention/Bullet-response robot holdout; not broad autonomous filmmaking or advertising-grade photorealism.",
    }
    audit["auditHash"] = self_hash(audit, "auditHash")
    write(EVIDENCE / "independent-audit.json", audit)
    manifest = {"schemaVersion": "bfs.rc1RootManifest.v0.1", "files": evidence_rows({"root-manifest.json"})}
    manifest["manifestHash"] = self_hash(manifest, "manifestHash")
    write(EVIDENCE / "root-manifest.json", manifest)
    print("RC1_AUDIT=" + canonical(audit))
    if audit["status"] != "PASS":
        raise RuntimeError("RC1 independent audit failed")


if __name__ == "__main__":
    main()
