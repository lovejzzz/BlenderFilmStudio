#!/usr/bin/env python3
"""Static and negative audit for the PB.3 C6 standing-authority adapter."""

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
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise RuntimeError("audit write made no progress")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--c6-contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    c6_path = args.c6_contract.resolve(strict=True)
    c6 = json.loads(c6_path.read_text(encoding="utf-8"))
    root = c6_path.parent.parent
    output = args.output.resolve(strict=False)
    charter_path = root / c6["standingCharter"]["uri"]
    charter = json.loads(charter_path.read_text(encoding="utf-8"))
    historical_path = root / c6["historicalRequest"]["uri"]
    c5_path = root / c6["c5Binding"]["uri"]
    c4_path = root / c6["c4Binding"]["uri"]
    c4 = json.loads(c4_path.read_text(encoding="utf-8"))
    tool_path = root / c6["correctedTool"]["uri"]
    tool = json.loads(tool_path.read_text(encoding="utf-8"))
    template_path = root / c6["executionTemplate"]
    template = json.loads(template_path.read_text(encoding="utf-8"))
    runner_path = root / c6["tools"]["runner"]
    auditor_path = root / c6["tools"]["independentAuditor"]
    static_path = Path(__file__).resolve(strict=True)
    runner_source = runner_path.read_text(encoding="utf-8")
    auditor_source = auditor_path.read_text(encoding="utf-8")
    work04 = Path(c6["paths"]["attempt04WorkRoot"])
    evidence04 = Path(c6["paths"]["attempt04EvidenceRoot"])
    fresh_before = not work04.exists() and not evidence04.exists()
    inputs = [*tool["commonInputs"], *(record for fixture in tool["fixtures"] for record in fixture["inputs"])]
    retained03 = c6["retainedAttempt03"]
    retained03_exact = not Path(retained03["workRoot"]).exists() and tree_manifest(Path(retained03["evidenceRoot"])) == retained03["evidenceManifest"]
    retained03_exact = retained03_exact and all(sha256_file(Path(retained03["evidenceRoot"]) / record["name"]) == record["sha256"] for record in retained03["files"])
    retained12_exact = all(
        tree_manifest(Path(row["workRoot"])) == row["workManifest"]
        and tree_manifest(Path(row["evidenceRoot"])) == row["evidenceManifest"]
        and all(sha256_file(Path(row["evidenceRoot"]) / record["name"]) == record["sha256"] for record in row.get("files", []))
        for row in c4["retainedAttempts"]
    )
    self_test = run(["python3", str(runner_path), "--c6-contract", str(c6_path), "--self-test"], root)
    inert = run([
        "python3", str(runner_path), "--c6-contract", str(c6_path), "--execute",
        "--repository-root", str(root), "--engine-source", c6["source"]["root"],
        "--binary", c6["binary"]["path"], "--work-root", str(work04),
        "--evidence-root", str(evidence04), "--tool-contract", str(tool_path),
        "--execution-contract", str(template_path),
    ], root)
    fresh_after = not work04.exists() and not evidence04.exists()
    forbidden_network_literals = ("ls-remote", "https://", "http://", "curl ", "urllib", "requests.")
    owner = charter["ownerAuthority"]
    checks = {
        "c6SchemaStatus": c6.get("schemaVersion") == "bfs.aiNativeStudioPb3ValidationC6ExecutionToolFreeze.v1.13" and c6.get("status") == "FROZEN_INERT_C6_STANDING_AUTHORITY_TOOLING",
        "staticAuditorHash": sha256_file(static_path) == c6["tools"]["staticAuditorSha256"],
        "runnerHash": sha256_file(runner_path) == c6["tools"]["runnerSha256"],
        "independentAuditorHash": sha256_file(auditor_path) == c6["tools"]["independentAuditorSha256"],
        "standingCharterHash": sha256_file(charter_path) == c6["standingCharter"]["sha256"],
        "standingCharterActive": charter.get("status") == "ACTIVE_STANDING_AUTHORITY" and owner["exactUserTextSha256"] == sha256_bytes(owner["exactUserText"].encode()),
        "historicalRequestPreserved": sha256_file(historical_path) == c6["historicalRequest"]["sha256"] and c6["historicalRequest"]["exactTextWasNotSupplied"] is True,
        "c5Hash": sha256_file(c5_path) == c6["c5Binding"]["sha256"],
        "c4Hash": sha256_file(c4_path) == c6["c4Binding"]["sha256"],
        "correctedToolHash": sha256_file(tool_path) == c6["correctedTool"]["sha256"],
        "templateInert": template.get("status") == "DRAFT_STANDING_EXECUTION_NOT_COMMITTED" and template.get("authorization", {}).get("ownerExactText") is None,
        "templateDoesNotClaimHistoricalText": "exactUserText" not in template.get("authorization", {}) and "authorizationRequest" not in template,
        "templateBindsC6": template.get("toolC6Correction", {}).get("sha256") == sha256_file(c6_path),
        "templateBindsStandingCharter": template.get("standingCharter") == c6["standingCharter"] and template.get("historicalRequest") == c6["historicalRequest"],
        "templateScopeExact": template.get("stillUnauthorized") == tool.get("stillUnauthorized"),
        "templateAttempt04Roots": template.get("authorizedRun", {}).get("workRoot") == str(work04) and template.get("authorizedRun", {}).get("evidenceRoot") == str(evidence04),
        "runnerUsesStandingOwnerText": 'authorization.get("ownerExactText") == owner["exactUserText"]' in runner_source,
        "runnerRejectsHistoricalClaim": '"exactUserText" not in authorization and "authorizationRequest" not in execution' in runner_source,
        "auditorUsesStandingCharter": '"standingCharterBinding"' in auditor_source and '"standingOwnerTextExact"' in auditor_source,
        "auditorFullArtifactPredicate": all(suffix in auditor_source for suffix in ('.exr', '.png', '.jpg', '.jpeg', '.mov', '.mp4')),
        "noNetworkLiteralsInFormalTools": not any(value in runner_source or value in auditor_source for value in forbidden_network_literals),
        "inputRoster13Exact": len(inputs) == 13 and all(sha256_file(root / record["uri"]) == record["sha256"] for record in inputs),
        "retainedAttempt01And02Exact": retained12_exact,
        "retainedAttempt03Exact": retained03_exact,
        "attempt04FreshBeforeAfter": fresh_before and fresh_after,
        "sourceIdentityClean": subprocess.run(["git", "rev-parse", "HEAD"], cwd=c6["source"]["root"], capture_output=True, text=True, check=True).stdout.strip() == c6["source"]["head"] and subprocess.run(["git", "status", "--porcelain"], cwd=c6["source"]["root"], capture_output=True, text=True, check=True).stdout.strip() == "",
        "binaryIdentity": sha256_file(Path(c6["binary"]["path"])) == c6["binary"]["sha256"],
        "resourcesUnchanged": c6["resources"] == {"maximumWorkRootBytes": 2147483648, "maximumEvidenceRootBytes": 67108864},
        "operationCeilingsUnchanged": c6["acceptance"]["maximumBlenderStarts"] == 4 and c6["acceptance"]["maximumProposalExecutions"] == 2 and c6["acceptance"]["maximumBuildPlanWrites"] == 2 and c6["acceptance"]["renders"] == c6["acceptance"]["networkCalls"] == 0,
        "runnerSelfTestPass": self_test.returncode == 0 and '"status": "PASS"' in self_test.stdout,
        "inertTemplateRejected": inert.returncode != 0 and "PB.3 C6 execution is not authorized" in inert.stderr,
        "zeroFormalCounts": all(value == 0 for value in c6["currentCounts"].values()),
    }
    passed = sum(checks.values())
    body = {
        "schemaVersion": "bfs.aiNativeStudioPb3ValidationC6StaticAudit.v0.1",
        "status": "PASS" if passed == len(checks) else "FAIL",
        "checks": checks,
        "counts": {"passed": passed, "total": len(checks), **c6["currentCounts"]},
        "negativeControls": {"runnerSelfTestExit": self_test.returncode, "inertTemplateExit": inert.returncode, "inertTemplateStderr": inert.stderr.strip()},
        "retainedAttempt03Manifest": tree_manifest(Path(retained03["evidenceRoot"])),
        "claimCeiling": "Static and negative-control evidence only. No Blender process, formal root, proposal, render, network call or engine mutation was performed.",
    }
    body["auditHash"] = sha256_bytes(canonical(body))
    output.parent.mkdir(parents=True, exist_ok=False)
    write_exclusive(output, body)
    print(json.dumps({"status": body["status"], "passed": passed, "total": len(checks), "auditHash": body["auditHash"]}, sort_keys=True))
    return 0 if body["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
