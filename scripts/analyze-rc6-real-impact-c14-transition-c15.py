#!/usr/bin/env python3
"""Measure copied C14 Data support and transition order against C12/C13."""

import argparse
import gzip
import hashlib
import json
import math
import struct
from pathlib import Path

import openvdb


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def self_hash(value, field):
    body = dict(value)
    body.pop(field, None)
    return hashlib.sha256(canonical(body).encode()).hexdigest()


def pearson(first, second):
    first_mean = sum(first) / len(first)
    second_mean = sum(second) / len(second)
    numerator = sum((a - first_mean) * (b - second_mean) for a, b in zip(first, second))
    denominator = math.sqrt(
        sum((a - first_mean) ** 2 for a in first)
        * sum((b - second_mean) ** 2 for b in second)
    )
    return numerator / denominator if denominator else 0.0


def first_frame(rows, predicate):
    return next((row["frame"] for row in rows if predicate(row)), None)


def terminal_timestep(config_path):
    raw = gzip.open(config_path, "rb").read()
    if len(raw) != 204:
        raise RuntimeError(f"unexpected config bytes: {config_path}")
    return {
        "seconds": float(struct.unpack_from("<f", raw, 20)[0]),
        "timeTotal": float(struct.unpack_from("<f", raw, 196)[0]),
    }


parser = argparse.ArgumentParser()
parser.add_argument("--cache-copy", type=Path, required=True)
parser.add_argument("--attempt86-result", type=Path, required=True)
parser.add_argument("--c13-result", type=Path, required=True)
parser.add_argument("--spec", type=Path, required=True)
parser.add_argument("--result", type=Path, required=True)
args = parser.parse_args()

cache = args.cache_copy.resolve(strict=True)
attempt86 = json.loads(args.attempt86_result.resolve(strict=True).read_text())
c13 = json.loads(args.c13_result.resolve(strict=True).read_text())
spec = json.loads(args.spec.resolve(strict=True).read_text())
result_path = args.result.resolve()
if result_path.exists():
    raise RuntimeError("C15 result already exists")
if spec["specHash"] != self_hash(spec, "specHash"):
    raise RuntimeError("C15 spec self hash mismatch")
if tuple(openvdb.LIBRARY_VERSION) != tuple(spec["runtime"]["openVdbLibraryVersion"]):
    raise RuntimeError("C15 OpenVDB library identity mismatch")
if openvdb.FILE_FORMAT_VERSION != spec["runtime"]["openVdbFileFormatVersion"]:
    raise RuntimeError("C15 OpenVDB file-format identity mismatch")

