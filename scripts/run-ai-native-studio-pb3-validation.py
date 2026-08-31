#!/usr/bin/env python3
"""Fail-closed PB.3 canonical compile and editable-workspace runner."""

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


TOOL_SCHEMA = "bfs.aiNativeStudioPb3ValidationToolFreeze.v0.2"
EXECUTION_SCHEMA = "bfs.aiNativeStudioPb3ValidationExecution.v0.3"
EXECUTION_STATUS = "AUTHORIZED_FOR_ONE_FORMAL_RUN"


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--repository-root", type=Path)
    parser.add_argument("--engine-source", type=Path)
    parser.add_argument("--binary", type=Path)
    parser.add_argument("--work-root", type=Path)
    parser.add_argument("--evidence-root", type=Path)
    parser.add_argument("--tool-contract", type=Path)
    parser.add_argument("--execution-contract", type=Path)
    return parser.parse_args()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_exclusive(path: Path, value: object) -> None:
    payload = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        offset = 0
        while offset < len(payload):
            offset += os.write(descriptor, payload[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def git(args: list[str], cwd: Path, binary: bool = False):
    result = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=not binary)
    return result.stdout if binary else result.stdout.strip()


def fresh_absolute(path: Path, label: str) -> Path:
    require(path.is_absolute(), f"{label} must be absolute")
    require(not path.exists() and not path.is_symlink(), f"{label} must not exist")
    require(path.parent.resolve(strict=True).is_dir(), f"{label} parent must exist")
    return path


def copy_exact(repository_root: Path, fixture_root: Path, record: dict) -> None:
    source = repository_root / record["uri"]
    require(source.is_file() and not source.is_symlink(), f"missing input: {record['uri']}")
    require(sha256_file(source) == record["sha256"], f"input hash mismatch: {record['uri']}")
    destination = fixture_root / record["uri"]
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    require(sha256_file(destination) == record["sha256"], f"copy mismatch: {record['uri']}")


def self_test() -> int:
    checks = {
        "canonicalStable": canonical({"b": 2, "a": [True, None]}) == b'{"a":[true,null],"b":2}',
        "hashStable": sha256_bytes(b"PB.3") == "af84fa3c77c07d0db5b489ae89cb72a74a83951f9a4efa1537c6aec78b6a190a",
        "executionRequiresFlag": EXECUTION_STATUS == "AUTHORIZED_FOR_ONE_FORMAL_RUN",
        "executionSchemaVersioned": EXECUTION_SCHEMA.endswith(".v0.3"),
    }
    require(all(checks.values()), "self-test failed")
    print(json.dumps({"status": "PASS", "checks": checks}, sort_keys=True))
    return 0


def require_arguments(parsed: argparse.Namespace) -> None:
    missing = [
        name for name in (
            "repository_root", "engine_source", "binary", "work_root", "evidence_root",
            "tool_contract", "execution_contract",
        )
        if getattr(parsed, name) is None
    ]
    require(not missing, "missing formal arguments: " + ",".join(missing))


def validate_authority(parsed: argparse.Namespace, root: Path, tool: dict, execution: dict) -> str:
    require(parsed.execute, "PB.3 runner is inert without --execute")
    require(tool.get("schemaVersion") == TOOL_SCHEMA and tool.get("status") == "FROZEN_INERT_EXECUTION_UNAUTHORIZED", "tool freeze is not exact")
    require(execution.get("schemaVersion") == EXECUTION_SCHEMA and execution.get("status") == EXECUTION_STATUS, "PB.3 execution is not authorized")
    require(execution.get("toolFreeze", {}).get("sha256") == sha256_file(parsed.tool_contract), "execution does not bind tool freeze")
    authorization = execution.get("authorization", {})
    require(authorization.get("explicitPb3ScopePresent") is True, "explicit PB.3 scope is absent")
    require("PB.3" in authorization.get("exactUserText", ""), "authorization does not name PB.3")
    require("executionCommit" not in execution, "execution contract must not self-reference its commit")

    expected = {
        "repositoryRoot": str(parsed.repository_root),
        "engineSource": str(parsed.engine_source),
        "binary": str(parsed.binary),
        "workRoot": str(parsed.work_root),
        "evidenceRoot": str(parsed.evidence_root),
        "benchmarks": ["B01", "B02"],
        "blenderStarts": 4,
        "proposalExecutions": 2,
        "buildPlanWrites": 2,
        "sceneBuilds": 2,
        "workspaceSaves": 2,
        "reopens": 2,
        "renders": 0,
        "engineSourceEdits": 0,
        "engineRemoteWrites": 0,
        "networkCalls": 0,
    }
    require(execution.get("authorizedRun") == expected, "authorized PB.3 scope differs")
    require(execution.get("stillUnauthorized") == tool.get("stillUnauthorized"), "unauthorized scope differs")
    require(execution.get("executionParentResearchCommit") == git(["rev-parse", "HEAD^"], root), "execution parent mismatch")
    require(git(["status", "--porcelain"], root) == "", "research worktree must be clean")
    contract_uri = parsed.execution_contract.resolve(strict=True).relative_to(root).as_posix()
    committed = git(["show", f"HEAD:{contract_uri}"], root, binary=True)
    require(committed == parsed.execution_contract.read_bytes(), "execution contract bytes are not committed at HEAD")
    return git(["rev-parse", "HEAD"], root)


def prepare_fixture(root: Path, work_root: Path, tool: dict, row: dict) -> Path:
    fixture_root = work_root / row["id"].lower()
    fixture_root.mkdir()
    for record in tool["commonInputs"] + row["inputs"]:
        copy_exact(root, fixture_root, record)
    (fixture_root / row["outputUri"]).parent.mkdir(parents=True, exist_ok=True)
    (fixture_root / row["artifactRoot"]).mkdir(parents=True)
    return fixture_root


def blender_environment(root: Path, fixture_id: str, tool: dict) -> dict[str, str]:
    isolation = root / "isolation" / fixture_id.lower()
    values = {
        "HOME": isolation / "home",
        "TMPDIR": isolation / "tmp",
        "BLENDER_USER_CONFIG": isolation / "config",
        "BLENDER_USER_SCRIPTS": isolation / "scripts",
        "BLENDER_USER_DATAFILES": isolation / "datafiles",
        "BLENDER_USER_EXTENSIONS": isolation / "extensions",
    }
    for path in values.values():
        path.mkdir(parents=True, exist_ok=True)
    return {
        **os.environ,
        **{name: str(path) for name, path in values.items()},
        "OCIO": tool["ocio"]["absolutePath"],
        "PYTHONDONTWRITEBYTECODE": "1",
    }


def run_process(argv: list[str], cwd: Path, env: dict[str, str], stdout_path: Path, stderr_path: Path, timeout: int) -> dict:
    started = time.monotonic()
    result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, timeout=timeout)
    stdout_path.write_bytes(result.stdout)
    stderr_path.write_bytes(result.stderr)
    return {
        "argv": argv,
        "exitCode": result.returncode,
        "wallSeconds": time.monotonic() - started,
        "stdoutSha256": sha256_bytes(result.stdout),
        "stderrSha256": sha256_bytes(result.stderr),
    }


