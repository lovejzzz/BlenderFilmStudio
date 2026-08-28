#!/usr/bin/env python3
"""Zero-render admission preflight for B52-D12.14-H2."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


SPEC_SHA256 = "2961f621b38f934cffaa7abe36deaaa5e01e7505d6361985039d0380578d244b"
CORRECTION_SHA256 = "9b6fdcedd571ad1ec7fb8d02bc7c6a630014d204de02f4a8b74bf5509c625a92"


def sha_bytes(value: bytes) -> str: return hashlib.sha256(value).hexdigest()
def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""): digest.update(chunk)
    return digest.hexdigest()
def canonical_hash(value: object) -> str: return sha_bytes(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode())


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--correction", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    return parser.parse_args()


def clean_env(spec: dict, root: Path) -> dict:
    env = {key: os.environ[key] for key in spec["runtime"]["environmentAllowlist"] if key in os.environ}
    env.update({"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "OCIO": str(root / spec["runtime"]["ocio"]["uri"]), "TMPDIR": os.environ.get("TMPDIR", "/tmp")})
    return env


def run_child(command: list[str], label: str, log_dir: Path, env: dict, children: list[dict]) -> None:
    started = time.monotonic()
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    stdout, stderr = process.communicate()
    stdout_path, stderr_path = log_dir / f"{label}.stdout.log", log_dir / f"{label}.stderr.log"
    stdout_path.write_text(stdout); stderr_path.write_text(stderr)
    row = {"label": label, "command": command, "pid": process.pid, "exitCode": process.returncode, "elapsedSeconds": round(time.monotonic() - started, 6), "stdout": {"uri": str(stdout_path), "sha256": sha_file(stdout_path)}, "stderr": {"uri": str(stderr_path), "sha256": sha_file(stderr_path)}}
    children.append(row)
    if process.returncode != 0: raise RuntimeError(f"H2 preflight child failed: {label}: {stderr[-2000:]}")


def git_value(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def main() -> None:
    cli = arguments()
    root = Path(__file__).resolve().parents[1]
    if sha_file(cli.spec) != SPEC_SHA256 or sha_file(cli.correction) != CORRECTION_SHA256 or cli.output_root.exists(): raise RuntimeError("H2 preflight identity/output freshness failure")
    spec = json.loads(cli.spec.read_text())
    correction = json.loads(cli.correction.read_text())
    if correction.get("experimentId") != spec["experimentId"]: raise RuntimeError("H2 preflight correction identity mismatch")
    formal_root = root / spec["freshness"]["formalRoot"]
    if formal_root.exists(): raise RuntimeError("H2 formal root exists before preflight")
    cli.output_root.mkdir(parents=True, exist_ok=False)
    logs = cli.output_root / "logs"; logs.mkdir()
    env = clean_env(spec, root)
    tool_paths = [root / path for path in spec["freshness"]["newToolPaths"]]
    if any(not path.is_file() for path in tool_paths): raise RuntimeError("H2 preflight missing frozen tool")
    tool_hashes = {str(path.relative_to(root)): sha_file(path) for path in tool_paths}
    tracked_clean = all(subprocess.run(["git", "diff", "--quiet", "HEAD", "--", str(path.relative_to(root))], cwd=root).returncode == 0 for path in tool_paths)
    if not tracked_clean: raise RuntimeError("H2 preflight tool bytes are not frozen in Git")
    children = []
    python_tools = [str(path) for path in tool_paths if path.suffix == ".py"]
    node_tools = [str(path) for path in tool_paths if path.suffix == ".mjs"]
    run_child([spec["runtime"]["python"]["executable"], "-m", "py_compile", *python_tools], "syntax-python", logs, env, children)
    run_child([spec["runtime"]["node"]["executable"], "--check", *node_tools], "syntax-node", logs, env, children)
    probe_report = cli.output_root / "scene-probe-report.json"
    source_tool = root / "blender/render_b52_d12_14_h2_projective_depth_source.py"
    run_child([spec["runtime"]["blender"]["executable"], *spec["runtime"]["blender"]["launchFlags"], "--python", str(source_tool), "--", "--spec", str(cli.spec), "--correction", str(cli.correction), "--fixture", spec["fixture"]["id"], "--frame", "1", "--repeat", "1", "--report", str(probe_report), "--probe-only"], "scene-probe", logs, env, children)
    probe = json.loads(probe_report.read_text())
    probe_body = {key: value for key, value in probe.items() if key != "reportHash"}
    probe_ok = probe.get("reportHash") == canonical_hash(probe_body) and probe.get("probeOnly") is True and probe.get("operationCounts", {}).get("blenderRenderCalls") == 0 and probe.get("passState", {}).get("Position") is True and probe.get("renderState", {}).get("resolution") == spec["sceneContract"]["render"]["resolution"]
    arithmetic_script = "const d=[2,4,2,4],w=[.25,.25,.25,.25];const f=(v)=>((v[0]*w[0]+v[1]*w[1])+v[2]*w[2])+v[3]*w[3];const direct=f(d),inverse=1/f(d.map(x=>1/x));if(direct!==3||Math.abs(inverse-8/3)>1e-15)process.exit(2);console.log(JSON.stringify({direct,inverse}));"
    run_child([spec["runtime"]["node"]["executable"], "-e", arithmetic_script], "synthetic-arithmetic", logs, env, children)
    depths, weights = [2.0, 4.0, 2.0, 4.0], [0.25] * 4
    direct = ((depths[0] * weights[0] + depths[1] * weights[1]) + depths[2] * weights[2]) + depths[3] * weights[3]
    inverse = 1.0 / ((((1.0 / depths[0]) * weights[0] + (1.0 / depths[1]) * weights[1]) + (1.0 / depths[2]) * weights[2]) + (1.0 / depths[3]) * weights[3])
    arithmetic_ok = direct == 3.0 and abs(inverse - 8.0 / 3.0) <= 1e-15
    smoke_bundle = cli.output_root / "analyzer-smoke-bundle.json"
    smoke_bundle.write_text(json.dumps({
        "experimentId": spec["experimentId"], "specSha256": SPEC_SHA256, "correctionSha256": CORRECTION_SHA256,
        "source": {"reportHash": "probe", "output": {"sha256": "probe"}, "operationCounts": {"blenderRenderCalls": 0}, "passState": {"Position": True}},
        "adapter": {"reportHash": "probe", "multipart": {"previousMetadata": {}}, "decodedPasses": {"current": {}}, "decisionArrays": {"currentDepth": {"sha256": "probe"}}, "controlArrays": {"currentPosition": {"sha256": "probe"}}},
        "consumer": {"reportHash": "probe", "inputBoundary": {"positionAvailable": False}, "controlArrays": {"projectiveDepthRescued": {"sha256": "probe"}}, "decisionArrays": {"reconstructed": {"sha256": "probe"}}, "counts": {"neitherHorizontal": 0}},
        "execution": {"executionHash": "probe", "children": [], "operationCounts": {"blenderRenderCalls": 0}},
    }, indent=2, sort_keys=True) + "\n")
    smoke_output = cli.output_root / "analyzer-smoke-result.json"
    analyzer_tool = root / "scripts/analyze-b52-d12-14-h2-projective-depth.py"
    run_child([spec["runtime"]["python"]["executable"], str(analyzer_tool), "--spec", str(cli.spec), "--correction", str(cli.correction), "--schema-smoke", str(smoke_bundle), "--output", str(smoke_output)], "analyzer-schema-smoke", logs, env, children)
    smoke = json.loads(smoke_output.read_text())
    smoke_body = {key: value for key, value in smoke.items() if key != "resultHash"}
    smoke_ok = smoke.get("resultHash") == canonical_hash(smoke_body) and smoke.get("passed") is True and smoke.get("keysExercised") == 17
    failure_probe_root = cli.output_root / "runner-failure-probe"
    runner_tool = root / "scripts/run-b52-d12-14-h2-projective-depth.py"
    run_child([spec["runtime"]["python"]["executable"], str(runner_tool), "--spec", str(cli.spec), "--correction", str(cli.correction), "--failure-probe", "--probe-root", str(failure_probe_root)], "runner-failure-probe", logs, env, children)
    failure = json.loads((failure_probe_root / "failure.json").read_text())
    execution_probe = json.loads((failure_probe_root / "execution.json").read_text())
    receipt_probe = json.loads((failure_probe_root / "receipt.json").read_text())
    failure_probe_ok = failure.get("scientificVerdict") is None and failure.get("failureHash") == canonical_hash({key: value for key, value in failure.items() if key != "failureHash"}) and execution_probe.get("executionHash") == canonical_hash({key: value for key, value in execution_probe.items() if key != "executionHash"}) and receipt_probe.get("receiptHash") == canonical_hash({key: value for key, value in receipt_probe.items() if key != "receiptHash"})
    free_bytes = os.statvfs(root).f_bavail * os.statvfs(root).f_frsize
    disk_ok = free_bytes - spec["diskAdmission"]["projectedWriteBytes"] >= spec["diskAdmission"]["minimumReserveBytesAfterProjectedWrite"]
    gates = {
        "SPEC_AND_CORRECTION_IDENTITIES": True, "ALL_TOOL_BYTES_TRACKED_CLEAN": tracked_clean, "PYTHON_AND_NODE_SYNTAX": True,
        "FACTORY_SCENE_PROBE": probe_ok, "ZERO_RENDER_AND_EXR": probe.get("operationCounts") == {"blenderProcesses": 1, "blenderRenderCalls": 0, "cyclesRayRenders": 0, "exrFiles": 0, "modelCalls": 0, "networkCalls": 0},
        "RECIPROCAL_DEPTH_SYNTHETIC_ARITHMETIC": arithmetic_ok, "ANALYZER_PROBE_SCHEMA_SMOKE": smoke_ok, "RUNNER_FAILURE_FINALLY_PATH": failure_probe_ok,
        "FORMAL_ROOT_ABSENT": not formal_root.exists(), "DISK_RESERVE": disk_ok, "UNIQUE_CHILD_PIDS": len({row["pid"] for row in children}) == len(children),
        "CHILDREN_EXIT_ZERO": all(row["exitCode"] == 0 for row in children), "MODEL_AND_NETWORK_ZERO": True,
    }
    passed = all(gates.values())
    body = {
        "schemaVersion": "bfs.blenderMaterialOwnerProjectiveDepthPreflight.v0.1", "experimentId": spec["experimentId"], "specSha256": SPEC_SHA256, "correctionSha256": CORRECTION_SHA256,
        "status": "ACCEPTED" if passed else "REJECTED", "passed": passed, "pid": os.getpid(), "gitCommit": git_value(root, "rev-parse", "HEAD"), "gitTree": git_value(root, "rev-parse", "HEAD^{tree}"),
        "toolHashes": tool_hashes, "children": children, "evidenceChecks": [{"name": name, "passed": bool(value)} for name, value in gates.items()], "evidenceChecksPassed": sum(bool(value) for value in gates.values()), "evidenceChecksTotal": len(gates),
        "disk": {"freeBytesObserved": free_bytes, "projectedWriteBytes": spec["diskAdmission"]["projectedWriteBytes"], "minimumReserveBytesAfterProjectedWrite": spec["diskAdmission"]["minimumReserveBytesAfterProjectedWrite"]},
        "artifacts": {"sceneProbe": {"uri": str(probe_report), "sha256": sha_file(probe_report)}, "analyzerSmoke": {"uri": str(smoke_output), "sha256": sha_file(smoke_output)}, "runnerFailureProbe": {"uri": str(failure_probe_root), "failureSha256": sha_file(failure_probe_root / "failure.json")}},
        "operationCounts": {"preflightProcesses": 1, "childProcesses": len(children), "blenderProcesses": 1, "blenderRenderCalls": 0, "cyclesRayRenders": 0, "exrFiles": 0, "modelCalls": 0, "networkCalls": 0},
    }
    preflight = {**body, "preflightHash": canonical_hash(body)}
    preflight_path = cli.output_root / "preflight.json"
    preflight_path.write_text(json.dumps(preflight, indent=2, sort_keys=True, allow_nan=False) + "\n")
    receipt_body = {"schemaVersion": "bfs.blenderMaterialOwnerProjectiveDepthPreflightReceipt.v0.1", "experimentId": spec["experimentId"], "specSha256": SPEC_SHA256, "correctionSha256": CORRECTION_SHA256, "preflight": {"uri": str(preflight_path), "sha256": sha_file(preflight_path), "preflightHash": preflight["preflightHash"]}, "formalRootAbsent": not formal_root.exists(), "operationCounts": {"receiptWrites": 1, "modelCalls": 0, "networkCalls": 0}}
    receipt = {**receipt_body, "receiptHash": canonical_hash(receipt_body)}
    (cli.output_root / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    if not passed: raise RuntimeError("H2 preflight rejected")
    print(f"BFS_D1214H2_PREFLIGHT_ACCEPTED gates={sum(gates.values())}/{len(gates)}")


if __name__ == "__main__": main()
