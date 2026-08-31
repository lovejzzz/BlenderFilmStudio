#!/usr/bin/env python3
"""Consolidated PB.3 C3 runner with corrected input, resources and evidence binding."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path


C3_SCHEMA = "bfs.aiNativeStudioPb3ValidationC3ExecutionToolFreeze.v0.8"
C3_STATUS = "FROZEN_INERT_C3_CORRECTED_EXECUTION_TOOLING"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def extract_option(name: str) -> str:
    require(sys.argv.count(name) == 1, f"{name} must appear exactly once")
    index = sys.argv.index(name)
    require(index + 1 < len(sys.argv), f"{name} value missing")
    value = sys.argv[index + 1]
    del sys.argv[index : index + 2]
    return value


def option_value(name: str) -> str:
    require(sys.argv.count(name) == 1, f"{name} must appear exactly once")
    index = sys.argv.index(name)
    require(index + 1 < len(sys.argv), f"{name} value missing")
    return sys.argv[index + 1]


def git(args: list[str], cwd: Path, binary: bool = False):
    result = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=not binary)
    return result.stdout if binary else result.stdout.strip()


def load_module(path: Path, expected_sha256: str):
    require(sha256_file(path) == expected_sha256, "base runner SHA-256 mismatch")
    spec = importlib.util.spec_from_file_location("pb3_base_runner_c3", path)
    require(spec is not None and spec.loader is not None, "cannot load base runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def regular_tree(root: Path) -> dict:
    require(root.is_dir() and not root.is_symlink(), f"root is not an exact directory: {root}")
    rows = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        require(not path.is_symlink(), f"root contains symbolic path: {path}")
        if path.is_file():
            rows.append({"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return {
        "regularFiles": len(rows),
        "regularFileBytes": sum(row["bytes"] for row in rows),
        "manifestSha256": sha256_bytes(canonical(rows)),
    }


def write_bytes_exclusive(path: Path, payload: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            require(written > 0, "exclusive write made no progress")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def exact_process_argv(binary: Path, helper: Path, root: Path, tool: Path, work: Path, evidence: Path, fixture: str, stage: str) -> list[str]:
    fixture_root = work / fixture.lower()
    prefix = [str(binary), "--background", "--disable-autoexec", "--offline-mode"]
    if stage == "build":
        prefix.insert(2, "--factory-startup")
    else:
        prefix.append(str(fixture_root / "artifacts" / "scene.blend"))
    return [
        *prefix, "--python", str(helper), "--", "--stage", stage,
        "--fixture-id", fixture, "--fixture-root", str(fixture_root),
        "--repository-root", str(root), "--tool-contract", str(tool),
        "--receipt", str(evidence / fixture.lower() / f"{stage}.json"),
    ]


def verify_retained_attempt(c3: dict) -> None:
    retained = c3["retainedAttempt01"]
    work = Path(retained["workRoot"])
    evidence = Path(retained["evidenceRoot"])
    require(regular_tree(work) == retained["workManifest"], "attempt-01 work root changed")
    require(regular_tree(evidence) == retained["evidenceManifest"], "attempt-01 evidence root changed")
    for record in retained["files"]:
        require(sha256_file(evidence / record["name"]) == record["sha256"], f"attempt-01 file changed: {record['name']}")


def validate_authority(c3_path: Path, c3: dict) -> None:
    root = Path(option_value("--repository-root")).resolve(strict=True)
    tool_path = Path(option_value("--tool-contract")).resolve(strict=True)
    execution_path = Path(option_value("--execution-contract")).resolve(strict=True)
    execution = json.loads(execution_path.read_text(encoding="utf-8"))
    request_record = c3["authorizationRequest"]
    request_path = root / request_record["uri"]
    request = json.loads(request_path.read_text(encoding="utf-8"))
    require(sha256_file(tool_path) == c3["correctedTool"]["sha256"], "corrected tool SHA-256 mismatch")
    require(execution.get("toolFreeze") == c3["correctedTool"], "execution does not bind corrected tool")
    require(execution.get("toolC3Correction", {}).get("sha256") == sha256_file(c3_path), "execution does not bind C3 tooling")
    require(sha256_file(request_path) == request_record["sha256"] and execution.get("authorizationRequest") == request_record, "execution does not bind C3 authorization request")
    exact_text = request["requestedAuthorization"]["exactText"]
    authorization = execution.get("authorization", {})
    require(authorization.get("exactUserText") == exact_text, "exact PB.3 C3 authorization text differs")
    require(authorization.get("exactUserTextSha256") == sha256_bytes(exact_text.encode()), "PB.3 C3 authorization SHA-256 differs")
    require(authorization.get("explicitPb3ScopePresent") is True and authorization.get("authorizedAtUtc"), "explicit PB.3 C3 authority is absent")
    expected_run = {
        "repositoryRoot": str(root),
        "engineSource": str(Path(option_value("--engine-source"))),
        "binary": str(Path(option_value("--binary"))),
        "workRoot": str(Path(option_value("--work-root"))),
        "evidenceRoot": str(Path(option_value("--evidence-root"))),
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
    require(execution.get("authorizedRun") == expected_run, "authorized PB.3 C3 scope differs")
    require(execution.get("runner", {}).get("path") == c3["tools"]["runner"], "execution runner is not C3")
    require(execution.get("independentAuditor", {}).get("path") == c3["tools"]["independentAuditor"], "execution auditor is not C3")
    contract_uri = execution_path.relative_to(root).as_posix()
    require(git(["diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"], root).splitlines() == [contract_uri], "execution commit must change only its contract")
    for frozen in (request_path, c3_path, tool_path):
        uri = frozen.relative_to(root).as_posix()
        require(git(["show", f"HEAD^:{uri}"], root, binary=True) == frozen.read_bytes(), f"execution parent does not freeze {uri}")
    verify_retained_attempt(c3)
    tool = json.loads(tool_path.read_text(encoding="utf-8"))
    input_records = [*tool["commonInputs"], *(record for fixture in tool["fixtures"] for record in fixture["inputs"])]
    require(len(input_records) == 13 and all(sha256_file(root / record["uri"]) == record["sha256"] for record in input_records), "corrected 13-input roster is not exact")


def verify_processes(c3: dict) -> None:
    root = Path(option_value("--repository-root")).resolve(strict=True)
    tool_path = Path(option_value("--tool-contract")).resolve(strict=True)
    tool = json.loads(tool_path.read_text(encoding="utf-8"))
    binary = Path(option_value("--binary")).resolve(strict=True)
    work = Path(option_value("--work-root"))
    evidence = Path(option_value("--evidence-root"))
    helper = root / tool["tools"]["blenderProbe"]
    receipt = json.loads((evidence / "receipt.json").read_text(encoding="utf-8"))
    pairs = [(fixture, stage) for fixture in ("B01", "B02") for stage in ("build", "reopen")]
    require(len(receipt.get("processes", [])) == 4, "process roster differs")
    for process, (fixture, stage) in zip(receipt["processes"], pairs, strict=True):
        require(process.get("fixtureId") == fixture and process.get("stage") == stage, "process order differs")
        require(process.get("argv") == exact_process_argv(binary, helper, root, tool_path, work, evidence, fixture, stage), "process argv differs")
        for stream in ("stdout", "stderr"):
            log = evidence / fixture.lower() / f"{stage}.{stream}.log"
            require(log.is_file() and not log.is_symlink(), f"process log missing: {log}")
            require(sha256_file(log) == process.get(f"{stream}Sha256"), f"process log SHA-256 differs: {log}")


def main() -> int:
    c3_path = Path(extract_option("--c3-contract")).resolve(strict=True)
    c3 = json.loads(c3_path.read_text(encoding="utf-8"))
    require(c3.get("schemaVersion") == C3_SCHEMA and c3.get("status") == C3_STATUS, "C3 execution tooling is not exact")
    require(sha256_file(Path(__file__)) == c3["tools"]["runnerSha256"], "C3 runner SHA-256 mismatch")
    root = c3_path.parent.parent
    base = load_module(root / c3["base"]["runner"], c3["base"]["runnerSha256"])
    if "--self-test" in sys.argv:
        checks = {
            "canonicalStable": canonical({"b": 2, "a": 1}) == b'{"a":1,"b":2}',
            "correctedToolOneLeaf": c3["correctedTool"]["changedFields"] == ["commonInputs[0].sha256"],
            "retainedAttemptRequired": c3["retainedAttempt01"]["immutable"] is True,
            "eightLogsRequired": c3["evidenceBinding"]["processLogFiles"] == 8,
        }
        require(all(checks.values()), "C3 self-test failed")
        result = base.main()
        require(result == 0, "base self-test failed")
        print(json.dumps({"status": "PASS", "c3Checks": checks}, sort_keys=True))
        return 0
    validate_authority(c3_path, c3)
    work = Path(option_value("--work-root"))
    evidence = Path(option_value("--evidence-root"))
    ceilings = c3["resources"]
    original_write = base.write_exclusive

    def c3_run_process(argv, cwd, env, stdout_path, stderr_path, timeout):
        require(not stdout_path.exists() and not stderr_path.exists(), "process log path must be fresh")
        started = time.monotonic()
        result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, timeout=timeout)
        write_bytes_exclusive(stdout_path, result.stdout)
        write_bytes_exclusive(stderr_path, result.stderr)
        return {
            "argv": argv,
            "exitCode": result.returncode,
            "wallSeconds": time.monotonic() - started,
            "stdoutSha256": sha256_bytes(result.stdout),
            "stderrSha256": sha256_bytes(result.stderr),
        }

    def c3_write(path: Path, value: object) -> None:
        if isinstance(value, dict) and value.get("schemaVersion") == "bfs.aiNativeStudioPb3ValidationReceipt.v0.1":
            work_manifest = regular_tree(work)
            evidence_manifest = regular_tree(evidence)
            require(work_manifest["regularFileBytes"] <= ceilings["maximumWorkRootBytes"], "work root exceeds C3 ceiling")
            body = dict(value)
            body.pop("receiptHash", None)
            body["resourceEnforcement"] = {
                "c3CorrectionSha256": sha256_file(c3_path),
                "workManifest": work_manifest,
                "evidenceManifestBeforeReceipt": evidence_manifest,
                "maximumWorkRootBytes": ceilings["maximumWorkRootBytes"],
                "maximumEvidenceRootBytes": ceilings["maximumEvidenceRootBytes"],
                "processLogsWrittenExclusively": True,
                "symbolicPathsAllowed": False,
            }
            while True:
                body["resourceEnforcement"]["receiptBytes"] = len((json.dumps({**body, "receiptHash": "0" * 64}, indent=2, ensure_ascii=False) + "\n").encode())
                projected = evidence_manifest["regularFileBytes"] + body["resourceEnforcement"]["receiptBytes"]
                if body["resourceEnforcement"].get("projectedEvidenceRootBytes") == projected:
                    break
                body["resourceEnforcement"]["projectedEvidenceRootBytes"] = projected
            require(projected <= ceilings["maximumEvidenceRootBytes"], "evidence root exceeds C3 ceiling")
            body["receiptHash"] = sha256_bytes(canonical(body))
            original_write(path, body)
            return
        original_write(path, value)

    base.run_process = c3_run_process
    base.write_exclusive = c3_write
    result = base.main()
    require(result == 0, "base PB.3 runner failed")
    receipt = json.loads((evidence / "receipt.json").read_text(encoding="utf-8"))
    resources = receipt["resourceEnforcement"]
    require(regular_tree(work) == resources["workManifest"], "work manifest changed after receipt")
    require(regular_tree(evidence)["regularFileBytes"] == resources["projectedEvidenceRootBytes"], "evidence bytes differ after receipt")
    verify_processes(c3)
    verify_retained_attempt(c3)
    print("PB3_VALIDATION_C3 PASS corrected input, resources, authority, argv and logs verified")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"PB3_VALIDATION_C3_STOP {type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1) from error
