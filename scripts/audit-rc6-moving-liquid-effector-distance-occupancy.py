#!/usr/bin/env python3
"""Independently reread attempt-60 copied VDB metadata and audit the comparison."""

import hashlib
import json
import math
import sys
from pathlib import Path

import openvdb


RESEARCH = Path(__file__).resolve().parents[1]
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-moving-liquid-effector-distance-data-occupancy-attempt-60")
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-effector-distance-data-occupancy-attempt-60"
SOURCE_CACHE = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-moving-liquid-effector-distance-attempt-59/mantaflow-cache")
ATTEMPT59 = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-effector-distance-attempt-59/result.json"
ATTEMPT59_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-effector-distance-attempt-59/independent-audit.json"
ATTEMPT58 = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-data-occupancy-attempt-58/result.json"
ENGINE_PYTHON = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC5-2026-09-01-attempt-01/build/bin/Film Studio Engine F0.app/Contents/Resources/5.2/python/bin/python3.13")
OPENVDB_MODULE = ENGINE_PYTHON.parent.parent / "lib/python3.13/site-packages/openvdb.cpython-313-darwin.so"
OPENVDB_LIBRARY = ENGINE_PYTHON.parents[3] / "lib/libopenvdb.dylib"
ANALYZER = RESEARCH / "scripts/analyze-rc6-moving-liquid-effector-distance-occupancy.py"
RUNNER = RESEARCH / "scripts/run-rc6-moving-liquid-effector-distance-occupancy.py"
SPEC = RESEARCH / "specs/ai-native-studio-rc6-moving-liquid-effector-distance-data-occupancy.v0.71.json"


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


def pearson(first, second):
    mean_first = sum(first) / len(first)
    mean_second = sum(second) / len(second)
    numerator = sum((a - mean_first) * (b - mean_second) for a, b in zip(first, second))
    denominator = math.sqrt(
        sum((a - mean_first) ** 2 for a in first)
        * sum((b - mean_second) ** 2 for b in second)
    )
    return numerator / denominator if denominator else 0.0


spec = json.loads(SPEC.read_text())
result = json.loads((EVIDENCE / "result.json").read_text())
receipt = json.loads((EVIDENCE / "receipt.json").read_text())
process = json.loads((EVIDENCE / "processes/01-data-occupancy.json").read_text())
admission = json.loads((EVIDENCE / "admission.json").read_text())
attempt59 = json.loads(ATTEMPT59.read_text())
attempt59_audit = json.loads(ATTEMPT59_AUDIT.read_text())
attempt58 = json.loads(ATTEMPT58.read_text())
cache = WORK / "cache-copy"
samples = []
for frame in range(1, 25):
    grids = {grid.name: grid for grid in openvdb.readAllGridMetadata(str(cache / "data" / f"fluid_data_{frame:04d}.vdb"))}
    particle = grids["particles"]
    velocity = grids["velocity"]
    particle_meta = dict(particle.metadata)
    velocity_meta = dict(velocity.metadata)
    voxel = float(particle_meta["file_voxel_size"])
    occupied = int(particle_meta["file_voxel_count"])
    occupancy = occupied * voxel ** 3
    mesh59 = attempt59["fluidSamples"][frame - 1]
    prior = attempt58["samples"][frame - 1]
    samples.append(
        {
            "frame": frame,
            "particleGridType": type(particle).__name__,
            "velocityGridType": type(velocity).__name__,
            "particleOccupiedVoxelCount": occupied,
            "velocityActiveVoxelCount": int(velocity_meta["file_voxel_count"]),
            "voxelSizeMeters": voxel,
            "particleOccupancyVolumeProxyCubicMeters": occupancy,
            "particleGridBBoxMin": list(particle_meta["file_bbox_min"]),
            "particleGridBBoxMax": list(particle_meta["file_bbox_max"]),
            "velocityGridBBoxMin": list(velocity_meta["file_bbox_min"]),
            "velocityGridBBoxMax": list(velocity_meta["file_bbox_max"]),
            "meshVolumeCubicMeters": mesh59["meshVolumeCubicMeters"],
            "meshTemporalDriftFraction": mesh59["temporalVolumeDriftFraction"],
            "baseline2p5OccupancyTemporalDriftFraction": prior["occupancyTemporalDriftFraction"],
            "baseline2p5MeshTemporalDriftFraction": prior["meshVolumeCubicMeters"] / attempt58["samples"][0]["meshVolumeCubicMeters"] - 1.0,
        }
    )
