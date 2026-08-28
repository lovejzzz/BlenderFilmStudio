#!/usr/bin/env python3
"""Run the frozen 56-process B52-D12.14-H1 formal matrix."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


SPEC_SHA256 = "7ff239d91dca6ea8708ce4cac955dd0b129ae067028a77ec1699a43a236195a8"
ENVELOPE_SPEC = "specs/blender-cross-language-evidence-envelope-development.v0.1.json"


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def self_ok(value: dict, field: str) -> bool:
    return value.get(field) == canonical_hash({key: row for key, row in value.items() if key != field})


def git(*arguments: str) -> str:
    return subprocess.run(["git", *arguments], check=True, text=True, capture_output=True).stdout.strip()


def command_env(spec: dict) -> dict[str, str]:
    allowed = set(spec["runtime"]["environmentAllowlist"])
    environment = {key: value for key, value in os.environ.items() if key in allowed}
    environment["OCIO"] = str(Path(spec["runtime"]["ocio"]["uri"]).resolve())
    environment.setdefault("PATH", "/usr/bin:/bin:/usr/sbin:/sbin")
    environment.setdefault("LANG", "C.UTF-8")
    environment.setdefault("LC_ALL", "C.UTF-8")
    return environment


def spawn(command: list[str], category: str, environment: dict[str, str]) -> dict:
    started = time.monotonic()
    process = subprocess.Popen(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment)
    stdout, stderr = process.communicate()
    row = {
        "category": category, "pid": process.pid, "exitCode": process.returncode,
        "elapsedSeconds": round(time.monotonic() - started, 6), "command": command,
        "stdout": stdout, "stderr": stderr,
    }
    if process.returncode != 0:
        raise RuntimeError(f"D12.14-H1 child failed: {category} pid={process.pid}\n{stdout}\n{stderr}")
    return row


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--preflight-receipt", type=Path, required=True)
    return parser.parse_args()


def main():
    cli = arguments()
    if sha_file(cli.spec) != SPEC_SHA256:
        raise RuntimeError("D12.14-H1 spec identity mismatch")
    spec = json.loads(cli.spec.read_text())
    if cli.root.as_posix() != spec["freshness"]["formalRoot"] or cli.root.exists():
        raise RuntimeError("D12.14-H1 formal root must be exact and fresh")
    preflight = json.loads(cli.preflight_receipt.read_text())
    if not self_ok(preflight, "receiptHash") or not preflight.get("passed") or preflight.get("specSha256") != SPEC_SHA256:
        raise RuntimeError("D12.14-H1 passing preflight receipt required")
    tool_hashes = {uri: sha_file(Path(uri)) for uri in spec["freshness"]["newFormalToolPaths"]}
    if preflight.get("toolHashes") != tool_hashes:
        raise RuntimeError("D12.14-H1 preflight/tool freeze mismatch")
    for uri in spec["freshness"]["newFormalToolPaths"]:
        subprocess.run(["git", "diff", "--quiet", "HEAD", "--", uri], check=True)
        subprocess.run(["git", "ls-files", "--error-unmatch", uri], check=True, stdout=subprocess.DEVNULL)
    parent_trees_before = {
        "derivationFormalRoot": git("rev-parse", f"HEAD:{spec['parents']['derivationFormalRoot']['uri']}"),
        "materialOwnerFormalRoot": git("rev-parse", f"HEAD:{spec['parents']['materialOwnerFormalRoot']['uri']}"),
    }
    if parent_trees_before != {
        "derivationFormalRoot": spec["parents"]["derivationFormalRoot"]["gitTree"],
        "materialOwnerFormalRoot": spec["parents"]["materialOwnerFormalRoot"]["gitTree"],
    }:
        raise RuntimeError("D12.14-H1 parent formal tree mismatch")
    free_bytes = shutil.disk_usage(Path.cwd()).free
    reserve = int(spec["diskAdmission"]["minimumReserveBytesAfterProjectedWrite"])
    required_before = reserve + int(spec["diskAdmission"]["projectedWriteBytes"])
    if free_bytes < required_before:
        raise RuntimeError(f"D12.14-H1 disk reserve gate failed: {free_bytes} < {required_before}")
    environment = command_env(spec)
    cli.root.mkdir(parents=True, exist_ok=False)
    children = []
    blender = spec["runtime"]["blender"]["executable"]
    python = spec["runtime"]["python"]["executable"]
    node = spec["runtime"]["node"]["executable"]
    source_tool = "blender/render_b52_d12_14_h1_rigid_directional_source.py"
    adapter_tool = "scripts/adapt-b52-d12-14-h1-rigid-directional-source.py"
    python_consumer = "scripts/reconstruct-b52-d12-14-h1-rigid-directional.py"
    node_consumer = "scripts/reconstruct-b52-d12-14-h1-rigid-directional.mjs"

    for fixture in spec["fixtures"]:
        fixture_id = fixture["id"]
        for repeat in (1, 2):
            for frame in (0, 1):
                base = cli.root / "sources" / fixture_id / f"R{repeat}"
                command = [
                    blender, *spec["runtime"]["blender"]["launchFlags"], "--python", source_tool, "--",
                    "--spec", str(cli.spec), "--fixture", fixture_id, "--frame", str(frame), "--repeat", str(repeat),
                    "--output-exr", str(base / f"frame-{frame}.exr"), "--report", str(base / f"frame-{frame}-report.json"),
                ]
                children.append(spawn(command, "sourceBlender", environment))

    for fixture in spec["fixtures"]:
        fixture_id = fixture["id"]
        for repeat in (1, 2):
            source_base = cli.root / "sources" / fixture_id / f"R{repeat}"
            adapter_base = cli.root / "adapters" / fixture_id / f"R{repeat}"
            command = [
                python, adapter_tool, "--spec", str(cli.spec), "--fixture", fixture_id, "--repeat", str(repeat),
                "--previous-exr", str(source_base / "frame-0.exr"), "--current-exr", str(source_base / "frame-1.exr"),
                "--previous-report", str(source_base / "frame-0-report.json"), "--current-report", str(source_base / "frame-1-report.json"),
                "--output-dir", str(adapter_base / "arrays"), "--report", str(adapter_base / "report.json"),
            ]
            children.append(spawn(command, "adapter", environment))

    for fixture in spec["fixtures"]:
        fixture_id = fixture["id"]
        for repeat in (1, 2):
            adapter_base = cli.root / "adapters" / fixture_id / f"R{repeat}"
            for producer, executable, tool in (
                ("python", python, python_consumer), ("node", node, node_consumer),
            ):
                consumer_base = cli.root / "consumers" / producer / fixture_id / f"R{repeat}"
                command = [
                    executable, tool, "--spec", str(cli.spec), "--fixture", fixture_id, "--repeat", str(repeat),
                    "--input-dir", str(adapter_base / "arrays"), "--adapter-report", str(adapter_base / "report.json"),
                    "--output-dir", str(consumer_base / "arrays"), "--report", str(consumer_base / "report.json"),
                ]
                children.append(spawn(command, f"{producer}Consumer", environment))

    for fixture in spec["fixtures"]:
        fixture_id = fixture["id"]
        for repeat in (1, 2):
            input_report = cli.root / "consumers" / "python" / fixture_id / f"R{repeat}" / "report.json"
            for subtree in ("controlArrays", "decisionArrays"):
                envelope_base = cli.root / "envelopes" / fixture_id / f"R{repeat}" / subtree
                for producer, executable, tool, output in (
                    ("python", python, spec["parents"]["typedEnvelopePython"]["uri"], envelope_base / "python.bin"),
                    ("node", node, spec["parents"]["typedEnvelopeNode"]["uri"], envelope_base / "node.bin"),
                ):
                    command = [executable, tool, "--spec", ENVELOPE_SPEC, "--input", str(input_report), "--output", str(output), "--subtree", subtree]
                    children.append(spawn(command, f"typedEnvelope{producer.title()}", environment))

    result_path = cli.root / "results.json"
    analysis_receipt_path = cli.root / "analysis-receipt.json"
    analyzer_command = [
        python, "scripts/analyze-b52-d12-14-h1-rigid-directional.py", "--spec", str(cli.spec), "--root", str(cli.root),
        "--output", str(result_path), "--analysis-receipt", str(analysis_receipt_path),
    ]
    children.append(spawn(analyzer_command, "analyzer", environment))
    if len(children) != 109:
        raise RuntimeError(f"D12.14-H1 pre-audit process roster mismatch: {len(children)}")

    execution_plan_path = cli.root / "execution-plan.json"
    audit_path = cli.root / "audit.json"
    audit_command = [
        python, "scripts/audit-b52-d12-14-h1-rigid-directional.py", "--spec", str(cli.spec), "--root", str(cli.root),
        "--result", str(result_path), "--analysis-receipt", str(analysis_receipt_path),
        "--execution-plan", str(execution_plan_path), "--preflight-receipt", str(cli.preflight_receipt), "--output", str(audit_path),
    ]
    audit_started = time.monotonic()
    audit_process = subprocess.Popen(audit_command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment)
    audit_plan_row = {"category": "audit", "pid": audit_process.pid, "exitCode": None, "status": "running", "command": audit_command}
    planned_children = [*children, audit_plan_row]
    category_counts = {}
    for row in planned_children:
        category_counts[row["category"]] = category_counts.get(row["category"], 0) + 1
    plan_body = {
        "schemaVersion": "bfs.blenderMaterialOwnerRigidDirectionalRenderHoldoutExecutionPlan.v0.1",
        "experimentId": spec["experimentId"], "specSha256": SPEC_SHA256,
        "children": planned_children, "categoryCounts": category_counts,
        "allChildrenUniquePid": len({row["pid"] for row in planned_children}) == len(planned_children),
        "toolHashes": tool_hashes, "parentTreesBefore": parent_trees_before,
        "operationCounts": {**spec["processMatrix"]},
    }
    plan = {**plan_body, "executionPlanHash": canonical_hash(plan_body)}
    execution_plan_path.write_text(json.dumps(plan, indent=2, sort_keys=True, allow_nan=False) + "\n")
    audit_stdout, audit_stderr = audit_process.communicate()
    audit_row = {
        "category": "audit", "pid": audit_process.pid, "exitCode": audit_process.returncode,
        "elapsedSeconds": round(time.monotonic() - audit_started, 6), "command": audit_command,
        "stdout": audit_stdout, "stderr": audit_stderr,
    }
    children.append(audit_row)
    parent_trees_after = {
        "derivationFormalRoot": git("rev-parse", f"HEAD:{spec['parents']['derivationFormalRoot']['uri']}"),
        "materialOwnerFormalRoot": git("rev-parse", f"HEAD:{spec['parents']['materialOwnerFormalRoot']['uri']}"),
    }
    execution_body = {
        "schemaVersion": "bfs.blenderMaterialOwnerRigidDirectionalRenderHoldoutExecution.v0.1",
        "experimentId": spec["experimentId"], "specSha256": SPEC_SHA256,
        "children": children, "categoryCounts": category_counts,
        "allChildrenUniquePid": len({row["pid"] for row in children}) == len(children),
        "allChildrenExitZero": all(row["exitCode"] == 0 for row in children),
        "toolHashes": tool_hashes, "parentTreesBefore": parent_trees_before, "parentTreesAfter": parent_trees_after,
        "parentTreesImmutable": parent_trees_before == parent_trees_after,
        "diskFreeBytesBefore": free_bytes, "diskFreeBytesAfter": shutil.disk_usage(Path.cwd()).free,
        "operationCounts": {**spec["processMatrix"]},
    }
    execution = {**execution_body, "executionHash": canonical_hash(execution_body)}
    execution_path = cli.root / "execution.json"
    execution_path.write_text(json.dumps(execution, indent=2, sort_keys=True, allow_nan=False) + "\n")
    audit = json.loads(audit_path.read_text()) if audit_path.exists() else None
    result = json.loads(result_path.read_text())
    evidence = {}
    for path in sorted(cli.root.rglob("*")):
        if path.is_file() and path.name != "receipt.json":
            evidence[path.relative_to(cli.root).as_posix()] = {"sha256": sha_file(path), "bytes": path.stat().st_size}
    final_valid = bool(
        audit_process.returncode == 0 and audit and audit.get("passed") and self_ok(audit, "auditHash")
        and execution["allChildrenUniquePid"] and execution["allChildrenExitZero"] and execution["parentTreesImmutable"]
    )
    receipt_body = {
        "schemaVersion": "bfs.blenderMaterialOwnerRigidDirectionalRenderHoldoutReceipt.v0.1",
        "experimentId": spec["experimentId"], "specSha256": SPEC_SHA256,
        "passed": final_valid, "scientificVerdict": result["verdict"],
        "auditVerdict": audit.get("verdict") if audit else "AUDIT_DID_NOT_PRODUCE_OUTPUT",
        "result": {"uri": str(result_path), "sha256": sha_file(result_path), "resultHash": result["resultHash"]},
        "audit": {"uri": str(audit_path), "sha256": sha_file(audit_path), "auditHash": audit["auditHash"]} if audit else None,
        "execution": {"uri": str(execution_path), "sha256": sha_file(execution_path), "executionHash": execution["executionHash"]},
        "analysisReceipt": {"uri": str(analysis_receipt_path), "sha256": sha_file(analysis_receipt_path)},
        "executionPlan": {"uri": str(execution_plan_path), "sha256": sha_file(execution_plan_path), "executionPlanHash": plan["executionPlanHash"]},
        "preflightReceipt": {"uri": str(cli.preflight_receipt), "sha256": sha_file(cli.preflight_receipt), "receiptHash": preflight["receiptHash"]},
        "evidence": evidence, "toolHashes": tool_hashes,
        "operationCounts": {**spec["processMatrix"]}, "modelCalls": 0, "networkCalls": 0,
        "promotionBoundary": spec["decision"]["promotionBoundary"],
    }
    receipt = {**receipt_body, "receiptHash": canonical_hash(receipt_body)}
    (cli.root / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D1214H1_RUN receipt={receipt['receiptHash']} audit={receipt['auditVerdict']} verdict={receipt['scientificVerdict']} processes={len(children)}")
    if not final_valid:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
