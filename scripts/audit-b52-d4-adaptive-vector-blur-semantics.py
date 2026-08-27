#!/usr/bin/env python3
"""Independent identity and replay audit for B52-D4."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_blob_hash(root: Path, commit: str, uri: str) -> str | None:
    process = subprocess.run(["git", "show", f"{commit}:{uri}"], cwd=root, capture_output=True, check=False)
    return hashlib.sha256(process.stdout).hexdigest() if process.returncode == 0 else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.spec.resolve().parent.parent
    output_root = args.output_root.resolve()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    receipt_path = output_root / "run.receipt.json"
    result_path = output_root / "results.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    result = json.loads(result_path.read_text(encoding="utf-8"))
    analyzer = root / receipt["tools"]["analyzer"]["uri"]
    amendment = receipt["analysisAmendment"]
    original_receipt_path = root / amendment["originalReceipt"]["uri"]
    original_failure_path = root / amendment["originalAnalysisFailure"]["uri"]
    original_receipt = json.loads(original_receipt_path.read_text(encoding="utf-8"))
    normalized_receipt = dict(receipt)
    normalized_receipt.pop("analysisAmendment", None)
    normalized_receipt["toolFreezeCommit"] = original_receipt["toolFreezeCommit"]
    normalized_receipt["tools"] = original_receipt["tools"]
    changed_tool_uris = amendment["changedToolUris"]
    amendment_commit = amendment["freezeCommit"]
    amendment_parent = amendment["parentCommit"]
    commit_parent = subprocess.run(["git", "rev-parse", f"{amendment_commit}^"], cwd=root, capture_output=True, text=True, check=False)
    commit_files_process = subprocess.run(["git", "diff-tree", "--no-commit-id", "--name-only", "-r", amendment_commit], cwd=root, capture_output=True, text=True, check=False)
    commit_files = sorted(line for line in commit_files_process.stdout.splitlines() if line)
    expected_changed_tools = sorted(changed_tool_uris)
    unchanged_tool_hashes = all(
        receipt["tools"][name]["sha256"] == original_receipt["tools"][name]["sha256"]
        for name in receipt["tools"]
        if receipt["tools"][name]["uri"] not in changed_tool_uris
    )
    amendment_checks = {
        "classificationMatch": amendment.get("classification") == "POST_OUTPUT_MECHANICAL_SERIALIZATION_FIX",
        "outcomeGatesUnchanged": amendment.get("outcomeGatesChanged") is False,
        "formalOutputsReused": amendment.get("formalCompositorOutputsReused") == 36,
        "originalReceiptIdentityMatch": sha256_file(original_receipt_path) == amendment["originalReceipt"]["sha256"],
        "originalFailureIdentityMatch": sha256_file(original_failure_path) == amendment["originalAnalysisFailure"]["sha256"],
        "receiptNonToolFieldsExact": normalized_receipt == original_receipt,
        "commitParentMatch": commit_parent.returncode == 0 and commit_parent.stdout.strip() == amendment_parent,
        "commitFilesExact": commit_files_process.returncode == 0 and commit_files == expected_changed_tools,
        "unchangedToolHashesExact": unchanged_tool_hashes,
        "resultBindingMatch": result.get("analysisAmendment") == amendment,
    }

    with tempfile.TemporaryDirectory(prefix="bfs-b52-d4-audit-") as temporary:
        temporary_root = Path(temporary)
        replay_result = temporary_root / "results.json"
        process = subprocess.run([sys.executable, str(analyzer), "--spec", str(args.spec), "--receipt", str(receipt_path), "--output", str(replay_result)], cwd=root, capture_output=True, text=True, check=False)
        if process.returncode:
            raise RuntimeError(f"B52-D4 replay failed: {process.stdout}\n{process.stderr}")
        replay_exact = result_path.read_bytes() == replay_result.read_bytes()
        analysis_replay = {"uri": str(result_path.relative_to(root)), "originalSha256": sha256_file(result_path), "replaySha256": sha256_file(replay_result), "byteExact": replay_exact}
        diagnostic_checks = []
        for diagnostic in result["diagnostics"]:
            for kind in ("png", "sidecar"):
                binding = diagnostic[kind]
                actual_path = root / binding["uri"]
                replay_path = temporary_root / "diagnostics" / actual_path.name
                observed_sha = sha256_file(actual_path) if actual_path.is_file() else None
                replay_sha = sha256_file(replay_path) if replay_path.is_file() else None
                observed_bytes = actual_path.stat().st_size if actual_path.is_file() else None
                diagnostic_checks.append({
                    "profileId": diagnostic["profileId"], "variantId": diagnostic["variantId"], "mapKind": diagnostic["kind"], "artifactKind": kind, "uri": binding["uri"],
                    "expectedSha256": binding["sha256"], "observedSha256": observed_sha, "replaySha256": replay_sha, "expectedBytes": binding["bytes"], "observedBytes": observed_bytes,
                    "match": observed_sha == binding["sha256"] and replay_sha == binding["sha256"] and observed_bytes == binding["bytes"],
                })

    frozen_tools = []
    for name, binding in receipt["tools"].items():
        observed = git_blob_hash(root, binding["freezeCommit"], binding["uri"])
        frozen_tools.append({"name": name, "uri": binding["uri"], "freezeCommit": binding["freezeCommit"], "expectedSha256": binding["sha256"], "observedGitBlobSha256": observed, "match": observed == binding["sha256"]})

    bound_inputs = []
    for item in [receipt["specObservation"], *receipt["parentObservations"]]:
        path = root / item["uri"]
        observed = sha256_file(path) if path.is_file() else None
        bound_inputs.append({"kind": item["kind"], "uri": item["uri"], "expectedSha256": item["expectedSha256"], "observedSha256": observed, "match": observed == item["expectedSha256"]})
    blender = receipt["runtimeObservations"]["blender"]
    blender_path = Path(blender["uri"])
    bound_inputs.append({"kind": "BLENDER", "uri": blender["uri"], "expectedSha256": blender["expectedSha256"], "observedSha256": sha256_file(blender_path) if blender_path.is_file() else None, "match": blender_path.is_file() and sha256_file(blender_path) == blender["expectedSha256"] and blender_path.stat().st_size == blender["expectedBytes"]})
    ocio = receipt["runtimeObservations"]["ocio"]
    ocio_path = root / ocio["uri"]
    bound_inputs.append({"kind": "OCIO", "uri": ocio["uri"], "expectedSha256": ocio["expectedSha256"], "observedSha256": sha256_file(ocio_path) if ocio_path.is_file() else None, "match": ocio_path.is_file() and sha256_file(ocio_path) == ocio["expectedSha256"]})

    artifact_checks = []
    for item in receipt["parentArtifactObservations"]:
        path = root / item["uri"]
        observed_sha = sha256_file(path) if path.is_file() else None
        observed_bytes = path.stat().st_size if path.is_file() else None
        artifact_checks.append({"runId": item["kind"], "uri": item["uri"], "expectedSha256": item["expectedSha256"], "observedSha256": observed_sha, "expectedBytes": item["expectedBytes"], "observedBytes": observed_bytes, "match": observed_sha == item["expectedSha256"] and observed_bytes == item["expectedBytes"]})

    output_checks = []
    for item in result["outputObservations"]:
        path = root / item["uri"]
        observed_sha = sha256_file(path) if path.is_file() else None
        observed_bytes = path.stat().st_size if path.is_file() else None
        output_checks.append({"cellId": item["cellId"], "uri": item["uri"], "expectedSha256": item["expectedSha256"], "observedSha256": observed_sha, "expectedBytes": item["expectedBytes"], "observedBytes": observed_bytes, "match": observed_sha == item["expectedSha256"] and observed_bytes == item["expectedBytes"]})

    source_post_checks = []
    for item in receipt["sourcePostObservations"]:
        path = root / item["uri"]
        observed_sha = sha256_file(path) if path.is_file() else None
        observed_bytes = path.stat().st_size if path.is_file() else None
        source_post_checks.append({"runId": item["kind"], "uri": item["uri"], "expectedSha256": item["expectedSha256"], "observedSha256": observed_sha, "expectedBytes": item["expectedBytes"], "observedBytes": observed_bytes, "match": observed_sha == item["expectedSha256"] and observed_bytes == item["expectedBytes"]})

    passed = (
        replay_exact
        and all(amendment_checks.values())
        and len(frozen_tools) == 7 and all(item["match"] for item in frozen_tools)
        and len(bound_inputs) == 8 and all(item["match"] for item in bound_inputs)
        and len(artifact_checks) == 54 and all(item["match"] for item in artifact_checks)
        and len(output_checks) == 36 and all(item["match"] for item in output_checks)
        and len(source_post_checks) == 18 and all(item["match"] for item in source_post_checks)
        and len(diagnostic_checks) == spec["diagnostics"]["pngCount"] * 2 and all(item["match"] for item in diagnostic_checks)
        and result["verdict"] == spec["decisionRule"]["usableVerdict"] and result["baseFailure"] is None
        and result["attacksPassed"] == len(spec["attacks"]) and len(result["attacks"]) == len(spec["attacks"])
        and result["operationCounts"] == spec["operationBoundary"]
        and result["d3Invariants"]["verdict"] == spec["parents"]["d3Result"]["verdict"]
        and result["d3Invariants"]["futureHoldoutCandidates"] == spec["parents"]["d3Result"]["futureHoldoutCandidates"]
    )
    audit = {
        "schemaVersion": "bfs.adaptiveVectorBlurSemanticsDerivationAudit.v0.1", "status": "PASS" if passed else "FAIL", "verdict": result["verdict"], "vectorTaskTolerableProfiles": result["vectorTaskTolerableProfiles"], "analysisAmendmentChecks": amendment_checks,
        "attacksPassed": result["attacksPassed"], "attackCount": len(result["attacks"]), "evidenceCoreHash": result["evidenceCoreHash"],
        "receipt": {"uri": str(receipt_path.relative_to(root)), "sha256": sha256_file(receipt_path)}, "analysisReplay": analysis_replay,
        "frozenToolChecks": frozen_tools, "frozenToolsMatch": all(item["match"] for item in frozen_tools), "boundInputChecks": bound_inputs, "boundInputsMatch": all(item["match"] for item in bound_inputs),
        "artifactChecks": artifact_checks, "artifactsMatch": all(item["match"] for item in artifact_checks), "outputChecks": output_checks, "outputsMatch": all(item["match"] for item in output_checks),
        "sourcePostChecks": source_post_checks, "sourcePostMatch": all(item["match"] for item in source_post_checks), "diagnosticChecks": diagnostic_checks, "diagnosticsMatch": all(item["match"] for item in diagnostic_checks),
        "toolHashes": {"analyzer": sha256_file(analyzer), "audit": sha256_file(Path(__file__))}, "replayStdout": process.stdout.strip(), "failures": [] if passed else ["REPLAY_OR_GATE_MISMATCH"],
    }
    args.output.write_text(json.dumps(audit, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(f"BFS_B52_D4_AUDIT {audit['status']} replayExact={replay_exact} artifacts={sum(item['match'] for item in artifact_checks)}/{len(artifact_checks)} outputs={sum(item['match'] for item in output_checks)}/{len(output_checks)} diagnostics={sum(item['match'] for item in diagnostic_checks)}/{len(diagnostic_checks)}", flush=True)
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
