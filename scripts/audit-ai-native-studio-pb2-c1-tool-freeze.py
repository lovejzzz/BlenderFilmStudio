#!/usr/bin/env python3
"""Static audit of the PB.2 C1 non-circular tool correction."""

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
    parser.add_argument("--correction-contract", type=Path, required=True)
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


def imports(tree: ast.AST) -> set[str]:
    result = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import): result.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module: result.add(node.module.split(".")[0])
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
    freeze_path = root / correction["baseToolFreeze"]["uri"]
    runner_path = root / correction["runner"]["uri"]
    base_path = root / correction["baseRunner"]["uri"]
    auditor_path = root / correction["independentAuditor"]["uri"]
    runner_source = runner_path.read_text(encoding="utf-8")
    base_source = base_path.read_text(encoding="utf-8")
    auditor_source = auditor_path.read_text(encoding="utf-8")
    runner_tree = ast.parse(runner_source)
    auditor_tree = ast.parse(auditor_source)
    checks = {}

    checks["statusNotAuthority"] = correction["status"] == "FROZEN_CORRECTION_NOT_AUTHORITY"
    checks["parentCommitExact"] = git(["rev-parse", "HEAD"], root) == correction["parentResearchCommit"]
    checks["baseFreezeExact"] = sha256(freeze_path.read_bytes()) == correction["baseToolFreeze"]["sha256"]
    checks["baseRunnerExact"] = sha256(base_path.read_bytes()) == correction["baseRunner"]["sha256"]
    checks["runnerExact"] = sha256(runner_path.read_bytes()) == correction["runner"]["sha256"]
    checks["auditorExact"] = sha256(auditor_path.read_bytes()) == correction["independentAuditor"]["sha256"]
    checks["executionContractAbsent"] = not (root / correction["executionContract"]["uri"]).exists()
    freeze = read_json(freeze_path)
    checks["formalRootsAbsent"] = not Path(freeze["paths"]["workRoot"]).exists() and not Path(freeze["paths"]["evidenceRoot"]).exists()
    checks["caseOrderExact"] = correction["negativeCases"] == [item["id"] for item in freeze["negativeCases"]]
    checks["scopeStillZero"] = all(
        correction["scopeUnchanged"][key] == 0
        for key in ["blenderStarts", "renders", "proposalExecutions", "buildPlanWrites", "sceneMutations", "engineSourceEdits", "engineRemoteWrites", "networkCalls"]
    )
    checks["noBpyOrNetworkImports"] = not ({"bpy", "socket", "urllib", "requests", "httpx"} & (imports(runner_tree) | imports(auditor_tree)))
    checks["auditorDoesNotImportEngineContract"] = "film_studio_contract" not in imports(auditor_tree)
    checks["runnerRequiresV06Authority"] = 'EXECUTION_SCHEMA = "bfs.aiNativeStudioPb2ValidationOnlyExecutionC2.v0.6"' in runner_source and 'EXECUTION_STATUS = "AUTHORIZED_FOR_ONE_FORMAL_RUN"' in runner_source
    authority = runner_source.index("validate_authority(parsed, root, freeze, correction, execution)")
    module_load = runner_source.index("base = load_base_runner", authority)
    root_check = runner_source.index("work_root = base.require_fresh_absolute", module_load)
    root_create = runner_source.index("work_root.mkdir()", root_check)
    checks["authorityAndCommitBeforeRoots"] = authority < module_load < root_check < root_create
    checks["nonCircularChecksPresent"] = all(token in runner_source for token in [
        'git(["rev-parse", "HEAD^"]', 'git(["show", f"HEAD:{execution_uri}"]', '"executionCommit": head', 'git(["status", "--porcelain=v1"], root)',
    ]) and 'execution["executionCommit"]' not in runner_source
    checks["auditorRecomputesCommitBinding"] = all(token in auditor_source for token in [
        'git(["show", f"{receipt[\'executionCommit\']}:{execution_uri}"]', 'git(["rev-parse", f"{receipt[\'executionCommit\']}^"]',
    ])
    checks["exclusiveEvidence"] = "base.write_exclusive" in runner_source and "os.O_EXCL" in base_source and "os.O_EXCL" in auditor_source

    passed = sum(checks.values())
    total = len(checks)
    body = {
        "schemaVersion": "bfs.aiNativeStudioPb2ValidationC1ToolAudit.v0.1",
        "status": "PASS" if passed == total else "FAIL",
        "mode": "STATIC_C1_TOOL_ONLY_NO_RUNNER_NO_PROPOSAL_NO_BLENDER",
        "correctionContract": {"uri": correction_path.relative_to(root).as_posix(), "sha256": sha256(correction_path.read_bytes())},
        "checks": checks,
        "counts": {"passed": passed, "total": total, "runnerStarts": 0, "proposalInspections": 0, "proposalExecutions": 0, "blenderStarts": 0, "renders": 0, "buildPlanWrites": 0, "engineSourceEdits": 0, "engineRemoteWrites": 0, "networkCalls": 0},
        "claimCeiling": "PASS proves only static integrity of the non-circular C1 correction. It grants no execution authority and does not start PB.2.",
    }
    body["auditHash"] = sha256(canonical(body))
    parsed.output.parent.mkdir(parents=True, exist_ok=False)
    write_exclusive(parsed.output, body)
    print(f"PB2_C1_TOOL_AUDIT {body['status']} {passed}/{total} auditHash={body['auditHash']}")
    return 0 if body["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
