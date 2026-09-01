#!/usr/bin/env python3
"""Remove an exact allowlist of regenerable caches for RC2 build admission."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path


TARGETS = [
    Path("/Users/mengyingli/Library/Application Support/bud-recorder/llm-runtime/models/qwen-qwen2-5-7b-instruct"),
    Path("/Users/mengyingli/.cache/huggingface"),
    Path("/Users/mengyingli/Library/Caches/electron"),
    Path("/Users/mengyingli/Library/Caches/camoufox"),
    Path("/Users/mengyingli/Library/Caches/com.apple.callintelligenced"),
    Path("/Users/mengyingli/Library/Caches/pnpm"),
    Path("/Users/mengyingli/Library/Caches/Homebrew"),
    Path("/Users/mengyingli/Library/Caches/com.apple.python"),
    Path("/Users/mengyingli/Library/Caches/node-gyp"),
    Path("/Users/mengyingli/Library/Caches/Unity"),
    Path("/Users/mengyingli/Library/Caches/com.unity3d.UnityEditor"),
    Path("/Users/mengyingli/.npm/_npx"),
    Path("/Users/mengyingli/.npm/_cacache"),
    Path("/Users/mengyingli/Library/Developer/CoreSimulator/Caches"),
    Path("/Users/mengyingli/Library/Developer/Xcode/DerivedData"),
    Path("/Users/mengyingli/Library/Application Support/Claude/Cache"),
    Path("/Users/mengyingli/Library/Application Support/Claude/vm_bundles/warm"),
]
DUPLICATE = TARGETS[0]
DUPLICATE_COPY = Path("/Users/mengyingli/Library/Application Support/BudRecorder/llm-runtime/models/qwen-qwen2-5-7b-instruct")


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def tree_bytes(path):
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def allocated_bytes(path):
    output = subprocess.run(["du", "-sk", str(path)], check=True, text=True, capture_output=True).stdout
    return int(output.split()[0]) * 1024


parser = argparse.ArgumentParser()
parser.add_argument("--repository-root", type=Path, required=True)
parser.add_argument("--output-root", type=Path, required=True)
parser.add_argument("--apply", action="store_true")
args = parser.parse_args()
if not args.apply:
    raise SystemExit("refusing cleanup without --apply")

repository = args.repository_root.resolve(strict=True)
output = args.output_root.resolve()
output.mkdir(parents=True, exist_ok=False)
receipt_path = output / "receipt.json"

for target in TARGETS:
    if target.is_symlink() or not target.is_dir():
        raise SystemExit(f"target must be an existing real directory: {target}")
    if target in (Path("/"), Path("/Users/mengyingli")):
        raise SystemExit(f"unsafe target: {target}")

processes = subprocess.run(["pgrep", "-ifl", "BudRecorder|bud-recorder|Claude"], text=True, capture_output=True)
if processes.returncode == 0 and processes.stdout.strip():
    raise SystemExit("a protected cache owner is running: " + processes.stdout.strip())

left = {item.relative_to(DUPLICATE).as_posix(): item for item in DUPLICATE.rglob("*") if item.is_file() and not item.name.endswith(".metadata")}
right = {item.relative_to(DUPLICATE_COPY).as_posix(): item for item in DUPLICATE_COPY.rglob("*") if item.is_file() and not item.name.endswith(".metadata")}
if set(left) != set(right):
    raise SystemExit("the old model's non-metadata file roster is not duplicated")
duplicate_bytes = 0
for name in sorted(left):
    if left[name].stat().st_size != right[name].stat().st_size or sha256_file(left[name]) != sha256_file(right[name]):
        raise SystemExit(f"the retained model copy differs: {name}")
    duplicate_bytes += left[name].stat().st_size

before_free = shutil.disk_usage(repository).free
rows = []
for target in TARGETS:
    rows.append({"path": str(target), "logicalBytes": tree_bytes(target), "allocatedBytes": allocated_bytes(target), "recovery": "redownload_or_regenerate"})
in_progress = {
    "schemaVersion": "bfs.rc2BuildAdmissionCleanup.v0.1",
    "status": "IN_PROGRESS",
    "targets": rows,
    "duplicateModelVerification": {"retainedCopy": str(DUPLICATE_COPY), "fileCount": len(left), "verifiedBytes": duplicate_bytes, "nonMetadataFilesSha256Exact": True},
    "freeBytesBefore": before_free,
}
receipt_path.write_text(json.dumps(in_progress, indent=2, sort_keys=True) + "\n", encoding="utf-8")

for target in TARGETS:
    shutil.rmtree(target)

preflight_process = subprocess.run(["node", "scripts/preflight-f0-source-host.mjs"], cwd=repository, text=True, capture_output=True)
preflight = json.loads(preflight_process.stdout)
after_free = shutil.disk_usage(repository).free
receipt = {
    **in_progress,
    "status": "PASS" if preflight["status"] == "F0_HOST_PREFLIGHT_READY" else "FAIL_CLEANUP_INSUFFICIENT",
    "freeBytesAfter": after_free,
    "freedBytesObserved": after_free - before_free,
    "allTargetsAbsent": all(not target.exists() for target in TARGETS),
    "preflight": preflight,
    "preflightExitCode": preflight_process.returncode,
}
receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({"status": receipt["status"], "freeGiB": preflight["disk"]["freeGiB"], "freedBytesObserved": receipt["freedBytesObserved"], "targetCount": len(TARGETS)}, sort_keys=True))
raise SystemExit(0 if receipt["status"] == "PASS" else 2)
