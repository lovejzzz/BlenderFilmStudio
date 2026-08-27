#!/usr/bin/env python3
"""Zero-formal-output identity, API, contract and disk admission for B52-D12."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


SPEC_SHA256 = "dd2e990d276e0ee5c2fee9d22cf42c7f84db2b6c1947b1219dceab06a76f66a2"


def sha_bytes(value: bytes) -> str: return hashlib.sha256(value).hexdigest()
def sha(path: Path) -> str: return sha_bytes(path.read_bytes())
def canonical_hash(value: object) -> str: return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def run(argv, root, env=None): return subprocess.run(argv, cwd=root, env=env, text=True, capture_output=True, check=False)


def write_probe_exr(path: Path, width: int, height: int) -> None:
    pixels = np.zeros((height, width, 4), dtype=np.float32); pixels[..., 0] = np.linspace(0.0, 1.0, width, dtype=np.float32); pixels[..., 1] = 0.25; pixels[..., 2] = 0.75; pixels[..., 3] = 1.0
    output = oiio.ImageOutput.create(str(path)); spec = oiio.ImageSpec(width, height, 4, oiio.FLOAT); spec.channelnames = ("R", "G", "B", "A"); spec.attribute("oiio:ColorSpace", "Raw"); spec.attribute("compression", "zip")
    if output is None or not output.open(str(path), spec) or not output.write_image(pixels): raise RuntimeError(oiio.geterror() or "D12 preflight EXR write failed")
    output.close()


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--spec", type=Path, required=True); parser.add_argument("--output", type=Path, required=True); parser.add_argument("--freeze-commit", required=True); args = parser.parse_args()
    root = Path.cwd().resolve(); spec_path = args.spec.resolve(); spec = json.loads(spec_path.read_text())
    if sha(spec_path) != SPEC_SHA256 or args.output.exists() or args.output.parent.exists(): raise RuntimeError("B52-D12 preflight identity/output mismatch")
    formal_root = root / spec["formalOutputRoot"]
    formal_absent_before = not formal_root.exists()
    parent_rows = []
    for name, row in spec["parents"].items():
        if not isinstance(row, dict) or "uri" not in row or "sha256" not in row: continue
        path = root / row["uri"]; parent_rows.append({"name": name, "uri": row["uri"], "expectedSha256": row["sha256"], "actualSha256": sha(path) if path.is_file() else None, "match": path.is_file() and sha(path) == row["sha256"]})
    parents_match = all(row["match"] for row in parent_rows)
    runtime_rows = []
    for name in ("blender", "python", "node"):
        row = spec["runtime"][name]; path = Path(row["executable"]); runtime_rows.append({"name": name, "uri": str(path), "expectedSha256": row["sha256"], "actualSha256": sha(path), "match": sha(path) == row["sha256"]})
    ocio = root / spec["runtime"]["ocio"]["uri"]; runtime_rows.append({"name": "ocio", "uri": str(ocio), "expectedSha256": spec["runtime"]["ocio"]["sha256"], "actualSha256": sha(ocio), "match": sha(ocio) == spec["runtime"]["ocio"]["sha256"]})
    runtime_match = all(row["match"] for row in runtime_rows)
    tool_rows = []
    for relative in spec["formalToolPaths"]:
        path = root / relative; git = run(["git", "show", f"{args.freeze_commit}:{relative}"], root)
        git_bytes = git.stdout.encode() if git.returncode == 0 else b""; working_bytes = path.read_bytes() if path.is_file() else b""
        tool_rows.append({"uri": relative, "workingSha256": sha_bytes(working_bytes) if working_bytes else None, "gitBlobSha256": sha_bytes(git_bytes) if git_bytes else None, "match": bool(working_bytes) and git.returncode == 0 and working_bytes == git_bytes})
    tools_match = all(row["match"] for row in tool_rows)
    tests = run([spec["runtime"]["python"]["executable"], "-m", "unittest", "-v", "tests/test_b52_d12_projective_subpixel_contract.py"], root)
    contract_tests = {"passed": tests.returncode == 0, "exitCode": tests.returncode, "stdout": tests.stdout, "stderr": tests.stderr, "testCount": 11}
    probe_environment = {key: os.environ[key] for key in spec["runtime"]["environmentAllowlist"] if key in os.environ}; probe_environment["OCIO"] = str(ocio.resolve())
    with tempfile.TemporaryDirectory(prefix="bfs-d12-preflight-") as temp_text:
        temp = Path(temp_text); source_report = temp / "source-probe.json"
        source_argv = [spec["runtime"]["blender"]["executable"], *spec["runtime"]["blender"]["launchFlags"], "--python", str(root / "blender/render_b52_d12_projective_source.py"), "--", "--spec", str(spec_path), "--fixture", spec["fixtures"][3]["id"], "--frame", "1", "--repeat", "1", "--report", str(source_report), "--probe-only"]
        with tempfile.TemporaryDirectory(prefix="bfs-d12-config-") as config, tempfile.TemporaryDirectory(prefix="bfs-d12-scripts-") as scripts:
            env = {**probe_environment, "BLENDER_USER_CONFIG": config, "BLENDER_USER_SCRIPTS": scripts}; source_completed = run(source_argv, root, env)
        source_payload = json.loads(source_report.read_text()) if source_report.is_file() else {}
        source_probe = {"passed": source_completed.returncode == 0 and source_payload.get("probeOnly") is True and source_payload.get("operationCounts", {}).get("cyclesRayRenders") == 0 and source_payload.get("passState", {}).get("Vector") is True, "exitCode": source_completed.returncode, "stdout": source_completed.stdout, "stderr": source_completed.stderr, "report": source_payload}
        probe_exr = temp / "probe.exr"; write_probe_exr(probe_exr, *spec["scene"]["resolution"]); bridge_report = temp / "bridge-probe.json"
        bridge_argv = [spec["runtime"]["blender"]["executable"], *spec["runtime"]["blender"]["launchFlags"], "--python", str(root / "blender/render_b52_d12_reconstruction_passthrough.py"), "--", "--spec", str(spec_path), "--fixture", spec["fixtures"][3]["id"], "--source-repeat", "1", "--bridge-repeat", "1", "--input", str(probe_exr), "--report", str(bridge_report), "--probe-only"]
        with tempfile.TemporaryDirectory(prefix="bfs-d12-config-") as config, tempfile.TemporaryDirectory(prefix="bfs-d12-scripts-") as scripts:
            env = {**probe_environment, "BLENDER_USER_CONFIG": config, "BLENDER_USER_SCRIPTS": scripts}; bridge_completed = run(bridge_argv, root, env)
        bridge_payload = json.loads(bridge_report.read_text()) if bridge_report.is_file() else {}
        bridge_probe = {"passed": bridge_completed.returncode == 0 and bridge_payload.get("graph", {}).get("match") is True and bridge_payload.get("rna", {}).get("match") is True and bridge_payload.get("operationCounts", {}).get("bridgeCompositorRenders") == 0, "exitCode": bridge_completed.returncode, "stdout": bridge_completed.stdout, "stderr": bridge_completed.stderr, "report": bridge_payload}
    analyzer_text = (root / "scripts/analyze-b52-d12-projective-subpixel-holdout.py").read_text()
    analyzer_independent = all(token not in analyzer_text for token in ("import bpy", "import bpy_extras", "import mathutils", "import reconstruct_b52_d12", "importlib"))
    available = shutil.disk_usage(root).free; projected_after = available - spec["projectedWriteBytes"]
    disk = {"availableBytes": available, "projectedWriteBytes": spec["projectedWriteBytes"], "projectedAvailableAfterBytes": projected_after, "reserveBytes": spec["diskReserveBytes"], "accepted": projected_after >= spec["diskReserveBytes"]}
    freshness = {"formalRootAbsent": formal_absent_before and not formal_root.exists(), "developmentResolutionDiffers": spec["freshness"]["formalResolution"] != spec["freshness"]["excludedDevelopmentResolution"], "developmentLensDiffers": spec["freshness"]["formalLensMm"] != spec["freshness"]["excludedLensMm"], "formalOperationCounts": {"formalRenders": 0, "formalMeasurements": 0}}
    freshness_matched = all((freshness["formalRootAbsent"], freshness["developmentResolutionDiffers"], freshness["developmentLensDiffers"]))
    accepted = parents_match and runtime_match and tools_match and contract_tests["passed"] and source_probe["passed"] and bridge_probe["passed"] and analyzer_independent and freshness_matched and disk["accepted"]
    body = {"schemaVersion": "bfs.blenderProjectiveSubpixelFrozenToolPreflight.v0.1", "experimentId": spec["experimentId"], "status": "ACCEPTED" if accepted else "REJECTED", "freezeCommit": args.freeze_commit, "spec": {"uri": str(args.spec), "sha256": SPEC_SHA256}, "parents": parent_rows, "parentsMatch": parents_match, "runtimes": runtime_rows, "runtimeMatch": runtime_match, "tools": tool_rows, "allFrozenToolsMatchGit": tools_match, "contractTests": contract_tests, "sourceApiProbe": source_probe, "bridgeApiProbe": bridge_probe, "analyzerIndependent": analyzer_independent, "freshness": freshness, "freshnessMatched": freshness_matched, "formalRootAbsent": freshness["formalRootAbsent"], "diskAdmission": disk, "operationCounts": {"formalChildProcesses": 0, "formalRenders": 0, "formalMeasurements": 0, "preflightBlenderProcesses": 2, "preflightBlenderRenders": 0, "modelCalls": 0, "networkCalls": 0}}
    result = {**body, "preflightHash": canonical_hash(body)}; args.output.parent.mkdir(parents=True, exist_ok=False); args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D12_PREFLIGHT status={result['status']} tools={sum(row['match'] for row in tool_rows)}/{len(tool_rows)} tests={contract_tests['passed']} disk={disk['accepted']}")
    if not accepted: raise SystemExit(1)


if __name__ == "__main__": main()
