#!/usr/bin/env python3
"""Run one exact-R40 Review128 Data-only native-field convergence test."""

import hashlib
import json
import os
import resource
import shutil
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "specs/ai-native-studio-rc6-native-phi-resolution-c36.v1.29.json"


def canonical(value): return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
def digest(value): return hashlib.sha256(value).hexdigest()
def file_hash(path): return digest(path.read_bytes())
def self_hash(value, field):
    body = dict(value); body.pop(field, None); return digest(canonical(body))


def write_exclusive(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False); handle.write("\n")


def rows(root):
    result = []
    for path in sorted(root.rglob("*"), key=lambda item: str(item)):
        if path.is_symlink(): raise RuntimeError(f"symlink forbidden: {path}")
        if path.is_file(): result.append({"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": file_hash(path)})
    return result


def checked(path, expected):
    if not path.is_file() or path.is_symlink() or file_hash(path) != expected: raise RuntimeError(f"identity mismatch: {path}")


def run_logged(argv, stdout_path, stderr_path, timeout):
    stdout_path.parent.mkdir(parents=True, exist_ok=True); started = time.monotonic()
    with stdout_path.open("x") as out, stderr_path.open("x") as err:
        completed = subprocess.run(argv, stdout=out, stderr=err, timeout=timeout, check=False, env=os.environ.copy())
    return {"argv": argv, "exitCode": completed.returncode, "seconds": time.monotonic() - started,
            "stdout": str(stdout_path), "stderr": str(stderr_path)}


def grid_map(value): return {row["name"]: row for row in value["grids"]}


def field_metrics(frames, name):
    values = [row["nativeFields"][name]["negativeLevelsetOccupiedVolumeCubicMeters"] for row in frames]
    initial = values[0]; drift = [value / initial - 1 for value in values]
    return {"frame1OccupiedVolumeCubicMeters": initial, "frame36OccupiedVolumeCubicMeters": values[-1],
            "frame36DriftFromFrame1Fraction": drift[-1], "maximumAbsoluteDriftFromFrame1Fraction": max(map(abs, drift)),
            "first15PercentLossFrame": next((index + 1 for index, value in enumerate(drift) if value <= -0.15), None),
            "minimumOccupiedVolumeCubicMeters": min(values), "maximumOccupiedVolumeCubicMeters": max(values)}


def classify(metrics, baseline, rule):
    improvements = {name: abs(baseline[name]["frame36DriftFromFrame1Fraction"]) - abs(metrics[name]["frame36DriftFromFrame1Fraction"]) for name in ("phi", "phi_particles")}
    onset_ok = all((metrics[name]["first15PercentLossFrame"] or 37) >= (baseline[name]["first15PercentLossFrame"] or 37) for name in improvements)
    if all(value >= rule["minimumAbsoluteImprovementFraction"] for value in improvements.values()) and onset_ok:
        status = "RESOLUTION_CONVERGENCE_SUPPORTS_DISCRETIZATION"
    elif all(value > 0 for value in improvements.values()) and onset_ok:
        status = "DIRECTIONAL_BUT_BELOW_CONVERGENCE_GATE"
    else:
        status = "NO_CONVERGENCE_OR_REGRESSION"
    return status, improvements, onset_ok


