#!/usr/bin/env python3
"""Independently audit the RC3 attempt-03 zero-render development evidence."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "experiments/physics-native-action/RC3-2026-09-01-development-attempt-03"
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC3-development-attempt-03")
PRODUCT = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC1-development/source")
MODULE = PRODUCT / "scripts/modules/film_studio_physics_action.py"
OPERATOR = PRODUCT / "scripts/startup/bl_operators/film_studio_workspace.py"


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
    d1, h1 = load(EVIDENCE / "D1-build.json"), load(EVIDENCE / "H1-build.json")
    d1_reopen, h1_reopen = load(EVIDENCE / "D1-reopen.json"), load(EVIDENCE / "H1-reopen.json")
    negative = load(EVIDENCE / "negative-controls.json")
    process_names = ((1, "d1-build"), (2, "d1-reopen"), (3, "h1-build"), (4, "h1-reopen"), (5, "negative-controls"))
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
    module_text = MODULE.read_text(encoding="utf-8")
    prohibited = ("RC3-D1", "RC3-H1", "SIGNAL-GATE-GRAPH", "BALL-THREE-BOTTLES", "0d03778492f9", "7adfb3e8223f", "projectId ==")
    render_like = [str(path) for path in WORK.rglob("*") if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".exr", ".mov", ".mp4"}]
    checks = {
        "receiptSelfHash": receipt["receiptHash"] == self_hash(receipt, "receiptHash"),
        "receiptPass": receipt["status"] == "PASS" and len(receipt["checks"]) == 11 and all(receipt["checks"].values()),
        "processIntegrity": process_integrity,
        "productModuleExact": sha(MODULE) == receipt["productSource"]["moduleSha256"] == "6135a3c0582dcc81e4781af7836567bf90c801000911b881ca4c0b4ec2d625ee",
        "productOperatorExact": sha(OPERATOR) == receipt["productSource"]["operatorSha256"] == "37ee599a287a2938d0fb5d8f0dfecb49ce258c3349bf48cb6e319401fc84f2ce",
        "sourceIdentityBranchesAbsent": all(token not in module_text for token in prohibited),
        "sameCompilerContract": dr["contractVersion"] == hr["contractVersion"] == "bfs.filmStudioPhysicsAction.v0.1",
        "differentGraphTopologies": dr["compiledGraphHash"] != hr["compiledGraphHash"] and dr["topology"] == "HINGE_LIGHT" and hr["topology"] == "GROUP_RESPONSE",
        "d1Mechanism": dr["mechanism"]["activeRigidBodyCount"] == 2 and dr["mechanism"]["rigidBodyConstraintCount"] == 1,
        "d1Physics": dp["contactFrame"] == dp["firstShutterResponseFrame"] == 52 and dp["firstResponseDelayFrames"] == 0 and dp["actorTravelMeters"] >= 1.5 and dp["medianRollingSlipRatio"] <= .3 and 35 <= dp["peakShutterOpenDegrees"] <= 105,
        "h1Mechanism": hr["mechanism"]["activeRigidBodyCount"] == 4 and hr["mechanism"]["rigidBodyConstraintCount"] == 0,
        "h1Physics": hp["contactFrame"] == hp["firstResponseFrame"] == 16 and hp["firstResponseDelayFrames"] == 0 and hp["respondingTargetCount"] >= 2 and hp["continuousActorMotionThroughContact"],
        "solverAuthority": all(row["authority"]["postReleaseTransformKeyframes"] == row["authority"]["authoredOutcomeFields"] == row["authority"]["authoredContactResponsePeakOrFinalFrames"] == row["authority"]["lightAnimationChannels"] == 0 for row in (dr, hr)),
        "measuredNativeBlur": all(row["cinematography"]["motionBlur"]["nativeTransformMotionBlur"] and not row["cinematography"]["motionBlur"]["compositorOrPostprocessBlur"] for row in (dr, hr)),
        "reopenExact": d1_reopen["status"] == h1_reopen["status"] == "PASS" and d1_reopen["maximumActorLocationDeltaMeters"] <= 1e-6 and h1_reopen["maximumActorLocationDeltaMeters"] <= 1e-6 and h1_reopen["maximumTargetTiltDeltaDegrees"] <= .001,
        "negativeControls": negative["status"] == "PASS" and negative["caseCount"] == negative["passCount"] == 16 and all(row["passed"] for row in negative["cases"]),
        "zeroRenderArtifacts": receipt["counts"]["renders"] == 0 and not render_like,
        "operationCounts": receipt["counts"] == {"acceptedBinaryStarts": 5, "blendSaves": 2, "engineRemoteWrites": 0, "networkCalls": 0, "renders": 0, "reopens": 2, "sceneMutatingExecutions": 2},
        "resourceCeilings": tree_bytes(WORK) <= 2 * 1024**3 and tree_bytes(EVIDENCE) <= 64 * 1024**2 and receipt["resources"]["freeBytesAfter"] >= 100 * 1024**3,
        "retainedAttemptsPresent": all((ROOT / f"experiments/physics-native-action/RC3-2026-09-01-development-attempt-{index}/failure.json").is_file() for index in ("01", "02")),
        "blendArtifactsExact": all(Path(row["blend"]["path"]).is_file() and sha(Path(row["blend"]["path"])) == row["blend"]["sha256"] for row in (d1, h1)),
    }
    audit = {
        "schemaVersion": "bfs.rc3PhysicsActionDevelopmentIndependentAudit.v0.1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "checkCount": len(checks),
        "passCount": sum(checks.values()),
        "measurements": {
            "d1ContactFrame": dp["contactFrame"],
            "d1PeakShutterOpenDegrees": dp["peakShutterOpenDegrees"],
            "h1ContactFrame": hp["contactFrame"],
            "h1RespondingTargetCount": hp["respondingTargetCount"],
            "h1FinalTiltDegrees": hp["finalTiltDegrees"],
            "d1ReopenLocationDeltaMeters": d1_reopen["maximumActorLocationDeltaMeters"],
            "h1ReopenLocationDeltaMeters": h1_reopen["maximumActorLocationDeltaMeters"],
            "h1ReopenTiltDeltaDegrees": h1_reopen["maximumTargetTiltDeltaDegrees"],
        },
    }
    audit["auditHash"] = self_hash(audit, "auditHash")
    (EVIDENCE / "audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": audit["status"], "checks": f"{audit['passCount']}/{audit['checkCount']}", "auditHash": audit["auditHash"]}, sort_keys=True))
    raise SystemExit(0 if audit["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