measurement = spec["measurement"]
mesh_by_frame = {row["frame"]: row for row in attempt86["fluidSamples"]}
c12_by_frame = {row["frame"]: row for row in c13["samples"]}
samples = []
for frame in range(measurement["frameStart"], measurement["frameEnd"] + 1):
    data_path = cache / "data" / f"fluid_data_{frame:04d}.vdb"
    grids = {grid.name: grid for grid in openvdb.readAllGridMetadata(str(data_path))}
    if set(grids) != set(measurement["requiredGridNames"]):
        raise RuntimeError(f"frame {frame}: unexpected VDB grid roster")
    particle = grids["particles"]
    velocity = grids["velocity"]
    pmeta = dict(particle.metadata)
    vmeta = dict(velocity.metadata)
    if [type(particle).__name__, type(velocity).__name__] != measurement["requiredGridTypes"]:
        raise RuntimeError(f"frame {frame}: VDB grid type mismatch")
    if list(pmeta["file_base_resolution"]) != measurement["requiredBaseResolution"]:
        raise RuntimeError(f"frame {frame}: particle base resolution mismatch")
    if list(vmeta["file_base_resolution"]) != measurement["requiredBaseResolution"]:
        raise RuntimeError(f"frame {frame}: velocity base resolution mismatch")
    voxel = float(pmeta["file_voxel_size"])
    if abs(voxel - measurement["requiredVoxelSizeMeters"]) > measurement["voxelToleranceMeters"]:
        raise RuntimeError(f"frame {frame}: particle voxel size mismatch")
    if abs(float(vmeta["file_voxel_size"]) - voxel) > 1e-12:
        raise RuntimeError(f"frame {frame}: grid voxel-size mismatch")
    mesh = mesh_by_frame[frame]
    prior = c12_by_frame[frame]
    timestep = terminal_timestep(cache / "config" / f"config_{frame:04d}.uni")
    samples.append({
        "frame": frame,
        "cupTiltDegrees": mesh["cupTiltDegrees"],
        "particleOccupiedVoxelCount": int(pmeta["file_voxel_count"]),
        "velocityOccupiedVoxelCount": int(vmeta["file_voxel_count"]),
        "particleGridBBoxMin": list(pmeta["file_bbox_min"]),
        "particleGridBBoxMax": list(pmeta["file_bbox_max"]),
        "velocityGridBBoxMin": list(vmeta["file_bbox_min"]),
        "velocityGridBBoxMax": list(vmeta["file_bbox_max"]),
        "voxelSizeMeters": voxel,
        "savedTerminalSubstepSeconds": timestep["seconds"],
        "savedTimeTotalSeconds": timestep["timeTotal"],
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

baseline_frame = measurement["coherentBaselineFrame"]
baseline = next(row for row in samples if row["frame"] == baseline_frame)
for row in samples:
    row["particleOccupancyDriftFromBaselineFraction"] = (
        row["particleOccupiedVoxelCount"] / baseline["particleOccupiedVoxelCount"] - 1.0
    )
    row["velocityOccupancyDriftFromBaselineFraction"] = (
        row["velocityOccupiedVoxelCount"] / baseline["velocityOccupiedVoxelCount"] - 1.0
    )
    row["meshVolumeDriftFromBaselineFraction"] = (
        row["meshVolumeCubicMeters"] / baseline["meshVolumeCubicMeters"] - 1.0
    )

window = [row for row in samples if row["frame"] >= measurement["comparisonFrameStart"]]
rules = spec["classificationRules"]
expansion = rules["expansionThresholdFraction"]
intrusion = rules["cupIntrusionThresholdFraction"]
first_data = first_frame(window, lambda row: row["particleOccupancyDriftFromBaselineFraction"] > expansion)
first_mesh = first_frame(window, lambda row: row["meshVolumeDriftFromBaselineFraction"] > expansion)
first_intrusion = first_frame(window, lambda row: row["cupSolidIntrusionFraction"] > intrusion)
first_source = first_frame(window, lambda row: abs(row["sourceVolumeErrorFraction"]) > rules["sourceVolumeErrorThresholdFraction"])
first_temporal = first_frame(window, lambda row: abs(row["temporalVolumeDriftFraction"]) > rules["temporalDriftThresholdFraction"])
first_positive = first_frame(window, lambda row: row["positiveBodyCount"] > rules["maximumPositiveBodies"])
first_components = first_frame(window, lambda row: row["connectedComponentCount"] > rules["maximumConnectedComponents"])
particle_mesh_correlation = pearson(
    [row["particleOccupiedVoxelCount"] for row in window],
    [row["meshVolumeCubicMeters"] for row in window],
)
if (
    first_intrusion is not None
    and first_data is not None
    and first_mesh is not None
    and first_intrusion < first_data <= first_mesh
    and particle_mesh_correlation >= rules["minimumStrongCorrelation"]
):
    classification = "CUP_INTRUSION_PRECEDES_LATER_DATA_MESH_EXPANSION"
elif (
    first_data is not None
    and first_mesh is not None
    and first_data <= first_mesh
    and particle_mesh_correlation >= rules["minimumStrongCorrelation"]
):
    classification = "DATA_MESH_EXPANSION_WITHOUT_PRIOR_CUP_INTRUSION"
elif first_data is None and first_mesh is not None:
    classification = "DATA_SUPPORT_STABLE_MESH_RECONSTRUCTION_SUSPECTED"
else:
    classification = "TRANSITION_ORDER_INCONCLUSIVE"

metrics = {
    "coherentBaselineFrame": baseline_frame,
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
    "particleOccupancyMeshVolumePearsonCorrelation": particle_mesh_correlation,
    "velocityOccupancyMeshVolumePearsonCorrelation": pearson(
        [row["velocityOccupiedVoxelCount"] for row in window],
        [row["meshVolumeCubicMeters"] for row in window],
    ),
    "maximumParticleOccupancyExpansionFraction": max(row["particleOccupancyDriftFromBaselineFraction"] for row in window),
    "maximumVelocityOccupancyExpansionFraction": max(row["velocityOccupancyDriftFromBaselineFraction"] for row in window),
    "maximumMeshVolumeExpansionFraction": max(row["meshVolumeDriftFromBaselineFraction"] for row in window),
    "minimumSavedTerminalSubstepSeconds": min(row["savedTerminalSubstepSeconds"] for row in window),
    "maximumSavedTerminalSubstepSeconds": max(row["savedTerminalSubstepSeconds"] for row in window),
    "theoreticalMinimumRegularSubstepSeconds": measurement["frameLengthSeconds"] / measurement["timestepsMax"],
    "c12FirstDataExpansionFrame": c13["metrics"]["firstDataExpansionFrame"],
    "c12FirstMeshExpansionFrame": c13["metrics"]["firstMeshExpansionFrame"],
}
checks = {
    "openVdbIdentityExact": True,
    "all36FramesMeasured": len(samples) == 36 and [row["frame"] for row in samples] == list(range(1, 37)),
    "exactGridRosterEveryFrame": True,
    "exactVoxelSizeEveryFrame": all(abs(row["voxelSizeMeters"] - measurement["requiredVoxelSizeMeters"]) <= measurement["voxelToleranceMeters"] for row in samples),
    "attempt86FailureBound": attempt86["resultHash"] == spec["baseline"]["attempt86ResultHash"] and attempt86["verdict"] == "FAIL_REAL_IMPACT_LIQUID_TIMESTEP_MAX_C14",
    "c13DiagnosticBound": c13["resultHash"] == spec["baseline"]["c13ResultHash"] and c13["classification"] == "DATA_SUPPORT_EXPANDS_WITH_MESH_MESH_ONLY_CAUSE_REJECTED",
    "coherentBaselineFrameExact": baseline_frame == 22,
}
result = {
    "schemaVersion": "bfs.rc6RealImpactC14TransitionC15Result.v0.1",
    "status": "MEASURED_TRANSITION_ORDER" if all(checks.values()) else "FAIL_HARNESS",
    "classification": classification if all(checks.values()) else "INCONCLUSIVE_HARNESS_FAILURE",
    "runtime": {
        "python": "3.13.13",
        "openVdbLibraryVersion": list(openvdb.LIBRARY_VERSION),
        "openVdbFileFormatVersion": openvdb.FILE_FORMAT_VERSION,
    },
    "metrics": metrics,
    "samples": samples,
    "checks": checks,
    "checkCount": len(checks),
    "passCount": sum(checks.values()),
    "interpretation": "Saved terminal substep is diagnostic metadata, not a solver-step count. Occupied Data support is not exact liquid mass. Transition order localizes the next layer without proving a repair.",
    "counts": {"enginePythonStarts": 1, "blenderStarts": 0, "fluidDataBakes": 0, "fluidMeshBakes": 0, "renders": 0, "blendSaves": 0, "networkCalls": 0, "retainedRootWrites": 0},
    "claimCeiling": spec["claimCeiling"],
}
result["resultHash"] = self_hash(result, "resultHash")
result_path.parent.mkdir(parents=True, exist_ok=True)
with result_path.open("x", encoding="utf-8") as handle:
    json.dump(result, handle, indent=2, sort_keys=True)
    handle.write("\n")
print("RC6_REAL_IMPACT_C14_TRANSITION_C15=" + canonical({"status": result["status"], "classification": result["classification"], "metrics": metrics, "resultHash": result["resultHash"]}))
if result["status"] != "MEASURED_TRANSITION_ORDER":
    raise RuntimeError("C15 analysis harness failed")
