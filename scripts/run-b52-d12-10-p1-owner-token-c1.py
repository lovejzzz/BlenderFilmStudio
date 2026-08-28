#!/usr/bin/env python3
"""Single-use correction runner for B52-D12.10-P1-C1."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path


SPEC_SHA256 = "5805af301077a8b3ae18892e3c4c2c5a2ad646a7e8b3cdddd762c39d22293a77"


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canon(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=check)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    repo = Path.cwd().resolve()
    spec = json.loads(args.spec.read_text())
    root = args.output_root.resolve()
    if sha_file(args.spec) != SPEC_SHA256 or root != (repo / spec["freshness"]["correctedOutputRoot"]).resolve() or root.exists():
        raise RuntimeError("P1-C1 runner spec/output freshness mismatch")
    parent_checks = {name: sha_file(repo / row["uri"]) == row["sha256"] for name, row in spec["parents"].items()}
    source_checks = {row["cell"]: sha_file(repo / row["reportUri"]) == row["reportSha256"] and sha_file(repo / row["exrUri"]) == row["exrSha256"] for row in spec["sourceManifest"]}
    tool_paths = spec["freshness"]["newToolPaths"]
    tool_hashes = {path: sha_file(repo / path) for path in tool_paths}
    freeze_commit = git(repo, "rev-parse", "HEAD").stdout.decode().strip()
    blob_checks = {}
    for path, digest in tool_hashes.items():
        observed = git(repo, "show", f"{freeze_commit}:{path}", check=False)
        blob_checks[path] = observed.returncode == 0 and sha_bytes(observed.stdout) == digest
    prereg_commit = git(repo, "log", "-1", "--format=%H", "--", str(args.spec.resolve().relative_to(repo))).stdout.decode().strip()
    prereg_absence = {path: git(repo, "cat-file", "-e", f"{prereg_commit}:{path}", check=False).returncode != 0 for path in tool_paths}
    if not all(parent_checks.values()) or not all(source_checks.values()) or not all(blob_checks.values()) or not all(prereg_absence.values()):
        raise RuntimeError("P1-C1 runner immutable identity admission rejected")
    p1_spec = json.loads((repo / spec["parents"]["p1Spec"]["uri"]).read_text())
    python = p1_spec["runtime"]["python"]["executable"]
    if sha_file(Path(python)) != p1_spec["runtime"]["python"]["sha256"]:
        raise RuntimeError("P1-C1 Python runtime mismatch")

    root.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    marker_body = {"experimentId": spec["experimentId"], "createdAtUtc": dt.datetime.now(dt.timezone.utc).isoformat(), "pid": os.getpid(), "specSha256": SPEC_SHA256, "preregistrationCommit": prereg_commit, "toolFreezeCommit": freeze_commit}
    marker = {**marker_body, "markerHash": canon(marker_body)}
    marker_path = root / ".correction-root-created.json"
    marker_path.write_text(json.dumps(marker, indent=2, sort_keys=True) + "\n")
    env = {"PATH": os.environ.get("PATH", ""), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "OCIO": str((repo / p1_spec["runtime"]["ocio"]["uri"]).resolve())}
    children = []

    def child(role: str, command: list[str]) -> None:
        log_dir = root / "logs" / role.lower()
        log_dir.mkdir(parents=True, exist_ok=True)
        stdout_path, stderr_path = log_dir / "stdout.log", log_dir / "stderr.log"
        tick = time.monotonic()
        process = subprocess.Popen(command, cwd=repo, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate()
        stdout_path.write_text(stdout)
        stderr_path.write_text(stderr)
        row = {"role": role, "pid": process.pid, "exitCode": process.returncode, "elapsedSeconds": round(time.monotonic() - tick, 6), "argv": command, "stdout": {"uri": str(stdout_path), "sha256": sha_file(stdout_path)}, "stderr": {"uri": str(stderr_path), "sha256": sha_file(stderr_path)}}
        children.append(row)
        print(f"BFS_D1210_P1_C1_CHILD role={role} pid={process.pid} exit={process.returncode}", flush=True)
        if process.returncode != 0:
            failure = {"schemaVersion": "bfs.blenderOwnerTokenPassProbeCorrectionFailure.v0.1", "experimentId": spec["experimentId"], "failedChild": row, "completedChildren": children, "specSha256": SPEC_SHA256, "markerSha256": sha_file(marker_path)}
            failure["failureHash"] = canon(failure)
            (root / "run.failure.json").write_text(json.dumps(failure, indent=2, sort_keys=True) + "\n")
            raise RuntimeError(f"P1-C1 child failed: {role}")

    result_path, audit_path = root / "results.json", root / "audit.json"
    child("ANALYZER", [python, str(repo / "scripts/analyze-b52-d12-10-p1-owner-token-c1.py"), "--spec", str(args.spec.resolve()), "--output-root", str(root), "--output", str(result_path)])
    result = json.loads(result_path.read_text())
    execution_body = {
        "schemaVersion": "bfs.blenderOwnerTokenPassProbeCorrectionExecution.v0.1",
        "experimentId": spec["experimentId"],
        "rootCreatedFresh": True,
        "marker": {"uri": str(marker_path), "sha256": sha_file(marker_path), "markerHash": marker["markerHash"]},
        "spec": {"uri": str(args.spec.resolve()), "sha256": sha_file(args.spec)},
        "preregistrationCommit": prereg_commit,
        "toolFreezeCommit": freeze_commit,
        "toolHashes": tool_hashes,
        "parentChecks": parent_checks,
        "sourceManifestChecks": source_checks,
        "children": children.copy(),
        "operationCounts": {"analyzerProcesses": 1, "auditProcesses": 1, "newBlenderProcesses": 0, "newBlenderRenderCalls": 0, "modelCalls": 0, "networkCalls": 0},
    }
    execution = {**execution_body, "executionHash": canon(execution_body)}
    execution_path = root / "execution.json"
    execution_path.write_text(json.dumps(execution, indent=2, sort_keys=True, allow_nan=False) + "\n")
    child("AUDIT", [python, str(repo / "scripts/audit-b52-d12-10-p1-owner-token-c1.py"), "--spec", str(args.spec.resolve()), "--output-root", str(root), "--execution", str(execution_path), "--result", str(result_path), "--output", str(audit_path)])
    audit = json.loads(audit_path.read_text())
    pids = [row["pid"] for row in children]
    process_ok = len(children) == 2 and len(set(pids)) == 2 and all(row["exitCode"] == 0 for row in children)
    body = {
        "schemaVersion": "bfs.blenderOwnerTokenPassProbeCorrectionReceipt.v0.1",
        "experimentId": spec["experimentId"],
        "executedAtUtc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "elapsedSeconds": round(time.monotonic() - started, 6),
        "spec": {"uri": str(args.spec.resolve()), "sha256": sha_file(args.spec)},
        "execution": {"uri": str(execution_path), "sha256": sha_file(execution_path), "executionHash": execution["executionHash"]},
        "result": {"uri": str(result_path), "sha256": sha_file(result_path), "evidenceHash": result["evidenceHash"], "verdict": result["verdict"], "passed": result["passed"]},
        "audit": {"uri": str(audit_path), "sha256": sha_file(audit_path), "auditHash": audit["auditHash"], "passed": audit["passed"]},
        "preregistrationCommit": prereg_commit,
        "toolFreezeCommit": freeze_commit,
        "toolHashes": tool_hashes,
        "processes": {"expected": 2, "observed": len(children), "unique": len(set(pids)), "passed": process_ok, "children": children},
        "operationCounts": {"newAnalyzerProcesses": 1, "newAuditProcesses": 1, "newBlenderProcesses": 0, "newBlenderRenderCalls": 0, "modelCalls": 0, "networkCalls": 0},
    }
    receipt = {**body, "receiptHash": canon(body)}
    (root / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n")
    if not process_ok or not result["passed"] or not audit["passed"]:
        raise RuntimeError("P1-C1 correction totality failure")
    print(f"BFS_B52_D1210_P1_C1_COMPLETE verdict={result['verdict']} checks={result['checkPassed']}/{result['checkTotal']} attacks={result['mutationAttackPassed']}/{result['mutationAttackTotal']} audit={audit['checkPassed']}/{audit['checkTotal']} receipt={receipt['receiptHash']}")


if __name__ == "__main__":
    main()
