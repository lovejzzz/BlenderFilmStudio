#!/usr/bin/env python3
"""Close retained attempt-56 as a physical FAIL plus exit-code harness mismatch."""

import hashlib
import json
import math
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-moving-liquid-preview-attempt-56")
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-preview-attempt-56"
SPEC = RESEARCH / "specs/ai-native-studio-rc6-moving-liquid-preview.v0.66.json"
CLOSURE_SPEC = RESEARCH / "specs/ai-native-studio-rc6-moving-liquid-preview-failure-c1.v0.67.json"
TRAJECTORY = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-slow-tip-bullet-screen-c5-c3-attempt-55/cells/C5F96/result.json"
RETAINED_CACHE = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-final-effector-mesh-c3-attempt-46/final-effector-mesh-c3/mantaflow-cache")


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


def write_exclusive(path, value):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def file_manifest(root):
    rows = [
        {"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": sha(path)}
        for path in sorted(root.rglob("*"))
        if path.is_file()
    ]
    value = {"root": str(root), "files": rows}
    value["manifestHash"] = self_hash(value, "manifestHash")
    return value


def retained_cache_manifest_hash():
    rows = [
        {"path": str(path.relative_to(RETAINED_CACHE)), "bytes": path.stat().st_size, "sha256": sha(path)}
        for path in sorted(RETAINED_CACHE.rglob("*"))
        if path.is_file()
    ]
    return self_hash({"root": str(RETAINED_CACHE), "files": rows}, "manifestHash"), len(rows), sum(row["bytes"] for row in rows)


spec = json.loads(SPEC.read_text())
closure_spec = json.loads(CLOSURE_SPEC.read_text())
result = json.loads((EVIDENCE / "result.json").read_text())
process = json.loads((EVIDENCE / "processes/01-moving-liquid-preview.json").read_text())
admission = json.loads((EVIDENCE / "admission.json").read_text())
trajectory = json.loads(TRAJECTORY.read_text())
stdout_path = EVIDENCE / "logs/01-moving-liquid-preview.stdout.log"
stderr_path = EVIDENCE / "logs/01-moving-liquid-preview.stderr.log"
stdout = stdout_path.read_text()
stderr = stderr_path.read_text()
fluid = result["fluidSamples"]
bullet = result["bulletSamples"]
source_volume = result["configuration"]["sourceMeshVolumeCubicMeters"]
initial_volume = fluid[0]["meshVolumeCubicMeters"]
source_error = max(abs(row["meshVolumeCubicMeters"] / source_volume - 1.0) for row in fluid)
temporal_drift = max(abs(row["meshVolumeCubicMeters"] / initial_volume - 1.0) for row in fluid)
centroid_shift = max(math.dist(row["centroidCupLocalMeters"], fluid[0]["centroidCupLocalMeters"]) for row in fluid)
expected_trajectory = {row["frame"]: row for row in trajectory["samples"] if 1 <= row["frame"] <= 24}
location_delta = max(math.dist(row["cupLocation"], expected_trajectory[row["frame"]]["cupLocation"]) for row in bullet)
cache_root = WORK / "mantaflow-cache"
cache_files = sorted(str(path.relative_to(cache_root)) for path in cache_root.rglob("*") if path.is_file())
expected_cache_files = sorted(
    [f"config/config_{frame:04d}.uni" for frame in range(1, 25)]
    + [f"data/fluid_data_{frame:04d}.vdb" for frame in range(1, 25)]
    + [f"mesh/fluid_mesh_{frame:04d}.bobj.gz" for frame in range(1, 25)]
)
retained_hash, retained_files, retained_bytes = retained_cache_manifest_hash()
false_checks = sorted(name for name, passed in result["checks"].items() if not passed)
banned = {".png", ".jpg", ".jpeg", ".exr", ".mov", ".mp4"}
source_copy = WORK / "source-state-copy.blend"
append_paths = [RESEARCH / path for path in closure_spec["allowedAppendPaths"]]

