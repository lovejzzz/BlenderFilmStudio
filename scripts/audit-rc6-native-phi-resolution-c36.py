#!/usr/bin/env python3
"""Independent Review128 scalar/vector decode and C34 convergence audit."""

import hashlib
import json
import math
import subprocess
from pathlib import Path

import numpy as np
import openvdb


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "specs/ai-native-studio-rc6-native-phi-resolution-c36.v1.29.json"


def canonical(value): return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
def digest(value): return hashlib.sha256(value).hexdigest()
def file_hash(path): return digest(path.read_bytes())
def self_hash(value, field):
    body = dict(value); body.pop(field, None); return digest(canonical(body))


def write_exclusive(path, value):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False); handle.write("\n")


def root_rows(root):
    result = []
    for path in sorted(root.rglob("*"), key=lambda item: str(item)):
        if path.is_symlink(): raise RuntimeError(f"symlink forbidden: {path}")
        if path.is_file(): result.append({"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": file_hash(path)})
    return result


def field_metrics(frames, name):
    values = [row["nativeFields"][name]["negativeLevelsetOccupiedVolumeCubicMeters"] for row in frames]
    drift = [value / values[0] - 1 for value in values]
    return {"frame1OccupiedVolumeCubicMeters": values[0], "frame36OccupiedVolumeCubicMeters": values[-1],
            "frame36DriftFromFrame1Fraction": drift[-1], "maximumAbsoluteDriftFromFrame1Fraction": max(map(abs, drift)),
            "first15PercentLossFrame": next((index + 1 for index, value in enumerate(drift) if value <= -0.15), None),
            "minimumOccupiedVolumeCubicMeters": min(values), "maximumOccupiedVolumeCubicMeters": max(values)}


def classify(metrics, baseline, rule):
    improvements = {name: abs(baseline[name]["frame36DriftFromFrame1Fraction"]) - abs(metrics[name]["frame36DriftFromFrame1Fraction"]) for name in ("phi", "phi_particles")}
    onset_ok = all((metrics[name]["first15PercentLossFrame"] or 37) >= (baseline[name]["first15PercentLossFrame"] or 37) for name in improvements)
    if all(value >= rule["minimumAbsoluteImprovementFraction"] for value in improvements.values()) and onset_ok: status = "RESOLUTION_CONVERGENCE_SUPPORTS_DISCRETIZATION"
    elif all(value > 0 for value in improvements.values()) and onset_ok: status = "DIRECTIONAL_BUT_BELOW_CONVERGENCE_GATE"
    else: status = "NO_CONVERGENCE_OR_REGRESSION"
    return status, improvements, onset_ok


