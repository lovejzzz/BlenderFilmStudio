#!/usr/bin/env python3
"""Independently reread copied VDB metadata and audit attempt-58 occupancy."""

import hashlib
import json
import math
import sys
from pathlib import Path

import openvdb


RESEARCH = Path(__file__).resolve().parents[1]
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-moving-liquid-data-occupancy-attempt-58")
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-data-occupancy-attempt-58"
SOURCE_CACHE = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-moving-liquid-data-diagnostic-attempt-57/mantaflow-cache")
ATTEMPT56 = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-preview-attempt-56/result.json"
ATTEMPT57 = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-data-diagnostic-attempt-57/result.json"
ENGINE_PYTHON = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC5-2026-09-01-attempt-01/build/bin/Film Studio Engine F0.app/Contents/Resources/5.2/python/bin/python3.13")
OPENVDB_MODULE = ENGINE_PYTHON.parent.parent / "lib/python3.13/site-packages/openvdb.cpython-313-darwin.so"
OPENVDB_LIBRARY = ENGINE_PYTHON.parents[3] / "lib/libopenvdb.dylib"
ANALYZER = RESEARCH / "scripts/analyze-rc6-moving-liquid-data-occupancy.py"
RUNNER = RESEARCH / "scripts/run-rc6-moving-liquid-data-occupancy.py"
SPEC = RESEARCH / "specs/ai-native-studio-rc6-moving-liquid-data-occupancy.v0.69.json"
SOURCE_VOLUME = 0.0013283283766941


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
    a = sum(first) / len(first)
    b = sum(second) / len(second)
    numerator = sum((x - a) * (y - b) for x, y in zip(first, second))
    denominator = math.sqrt(sum((x - a) ** 2 for x in first) * sum((y - b) ** 2 for y in second))
    return numerator / denominator if denominator else 0.0


spec = json.loads(SPEC.read_text())
result = json.loads((EVIDENCE / "result.json").read_text())
receipt = json.loads((EVIDENCE / "receipt.json").read_text())
process = json.loads((EVIDENCE / "processes/01-data-occupancy.json").read_text())
admission = json.loads((EVIDENCE / "admission.json").read_text())
attempt56 = json.loads(ATTEMPT56.read_text())
attempt57 = json.loads(ATTEMPT57.read_text())
cache = WORK / "cache-copy"
samples = []
for frame in range(1, 25):
    grids = {grid.name: grid for grid in openvdb.readAllGridMetadata(str(cache / "data" / f"fluid_data_{frame:04d}.vdb"))}
    if set(grids) != {"particles", "velocity"}:
        raise RuntimeError(f"audit frame {frame}: VDB grid roster mismatch")
    particle_meta = dict(grids["particles"].metadata)
    velocity_meta = dict(grids["velocity"].metadata)
    voxel = float(particle_meta["file_voxel_size"])
    occupancy = int(particle_meta["file_voxel_count"]) * voxel ** 3
    samples.append({
        "frame": frame,
        "particleVoxelCount": int(particle_meta["file_voxel_count"]),
        "velocityVoxelCount": int(velocity_meta["file_voxel_count"]),
        "voxel": voxel,
        "occupancy": occupancy,
        "particleBBoxMin": list(particle_meta["file_bbox_min"]),
        "particleBBoxMax": list(particle_meta["file_bbox_max"]),
        "velocityBBoxMin": list(velocity_meta["file_bbox_min"]),
        "velocityBBoxMax": list(velocity_meta["file_bbox_max"]),
    })
