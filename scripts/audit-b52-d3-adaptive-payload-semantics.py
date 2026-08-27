#!/usr/bin/env python3
"""Independent identity and byte-exact replay audit for B52-D3."""

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

    with tempfile.TemporaryDirectory(prefix="bfs-b52-d3-audit-") as temporary:
        temporary_root = Path(temporary)
        replay_result = temporary_root / "results.json"
        process = subprocess.run([
            sys.executable,
            str(analyzer),
            "--spec",
            str(args.spec),
            "--receipt",
            str(receipt_path),
            "--output",
            str(replay_result),
        ], cwd=root, capture_output=True, text=True, check=False)
        if process.returncode:
            raise RuntimeError(f"B52-D3 replay failed: {process.stdout}\n{process.stderr}")
        replay_exact = result_path.read_bytes() == replay_result.read_bytes()
        replay_observation = {
            "uri": str(result_path.relative_to(root)),
            "originalSha256": sha256_file(result_path),
            "replaySha256": sha256_file(replay_result),
            "byteExact": replay_exact,
        }
        diagnostic_checks = []
        for diagnostic in result["diagnostics"]:
            for kind in ("png", "sidecar"):
                binding = diagnostic[kind]
                actual_path = root / binding["uri"]
                replay_path = temporary_root / "diagnostics" / actual_path.name
                actual_sha = sha256_file(actual_path) if actual_path.is_file() else None
                replay_sha = sha256_file(replay_path) if replay_path.is_file() else None
                diagnostic_checks.append({
                    "profileId": diagnostic["profileId"],
                    "variantId": diagnostic["variantId"],
                    "mapKind": diagnostic["kind"],
                    "artifactKind": kind,
                    "uri": binding["uri"],
                    "expectedSha256": binding["sha256"],
                    "observedSha256": actual_sha,
                    "replaySha256": replay_sha,
                    "expectedBytes": binding["bytes"],
                    "observedBytes": actual_path.stat().st_size if actual_path.is_file() else None,
                    "match": actual_sha == binding["sha256"] and replay_sha == binding["sha256"] and actual_path.is_file() and actual_path.stat().st_size == binding["bytes"],
                })

    frozen_tools = []
    for name, binding in receipt["tools"].items():
        observed = git_blob_hash(root, binding["freezeCommit"], binding["uri"])
        frozen_tools.append({
            "name": name,
            "uri": binding["uri"],
            "freezeCommit": binding["freezeCommit"],
            "expectedSha256": binding["sha256"],
            "observedGitBlobSha256": observed,
            "match": observed == binding["sha256"],
        })

    bound_inputs = []
    for item in [receipt["specObservation"], *receipt["parentObservations"]]:
        path = root / item["uri"]
        observed = sha256_file(path) if path.is_file() else None
        bound_inputs.append({
            "kind": item["kind"],
            "uri": item["uri"],
            "expectedSha256": item["expectedSha256"],
            "observedSha256": observed,
            "match": observed == item["expectedSha256"],
        })
    transitive = result["transitiveD6Spec"]
    transitive_path = root / transitive["uri"]
    bound_inputs.append({
        "kind": "TRANSITIVE_D6_SPEC",
        "uri": transitive["uri"],
        "expectedSha256": transitive["sha256"],
        "observedSha256": sha256_file(transitive_path) if transitive_path.is_file() else None,
        "match": transitive_path.is_file() and sha256_file(transitive_path) == transitive["sha256"],
    })

    artifact_checks = []
    for item in receipt["artifactObservations"]:
        path = root / item["uri"]
        observed_sha = sha256_file(path) if path.is_file() else None
        observed_bytes = path.stat().st_size if path.is_file() else None
        artifact_checks.append({
            "runId": item["runId"],
            "uri": item["uri"],
            "expectedSha256": item["expectedSha256"],
            "observedSha256": observed_sha,
            "expectedBytes": item["expectedBytes"],
            "observedBytes": observed_bytes,
            "match": observed_sha == item["expectedSha256"] and observed_bytes == item["expectedBytes"],
        })

    passed = (
        replay_exact
        and all(item["match"] for item in frozen_tools)
        and all(item["match"] for item in bound_inputs)
        and len(artifact_checks) == spec["inputs"]["verifiedArtifacts"]
        and all(item["match"] for item in artifact_checks)
        and len(diagnostic_checks) == spec["diagnostics"]["pngCount"] * 2
        and all(item["match"] for item in diagnostic_checks)
        and result["verdict"] == spec["decisionRule"]["usableVerdict"]
        and result["baseFailure"] is None
        and result["attacksPassed"] == len(spec["attacks"])
        and result["operationCounts"] == spec["operationBoundary"]
        and result["d2Invariants"]["verdict"] == spec["parents"]["d2Result"]["verdict"]
        and result["d2Invariants"]["auditStatus"] == spec["parents"]["d2Audit"]["status"]
    )
    audit = {
        "schemaVersion": "bfs.adaptivePayloadSemanticsDerivationAudit.v0.1",
        "status": "PASS" if passed else "FAIL",
        "verdict": result["verdict"],
        "futureHoldoutCandidates": result["futureHoldoutCandidates"],
        "attacksPassed": result["attacksPassed"],
        "attackCount": len(result["attacks"]),
        "evidenceCoreHash": result["evidenceCoreHash"],
        "receipt": {"uri": str(receipt_path.relative_to(root)), "sha256": sha256_file(receipt_path)},
        "analysisReplay": replay_observation,
        "frozenToolChecks": frozen_tools,
        "frozenToolsMatch": all(item["match"] for item in frozen_tools),
        "boundInputChecks": bound_inputs,
        "boundInputsMatch": all(item["match"] for item in bound_inputs),
        "artifactChecks": artifact_checks,
        "artifactsMatch": all(item["match"] for item in artifact_checks),
        "diagnosticChecks": diagnostic_checks,
        "diagnosticsMatch": all(item["match"] for item in diagnostic_checks),
        "toolHashes": {"analyzer": sha256_file(analyzer), "audit": sha256_file(Path(__file__))},
        "replayStdout": process.stdout.strip(),
        "failures": [] if passed else ["REPLAY_OR_GATE_MISMATCH"],
    }
    args.output.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"BFS_B52_D3_AUDIT {audit['status']} replayExact={replay_exact} "
        f"artifacts={sum(item['match'] for item in artifact_checks)}/{len(artifact_checks)} "
        f"diagnostics={sum(item['match'] for item in diagnostic_checks)}/{len(diagnostic_checks)}",
        flush=True,
    )
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
