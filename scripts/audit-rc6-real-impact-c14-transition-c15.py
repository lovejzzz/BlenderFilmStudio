#!/usr/bin/env python3
"""Independently audit the copied-cache C15 transition diagnosis."""

import gzip
import hashlib
import json
import math
import struct
import subprocess
import sys
from pathlib import Path

import openvdb


RESEARCH = Path(__file__).resolve().parents[1]
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-real-impact-c14-transition-c15-attempt-87")
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-c14-transition-c15-attempt-87"
SOURCE_CACHE = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-real-impact-liquid-timestep-max-c14-attempt-86/mantaflow-cache")
ATTEMPT86_ROOT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-timestep-max-c14-attempt-86"
C13_ROOT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-data-occupancy-c13-attempt-85"
ENGINE_PYTHON = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC5-2026-09-01-attempt-01/build/bin/Film Studio Engine F0.app/Contents/Resources/5.2/python/bin/python3.13")
OPENVDB_MODULE = ENGINE_PYTHON.parent.parent / "lib/python3.13/site-packages/openvdb.cpython-313-darwin.so"
OPENVDB_LIBRARY = ENGINE_PYTHON.parents[3] / "lib/libopenvdb.dylib"
ANALYZER = RESEARCH / "scripts/analyze-rc6-real-impact-c14-transition-c15.py"
RUNNER = RESEARCH / "scripts/run-rc6-real-impact-c14-transition-c15.py"
SPEC = RESEARCH / "specs/ai-native-studio-rc6-real-impact-c14-transition-c15.v0.98.json"


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
    first_mean = sum(first) / len(first)
    second_mean = sum(second) / len(second)
    numerator = sum((a - first_mean) * (b - second_mean) for a, b in zip(first, second))
    denominator = math.sqrt(sum((a - first_mean) ** 2 for a in first) * sum((b - second_mean) ** 2 for b in second))
    return numerator / denominator if denominator else 0.0


def first_frame(rows, predicate):
    return next((row["frame"] for row in rows if predicate(row)), None)


def terminal_timestep(path):
    raw = gzip.open(path, "rb").read()
    if len(raw) != 204:
        raise RuntimeError(f"unexpected config bytes: {path}")
    return float(struct.unpack_from("<f", raw, 20)[0]), float(struct.unpack_from("<f", raw, 196)[0])


spec = json.loads(SPEC.read_text())
result = json.loads((EVIDENCE / "result.json").read_text())
receipt = json.loads((EVIDENCE / "receipt.json").read_text())
process = json.loads((EVIDENCE / "processes/01-transition.json").read_text())
admission = json.loads((EVIDENCE / "admission.json").read_text())
attempt86 = json.loads((ATTEMPT86_ROOT / "result.json").read_text())
attempt86_receipt = json.loads((ATTEMPT86_ROOT / "receipt.json").read_text())
attempt86_audit = json.loads((ATTEMPT86_ROOT / "independent-audit.json").read_text())
c13 = json.loads((C13_ROOT / "result.json").read_text())
c13_receipt = json.loads((C13_ROOT / "receipt.json").read_text())
c13_audit = json.loads((C13_ROOT / "independent-audit.json").read_text())
cache = WORK / "cache-copy"
measurement = spec["measurement"]
mesh_by_frame = {row["frame"]: row for row in attempt86["fluidSamples"]}
c12_by_frame = {row["frame"]: row for row in c13["samples"]}
recomputed = []
for frame in range(1, 37):
    grids = {grid.name: grid for grid in openvdb.readAllGridMetadata(str(cache / "data" / f"fluid_data_{frame:04d}.vdb"))}
    particle = grids["particles"]
    velocity = grids["velocity"]
    pmeta = dict(particle.metadata)
    vmeta = dict(velocity.metadata)
    mesh = mesh_by_frame[frame]
    prior = c12_by_frame[frame]
    timestep, time_total = terminal_timestep(cache / "config" / f"config_{frame:04d}.uni")
    recomputed.append({
        "frame": frame,
        "cupTiltDegrees": mesh["cupTiltDegrees"],
        "particleOccupiedVoxelCount": int(pmeta["file_voxel_count"]),
        "velocityOccupiedVoxelCount": int(vmeta["file_voxel_count"]),
        "particleGridBBoxMin": list(pmeta["file_bbox_min"]),
        "particleGridBBoxMax": list(pmeta["file_bbox_max"]),
        "velocityGridBBoxMin": list(vmeta["file_bbox_min"]),
        "velocityGridBBoxMax": list(vmeta["file_bbox_max"]),
        "voxelSizeMeters": float(pmeta["file_voxel_size"]),
        "savedTerminalSubstepSeconds": timestep,
        "savedTimeTotalSeconds": time_total,
        "meshVolumeCubicMeters": mesh["meshVolumeCubicMeters"],
        "sourceVolumeErrorFraction": mesh["sourceVolumeErrorFraction"],
        "temporalVolumeDriftFraction": mesh["temporalVolumeDriftFraction"],
        "connectedComponentCount": mesh["connectedComponentCount"],
        "positiveBodyCount": mesh["positiveBodyCount"],
        "largestComponentFraction": mesh["largestComponentFraction"],
        "cupSolidIntrusionFraction": mesh["cupSolidIntrusionFraction"],
        "outsideCupFraction": mesh["outsideCupInteriorPlusOneVoxelFraction"],
        "c12ParticleOccupiedVoxelCount": prior["particleOccupiedVoxelCount"],
        "c12MeshVolumeCubicMeters": prior["meshVolumeCubicMeters"],
    })