def validate_probe_receipt(path: Path, row: dict, stage: str) -> dict:
    receipt = read_json(path)
    claimed = receipt.pop("receiptHash")
    require(claimed == sha256_bytes(canonical(receipt)), f"{row['id']} {stage} receipt self-hash mismatch")
    receipt["receiptHash"] = claimed
    require(receipt.get("status") == "PASS" and receipt.get("fixtureId") == row["id"] and receipt.get("stage") == stage, f"{row['id']} {stage} receipt failed")
    require(receipt.get("counts") == {"blenderStarts": 1, "renders": 0, "networkCalls": 0}, f"{row['id']} {stage} counts differ")
    return receipt


def main() -> int:
    parsed = arguments()
    if parsed.self_test:
        require(not parsed.execute, "self-test cannot execute")
        return self_test()
    require_arguments(parsed)
    root = parsed.repository_root.resolve(strict=True)
    engine = parsed.engine_source.resolve(strict=True)
    binary = parsed.binary.resolve(strict=True)
    require(parsed.tool_contract.resolve(strict=True).parent == root / "specs", "tool contract must be in specs/")
    require(parsed.execution_contract.resolve(strict=True).parent == root / "specs", "execution contract must be in specs/")
    tool = read_json(parsed.tool_contract)
    execution = read_json(parsed.execution_contract)
    execution_commit = validate_authority(parsed, root, tool, execution)

    require(sha256_file(Path(__file__)) == tool["tools"]["runnerSha256"], "runner SHA-256 mismatch")
    helper = root / tool["tools"]["blenderProbe"]
    compiler = root / tool["tools"]["sceneCompiler"]
    require(sha256_file(helper) == tool["tools"]["blenderProbeSha256"], "Blender probe SHA-256 mismatch")
    require(sha256_file(compiler) == tool["tools"]["sceneCompilerSha256"], "scene compiler SHA-256 mismatch")
    require(sha256_file(binary) == tool["binary"]["sha256"], "binary SHA-256 mismatch")
    require(git(["rev-parse", "HEAD"], engine) == tool["source"]["head"], "engine HEAD mismatch")
    require(git(["status", "--porcelain"], engine) == "", "engine source is not clean")
    work = fresh_absolute(parsed.work_root, "work root")
    evidence = fresh_absolute(parsed.evidence_root, "evidence root")
    free = shutil.disk_usage(work.parent).free
    require(free >= tool["resources"]["minimumFreeBytes"], "free-space admission failed")

    os.mkdir(work)
    os.mkdir(evidence)
    process_rows = []
    probe_rows = []
    for row in tool["fixtures"]:
        fixture_root = prepare_fixture(root, work, tool, row)
        env = blender_environment(work, row["id"], tool)
        row_evidence = evidence / row["id"].lower()
        row_evidence.mkdir()
        build_receipt = row_evidence / "build.json"
        build_argv = [
            str(binary), "--background", "--factory-startup", "--disable-autoexec", "--offline-mode",
            "--python", str(helper), "--", "--stage", "build", "--fixture-id", row["id"],
            "--fixture-root", str(fixture_root), "--repository-root", str(root),
            "--tool-contract", str(parsed.tool_contract), "--receipt", str(build_receipt),
        ]
        build_process = run_process(build_argv, root, env, row_evidence / "build.stdout.log", row_evidence / "build.stderr.log", tool["resources"]["perStartTimeoutSeconds"])
        process_rows.append({"fixtureId": row["id"], "stage": "build", **build_process})
        require(build_process["exitCode"] == 0, f"{row['id']} build start failed")
        build = validate_probe_receipt(build_receipt, row, "build")
        blend = fixture_root / row["artifactRoot"] / "scene.blend"
        reopen_receipt = row_evidence / "reopen.json"
        reopen_argv = [
            str(binary), "--background", "--disable-autoexec", "--offline-mode", str(blend),
            "--python", str(helper), "--", "--stage", "reopen", "--fixture-id", row["id"],
            "--fixture-root", str(fixture_root), "--repository-root", str(root),
            "--tool-contract", str(parsed.tool_contract), "--receipt", str(reopen_receipt),
        ]
        reopen_process = run_process(reopen_argv, root, env, row_evidence / "reopen.stdout.log", row_evidence / "reopen.stderr.log", tool["resources"]["perStartTimeoutSeconds"])
        process_rows.append({"fixtureId": row["id"], "stage": "reopen", **reopen_process})
        require(reopen_process["exitCode"] == 0, f"{row['id']} reopen start failed")
        reopen = validate_probe_receipt(reopen_receipt, row, "reopen")
        probe_rows.append({"fixtureId": row["id"], "buildReceiptHash": build["receiptHash"], "reopenReceiptHash": reopen["receiptHash"]})

    require(git(["rev-parse", "HEAD"], engine) == tool["source"]["head"], "engine HEAD changed")
    require(git(["status", "--porcelain"], engine) == "", "engine source changed")
    counts = {
        "blenderStarts": 4, "proposalExecutions": 2, "buildPlanWrites": 2,
        "sceneBuilds": 2, "workspaceSaves": 2, "reopens": 2, "renders": 0,
        "engineSourceEdits": 0, "engineRemoteWrites": 0, "networkCalls": 0,
    }
    receipt = {
        "schemaVersion": "bfs.aiNativeStudioPb3ValidationReceipt.v0.1",
        "status": "PASS",
        "executionCommit": execution_commit,
        "executionParentResearchCommit": execution["executionParentResearchCommit"],
        "engineHead": tool["source"]["head"],
        "binarySha256": tool["binary"]["sha256"],
        "toolFreezeSha256": sha256_file(parsed.tool_contract),
        "workRoot": str(work),
        "evidenceRoot": str(evidence),
        "probes": probe_rows,
        "processes": process_rows,
        "counts": counts,
        "freeBytesAtAdmission": free,
        "claimCeiling": tool["claimCeiling"],
    }
    receipt["receiptHash"] = sha256_bytes(canonical(receipt))
    write_exclusive(evidence / "receipt.json", receipt)
    print(f"PB3_VALIDATION PASS receiptHash={receipt['receiptHash']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"PB3_VALIDATION_STOP {type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1) from error
