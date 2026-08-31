#!/usr/bin/env python3
"""Independent consolidated audit for PB.3 C3 corrected execution."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path


C3_SCHEMA = "bfs.aiNativeStudioPb3ValidationC3ExecutionToolFreeze.v0.8"


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
    return sys.argv[sys.argv.index(name) + 1]


def replace_option(name: str, value: str) -> None:
    require(sys.argv.count(name) == 1, f"{name} must appear exactly once")
    sys.argv[sys.argv.index(name) + 1] = value


def git(args: list[str], cwd: Path, binary: bool = False):
    result = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=not binary)
    return result.stdout if binary else result.stdout.strip()


def load_module(path: Path, expected_sha256: str):
    require(sha256_file(path) == expected_sha256, "base auditor SHA-256 mismatch")
    spec = importlib.util.spec_from_file_location("pb3_base_auditor_c3", path)
    require(spec is not None and spec.loader is not None, "cannot load base auditor")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def tree_manifest(root: Path) -> dict:
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


def write_exclusive(path: Path, value: object) -> int:
    payload = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            require(written > 0, "audit write made no progress")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return len(payload)


def expected_argv(binary: Path, helper: Path, root: Path, tool: Path, work: Path, evidence: Path, fixture: str, stage: str) -> list[str]:
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


def retained_exact(c3: dict) -> bool:
    retained = c3["retainedAttempt01"]
    work = Path(retained["workRoot"])
    evidence = Path(retained["evidenceRoot"])
    if tree_manifest(work) != retained["workManifest"] or tree_manifest(evidence) != retained["evidenceManifest"]:
        return False
    return all(sha256_file(evidence / record["name"]) == record["sha256"] for record in retained["files"])


def main() -> int:
    c3_path = Path(extract_option("--c3-contract")).resolve(strict=True)
    c3 = json.loads(c3_path.read_text(encoding="utf-8"))
    require(c3.get("schemaVersion") == C3_SCHEMA and c3.get("status") == "FROZEN_INERT_C3_CORRECTED_EXECUTION_TOOLING", "C3 tooling mismatch")
    require(sha256_file(Path(__file__)) == c3["tools"]["independentAuditorSha256"], "C3 auditor SHA-256 mismatch")
    root = Path(option_value("--repository-root")).resolve(strict=True)
    engine = Path(option_value("--engine-source")).resolve(strict=True)
    binary = Path(option_value("--binary")).resolve(strict=True)
    tool_path = Path(option_value("--tool-contract")).resolve(strict=True)
    execution_path = Path(option_value("--execution-contract")).resolve(strict=True)
    receipt_path = Path(option_value("--receipt")).resolve(strict=True)
    final_output = Path(option_value("--output"))
    tool = json.loads(tool_path.read_text(encoding="utf-8"))
    execution = json.loads(execution_path.read_text(encoding="utf-8"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    work = Path(receipt["workRoot"])
    evidence = Path(receipt["evidenceRoot"])
    require(final_output == evidence / "audit.json", "final C3 audit path differs")
    require(not final_output.exists() and not final_output.is_symlink(), "final C3 audit path is not fresh")
    evidence_before_base = tree_manifest(evidence)
    base_output = evidence / "audit-base.json"
    require(not base_output.exists() and not base_output.is_symlink(), "base audit path is not fresh")
    replace_option("--output", str(base_output))
    base = load_module(root / c3["base"]["independentAuditor"], c3["base"]["independentAuditorSha256"])
    base_result = base.main()
    base_audit = json.loads(base_output.read_text(encoding="utf-8"))
    evidence_after_base = tree_manifest(evidence)
    request_record = c3["authorizationRequest"]
    request_path = root / request_record["uri"]
    request = json.loads(request_path.read_text(encoding="utf-8"))
    exact_text = request["requestedAuthorization"]["exactText"]
    authorization = execution.get("authorization", {})
    authorized = execution.get("authorizedRun", {})
    processes = receipt.get("processes", [])
    helper = root / tool["tools"]["blenderProbe"]
    pairs = [(fixture, stage) for fixture in ("B01", "B02") for stage in ("build", "reopen")]
    process_exact = len(processes) == 4
    logs = []
    if process_exact:
        for process, (fixture, stage) in zip(processes, pairs, strict=True):
            process_exact = process_exact and process.get("fixtureId") == fixture and process.get("stage") == stage
            process_exact = process_exact and process.get("argv") == expected_argv(binary, helper, root, tool_path, work, evidence, fixture, stage)
            for stream in ("stdout", "stderr"):
                path = evidence / fixture.lower() / f"{stage}.{stream}.log"
                exact = path.is_file() and not path.is_symlink() and sha256_file(path) == process.get(f"{stream}Sha256")
                logs.append({"path": path.relative_to(evidence).as_posix(), "sha256": sha256_file(path) if path.is_file() and not path.is_symlink() else None, "exact": exact})
                process_exact = process_exact and exact
    resources = receipt.get("resourceEnforcement", {})
    contract_uri = execution_path.relative_to(root).as_posix()
    request_uri = request_path.relative_to(root).as_posix()
    work_manifest = tree_manifest(work)
    checks = {
        "baseAuditPass": base_result == 0 and base_audit.get("status") == "PASS",
        "correctedToolBinding": receipt.get("toolFreezeSha256") == c3["correctedTool"]["sha256"] == sha256_file(tool_path),
        "c3CorrectionBinding": execution.get("toolC3Correction", {}).get("sha256") == resources.get("c3CorrectionSha256") == sha256_file(c3_path),
        "authorizationRequestBinding": execution.get("authorizationRequest") == request_record and sha256_file(request_path) == request_record["sha256"],
        "authorizationTextExact": authorization.get("exactUserText") == exact_text and authorization.get("exactUserTextSha256") == sha256_bytes(exact_text.encode()),
        "authorizationExplicitAndDated": authorization.get("explicitPb3ScopePresent") is True and bool(authorization.get("authorizedAtUtc")),
        "authorizedRootsExact": authorized.get("workRoot") == str(work) and authorized.get("evidenceRoot") == str(evidence),
        "authorizedIdentityExact": authorized.get("repositoryRoot") == str(root) and authorized.get("engineSource") == str(engine) and authorized.get("binary") == str(binary),
        "receiptPathExact": receipt_path == evidence / "receipt.json",
        "executionSinglePath": git(["diff-tree", "--no-commit-id", "--name-only", "-r", receipt["executionCommit"]], root).splitlines() == [contract_uri],
        "requestFrozenInParent": git(["show", f"{receipt['executionCommit']}^:{request_uri}"], root, binary=True) == request_path.read_bytes(),
        "c3FrozenInParent": git(["show", f"{receipt['executionCommit']}^:{c3_path.relative_to(root).as_posix()}"], root, binary=True) == c3_path.read_bytes(),
        "correctedToolFrozenInParent": git(["show", f"{receipt['executionCommit']}^:{tool_path.relative_to(root).as_posix()}"], root, binary=True) == tool_path.read_bytes(),
        "processArgvAndLogsExact": process_exact and len(logs) == 8 and all(row["exact"] for row in logs),
        "workManifestExact": work_manifest == resources.get("workManifest"),
        "evidenceBeforeReceiptProjectionExact": evidence_before_base["regularFileBytes"] == resources.get("projectedEvidenceRootBytes"),
        "exclusiveAndNoSymlinks": resources.get("processLogsWrittenExclusively") is True and resources.get("symbolicPathsAllowed") is False,
        "workWithinCeiling": work_manifest["regularFileBytes"] <= c3["resources"]["maximumWorkRootBytes"] == resources.get("maximumWorkRootBytes"),
        "evidenceWithinCeilingBeforeFinal": evidence_after_base["regularFileBytes"] <= c3["resources"]["maximumEvidenceRootBytes"] == resources.get("maximumEvidenceRootBytes"),
        "retainedAttempt01Exact": retained_exact(c3),
        "sourceIdentityClean": git(["rev-parse", "HEAD"], engine) == c3["source"]["head"] and git(["status", "--porcelain"], engine) == "",
        "binaryIdentity": sha256_file(binary) == c3["binary"]["sha256"],
        "zeroProhibitedCounts": all(receipt["counts"][key] == 0 for key in ("renders", "engineSourceEdits", "engineRemoteWrites", "networkCalls")),
    }
    passed = sum(bool(value) for value in checks.values())
    body = {
        "schemaVersion": "bfs.aiNativeStudioPb3ValidationIndependentAuditC3.v0.1",
        "status": "PASS" if passed == len(checks) else "FAIL",
        "independence": "Delegates the frozen base semantic audit, then independently verifies corrected-tool authority, roots, resources, argv/logs, manifests and retained attempt-01.",
        "checks": checks,
        "counts": {
            "passed": passed, "total": len(checks), "blenderStarts": 0,
            "proposalExecutions": 0, "buildPlanWrites": 0, "renders": 0,
            "engineSourceEdits": 0, "engineRemoteWrites": 0, "networkCalls": 0,
        },
        "baseAudit": {"uri": str(base_output), "sha256": sha256_file(base_output), "auditHash": base_audit.get("auditHash")},
        "logEvidence": logs,
        "workManifest": work_manifest,
        "evidenceManifestBeforeBaseAudit": evidence_before_base,
        "evidenceManifestAfterBaseAudit": evidence_after_base,
        "resourceAudit": {
            "maximumWorkRootBytes": c3["resources"]["maximumWorkRootBytes"],
            "maximumEvidenceRootBytes": c3["resources"]["maximumEvidenceRootBytes"],
        },
        "claimCeiling": c3["claimCeiling"],
    }
    while True:
        body["resourceAudit"]["auditBytes"] = len((json.dumps({**body, "auditHash": "0" * 64}, indent=2, ensure_ascii=False) + "\n").encode())
        projected = evidence_after_base["regularFileBytes"] + body["resourceAudit"]["auditBytes"]
        if body["resourceAudit"].get("projectedEvidenceRootBytesAfterC3Audit") == projected:
            break
        body["resourceAudit"]["projectedEvidenceRootBytesAfterC3Audit"] = projected
    require(projected <= c3["resources"]["maximumEvidenceRootBytes"], "final C3 audit exceeds evidence ceiling")
    body["auditHash"] = sha256_bytes(canonical(body))
    written = write_exclusive(final_output, body)
    require(written == body["resourceAudit"]["auditBytes"], "final C3 audit byte projection differs")
    require(tree_manifest(evidence)["regularFileBytes"] == projected, "final C3 evidence bytes differ")
    print(f"PB3_AUDIT_C3 {body['status']} {passed}/{len(checks)} auditHash={body['auditHash']}")
    return 0 if body["status"] == "PASS" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"PB3_AUDIT_C3_STOP {type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1) from error
