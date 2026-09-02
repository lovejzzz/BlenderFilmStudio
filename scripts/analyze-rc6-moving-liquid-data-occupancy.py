#!/usr/bin/env python3
"""Read copied Mantaflow VDB metadata and compare occupancy support with Mesh."""

import argparse
import hashlib
import json
import math
from pathlib import Path

import openvdb


SOURCE_VOLUME = 0.0013283283766941


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
    denominator = math.sqrt(sum((a - mean_first) ** 2 for a in first) * sum((b - mean_second) ** 2 for b in second))
    return numerator / denominator if denominator else 0.0


parser = argparse.ArgumentParser()
parser.add_argument("--cache-copy", type=Path, required=True)
parser.add_argument("--attempt56-result", type=Path, required=True)
parser.add_argument("--attempt57-result", type=Path, required=True)
parser.add_argument("--result", type=Path, required=True)
args = parser.parse_args()
cache = args.cache_copy.resolve(strict=True)
attempt56 = json.loads(args.attempt56_result.resolve(strict=True).read_text())
attempt57 = json.loads(args.attempt57_result.resolve(strict=True).read_text())
result_path = args.result.resolve()
if result_path.exists():
    raise RuntimeError("Data occupancy diagnostic result already exists")
if tuple(openvdb.LIBRARY_VERSION) != (13, 0, 0) or openvdb.FILE_FORMAT_VERSION != 225:
    raise RuntimeError("Data occupancy diagnostic OpenVDB identity mismatch")

mesh_by_frame = {row["frame"]: row for row in attempt56["fluidSamples"]}
particles_by_frame = {row["frame"]: row for row in attempt57["particleSamples"]}
samples = []
for frame in range(1, 25):
    path = cache / "data" / f"fluid_data_{frame:04d}.vdb"
    metadata_grids = openvdb.readAllGridMetadata(str(path))
    grids = {grid.name: grid for grid in metadata_grids}
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
    particle_voxel = float(particle_meta["file_voxel_size"])
    velocity_voxel = float(velocity_meta["file_voxel_size"])
    if abs(particle_voxel - 0.009375) > 1e-8 or abs(velocity_voxel - particle_voxel) > 1e-12:
        raise RuntimeError(f"frame {frame}: VDB voxel size mismatch")
    particle_voxels = int(particle_meta["file_voxel_count"])
    velocity_voxels = int(velocity_meta["file_voxel_count"])
    occupancy_proxy = particle_voxels * particle_voxel ** 3
    velocity_support = velocity_voxels * velocity_voxel ** 3
    row57 = particles_by_frame[frame]
    row56 = mesh_by_frame[frame]
    samples.append(
        {
            "frame": frame,
            "particleGridType": type(particle).__name__,
            "velocityGridType": type(velocity).__name__,
            "particleOccupiedVoxelCount": particle_voxels,
            "velocityActiveVoxelCount": velocity_voxels,
            "voxelSizeMeters": particle_voxel,
            "particleOccupancyVolumeProxyCubicMeters": occupancy_proxy,
            "velocitySupportVolumeCubicMeters": velocity_support,
            "occupancySourceErrorFraction": occupancy_proxy / SOURCE_VOLUME - 1.0,
            "particleGridBBoxMin": list(particle_meta["file_bbox_min"]),
            "particleGridBBoxMax": list(particle_meta["file_bbox_max"]),
            "velocityGridBBoxMin": list(velocity_meta["file_bbox_min"]),
            "velocityGridBBoxMax": list(velocity_meta["file_bbox_max"]),
            "aliveParticleCount": row57["aliveParticleCount"],
            "meshVolumeCubicMeters": row56["meshVolumeCubicMeters"],
        }
    )

initial_occupancy = samples[0]["particleOccupancyVolumeProxyCubicMeters"]
for row in samples:
    row["occupancyTemporalDriftFraction"] = row["particleOccupancyVolumeProxyCubicMeters"] / initial_occupancy - 1.0
