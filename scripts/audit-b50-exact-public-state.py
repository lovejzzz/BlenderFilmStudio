#!/usr/bin/env python3
"""Scan exact Git HEAD objects and the exact static build against B50 private identities."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "experiments/focus-intent-human-review-v0-1/work"


def canonical(value): return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
def hash_object(value): return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def command(args): return subprocess.run(args, cwd=ROOT, check=True, capture_output=True).stdout


def main():
    registry = json.loads((WORK / "sealed/sensitive-registry.sealed.json").read_text(encoding="utf-8"))
    values = [item.encode("ascii") for item in registry["values"]]
    head = command(["git", "rev-parse", "HEAD"]).decode().strip()
    names = command(["git", "ls-tree", "-r", "-z", "--name-only", head]).decode().split("\0")
    records, matches = [], []
    for name in sorted(item for item in names if item):
        data = command(["git", "show", f"{head}:{name}"])
        records.append({"surface": "GIT_HEAD", "path": name, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
        for value in values:
            if value in data: matches.append({"surface": "GIT_HEAD", "path": name, "valuePrefix": value[:12].decode()})
    out = ROOT / "out"
    if not out.exists(): raise RuntimeError("static site build absent")
    for path in sorted((item for item in out.rglob("*") if item.is_file()), key=lambda item: str(item)):
        data = path.read_bytes(); name = str(path.relative_to(out)).replace(os.sep, "/")
        records.append({"surface": "STATIC_BUILD", "path": name, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
        for value in values:
            if value in data: matches.append({"surface": "STATIC_BUILD", "path": name, "valuePrefix": value[:12].decode()})
    body = {"schemaVersion": "bfs.focusIntentExactPublicStateAudit.v0.1", "gitHead": head, "surfaces": ["GIT_HEAD", "STATIC_BUILD"], "fileCount": len(records), "stateRootHash": hash_object(records), "sensitiveRegistryCommitment": registry["commitment"], "matchCount": len(matches), "matches": matches, "status": "PASS" if not matches else "FAIL", "humanResponses": 0, "nonClaim": "public-state isolation is not human evidence"}
    output = WORK / "evidence/exact-public-state.audit.json"
    output.write_text(json.dumps({**body, "auditHash": hash_object(body)}, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if matches: raise RuntimeError(f"B50 exact public-state leak: {matches}")
    print(f"BFS_B50_EXACT_PUBLIC_STATE_PASS head={head[:12]} files={len(records)} matches=0 human=0/18")


if __name__ == "__main__": main()
