#!/usr/bin/env python3
"""Independent auditor for the non-circular PB.2 C1 receipt."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


def args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--engine-source", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--freeze-contract", type=Path, required=True)
    parser.add_argument("--correction-contract", type=Path, required=True)
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


def git(arguments: list[str], cwd: Path, binary: bool = False):
    result = subprocess.run(["git", *arguments], cwd=cwd, check=True, capture_output=True)
    return result.stdout if binary else result.stdout.decode().strip()


def main() -> int:
    parsed = args()
    root = parsed.repository_root.resolve(strict=True)
    engine = parsed.engine_source.resolve(strict=True)
    receipt = read_json(parsed.receipt.resolve(strict=True))
    freeze = read_json(parsed.freeze_contract.resolve(strict=True))
    correction = read_json(parsed.correction_contract.resolve(strict=True))
    execution = read_json(parsed.execution_contract.resolve(strict=True))
    runner_path = root / correction["runner"]["uri"]
    base_path = root / correction["baseRunner"]["uri"]
    runner_source = runner_path.read_text(encoding="utf-8")
    base_source = base_path.read_text(encoding="utf-8")
    contract_source = (engine / freeze["engineSource"]["contractModuleUri"]).read_text(encoding="utf-8")
    checks = {}

    checks["receiptSelfHash"] = valid_self(receipt, "receiptHash")
    checks["receiptPass"] = receipt["status"] == "PASS"
    checks["baseFreezeBinding"] = receipt["baseToolFreeze"]["sha256"] == sha256(parsed.freeze_contract.read_bytes())
    checks["correctionBinding"] = receipt["toolCorrection"]["sha256"] == sha256(parsed.correction_contract.read_bytes())
    checks["executionBinding"] = receipt["executionContract"]["sha256"] == sha256(parsed.execution_contract.read_bytes())
    execution_uri = receipt["executionContract"]["uri"]
    committed_execution = git(["show", f"{receipt['executionCommit']}:{execution_uri}"], root, binary=True)
    committed_parent = git(["rev-parse", f"{receipt['executionCommit']}^"], root)
    checks["commitBindingNonCircular"] = committed_execution == parsed.execution_contract.read_bytes()
    checks["commitBindingNonCircular"] &= committed_parent == receipt["executionParentResearchCommit"] == execution["executionParentResearchCommit"]
    checks["sourceIdentity"] = receipt["engineHead"] == freeze["engineSource"]["head"]
    checks["twoExactPositives"] = [row["id"] for row in receipt["positives"]] == ["B01", "B02"]
    checks["positiveExact"] = all(
        row["planHash"] == row["expectedPlanHash"] == fixture["planHash"]
        and row["status"] == "APPROVED_READY" and row["approvedOperation"] == "COMPILE_BUILD_PLAN"
        and row["approvedMutationScope"] == ["WRITE_BUILD_PLAN"] and row["filesystemExact"] is True
        and row["buildPlanWritten"] is False
        for row, fixture in zip(receipt["positives"], freeze["fixtures"], strict=True)
    )
    reasons = dict(correction["negativeReasons"])
    checks["eightExactNegatives"] = [row["id"] for row in receipt["negatives"]] == correction["negativeCases"]
    checks["negativeExact"] = all(
        row["expectedReason"] == row["actualReason"] == reasons[row["id"]]
        and row["passed"] is True and row["filesystemExact"] is True
        for row in receipt["negatives"]
    )
    negative_zero = ["buildPlanFilesWritten", "blenderStarts", "sceneMutations", "networkCalls", "shellCommandsFromProposal", "filesystemOperationsOutsideWorkAndEvidenceRoots", "arbitraryPythonFromProposalExecuted"]
    checks["negativeCountsZero"] = all(all(row[key] == 0 for key in negative_zero) for row in receipt["negatives"])
    total_zero = ["proposalExecutions", "buildPlanFilesWritten", "blenderStarts", "renders", "sceneMutations", "networkCalls", "shellCommandsFromProposal", "arbitraryPythonFromProposalExecuted", "engineSourceEdits", "engineRemoteWrites"]
    checks["totalCountsExact"] = receipt["counts"]["positiveInspections"] == 2 and receipt["counts"]["negativeCases"] == 8 and all(receipt["counts"][key] == 0 for key in total_zero)
    checks["fixedGitCount"] = receipt["counts"]["fixedGitProcesses"] == 8
    checks["resourcesWithinCeiling"] = receipt["resources"]["wallSeconds"] <= freeze["ceilings"]["maximumWallSeconds"] and receipt["resources"]["workRootBytes"] <= freeze["ceilings"]["maximumWorkRootBytes"]
    checks["runnerSourcesExact"] = sha256(runner_path.read_bytes()) == correction["runner"]["sha256"] and sha256(base_path.read_bytes()) == correction["baseRunner"]["sha256"]
    imports = set()
    for source in (runner_source, base_source):
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import): imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module: imports.add(node.module.split(".")[0])
    checks["noBpyOrNetworkImports"] = not ({"bpy", "socket", "urllib", "requests", "httpx"} & imports)
    checks["contractRejectsDynamicAuthority"] = 'exact_security = {"networkAccess": False, "arbitraryPython": False, "sceneMutation": False}' in contract_source and 'raise ContractError("INSPECTION_REQUIRED"' in contract_source
    checks["claimCeilingExact"] = receipt["claimCeiling"] == correction["claimCeiling"]

    passed = sum(checks.values())
    total = len(checks)
    body = {
        "schemaVersion": "bfs.aiNativeStudioPb2ValidationIndependentAuditC2.v0.3",
        "status": "PASS" if passed == total else "FAIL",
        "independence": "Does not import or execute film_studio_contract and does not start Blender.",
        "checks": checks,
        "counts": {"passed": passed, "total": total, "blenderStarts": 0, "renders": 0, "networkCalls": 0, "engineSourceEdits": 0, "engineRemoteWrites": 0},
        "receipt": {"uri": str(parsed.receipt), "sha256": sha256(parsed.receipt.read_bytes()), "receiptHash": receipt["receiptHash"]},
        "claimCeiling": correction["claimCeiling"],
    }
    body["auditHash"] = sha256(canonical(body))
    write_exclusive(parsed.output, body)
    print(f"PB2_AUDIT_C2 {body['status']} {passed}/{total} auditHash={body['auditHash']}")
    return 0 if body["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
