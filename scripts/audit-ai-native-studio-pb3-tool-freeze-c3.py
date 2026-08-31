#!/usr/bin/env python3
"""Static audit for PB.3 C3 corrected consolidated tooling."""

from __future__ import annotations

import argparse
import ast
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
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def git(args: list[str], cwd: Path) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    result = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.add(node.module.split(".")[0])
    return result


def json_diffs(left, right, path="") -> list[tuple[str, object, object]]:
    if type(left) is not type(right):
        return [(path, left, right)]
    if isinstance(left, dict):
        result = []
        for key in sorted(set(left) | set(right)):
            child = f"{path}.{key}" if path else key
            if key not in left or key not in right:
                result.append((child, left.get(key), right.get(key)))
            else:
                result.extend(json_diffs(left[key], right[key], child))
        return result
    if isinstance(left, list):
        if len(left) != len(right):
            return [(path, left, right)]
        result = []
        for index, (first, second) in enumerate(zip(left, right, strict=True)):
            result.extend(json_diffs(first, second, f"{path}[{index}]"))
        return result
    return [] if left == right else [(path, left, right)]


def tree_manifest(root: Path) -> dict:
    if not root.is_dir() or root.is_symlink():
        raise RuntimeError(f"root is not exact: {root}")
    rows = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        if path.is_symlink():
            raise RuntimeError(f"symbolic path: {path}")
        if path.is_file():
            rows.append({"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return {
        "regularFiles": len(rows),
        "regularFileBytes": sum(row["bytes"] for row in rows),
        "manifestSha256": sha256_bytes(canonical(rows)),
    }


def write_exclusive(path: Path, value: object) -> None:
    payload = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise RuntimeError("static audit write made no progress")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def main() -> int:
    args = arguments()
    root = args.repository_root.resolve(strict=True)
    engine = args.engine_source.resolve(strict=True)
    binary = args.binary.resolve(strict=True)
    correction = json.loads(args.correction.read_text(encoding="utf-8"))
    template = json.loads(args.template.read_text(encoding="utf-8"))
    base_tool_path = root / correction["base"]["toolFreeze"]
    corrected_path = root / correction["correctedTool"]["uri"]
    base_tool = json.loads(base_tool_path.read_text(encoding="utf-8"))
    corrected = json.loads(corrected_path.read_text(encoding="utf-8"))
    runner = root / correction["tools"]["runner"]
    auditor = root / correction["tools"]["independentAuditor"]
    static = Path(__file__).resolve(strict=True)
    request = root / correction["authorizationRequest"]["uri"]
    forbidden = {"bpy", "socket", "urllib", "requests", "http", "ftplib"}
    expected_diff = [(
        "commonInputs[0].sha256",
        "b308c7832d4f4b02e16f930f19dcf1baae7475d2f283aee3cb453f05a2224a",
        "b308c7832d4f4b02e16f930f19dcf1baaeae7475d2f283aee3cb453f05a2224a",
    )]
    records = [*corrected["commonInputs"], *(record for fixture in corrected["fixtures"] for record in fixture["inputs"])]
    self_test = subprocess.run(
        ["python3", str(runner), "--c3-contract", str(args.correction), "--self-test"],
        cwd=root, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, capture_output=True, text=True,
    )
    attempt02_work = Path(correction["paths"]["attempt02WorkRoot"])
    attempt02_evidence = Path(correction["paths"]["attempt02EvidenceRoot"])
    inert = subprocess.run(
        [
            "python3", str(runner), "--c3-contract", str(args.correction), "--execute",
            "--repository-root", str(root), "--engine-source", str(engine), "--binary", str(binary),
            "--work-root", str(attempt02_work), "--evidence-root", str(attempt02_evidence),
            "--tool-contract", str(corrected_path), "--execution-contract", str(args.template),
        ],
        cwd=root, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, capture_output=True, text=True,
    )
    retained = correction["retainedAttempt01"]
    checks = {
        "correctionSchemaStatus": correction.get("schemaVersion") == "bfs.aiNativeStudioPb3ValidationC3ExecutionToolFreeze.v0.8" and correction.get("status") == "FROZEN_INERT_C3_CORRECTED_EXECUTION_TOOLING",
        "parentCommitCurrent": correction.get("parentResearchCommit") == git(["rev-parse", "HEAD"], root),
        "inputCorrectionHash": sha256_file(root / correction["inputCorrection"]["uri"]) == correction["inputCorrection"]["sha256"],
        "baseToolHash": sha256_file(base_tool_path) == correction["base"]["toolFreezeSha256"],
        "correctedToolHash": sha256_file(corrected_path) == correction["correctedTool"]["sha256"],
        "correctedToolOneLeaf": json_diffs(base_tool, corrected) == expected_diff,
        "correctedInputRosterExact": len(records) == 13 and all(sha256_file(root / record["uri"]) == record["sha256"] for record in records),
        "baseRunnerHash": sha256_file(root / correction["base"]["runner"]) == correction["base"]["runnerSha256"],
        "baseAuditorHash": sha256_file(root / correction["base"]["independentAuditor"]) == correction["base"]["independentAuditorSha256"],
        "runnerHash": sha256_file(runner) == correction["tools"]["runnerSha256"],
        "auditorHash": sha256_file(auditor) == correction["tools"]["independentAuditorSha256"],
        "staticAuditorHash": sha256_file(static) == correction["tools"]["staticAuditorSha256"],
        "authorizationRequestHash": sha256_file(request) == correction["authorizationRequest"]["sha256"],
        "runnerNoNetworkOrBpyImports": not (imported_roots(runner) & forbidden),
        "auditorNoNetworkOrBpyImports": not (imported_roots(auditor) & forbidden),
        "runnerBindsExactAuthority": "exact PB.3 C3 authorization text differs" in runner.read_text(encoding="utf-8") and "execution commit must change only its contract" in runner.read_text(encoding="utf-8"),
        "runnerEnforcesResources": "projectedEvidenceRootBytes" in runner.read_text(encoding="utf-8") and "processLogsWrittenExclusively" in runner.read_text(encoding="utf-8"),
        "runnerVerifiesRetainedAttempt": "verify_retained_attempt" in runner.read_text(encoding="utf-8"),
        "auditorVerifiesSemanticBase": "baseAuditPass" in auditor.read_text(encoding="utf-8"),
        "auditorVerifiesArgvLogsManifests": "processArgvAndLogsExact" in auditor.read_text(encoding="utf-8") and "workManifestExact" in auditor.read_text(encoding="utf-8"),
        "auditorVerifiesRetainedAttempt": "retainedAttempt01Exact" in auditor.read_text(encoding="utf-8"),
        "selfTestPass": self_test.returncode == 0 and '"status": "PASS"' in self_test.stdout,
        "templateNonExecutable": template.get("status") == "DRAFT_AUTHORIZATION_MISSING" and template.get("authorization", {}).get("exactUserText") is None,
        "templateBindingsExact": template.get("toolFreeze") == correction["correctedTool"] and template.get("toolC3Correction", {}).get("sha256") == sha256_file(args.correction) and template.get("authorizationRequest") == correction["authorizationRequest"],
        "inertInvocationRejected": inert.returncode != 0 and not attempt02_work.exists() and not attempt02_work.is_symlink() and not attempt02_evidence.exists() and not attempt02_evidence.is_symlink(),
        "attempt02RootsAbsent": not attempt02_work.exists() and not attempt02_work.is_symlink() and not attempt02_evidence.exists() and not attempt02_evidence.is_symlink(),
        "retainedWorkExact": tree_manifest(Path(retained["workRoot"])) == retained["workManifest"],
        "retainedEvidenceExact": tree_manifest(Path(retained["evidenceRoot"])) == retained["evidenceManifest"],
        "sourceIdentity": git(["rev-parse", "HEAD"], engine) == correction["source"]["head"] and git(["status", "--porcelain"], engine) == "",
        "binaryIdentity": sha256_file(binary) == correction["binary"]["sha256"],
        "ceilingsUnchanged": correction["resources"] == {"maximumWorkRootBytes": 2147483648, "maximumEvidenceRootBytes": 67108864},
        "formalCountsZero": all(value == 0 for value in correction["currentCounts"].values()),
    }
    passed = sum(bool(value) for value in checks.values())
    audit = {
        "schemaVersion": "bfs.aiNativeStudioPb3ValidationC3StaticAudit.v0.1",
        "status": "PASS" if passed == len(checks) else "FAIL",
        "checks": checks,
        "counts": {
            "passed": passed, "total": len(checks), "systemPythonSelfTests": 1,
            "inertRunnerInvocations": 1, "blenderStarts": 0, "proposalExecutions": 0,
            "buildPlanWrites": 0, "sceneBuilds": 0, "workspaceSaves": 0,
            "reopens": 0, "renders": 0, "engineSourceEdits": 0,
            "engineRemoteWrites": 0, "networkCalls": 0,
        },
        "bindings": {
            "correctionSha256": sha256_file(args.correction),
            "templateSha256": sha256_file(args.template),
            "authorizationRequestSha256": sha256_file(request),
            "correctedToolSha256": sha256_file(corrected_path),
            "retainedAttempt01EvidenceManifest": retained["evidenceManifest"]["manifestSha256"],
        },
        "claimCeiling": "Static proof only: corrected tool differs at one SHA leaf; C3 is inert without a new exact attempt-02 contract and authorization. No Blender process or attempt-02 root was created.",
    }
    audit["auditHash"] = sha256_bytes(canonical(audit))
    write_exclusive(args.output, audit)
    print(f"PB3_C3_TOOL_AUDIT {audit['status']} {passed}/{len(checks)} auditHash={audit['auditHash']}")
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
