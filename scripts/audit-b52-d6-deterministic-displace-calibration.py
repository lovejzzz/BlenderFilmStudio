#!/usr/bin/env python3
"""Independent integrity and replay audit for B52-D6."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from b52_d6_reference import SPEC_SHA256, canonical_hash, sha256_file


EVIDENCE_FIELDS = {
    "PARENT_IDENTITY": "parentIdentity",
    "RUNTIME_BINARY_IDENTITY": "runtimeBinaryIdentity",
    "OCIO_IDENTITY": "ocioIdentity",
    "CASE_ROSTER": "caseRoster",
    "PROCESS_ROSTER": "processRoster",
    "PID_UNIQUENESS": "pidUniqueness",
    "REPORT_SELF_HASH": "reportSelfHash",
    "SOURCE_FORMULA": "sourceFormula",
    "DISPLACEMENT_FORMULA": "displacementFormula",
    "RNA_CONTRACT": "rnaContract",
    "GRAPH_CONTRACT": "graphContract",
    "OPERATION_COUNTS": "operationCounts",
    "OUTPUT_HASH": "outputHash",
    "DECODED_REPEAT": "decodedRepeat",
    "REFERENCE_ARRAY_HASH": "referenceArrayHash",
    "REFERENCE_MATCH": "referenceMatch",
    "TASK_SENSITIVITY": "taskSensitivity",
    "DIAGNOSTIC_ROSTER": "diagnosticRoster",
    "DIAGNOSTIC_SIDECAR": "diagnosticSidecar",
    "RESULT_SELF_HASH": "resultSelfHash",
}


def git_blob_hash(root: Path, commit: str, uri: str) -> str | None:
    process = subprocess.run(["git", "show", f"{commit}:{uri}"], cwd=root, capture_output=True, check=False)
    return hashlib.sha256(process.stdout).hexdigest() if process.returncode == 0 else None


def report_hash_valid(report: dict) -> bool:
    body = {key: value for key, value in report.items() if key != "reportHash"}
    return report.get("reportHash") == canonical_hash(body)


def first_failure(evidence: dict, spec: dict) -> str | None:
    for attack in spec["attacks"]:
        if not evidence.get(EVIDENCE_FIELDS[attack], False):
            return attack
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError("refusing to overwrite B52-D6 audit")
    root = args.spec.resolve().parent.parent
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    result = json.loads(args.result.read_text(encoding="utf-8"))
    if sha256_file(args.spec) != SPEC_SHA256:
        raise RuntimeError("B52-D6 spec hash mismatch")

    receipt_body = {key: value for key, value in receipt.items() if key != "receiptHash"}
    result_body = {key: value for key, value in result.items() if key != "resultHash"}
    core = {"evidence": result["evidence"], "measurements": result["measurements"], "operationCounts": result["operationCounts"], "verdict": result["verdict"], "baseFailure": result["baseFailure"]}
    receipt_self_hash = receipt.get("receiptHash") == canonical_hash(receipt_body)
    result_self_hash = result.get("resultHash") == canonical_hash(result_body)
    evidence_core_hash = result.get("evidenceCoreHash") == canonical_hash(core)

    frozen_tool_checks = []
    for binding in receipt["tools"].values():
        current = sha256_file(root / binding["uri"]) if (root / binding["uri"]).is_file() else None
        frozen = git_blob_hash(root, receipt["toolFreezeCommit"], binding["uri"])
        frozen_tool_checks.append({"uri": binding["uri"], "expectedSha256": binding["sha256"], "currentSha256": current, "frozenSha256": frozen, "match": current == frozen == binding["sha256"]})
    bound_input_checks = []
    for observation in receipt["parentObservations"]:
        current = sha256_file(root / observation["uri"]) if (root / observation["uri"]).is_file() else None
        bound_input_checks.append({"uri": observation["uri"], "expectedSha256": observation["expectedSha256"], "currentSha256": current, "match": current == observation["expectedSha256"] == observation["observedSha256"]})
    ocio = receipt["runtimeObservations"]["ocio"]
    current_ocio = sha256_file(root / ocio["uri"])
    blender = receipt["runtimeObservations"]["blender"]
    current_blender = sha256_file(Path(blender["uri"]))
    runtime_exact = current_ocio == ocio["expectedSha256"] == ocio["observedSha256"] and current_blender == blender["expectedSha256"] == blender["observedSha256"]

    run_checks = []
    for run in receipt["runs"]:
        report_path = root / run["reportUri"]
        report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else None
        output = report.get("output") if report else None
        output_path = root / output["uri"] if output else None
        match = (
            report is not None
            and report == run["report"]
            and report_hash_valid(report)
            and output_path is not None
            and output_path.is_file()
            and sha256_file(output_path) == output["sha256"]
            and output_path.stat().st_size == output["bytes"]
        )
        run_checks.append({"cellId": run["cellId"], "reportUri": run["reportUri"], "outputUri": output.get("uri") if output else None, "match": match})

    artifact_checks = []
    for measurement in result["measurements"]:
        reference = measurement["reference"]
        reference_path = root / reference["uri"]
        artifact_checks.append({"kind": "reference", "fixtureId": measurement["fixtureId"], "uri": reference["uri"], "match": reference_path.is_file() and sha256_file(reference_path) == reference["sha256"] and reference_path.stat().st_size == reference["bytes"]})
    for diagnostic in result["diagnostics"]:
        for kind in ("png", "sidecar"):
            binding = diagnostic[kind]
            path = root / binding["uri"]
            artifact_checks.append({"kind": kind, "fixtureId": diagnostic["fixtureId"], "mapKind": diagnostic["kind"], "uri": binding["uri"], "match": path.is_file() and sha256_file(path) == binding["sha256"] and path.stat().st_size == binding["bytes"]})

    analyzer = root / receipt["tools"]["analyzer"]["uri"]
    with tempfile.TemporaryDirectory(prefix="bfs-b52-d6-audit-", dir=root / "experiments") as temporary_string:
        temporary = Path(temporary_string)
        replay_result = temporary / "results.json"
        command = [sys.executable, str(analyzer), "--spec", str(args.spec.resolve()), "--receipt", str(args.receipt.resolve()), "--output", str(replay_result)]
        process = subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)
        replay_exact = process.returncode == 0 and replay_result.is_file() and replay_result.read_bytes() == args.result.read_bytes()
        replay_artifact_checks = []
        if replay_exact:
            for measurement in result["measurements"]:
                actual = root / measurement["reference"]["uri"]
                replay = temporary / "references" / actual.name
                replay_artifact_checks.append({"uri": measurement["reference"]["uri"], "match": replay.is_file() and replay.read_bytes() == actual.read_bytes()})
            for diagnostic in result["diagnostics"]:
                for kind in ("png", "sidecar"):
                    actual = root / diagnostic[kind]["uri"]
                    replay = temporary / "diagnostics" / actual.name
                    replay_artifact_checks.append({"uri": diagnostic[kind]["uri"], "match": replay.is_file() and replay.read_bytes() == actual.read_bytes()})
        replay_stdout = process.stdout.strip()
        replay_stderr = process.stderr.strip()

    observed_failure = first_failure(result["evidence"], spec)
    expected_verdict = spec["decision"]["passVerdict"] if observed_failure is None else spec["decision"]["failVerdict"]
    operation_expected = {
        "blenderProcesses": spec["blenderMatrix"]["expectedProcesses"],
        "renderCalls": spec["blenderMatrix"]["expectedRenderCalls"],
        "cyclesRayRenders": spec["blenderMatrix"]["expectedCyclesRayRenders"],
        "sourceBlendFilesOpened": spec["blenderMatrix"]["sourceBlendFilesOpened"],
        "externalAssetsOpened": spec["blenderMatrix"]["externalAssetsOpened"],
    }
    integrity = {
        "receiptSelfHashExact": receipt_self_hash,
        "resultSelfHashExact": result_self_hash,
        "evidenceCoreHashExact": evidence_core_hash,
        "analysisReplayByteExact": replay_exact,
        "replayArtifactsByteExact": len(replay_artifact_checks) == len(spec["fixtures"]) + spec["diagnostics"]["expectedPngs"] * 2 and all(item["match"] for item in replay_artifact_checks),
        "frozenToolsExact": len(frozen_tool_checks) == len(receipt["tools"]) and all(item["match"] for item in frozen_tool_checks),
        "boundInputsExact": len(bound_input_checks) == len(spec["parents"]) and all(item["match"] for item in bound_input_checks),
        "runtimeExact": runtime_exact,
        "runArtifactsExact": len(run_checks) == spec["blenderMatrix"]["expectedProcesses"] and all(item["match"] for item in run_checks),
        "derivedArtifactsExact": len(artifact_checks) == len(spec["fixtures"]) + spec["diagnostics"]["expectedPngs"] * 2 and all(item["match"] for item in artifact_checks),
        "attackContractExact": result["attacksPassed"] == len(spec["attacks"]) and len(result["attacks"]) == len(spec["attacks"]) and all(item["passed"] for item in result["attacks"]),
        "operationCountsExact": result["operationCounts"] == operation_expected,
        "scientificVerdictConsistent": result["baseFailure"] == observed_failure and result["verdict"] == expected_verdict,
    }
    passed = all(integrity.values())
    audit_body = {
        "schemaVersion": "bfs.deterministicDisplaceCalibrationAudit.v0.1",
        "status": "PASS" if passed else "FAIL",
        "scientificVerdict": result["verdict"],
        "baseFailure": result["baseFailure"],
        "auditInterpretation": "PASS means the evidence is intact and independently replayable; it does not force a supported scientific verdict.",
        "integrityChecks": integrity,
        "receipt": {"uri": str(args.receipt.resolve().relative_to(root)), "sha256": sha256_file(args.receipt)},
        "result": {"uri": str(args.result.resolve().relative_to(root)), "sha256": sha256_file(args.result)},
        "frozenToolChecks": frozen_tool_checks,
        "boundInputChecks": bound_input_checks,
        "runChecks": run_checks,
        "artifactChecks": artifact_checks,
        "replayArtifactChecks": replay_artifact_checks,
        "replayStdout": replay_stdout,
        "replayStderr": replay_stderr,
        "failures": [] if passed else [name for name, value in integrity.items() if not value],
    }
    audit = {**audit_body, "auditHash": canonical_hash(audit_body)}
    args.output.write_text(json.dumps(audit, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(f"BFS_B52_D6_AUDIT {audit['status']} replayExact={replay_exact} runs={sum(item['match'] for item in run_checks)}/{len(run_checks)} artifacts={sum(item['match'] for item in artifact_checks)}/{len(artifact_checks)} scientific={result['verdict']}", flush=True)
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
