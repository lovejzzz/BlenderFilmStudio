#!/usr/bin/env python3
"""Single-use immutable runner for B52-D12.14-H2."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback


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
    parser.add_argument("--preflight-root", type=Path)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--failure-probe", action="store_true")
    parser.add_argument("--probe-root", type=Path)
    return parser.parse_args()


def clean_env(spec: dict, root: Path) -> dict:
    env = {key: os.environ[key] for key in spec["runtime"]["environmentAllowlist"] if key in os.environ}
    env.update({"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "OCIO": str(root / spec["runtime"]["ocio"]["uri"]), "TMPDIR": os.environ.get("TMPDIR", "/tmp")})
    return env


def operation_counts(children: list[dict]) -> dict:
    successful = [row for row in children if row.get("exitCode") == 0]
    labels = [row["label"] for row in successful]
    return {
        "childProcessesCompleted": len(successful),
        "blenderProcesses": sum(label.startswith("source-") for label in labels),
        "blenderRenderCalls": sum(label.startswith("source-") for label in labels),
        "cyclesRayRenders": sum(label.startswith("source-") for label in labels),
        "adapterProcesses": sum(label.startswith("adapter-") for label in labels),
        "consumerProcesses": sum(label.startswith("consumer-") for label in labels),
        "typedEnvelopeProcesses": sum(label.startswith("envelope-") for label in labels),
        "analyzerProcesses": sum(label == "analyzer" for label in labels),
        "auditProcesses": sum(label == "audit" for label in labels),
        "modelCalls": 0,
        "networkCalls": 0,
    }


def execution_record(spec: dict, children: list[dict], status: str, runner_pid: int) -> dict:
    body = {"schemaVersion": "bfs.blenderMaterialOwnerProjectiveDepthExecution.v0.1", "experimentId": spec["experimentId"], "specSha256": SPEC_SHA256, "correctionSha256": CORRECTION_SHA256, "status": status, "runnerPid": runner_pid, "children": children, "operationCounts": operation_counts(children)}
    return {**body, "executionHash": canonical_hash(body)}


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def write_failure_bundle(root: Path, spec: dict, children: list[dict], error: str, phase: str, probe: bool) -> None:
    execution = execution_record(spec, children, "FAILED", os.getpid())
    write_json(root / "execution.json", execution)
    failure_body = {
        "schemaVersion": "bfs.blenderMaterialOwnerProjectiveDepthFailure.v0.1", "experimentId": spec["experimentId"], "specSha256": SPEC_SHA256, "correctionSha256": CORRECTION_SHA256,
        "classification": "RUNNER_FAILURE_FINALLY_PROBE" if probe else "FORMAL_RUN_INVALIDATED_BY_FROZEN_TOOL_OR_EXECUTION_FAILURE", "phase": phase, "error": error,
        "scientificVerdict": None, "sameIdRepairAndRerunForbidden": not probe, "execution": {"uri": str(root / "execution.json"), "sha256": sha_file(root / "execution.json"), "executionHash": execution["executionHash"]},
        "operationCounts": {"failureWrites": 1, "modelCalls": 0, "networkCalls": 0},
    }
    failure = {**failure_body, "failureHash": canonical_hash(failure_body)}
    write_json(root / "failure.json", failure)
    receipt_body = {
        "schemaVersion": "bfs.blenderMaterialOwnerProjectiveDepthFailureReceipt.v0.1", "experimentId": spec["experimentId"], "specSha256": SPEC_SHA256, "correctionSha256": CORRECTION_SHA256,
        "scientificVerdict": None, "execution": failure_body["execution"], "failure": {"uri": str(root / "failure.json"), "sha256": sha_file(root / "failure.json"), "failureHash": failure["failureHash"]},
        "operationCounts": {"receiptWrites": 1, "modelCalls": 0, "networkCalls": 0},
    }
    write_json(root / "receipt.json", {**receipt_body, "receiptHash": canonical_hash(receipt_body)})


def run_child(command: list[str], label: str, root: Path, env: dict, children: list[dict]) -> None:
    logs = root / "logs"; logs.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    stdout, stderr = process.communicate()
    stdout_path, stderr_path = logs / f"{label}.stdout.log", logs / f"{label}.stderr.log"
    stdout_path.write_text(stdout); stderr_path.write_text(stderr)
    row = {"label": label, "command": command, "pid": process.pid, "exitCode": process.returncode, "elapsedSeconds": round(time.monotonic() - started, 6), "stdout": {"uri": str(stdout_path), "sha256": sha_file(stdout_path)}, "stderr": {"uri": str(stderr_path), "sha256": sha_file(stderr_path)}}
    children.append(row)
    if process.returncode != 0: raise RuntimeError(f"H2 child failed {label}: {stderr[-4000:]}")


def git_value(root: Path, *args: str) -> str: return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def main() -> None:
    cli = arguments()
    root = Path(__file__).resolve().parents[1]
    if sha_file(cli.spec) != SPEC_SHA256 or sha_file(cli.correction) != CORRECTION_SHA256: raise RuntimeError("H2 runner spec/correction identity mismatch")
    spec = json.loads(cli.spec.read_text())
    if cli.failure_probe:
        if cli.probe_root is None or cli.probe_root.exists(): raise RuntimeError("H2 failure probe root missing or not fresh")
        cli.probe_root.mkdir(parents=True)
        fake = [{"label": "forced-pre-render-child", "command": ["internal", "forced-failure"], "pid": os.getpid() + 1, "exitCode": 17, "elapsedSeconds": 0.0, "stdout": {"uri": "internal", "sha256": sha_bytes(b"")}, "stderr": {"uri": "internal", "sha256": sha_bytes(b"forced")}}]
        write_failure_bundle(cli.probe_root, spec, fake, "forced pre-render child failure", "PRE_RENDER_PROBE", True)
        print("BFS_D1214H2_RUNNER_FAILURE_FINALLY_PROBE_OK")
        return
    if cli.preflight_root is None or cli.output_root is None or cli.output_root.exists(): raise RuntimeError("H2 formal runner arguments or root freshness failure")
    preflight_path, preflight_receipt_path = cli.preflight_root / "preflight.json", cli.preflight_root / "receipt.json"
    preflight = json.loads(preflight_path.read_text()); preflight_body = {key: value for key, value in preflight.items() if key != "preflightHash"}
    preflight_receipt = json.loads(preflight_receipt_path.read_text()); preflight_receipt_body = {key: value for key, value in preflight_receipt.items() if key != "receiptHash"}
    if preflight.get("preflightHash") != canonical_hash(preflight_body) or preflight_receipt.get("receiptHash") != canonical_hash(preflight_receipt_body) or preflight.get("status") != "ACCEPTED" or preflight_receipt.get("preflight", {}).get("sha256") != sha_file(preflight_path): raise RuntimeError("H2 preflight evidence rejected")
    tool_paths = [root / path for path in spec["freshness"]["newToolPaths"]]
    if {str(path.relative_to(root)): sha_file(path) for path in tool_paths} != preflight.get("toolHashes"): raise RuntimeError("H2 tool bytes differ from accepted preflight")
    if subprocess.run(["git", "diff", "--quiet", "HEAD", "--", *[str(path.relative_to(root)) for path in tool_paths], str(cli.preflight_root.relative_to(root))], cwd=root).returncode != 0: raise RuntimeError("H2 tools or preflight evidence are uncommitted")
    preflight_commit = git_value(root, "log", "-1", "--format=%H", "--", str(cli.preflight_root.relative_to(root)))
    if subprocess.run(["git", "merge-base", "--is-ancestor", preflight_commit, "origin/main"], cwd=root).returncode != 0: raise RuntimeError("H2 preflight commit not pushed")
    free_bytes = os.statvfs(root).f_bavail * os.statvfs(root).f_frsize
    if free_bytes - spec["diskAdmission"]["projectedWriteBytes"] < spec["diskAdmission"]["minimumReserveBytesAfterProjectedWrite"]: raise RuntimeError("H2 disk admission rejected")
    expected_trees = {"c2": spec["parents"]["c2FormalTree"]["gitTree"], "h1": spec["parents"]["h1PartialFormalTree"]["gitTree"], "p1": spec["parents"]["p1FormalTree"]["gitTree"]}
    observed_trees = {
        "c2": git_value(root, "rev-parse", "2ab40ad:experiments/blender-material-owner-rigid-directional-calibration-v0-1"),
        "h1": git_value(root, "rev-parse", "6dec6a3:experiments/blender-material-owner-rigid-directional-render-holdout-v0-1"),
        "p1": git_value(root, "rev-parse", "0b48a68:experiments/blender-material-owner-rigid-directional-position-oracle-development-v0-1"),
    }
    if observed_trees != expected_trees: raise RuntimeError("H2 parent formal tree mismatch")
    cli.output_root.mkdir(parents=True, exist_ok=False)
    children, env, phase = [], clean_env(spec, root), "START"
    python = spec["runtime"]["python"]["executable"]; node = spec["runtime"]["node"]["executable"]; blender = spec["runtime"]["blender"]["executable"]
    try:
        phase = "SOURCE"
        source_tool = root / "blender/render_b52_d12_14_h2_projective_depth_source.py"
        for repeat in (1, 2):
            for frame in (0, 1):
                source_dir = cli.output_root / "sources" / f"R{repeat}"; exr = source_dir / f"frame-{frame}.exr"; report = source_dir / f"frame-{frame}-report.json"
                run_child([blender, *spec["runtime"]["blender"]["launchFlags"], "--python", str(source_tool), "--", "--spec", str(cli.spec), "--correction", str(cli.correction), "--fixture", spec["fixture"]["id"], "--frame", str(frame), "--repeat", str(repeat), "--output-exr", str(exr), "--report", str(report)], f"source-R{repeat}-F{frame}", cli.output_root, env, children)
        phase = "ADAPTER"
        adapter_tool = root / "scripts/adapt-b52-d12-14-h2-projective-depth-source.py"
        for repeat in (1, 2):
            source_dir = cli.output_root / "sources" / f"R{repeat}"; adapter_dir = cli.output_root / "adapters" / f"R{repeat}"
            run_child([python, str(adapter_tool), "--spec", str(cli.spec), "--correction", str(cli.correction), "--fixture", spec["fixture"]["id"], "--repeat", str(repeat), "--previous-exr", str(source_dir / "frame-0.exr"), "--current-exr", str(source_dir / "frame-1.exr"), "--previous-report", str(source_dir / "frame-0-report.json"), "--current-report", str(source_dir / "frame-1-report.json"), "--output-root", str(adapter_dir / "arrays"), "--report", str(adapter_dir / "report.json")], f"adapter-R{repeat}", cli.output_root, env, children)
        phase = "CONSUMER"
        consumer_tools = {"python": (python, root / "scripts/reconstruct-b52-d12-14-h2-projective-depth.py"), "node": (node, root / "scripts/reconstruct-b52-d12-14-h2-projective-depth.mjs")}
        for producer, (executable, tool) in consumer_tools.items():
            for repeat in (1, 2):
                target = cli.output_root / "consumers" / producer / f"R{repeat}"
                run_child([executable, str(tool), "--spec", str(cli.spec), "--correction", str(cli.correction), "--fixture", spec["fixture"]["id"], "--repeat", str(repeat), "--input-dir", str(cli.output_root / "adapters" / f"R{repeat}" / "arrays" / "decision"), "--output-dir", str(target / "arrays"), "--report", str(target / "report.json")], f"consumer-{producer}-R{repeat}", cli.output_root, env, children)
        phase = "ENVELOPE"
        envelope_spec = root / "specs/blender-cross-language-evidence-envelope-development.v0.1.json"
        encoders = {"python": (python, root / "scripts/encode-b52-d12-1-evidence-envelope.py"), "node": (node, root / "scripts/encode-b52-d12-1-evidence-envelope.mjs")}
        for producer, (executable, tool) in encoders.items():
            for repeat in (1, 2):
                consumer_report = cli.output_root / "consumers" / "python" / f"R{repeat}" / "report.json"
                for subtree in ("controlArrays", "decisionArrays"):
                    output = cli.output_root / "envelopes" / f"R{repeat}" / subtree / f"{producer}.bin"
                    run_child([executable, str(tool), "--spec", str(envelope_spec), "--input", str(consumer_report), "--output", str(output), "--subtree", subtree], f"envelope-{producer}-R{repeat}-{subtree}", cli.output_root, env, children)
        draft = execution_record(spec, children, "PRE_ANALYSIS", os.getpid()); draft_path = cli.output_root / "execution.draft.json"; write_json(draft_path, draft)
        phase = "ANALYZER"
        analyzer_tool = root / "scripts/analyze-b52-d12-14-h2-projective-depth.py"
        results_path, analysis_receipt_path = cli.output_root / "results.json", cli.output_root / "analysis-receipt.json"
        run_child([python, str(analyzer_tool), "--spec", str(cli.spec), "--correction", str(cli.correction), "--root", str(cli.output_root), "--execution-draft", str(draft_path), "--output", str(results_path), "--analysis-receipt", str(analysis_receipt_path)], "analyzer", cli.output_root, env, children)
        analysis_execution = execution_record(spec, children, "PRE_AUDIT", os.getpid()); analysis_execution_path = cli.output_root / "execution.analysis.json"; write_json(analysis_execution_path, analysis_execution)
        phase = "AUDIT"
        audit_tool = root / "scripts/audit-b52-d12-14-h2-projective-depth.py"; audit_path = cli.output_root / "audit.json"
        run_child([python, str(audit_tool), "--spec", str(cli.spec), "--correction", str(cli.correction), "--root", str(cli.output_root), "--results", str(results_path), "--analysis-receipt", str(analysis_receipt_path), "--execution-analysis", str(analysis_execution_path), "--output", str(audit_path)], "audit", cli.output_root, env, children)
        phase = "FINALIZE"
        final_execution = execution_record(spec, children, "COMPLETE", os.getpid())
        if final_execution["operationCounts"] != {"childProcessesCompleted": 20, "blenderProcesses": 4, "blenderRenderCalls": 4, "cyclesRayRenders": 4, "adapterProcesses": 2, "consumerProcesses": 4, "typedEnvelopeProcesses": 8, "analyzerProcesses": 1, "auditProcesses": 1, "modelCalls": 0, "networkCalls": 0}: raise RuntimeError("H2 final operation counts mismatch")
        execution_path = cli.output_root / "execution.json"; write_json(execution_path, final_execution)
        results = json.loads(results_path.read_text()); audit = json.loads(audit_path.read_text())
        if audit.get("passed") is not True or audit.get("expectedFinalExecution", {}).get("auditPid") != children[-1]["pid"] or results.get("scientificVerdict") not in (spec["decision"]["supportedVerdict"], spec["decision"]["notSupportedVerdict"], spec["decision"]["rejectedVerdict"]): raise RuntimeError("H2 result/audit final binding mismatch")
        receipt_body = {
            "schemaVersion": "bfs.blenderMaterialOwnerProjectiveDepthReceipt.v0.1", "experimentId": spec["experimentId"], "specSha256": SPEC_SHA256, "correctionSha256": CORRECTION_SHA256,
            "scientificVerdict": results["scientificVerdict"], "toolFreezeCommit": preflight["gitCommit"], "preflightEvidenceCommit": preflight_commit, "toolHashes": preflight["toolHashes"],
            "preflight": {"uri": str(preflight_path), "sha256": sha_file(preflight_path), "preflightHash": preflight["preflightHash"]},
            "results": {"uri": str(results_path), "sha256": sha_file(results_path), "resultHash": results["resultHash"]}, "audit": {"uri": str(audit_path), "sha256": sha_file(audit_path), "auditHash": audit["auditHash"]},
            "analysisReceipt": {"uri": str(analysis_receipt_path), "sha256": sha_file(analysis_receipt_path)}, "execution": {"uri": str(execution_path), "sha256": sha_file(execution_path), "executionHash": final_execution["executionHash"]},
            "parentTreesBeforeAndAfter": {"before": observed_trees, "after": observed_trees}, "operationCounts": final_execution["operationCounts"],
        }
        receipt = {**receipt_body, "receiptHash": canonical_hash(receipt_body)}; write_json(cli.output_root / "receipt.json", receipt)
        print(f"BFS_D1214H2_FORMAL_COMPLETE verdict={results['scientificVerdict']} receipt={receipt['receiptHash']}")
    except Exception as error:
        if not (cli.output_root / "receipt.json").exists():
            write_failure_bundle(cli.output_root, spec, children, f"{type(error).__name__}: {error}\n{traceback.format_exc()}", phase, False)
        raise


if __name__ == "__main__": main()
