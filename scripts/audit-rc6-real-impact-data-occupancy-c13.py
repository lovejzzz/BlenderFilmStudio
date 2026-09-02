#!/usr/bin/env python3
"""Independently audit the copied-cache C13 impact diagnosis."""

import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

import openvdb


RESEARCH = Path(__file__).resolve().parents[1]
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-real-impact-data-occupancy-c13-attempt-85")
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-data-occupancy-c13-attempt-85"
SOURCE_CACHE = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-real-impact-liquid-preview-c12-attempt-84/mantaflow-cache")
ATTEMPT84 = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-preview-c12-attempt-84/result.json"
ATTEMPT84_RECEIPT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-preview-c12-attempt-84/receipt.json"
ATTEMPT84_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-preview-c12-attempt-84/independent-audit.json"
ENGINE_PYTHON = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC5-2026-09-01-attempt-01/build/bin/Film Studio Engine F0.app/Contents/Resources/5.2/python/bin/python3.13")
OPENVDB_MODULE = ENGINE_PYTHON.parent.parent / "lib/python3.13/site-packages/openvdb.cpython-313-darwin.so"
OPENVDB_LIBRARY = ENGINE_PYTHON.parents[3] / "lib/libopenvdb.dylib"
ANALYZER = RESEARCH / "scripts/analyze-rc6-real-impact-data-occupancy-c13.py"
RUNNER = RESEARCH / "scripts/run-rc6-real-impact-data-occupancy-c13.py"
SPEC = RESEARCH / "specs/ai-native-studio-rc6-real-impact-data-occupancy-c13.v0.96.json"


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


def manifest(root, exclude=()):
    excluded = set(exclude)
    rows = [
        {"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": sha(path)}
        for path in sorted(root.rglob("*"))
        if path.is_file() and str(path.relative_to(root)) not in excluded
    ]
    value = {"root": str(root), "files": rows}
    value["manifestHash"] = self_hash(value, "manifestHash")
    return value


def pearson(first, second):
    mean_first = sum(first) / len(first)
    mean_second = sum(second) / len(second)
    numerator = sum((a - mean_first) * (b - mean_second) for a, b in zip(first, second))
    denominator = math.sqrt(sum((a - mean_first) ** 2 for a in first) * sum((b - mean_second) ** 2 for b in second))
    return numerator / denominator if denominator else 0.0


def first_frame(rows, key, threshold):
    return next((row["frame"] for row in rows if row[key] > threshold), None)


spec = json.loads(SPEC.read_text())
result = json.loads((EVIDENCE / "result.json").read_text())
receipt = json.loads((EVIDENCE / "receipt.json").read_text())
process = json.loads((EVIDENCE / "processes/01-data-occupancy.json").read_text())
admission = json.loads((EVIDENCE / "admission.json").read_text())
attempt84 = json.loads(ATTEMPT84.read_text())
attempt84_receipt = json.loads(ATTEMPT84_RECEIPT.read_text())
attempt84_audit = json.loads(ATTEMPT84_AUDIT.read_text())
cache = WORK / "cache-copy"
measurement = spec["measurement"]
mesh_by_frame = {row["frame"]: row for row in attempt84["fluidSamples"]}
recomputed = []
for frame in range(1, 37):
    grids = {grid.name: grid for grid in openvdb.readAllGridMetadata(str(cache / "data" / f"fluid_data_{frame:04d}.vdb"))}
    particle = grids["particles"]
    velocity = grids["velocity"]
    pmeta = dict(particle.metadata)
    vmeta = dict(velocity.metadata)
    mesh = mesh_by_frame[frame]
    recomputed.append({
        "frame": frame,
        "particleGridType": type(particle).__name__,
        "velocityGridType": type(velocity).__name__,
        "particleOccupiedVoxelCount": int(pmeta["file_voxel_count"]),
        "velocityOccupiedVoxelCount": int(vmeta["file_voxel_count"]),
        "voxelSizeMeters": float(pmeta["file_voxel_size"]),
        "particleGridBBoxMin": list(pmeta["file_bbox_min"]),
        "particleGridBBoxMax": list(pmeta["file_bbox_max"]),
        "velocityGridBBoxMin": list(vmeta["file_bbox_min"]),
        "velocityGridBBoxMax": list(vmeta["file_bbox_max"]),
        "meshVolumeCubicMeters": mesh["meshVolumeCubicMeters"],
        "meshSourceVolumeErrorFraction": mesh["sourceVolumeErrorFraction"],
        "meshTemporalVolumeDriftFraction": mesh["temporalVolumeDriftFraction"],
        "meshConnectedComponentCount": mesh["connectedComponentCount"],
        "meshPositiveBodyCount": mesh["positiveBodyCount"],
        "meshLargestComponentFraction": mesh["largestComponentFraction"],
    })
