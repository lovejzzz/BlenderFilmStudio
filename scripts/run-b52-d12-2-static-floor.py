#!/usr/bin/env python3
"""Single-use formal runner for B52-D12.2."""

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


SPEC_SHA256 = "fa63daa0c3b7b3f080a488aa0fc84996fd52cd731efce94ebe28bbc81b55d9d3"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    repo = Path.cwd().resolve()
    spec_path = args.spec.resolve()
    preflight_path = args.preflight.resolve()
    root = args.output_root.resolve()
    spec = json.loads(spec_path.read_text())
    preflight = json.loads(preflight_path.read_text())
    preflight_body = {key: value for key, value in preflight.items() if key != "preflightHash"}
    if sha256_file(spec_path) != SPEC_SHA256:
        raise RuntimeError("B52-D12.2 spec identity mismatch")
    if preflight.get("preflightHash") != canonical_hash(preflight_body) or preflight.get("status") != "ACCEPTED":
        raise RuntimeError("B52-D12.2 preflight is not accepted or self-consistent")
    if root.exists():
        raise RuntimeError("refusing to reuse D12.2 formal root")
    current_tools = {path: sha256_file(repo / path) for path in spec["formalToolPaths"]}
    if current_tools != preflight["toolHashes"]:
        raise RuntimeError("D12.2 tools differ from admitted preflight")
    available = shutil.disk_usage(repo).free
    projected = spec["diskAdmission"]["projectedWriteBytes"]
    reserve = spec["diskAdmission"]["minimumReserveBytes"]
    if available - projected < reserve:
        raise RuntimeError("D12.2 formal disk admission rejected")
    root.mkdir(parents=True, exist_ok=False)
    marker = {"experimentId": spec["experimentId"], "createdAtUtc": dt.datetime.now(dt.timezone.utc).isoformat(), "pid": os.getpid(), "specSha256": SPEC_SHA256}
    marker_path = root / ".formal-root-created.json"
    marker_path.write_text(json.dumps(marker, indent=2, sort_keys=True) + "\n")
    children = []
    started = time.monotonic()
    base_env = {
        "PATH": os.environ.get("PATH", ""), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
        "OCIO": str((repo / spec["runtime"]["ocio"]["uri"]).resolve()),
    }

    def child(role: str, cell: str, argv: list[str], env: dict[str, str] | None = None) -> dict:
        log_dir = root / "logs" / role.lower()
        log_dir.mkdir(parents=True, exist_ok=True)
        safe = cell.replace("/", "_")
        stdout_path, stderr_path = log_dir / f"{safe}.stdout.log", log_dir / f"{safe}.stderr.log"
        tick = time.monotonic()
        process = subprocess.Popen(argv, cwd=repo, env=env or base_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate()
        stdout_path.write_text(stdout)
        stderr_path.write_text(stderr)
        row = {
            "role": role, "cell": cell, "pid": process.pid, "exitCode": process.returncode,
            "elapsedSeconds": round(time.monotonic() - tick, 6), "argv": argv,
            "stdout": {"uri": str(stdout_path), "sha256": sha256_file(stdout_path)},
            "stderr": {"uri": str(stderr_path), "sha256": sha256_file(stderr_path)},
        }
        children.append(row)
        print(f"BFS_D122_CHILD role={role} cell={cell} pid={process.pid} exit={process.returncode}", flush=True)
        if process.returncode != 0:
            failure = {
                "schemaVersion": "bfs.blenderStaticVectorFloorRunFailure.v0.1", "experimentId": spec["experimentId"],
                "failedChild": row, "completedChildren": children, "specSha256": SPEC_SHA256,
                "preflightSha256": sha256_file(preflight_path), "formalRootMarkerSha256": sha256_file(marker_path),
            }
            failure["failureHash"] = canonical_hash(failure)
            (root / "run.failure.json").write_text(json.dumps(failure, indent=2, sort_keys=True) + "\n")
            raise RuntimeError(f"D12.2 child failed: {role} {cell}")
        return row

    blender = spec["runtime"]["blender"]["executable"]
    python = spec["runtime"]["python"]["executable"]
    node = spec["runtime"]["node"]["executable"]
    source_tool = str(repo / "blender/render_b52_d12_2_static_floor_source.py")
    adapter_tool = str(repo / "scripts/adapt-b52-d12-2-static-floor.py")
    python_consumer = str(repo / "scripts/reconstruct-b52-d12-2-static-floor.py")
    node_consumer = str(repo / "scripts/reconstruct-b52-d12-2-static-floor.mjs")
    typed_spec = str((repo / spec["parents"]["typedEnvelopeSpec"]["uri"]).resolve())
    typed_python = str((repo / spec["parents"]["typedEnvelopePython"]["uri"]).resolve())
    typed_node = str((repo / spec["parents"]["typedEnvelopeNode"]["uri"]).resolve())

    for fixture in spec["fixtures"]:
        fixture_id = fixture["id"]
        for repeat in (1, 2):
            for frame in (0, 1):
                cell = f"{fixture_id}/R{repeat}/F{frame}"
                source_dir = root / "sources" / fixture_id / f"R{repeat}" / f"frame-{frame}"
                runtime_dir = root / "runtime" / fixture_id / f"R{repeat}" / f"frame-{frame}"
                render_env = {**base_env}
                for key, suffix in (("TMPDIR", "tmp"), ("BLENDER_USER_CONFIG", "config"), ("BLENDER_USER_SCRIPTS", "scripts")):
                    target = runtime_dir / suffix
                    target.mkdir(parents=True, exist_ok=True)
                    render_env[key] = str(target)
                child("SOURCE", cell, [
                    blender, *spec["runtime"]["blender"]["launchFlags"], "--python", source_tool, "--",
                    "--spec", str(spec_path), "--fixture", fixture_id, "--frame", str(frame), "--repeat", str(repeat),
                    "--output-exr", str(source_dir / "source.exr"), "--report", str(source_dir / "report.json"),
                ], render_env)
            adapter_dir = root / "adapters" / fixture_id / f"R{repeat}"
            child("ADAPTER", f"{fixture_id}/R{repeat}", [
                python, adapter_tool, "--spec", str(spec_path), "--fixture", fixture_id, "--repeat", str(repeat),
                "--previous-exr", str(root / "sources" / fixture_id / f"R{repeat}" / "frame-0/source.exr"),
                "--current-exr", str(root / "sources" / fixture_id / f"R{repeat}" / "frame-1/source.exr"),
                "--previous-report", str(root / "sources" / fixture_id / f"R{repeat}" / "frame-0/report.json"),
                "--current-report", str(root / "sources" / fixture_id / f"R{repeat}" / "frame-1/report.json"),
                "--output-dir", str(adapter_dir / "arrays"), "--report", str(adapter_dir / "report.json"),
            ])
            for producer, executable, tool in (("python", python, python_consumer), ("node", node, node_consumer)):
                consumer_dir = root / "consumers" / producer / fixture_id / f"R{repeat}"
                child(f"CONSUMER_{producer.upper()}", f"{fixture_id}/R{repeat}", [
                    executable, tool, "--spec", str(spec_path), "--fixture", fixture_id, "--repeat", str(repeat),
                    "--input-dir", str(adapter_dir / "arrays"), "--adapter-report", str(adapter_dir / "report.json"),
                    "--output-dir", str(consumer_dir / "arrays"), "--report", str(consumer_dir / "report.json"),
                ])
                envelope_dir = root / "envelopes" / producer / fixture_id / f"R{repeat}"
                child("ENVELOPE_PYTHON", f"{producer}/{fixture_id}/R{repeat}", [
                    python, typed_python, "--spec", typed_spec, "--input", str(consumer_dir / "report.json"),
                    "--output", str(envelope_dir / "report.python-envelope.json"),
                ])
                child("ENVELOPE_NODE", f"{producer}/{fixture_id}/R{repeat}", [
                    node, typed_node, "--spec", typed_spec, "--input", str(consumer_dir / "report.json"),
                    "--output", str(envelope_dir / "report.node-envelope.json"),
                ])

    execution = {
        "schemaVersion": "bfs.blenderStaticVectorFloorExecution.v0.1", "experimentId": spec["experimentId"],
        "rootCreatedFresh": True, "formalRootMarker": {"uri": str(marker_path), "sha256": sha256_file(marker_path)},
        "spec": {"uri": str(spec_path), "sha256": sha256_file(spec_path)},
        "preflight": {"uri": str(preflight_path), "sha256": sha256_file(preflight_path), "preflightHash": preflight["preflightHash"]},
        "toolFreezeCommit": preflight["toolFreezeCommit"], "toolHashes": current_tools,
        "diskAdmission": {"availableBytes": available, "projectedWriteBytes": projected, "minimumReserveBytes": reserve, "freeAfterProjectedBytes": available - projected, "status": "ACCEPTED"},
        "children": children,
    }
    execution["executionHash"] = canonical_hash(execution)
    execution_path = root / "execution.json"
    execution_path.write_text(json.dumps(execution, indent=2, sort_keys=True, allow_nan=False) + "\n")
    analyzer_row = child("ANALYZER", "FORMAL", [
        python, str(repo / "scripts/analyze-b52-d12-2-static-floor.py"), "--spec", str(spec_path), "--root", str(root),
        "--preflight", str(preflight_path), "--execution", str(execution_path), "--output", str(root / "results.json"),
    ])
    result = json.loads((root / "results.json").read_text())
    all_pids = [row["pid"] for row in children]
    process_totality = len(children) == spec["processBoundary"]["expectedUniqueChildProcesses"] and len(set(all_pids)) == len(all_pids)
    body = {
        "schemaVersion": "bfs.blenderStaticVectorFloorReceipt.v0.1", "experimentId": spec["experimentId"],
        "executedAtUtc": dt.datetime.now(dt.timezone.utc).isoformat(), "elapsedSeconds": round(time.monotonic() - started, 6),
        "spec": {"uri": str(spec_path), "sha256": sha256_file(spec_path)},
        "preflight": {"uri": str(preflight_path), "sha256": sha256_file(preflight_path), "preflightHash": preflight["preflightHash"]},
        "execution": {"uri": str(execution_path), "sha256": sha256_file(execution_path), "executionHash": execution["executionHash"]},
        "result": {"uri": str(root / "results.json"), "sha256": sha256_file(root / "results.json"), "evidenceHash": result["evidenceHash"], "verdict": result["verdict"]},
        "toolFreezeCommit": preflight["toolFreezeCommit"], "toolHashes": current_tools,
        "processes": {"expected": spec["processBoundary"]["expectedUniqueChildProcesses"], "observed": len(children), "unique": len(set(all_pids)), "passed": process_totality, "children": children},
        "operationCounts": {
            "sourceRenders": sum(row["role"] == "SOURCE" for row in children), "adapters": sum(row["role"] == "ADAPTER" for row in children),
            "pythonConsumers": sum(row["role"] == "CONSUMER_PYTHON" for row in children), "nodeConsumers": sum(row["role"] == "CONSUMER_NODE" for row in children),
            "pythonEnvelopeEncoders": sum(row["role"] == "ENVELOPE_PYTHON" for row in children), "nodeEnvelopeEncoders": sum(row["role"] == "ENVELOPE_NODE" for row in children),
            "analyzers": sum(row["role"] == "ANALYZER" for row in children), "modelCalls": 0, "networkCalls": 0,
        },
    }
    receipt = {**body, "receiptHash": canonical_hash(body)}
    (root / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n")
    if not process_totality:
        raise RuntimeError("D12.2 process totality failure")
    print(f"BFS_B52_D122_FORMAL_COMPLETE verdict={result['verdict']} exactZero={result['exactZeroObservation']} receipt={receipt['receiptHash']}")


if __name__ == "__main__":
    main()
