#!/usr/bin/env python3
"""Evaluate an RC2 development result against the frozen machine thresholds."""

import argparse
import hashlib
import json
from pathlib import Path


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


parser = argparse.ArgumentParser()
parser.add_argument("--development", type=Path, required=True)
parser.add_argument("--reopen", type=Path, required=True)
parser.add_argument("--preregistration", type=Path, required=True)
parser.add_argument("--fixture", type=Path, required=True)
parser.add_argument("--clip", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()

development = load(args.development)
reopen = load(args.reopen)
preregistration = load(args.preregistration)
fixture = load(args.fixture)
result = development["result"]
physics = result["physics"]
authority = result["authority"]
mechanism = result["mechanism"]
illumination = development["illuminationCausality"]
cinematography = result["cinematography"]
limits = preregistration["machineAcceptance"]

peak_low, peak_high = limits["peakShutterOpenDegreesRange"]
checks = {
    "activeRigidBodyCountMinimum": mechanism["activeRigidBodyCount"] >= limits["activeRigidBodyCountMinimum"],
    "hingeConstraintCountExact": mechanism["hingeConstraintCount"] == limits["hingeConstraintCountExact"],
    "actorTravelMetersMinimum": physics["actorTravelMeters"] >= limits["actorTravelMetersMinimum"],
    "medianRollingSlipRatioMaximum": physics["medianRollingSlipRatio"] <= limits["medianRollingSlipRatioMaximum"],
    "derivedContactRequired": physics["contactFrame"] is not None,
    "firstShutterResponseAfterContactMaximumFrames": physics["firstResponseDelayFrames"] <= limits["firstShutterResponseAfterContactMaximumFrames"],
    "peakShutterOpenDegreesRange": peak_low <= physics["peakShutterOpenDegrees"] <= peak_high,
    "shutterDirectionReversalOrSettledWindowRequired": physics["directionReversalFrame"] is not None or physics["settledWindowStartFrame"] is not None,
    "actorTransformKeyframesAfterRelease": authority["actorPoseKeyframesAfterRelease"] == limits["actorTransformKeyframesAfterRelease"],
    "shutterTransformKeyframesAfterContact": authority["shutterPoseKeyframesAfterContact"] == limits["shutterTransformKeyframesAfterContact"],
    "lightPowerAndColorKeyframes": authority["lightAnimationChannels"] == limits["lightPowerAndColorKeyframes"],
    "lightPowerConstantExact": authority["lightPowerWatts"] == fixture["illumination"]["powerWatts"] == illumination["lightEnergyWatts"],
    "receiverLuminanceIncreaseRatioMinimum": illumination["actualToClosedLuminanceRatio"] >= limits["receiverLuminanceIncreaseRatioMinimum"],
    "closedShutterCounterfactualLuminanceRatioMaximum": illumination["closedToActualLuminanceRatio"] <= limits["closedShutterCounterfactualLuminanceRatioMaximum"],
    "measuredNativeMotionBlurRequired": cinematography["motionBlur"]["nativeTransformMotionBlur"] and not cinematography["motionBlur"]["compositorOrPostprocessBlur"],
    "saveReopenActualPhysicsMaximumDeltaMeters": reopen["measurements"]["maxActorLocationDeltaMeters"] <= limits["saveReopenActualPhysicsMaximumDeltaMeters"],
    "saveReopenActualShutterAngleMaximumDeltaDegrees": reopen["measurements"]["maxShutterAngleDeltaDegrees"] <= limits["saveReopenActualShutterAngleMaximumDeltaDegrees"],
    "reviewStillCount": len(development["stills"]) == limits["reviewStillCount"],
    "contactClipFrameCount": development["contactClipFrames"]["frameCount"] == limits["contactClipFrameCount"],
}
receipt = {
    "schemaVersion": "bfs.rc2PhysicalLightDevelopmentAudit.v0.1",
    "status": "PASS" if all(checks.values()) else "FAIL",
    "checkCount": len(checks),
    "passCount": sum(checks.values()),
    "checks": checks,
    "measurements": {
        "actorTravelMeters": physics["actorTravelMeters"],
        "medianRollingSlipRatio": physics["medianRollingSlipRatio"],
        "contactFrame": physics["contactFrame"],
        "firstResponseDelayFrames": physics["firstResponseDelayFrames"],
        "peakShutterOpenDegrees": physics["peakShutterOpenDegrees"],
        "settledWindowStartFrame": physics["settledWindowStartFrame"],
        "actualToClosedLuminanceRatio": illumination["actualToClosedLuminanceRatio"],
        "closedToActualLuminanceRatio": illumination["closedToActualLuminanceRatio"],
        "reopenMaxActorLocationDeltaMeters": reopen["measurements"]["maxActorLocationDeltaMeters"],
        "reopenMaxShutterAngleDeltaDegrees": reopen["measurements"]["maxShutterAngleDeltaDegrees"],
    },
    "bindings": {
        "physicalLightSpecHash": result["physicalLightSpecHash"],
        "productResultHash": result["resultHash"],
        "clip": {"path": str(args.clip), "bytes": args.clip.stat().st_size, "sha256": sha256_file(args.clip)},
    },
}
args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(receipt, indent=2, sort_keys=True))
raise SystemExit(0 if receipt["status"] == "PASS" else 1)
