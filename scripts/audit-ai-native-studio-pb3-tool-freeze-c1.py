#!/usr/bin/env python3
"""Independent static audit of PB.3 C1 resource-enforcement wrappers."""

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


def imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


def git(args: list[str], cwd: Path) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


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
    base = correction["base"]
    tools = correction["tools"]
    base_contract = root / base["toolFreeze"]
    base_runner = root / base["runner"]
    base_auditor = root / base["independentAuditor"]
    runner = root / tools["runnerWrapper"]
    auditor = root / tools["independentAuditorWrapper"]
    static = Path(__file__).resolve()
    work = Path(correction["paths"]["workRoot"])
    evidence = Path(correction["paths"]["evidenceRoot"])

    self_test = subprocess.run(
        ["python3", str(runner), "--correction-contract", str(args.correction), "--self-test"],
        cwd=root, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, capture_output=True, text=True,
    )
    inert = subprocess.run(
        [
            "python3", str(runner), "--correction-contract", str(args.correction), "--execute",
            "--repository-root", str(root), "--engine-source", str(engine), "--binary", str(binary),
            "--work-root", str(work), "--evidence-root", str(evidence),
            "--tool-contract", str(base_contract), "--execution-contract", str(args.template),
        ],
        cwd=root, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, capture_output=True, text=True,
    )
    runner_source = runner.read_text(encoding="utf-8")
    auditor_source = auditor.read_text(encoding="utf-8")
    forbidden = {"socket", "urllib", "requests", "http", "ftplib", "bpy"}
    checks = {
        "correctionSchemaAndStatus": correction.get("schemaVersion") == "bfs.aiNativeStudioPb3ValidationToolC1ResourceEnforcement.v0.3" and correction.get("status") == "FROZEN_INERT_C1_RESOURCE_ENFORCEMENT",
        "parentCommitCurrent": correction.get("parentResearchCommit") == git(["rev-parse", "HEAD"], root),
        "baseToolHash": sha256_file(base_contract) == base["toolFreezeSha256"],
        "baseRunnerHash": sha256_file(base_runner) == base["runnerSha256"],
        "baseAuditorHash": sha256_file(base_auditor) == base["independentAuditorSha256"],
        "runnerWrapperHash": sha256_file(runner) == tools["runnerWrapperSha256"],
        "auditorWrapperHash": sha256_file(auditor) == tools["independentAuditorWrapperSha256"],
        "staticAuditorHash": sha256_file(static) == tools["staticAuditorSha256"],
        "runnerNoNetworkOrBpyImports": not (imports(runner) & forbidden),
        "auditorNoNetworkOrBpyImports": not (imports(auditor) & forbidden),
        "runnerExclusiveBinaryWrites": "os.O_EXCL" in runner_source and "write_bytes_exclusive" in runner_source,
        "runnerEnforcesWorkCeiling": "maximumWorkRootBytes" in runner_source and "work root exceeds C1 ceiling" in runner_source,
        "runnerEnforcesEvidenceCeiling": "maximumEvidenceRootBytes" in runner_source and "evidence root exceeds C1 ceiling" in runner_source,
        "runnerRejectsSymlinks": "resource root contains symbolic path" in runner_source,
        "auditorRecomputesRootSizes": "tree_file_bytes(work_root)" in auditor_source and "tree_file_bytes(evidence_root)" in auditor_source,
        "auditorProjectsOwnBytes": "projectedEvidenceRootBytesAfterAudit" in auditor_source,
        "selfTestPass": self_test.returncode == 0 and self_test.stdout.count('"status": "PASS"') >= 2,
        "templateNonExecutable": template.get("status") == "DRAFT_AUTHORIZATION_MISSING" and template.get("authorization", {}).get("exactUserText") is None,
        "templateBindsCorrection": template.get("toolCorrection", {}).get("sha256") == sha256_file(args.correction),
        "inertInvocationRejected": inert.returncode != 0 and "PB.3 execution is not authorized" in inert.stderr,
        "formalRootsAbsent": not work.exists() and not work.is_symlink() and not evidence.exists() and not evidence.is_symlink(),
        "sourceIdentity": git(["rev-parse", "HEAD"], engine) == correction["source"]["head"] and git(["status", "--porcelain"], engine) == "",
        "binaryIdentity": sha256_file(binary) == correction["binary"]["sha256"],
        "ceilingsUnchanged": correction["resourceEnforcement"] == {"maximumWorkRootBytes": 2147483648, "maximumEvidenceRootBytes": 67108864},
        "formalCountsZero": all(value == 0 for value in correction["currentCounts"].values()),
    }
    passed = sum(bool(value) for value in checks.values())
    audit = {
        "schemaVersion": "bfs.aiNativeStudioPb3ToolFreezeC1StaticAudit.v0.1",
        "status": "PASS" if passed == len(checks) else "FAIL",
        "checks": checks,
        "counts": {
            "passed": passed, "total": len(checks), "systemPythonSelfTests": 1,
            "inertRunnerInvocations": 1, "blenderStarts": 0, "proposalExecutions": 0,
            "buildPlanWrites": 0, "sceneBuilds": 0, "workspaceSaves": 0,
            "reopens": 0, "renders": 0, "engineSourceEdits": 0,
            "engineRemoteWrites": 0, "networkCalls": 0,
        },
        "selfTestStdoutSha256": sha256_bytes(self_test.stdout.encode()),
        "inertStderrSha256": sha256_bytes(inert.stderr.encode()),
        "claimCeiling": correction.get("claimCeiling"),
    }
    audit["auditHash"] = sha256_bytes(canonical(audit))
    write_exclusive(args.output, audit)
    print(f"PB3_TOOL_C1_AUDIT {audit['status']} {passed}/{len(checks)} auditHash={audit['auditHash']}")
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
