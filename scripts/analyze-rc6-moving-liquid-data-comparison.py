#!/usr/bin/env python3
"""Reusable copied-VDB occupancy comparison for one current and one baseline run."""

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


def write_exclusive(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def pearson(first, second):
    mean_first = sum(first) / len(first)
    mean_second = sum(second) / len(second)
    numerator = sum((a - mean_first) * (b - mean_second) for a, b in zip(first, second))
    denominator = math.sqrt(
        sum((a - mean_first) ** 2 for a in first)
        * sum((b - mean_second) ** 2 for b in second)
    )
    return numerator / denominator if denominator else 0.0


parser = argparse.ArgumentParser()
parser.add_argument("--cache-copy", type=Path, required=True)
parser.add_argument("--current-result", type=Path, required=True)
parser.add_argument("--baseline-occupancy-result", type=Path, required=True)
parser.add_argument("--expected-current-result-hash", required=True)
parser.add_argument("--expected-baseline-result-hash", required=True)
parser.add_argument("--expected-surface-distance", type=float, required=True)
parser.add_argument("--expected-subframes", type=int, required=True)
parser.add_argument("--current-label", required=True)
parser.add_argument("--baseline-label", required=True)
parser.add_argument("--result", type=Path, required=True)
args = parser.parse_args()
cache = args.cache_copy.resolve(strict=True)
current = json.loads(args.current_result.resolve(strict=True).read_text())
baseline = json.loads(args.baseline_occupancy_result.resolve(strict=True).read_text())
result_path = args.result.resolve()
if result_path.exists():
    raise RuntimeError("moving-liquid Data comparison result already exists")
if tuple(openvdb.LIBRARY_VERSION) != (13, 0, 0) or openvdb.FILE_FORMAT_VERSION != 225:
    raise RuntimeError("moving-liquid Data comparison OpenVDB identity mismatch")

current_mesh = {row["frame"]: row for row in current["fluidSamples"]}
baseline_samples = {row["frame"]: row for row in baseline["samples"]}
samples = []
for frame in range(1, 25):
    path = cache / "data" / f"fluid_data_{frame:04d}.vdb"
    grids = {grid.name: grid for grid in openvdb.readAllGridMetadata(str(path))}
    if set(grids) != {"particles", "velocity"}:
        raise RuntimeError(f"frame {frame}: unexpected VDB grid roster {sorted(grids)}")
    particle = grids["particles"]
    velocity = grids["velocity"]
    particle_meta = dict(particle.metadata)
    velocity_meta = dict(velocity.metadata)
    if type(particle).__name__ != "PointDataGrid" or type(velocity).__name__ != "Vec3SGrid":
        raise RuntimeError(f"frame {frame}: VDB grid type mismatch")
    if tuple(particle_meta["file_base_resolution"]) != (96, 53, 62) or tuple(velocity_meta["file_base_resolution"]) != (96, 53, 62):
        raise RuntimeError(f"frame {frame}: VDB base resolution mismatch")
    voxel = float(particle_meta["file_voxel_size"])
    if abs(voxel - 0.009375) > 1e-8 or abs(float(velocity_meta["file_voxel_size"]) - voxel) > 1e-12:
        raise RuntimeError(f"frame {frame}: VDB voxel size mismatch")
    occupied = int(particle_meta["file_voxel_count"])
    occupancy = occupied * voxel ** 3
    mesh = current_mesh[frame]
    prior = baseline_samples[frame]
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
            "meshVolumeCubicMeters": mesh["meshVolumeCubicMeters"],
            "meshTemporalDriftFraction": mesh["temporalVolumeDriftFraction"],
            "baselineOccupancyTemporalDriftFraction": prior["occupancyTemporalDriftFraction"],
            "baselineMeshTemporalDriftFraction": prior["meshTemporalDriftFraction"],
        }
    )

initial_occupancy = samples[0]["particleOccupancyVolumeProxyCubicMeters"]
for row in samples:
    row["occupancyTemporalDriftFraction"] = row["particleOccupancyVolumeProxyCubicMeters"] / initial_occupancy - 1.0
    row["occupancyDriftChangeVsBaseline"] = row["occupancyTemporalDriftFraction"] - row["baselineOccupancyTemporalDriftFraction"]
    row["meshDriftChangeVsBaseline"] = row["meshTemporalDriftFraction"] - row["baselineMeshTemporalDriftFraction"]

