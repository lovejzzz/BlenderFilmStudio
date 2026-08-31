#!/usr/bin/env python3
"""C1 correction for one overbroad PB.2 tool-freeze audit check."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import sys
from pathlib import Path


def args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--correction-contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def imported_modules(tree: ast.AST) -> set[str]:
    result = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.add(node.module)
    return result


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
    root = parsed.repository_root.resolve(strict=True)
    correction_path = parsed.correction_contract.resolve(strict=True)
    correction = read_json(correction_path)
    retained_path = root / correction["retainedAttempt01"]["uri"]
    retained = read_json(retained_path)
    freeze_path = root / correction["toolFreeze"]["uri"]
    freeze = read_json(freeze_path)
    auditor_path = root / freeze["independentAuditor"]["uri"]
    auditor_tree = ast.parse(auditor_path.read_text(encoding="utf-8"))
    imports = imported_modules(auditor_tree)
    checks = {}

    checks["correctionStatusClosed"] = correction["status"] == "PREREGISTERED_STATIC_AUDIT_CORRECTION_NO_PB2_EXECUTION"
    checks["toolFreezeExact"] = sha256(freeze_path.read_bytes()) == correction["toolFreeze"]["sha256"]
    checks["retainedFailureFileExact"] = sha256(retained_path.read_bytes()) == correction["retainedAttempt01"]["fileSha256"]
    checks["retainedFailureSelfExact"] = retained["auditHash"] == correction["retainedAttempt01"]["auditHash"]
    checks["retainedFailureShapeExact"] = retained["status"] == "FAIL" and retained["counts"]["passed"] == 27 and retained["counts"]["total"] == 28
    checks["retainedOnlyFailedCheckExact"] = [key for key, value in retained["checks"].items() if not value] == ["auditorDoesNotImportEngineContract"]
    checks["retainedZeroExecutionCounts"] = all(
        retained["counts"][key] == 0
        for key in [
            "runnerStarts", "proposalInspections", "proposalExecutions", "blenderStarts",
            "renders", "buildPlanWrites", "engineSourceEdits", "engineRemoteWrites", "networkCalls",
        ]
    )
    checks["astShowsNoEngineContractImport"] = not any(
        module == "film_studio_contract" or module.endswith(".film_studio_contract")
        for module in imports
    )
    checks["formalAuditorStillExact"] = sha256(auditor_path.read_bytes()) == freeze["independentAuditor"]["sha256"]
    checks["freshFormalRootsRemainAbsent"] = not Path(freeze["paths"]["workRoot"]).exists() and not Path(freeze["paths"]["evidenceRoot"]).exists()

    passed = sum(checks.values())
    total = len(checks)
    body = {
        "schemaVersion": "bfs.aiNativeStudioPb2ValidationToolFreezeAuditC1.v0.1",
        "status": "PASS" if passed == total else "FAIL",
        "mode": "STATIC_C1_ONLY_NO_RUNNER_NO_PROPOSAL_NO_BLENDER",
        "correctionContract": {"uri": correction_path.relative_to(root).as_posix(), "sha256": sha256(correction_path.read_bytes())},
        "retainedAttempt01": correction["retainedAttempt01"],
        "checks": checks,
        "counts": {
            "passed": passed,
            "total": total,
            "combinedPassed": 28 if passed == total else 27,
            "combinedTotal": 28,
            "runnerStarts": 0,
            "proposalInspections": 0,
            "proposalExecutions": 0,
            "blenderStarts": 0,
            "renders": 0,
            "buildPlanWrites": 0,
            "engineSourceEdits": 0,
            "engineRemoteWrites": 0,
            "networkCalls": 0,
        },
        "observation": {
            "formalAuditorImportedModules": sorted(imports),
            "filmStudioContractImported": False,
            "sourceFilenameMayBeReadAsData": True,
        },
        "claimCeiling": correction["claimCeiling"],
    }
    body["auditHash"] = sha256(canonical(body))
    parsed.output.parent.mkdir(parents=True, exist_ok=False)
    write_exclusive(parsed.output, body)
    print(f"PB2_TOOL_FREEZE_AUDIT_C1 {body['status']} {passed}/{total} combined={body['counts']['combinedPassed']}/28 auditHash={body['auditHash']}")
    return 0 if body["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
