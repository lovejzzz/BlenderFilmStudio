#!/usr/bin/env python3
"""Run one frozen C34 exact-C29 uninterrupted resumable Data diagnostic."""

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
SPEC = ROOT / "specs/ai-native-studio-rc6-native-phi-c34.v1.26.json"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest_bytes(value):
    return hashlib.sha256(value).hexdigest()


def digest_file(path):
    return digest_bytes(path.read_bytes())


def self_hash(value, field):
    body = dict(value)
    body.pop(field, None)
    return digest_bytes(canonical(body))


def write_exclusive(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def tree_manifest(root):
    rows = []
    for path in sorted(root.rglob("*"), key=lambda item: str(item)):
        if path.is_symlink():
            raise RuntimeError(f"symlink forbidden: {path}")
        if path.is_file():
            rows.append({"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": digest_file(path)})
    return rows


def checked_file(path, expected):
    if not path.is_file() or path.is_symlink() or digest_file(path) != expected:
        raise RuntimeError(f"input identity mismatch: {path}")


def run_logged(argv, stdout_path, stderr_path, timeout, env=None):
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    with stdout_path.open("x") as stdout, stderr_path.open("x") as stderr:
        started = time.monotonic()
        completed = subprocess.run(argv, stdout=stdout, stderr=stderr, timeout=timeout, env=env, check=False)
    return {"argv": argv, "exitCode": completed.returncode, "seconds": time.monotonic() - started,
            "stdout": str(stdout_path), "stderr": str(stderr_path)}


def grid_map(frame):
    return {row["name"]: row for row in frame["grids"]}


def main():
    spec = json.loads(SPEC.read_text())
    if self_hash(spec, "specFileSha256") != spec["specFileSha256"]:
        raise RuntimeError("C34 spec self identity mismatch")
    for row in spec["inputs"] + spec["tools"]:
        path = Path(row["path"]) if row.get("absolute") else ROOT / row["path"]
        checked_file(path, row["sha256"])
    if shutil.disk_usage(Path(spec["workspace"]).parent).free < spec["resourceCeilings"]["minimumReserveBytes"]:
        raise RuntimeError("C34 host reserve admission failed")
    work = Path(spec["workspace"])
    evidence = ROOT / spec["evidence"]
    if work.exists() or evidence.exists():
        raise RuntimeError("C34 fresh roots already exist")
    work.mkdir(parents=True)
    evidence.mkdir(parents=True)
    write_exclusive(evidence / "admission.json", {
        "schemaVersion": "bfs.rc6NativePhiC34Admission.v1", "status": "PASS",
        "observedFreeBytes": shutil.disk_usage(work.parent).free,
        "specFileSha256": spec["specFileSha256"], "workspace": str(work), "evidence": str(evidence),
    })

    try:
        source = Path(spec["baseline"]["sourceBlend"])
        trajectory = ROOT / spec["baseline"]["trajectory"]
        binary = Path(spec["baseline"]["binary"])
        helper_source = Path(spec["reader"]["acceptedHelper"])
        source_copy = work / "source-state.blend"
        helper_copy = work / "native-vdb-reader"
        shutil.copy2(source, source_copy)
        shutil.copy2(helper_source, helper_copy)
        checked_file(source_copy, spec["baseline"]["sourceBlendSha256"])
        checked_file(helper_copy, spec["reader"]["acceptedHelperSha256"])

        scene_script = ROOT / "scripts/run-rc6-native-phi-c34-scene.py"
        argv = [str(binary), "-b", str(source_copy), "--python", str(scene_script), "--",
                "--work-root", str(work), "--evidence-root", str(evidence),
                "--trajectory-json", str(trajectory), "--source-copy", str(source_copy)]
        process = run_logged(argv, evidence / "logs/blender.stdout.txt", evidence / "logs/blender.stderr.txt",
                             spec["resourceCeilings"]["blenderTimeoutSeconds"], os.environ.copy())
        write_exclusive(evidence / "processes/blender.json", process)
        if process["exitCode"] != 0:
            raise RuntimeError(f"C34 Blender exited {process['exitCode']}")

        scene_result = json.loads((evidence / "result.json").read_text())
        scene_hash = scene_result.get("resultHash")
        if scene_result.get("status") != "PASS_DATA_BAKE" or self_hash(scene_result, "resultHash") != scene_hash:
            raise RuntimeError("C34 Blender result rejected")
        if scene_result["counts"] != spec["processCeilings"]:
            raise RuntimeError("C34 operation count mismatch")

        accepted = json.loads((ROOT / spec["reader"]["acceptedC33Result"]).read_text())
        old_frames = {row["frame"]: row for row in accepted["frames"]}
        frame_rows = []
        required = set(spec["reader"]["requiredNativeFields"])
        for frame in range(1, 37):
            cache_file = work / "mantaflow-cache/data" / f"fluid_data_{frame:04d}.vdb"
            if not cache_file.is_file() or cache_file.is_symlink():
                raise RuntimeError(f"C34 missing Data frame {frame}")
            completed = subprocess.run([str(helper_copy), str(cache_file)], capture_output=True, text=True,
                                       timeout=spec["resourceCeilings"]["readerTimeoutSecondsPerFrame"], check=False)
            if completed.returncode != 0:
                raise RuntimeError(f"C34 reader rejected frame {frame}: {completed.stderr.strip()}")
            observed = json.loads(completed.stdout)
            observed["frame"] = frame
            current = grid_map(observed)
            old = grid_map(old_frames[frame])
            if not required.issubset(current):
                raise RuntimeError(f"C34 native field roster incomplete at frame {frame}: {sorted(current)}")
            common = {}
            for name in ("particles", "velocity"):
                common[name] = {
                    "decodedValueExact": current[name]["decodedValueSha256"] == old[name]["decodedValueSha256"],
                    "dimensionsExact": current[name]["dimensions"] == old[name]["dimensions"],
                    "typeExact": current[name]["type"] == old[name]["type"],
                    "voxelSizeExact": current[name]["voxelSize"] == old[name]["voxelSize"],
                    "precisionExact": current[name]["saveFloatAsHalf"] == old[name]["saveFloatAsHalf"],
                }
                if name == "particles":
                    common[name]["particleCountExact"] = current[name]["particleCount"] == old[name]["particleCount"]
                    common[name]["attributeRosterExact"] = current[name]["attributes"] == old[name]["attributes"]
            native = {name: {
                "negativeCells": current[name]["negativeCells"],
                "zeroCells": current[name]["zeroCells"],
                "positiveCells": current[name]["positiveCells"],
                "negativeLevelsetOccupiedVolumeCubicMeters": current[name]["negativeLevelsetOccupiedVolume"],
                "minimum": current[name]["minimum"], "maximum": current[name]["maximum"],
                "decodedValueSha256": current[name]["decodedValueSha256"],
                "dimensions": current[name]["dimensions"], "voxelSize": current[name]["voxelSize"],
                "type": current[name]["type"], "saveFloatAsHalf": current[name]["saveFloatAsHalf"],
            } for name in sorted(required)}
            frame_rows.append({"frame": frame, "gridRoster": sorted(current), "commonComparison": common,
                               "nativeFields": native, "readerOutput": observed})

        common_exact = all(all(values.values()) for row in frame_rows for values in row["commonComparison"].values())
        native_summary = {}
        for name in sorted(required):
            volumes = [row["nativeFields"][name]["negativeLevelsetOccupiedVolumeCubicMeters"] for row in frame_rows]
            initial = volumes[0]
            native_summary[name] = {
                "frame1OccupiedVolumeCubicMeters": initial, "frame36OccupiedVolumeCubicMeters": volumes[-1],
                "frame36DriftFromFrame1Fraction": None if initial == 0 else volumes[-1] / initial - 1,
                "minimumOccupiedVolumeCubicMeters": min(volumes), "maximumOccupiedVolumeCubicMeters": max(volumes),
                "maximumAbsoluteDriftFromFrame1Fraction": None if initial == 0 else max(abs(value / initial - 1) for value in volumes),
                "frame36ErrorFromSourceMeshVolumeFraction": volumes[-1] / scene_result["configuration"]["sourceMeshVolumeCubicMeters"] - 1,
            }
        status = "PASS_NATIVE_EXPORT_STRONG_COMMON_FIELD_EQUIVALENCE" if common_exact else "OBSERVED_PASSIVITY_UNPROVEN"
        result = {
            "schemaVersion": "bfs.rc6NativePhiC34Result.v1", "status": status,
            "specFileSha256": spec["specFileSha256"], "sceneResultHash": scene_hash,
            "acceptedC33ResultHash": accepted["resultHash"], "helperSha256": digest_file(helper_copy),
            "strongCommonFieldEquivalence": common_exact, "frames": frame_rows, "nativeSummary": native_summary,
            "counts": scene_result["counts"],
            "interpretation": "Native negative-levelset occupied volume is finite-grid numerical occupancy, not exact mass. Common-field equality establishes only same-host uninterrupted Data-export equivalence for this exact run.",
            "claimCeiling": spec["claimCeiling"],
        }
        result["resultHash"] = self_hash(result, "resultHash")
        write_exclusive(evidence / "diagnostic-result.json", result)

        work_rows = tree_manifest(work)
        work_manifest = {"schemaVersion": "bfs.rootManifest.v1", "root": str(work), "files": work_rows,
                         "fileCount": len(work_rows), "bytes": sum(row["bytes"] for row in work_rows)}
        work_manifest["manifestHash"] = self_hash(work_manifest, "manifestHash")
        write_exclusive(evidence / "work-manifest.json", work_manifest)
        if work_manifest["bytes"] > spec["resourceCeilings"]["maximumWorkspaceBytes"]:
            raise RuntimeError("C34 workspace byte ceiling exceeded")

        audit_process = run_logged([sys.executable, str(ROOT / "scripts/audit-rc6-native-phi-c34.py")],
                                   evidence / "logs/audit.stdout.txt", evidence / "logs/audit.stderr.txt",
                                   spec["resourceCeilings"]["auditTimeoutSeconds"])
        write_exclusive(evidence / "processes/audit.json", audit_process)
        if audit_process["exitCode"] != 0:
            raise RuntimeError(f"C34 independent audit exited {audit_process['exitCode']}")
        audit = json.loads((evidence / "independent-audit.json").read_text())
        if audit["status"] != status:
            raise RuntimeError("C34 audit classification mismatch")

        receipt = {
            "schemaVersion": "bfs.rc6NativePhiC34Receipt.v1", "status": status,
            "resultHash": result["resultHash"], "auditHash": audit["auditHash"],
            "sceneResultHash": scene_hash, "workManifestHash": work_manifest["manifestHash"],
            "workspaceBytes": work_manifest["bytes"],
            "evidenceBytesBeforeReceipt": sum(path.stat().st_size for path in evidence.rglob("*") if path.is_file()),
            "peakChildRssBytes": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
            "counts": scene_result["counts"], "claimCeiling": spec["claimCeiling"],
        }
        receipt["receiptHash"] = self_hash(receipt, "receiptHash")
        write_exclusive(evidence / "receipt.json", receipt)
        if sum(path.stat().st_size for path in evidence.rglob("*") if path.is_file()) > spec["resourceCeilings"]["maximumEvidenceBytes"]:
            raise RuntimeError("C34 evidence byte ceiling exceeded")
        print(json.dumps({"status": status, "resultHash": result["resultHash"], "auditHash": audit["auditHash"],
                          "phiFrame36Drift": native_summary["phi"]["frame36DriftFromFrame1Fraction"]}, sort_keys=True))
        return 0
    except Exception as error:
        failure = {"schemaVersion": "bfs.rc6NativePhiC34Failure.v1", "status": "FAIL_RETAINED",
                   "error": str(error), "countsMaximum": spec["processCeilings"]}
        failure["failureHash"] = self_hash(failure, "failureHash")
        if not (evidence / "failure.json").exists():
            write_exclusive(evidence / "failure.json", failure)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
