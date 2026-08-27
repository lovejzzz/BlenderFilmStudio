#!/usr/bin/env python3
"""Admit and execute the zero-render B52-D3 derivation with frozen tools."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path


PREREGISTRATION_COMMIT = "51b5033cc76a95638c68b45a8015347863c73a73"
SPEC_SHA256 = "88f9284e014a5c4020aed374eef306cf22ed1c1badf5e680d93a919038526b7d"
TOOL_URIS = {
    "analysisLibrary": "scripts/analyze-b52-native-cpu-adaptive-quality-cost.py",
    "analyzer": "scripts/analyze-b52-d3-adaptive-payload-semantics.py",
    "audit": "scripts/audit-b52-d3-adaptive-payload-semantics.py",
    "runner": "scripts/run-b52-d3-adaptive-payload-semantics.py",
    "analysisContractTest": "tests/test_b52_d3_analysis_contract.py",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_blob_hash(root: Path, commit: str, uri: str) -> str | None:
    process = subprocess.run(["git", "show", f"{commit}:{uri}"], cwd=root, capture_output=True, check=False)
    return hashlib.sha256(process.stdout).hexdigest() if process.returncode == 0 else None


def observation(root: Path, kind: str, uri: str, expected_sha: str) -> dict:
    path = root / uri
    observed = sha256_file(path) if path.is_file() else None
    return {
        "kind": kind,
        "uri": uri,
        "expectedSha256": expected_sha,
        "observedSha256": observed,
        "observedBytes": path.stat().st_size if path.is_file() else None,
        "match": observed == expected_sha,
    }


def normalized_argv(argv: list[str], root: Path) -> list[str]:
    prefix = str(root.resolve())
    return [item.replace(prefix, "<REPO>") for item in argv]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--tool-freeze-commit", required=True)
    args = parser.parse_args()
    root = args.spec.resolve().parent.parent
    output_root = args.output_root.resolve()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    if sha256_file(args.spec) != SPEC_SHA256:
        raise RuntimeError("B52-D3 spec hash differs from amended preregistration")
    expected_output = (root / spec["outputRoot"]).resolve()
    if output_root != expected_output:
        raise RuntimeError(f"output root must equal preregistered path: {expected_output}")
    if output_root.exists():
        raise RuntimeError(f"formal output root already exists: {output_root}")
    ancestor = subprocess.run(["git", "merge-base", "--is-ancestor", args.tool_freeze_commit, "HEAD"], cwd=root, check=False)
    if ancestor.returncode:
        raise RuntimeError("tool freeze commit is not an ancestor of HEAD")

    tools = {}
    for name, uri in TOOL_URIS.items():
        path = root / uri
        current_sha = sha256_file(path) if path.is_file() else None
        frozen_sha = git_blob_hash(root, args.tool_freeze_commit, uri)
        if current_sha is None or current_sha != frozen_sha:
            raise RuntimeError(f"tool is absent or differs from freeze commit: {uri}")
        tools[name] = {"uri": uri, "sha256": current_sha, "freezeCommit": args.tool_freeze_commit}

    spec_observation = observation(root, "D3_SPEC", "specs/adaptive-payload-semantics-derivation.v0.1.json", SPEC_SHA256)
    parent_observations = []
    for name, binding in spec["parents"].items():
        parent_observations.append(observation(root, name, binding["uri"], binding["sha256"]))
    if not spec_observation["match"] or not all(item["match"] for item in parent_observations):
        raise RuntimeError("B52-D3 parent identity preflight failed")

    d2_receipt_path = root / spec["parents"]["d2Receipt"]["uri"]
    d2_receipt = json.loads(d2_receipt_path.read_text(encoding="utf-8"))
    artifact_observations = []
    for run in d2_receipt["runs"]:
        report = run["report"]
        path = d2_receipt_path.parent / run["runId"] / "artifacts" / report["artifact"]["uri"]
        observed_sha = sha256_file(path) if path.is_file() else None
        observed_bytes = path.stat().st_size if path.is_file() else None
        artifact_observations.append({
            "runId": run["runId"],
            "uri": str(path.relative_to(root)),
            "expectedSha256": report["artifact"]["sha256"],
            "observedSha256": observed_sha,
            "expectedBytes": report["artifact"]["bytes"],
            "observedBytes": observed_bytes,
            "match": observed_sha == report["artifact"]["sha256"] and observed_bytes == report["artifact"]["bytes"],
        })
    if len(artifact_observations) != spec["inputs"]["verifiedArtifacts"] or not all(item["match"] for item in artifact_observations):
        raise RuntimeError("B52-D3 artifact identity preflight failed")

    free_bytes = shutil.disk_usage(root).free
    reserve = int(spec["evidenceGates"]["minimumDiskReserveBytes"])
    projected = int(spec["evidenceGates"]["projectedWriteBytes"])
    disk_admission = {
        "availableBytes": free_bytes,
        "minimumReserveBytes": reserve,
        "projectedWriteBytes": projected,
        "projectedFreeAfterBytes": free_bytes - projected,
        "status": "ACCEPTED" if free_bytes - projected >= reserve else "BLOCKED",
    }
    if disk_admission["status"] != "ACCEPTED":
        raise RuntimeError(f"B52-D3 disk admission blocked: {disk_admission}")

    output_root.mkdir(parents=True)
    receipt_path = output_root / "run.receipt.json"
    result_path = output_root / "results.json"
    receipt = {
        "schemaVersion": "bfs.adaptivePayloadSemanticsDerivationReceipt.v0.1",
        "experimentId": spec["experimentId"],
        "preregistration": {"commit": PREREGISTRATION_COMMIT, "specUri": "specs/adaptive-payload-semantics-derivation.v0.1.json", "specSha256": SPEC_SHA256},
        "toolFreezeCommit": args.tool_freeze_commit,
        "tools": tools,
        "specObservation": spec_observation,
        "parentObservations": parent_observations,
        "artifactObservations": artifact_observations,
        "diskAdmission": disk_admission,
        "operationPlan": spec["operationBoundary"],
    }
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    command = [sys.executable, str(root / TOOL_URIS["analyzer"]), "--spec", str(args.spec.resolve()), "--receipt", str(receipt_path), "--output", str(result_path)]
    process = subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)
    (output_root / "analysis.stdout.log").write_text(process.stdout, encoding="utf-8")
    (output_root / "analysis.stderr.log").write_text(process.stderr, encoding="utf-8")
    if process.returncode:
        failure = {"schemaVersion": "bfs.adaptivePayloadSemanticsDerivationFailure.v0.1", "exitCode": process.returncode, "argv": normalized_argv(command, root), "stdout": process.stdout, "stderr": process.stderr}
        (output_root / "analysis.failure.json").write_text(json.dumps(failure, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        raise SystemExit(process.returncode)
    print(process.stdout.strip())
    print(f"BFS_B52_D3_RUN_OK receipt={sha256_file(receipt_path)} result={sha256_file(result_path)}", flush=True)


if __name__ == "__main__":
    main()
