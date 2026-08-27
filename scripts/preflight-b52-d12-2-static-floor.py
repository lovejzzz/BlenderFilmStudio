#!/usr/bin/env python3
"""Frozen-tool, synthetic-contract, Blender API and disk preflight for B52-D12.2."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np


SPEC_SHA256 = "fa63daa0c3b7b3f080a488aa0fc84996fd52cd731efce94ebe28bbc81b55d9d3"
PREREGISTRATION_COMMIT = "eee1b8404c1e56d4d39c65dabd4bef2727e968a0"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def run(argv: list[str], env: dict[str, str], cwd: Path) -> dict:
    completed = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True)
    return {"argv": argv, "exitCode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--tool-freeze-commit", required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    repo = Path.cwd().resolve()
    spec_path = args.spec.resolve()
    spec = json.loads(spec_path.read_text())
    formal_root = (repo / spec["diskAdmission"]["formalRoot"]).resolve()
    output_root = args.output_root.resolve()
    if output_root.exists():
        raise RuntimeError("refusing to overwrite D12.2 preflight")
    if formal_root.exists():
        raise RuntimeError("D12.2 formal root must remain absent during preflight")
    output_root.mkdir(parents=True, exist_ok=False)
    tests = []

    def check(name: str, passed: bool, detail: object = None) -> None:
        tests.append({"id": name, "passed": bool(passed), "detail": detail})

    check("SPEC_IDENTITY", sha256_file(spec_path) == SPEC_SHA256, sha256_file(spec_path))
    prereg = subprocess.run(["git", "cat-file", "-e", f"{PREREGISTRATION_COMMIT}^{{commit}}"], cwd=repo).returncode == 0
    check("PREREGISTRATION_COMMIT", prereg, PREREGISTRATION_COMMIT)
    tool_hashes, git_blob_hashes, tools_match = {}, {}, True
    for relative in spec["formalToolPaths"]:
        working = (repo / relative).read_bytes()
        frozen = subprocess.run(["git", "show", f"{args.tool_freeze_commit}:{relative}"], cwd=repo, capture_output=True, check=False)
        tool_hashes[relative] = sha256_bytes(working)
        git_blob_hashes[relative] = sha256_bytes(frozen.stdout) if frozen.returncode == 0 else None
        tools_match = tools_match and frozen.returncode == 0 and working == frozen.stdout
    check("FROZEN_TOOL_IDENTITY", tools_match, {"working": tool_hashes, "git": git_blob_hashes})
    check("RUNTIME_BLENDER", sha256_file(Path(spec["runtime"]["blender"]["executable"])) == spec["runtime"]["blender"]["sha256"])
    check("RUNTIME_PYTHON", sha256_file(Path(spec["runtime"]["python"]["executable"])) == spec["runtime"]["python"]["sha256"])
    check("RUNTIME_NODE", sha256_file(Path(spec["runtime"]["node"]["executable"])) == spec["runtime"]["node"]["sha256"])
    check("RUNTIME_OCIO", sha256_file(repo / spec["runtime"]["ocio"]["uri"]) == spec["runtime"]["ocio"]["sha256"])

    syntax = []
    for relative in spec["formalToolPaths"]:
        path = repo / relative
        try:
            if path.suffix == ".py":
                ast.parse(path.read_text())
            elif path.suffix == ".mjs":
                completed = subprocess.run([spec["runtime"]["node"]["executable"], "--check", str(path)], capture_output=True, text=True)
                if completed.returncode != 0:
                    raise RuntimeError(completed.stderr)
            syntax.append({"uri": relative, "passed": True})
        except Exception as error:
            syntax.append({"uri": relative, "passed": False, "error": str(error)})
    check("TOOL_SYNTAX", all(row["passed"] for row in syntax), syntax)

    analyzer_tree = ast.parse((repo / "scripts/analyze-b52-d12-2-static-floor.py").read_text())
    imported = []
    for node in ast.walk(analyzer_tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    check("ANALYZER_IMPORT_INDEPENDENCE", all(not name.startswith(("scripts", "blender", "importlib")) for name in imported), imported)

    env = {"PATH": os.environ.get("PATH", ""), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "OCIO": str((repo / spec["runtime"]["ocio"]["uri"]).resolve())}
    fixture = spec["fixtures"][0]
    width, height = fixture["resolution"]
    synthetic = output_root / "synthetic"
    arrays_root = synthetic / "adapter-arrays"
    arrays_root.mkdir(parents=True)
    previous = np.zeros((height, width, 4), dtype="<f4")
    for y in range(height):
        for x in range(width):
            previous[y, x] = (x / width, y / height, (x + y) / (width + height), 1.0)
    current = previous.copy()
    owner = np.full((height, width), fixture["passIndex"], dtype="<f4")
    vector = np.zeros((height, width, 2), dtype="<f4")
    vector[..., 0] = np.float32(1.0 / 65536.0)
    payloads = {
        "previousRgba": ("previous.rgba32", previous), "currentRgba": ("current.rgba32", current),
        "previousOwner": ("previous-owner.f32", owner), "currentOwner": ("current-owner.f32", owner), "vector": ("vector.xy32", vector),
    }
    records = {}
    for name, (filename, array) in payloads.items():
        payload = np.ascontiguousarray(array, dtype="<f4").tobytes()
        target = arrays_root / filename
        target.write_bytes(payload)
        records[name] = {"uri": str(target), "sha256": sha256_bytes(payload), "bytes": len(payload)}
    adapter_body = {"schemaVersion": "synthetic", "fixtureId": fixture["id"], "repeat": 1, "arrays": records}
    adapter_report = {**adapter_body, "reportHash": canonical_hash(adapter_body)}
    adapter_path = synthetic / "adapter-report.json"
    adapter_path.write_text(json.dumps(adapter_report, indent=2, sort_keys=True) + "\n")
    py_result = run([
        spec["runtime"]["python"]["executable"], str(repo / "scripts/reconstruct-b52-d12-2-static-floor.py"),
        "--spec", str(spec_path), "--fixture", fixture["id"], "--repeat", "1", "--input-dir", str(arrays_root),
        "--adapter-report", str(adapter_path), "--output-dir", str(synthetic / "python" / "arrays"), "--report", str(synthetic / "python" / "report.json"),
    ], env, repo)
    node_result = run([
        spec["runtime"]["node"]["executable"], str(repo / "scripts/reconstruct-b52-d12-2-static-floor.mjs"),
        "--spec", str(spec_path), "--fixture", fixture["id"], "--repeat", "1", "--input-dir", str(arrays_root),
        "--adapter-report", str(adapter_path), "--output-dir", str(synthetic / "node" / "arrays"), "--report", str(synthetic / "node" / "report.json"),
    ], env, repo)
    synthetic_equal = py_result["exitCode"] == 0 and node_result["exitCode"] == 0
    if synthetic_equal:
        synthetic_equal = (synthetic / "python/arrays/reconstructed.rgba32").read_bytes() == (synthetic / "node/arrays/reconstructed.rgba32").read_bytes()
        synthetic_equal = synthetic_equal and (synthetic / "python/arrays/valid.u8").read_bytes() == (synthetic / "node/arrays/valid.u8").read_bytes()
    check("SYNTHETIC_DUAL_CONSUMER", synthetic_equal, {"python": py_result, "node": node_result})

    probe_root = output_root / "blender-probe"
    probe_env = {**env, "TMPDIR": str((probe_root / "tmp").resolve()), "BLENDER_USER_CONFIG": str((probe_root / "config").resolve()), "BLENDER_USER_SCRIPTS": str((probe_root / "scripts").resolve())}
    for key in ("TMPDIR", "BLENDER_USER_CONFIG", "BLENDER_USER_SCRIPTS"):
        Path(probe_env[key]).mkdir(parents=True, exist_ok=True)
    probe = run([
        spec["runtime"]["blender"]["executable"], *spec["runtime"]["blender"]["launchFlags"],
        "--python", str(repo / "blender/render_b52_d12_2_static_floor_source.py"), "--",
        "--spec", str(spec_path), "--fixture", fixture["id"], "--frame", "1", "--repeat", "1",
        "--report", str(probe_root / "report.json"), "--probe-only",
    ], probe_env, repo)
    probe_ok = probe["exitCode"] == 0 and (probe_root / "report.json").is_file()
    if probe_ok:
        probe_report = json.loads((probe_root / "report.json").read_text())
        probe_ok = probe_report.get("operationCounts", {}).get("blenderRenderCalls") == 0 and probe_report.get("output") is None
    check("REAL_BLENDER_ZERO_RENDER_PROBE", probe_ok, probe)

    available = shutil.disk_usage(repo).free
    projected = spec["diskAdmission"]["projectedWriteBytes"]
    reserve = spec["diskAdmission"]["minimumReserveBytes"]
    disk = {"availableBytes": available, "projectedWriteBytes": projected, "minimumReserveBytes": reserve, "freeAfterProjectedBytes": available - projected, "status": "ACCEPTED" if available - projected >= reserve else "REJECTED"}
    check("DISK_ADMISSION", disk["status"] == "ACCEPTED", disk)
    check("FORMAL_ROOT_REMAINS_ABSENT", not formal_root.exists(), str(formal_root))
    status = "ACCEPTED" if all(row["passed"] for row in tests) else "REJECTED"
    body = {
        "schemaVersion": "bfs.blenderStaticVectorFloorPreflight.v0.1", "experimentId": spec["experimentId"],
        "preregistrationCommit": PREREGISTRATION_COMMIT, "toolFreezeCommit": args.tool_freeze_commit,
        "specSha256": sha256_file(spec_path), "toolHashes": tool_hashes, "gitBlobHashes": git_blob_hashes,
        "diskAdmission": disk, "tests": tests, "passedTests": sum(row["passed"] for row in tests), "totalTests": len(tests),
        "status": status, "formalOperations": {"blenderRenders": 0, "adapters": 0, "consumers": 0, "envelopeEncoders": 0, "analyzers": 0},
    }
    receipt = {**body, "preflightHash": canonical_hash(body)}
    target = output_root / "frozen-tool-preflight.json"
    target.write_text(json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D122_PREFLIGHT_{status} tests={receipt['passedTests']}/{receipt['totalTests']} disk={disk['freeAfterProjectedBytes'] - reserve}")
    if status != "ACCEPTED":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
