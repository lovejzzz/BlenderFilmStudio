#!/usr/bin/env python3
"""Zero-formal-output frozen-tool admission for B52-D10."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


SPEC_SHA256 = "147338ae39b9c025a8f2a4921da55b15f8c16f339f34c711502dc3c94ca03566"
TOOLS = [
    "blender/render_b52_d10_pass_adapter_source.py",
    "scripts/adapt-b52-d10-multipart.py",
    "scripts/analyze-b52-d10-pass-adapter-holdout.py",
    "scripts/run-b52-d10-pass-adapter-holdout.py",
    "scripts/audit-b52-d10-pass-adapter-holdout.py",
    "scripts/preflight-b52-d10-pass-adapter-holdout.py",
    "tests/test_b52_d10_pass_adapter_contract.py",
]


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def git_blob(root: Path, commit: str, relative: str) -> bytes:
    result = subprocess.run(["git", "show", f"{commit}:{relative}"], cwd=root, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace"))
    return result.stdout


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


def main() -> None:
    args = arguments()
    root = Path.cwd().resolve()
    spec_path = args.spec.resolve()
    output = args.output.resolve()
    if output.exists() or output.parent.exists():
        raise RuntimeError("refusing to overwrite D10 preflight")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec_identity = sha256_file(spec_path) == SPEC_SHA256
    formal_root = root / spec["formalOutputRoot"]
    formal_absent = not formal_root.exists()
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, check=True).stdout.strip()

    tool_rows = []
    for relative in TOOLS:
        current = (root / relative).read_bytes()
        frozen = git_blob(root, commit, relative)
        tool_rows.append({"uri": relative, "currentSha256": sha256_bytes(current), "gitBlobSha256": sha256_bytes(frozen), "match": current == frozen})
    all_tools = len(tool_rows) == len(TOOLS) and all(item["match"] for item in tool_rows)

    parent_rows = []
    for name, value in spec["parents"].items():
        observed = sha256_file(root / value["uri"])
        parent_rows.append({"name": name, "uri": value["uri"], "expectedSha256": value["sha256"], "observedSha256": observed, "match": observed == value["sha256"]})
    parents_match = all(item["match"] for item in parent_rows)

    runtime_rows = []
    for name in ("blender", "python"):
        value = spec["runtime"][name]
        observed = sha256_file(Path(value["executable"]))
        runtime_rows.append({"name": name, "uri": value["executable"], "expectedSha256": value["sha256"], "observedSha256": observed, "match": observed == value["sha256"]})
    ocio = spec["runtime"]["ocio"]
    ocio_observed = sha256_file(root / ocio["uri"])
    runtime_rows.append({"name": "ocio", "uri": ocio["uri"], "expectedSha256": ocio["sha256"], "observedSha256": ocio_observed, "match": ocio_observed == ocio["sha256"]})
    runtime_match = all(item["match"] for item in runtime_rows) and oiio.VERSION_STRING == spec["runtime"]["python"]["openImageIO"] and np.__version__ == spec["runtime"]["python"]["numpy"] and sha256_file(Path(sys.executable)) == spec["runtime"]["python"]["sha256"]

    development = json.loads((root / "experiments/layer-depth-pass-adapter-development-v0-1/OBJECT_ASYMMETRIC_XY/source.report.json").read_text(encoding="utf-8"))
    development_ids = {11, 22, 33}
    formal_ids = {int(item["passIndex"]) for item in spec["scene"]["objects"]}
    freshness = bool(spec["sourceRender"]["resolution"] != development["render"]["resolution"] and spec["scene"]["camera"]["orthoScale"] != 8.0 and formal_ids.isdisjoint(development_ids) and spec["fixtures"][0]["moverByFrame"] != development["fixture"]["moverByFrame"])

    analyzer_path = root / "scripts/analyze-b52-d10-pass-adapter-holdout.py"
    imports = imported_modules(analyzer_path)
    oracle_import_ok = imports.isdisjoint({"bpy", "bpy_extras", "mathutils"}) and "projections" not in analyzer_path.read_text(encoding="utf-8")

    tests_argv = [spec["runtime"]["python"]["executable"], "tests/test_b52_d10_pass_adapter_contract.py"]
    tests = subprocess.run(tests_argv, cwd=root, text=True, capture_output=True, check=False)
    tests_ok = tests.returncode == 0 and "Ran 5 tests" in tests.stderr and "OK" in tests.stderr

    probe_code = "import bpy; vl=bpy.context.view_layer; print('BFS_D10_PREFLIGHT',bpy.app.version_string,bpy.app.build_hash.decode('ascii'),hasattr(vl,'use_pass_z'),hasattr(vl,'use_pass_vector'),hasattr(vl,'use_pass_object_index'),hasattr(vl,'pass_alpha_threshold'))"
    with tempfile.TemporaryDirectory(prefix="bfs-d10-preflight-config-") as config, tempfile.TemporaryDirectory(prefix="bfs-d10-preflight-scripts-") as scripts:
        environment = {key: os.environ[key] for key in spec["runtime"]["environmentAllowlist"] if key in os.environ}
        environment.update({"OCIO": str((root / ocio["uri"]).resolve()), "BLENDER_USER_CONFIG": config, "BLENDER_USER_SCRIPTS": scripts})
        probe = subprocess.run([spec["runtime"]["blender"]["executable"], *spec["runtime"]["blender"]["launchFlags"], "--python-expr", probe_code], cwd=root, env=environment, text=True, capture_output=True, check=False)
    probe_ok = probe.returncode == 0 and f"BFS_D10_PREFLIGHT {spec['runtime']['blender']['version']} {spec['runtime']['blender']['buildHash']} True True True True" in probe.stdout

    available = shutil.disk_usage(root).free
    projected_after = available - spec["projectedWriteBytes"]
    disk = {"status": "ACCEPTED" if projected_after >= spec["diskReserveBytes"] else "REJECTED", "availableBytes": available, "projectedWriteBytes": spec["projectedWriteBytes"], "projectedAvailableAfterBytes": projected_after, "reserveBytes": spec["diskReserveBytes"]}
    formal_absent_after = not formal_root.exists()
    accepted = all([spec_identity, formal_absent, formal_absent_after, all_tools, parents_match, runtime_match, freshness, oracle_import_ok, tests_ok, probe_ok, disk["status"] == "ACCEPTED"])
    body = {
        "schemaVersion": "bfs.blenderMultipartTemporalAdapterFrozenToolPreflight.v0.1",
        "experimentId": spec["experimentId"],
        "status": "ACCEPTED" if accepted else "REJECTED",
        "freezeCommit": commit,
        "spec": {"uri": str(spec_path), "sha256": sha256_file(spec_path), "identityMatch": spec_identity},
        "formalRoot": str(formal_root),
        "formalRootAbsent": formal_absent and formal_absent_after,
        "formalOperationCounts": {"childProcesses": 0, "blenderProcesses": 0, "adapterProcesses": 0, "renderCalls": 0, "cyclesRayRenders": 0, "formalMeasurements": 0},
        "frozenTools": tool_rows,
        "allFrozenToolsMatchGit": all_tools,
        "parents": parent_rows,
        "allParentsMatch": parents_match,
        "runtimes": runtime_rows,
        "allRuntimesMatch": runtime_match,
        "freshnessMatched": freshness,
        "analyticOracleImports": sorted(imports),
        "analyticOracleImportAuditPassed": oracle_import_ok,
        "contractTests": {"argv": tests_argv, "exitCode": tests.returncode, "stdout": tests.stdout, "stderr": tests.stderr, "passed": tests_ok},
        "realBlenderZeroRenderProbe": {"pidNotRecorded": True, "exitCode": probe.returncode, "stdout": probe.stdout, "stderr": probe.stderr, "renderCalls": 0, "cyclesRayRenders": 0, "passed": probe_ok},
        "diskAdmission": disk,
        "nonClaims": ["Preflight executes no formal fixture and creates no formal output.", "The Blender probe checks runtime/API presence only and performs zero renders.", "Preflight measurements cannot satisfy any D10 formal gate."],
    }
    result = {**body, "preflightHash": canonical_hash(body)}
    output.parent.mkdir(parents=True, exist_ok=False)
    output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(f"BFS_B52_D10_PREFLIGHT status={result['status']} tools={sum(item['match'] for item in tool_rows)}/{len(tool_rows)} tests={'PASS' if tests_ok else 'FAIL'} output={sha256_file(output)}")
    if not accepted:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
