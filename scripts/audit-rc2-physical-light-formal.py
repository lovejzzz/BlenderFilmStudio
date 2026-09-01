#!/usr/bin/env python3
"""Independently audit the RC2 formal machine evidence."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "experiments/physical-light-transfer/RC2-2026-09-01-attempt-01"
WORKSPACE = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC2-2026-09-01-attempt-01")
PREREG = ROOT / "specs/ai-native-studio-rc2-physical-light-transfer-preregistration.v0.1.json"
FIXTURE = ROOT / "specs/fixtures/physical-light/RC2_F1.rolling-sphere-hinged-shutter.physical-light-spec.v0.1.json"


def load(path): return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024): digest.update(chunk)
    return digest.hexdigest()


def canonical(value): return json.dumps(value, sort_keys=True, separators=(",", ":"))


def self_hash(value, field):
    body = dict(value); body.pop(field, None)
    return hashlib.sha256(canonical(body).encode()).hexdigest()


def main():
    receipt, build, reopen = load(EVIDENCE / "receipt.json"), load(EVIDENCE / "build.json"), load(EVIDENCE / "reopen.json")
    prereg, fixture = load(PREREG), load(FIXTURE)
    limits, result = prereg["machineAcceptance"], build["result"]
    physics, authority, mechanism = result["physics"], result["authority"], result["mechanism"]
    illumination, blur = build["illuminationCausality"], result["cinematography"]["motionBlur"]
    low, high = limits["peakShutterOpenDegreesRange"]
    processes = [load(EVIDENCE / "processes" / f"{index:02d}-{name}.json") for index, name in ((1,"local-clone"),(2,"checkout"),(3,"lfs-checkout"),(4,"clean-native-build"),(5,"pc8-pc9-regression"),(6,"physical-light-build"),(7,"physical-light-reopen"),(8,"ffmpeg"))]
    process_integrity = all(row["processHash"] == self_hash(row, "processHash") and row["exitCode"] == 0 and sha256_file(EVIDENCE / "logs" / f"{row['index']:02d}-{row['name']}.stdout.log") == row["stdoutSha256"] and sha256_file(EVIDENCE / "logs" / f"{row['index']:02d}-{row['name']}.stderr.log") == row["stderrSha256"] for row in processes)
    checks = {
        "receiptSelfHash": receipt["receiptHash"] == self_hash(receipt, "receiptHash"),
        "productCommitExact": receipt["productCommit"] == "636f42f28f781f3e858fd5b6bf641910a549c91b",
        "productParentExact": receipt["productParent"] == "0e84ef3b6f79521b4f21a9d12a180dfd9713aab4",
        "specHashExact": result["physicalLightSpecHash"] == fixture["physicalLightSpecHash"],
        "processIntegrity": process_integrity,
        "cleanNativeBuildCount": receipt["counts"]["cleanNativeBuilds"] == 1,
        "productStartCount": receipt["counts"]["productStarts"] == 3,
        "sceneMutationCount": receipt["counts"]["sceneMutatingExecutions"] == 1,
        "blendSaveCount": receipt["counts"]["blendSaves"] == 1,
        "reopenCount": receipt["counts"]["reopens"] == 1,
        "stillCount": len(build["stills"]) == limits["reviewStillCount"] == 3,
        "clipFrameCount": build["clip"]["frameCount"] == limits["contactClipFrameCount"] == 48,
        "activeRigidBodyCount": mechanism["activeRigidBodyCount"] >= limits["activeRigidBodyCountMinimum"],
        "hingeCount": mechanism["hingeConstraintCount"] == limits["hingeConstraintCountExact"],
        "actorTravel": physics["actorTravelMeters"] >= limits["actorTravelMetersMinimum"],
        "rollingSlip": physics["medianRollingSlipRatio"] <= limits["medianRollingSlipRatioMaximum"],
        "derivedContact": physics["contactFrame"] is not None,
        "responseDelay": physics["firstResponseDelayFrames"] <= limits["firstShutterResponseAfterContactMaximumFrames"],
        "peakOpening": low <= physics["peakShutterOpenDegrees"] <= high,
        "reversalOrSettled": physics["directionReversalFrame"] is not None or physics["settledWindowStartFrame"] is not None,
        "actorPoseKeysZero": authority["actorPoseKeyframesAfterRelease"] == 0,
        "shutterPoseKeysZero": authority["shutterPoseKeyframesAfterContact"] == 0,
        "lightChannelsZero": authority["lightAnimationChannels"] == 0,
        "lightPowerExact": authority["lightPowerWatts"] == fixture["illumination"]["powerWatts"] == illumination["lightEnergyWatts"],
        "actualClosedRatio": illumination["actualToClosedLuminanceRatio"] >= limits["receiverLuminanceIncreaseRatioMinimum"],
        "closedActualRatio": illumination["closedToActualLuminanceRatio"] <= limits["closedShutterCounterfactualLuminanceRatioMaximum"],
        "nativeMeasuredBlur": blur["nativeTransformMotionBlur"] and not blur["compositorOrPostprocessBlur"],
        "reopenStoredExact": reopen["checks"]["storedResultExact"] and reopen["checks"]["storedResultHashExact"],
        "reopenActorDelta": reopen["maximumActorLocationDeltaMeters"] <= limits["saveReopenActualPhysicsMaximumDeltaMeters"],
        "reopenShutterDelta": reopen["maximumShutterAngleDeltaDegrees"] <= limits["saveReopenActualShutterAngleMaximumDeltaDegrees"],
        "pc8Pc9Regression": load(EVIDENCE / "backward-compatibility.json")["status"] == "PASS",
        "pc9NegativeControls": load(EVIDENCE / "negative-controls.json")["status"] == "PASS",
        "rc1SourceRegression": load(EVIDENCE / "rc1-source-regression.json")["status"] == "PASS",
        "workspaceLimit": receipt["resources"]["workspaceBytes"] <= prereg["resourceCeilings"]["workspaceBytes"],
        "evidenceLimit": receipt["resources"]["evidenceBytes"] <= prereg["resourceCeilings"]["evidenceBytes"],
        "freeReserve": receipt["resources"]["freeBytesAfter"] >= prereg["resourceCeilings"]["minimumFreeReserveGiB"] * 1024**3,
        "forbiddenCountsZero": all(receipt["counts"][key] == 0 for key in ("networkCalls","engineRemoteWrites","forcePushes","tags","releases","binaryDistribution","signing","notarization")),
        "sourceScopeExact": receipt["sourceDiffNumstat"] == ["631\t0\tscripts/modules/film_studio_physical_light.py", "21\t5\tscripts/startup/bl_operators/film_studio_workspace.py"],
        "binaryExistsAndHash": Path(receipt["binary"]["path"]).is_file() and sha256_file(Path(receipt["binary"]["path"])) == receipt["binary"]["sha256"],
        "blendExistsAndHash": Path(build["blend"]["path"]).is_file() and sha256_file(Path(build["blend"]["path"])) == build["blend"]["sha256"],
    }
    audit = {"schemaVersion": "bfs.rc2PhysicalLightIndependentAudit.v0.1", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "checkCount": len(checks), "passCount": sum(checks.values()), "measurements": {"contactFrame": physics["contactFrame"], "peakShutterOpenDegrees": physics["peakShutterOpenDegrees"], "actorTravelMeters": physics["actorTravelMeters"], "medianRollingSlipRatio": physics["medianRollingSlipRatio"], "actualToClosedLuminanceRatio": illumination["actualToClosedLuminanceRatio"], "reopenMaximumActorLocationDeltaMeters": reopen["maximumActorLocationDeltaMeters"], "reopenMaximumShutterAngleDeltaDegrees": reopen["maximumShutterAngleDeltaDegrees"]}}
    audit["auditHash"] = self_hash(audit, "auditHash")
    (EVIDENCE / "audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": audit["status"], "checks": f"{audit['passCount']}/{audit['checkCount']}", "auditHash": audit["auditHash"]}, sort_keys=True))
    raise SystemExit(0 if audit["status"] == "PASS" else 1)


if __name__ == "__main__": main()
