#!/usr/bin/env python3
"""Single-use formal runner for B52-D12.10-P1."""
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


SPEC_SHA256 = "7eb76c00baad8cbc4f996ec7a139e6a3cb1fd90c1c02391a531d8c2637abd4be"


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canon(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    repo = Path.cwd().resolve()
    spec = json.loads(args.spec.read_text())
    preflight = json.loads(args.preflight.read_text())
    root = args.output_root.resolve()
    if sha_file(args.spec) != SPEC_SHA256 or preflight.get("preflightHash") != canon({key: value for key, value in preflight.items() if key != "preflightHash"}) or preflight.get("status") != "ACCEPTED":
        raise RuntimeError("D12.10-P1 formal admission mismatch")
    if root.exists() or root != (repo / spec["freshness"]["formalRoot"]).resolve():
        raise RuntimeError("refusing to reuse or redirect D12.10-P1 root")
    tool_hashes = {path: sha_file(repo / path) for path in spec["freshness"]["newToolPaths"]}
    if tool_hashes != preflight["toolHashes"]:
        raise RuntimeError("D12.10-P1 tools differ from admitted preflight")
    available = shutil.disk_usage(repo).free
    projected = spec["diskAdmission"]["projectedWriteBytes"]
    reserve = spec["diskAdmission"]["minimumReserveBytes"]
    if available - projected < reserve:
        raise RuntimeError("D12.10-P1 disk admission rejected")

    root.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    marker = {"experimentId": spec["experimentId"], "createdAtUtc": dt.datetime.now(dt.timezone.utc).isoformat(), "pid": os.getpid(), "specSha256": SPEC_SHA256}
    marker["markerHash"] = canon(marker)
    marker_path = root / ".formal-root-created.json"
    marker_path.write_text(json.dumps(marker, indent=2, sort_keys=True) + "\n")
    base_env = {"PATH": os.environ.get("PATH", ""), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "OCIO": str((repo / spec["runtime"]["ocio"]["uri"]).resolve())}
    children = []

    def child(role: str, cell: str, command: list[str], env: dict | None = None) -> None:
        safe = cell.replace("/", "_")
        log_dir = root / "logs" / role.lower()
        log_dir.mkdir(parents=True, exist_ok=True)
        stdout_path, stderr_path = log_dir / f"{safe}.stdout.log", log_dir / f"{safe}.stderr.log"
        tick = time.monotonic()
        process = subprocess.Popen(command, cwd=repo, env=env or base_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate()
        stdout_path.write_text(stdout)
        stderr_path.write_text(stderr)
        row = {"role": role, "cell": cell, "pid": process.pid, "exitCode": process.returncode, "elapsedSeconds": round(time.monotonic() - tick, 6), "argv": command, "stdout": {"uri": str(stdout_path), "sha256": sha_file(stdout_path)}, "stderr": {"uri": str(stderr_path), "sha256": sha_file(stderr_path)}}
        children.append(row)
        print(f"BFS_D1210_P1_CHILD role={role} cell={cell} pid={process.pid} exit={process.returncode}", flush=True)
        if process.returncode != 0:
            failure = {"schemaVersion": "bfs.blenderOwnerTokenPassProbeFailure.v0.1", "experimentId": spec["experimentId"], "failedChild": row, "completedChildren": children, "specSha256": SPEC_SHA256, "preflightSha256": sha_file(args.preflight), "formalRootMarkerSha256": sha_file(marker_path)}
            failure["failureHash"] = canon(failure)
            (root / "run.failure.json").write_text(json.dumps(failure, indent=2, sort_keys=True) + "\n")
            raise RuntimeError(f"D12.10-P1 child failed: {role} {cell}")

    source_tool = str(repo / "blender/render_b52_d12_10_p1_owner_token_source.py")
    for frame in spec["formalMatrix"]["frames"]:
        for display in spec["sceneContract"]["displayCells"]:
            display_id = display["id"]
            for repeat in spec["formalMatrix"]["repeats"]:
                cell = f"F{frame}/{display_id}/R{repeat}"
                source_dir = root / "sources" / f"frame-{frame}" / display_id / f"R{repeat}"
                runtime_dir = root / "runtime" / f"frame-{frame}" / display_id / f"R{repeat}"
                env = {**base_env}
                for name, suffix in (("TMPDIR", "tmp"), ("BLENDER_USER_CONFIG", "config"), ("BLENDER_USER_SCRIPTS", "scripts")):
                    target = runtime_dir / suffix
                    target.mkdir(parents=True, exist_ok=True)
                    env[name] = str(target)
                command = [spec["runtime"]["blender"]["executable"], *spec["runtime"]["blender"]["launchFlags"], "--python", source_tool, "--", "--spec", str(args.spec.resolve()), "--frame", str(frame), "--display-cell", display_id, "--repeat", str(repeat), "--output-exr", str(source_dir / "source.exr"), "--report", str(source_dir / "report.json")]
                child("SOURCE", cell, command, env)

    source_children = children.copy()
    execution_body = {
        "schemaVersion": "bfs.blenderOwnerTokenPassProbeExecution.v0.1",
        "experimentId": spec["experimentId"],
        "rootCreatedFresh": True,
        "formalRootMarker": {"uri": str(marker_path), "sha256": sha_file(marker_path), "markerHash": marker["markerHash"]},
        "spec": {"uri": str(args.spec.resolve()), "sha256": sha_file(args.spec)},
        "preflight": {"uri": str(args.preflight.resolve()), "sha256": sha_file(args.preflight), "preflightHash": preflight["preflightHash"]},
        "toolFreezeCommit": preflight["toolFreezeCommit"],
        "toolHashes": tool_hashes,
        "diskAdmission": {"availableBytes": available, "projectedWriteBytes": projected, "minimumReserveBytes": reserve, "freeAfterProjectedBytes": available - projected, "status": "ACCEPTED"},
        "operationCounts": {"sourceRenderProcesses": 8, "analyzerProcesses": 1, "auditProcesses": 1, "blenderRenderCalls": 8, "modelCalls": 0, "networkCalls": 0},
        "children": source_children,
    }
    execution = {**execution_body, "executionHash": canon(execution_body)}
    execution_path = root / "execution.json"
    execution_path.write_text(json.dumps(execution, indent=2, sort_keys=True, allow_nan=False) + "\n")
    python = spec["runtime"]["python"]["executable"]
    result_path, audit_path = root / "results.json", root / "audit.json"
    child("ANALYZER", "FORMAL", [python, str(repo / "scripts/analyze-b52-d12-10-p1-owner-token.py"), "--spec", str(args.spec.resolve()), "--root", str(root), "--execution", str(execution_path), "--output", str(result_path)])
    result = json.loads(result_path.read_text())
    child("AUDIT", "FORMAL", [python, str(repo / "scripts/audit-b52-d12-10-p1-owner-token.py"), "--spec", str(args.spec.resolve()), "--root", str(root), "--execution", str(execution_path), "--result", str(result_path), "--output", str(audit_path)])
    audit = json.loads(audit_path.read_text())
    pids = [row["pid"] for row in children]
    expected = spec["formalMatrix"]["expectedUniqueChildProcesses"]
    process_ok = len(children) == expected and len(set(pids)) == expected and all(row["exitCode"] == 0 for row in children)
    body = {
        "schemaVersion": "bfs.blenderOwnerTokenPassProbeReceipt.v0.1",
        "experimentId": spec["experimentId"],
        "executedAtUtc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "elapsedSeconds": round(time.monotonic() - started, 6),
        "spec": {"uri": str(args.spec.resolve()), "sha256": sha_file(args.spec)},
        "preflight": {"uri": str(args.preflight.resolve()), "sha256": sha_file(args.preflight), "preflightHash": preflight["preflightHash"]},
        "execution": {"uri": str(execution_path), "sha256": sha_file(execution_path), "executionHash": execution["executionHash"]},
        "result": {"uri": str(result_path), "sha256": sha_file(result_path), "evidenceHash": result["evidenceHash"], "verdict": result["verdict"], "passed": result["passed"]},
        "audit": {"uri": str(audit_path), "sha256": sha_file(audit_path), "auditHash": audit["auditHash"], "passed": audit["passed"]},
        "toolFreezeCommit": preflight["toolFreezeCommit"],
        "toolHashes": tool_hashes,
        "processes": {"expected": expected, "observed": len(children), "unique": len(set(pids)), "passed": process_ok, "children": children},
        "operationCounts": {"sourceRenderProcesses": 8, "analyzerProcesses": 1, "auditProcesses": 1, "blenderRenderCalls": 8, "modelCalls": 0, "networkCalls": 0},
    }
    receipt = {**body, "receiptHash": canon(body)}
    (root / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n")
    if not process_ok or not result["passed"] or not audit["passed"]:
        raise RuntimeError("D12.10-P1 formal totality failure")
    print(f"BFS_B52_D1210_P1_COMPLETE verdict={result['verdict']} checks={result['checkPassed']}/{result['checkTotal']} attacks={result['mutationAttackPassed']}/{result['mutationAttackTotal']} audit={audit['checkPassed']}/{audit['checkTotal']} receipt={receipt['receiptHash']}")


if __name__ == "__main__":
    main()
