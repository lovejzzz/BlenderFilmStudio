#!/usr/bin/env python3
"""Frozen-tool and zero-render admission for B52-D12.4."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


SPEC_SHA256 = "8df3c666e4409a243b1611131e5927b757fcd47453511b732fc26e579f526326"
TOOLS = (
    "scripts/analyze-b52-d12-4-zero-headroom.py",
    "scripts/audit-b52-d12-4-zero-headroom.py",
    "scripts/preflight-b52-d12-4-zero-headroom.py",
)
RESERVE_BYTES = 100 * 1024 * 1024 * 1024
PROJECTED_BYTES = 4 * 1024 * 1024


def sha256_bytes(value: bytes) -> str: return hashlib.sha256(value).hexdigest()
def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""): digest.update(chunk)
    return digest.hexdigest()
def canonical_hash(value: object) -> str: return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def run(command: list[str], root: Path) -> dict:
    completed = subprocess.run(command, cwd=root, capture_output=True, text=True)
    return {"command": command, "exitCode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr}


def imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text())
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import): found.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom): found.append(node.module or "")
    return found


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--experiment-root", type=Path, required=True)
    parser.add_argument("--formal-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.output.exists(): raise RuntimeError("refusing to overwrite D12.4 preflight")
    spec = json.loads(args.spec.read_text())
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True).stdout.strip()
    tool_hashes = {}
    frozen = True
    parsed = True
    for uri in TOOLS:
        path = root / uri
        payload = path.read_bytes()
        tool_hashes[uri] = sha256_bytes(payload)
        committed = subprocess.run(["git", "show", f"{head}:{uri}"], cwd=root, capture_output=True)
        frozen &= committed.returncode == 0 and committed.stdout == payload
        try: ast.parse(path.read_text())
        except SyntaxError: parsed = False
    analyzer_imports = imports(root / TOOLS[0])
    audit_imports = imports(root / TOOLS[1])
    independent = not any("analyze-b52-d12-4" in value for value in audit_imports)
    zero_render_surface = "bpy" not in analyzer_imports and "subprocess" not in analyzer_imports and "bpy" not in audit_imports
    available = shutil.disk_usage(root).free
    disk_ok = available - PROJECTED_BYTES >= RESERVE_BYTES

    with tempfile.TemporaryDirectory(prefix="bfs-d124-preflight-") as temporary:
        temporary_path = Path(temporary)
        result_path = temporary_path / "results.json"
        audit_path = temporary_path / "audit.json"
        localizer = run([spec["runtime"]["python"]["executable"], str(root / TOOLS[0]), "--spec", str(args.spec.resolve()), "--experiment-root", str(args.experiment_root.resolve()), "--output", str(result_path)], root)
        audit = run([spec["runtime"]["python"]["executable"], str(root / TOOLS[1]), "--spec", str(args.spec.resolve()), "--experiment-root", str(args.experiment_root.resolve()), "--result", str(result_path), "--output", str(audit_path)], root) if localizer["exitCode"] == 0 else {"command": [], "exitCode": -1, "stdout": "", "stderr": "localizer failed"}
        result_document = json.loads(result_path.read_text()) if result_path.is_file() else {}
        audit_document = json.loads(audit_path.read_text()) if audit_path.is_file() else {}
        smoke_ok = localizer["exitCode"] == 0 and audit["exitCode"] == 0 and result_document.get("passed") is True and audit_document.get("passed") is True and audit_document.get("basePassed") == 15 and audit_document.get("attackPassed") == 15
        smoke = {"localizer": localizer, "audit": audit, "resultHash": result_document.get("analysisHash"), "auditHash": audit_document.get("auditHash")}

    checks = [
        ("SPEC_IDENTITY", sha256_file(args.spec) == SPEC_SHA256),
        ("PYTHON_IDENTITY", sha256_file(Path(spec["runtime"]["python"]["executable"])) == spec["runtime"]["python"]["sha256"]),
        ("FROZEN_TOOL_IDENTITY", frozen),
        ("TOOL_PARSE", parsed),
        ("AUDIT_IMPORT_INDEPENDENCE", independent),
        ("ZERO_RENDER_SURFACE", zero_render_surface),
        ("FORMAL_ROOT_ABSENT", not args.formal_root.exists()),
        ("D12_3_ROOT_PRESENT", args.experiment_root.is_dir()),
        ("DISK_RESERVE", disk_ok),
        ("LOCALIZER_SMOKE", smoke_ok),
        ("AUDIT_BASE_TOTALITY", audit_document.get("basePassed") == audit_document.get("baseTotal") == 15),
        ("AUDIT_ATTACK_TOTALITY", audit_document.get("attackPassed") == audit_document.get("attackTotal") == 15),
    ]
    accepted = all(value for _, value in checks)
    body = {
        "schemaVersion": "bfs.blenderStaticZeroHeadroomLocalizationPreflight.v0.1",
        "experimentId": spec["experimentId"],
        "status": "ACCEPTED" if accepted else "REJECTED",
        "baseFailure": next((name for name, value in checks if not value), None),
        "toolFreezeCommit": head,
        "toolHashes": tool_hashes,
        "checks": [{"id": name, "passed": bool(value)} for name, value in checks],
        "passed": sum(value for _, value in checks),
        "total": len(checks),
        "diskAdmission": {"availableBytes": available, "projectedBytes": PROJECTED_BYTES, "reserveBytes": RESERVE_BYTES, "remainingBytes": available - PROJECTED_BYTES, "status": "ACCEPTED" if disk_ok else "REJECTED"},
        "smoke": smoke,
        "operationCounts": {"newBlenderRenders": 0, "modelCalls": 0, "networkCalls": 0},
    }
    result = {**body, "preflightHash": canonical_hash(body)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D124_PREFLIGHT status={result['status']} checks={result['passed']}/{result['total']} attacks={audit_document.get('attackPassed')}/{audit_document.get('attackTotal')}")


if __name__ == "__main__": main()
