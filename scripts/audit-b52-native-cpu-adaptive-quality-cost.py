#!/usr/bin/env python3
"""Independent frozen-tool and byte-exact replay audit for B52-D1."""

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


def git_blob_hash(commit: str, uri: str, root: Path) -> str | None:
    process = subprocess.run(["git", "show", f"{commit}:{uri}"], cwd=root, capture_output=True, check=False)
    return hashlib.sha256(process.stdout).hexdigest() if process.returncode == 0 else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root, output_root = args.spec.resolve().parent.parent, args.output_root.resolve()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    receipt_path = output_root / "run.receipt.json"
    result_path = output_root / "results.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    result = json.loads(result_path.read_text(encoding="utf-8"))
    analyzer = root / receipt["tools"]["analyzer"]["uri"]

    with tempfile.TemporaryDirectory(prefix="bfs-b52-d1-audit-") as temporary:
        replay = Path(temporary) / "results.json"
        replay_argv = [
            sys.executable, str(analyzer), "--spec", str(args.spec),
            "--receipt", str(receipt_path), "--output", str(replay),
        ]
        correction = result.get("analysisCorrection")
        if correction is not None:
            replay_argv += ["--correction-tool-freeze-commit", correction["correctedToolFreezeCommit"]]
        process = subprocess.run(replay_argv, cwd=root, capture_output=True, text=True, check=False)
        if process.returncode:
            raise RuntimeError(f"B52-D1 analyzer replay failed: {process.stdout}\n{process.stderr}")
        replay_exact = result_path.read_bytes() == replay.read_bytes()
        replay_observation = {"uri": "results.json", "originalSha256": sha256_file(result_path), "replaySha256": sha256_file(replay), "byteExact": replay_exact}

    frozen_tools = []
    for name, binding in result["tools"].items():
        freeze_commit = binding.get("freezeCommit", receipt["toolFreezeCommit"])
        observed = git_blob_hash(freeze_commit, binding["uri"], root)
        frozen_tools.append({"name": name, "uri": binding["uri"], "freezeCommit": freeze_commit, "expectedSha256": binding["sha256"], "observedGitBlobSha256": observed, "match": observed == binding["sha256"]})

    bound_inputs = []
    for item in [*receipt["parentObservations"], *receipt["sourceObservations"], *receipt["sourcePostObservations"]]:
        path = root / item["uri"]
        observed = sha256_file(path) if path.is_file() else None
        bound_inputs.append({"kind": item["kind"], "uri": item["uri"], "expectedSha256": item["expectedSha256"], "observedSha256": observed, "match": observed == item["expectedSha256"]})

    artifacts = []
    for run in receipt["runs"]:
        report = run["report"]
        path = output_root / run["runId"] / "artifacts" / report["artifact"]["uri"]
        observed = sha256_file(path) if path.is_file() else None
        artifacts.append({
            "runId": run["runId"], "uri": str(path.relative_to(root)),
            "expectedSha256": report["artifact"]["sha256"], "observedSha256": observed,
            "expectedBytes": report["artifact"]["bytes"], "observedBytes": path.stat().st_size if path.is_file() else None,
            "match": observed == report["artifact"]["sha256"] and path.is_file() and path.stat().st_size == report["artifact"]["bytes"],
        })

    valid_verdicts = {
        spec["selectionRule"]["positiveVerdict"], spec["selectionRule"]["negativeVerdict"]
    }
    correction_checks = []
    if result.get("analysisCorrection") is not None:
        correction = result["analysisCorrection"]
        for binding_name in ("originalRunReceipt", "failureEvidence"):
            binding = correction[binding_name]
            path = root / binding["uri"]
            observed = sha256_file(path) if path.is_file() else None
            correction_checks.append({"name": binding_name, "uri": binding["uri"], "expectedSha256": binding["sha256"], "observedSha256": observed, "match": observed == binding["sha256"]})
        correction_checks.append({"name": "noRerender", "expected": {"rendersReused": 30, "rendersRepeated": 0}, "observed": {"rendersReused": correction["rendersReused"], "rendersRepeated": correction["rendersRepeated"]}, "match": correction["rendersReused"] == 30 and correction["rendersRepeated"] == 0})
    passed = (
        replay_exact and all(item["match"] for item in frozen_tools + bound_inputs + artifacts)
        and all(item["match"] for item in correction_checks)
        and result["verdict"] in valid_verdicts and result["attacksPassed"] == len(spec["attacks"])
        and result["baseFailure"] is None
    )
    audit = {
        "schemaVersion": "bfs.nativeCpuAdaptiveQualityCostAudit.v0.1", "status": "PASS" if passed else "FAIL",
        "verdict": result["verdict"], "selectedProfileId": result["selectedProfileId"],
        "attacksPassed": result["attacksPassed"], "attackCount": len(result["attacks"]),
        "evidenceCoreHash": result["evidenceCoreHash"], "analysisReplay": replay_observation,
        "frozenToolChecks": frozen_tools, "frozenToolsMatch": all(item["match"] for item in frozen_tools),
        "boundInputChecks": bound_inputs, "boundInputsMatch": all(item["match"] for item in bound_inputs),
        "correctionChecks": correction_checks, "correctionChecksMatch": all(item["match"] for item in correction_checks),
        "artifactChecks": artifacts, "artifactsMatch": all(item["match"] for item in artifacts),
        "toolHashes": {"analyzer": sha256_file(analyzer), "audit": sha256_file(Path(__file__))},
        "replayStdout": process.stdout.strip(), "failures": [] if passed else ["REPLAY_OR_GATE_MISMATCH"],
    }
    args.output.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_B52_D1_AUDIT {audit['status']} replayExact={replay_exact} artifacts={sum(item['match'] for item in artifacts)}/{len(artifacts)}", flush=True)
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