baseline = recomputed[measurement["coherentBaselineFrame"] - 1]
for row in recomputed:
    row["particleOccupancyDriftFromBaselineFraction"] = row["particleOccupiedVoxelCount"] / baseline["particleOccupiedVoxelCount"] - 1.0
    row["velocityOccupancyDriftFromBaselineFraction"] = row["velocityOccupiedVoxelCount"] / baseline["velocityOccupiedVoxelCount"] - 1.0
    row["meshVolumeDriftFromBaselineFraction"] = row["meshVolumeCubicMeters"] / baseline["meshVolumeCubicMeters"] - 1.0
window = [row for row in recomputed if row["frame"] >= measurement["comparisonFrameStart"]]
rules = spec["classificationRules"]
first_data = first_frame(window, lambda row: row["particleOccupancyDriftFromBaselineFraction"] > rules["expansionThresholdFraction"])
first_mesh = first_frame(window, lambda row: row["meshVolumeDriftFromBaselineFraction"] > rules["expansionThresholdFraction"])
first_intrusion = first_frame(window, lambda row: row["cupSolidIntrusionFraction"] > rules["cupIntrusionThresholdFraction"])
first_source = first_frame(window, lambda row: abs(row["sourceVolumeErrorFraction"]) > rules["sourceVolumeErrorThresholdFraction"])
first_temporal = first_frame(window, lambda row: abs(row["temporalVolumeDriftFraction"]) > rules["temporalDriftThresholdFraction"])
first_positive = first_frame(window, lambda row: row["positiveBodyCount"] > rules["maximumPositiveBodies"])
first_components = first_frame(window, lambda row: row["connectedComponentCount"] > rules["maximumConnectedComponents"])
particle_corr = pearson([row["particleOccupiedVoxelCount"] for row in window], [row["meshVolumeCubicMeters"] for row in window])
velocity_corr = pearson([row["velocityOccupiedVoxelCount"] for row in window], [row["meshVolumeCubicMeters"] for row in window])
if first_intrusion is not None and first_data is not None and first_mesh is not None and first_intrusion < first_data <= first_mesh and particle_corr >= rules["minimumStrongCorrelation"]:
    classification = "CUP_INTRUSION_PRECEDES_LATER_DATA_MESH_EXPANSION"
elif first_data is not None and first_mesh is not None and first_data <= first_mesh and particle_corr >= rules["minimumStrongCorrelation"]:
    classification = "DATA_MESH_EXPANSION_WITHOUT_PRIOR_CUP_INTRUSION"
elif first_data is None and first_mesh is not None:
    classification = "DATA_SUPPORT_STABLE_MESH_RECONSTRUCTION_SUSPECTED"
else:
    classification = "TRANSITION_ORDER_INCONCLUSIVE"
