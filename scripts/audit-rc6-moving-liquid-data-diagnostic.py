#!/usr/bin/env python3
"""Independently audit the attempt-57 Data-only FLIP-particle diagnosis."""

import hashlib
import json
import math
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-moving-liquid-data-diagnostic-attempt-57")
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-data-diagnostic-attempt-57"
SOURCE = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-final-effector-mesh-c3-attempt-46/final-effector-mesh-c3/source-state.blend")
TRAJECTORY = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-slow-tip-bullet-screen-c5-c3-attempt-55/cells/C5F96/result.json"
RETAINED56_WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-moving-liquid-preview-attempt-56")
RETAINED56_EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-preview-attempt-56"
SCENE_TOOL = RESEARCH / "scripts/run-rc6-moving-liquid-data-diagnostic-scene.py"
RUNNER = RESEARCH / "scripts/run-rc6-moving-liquid-data-diagnostic.py"
SPEC = RESEARCH / "specs/ai-native-studio-rc6-moving-liquid-data-diagnostic.v0.68.json"


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
    rows = [
        {"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": sha(path)}
        for path in sorted(root.rglob("*"))
        if path.is_file()
    ]
    value = {"root": str(root), "files": rows}
    value["manifestHash"] = self_hash(value, "manifestHash")
    return value


spec = json.loads(SPEC.read_text())
result = json.loads((EVIDENCE / "result.json").read_text())
receipt = json.loads((EVIDENCE / "receipt.json").read_text())
process = json.loads((EVIDENCE / "processes/01-moving-liquid-data-diagnostic.json").read_text())
admission = json.loads((EVIDENCE / "admission.json").read_text())
trajectory = json.loads(TRAJECTORY.read_text())
stdout_path = EVIDENCE / "logs/01-moving-liquid-data-diagnostic.stdout.log"
stderr_path = EVIDENCE / "logs/01-moving-liquid-data-diagnostic.stderr.log"
samples = result["particleSamples"]
bullet = result["bulletSamples"]
initial_count = samples[0]["aliveParticleCount"]
ratios = [row["aliveParticleCount"] / initial_count for row in samples]
minimum_ratio = min(ratios)
maximum_count_drift = max(abs(ratio - 1.0) for ratio in ratios)
maximum_outside = max(row["outsideCupInteriorPlusOneVoxelFraction"] for row in samples)
centroid0 = samples[0]["centroidCupLocalMeters"]
centroid_shift = max(math.dist(row["centroidCupLocalMeters"], centroid0) for row in samples)
expected_trajectory = {row["frame"]: row for row in trajectory["samples"] if 1 <= row["frame"] <= 24}
location_delta = max(math.dist(row["cupLocation"], expected_trajectory[row["frame"]]["cupLocation"]) for row in bullet)
if maximum_outside > 0.01:
    classification = "DATA_PARTICLE_CONTAINMENT_FAILURE"
elif maximum_count_drift > 0.15:
    classification = "DATA_PARTICLE_COUNT_DRIFT_SIGNAL"
else:
    classification = "DATA_PARTICLE_COUNT_STABLE_SURFACE_RECONSTRUCTION_SUSPECTED"
