#!/usr/bin/env python3
"""Independent audit for retained PB.3 C2 attempt-01 pre-start failure."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--engine-source", type=Path, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--correction", type=Path, required=True)
    parser.add_argument("--failure", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def valid_self(document: dict, field: str) -> bool:
    body = dict(document)
    claimed = body.pop(field, None)
    return isinstance(claimed, str) and claimed == sha256_bytes(canonical(body))


def git(args: list[str], cwd: Path, binary: bool = False):
    result = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=not binary)
    return result.stdout if binary else result.stdout.strip()


def regular_files(root: Path) -> list[Path]:
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise RuntimeError(f"retained root contains symbolic path: {path}")
        if path.is_file():
            files.append(path)
    return files


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


def main() -> int:
    args = arguments()
    root = args.repository_root.resolve(strict=True)
    engine = args.engine_source.resolve(strict=True)
    binary = args.binary.resolve(strict=True)
    correction = json.loads(args.correction.read_text(encoding="utf-8"))
    failure = json.loads(args.failure.read_text(encoding="utf-8"))
    require_schema = correction.get("schemaVersion") == "bfs.aiNativeStudioPb3ValidationC3InputHashCorrection.v0.7"
    tool_path = root / failure["toolBindings"]["base"]["uri"]
    tool = json.loads(tool_path.read_text(encoding="utf-8"))
    execution_path = root / failure["executionContract"]["uri"]
    work = Path(failure["workRoot"])
    evidence = Path(failure["evidenceRoot"])
    input_rows = []
    for record in tool["commonInputs"]:
        input_rows.append(("common", record))
    for fixture in tool["fixtures"]:
        for record in fixture["inputs"]:
            input_rows.append((fixture["id"], record))
    mismatches = []
    for scope, record in input_rows:
        actual = sha256_file(root / record["uri"])
        if actual != record["sha256"]:
            mismatches.append({"scope": scope, "uri": record["uri"], "expected": record["sha256"], "actual": actual})
    actual = failure["failure"]["actualSha256"]
    stable_commits = correction["finding"]["sourceStabilityCommits"]
    stable = all(sha256_bytes(git(["cat-file", "blob", f"{commit}:specs/scene-spec.v0.1.schema.json"], root, binary=True)) == actual for commit in stable_commits)
    evidence_files_before = [path.relative_to(evidence).as_posix() for path in regular_files(evidence)]
    work_files = regular_files(work)
    contract_uri = failure["executionContract"]["uri"]
    checks = {
        "correctionSchemaStatus": require_schema and correction.get("status") == "FROZEN_INERT_C3_SINGLE_INPUT_HASH_CORRECTION",
        "correctionParentCurrent": correction.get("parentResearchCommit") == git(["rev-parse", "HEAD"], root),
        "auditorHash": sha256_file(Path(__file__)) == correction["tools"]["failureAuditorSha256"],
        "failureFileHash": sha256_file(args.failure) == correction["retainedAttempt01"]["failureFileSha256"],
        "failureSelfHash": valid_self(failure, "failureHash") and failure.get("failureHash") == correction["retainedAttempt01"]["failureHash"],
        "failureStatusStage": failure.get("status") == "FAIL" and failure.get("failedStage") == "PREPARE_FIXTURE_B01_COMMON_INPUT",
        "executionContractHash": sha256_file(execution_path) == failure["executionContract"]["sha256"],
        "executionCommitExact": git(["rev-parse", failure["executionCommit"]], root) == failure["executionCommit"],
        "executionParentExact": git(["rev-parse", f"{failure['executionCommit']}^"], root) == failure["executionParentResearchCommit"],
        "executionSinglePath": git(["diff-tree", "--no-commit-id", "--name-only", "-r", failure["executionCommit"]], root).splitlines() == [contract_uri],
        "toolBindingsExact": all(sha256_file(root / record["uri"]) == record["sha256"] for record in failure["toolBindings"].values()),
        "oneInputMismatch": len(input_rows) == 13 and len(mismatches) == 1,
        "mismatchExact": mismatches == [{
            "scope": "common",
            "uri": "specs/scene-spec.v0.1.schema.json",
            "expected": "b308c7832d4f4b02e16f930f19dcf1baae7475d2f283aee3cb453f05a2224a",
            "actual": "b308c7832d4f4b02e16f930f19dcf1baaeae7475d2f283aee3cb453f05a2224a",
        }],
        "sourceFileStable": stable,
        "sourceFileBytes": (root / "specs/scene-spec.v0.1.schema.json").stat().st_size == 10516,
        "workRootExactEmpty": work.is_dir() and not work.is_symlink() and len(work_files) == 0,
        "evidenceRootExactBeforeAudit": evidence.is_dir() and not evidence.is_symlink() and evidence_files_before == ["failure.json"],
        "noFormalReceiptOrProcessLogs": not (evidence / "receipt.json").exists() and not any(path.suffix == ".log" for path in evidence.rglob("*")),
        "sourceIdentityClean": git(["rev-parse", "HEAD"], engine) == failure["source"]["head"] and git(["status", "--porcelain"], engine) == "",
        "binaryIdentity": sha256_file(binary) == failure["binarySha256"],
        "zeroBlenderAndMutations": all(failure["counts"][key] == 0 for key in (
            "blenderStarts", "proposalExecutions", "buildPlanWrites", "sceneBuilds",
            "workspaceSaves", "reopens", "renders", "engineSourceEdits",
            "engineRemoteWrites", "networkCalls",
        )),
        "rootsCreatedOnly": failure["counts"]["workRootsCreated"] == 1 and failure["counts"]["evidenceRootsCreated"] == 1 and failure["counts"]["inputFilesCopied"] == 0,
        "c3CorrectionSingleField": correction["correction"]["changedFields"] == ["commonInputs[0].sha256"],
        "attempt02RootsFresh": not Path(correction["paths"]["attempt02WorkRoot"]).exists() and not Path(correction["paths"]["attempt02EvidenceRoot"]).exists(),
    }
    passed = sum(bool(value) for value in checks.values())
    audit = {
        "schemaVersion": "bfs.aiNativeStudioPb3ValidationFailureAudit.v0.1",
        "status": "PASS" if passed == len(checks) else "FAIL",
        "checks": checks,
        "counts": {
            "passed": passed,
            "total": len(checks),
            "blenderStarts": 0,
            "proposalExecutions": 0,
            "buildPlanWrites": 0,
            "renders": 0,
            "engineSourceEdits": 0,
            "engineRemoteWrites": 0,
            "networkCalls": 0
        },
        "failure": {
            "uri": str(args.failure),
            "fileSha256": sha256_file(args.failure),
            "failureHash": failure["failureHash"]
        },
        "inputRoster": {
            "total": len(input_rows),
            "exact": len(input_rows) - len(mismatches),
            "mismatches": mismatches
        },
        "claimCeiling": "Independent retained-failure proof only. No Blender or proposal process was started, and this audit does not authorize attempt-02.",
    }
    audit["auditHash"] = sha256_bytes(canonical(audit))
    write_exclusive(args.output, audit)
    print(f"PB3_ATTEMPT01_FAILURE_AUDIT {audit['status']} {passed}/{len(checks)} auditHash={audit['auditHash']}")
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
