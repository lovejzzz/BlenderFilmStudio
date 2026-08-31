#!/usr/bin/env python3
"""PB.3 C6-C1 runner: closure-guarded nested authority over frozen semantics."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path


TOOL_SCHEMA = "bfs.aiNativeStudioPb3ValidationC6ExecutionToolFreeze.v1.13"
TOOL_STATUS = "FROZEN_INERT_C6_STANDING_AUTHORITY_TOOLING"
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
    return sys.argv[sys.argv.index(name) + 1]


def load_module(path: Path, expected_sha256: str, name: str):
    require(sha256_file(path) == expected_sha256, f"module SHA-256 mismatch: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def tree_manifest(root: Path) -> dict:
    require(root.is_dir() and not root.is_symlink(), f"root is not exact: {root}")
    rows = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        require(not path.is_symlink(), f"symbolic path: {path}")
        if path.is_file():
            rows.append({"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    payload = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    return {"regularFiles": len(rows), "regularFileBytes": sum(row["bytes"] for row in rows), "manifestSha256": sha256_bytes(payload)}


def expected_run() -> dict:
    return {
        "repositoryRoot": str(Path(option_value("--repository-root")).resolve(strict=True)),
        "engineSource": str(Path(option_value("--engine-source"))),
        "binary": str(Path(option_value("--binary"))),
        "workRoot": str(Path(option_value("--work-root"))),
        "evidenceRoot": str(Path(option_value("--evidence-root"))),
        "benchmarks": ["B01", "B02"],
        "blenderStarts": 4, "proposalExecutions": 2, "buildPlanWrites": 2,
        "sceneBuilds": 2, "workspaceSaves": 2, "reopens": 2,
        "renders": 0, "engineSourceEdits": 0, "engineRemoteWrites": 0, "networkCalls": 0,
    }


def retained_attempt04_exact(tooling: dict) -> None:
    retained = tooling["retainedAttempt04"]
    work = Path(retained["workRoot"])
    evidence = Path(retained["evidenceRoot"])
    require(not work.exists(), "retained attempt-04 work root changed")
    require(tree_manifest(evidence) == retained["evidenceManifest"], "retained attempt-04 evidence root changed")
    for record in retained["files"]:
        require(sha256_file(evidence / record["name"]) == record["sha256"], f"retained attempt-04 file changed: {record['name']}")


def main() -> int:
    tooling_path = Path(extract_option("--c6-contract")).resolve(strict=True)
    tooling = json.loads(tooling_path.read_text(encoding="utf-8"))
    require(tooling.get("schemaVersion") == TOOL_SCHEMA and tooling.get("status") == TOOL_STATUS, "C6-C1 tooling mismatch")
    require(sha256_file(Path(__file__)) == tooling["tools"]["runnerSha256"], "C6-C1 runner SHA-256 mismatch")
    root = tooling_path.parent.parent
    c5_path = root / tooling["c5Binding"]["uri"]
    require(sha256_file(c5_path) == tooling["c5Binding"]["sha256"], "C5-C2 tooling changed")
    c5 = json.loads(c5_path.read_text(encoding="utf-8"))
    c5_module = load_module(root / tooling["base"]["c5Runner"], tooling["base"]["c5RunnerSha256"], "pb3_c5_for_c6_c1")
    authority_state = {"validated": False}

    original_c5_load = c5_module.load_module

    def guarded_c5_load(path: Path, expected_sha256: str):
        module = original_c5_load(path, expected_sha256)
        if path.name != "run-ai-native-studio-pb3-validation-c4.py":
            return module
        original_c4_load = module.load_module

        def guarded_c4_load(nested_path: Path, nested_sha256: str):
            nested = original_c4_load(nested_path, nested_sha256)
            if nested_path.name != "run-ai-native-studio-pb3-validation-c3.py":
                return nested
            original_c3_load = nested.load_module

            def guarded_c3_load(base_path: Path, base_sha256: str):
                base = original_c3_load(base_path, base_sha256)
                if base_path.name == "run-ai-native-studio-pb3-validation.py":
                    def validated_base_authority(_parsed, base_root: Path, _tool, _execution) -> str:
                        require(authority_state["validated"], "nested base authority reached before standing authority")
                        return nested.git(["rev-parse", "HEAD"], base_root)
                    base.validate_authority = validated_base_authority
                return base

            nested.load_module = guarded_c3_load
            return nested

        module.load_module = guarded_c4_load
        return module

    c5_module.load_module = guarded_c5_load
    sys.argv.extend(["--c5-contract", str(c5_path)])

    if "--self-test" in sys.argv:
        checks = {
            "attempt04Retained": tooling["retainedAttempt04"]["immutable"] is True,
            "attempt05Fresh": not Path(tooling["paths"]["attempt04WorkRoot"]).exists() and not Path(tooling["paths"]["attempt04EvidenceRoot"]).exists(),
            "closureInitiallyFalse": authority_state["validated"] is False,
            "thresholdsUnchanged": tooling["acceptance"]["thresholdsUnchanged"] is True,
        }
        retained_attempt04_exact(tooling)
        require(all(checks.values()), "C6-C1 self-test failed")
        result = c5_module.main()
        require(result == 0, "delegated C5-C2 self-test failed")
        print(json.dumps({"status": "PASS", "c6c1Checks": checks}, sort_keys=True))
        return 0

    def validate_standing_authority(c4, c5_path_arg: Path, c5_contract: dict, _c4_path: Path, base_c4: dict) -> None:
        repository = Path(option_value("--repository-root")).resolve(strict=True)
        tool_path = Path(option_value("--tool-contract")).resolve(strict=True)
        execution_path = Path(option_value("--execution-contract")).resolve(strict=True)
        execution = json.loads(execution_path.read_text(encoding="utf-8"))
        charter_path = repository / tooling["standingCharter"]["uri"]
        charter = json.loads(charter_path.read_text(encoding="utf-8"))
        historical_path = repository / tooling["historicalRequest"]["uri"]
        semantic_tool = json.loads(tool_path.read_text(encoding="utf-8"))
        require(execution.get("schemaVersion") == EXECUTION_SCHEMA and execution.get("status") == EXECUTION_STATUS, "PB.3 C6 execution is not authorized")
        require(sha256_file(tool_path) == tooling["correctedTool"]["sha256"] and execution.get("toolFreeze") == tooling["correctedTool"], "corrected tool binding differs")
        require(execution.get("toolC4Correction") == c5_contract["c4Binding"], "C4 binding differs")
        require(execution.get("toolC5Correction") == tooling["c5Binding"], "C5 binding differs")
        require(execution.get("toolC6Correction", {}).get("uri") == tooling_path.relative_to(repository).as_posix() and execution.get("toolC6Correction", {}).get("sha256") == sha256_file(tooling_path), "C6-C1 binding differs")
        require(execution.get("standingCharter") == tooling["standingCharter"] and sha256_file(charter_path) == tooling["standingCharter"]["sha256"], "standing charter binding differs")
        require(execution.get("historicalRequest") == tooling["historicalRequest"] and sha256_file(historical_path) == tooling["historicalRequest"]["sha256"], "historical request binding differs")
        owner = charter["ownerAuthority"]
        authorization = execution.get("authorization", {})
        require(charter.get("status") == "ACTIVE_STANDING_AUTHORITY" and authorization.get("mode") == "STANDING_AUTONOMY", "standing authority inactive")
        require(authorization.get("ownerExactText") == owner["exactUserText"] and authorization.get("ownerExactTextSha256") == owner["exactUserTextSha256"] == sha256_bytes(owner["exactUserText"].encode()), "standing owner binding differs")
        require(authorization.get("authorizedAtUtc") and "exactUserText" not in authorization and "authorizationRequest" not in execution, "historical exact authorization was claimed")
        require(execution.get("authorizedRun") == expected_run(), "authorized run differs")
        require(execution.get("runner", {}).get("path") == tooling["tools"]["runner"] and execution.get("independentAuditor", {}).get("path") == tooling["tools"]["independentAuditor"], "formal tools differ")
        require(execution.get("stillUnauthorized") == semantic_tool["stillUnauthorized"], "unauthorized scope differs")
        contract_uri = execution_path.relative_to(repository).as_posix()
        git = c4.c3_for_c5.git
        require(git(["diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"], repository).splitlines() == [contract_uri], "execution commit must change only its contract")
        require(execution.get("executionParentResearchCommit") == git(["rev-parse", "HEAD^"], repository), "execution parent differs")
        require(git(["status", "--porcelain"], repository) == "", "research worktree must be clean")
        for frozen in (charter_path, historical_path, tooling_path, c5_path_arg, repository / c5_contract["c4Binding"]["uri"], tool_path):
            uri = frozen.relative_to(repository).as_posix()
            require(git(["show", f"HEAD^:{uri}"], repository, binary=True) == frozen.read_bytes(), f"execution parent does not freeze {uri}")
        c5_module.retained_exact(c4, c5_contract, base_c4)
        retained_attempt04_exact(tooling)
        inputs = [*semantic_tool["commonInputs"], *(record for fixture in semantic_tool["fixtures"] for record in fixture["inputs"])]
        require(len(inputs) == 13 and all(sha256_file(repository / record["uri"]) == record["sha256"] for record in inputs), "13-input roster differs")
        authority_state["validated"] = True

    c5_module.validate_c5_authority = validate_standing_authority
    result = c5_module.main()
    require(result == 0, "delegated C5-C2 semantic runner failed")
    require(authority_state["validated"], "standing authority was not validated")
    retained_attempt04_exact(tooling)
    receipt = json.loads((Path(option_value("--evidence-root")) / "receipt.json").read_text(encoding="utf-8"))
    require(receipt["counts"]["networkCalls"] == 0, "formal receipt network count differs")
    print("PB3_VALIDATION_C6_C1 PASS guarded nested authority and unchanged C5-C2 semantics verified")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"PB3_VALIDATION_C6_C1_STOP {type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1) from error