initial_occupancy = samples[0]["particleOccupancyVolumeProxyCubicMeters"]
for row in samples:
    row["occupancyTemporalDriftFraction"] = row["particleOccupancyVolumeProxyCubicMeters"] / initial_occupancy - 1.0
    row["occupancyDriftImprovementVs2p5"] = row["occupancyTemporalDriftFraction"] - row["baseline2p5OccupancyTemporalDriftFraction"]
    row["meshDriftImprovementVs2p5"] = row["meshTemporalDriftFraction"] - row["baseline2p5MeshTemporalDriftFraction"]
occupancy = [row["particleOccupancyVolumeProxyCubicMeters"] for row in samples]
mesh = [row["meshVolumeCubicMeters"] for row in samples]
occupancy_improvement = [row["occupancyDriftImprovementVs2p5"] for row in samples]
mesh_improvement = [row["meshDriftImprovementVs2p5"] for row in samples]
drifts = [row["occupancyTemporalDriftFraction"] for row in samples]
final_mesh_drift = samples[-1]["meshTemporalDriftFraction"]
correlation_mesh = pearson(occupancy, mesh)
correlation_improvement = pearson(occupancy_improvement, mesh_improvement)
if drifts[-1] < -0.15 and final_mesh_drift < -0.15 and correlation_mesh >= 0.8:
    classification = "DATA_SPATIAL_SUPPORT_SHRINK_PERSISTS_AT_2P0"
elif max(abs(value) for value in drifts) <= 0.15 and abs(final_mesh_drift) > 0.15:
    classification = "DATA_SUPPORT_STABLE_SURFACE_RECONSTRUCTION_SUSPECTED"
else:
    classification = "DATA_MESH_RELATION_INCONCLUSIVE"

tools = {row["uri"]: row["sha256"] for row in spec["tools"]}
source_manifest = manifest(SOURCE_CACHE)
copy_manifest = manifest(cache)
normalized_copy = dict(copy_manifest)
normalized_copy["root"] = str(SOURCE_CACHE)
normalized_copy["manifestHash"] = self_hash(normalized_copy, "manifestHash")
stdout = EVIDENCE / "logs/01-data-occupancy.stdout.log"
stderr = EVIDENCE / "logs/01-data-occupancy.stderr.log"
stored_copy_manifest = json.loads((EVIDENCE / "copied-cache-manifest.json").read_text())
expected_argv = [
    str(ENGINE_PYTHON), str(ANALYZER),
    "--cache-copy", str(cache),
    "--attempt59-result", str(ATTEMPT59),
    "--attempt58-result", str(ATTEMPT58),
    "--result", str(EVIDENCE / "result.json"),
]

def close(a, b, tolerance=1e-12):
    return abs(a - b) <= tolerance