checks = {
    "baseSpecSelfHash": spec["specHash"] == self_hash(spec, "specHash") == "d90ac6dfc6487b7d7616878091c7638a179c277ac9e5bac30bf57eb9ece3b3d9",
    "closureSpecSelfHash": closure_spec["specHash"] == self_hash(closure_spec, "specHash"),
    "closureToolIdentity": closure_spec["closureTool"] == {"uri": str(Path(__file__).resolve().relative_to(RESEARCH)), "sha256": sha(Path(__file__).resolve())},
    "appendPathsAbsentBeforeClosure": all(not path.exists() for path in append_paths),
    "admissionPassedBeforeRootCreation": admission["status"] == "PASS" and admission["workRootAbsentBeforeRun"] and admission["evidenceRootAbsentBeforeRun"],
    "resultSelfHash": result["resultHash"] == self_hash(result, "resultHash") == "4969ee48c700fd86e452f1df536918b0c5c2ae868c77f39b4c3e37bc548f1a99",
    "processSelfHash": process["processHash"] == self_hash(process, "processHash") == "ca3a5d1d81ac96df2dc15b678fa2a81280733553991067d8420a71be16c0388d",
    "processLogsBound": process["stdoutSha256"] == sha(stdout_path) and process["stderrSha256"] == sha(stderr_path),
    "blenderExitZeroDespiteThresholdException": process["exitCode"] == 0 and "RuntimeError: moving-liquid Preview thresholds failed" in stderr and '"status":"FAIL"' in stdout,
    "physicalVerdictFailExact": result["status"] == "FAIL" and result["verdict"] == "FAIL_MOVING_LIQUID_PREVIEW" and result["passCount"] == 15 and result["checkCount"] == 17,
    "onlyVolumeChecksFailed": false_checks == ["sourceRelativeVolumeWithin25Percent", "temporalVolumeDriftWithin15Percent"],
    "sourceVolumeFailureRecomputed": abs(source_error - result["metrics"]["maximumAbsoluteSourceVolumeErrorFraction"]) <= 1e-8 and source_error > 0.25,
    "temporalVolumeFailureRecomputed": abs(temporal_drift - result["metrics"]["maximumAbsoluteTemporalVolumeDriftFraction"]) <= 1e-8 and temporal_drift > 0.15,
    "movingLiquidRecomputed": abs(centroid_shift - result["metrics"]["maximumLiquidCentroidShiftCupLocalMeters"]) <= 1e-8 and centroid_shift >= 0.002,
    "exactTrajectoryRecomputed": location_delta <= 1e-5 and max(row["acceptedRotationDeltaDegrees"] for row in bullet) <= 1e-4,
    "containmentAndTopologyPassed": max(row["outsideCupInteriorPlusOneVoxelFraction"] for row in fluid) == 0.0 and max(row["belowFloorFraction"] for row in fluid) == 0.0 and max(row["aboveRimFraction"] for row in fluid) == 0.0 and max(row["nonManifoldEdgeCount"] for row in fluid) == 0 and {row["positiveBodyCount"] for row in fluid} == {1},
    "exactCacheRoster": cache_files == expected_cache_files == result["cache"]["files"] and len(cache_files) == 72,
    "retainedStaticCacheUnchanged": (retained_hash, retained_files, retained_bytes) == ("53bc19e1532b64ea8c37b0cc5fa52347c72c73023728d3705d45c063d5b7c265", 21, 31537894),
    "sourceCopyOnlyBlend": sha(source_copy) == spec["baseline"]["sourceBlendSha256"] and [path for path in WORK.rglob("*.blend")] == [source_copy],
    "zeroRenderSaveNetwork": result["counts"] == {"blenderStarts": 1, "bulletBakes": 1, "fluidDataBakes": 1, "fluidMeshBakes": 1, "renders": 0, "blendSaves": 0, "networkCalls": 0, "engineRemoteWrites": 0},
    "noRenderMedia": not any(path.suffix.lower() in banned for root in (WORK, EVIDENCE) for path in root.rglob("*")),
    "noSymlinks": not any(path.is_symlink() for root in (WORK, EVIDENCE) for path in root.rglob("*")),
    "rootsBelowCeilings": sum(path.stat().st_size for path in WORK.rglob("*") if path.is_file()) < 2147483648 and sum(path.stat().st_size for path in EVIDENCE.rglob("*") if path.is_file()) < 67108864,
}

receipt = {
    "schemaVersion": "bfs.rc6MovingLiquidPreviewFailureReceiptC1.v0.1",
    "status": "FAIL",
    "verdict": "FAIL_MOVING_LIQUID_PREVIEW_WITH_RETAINED_BLENDER_EXIT_ZERO_HARNESS_MISMATCH",
    "resultHash": result["resultHash"],
    "processHash": process["processHash"],
    "physicalFailures": false_checks,
    "maximumAbsoluteSourceVolumeErrorFraction": source_error,
    "maximumAbsoluteTemporalVolumeDriftFraction": temporal_drift,
    "maximumLiquidCentroidShiftCupLocalMeters": centroid_shift,
    "blenderExitCode": process["exitCode"],
    "blenderPythonThresholdExceptionObserved": True,
    "counts": result["counts"],
    "claimCeiling": "Retained 24-frame Preview-96 scientific failure: coherent contained single-body motion was observed, but source-relative and temporal mesh-volume conservation failed. No render, full-tip, spill, impact or film-quality claim.",
}
receipt["failureReceiptHash"] = self_hash(receipt, "failureReceiptHash")

audit = {
    "schemaVersion": "bfs.rc6MovingLiquidPreviewFailureIndependentAuditC1.v0.1",
    "status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "checkCount": len(checks),
    "passCount": sum(checks.values()),
    "resultHash": result["resultHash"],
    "processHash": process["processHash"],
    "failureReceiptHash": receipt["failureReceiptHash"],
}
audit["auditHash"] = self_hash(audit, "auditHash")

write_exclusive(EVIDENCE / "failure-receipt-c1.json", receipt)
write_exclusive(EVIDENCE / "independent-audit-c1.json", audit)
write_exclusive(EVIDENCE / "work-manifest-c1.json", file_manifest(WORK))
write_exclusive(EVIDENCE / "evidence-manifest-c1.json", file_manifest(EVIDENCE))
print("RC6_MOVING_LIQUID_PREVIEW_FAILURE_C1=" + canonical({"status": audit["status"], "auditHash": audit["auditHash"], "failureReceiptHash": receipt["failureReceiptHash"]}))
if audit["status"] != "PASS":
    raise RuntimeError("moving-liquid Preview failure closure audit failed")
