#!/usr/bin/env python3
"""Run the frozen D12.14-P1 Position-oracle development matrix."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time


SPEC_SHA256 = "2ccffbcfe861fd80406901b417cf4cd2b2b8977c6925d6fb73e3d0328092efe3"
SOURCE_SHA256 = "9e1d338608306cfc89ed2111560ed88e46b860549505e084388e4150a7b3def2"
ANALYZER_SHA256 = "6cf55af97af37dfe4e94e048246a3796b1a143760c0077fd6f343ea5fcb8b302"
MINIMUM_FREE_AFTER = 100 * 1024 * 1024 * 1024
MAXIMUM_PROJECTED_WRITE = 32 * 1024 * 1024


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    return sha_bytes(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode())


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    return parser.parse_args()


def write_json(path: Path, body: dict, hash_name: str) -> dict:
    value = {**body, hash_name: canonical_hash(body)}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
    return value


def run_child(command: list[str], environment: dict[str, str], log_root: Path, name: str) -> dict:
    started = time.monotonic()
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment)
    stdout, stderr = process.communicate()
    stdout_path = log_root / f"{name}.stdout.log"
    stderr_path = log_root / f"{name}.stderr.log"
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stdout_path.write_bytes(stdout)
    stderr_path.write_bytes(stderr)
    return {
        "name": name,
        "pid": process.pid,
        "command": command,
        "exitCode": process.returncode,
        "elapsedSeconds": round(time.monotonic() - started, 6),
        "stdoutUri": str(stdout_path),
        "stdoutSha256": sha_bytes(stdout),
        "stderrUri": str(stderr_path),
        "stderrSha256": sha_bytes(stderr),
    }


def main() -> None:
    cli = arguments()
    repo = Path(__file__).resolve().parents[1]
    spec_path = cli.spec.resolve()
    output_root = cli.output_root.resolve()
    expected_root = (repo / "experiments/blender-material-owner-rigid-directional-position-oracle-development-v0-1").resolve()
    source_tool = repo / "blender/develop_b52_d12_14_position_oracle_probe.py"
    analyzer_tool = repo / "scripts/analyze-b52-d12-14-position-oracle-probe.py"
    if sha_file(spec_path) != SPEC_SHA256:
        raise RuntimeError("P1 runner spec identity mismatch")
    if sha_file(source_tool) != SOURCE_SHA256 or sha_file(analyzer_tool) != ANALYZER_SHA256:
        raise RuntimeError("P1 runner frozen tool identity mismatch")
    if output_root != expected_root or output_root.exists():
        raise RuntimeError("P1 runner requires the exact fresh output root")
    free_before = shutil.disk_usage(repo).free
    if free_before - MAXIMUM_PROJECTED_WRITE < MINIMUM_FREE_AFTER:
        raise RuntimeError("P1 disk reserve gate failed")

    spec = json.loads(spec_path.read_text())
    runtime = spec["runtime"]
    blender = runtime["blender"]["executable"]
    python = runtime["python"]["executable"]
    if sha_file(Path(blender)) != runtime["blender"]["sha256"] or sha_file(Path(python)) != runtime["python"]["sha256"]:
        raise RuntimeError("P1 runner runtime identity mismatch")
    ocio = (repo / runtime["ocio"]["uri"]).resolve()
    if sha_file(ocio) != runtime["ocio"]["sha256"]:
        raise RuntimeError("P1 runner OCIO identity mismatch")

    output_root.mkdir(parents=True, exist_ok=False)
    log_root = output_root / "logs"
    children = []
    failure_message = None
    started = time.monotonic()
    base_environment = {
        key: value
        for key, value in os.environ.items()
        if key in {"PATH", "LANG", "LC_ALL", "TMPDIR"}
    }
    base_environment["OCIO"] = str(ocio)
    try:
        with tempfile.TemporaryDirectory(prefix="bfs-d1214p1-") as temporary:
            for repeat in (1, 2):
                repeat_root = output_root / "sources" / f"R{repeat}"
                config = Path(temporary) / f"config-r{repeat}"
                scripts = Path(temporary) / f"scripts-r{repeat}"
                config.mkdir()
                scripts.mkdir()
                environment = {**base_environment, "BLENDER_USER_CONFIG": str(config), "BLENDER_USER_SCRIPTS": str(scripts)}
                command = [
                    blender,
                    "--background",
                    "--factory-startup",
                    "--disable-autoexec",
                    "--python-exit-code",
                    "1",
                    "--python",
                    str(source_tool),
                    "--",
                    "--spec",
                    str(spec_path),
                    "--repeat",
                    str(repeat),
                    "--output-exr",
                    str(repeat_root / "frame-1.exr"),
                    "--report",
                    str(repeat_root / "frame-1-report.json"),
                ]
                child = run_child(command, environment, log_root, f"source-r{repeat}")
                children.append(child)
                if child["exitCode"] != 0:
                    raise RuntimeError(f"P1 source R{repeat} failed")

        analyzer_command = [
            python,
            str(analyzer_tool),
            "--spec",
            str(spec_path),
            "--root",
            str(output_root),
            "--output",
            str(output_root / "results.json"),
        ]
        analyzer_environment = {**base_environment}
        child = run_child(analyzer_command, analyzer_environment, log_root, "analyzer")
        children.append(child)
        if child["exitCode"] != 0:
            raise RuntimeError("P1 analyzer failed")
    except Exception as error:
        failure_message = f"{type(error).__name__}: {error}"

    status = "POSITION_ORACLE_DEVELOPMENT_EXECUTION_COMPLETE" if failure_message is None else "POSITION_ORACLE_DEVELOPMENT_EXECUTION_FAILED"
    execution_body = {
        "schemaVersion": "bfs.blenderMaterialOwnerRigidDirectionalPositionOracleDevelopmentExecution.v0.1",
        "experimentId": spec["experimentId"],
        "specSha256": SPEC_SHA256,
        "status": status,
        "scientificVerdict": None,
        "pid": os.getpid(),
        "children": children,
        "childrenSucceeded": sum(row["exitCode"] == 0 for row in children),
        "childrenExpected": 3,
        "failure": failure_message,
        "tools": {
            "source": {"uri": str(source_tool.relative_to(repo)), "sha256": sha_file(source_tool)},
            "analyzer": {"uri": str(analyzer_tool.relative_to(repo)), "sha256": sha_file(analyzer_tool)},
            "runner": {"uri": str(Path(__file__).resolve().relative_to(repo)), "sha256": sha_file(Path(__file__).resolve())},
        },
        "disk": {
            "freeBytesBefore": free_before,
            "maximumProjectedWriteBytes": MAXIMUM_PROJECTED_WRITE,
            "minimumFreeAfterBytes": MINIMUM_FREE_AFTER,
            "freeBytesAfter": shutil.disk_usage(repo).free,
        },
        "elapsedSeconds": round(time.monotonic() - started, 6),
        "operationCounts": {
            "blenderProcesses": sum(row["name"].startswith("source-") for row in children),
            "blenderRenderCalls": sum(row["name"].startswith("source-") and row["exitCode"] == 0 for row in children),
            "analyzerProcesses": sum(row["name"] == "analyzer" for row in children),
            "modelCalls": 0,
            "networkCalls": 0,
        },
    }
    execution = write_json(output_root / "execution.json", execution_body, "executionHash")

    if failure_message is not None:
        failure_body = {
            "schemaVersion": "bfs.blenderMaterialOwnerRigidDirectionalPositionOracleDevelopmentFailure.v0.1",
            "experimentId": spec["experimentId"],
            "status": spec["outcomes"]["failure"],
            "scientificVerdict": None,
            "message": failure_message,
            "executionHash": execution["executionHash"],
        }
        failure = write_json(output_root / "failure.json", failure_body, "failureHash")
        receipt_body = {
            "schemaVersion": "bfs.blenderMaterialOwnerRigidDirectionalPositionOracleDevelopmentReceipt.v0.1",
            "experimentId": spec["experimentId"],
            "status": "FAILED_RECEIPT",
            "scientificVerdict": None,
            "execution": {"sha256": sha_file(output_root / "execution.json"), "executionHash": execution["executionHash"]},
            "failure": {"sha256": sha_file(output_root / "failure.json"), "failureHash": failure["failureHash"]},
        }
        write_json(output_root / "receipt.json", receipt_body, "receiptHash")
        print(f"BFS_D1214P1_FAILED {failure_message}", file=sys.stderr)
        raise SystemExit(1)

    results_path = output_root / "results.json"
    results = json.loads(results_path.read_text())
    artifacts = []
    for path in sorted((output_root / "sources").glob("R*/frame-1*")):
        artifacts.append({"uri": str(path.relative_to(repo)), "sha256": sha_file(path), "bytes": path.stat().st_size})
    receipt_body = {
        "schemaVersion": "bfs.blenderMaterialOwnerRigidDirectionalPositionOracleDevelopmentReceipt.v0.1",
        "experimentId": spec["experimentId"],
        "status": "COMPLETE_RECEIPT",
        "scientificVerdict": None,
        "execution": {"sha256": sha_file(output_root / "execution.json"), "executionHash": execution["executionHash"]},
        "results": {"sha256": sha_file(results_path), "resultHash": results["resultHash"], "developmentVerdict": results["developmentVerdict"]},
        "artifacts": artifacts,
    }
    receipt = write_json(output_root / "receipt.json", receipt_body, "receiptHash")
    print(f"BFS_D1214P1_COMPLETE verdict={results['developmentVerdict']} receipt={receipt['receiptHash']}")


if __name__ == "__main__":
    main()