metrics = {
    "coherentBaselineFrame": measurement["coherentBaselineFrame"],
    "baselineParticleOccupiedVoxelCount": baseline["particleOccupiedVoxelCount"],
    "baselineVelocityOccupiedVoxelCount": baseline["velocityOccupiedVoxelCount"],
    "baselineMeshVolumeCubicMeters": baseline["meshVolumeCubicMeters"],
    "firstCupSolidIntrusionFrame": first_intrusion,
    "firstDataExpansionFrame": first_data,
    "firstMeshExpansionFrame": first_mesh,
    "firstSourceVolumeFailureFrame": first_source,
    "firstTemporalDriftFailureFrame": first_temporal,
    "firstPositiveBodyFailureFrame": first_positive,
    "firstConnectedComponentFailureFrame": first_components,
    "particleOccupancyMeshVolumePearsonCorrelation": particle_corr,
    "velocityOccupancyMeshVolumePearsonCorrelation": velocity_corr,
    "maximumParticleOccupancyExpansionFraction": max(row["particleOccupancyDriftFromBaselineFraction"] for row in window),
    "maximumVelocityOccupancyExpansionFraction": max(row["velocityOccupancyDriftFromBaselineFraction"] for row in window),
    "maximumMeshVolumeExpansionFraction": max(row["meshVolumeDriftFromBaselineFraction"] for row in window),
    "minimumSavedTerminalSubstepSeconds": min(row["savedTerminalSubstepSeconds"] for row in window),
    "maximumSavedTerminalSubstepSeconds": max(row["savedTerminalSubstepSeconds"] for row in window),
    "theoreticalMinimumRegularSubstepSeconds": measurement["frameLengthSeconds"] / measurement["timestepsMax"],
    "c12FirstDataExpansionFrame": c13["metrics"]["firstDataExpansionFrame"],
    "c12FirstMeshExpansionFrame": c13["metrics"]["firstMeshExpansionFrame"],
}
expected_argv = [str(ENGINE_PYTHON), str(ANALYZER), "--cache-copy", str(cache), "--attempt86-result", str(ATTEMPT86_ROOT / "result.json"), "--c13-result", str(C13_ROOT / "result.json"), "--spec", str(SPEC), "--result", str(EVIDENCE / "result.json")]
source_manifest = manifest(SOURCE_CACHE)
copy_manifest = manifest(cache)
normalized_copy = dict(copy_manifest)
normalized_copy["root"] = str(SOURCE_CACHE)
normalized_copy["manifestHash"] = self_hash(normalized_copy, "manifestHash")
stored_copy_manifest = json.loads((EVIDENCE / "copied-cache-manifest.json").read_text())
stored_work_manifest = json.loads((EVIDENCE / "work-manifest.json").read_text())
stored_evidence_manifest = json.loads((EVIDENCE / "evidence-manifest.pre-audit.json").read_text())
stdout = EVIDENCE / "logs/01-transition.stdout.log"
stderr = EVIDENCE / "logs/01-transition.stderr.log"
tool_hashes = {row["uri"]: row["sha256"] for row in spec["tools"]}
checks = {
    "specSelfHash": spec["specHash"] == self_hash(spec, "specHash"),
    "frozenToolIdentities": tool_hashes == {str(ANALYZER.relative_to(RESEARCH)): sha(ANALYZER), str(RUNNER.relative_to(RESEARCH)): sha(RUNNER), str(Path(__file__).resolve().relative_to(RESEARCH)): sha(Path(__file__).resolve())},
    "executionCommitExact": receipt["researchExecutionCommit"] == subprocess.run(["git", "rev-parse", "HEAD"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.strip(),
    "committedToolsAndSpecExact": all(hashlib.sha256(subprocess.run(["git", "show", f"HEAD:{str(path.relative_to(RESEARCH))}"], cwd=RESEARCH, capture_output=True, check=True).stdout).hexdigest() == sha(path) for path in (ANALYZER, RUNNER, Path(__file__).resolve(), SPEC)),
    "auditRuntimeExact": Path(sys.executable).resolve() == ENGINE_PYTHON.resolve() and sha(ENGINE_PYTHON) == spec["runtime"]["enginePythonSha256"] and sha(OPENVDB_MODULE) == spec["runtime"]["openVdbModuleSha256"] and sha(OPENVDB_LIBRARY) == spec["runtime"]["openVdbLibrarySha256"],
    "attempt86EvidenceExact": sha(ATTEMPT86_ROOT / "result.json") == spec["baseline"]["attempt86ResultFileSha256"] and attempt86["resultHash"] == spec["baseline"]["attempt86ResultHash"] and sha(ATTEMPT86_ROOT / "receipt.json") == spec["baseline"]["attempt86ReceiptFileSha256"] and attempt86_receipt["receiptHash"] == spec["baseline"]["attempt86ReceiptHash"] and sha(ATTEMPT86_ROOT / "independent-audit.json") == spec["baseline"]["attempt86AuditFileSha256"] and attempt86_audit["auditHash"] == spec["baseline"]["attempt86AuditHash"] and attempt86_audit["status"] == "PASS",
    "c13EvidenceExact": sha(C13_ROOT / "result.json") == spec["baseline"]["c13ResultFileSha256"] and c13["resultHash"] == spec["baseline"]["c13ResultHash"] and sha(C13_ROOT / "receipt.json") == spec["baseline"]["c13ReceiptFileSha256"] and c13_receipt["receiptHash"] == spec["baseline"]["c13ReceiptHash"] and sha(C13_ROOT / "independent-audit.json") == spec["baseline"]["c13AuditFileSha256"] and c13_audit["auditHash"] == spec["baseline"]["c13AuditHash"] and c13_audit["status"] == "PASS",
    "admissionExact": admission["status"] == "PASS" and admission["workRootAbsentBeforeRun"] and admission["evidenceRootAbsentBeforeRun"],
    "resultSelfHash": result["resultHash"] == self_hash(result, "resultHash"),
    "receiptSelfHash": receipt["receiptHash"] == self_hash(receipt, "receiptHash") and receipt["resultHash"] == result["resultHash"],
    "processSelfHashArgvAndLogs": process["processHash"] == self_hash(process, "processHash") and process["argv"] == expected_argv and process["exitCode"] == 0 and process["stdoutSha256"] == sha(stdout) and process["stderrSha256"] == sha(stderr),
    "retainedCacheExactAndUnchanged": source_manifest["manifestHash"] == normalized_copy["manifestHash"] == spec["baseline"]["attempt86CacheManifestHash"] == receipt["sourceCacheManifestBefore"] == receipt["sourceCacheManifestAfter"],
    "copiedManifestBound": stored_copy_manifest["manifestHash"] == self_hash(stored_copy_manifest, "manifestHash") == copy_manifest["manifestHash"] == receipt["copiedCacheManifest"],
    "rootManifestsExact": stored_work_manifest == manifest(WORK) and stored_evidence_manifest == manifest(EVIDENCE, exclude={"evidence-manifest.pre-audit.json"}),
    "all36GridRostersReopened": len(recomputed) == 36 and all(abs(row["voxelSizeMeters"] - measurement["requiredVoxelSizeMeters"]) <= measurement["voxelToleranceMeters"] for row in recomputed),
    "all36SampleRowsRecomputed": result["samples"] == recomputed,
    "transitionMetricsRecomputed": result["metrics"] == metrics,
    "classificationRecomputed": result["status"] == "MEASURED_TRANSITION_ORDER" and result["classification"] == classification == receipt["classification"],
    "terminalSubstepClaimBounded": "not a solver-step count" in result["interpretation"],
    "noBlenderBakeRenderSaveNetwork": result["counts"] == {"enginePythonStarts": 1, "blenderStarts": 0, "fluidDataBakes": 0, "fluidMeshBakes": 0, "renders": 0, "blendSaves": 0, "networkCalls": 0, "retainedRootWrites": 0} and receipt["counts"] == result["counts"],
    "rootsBelowCeilings": sum(path.stat().st_size for path in WORK.rglob("*") if path.is_file()) <= spec["resourceCeilings"]["maximumWorkspaceBytes"] and sum(path.stat().st_size for path in EVIDENCE.rglob("*") if path.is_file()) <= spec["resourceCeilings"]["maximumEvidenceBytes"],
    "noSymlinksOrMedia": not any(path.is_symlink() or path.suffix.lower() in {".png", ".jpg", ".jpeg", ".exr", ".mov", ".mp4"} for root in (WORK, EVIDENCE) for path in root.rglob("*")),
}
audit = {
    "schemaVersion": "bfs.rc6RealImpactC14TransitionC15IndependentAudit.v0.1",
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
print("RC6_REAL_IMPACT_C14_TRANSITION_C15_AUDIT=" + canonical(audit))
if audit["status"] != "PASS":
    raise RuntimeError("C15 independent audit failed")
