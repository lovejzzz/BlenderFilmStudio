#!/usr/bin/env python3
"""Execute the immutable 65-process B52-D11 formal matrix exactly once."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


SPEC_SHA256 = "f1505c42426e8e286ee1584de3df12fb33b7db57518d6d91e1fd93aa3bed5a5f"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def normalized(argv: list[str], root: Path) -> list[str]:
    prefix = str(root)
    return [value.replace(prefix, "<ROOT>") for value in argv]


def environment(spec: dict, config: str | None = None, scripts: str | None = None) -> dict[str, str]:
    result = {key: os.environ[key] for key in spec["runtime"]["environmentAllowlist"] if key in os.environ}
    result["OCIO"] = str(Path(spec["runtime"]["ocio"]["uri"]).resolve())
    if config:
        result["BLENDER_USER_CONFIG"] = config
    if scripts:
        result["BLENDER_USER_SCRIPTS"] = scripts
    return result


def run(argv: list[str], root: Path, env: dict[str, str], stdout: Path, stderr: Path) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(argv, cwd=root, env=env, text=True, capture_output=True, check=False)
    stdout.parent.mkdir(parents=True, exist_ok=True)
    stdout.write_text(completed.stdout)
    stderr.write_text(completed.stderr)
    return completed


def record_report(stage: str, cell: str, argv: list[str], result: subprocess.CompletedProcess[str], report: Path, root: Path) -> dict:
    base = {"stage": stage, "cellId": cell, "argv": normalized(argv, root), "exitCode": result.returncode, "reportUri": str(report)}
    if result.returncode != 0 or not report.is_file():
        return base
    payload = json.loads(report.read_text())
    return {**base, "pid": payload["pid"], "reportSha256": sha(report), "report": payload}


def fail(output_root: Path, stage: str, record: dict, runs: list[dict]) -> None:
    payload = {"schemaVersion": "bfs.blenderRealTexturedTemporalRunFailure.v0.1", "stage": stage, "failedCell": record, "completedRuns": runs}
    (output_root / "run.failure.json").write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n")
    raise SystemExit(record["exitCode"] or 1)


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = arguments()
    root = Path.cwd().resolve()
    spec_path, preflight_path = args.spec.resolve(), args.preflight.resolve()
    spec, preflight = json.loads(spec_path.read_text()), json.loads(preflight_path.read_text())
    if sha(spec_path) != SPEC_SHA256:
        raise RuntimeError("B52-D11 spec identity mismatch")
    if preflight.get("status") != "ACCEPTED" or preflight.get("spec", {}).get("sha256") != SPEC_SHA256 or preflight.get("allFrozenToolsMatchGit") is not True:
        raise RuntimeError("B52-D11 frozen preflight not accepted")
    output_root = root / spec["formalOutputRoot"]
    if output_root.exists():
        raise RuntimeError("refusing to overwrite immutable D11 formal root")
    available = shutil.disk_usage(root).free
    projected_after = available - spec["projectedWriteBytes"]
    if projected_after < spec["diskReserveBytes"]:
        raise RuntimeError("B52-D11 disk admission rejected")
    disk = {"status": "ACCEPTED", "availableBytes": available, "projectedWriteBytes": spec["projectedWriteBytes"], "projectedAvailableAfterBytes": projected_after, "reserveBytes": spec["diskReserveBytes"]}

    output_root.mkdir(parents=True, exist_ok=False)
    for name in ("sources", "adapters", "accumulators", "encoders", "bridges"):
        (output_root / name).mkdir()
    blender = spec["runtime"]["blender"]["executable"]
    python = spec["runtime"]["python"]["executable"]
    node = spec["runtime"]["node"]["executable"]
    tools = {
        "source": root / "blender/render_b52_d11_textured_source.py",
        "adapter": root / "scripts/adapt-b52-d11-multipart.py",
        "pythonAccumulator": root / "scripts/accumulate-b52-d11-temporal.py",
        "nodeAccumulator": root / "scripts/accumulate-b52-d11-temporal.mjs",
        "encoder": root / "scripts/encode-b52-d11-resolved.py",
        "bridge": root / "blender/render_b52_d11_resolved_passthrough.py",
        "analyzer": root / "scripts/analyze-b52-d11-textured-temporal-end-to-end.py",
    }
    runs: list[dict] = []

    for fixture in spec["fixtures"]:
        for source_repeat in (1, 2):
            for frame in (0, 1):
                cell_id = f"{fixture['id']}_F{frame}_R{source_repeat}"
                cell = output_root / "sources" / cell_id
                exr, report = cell / "source.exr", cell / "source.report.json"
                argv = [blender, *spec["runtime"]["blender"]["launchFlags"], "--python", str(tools["source"]), "--", "--spec", str(spec_path), "--fixture", fixture["id"], "--frame", str(frame), "--repeat", str(source_repeat), "--output-exr", str(exr), "--report", str(report)]
                with tempfile.TemporaryDirectory(prefix="bfs-d11-config-") as config, tempfile.TemporaryDirectory(prefix="bfs-d11-scripts-") as scripts:
                    completed = run(argv, root, environment(spec, config, scripts), cell / "stdout.log", cell / "stderr.log")
                record = record_report("SOURCE", cell_id, argv, completed, report, root)
                record.update({"fixtureId": fixture["id"], "frame": frame, "sourceRepeat": source_repeat, "exrUri": str(exr)})
                if completed.returncode != 0 or not exr.is_file() or not report.is_file():
                    fail(output_root, "SOURCE", record, runs)
                record["exrSha256"] = sha(exr)
                runs.append(record)

    source_by_cell = {(run_row["fixtureId"], run_row["frame"], run_row["sourceRepeat"]): run_row for run_row in runs if run_row["stage"] == "SOURCE"}
    for fixture in spec["fixtures"]:
        for source_repeat in (1, 2):
            fixture_id = fixture["id"]
            previous, current = source_by_cell[(fixture_id, 0, source_repeat)], source_by_cell[(fixture_id, 1, source_repeat)]
            cell_id = f"{fixture_id}_R{source_repeat}"
            adapter_cell = output_root / "adapters" / cell_id
            adapter_arrays, adapter_report = adapter_cell / "arrays", adapter_cell / "adapter.report.json"
            argv = [python, str(tools["adapter"]), "--spec", str(spec_path), "--fixture", fixture_id, "--repeat", str(source_repeat), "--previous-exr", previous["exrUri"], "--current-exr", current["exrUri"], "--previous-report", previous["reportUri"], "--current-report", current["reportUri"], "--output-dir", str(adapter_arrays), "--report", str(adapter_report)]
            completed = run(argv, root, environment(spec), adapter_cell / "stdout.log", adapter_cell / "stderr.log")
            record = record_report("ADAPTER", cell_id, argv, completed, adapter_report, root)
            record.update({"fixtureId": fixture_id, "sourceRepeat": source_repeat, "arraysUri": str(adapter_arrays)})
            if completed.returncode != 0 or not adapter_report.is_file():
                fail(output_root, "ADAPTER", record, runs)
            runs.append(record)

            accumulator_records = {}
            for producer, executable, tool_key in (("python", python, "pythonAccumulator"), ("node", node, "nodeAccumulator")):
                accumulator_cell = output_root / "accumulators" / producer / cell_id
                accumulator_arrays, accumulator_report = accumulator_cell / "arrays", accumulator_cell / "accumulator.report.json"
                argv = [executable, str(tools[tool_key]), "--spec", str(spec_path), "--fixture", fixture_id, "--repeat", str(source_repeat), "--input-dir", str(adapter_arrays), "--adapter-report", str(adapter_report), "--output-dir", str(accumulator_arrays), "--report", str(accumulator_report)]
                completed = run(argv, root, environment(spec), accumulator_cell / "stdout.log", accumulator_cell / "stderr.log")
                record = record_report(f"ACCUMULATOR_{producer.upper()}", f"{producer}_{cell_id}", argv, completed, accumulator_report, root)
                record.update({"fixtureId": fixture_id, "sourceRepeat": source_repeat, "producer": producer, "arraysUri": str(accumulator_arrays)})
                if completed.returncode != 0 or not accumulator_report.is_file():
                    fail(output_root, record["stage"], record, runs)
                runs.append(record)
                accumulator_records[producer] = record

            encoder_cell = output_root / "encoders" / cell_id
            encoded_exr, encoder_report = encoder_cell / "resolved.exr", encoder_cell / "encoder.report.json"
            python_accumulator = accumulator_records["python"]
            resolved = Path(python_accumulator["arraysUri"]) / "resolved.rgba32"
            argv = [python, str(tools["encoder"]), "--spec", str(spec_path), "--fixture", fixture_id, "--source-repeat", str(source_repeat), "--input", str(resolved), "--accumulator-report", python_accumulator["reportUri"], "--output", str(encoded_exr), "--report", str(encoder_report)]
            completed = run(argv, root, environment(spec), encoder_cell / "stdout.log", encoder_cell / "stderr.log")
            record = record_report("ENCODER", cell_id, argv, completed, encoder_report, root)
            record.update({"fixtureId": fixture_id, "sourceRepeat": source_repeat, "exrUri": str(encoded_exr)})
            if completed.returncode != 0 or not encoded_exr.is_file() or not encoder_report.is_file():
                fail(output_root, "ENCODER", record, runs)
            record["exrSha256"] = sha(encoded_exr)
            runs.append(record)

            for bridge_repeat in (1, 2):
                bridge_id = f"{cell_id}_B{bridge_repeat}"
                bridge_cell = output_root / "bridges" / bridge_id
                bridge_exr, bridge_report = bridge_cell / "resolved.exr", bridge_cell / "bridge.report.json"
                argv = [blender, *spec["runtime"]["blender"]["launchFlags"], "--python", str(tools["bridge"]), "--", "--spec", str(spec_path), "--fixture", fixture_id, "--source-repeat", str(source_repeat), "--bridge-repeat", str(bridge_repeat), "--input", str(encoded_exr), "--output", str(bridge_exr), "--report", str(bridge_report)]
                with tempfile.TemporaryDirectory(prefix="bfs-d11-config-") as config, tempfile.TemporaryDirectory(prefix="bfs-d11-scripts-") as scripts:
                    completed = run(argv, root, environment(spec, config, scripts), bridge_cell / "stdout.log", bridge_cell / "stderr.log")
                record = record_report("BRIDGE", bridge_id, argv, completed, bridge_report, root)
                record.update({"fixtureId": fixture_id, "sourceRepeat": source_repeat, "bridgeRepeat": bridge_repeat, "exrUri": str(bridge_exr)})
                if completed.returncode != 0 or not bridge_exr.is_file() or not bridge_report.is_file():
                    fail(output_root, "BRIDGE", record, runs)
                record["exrSha256"] = sha(bridge_exr)
                runs.append(record)

    preanalysis_pids = [row["pid"] for row in runs]
    counts = {stage: sum(row["stage"] == stage for row in runs) for stage in ("SOURCE", "ADAPTER", "ACCUMULATOR_PYTHON", "ACCUMULATOR_NODE", "ENCODER", "BRIDGE")}
    receipt_body = {
        "schemaVersion": "bfs.blenderRealTexturedTemporalRunReceipt.v0.1",
        "experimentId": spec["experimentId"],
        "runnerPid": os.getpid(),
        "preregistration": {"commit": "c1751fca992bb522958dbd703637a0690f9f5496", "specUri": str(spec_path.relative_to(root)), "specSha256": SPEC_SHA256},
        "preflight": {"uri": str(preflight_path), "sha256": sha(preflight_path), "status": preflight["status"], "freezeCommit": preflight["freezeCommit"]},
        "tools": preflight["tools"],
        "diskAdmission": disk,
        "runs": runs,
        "preAnalysisOperationCounts": {"totalChildProcesses": len(runs), "uniqueChildPids": len(set(preanalysis_pids)), "stageCounts": counts},
    }
    receipt = {**receipt_body, "receiptHash": canonical_hash(receipt_body)}
    receipt_path = output_root / "run.receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n")

    result_path = output_root / "results.json"
    analyzer_argv = [python, str(tools["analyzer"]), "--spec", str(spec_path), "--formal-root", str(output_root), "--receipt", str(receipt_path), "--preflight", str(preflight_path), "--output", str(result_path)]
    completed = run(analyzer_argv, root, environment(spec), output_root / "analysis.stdout.log", output_root / "analysis.stderr.log")
    if completed.returncode != 0 or not result_path.is_file():
        fail(output_root, "ANALYSIS", {"exitCode": completed.returncode, "argv": normalized(analyzer_argv, root), "stdout": completed.stdout, "stderr": completed.stderr}, runs)
    result = json.loads(result_path.read_text())
    print(f"BFS_B52_D11_RUN_OK verdict={result['verdict']} result={sha(result_path)} receipt={sha(receipt_path)}")


if __name__ == "__main__":
    main()
