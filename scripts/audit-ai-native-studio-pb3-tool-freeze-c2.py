#!/usr/bin/env python3
"""Independent static audit for inert PB.3 C2 authority/evidence binding."""

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


def imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


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
    template = json.loads(args.template.read_text(encoding="utf-8"))
    runner = root / correction["tools"]["runner"]
    auditor = root / correction["tools"]["independentAuditor"]
    static = Path(__file__).resolve(strict=True)
    request = root / correction["authorizationRequest"]["uri"]
    runner_source = runner.read_text(encoding="utf-8")
    auditor_source = auditor.read_text(encoding="utf-8")
    forbidden = {"bpy", "socket", "urllib", "requests", "http", "ftplib"}
    self_test = subprocess.run(
        [
            "python3", str(runner), "--c2-contract", str(args.correction),
            "--correction-contract", str(root / correction["baseC1"]["correction"]), "--self-test",
        ],
        cwd=root, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, capture_output=True, text=True,
    )
    work = Path(correction["paths"]["workRoot"])
    evidence = Path(correction["paths"]["evidenceRoot"])
    inert = subprocess.run(
        [
            "python3", str(runner), "--c2-contract", str(args.correction),
            "--correction-contract", str(root / correction["baseC1"]["correction"]), "--execute",
            "--repository-root", str(root), "--engine-source", str(engine), "--binary", str(binary),
            "--work-root", str(work), "--evidence-root", str(evidence),
            "--tool-contract", str(root / correction["baseC1"]["toolFreeze"]),
            "--execution-contract", str(args.template),
        ],
        cwd=root, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, capture_output=True, text=True,
    )
    checks = {
        "correctionSchemaStatus": correction.get("schemaVersion") == "bfs.aiNativeStudioPb3ValidationToolC2EvidenceBinding.v0.5" and correction.get("status") == "FROZEN_INERT_C2_AUTHORIZATION_AND_EVIDENCE_BINDING",
        "parentCommitCurrent": correction.get("parentResearchCommit") == git(["rev-parse", "HEAD"], root),
        "baseC1CorrectionHash": sha256_file(root / correction["baseC1"]["correction"]) == correction["baseC1"]["correctionSha256"],
        "baseC1RunnerHash": sha256_file(root / correction["baseC1"]["runner"]) == correction["baseC1"]["runnerSha256"],
        "baseC1AuditorHash": sha256_file(root / correction["baseC1"]["independentAuditor"]) == correction["baseC1"]["independentAuditorSha256"],
        "runnerHash": sha256_file(runner) == correction["tools"]["runnerSha256"],
        "auditorHash": sha256_file(auditor) == correction["tools"]["independentAuditorSha256"],
        "staticAuditorHash": sha256_file(static) == correction["tools"]["staticAuditorSha256"],
        "authorizationRequestHash": sha256_file(request) == correction["authorizationRequest"]["sha256"],
        "runnerNoNetworkOrBpyImports": not (imports(runner) & forbidden),
        "auditorNoNetworkOrBpyImports": not (imports(auditor) & forbidden),
        "runnerBindsExactAuthorization": "exact PB.3 C2 authorization text differs" in runner_source and "authorization request was not frozen in execution parent" in runner_source,
        "runnerRequiresSinglePathCommit": "execution commit must change only its contract" in runner_source,
        "runnerVerifiesArgvAndLogs": "formal process argv differs" in runner_source and "log SHA-256 differs" in runner_source,
        "auditorBindsAuthorizedRoots": "workRootAuthorized" in auditor_source and "evidenceRootAuthorized" in auditor_source,
        "auditorVerifiesSinglePathCommit": "executionCommitSinglePath" in auditor_source,
        "auditorVerifiesArgvAndLogs": "processRosterArgvAndLogsExact" in auditor_source,
        "auditorCreatesRootManifests": "workManifest" in auditor_source and "evidenceManifestBeforeC2Audit" in auditor_source,
        "auditorEnforcesFinalEvidenceCeiling": "projectedEvidenceRootBytesAfterC2Audit" in auditor_source and "final C2 evidence bytes differ" in auditor_source,
        "selfTestPass": self_test.returncode == 0 and '"status": "PASS"' in self_test.stdout,
        "templateNonExecutable": template.get("status") == "DRAFT_AUTHORIZATION_MISSING" and template.get("authorization", {}).get("exactUserText") is None,
        "templateBindsC2": template.get("toolC2Correction", {}).get("sha256") == sha256_file(args.correction),
        "templateBindsRequest": template.get("authorizationRequest") == correction["authorizationRequest"],
        "inertInvocationRejected": inert.returncode != 0 and not work.exists() and not work.is_symlink() and not evidence.exists() and not evidence.is_symlink(),
        "formalRootsAbsent": not work.exists() and not work.is_symlink() and not evidence.exists() and not evidence.is_symlink(),
        "sourceIdentity": git(["rev-parse", "HEAD"], engine) == correction["source"]["head"] and git(["status", "--porcelain"], engine) == "",
        "binaryIdentity": sha256_file(binary) == correction["binary"]["sha256"],
        "ceilingsUnchanged": correction["resources"] == {"maximumWorkRootBytes": 2147483648, "maximumEvidenceRootBytes": 67108864},
        "formalCountsZero": all(value == 0 for value in correction["currentCounts"].values()),
    }
    passed = sum(bool(value) for value in checks.values())
    audit = {
        "schemaVersion": "bfs.aiNativeStudioPb3ValidationToolC2StaticAudit.v0.1",
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
            "sourceHead": correction["source"]["head"],
            "binarySha256": correction["binary"]["sha256"],
        },
        "claimCeiling": "Static proof only: C2 binds exact future authority, single-path execution commit, formal roots, exact argv/logs and root manifests. It creates no formal root and starts no Blender process.",
    }
    audit["auditHash"] = sha256_bytes(canonical(audit))
    write_exclusive(args.output, audit)
    print(f"PB3_C2_TOOL_AUDIT {audit['status']} {passed}/{len(checks)} auditHash={audit['auditHash']}")
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