occupancy_values = [row["particleOccupancyVolumeProxyCubicMeters"] for row in samples]
mesh_values = [row["meshVolumeCubicMeters"] for row in samples]
alive_values = [row["aliveParticleCount"] for row in samples]
occupancy_mesh_correlation = pearson(occupancy_values, mesh_values)
occupancy_alive_correlation = pearson(occupancy_values, alive_values)
final_occupancy_drift = samples[-1]["occupancyTemporalDriftFraction"]
final_mesh_drift = attempt56["fluidSamples"][-1]["temporalVolumeDriftFraction"]
if final_occupancy_drift < -0.15 and final_mesh_drift < -0.15 and occupancy_mesh_correlation >= 0.8:
    classification = "DATA_SPATIAL_SUPPORT_SHRINKS_WITH_MESH"
elif max(abs(row["occupancyTemporalDriftFraction"]) for row in samples) <= 0.15 and abs(final_mesh_drift) > 0.15:
    classification = "DATA_OCCUPANCY_STABLE_SURFACE_RECONSTRUCTION_SUSPECTED"
else:
    classification = "DATA_MESH_RELATION_DIVERGENT_INCONCLUSIVE"
checks = {
    "openVdbIdentityExact": tuple(openvdb.LIBRARY_VERSION) == (13, 0, 0) and openvdb.FILE_FORMAT_VERSION == 225,
    "all24FramesMeasured": len(samples) == 24 and [row["frame"] for row in samples] == list(range(1, 25)),
    "exactGridRosterEveryFrame": all(row["particleGridType"] == "PointDataGrid" and row["velocityGridType"] == "Vec3SGrid" for row in samples),
    "exactVoxelSizeEveryFrame": all(abs(row["voxelSizeMeters"] - 0.009375) <= 1e-8 for row in samples),
    "attempt56MeshFailureBound": attempt56["resultHash"] == "4969ee48c700fd86e452f1df536918b0c5c2ae868c77f39b4c3e37bc548f1a99" and abs(final_mesh_drift) > 0.15,
    "attempt57ParticleDiagnosisBound": attempt57["resultHash"] == "fa82f7dc69d363f898f7249a8565b3909ea87434336f70b180865eb737caca12" and attempt57["classification"] == "DATA_PARTICLE_COUNT_DRIFT_SIGNAL",
}
result = {
    "schemaVersion": "bfs.rc6MovingLiquidDataOccupancyDiagnosticResult.v0.1",
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
        "occupancyAliveCountPearsonCorrelation": occupancy_alive_correlation,
        "initialOccupancySourceErrorFraction": samples[0]["occupancySourceErrorFraction"],
        "finalOccupancySourceErrorFraction": samples[-1]["occupancySourceErrorFraction"],
    },
    "samples": samples,
    "checks": checks,
    "checkCount": len(checks),
    "passCount": sum(checks.values()),
    "interpretation": "particle-grid occupied-voxel volume measures sparse spatial support, not exact liquid mass or signed level-set volume; no phi/liquid grid exists in the retained VDB roster",
    "counts": {"enginePythonStarts": 1, "blenderStarts": 0, "fluidDataBakes": 0, "fluidMeshBakes": 0, "renders": 0, "blendSaves": 0, "networkCalls": 0, "retainedRootWrites": 0},
    "claimCeiling": "Read-only 24-frame OpenVDB metadata occupancy diagnosis on a copied immutable cache. It cannot prove exact mass, a physical fix, moving-liquid PASS, impact, render or film quality.",
}
result["resultHash"] = self_hash(result, "resultHash")
write_exclusive(result_path, result)
print("RC6_MOVING_LIQUID_DATA_OCCUPANCY=" + canonical({"status": result["status"], "classification": result["classification"], "resultHash": result["resultHash"], "metrics": result["metrics"]}))
if result["status"] != "MEASURED_DATA_OCCUPANCY":
    raise RuntimeError("moving-liquid Data occupancy diagnostic harness failed")