baseline = recomputed[21]
for row in recomputed:
    row["particleOccupancyDriftFromBaselineFraction"] = row["particleOccupiedVoxelCount"] / baseline["particleOccupiedVoxelCount"] - 1.0
    row["velocityOccupancyDriftFromBaselineFraction"] = row["velocityOccupiedVoxelCount"] / baseline["velocityOccupiedVoxelCount"] - 1.0
    row["meshVolumeDriftFromBaselineFraction"] = row["meshVolumeCubicMeters"] / baseline["meshVolumeCubicMeters"] - 1.0
window = [row for row in recomputed if row["frame"] >= measurement["comparisonFrameStart"]]
threshold = spec["classificationRules"]["expansionThresholdFraction"]
first_data = first_frame(window, "particleOccupancyDriftFromBaselineFraction", threshold)
first_mesh = first_frame(window, "meshVolumeDriftFromBaselineFraction", threshold)
particle_corr = pearson([row["particleOccupiedVoxelCount"] for row in window], [row["meshVolumeCubicMeters"] for row in window])
velocity_corr = pearson([row["velocityOccupiedVoxelCount"] for row in window], [row["meshVolumeCubicMeters"] for row in window])
maximum_particle = max(row["particleOccupancyDriftFromBaselineFraction"] for row in window)
maximum_mesh = max(row["meshVolumeDriftFromBaselineFraction"] for row in window)
rules = spec["classificationRules"]
if first_data is not None and first_mesh is not None and first_data <= first_mesh and particle_corr >= rules["minimumStrongCorrelation"] and maximum_particle > rules["minimumGrossExpansionFraction"] and maximum_mesh > rules["minimumGrossExpansionFraction"]:
    classification = "DATA_SUPPORT_EXPANDS_WITH_MESH_MESH_ONLY_CAUSE_REJECTED"
elif maximum_particle <= threshold and maximum_mesh > rules["minimumGrossExpansionFraction"]:
    classification = "DATA_SUPPORT_STABLE_MESH_RECONSTRUCTION_SUSPECTED"
else:
    classification = "DATA_MESH_RELATION_DIVERGENT_INCONCLUSIVE"

