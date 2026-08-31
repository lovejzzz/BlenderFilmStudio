#!/usr/bin/env python3
"""Static and negative audit for the inert PB.3 C4 tool freeze."""

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


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def tree_manifest(root: Path) -> dict:
    require(root.is_dir() and not root.is_symlink(), f"retained root invalid: {root}")
    rows = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        require(not path.is_symlink(), f"retained root contains symlink: {path}")
        if path.is_file():
            rows.append({"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return {
        "regularFiles": len(rows),
        "regularFileBytes": sum(row["bytes"] for row in rows),
        "manifestSha256": sha256_bytes(canonical(rows)),
    }


def json_diff(left: object, right: object, path: str = "") -> list[tuple[str, object, object]]:
    if type(left) is not type(right):
        return [(path, left, right)]
    if isinstance(left, dict):
        if left.keys() != right.keys():
            return [(path + ".keys", sorted(left), sorted(right))]
        rows = []
        for key in left:
            rows.extend(json_diff(left[key], right[key], f"{path}.{key}" if path else key))
        return rows
    if isinstance(left, list):
        if len(left) != len(right):
            return [(path + ".length", len(left), len(right))]
        rows = []
        for index, value in enumerate(left):
            rows.extend(json_diff(value, right[index], f"{path}[{index}]"))
        return rows
    return [] if left == right else [(path, left, right)]


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
            written = os.write(descriptor, payload[offset:])
            require(written > 0, "static audit write made no progress")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def main() -> int:
    args = arguments()
    root = args.repository_root.resolve(strict=True)
    engine = args.engine_source.resolve(strict=True)
    binary = args.binary.resolve(strict=True)
    c4_path = args.correction.resolve(strict=True)
    c4 = json.loads(c4_path.read_text(encoding="utf-8"))
    template = json.loads(args.template.read_text(encoding="utf-8"))
    prereg_path = root / c4["correctionPreregistration"]["uri"]
    request_path = root / c4["authorizationRequest"]["uri"]
    corrected_path = root / c4["correctedTool"]["uri"]
    prior_tool_path = root / c4["base"]["c3CorrectedTool"]
    prior_helper_path = root / c4["base"]["c3BlenderHelper"]
    helper_path = root / c4["correctedTool"]["blenderHelper"]
    runner = root / c4["tools"]["runner"]
    auditor = root / c4["tools"]["independentAuditor"]
    static = Path(__file__).resolve(strict=True)
    request = json.loads(request_path.read_text(encoding="utf-8"))
    corrected = json.loads(corrected_path.read_text(encoding="utf-8"))
    prior_tool = json.loads(prior_tool_path.read_text(encoding="utf-8"))
    helper_lines = helper_path.read_text(encoding="utf-8").splitlines()
    prior_helper_lines = prior_helper_path.read_text(encoding="utf-8").splitlines()
    added = [line for line in helper_lines if line not in prior_helper_lines]
    forbidden = {"bpy", "socket", "urllib", "requests", "http", "ftplib"}
    runner_text = runner.read_text(encoding="utf-8")
    auditor_text = auditor.read_text(encoding="utf-8")
    tool_differences = json_diff(prior_tool, corrected)
    self_test = subprocess.run(
        ["python3", str(runner), "--c4-contract", str(c4_path), "--self-test"],
        cwd=root, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, capture_output=True, text=True,
    )
    attempt_work = Path(c4["paths"]["attempt03WorkRoot"])
    attempt_evidence = Path(c4["paths"]["attempt03EvidenceRoot"])
    inert = subprocess.run(
        [
            "python3", str(runner), "--c4-contract", str(c4_path), "--execute",
            "--repository-root", str(root), "--engine-source", str(engine), "--binary", str(binary),
            "--work-root", str(attempt_work), "--evidence-root", str(attempt_evidence),
            "--tool-contract", str(corrected_path), "--execution-contract", str(args.template.resolve(strict=True)),
        ],
        cwd=root, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, capture_output=True, text=True,
    )
    retained_exact = all(
        tree_manifest(Path(row["workRoot"])) == row["workManifest"]
        and tree_manifest(Path(row["evidenceRoot"])) == row["evidenceManifest"]
        and all(sha256_file(Path(row["evidenceRoot"]) / record["name"]) == record["sha256"] for record in row.get("files", []))
        for row in c4["retainedAttempts"]
    )
    input_records = [*corrected["commonInputs"], *(record for fixture in corrected["fixtures"] for record in fixture["inputs"])]
    checks = {
        "c4SchemaStatus": c4.get("schemaVersion") == "bfs.aiNativeStudioPb3ValidationC4ExecutionToolFreeze.v1.2" and c4.get("status") == "FROZEN_INERT_C4_EXECUTION_TOOLING",
        "staticAuditorSelfBinding": c4["tools"]["staticAuditorSha256"] == sha256_file(static),
        "runnerBinding": c4["tools"]["runnerSha256"] == sha256_file(runner),
        "independentAuditorBinding": c4["tools"]["independentAuditorSha256"] == sha256_file(auditor),
        "preregistrationBinding": c4["correctionPreregistration"]["sha256"] == sha256_file(prereg_path),
        "authorizationRequestBinding": c4["authorizationRequest"]["sha256"] == sha256_file(request_path),
        "authorizationStillMissing": request.get("status") == "AWAITING_EXPLICIT_USER_AUTHORIZATION" and request["requestedAuthorization"]["generalContinueIsInsufficient"] is True,
        "correctedToolBinding": c4["correctedTool"]["sha256"] == sha256_file(corrected_path),
        "helperBinding": c4["correctedTool"]["blenderHelperSha256"] == sha256_file(helper_path),
        "toolDiffExactlyTwoFields": [row[0] for row in tool_differences] == ["tools.blenderProbe", "tools.blenderProbeSha256"],
        "helperDiffExactlyTwoLines": len(helper_lines) == len(prior_helper_lines) + 2 and added == [
            '    bpy.context.preferences.filepaths.file_preview_type = "NONE"',
            '    require(bpy.context.preferences.filepaths.file_preview_type == "NONE", "blend preview suppression failed")',
        ],
        "helperChangeImmediatelyBeforeSave": "file_preview_type = \"NONE\"\n    require(bpy.context.preferences.filepaths.file_preview_type == \"NONE\"" in helper_path.read_text(encoding="utf-8") and helper_lines.index(added[1]) + 1 == next(index for index, line in enumerate(helper_lines) if "save_as_mainfile" in line),
        "runnerNoPowerImports": not (imports(runner) & forbidden),
        "auditorNoPowerImports": not (imports(auditor) & forbidden),
        "helperOnlyExpectedPowerImport": imports(helper_path) & forbidden == {"bpy"},
        "runnerNormalizesBeforeDelegate": "replace_option(\"--tool-contract\", absolute_tool)" in runner_text and runner_text.index("replace_option(\"--tool-contract\", absolute_tool)") < runner_text.index("result = c3.main()", runner_text.index("replace_option(\"--tool-contract\", absolute_tool)")),
        "auditorRequiresAbsoluteToolPath": 'tool_path = Path(option_value("--tool-contract")).resolve(strict=True)' in auditor_text,
        "auditorPreservesAllArtifactExtensions": 'FORBIDDEN_ARTIFACT_SUFFIXES = {".exr", ".png", ".jpg", ".jpeg", ".mov", ".mp4"}' in auditor_text,
        "correctedInputRosterExact": len(input_records) == 13 and all(sha256_file(root / record["uri"]) == record["sha256"] for record in input_records),
        "retainedAttemptsExact": retained_exact,
        "attempt03RootsAbsentBeforeSelfTest": not attempt_work.exists() and not attempt_evidence.exists(),
        "attempt03RootsAbsentAfterInert": not attempt_work.exists() and not attempt_evidence.exists(),
        "runnerSelfTestPass": self_test.returncode == 0 and '"status": "PASS"' in self_test.stdout,
        "inertTemplateRejected": inert.returncode != 0 and "PB.3 C4 execution is not authorized" in inert.stderr,
        "templateInert": template.get("status") == "DRAFT_AUTHORIZATION_MISSING" and template.get("authorization", {}).get("exactUserText") is None,
        "sourceIdentity": c4["source"]["head"] == subprocess.run(["git", "rev-parse", "HEAD"], cwd=engine, check=True, capture_output=True, text=True).stdout.strip(),
        "sourceClean": subprocess.run(["git", "status", "--porcelain"], cwd=engine, check=True, capture_output=True, text=True).stdout == "",
        "binaryIdentity": c4["binary"]["sha256"] == sha256_file(binary),
        "resourcesUnchanged": c4["resources"] == {"maximumWorkRootBytes": 2147483648, "maximumEvidenceRootBytes": 67108864},
        "formalCountsRemainZero": all(value == 0 for value in c4["currentCounts"].values()),
        "noEngineMutationAuthorized": c4["acceptance"]["engineSourceEdits"] == c4["acceptance"]["engineRemoteWrites"] == c4["acceptance"]["networkCalls"] == c4["acceptance"]["renders"] == 0,
        "thresholdsUnchanged": c4["acceptance"]["thresholdsUnchanged"] is True,
    }
    passed = sum(bool(value) for value in checks.values())
    body = {
        "schemaVersion": "bfs.aiNativeStudioPb3C4ToolFreezeStaticAudit.v0.1",
        "status": "PASS" if passed == len(checks) else "FAIL",
        "checks": checks,
        "counts": {
            "passed": passed,
            "total": len(checks),
            "selfTests": 1,
            "inertInvocations": 1,
            "blenderStarts": 0,
            "proposalExecutions": 0,
            "buildPlanWrites": 0,
            "sceneBuilds": 0,
            "workspaceSaves": 0,
            "reopens": 0,
            "renders": 0,
            "networkCalls": 0,
            "engineSourceEdits": 0,
            "engineRemoteWrites": 0,
        },
        "toolDiff": [{"path": path, "before": before, "after": after} for path, before, after in tool_differences],
        "helperAddedLines": added,
        "runnerSelfTest": {"exitCode": self_test.returncode, "stdoutSha256": sha256_bytes(self_test.stdout.encode()), "stderrSha256": sha256_bytes(self_test.stderr.encode())},
        "inertTemplateInvocation": {"exitCode": inert.returncode, "stdoutSha256": sha256_bytes(inert.stdout.encode()), "stderrSha256": sha256_bytes(inert.stderr.encode())},
        "claimCeiling": c4["claimCeiling"],
    }
    body["auditHash"] = sha256_bytes(canonical(body))
    write_exclusive(args.output, body)
    print(f"PB3_C4_TOOL_AUDIT {body['status']} {passed}/{len(checks)} auditHash={body['auditHash']}")
    return 0 if body["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