cache_root = WORK / "mantaflow-cache"
cache_files = sorted(str(path.relative_to(cache_root)) for path in cache_root.rglob("*") if path.is_file())
expected_cache_files = sorted(
    [f"config/config_{frame:04d}.uni" for frame in range(1, 25)]
    + [f"data/fluid_data_{frame:04d}.vdb" for frame in range(1, 25)]
)
tools = {row["uri"]: row["sha256"] for row in spec["tools"]}
recomputed_checks = {
    "exactAcceptedC5F96Trajectory": location_delta <= 1e-5 and max(row["acceptedRotationDeltaDegrees"] for row in bullet) <= 1e-4,
    "solverOwnedCupMotionPresent": bullet[-1]["cupTiltDegrees"] >= 14.0,
    "hingeAndMotorExact": result["checks"]["hingeAndMotorExact"],
    "hingePivotStable": max(row["hingePivotDriftMeters"] for row in bullet) <= 0.005,
    "exactDataCacheFrameRoster": cache_files == expected_cache_files and len(cache_files) == 48,
    "singleFlipParticleSystemEveryFrame": len(samples) == 24 and all(row["particleCount"] > 0 and row["aliveParticleCount"] > 0 for row in samples),
    "allParticleStatesBound": all(sum(row["aliveStateCounts"].values()) == row["particleCount"] for row in samples),
    "particleCountProxyMeasured": initial_count > 0 and minimum_ratio > 0.0,
    "singleInitialGeometryFlow": result["checks"]["singleInitialGeometryFlow"],
    "zeroOutcomePoseAuthority": result["checks"]["zeroOutcomePoseAuthority"],
    "previewDataTierExact": result["configuration"]["resolutionMax"] == 96 and result["configuration"]["frameEnd"] == 24 and abs(result["configuration"]["particleRadius"] - 1.6) <= 1e-6 and not result["configuration"]["useMesh"] and result["configuration"]["cupEffectorSubframes"] == 1,
}
banned = {".png", ".jpg", ".jpeg", ".exr", ".mov", ".mp4"}
source_copy = WORK / "source-state-copy.blend"
checks = {
    "specSelfHash": spec["specHash"] == self_hash(spec, "specHash"),
    "frozenToolIdentities": tools == {str(SCENE_TOOL.relative_to(RESEARCH)): sha(SCENE_TOOL), str(RUNNER.relative_to(RESEARCH)): sha(RUNNER), str(Path(__file__).resolve().relative_to(RESEARCH)): sha(Path(__file__).resolve())},
    "sourceTrajectoryExact": sha(SOURCE) == spec["baseline"]["sourceBlendSha256"] and sha(TRAJECTORY) == spec["baseline"]["trajectoryFileSha256"],
    "attempt56EvidenceExact": sha(RETAINED56_EVIDENCE / "result.json") == spec["retainedAttempt56"]["resultFileSha256"] and sha(RETAINED56_EVIDENCE / "failure-receipt-c1.json") == spec["retainedAttempt56"]["failureReceiptFileSha256"] and sha(RETAINED56_EVIDENCE / "independent-audit-c1.json") == spec["retainedAttempt56"]["failureAuditFileSha256"],
    "attempt56WorkExact": manifest(RETAINED56_WORK)["manifestHash"] == spec["retainedAttempt56"]["workManifestHash"] == receipt["retainedAttempt56WorkManifestBefore"] == receipt["retainedAttempt56WorkManifestAfter"],
    "admissionExact": admission["status"] == "PASS" and admission["workRootAbsentBeforeRun"] and admission["evidenceRootAbsentBeforeRun"],
    "resultSelfHash": result["resultHash"] == self_hash(result, "resultHash"),
    "receiptSelfHash": receipt["receiptHash"] == self_hash(receipt, "receiptHash") and receipt["resultHash"] == result["resultHash"],
    "processSelfHashAndLogs": process["processHash"] == self_hash(process, "processHash") and process["exitCode"] == 0 and process["stdoutSha256"] == sha(stdout_path) and process["stderrSha256"] == sha(stderr_path),
    "physicalHarnessChecksRecomputed": recomputed_checks == result["checks"] and all(recomputed_checks.values()),
    "metricsRecomputed": abs(result["metrics"]["minimumAliveCountRatioToFrame1"] - minimum_ratio) <= 1e-8 and abs(result["metrics"]["maximumAbsoluteAliveCountDriftFraction"] - maximum_count_drift) <= 1e-8 and abs(result["metrics"]["maximumParticleOutsideCupPlusOneVoxelFraction"] - maximum_outside) <= 1e-8 and abs(result["metrics"]["maximumParticleCentroidShiftCupLocalMeters"] - centroid_shift) <= 1e-8,
    "classificationRecomputed": result["status"] == "MEASURED_DATA_ONLY" and result["classification"] == classification == receipt["classification"],
    "exactDataOnlyCacheRoster": cache_files == expected_cache_files and len(cache_files) == 48 and not any(path.suffix == ".gz" for path in cache_root.rglob("*")),
    "sourceCopyExactOnlyBlend": sha(source_copy) == spec["baseline"]["sourceBlendSha256"] and [path for path in WORK.rglob("*.blend")] == [source_copy],
    "zeroMeshRenderSaveNetwork": result["counts"] == {"blenderStarts": 1, "bulletBakes": 1, "fluidDataBakes": 1, "fluidMeshBakes": 0, "renders": 0, "blendSaves": 0, "networkCalls": 0, "engineRemoteWrites": 0},
    "noRenderMedia": not any(path.suffix.lower() in banned for root in (WORK, EVIDENCE) for path in root.rglob("*")),
    "noSymlinks": not any(path.is_symlink() for root in (WORK, EVIDENCE) for path in root.rglob("*")),
    "rootsBelowCeilings": sum(path.stat().st_size for path in WORK.rglob("*") if path.is_file()) < spec["resourceCeilings"]["maximumWorkspaceBytes"] and sum(path.stat().st_size for path in EVIDENCE.rglob("*") if path.is_file()) < spec["resourceCeilings"]["maximumEvidenceBytes"],
}
audit = {
    "schemaVersion": "bfs.rc6MovingLiquidDataDiagnosticIndependentAudit.v0.1",
    "status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "checkCount": len(checks),
    "passCount": sum(checks.values()),
    "classification": classification,
    "resultHash": result["resultHash"],
    "receiptHash": receipt["receiptHash"],
}
audit["auditHash"] = self_hash(audit, "auditHash")
with (EVIDENCE / "independent-audit.json").open("x", encoding="utf-8") as handle:
    json.dump(audit, handle, indent=2, sort_keys=True)
    handle.write("\n")
print("RC6_MOVING_LIQUID_DATA_DIAGNOSTIC_AUDIT=" + canonical(audit))
if audit["status"] != "PASS":
    raise RuntimeError("moving-liquid Data diagnostic independent audit failed")
