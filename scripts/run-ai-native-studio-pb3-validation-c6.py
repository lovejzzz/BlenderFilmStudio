#!/usr/bin/env python3
"""PB.3 C6 runner: standing-authority adapter over unchanged C5-C2 semantics."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path


C6_SCHEMA = "bfs.aiNativeStudioPb3ValidationC6ExecutionToolFreeze.v1.13"
C6_STATUS = "FROZEN_INERT_C6_STANDING_AUTHORITY_TOOLING"
EXECUTION_SCHEMA = "bfs.aiNativeStudioPb3StandingAuthorityExecution.v1.0"
EXECUTION_STATUS = "AUTHORIZED_UNDER_STANDING_AUTHORITY_FOR_ONE_FORMAL_RUN"


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
    spec = importlib.util.spec_from_file_location("pb3_c5_runner_for_c6", path)
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


def validate_c6_authority(c5_module, c6_path: Path, c6: dict, c4, c5_path: Path, c5: dict, _c4_path: Path, base_c4: dict) -> None:
    root = Path(option_value("--repository-root")).resolve(strict=True)
    tool_path = Path(option_value("--tool-contract")).resolve(strict=True)
    execution_path = Path(option_value("--execution-contract")).resolve(strict=True)
    execution = json.loads(execution_path.read_text(encoding="utf-8"))
    charter_path = root / c6["standingCharter"]["uri"]
    charter = json.loads(charter_path.read_text(encoding="utf-8"))
    historical_path = root / c6["historicalRequest"]["uri"]
    tool = json.loads(tool_path.read_text(encoding="utf-8"))

    require(execution.get("schemaVersion") == EXECUTION_SCHEMA, "standing execution schema differs")
    require(execution.get("status") == EXECUTION_STATUS, "PB.3 C6 execution is not authorized")
    require(sha256_file(tool_path) == c6["correctedTool"]["sha256"], "C6 corrected tool SHA-256 mismatch")
    require(execution.get("toolFreeze") == c6["correctedTool"], "execution does not bind corrected tool")
    require(execution.get("toolC4Correction") == c5["c4Binding"], "execution does not bind C4 tooling")
    require(execution.get("toolC5Correction") == c6["c5Binding"], "execution does not bind C5-C2 tooling")
    require(execution.get("toolC6Correction", {}).get("sha256") == sha256_file(c6_path), "execution does not bind C6 tooling")
    require(execution.get("standingCharter") == c6["standingCharter"], "execution does not bind standing charter")
    require(execution.get("historicalRequest") == c6["historicalRequest"], "execution does not bind historical unsupplied request")
    require(sha256_file(charter_path) == c6["standingCharter"]["sha256"], "standing charter hash differs")
    require(sha256_file(historical_path) == c6["historicalRequest"]["sha256"], "historical request changed")
    require(charter.get("status") == "ACTIVE_STANDING_AUTHORITY", "standing authority is not active")
    owner = charter["ownerAuthority"]
    authorization = execution.get("authorization", {})
    require(authorization.get("mode") == "STANDING_AUTONOMY", "standing authorization mode differs")
    require(authorization.get("ownerExactText") == owner["exactUserText"], "standing owner text differs")
    require(authorization.get("ownerExactTextSha256") == owner["exactUserTextSha256"] == sha256_bytes(owner["exactUserText"].encode()), "standing owner text SHA-256 differs")
    require(authorization.get("authorizedAtUtc"), "standing authorization time is absent")
    require("exactUserText" not in authorization and "authorizationRequest" not in execution, "historical exact authorization must not be claimed")
    require(execution.get("authorizedRun") == expected_run(), "authorized PB.3 C6 scope differs")
    require(execution.get("runner", {}).get("path") == c6["tools"]["runner"], "execution runner is not C6")
    require(execution.get("independentAuditor", {}).get("path") == c6["tools"]["independentAuditor"], "execution auditor is not C6")
    require(execution.get("stillUnauthorized") == tool["stillUnauthorized"], "unauthorized scope differs")
    contract_uri = execution_path.relative_to(root).as_posix()
    git = c4.c3_for_c5.git
    require(git(["diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"], root).splitlines() == [contract_uri], "execution commit must change only its contract")
    require(execution.get("executionParentResearchCommit") == git(["rev-parse", "HEAD^"], root), "execution parent mismatch")
    require(git(["status", "--porcelain"], root) == "", "research worktree must be clean")
    require("executionCommit" not in execution, "execution contract must not self-reference its commit")
    for frozen in (charter_path, historical_path, c6_path, c5_path, root / c5["c4Binding"]["uri"], tool_path):
        uri = frozen.relative_to(root).as_posix()
        require(git(["show", f"HEAD^:{uri}"], root, binary=True) == frozen.read_bytes(), f"execution parent does not freeze {uri}")
    c5_module.retained_exact(c4, c5, base_c4)
    inputs = [*tool["commonInputs"], *(record for fixture in tool["fixtures"] for record in fixture["inputs"])]
    require(len(inputs) == 13 and all(sha256_file(root / record["uri"]) == record["sha256"] for record in inputs), "C6 13-input roster is not exact")


def main() -> int:
    c6_path = Path(extract_option("--c6-contract")).resolve(strict=True)
    c6 = json.loads(c6_path.read_text(encoding="utf-8"))
    require(c6.get("schemaVersion") == C6_SCHEMA and c6.get("status") == C6_STATUS, "C6 execution tooling is not exact")
    require(sha256_file(Path(__file__)) == c6["tools"]["runnerSha256"], "C6 runner SHA-256 mismatch")
    root = c6_path.parent.parent
    c5_path = root / c6["c5Binding"]["uri"]
    require(sha256_file(c5_path) == c6["c5Binding"]["sha256"], "C5-C2 tooling changed")
    c5 = json.loads(c5_path.read_text(encoding="utf-8"))
    c5_module = load_module(root / c6["base"]["c5Runner"], c6["base"]["c5RunnerSha256"])
    sys.argv.extend(["--c5-contract", str(c5_path)])
    if "--self-test" in sys.argv:
        checks = {
            "standingCharterActive": json.loads((root / c6["standingCharter"]["uri"]).read_text(encoding="utf-8"))["status"] == "ACTIVE_STANDING_AUTHORITY",
            "historicalRequestNotAuthority": c6["historicalRequest"]["exactTextWasNotSupplied"] is True,
            "attempt04Fresh": not Path(c6["paths"]["attempt04WorkRoot"]).exists() and not Path(c6["paths"]["attempt04EvidenceRoot"]).exists(),
            "thresholdsUnchanged": c6["acceptance"]["thresholdsUnchanged"] is True,
        }
        require(all(checks.values()), "C6 self-test failed")
        result = c5_module.main()
        require(result == 0, "C5-C2 delegated self-test failed")
        print(json.dumps({"status": "PASS", "c6Checks": checks}, sort_keys=True))
        return 0

    def c6_authority(c4, c5_path_arg: Path, c5_contract: dict, c4_path_arg: Path, c4_contract: dict) -> None:
        validate_c6_authority(c5_module, c6_path, c6, c4, c5_path_arg, c5_contract, c4_path_arg, c4_contract)

    c5_module.validate_c5_authority = c6_authority
    result = c5_module.main()
    require(result == 0, "delegated C5-C2 semantic runner failed")
    receipt = json.loads((Path(option_value("--evidence-root")) / "receipt.json").read_text(encoding="utf-8"))
    require(receipt["counts"]["networkCalls"] == 0, "formal receipt network count differs")
    print("PB3_VALIDATION_C6 PASS standing authority and unchanged C5-C2 semantics verified")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"PB3_VALIDATION_C6_STOP {type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1) from error
