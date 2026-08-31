#!/usr/bin/env python3
"""Static independent audit for the inert PB.3 formal-validation tool freeze."""

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
    parser.add_argument("--contract", type=Path, required=True)
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
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    template = json.loads(args.template.read_text(encoding="utf-8"))
    tools = contract.get("tools", {})
    runner = root / tools.get("runner", "missing")
    probe = root / tools.get("blenderProbe", "missing")
    compiler = root / tools.get("sceneCompiler", "missing")
    formal_auditor = root / tools.get("independentAuditor", "missing")
    static_auditor = Path(__file__).resolve()
    work = Path(contract.get("paths", {}).get("workRoot", ""))
    evidence = Path(contract.get("paths", {}).get("evidenceRoot", ""))

    self_test = subprocess.run(
        ["python3", str(runner), "--self-test"], cwd=root,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, capture_output=True, text=True,
    )
    inert = subprocess.run(
        [
            "python3", str(runner), "--execute",
            "--repository-root", str(root), "--engine-source", str(engine),
            "--binary", str(binary), "--work-root", str(work),
            "--evidence-root", str(evidence), "--tool-contract", str(args.contract),
            "--execution-contract", str(args.template),
        ],
        cwd=root, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, capture_output=True, text=True,
    )
    forbidden_network = {"socket", "urllib", "requests", "http", "ftplib"}
    runner_source = runner.read_text(encoding="utf-8")
    probe_source = probe.read_text(encoding="utf-8")
    formal_source = formal_auditor.read_text(encoding="utf-8")
    checks = {
        "schemaAndStatus": contract.get("schemaVersion") == "bfs.aiNativeStudioPb3ValidationToolFreeze.v0.2" and contract.get("status") == "FROZEN_INERT_EXECUTION_UNAUTHORIZED",
        "parentCommitCurrent": contract.get("parentResearchCommit") == git(["rev-parse", "HEAD"], root),
        "runnerHash": sha256_file(runner) == tools.get("runnerSha256"),
        "probeHash": sha256_file(probe) == tools.get("blenderProbeSha256"),
        "compilerHash": sha256_file(compiler) == tools.get("sceneCompilerSha256"),
        "formalAuditorHash": sha256_file(formal_auditor) == tools.get("independentAuditorSha256"),
        "staticAuditorHash": sha256_file(static_auditor) == tools.get("staticAuditorSha256"),
        "runnerAstNoNetwork": not (imports(runner) & forbidden_network),
        "probeAstNoNetwork": not (imports(probe) & forbidden_network),
        "formalAuditorDoesNotImportBpy": "bpy" not in imports(formal_auditor),
        "formalAuditorDoesNotImportEngineContract": "film_studio_contract" not in imports(formal_auditor),
        "runnerRequiresExecute": "require(parsed.execute" in runner_source,
        "runnerRequiresExplicitPb3": "explicitPb3ScopePresent" in runner_source and '"PB.3"' in runner_source,
        "runnerUsesOfflineMode": runner_source.count('"--offline-mode"') >= 2,
        "runnerUsesDisableAutoexec": runner_source.count('"--disable-autoexec"') >= 2,
        "probeWritesExclusive": "os.O_EXCL" in probe_source,
        "probeHasNoRenderCall": "bpy.ops.render" not in probe_source,
        "formalAuditorHasNoBlenderStart": "subprocess.run([str(binary)" not in formal_source,
        "runnerSelfTest": self_test.returncode == 0 and '"status": "PASS"' in self_test.stdout,
        "templateNonExecutable": template.get("schemaVersion") == "bfs.aiNativeStudioPb3ValidationExecution.v0.3" and template.get("status") == "DRAFT_AUTHORIZATION_MISSING",
        "templateAuthorizationNull": all(template.get("authorization", {}).get(key) is None for key in ("exactUserText", "exactUserTextSha256", "authorizedAtUtc")),
        "templateBindsTool": template.get("toolFreeze", {}).get("sha256") == sha256_file(args.contract),
        "inertInvocationRejected": inert.returncode != 0 and "PB.3 execution is not authorized" in inert.stderr,
        "formalRootsStillAbsent": not work.exists() and not work.is_symlink() and not evidence.exists() and not evidence.is_symlink(),
        "sourceIdentity": git(["rev-parse", "HEAD"], engine) == contract.get("source", {}).get("head") and git(["status", "--porcelain"], engine) == "",
        "binaryIdentity": sha256_file(binary) == contract.get("binary", {}).get("sha256"),
        "fourStartsTwoWritesFrozen": contract.get("futureAuthorizedMaximums", {}).get("blenderStarts") == 4 and contract.get("futureAuthorizedMaximums", {}).get("proposalExecutions") == 2 and contract.get("futureAuthorizedMaximums", {}).get("buildPlanWrites") == 2,
        "allForbiddenCountsZeroNow": all(value == 0 for value in contract.get("currentCounts", {}).values()),
    }
    passed = sum(bool(value) for value in checks.values())
    audit = {
        "schemaVersion": "bfs.aiNativeStudioPb3ToolFreezeStaticAudit.v0.1",
        "status": "PASS" if passed == len(checks) else "FAIL",
        "checks": checks,
        "counts": {
            "passed": passed, "total": len(checks), "systemPythonSelfTests": 1,
            "inertRunnerInvocations": 1, "blenderStarts": 0, "proposalExecutions": 0,
            "buildPlanWrites": 0, "sceneMutations": 0, "renders": 0,
            "engineSourceEdits": 0, "engineRemoteWrites": 0, "networkCalls": 0,
        },
        "selfTestStdoutSha256": sha256_bytes(self_test.stdout.encode()),
        "inertStderrSha256": sha256_bytes(inert.stderr.encode()),
        "claimCeiling": contract.get("claimCeiling"),
    }
    audit["auditHash"] = sha256_bytes(canonical(audit))
    write_exclusive(args.output, audit)
    print(f"PB3_TOOL_AUDIT {audit['status']} {passed}/{len(checks)} auditHash={audit['auditHash']}")
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
