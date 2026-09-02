#!/usr/bin/env python3
"""Compare copied attempt-59 VDB occupancy with attempt-58 and both Mesh curves."""

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
parser.add_argument("--attempt59-result", type=Path, required=True)
parser.add_argument("--attempt58-result", type=Path, required=True)
parser.add_argument("--result", type=Path, required=True)
args = parser.parse_args()
cache = args.cache_copy.resolve(strict=True)
attempt59 = json.loads(args.attempt59_result.resolve(strict=True).read_text())
attempt58 = json.loads(args.attempt58_result.resolve(strict=True).read_text())
result_path = args.result.resolve()
if result_path.exists():
    raise RuntimeError("effector-distance occupancy result already exists")
if tuple(openvdb.LIBRARY_VERSION) != (13, 0, 0) or openvdb.FILE_FORMAT_VERSION != 225:
    raise RuntimeError("OpenVDB identity mismatch")

mesh59 = {row["frame"]: row for row in attempt59["fluidSamples"]}
baseline58 = {row["frame"]: row for row in attempt58["samples"]}
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
    if tuple(particle_meta["file_base_resolution"]) != (96, 53, 62):
        raise RuntimeError(f"frame {frame}: particle VDB base resolution mismatch")
    if tuple(velocity_meta["file_base_resolution"]) != (96, 53, 62):
        raise RuntimeError(f"frame {frame}: velocity VDB base resolution mismatch")
    voxel = float(particle_meta["file_voxel_size"])
    if abs(voxel - 0.009375) > 1e-8 or abs(float(velocity_meta["file_voxel_size"]) - voxel) > 1e-12:
        raise RuntimeError(f"frame {frame}: VDB voxel size mismatch")
    occupied = int(particle_meta["file_voxel_count"])
    occupancy = occupied * voxel ** 3
    current_mesh = mesh59[frame]["meshVolumeCubicMeters"]
    current_mesh_drift = mesh59[frame]["temporalVolumeDriftFraction"]
    prior = baseline58[frame]
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
            "meshVolumeCubicMeters": current_mesh,
            "meshTemporalDriftFraction": current_mesh_drift,
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
final_occupancy_drift = samples[-1]["occupancyTemporalDriftFraction"]
final_mesh_drift = samples[-1]["meshTemporalDriftFraction"]
occupancy_mesh_correlation = pearson(occupancy, mesh)
improvement_correlation = pearson(occupancy_improvement, mesh_improvement)

if final_occupancy_drift < -0.15 and final_mesh_drift < -0.15 and occupancy_mesh_correlation >= 0.8:
    classification = "DATA_SPATIAL_SUPPORT_SHRINK_PERSISTS_AT_2P0"
elif max(abs(row["occupancyTemporalDriftFraction"]) for row in samples) <= 0.15 and abs(final_mesh_drift) > 0.15:
    classification = "DATA_SUPPORT_STABLE_SURFACE_RECONSTRUCTION_SUSPECTED"
else:
    classification = "DATA_MESH_RELATION_INCONCLUSIVE"

checks = {
    "openVdbIdentityExact": tuple(openvdb.LIBRARY_VERSION) == (13, 0, 0) and openvdb.FILE_FORMAT_VERSION == 225,
    "all24FramesMeasured": len(samples) == 24 and [row["frame"] for row in samples] == list(range(1, 25)),
    "exactGridRosterEveryFrame": all(row["particleGridType"] == "PointDataGrid" and row["velocityGridType"] == "Vec3SGrid" for row in samples),
    "exactVoxelSizeEveryFrame": all(abs(row["voxelSizeMeters"] - 0.009375) <= 1e-8 for row in samples),
    "attempt59PhysicalFailureBound": attempt59["resultHash"] == "ccb16ddd6e36c50ce4009e9a36afb3b249a6d9ff2715521129142588a3b3f2cb" and attempt59["configuration"]["cupEffectorSurfaceDistanceCells"] == 2.0 and not attempt59["checks"]["temporalVolumeDriftWithin15Percent"],
    "attempt58OccupancyBaselineBound": attempt58["resultHash"] == "f254bca2e485f037e2351d1b5248e8fec74f8d47d8179876734ae51b04c48ee9" and attempt58["classification"] == "DATA_SPATIAL_SUPPORT_SHRINKS_WITH_MESH",
}
result = {
    "schemaVersion": "bfs.rc6MovingLiquidEffectorDistanceOccupancyResult.v0.1",
    "status": "MEASURED_DATA_OCCUPANCY" if all(checks.values()) else "FAIL_HARNESS",
    "classification": classification if all(checks.values()) else "INCONCLUSIVE_HARNESS_FAILURE",
    "runtime": {"python": "3.13.13", "openVdbLibraryVersion": list(openvdb.LIBRARY_VERSION), "openVdbFileFormatVersion": openvdb.FILE_FORMAT_VERSION},
    "metrics": {
        "initialParticleOccupiedVoxelCount": samples[0]["particleOccupiedVoxelCount"],
        "finalParticleOccupiedVoxelCount": samples[-1]["particleOccupiedVoxelCount"],
        "finalParticleOccupancyTemporalDriftFraction": final_occupancy_drift,
        "maximumAbsoluteParticleOccupancyTemporalDriftFraction": max(abs(row["occupancyTemporalDriftFraction"]) for row in samples),
        "finalMeshTemporalVolumeDriftFraction": final_mesh_drift,
        "occupancyMeshPearsonCorrelation": occupancy_mesh_correlation,
        "finalOccupancyDriftImprovementVs2p5": occupancy_improvement[-1],
        "finalMeshDriftImprovementVs2p5": mesh_improvement[-1],
        "occupancyMeshImprovementPearsonCorrelation": improvement_correlation,
    },
    "samples": samples,
    "checks": checks,
    "checkCount": len(checks),
    "passCount": sum(checks.values()),
    "interpretation": "particle-grid occupied voxels measure sparse Data support, not exact mass; this comparison localizes whether the useful 2.0-cell response is present before Mesh reconstruction",
    "counts": {"enginePythonStarts": 1, "blenderStarts": 0, "fluidDataBakes": 0, "fluidMeshBakes": 0, "renders": 0, "blendSaves": 0, "networkCalls": 0, "retainedRootWrites": 0},
    "claimCeiling": "Read-only 24-frame copied-cache comparison. It cannot prove exact mass, causal sufficiency, moving-liquid PASS, impact, render or film quality.",
}
result["resultHash"] = self_hash(result, "resultHash")
write_exclusive(result_path, result)
print("RC6_MOVING_LIQUID_EFFECTOR_DISTANCE_OCCUPANCY=" + canonical({"status": result["status"], "classification": result["classification"], "resultHash": result["resultHash"], "metrics": result["metrics"]}))
if result["status"] != "MEASURED_DATA_OCCUPANCY":
    raise RuntimeError("effector-distance occupancy harness failed")
