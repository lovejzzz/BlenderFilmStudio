#!/usr/bin/env python3
"""Static preflight for the non-executable PB.2 v0.4 template."""

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


def args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def git(arguments: list[str], cwd: Path) -> str:
    return subprocess.run(["git", *arguments], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


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
    template_path = parsed.template.resolve(strict=True)
    template = read_json(template_path)
    freeze_path = root / template["toolFreeze"]["uri"]
    request_path = root / template["authorizationRequest"]["uri"]
    freeze = read_json(freeze_path)
    runner_path = root / freeze["runner"]["uri"]
    auditor_path = root / freeze["independentAuditor"]["uri"]
    runner_source = runner_path.read_text(encoding="utf-8")
    runner_tree = ast.parse(runner_source)
    checks = {}

    checks["templateSchemaMatchesFutureExecution"] = template["schemaVersion"] == "bfs.aiNativeStudioPb2ValidationOnlyExecution.v0.4"
    checks["templateStatusRejected"] = template["status"] == "DRAFT_NON_EXECUTABLE_AUTHORIZATION_MISSING" and template["templateOnly"] is True
    checks["authorizationFieldsEmpty"] = template["authorization"] == {
        "exactUserText": None,
        "exactUserTextSha256": None,
        "authorizedAtUtc": None,
        "explicitPb2ScopePresent": False,
    }
    checks["researchCommitEmpty"] = template["researchCommit"] is None
    checks["freezeFileExact"] = sha256(freeze_path.read_bytes()) == template["toolFreeze"]["sha256"]
    checks["freezeCommitExact"] = git(["rev-parse", template["toolFreeze"]["commit"]], root) == template["toolFreeze"]["commit"]
    frozen_bytes = subprocess.run(
        ["git", "show", f"{template['toolFreeze']['commit']}:{template['toolFreeze']['uri']}"],
        cwd=root, check=True, capture_output=True,
    ).stdout
    checks["freezeAtCommitExact"] = sha256(frozen_bytes) == template["toolFreeze"]["sha256"]
    checks["requestFileExact"] = sha256(request_path.read_bytes()) == template["authorizationRequest"]["sha256"]
    checks["runnerFileExact"] = sha256(runner_path.read_bytes()) == template["runnerSha256"] == freeze["runner"]["sha256"]
    checks["auditorFileExact"] = sha256(auditor_path.read_bytes()) == template["auditorSha256"] == freeze["independentAuditor"]["sha256"]
    checks["caseOrderExact"] = template["authorizedRun"]["negativeCases"] == EXPECTED_CASES
    checks["zeroRunCounts"] = all(
        template["authorizedRun"][key] == 0
        for key in ["blenderStarts", "renders", "proposalExecutions", "engineSourceEdits", "engineRemoteWrites", "networkCalls"]
    )
    checks["pathsEqualFreeze"] = all(
        template["authorizedRun"][key] == freeze["paths"][key]
        for key in ["repositoryRoot", "engineSource", "workRoot", "evidenceRoot"]
    )
    checks["stillUnauthorizedExact"] = template["stillUnauthorized"] == freeze["stillUnauthorized"]
    checks["formalExecutionContractAbsent"] = not (root / "specs/ai-native-studio-pb2-validation-only-execution.v0.4.json").exists()
    checks["formalWorkRootAbsent"] = not Path(freeze["paths"]["workRoot"]).exists()
    checks["formalEvidenceRootAbsent"] = not Path(freeze["paths"]["evidenceRoot"]).exists()

    runner_argv = template["commandsAfterAuthorization"]["runnerArgv"]
    auditor_argv = template["commandsAfterAuthorization"]["auditorArgv"]
    checks["runnerArgvFixed"] = runner_argv[:2] == ["python3", freeze["runner"]["uri"]] and len(runner_argv) == 14
    checks["auditorArgvFixed"] = auditor_argv[:2] == ["python3", freeze["independentAuditor"]["uri"]] and len(auditor_argv) == 14
    checks["executionPathOnlyInArgv"] = runner_argv[-1].endswith("specs/ai-native-studio-pb2-validation-only-execution.v0.4.json") and auditor_argv[-3].endswith("specs/ai-native-studio-pb2-validation-only-execution.v0.4.json")
    assignments = {
        target.id: ast.literal_eval(node.value)
        for node in runner_tree.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name) and target.id in {"EXECUTION_SCHEMA", "EXECUTION_STATUS"}
    }
    checks["runnerRequiresAuthorizedStatus"] = assignments == {
        "EXECUTION_SCHEMA": "bfs.aiNativeStudioPb2ValidationOnlyExecution.v0.4",
        "EXECUTION_STATUS": "AUTHORIZED_FOR_ONE_FORMAL_RUN",
    }
    authority_index = runner_source.index("validate_authority(args, freeze, execution)")
    checks["runnerChecksBeforeFreshRoots"] = authority_index < runner_source.index("work_root = require_fresh_absolute", authority_index)
    checks["conversionRequiresNewFileAndCommit"] = len(template["conversionRequirements"]) == 7 and "never rename or edit the template in place" in template["conversionRequirements"][0]

    passed = sum(checks.values())
    total = len(checks)
    body = {
        "schemaVersion": "bfs.aiNativeStudioPb2ExecutionTemplatePreflight.v0.1",
        "status": "PASS" if passed == total else "FAIL",
        "mode": "STATIC_TEMPLATE_ONLY_RUNNER_NOT_INVOKED",
        "template": {"uri": template_path.relative_to(root).as_posix(), "sha256": sha256(template_path.read_bytes())},
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
        "claimCeiling": template["claimCeiling"],
    }
    body["preflightHash"] = sha256(canonical(body))
    parsed.output.parent.mkdir(parents=True, exist_ok=False)
    write_exclusive(parsed.output, body)
    print(f"PB2_EXECUTION_TEMPLATE_PREFLIGHT {body['status']} {passed}/{total} preflightHash={body['preflightHash']}")
    return 0 if body["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
