#!/usr/bin/env python3
"""Zero-formal-output admission preflight for B52-D12.9-H1."""
from __future__ import annotations

import argparse
import ast
import datetime as dt
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np


SPEC_SHA256 = "c2756a20e314cf470698ef7af6160154b8d7e2d5e8531ce6591b2509a8730dbc"
FILES = {
    "previousRgba": "previous.rgba32",
    "currentRgba": "current.rgba32",
    "previousDepth": "previous-depth.f32",
    "currentDepth": "current-depth.f32",
    "previousOwner": "previous-owner.f32",
    "currentOwner": "current-owner.f32",
    "vector": "vector.xy32",
    "vectorNext": "vector-next.xy32",
}


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canon(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def run(argv, repo, env=None):
    process = subprocess.run(argv, cwd=repo, env=env, capture_output=True, text=True)
    return {"pid": None, "exitCode": process.returncode, "stdout": process.stdout, "stderr": process.stderr, "argv": argv}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repo = Path.cwd().resolve()
    spec_path = args.spec.resolve()
    output = args.output.resolve()
    spec = json.loads(spec_path.read_text())
    if sha_file(spec_path) != SPEC_SHA256:
        raise RuntimeError("D12.9-H1 spec identity mismatch")
    expected_output = (repo / spec["diskAdmission"]["preflightRoot"] / "frozen-tool-preflight.json").resolve()
    if output != expected_output or output.parent.exists() or (repo / spec["diskAdmission"]["formalRoot"]).exists():
        raise RuntimeError("D12.9-H1 preflight/formal freshness rejected")
    tool_paths = spec["freshness"]["newFormalToolPaths"] + spec["freshness"]["reusedFrozenTools"]
    tool_hashes = {uri: sha_file(repo / uri) for uri in tool_paths}
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    git_checks = {}
    for uri in tool_paths:
        tracked = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", uri], cwd=repo).returncode == 0 and subprocess.run(["git", "ls-files", "--error-unmatch", uri], cwd=repo, capture_output=True).returncode == 0
        blob = subprocess.check_output(["git", "show", f"HEAD:{uri}"], cwd=repo)
        git_checks[uri] = tracked and sha_bytes(blob) == tool_hashes[uri]
    parent_checks = {name: sha_file(repo / row["uri"]) == row["sha256"] for name, row in spec["parents"].items() if "uri" in row and "sha256" in row}
    runtime_checks = {
        "blender": sha_file(Path(spec["runtime"]["blender"]["executable"])) == spec["runtime"]["blender"]["sha256"],
        "python": sha_file(Path(spec["runtime"]["python"]["executable"])) == spec["runtime"]["python"]["sha256"],
        "node": sha_file(Path(spec["runtime"]["node"]["executable"])) == spec["runtime"]["node"]["sha256"],
        "ocio": sha_file(repo / spec["runtime"]["ocio"]["uri"]) == spec["runtime"]["ocio"]["sha256"],
    }
    available = shutil.disk_usage(repo).free
    disk = {
        "availableBytes": available,
        "projectedWriteBytes": spec["diskAdmission"]["projectedWriteBytes"],
        "minimumReserveBytes": spec["diskAdmission"]["minimumReserveBytes"],
        "freeAfterProjectedBytes": available - spec["diskAdmission"]["projectedWriteBytes"],
    }
    disk["passed"] = disk["freeAfterProjectedBytes"] >= disk["minimumReserveBytes"]
    analyzer_tree = ast.parse((repo / "scripts/analyze-b52-d12-9-motion-aware.py").read_text())
    imports = []
    for node in ast.walk(analyzer_tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    analyzer_independent = all("reconstruct" not in name and "bpy" not in name and "mathutils" not in name for name in imports)
    base_env = {"PATH": os.environ.get("PATH", ""), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "OCIO": str((repo / spec["runtime"]["ocio"]["uri"]).resolve())}
    probe_rows, synthetic = [], {}
    with tempfile.TemporaryDirectory(prefix="bfs-d129-h1-preflight-") as temporary:
        temp = Path(temporary)
        for fixture in spec["fixtures"]:
            report = temp / "probes" / f"{fixture['id']}.json"
            runtime = temp / "runtime" / fixture["id"]
            env = {**base_env}
            for key, suffix in (("TMPDIR", "tmp"), ("BLENDER_USER_CONFIG", "config"), ("BLENDER_USER_SCRIPTS", "scripts")):
                target = runtime / suffix
                target.mkdir(parents=True, exist_ok=True)
                env[key] = str(target)
            row = run([spec["runtime"]["blender"]["executable"], *spec["runtime"]["blender"]["launchFlags"], "--python", str(repo / "blender/render_b52_d12_9_motion_aware_source.py"), "--", "--spec", str(spec_path), "--fixture", fixture["id"], "--frame", "1", "--repeat", "1", "--report", str(report), "--probe-only"], repo, env)
            payload = json.loads(report.read_text()) if report.exists() else {}
            probe_rows.append({
                "fixtureId": fixture["id"],
                "exitCode": row["exitCode"],
                "reportHashValid": payload.get("reportHash") == canon({key: value for key, value in payload.items() if key != "reportHash"}) if payload else False,
                "probeOnly": payload.get("probeOnly"),
                "output": payload.get("output"),
                "ownerCount": len(payload.get("sceneStructure", {}).get("owners", [])),
                "passIndices": [owner["passIndex"] for owner in payload.get("sceneStructure", {}).get("owners", [])],
                "renderCalls": payload.get("operationCounts", {}).get("blenderRenderCalls"),
                "stdoutTail": row["stdout"].strip().splitlines()[-1:],
                "stderrTail": row["stderr"].strip().splitlines()[-1:],
            })
        module_spec = importlib.util.spec_from_file_location("d129_consumer", repo / "scripts/reconstruct-b52-d12-9-motion-aware.py")
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        fixture = next(row for row in spec["fixtures"] if row["id"] == "STATIC_FREQUENCY_CONTROL_131X89")
        width, height = fixture["resolution"]
        arrays = {
            "previousRgba": np.zeros((height, width, 4), "<f4"),
            "currentRgba": np.zeros((height, width, 4), "<f4"),
            "previousDepth": np.zeros((height, width), "<f4"),
            "currentDepth": np.zeros((height, width), "<f4"),
            "previousOwner": np.zeros((height, width), "<f4"),
            "currentOwner": np.zeros((height, width), "<f4"),
            "vector": np.zeros((height, width, 2), "<f4"),
            "vectorNext": np.zeros((height, width, 2), "<f4"),
        }
        oracle_grid = {}
        for y in range(height):
            for x in range(width):
                oracle = module.oracle_pixel(spec, fixture, x, y)
                oracle_grid[(x, y)] = oracle
                if oracle:
                    color = np.array((0.25, 0.5, 0.75, 1.0) if oracle["ownerIndex"] == 1 else (0.75, 0.25, 0.5, 1.0), "<f4")
                    owner = np.float32(oracle["passIndex"])
                    arrays["previousRgba"][y, x] = color
                    arrays["currentRgba"][y, x] = color
                    arrays["previousDepth"][y, x] = np.float32(oracle["previousDepth"])
                    arrays["currentDepth"][y, x] = np.float32(oracle["currentDepth"])
                    arrays["previousOwner"][y, x] = owner
                    arrays["currentOwner"][y, x] = owner
        for y in range(10, 14):
            arrays["previousOwner"][y, 10:14] = 0
            arrays["previousRgba"][y, 20:24, 3] = 0
            arrays["previousDepth"][y, 30:34] += 1
            arrays["vector"][y, 40:44, 0] = -100
            arrays["currentOwner"][y, 50:54] = 0
        risk_target = None
        for y in range(8, height - 8):
            for x in range(8, width - 8):
                oracle = oracle_grid[(x, y)]
                if oracle and oracle["ownerIndex"] == 1 and all(oracle_grid[(xx, yy)] and oracle_grid[(xx, yy)]["passIndex"] == oracle["passIndex"] for yy in range(y - 3, y + 4) for xx in range(x - 3, x + 4)):
                    risk_target = (x, y, oracle)
                    break
            if risk_target:
                break
        if risk_target is None:
            raise RuntimeError("D12.9-H1 synthetic risk target absent")
        target_x, target_y, target_oracle = risk_target
        arrays["vector"][target_y, target_x] = np.array((0.5, -0.5), "<f4")
        arrays["previousDepth"][target_y:target_y + 2, target_x:target_x + 2] = np.float32(target_oracle["previousDepth"])
        for yy in range(target_y - 1, target_y + 3):
            for xx in range(target_x - 1, target_x + 3):
                value = np.float32(0.875 if (xx + yy) % 2 else 0.125)
                arrays["previousRgba"][yy, xx, :3] = value
        input_dir = temp / "synthetic/input"
        input_dir.mkdir(parents=True)
        records = {}
        for name, filename in FILES.items():
            payload = np.ascontiguousarray(arrays[name], dtype="<f4").tobytes()
            target = input_dir / filename
            target.write_bytes(payload)
            records[name] = {"uri": str(target), "sha256": sha_bytes(payload), "bytes": len(payload), "shape": list(arrays[name].shape), "dtype": "little-endian-float32"}
        adapter_body = {"schemaVersion": "bfs.d129SyntheticAdapter.v0.1", "experimentId": spec["experimentId"], "fixtureId": fixture["id"], "repeat": 1, "pid": 0, "arrays": records}
        adapter = {**adapter_body, "reportHash": canon(adapter_body)}
        adapter_path = temp / "synthetic/adapter.json"
        adapter_path.write_text(json.dumps(adapter, indent=2, sort_keys=True) + "\n")
        reports = {}
        for producer, executable, tool in (("python", spec["runtime"]["python"]["executable"], repo / "scripts/reconstruct-b52-d12-9-motion-aware.py"), ("node", spec["runtime"]["node"]["executable"], repo / "scripts/reconstruct-b52-d12-9-motion-aware.mjs")):
            output_dir = temp / "synthetic" / producer / "arrays"
            report = temp / "synthetic" / producer / "report.json"
            row = run([executable, str(tool), "--spec", str(spec_path), "--fixture", fixture["id"], "--repeat", "1", "--input-dir", str(input_dir), "--adapter-report", str(adapter_path), "--output-dir", str(output_dir), "--report", str(report)], repo, base_env)
            reports[producer] = {"exitCode": row["exitCode"], "report": json.loads(report.read_text()) if report.exists() else {}, "outputDir": output_dir}
        py_dir, node_dir = reports["python"]["outputDir"], reports["node"]["outputDir"]
        payload_identity = all((py_dir / filename).read_bytes() == (node_dir / filename).read_bytes() for filename, _dtype in module.OUTPUTS.values())
        risk_rejected = np.frombuffer((py_dir / "risk-rejected.u8").read_bytes(), dtype="u1").reshape(height, width)
        accepted = np.frombuffer((py_dir / "accepted.u8").read_bytes(), dtype="u1").reshape(height, width)
        support = np.frombuffer((py_dir / "support-eligible.u8").read_bytes(), dtype="u1").reshape(height, width)
        synthetic = {
            "pythonExitCode": reports["python"]["exitCode"],
            "nodeExitCode": reports["node"]["exitCode"],
            "pythonReportHashValid": reports["python"]["report"].get("reportHash") == canon({key: value for key, value in reports["python"]["report"].items() if key != "reportHash"}),
            "nodeReportHashValid": reports["node"]["report"].get("reportHash") == canon({key: value for key, value in reports["node"]["report"].items() if key != "reportHash"}),
            "payloadIdentity": payload_identity,
            "riskTarget": [target_x, target_y],
            "riskTargetSupportEligible": bool(support[target_y, target_x]),
            "riskTargetRejected": bool(risk_rejected[target_y, target_x]),
            "riskRejectedPixels": int(risk_rejected.sum()),
            "acceptedPixels": int(accepted.sum()),
        }
    probe_ok = all(row["exitCode"] == 0 and row["reportHashValid"] and row["probeOnly"] is True and row["output"] is None and row["ownerCount"] == 2 and row["renderCalls"] == 0 for row in probe_rows)
    synthetic_ok = synthetic["pythonExitCode"] == 0 and synthetic["nodeExitCode"] == 0 and synthetic["pythonReportHashValid"] and synthetic["nodeReportHashValid"] and synthetic["payloadIdentity"] and synthetic["riskTargetSupportEligible"] and synthetic["riskTargetRejected"] and synthetic["riskRejectedPixels"] >= 1 and synthetic["acceptedPixels"] > 0
    checks = {
        "specIdentity": True,
        "formalRootAbsent": not (repo / spec["diskAdmission"]["formalRoot"]).exists(),
        "preflightRootFresh": not output.parent.exists(),
        "toolHashesMatchHead": all(git_checks.values()),
        "parentIdentity": all(parent_checks.values()),
        "runtimeIdentity": all(runtime_checks.values()),
        "diskAdmission": disk["passed"],
        "analyzerImportIndependence": analyzer_independent,
        "allFixtureConstructionProbes": probe_ok,
        "dualConsumerSyntheticIdentityAndRiskBranch": synthetic_ok,
    }
    body = {
        "schemaVersion": "bfs.blenderMotionAwareCurvatureRiskHoldoutPreflight.v0.1",
        "experimentId": spec["experimentId"],
        "executedAtUtc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "ACCEPTED" if all(checks.values()) else "REJECTED",
        "toolFreezeCommit": head,
        "toolHashes": tool_hashes,
        "gitChecks": git_checks,
        "parentChecks": parent_checks,
        "runtimeChecks": runtime_checks,
        "diskAdmission": disk,
        "analyzerImports": sorted(imports),
        "constructionProbes": probe_rows,
        "syntheticBranchTest": synthetic,
        "checks": checks,
        "operationCounts": {"blenderProbeProcesses": len(probe_rows), "syntheticConsumerProcesses": 2, "blenderRenderCalls": 0, "modelCalls": 0, "networkCalls": 0},
    }
    report = {**body, "preflightHash": canon(body)}
    output.parent.mkdir(parents=True, exist_ok=False)
    output.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D129_PREFLIGHT status={report['status']} checks={sum(checks.values())}/{len(checks)} riskRejected={synthetic['riskRejectedPixels']}")
    raise SystemExit(0 if report["status"] == "ACCEPTED" else 1)


if __name__ == "__main__":
    main()
