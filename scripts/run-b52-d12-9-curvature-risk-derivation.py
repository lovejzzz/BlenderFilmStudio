#!/usr/bin/env python3
"""One-shot runner for exploratory B52-D12.9-D1 derivation."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = arguments()
    repo = Path.cwd().resolve()
    spec_path = args.spec.resolve()
    output_root = args.output_root.resolve()
    if output_root.exists():
        raise RuntimeError("refusing to reuse D12.9-D1 output root")
    spec = json.loads(spec_path.read_text())
    free = shutil.disk_usage(repo).free
    if free < 100 * 1024**3:
        raise RuntimeError("D12.9-D1 disk reserve below 100 GiB")
    output_root.mkdir(parents=True, exist_ok=False)
    marker = {"experimentId": spec["experimentId"], "createdAtUtc": dt.datetime.now(dt.timezone.utc).isoformat(), "pid": os.getpid(), "specSha256": sha_file(spec_path)}
    (output_root / ".derivation-root-created.json").write_text(json.dumps(marker, indent=2, sort_keys=True) + "\n")
    python = spec["runtime"]["python"]["executable"]
    node = spec["runtime"]["node"]["executable"]
    source_root = (repo / spec["sourceEvidence"]["root"]).resolve()
    children = []
    started = time.monotonic()

    def child(role: str, argv: list[str]) -> None:
        log_dir = output_root / "logs"
        log_dir.mkdir(exist_ok=True)
        tick = time.monotonic()
        process = subprocess.Popen(argv, cwd=repo, env={"PATH": os.environ.get("PATH", ""), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"}, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate()
        stdout_path = log_dir / f"{role.lower()}.stdout.log"
        stderr_path = log_dir / f"{role.lower()}.stderr.log"
        stdout_path.write_text(stdout)
        stderr_path.write_text(stderr)
        row = {"role": role, "pid": process.pid, "exitCode": process.returncode, "elapsedSeconds": round(time.monotonic() - tick, 6), "argv": argv, "stdout": {"uri": str(stdout_path), "sha256": sha_file(stdout_path)}, "stderr": {"uri": str(stderr_path), "sha256": sha_file(stderr_path)}}
        children.append(row)
        print(f"BFS_D129_D1_CHILD role={role} pid={process.pid} exit={process.returncode}", flush=True)
        if process.returncode != 0:
            failure = {"schemaVersion": "bfs.blenderMotionAwareCurvatureRiskDerivationFailure.v0.1", "experimentId": spec["experimentId"], "failedChild": row, "completedChildren": children}
            failure["failureHash"] = canonical_hash(failure)
            (output_root / "run.failure.json").write_text(json.dumps(failure, indent=2, sort_keys=True) + "\n")
            raise RuntimeError(f"D12.9-D1 child failed: {role}")

    python_root = output_root / "producers" / "python"
    node_root = output_root / "producers" / "node"
    python_report = output_root / "python-report.json"
    node_report = output_root / "node-report.json"
    child("PYTHON_PRODUCER", [python, str(repo / "scripts/derive-b52-d12-9-curvature-risk.py"), "--spec", str(spec_path), "--source-root", str(source_root), "--output-root", str(python_root), "--report", str(python_report)])
    child("NODE_PRODUCER", [node, str(repo / "scripts/derive-b52-d12-9-curvature-risk.mjs"), "--spec", str(spec_path), "--source-root", str(source_root), "--output-root", str(node_root), "--report", str(node_report)])
    operation_counts = {"pythonProducers": 1, "nodeProducers": 1, "analyzers": 1, "modelCalls": 0, "networkCalls": 0}
    tool_paths = [
        "scripts/derive-b52-d12-9-curvature-risk.py",
        "scripts/derive-b52-d12-9-curvature-risk.mjs",
        "scripts/analyze-b52-d12-9-curvature-risk.py",
        "scripts/run-b52-d12-9-curvature-risk-derivation.py",
    ]
    execution = {
        "schemaVersion": "bfs.blenderMotionAwareCurvatureRiskDerivationExecution.v0.1",
        "experimentId": spec["experimentId"],
        "spec": {"uri": str(spec_path), "sha256": sha_file(spec_path)},
        "sourceRoot": str(source_root),
        "availableBytesBeforeWrite": free,
        "toolHashes": {path: sha_file(repo / path) for path in tool_paths},
        "operationCounts": operation_counts,
        "children": children,
    }
    execution["executionHash"] = canonical_hash(execution)
    execution_path = output_root / "execution.json"
    execution_path.write_text(json.dumps(execution, indent=2, sort_keys=True, allow_nan=False) + "\n")
    analyzer_argv = [python, str(repo / "scripts/analyze-b52-d12-9-curvature-risk.py"), "--spec", str(spec_path), "--source-root", str(source_root), "--python-root", str(python_root), "--node-root", str(node_root), "--python-report", str(python_report), "--node-report", str(node_report), "--execution", str(execution_path), "--output", str(output_root / "results.json")]
    tick = time.monotonic()
    analyzer = subprocess.Popen(analyzer_argv, cwd=repo, env={"PATH": os.environ.get("PATH", ""), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"}, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = analyzer.communicate()
    stdout_path = output_root / "logs" / "analyzer.stdout.log"
    stderr_path = output_root / "logs" / "analyzer.stderr.log"
    stdout_path.write_text(stdout)
    stderr_path.write_text(stderr)
    print(f"BFS_D129_D1_CHILD role=ANALYZER pid={analyzer.pid} exit={analyzer.returncode}", flush=True)
    if analyzer.returncode != 0:
        raise RuntimeError(f"D12.9-D1 analyzer failed: {stderr}")
    result = json.loads((output_root / "results.json").read_text())
    receipt_body = {
        "schemaVersion": "bfs.blenderMotionAwareCurvatureRiskDerivationReceipt.v0.1",
        "experimentId": spec["experimentId"],
        "executedAtUtc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "elapsedSeconds": round(time.monotonic() - started, 6),
        "spec": {"uri": str(spec_path), "sha256": sha_file(spec_path)},
        "execution": {"uri": str(execution_path), "sha256": sha_file(execution_path), "executionHash": execution["executionHash"]},
        "result": {"uri": str(output_root / "results.json"), "sha256": sha_file(output_root / "results.json"), "resultHash": result["resultHash"], "evidenceHash": result["evidenceHash"], "verdict": result["verdict"]},
        "processes": {"expected": 3, "observed": 3, "unique": len({row["pid"] for row in children} | {analyzer.pid}), "producerChildren": children, "analyzer": {"pid": analyzer.pid, "elapsedSeconds": round(time.monotonic() - tick, 6), "stdout": {"uri": str(stdout_path), "sha256": sha_file(stdout_path)}, "stderr": {"uri": str(stderr_path), "sha256": sha_file(stderr_path)}}},
        "operationCounts": operation_counts,
    }
    receipt = {**receipt_body, "receiptHash": canonical_hash(receipt_body)}
    (output_root / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D129_D1_COMPLETE verdict={result['verdict']} checks={result['checkPassed']}/{result['checkTotal']} receipt={receipt['receiptHash']}")


if __name__ == "__main__":
    main()
