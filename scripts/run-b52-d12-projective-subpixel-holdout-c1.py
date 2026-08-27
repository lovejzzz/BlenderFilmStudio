#!/usr/bin/env python3
"""Execute the C1-corrected immutable 65-process B52-D12 matrix from scratch."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


SPEC_SHA256 = "dd2e990d276e0ee5c2fee9d22cf42c7f84db2b6c1947b1219dceab06a76f66a2"
PREREGISTRATION_COMMIT = "d4158eddcfac697a8555f25d8f3a7fb38eab4836"
CORRECTION_SPEC_SHA256 = "f540b6a2ee0bb7b2e149c795b89adbc5ab24355750f73392f21ca65c40020a79"
CORRECTION_PREREGISTRATION_COMMIT = "af0036f613d3df88eb8d01bb97511cbeedc654ff"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def normalized(argv: list[str], root: Path) -> list[str]:
    return [value.replace(str(root), "<ROOT>") for value in argv]


def environment(spec: dict, config: str | None = None, scripts: str | None = None) -> dict[str, str]:
    result = {key: os.environ[key] for key in spec["runtime"]["environmentAllowlist"] if key in os.environ}
    result["OCIO"] = str(Path(spec["runtime"]["ocio"]["uri"]).resolve())
    if config: result["BLENDER_USER_CONFIG"] = config
    if scripts: result["BLENDER_USER_SCRIPTS"] = scripts
    return result


def run(argv, root, env, stdout, stderr):
    completed = subprocess.run(argv, cwd=root, env=env, text=True, capture_output=True, check=False)
    stdout.parent.mkdir(parents=True, exist_ok=True); stdout.write_text(completed.stdout); stderr.write_text(completed.stderr)
    return completed


def record_report(stage, cell, argv, completed, report, root):
    base = {"stage": stage, "cellId": cell, "argv": normalized(argv, root), "exitCode": completed.returncode, "reportUri": str(report)}
    if completed.returncode != 0 or not report.is_file(): return base
    payload = json.loads(report.read_text())
    return {**base, "pid": payload["pid"], "reportSha256": sha(report), "report": payload}


def fail(output_root, stage, record, runs):
    payload = {"schemaVersion": "bfs.blenderProjectiveSubpixelRunFailure.v0.1", "stage": stage, "failedCell": record, "completedRuns": runs}
    (output_root / "run.failure.json").write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n")
    raise SystemExit(record.get("exitCode") or 1)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--spec", type=Path, required=True); parser.add_argument("--correction-spec", type=Path, required=True); parser.add_argument("--preflight", type=Path, required=True); args = parser.parse_args()
    root = Path.cwd().resolve(); spec_path, correction_path, preflight_path = args.spec.resolve(), args.correction_spec.resolve(), args.preflight.resolve()
    spec, correction, preflight = json.loads(spec_path.read_text()), json.loads(correction_path.read_text()), json.loads(preflight_path.read_text())
    if sha(spec_path) != SPEC_SHA256 or sha(correction_path) != CORRECTION_SPEC_SHA256: raise RuntimeError("B52-D12-C1 spec identity mismatch")
    if preflight.get("status") != "ACCEPTED" or preflight.get("spec", {}).get("sha256") != SPEC_SHA256 or preflight.get("correctionSpec", {}).get("sha256") != CORRECTION_SPEC_SHA256 or preflight.get("allFrozenToolsMatchGit") is not True: raise RuntimeError("B52-D12-C1 frozen preflight not accepted")
    output_root = root / correction["execution"]["formalOutputRoot"]
    if output_root.exists(): raise RuntimeError("refusing to overwrite immutable D12-C1 formal root")
    available = shutil.disk_usage(root).free; projected_after = available - correction["execution"]["projectedWriteBytes"]
    if projected_after < correction["execution"]["diskReserveBytes"]: raise RuntimeError("B52-D12 disk admission rejected")
    disk = {"status": "ACCEPTED", "availableBytes": available, "projectedWriteBytes": correction["execution"]["projectedWriteBytes"], "projectedAvailableAfterBytes": projected_after, "reserveBytes": correction["execution"]["diskReserveBytes"]}
    output_root.mkdir(parents=True, exist_ok=False)
    for name in ("sources", "adapters", "reconstructors", "encoders", "bridges"): (output_root / name).mkdir()
    blender, python, node = spec["runtime"]["blender"]["executable"], spec["runtime"]["python"]["executable"], spec["runtime"]["node"]["executable"]
    tools = {"source": root / "blender/render_b52_d12_projective_source.py", "adapter": root / "scripts/adapt-b52-d12-projective-multipart.py", "pythonReconstructor": root / "scripts/reconstruct-b52-d12-subpixel.py", "nodeReconstructor": root / "scripts/reconstruct-b52-d12-subpixel-c1.mjs", "encoder": root / "scripts/encode-b52-d12-reconstruction.py", "bridge": root / "blender/render_b52_d12_reconstruction_passthrough.py", "analyzer": root / "scripts/analyze-b52-d12-projective-subpixel-holdout.py"}
    runs = []
    for fixture in spec["fixtures"]:
        for source_repeat in (1, 2):
            for frame in (0, 1):
                cell_id = f"{fixture['id']}_F{frame}_R{source_repeat}"; cell = output_root / "sources" / cell_id; exr, report = cell / "source.exr", cell / "source.report.json"
                argv = [blender, *spec["runtime"]["blender"]["launchFlags"], "--python", str(tools["source"]), "--", "--spec", str(spec_path), "--fixture", fixture["id"], "--frame", str(frame), "--repeat", str(source_repeat), "--output-exr", str(exr), "--report", str(report)]
                with tempfile.TemporaryDirectory(prefix="bfs-d12-config-") as config, tempfile.TemporaryDirectory(prefix="bfs-d12-scripts-") as scripts:
                    completed = run(argv, root, environment(spec, config, scripts), cell / "stdout.log", cell / "stderr.log")
                record = record_report("SOURCE", cell_id, argv, completed, report, root); record.update({"fixtureId": fixture["id"], "frame": frame, "sourceRepeat": source_repeat, "exrUri": str(exr)})
                if completed.returncode != 0 or not exr.is_file() or not report.is_file(): fail(output_root, "SOURCE", record, runs)
                record["exrSha256"] = sha(exr); runs.append(record)
    source_by_cell = {(row["fixtureId"], row["frame"], row["sourceRepeat"]): row for row in runs if row["stage"] == "SOURCE"}
    for fixture in spec["fixtures"]:
        for source_repeat in (1, 2):
            fixture_id = fixture["id"]; previous, current = source_by_cell[(fixture_id, 0, source_repeat)], source_by_cell[(fixture_id, 1, source_repeat)]; cell_id = f"{fixture_id}_R{source_repeat}"
            adapter_cell = output_root / "adapters" / cell_id; arrays, report = adapter_cell / "arrays", adapter_cell / "adapter.report.json"
            argv = [python, str(tools["adapter"]), "--spec", str(spec_path), "--fixture", fixture_id, "--repeat", str(source_repeat), "--previous-exr", previous["exrUri"], "--current-exr", current["exrUri"], "--previous-report", previous["reportUri"], "--current-report", current["reportUri"], "--output-dir", str(arrays), "--report", str(report)]
            completed = run(argv, root, environment(spec), adapter_cell / "stdout.log", adapter_cell / "stderr.log"); record = record_report("ADAPTER", cell_id, argv, completed, report, root); record.update({"fixtureId": fixture_id, "sourceRepeat": source_repeat, "arraysUri": str(arrays)})
            if completed.returncode != 0 or not report.is_file(): fail(output_root, "ADAPTER", record, runs)
            runs.append(record); reconstructor_records = {}
            for producer, executable, tool_key in (("python", python, "pythonReconstructor"), ("node", node, "nodeReconstructor")):
                recon_cell = output_root / "reconstructors" / producer / cell_id; recon_arrays, recon_report = recon_cell / "arrays", recon_cell / "reconstructor.report.json"
                argv = [executable, str(tools[tool_key]), "--spec", str(spec_path), "--fixture", fixture_id, "--repeat", str(source_repeat), "--input-dir", str(arrays), "--adapter-report", str(report), "--output-dir", str(recon_arrays), "--report", str(recon_report)]
                completed = run(argv, root, environment(spec), recon_cell / "stdout.log", recon_cell / "stderr.log"); record = record_report(f"RECONSTRUCTOR_{producer.upper()}", f"{producer}_{cell_id}", argv, completed, recon_report, root); record.update({"fixtureId": fixture_id, "sourceRepeat": source_repeat, "producer": producer, "arraysUri": str(recon_arrays)})
                if completed.returncode != 0 or not recon_report.is_file(): fail(output_root, record["stage"], record, runs)
                runs.append(record); reconstructor_records[producer] = record
            encoder_cell = output_root / "encoders" / cell_id; encoded_exr, encoder_report = encoder_cell / "reconstructed.exr", encoder_cell / "encoder.report.json"; python_recon = reconstructor_records["python"]; reconstructed = Path(python_recon["arraysUri"]) / "reconstructed.rgba32"
            argv = [python, str(tools["encoder"]), "--spec", str(spec_path), "--fixture", fixture_id, "--source-repeat", str(source_repeat), "--input", str(reconstructed), "--reconstructor-report", python_recon["reportUri"], "--output", str(encoded_exr), "--report", str(encoder_report)]
            completed = run(argv, root, environment(spec), encoder_cell / "stdout.log", encoder_cell / "stderr.log"); record = record_report("ENCODER", cell_id, argv, completed, encoder_report, root); record.update({"fixtureId": fixture_id, "sourceRepeat": source_repeat, "exrUri": str(encoded_exr)})
            if completed.returncode != 0 or not encoded_exr.is_file() or not encoder_report.is_file(): fail(output_root, "ENCODER", record, runs)
            record["exrSha256"] = sha(encoded_exr); runs.append(record)
            for bridge_repeat in (1, 2):
                bridge_id = f"{cell_id}_B{bridge_repeat}"; bridge_cell = output_root / "bridges" / bridge_id; bridge_exr, bridge_report = bridge_cell / "reconstructed.exr", bridge_cell / "bridge.report.json"
                argv = [blender, *spec["runtime"]["blender"]["launchFlags"], "--python", str(tools["bridge"]), "--", "--spec", str(spec_path), "--fixture", fixture_id, "--source-repeat", str(source_repeat), "--bridge-repeat", str(bridge_repeat), "--input", str(encoded_exr), "--output", str(bridge_exr), "--report", str(bridge_report)]
                with tempfile.TemporaryDirectory(prefix="bfs-d12-config-") as config, tempfile.TemporaryDirectory(prefix="bfs-d12-scripts-") as scripts:
                    completed = run(argv, root, environment(spec, config, scripts), bridge_cell / "stdout.log", bridge_cell / "stderr.log")
                record = record_report("BRIDGE", bridge_id, argv, completed, bridge_report, root); record.update({"fixtureId": fixture_id, "sourceRepeat": source_repeat, "bridgeRepeat": bridge_repeat, "exrUri": str(bridge_exr)})
                if completed.returncode != 0 or not bridge_exr.is_file() or not bridge_report.is_file(): fail(output_root, "BRIDGE", record, runs)
                record["exrSha256"] = sha(bridge_exr); runs.append(record)
    preanalysis_pids = [row["pid"] for row in runs]
    stage_counts = {name: sum(row["stage"] == name for row in runs) for name in ("SOURCE", "ADAPTER", "RECONSTRUCTOR_PYTHON", "RECONSTRUCTOR_NODE", "ENCODER", "BRIDGE")}
    receipt_body = {"schemaVersion": "bfs.blenderProjectiveSubpixelRunReceipt.v0.1", "experimentId": spec["experimentId"], "runnerPid": os.getpid(), "preregistration": {"commit": PREREGISTRATION_COMMIT, "specUri": str(spec_path.relative_to(root)), "specSha256": SPEC_SHA256}, "correction": {"id": correction["correctionId"], "commit": CORRECTION_PREREGISTRATION_COMMIT, "specUri": str(correction_path.relative_to(root)), "specSha256": CORRECTION_SPEC_SHA256, "invalidFailureSha256": correction["invalidExecution"]["failureSha256"], "newRoot": correction["execution"]["formalOutputRoot"]}, "preflight": {"uri": str(preflight_path), "sha256": sha(preflight_path), "status": preflight["status"], "freezeCommit": preflight["freezeCommit"]}, "tools": preflight["tools"], "diskAdmission": disk, "runs": runs, "preAnalysisOperationCounts": {"totalChildProcesses": len(runs), "uniqueChildPids": len(set(preanalysis_pids)), "stageCounts": stage_counts}}
    receipt = {**receipt_body, "receiptHash": canonical_hash(receipt_body)}; receipt_path = output_root / "run.receipt.json"; receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n")
    result_path = output_root / "results.json"; analyzer_argv = [python, str(tools["analyzer"]), "--spec", str(spec_path), "--formal-root", str(output_root), "--receipt", str(receipt_path), "--preflight", str(preflight_path), "--output", str(result_path)]
    completed = run(analyzer_argv, root, environment(spec), output_root / "analysis.stdout.log", output_root / "analysis.stderr.log")
    if completed.returncode != 0 or not result_path.is_file(): fail(output_root, "ANALYSIS", {"exitCode": completed.returncode, "argv": normalized(analyzer_argv, root), "stdout": completed.stdout, "stderr": completed.stderr}, runs)
    result = json.loads(result_path.read_text()); print(f"BFS_B52_D12_C1_RUN_OK verdict={result['verdict']} result={sha(result_path)} receipt={sha(receipt_path)}")


if __name__ == "__main__": main()