all_sample_rows_match = all(
    observed["frame"] == recomputed["frame"]
    and observed["particleGridType"] == recomputed["particleGridType"]
    and observed["velocityGridType"] == recomputed["velocityGridType"]
    and observed["particleOccupiedVoxelCount"] == recomputed["particleOccupiedVoxelCount"]
    and observed["velocityActiveVoxelCount"] == recomputed["velocityActiveVoxelCount"]
    and close(observed["voxelSizeMeters"], recomputed["voxelSizeMeters"])
    and close(observed["particleOccupancyVolumeProxyCubicMeters"], recomputed["particleOccupancyVolumeProxyCubicMeters"])
    and observed["particleGridBBoxMin"] == recomputed["particleGridBBoxMin"]
    and observed["particleGridBBoxMax"] == recomputed["particleGridBBoxMax"]
    and observed["velocityGridBBoxMin"] == recomputed["velocityGridBBoxMin"]
    and observed["velocityGridBBoxMax"] == recomputed["velocityGridBBoxMax"]
    and close(observed["meshVolumeCubicMeters"], recomputed["meshVolumeCubicMeters"])
    and close(observed["meshTemporalDriftFraction"], recomputed["meshTemporalDriftFraction"])
    and close(observed["baseline2p5OccupancyTemporalDriftFraction"], recomputed["baseline2p5OccupancyTemporalDriftFraction"])
    and close(observed["baseline2p5MeshTemporalDriftFraction"], recomputed["baseline2p5MeshTemporalDriftFraction"])
    and close(observed["occupancyTemporalDriftFraction"], recomputed["occupancyTemporalDriftFraction"])
    and close(observed["occupancyDriftImprovementVs2p5"], recomputed["occupancyDriftImprovementVs2p5"])
    and close(observed["meshDriftImprovementVs2p5"], recomputed["meshDriftImprovementVs2p5"])
    for observed, recomputed in zip(result["samples"], samples)
)
checks = {
    "specSelfHash": spec["specHash"] == self_hash(spec, "specHash"),
    "frozenToolIdentities": tools == {
        str(ANALYZER.relative_to(RESEARCH)): sha(ANALYZER),
        str(RUNNER.relative_to(RESEARCH)): sha(RUNNER),
        str(Path(__file__).resolve().relative_to(RESEARCH)): sha(Path(__file__).resolve()),
    },
    "auditRuntimeExact": Path(sys.executable).resolve() == ENGINE_PYTHON.resolve() and sha(ENGINE_PYTHON) == spec["runtime"]["enginePythonSha256"] and sha(OPENVDB_MODULE) == spec["runtime"]["openVdbModuleSha256"] and sha(OPENVDB_LIBRARY) == spec["runtime"]["openVdbLibrarySha256"] and tuple(openvdb.LIBRARY_VERSION) == (13, 0, 0) and openvdb.FILE_FORMAT_VERSION == 225,
    "attemptResultsExact": sha(ATTEMPT59) == spec["baseline"]["attempt59ResultFileSha256"] and sha(ATTEMPT59_AUDIT) == spec["baseline"]["attempt59AuditFileSha256"] and attempt59_audit["auditHash"] == spec["baseline"]["attempt59AuditHash"] and attempt59_audit["status"] == "PASS" and sha(ATTEMPT58) == spec["baseline"]["attempt58ResultFileSha256"],
    "admissionExact": admission["status"] == "PASS" and admission["workRootAbsentBeforeRun"] and admission["evidenceRootAbsentBeforeRun"],
    "resultSelfHash": result["resultHash"] == self_hash(result, "resultHash"),
    "receiptSelfHash": receipt["receiptHash"] == self_hash(receipt, "receiptHash") and receipt["resultHash"] == result["resultHash"],
    "processSelfHashLogsAndArgv": process["processHash"] == self_hash(process, "processHash") and process["exitCode"] == 0 and process["argv"] == expected_argv and process["stdoutSha256"] == sha(stdout) and process["stderrSha256"] == sha(stderr),
    "retainedCacheExactAndUnchanged": source_manifest["manifestHash"] == normalized_copy["manifestHash"] == spec["baseline"]["attempt59CacheManifestHash"] == receipt["sourceCacheManifestBefore"] == receipt["sourceCacheManifestAfter"],
    "copiedManifestBound": stored_copy_manifest["manifestHash"] == self_hash(stored_copy_manifest, "manifestHash") == copy_manifest["manifestHash"] == receipt["copiedCacheManifest"],
    "exact72FileCopy": len(copy_manifest["files"]) == 72 and sum(row["bytes"] for row in copy_manifest["files"]) == spec["baseline"]["attempt59CacheBytes"],
    "all24GridRostersReopened": len(samples) == 24 and all(row["particleGridType"] == "PointDataGrid" and row["velocityGridType"] == "Vec3SGrid" and row["particleOccupiedVoxelCount"] > 0 and row["velocityActiveVoxelCount"] > 0 and close(row["voxelSizeMeters"], 0.009375, 1e-8) for row in samples),
    "all24SampleRowsRecomputed": len(result["samples"]) == 24 and all_sample_rows_match,
    "occupancyMetricsRecomputed": result["metrics"]["initialParticleOccupiedVoxelCount"] == samples[0]["particleOccupiedVoxelCount"] and result["metrics"]["finalParticleOccupiedVoxelCount"] == samples[-1]["particleOccupiedVoxelCount"] and close(result["metrics"]["finalParticleOccupancyTemporalDriftFraction"], drifts[-1], 1e-10) and close(result["metrics"]["maximumAbsoluteParticleOccupancyTemporalDriftFraction"], max(abs(value) for value in drifts), 1e-10),
    "meshAndImprovementMetricsRecomputed": close(result["metrics"]["finalMeshTemporalVolumeDriftFraction"], final_mesh_drift, 1e-10) and close(result["metrics"]["occupancyMeshPearsonCorrelation"], correlation_mesh, 1e-10) and close(result["metrics"]["finalOccupancyDriftImprovementVs2p5"], occupancy_improvement[-1], 1e-10) and close(result["metrics"]["finalMeshDriftImprovementVs2p5"], mesh_improvement[-1], 1e-10) and close(result["metrics"]["occupancyMeshImprovementPearsonCorrelation"], correlation_improvement, 1e-10),
    "classificationRecomputed": result["status"] == "MEASURED_DATA_OCCUPANCY" and result["classification"] == classification == receipt["classification"],
    "zeroBlenderBakeRenderSaveNetwork": result["counts"] == {"enginePythonStarts": 1, "blenderStarts": 0, "fluidDataBakes": 0, "fluidMeshBakes": 0, "renders": 0, "blendSaves": 0, "networkCalls": 0, "retainedRootWrites": 0} and receipt["counts"] == result["counts"],
    "rootsBelowCeilings": sum(path.stat().st_size for path in WORK.rglob("*") if path.is_file()) < spec["resourceCeilings"]["maximumWorkspaceBytes"] and sum(path.stat().st_size for path in EVIDENCE.rglob("*") if path.is_file()) < spec["resourceCeilings"]["maximumEvidenceBytes"],
    "noSymlinksOrMedia": not any(path.is_symlink() or path.suffix.lower() in {".png", ".jpg", ".jpeg", ".exr", ".mov", ".mp4"} for root in (WORK, EVIDENCE) for path in root.rglob("*")),
}
audit = {
    "schemaVersion": "bfs.rc6MovingLiquidEffectorDistanceOccupancyIndependentAudit.v0.1",
    "status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "checkCount": len(checks),
    "passCount": sum(checks.values()),
    "classification": classification,
    "resultHash": result["resultHash"],
    "receiptHash": receipt["receiptHash"],
    "auditCommand": [str(Path(sys.executable).resolve()), str(Path(__file__).resolve())],
    "totalCountsIncludingAudit": {"enginePythonStarts": 2, "blenderStarts": 0, "fluidDataBakes": 0, "fluidMeshBakes": 0, "renders": 0, "blendSaves": 0, "networkCalls": 0, "retainedRootWrites": 0},
}
audit["auditHash"] = self_hash(audit, "auditHash")
with (EVIDENCE / "independent-audit.json").open("x", encoding="utf-8") as handle:
    json.dump(audit, handle, indent=2, sort_keys=True)
    handle.write("\n")
print("RC6_MOVING_LIQUID_EFFECTOR_DISTANCE_OCCUPANCY_AUDIT=" + canonical(audit))
if audit["status"] != "PASS":
    raise RuntimeError("attempt-60 independent audit failed")
