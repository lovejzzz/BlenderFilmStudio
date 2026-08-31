#!/usr/bin/env python3
"""Independent PB.3 C5 audit over the frozen base semantic oracle."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path


C5_SCHEMA = "bfs.aiNativeStudioPb3ValidationC5ExecutionToolFreeze.v1.8"
FORBIDDEN_ARTIFACT_SUFFIXES = {".exr", ".png", ".jpg", ".jpeg", ".mov", ".mp4"}


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


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


def replace_option(name: str, value: str) -> None:
    require(sys.argv.count(name) == 1, f"{name} must appear exactly once")
    sys.argv[sys.argv.index(name) + 1] = value


def git(args: list[str], cwd: Path, binary: bool = False):
    result = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=not binary)
    return result.stdout if binary else result.stdout.strip()


def load_module(path: Path, expected_sha256: str):
    require(sha256_file(path) == expected_sha256, f"module SHA-256 mismatch: {path}")
    spec = importlib.util.spec_from_file_location("pb3_base_auditor_for_c5", path)
    require(spec is not None and spec.loader is not None, f"cannot load module: {path}")
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


def retained_exact(c5: dict, base_c4: dict) -> tuple[bool, dict]:
    observed = {}
    exact = True
    for retained in base_c4["retainedAttempts"]:
        work_manifest = tree_manifest(Path(retained["workRoot"]))
        evidence_manifest = tree_manifest(Path(retained["evidenceRoot"]))
        row_exact = work_manifest == retained["workManifest"] and evidence_manifest == retained["evidenceManifest"]
        row_exact = row_exact and all(sha256_file(Path(retained["evidenceRoot"]) / record["name"]) == record["sha256"] for record in retained.get("files", []))
        observed[retained["id"]] = {"workManifest": work_manifest, "evidenceManifest": evidence_manifest, "exact": row_exact}
        exact = exact and row_exact
    retained = c5["retainedAttempt03"]
    attempt03_manifest = tree_manifest(Path(retained["evidenceRoot"]))
    attempt03_exact = not Path(retained["workRoot"]).exists() and attempt03_manifest == retained["evidenceManifest"]
    attempt03_exact = attempt03_exact and all(sha256_file(Path(retained["evidenceRoot"]) / record["name"]) == record["sha256"] for record in retained["files"])
    observed["attempt-03"] = {"workRootAbsent": not Path(retained["workRoot"]).exists(), "evidenceManifest": attempt03_manifest, "exact": attempt03_exact}
    return exact and attempt03_exact, observed


def main() -> int:
    c5_path = Path(extract_option("--c5-contract")).resolve(strict=True)
    c5 = json.loads(c5_path.read_text(encoding="utf-8"))
    require(c5.get("schemaVersion") == C5_SCHEMA and c5.get("status") == "FROZEN_INERT_C5_EXECUTION_TOOLING", "C5 tooling mismatch")
    require(sha256_file(Path(__file__)) == c5["tools"]["independentAuditorSha256"], "C5 auditor SHA-256 mismatch")
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
    require(final_output == evidence / "audit.json", "final C5 audit path differs")
    require(not final_output.exists() and not final_output.is_symlink(), "final C5 audit path is not fresh")
    evidence_before_base = tree_manifest(evidence)
    base_output = evidence / "audit-base.json"
    require(not base_output.exists() and not base_output.is_symlink(), "base audit path is not fresh")
    replace_option("--output", str(base_output))
    base_c4_path = root / c5["c4Binding"]["uri"]
    base_c4 = json.loads(base_c4_path.read_text(encoding="utf-8"))
    base = load_module(root / base_c4["base"]["baseAuditor"], base_c4["base"]["baseAuditorSha256"])
    base_result = base.main()
    base_audit = json.loads(base_output.read_text(encoding="utf-8"))
    evidence_after_base = tree_manifest(evidence)
    request_record = c5["authorizationRequest"]
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
    work_manifest = tree_manifest(work)
    retained_ok, retained_observed = retained_exact(c5, base_c4)
    no_render_artifacts = not any(path.is_file() and path.suffix.lower() in FORBIDDEN_ARTIFACT_SUFFIXES for path in work.rglob("*"))
    expected_authorized = {
        "repositoryRoot": str(root), "engineSource": str(engine), "binary": str(binary),
        "workRoot": str(work), "evidenceRoot": str(evidence), "benchmarks": ["B01", "B02"],
        "blenderStarts": 4, "proposalExecutions": 2, "buildPlanWrites": 2,
        "sceneBuilds": 2, "workspaceSaves": 2, "reopens": 2, "renders": 0,
        "engineSourceEdits": 0, "engineRemoteWrites": 0, "networkCalls": 0,
    }
    checks = {
        "baseAuditPass": base_result == 0 and base_audit.get("status") == "PASS",
        "correctedToolBinding": receipt.get("toolFreezeSha256") == c5["correctedTool"]["sha256"] == sha256_file(tool_path),
        "c3ReceiptBindingExact": resources.get("c3CorrectionSha256") == c5["receiptBinding"]["c3CorrectionSha256"],
        "c4ExecutionBinding": execution.get("toolC4Correction") == c5["c4Binding"] and sha256_file(base_c4_path) == c5["c4Binding"]["sha256"],
        "c5ExecutionBinding": execution.get("toolC5Correction", {}).get("sha256") == sha256_file(c5_path),
        "authorizationRequestBinding": execution.get("authorizationRequest") == request_record and sha256_file(request_path) == request_record["sha256"],
        "authorizationTextExact": authorization.get("exactUserText") == exact_text and authorization.get("exactUserTextSha256") == sha256_bytes(exact_text.encode()),
        "authorizationExplicitAndDated": authorization.get("explicitPb3ScopePresent") is True and bool(authorization.get("authorizedAtUtc")),
        "authorizedRunExact": authorized == expected_authorized,
        "stillUnauthorizedExact": execution.get("stillUnauthorized") == tool.get("stillUnauthorized"),
        "receiptPathExact": receipt_path == evidence / "receipt.json",
        "executionSinglePath": git(["diff-tree", "--no-commit-id", "--name-only", "-r", receipt["executionCommit"]], root).splitlines() == [contract_uri],
        "executionParentExact": git(["rev-parse", f"{receipt['executionCommit']}^"], root) == execution.get("executionParentResearchCommit"),
        "frozenInputsInParent": all(git(["show", f"{receipt['executionCommit']}^:{path.relative_to(root).as_posix()}"], root, binary=True) == path.read_bytes() for path in (request_path, c5_path, base_c4_path, tool_path)),
        "processArgvAndLogsExact": process_exact and len(logs) == 8 and all(row["exact"] for row in logs),
        "workManifestExact": work_manifest == resources.get("workManifest"),
        "evidenceBeforeReceiptProjectionExact": evidence_before_base["regularFileBytes"] == resources.get("projectedEvidenceRootBytes"),
        "exclusiveAndNoSymlinks": resources.get("processLogsWrittenExclusively") is True and resources.get("symbolicPathsAllowed") is False,
        "workWithinCeiling": work_manifest["regularFileBytes"] <= c5["resources"]["maximumWorkRootBytes"] == resources.get("maximumWorkRootBytes"),
        "evidenceWithinCeilingBeforeFinal": evidence_after_base["regularFileBytes"] <= c5["resources"]["maximumEvidenceRootBytes"] == resources.get("maximumEvidenceRootBytes"),
        "retainedAttemptsExact": retained_ok,
        "sourceIdentityClean": git(["rev-parse", "HEAD"], engine) == c5["source"]["head"] and git(["status", "--porcelain"], engine) == "",
        "binaryIdentity": sha256_file(binary) == c5["binary"]["sha256"],
        "zeroProhibitedCounts": all(receipt["counts"][key] == 0 for key in ("renders", "engineSourceEdits", "engineRemoteWrites", "networkCalls")),
        "noRenderArtifactsAnywhere": no_render_artifacts,
    }
    passed = sum(bool(value) for value in checks.values())
    body = {
        "schemaVersion": "bfs.aiNativeStudioPb3ValidationIndependentAuditC5.v0.1",
        "status": "PASS" if passed == len(checks) else "FAIL",
        "independence": "Delegates only the frozen base semantic audit, then independently verifies C5/C4 authority, exact scope array, absolute argv, logs, resources, all retained attempts and the unchanged no-artifact predicate.",
        "checks": checks,
        "counts": {"passed": passed, "total": len(checks), "blenderStarts": 0, "proposalExecutions": 0, "buildPlanWrites": 0, "renders": 0, "engineSourceEdits": 0, "engineRemoteWrites": 0, "networkCalls": 0},
        "baseAudit": {"uri": str(base_output), "sha256": sha256_file(base_output), "auditHash": base_audit.get("auditHash")},
        "logEvidence": logs,
        "workManifest": work_manifest,
        "evidenceManifestBeforeBaseAudit": evidence_before_base,
        "evidenceManifestAfterBaseAudit": evidence_after_base,
        "retainedManifests": retained_observed,
        "resourceAudit": {"maximumWorkRootBytes": c5["resources"]["maximumWorkRootBytes"], "maximumEvidenceRootBytes": c5["resources"]["maximumEvidenceRootBytes"]},
        "claimCeiling": c5["claimCeiling"],
    }
    while True:
        body["resourceAudit"]["auditBytes"] = len((json.dumps({**body, "auditHash": "0" * 64}, indent=2, ensure_ascii=False) + "\n").encode())
        projected = evidence_after_base["regularFileBytes"] + body["resourceAudit"]["auditBytes"]
        if body["resourceAudit"].get("projectedEvidenceRootBytesAfterC5Audit") == projected:
            break
        body["resourceAudit"]["projectedEvidenceRootBytesAfterC5Audit"] = projected
    require(projected <= c5["resources"]["maximumEvidenceRootBytes"], "final C5 audit exceeds evidence ceiling")
    body["auditHash"] = sha256_bytes(canonical(body))
    written = write_exclusive(final_output, body)
    require(written == body["resourceAudit"]["auditBytes"], "final C5 audit byte projection differs")
    require(tree_manifest(evidence)["regularFileBytes"] == projected, "final C5 evidence bytes differ")
    print(f"PB3_AUDIT_C5 {body['status']} {passed}/{len(checks)} auditHash={body['auditHash']}")
    return 0 if body["status"] == "PASS" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"PB3_AUDIT_C5_STOP {type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1) from error
