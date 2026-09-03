#!/usr/bin/env python3
"""Independent C34 replay, native-grid decode, provenance and resource audit."""

import hashlib
import json
import struct
import subprocess
from pathlib import Path

import numpy as np
import openvdb


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "specs/ai-native-studio-rc6-native-phi-c34.v1.26.json"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def file_hash(path):
    return digest(path.read_bytes())


def self_hash(value, field):
    body = dict(value)
    body.pop(field, None)
    return digest(canonical(body))


def write_exclusive(path, value):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def grid_map(frame):
    return {row["name"]: row for row in frame["grids"]}


def main():
    spec = json.loads(SPEC.read_text())
    evidence = ROOT / spec["evidence"]
    work = Path(spec["workspace"])
    scene = json.loads((evidence / "result.json").read_text())
    result = json.loads((evidence / "diagnostic-result.json").read_text())
    accepted = json.loads((ROOT / spec["reader"]["acceptedC33Result"]).read_text())
    c29 = json.loads((ROOT / spec["baseline"]["acceptedC29Result"]).read_text())
    checks = {}

    checks["specSelfIdentity"] = self_hash(spec, "specFileSha256") == spec["specFileSha256"]
    checks["toolAndInputIdentities"] = all(
        file_hash(Path(row["path"]) if row.get("absolute") else ROOT / row["path"]) == row["sha256"]
        for row in spec["inputs"] + spec["tools"]
    )
    checks["sceneResultSelfHash"] = self_hash(scene, "resultHash") == scene["resultHash"] and scene["status"] == "PASS_DATA_BAKE"
    checks["diagnosticResultSelfHash"] = self_hash(result, "resultHash") == result["resultHash"]
    checks["exactCounts"] = scene["counts"] == spec["processCeilings"] == result["counts"]
    checks["dataOnlyNoMedia"] = (
        not (work / "mantaflow-cache/mesh").exists()
        and not any(path.suffix.lower() in {".png", ".jpg", ".jpeg", ".exr", ".mov", ".mp4", ".bobj", ".gz"} for path in work.rglob("*") if path.is_file())
    )
    cache_files = sorted(str(path.relative_to(work / "mantaflow-cache")) for path in (work / "mantaflow-cache").rglob("*") if path.is_file())
    expected_cache = sorted([f"config/config_{frame:04d}.uni" for frame in range(1, 37)] + [f"data/fluid_data_{frame:04d}.vdb" for frame in range(1, 37)])
    checks["exact72FileDataRoster"] = cache_files == expected_cache

    manifest = json.loads((evidence / "work-manifest.json").read_text())
    actual_rows = []
    symlinks = []
    for path in sorted(work.rglob("*"), key=lambda item: str(item)):
        if path.is_symlink():
            symlinks.append(str(path))
        elif path.is_file():
            actual_rows.append({"path": str(path.relative_to(work)), "bytes": path.stat().st_size, "sha256": file_hash(path)})
    checks["workManifestExact"] = not symlinks and actual_rows == manifest["files"] and self_hash(manifest, "manifestHash") == manifest["manifestHash"]
    checks["resourceCeilings"] = manifest["bytes"] <= spec["resourceCeilings"]["maximumWorkspaceBytes"] and sum(path.stat().st_size for path in evidence.rglob("*") if path.is_file()) <= spec["resourceCeilings"]["maximumEvidenceBytes"]
    checks["sourceAndHelperCopiesExact"] = file_hash(work / "source-state.blend") == spec["baseline"]["sourceBlendSha256"] and file_hash(work / "native-vdb-reader") == spec["reader"]["acceptedHelperSha256"]

    physics_keys = [
        "frameStart", "frameEnd", "fps", "resolutionMax", "domainCenterMeters", "domainDimensionsMeters",
        "baseVoxelMeters", "trajectoryCellId", "driveEndFrame", "bulletSubstepsPerFrame", "bulletSolverIterations",
        "cupUseMargin", "cupCollisionMarginMeters", "cupFriction", "simulationMethod", "particleNumber",
        "particleMinimum", "particleMaximum", "particleRadius", "particleBandWidth", "meshParticleRadius",
        "meshScale", "meshConcaveLower", "meshConcaveUpper", "meshSmoothenPos", "meshSmoothenNeg",
        "fractionsThreshold", "fractionsDistance", "cupEffectorSurfaceDistanceCells", "cupEffectorSubframes",
        "timestepsMin", "timestepsMax", "cflCondition", "useFractions", "deleteInObstacle",
        "sourceMeshVolumeCubicMeters",
    ]
    checks["exactC29Configuration"] = all(scene["configuration"].get(key) == c29["configuration"].get(key) for key in physics_keys)
    checks["soleObservationSetting"] = scene["configuration"]["cacheResumable"] is True and scene["configuration"]["cacheType"] == "MODULAR" and scene["configuration"]["cacheDataFormat"] == "OPENVDB"
    checks["exactR40BeforeAndAfter"] = scene["bulletSamples"] == c29["bulletSamples"] and scene["postFluidBulletSamples"] == c29["postFluidBulletSamples"]
    checks["sceneChecksAllPass"] = scene["passCount"] == scene["checkCount"] == len(scene["checks"]) and all(scene["checks"].values())

    old_frames = {row["frame"]: row for row in accepted["frames"]}
    replay_exact = []
    independent_velocity = []
    independent_native = []
    common_recomputed = []
    required = set(spec["reader"]["requiredNativeFields"])
    for recorded in result["frames"]:
        frame = recorded["frame"]
        path = work / "mantaflow-cache/data" / f"fluid_data_{frame:04d}.vdb"
        completed = subprocess.run([str(work / "native-vdb-reader"), str(path)], capture_output=True, text=True,
                                   timeout=spec["resourceCeilings"]["readerTimeoutSecondsPerFrame"], check=False)
        replay = json.loads(completed.stdout) if completed.returncode == 0 else None
        if replay is not None:
            replay["frame"] = frame
        replay_exact.append(replay == recorded["readerOutput"])
        current = grid_map(recorded["readerOutput"])
        old = grid_map(old_frames[frame])
        row_common = all(
            recorded["commonComparison"][name] == ({
                "decodedValueExact": current[name]["decodedValueSha256"] == old[name]["decodedValueSha256"],
                "dimensionsExact": current[name]["dimensions"] == old[name]["dimensions"],
                "typeExact": current[name]["type"] == old[name]["type"],
                "voxelSizeExact": current[name]["voxelSize"] == old[name]["voxelSize"],
                "precisionExact": current[name]["saveFloatAsHalf"] == old[name]["saveFloatAsHalf"],
                **({"particleCountExact": current[name]["particleCount"] == old[name]["particleCount"],
                    "attributeRosterExact": current[name]["attributes"] == old[name]["attributes"]} if name == "particles" else {}),
            }) for name in ("particles", "velocity")
        )
        common_recomputed.append(row_common)

        metadata = {grid.name: grid for grid in openvdb.readAllGridMetadata(str(path))}
        velocity = openvdb.read(str(path), "velocity")
        dims = tuple(velocity.metadata["file_base_resolution"])
        vector_values = np.zeros(dims + (3,), dtype=np.float32)
        velocity.copyToArray(vector_values)
        vector_values[vector_values == 0] = 0
        velocity_hash = digest(vector_values.transpose(2, 1, 0, 3).astype("<f8").tobytes())
        independent_velocity.append(velocity_hash == current["velocity"]["decodedValueSha256"])

        scalar_ok = required.issubset(metadata)
        for name in required:
            scalar = openvdb.read(str(path), name)
            scalar_dims = tuple(scalar.metadata["file_base_resolution"])
            values = np.zeros(scalar_dims, dtype=np.float32)
            scalar.copyToArray(values)
            values[values == 0] = 0
            observed = recorded["nativeFields"][name]
            scalar_ok &= (
                np.isfinite(values).all()
                and digest(values.transpose(2, 1, 0).astype("<f8").tobytes()) == observed["decodedValueSha256"]
                and int(np.count_nonzero(values < 0)) == observed["negativeCells"]
                and int(np.count_nonzero(values == 0)) == observed["zeroCells"]
                and int(np.count_nonzero(values > 0)) == observed["positiveCells"]
                and tuple(observed["dimensions"]) == scalar_dims == (96, 53, 62)
                and abs(observed["negativeLevelsetOccupiedVolumeCubicMeters"] - int(np.count_nonzero(values < 0)) * observed["voxelSize"] ** 3) <= 1e-15
            )
        independent_native.append(bool(scalar_ok))

    checks["exact36FrameSequence"] = [row["frame"] for row in result["frames"]] == list(range(1, 37))
    checks["readerReplayExact"] = len(replay_exact) == 36 and all(replay_exact)
    checks["independentVelocityDecodeExact"] = len(independent_velocity) == 36 and all(independent_velocity)
    checks["independentNativeScalarDecodeExact"] = len(independent_native) == 36 and all(independent_native)
    checks["commonComparisonRecomputed"] = len(common_recomputed) == 36 and all(common_recomputed)
    recomputed_common_exact = all(all(values.values()) for row in result["frames"] for values in row["commonComparison"].values())
    checks["classificationExact"] = result["strongCommonFieldEquivalence"] == recomputed_common_exact and result["status"] == ("PASS_NATIVE_EXPORT_STRONG_COMMON_FIELD_EQUIVALENCE" if recomputed_common_exact else "OBSERVED_PASSIVITY_UNPROVEN")

    retained_manifest = json.loads((ROOT / spec["baseline"]["retainedC29WorkManifest"]).read_text())
    retained_cache = Path(retained_manifest["root"])
    checks["retainedC29CacheExact"] = all(file_hash(retained_cache / row["path"]) == row["sha256"] for row in retained_manifest["files"] if row["path"].startswith("mantaflow-cache/"))
    blender_process = json.loads((evidence / "processes/blender.json").read_text())
    checks["absoluteBlenderArgv"] = blender_process["exitCode"] == 0 and all(Path(value).is_absolute() for value in (blender_process["argv"][0], blender_process["argv"][2], blender_process["argv"][4]))

    mechanical_pass = all(value for key, value in checks.items() if key != "classificationExact")
    status = result["status"] if mechanical_pass and checks["classificationExact"] else "FAIL_AUDIT"
    audit = {
        "schemaVersion": "bfs.rc6NativePhiC34IndependentAudit.v1", "status": status,
        "checks": checks, "passCount": sum(checks.values()), "checkCount": len(checks),
        "resultHash": result["resultHash"], "sceneResultHash": scene["resultHash"],
        "classificationBasis": "Strong equality covers full decoded P/point-velocity/U rows and dense velocity values, dimensions, types, voxel size and storage precision for all 36 frames. Native phi volumes remain numerical occupancy, not mass.",
        "claimCeiling": spec["claimCeiling"],
    }
    audit["auditHash"] = self_hash(audit, "auditHash")
    write_exclusive(evidence / "independent-audit.json", audit)
    print(json.dumps({"status": status, "checks": f"{audit['passCount']}/{audit['checkCount']}", "auditHash": audit["auditHash"]}, sort_keys=True))
    return 0 if status != "FAIL_AUDIT" else 1


if __name__ == "__main__":
    raise SystemExit(main())
