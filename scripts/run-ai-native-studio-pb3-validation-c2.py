#!/usr/bin/env python3
"""C2 wrapper: bind exact PB.3 authority and verify process-log evidence."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path


C2_SCHEMA = "bfs.aiNativeStudioPb3ValidationToolC2EvidenceBinding.v0.5"
C2_STATUS = "FROZEN_INERT_C2_AUTHORIZATION_AND_EVIDENCE_BINDING"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def extract_option(name: str) -> str:
    require(sys.argv.count(name) == 1, f"{name} must appear exactly once")
    index = sys.argv.index(name)
    require(index + 1 < len(sys.argv), f"{name} value is missing")
    value = sys.argv[index + 1]
    del sys.argv[index : index + 2]
    return value


def option_value(name: str) -> str:
    require(sys.argv.count(name) == 1, f"{name} must appear exactly once")
    index = sys.argv.index(name)
    require(index + 1 < len(sys.argv), f"{name} value is missing")
    return sys.argv[index + 1]


def load_module(path: Path, expected_sha256: str, name: str):
    require(sha256_file(path) == expected_sha256, f"{name} SHA-256 mismatch")
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(args: list[str], cwd: Path, binary: bool = False):
    result = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=not binary)
    return result.stdout if binary else result.stdout.strip()


def exact_process_argv(binary: Path, helper: Path, root: Path, tool_path: Path, work: Path, fixture_id: str, stage: str) -> list[str]:
    fixture = work / fixture_id.lower()
    common = [
        str(binary), "--background", "--disable-autoexec", "--offline-mode",
    ]
    if stage == "build":
        common.insert(2, "--factory-startup")
    else:
        common.append(str(fixture / "artifacts" / "scene.blend"))
    return [
        *common, "--python", str(helper), "--", "--stage", stage,
        "--fixture-id", fixture_id, "--fixture-root", str(fixture),
        "--repository-root", str(root), "--tool-contract", str(tool_path),
        "--receipt", str(Path(option_value("--evidence-root")) / fixture_id.lower() / f"{stage}.json"),
    ]


def validate_authority(c2_path: Path, c2: dict) -> None:
    root = Path(option_value("--repository-root")).resolve(strict=True)
    execution_path = Path(option_value("--execution-contract")).resolve(strict=True)
    tool_path = Path(option_value("--tool-contract")).resolve(strict=True)
    execution = json.loads(execution_path.read_text(encoding="utf-8"))
    c2_sha = sha256_file(c2_path)
    require(execution.get("toolC2Correction", {}).get("sha256") == c2_sha, "execution does not bind C2 correction")
    request_record = c2["authorizationRequest"]
    request_path = root / request_record["uri"]
    require(request_path.is_file() and not request_path.is_symlink(), "C2 authorization request is missing")
    require(sha256_file(request_path) == request_record["sha256"], "C2 authorization request SHA-256 mismatch")
    request = json.loads(request_path.read_text(encoding="utf-8"))
    require(execution.get("authorizationRequest") == request_record, "execution authorization-request binding differs")
    authorization = execution.get("authorization", {})
    exact_text = request["requestedAuthorization"]["exactText"]
    require(authorization.get("exactUserText") == exact_text, "exact PB.3 C2 authorization text differs")
    require(authorization.get("exactUserTextSha256") == sha256_bytes(exact_text.encode()), "authorization text SHA-256 differs")
    require(authorization.get("explicitPb3ScopePresent") is True and authorization.get("authorizedAtUtc"), "explicit PB.3 C2 authority is absent")
    expected_run = execution.get("authorizedRun", {})
    argument_bindings = {
        "repositoryRoot": str(root),
        "engineSource": str(Path(option_value("--engine-source"))),
        "binary": str(Path(option_value("--binary"))),
        "workRoot": str(Path(option_value("--work-root"))),
        "evidenceRoot": str(Path(option_value("--evidence-root"))),
    }
    require(all(expected_run.get(key) == value for key, value in argument_bindings.items()), "formal arguments differ from authorized roots")
    require(execution.get("runner", {}).get("path") == c2["tools"]["runner"], "execution runner is not C2")
    require(execution.get("independentAuditor", {}).get("path") == c2["tools"]["independentAuditor"], "execution auditor is not C2")
    require(execution_path.parent == root / "specs", "execution contract must be in specs/")
    contract_uri = execution_path.relative_to(root).as_posix()
    require(git(["diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"], root).splitlines() == [contract_uri], "execution commit must change only its contract")
    request_uri = request_path.relative_to(root).as_posix()
    require(git(["show", f"HEAD^:{request_uri}"], root, binary=True) == request_path.read_bytes(), "authorization request was not frozen in execution parent")
    require(git(["show", f"HEAD^:{c2_path.relative_to(root).as_posix()}"], root, binary=True) == c2_path.read_bytes(), "C2 correction was not frozen in execution parent")
    require(sha256_file(tool_path) == c2["baseC1"]["toolFreezeSha256"], "base tool hash differs")


def verify_process_logs(c2: dict) -> None:
    root = Path(option_value("--repository-root")).resolve(strict=True)
    binary = Path(option_value("--binary")).resolve(strict=True)
    tool_path = Path(option_value("--tool-contract")).resolve(strict=True)
    work = Path(option_value("--work-root"))
    evidence = Path(option_value("--evidence-root"))
    tool = json.loads(tool_path.read_text(encoding="utf-8"))
    helper = root / tool["tools"]["blenderProbe"]
    receipt = json.loads((evidence / "receipt.json").read_text(encoding="utf-8"))
    processes = receipt.get("processes", [])
    expected_pairs = [(fixture, stage) for fixture in ("B01", "B02") for stage in ("build", "reopen")]
    require(len(processes) == len(expected_pairs), "formal process roster differs")
    for process, (fixture, stage) in zip(processes, expected_pairs, strict=True):
        require(process.get("fixtureId") == fixture and process.get("stage") == stage, "formal process order differs")
        require(process.get("argv") == exact_process_argv(binary, helper, root, tool_path, work, fixture, stage), "formal process argv differs")
        for stream in ("stdout", "stderr"):
            log = evidence / fixture.lower() / f"{stage}.{stream}.log"
            require(log.is_file() and not log.is_symlink(), f"missing exact {fixture} {stage} {stream} log")
            require(sha256_file(log) == process.get(f"{stream}Sha256"), f"{fixture} {stage} {stream} log SHA-256 differs")
    require(c2["evidenceBinding"]["processLogFiles"] == 8, "C2 log roster contract differs")


def main() -> int:
    c2_path = Path(extract_option("--c2-contract")).resolve(strict=True)
    c2 = json.loads(c2_path.read_text(encoding="utf-8"))
    require(c2.get("schemaVersion") == C2_SCHEMA and c2.get("status") == C2_STATUS, "C2 correction contract is not exact")
    require(sha256_file(Path(__file__)) == c2["tools"]["runnerSha256"], "C2 runner SHA-256 mismatch")
    c1_path = c2_path.parent.parent / c2["baseC1"]["runner"]
    c1 = load_module(c1_path, c2["baseC1"]["runnerSha256"], "pb3_c1_runner")
    if "--self-test" in sys.argv:
        checks = {
            "authorizationHashStable": sha256_bytes("PB.3 C2".encode()) == "d715d450959de850606f6e5c31c02255267c28834f2d6ec43a262d3e922b0c24",
            "exactChangedPathRequired": True,
            "eightProcessLogsRequired": c2["evidenceBinding"]["processLogFiles"] == 8,
        }
        require(all(checks.values()), "C2 self-test failed")
        result = c1.main()
        require(result == 0, "C1 self-test delegation failed")
        print(json.dumps({"status": "PASS", "c2Checks": checks}, sort_keys=True))
        return 0
    validate_authority(c2_path, c2)
    result = c1.main()
    require(result == 0, "C1 runner failed")
    verify_process_logs(c2)
    print("PB3_VALIDATION_C2 PASS exact authority, argv and process logs verified")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"PB3_VALIDATION_C2_STOP {type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1) from error
