#!/usr/bin/env python3
"""Independently audit the one-cell RC6 moving-liquid Preview gate."""

import hashlib
import json
import math
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-moving-liquid-preview-attempt-56")
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-preview-attempt-56"
BINARY = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC5-2026-09-01-attempt-01/build/bin/Film Studio Engine F0.app/Contents/MacOS/Blender")
SOURCE = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-final-effector-mesh-c3-attempt-46/final-effector-mesh-c3/source-state.blend")
RETAINED_CACHE = SOURCE.parent / "mantaflow-cache"
TRAJECTORY = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-slow-tip-bullet-screen-c5-c3-attempt-55/cells/C5F96/result.json"
SCENE_TOOL = RESEARCH / "scripts/run-rc6-moving-liquid-preview-scene.py"
RUNNER = RESEARCH / "scripts/run-rc6-moving-liquid-preview.py"
SPEC = RESEARCH / "specs/ai-native-studio-rc6-moving-liquid-preview.v0.66.json"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def self_hash(value, field):
    body = dict(value)
    body.pop(field, None)
    return hashlib.sha256(canonical(body).encode()).hexdigest()


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def retained_cache_manifest():
    rows = [
        {"path": str(path.relative_to(RETAINED_CACHE)), "bytes": path.stat().st_size, "sha256": sha(path)}
        for path in sorted(RETAINED_CACHE.rglob("*"))
        if path.is_file()
    ]
    value = {"root": str(RETAINED_CACHE), "files": rows}
    return self_hash(value, "manifestHash")


spec = json.loads(SPEC.read_text())
result = json.loads((EVIDENCE / "result.json").read_text())
receipt = json.loads((EVIDENCE / "receipt.json").read_text())
admission = json.loads((EVIDENCE / "admission.json").read_text())
process = json.loads((EVIDENCE / "processes/01-moving-liquid-preview.json").read_text())
trajectory = json.loads(TRAJECTORY.read_text())
stdout = EVIDENCE / "logs/01-moving-liquid-preview.stdout.log"
stderr = EVIDENCE / "logs/01-moving-liquid-preview.stderr.log"
fluid = result["fluidSamples"]
bullet = result["bulletSamples"]
source_volume = result["configuration"]["sourceMeshVolumeCubicMeters"]
initial_volume = fluid[0]["meshVolumeCubicMeters"]
maximum_source_error = max(abs(row["meshVolumeCubicMeters"] / source_volume - 1.0) for row in fluid)
maximum_temporal_drift = max(abs(row["meshVolumeCubicMeters"] / initial_volume - 1.0) for row in fluid)
initial_centroid = fluid[0]["centroidCupLocalMeters"]
maximum_centroid_shift = max(math.dist(row["centroidCupLocalMeters"], initial_centroid) for row in fluid)
expected_trajectory = {row["frame"]: row for row in trajectory["samples"] if 1 <= row["frame"] <= 24}
maximum_location_delta = max(math.dist(row["cupLocation"], expected_trajectory[row["frame"]]["cupLocation"]) for row in bullet)
def quat_angle_degrees(first, second):
    dot = abs(sum(a * b for a, b in zip(first, second)))
    return math.degrees(2.0 * math.acos(max(-1.0, min(1.0, dot))))
