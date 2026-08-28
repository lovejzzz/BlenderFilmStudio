#!/usr/bin/env python3
"""Single-use formal runner for B52-D12.11-I1."""
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


SPEC_SHA256 = "89dd3637ffe5af3544e8cd8aca8869eedd8b1a1867d41e08a354e5cd0c3b2a0e"
H1_SPEC_SHA256 = "c2756a20e314cf470698ef7af6160154b8d7e2d5e8531ce6591b2509a8730dbc"


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canon(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    repo = Path.cwd().resolve()
    spec_path = args.spec.resolve()
    preflight_path = args.preflight.resolve()
    root = args.output_root.resolve()
    intervention = json.loads(spec_path.read_text())
    h1_path = repo / intervention["parents"]["h1Spec"]["uri"]
    if sha_file(spec_path) != SPEC_SHA256 or sha_file(h1_path) != H1_SPEC_SHA256:
        raise RuntimeError("D12.11-I1 spec identity mismatch")
    spec = json.loads(h1_path.read_text())
    preflight = json.loads(preflight_path.read_text())
    if sha_file(spec_path) != SPEC_SHA256 or preflight.get("preflightHash") != canon({key: value for key, value in preflight.items() if key != "preflightHash"}) or preflight.get("status") != "ACCEPTED":
        raise RuntimeError("D12.11-I1 identity/admission mismatch")
    if root.exists() or root != (repo / intervention["diskAdmission"]["formalRoot"]).resolve():
        raise RuntimeError("refusing to reuse or redirect D12.11-I1 formal root")
    tool_paths = intervention["freshness"]["newFormalToolPaths"] + intervention["freshness"]["reusedFrozenTools"]
    tool_hashes = {uri: sha_file(repo / uri) for uri in tool_paths}
    if tool_hashes != preflight["toolHashes"]:
        raise RuntimeError("D12.11-I1 tools differ from preflight")
    available = shutil.disk_usage(repo).free
    projected = intervention["diskAdmission"]["projectedWriteBytes"]
    reserve = intervention["diskAdmission"]["minimumReserveBytes"]
    if available - projected < reserve:
        raise RuntimeError("D12.11-I1 disk admission rejected")
    root.mkdir(parents=True, exist_ok=False)
    marker = {"experimentId": intervention["experimentId"], "createdAtUtc": dt.datetime.now(dt.timezone.utc).isoformat(), "pid": os.getpid(), "specSha256": SPEC_SHA256}
    marker_path = root / ".formal-root-created.json"
    marker_path.write_text(json.dumps(marker, indent=2, sort_keys=True) + "\n")
    base_env = {"PATH": os.environ.get("PATH", ""), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "OCIO": str((repo / spec["runtime"]["ocio"]["uri"]).resolve())}
    children = []
    started = time.monotonic()

    def child(role: str, cell: str, argv: list[str], env: dict[str, str] | None = None):
        logs = root / "logs" / role.lower()
        logs.mkdir(parents=True, exist_ok=True)
        safe = cell.replace("/", "_")
        stdout_path = logs / f"{safe}.stdout.log"
        stderr_path = logs / f"{safe}.stderr.log"
        tick = time.monotonic()
        process = subprocess.Popen(argv, cwd=repo, env=env or base_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate()
        stdout_path.write_text(stdout)
        stderr_path.write_text(stderr)
        row = {
            "role": role,
            "cell": cell,
            "pid": process.pid,
            "exitCode": process.returncode,
            "elapsedSeconds": round(time.monotonic() - tick, 6),
            "argv": argv,
            "stdout": {"uri": str(stdout_path), "sha256": sha_file(stdout_path)},
            "stderr": {"uri": str(stderr_path), "sha256": sha_file(stderr_path)},
        }
        children.append(row)
        print(f"BFS_D1211_CHILD role={role} cell={cell} pid={process.pid} exit={process.returncode}", flush=True)
        if process.returncode != 0:
            failure = {
                "schemaVersion": "bfs.blenderMaterialIndexOwnerIntegrationFailure.v0.1",
                "experimentId": intervention["experimentId"],
                "failedChild": row,
                "completedChildren": children,
                "specSha256": SPEC_SHA256,
                "preflightSha256": sha_file(preflight_path),
                "formalRootMarkerSha256": sha_file(marker_path),
            }
            failure["failureHash"] = canon(failure)
            (root / "run.failure.json").write_text(json.dumps(failure, indent=2, sort_keys=True) + "\n")
            raise RuntimeError(f"D12.11-I1 child failed: {role} {cell}")

    blender = spec["runtime"]["blender"]["executable"]
    python = spec["runtime"]["python"]["executable"]
    node = spec["runtime"]["node"]["executable"]
    source = str(repo / "blender/render_b52_d12_11_material_owner_source.py")
    adapter = str(repo / "scripts/adapt-b52-d12-11-material-owner-source.py")
    py_consumer = str(repo / "scripts/reconstruct-b52-d12-11-material-owner.py")
    node_consumer = str(repo / "scripts/reconstruct-b52-d12-11-material-owner.mjs")
    typed_spec = str((repo / intervention["parents"]["typedEnvelopeSpec"]["uri"]).resolve())
    typed_py = str((repo / intervention["parents"]["typedEnvelopePython"]["uri"]).resolve())
    typed_node = str((repo / intervention["parents"]["typedEnvelopeNode"]["uri"]).resolve())
    for fixture in spec["fixtures"]:
        fixture_id = fixture["id"]
        for repeat in (1, 2):
            for frame in (0, 1):
                cell = f"{fixture_id}/R{repeat}/F{frame}"
                source_dir = root / "sources" / fixture_id / f"R{repeat}" / f"frame-{frame}"
                runtime = root / "runtime" / fixture_id / f"R{repeat}" / f"frame-{frame}"
                env = {**base_env}
                for key, suffix in (("TMPDIR", "tmp"), ("BLENDER_USER_CONFIG", "config"), ("BLENDER_USER_SCRIPTS", "scripts")):
                    target = runtime / suffix
                    target.mkdir(parents=True, exist_ok=True)
                    env[key] = str(target)
                child("SOURCE", cell, [blender, *spec["runtime"]["blender"]["launchFlags"], "--python", source, "--", "--spec", str(spec_path), "--fixture", fixture_id, "--frame", str(frame), "--repeat", str(repeat), "--output-exr", str(source_dir / "source.exr"), "--report", str(source_dir / "report.json")], env)
            adapter_dir = root / "adapters" / fixture_id / f"R{repeat}"
            source_pair = root / "sources" / fixture_id / f"R{repeat}"
            child("ADAPTER", f"{fixture_id}/R{repeat}", [python, adapter, "--spec", str(spec_path), "--fixture", fixture_id, "--repeat", str(repeat), "--previous-exr", str(source_pair / "frame-0/source.exr"), "--current-exr", str(source_pair / "frame-1/source.exr"), "--previous-report", str(source_pair / "frame-0/report.json"), "--current-report", str(source_pair / "frame-1/report.json"), "--output-dir", str(adapter_dir / "arrays"), "--report", str(adapter_dir / "report.json")])
            for producer, executable, tool in (("python", python, py_consumer), ("node", node, node_consumer)):
                consumer_dir = root / "consumers" / producer / fixture_id / f"R{repeat}"
                child(f"CONSUMER_{producer.upper()}", f"{fixture_id}/R{repeat}", [executable, tool, "--spec", str(spec_path), "--fixture", fixture_id, "--repeat", str(repeat), "--input-dir", str(adapter_dir / "arrays"), "--adapter-report", str(adapter_dir / "report.json"), "--output-dir", str(consumer_dir / "arrays"), "--report", str(consumer_dir / "report.json")])
                envelope_dir = root / "envelopes" / producer / fixture_id / f"R{repeat}"
                child("ENVELOPE_PYTHON", f"{producer}/{fixture_id}/R{repeat}", [python, typed_py, "--spec", typed_spec, "--input", str(consumer_dir / "report.json"), "--output", str(envelope_dir / "report.python-envelope.json")])
                child("ENVELOPE_NODE", f"{producer}/{fixture_id}/R{repeat}", [node, typed_node, "--spec", typed_spec, "--input", str(consumer_dir / "report.json"), "--output", str(envelope_dir / "report.node-envelope.json")])
    operation_counts = {
        "sourceRenders": sum(row["role"] == "SOURCE" for row in children),
        "adapters": sum(row["role"] == "ADAPTER" for row in children),
        "pythonConsumers": sum(row["role"] == "CONSUMER_PYTHON" for row in children),
        "nodeConsumers": sum(row["role"] == "CONSUMER_NODE" for row in children),
        "pythonEnvelopeEncoders": sum(row["role"] == "ENVELOPE_PYTHON" for row in children),
        "nodeEnvelopeEncoders": sum(row["role"] == "ENVELOPE_NODE" for row in children),
        "analyzers": 1,
        "audits": 1,
        "modelCalls": 0,
        "networkCalls": 0,
    }
    execution = {
        "schemaVersion": "bfs.blenderMaterialIndexOwnerIntegrationExecution.v0.1",
        "experimentId": intervention["experimentId"],
        "rootCreatedFresh": True,
        "formalRootMarker": {"uri": str(marker_path), "sha256": sha_file(marker_path)},
        "spec": {"uri": str(spec_path), "sha256": sha_file(spec_path)},
        "preflight": {"uri": str(preflight_path), "sha256": sha_file(preflight_path), "preflightHash": preflight["preflightHash"]},
        "toolFreezeCommit": preflight["toolFreezeCommit"],
        "toolHashes": tool_hashes,
        "diskAdmission": {"availableBytes": available, "projectedWriteBytes": projected, "minimumReserveBytes": reserve, "freeAfterProjectedBytes": available - projected, "status": "ACCEPTED"},
        "operationCounts": operation_counts,
        "children": children.copy(),
    }
    execution["executionHash"] = canon(execution)
    execution_path = root / "execution.json"
    execution_path.write_text(json.dumps(execution, indent=2, sort_keys=True, allow_nan=False) + "\n")
    child("ANALYZER", "FORMAL", [python, str(repo / "scripts/analyze-b52-d12-11-material-owner.py"), "--spec", str(spec_path), "--root", str(root), "--preflight", str(preflight_path), "--execution", str(execution_path), "--output", str(root / "results.json")])
    result = json.loads((root / "results.json").read_text())
    child("AUDIT", "FORMAL", [python, str(repo / "scripts/audit-b52-d12-11-material-owner.py"), "--spec", str(spec_path), "--root", str(root), "--result", str(root / "results.json"), "--execution", str(execution_path), "--output", str(root / "audit.json")])
    audit = json.loads((root / "audit.json").read_text())
    pids = [row["pid"] for row in children]
    expected = intervention["processMatrix"]["totalUniqueChildProcessesIncludingAudit"]
    process_ok = len(children) == expected and len(set(pids)) == expected and all(row["exitCode"] == 0 for row in children)
    body = {
        "schemaVersion": "bfs.blenderMaterialIndexOwnerIntegrationReceipt.v0.1",
        "experimentId": intervention["experimentId"],
        "executedAtUtc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "elapsedSeconds": round(time.monotonic() - started, 6),
        "spec": {"uri": str(spec_path), "sha256": sha_file(spec_path)},
        "preflight": {"uri": str(preflight_path), "sha256": sha_file(preflight_path), "preflightHash": preflight["preflightHash"]},
        "execution": {"uri": str(execution_path), "sha256": sha_file(execution_path), "executionHash": execution["executionHash"]},
        "result": {"uri": str(root / "results.json"), "sha256": sha_file(root / "results.json"), "evidenceHash": result["evidenceHash"], "verdict": result["verdict"]},
        "audit": {"uri": str(root / "audit.json"), "sha256": sha_file(root / "audit.json"), "auditHash": audit["auditHash"], "passed": audit["passed"]},
        "toolFreezeCommit": preflight["toolFreezeCommit"],
        "toolHashes": tool_hashes,
        "processes": {"expected": expected, "observed": len(children), "unique": len(set(pids)), "passed": process_ok, "children": children},
        "operationCounts": operation_counts,
    }
    receipt = {**body, "receiptHash": canon(body)}
    (root / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n")
    if not process_ok or not audit["passed"]:
        raise RuntimeError("D12.11-I1 process/audit totality failure")
    print(f"BFS_B52_D1211_FORMAL_COMPLETE verdict={result['verdict']} checks={result['checkPassed']}/{result['checkTotal']} attacks={result['mutationAttackPassed']}/{result['mutationAttackTotal']} audit={audit['checkPassed']}/{audit['checkTotal']} receipt={receipt['receiptHash']}")


if __name__ == "__main__":
    main()