occupancy = [row["particleOccupancyVolumeProxyCubicMeters"] for row in samples]
mesh = [row["meshVolumeCubicMeters"] for row in samples]
occupancy_change = [row["occupancyDriftChangeVsBaseline"] for row in samples]
mesh_change = [row["meshDriftChangeVsBaseline"] for row in samples]
drifts = [row["occupancyTemporalDriftFraction"] for row in samples]
final_mesh_drift = samples[-1]["meshTemporalDriftFraction"]
correlation_mesh = pearson(occupancy, mesh)
correlation_change = pearson(occupancy_change, mesh_change)
if drifts[-1] < -0.15 and final_mesh_drift < -0.15 and correlation_mesh >= 0.8:
    classification = "DATA_SPATIAL_SUPPORT_SHRINK_PERSISTS"
elif max(abs(value) for value in drifts) <= 0.15 and abs(final_mesh_drift) > 0.15:
    classification = "DATA_SUPPORT_STABLE_SURFACE_RECONSTRUCTION_SUSPECTED"
else:
    classification = "DATA_MESH_RELATION_INCONCLUSIVE"

checks = {
    "openVdbIdentityExact": tuple(openvdb.LIBRARY_VERSION) == (13, 0, 0) and openvdb.FILE_FORMAT_VERSION == 225,
    "all24FramesMeasured": len(samples) == 24 and [row["frame"] for row in samples] == list(range(1, 25)),
    "exactGridRosterEveryFrame": all(row["particleGridType"] == "PointDataGrid" and row["velocityGridType"] == "Vec3SGrid" for row in samples),
    "exactVoxelSizeEveryFrame": all(abs(row["voxelSizeMeters"] - 0.009375) <= 1e-8 for row in samples),
    "currentPhysicalResultBound": current["resultHash"] == args.expected_current_result_hash and current["configuration"]["cupEffectorSurfaceDistanceCells"] == args.expected_surface_distance and current["configuration"]["cupEffectorSubframes"] == args.expected_subframes and not current["checks"]["temporalVolumeDriftWithin15Percent"],
    "baselineOccupancyResultBound": baseline["resultHash"] == args.expected_baseline_result_hash and len(baseline["samples"]) == 24,
}
result = {
    "schemaVersion": "bfs.rc6MovingLiquidDataComparisonResult.v0.1",
    "status": "MEASURED_DATA_COMPARISON" if all(checks.values()) else "FAIL_HARNESS",
    "classification": classification if all(checks.values()) else "INCONCLUSIVE_HARNESS_FAILURE",
    "labels": {"current": args.current_label, "baseline": args.baseline_label},
    "runtime": {"python": "3.13.13", "openVdbLibraryVersion": list(openvdb.LIBRARY_VERSION), "openVdbFileFormatVersion": openvdb.FILE_FORMAT_VERSION},
    "metrics": {
        "initialParticleOccupiedVoxelCount": samples[0]["particleOccupiedVoxelCount"],
        "finalParticleOccupiedVoxelCount": samples[-1]["particleOccupiedVoxelCount"],
        "finalParticleOccupancyTemporalDriftFraction": drifts[-1],
        "maximumAbsoluteParticleOccupancyTemporalDriftFraction": max(abs(value) for value in drifts),
        "finalMeshTemporalVolumeDriftFraction": final_mesh_drift,
        "occupancyMeshPearsonCorrelation": correlation_mesh,
        "finalOccupancyDriftChangeVsBaseline": occupancy_change[-1],
        "finalMeshDriftChangeVsBaseline": mesh_change[-1],
        "occupancyMeshChangePearsonCorrelation": correlation_change,
    },
    "samples": samples,
    "checks": checks,
    "checkCount": len(checks),
    "passCount": sum(checks.values()),
    "interpretation": "occupied particle-grid voxels measure sparse Data support rather than exact liquid mass; the comparison tests whether a single-variable response exists before Mesh",
    "counts": {"enginePythonStarts": 1, "blenderStarts": 0, "fluidDataBakes": 0, "fluidMeshBakes": 0, "renders": 0, "blendSaves": 0, "networkCalls": 0, "retainedRootWrites": 0},
    "claimCeiling": "Read-only 24-frame copied-cache Data comparison. It cannot prove exact mass, causal sufficiency, moving-liquid PASS, impact, render or film quality.",
}
result["resultHash"] = self_hash(result, "resultHash")
write_exclusive(result_path, result)
print("RC6_MOVING_LIQUID_DATA_COMPARISON=" + canonical({"status": result["status"], "classification": result["classification"], "resultHash": result["resultHash"], "metrics": result["metrics"]}))
if result["status"] != "MEASURED_DATA_COMPARISON":
    raise RuntimeError("moving-liquid Data comparison harness failed")
