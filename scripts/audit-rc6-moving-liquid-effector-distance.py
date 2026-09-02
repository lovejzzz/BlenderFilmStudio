#!/usr/bin/env python3
"""Independently audit the attempt-59 2.0-cell moving-liquid test."""

import hashlib
import json
import math
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-moving-liquid-effector-distance-attempt-59")
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-effector-distance-attempt-59"
SOURCE = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-final-effector-mesh-c3-attempt-46/final-effector-mesh-c3/source-state.blend")
STATIC_CACHE = SOURCE.parent / "mantaflow-cache"
TRAJECTORY = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-slow-tip-bullet-screen-c5-c3-attempt-55/cells/C5F96/result.json"
ATTEMPT56 = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-preview-attempt-56/result.json"
ATTEMPT57_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-data-diagnostic-attempt-57/independent-audit.json"
ATTEMPT58_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-data-occupancy-attempt-58/independent-audit.json"
SCENE_TOOL = RESEARCH / "scripts/run-rc6-moving-liquid-effector-distance-scene.py"
RUNNER = RESEARCH / "scripts/run-rc6-moving-liquid-effector-distance.py"
SPEC = RESEARCH / "specs/ai-native-studio-rc6-moving-liquid-effector-distance.v0.70.json"


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


def manifest(root):
    rows = [{"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": sha(path)} for path in sorted(root.rglob("*")) if path.is_file()]
    value = {"root": str(root), "files": rows}
    value["manifestHash"] = self_hash(value, "manifestHash")
    return value