tools = {row["uri"]: row["sha256"] for row in spec["tools"]}
source_manifest = manifest(SOURCE_CACHE)
copy_manifest = manifest(cache)
normalized_copy = dict(copy_manifest)
normalized_copy["root"] = str(SOURCE_CACHE)
normalized_copy["manifestHash"] = self_hash(normalized_copy, "manifestHash")
stored_copy_manifest = json.loads((EVIDENCE / "copied-cache-manifest.json").read_text())
stored_work_manifest = json.loads((EVIDENCE / "work-manifest.json").read_text())
stored_evidence_manifest = json.loads((EVIDENCE / "evidence-manifest.pre-audit.json").read_text())
stdout = EVIDENCE / "logs/01-data-occupancy.stdout.log"
stderr = EVIDENCE / "logs/01-data-occupancy.stderr.log"
expected_argv = [
    str(ENGINE_PYTHON), str(ANALYZER),
    "--cache-copy", str(cache),
    "--attempt84-result", str(ATTEMPT84),
    "--spec", str(SPEC),
    "--result", str(EVIDENCE / "result.json"),
]
sample_rows_match = result["samples"] == recomputed
metric = result["metrics"]
checks = {
    "specSelfHash": spec["specHash"] == self_hash(spec, "specHash"),
    "frozenToolIdentities": tools == {
        str(ANALYZER.relative_to(RESEARCH)): sha(ANALYZER),
        str(RUNNER.relative_to(RESEARCH)): sha(RUNNER),
        str(Path(__file__).resolve().relative_to(RESEARCH)): sha(Path(__file__).resolve()),
    },
    "executionCommitExact": receipt["researchExecutionCommit"] == subprocess.run(["git", "rev-parse", "HEAD"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.strip(),
    "committedToolsAndSpecExact": all(
        hashlib.sha256(subprocess.run(["git", "show", f"HEAD:{str(path.relative_to(RESEARCH))}"], cwd=RESEARCH, capture_output=True, check=True).stdout).hexdigest() == sha(path)
        for path in (ANALYZER, RUNNER, Path(__file__).resolve(), SPEC)
    ),
    "auditRuntimeExact": Path(sys.executable).resolve() == ENGINE_PYTHON.resolve() and sha(ENGINE_PYTHON) == spec["runtime"]["enginePythonSha256"] and sha(OPENVDB_MODULE) == spec["runtime"]["openVdbModuleSha256"] and sha(OPENVDB_LIBRARY) == spec["runtime"]["openVdbLibrarySha256"],
    "attempt84EvidenceExact": sha(ATTEMPT84) == spec["baseline"]["attempt84ResultFileSha256"] and attempt84["resultHash"] == spec["baseline"]["attempt84ResultHash"] and sha(ATTEMPT84_RECEIPT) == spec["baseline"]["attempt84ReceiptFileSha256"] and attempt84_receipt["receiptHash"] == spec["baseline"]["attempt84ReceiptHash"] and sha(ATTEMPT84_AUDIT) == spec["baseline"]["attempt84AuditFileSha256"] and attempt84_audit["auditHash"] == spec["baseline"]["attempt84AuditHash"] and attempt84_audit["status"] == "PASS",
    "admissionExact": admission["status"] == "PASS" and admission["workRootAbsentBeforeRun"] and admission["evidenceRootAbsentBeforeRun"],
    "resultSelfHash": result["resultHash"] == self_hash(result, "resultHash"),
    "receiptSelfHash": receipt["receiptHash"] == self_hash(receipt, "receiptHash") and receipt["resultHash"] == result["resultHash"],
    "processSelfHashArgvAndLogs": process["processHash"] == self_hash(process, "processHash") and process["argv"] == expected_argv and process["exitCode"] == 0 and process["stdoutSha256"] == sha(stdout) and process["stderrSha256"] == sha(stderr),
    "retainedCacheExactAndUnchanged": source_manifest["manifestHash"] == normalized_copy["manifestHash"] == spec["baseline"]["attempt84CacheManifestHash"] == receipt["sourceCacheManifestBefore"] == receipt["sourceCacheManifestAfter"],
    "copiedManifestBound": stored_copy_manifest["manifestHash"] == self_hash(stored_copy_manifest, "manifestHash") == copy_manifest["manifestHash"] == receipt["copiedCacheManifest"],
    "rootManifestsExact": stored_work_manifest == manifest(WORK) and stored_evidence_manifest == manifest(EVIDENCE, exclude={"evidence-manifest.pre-audit.json"}),
    "all36GridRostersReopened": len(recomputed) == 36 and all(row["particleGridType"] == "PointDataGrid" and row["velocityGridType"] == "Vec3SGrid" for row in recomputed),
    "all36SampleRowsRecomputed": sample_rows_match,
    "onsetRecomputed": metric["firstDataExpansionFrame"] == first_data and metric["firstMeshExpansionFrame"] == first_mesh,
    "expansionMetricsRecomputed": abs(metric["maximumParticleOccupancyExpansionFraction"] - maximum_particle) <= 1e-12 and abs(metric["maximumMeshVolumeExpansionFraction"] - maximum_mesh) <= 1e-12,
    "correlationsRecomputed": abs(metric["particleOccupancyMeshVolumePearsonCorrelation"] - particle_corr) <= 1e-12 and abs(metric["velocityOccupancyMeshVolumePearsonCorrelation"] - velocity_corr) <= 1e-12,
    "classificationRecomputed": result["status"] == "MEASURED_DATA_OCCUPANCY" and result["classification"] == classification == receipt["classification"],
    "noBlenderBakeRenderSaveNetwork": result["counts"] == {"enginePythonStarts": 1, "blenderStarts": 0, "fluidDataBakes": 0, "fluidMeshBakes": 0, "renders": 0, "blendSaves": 0, "networkCalls": 0, "retainedRootWrites": 0} and receipt["counts"] == result["counts"],
    "rootsBelowCeilings": sum(path.stat().st_size for path in WORK.rglob("*") if path.is_file()) <= spec["resourceCeilings"]["maximumWorkspaceBytes"] and sum(path.stat().st_size for path in EVIDENCE.rglob("*") if path.is_file()) <= spec["resourceCeilings"]["maximumEvidenceBytes"],
    "noSymlinksOrMedia": not any(path.is_symlink() or path.suffix.lower() in {".png", ".jpg", ".jpeg", ".exr", ".mov", ".mp4"} for root in (WORK, EVIDENCE) for path in root.rglob("*")),
}
audit = {
    "schemaVersion": "bfs.rc6RealImpactDataOccupancyC13IndependentAudit.v0.1",
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
final_manifest = manifest(EVIDENCE, exclude={"evidence-manifest.json"})
with (EVIDENCE / "evidence-manifest.json").open("x", encoding="utf-8") as handle:
    json.dump(final_manifest, handle, indent=2, sort_keys=True)
    handle.write("\n")
print("RC6_REAL_IMPACT_DATA_OCCUPANCY_C13_AUDIT=" + canonical(audit))
if audit["status"] != "PASS":
    raise RuntimeError("C13 independent audit failed")
