#!/usr/bin/env python3
"""Run the frozen six-process B52-D12.14-C2 calibration matrix."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path


SPEC_SHA256 = "e123b80fdba40c7e7e396e1aad149573e1e123c57198a21fa8af944320d7e4c3"
TARGETS = (
    "TOP_MISSING_BOTTOM_AVAILABLE",
    "BOTTOM_MISSING_TOP_AVAILABLE",
    "NEITHER_HORIZONTAL_AVAILABLE",
)


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(payload).hexdigest()


def self_ok(value: dict, field: str) -> bool:
    return value.get(field) == canonical_hash({key: row for key, row in value.items() if key != field})


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    return parser.parse_args()


def git_value(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, text=True, capture_output=True).stdout.strip()


def filtered_environment(spec: dict) -> dict[str, str]:
    allowlist = set(spec["runtime"]["environmentAllowlist"])
    return {key: value for key, value in os.environ.items() if key in allowlist}


def run_child(command: list[str], env: dict[str, str], label: str) -> dict:
    started = time.monotonic()
    process = subprocess.Popen(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    stdout, stderr = process.communicate()
    record = {
        "label": label, "pid": process.pid, "exitCode": process.returncode,
        "command": command, "stdout": stdout, "stderr": stderr,
        "elapsedSeconds": round(time.monotonic() - started, 6),
    }
    if process.returncode != 0:
        raise RuntimeError(f"D12.14-C2 child failed {label}: {stderr[-4000:]}")
    return record


def normalized_selected(report: dict):
    rows = []
    for row in report["selected"]:
        if row["candidateId"] is None:
            rows.append({"target": row["target"], "candidateId": None})
        else:
            rows.append({
                "target": row["target"], "candidateId": row["candidateId"], "ordinal": row["ordinal"],
                "resolution": row["resolution"], "counts": row["counts"],
                "currentLocationQ6": [round(float(value) * 1_000_000) for value in row["currentLocation"]],
                "currentRotationQ12": [round(float(value) * 1_000_000_000_000) for value in row["currentRotationEuler"]],
                "previousLocationQ6": [round(float(value) * 1_000_000) for value in row["previousLocation"]],
                "previousRotationQ12": [round(float(value) * 1_000_000_000_000) for value in row["previousRotationEuler"]],
                "neighborhoodMinimumTargetWitnesses": row["neighborhoodMinimumTargetWitnesses"],
            })
    return rows


def main():
    args = parse_args()
    repo = Path.cwd().resolve()
    spec_path = args.spec.resolve()
    root = args.root.resolve()
    if root.exists() or sha_file(spec_path) != SPEC_SHA256:
        raise RuntimeError("D12.14-C2 formal root freshness or spec identity failure")
    spec = json.loads(spec_path.read_text())
    if root != (repo / spec["freshness"]["formalRoot"]).resolve():
        raise RuntimeError("D12.14-C2 formal root path mismatch")
    tool_paths = [Path(uri) for uri in spec["freshness"]["newToolPaths"]]
    for path in [Path("specs/blender-material-owner-rigid-directional-calibration.v0.1.json"), *tool_paths]:
        subprocess.run(["git", "ls-files", "--error-unmatch", str(path)], check=True, stdout=subprocess.DEVNULL)
        if subprocess.run(["git", "diff", "--quiet", "HEAD", "--", str(path)]).returncode != 0:
            raise RuntimeError(f"D12.14-C2 uncommitted frozen path: {path}")
    parent_ok = (
        sha_file(Path(spec["parents"]["failedCalibrationSpec"]["uri"])) == spec["parents"]["failedCalibrationSpec"]["sha256"]
        and sha_file(Path(spec["parents"]["failedCalibrationReport"]["uri"])) == spec["parents"]["failedCalibrationReport"]["sha256"]
        and sha_file(Path(spec["parents"]["rejectedHoldoutResult"]["uri"])) == spec["parents"]["rejectedHoldoutResult"]["sha256"]
        and git_value("rev-parse", f"HEAD:{spec['parents']['rejectedHoldoutFormalRoot']['uri']}") == spec["parents"]["rejectedHoldoutFormalRoot"]["gitTree"]
    )
    if not parent_ok:
        raise RuntimeError("D12.14-C2 parent identity failure")
    runtime = spec["runtime"]
    for key in ("blender", "python", "node"):
        if sha_file(Path(runtime[key]["executable"])) != runtime[key]["sha256"]:
            raise RuntimeError(f"D12.14-C2 {key} executable identity failure")
    free_before = shutil.disk_usage(repo).free
    if free_before - spec["diskAdmission"]["projectedMaximumWriteBytes"] < spec["diskAdmission"]["minimumReserveBytesAfterWrite"]:
        raise RuntimeError("D12.14-C2 disk admission failure")
    tool_hashes = {str(path): sha_file(path) for path in tool_paths}
    head_commit = git_value("rev-parse", "HEAD")
    env = filtered_environment(spec)
    python = runtime["python"]["executable"]
    node = runtime["node"]["executable"]
    blender = runtime["blender"]["executable"]
    python_output = root / "oracles/python"
    node_output = root / "oracles/node"
    commands = [
        {"label": "python-oracle", "command": [python, str(repo / tool_paths[1]), "--spec", str(spec_path), "--output", str(python_output)]},
        {"label": "node-oracle", "command": [node, str(repo / tool_paths[2]), "--spec", str(spec_path), "--output", str(node_output)]},
    ]
    for target in TARGETS:
        commands.append({
            "label": f"blender-probe-{target}",
            "command": [
                blender, *runtime["blender"]["launchFlags"], "--python", str(repo / tool_paths[0]), "--",
                "--spec", str(spec_path), "--oracle-report", str(python_output / "report.json"),
                "--target", target, "--output", str(root / "blender-probes" / target / "report.json"),
            ],
        })
    audit_command = [python, str(repo / tool_paths[3]), "--spec", str(spec_path), "--root", str(root), "--output", str(root / "audit.json")]
    plan_body = {
        "schemaVersion": "bfs.blenderMaterialOwnerRigidDirectionalCalibrationExecutionPlan.v0.1",
        "experimentId": spec["experimentId"], "specSha256": SPEC_SHA256, "toolFreezeCommit": head_commit,
        "toolHashes": tool_hashes, "commands": commands + [{"label": "independent-audit", "command": audit_command}],
        "expectedUniqueChildProcesses": spec["processMatrix"]["totalUniqueChildProcesses"],
        "operationCounts": {"blenderRenderCalls": 0, "cyclesRayRenders": 0, "modelCalls": 0, "networkCalls": 0},
    }
    plan = {**plan_body, "planHash": canonical_hash(plan_body)}
    root.mkdir(parents=True)
    (root / "execution-plan.json").write_text(json.dumps(plan, indent=2, sort_keys=True, allow_nan=False) + "\n")
    child_records = [run_child(row["command"], env, row["label"]) for row in commands]
    pids = [row["pid"] for row in child_records]
    if len(set(pids)) != len(pids):
        raise RuntimeError("D12.14-C2 duplicate pre-audit PID")
    python_report = json.loads((python_output / "report.json").read_text())
    node_report = json.loads((node_output / "report.json").read_text())
    python_candidates = python_output / "candidates.bin"
    node_candidates = node_output / "candidates.bin"
    candidate_exact = python_candidates.read_bytes() == node_candidates.read_bytes()
    selected_exact = normalized_selected(python_report) == normalized_selected(node_report)
    masks_exact = True
    for row in python_report["selected"]:
        if row["candidateId"] is None:
            continue
        for mask_name in python_report["selectedMasks"][row["target"]]:
            masks_exact = masks_exact and (python_output / "selected" / row["target"] / f"{mask_name}.u8").read_bytes() == (node_output / "selected" / row["target"] / f"{mask_name}.u8").read_bytes()
    probes = [json.loads((root / "blender-probes" / target / "report.json").read_text()) for target in TARGETS]
    selected_ids = {row["target"]: row["candidateId"] for row in python_report["selected"]}
    probe_bindings = {row["target"]: row["candidateId"] for row in probes} == selected_ids
    rigid_probe = all(row["meshIdentityStable"] and row["meshLocalVertexHashStable"] and row["scaleStable"] for row in probes if row["selectionPresent"])
    projection_probe = all(row["maximumProjectionAbsoluteErrorPixels"] <= spec["blenderProbeContract"]["projectionMaximumAbsoluteErrorPixels"] and row["maximumRnaTransformAbsoluteError"] <= spec["blenderProbeContract"]["rnaTransformMaximumAbsoluteError"] for row in probes if row["selectionPresent"])
    exr_count = sum(1 for path in root.rglob("*") if path.is_file() and path.suffix.lower() == ".exr")
    zero_operations = exr_count == 0 and all(not row["renderResultPresent"] and row["operationCounts"]["blenderRenderCalls"] == 0 and row["operationCounts"]["cyclesRayRenders"] == 0 and row["operationCounts"]["modelCalls"] == 0 and row["operationCounts"]["networkCalls"] == 0 for row in probes)
    selected_all = all(selected_ids[target] is not None for target in TARGETS)
    evidence_checks = [
        {"name": "PARENT_AND_RUNTIME_IDENTITIES", "passed": parent_ok},
        {"name": "TOOL_FREEZE_AND_PROCESS_IDENTITIES", "passed": len(child_records) == 5 and len(set(pids)) == 5 and all(row["exitCode"] == 0 for row in child_records)},
        {"name": "PYTHON_NODE_CANDIDATE_BYTES", "passed": candidate_exact and python_report["candidateCount"] == node_report["candidateCount"] == spec["searchSpace"]["totalCandidateCount"]},
        {"name": "PYTHON_NODE_SELECTION_AND_MASKS", "passed": selected_exact and masks_exact},
        {"name": "BLENDER_PROBE_BINDINGS", "passed": probe_bindings},
        {"name": "SAME_RIGID_MESH_AND_SCALE", "passed": rigid_probe},
        {"name": "BLENDER_PROJECTION_AND_RNA", "passed": projection_probe},
        {"name": "ZERO_RENDER_EXR_MODEL_NETWORK", "passed": zero_operations},
    ]
    if not all(row["passed"] for row in evidence_checks):
        raise RuntimeError(f"D12.14-C2 runner evidence gate failed: {evidence_checks}")
    verdict = spec["decision"]["derivedVerdict"] if selected_all else spec["decision"]["notDerivedVerdict"]
    operation_counts = {"blenderProcesses": 3, "blenderRenderCalls": 0, "cyclesRayRenders": 0, "exrFiles": exr_count, "modelCalls": 0, "networkCalls": 0}
    result_body = {
        "schemaVersion": "bfs.blenderMaterialOwnerRigidDirectionalCalibrationResult.v0.1",
        "experimentId": spec["experimentId"], "specSha256": SPEC_SHA256,
        "toolFreezeCommit": head_commit, "toolHashes": tool_hashes,
        "parentTrees": {spec["parents"]["rejectedHoldoutFormalRoot"]["uri"]: spec["parents"]["rejectedHoldoutFormalRoot"]["gitTree"]},
        "executionPlanHash": plan["planHash"], "candidateTableSha256": sha_file(python_candidates),
        "selected": python_report["selected"],
        "probeSummary": [{
            "target": row["target"], "candidateId": row["candidateId"], "meshIdentityStable": row["meshIdentityStable"],
            "scaleStable": row["scaleStable"], "maximumProjectionAbsoluteErrorPixels": row["maximumProjectionAbsoluteErrorPixels"],
            "maximumRnaTransformAbsoluteError": row["maximumRnaTransformAbsoluteError"],
        } for row in probes],
        "evidenceChecks": evidence_checks, "evidenceChecksPassed": sum(int(row["passed"]) for row in evidence_checks), "evidenceChecksTotal": len(evidence_checks),
        "childProcesses": [{key: value for key, value in row.items() if key not in {"stdout", "stderr"}} for row in child_records],
        "operationCounts": operation_counts, "passed": selected_all, "verdict": verdict,
        "promotionBoundary": spec["decision"]["promotionBoundary"], "nonClaims": spec["nonClaims"],
    }
    result = {**result_body, "resultHash": canonical_hash(result_body)}
    (root / "results.json").write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    audit_record = run_child(audit_command, env, "independent-audit")
    audit = json.loads((root / "audit.json").read_text())
    if not self_ok(audit, "auditHash") or not audit["passed"] or audit_record["pid"] in pids:
        raise RuntimeError("D12.14-C2 audit evidence gate failed")
    all_records = [*child_records, audit_record]
    execution_body = {
        "schemaVersion": "bfs.blenderMaterialOwnerRigidDirectionalCalibrationExecution.v0.1",
        "experimentId": spec["experimentId"], "specSha256": SPEC_SHA256, "toolFreezeCommit": head_commit,
        "executionPlanHash": plan["planHash"], "processes": all_records,
        "allChildrenUniquePid": len({row["pid"] for row in all_records}) == len(all_records),
        "allChildrenExitZero": all(row["exitCode"] == 0 for row in all_records),
        "operationCounts": operation_counts, "freeBytesBefore": free_before, "freeBytesAfter": shutil.disk_usage(repo).free,
    }
    execution = {**execution_body, "executionHash": canonical_hash(execution_body)}
    (root / "execution.json").write_text(json.dumps(execution, indent=2, sort_keys=True, allow_nan=False) + "\n")
    receipt_body = {
        "schemaVersion": "bfs.blenderMaterialOwnerRigidDirectionalCalibrationReceipt.v0.1",
        "experimentId": spec["experimentId"], "specSha256": SPEC_SHA256, "toolFreezeCommit": head_commit,
        "result": {"uri": str(root / "results.json"), "sha256": sha_file(root / "results.json"), "resultHash": result["resultHash"], "verdict": result["verdict"]},
        "audit": {"uri": str(root / "audit.json"), "sha256": sha_file(root / "audit.json"), "auditHash": audit["auditHash"], "verdict": audit["verdict"]},
        "execution": {"uri": str(root / "execution.json"), "sha256": sha_file(root / "execution.json"), "executionHash": execution["executionHash"]},
        "plan": {"uri": str(root / "execution-plan.json"), "sha256": sha_file(root / "execution-plan.json"), "planHash": plan["planHash"]},
        "valid": audit["passed"] and execution["allChildrenUniquePid"] and execution["allChildrenExitZero"],
    }
    receipt = {**receipt_body, "receiptHash": canonical_hash(receipt_body)}
    (root / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n")
    if not receipt["valid"]:
        raise RuntimeError("D12.14-C2 receipt invalid")
    print(f"BFS_B52_D1214C2_RUN_OK verdict={verdict} processes={len(all_records)} audit={audit['attacksPassed']}/{audit['attacksTotal']}")


if __name__ == "__main__":
    main()
