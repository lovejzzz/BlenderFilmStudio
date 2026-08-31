#!/usr/bin/env python3
"""PB.3 C6-C2 entrypoint with retained-attempt-aware self-test."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path


STANDING_OWNER_GUARD = 'authorization.get("ownerExactText") == owner["exactUserText"]'
HISTORICAL_CLAIM_GUARD = '"exactUserText" not in authorization and "authorizationRequest" not in execution'


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def tree_manifest(root: Path) -> dict:
    require(root.is_dir() and not root.is_symlink(), f"root is not exact: {root}")
    rows = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        require(not path.is_symlink(), f"symbolic path: {path}")
        if path.is_file():
            rows.append({"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    payload = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    return {"regularFiles": len(rows), "regularFileBytes": sum(row["bytes"] for row in rows), "manifestSha256": hashlib.sha256(payload).hexdigest()}


def contract_path() -> Path:
    require(sys.argv.count("--c6-contract") == 1, "--c6-contract must appear exactly once")
    index = sys.argv.index("--c6-contract")
    require(index + 1 < len(sys.argv), "--c6-contract value missing")
    return Path(sys.argv[index + 1]).resolve(strict=True)


def load_runner(path: Path, expected_sha256: str):
    require(sha256_file(path) == expected_sha256, "C6-C1 base runner changed")
    spec = importlib.util.spec_from_file_location("pb3_c6_c1_for_c6_c2", path)
    require(spec is not None and spec.loader is not None, "cannot load C6-C1 base runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    tooling_path = contract_path()
    tooling = json.loads(tooling_path.read_text(encoding="utf-8"))
    require(tooling.get("schemaVersion") == "bfs.aiNativeStudioPb3ValidationC6ExecutionToolFreeze.v1.13", "C6-C2 schema differs")
    require(tooling.get("status") == "FROZEN_INERT_C6_STANDING_AUTHORITY_TOOLING", "C6-C2 tooling is not frozen")
    require(sha256_file(Path(__file__)) == tooling["tools"]["runnerSha256"], "C6-C2 entrypoint hash differs")
    root = tooling_path.parent.parent
    base_path = root / tooling["base"]["c6c1Runner"]
    base = load_runner(base_path, tooling["base"]["c6c1RunnerSha256"])
    retained = tooling["retainedAttempt04"]

    if "--self-test" in sys.argv:
        evidence = Path(retained["evidenceRoot"])
        checks = {
            "baseRunnerExact": sha256_file(base_path) == tooling["base"]["c6c1RunnerSha256"],
            "retainedAttempt04WorkAbsent": not Path(retained["workRoot"]).exists(),
            "retainedAttempt04EvidenceExact": tree_manifest(evidence) == retained["evidenceManifest"] and all(sha256_file(evidence / record["name"]) == record["sha256"] for record in retained["files"]),
            "attempt05Fresh": not Path(tooling["paths"]["attempt04WorkRoot"]).exists() and not Path(tooling["paths"]["attempt04EvidenceRoot"]).exists(),
            "formalAuthorityGuardsPresent": STANDING_OWNER_GUARD in base_path.read_text(encoding="utf-8") and HISTORICAL_CLAIM_GUARD in base_path.read_text(encoding="utf-8"),
            "thresholdsUnchanged": tooling["acceptance"]["thresholdsUnchanged"] is True,
        }
        require(all(checks.values()), "C6-C2 self-test failed")
        print(json.dumps({"status": "PASS", "c6c2Checks": checks}, sort_keys=True))
        return 0

    original_sha256_file = base.sha256_file
    base_source = Path(base.__file__).resolve(strict=True)
    entrypoint_sha256 = tooling["tools"]["runnerSha256"]

    def entrypoint_bound_sha256(path: Path) -> str:
        if path.resolve(strict=True) == base_source:
            return entrypoint_sha256
        return original_sha256_file(path)

    base.sha256_file = entrypoint_bound_sha256
    return base.main()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"PB3_VALIDATION_C6_C2_STOP {type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1) from error
