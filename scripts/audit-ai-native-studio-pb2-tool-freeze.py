#!/usr/bin/env python3
"""Static audit of the inert PB.2 v0.3 tool freeze; executes no proposal."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


EXPECTED_CASES = [
    "N_REJECTED_PROPOSAL",
    "N_TAMPERED_PROPOSAL",
    "N_UNAPPROVED_PROPOSAL",
    "N_WRONG_ORDER",
    "N_UNAUTHORIZED_SCOPE",
    "N_UNKNOWN_FIELD",
    "N_PATH_ESCAPE",
    "N_NONFINITE",
]


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--freeze-contract", type=Path, required=True)
    parser.add_argument("--authorization-request", type=Path, required=True)
    parser.add_argument("--engine-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def git(args: list[str], cwd: Path) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def write_exclusive(path: Path, value: dict) -> None:
    payload = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        os.write(descriptor, payload)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def imported_roots(tree: ast.AST) -> set[str]:
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def literal_expected_cases(tree: ast.Module) -> list[str] | None:
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "EXPECTED_CASES" for target in node.targets):
            value = ast.literal_eval(node.value)
            return list(value)
    return None


def main() -> int:
    parsed = arguments()
    root = parsed.repository_root.resolve(strict=True)
    freeze_path = parsed.freeze_contract.resolve(strict=True)
    request_path = parsed.authorization_request.resolve(strict=True)
    engine = parsed.engine_source.resolve(strict=True)
    freeze = read_json(freeze_path)
    request = read_json(request_path)
    state = read_json(root / "handoff/ai-native-studio-current-state.v0.1.json")
    runner_path = root / freeze["runner"]["uri"]
    auditor_path = root / freeze["independentAuditor"]["uri"]
    runner_source = runner_path.read_text(encoding="utf-8")
    auditor_source = auditor_path.read_text(encoding="utf-8")
    runner_tree = ast.parse(runner_source)
    auditor_tree = ast.parse(auditor_source)
    checks = {}

    checks["freezeStatusClosed"] = freeze["schemaVersion"] == "bfs.aiNativeStudioPb2ValidationToolFreeze.v0.3" and freeze["status"] == "FROZEN_NOT_AUTHORIZED"
    checks["requestStatusNotExecutable"] = request["status"] == "AUTHORIZATION_REQUIRED_NOT_EXECUTABLE"
    checks["requestBindsFreeze"] = request["toolFreeze"]["uri"] == freeze["self"]["uri"] and request["toolFreeze"]["sha256"] == sha256(freeze_path.read_bytes())
    checks["researchParentExact"] = git(["rev-parse", "HEAD"], root) == freeze["parentResearchCommit"]
    checks["engineHeadExact"] = git(["rev-parse", "HEAD"], engine) == freeze["engineSource"]["head"]
    checks["engineClean"] = git(["status", "--porcelain=v1"], engine) == ""
    contract_path = engine / freeze["engineSource"]["contractModuleUri"]
    checks["engineContractShaExact"] = sha256(contract_path.read_bytes()) == freeze["engineSource"]["contractModuleSha256"]
    checks["engineContractBlobExact"] = git(["rev-parse", f"HEAD:{freeze['engineSource']['contractModuleUri']}"], engine) == freeze["engineSource"]["contractModuleGitBlobOid"]
    checks["runnerShaExact"] = sha256(runner_path.read_bytes()) == freeze["runner"]["sha256"]
    checks["auditorShaExact"] = sha256(auditor_path.read_bytes()) == freeze["independentAuditor"]["sha256"]

    input_rows = []
    for record in freeze["commonInputs"] + [item for fixture in freeze["fixtures"] for item in fixture["inputs"]]:
        actual = sha256((root / record["uri"]).read_bytes())
        input_rows.append({"uri": record["uri"], "expectedSha256": record["sha256"], "actualSha256": actual, "pass": actual == record["sha256"]})
    checks["allInputHashesExact"] = all(row["pass"] for row in input_rows)

    checks["fixtureOrderExact"] = [item["id"] for item in freeze["fixtures"]] == ["B01", "B02"]
    checks["caseOrderExact"] = [item["id"] for item in freeze["negativeCases"]] == EXPECTED_CASES
    checks["runnerCaseSetExact"] = literal_expected_cases(runner_tree) == EXPECTED_CASES
    checks["zeroExecutionCeilings"] = all(
        freeze["ceilings"][key] == 0
        for key in [
            "maximumBlenderStarts", "maximumRenders", "maximumProposalExecutions",
            "maximumBuildPlanWrites", "maximumEngineSourceEdits",
            "maximumEngineRemoteWrites", "maximumNetworkCalls",
        ]
    )
    checks["freshWorkRootAbsent"] = not Path(freeze["paths"]["workRoot"]).exists()
    checks["freshEvidenceRootAbsent"] = not Path(freeze["paths"]["evidenceRoot"]).exists()
    checks["executionContractAbsent"] = not (root / "specs/ai-native-studio-pb2-validation-only-execution.v0.4.json").exists()
    checks["currentStateStillUnauthorized"] = state["phaseBPreparation"]["pb2Readiness"]["pb2FormalExecutionAuthorized"] is False and state["phaseBPreparation"]["activeCorrection"]["pb2ThroughPb7Authorized"] is False

    runner_imports = imported_roots(runner_tree)
    auditor_imports = imported_roots(auditor_tree)
    checks["runnerNoBpyOrNetworkImports"] = not ({"bpy", "socket", "urllib", "requests", "httpx"} & runner_imports)
    checks["auditorNoBpyOrNetworkImports"] = not ({"bpy", "socket", "urllib", "requests", "httpx"} & auditor_imports)
    checks["auditorDoesNotImportEngineContract"] = "film_studio_contract" not in auditor_source
    forbidden_calls = []
    for node in ast.walk(runner_tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec", "compile"}:
                forbidden_calls.append(node.func.id)
            if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id in {"os", "subprocess"} and node.func.attr in {"system", "popen", "Popen", "call", "check_call", "check_output"}:
                forbidden_calls.append(f"{node.func.value.id}.{node.func.attr}")
    checks["runnerNoDynamicExecution"] = forbidden_calls == []
    subprocess_runs = [
        node for node in ast.walk(runner_tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "subprocess"
        and node.func.attr == "run"
    ]
    checks["oneFixedSubprocessPrimitive"] = len(subprocess_runs) == 1 and '["git", *args]' in runner_source
    authority_index = runner_source.index("validate_authority(args, freeze, execution)")
    first_root_index = runner_source.index("work_root = require_fresh_absolute", authority_index)
    module_load_index = runner_source.index("contract = load_contract_module", authority_index)
    root_create_index = runner_source.index("work_root.mkdir()", authority_index)
    checks["authorityBeforeRootsAndModule"] = authority_index < first_root_index < module_load_index < root_create_index
    checks["runnerRejectsRequestSchema"] = "EXECUTION_SCHEMA = \"bfs.aiNativeStudioPb2ValidationOnlyExecution.v0.4\"" in runner_source and "AUTHORIZED_FOR_ONE_FORMAL_RUN" in runner_source
    checks["exclusiveEvidenceAndOutput"] = "os.O_EXCL" in runner_source and "os.O_EXCL" in auditor_source
    checks["stillUnauthorizedExact"] = request["requestedRun"]["blenderStarts"] == 0 and request["requestedRun"]["proposalExecutions"] == 0 and request["requestedRun"]["engineRemoteWrites"] == 0

    passed = sum(checks.values())
    total = len(checks)
    body = {
        "schemaVersion": "bfs.aiNativeStudioPb2ValidationToolFreezeAudit.v0.1",
        "status": "PASS" if passed == total else "FAIL",
        "mode": "STATIC_ONLY_NO_RUNNER_NO_PROPOSAL_NO_BLENDER",
        "freezeContract": {"uri": freeze["self"]["uri"], "sha256": sha256(freeze_path.read_bytes())},
        "authorizationRequest": {"uri": request_path.relative_to(root).as_posix(), "sha256": sha256(request_path.read_bytes())},
        "checks": checks,
        "counts": {
            "passed": passed,
            "total": total,
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
        "inputs": input_rows,
        "claimCeiling": "PASS proves only static integrity and fail-closed placement of the inert PB.2 v0.3 tools. It does not start or pass PB.2.",
    }
    body["auditHash"] = sha256(canonical(body))
    parsed.output.parent.mkdir(parents=True, exist_ok=False)
    write_exclusive(parsed.output, body)
    print(f"PB2_TOOL_FREEZE_AUDIT {body['status']} {passed}/{total} auditHash={body['auditHash']}")
    return 0 if body["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
