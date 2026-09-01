#!/usr/bin/env python3
"""Independently audit the RC3 clean-build formal evidence."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "experiments/physics-native-action/RC3-2026-09-01-attempt-01"
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC3-2026-09-01-attempt-01")
VISUAL = ROOT / "experiments/physics-native-action/RC3-2026-09-01-visual-attempt-01"
PREREG = ROOT / "specs/ai-native-studio-rc3-physics-native-action-grammar-preregistration.v0.2.json"
FREEZE = ROOT / "specs/ai-native-studio-rc3-physics-action-formal-tool-freeze.v0.1.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
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
    return hashlib.sha256(canonical(body).encode()).hexdigest()


def tree_bytes(root):
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file() and not path.is_symlink())


def main():
    receipt = load(EVIDENCE / "receipt.json")
    admission = load(EVIDENCE / "admission.json")
    route_regression = load(EVIDENCE / "installed-route-regression.json")
    d1, h1 = load(EVIDENCE / "D1-build.json"), load(EVIDENCE / "H1-build.json")
    d1_reopen, h1_reopen = load(EVIDENCE / "D1-reopen.json"), load(EVIDENCE / "H1-reopen.json")
    negative = load(EVIDENCE / "negative-controls.json")
    render = load(EVIDENCE / "render.json")
    visual_receipt = load(VISUAL / "receipt.json")
    visual_review = load(VISUAL / "direct-visual-review.json")
    prereg, freeze = load(PREREG), load(FREEZE)
    process_names = (
        (1, "local-clone"), (2, "checkout"), (3, "lfs-checkout"), (4, "clean-native-build"),
        (5, "d1-build"), (6, "d1-reopen"), (7, "h1-build"), (8, "h1-reopen"),
        (9, "negative-controls"), (10, "render-both-cases"), (11, "d1-video"),
        (12, "d1-sheet"), (13, "h1-video"), (14, "h1-sheet"),
    )
    processes = [load(EVIDENCE / "processes" / f"{index:02d}-{name}.json") for index, name in process_names]
    process_integrity = all(
        row["processHash"] == self_hash(row, "processHash")
        and row["exitCode"] == 0
        and sha(EVIDENCE / "logs" / f"{row['index']:02d}-{row['name']}.stdout.log") == row["stdoutSha256"]
        and sha(EVIDENCE / "logs" / f"{row['index']:02d}-{row['name']}.stderr.log") == row["stderrSha256"]
        for row in processes
    )
    dr, hr = d1["result"], h1["result"]
    dp, hp = dr["physics"], hr["physics"]
    formal_media = {row["case"]: row for row in receipt["render"]["media"]}
    accepted_media = {row["case"]: row for row in visual_receipt["media"]}
    media_exact = all(
        formal_media[case][kind]["sha256"] == accepted_media[case][kind]["sha256"]
        for case in ("D1", "H1") for kind in ("video", "contactSheet")
    )
    formal_stills = {
        case["case"]: {row["role"]: row["sha256"] for row in case["stills"]}
        for case in render["cases"]
    }
    accepted_stills = {
        "D1": {
            "cause": visual_review["artifacts"]["D1"]["causeStillSha256"],
            "contact": visual_review["artifacts"]["D1"]["contactStillSha256"],
            "effect": visual_review["artifacts"]["D1"]["effectStillSha256"],
        },
        "H1": {
            "cause": visual_review["artifacts"]["H1"]["causeStillSha256"],
            "contact": visual_review["artifacts"]["H1"]["contactStillSha256"],
            "effect": visual_review["artifacts"]["H1"]["effectStillSha256"],
        },
    }
    source = WORK / "source"
    module = source / "scripts/modules/film_studio_physics_action.py"
    operator = source / "scripts/startup/bl_operators/film_studio_workspace.py"
    prohibited = ("RC3-D1", "RC3-H1", "SIGNAL-GATE-GRAPH", "BALL-THREE-BOTTLES", "0d03778492f9", "7adfb3e8223f", "projectId ==")
    checks = {
        "receiptSelfHash": receipt["receiptHash"] == self_hash(receipt, "receiptHash"),
        "receiptMachinePass": receipt["status"] == "PASS_PENDING_INDEPENDENT_AUDIT_AND_VISUAL_BINDING" and all(receipt["checks"].values()),
        "admissionSelfHash": admission["status"] == "PASS" and admission["admissionHash"] == self_hash(admission, "admissionHash"),
        "admissionThreshold": admission["freeBytesBefore"] >= 160 * 1024**3,
        "processIntegrity": process_integrity,
        "toolFreezeSelfHash": freeze["freezeHash"] == self_hash(freeze, "freezeHash"),
        "toolFreezeBindings": all(sha(ROOT / row["uri"]) == row["sha256"] for row in freeze["tools"]),
        "productCommit": receipt["product"]["commit"] == "5f595fe3aca7118847aec5b572f6d90a377a4352",
        "productParent": receipt["product"]["parent"] == "636f42f28f781f3e858fd5b6bf641910a549c91b",
        "sourceScope": receipt["product"]["sourceDiffNumstat"] == ["857\t0\tscripts/modules/film_studio_physics_action.py", "24\t5\tscripts/startup/bl_operators/film_studio_workspace.py"],
        "sourceModuleExact": sha(module) == "6135a3c0582dcc81e4781af7836567bf90c801000911b881ca4c0b4ec2d625ee",
        "sourceOperatorExact": sha(operator) == "37ee599a287a2938d0fb5d8f0dfecb49ce258c3349bf48cb6e319401fc84f2ce",
        "identityBranchesAbsent": all(token not in module.read_text(encoding="utf-8") for token in prohibited),
        "installedRouteRegression": route_regression["status"] == "PASS" and all(route_regression["operatorRoutes"].values()),
        "sameCompilerContract": dr["contractVersion"] == hr["contractVersion"] == "bfs.filmStudioPhysicsAction.v0.1",
        "differentGraphs": dr["compiledGraphHash"] != hr["compiledGraphHash"] and dr["topology"] == "HINGE_LIGHT" and hr["topology"] == "GROUP_RESPONSE",
        "d1Mechanism": dr["mechanism"]["activeRigidBodyCount"] == 2 and dr["mechanism"]["rigidBodyConstraintCount"] == 1,
        "d1Physics": dp["contactFrame"] == dp["firstShutterResponseFrame"] == 52 and dp["firstResponseDelayFrames"] == 0 and dp["actorTravelMeters"] >= 1.5 and dp["medianRollingSlipRatio"] <= 0.3 and 35 <= dp["peakShutterOpenDegrees"] <= 105,
        "h1Mechanism": hr["mechanism"]["activeRigidBodyCount"] == 4 and hr["mechanism"]["rigidBodyConstraintCount"] == 0,
        "h1Physics": hp["contactFrame"] == hp["firstResponseFrame"] == 16 and hp["firstResponseDelayFrames"] == 0 and hp["respondingTargetCount"] >= 2 and hp["continuousActorMotionThroughContact"],
        "solverAuthority": all(row["authority"]["postReleaseTransformKeyframes"] == row["authority"]["authoredOutcomeFields"] == row["authority"]["authoredContactResponsePeakOrFinalFrames"] == row["authority"]["lightAnimationChannels"] == 0 for row in (dr, hr)),
        "measuredNativeBlur": all(row["cinematography"]["motionBlur"]["nativeTransformMotionBlur"] and not row["cinematography"]["motionBlur"]["compositorOrPostprocessBlur"] for row in (dr, hr)),
        "reopenExact": d1_reopen["status"] == h1_reopen["status"] == "PASS" and d1_reopen["maximumActorLocationDeltaMeters"] <= 1e-6 and h1_reopen["maximumActorLocationDeltaMeters"] <= 1e-6 and h1_reopen["maximumTargetTiltDeltaDegrees"] <= 0.001,
        "negativeControls": negative["status"] == "PASS" and negative["caseCount"] == negative["passCount"] == 16 and all(row["passed"] for row in negative["cases"]),
        "renderCounts": render["counts"] == {"blendSaves": 0, "clipFrames": 96, "networkCalls": 0, "productStarts": 1, "reviewStills": 6, "sceneMutations": 0},
        "formalMediaExactToReviewed": media_exact and formal_stills == accepted_stills,
        "acceptedVisualReview": visual_review["status"] == "PASS" and visual_review["answerCounts"] == {"YES": 10, "NO": 0} and visual_review["reviewHash"] == self_hash(visual_review, "reviewHash"),
        "blendArtifactsExact": all(Path(row["blend"]["path"]).is_file() and sha(Path(row["blend"]["path"])) == row["blend"]["sha256"] for row in (d1, h1)),
        "operationCounts": receipt["counts"] == {"binaryDistribution": 0, "blendSaves": 2, "cleanNativeBuilds": 1, "contactClipFrameRenders": 96, "engineRemoteWrites": 0, "ffmpegProcesses": 4, "forcePushes": 0, "negativeControlRuns": 16, "networkCalls": 0, "notarization": 0, "productStarts": 6, "releases": 0, "reopens": 2, "reviewStillRenders": 6, "sceneMutatingExecutions": 2, "signing": 0, "tags": 0},
        "resourceCeilings": tree_bytes(WORK) <= prereg["resourceCeilings"]["workspaceBytes"] and tree_bytes(EVIDENCE) <= prereg["resourceCeilings"]["evidenceBytes"] and receipt["resources"]["freeBytesAfter"] >= prereg["resourceCeilings"]["minimumFreeReserveGiB"] * 1024**3,
    }
    audit = {
        "schemaVersion": "bfs.rc3PhysicsActionFormalIndependentAudit.v0.1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "checkCount": len(checks),
        "passCount": sum(checks.values()),
        "measurements": {
            "binarySha256": receipt["binary"]["sha256"],
            "d1ContactFrame": dp["contactFrame"],
            "d1PeakShutterOpenDegrees": dp["peakShutterOpenDegrees"],
            "h1ContactFrame": hp["contactFrame"],
            "h1RespondingTargetCount": hp["respondingTargetCount"],
            "h1FinalTiltDegrees": hp["finalTiltDegrees"],
            "formalMediaExactToReviewed": media_exact and formal_stills == accepted_stills,
        },
    }
    audit["auditHash"] = self_hash(audit, "auditHash")
    (EVIDENCE / "audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": audit["status"], "checks": f"{audit['passCount']}/{audit['checkCount']}", "auditHash": audit["auditHash"]}, sort_keys=True))
    raise SystemExit(0 if audit["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
