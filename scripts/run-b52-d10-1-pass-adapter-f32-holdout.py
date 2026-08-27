#!/usr/bin/env python3
"""Run the immutable 19-process B52-D10.1 formal matrix exactly once."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


SPEC_SHA256 = "11686c5e796c7bc1b4e45cf137c3d98347bc65bfec428f9d19545b55430f584b"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    return parser.parse_args()


def normalized(argv: list[str], root: Path) -> list[str]:
    prefix = str(root.resolve())
    return [value.replace(prefix, "<ROOT>") for value in argv]


def clean_environment(spec: dict, config: str | None = None, scripts: str | None = None) -> dict[str, str]:
    allowed = spec["runtime"]["environmentAllowlist"]
    environment = {key: os.environ[key] for key in allowed if key in os.environ}
    environment["OCIO"] = str(Path(spec["runtime"]["ocio"]["uri"]).resolve())
    if config is not None:
        environment["BLENDER_USER_CONFIG"] = config
    if scripts is not None:
        environment["BLENDER_USER_SCRIPTS"] = scripts
    return environment


def run_logged(argv: list[str], cwd: Path, environment: dict[str, str], stdout_path: Path, stderr_path: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(argv, cwd=cwd, env=environment, text=True, capture_output=True, check=False)
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stdout_path.write_text(result.stdout, encoding="utf-8")
    stderr_path.write_text(result.stderr, encoding="utf-8")
    return result


def main() -> None:
    args = arguments()
    root = Path.cwd().resolve()
    spec_path = args.spec.resolve()
    preflight_path = args.preflight.resolve()
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    if sha256_file(spec_path) != SPEC_SHA256:
        raise RuntimeError("B52-D10.1 spec identity mismatch")
    if not (preflight.get("status") == "ACCEPTED" and preflight.get("spec", {}).get("sha256") == SPEC_SHA256 and preflight.get("allFrozenToolsMatchGit") is True):
        raise RuntimeError("frozen D10.1 preflight not accepted")
    output_root = root / spec["formalOutputRoot"]
    if output_root.exists():
        raise RuntimeError("refusing to overwrite immutable D10.1 formal root")
    available = shutil.disk_usage(root).free
    projected_after = available - spec["projectedWriteBytes"]
    if projected_after < spec["diskReserveBytes"]:
        raise RuntimeError("D10.1 disk admission rejected")
    disk_admission = {"status": "ACCEPTED", "availableBytes": available, "projectedWriteBytes": spec["projectedWriteBytes"], "projectedAvailableAfterBytes": projected_after, "reserveBytes": spec["diskReserveBytes"]}

    output_root.mkdir(parents=True, exist_ok=False)
    (output_root / "sources").mkdir()
    (output_root / "adapters").mkdir()
    blender = spec["runtime"]["blender"]["executable"]
    python = spec["runtime"]["python"]["executable"]
    renderer = root / "blender/render_b52_d10_1_pass_adapter_source.py"
    adapter = root / "scripts/adapt-b52-d10-1-multipart.py"
    analyzer = root / "scripts/analyze-b52-d10-1-pass-adapter-f32-holdout.py"
    source_runs, adapter_runs = [], []

    for fixture in spec["fixtures"]:
        for repeat in (1, 2):
            for frame in (0, 1):
                cell_id = f"{fixture['id']}_F{frame}_R{repeat}"
                cell = output_root / "sources" / cell_id
                exr = cell / "source.exr"
                report = cell / "source.report.json"
                argv = [blender, *spec["runtime"]["blender"]["launchFlags"], "--python", str(renderer), "--", "--spec", str(spec_path), "--fixture", fixture["id"], "--frame", str(frame), "--repeat", str(repeat), "--output-exr", str(exr), "--report", str(report)]
                with tempfile.TemporaryDirectory(prefix="bfs-d10-1-config-") as config, tempfile.TemporaryDirectory(prefix="bfs-d10-1-scripts-") as scripts:
                    result = run_logged(argv, root, clean_environment(spec, config, scripts), cell / "stdout.log", cell / "stderr.log")
                record = {"cellId": cell_id, "fixtureId": fixture["id"], "frame": frame, "repeat": repeat, "exitCode": result.returncode, "argv": normalized(argv, root), "exrUri": str(exr), "reportUri": str(report)}
                if result.returncode != 0 or not exr.is_file() or not report.is_file():
                    (output_root / "run.failure.json").write_text(json.dumps({"schemaVersion": "bfs.blenderMultipartTemporalAdapterF32RunFailure.v0.1", "stage": "SOURCE", "failedCell": record, "sourceRuns": source_runs}, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
                    raise SystemExit(result.returncode or 1)
                source_report = json.loads(report.read_text(encoding="utf-8"))
                record.update({"pid": source_report["pid"], "exrSha256": sha256_file(exr), "reportSha256": sha256_file(report)})
                source_runs.append(record)

    source_by_key = {(item["fixtureId"], item["frame"], item["repeat"]): item for item in source_runs}
    for fixture in spec["fixtures"]:
        for repeat in (1, 2):
            cell_id = f"{fixture['id']}_R{repeat}"
            cell = output_root / "adapters" / cell_id
            arrays = cell / "arrays"
            report = cell / "adapter.report.json"
            previous = source_by_key[(fixture["id"], 0, repeat)]
            current = source_by_key[(fixture["id"], 1, repeat)]
            argv = [python, str(adapter), "--spec", str(spec_path), "--fixture", fixture["id"], "--repeat", str(repeat), "--previous-exr", previous["exrUri"], "--current-exr", current["exrUri"], "--previous-report", previous["reportUri"], "--current-report", current["reportUri"], "--output-dir", str(arrays), "--report", str(report)]
            result = run_logged(argv, root, clean_environment(spec), cell / "stdout.log", cell / "stderr.log")
            record = {"cellId": cell_id, "fixtureId": fixture["id"], "repeat": repeat, "exitCode": result.returncode, "argv": normalized(argv, root), "arraysUri": str(arrays), "reportUri": str(report)}
            if result.returncode != 0 or not report.is_file():
                (output_root / "run.failure.json").write_text(json.dumps({"schemaVersion": "bfs.blenderMultipartTemporalAdapterF32RunFailure.v0.1", "stage": "ADAPTER", "failedCell": record, "sourceRuns": source_runs, "adapterRuns": adapter_runs}, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
                raise SystemExit(result.returncode or 1)
            adapter_report = json.loads(report.read_text(encoding="utf-8"))
            record.update({"pid": adapter_report["pid"], "reportSha256": sha256_file(report), "arrayHashes": {name: value["sha256"] for name, value in adapter_report["arrays"].items()}})
            adapter_runs.append(record)

    receipt_body = {
        "schemaVersion": "bfs.blenderMultipartTemporalAdapterF32RunReceipt.v0.1",
        "experimentId": spec["experimentId"],
        "runnerPid": os.getpid(),
        "spec": {"uri": str(spec_path), "sha256": SPEC_SHA256},
        "preflight": {"uri": str(preflight_path), "sha256": sha256_file(preflight_path), "status": preflight["status"], "freezeCommit": preflight["freezeCommit"]},
        "diskAdmission": disk_admission,
        "sourceRuns": source_runs,
        "adapterRuns": adapter_runs,
        "preAnalysisOperationCounts": {"sourceBlenderProcesses": 12, "sourceRenderCalls": 12, "cyclesRayRenders": 12, "adapterPythonProcesses": 6, "uniqueChildPids": len({item["pid"] for item in [*source_runs, *adapter_runs]})},
    }
    receipt = {**receipt_body, "receiptHash": canonical_hash(receipt_body)}
    receipt_path = output_root / "run.receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")

    result_path = output_root / "results.json"
    argv = [python, str(analyzer), "--spec", str(spec_path), "--formal-root", str(output_root), "--receipt", str(receipt_path), "--preflight", str(preflight_path), "--output", str(result_path)]
    analysis = run_logged(argv, root, clean_environment(spec), output_root / "analysis.stdout.log", output_root / "analysis.stderr.log")
    if analysis.returncode != 0 or not result_path.is_file():
        (output_root / "analysis.failure.json").write_text(json.dumps({"schemaVersion": "bfs.blenderMultipartTemporalAdapterF32AnalysisFailure.v0.1", "exitCode": analysis.returncode, "argv": normalized(argv, root), "stdout": analysis.stdout, "stderr": analysis.stderr}, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
        raise SystemExit(analysis.returncode or 1)
    result = json.loads(result_path.read_text(encoding="utf-8"))
    print(f"BFS_B52_D10_1_RUN_OK verdict={result['verdict']} result={sha256_file(result_path)} receipt={sha256_file(receipt_path)}")


if __name__ == "__main__":
    main()
