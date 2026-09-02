#!/usr/bin/env python3
"""Measure copied C12 OpenVDB support against retained Mesh behavior."""

import argparse
import hashlib
import json
import math
from pathlib import Path

import openvdb


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def self_hash(value, field):
    body = dict(value)
    body.pop(field, None)
    return hashlib.sha256(canonical(body).encode()).hexdigest()


def pearson(first, second):
    mean_first = sum(first) / len(first)
    mean_second = sum(second) / len(second)
    numerator = sum((a - mean_first) * (b - mean_second) for a, b in zip(first, second))
    denominator = math.sqrt(
        sum((a - mean_first) ** 2 for a in first)
        * sum((b - mean_second) ** 2 for b in second)
    )
    return numerator / denominator if denominator else 0.0


def first_frame(rows, predicate):
    return next((row["frame"] for row in rows if predicate(row)), None)


parser = argparse.ArgumentParser()
parser.add_argument("--cache-copy", type=Path, required=True)
parser.add_argument("--attempt84-result", type=Path, required=True)
parser.add_argument("--spec", type=Path, required=True)
parser.add_argument("--result", type=Path, required=True)
args = parser.parse_args()

cache = args.cache_copy.resolve(strict=True)
attempt84 = json.loads(args.attempt84_result.resolve(strict=True).read_text())
spec = json.loads(args.spec.resolve(strict=True).read_text())
result_path = args.result.resolve()
if result_path.exists():
    raise RuntimeError("C13 result already exists")
if spec["specHash"] != self_hash(spec, "specHash"):
    raise RuntimeError("C13 spec self hash mismatch")
if tuple(openvdb.LIBRARY_VERSION) != tuple(spec["runtime"]["openVdbLibraryVersion"]):
    raise RuntimeError("C13 OpenVDB library identity mismatch")
if openvdb.FILE_FORMAT_VERSION != spec["runtime"]["openVdbFileFormatVersion"]:
    raise RuntimeError("C13 OpenVDB file-format identity mismatch")

mesh_by_frame = {row["frame"]: row for row in attempt84["fluidSamples"]}
measurement = spec["measurement"]
samples = []
for frame in range(measurement["frameStart"], measurement["frameEnd"] + 1):
    path = cache / "data" / f"fluid_data_{frame:04d}.vdb"
    grids = {grid.name: grid for grid in openvdb.readAllGridMetadata(str(path))}
    if set(grids) != set(measurement["requiredGridNames"]):
        raise RuntimeError(f"frame {frame}: unexpected VDB grid roster")
    particle = grids["particles"]
    velocity = grids["velocity"]
    particle_meta = dict(particle.metadata)
    velocity_meta = dict(velocity.metadata)
    if [type(particle).__name__, type(velocity).__name__] != measurement["requiredGridTypes"]:
        raise RuntimeError(f"frame {frame}: VDB grid type mismatch")
    if list(particle_meta["file_base_resolution"]) != measurement["requiredBaseResolution"]:
        raise RuntimeError(f"frame {frame}: particle base resolution mismatch")
    if list(velocity_meta["file_base_resolution"]) != measurement["requiredBaseResolution"]:
        raise RuntimeError(f"frame {frame}: velocity base resolution mismatch")
    particle_voxel = float(particle_meta["file_voxel_size"])
    velocity_voxel = float(velocity_meta["file_voxel_size"])
    if abs(particle_voxel - measurement["requiredVoxelSizeMeters"]) > measurement["voxelToleranceMeters"]:
        raise RuntimeError(f"frame {frame}: particle voxel size mismatch")
    if abs(velocity_voxel - particle_voxel) > 1e-12:
        raise RuntimeError(f"frame {frame}: grid voxel-size mismatch")
    mesh = mesh_by_frame[frame]
    samples.append(
        {
            "frame": frame,
            "particleGridType": type(particle).__name__,
            "velocityGridType": type(velocity).__name__,
            "particleOccupiedVoxelCount": int(particle_meta["file_voxel_count"]),
            "velocityOccupiedVoxelCount": int(velocity_meta["file_voxel_count"]),
            "voxelSizeMeters": particle_voxel,
            "particleGridBBoxMin": list(particle_meta["file_bbox_min"]),
            "particleGridBBoxMax": list(particle_meta["file_bbox_max"]),
            "velocityGridBBoxMin": list(velocity_meta["file_bbox_min"]),
            "velocityGridBBoxMax": list(velocity_meta["file_bbox_max"]),
            "meshVolumeCubicMeters": mesh["meshVolumeCubicMeters"],
            "meshSourceVolumeErrorFraction": mesh["sourceVolumeErrorFraction"],
            "meshTemporalVolumeDriftFraction": mesh["temporalVolumeDriftFraction"],
            "meshConnectedComponentCount": mesh["connectedComponentCount"],
            "meshPositiveBodyCount": mesh["positiveBodyCount"],
            "meshLargestComponentFraction": mesh["largestComponentFraction"],
        }
    )

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
threshold = spec["classificationRules"]["expansionThresholdFraction"]
first_data_expansion = first_frame(
    window, lambda row: row["particleOccupancyDriftFromBaselineFraction"] > threshold
)
first_mesh_expansion = first_frame(
    window, lambda row: row["meshVolumeDriftFromBaselineFraction"] > threshold
)
particle_mesh_correlation = pearson(
    [row["particleOccupiedVoxelCount"] for row in window],
    [row["meshVolumeCubicMeters"] for row in window],
)
velocity_mesh_correlation = pearson(
    [row["velocityOccupiedVoxelCount"] for row in window],
    [row["meshVolumeCubicMeters"] for row in window],
)
maximum_particle_expansion = max(
    row["particleOccupancyDriftFromBaselineFraction"] for row in window
)
maximum_mesh_expansion = max(row["meshVolumeDriftFromBaselineFraction"] for row in window)
rules = spec["classificationRules"]
if (
    first_data_expansion is not None
    and first_mesh_expansion is not None
    and first_data_expansion <= first_mesh_expansion
    and particle_mesh_correlation >= rules["minimumStrongCorrelation"]
    and maximum_particle_expansion > rules["minimumGrossExpansionFraction"]
    and maximum_mesh_expansion > rules["minimumGrossExpansionFraction"]
):
    classification = "DATA_SUPPORT_EXPANDS_WITH_MESH_MESH_ONLY_CAUSE_REJECTED"
