#!/usr/bin/env python3
"""PB.3 C5 runner: exact contract correction around unchanged C4 semantics."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path


C5_SCHEMA = "bfs.aiNativeStudioPb3ValidationC5ExecutionToolFreeze.v1.8"
C5_STATUS = "FROZEN_INERT_C5_EXECUTION_TOOLING"
EXECUTION_STATUS = "AUTHORIZED_FOR_ONE_FORMAL_RUN"


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
    del sys.argv[index:index + 2]
    return value


def option_value(name: str) -> str:
    require(sys.argv.count(name) == 1, f"{name} must appear exactly once")
    index = sys.argv.index(name)
    require(index + 1 < len(sys.argv), f"{name} value missing")
    return sys.argv[index + 1]


def load_module(path: Path, expected_sha256: str):
    require(sha256_file(path) == expected_sha256, f"module SHA-256 mismatch: {path}")
    spec = importlib.util.spec_from_file_location("pb3_c4_runner_for_c5", path)
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


def retained_exact(c4, c5: dict, base_c4: dict) -> None:
    c4.verify_retained(c4.c3_for_c5, base_c4)
    retained = c5["retainedAttempt03"]
    work = Path(retained["workRoot"])
    evidence = Path(retained["evidenceRoot"])
    require(not work.exists(), "retained attempt-03 work root changed")
    require(c4.c3_for_c5.regular_tree(evidence) == retained["evidenceManifest"], "retained attempt-03 evidence root changed")
    for record in retained["files"]:
        require(sha256_file(evidence / record["name"]) == record["sha256"], f"retained attempt-03 file changed: {record['name']}")


def validate_c5_authority(c4, c5_path: Path, c5: dict, _c4_path: Path, base_c4: dict) -> None:
    root = Path(option_value("--repository-root")).resolve(strict=True)
    tool_path = Path(option_value("--tool-contract")).resolve(strict=True)
    execution_path = Path(option_value("--execution-contract")).resolve(strict=True)
    execution = json.loads(execution_path.read_text(encoding="utf-8"))
    request_record = c5["authorizationRequest"]
    request_path = root / request_record["uri"]
    request = json.loads(request_path.read_text(encoding="utf-8"))
    require(execution.get("schemaVersion") == "bfs.aiNativeStudioPb3ValidationExecution.v0.3", "execution schema differs")
    require(execution.get("status") == EXECUTION_STATUS, "PB.3 C5 execution is not authorized")
    require(sha256_file(tool_path) == c5["correctedTool"]["sha256"], "C5 corrected tool SHA-256 mismatch")
    require(execution.get("toolFreeze") == c5["correctedTool"], "execution does not bind corrected tool")
    require(execution.get("toolC4Correction") == c5["c4Binding"], "execution does not bind C4 tooling")
    require(execution.get("toolC5Correction", {}).get("sha256") == sha256_file(c5_path), "execution does not bind C5 tooling")
    require(sha256_file(request_path) == request_record["sha256"] and execution.get("authorizationRequest") == request_record, "execution does not bind C5 authorization request")
    exact_text = request["requestedAuthorization"]["exactText"]
    authorization = execution.get("authorization", {})
    require(authorization.get("exactUserText") == exact_text, "exact PB.3 C5 authorization text differs")
    require(authorization.get("exactUserTextSha256") == sha256_bytes(exact_text.encode()), "PB.3 C5 authorization SHA-256 differs")
    require(authorization.get("explicitPb3ScopePresent") is True and authorization.get("authorizedAtUtc"), "explicit PB.3 C5 authority is absent")
    require(execution.get("authorizedRun") == expected_run(), "authorized PB.3 C5 scope differs")
    require(execution.get("runner", {}).get("path") == c5["tools"]["runner"], "execution runner is not C5")
    require(execution.get("independentAuditor", {}).get("path") == c5["tools"]["independentAuditor"], "execution auditor is not C5")
    require(execution.get("stillUnauthorized") == json.loads(tool_path.read_text(encoding="utf-8"))["stillUnauthorized"], "unauthorized scope differs")
    contract_uri = execution_path.relative_to(root).as_posix()
    require(c4.c3_for_c5.git(["diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"], root).splitlines() == [contract_uri], "execution commit must change only its contract")
    require(execution.get("executionParentResearchCommit") == c4.c3_for_c5.git(["rev-parse", "HEAD^"], root), "execution parent mismatch")
    require(c4.c3_for_c5.git(["status", "--porcelain"], root) == "", "research worktree must be clean")
    require("executionCommit" not in execution, "execution contract must not self-reference its commit")
    for frozen in (request_path, c5_path, tool_path, root / c5["c4Binding"]["uri"]):
        uri = frozen.relative_to(root).as_posix()
        require(c4.c3_for_c5.git(["show", f"HEAD^:{uri}"], root, binary=True) == frozen.read_bytes(), f"execution parent does not freeze {uri}")
    retained_exact(c4, c5, base_c4)
    tool = json.loads(tool_path.read_text(encoding="utf-8"))
    inputs = [*tool["commonInputs"], *(record for fixture in tool["fixtures"] for record in fixture["inputs"])]
    require(len(inputs) == 13 and all(sha256_file(root / record["uri"]) == record["sha256"] for record in inputs), "C5 13-input roster is not exact")


def main() -> int:
    c5_path = Path(extract_option("--c5-contract")).resolve(strict=True)
    c5 = json.loads(c5_path.read_text(encoding="utf-8"))
    require(c5.get("schemaVersion") == C5_SCHEMA and c5.get("status") == C5_STATUS, "C5 execution tooling is not exact")
    require(sha256_file(Path(__file__)) == c5["tools"]["runnerSha256"], "C5 runner SHA-256 mismatch")
    root = c5_path.parent.parent
    c4_path = root / c5["c4Binding"]["uri"]
    require(sha256_file(c4_path) == c5["c4Binding"]["sha256"], "C4 tooling changed")
    base_c4 = json.loads(c4_path.read_text(encoding="utf-8"))
    c4 = load_module(root / c5["base"]["c4Runner"], c5["base"]["c4RunnerSha256"])
    c3_path = root / base_c4["base"]["c3ExecutionToolFreeze"]
    c4.c3_for_c5 = load_module(root / base_c4["base"]["c3Runner"], base_c4["base"]["c3RunnerSha256"])
    require(sha256_file(c3_path) == base_c4["base"]["c3ExecutionToolFreezeSha256"], "C3 tooling changed")
    sys.argv.extend(["--c4-contract", str(c4_path)])
    if "--self-test" in sys.argv:
        checks = {
            "c4RunnerUnchanged": sha256_file(root / c5["base"]["c4Runner"]) == c5["base"]["c4RunnerSha256"],
            "attempt03Immutable": c5["retainedAttempt03"]["immutable"] is True,
            "attempt04Fresh": not Path(c5["paths"]["attempt04WorkRoot"]).exists() and not Path(c5["paths"]["attempt04EvidenceRoot"]).exists(),
            "zeroNetwork": c5["acceptance"]["networkCalls"] == 0,
        }
        require(all(checks.values()), "C5 self-test failed")
        result = c4.main()
        require(result == 0, "C4 delegated self-test failed")
        print(json.dumps({"status": "PASS", "c5Checks": checks}, sort_keys=True))
        return 0

    def c5_authority(c4_path_arg: Path, c4_contract: dict) -> None:
        validate_c5_authority(c4, c5_path, c5, c4_path_arg, c4_contract)

    c4.validate_c4_authority = c5_authority
    result = c4.main()
    require(result == 0, "delegated C4 semantic runner failed")
    retained_exact(c4, c5, base_c4)
    receipt = json.loads((Path(option_value("--evidence-root")) / "receipt.json").read_text(encoding="utf-8"))
    require(receipt["counts"]["networkCalls"] == 0, "formal receipt network count differs")
    print("PB3_VALIDATION_C5 PASS exact scope, retained attempt-03 and unchanged C4 semantics verified")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"PB3_VALIDATION_C5_STOP {type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1) from error
