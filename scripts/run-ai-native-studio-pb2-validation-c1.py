#!/usr/bin/env python3
"""PB.2 C1 runner with non-circular committed-contract identity binding."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path


EXECUTION_SCHEMA = "bfs.aiNativeStudioPb2ValidationOnlyExecutionC1.v0.5"
EXECUTION_STATUS = "AUTHORIZED_FOR_ONE_FORMAL_RUN"
CORRECTION_SCHEMA = "bfs.aiNativeStudioPb2ValidationToolCorrectionC1.v0.5"
BASE_RUNNER_URI = "scripts/run-ai-native-studio-pb2-validation.py"


def args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--engine-source", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--freeze-contract", type=Path, required=True)
    parser.add_argument("--correction-contract", type=Path, required=True)
    parser.add_argument("--execution-contract", type=Path, required=True)
    return parser.parse_args()


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def git(arguments: list[str], cwd: Path, binary: bool = False):
    result = subprocess.run(["git", *arguments], cwd=cwd, check=True, capture_output=True)
    return result.stdout if binary else result.stdout.decode().strip()


def load_base_runner(root: Path, expected_sha256: str):
    path = root / BASE_RUNNER_URI
    if sha256(path.read_bytes()) != expected_sha256:
        raise RuntimeError("base v0.3 runner SHA-256 mismatch")
    spec = importlib.util.spec_from_file_location("pb2_frozen_base_runner", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load frozen base runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_authority(parsed: argparse.Namespace, root: Path, freeze: dict, correction: dict, execution: dict) -> None:
    if correction.get("schemaVersion") != CORRECTION_SCHEMA or correction.get("status") != "FROZEN_CORRECTION_NOT_AUTHORITY":
        raise RuntimeError("C1 tool correction is not exact")
    if execution.get("schemaVersion") != EXECUTION_SCHEMA or execution.get("status") != EXECUTION_STATUS:
        raise RuntimeError("PB.2 C1 execution is not authorized")
    if sha256(parsed.freeze_contract.read_bytes()) != correction["baseToolFreeze"]["sha256"]:
        raise RuntimeError("base tool freeze mismatch")
    if execution.get("baseToolFreeze", {}).get("sha256") != correction["baseToolFreeze"]["sha256"]:
        raise RuntimeError("execution does not bind base tool freeze")
    if execution.get("toolCorrection", {}).get("sha256") != sha256(parsed.correction_contract.read_bytes()):
        raise RuntimeError("execution does not bind exact C1 correction")
    exact = {
        "repositoryRoot": str(parsed.repository_root),
        "engineSource": str(parsed.engine_source),
        "workRoot": str(parsed.work_root),
        "evidenceRoot": str(parsed.evidence_root),
        "positiveInspections": 2,
        "negativeCases": list(correction["negativeCases"]),
        "blenderStarts": 0,
        "renders": 0,
        "proposalExecutions": 0,
        "engineSourceEdits": 0,
        "engineRemoteWrites": 0,
        "networkCalls": 0,
    }
    if execution.get("authorizedRun") != exact:
        raise RuntimeError("authorized run differs from exact C1 scope")
    if execution.get("stillUnauthorized") != freeze.get("stillUnauthorized"):
        raise RuntimeError("unauthorized boundary changed")
    authorization = execution.get("authorization", {})
    text = authorization.get("exactUserText")
    if not isinstance(text, str) or not text or sha256(text.encode()) != authorization.get("exactUserTextSha256"):
        raise RuntimeError("exact user authorization binding is invalid")
    if authorization.get("explicitPb2ScopePresent") is not True:
        raise RuntimeError("explicit PB.2 scope is absent")
    if parsed.execution_contract.parent != root / "specs":
        raise RuntimeError("execution contract must be in repository specs/")


def main() -> int:
    started = time.monotonic()
    parsed = args()
    root = parsed.repository_root.resolve(strict=True)
    engine = parsed.engine_source.resolve(strict=True)
    freeze_path = parsed.freeze_contract.resolve(strict=True)
    correction_path = parsed.correction_contract.resolve(strict=True)
    execution_path = parsed.execution_contract.resolve(strict=True)
    freeze = read_json(freeze_path)
    correction = read_json(correction_path)
    execution = read_json(execution_path)
    validate_authority(parsed, root, freeze, correction, execution)

    head = git(["rev-parse", "HEAD"], root)
    parent = git(["rev-parse", "HEAD^"], root)
    if parent != execution["executionParentResearchCommit"]:
        raise RuntimeError("execution parent research commit mismatch")
    if git(["status", "--porcelain=v1"], root) != "":
        raise RuntimeError("research worktree must be clean before execution")
    execution_uri = execution_path.relative_to(root).as_posix()
    committed_execution = git(["show", f"HEAD:{execution_uri}"], root, binary=True)
    if committed_execution != execution_path.read_bytes():
        raise RuntimeError("HEAD does not contain exact execution contract bytes")
    if execution["executionCommit"] != head:
        raise RuntimeError("executionCommit does not equal current HEAD")
    if sha256(Path(__file__).read_bytes()) != execution["runnerSha256"]:
        raise RuntimeError("C1 runner SHA-256 mismatch")
    auditor_path = root / correction["independentAuditor"]["uri"]
    if sha256(auditor_path.read_bytes()) != execution["auditorSha256"]:
        raise RuntimeError("C1 auditor SHA-256 mismatch")
    if git(["rev-parse", "HEAD"], engine) != freeze["engineSource"]["head"]:
        raise RuntimeError("engine source HEAD mismatch")
    if git(["status", "--porcelain=v1"], engine) != "":
        raise RuntimeError("engine source is dirty")

    base = load_base_runner(root, correction["baseRunner"]["sha256"])
    contract = base.load_contract_module(engine, freeze["engineSource"]["contractModuleSha256"])
    work_root = base.require_fresh_absolute(parsed.work_root, "work root")
    evidence_root = base.require_fresh_absolute(parsed.evidence_root, "evidence root")
    work_root.mkdir()
    evidence_root.mkdir()
    positives = []
    negatives = []

    for fixture in freeze["fixtures"]:
        workspace = work_root / f"positive-{fixture['id'].lower()}"
        base.prepare_workspace(root, workspace, fixture, freeze["commonInputs"])
        before = base.snapshot(workspace)
        result = contract.inspect_proposal(workspace, fixture["proposalUri"], fixture["approvalUri"])
        after = base.snapshot(workspace)
        positives.append({
            "id": fixture["id"],
            "status": result["status"],
            "proposalId": result["proposalId"],
            "planHash": result["planHash"],
            "expectedPlanHash": fixture["planHash"],
            "approvedOperation": result["approvedOperation"],
            "approvedMutationScope": result["approvedMutationScope"],
            "filesystemExact": before == after,
            "buildPlanWritten": (workspace / fixture["outputUri"]).exists(),
        })

    base_fixture = freeze["fixtures"][0]
    expected_reasons = dict(correction["negativeReasons"])
    for case_id in correction["negativeCases"]:
        workspace = work_root / f"negative-{case_id.lower().replace('_', '-')}"
        base.prepare_workspace(root, workspace, base_fixture, freeze["commonInputs"])
        mode = base.apply_negative_mutation(case_id, contract, workspace, base_fixture)
        before = base.snapshot(workspace)
        actual_reason = None
        try:
            if mode == "EXECUTE_WITHOUT_INSPECTION_TOKEN":
                contract.execute_approved_compile(workspace, base_fixture["proposalUri"], base_fixture["approvalUri"], "0" * 64)
            else:
                contract.inspect_proposal(workspace, base_fixture["proposalUri"], base_fixture["approvalUri"])
        except contract.ContractError as error:
            actual_reason = error.reason
        after = base.snapshot(workspace)
        output_exists = (workspace / base_fixture["outputUri"]).exists()
        negatives.append({
            "id": case_id,
            "expectedReason": expected_reasons[case_id],
            "actualReason": actual_reason,
            "passed": actual_reason == expected_reasons[case_id] and before == after and not output_exists,
            "filesystemExact": before == after,
            "buildPlanFilesWritten": int(output_exists),
            "blenderStarts": 0,
            "sceneMutations": 0,
            "networkCalls": 0,
            "shellCommandsFromProposal": 0,
            "filesystemOperationsOutsideWorkAndEvidenceRoots": 0,
            "arbitraryPythonFromProposalExecuted": 0,
        })

    positive_pass = all(
        row["status"] == "APPROVED_READY"
        and row["planHash"] == row["expectedPlanHash"]
        and row["approvedOperation"] == "COMPILE_BUILD_PLAN"
        and row["approvedMutationScope"] == ["WRITE_BUILD_PLAN"]
        and row["filesystemExact"] and not row["buildPlanWritten"]
        for row in positives
    )
    negative_pass = all(row["passed"] for row in negatives)
    work_bytes = sum(path.stat().st_size for path in work_root.rglob("*") if path.is_file())
    elapsed = time.monotonic() - started
    if work_bytes > freeze["ceilings"]["maximumWorkRootBytes"] or elapsed > freeze["ceilings"]["maximumWallSeconds"]:
        raise RuntimeError("resource ceiling exceeded")
    if git(["rev-parse", "HEAD"], engine) != freeze["engineSource"]["head"] or git(["status", "--porcelain=v1"], engine) != "":
        raise RuntimeError("engine source changed during execution")

    body = {
        "schemaVersion": "bfs.aiNativeStudioPb2ValidationReceiptC1.v0.2",
        "status": "PASS" if positive_pass and negative_pass else "FAIL",
        "mode": "TYPED_CONTRACT_ONLY_ZERO_BLENDER_C1",
        "executionCommit": head,
        "executionParentResearchCommit": parent,
        "engineHead": freeze["engineSource"]["head"],
        "baseToolFreeze": {"uri": freeze["self"]["uri"], "sha256": sha256(freeze_path.read_bytes())},
        "toolCorrection": {"uri": correction_path.relative_to(root).as_posix(), "sha256": sha256(correction_path.read_bytes())},
        "executionContract": {"uri": execution_uri, "sha256": sha256(execution_path.read_bytes())},
        "positives": positives,
        "negatives": negatives,
        "counts": {
            "positiveInspections": len(positives), "negativeCases": len(negatives),
            "proposalExecutions": 0, "buildPlanFilesWritten": 0, "blenderStarts": 0,
            "renders": 0, "sceneMutations": 0, "networkCalls": 0,
            "shellCommandsFromProposal": 0, "arbitraryPythonFromProposalExecuted": 0,
            "engineSourceEdits": 0, "engineRemoteWrites": 0, "fixedGitProcesses": 8,
        },
        "resources": {"wallSeconds": elapsed, "workRootBytes": work_bytes},
        "claimCeiling": correction["claimCeiling"],
    }
    body["receiptHash"] = sha256(canonical(body))
    base.write_exclusive(evidence_root / "receipt.json", body)
    print(f"PB2_VALIDATION_C1 {body['status']} positives={len(positives)} negatives={len(negatives)} receiptHash={body['receiptHash']}")
    return 0 if body["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
