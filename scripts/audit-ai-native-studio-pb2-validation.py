#!/usr/bin/env python3
"""Independent PB.2 receipt auditor; never imports the engine contract module."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import sys
from pathlib import Path


EXPECTED_CASES = {
    "N_REJECTED_PROPOSAL": "PROPOSAL_SCHEMA",
    "N_TAMPERED_PROPOSAL": "APPROVAL_BINDING",
    "N_UNAPPROVED_PROPOSAL": "APPROVAL_SCHEMA",
    "N_WRONG_ORDER": "INSPECTION_REQUIRED",
    "N_UNAUTHORIZED_SCOPE": "APPROVAL_SCOPE",
    "N_UNKNOWN_FIELD": "SCHEMA_ADDITIONAL_PROPERTY",
    "N_PATH_ESCAPE": "PATH_ESCAPE",
    "N_NONFINITE": "NONFINITE_NUMBER",
}


def args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--engine-source", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--freeze-contract", type=Path, required=True)
    parser.add_argument("--execution-contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def valid_self(value: dict, field: str) -> bool:
    expected = value[field]
    body = {key: item for key, item in value.items() if key != field}
    return expected == sha256(canonical(body))


def write_exclusive(path: Path, value: dict) -> None:
    payload = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        os.write(descriptor, payload)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def main() -> int:
    parsed = args()
    repository = parsed.repository_root.resolve(strict=True)
    engine = parsed.engine_source.resolve(strict=True)
    receipt = read_json(parsed.receipt.resolve(strict=True))
    freeze = read_json(parsed.freeze_contract.resolve(strict=True))
    execution = read_json(parsed.execution_contract.resolve(strict=True))
    runner_source = (repository / freeze["runner"]["uri"]).read_text(encoding="utf-8")
    contract_source = (engine / "scripts/modules/film_studio_contract.py").read_text(encoding="utf-8")
    checks = {}

    checks["receiptSelfHash"] = valid_self(receipt, "receiptHash")
    checks["receiptPass"] = receipt.get("status") == "PASS"
    checks["freezeBinding"] = receipt["freezeContract"]["sha256"] == sha256(parsed.freeze_contract.read_bytes())
    checks["executionBinding"] = receipt["executionContract"]["sha256"] == sha256(parsed.execution_contract.read_bytes())
    checks["sourceIdentity"] = receipt["engineHead"] == freeze["engineSource"]["head"]
    checks["twoExactPositives"] = [row["id"] for row in receipt["positives"]] == ["B01", "B02"]
    checks["positivePlanHashes"] = all(
        row["planHash"] == row["expectedPlanHash"] == fixture["planHash"]
        and row["status"] == "APPROVED_READY"
        and row["approvedOperation"] == "COMPILE_BUILD_PLAN"
        and row["approvedMutationScope"] == ["WRITE_BUILD_PLAN"]
        and row["filesystemExact"] is True
        and row["buildPlanWritten"] is False
        for row, fixture in zip(receipt["positives"], freeze["fixtures"], strict=True)
    )
    checks["eightExactNegatives"] = [row["id"] for row in receipt["negatives"]] == list(EXPECTED_CASES)
    checks["negativeReasonsExact"] = all(
        row["expectedReason"] == row["actualReason"] == EXPECTED_CASES[row["id"]]
        and row["passed"] is True
        and row["filesystemExact"] is True
        for row in receipt["negatives"]
    )
    zero_fields = [
        "buildPlanFilesWritten", "blenderStarts", "sceneMutations", "networkCalls",
        "shellCommandsFromProposal", "filesystemOperationsOutsideWorkAndEvidenceRoots",
        "arbitraryPythonFromProposalExecuted",
    ]
    checks["negativeCountsZero"] = all(
        all(row[field] == 0 for field in zero_fields) for row in receipt["negatives"]
    )
    total_zero_fields = [
        "proposalExecutions", "buildPlanFilesWritten", "blenderStarts", "renders",
        "sceneMutations", "networkCalls", "shellCommandsFromProposal",
        "arbitraryPythonFromProposalExecuted", "engineSourceEdits", "engineRemoteWrites",
    ]
    checks["totalCountsExact"] = receipt["counts"]["positiveInspections"] == 2
    checks["totalCountsExact"] &= receipt["counts"]["negativeCases"] == 8
    checks["totalCountsExact"] &= all(receipt["counts"][field] == 0 for field in total_zero_fields)
    checks["fixedGitProcessCount"] = receipt["counts"]["fixedGitProcesses"] == 5
    checks["resourceCeilings"] = receipt["resources"]["wallSeconds"] <= freeze["ceilings"]["maximumWallSeconds"]
    checks["resourceCeilings"] &= receipt["resources"]["workRootBytes"] <= freeze["ceilings"]["maximumWorkRootBytes"]
    runner_tree = ast.parse(runner_source)
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(runner_tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in (node.names if isinstance(node, ast.Import) else [ast.alias(name=node.module or "")])
    }
    subprocess_calls = [
        node for node in ast.walk(runner_tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "subprocess"
        and node.func.attr == "run"
    ]
    git_calls = [
        node for node in ast.walk(runner_tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "git"
    ]
    checks["runnerHasNoBlenderImport"] = "bpy" not in imports
    checks["runnerFixedChildCommandsOnly"] = len(subprocess_calls) == 1 and all(
        node.args
        and isinstance(node.args[0], ast.List)
        and all(isinstance(item, ast.Constant) and isinstance(item.value, str) for item in node.args[0].elts)
        for node in git_calls
    )
    checks["contractHasNoBpyDependency"] = "This module deliberately has no bpy dependency." in contract_source
    checks["contractRejectsDynamicAuthority"] = 'exact_security = {"networkAccess": False, "arbitraryPython": False, "sceneMutation": False}' in contract_source
    checks["contractRequiresInspection"] = 'raise ContractError("INSPECTION_REQUIRED"' in contract_source
    checks["exclusiveOutputPrimitive"] = "os.O_EXCL" in contract_source and "os.O_EXCL" in runner_source
    checks["claimCeilingExact"] = receipt["claimCeiling"] == freeze["claimCeiling"]

    passed = sum(checks.values())
    total = len(checks)
    body = {
        "schemaVersion": "bfs.aiNativeStudioPb2ValidationIndependentAudit.v0.1",
        "status": "PASS" if passed == total else "FAIL",
        "independence": "Does not import or execute film_studio_contract and does not start Blender.",
        "checks": checks,
        "counts": {
            "passed": passed,
            "total": total,
            "blenderStarts": 0,
            "renders": 0,
            "networkCalls": 0,
            "engineSourceEdits": 0,
            "engineRemoteWrites": 0,
        },
        "receipt": {"uri": str(parsed.receipt), "sha256": sha256(parsed.receipt.read_bytes()), "receiptHash": receipt["receiptHash"]},
        "claimCeiling": freeze["claimCeiling"],
    }
    body["auditHash"] = sha256(canonical(body))
    parsed.output.parent.resolve(strict=True)
    write_exclusive(parsed.output, body)
    print(f"PB2_AUDIT {body['status']} {passed}/{total} auditHash={body['auditHash']}")
    return 0 if body["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