def main():
    spec = json.loads(SPEC.read_text()); body = dict(spec); expected = body.pop("specFileSha256")
    checks = {"specSelfIdentity": digest(canonical(body)) == expected}
    checks["toolAndInputIdentities"] = all(file_hash(Path(row["path"]) if row.get("absolute") else ROOT / row["path"]) == row["sha256"] for row in spec["inputs"] + spec["tools"])
    evidence = ROOT / spec["evidence"]; work = Path(spec["workspace"])
    scene = json.loads((evidence / "result.json").read_text()); result = json.loads((evidence / "diagnostic-result.json").read_text())
    c34_scene = json.loads((ROOT / spec["baseline"]["c34SceneResult"]).read_text()); c34 = json.loads((ROOT / spec["baseline"]["c34Result"]).read_text())
    checks["sceneSelfHash"] = self_hash(scene, "resultHash") == scene["resultHash"] and scene["status"] == "PASS_DATA_BAKE"
    checks["resultSelfHash"] = self_hash(result, "resultHash") == result["resultHash"]
    checks["exactCounts"] = scene["counts"] == result["counts"] == spec["processCeilings"]
    checks["sceneChecksPass"] = scene["passCount"] == scene["checkCount"] and all(scene["checks"].values())
    checks["review128Exact"] = scene["configuration"]["resolutionMax"] == 128 and abs(scene["configuration"]["baseVoxelMeters"] - 0.00703125) <= 1e-12 and scene["configuration"]["cacheResumable"] is True
    physics_keys = set(c34_scene["configuration"]) - {"resolutionMax", "baseVoxelMeters"}
    checks["onlyResolutionAndDerivedVoxelDiffer"] = all(scene["configuration"][key] == c34_scene["configuration"][key] for key in physics_keys)
    checks["exactR40Trajectory"] = scene["bulletSamples"] == c34_scene["bulletSamples"] and scene["postFluidBulletSamples"] == c34_scene["postFluidBulletSamples"]
    cache_files = sorted(str(path.relative_to(work / "mantaflow-cache")) for path in (work / "mantaflow-cache").rglob("*") if path.is_file())
    expected_cache = sorted([f"config/config_{frame:04d}.uni" for frame in range(1, 37)] + [f"data/fluid_data_{frame:04d}.vdb" for frame in range(1, 37)])
    checks["exactDataOnlyRoster"] = cache_files == expected_cache and not (work / "mantaflow-cache/mesh").exists()
    checks["noMedia"] = not any(path.suffix.lower() in {".png", ".jpg", ".jpeg", ".exr", ".mov", ".mp4", ".bobj", ".gz"} for path in work.rglob("*") if path.is_file())
    manifest = json.loads((evidence / "work-manifest.json").read_text()); actual = root_rows(work)
    checks["workManifestExact"] = actual == manifest["files"] and self_hash(manifest, "manifestHash") == manifest["manifestHash"]
    checks["resourceCeilings"] = manifest["bytes"] <= spec["resources"]["maximumWorkspaceBytes"] and sum(path.stat().st_size for path in evidence.rglob("*") if path.is_file()) <= spec["resources"]["maximumEvidenceBytes"]

    replay_ok = []; scalar_ok = []; velocity_ok = []; dimension_rows = []
    required = set(spec["reader"]["requiredNativeFields"])
    for row in result["frames"]:
        frame = row["frame"]; path = work / "mantaflow-cache/data" / f"fluid_data_{frame:04d}.vdb"
        completed = subprocess.run([str(work / "native-vdb-reader"), str(path)], capture_output=True, text=True, timeout=spec["resources"]["readerTimeoutSecondsPerFrame"], check=False)
        replay = json.loads(completed.stdout) if completed.returncode == 0 else None
        replay_ok.append(replay == row["readerOutput"])
        metadata = {grid.name: grid for grid in openvdb.readAllGridMetadata(str(path))}; scalar_frame_ok = required.issubset(metadata)
        for name in required:
            grid = openvdb.read(str(path), name); dims = tuple(grid.metadata["file_base_resolution"]); array = np.zeros(dims, dtype=np.float32); grid.copyToArray(array); array[array == 0] = 0
            observed = row["nativeFields"][name]; count = int(np.count_nonzero(array < 0))
            scalar_frame_ok &= np.isfinite(array).all() and digest(array.transpose(2, 1, 0).astype("<f8").tobytes()) == observed["decodedValueSha256"] and count == observed["negativeCells"] and abs(count * observed["voxelSize"] ** 3 - observed["negativeLevelsetOccupiedVolumeCubicMeters"]) <= 1e-15
            dimension_rows.append(tuple(observed["dimensions"]))
        scalar_ok.append(bool(scalar_frame_ok))
        velocity = openvdb.read(str(path), "velocity"); dims = tuple(velocity.metadata["file_base_resolution"]); values = np.zeros(dims + (3,), dtype=np.float32); velocity.copyToArray(values); values[values == 0] = 0
        measured_velocity = next(grid for grid in row["readerOutput"]["grids"] if grid["name"] == "velocity")
        velocity_ok.append(digest(values.transpose(2, 1, 0, 3).astype("<f8").tobytes()) == measured_velocity["decodedValueSha256"])
    checks["exact36Frames"] = [row["frame"] for row in result["frames"]] == list(range(1, 37))
    checks["readerReplayExact"] = len(replay_ok) == 36 and all(replay_ok)
    checks["independentNativeScalars"] = len(scalar_ok) == 36 and all(scalar_ok)
    checks["independentVelocity"] = len(velocity_ok) == 36 and all(velocity_ok)
    checks["consistentReviewDimensions"] = len(set(dimension_rows)) == 1 and max(dimension_rows[0]) == 128 and math.prod(dimension_rows[0]) <= 2097152
    metrics = {name: field_metrics(result["frames"], name) for name in ("phi", "phi_particles", "phi_previous")}
    baseline = {name: {"frame36DriftFromFrame1Fraction": c34["nativeSummary"][name]["frame36DriftFromFrame1Fraction"], "first15PercentLossFrame": next((row["frame"] for row in c34["frames"] if row["nativeFields"][name]["negativeLevelsetOccupiedVolumeCubicMeters"] / c34["frames"][0]["nativeFields"][name]["negativeLevelsetOccupiedVolumeCubicMeters"] - 1 <= -0.15), None)} for name in ("phi", "phi_particles")}
    status, improvements, onset_ok = classify(metrics, baseline, spec["classificationRule"])
    checks["metricsRecomputed"] = metrics == result["nativeSummary"] and baseline == result["baselineSummary"] and all(abs(improvements[key] - result["absoluteLossImprovements"][key]) <= 1e-15 for key in improvements) and onset_ok == result["onsetNotEarlier"]
    checks["classificationExact"] = status == result["status"]
    checks["retainedC34Exact"] = all(digest(canonical(root_rows(Path(item["root"])))) == item["sha256"] for item in spec["retainedRoots"])
    checks["auditRuntimeExact"] = tuple(openvdb.LIBRARY_VERSION) == (13, 0, 0) and file_hash(Path(spec["auditPython"])) == spec["auditPythonSha256"]
    audit = {"schemaVersion": "bfs.rc6NativePhiResolutionC36Audit.v1", "status": status if all(checks.values()) else "FAIL_AUDIT", "checks": checks, "passCount": sum(checks.values()), "checkCount": len(checks), "resultHash": result["resultHash"], "metrics": metrics, "absoluteLossImprovements": improvements, "claimCeiling": spec["claimCeiling"]}
    audit["auditHash"] = self_hash(audit, "auditHash"); write_exclusive(evidence / "independent-audit.json", audit)
    print(json.dumps({"status": audit["status"], "checks": f"{audit['passCount']}/{audit['checkCount']}", "auditHash": audit["auditHash"]}, sort_keys=True))
    return 0 if audit["status"] != "FAIL_AUDIT" else 1


if __name__ == "__main__": raise SystemExit(main())
