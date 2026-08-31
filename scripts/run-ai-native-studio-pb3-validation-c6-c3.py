#!/usr/bin/env python3
"""PB.3 C6-C3 entrypoint with evidence-bounded HOME isolation."""

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


def option_value(name: str) -> str:
    require(sys.argv.count(name) == 1, f"{name} must appear exactly once")
    index = sys.argv.index(name)
    require(index + 1 < len(sys.argv), f"{name} value missing")
    return sys.argv[index + 1]


def tree_manifest(root: Path) -> dict:
    require(root.is_dir() and not root.is_symlink(), f"root is not exact: {root}")
    rows = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        require(not path.is_symlink(), f"symbolic path: {path}")
        if path.is_file():
            rows.append({"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    payload = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    return {"regularFiles": len(rows), "regularFileBytes": sum(row["bytes"] for row in rows), "manifestSha256": hashlib.sha256(payload).hexdigest()}


def retained_exact(tooling: dict) -> None:
    retained = tooling["retainedAttempt05"]
    require(tree_manifest(Path(retained["workRoot"])) == retained["workManifest"], "retained attempt-05 work root changed")
    evidence = Path(retained["evidenceRoot"])
    require(tree_manifest(evidence) == retained["evidenceManifest"], "retained attempt-05 evidence root changed")
    for record in retained["files"]:
        require(sha256_file(evidence / record["name"]) == record["sha256"], f"retained attempt-05 file changed: {record['name']}")


def load_runner(path: Path, expected_sha256: str):
    require(sha256_file(path) == expected_sha256, f"base runner changed: {path}")
    spec = importlib.util.spec_from_file_location("pb3_c6_c1_for_c6_c3", path)
    require(spec is not None and spec.loader is not None, "cannot load C6-C1 runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    tooling_path = Path(option_value("--c6-contract")).resolve(strict=True)
    tooling = json.loads(tooling_path.read_text(encoding="utf-8"))
    require(tooling.get("schemaVersion") == "bfs.aiNativeStudioPb3ValidationC6ExecutionToolFreeze.v1.13", "C6-C3 schema differs")
    require(tooling.get("status") == "FROZEN_INERT_C6_STANDING_AUTHORITY_TOOLING", "C6-C3 tooling is not frozen")
    require(sha256_file(Path(__file__)) == tooling["tools"]["runnerSha256"], "C6-C3 entrypoint hash differs")
    root = tooling_path.parent.parent
    c1_path = root / tooling["base"]["c6c1Runner"]
    c1 = load_runner(c1_path, tooling["base"]["c6c1RunnerSha256"])
    retained_exact(tooling)

    if "--self-test" in sys.argv:
        checks = {
            "c6c1RunnerExact": sha256_file(c1_path) == tooling["base"]["c6c1RunnerSha256"],
            "attempt05Retained": tooling["retainedAttempt05"]["immutable"] is True,
            "attempt06Fresh": not Path(tooling["paths"]["attempt04WorkRoot"]).exists() and not Path(tooling["paths"]["attempt04EvidenceRoot"]).exists(),
            "formalAuthorityGuardsPresent": STANDING_OWNER_GUARD in c1_path.read_text(encoding="utf-8") and HISTORICAL_CLAIM_GUARD in c1_path.read_text(encoding="utf-8"),
            "homeTargetWithinEvidence": tooling["homeIsolation"]["target"] == "evidenceRoot/isolation/<fixture>/home",
            "thresholdsUnchanged": tooling["acceptance"]["thresholdsUnchanged"] is True,
        }
        require(all(checks.values()), "C6-C3 self-test failed")
        print(json.dumps({"status": "PASS", "c6c3Checks": checks}, sort_keys=True))
        return 0

    original_c1_load = c1.load_module

    def environment_c5_load(path: Path, expected_sha256: str, name: str):
        c5 = original_c1_load(path, expected_sha256, name)
        original_c5_load = c5.load_module

        def environment_c4_load(c4_path: Path, c4_sha256: str):
            c4 = original_c5_load(c4_path, c4_sha256)
            if c4_path.name != "run-ai-native-studio-pb3-validation-c4.py":
                return c4
            original_c4_load = c4.load_module

            def environment_c3_load(c3_path: Path, c3_sha256: str):
                c3 = original_c4_load(c3_path, c3_sha256)
                if c3_path.name != "run-ai-native-studio-pb3-validation-c3.py":
                    return c3
                original_c3_load = c3.load_module

                def environment_base_load(base_path: Path, base_sha256: str):
                    semantic = original_c3_load(base_path, base_sha256)
                    if base_path.name == "run-ai-native-studio-pb3-validation.py":
                        original_environment = semantic.blender_environment

                        def evidence_home_environment(work_root: Path, fixture_id: str, semantic_tool: dict) -> dict[str, str]:
                            environment = original_environment(work_root, fixture_id, semantic_tool)
                            evidence_root = Path(option_value("--evidence-root"))
                            home = evidence_root / "isolation" / fixture_id.lower() / "home"
                            home.mkdir(parents=True, exist_ok=True)
                            environment["HOME"] = str(home)
                            return environment

                        semantic.blender_environment = evidence_home_environment
                    return semantic

                c3.load_module = environment_base_load
                return c3

            c4.load_module = environment_c3_load
            return c4

        c5.load_module = environment_c4_load
        return c5

    c1.load_module = environment_c5_load
    original_sha256 = c1.sha256_file
    c1_source = Path(c1.__file__).resolve(strict=True)
    entrypoint_sha256 = tooling["tools"]["runnerSha256"]

    def entrypoint_bound_sha256(path: Path) -> str:
        if path.resolve(strict=True) == c1_source:
            return entrypoint_sha256
        return original_sha256(path)

    c1.sha256_file = entrypoint_bound_sha256
    result = c1.main()
    require(result == 0, "C6-C1 delegated formal run failed")
    retained_exact(tooling)
    work_root = Path(option_value("--work-root"))
    require(not any(path.is_file() and path.suffix.lower() in {".exr", ".png", ".jpg", ".jpeg", ".mov", ".mp4"} for path in work_root.rglob("*")), "C6-C3 work root contains a render-like artifact")
    print("PB3_VALIDATION_C6_C3 PASS evidence-bounded HOME and unchanged semantics verified")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"PB3_VALIDATION_C6_C3_STOP {type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1) from error
