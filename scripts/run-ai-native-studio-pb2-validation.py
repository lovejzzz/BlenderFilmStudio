#!/usr/bin/env python3
"""Fail-closed PB.2 typed proposal/approval validation runner.

This trusted harness never starts Blender and never executes proposal-supplied
Python, shell commands, network requests, or scene mutations. It is inert until
an exact one-run execution contract is present and authorized.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


EXECUTION_SCHEMA = "bfs.aiNativeStudioPb2ValidationOnlyExecution.v0.4"
EXECUTION_STATUS = "AUTHORIZED_FOR_ONE_FORMAL_RUN"
FREEZE_SCHEMA = "bfs.aiNativeStudioPb2ValidationToolFreeze.v0.3"
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--engine-source", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--freeze-contract", type=Path, required=True)
    parser.add_argument("--execution-contract", type=Path, required=True)
    return parser.parse_args()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_exclusive(path: Path, value: object) -> None:
    payload = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        written = 0
        while written < len(payload):
            written += os.write(descriptor, payload[written:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def git(args: list[str], cwd: Path) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True,
    ).stdout.strip()


def require_fresh_absolute(path: Path, label: str) -> Path:
    if not path.is_absolute():
        raise RuntimeError(f"{label} must be absolute")
    if path.exists() or path.is_symlink():
        raise RuntimeError(f"{label} must not exist")
    if not path.parent.resolve(strict=True).is_dir():
        raise RuntimeError(f"{label} parent must already exist")
    return path


def load_contract_module(engine_source: Path, expected_sha256: str):
    module_path = engine_source / "scripts/modules/film_studio_contract.py"
    if sha256_file(module_path) != expected_sha256:
        raise RuntimeError("engine contract module SHA-256 mismatch")
    spec = importlib.util.spec_from_file_location("pb2_frozen_film_studio_contract", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load frozen engine contract module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def copy_exact(repository_root: Path, workspace: Path, uri: str, expected: str | None = None) -> None:
    source = repository_root / uri
    if not source.is_file() or source.is_symlink():
        raise RuntimeError(f"input is missing or symbolic: {uri}")
    if expected is not None and sha256_file(source) != expected:
        raise RuntimeError(f"input SHA-256 mismatch: {uri}")
    destination = workspace / uri
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    if sha256_file(destination) != sha256_file(source):
        raise RuntimeError(f"copied input mismatch: {uri}")


def prepare_workspace(repository_root: Path, root: Path, fixture: dict, common: list[dict]) -> None:
    root.mkdir()
    for record in common:
        copy_exact(repository_root, root, record["uri"], record["sha256"])
    for record in fixture["inputs"]:
        copy_exact(repository_root, root, record["uri"], record["sha256"])
    output_parent = (root / fixture["outputUri"]).parent
    output_parent.mkdir(parents=True, exist_ok=True)


def snapshot(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file() and not path.is_symlink()
    }


def rewrite_json(path: Path, value: dict) -> None:
    payload = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    path.write_text(payload, encoding="utf-8")


def bind_approval(workspace: Path, proposal_uri: str, approval_uri: str) -> None:
    approval_path = workspace / approval_uri
    approval = read_json(approval_path)
    approval["proposal"] = {"uri": proposal_uri, "fileSha256": sha256_file(workspace / proposal_uri)}
    rewrite_json(approval_path, approval)


def update_scene_binding(contract, workspace: Path, fixture: dict, raw: bytes | None = None) -> None:
    proposal_path = workspace / fixture["proposalUri"]
    proposal = read_json(proposal_path)
    scene_path = workspace / fixture["sceneSpecUri"]
    scene_bytes = scene_path.read_bytes() if raw is None else raw
    if raw is not None:
        scene_path.write_bytes(raw)
    try:
        document = json.loads(scene_bytes)
        canonical_sha = contract.sha256_bytes(
            contract.javascript_canonical_json(contract.canonicalize(document)).encode()
        )
    except (ValueError, contract.ContractError):
        canonical_sha = "0" * 64
    proposal["sceneSpec"] = {
        "uri": fixture["sceneSpecUri"],
        "fileSha256": sha256_bytes(scene_path.read_bytes()),
        "canonicalSha256": canonical_sha,
    }
    rewrite_json(proposal_path, proposal)
    bind_approval(workspace, fixture["proposalUri"], fixture["approvalUri"])


def apply_negative_mutation(case_id: str, contract, workspace: Path, fixture: dict) -> str:
    proposal_path = workspace / fixture["proposalUri"]
    approval_path = workspace / fixture["approvalUri"]
    scene_path = workspace / fixture["sceneSpecUri"]
    proposal = read_json(proposal_path)
    approval = read_json(approval_path)

    if case_id == "N_REJECTED_PROPOSAL":
        proposal["decision"] = "REJECT"
        rewrite_json(proposal_path, proposal)
    elif case_id == "N_TAMPERED_PROPOSAL":
        proposal["diff"]["summary"] += " tampered"
        rewrite_json(proposal_path, proposal)
    elif case_id == "N_UNAPPROVED_PROPOSAL":
        approval["decision"] = "PENDING"
        rewrite_json(approval_path, approval)
    elif case_id == "N_WRONG_ORDER":
        return "EXECUTE_WITHOUT_INSPECTION_TOKEN"
    elif case_id == "N_UNAUTHORIZED_SCOPE":
        proposal["requestedMutationScope"] = ["WRITE_BUILD_PLAN", "MUTATE_SCENE"]
        rewrite_json(proposal_path, proposal)
        bind_approval(workspace, fixture["proposalUri"], fixture["approvalUri"])
    elif case_id == "N_UNKNOWN_FIELD":
        scene = read_json(scene_path)
        scene["unexpectedField"] = True
        rewrite_json(scene_path, scene)
        update_scene_binding(contract, workspace, fixture)
    elif case_id == "N_PATH_ESCAPE":
        scene = read_json(scene_path)
        scene["assets"][0]["uri"] = "../outside.blend"
        rewrite_json(scene_path, scene)
        update_scene_binding(contract, workspace, fixture)
    elif case_id == "N_NONFINITE":
        raw = scene_path.read_text(encoding="utf-8").replace('"energy": 1200', '"energy": NaN', 1).encode()
        if raw == scene_path.read_bytes():
            raise RuntimeError("nonfinite mutation token was not found")
        update_scene_binding(contract, workspace, fixture, raw)
    else:
        raise RuntimeError(f"unknown negative case: {case_id}")
    return "INSPECT"


def validate_authority(args: argparse.Namespace, freeze: dict, execution: dict) -> None:
    if freeze.get("schemaVersion") != FREEZE_SCHEMA or freeze.get("status") != "FROZEN_NOT_AUTHORIZED":
        raise RuntimeError("tool freeze contract is not exact")
    if execution.get("schemaVersion") != EXECUTION_SCHEMA or execution.get("status") != EXECUTION_STATUS:
        raise RuntimeError("PB.2 execution is not authorized")
    if execution.get("toolFreeze", {}).get("sha256") != sha256_file(args.freeze_contract):
        raise RuntimeError("execution contract does not bind exact tool freeze")
    requested = execution.get("authorizedRun", {})
    exact = {
        "repositoryRoot": str(args.repository_root),
        "engineSource": str(args.engine_source),
        "workRoot": str(args.work_root),
        "evidenceRoot": str(args.evidence_root),
        "positiveInspections": 2,
        "negativeCases": list(EXPECTED_CASES),
        "blenderStarts": 0,
        "renders": 0,
        "proposalExecutions": 0,
        "engineSourceEdits": 0,
        "engineRemoteWrites": 0,
        "networkCalls": 0,
    }
    if requested != exact:
        raise RuntimeError("authorized run scope is not exact")
    frozen_paths = freeze.get("paths", {})
    if requested["repositoryRoot"] != frozen_paths.get("repositoryRoot"):
        raise RuntimeError("repository root differs from tool freeze")
    if requested["engineSource"] != frozen_paths.get("engineSource"):
        raise RuntimeError("engine source differs from tool freeze")
    if requested["workRoot"] != frozen_paths.get("workRoot"):
        raise RuntimeError("work root differs from tool freeze")
    if requested["evidenceRoot"] != frozen_paths.get("evidenceRoot"):
        raise RuntimeError("evidence root differs from tool freeze")
    if execution.get("stillUnauthorized") != freeze.get("stillUnauthorized"):
        raise RuntimeError("unauthorized scope changed")


def main() -> int:
    started = time.monotonic()
    args = parse_args()
    repository_root = args.repository_root.resolve(strict=True)
    engine_source = args.engine_source.resolve(strict=True)
    if args.freeze_contract.resolve(strict=True).parent != repository_root / "specs":
        raise RuntimeError("freeze contract must be inside repository specs/")
    if args.execution_contract.resolve(strict=True).parent != repository_root / "specs":
        raise RuntimeError("execution contract must be inside repository specs/")
    freeze = read_json(args.freeze_contract)
    execution = read_json(args.execution_contract)
    validate_authority(args, freeze, execution)
    work_root = require_fresh_absolute(args.work_root, "work root")
    evidence_root = require_fresh_absolute(args.evidence_root, "evidence root")

    if git(["rev-parse", "HEAD"], repository_root) != execution["researchCommit"]:
        raise RuntimeError("research commit mismatch")
    if git(["rev-parse", "HEAD"], engine_source) != freeze["engineSource"]["head"]:
        raise RuntimeError("engine source HEAD mismatch")
    if git(["status", "--porcelain=v1"], engine_source) != "":
        raise RuntimeError("engine source is dirty")
    if sha256_file(repository_root / freeze["runner"]["uri"]) != execution["runnerSha256"]:
        raise RuntimeError("runner SHA-256 mismatch")

    contract = load_contract_module(engine_source, freeze["engineSource"]["contractModuleSha256"])
    work_root.mkdir()
    evidence_root.mkdir()
    positives = []
    negatives = []

    for fixture in freeze["fixtures"]:
        workspace = work_root / f"positive-{fixture['id'].lower()}"
        prepare_workspace(repository_root, workspace, fixture, freeze["commonInputs"])
        before = snapshot(workspace)
        result = contract.inspect_proposal(workspace, fixture["proposalUri"], fixture["approvalUri"])
        after = snapshot(workspace)
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
    for case_id, expected_reason in EXPECTED_CASES.items():
        workspace = work_root / f"negative-{case_id.lower().replace('_', '-')}"
        prepare_workspace(repository_root, workspace, base_fixture, freeze["commonInputs"])
        mode = apply_negative_mutation(case_id, contract, workspace, base_fixture)
        before = snapshot(workspace)
        actual_reason = None
        try:
            if mode == "EXECUTE_WITHOUT_INSPECTION_TOKEN":
                contract.execute_approved_compile(
                    workspace, base_fixture["proposalUri"], base_fixture["approvalUri"], "0" * 64,
                )
            else:
                contract.inspect_proposal(workspace, base_fixture["proposalUri"], base_fixture["approvalUri"])
        except contract.ContractError as error:
            actual_reason = error.reason
        after = snapshot(workspace)
        output_exists = (workspace / base_fixture["outputUri"]).exists()
        negatives.append({
            "id": case_id,
            "expectedReason": expected_reason,
            "actualReason": actual_reason,
            "passed": actual_reason == expected_reason and before == after and not output_exists,
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
        and row["filesystemExact"]
        and not row["buildPlanWritten"]
        for row in positives
    )
    negative_pass = all(row["passed"] for row in negatives)
    work_bytes = sum(path.stat().st_size for path in work_root.rglob("*") if path.is_file())
    elapsed = time.monotonic() - started
    if work_bytes > freeze["ceilings"]["maximumWorkRootBytes"]:
        raise RuntimeError("work root byte ceiling exceeded")
    if elapsed > freeze["ceilings"]["maximumWallSeconds"]:
        raise RuntimeError("wall-time ceiling exceeded")
    if git(["rev-parse", "HEAD"], engine_source) != freeze["engineSource"]["head"]:
        raise RuntimeError("engine source HEAD changed during validation")
    if git(["status", "--porcelain=v1"], engine_source) != "":
        raise RuntimeError("engine source changed during validation")
    body = {
        "schemaVersion": "bfs.aiNativeStudioPb2ValidationReceipt.v0.1",
        "status": "PASS" if positive_pass and negative_pass else "FAIL",
        "mode": "TYPED_CONTRACT_ONLY_ZERO_BLENDER",
        "researchCommit": execution["researchCommit"],
        "engineHead": freeze["engineSource"]["head"],
        "freezeContract": {"uri": freeze["self"]["uri"], "sha256": sha256_file(args.freeze_contract)},
        "executionContract": {"uri": args.execution_contract.relative_to(repository_root).as_posix(), "sha256": sha256_file(args.execution_contract)},
        "positives": positives,
        "negatives": negatives,
        "counts": {
            "positiveInspections": len(positives),
            "negativeCases": len(negatives),
            "proposalExecutions": 0,
            "buildPlanFilesWritten": 0,
            "blenderStarts": 0,
            "renders": 0,
            "sceneMutations": 0,
            "networkCalls": 0,
            "shellCommandsFromProposal": 0,
            "arbitraryPythonFromProposalExecuted": 0,
            "engineSourceEdits": 0,
            "engineRemoteWrites": 0,
            "fixedGitProcesses": 5,
        },
        "resources": {"wallSeconds": elapsed, "workRootBytes": work_bytes},
        "claimCeiling": freeze["claimCeiling"],
    }
    body["receiptHash"] = sha256_bytes(canonical_bytes(body))
    write_exclusive(evidence_root / "receipt.json", body)
    if (evidence_root / "receipt.json").stat().st_size > freeze["ceilings"]["maximumEvidenceRootBytes"]:
        raise RuntimeError("evidence root byte ceiling exceeded")
    print(f"PB2_VALIDATION {body['status']} positives={len(positives)} negatives={len(negatives)} receiptHash={body['receiptHash']}")
    return 0 if body["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
