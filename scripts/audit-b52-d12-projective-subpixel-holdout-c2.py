#!/usr/bin/env python3
"""C2 independent replay audit for the immutable negative B52-D12 result."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path


SPEC_SHA256 = "dd2e990d276e0ee5c2fee9d22cf42c7f84db2b6c1947b1219dceab06a76f66a2"
CORRECTION_SPEC_SHA256 = "e9a19e608de800121da0aec460bc514f6f62d51acd80dd56236adababa05cf44"
CORRECTION_PREREGISTRATION_COMMIT = "362620bf326f564d2b2b00d5d74d9170b54e819f"
PREFLIGHT_SHA256 = "09b193b4a97b45884bc381b13df5ed5983c2403bbbffdbcce90bca558b293f8c"
RECEIPT_SHA256 = "8c78b88ef512a5f7aa39554fced1067c12a5a0036c4c8231964b544da146ea4b"
RESULT_SHA256 = "a411948ec8854029d199786bbf0a81565bc91099e2f973a2311b7513c2d07d82"
FAILED_AUDIT_SHA256 = "f090b7667f7ea882cc45df694f0d1dd0e39a2ead3bc83cde268b7990a64f832d"
THIS_TOOL_URI = "scripts/audit-b52-d12-projective-subpixel-holdout-c2.py"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--spec", type=Path, required=True); parser.add_argument("--correction-spec", type=Path, required=True); parser.add_argument("--formal-root", type=Path, required=True); parser.add_argument("--preflight", type=Path, required=True); parser.add_argument("--output", type=Path, required=True); parser.add_argument("--freeze-commit", required=True); args = parser.parse_args()
    root = Path.cwd().resolve(); args.formal_root = args.formal_root.resolve(); spec = json.loads(args.spec.read_text()); correction = json.loads(args.correction_spec.read_text()); preflight = json.loads(args.preflight.read_text())
    result_path, receipt_path = args.formal_root / "results.json", args.formal_root / "run.receipt.json"; failed_audit_path = args.formal_root / "audit.json"
    frozen_tool = subprocess.run(["git", "show", f"{args.freeze_commit}:{THIS_TOOL_URI}"], cwd=root, capture_output=True, check=False).stdout
    working_tool = (root / THIS_TOOL_URI).read_bytes()
    if sha(args.spec) != SPEC_SHA256 or sha(args.correction_spec) != CORRECTION_SPEC_SHA256 or sha(args.preflight) != PREFLIGHT_SHA256 or sha(receipt_path) != RECEIPT_SHA256 or sha(result_path) != RESULT_SHA256 or sha(failed_audit_path) != FAILED_AUDIT_SHA256 or working_tool != frozen_tool or args.output.exists(): raise RuntimeError("B52-D12-C2 audit identity/input mismatch")
    result, receipt = json.loads(result_path.read_text()), json.loads(receipt_path.read_text())
    result_body = {key: value for key, value in result.items() if key != "resultHash"}; receipt_body = {key: value for key, value in receipt.items() if key != "receiptHash"}
    attacks = result.get("attacks", [])
    attack_totality = len(attacks) == len(spec["attacks"]) == 57 and [row.get("name") for row in attacks] == spec["attacks"] and all(type(row.get("passed")) is bool and isinstance(row.get("method"), str) and bool(row["method"]) for row in attacks) and result.get("attacksPassed") == sum(row["passed"] for row in attacks)
    checks = {
        "specIdentity": sha(args.spec) == SPEC_SHA256,
        "preflightIdentity": preflight.get("status") == "ACCEPTED" and preflight.get("spec", {}).get("sha256") == SPEC_SHA256 and preflight.get("allFrozenToolsMatchGit") is True,
        "resultIdentity": result.get("resultHash") == canonical_hash(result_body),
        "receiptIdentity": receipt.get("receiptHash") == canonical_hash(receipt_body) and result.get("receipt", {}).get("sha256") == sha(receipt_path),
        "processIdentity": result.get("operationCounts", {}).get("formalChildProcesses") == 65 and result.get("operationCounts", {}).get("uniqueFormalChildPids") == 65,
        "attackTotality": attack_totality,
        "diagnosticIdentity": len(result.get("diagnostics", [])) == 24 and all(sha(Path(row["pngUri"])) == row["pngSha256"] and sha(Path(row["sidecarUri"])) == row["sidecarSha256"] for row in result.get("diagnostics", [])),
        "toolIdentity": all((root / row["uri"]).is_file() and sha(root / row["uri"]) == row["workingSha256"] for row in preflight.get("tools", [])) and working_tool == frozen_tool,
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
    body = {"schemaVersion": "bfs.blenderProjectiveSubpixelAuditC2.v0.1", "experimentId": spec["experimentId"], "correction": {"id": correction["correctionId"], "preregistrationCommit": CORRECTION_PREREGISTRATION_COMMIT, "spec": {"uri": str(args.correction_spec), "sha256": CORRECTION_SPEC_SHA256}, "toolFreezeCommit": args.freeze_commit, "failedAudit": {"uri": str(failed_audit_path), "sha256": FAILED_AUDIT_SHA256}}, "status": status, "pid": os.getpid(), "inputs": {"spec": {"uri": str(args.spec), "sha256": sha(args.spec)}, "preflight": {"uri": str(args.preflight), "sha256": sha(args.preflight)}, "receipt": {"uri": str(receipt_path), "sha256": sha(receipt_path)}, "result": {"uri": str(result_path), "sha256": sha(result_path)}}, "checks": checks, "replay": {"exitCode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr, "analysisPid": replay.get("analysisPid"), "verdict": replay.get("verdict"), "baseFailure": replay.get("baseFailure")}, "verdict": result.get("verdict"), "baseFailure": result.get("baseFailure"), "operationCounts": {"auditProcesses": 1, "replayAnalyzerProcesses": 1, "blenderProcesses": 0, "renders": 0, "modelCalls": 0, "networkCalls": 0}}
    audit = {**body, "auditHash": canonical_hash(body)}; args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(audit, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D12_C2_AUDIT_{status} verdict={audit['verdict']} baseFailure={audit['baseFailure']}")
    if status != "PASS": raise SystemExit(1)


if __name__ == "__main__": main()