def main():
    spec = json.loads(SPEC.read_text()); body = dict(spec); expected = body.pop("specFileSha256")
    assert digest(canonical(body)) == expected
    for row in spec["inputs"] + spec["tools"]:
        path = Path(row["path"]) if row.get("absolute") else ROOT / row["path"]
        checked(path, row["sha256"])
    work = Path(spec["workspace"]); evidence = ROOT / spec["evidence"]
    if work.exists() or evidence.exists(): raise RuntimeError("C36 fresh roots already exist")
    if shutil.disk_usage(work.parent).free < spec["resources"]["minimumReserveBytes"] + spec["resources"]["maximumWorkspaceBytes"]:
        raise RuntimeError("C36 host reserve admission failed")
    work.mkdir(); evidence.mkdir()
    write_exclusive(evidence / "admission.json", {"schemaVersion": "bfs.rc6C36Admission.v1", "status": "PASS",
                    "observedFreeBytes": shutil.disk_usage(work.parent).free, "specFileSha256": expected})
    try:
        source_copy = work / "source-state.blend"; helper = work / "native-vdb-reader"
        shutil.copy2(spec["baseline"]["sourceBlend"], source_copy); shutil.copy2(spec["reader"]["helper"], helper)
        checked(source_copy, spec["baseline"]["sourceBlendSha256"]); checked(helper, spec["reader"]["helperSha256"])
        argv = [spec["baseline"]["binary"], "-b", str(source_copy), "--python", str(ROOT / spec["sceneTool"]), "--",
                "--work-root", str(work), "--evidence-root", str(evidence), "--trajectory-json", str(ROOT / spec["baseline"]["trajectory"]), "--source-copy", str(source_copy)]
        process = run_logged(argv, evidence / "logs/blender.stdout.txt", evidence / "logs/blender.stderr.txt", spec["resources"]["blenderTimeoutSeconds"])
        write_exclusive(evidence / "processes/blender.json", process)
        if process["exitCode"] != 0: raise RuntimeError(f"C36 Blender exited {process['exitCode']}")
        scene = json.loads((evidence / "result.json").read_text())
        if scene["status"] != "PASS_DATA_BAKE" or self_hash(scene, "resultHash") != scene["resultHash"]: raise RuntimeError("C36 scene result rejected")
        if scene["counts"] != spec["processCeilings"]: raise RuntimeError("C36 process count mismatch")

        required = set(spec["reader"]["requiredNativeFields"]); frames = []
        for frame in range(1, 37):
            path = work / "mantaflow-cache/data" / f"fluid_data_{frame:04d}.vdb"
            completed = subprocess.run([str(helper), str(path)], capture_output=True, text=True, timeout=spec["resources"]["readerTimeoutSecondsPerFrame"], check=False)
            if completed.returncode: raise RuntimeError(f"C36 reader frame {frame}: {completed.stderr.strip()}")
            output = json.loads(completed.stdout); grids = grid_map(output)
            if not required.issubset(grids) or not {"particles", "velocity"}.issubset(grids): raise RuntimeError(f"C36 field roster frame {frame}: {sorted(grids)}")
            native = {name: {key: grids[name][key] for key in ("negativeCells", "zeroCells", "positiveCells", "negativeLevelsetOccupiedVolume", "minimum", "maximum", "decodedValueSha256", "dimensions", "voxelSize", "type", "saveFloatAsHalf")} for name in required}
            for value in native.values(): value["negativeLevelsetOccupiedVolumeCubicMeters"] = value.pop("negativeLevelsetOccupiedVolume")
            frames.append({"frame": frame, "gridRoster": sorted(grids), "nativeFields": native,
                           "particleCount": grids["particles"]["particleCount"], "readerOutput": output})
        metrics = {name: field_metrics(frames, name) for name in ("phi", "phi_particles", "phi_previous")}
        c34 = json.loads((ROOT / spec["baseline"]["c34Result"]).read_text())
        baseline = {name: {"frame36DriftFromFrame1Fraction": c34["nativeSummary"][name]["frame36DriftFromFrame1Fraction"],
                           "first15PercentLossFrame": next((row["frame"] for row in c34["frames"] if row["nativeFields"][name]["negativeLevelsetOccupiedVolumeCubicMeters"] / c34["frames"][0]["nativeFields"][name]["negativeLevelsetOccupiedVolumeCubicMeters"] - 1 <= -0.15), None)} for name in ("phi", "phi_particles")}
        classification, improvements, onset_ok = classify(metrics, baseline, spec["classificationRule"])
        result = {"schemaVersion": "bfs.rc6NativePhiResolutionC36Result.v1", "status": classification,
                  "specFileSha256": expected, "sceneResultHash": scene["resultHash"], "helperSha256": file_hash(helper),
                  "resolution": 128, "baseVoxelMeters": scene["configuration"]["baseVoxelMeters"], "frames": frames,
                  "nativeSummary": metrics, "baselineSummary": baseline, "absoluteLossImprovements": improvements,
                  "onsetNotEarlier": onset_ok, "dataBakeSeconds": scene["metrics"]["fluidDataBakeSeconds"],
                  "dataBakeCostRatioVersusC34": scene["metrics"]["fluidDataBakeSeconds"] / spec["baseline"]["c34DataBakeSeconds"],
                  "particleCountFrame1": frames[0]["particleCount"], "particleCountFrame36": frames[-1]["particleCount"],
                  "particleCountDrift": frames[-1]["particleCount"] / frames[0]["particleCount"] - 1,
                  "counts": scene["counts"], "claimCeiling": spec["claimCeiling"]}
        result["resultHash"] = self_hash(result, "resultHash")
        write_exclusive(evidence / "diagnostic-result.json", result)
        manifest = {"schemaVersion": "bfs.rootManifest.v1", "root": str(work), "files": rows(work)}
        manifest["fileCount"] = len(manifest["files"]); manifest["bytes"] = sum(row["bytes"] for row in manifest["files"]); manifest["manifestHash"] = self_hash(manifest, "manifestHash")
        write_exclusive(evidence / "work-manifest.json", manifest)
        if manifest["bytes"] > spec["resources"]["maximumWorkspaceBytes"]: raise RuntimeError("C36 workspace ceiling exceeded")
        audit_argv = [spec["auditPython"], str(ROOT / spec["auditTool"])]
        audit_process = run_logged(audit_argv, evidence / "logs/audit.stdout.txt", evidence / "logs/audit.stderr.txt", spec["resources"]["auditTimeoutSeconds"])
        write_exclusive(evidence / "processes/audit.json", audit_process)
        if audit_process["exitCode"] != 0: raise RuntimeError(f"C36 audit exited {audit_process['exitCode']}")
        audit = json.loads((evidence / "independent-audit.json").read_text())
        if audit["status"] != classification: raise RuntimeError("C36 audit classification mismatch")
        receipt = {"schemaVersion": "bfs.rc6NativePhiResolutionC36Receipt.v1", "status": classification,
                   "resultHash": result["resultHash"], "auditHash": audit["auditHash"], "sceneResultHash": scene["resultHash"],
                   "workManifestHash": manifest["manifestHash"], "workspaceBytes": manifest["bytes"],
                   "peakChildRssBytes": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
                   "counts": scene["counts"], "claimCeiling": spec["claimCeiling"]}
        receipt["receiptHash"] = self_hash(receipt, "receiptHash"); write_exclusive(evidence / "receipt.json", receipt)
        if sum(path.stat().st_size for path in evidence.rglob("*") if path.is_file()) > spec["resources"]["maximumEvidenceBytes"]: raise RuntimeError("C36 evidence ceiling exceeded")
        print(json.dumps({"status": classification, "phiDrift": metrics["phi"]["frame36DriftFromFrame1Fraction"], "resultHash": result["resultHash"], "auditHash": audit["auditHash"]}, sort_keys=True)); return 0
    except Exception as error:
        failure = {"schemaVersion": "bfs.rc6NativePhiResolutionC36Failure.v1", "status": "FAIL_RETAINED", "error": str(error)}
        failure["failureHash"] = self_hash(failure, "failureHash")
        if not (evidence / "failure.json").exists(): write_exclusive(evidence / "failure.json", failure)
        raise


if __name__ == "__main__": raise SystemExit(main())