spec = json.loads(SPEC.read_text())
result = json.loads((EVIDENCE / "result.json").read_text())
receipt = json.loads((EVIDENCE / "receipt.json").read_text())
process = json.loads((EVIDENCE / "processes/01-effector-distance.json").read_text())
admission = json.loads((EVIDENCE / "admission.json").read_text())
trajectory = json.loads(TRAJECTORY.read_text())
fluid = result["fluidSamples"]
bullet = result["bulletSamples"]
source_volume = result["configuration"]["sourceMeshVolumeCubicMeters"]
initial_volume = fluid[0]["meshVolumeCubicMeters"]
source_error = max(abs(row["meshVolumeCubicMeters"] / source_volume - 1.0) for row in fluid)
temporal_drift = max(abs(row["meshVolumeCubicMeters"] / initial_volume - 1.0) for row in fluid)
centroid_shift = max(math.dist(row["centroidCupLocalMeters"], fluid[0]["centroidCupLocalMeters"]) for row in fluid)
expected = {row["frame"]: row for row in trajectory["samples"] if 1 <= row["frame"] <= 24}
location_delta = max(math.dist(row["cupLocation"], expected[row["frame"]]["cupLocation"]) for row in bullet)
cache = WORK / "mantaflow-cache"
cache_files = sorted(str(path.relative_to(cache)) for path in cache.rglob("*") if path.is_file())
expected_cache = sorted([f"config/config_{frame:04d}.uni" for frame in range(1, 25)] + [f"data/fluid_data_{frame:04d}.vdb" for frame in range(1, 25)] + [f"mesh/fluid_mesh_{frame:04d}.bobj.gz" for frame in range(1, 25)])
recomputed_checks = {
    "exactAcceptedC5F96Trajectory": location_delta <= 1e-5 and max(row["acceptedRotationDeltaDegrees"] for row in bullet) <= 1e-4,
    "solverOwnedCupMotionPresent": bullet[-1]["cupTiltDegrees"] >= 14.0,
    "hingeAndMotorExact": result["checks"]["hingeAndMotorExact"],
    "hingePivotStable": max(row["hingePivotDriftMeters"] for row in bullet) <= 0.005,
    "exactCacheFrameRoster": cache_files == expected_cache,
    "liquidMeshEveryFrame": len(fluid) == 24 and all(row["vertexCount"] > 0 for row in fluid),
    "sourceRelativeVolumeWithin25Percent": source_error <= 0.25,
    "temporalVolumeDriftWithin15Percent": temporal_drift <= 0.15,
    "onePositiveLiquidBody": {row["positiveBodyCount"] for row in fluid} == {1},
    "manifoldEveryFrame": max(row["nonManifoldEdgeCount"] for row in fluid) == 0,
    "largestComponentAtLeastHalf": min(row["largestComponentFraction"] for row in fluid) >= 0.5,
    "containedWithinCupPlusOneVoxel": max(row["outsideCupInteriorPlusOneVoxelFraction"] for row in fluid) <= 0.05,
    "belowFloorWithinOnePercent": max(row["belowFloorFraction"] for row in fluid) <= 0.01,
    "movingLiquidRelativeToCup": centroid_shift >= 0.002,
    "singleInitialGeometryFlow": result["checks"]["singleInitialGeometryFlow"],
    "zeroOutcomePoseAuthority": result["checks"]["zeroOutcomePoseAuthority"],
    "previewTierExact": result["configuration"]["resolutionMax"] == 96 and result["configuration"]["frameEnd"] == 24 and abs(result["configuration"]["particleRadius"] - 1.6) <= 1e-6 and abs(result["configuration"]["meshParticleRadius"] - 2.5) <= 1e-6 and abs(result["configuration"]["cupEffectorSurfaceDistanceCells"] - 2.0) <= 1e-6 and result["configuration"]["cupEffectorSubframes"] == 1,
}
tools = {row["uri"]: row["sha256"] for row in spec["tools"]}
stdout = EVIDENCE / "logs/01-effector-distance.stdout.log"
stderr = EVIDENCE / "logs/01-effector-distance.stderr.log"
source_copy = WORK / "source-state-copy.blend"
checks = {
    "specSelfHash": spec["specHash"] == self_hash(spec, "specHash"),
    "frozenToolIdentities": tools == {str(SCENE_TOOL.relative_to(RESEARCH)): sha(SCENE_TOOL), str(RUNNER.relative_to(RESEARCH)): sha(RUNNER), str(Path(__file__).resolve().relative_to(RESEARCH)): sha(Path(__file__).resolve())},
    "baselineFilesExact": sha(SOURCE) == spec["baseline"]["sourceBlendSha256"] and sha(TRAJECTORY) == spec["baseline"]["trajectoryFileSha256"] and sha(ATTEMPT56) == spec["baseline"]["attempt56ResultFileSha256"] and sha(ATTEMPT57_AUDIT) == spec["baseline"]["attempt57AuditFileSha256"] and sha(ATTEMPT58_AUDIT) == spec["baseline"]["attempt58AuditFileSha256"],
    "admissionExact": admission["status"] == "PASS" and admission["workRootAbsentBeforeRun"] and admission["evidenceRootAbsentBeforeRun"],
    "resultSelfHash": result["resultHash"] == self_hash(result, "resultHash"),
    "receiptSelfHash": receipt["receiptHash"] == self_hash(receipt, "receiptHash") and receipt["resultHash"] == result["resultHash"],
    "processSelfHashAndLogs": process["processHash"] == self_hash(process, "processHash") and process["exitCode"] == 0 and process["stdoutSha256"] == sha(stdout) and process["stderrSha256"] == sha(stderr),
    "allPhysicalChecksRecomputed": recomputed_checks == result["checks"],
    "metricsRecomputed": abs(result["metrics"]["maximumAbsoluteSourceVolumeErrorFraction"] - source_error) <= 1e-8 and abs(result["metrics"]["maximumAbsoluteTemporalVolumeDriftFraction"] - temporal_drift) <= 1e-8 and abs(result["metrics"]["maximumLiquidCentroidShiftCupLocalMeters"] - centroid_shift) <= 1e-8,
    "verdictRecomputed": result["status"] == ("PASS" if all(recomputed_checks.values()) else "FAIL") and receipt["status"] == result["status"],
    "exact72FileCache": cache_files == expected_cache and len(cache_files) == 72,
    "retainedStaticCacheExact": manifest(STATIC_CACHE)["manifestHash"] == receipt["retainedStaticCacheManifestBefore"] == receipt["retainedStaticCacheManifestAfter"] == spec["baseline"]["retainedStaticCacheManifestHash"],
    "sourceCopyOnlyBlend": sha(source_copy) == spec["baseline"]["sourceBlendSha256"] and [path for path in WORK.rglob("*.blend")] == [source_copy],
    "zeroRenderSaveNetwork": result["counts"] == {"blenderStarts": 1, "bulletBakes": 1, "fluidDataBakes": 1, "fluidMeshBakes": 1, "renders": 0, "blendSaves": 0, "networkCalls": 0, "engineRemoteWrites": 0},
    "noMediaOrSymlinks": not any(path.is_symlink() or path.suffix.lower() in {".png", ".jpg", ".jpeg", ".exr", ".mov", ".mp4"} for root in (WORK, EVIDENCE) for path in root.rglob("*")),
    "rootsBelowCeilings": sum(path.stat().st_size for path in WORK.rglob("*") if path.is_file()) < spec["resourceCeilings"]["maximumWorkspaceBytes"] and sum(path.stat().st_size for path in EVIDENCE.rglob("*") if path.is_file()) < spec["resourceCeilings"]["maximumEvidenceBytes"],
}
audit = {"schemaVersion": "bfs.rc6MovingLiquidEffectorDistanceIndependentAudit.v0.1", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "checkCount": len(checks), "passCount": sum(checks.values()), "physicalStatus": result["status"], "resultHash": result["resultHash"], "receiptHash": receipt["receiptHash"]}
audit["auditHash"] = self_hash(audit, "auditHash")
with (EVIDENCE / "independent-audit.json").open("x", encoding="utf-8") as handle:
    json.dump(audit, handle, indent=2, sort_keys=True)
    handle.write("\n")
print("RC6_MOVING_LIQUID_EFFECTOR_DISTANCE_AUDIT=" + canonical(audit))
if audit["status"] != "PASS":
    raise RuntimeError("moving-liquid effector-distance independent audit failed")
