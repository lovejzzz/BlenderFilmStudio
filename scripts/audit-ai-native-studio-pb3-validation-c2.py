#!/usr/bin/env python3
"""C2 PB.3 auditor: bind authority, roots, argv, logs and root manifests."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path


C2_SCHEMA = "bfs.aiNativeStudioPb3ValidationToolC2EvidenceBinding.v0.5"


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


def load_module(path: Path, expected_sha256: str):
    require(sha256_file(path) == expected_sha256, "C1 auditor SHA-256 mismatch")
    spec = importlib.util.spec_from_file_location("pb3_c1_auditor", path)
    require(spec is not None and spec.loader is not None, "cannot load C1 auditor")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(args: list[str], cwd: Path, binary: bool = False):
    result = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=not binary)
    return result.stdout if binary else result.stdout.strip()


def write_exclusive(path: Path, value: object) -> int:
    payload = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        offset = 0
        while offset < len(payload):
            offset += os.write(descriptor, payload[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return len(payload)


def tree_manifest(root: Path) -> dict:
    require(root.is_dir() and not root.is_symlink(), f"manifest root is not an exact directory: {root}")
    rows = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        require(not path.is_symlink(), f"manifest root contains symbolic path: {path}")
        if path.is_file():
            rows.append({"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return {
        "regularFiles": len(rows),
        "regularFileBytes": sum(row["bytes"] for row in rows),
        "manifestSha256": sha256_bytes(canonical(rows)),
    }


def expected_argv(binary: Path, helper: Path, root: Path, tool_path: Path, work: Path, evidence: Path, fixture: str, stage: str) -> list[str]:
    fixture_root = work / fixture.lower()
    prefix = [str(binary), "--background", "--disable-autoexec", "--offline-mode"]
    if stage == "build":
        prefix.insert(2, "--factory-startup")
    else:
        prefix.append(str(fixture_root / "artifacts" / "scene.blend"))
    return [
        *prefix, "--python", str(helper), "--", "--stage", stage,
        "--fixture-id", fixture, "--fixture-root", str(fixture_root),
        "--repository-root", str(root), "--tool-contract", str(tool_path),
        "--receipt", str(evidence / fixture.lower() / f"{stage}.json"),
    ]


def main() -> int:
    c2_path = Path(extract_option("--c2-contract")).resolve(strict=True)
    c2 = json.loads(c2_path.read_text(encoding="utf-8"))
    require(c2.get("schemaVersion") == C2_SCHEMA and c2.get("status") == "FROZEN_INERT_C2_AUTHORIZATION_AND_EVIDENCE_BINDING", "C2 correction mismatch")
    require(sha256_file(Path(__file__)) == c2["tools"]["independentAuditorSha256"], "C2 auditor SHA-256 mismatch")
    root = Path(option_value("--repository-root")).resolve(strict=True)
    tool_path = Path(option_value("--tool-contract")).resolve(strict=True)
    execution_path = Path(option_value("--execution-contract")).resolve(strict=True)
    receipt_path = Path(option_value("--receipt")).resolve(strict=True)
    final_output = Path(option_value("--output"))
    tool = json.loads(tool_path.read_text(encoding="utf-8"))
    execution = json.loads(execution_path.read_text(encoding="utf-8"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    work = Path(receipt["workRoot"])
    evidence = Path(receipt["evidenceRoot"])
    require(final_output == evidence / "audit.json", "C2 final audit path must be exact")
    require(not final_output.exists() and not final_output.is_symlink(), "C2 final audit path is not fresh")
    c1_output = evidence / "audit-c1.json"
    require(not c1_output.exists() and not c1_output.is_symlink(), "C1 intermediate audit path is not fresh")
    replace_option("--output", str(c1_output))
    c1_path = c2_path.parent.parent / c2["baseC1"]["independentAuditor"]
    c1 = load_module(c1_path, c2["baseC1"]["independentAuditorSha256"])
    c1_result = c1.main()
    c1_audit = json.loads(c1_output.read_text(encoding="utf-8"))

    request_record = c2["authorizationRequest"]
    request_path = root / request_record["uri"]
    request = json.loads(request_path.read_text(encoding="utf-8"))
    exact_text = request["requestedAuthorization"]["exactText"]
    authorization = execution.get("authorization", {})
    authorized = execution.get("authorizedRun", {})
    binary = Path(option_value("--binary")).resolve(strict=True)
    helper = root / tool["tools"]["blenderProbe"]
    processes = receipt.get("processes", [])
    pairs = [(fixture, stage) for fixture in ("B01", "B02") for stage in ("build", "reopen")]
    exact_processes = len(processes) == 4
    log_rows = []
    if exact_processes:
        for process, (fixture, stage) in zip(processes, pairs, strict=True):
            exact_processes = exact_processes and process.get("fixtureId") == fixture and process.get("stage") == stage
            exact_processes = exact_processes and process.get("argv") == expected_argv(binary, helper, root, tool_path, work, evidence, fixture, stage)
            for stream in ("stdout", "stderr"):
                log = evidence / fixture.lower() / f"{stage}.{stream}.log"
                exact = log.is_file() and not log.is_symlink() and sha256_file(log) == process.get(f"{stream}Sha256")
                log_rows.append({"path": log.relative_to(evidence).as_posix(), "sha256": sha256_file(log) if log.is_file() and not log.is_symlink() else None, "exact": exact})
                exact_processes = exact_processes and exact

    contract_uri = execution_path.relative_to(root).as_posix()
    request_uri = request_path.relative_to(root).as_posix()
    work_manifest = tree_manifest(work)
    evidence_manifest = tree_manifest(evidence)
    checks = {
        "c1AuditPass": c1_result == 0 and c1_audit.get("status") == "PASS",
        "c2CorrectionBinding": execution.get("toolC2Correction", {}).get("sha256") == sha256_file(c2_path),
        "authorizationRequestHash": sha256_file(request_path) == request_record["sha256"],
        "authorizationRequestBinding": execution.get("authorizationRequest") == request_record,
        "authorizationTextExact": authorization.get("exactUserText") == exact_text,
        "authorizationTextHashExact": authorization.get("exactUserTextSha256") == sha256_bytes(exact_text.encode()),
        "authorizationExplicitAndDated": authorization.get("explicitPb3ScopePresent") is True and bool(authorization.get("authorizedAtUtc")),
        "workRootAuthorized": authorized.get("workRoot") == str(work),
        "evidenceRootAuthorized": authorized.get("evidenceRoot") == str(evidence),
        "repositoryRootAuthorized": authorized.get("repositoryRoot") == str(root),
        "binaryAuthorized": authorized.get("binary") == str(binary),
        "engineSourceAuthorized": authorized.get("engineSource") == str(Path(option_value("--engine-source"))),
        "receiptPathExact": receipt_path == evidence / "receipt.json",
        "executionCommitSinglePath": git(["diff-tree", "--no-commit-id", "--name-only", "-r", receipt["executionCommit"]], root).splitlines() == [contract_uri],
        "authorizationRequestFrozenInParent": git(["show", f"{receipt['executionCommit']}^:{request_uri}"], root, binary=True) == request_path.read_bytes(),
        "c2CorrectionFrozenInParent": git(["show", f"{receipt['executionCommit']}^:{c2_path.relative_to(root).as_posix()}"], root, binary=True) == c2_path.read_bytes(),
        "processRosterArgvAndLogsExact": exact_processes and len(log_rows) == 8 and all(row["exact"] for row in log_rows),
        "workRootNoSymbolicPaths": work_manifest["regularFiles"] >= 1,
        "evidenceRootNoSymbolicPaths": evidence_manifest["regularFiles"] >= 1,
        "workRootWithinCeiling": work_manifest["regularFileBytes"] <= c2["resources"]["maximumWorkRootBytes"],
        "evidenceBeforeC2AuditWithinCeiling": evidence_manifest["regularFileBytes"] <= c2["resources"]["maximumEvidenceRootBytes"],
    }
    passed = sum(bool(value) for value in checks.values())
    body = {
        "schemaVersion": "bfs.aiNativeStudioPb3ValidationIndependentAuditC2.v0.1",
        "status": "PASS" if passed == len(checks) else "FAIL",
        "independence": "Does not import engine modules, execute proposals or start Blender; delegates the exact C1/base evidence audit, then independently binds authority, roots, argv, logs and manifests.",
        "checks": checks,
        "counts": {
            "passed": passed, "total": len(checks), "blenderStarts": 0, "renders": 0,
            "networkCalls": 0, "engineSourceEdits": 0, "engineRemoteWrites": 0,
        },
        "c1Audit": {"uri": str(c1_output), "sha256": sha256_file(c1_output), "auditHash": c1_audit.get("auditHash")},
        "logEvidence": log_rows,
        "workManifest": work_manifest,
        "evidenceManifestBeforeC2Audit": evidence_manifest,
        "resourceAudit": {
            "maximumWorkRootBytes": c2["resources"]["maximumWorkRootBytes"],
            "maximumEvidenceRootBytes": c2["resources"]["maximumEvidenceRootBytes"],
        },
        "claimCeiling": c2["claimCeiling"],
    }
    while True:
        body["resourceAudit"]["auditBytes"] = len((json.dumps({**body, "auditHash": "0" * 64}, indent=2, ensure_ascii=False) + "\n").encode())
        projected = evidence_manifest["regularFileBytes"] + body["resourceAudit"]["auditBytes"]
        if body["resourceAudit"].get("projectedEvidenceRootBytesAfterC2Audit") == projected:
            break
        body["resourceAudit"]["projectedEvidenceRootBytesAfterC2Audit"] = projected
    require(projected <= c2["resources"]["maximumEvidenceRootBytes"], "C2 audit would exceed evidence ceiling")
    body["auditHash"] = sha256_bytes(canonical(body))
    written = write_exclusive(final_output, body)
    require(written == body["resourceAudit"]["auditBytes"], "C2 audit byte projection differs")
    require(tree_manifest(evidence)["regularFileBytes"] == projected, "final C2 evidence bytes differ")
    print(f"PB3_AUDIT_C2 {body['status']} {passed}/{len(checks)} auditHash={body['auditHash']}")
    return 0 if body["status"] == "PASS" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"PB3_AUDIT_C2_STOP {type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1) from error
