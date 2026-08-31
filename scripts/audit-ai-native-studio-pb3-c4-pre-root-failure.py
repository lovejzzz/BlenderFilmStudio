#!/usr/bin/env python3
"""Independently audit the retained PB.3 C4 attempt-03 pre-root failure."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def git(args: list[str], cwd: Path) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def tree_manifest(root: Path) -> dict:
    if not root.is_dir() or root.is_symlink():
        raise RuntimeError(f"root is not an exact directory: {root}")
    rows = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        if path.is_symlink():
            raise RuntimeError(f"root contains symbolic path: {path}")
        if path.is_file():
            rows.append({
                "path": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            })
    return {
        "regularFiles": len(rows),
        "regularFileBytes": sum(row["bytes"] for row in rows),
        "manifestSha256": sha256_bytes(canonical(rows)),
    }


def write_exclusive(path: Path, value: object) -> None:
    payload = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        os.write(descriptor, payload)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--failure", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    root = args.repository_root.resolve(strict=True)
    failure_path = args.failure.resolve(strict=True)
    output = args.output.resolve(strict=False)
    failure = json.loads(failure_path.read_text(encoding="utf-8"))
    execution_path = root / failure["executionContract"]["uri"]
    execution = json.loads(execution_path.read_text(encoding="utf-8"))
    tool_path = root / failure["toolBindings"]["correctedTool"]["uri"]
    tool = json.loads(tool_path.read_text(encoding="utf-8"))
    c4_path = root / failure["toolBindings"]["c4"]["uri"]
    work = Path(failure["rootStateAtStop"]["workRoot"])
    evidence = Path(failure["rootStateAtStop"]["evidenceRoot"])
    source = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PhaseB-workspace/PB.1-2026-08-31-mac-m2max-attempt-04/source")
    binary = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PhaseB-workspace/PB.1-2026-08-31-mac-m2max-attempt-04/build/bin/Film Studio Engine F0.app/Contents/MacOS/Blender")

    failure_body = dict(failure)
    recorded_failure_hash = failure_body.pop("failureHash")
    expected_scope = tool["stillUnauthorized"]
    observed_scope = execution["stillUnauthorized"]
    differing = [index for index, pair in enumerate(zip(expected_scope, observed_scope, strict=True)) if pair[0] != pair[1]]
    evidence_before_audit = tree_manifest(evidence)
    retained_expected = {
        "attempt01": {
            "work": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
            "evidence": "cc50ac9fc2366965cca73db9e1d1240c9d31d435c20fdfda05f03ca50c432754",
        },
        "attempt02": {
            "work": "6b12f0b8f2545a3463902638540a87981542a7f202b3cef161ad482458c97ca8",
            "evidence": "4d0930b596128fcaf3019777cc586046f4c5b10fc1a11bf60536a12c9620262e",
        },
    }
    retained_roots = {
        "attempt01": (
            Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PhaseB-workspace/PB.3-2026-08-31-mac-m2max-attempt-01"),
            root / "experiments/ai-native-studio-phase-b/PB.3-2026-08-31-mac-m2max-attempt-01",
        ),
        "attempt02": (
            Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PhaseB-workspace/PB.3-2026-08-31-mac-m2max-attempt-02"),
            root / "experiments/ai-native-studio-phase-b/PB.3-2026-08-31-mac-m2max-attempt-02",
        ),
    }
    retained_actual = {
        key: {"work": tree_manifest(paths[0]), "evidence": tree_manifest(paths[1])}
        for key, paths in retained_roots.items()
    }
    render_like = [
        path for path in evidence.rglob("*")
        if path.is_file() and path.suffix.lower() in {".exr", ".png", ".jpg", ".jpeg", ".mov", ".mp4"}
    ]
    checks = {
        "failureSchemaStatusStage": failure.get("schemaVersion") == "bfs.aiNativeStudioPb3ValidationC4Failure.v0.1" and failure.get("status") == "FAIL" and failure.get("failedStage") == "PRE_ROOT_AUTHORIZED_SCOPE_BINDING",
        "failureSelfHash": recorded_failure_hash == sha256_bytes(canonical(failure_body)),
        "executionContractHash": sha256_file(execution_path) == failure["executionContract"]["sha256"],
        "executionCommitExact": git(["rev-parse", failure["executionCommit"]], root) == failure["executionCommit"],
        "executionParentExact": git(["rev-parse", f"{failure['executionCommit']}^"], root) == failure["executionParentResearchCommit"],
        "executionSinglePath": git(["diff-tree", "--no-commit-id", "--name-only", "-r", failure["executionCommit"]], root).splitlines() == [failure["executionContract"]["uri"]],
        "frozenToolHashes": sha256_file(tool_path) == failure["toolBindings"]["correctedTool"]["sha256"] and sha256_file(c4_path) == failure["toolBindings"]["c4"]["sha256"],
        "scopeLengthExact": len(expected_scope) == len(observed_scope) == 5,
        "scopeSingleMismatch": differing == [0],
        "scopeMismatchExact": expected_scope[0] == failure["failure"]["frozenExpected"] and observed_scope[0] == failure["failure"]["executionObserved"],
        "scopeOtherItemsExact": expected_scope[1:] == observed_scope[1:],
        "runnerMessageExact": failure["failure"]["runnerMessage"] == "PB3_VALIDATION_C4_STOP RuntimeError: unauthorized scope differs",
        "workRootAbsent": not work.exists(),
        "evidenceBeforeAuditExact": evidence_before_audit["regularFiles"] == 1 and evidence_before_audit["regularFileBytes"] == failure_path.stat().st_size,
        "noFormalReceiptOrLogs": not (evidence / "receipt.json").exists() and not any(evidence.rglob("*.log")),
        "noRenderLikeArtifacts": not render_like,
        "zeroBlenderAndMutationCounts": all(failure["counts"][key] == 0 for key in ("blenderStarts", "proposalExecutions", "buildPlanWrites", "sceneBuilds", "workspaceSaves", "reopens", "renders", "engineSourceEdits", "engineRemoteWrites")),
        "networkDeviationDisclosed": failure["counts"]["networkCalls"] == 1 and failure["protocolDeviation"]["networkCalls"] == 1 and failure["protocolDeviation"]["remoteWrites"] == 0,
        "sourceIdentityClean": git(["rev-parse", "HEAD"], source) == failure["identityAtStop"]["engineSourceHead"] and git(["status", "--porcelain"], source) == "",
        "binaryIdentityExact": sha256_file(binary) == failure["identityAtStop"]["binarySha256"],
        "retainedAttempt01Exact": retained_actual["attempt01"]["work"]["manifestSha256"] == retained_expected["attempt01"]["work"] and retained_actual["attempt01"]["evidence"]["manifestSha256"] == retained_expected["attempt01"]["evidence"],
        "retainedAttempt02Exact": retained_actual["attempt02"]["work"]["manifestSha256"] == retained_expected["attempt02"]["work"] and retained_actual["attempt02"]["evidence"]["manifestSha256"] == retained_expected["attempt02"]["evidence"],
    }
    passed = sum(checks.values())
    audit = {
        "schemaVersion": "bfs.aiNativeStudioPb3ValidationC4FailureAudit.v0.1",
        "status": "PASS" if passed == len(checks) else "FAIL",
        "checks": checks,
        "counts": {"passed": passed, "total": len(checks), **failure["counts"]},
        "failure": {"uri": failure_path.relative_to(root).as_posix(), "fileSha256": sha256_file(failure_path), "failureHash": recorded_failure_hash},
        "scopeMismatch": {"jsonPath": "$.stillUnauthorized[0]", "expected": expected_scope[0], "observed": observed_scope[0]},
        "evidenceManifestBeforeAudit": evidence_before_audit,
        "retainedManifests": retained_actual,
        "claimCeiling": "Independent retained-failure proof only. No Blender process or attempt-03 work root was created; one disclosed read-only network call exceeded the zero-network ceiling. This audit grants no new execution authority.",
    }
    audit["auditHash"] = sha256_bytes(canonical(audit))
    write_exclusive(output, audit)
    print(json.dumps({"status": audit["status"], "passed": passed, "total": len(checks), "auditHash": audit["auditHash"]}, sort_keys=True))
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
