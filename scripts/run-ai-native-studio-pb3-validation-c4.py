#!/usr/bin/env python3
"""PB.3 C4 runner: normalize argv and preserve the frozen C3 semantics."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path


C4_SCHEMA = "bfs.aiNativeStudioPb3ValidationC4ExecutionToolFreeze.v1.2"
C4_STATUS = "FROZEN_INERT_C4_EXECUTION_TOOLING"
EXECUTION_STATUS = "AUTHORIZED_FOR_ONE_FORMAL_RUN"
FORBIDDEN_ARTIFACT_SUFFIXES = {".exr", ".png", ".jpg", ".jpeg", ".mov", ".mp4"}


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
    require(index + 1 < len(sys.argv), f"{name} value missing")
    value = sys.argv[index + 1]
    del sys.argv[index : index + 2]
    return value


def option_value(name: str) -> str:
    require(sys.argv.count(name) == 1, f"{name} must appear exactly once")
    index = sys.argv.index(name)
    require(index + 1 < len(sys.argv), f"{name} value missing")
    return sys.argv[index + 1]


def replace_option(name: str, value: str) -> None:
    require(sys.argv.count(name) == 1, f"{name} must appear exactly once")
    sys.argv[sys.argv.index(name) + 1] = value


def load_module(path: Path, expected_sha256: str):
    require(sha256_file(path) == expected_sha256, f"module SHA-256 mismatch: {path}")
    spec = importlib.util.spec_from_file_location("pb3_c3_runner_for_c4", path)
    require(spec is not None and spec.loader is not None, f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expected_run() -> dict:
    return {
        "repositoryRoot": str(Path(option_value("--repository-root")).resolve(strict=True)),
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


def verify_retained(c3, c4: dict) -> None:
    for retained in c4["retainedAttempts"]:
        work = Path(retained["workRoot"])
        evidence = Path(retained["evidenceRoot"])
        require(c3.regular_tree(work) == retained["workManifest"], f"{retained['id']} work root changed")
        require(c3.regular_tree(evidence) == retained["evidenceManifest"], f"{retained['id']} evidence root changed")
        for record in retained.get("files", []):
            require(sha256_file(evidence / record["name"]) == record["sha256"], f"{retained['id']} file changed: {record['name']}")


def validate_c4_authority(c3, c4_path: Path, c4: dict) -> None:
    root = Path(option_value("--repository-root")).resolve(strict=True)
    tool_path = Path(option_value("--tool-contract")).resolve(strict=True)
    execution_path = Path(option_value("--execution-contract")).resolve(strict=True)
    execution = json.loads(execution_path.read_text(encoding="utf-8"))
    request_record = c4["authorizationRequest"]
    request_path = root / request_record["uri"]
    request = json.loads(request_path.read_text(encoding="utf-8"))
    require(execution.get("schemaVersion") == "bfs.aiNativeStudioPb3ValidationExecution.v0.3", "execution schema differs")
    require(execution.get("status") == EXECUTION_STATUS, "PB.3 C4 execution is not authorized")
    require(sha256_file(tool_path) == c4["correctedTool"]["sha256"], "C4 corrected tool SHA-256 mismatch")
    require(execution.get("toolFreeze") == c4["correctedTool"], "execution does not bind C4 corrected tool")
    require(execution.get("toolC4Correction", {}).get("sha256") == sha256_file(c4_path), "execution does not bind C4 tooling")
    require(sha256_file(request_path) == request_record["sha256"] and execution.get("authorizationRequest") == request_record, "execution does not bind C4 authorization request")
    exact_text = request["requestedAuthorization"]["exactText"]
    authorization = execution.get("authorization", {})
    require(authorization.get("exactUserText") == exact_text, "exact PB.3 C4 authorization text differs")
    require(authorization.get("exactUserTextSha256") == sha256_bytes(exact_text.encode()), "PB.3 C4 authorization SHA-256 differs")
    require(authorization.get("explicitPb3ScopePresent") is True and authorization.get("authorizedAtUtc"), "explicit PB.3 C4 authority is absent")
    require(execution.get("authorizedRun") == expected_run(), "authorized PB.3 C4 scope differs")
    require(execution.get("runner", {}).get("path") == c4["tools"]["runner"], "execution runner is not C4")
    require(execution.get("independentAuditor", {}).get("path") == c4["tools"]["independentAuditor"], "execution auditor is not C4")
    contract_uri = execution_path.relative_to(root).as_posix()
    require(c3.git(["diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"], root).splitlines() == [contract_uri], "execution commit must change only its contract")
    require(execution.get("executionParentResearchCommit") == c3.git(["rev-parse", "HEAD^"], root), "execution parent mismatch")
    require(c3.git(["status", "--porcelain"], root) == "", "research worktree must be clean")
    require("executionCommit" not in execution, "execution contract must not self-reference its commit")
    for frozen in (request_path, c4_path, tool_path):
        uri = frozen.relative_to(root).as_posix()
        require(c3.git(["show", f"HEAD^:{uri}"], root, binary=True) == frozen.read_bytes(), f"execution parent does not freeze {uri}")
    verify_retained(c3, c4)
    tool = json.loads(tool_path.read_text(encoding="utf-8"))
    input_records = [*tool["commonInputs"], *(record for fixture in tool["fixtures"] for record in fixture["inputs"])]
    require(len(input_records) == 13 and all(sha256_file(root / record["uri"]) == record["sha256"] for record in input_records), "C4 13-input roster is not exact")


def main() -> int:
    c4_path = Path(extract_option("--c4-contract")).resolve(strict=True)
    c4 = json.loads(c4_path.read_text(encoding="utf-8"))
    require(c4.get("schemaVersion") == C4_SCHEMA and c4.get("status") == C4_STATUS, "C4 execution tooling is not exact")
    require(sha256_file(Path(__file__)) == c4["tools"]["runnerSha256"], "C4 runner SHA-256 mismatch")
    root = c4_path.parent.parent
    c3_path = root / c4["base"]["c3ExecutionToolFreeze"]
    require(sha256_file(c3_path) == c4["base"]["c3ExecutionToolFreezeSha256"], "C3 execution tool freeze changed")
    c3 = load_module(root / c4["base"]["c3Runner"], c4["base"]["c3RunnerSha256"])
    sys.argv.extend(["--c3-contract", str(c3_path)])
    if "--self-test" in sys.argv:
        checks = {
            "absoluteNormalization": str(Path(root / "specs").resolve()).startswith("/"),
            "previewHelperVersioned": c4["correctedTool"]["blenderHelperChangedLines"] == 2,
            "retainedAttempts": [row["id"] for row in c4["retainedAttempts"]] == ["attempt-01", "attempt-02"],
            "thresholdsUnchanged": c4["acceptance"]["thresholdsUnchanged"] is True,
        }
        require(all(checks.values()), "C4 self-test failed")
        result = c3.main()
        require(result == 0, "C3 delegated self-test failed")
        print(json.dumps({"status": "PASS", "c4Checks": checks}, sort_keys=True))
        return 0
    absolute_tool = str(Path(option_value("--tool-contract")).resolve(strict=True))
    replace_option("--tool-contract", absolute_tool)

    def c4_authority(_c3_path: Path, _c3_contract: dict) -> None:
        validate_c4_authority(c3, c4_path, c4)

    c3.validate_authority = c4_authority
    result = c3.main()
    require(result == 0, "delegated C3 semantic runner failed")
    work = Path(option_value("--work-root"))
    forbidden = [path for path in work.rglob("*") if path.is_file() and path.suffix.lower() in FORBIDDEN_ARTIFACT_SUFFIXES]
    require(not forbidden, "C4 work root contains a render-like artifact")
    verify_retained(c3, c4)
    print("PB3_VALIDATION_C4 PASS absolute argv and preview suppression verified")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"PB3_VALIDATION_C4_STOP {type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1) from error