maximum_rotation_delta = max(quat_angle_degrees(row["cupRotationQuaternion"], expected_trajectory[row["frame"]]["cupRotationQuaternion"]) for row in bullet)
cache_root = WORK / "mantaflow-cache"
actual_cache_files = sorted(str(path.relative_to(cache_root)) for path in cache_root.rglob("*") if path.is_file())
expected_cache_files = sorted(
    [f"config/config_{frame:04d}.uni" for frame in range(1, 25)]
    + [f"data/fluid_data_{frame:04d}.vdb" for frame in range(1, 25)]
    + [f"mesh/fluid_mesh_{frame:04d}.bobj.gz" for frame in range(1, 25)]
)
recomputed_checks = {
    "exactAcceptedC5F96Trajectory": maximum_location_delta <= 1e-5 and maximum_rotation_delta <= 1e-4,
    "solverOwnedCupMotionPresent": bullet[-1]["cupTiltDegrees"] >= 14.0,
    "hingeAndMotorExact": result["checks"]["hingeAndMotorExact"],
    "hingePivotStable": max(row["hingePivotDriftMeters"] for row in bullet) <= 0.005,
    "exactCacheFrameRoster": actual_cache_files == expected_cache_files == result["cache"]["files"],
    "liquidMeshEveryFrame": len(fluid) == 24 and all(row["vertexCount"] > 0 for row in fluid),
    "sourceRelativeVolumeWithin25Percent": maximum_source_error <= 0.25,
    "temporalVolumeDriftWithin15Percent": maximum_temporal_drift <= 0.15,
    "onePositiveLiquidBody": min(row["positiveBodyCount"] for row in fluid) == 1 and max(row["positiveBodyCount"] for row in fluid) == 1,
    "manifoldEveryFrame": max(row["nonManifoldEdgeCount"] for row in fluid) == 0,
    "largestComponentAtLeastHalf": min(row["largestComponentFraction"] for row in fluid) >= 0.5,
    "containedWithinCupPlusOneVoxel": max(row["outsideCupInteriorPlusOneVoxelFraction"] for row in fluid) <= 0.05,
    "belowFloorWithinOnePercent": max(row["belowFloorFraction"] for row in fluid) <= 0.01,
    "movingLiquidRelativeToCup": maximum_centroid_shift >= 0.002,
    "singleInitialGeometryFlow": result["checks"]["singleInitialGeometryFlow"],
    "zeroOutcomePoseAuthority": result["checks"]["zeroOutcomePoseAuthority"],
    "previewTierExact": result["configuration"]["resolutionMax"] == 96 and result["configuration"]["frameEnd"] == 24 and abs(result["configuration"]["particleRadius"] - 1.6) <= 1e-8 and abs(result["configuration"]["meshParticleRadius"] - 2.5) <= 1e-8 and result["configuration"]["cupEffectorSubframes"] == 1,
}
tools = {row["uri"]: row["sha256"] for row in spec["tools"]}
logs = list((EVIDENCE / "logs").glob("*.log"))
allowed_blend = WORK / "source-state-copy.blend"
banned = {".png", ".jpg", ".jpeg", ".exr", ".mov", ".mp4"}
checks = {
    "specSelfHash": spec["specHash"] == self_hash(spec, "specHash"),
    "frozenToolIdentities": tools == {str(SCENE_TOOL.relative_to(RESEARCH)): sha(SCENE_TOOL), str(RUNNER.relative_to(RESEARCH)): sha(RUNNER), str(Path(__file__).resolve().relative_to(RESEARCH)): sha(Path(__file__).resolve())},
    "binarySourceTrajectoryExact": sha(BINARY) == spec["baseline"]["binarySha256"] and sha(SOURCE) == spec["baseline"]["sourceBlendSha256"] and sha(TRAJECTORY) == spec["baseline"]["trajectoryFileSha256"],
    "admissionExact": admission["status"] == "PASS" and admission["workRootAbsentBeforeRun"] and admission["evidenceRootAbsentBeforeRun"],
    "resultSelfHash": result["resultHash"] == self_hash(result, "resultHash"),
    "receiptSelfHash": receipt["receiptHash"] == self_hash(receipt, "receiptHash") and receipt["resultHash"] == result["resultHash"],
    "processSelfHashAndStatus": process["processHash"] == self_hash(process, "processHash") and process["exitCode"] == (0 if result["status"] == "PASS" else 1),
    "logsBound": process["stdoutSha256"] == sha(stdout) and process["stderrSha256"] == sha(stderr) and len(logs) >= 2,
    "physicalChecksIndependentlyRecomputed": recomputed_checks == result["checks"],
    "metricsIndependentlyRecomputed": abs(result["metrics"]["maximumAbsoluteSourceVolumeErrorFraction"] - maximum_source_error) <= 1e-8 and abs(result["metrics"]["maximumAbsoluteTemporalVolumeDriftFraction"] - maximum_temporal_drift) <= 1e-8 and abs(result["metrics"]["maximumLiquidCentroidShiftCupLocalMeters"] - maximum_centroid_shift) <= 1e-8,
    "verdictRecomputed": result["status"] == ("PASS" if all(recomputed_checks.values()) else "FAIL") and receipt["status"] == result["status"],
    "retainedStaticCacheExact": retained_cache_manifest() == receipt["retainedStaticCacheManifestBefore"] == receipt["retainedStaticCacheManifestAfter"] == "53bc19e1532b64ea8c37b0cc5fa52347c72c73023728d3705d45c063d5b7c265",
    "cacheRosterExact": actual_cache_files == expected_cache_files and len(actual_cache_files) == 72,
    "sourceCopyExactOnlyBlend": sha(allowed_blend) == spec["baseline"]["sourceBlendSha256"] and [path for path in WORK.rglob("*.blend")] == [allowed_blend],
    "zeroRenderSaveNetwork": result["counts"] == {"blenderStarts": 1, "bulletBakes": 1, "fluidDataBakes": 1, "fluidMeshBakes": 1, "renders": 0, "blendSaves": 0, "networkCalls": 0, "engineRemoteWrites": 0},
    "noRenderArtifacts": not any(path.suffix.lower() in banned for root in (WORK, EVIDENCE) for path in root.rglob("*")),
    "noSymlinks": not any(path.is_symlink() for root in (WORK, EVIDENCE) for path in root.rglob("*")),
    "rootsBelowCeiling": sum(path.stat().st_size for path in WORK.rglob("*") if path.is_file()) < 2147483648 and sum(path.stat().st_size for path in EVIDENCE.rglob("*") if path.is_file()) < 67108864,
}
audit = {
    "schemaVersion": "bfs.rc6MovingLiquidPreviewIndependentAudit.v0.1",
    "status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "checkCount": len(checks),
    "passCount": sum(checks.values()),
    "resultHash": result["resultHash"],
    "receiptHash": receipt["receiptHash"],
}
audit["auditHash"] = self_hash(audit, "auditHash")
with (EVIDENCE / "independent-audit.json").open("x", encoding="utf-8") as handle:
    json.dump(audit, handle, indent=2, sort_keys=True)
    handle.write("\n")
print("RC6_MOVING_LIQUID_PREVIEW_AUDIT=" + canonical(audit))
if audit["status"] != "PASS":
    raise RuntimeError("moving-liquid Preview independent audit failed")
