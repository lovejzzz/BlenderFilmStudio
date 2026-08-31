#!/usr/bin/env python3
"""Static/negative audit for inert PB.3 C5 tool preparation."""

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


def tree_manifest(root: Path) -> dict:
    if not root.is_dir() or root.is_symlink():
        raise RuntimeError(f"root is not exact: {root}")
    rows = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        if path.is_symlink():
            raise RuntimeError(f"symbolic path: {path}")
        if path.is_file():
            rows.append({"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return {"regularFiles": len(rows), "regularFileBytes": sum(row["bytes"] for row in rows), "manifestSha256": sha256_bytes(canonical(rows))}


def run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=120)


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
    parser.add_argument("--c5-contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    c5_path = args.c5_contract.resolve(strict=True)
    c5 = json.loads(c5_path.read_text(encoding="utf-8"))
    root = c5_path.parent.parent
    output = args.output.resolve(strict=False)
    tool_path = root / c5["correctedTool"]["uri"]
    tool = json.loads(tool_path.read_text(encoding="utf-8"))
    c4_path = root / c5["c4Binding"]["uri"]
    request_path = root / c5["authorizationRequest"]["uri"]
    request = json.loads(request_path.read_text(encoding="utf-8"))
    template_path = root / c5["executionTemplate"]
    template = json.loads(template_path.read_text(encoding="utf-8"))
    runner_path = root / c5["tools"]["runner"]
    auditor_path = root / c5["tools"]["independentAuditor"]
    static_path = Path(__file__).resolve(strict=True)
    runner_source = runner_path.read_text(encoding="utf-8")
    auditor_source = auditor_path.read_text(encoding="utf-8")
    work04 = Path(c5["paths"]["attempt04WorkRoot"])
    evidence04 = Path(c5["paths"]["attempt04EvidenceRoot"])
    fresh_before = not work04.exists() and not evidence04.exists()
    inputs = [*tool["commonInputs"], *(record for fixture in tool["fixtures"] for record in fixture["inputs"])]
    retained03 = c5["retainedAttempt03"]
    retained03_exact = not Path(retained03["workRoot"]).exists() and tree_manifest(Path(retained03["evidenceRoot"])) == retained03["evidenceManifest"]
    retained03_exact = retained03_exact and all(sha256_file(Path(retained03["evidenceRoot"]) / record["name"]) == record["sha256"] for record in retained03["files"])
    base_c4 = json.loads(c4_path.read_text(encoding="utf-8"))
    retained12_exact = all(
        tree_manifest(Path(row["workRoot"])) == row["workManifest"]
        and tree_manifest(Path(row["evidenceRoot"])) == row["evidenceManifest"]
        and all(sha256_file(Path(row["evidenceRoot"]) / record["name"]) == record["sha256"] for record in row.get("files", []))
        for row in base_c4["retainedAttempts"]
    )
    self_test = run(["python3", str(runner_path), "--c5-contract", str(c5_path), "--self-test"], root)
    inert = run([
        "python3", str(runner_path), "--c5-contract", str(c5_path), "--execute",
        "--repository-root", str(root), "--engine-source", c5["source"]["root"],
        "--binary", c5["binary"]["path"], "--work-root", str(work04),
        "--evidence-root", str(evidence04), "--tool-contract", str(tool_path),
        "--execution-contract", str(template_path),
    ], root)
    fresh_after = not work04.exists() and not evidence04.exists()
    forbidden_network_literals = ("ls-remote", "https://", "http://", "curl ", "urllib", "requests.")
    checks = {
        "c5SchemaStatus": c5.get("schemaVersion") == "bfs.aiNativeStudioPb3ValidationC5ExecutionToolFreeze.v1.8" and c5.get("status") == "FROZEN_INERT_C5_EXECUTION_TOOLING",
        "staticAuditorHash": sha256_file(static_path) == c5["tools"]["staticAuditorSha256"],
        "runnerHash": sha256_file(runner_path) == c5["tools"]["runnerSha256"],
        "independentAuditorHash": sha256_file(auditor_path) == c5["tools"]["independentAuditorSha256"],
        "c4Hash": sha256_file(c4_path) == c5["c4Binding"]["sha256"],
        "correctedToolHash": sha256_file(tool_path) == c5["correctedTool"]["sha256"],
        "c5CorrectionHash": sha256_file(root / c5["corrections"][0]["uri"]) == c5["corrections"][0]["sha256"],
        "c5C1CorrectionHash": sha256_file(root / c5["corrections"][1]["uri"]) == c5["corrections"][1]["sha256"],
        "authorizationRequestHash": sha256_file(request_path) == c5["authorizationRequest"]["sha256"],
        "requestStillUnauthorized": request["status"] == "AWAITING_EXPLICIT_USER_AUTHORIZATION" and request["requestedAuthorization"]["generalContinueIsInsufficient"] is True,
        "templateInert": template.get("status") == "DRAFT_AUTHORIZATION_MISSING" and template.get("authorization", {}).get("exactUserText") is None,
        "templateBindsC5": template.get("toolC5Correction", {}).get("sha256") == sha256_file(c5_path),
        "templateScopeArrayExact": template.get("stillUnauthorized") == tool.get("stillUnauthorized"),
        "templateAttempt04Roots": template.get("authorizedRun", {}).get("workRoot") == str(work04) and template.get("authorizedRun", {}).get("evidenceRoot") == str(evidence04),
        "runnerUsesExactScope": 'execution.get("stillUnauthorized") == json.loads(tool_path.read_text(encoding="utf-8"))["stillUnauthorized"]' in runner_source,
        "runnerRetainsAttempt03": "retained attempt-03 work root changed" in runner_source and "retained attempt-03 evidence root changed" in runner_source,
        "auditorUsesC3ReceiptBinding": 'resources.get("c3CorrectionSha256")' in auditor_source and 'resources.get("c4CorrectionSha256")' not in auditor_source,
        "auditorFullArtifactPredicate": all(suffix in auditor_source for suffix in ('.exr', '.png', '.jpg', '.jpeg', '.mov', '.mp4')),
        "noNetworkLiteralsInFormalTools": not any(value in runner_source or value in auditor_source for value in forbidden_network_literals),
        "inputRoster13Exact": len(inputs) == 13 and all(sha256_file(root / record["uri"]) == record["sha256"] for record in inputs),
        "retainedAttempt01And02Exact": retained12_exact,
        "retainedAttempt03Exact": retained03_exact,
        "attempt04FreshBeforeAfter": fresh_before and fresh_after,
        "sourceIdentityClean": subprocess.run(["git", "rev-parse", "HEAD"], cwd=c5["source"]["root"], capture_output=True, text=True, check=True).stdout.strip() == c5["source"]["head"] and subprocess.run(["git", "status", "--porcelain"], cwd=c5["source"]["root"], capture_output=True, text=True, check=True).stdout.strip() == "",
        "binaryIdentity": sha256_file(Path(c5["binary"]["path"])) == c5["binary"]["sha256"],
        "resourcesUnchanged": c5["resources"] == {"maximumWorkRootBytes": 2147483648, "maximumEvidenceRootBytes": 67108864},
        "operationCeilingsUnchanged": c5["acceptance"]["maximumBlenderStarts"] == 4 and c5["acceptance"]["maximumProposalExecutions"] == 2 and c5["acceptance"]["maximumBuildPlanWrites"] == 2 and c5["acceptance"]["renders"] == c5["acceptance"]["networkCalls"] == 0,
        "runnerSelfTestPass": self_test.returncode == 0 and '"status": "PASS"' in self_test.stdout,
        "inertTemplateRejected": inert.returncode != 0 and "PB.3 C5 execution is not authorized" in inert.stderr,
        "zeroFormalCounts": all(value == 0 for value in c5["currentCounts"].values()),
    }
    passed = sum(checks.values())
    body = {
        "schemaVersion": "bfs.aiNativeStudioPb3ValidationC5StaticAudit.v0.1",
        "status": "PASS" if passed == len(checks) else "FAIL",
        "checks": checks,
        "counts": {"passed": passed, "total": len(checks), **c5["currentCounts"]},
        "negativeControls": {"runnerSelfTestExit": self_test.returncode, "inertTemplateExit": inert.returncode, "inertTemplateStderr": inert.stderr.strip()},
        "retainedAttempt03Manifest": tree_manifest(Path(retained03["evidenceRoot"])),
        "claimCeiling": "Static and negative-control evidence only. No Blender process, formal root, proposal, render, network call, or engine mutation was authorized or performed.",
    }
    body["auditHash"] = sha256_bytes(canonical(body))
    output.parent.mkdir(parents=True, exist_ok=False)
    write_exclusive(output, body)
    print(json.dumps({"status": body["status"], "passed": passed, "total": len(checks), "auditHash": body["auditHash"]}, sort_keys=True))
    return 0 if body["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