initial = samples[0]["occupancy"]
drifts = [row["occupancy"] / initial - 1.0 for row in samples]
mesh = [row["meshVolumeCubicMeters"] for row in attempt56["fluidSamples"]]
alive = [row["aliveParticleCount"] for row in attempt57["particleSamples"]]
correlation_mesh = pearson([row["occupancy"] for row in samples], mesh)
correlation_alive = pearson([row["occupancy"] for row in samples], alive)
final_mesh_drift = attempt56["fluidSamples"][-1]["temporalVolumeDriftFraction"]
if drifts[-1] < -0.15 and final_mesh_drift < -0.15 and correlation_mesh >= 0.8:
    classification = "DATA_SPATIAL_SUPPORT_SHRINKS_WITH_MESH"
elif max(abs(value) for value in drifts) <= 0.15 and abs(final_mesh_drift) > 0.15:
    classification = "DATA_OCCUPANCY_STABLE_SURFACE_RECONSTRUCTION_SUSPECTED"
else:
    classification = "DATA_MESH_RELATION_DIVERGENT_INCONCLUSIVE"
tools = {row["uri"]: row["sha256"] for row in spec["tools"]}
source_manifest = manifest(SOURCE_CACHE)
copy_manifest = manifest(cache)
normalized_copy = dict(copy_manifest)
normalized_copy["root"] = str(SOURCE_CACHE)
normalized_copy["manifestHash"] = self_hash(normalized_copy, "manifestHash")
stdout = EVIDENCE / "logs/01-data-occupancy.stdout.log"
stderr = EVIDENCE / "logs/01-data-occupancy.stderr.log"
stored_copy_manifest = json.loads((EVIDENCE / "copied-cache-manifest.json").read_text())
all_sample_rows_match = all(
    observed["frame"] == recomputed["frame"]
    and observed["particleOccupiedVoxelCount"] == recomputed["particleVoxelCount"]
    and observed["velocityActiveVoxelCount"] == recomputed["velocityVoxelCount"]
    and abs(observed["voxelSizeMeters"] - recomputed["voxel"]) <= 1e-12
    and abs(observed["particleOccupancyVolumeProxyCubicMeters"] - recomputed["occupancy"]) <= 1e-12
    and observed["particleGridBBoxMin"] == recomputed["particleBBoxMin"]
    and observed["particleGridBBoxMax"] == recomputed["particleBBoxMax"]
    and observed["velocityGridBBoxMin"] == recomputed["velocityBBoxMin"]
    and observed["velocityGridBBoxMax"] == recomputed["velocityBBoxMax"]
    and observed["aliveParticleCount"] == attempt57["particleSamples"][index]["aliveParticleCount"]
    and abs(observed["meshVolumeCubicMeters"] - attempt56["fluidSamples"][index]["meshVolumeCubicMeters"]) <= 1e-12
    for index, (observed, recomputed) in enumerate(zip(result["samples"], samples))
)
checks = {
    "specSelfHash": spec["specHash"] == self_hash(spec, "specHash"),
    "frozenToolIdentities": tools == {str(ANALYZER.relative_to(RESEARCH)): sha(ANALYZER), str(RUNNER.relative_to(RESEARCH)): sha(RUNNER), str(Path(__file__).resolve().relative_to(RESEARCH)): sha(Path(__file__).resolve())},
    "auditRuntimeExact": Path(sys.executable).resolve() == ENGINE_PYTHON.resolve() and sha(ENGINE_PYTHON) == spec["runtime"]["enginePythonSha256"] and sha(OPENVDB_MODULE) == spec["runtime"]["openVdbModuleSha256"] and sha(OPENVDB_LIBRARY) == spec["runtime"]["openVdbLibrarySha256"] and tuple(openvdb.LIBRARY_VERSION) == (13, 0, 0) and openvdb.FILE_FORMAT_VERSION == 225,
    "attemptResultsExact": sha(ATTEMPT56) == spec["baseline"]["attempt56ResultFileSha256"] and sha(ATTEMPT57) == spec["baseline"]["attempt57ResultFileSha256"],
    "admissionExact": admission["status"] == "PASS" and admission["workRootAbsentBeforeRun"] and admission["evidenceRootAbsentBeforeRun"],
    "resultSelfHash": result["resultHash"] == self_hash(result, "resultHash"),
    "receiptSelfHash": receipt["receiptHash"] == self_hash(receipt, "receiptHash") and receipt["resultHash"] == result["resultHash"],
    "processSelfHashAndLogs": process["processHash"] == self_hash(process, "processHash") and process["exitCode"] == 0 and process["stdoutSha256"] == sha(stdout) and process["stderrSha256"] == sha(stderr),
    "retainedCacheExactAndUnchanged": source_manifest["manifestHash"] == normalized_copy["manifestHash"] == spec["baseline"]["attempt57CacheManifestHash"] == receipt["sourceCacheManifestBefore"] == receipt["sourceCacheManifestAfter"],
    "copiedManifestBound": stored_copy_manifest["manifestHash"] == self_hash(stored_copy_manifest, "manifestHash") == copy_manifest["manifestHash"] == receipt["copiedCacheManifest"],
    "all24GridRostersReopened": len(samples) == 24 and all(row["particleVoxelCount"] > 0 and row["velocityVoxelCount"] > 0 and abs(row["voxel"] - 0.009375) <= 1e-8 for row in samples),
    "all24SampleRowsRecomputed": all_sample_rows_match,
    "occupancyMetricsRecomputed": result["metrics"]["initialParticleOccupiedVoxelCount"] == samples[0]["particleVoxelCount"] and result["metrics"]["finalParticleOccupiedVoxelCount"] == samples[-1]["particleVoxelCount"] and abs(result["metrics"]["finalParticleOccupancyTemporalDriftFraction"] - drifts[-1]) <= 1e-10 and abs(result["metrics"]["maximumAbsoluteParticleOccupancyTemporalDriftFraction"] - max(abs(value) for value in drifts)) <= 1e-10,
    "correlationsRecomputed": abs(result["metrics"]["occupancyMeshPearsonCorrelation"] - correlation_mesh) <= 1e-10 and abs(result["metrics"]["occupancyAliveCountPearsonCorrelation"] - correlation_alive) <= 1e-10,
    "sourceProxyRecomputed": abs(result["metrics"]["initialOccupancySourceErrorFraction"] - (samples[0]["occupancy"] / SOURCE_VOLUME - 1.0)) <= 1e-10 and abs(result["metrics"]["finalOccupancySourceErrorFraction"] - (samples[-1]["occupancy"] / SOURCE_VOLUME - 1.0)) <= 1e-10,
    "classificationRecomputed": result["status"] == "MEASURED_DATA_OCCUPANCY" and result["classification"] == classification == receipt["classification"],
    "noBlenderBakeRenderSaveNetwork": result["counts"] == {"enginePythonStarts": 1, "blenderStarts": 0, "fluidDataBakes": 0, "fluidMeshBakes": 0, "renders": 0, "blendSaves": 0, "networkCalls": 0, "retainedRootWrites": 0} and receipt["counts"] == result["counts"],
    "rootsBelowCeilings": sum(path.stat().st_size for path in WORK.rglob("*") if path.is_file()) < spec["resourceCeilings"]["maximumWorkspaceBytes"] and sum(path.stat().st_size for path in EVIDENCE.rglob("*") if path.is_file()) < spec["resourceCeilings"]["maximumEvidenceBytes"],
    "noSymlinksOrMedia": not any(path.is_symlink() or path.suffix.lower() in {".png", ".jpg", ".jpeg", ".exr", ".mov", ".mp4"} for root in (WORK, EVIDENCE) for path in root.rglob("*")),
}
audit = {
    "schemaVersion": "bfs.rc6MovingLiquidDataOccupancyIndependentAudit.v0.1",
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
print("RC6_MOVING_LIQUID_DATA_OCCUPANCY_AUDIT=" + canonical(audit))
if audit["status"] != "PASS":
    raise RuntimeError("moving-liquid Data occupancy independent audit failed")