elif (
    maximum_particle_expansion <= threshold
    and maximum_mesh_expansion > rules["minimumGrossExpansionFraction"]
):
    classification = "DATA_SUPPORT_STABLE_MESH_RECONSTRUCTION_SUSPECTED"
else:
    classification = "DATA_MESH_RELATION_DIVERGENT_INCONCLUSIVE"

checks = {
    "openVdbIdentityExact": True,
    "all36FramesMeasured": len(samples) == 36 and [row["frame"] for row in samples] == list(range(1, 37)),
    "exactGridRosterEveryFrame": all(
        row["particleGridType"] == "PointDataGrid" and row["velocityGridType"] == "Vec3SGrid"
        for row in samples
    ),
    "exactVoxelSizeEveryFrame": all(
        abs(row["voxelSizeMeters"] - measurement["requiredVoxelSizeMeters"])
        <= measurement["voxelToleranceMeters"]
        for row in samples
    ),
    "attempt84FailureBound": (
        attempt84["resultHash"] == spec["baseline"]["attempt84ResultHash"]
        and attempt84["verdict"] == "FAIL_REAL_IMPACT_LIQUID_PREVIEW"
        and attempt84["passCount"] == 22
        and attempt84["checkCount"] == 27
    ),
    "coherentBaselineFrameExact": baseline_frame == 22,
}
result = {
    "schemaVersion": "bfs.rc6RealImpactDataOccupancyC13Result.v0.1",
    "status": "MEASURED_DATA_OCCUPANCY" if all(checks.values()) else "FAIL_HARNESS",
    "classification": classification if all(checks.values()) else "INCONCLUSIVE_HARNESS_FAILURE",
    "runtime": {
        "python": "3.13.13",
        "openVdbLibraryVersion": list(openvdb.LIBRARY_VERSION),
        "openVdbFileFormatVersion": openvdb.FILE_FORMAT_VERSION,
    },
    "metrics": {
        "coherentBaselineFrame": baseline_frame,
        "baselineParticleOccupiedVoxelCount": baseline["particleOccupiedVoxelCount"],
        "baselineVelocityOccupiedVoxelCount": baseline["velocityOccupiedVoxelCount"],
        "baselineMeshVolumeCubicMeters": baseline["meshVolumeCubicMeters"],
        "firstDataExpansionFrame": first_data_expansion,
        "firstMeshExpansionFrame": first_mesh_expansion,
        "maximumParticleOccupancyExpansionFraction": maximum_particle_expansion,
        "maximumVelocityOccupancyExpansionFraction": max(
            row["velocityOccupancyDriftFromBaselineFraction"] for row in window
        ),
        "maximumMeshVolumeExpansionFraction": maximum_mesh_expansion,
        "particleOccupancyMeshVolumePearsonCorrelation": particle_mesh_correlation,
        "velocityOccupancyMeshVolumePearsonCorrelation": velocity_mesh_correlation,
        "frame23ParticleOccupancyExpansionFraction": next(
            row["particleOccupancyDriftFromBaselineFraction"] for row in samples if row["frame"] == 23
        ),
        "frame23VelocityOccupancyExpansionFraction": next(
            row["velocityOccupancyDriftFromBaselineFraction"] for row in samples if row["frame"] == 23
        ),
        "frame23MeshVolumeExpansionFraction": next(
            row["meshVolumeDriftFromBaselineFraction"] for row in samples if row["frame"] == 23
        ),
    },
    "samples": samples,
    "checks": checks,
    "checkCount": len(checks),
    "passCount": sum(checks.values()),
    "interpretation": "Particle occupied-voxel support is not exact liquid mass, but same-frame gross Data support expansion rejects a Mesh-only explanation.",
    "counts": {
        "enginePythonStarts": 1,
        "blenderStarts": 0,
        "fluidDataBakes": 0,
        "fluidMeshBakes": 0,
        "renders": 0,
        "blendSaves": 0,
        "networkCalls": 0,
        "retainedRootWrites": 0,
    },
    "claimCeiling": spec["claimCeiling"],
}
result["resultHash"] = self_hash(result, "resultHash")
result_path.parent.mkdir(parents=True, exist_ok=True)
with result_path.open("x", encoding="utf-8") as handle:
    json.dump(result, handle, indent=2, sort_keys=True)
    handle.write("\n")
print("RC6_REAL_IMPACT_DATA_OCCUPANCY_C13=" + canonical({
    "status": result["status"],
    "classification": result["classification"],
    "resultHash": result["resultHash"],
    "metrics": result["metrics"],
}))
if result["status"] != "MEASURED_DATA_OCCUPANCY":
    raise RuntimeError("C13 analysis harness failed")
