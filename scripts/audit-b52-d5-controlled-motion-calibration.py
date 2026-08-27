#!/usr/bin/env python3
"""Independent identity and replay audit for B52-D5."""

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


def check_binding(root: Path, binding: dict, kind: str, absolute: bool = False) -> dict:
    path = Path(binding["uri"]) if absolute else root / binding["uri"]
    expected_sha = binding.get("expectedSha256", binding.get("sha256"))
    expected_bytes = binding.get("expectedBytes", binding.get("bytes"))
    observed_sha = sha256_file(path) if path.is_file() else None
    observed_bytes = path.stat().st_size if path.is_file() else None
    return {
        "kind": kind, "uri": binding["uri"], "expectedSha256": expected_sha, "observedSha256": observed_sha,
        "expectedBytes": expected_bytes, "observedBytes": observed_bytes,
        "match": observed_sha == expected_sha and (expected_bytes is None or observed_bytes == expected_bytes),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.spec.resolve().parent.parent
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    output_root = args.output_root.resolve()
    receipt_path = output_root / "run.receipt.json"
    result_path = output_root / "results.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    result = json.loads(result_path.read_text(encoding="utf-8"))
    analyzer = root / receipt["tools"]["analyzer"]["uri"]

    with tempfile.TemporaryDirectory(prefix="bfs-b52-d5-audit-") as temporary:
        temporary_root = Path(temporary)
        replay_result = temporary_root / "results.json"
        process = subprocess.run([sys.executable, str(analyzer), "--spec", str(args.spec), "--receipt", str(receipt_path), "--output", str(replay_result)], cwd=root, capture_output=True, text=True, check=False)
        if process.returncode:
            raise RuntimeError(f"B52-D5 replay failed: {process.stdout}\n{process.stderr}")
        replay_exact = result_path.read_bytes() == replay_result.read_bytes()
        analysis_replay = {"uri": str(result_path.relative_to(root)), "originalSha256": sha256_file(result_path), "replaySha256": sha256_file(replay_result), "byteExact": replay_exact}
        diagnostic_checks = []
        for diagnostic in result["diagnostics"]:
            for artifact_kind in ("png", "sidecar"):
                binding = diagnostic[artifact_kind]
                actual_path = root / binding["uri"]
                replay_path = temporary_root / "diagnostics" / actual_path.name
                observed_sha = sha256_file(actual_path) if actual_path.is_file() else None
                replay_sha = sha256_file(replay_path) if replay_path.is_file() else None
                observed_bytes = actual_path.stat().st_size if actual_path.is_file() else None
                diagnostic_checks.append({
                    "fixtureId": diagnostic["fixtureId"], "mapKind": diagnostic["kind"], "artifactKind": artifact_kind, "uri": binding["uri"],
                    "expectedSha256": binding["sha256"], "observedSha256": observed_sha, "replaySha256": replay_sha,
                    "expectedBytes": binding["bytes"], "observedBytes": observed_bytes,
                    "match": observed_sha == binding["sha256"] and replay_sha == binding["sha256"] and observed_bytes == binding["bytes"],
                })

    frozen_tools = []
    for name, binding in receipt["tools"].items():
        observed = git_blob_hash(root, binding["freezeCommit"], binding["uri"])
        frozen_tools.append({"name": name, "uri": binding["uri"], "freezeCommit": binding["freezeCommit"], "expectedSha256": binding["sha256"], "observedGitBlobSha256": observed, "match": observed == binding["sha256"]})

    bound_inputs = [check_binding(root, receipt["specObservation"], "SPEC")]
    bound_inputs.extend(check_binding(root, item, item["kind"]) for item in receipt["parentObservations"])
    bound_inputs.append(check_binding(root, receipt["runtimeObservations"]["blender"], "BLENDER", absolute=True))
    bound_inputs.append(check_binding(root, receipt["runtimeObservations"]["ocio"], "OCIO"))

    source_checks = []
    for item in result["sourceOutputObservations"]:
        source_checks.append(check_binding(root, {"uri": item["uri"], "sha256": item["expectedSha256"], "bytes": item["expectedBytes"]}, f"{item['fixtureId']}_R{item['repeat']}"))
    compositor_checks = []
    for item in result["compositorOutputObservations"]:
        compositor_checks.append(check_binding(root, {"uri": item["uri"], "sha256": item["expectedSha256"], "bytes": item["expectedBytes"]}, f"{item['fixtureId']}_{item['shutter']}_R{item['repeat']}"))
    source_post_checks = [check_binding(root, item, item["kind"]) for item in receipt["sourcePostObservations"]]
    run_report_checks = []
    for run in [*receipt["sourceRuns"], *receipt["compositorRuns"]]:
        path = root / run["reportUri"]
        observed = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
        run_report_checks.append({"cellId": run["cellId"], "uri": run["reportUri"], "match": observed == run["report"]})

    expected_verdict = spec["decisionRule"]["supportedVerdict"] if result["baseFailure"] is None and result["attacksPassed"] == len(spec["attacks"]) else spec["decisionRule"]["invalidVerdict"]
    integrity_checks = {
        "analysisReplayByteExact": replay_exact,
        "frozenToolsExact": len(frozen_tools) == 6 and all(item["match"] for item in frozen_tools),
        "boundInputsExact": len(bound_inputs) == len(spec["parents"]) + 3 and all(item["match"] for item in bound_inputs),
        "sourceArtifactsExact": len(source_checks) == 6 and all(item["match"] for item in source_checks),
        "compositorArtifactsExact": len(compositor_checks) == 24 and all(item["match"] for item in compositor_checks),
        "sourcePostExact": len(source_post_checks) == 6 and all(item["match"] for item in source_post_checks),
        "runReportsExact": len(run_report_checks) == 30 and all(item["match"] for item in run_report_checks),
        "diagnosticsExact": len(diagnostic_checks) == spec["diagnostics"]["pngCount"] * 2 and all(item["match"] for item in diagnostic_checks),
        "attackContractExact": result["attacksPassed"] == len(spec["attacks"]) and len(result["attacks"]) == len(spec["attacks"]),
        "operationBoundaryExact": result["operationCounts"] == spec["operationBoundary"],
        "scientificVerdictConsistent": result["verdict"] == expected_verdict,
    }
    passed = all(integrity_checks.values())
    audit = {
        "schemaVersion": "bfs.controlledMotionVectorBlurCalibrationAudit.v0.1", "status": "PASS" if passed else "FAIL",
        "scientificVerdict": result["verdict"], "baseFailure": result["baseFailure"],
        "auditInterpretation": "PASS means the evidence is intact and replayable; it does not force the scientific verdict to be supported.",
        "integrityChecks": integrity_checks, "evidenceCoreHash": result["evidenceCoreHash"],
        "receipt": {"uri": str(receipt_path.relative_to(root)), "sha256": sha256_file(receipt_path)}, "analysisReplay": analysis_replay,
        "frozenToolChecks": frozen_tools, "boundInputChecks": bound_inputs, "sourceArtifactChecks": source_checks,
        "compositorArtifactChecks": compositor_checks, "sourcePostChecks": source_post_checks, "diagnosticChecks": diagnostic_checks,
        "runReportChecks": run_report_checks,
        "toolHashes": {"analyzer": sha256_file(analyzer), "audit": sha256_file(Path(__file__))},
        "replayStdout": process.stdout.strip(), "failures": [] if passed else [name for name, value in integrity_checks.items() if not value],
    }
    args.output.write_text(json.dumps(audit, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(f"BFS_B52_D5_AUDIT {audit['status']} replayExact={replay_exact} sources={sum(item['match'] for item in source_checks)}/{len(source_checks)} outputs={sum(item['match'] for item in compositor_checks)}/{len(compositor_checks)} diagnostics={sum(item['match'] for item in diagnostic_checks)}/{len(diagnostic_checks)} scientific={result['verdict']}", flush=True)
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
