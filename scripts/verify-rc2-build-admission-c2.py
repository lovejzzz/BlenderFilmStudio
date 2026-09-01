#!/usr/bin/env python3
"""Bind the accepted F0 host preflight after RC2 cleanup attempts 01/02."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def sha256_file(path):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest


parser = argparse.ArgumentParser()
parser.add_argument("--repository-root", type=Path, required=True)
parser.add_argument("--prior-receipt", type=Path, action="append", required=True)
parser.add_argument("--output-root", type=Path, required=True)
args = parser.parse_args()

repository = args.repository_root.resolve(strict=True)
priors = [path.resolve(strict=True) for path in args.prior_receipt]
output = args.output_root.resolve()
output.mkdir(parents=True, exist_ok=False)
process = subprocess.run(["node", "scripts/preflight-f0-source-host.mjs"], cwd=repository, text=True, capture_output=True)
preflight = json.loads(process.stdout)
checks = {
    "statusAccepted": preflight["status"] == "F0_HOST_PREFLIGHT_ACCEPTED",
    "noFailures": preflight["failures"] == [],
    "freeMeetsRequired": preflight["disk"]["freeGiB"] >= preflight["disk"]["requiredFreeGiB"],
}
receipt = {
    "schemaVersion": "bfs.rc2BuildAdmissionCleanupC2.v0.1",
    "status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "preflight": preflight,
    "preflightExitCode": process.returncode,
    "crossBindings": [{"path": str(path), "sha256": sha256_file(path), "status": json.loads(path.read_text(encoding="utf-8"))["status"]} for path in priors],
    "mutationCount": 0,
}
(output / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({"status": receipt["status"], "freeGiB": preflight["disk"]["freeGiB"], "requiredFreeGiB": preflight["disk"]["requiredFreeGiB"], "failureCount": len(preflight["failures"])}, sort_keys=True))
raise SystemExit(0 if receipt["status"] == "PASS" else 2)
