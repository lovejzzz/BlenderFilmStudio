#!/usr/bin/env python3
"""RC2 build-admission cleanup correction: remove one regenerable Claude VM bundle."""

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path


TARGET = Path("/Users/mengyingli/Library/Application Support/Claude/vm_bundles/claudevm.bundle")


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


parser = argparse.ArgumentParser()
parser.add_argument("--repository-root", type=Path, required=True)
parser.add_argument("--prior-receipt", type=Path, required=True)
parser.add_argument("--output-root", type=Path, required=True)
parser.add_argument("--apply", action="store_true")
args = parser.parse_args()
if not args.apply:
    raise SystemExit("refusing cleanup without --apply")

repository = args.repository_root.resolve(strict=True)
prior = args.prior_receipt.resolve(strict=True)
output = args.output_root.resolve()
output.mkdir(parents=True, exist_ok=False)
if TARGET.is_symlink() or not TARGET.is_dir():
    raise SystemExit(f"target must be an existing real directory: {TARGET}")
processes = subprocess.run(["pgrep", "-ifl", "Claude"], text=True, capture_output=True)
if processes.returncode == 0 and processes.stdout.strip():
    raise SystemExit("Claude is running: " + processes.stdout.strip())

before = shutil.disk_usage(repository).free
allocated = int(subprocess.run(["du", "-sk", str(TARGET)], check=True, text=True, capture_output=True).stdout.split()[0]) * 1024
logical = sum(item.stat().st_size for item in TARGET.rglob("*") if item.is_file())
shutil.rmtree(TARGET)
preflight_process = subprocess.run(["node", "scripts/preflight-f0-source-host.mjs"], cwd=repository, text=True, capture_output=True)
preflight = json.loads(preflight_process.stdout)
after = shutil.disk_usage(repository).free
receipt = {
    "schemaVersion": "bfs.rc2BuildAdmissionCleanupC1.v0.1",
    "status": "PASS" if preflight["status"] == "F0_HOST_PREFLIGHT_READY" else "FAIL_CLEANUP_INSUFFICIENT",
    "crossBinding": {"priorReceipt": str(prior), "priorReceiptSha256": sha256_file(prior), "priorStatus": json.loads(prior.read_text(encoding="utf-8"))["status"]},
    "target": {"path": str(TARGET), "logicalBytes": logical, "allocatedBytes": allocated, "recovery": "redownload_or_regenerate", "absentAfter": not TARGET.exists()},
    "freeBytesBefore": before,
    "freeBytesAfter": after,
    "freedBytesObserved": after - before,
    "preflight": preflight,
    "preflightExitCode": preflight_process.returncode,
}
(output / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({"status": receipt["status"], "freeGiB": preflight["disk"]["freeGiB"], "freedBytesObserved": receipt["freedBytesObserved"]}, sort_keys=True))
raise SystemExit(0 if receipt["status"] == "PASS" else 2)
