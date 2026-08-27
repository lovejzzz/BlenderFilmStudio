#!/usr/bin/env python3
"""Independent replay audit for immutable B52-D12 formal evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path


SPEC_SHA256 = "dd2e990d276e0ee5c2fee9d22cf42c7f84db2b6c1947b1219dceab06a76f66a2"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--spec", type=Path, required=True); parser.add_argument("--formal-root", type=Path, required=True); parser.add_argument("--preflight", type=Path, required=True); parser.add_argument("--output", type=Path, required=True); args = parser.parse_args()
    root = Path.cwd().resolve(); spec = json.loads(args.spec.read_text()); preflight = json.loads(args.preflight.read_text())
    result_path, receipt_path = args.formal_root / "results.json", args.formal_root / "run.receipt.json"
    if sha(args.spec) != SPEC_SHA256 or args.output.exists() or not result_path.is_file() or not receipt_path.is_file(): raise RuntimeError("B52-D12 audit identity/input mismatch")
    result, receipt = json.loads(result_path.read_text()), json.loads(receipt_path.read_text())
    result_body = {key: value for key, value in result.items() if key != "resultHash"}; receipt_body = {key: value for key, value in receipt.items() if key != "receiptHash"}
    checks = {
        "specIdentity": sha(args.spec) == SPEC_SHA256,
        "preflightIdentity": preflight.get("status") == "ACCEPTED" and preflight.get("spec", {}).get("sha256") == SPEC_SHA256 and preflight.get("allFrozenToolsMatchGit") is True,
        "resultIdentity": result.get("resultHash") == canonical_hash(result_body),
        "receiptIdentity": receipt.get("receiptHash") == canonical_hash(receipt_body) and result.get("receipt", {}).get("sha256") == sha(receipt_path),
        "processIdentity": result.get("operationCounts", {}).get("formalChildProcesses") == 65 and result.get("operationCounts", {}).get("uniqueFormalChildPids") == 65,
        "attackTotality": len(result.get("attacks", [])) == len(spec["attacks"]) == 57 and result.get("attacksPassed") == 57 and all(row.get("passed") is True for row in result.get("attacks", [])),
        "diagnosticIdentity": len(result.get("diagnostics", [])) == 24 and all(sha(Path(row["pngUri"])) == row["pngSha256"] and sha(Path(row["sidecarUri"])) == row["sidecarSha256"] for row in result.get("diagnostics", [])),
        "toolIdentity": all((root / row["uri"]).is_file() and sha(root / row["uri"]) == row["workingSha256"] for row in preflight.get("tools", [])),
    }
    analyzer = root / "scripts/analyze-b52-d12-projective-subpixel-holdout.py"
    environment = {key: os.environ[key] for key in spec["runtime"]["environmentAllowlist"] if key in os.environ}; environment["OCIO"] = str((root / spec["runtime"]["ocio"]["uri"]).resolve())
    with tempfile.TemporaryDirectory(prefix="bfs-d12-audit-") as temp_text:
        replay_path = Path(temp_text) / "replay-results.json"
        argv = [spec["runtime"]["python"]["executable"], str(analyzer), "--spec", str(args.spec), "--formal-root", str(args.formal_root), "--receipt", str(receipt_path), "--preflight", str(args.preflight), "--output", str(replay_path), "--diagnostics-mode", "verify"]
        completed = subprocess.run(argv, cwd=root, env=environment, text=True, capture_output=True, check=False)
        replay = json.loads(replay_path.read_text()) if replay_path.is_file() else {}
    comparable = ("evidence", "measurements", "diagnostics", "operationCounts", "attacks", "attacksPassed", "evidenceCoreHash", "verdict", "baseFailure", "nonClaims")
    checks["evidenceReplay"] = completed.returncode == 0 and all(replay.get(key) == result.get(key) for key in comparable)
    evidence_all = all(result.get("evidence", {}).values())
    expected_verdict = spec["decision"]["supportedVerdict"] if evidence_all else spec["decision"]["unsupportedVerdict"]
    expected_failure = next((label for label in spec["baseFailureOrder"] if not result.get("evidence", {}).get(label)), None)
    checks["verdictConsistency"] = result.get("verdict") == expected_verdict and result.get("baseFailure") == expected_failure
    status = "PASS" if all(checks.values()) else "FAIL"
    body = {"schemaVersion": "bfs.blenderProjectiveSubpixelAudit.v0.1", "experimentId": spec["experimentId"], "status": status, "pid": os.getpid(), "inputs": {"spec": {"uri": str(args.spec), "sha256": sha(args.spec)}, "preflight": {"uri": str(args.preflight), "sha256": sha(args.preflight)}, "receipt": {"uri": str(receipt_path), "sha256": sha(receipt_path)}, "result": {"uri": str(result_path), "sha256": sha(result_path)}}, "checks": checks, "replay": {"exitCode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr, "analysisPid": replay.get("analysisPid"), "verdict": replay.get("verdict"), "baseFailure": replay.get("baseFailure")}, "verdict": result.get("verdict"), "baseFailure": result.get("baseFailure"), "operationCounts": {"auditProcesses": 1, "replayAnalyzerProcesses": 1, "blenderProcesses": 0, "renders": 0, "modelCalls": 0, "networkCalls": 0}}
    audit = {**body, "auditHash": canonical_hash(body)}; args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(audit, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D12_AUDIT_{status} verdict={audit['verdict']} baseFailure={audit['baseFailure']}")
    if status != "PASS": raise SystemExit(1)


if __name__ == "__main__": main()
