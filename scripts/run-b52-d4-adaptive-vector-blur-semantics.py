#!/usr/bin/env python3
"""Run the preregistered B52-D4 Blender 5.2 compositor matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


PREREGISTRATION_COMMIT = "173a2ed294b79b32089bc518249303da3cc5bb17"
SPEC_SHA256 = "e8635a1507eb5a5e8bfd950dc02fc4630a7202fd9af14b5510a991359f2e439f"
TOOL_URIS = {
    "analysisLibrary": "scripts/analyze-b52-native-cpu-adaptive-quality-cost.py",
    "d3AnalysisLibrary": "scripts/analyze-b52-d3-adaptive-payload-semantics.py",
    "blenderWorker": "blender/render_b52_d4_vector_blur.py",
    "analyzer": "scripts/analyze-b52-d4-adaptive-vector-blur-semantics.py",
    "audit": "scripts/audit-b52-d4-adaptive-vector-blur-semantics.py",
    "runner": "scripts/run-b52-d4-adaptive-vector-blur-semantics.py",
    "analysisContractTest": "tests/test_b52_d4_analysis_contract.py",
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


def observation(root: Path, kind: str, uri: str, expected_sha: str, expected_bytes: int | None = None) -> dict:
    path = root / uri
    observed_sha = sha256_file(path) if path.is_file() else None
    observed_bytes = path.stat().st_size if path.is_file() else None
    match = observed_sha == expected_sha and (expected_bytes is None or observed_bytes == expected_bytes)
    return {"kind": kind, "uri": uri, "expectedSha256": expected_sha, "observedSha256": observed_sha, "expectedBytes": expected_bytes, "observedBytes": observed_bytes, "match": match}


def normalized_argv(argv: list[str], root: Path) -> list[str]:
    prefix = str(root.resolve())
    return [item.replace(prefix, "<REPO>") for item in argv]


def launch(command: list[str], root: Path, environment: dict[str, str], timeout_seconds: float) -> dict:
    started = time.monotonic()
    process = subprocess.Popen(command, cwd=root, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.terminate()
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
    return {"pid": process.pid, "exitCode": process.returncode, "timedOut": timed_out, "elapsedSeconds": round(time.monotonic() - started, 6), "stdout": stdout, "stderr": stderr}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--tool-freeze-commit", required=True)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--preflight-output", type=Path)
    args = parser.parse_args()
    root = args.spec.resolve().parent.parent
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    output_root = args.output_root.resolve()
    expected_output = (root / spec["outputRoot"]).resolve()
    if sha256_file(args.spec) != SPEC_SHA256:
        raise RuntimeError("B52-D4 spec hash differs from preregistration")
    if output_root != expected_output:
        raise RuntimeError(f"output root must equal preregistered path: {expected_output}")
    if output_root.exists():
        raise RuntimeError(f"formal output root already exists: {output_root}")
    if args.preflight_only != (args.preflight_output is not None):
        raise RuntimeError("--preflight-only and --preflight-output must be supplied together")
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

    spec_observation = observation(root, "D4_SPEC", "specs/adaptive-vector-blur-semantics-derivation.v0.1.json", SPEC_SHA256)
    parent_observations = [observation(root, name, binding["uri"], binding["sha256"]) for name, binding in spec["parents"].items()]
    if not spec_observation["match"] or not all(item["match"] for item in parent_observations):
        raise RuntimeError("B52-D4 parent identity preflight failed")

    d3_receipt = json.loads((root / spec["parents"]["d3Receipt"]["uri"]).read_text(encoding="utf-8"))
    parent_artifacts = []
    for item in d3_receipt["artifactObservations"]:
        parent_artifacts.append(observation(root, item["runId"], item["uri"], item["expectedSha256"], item["expectedBytes"]))
    if len(parent_artifacts) != spec["inputs"]["verifiedParentArtifacts"] or not all(item["match"] for item in parent_artifacts):
        raise RuntimeError("B52-D4 parent EXR identity preflight failed")

    blender_uri = spec["runtime"]["blenderExecutable"]
    blender_path = Path(blender_uri)
    blender_observation = {"uri": blender_uri, "expectedSha256": spec["runtime"]["blenderExecutableSha256"], "observedSha256": sha256_file(blender_path), "expectedBytes": spec["runtime"]["blenderExecutableBytes"], "observedBytes": blender_path.stat().st_size}
    blender_observation["match"] = blender_observation["observedSha256"] == blender_observation["expectedSha256"] and blender_observation["observedBytes"] == blender_observation["expectedBytes"]
    ocio_binding = spec["runtime"]["ocio"]
    ocio_observation = observation(root, "OCIO", ocio_binding["uri"], ocio_binding["sha256"])
    if not blender_observation["match"] or not ocio_observation["match"]:
        raise RuntimeError("B52-D4 Blender or OCIO identity preflight failed")

    artifact_by_run = {item["kind"]: item for item in parent_artifacts}
    source_pre = []
    source_identity_by_uri = {}
    for profile in [spec["inputs"]["baselineProfile"], *spec["inputs"]["candidateProfiles"]]:
        for variant in spec["inputs"]["variants"]:
            run_id = f"{variant}_{profile}_R1"
            item = artifact_by_run[run_id]
            source_pre.append({"runId": run_id, "uri": item["uri"], "expectedSha256": item["expectedSha256"], "observedSha256": item["observedSha256"], "expectedBytes": item["expectedBytes"], "observedBytes": item["observedBytes"], "match": item["match"]})
            source_identity_by_uri[item["uri"]] = item["observedSha256"]

    free_bytes = shutil.disk_usage(root).free
    reserve = int(spec["evidenceGates"]["minimumDiskReserveBytes"])
    projected = int(spec["evidenceGates"]["projectedWriteBytes"])
    disk_admission = {"availableBytes": free_bytes, "minimumReserveBytes": reserve, "projectedWriteBytes": projected, "projectedFreeAfterBytes": free_bytes - projected, "status": "ACCEPTED" if free_bytes - projected >= reserve else "BLOCKED"}
    if disk_admission["status"] != "ACCEPTED":
        raise RuntimeError(f"B52-D4 disk admission blocked: {disk_admission}")

    if args.preflight_only:
        preflight_path = args.preflight_output.resolve()
        if preflight_path.exists():
            raise RuntimeError(f"refusing to overwrite B52-D4 frozen-tool preflight: {preflight_path}")
        if root not in preflight_path.parents:
            raise RuntimeError("B52-D4 frozen-tool preflight must be stored inside the repository")
        preflight = {
            "schemaVersion": "bfs.adaptiveVectorBlurFrozenToolPreflight.v0.1",
            "experimentId": spec["experimentId"],
            "classification": "ZERO_FORMAL_OUTPUT_IDENTITY_PREFLIGHT",
            "preregistration": {
                "commit": PREREGISTRATION_COMMIT,
                "specUri": "specs/adaptive-vector-blur-semantics-derivation.v0.1.json",
                "specSha256": SPEC_SHA256,
            },
            "toolFreezeCommit": args.tool_freeze_commit,
            "tools": tools,
            "specObservation": spec_observation,
            "parentObservations": parent_observations,
            "parentArtifactObservations": parent_artifacts,
            "runtimeObservations": {"blender": blender_observation, "ocio": ocio_observation},
            "sourcePreObservations": source_pre,
            "diskAdmission": disk_admission,
            "formalOutputRoot": {"uri": spec["outputRoot"], "absent": not output_root.exists()},
            "operationCounts": {
                "blenderProcesses": 0,
                "blenderRenderCalls": 0,
                "cyclesRayRenders": 0,
                "compositorOutputs": 0,
                "formalMeasurements": 0,
            },
        }
        preflight_path.parent.mkdir(parents=True, exist_ok=True)
        preflight_path.write_text(json.dumps(preflight, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
        print(
            "BFS_B52_D4_PREFLIGHT_OK "
            f"tools={len(tools)} parents={len(parent_artifacts)} formalOutputAbsent={not output_root.exists()} "
            f"sha256={sha256_file(preflight_path)}",
            flush=True,
        )
        return

    output_root.mkdir(parents=True)
    spec_uri = str(args.spec.resolve().relative_to(root))
    worker_uri = TOOL_URIS["blenderWorker"]
    base_environment = {key: value for key, value in os.environ.items() if key in {"PATH"}}
    base_environment.update({"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "OCIO": str((root / ocio_binding["uri"]).resolve())})
    runs = []
    profiles = [spec["inputs"]["baselineProfile"], *spec["inputs"]["candidateProfiles"]]
    for profile in profiles:
        for variant in spec["inputs"]["variants"]:
            baseline_uri = f"{spec['inputs']['parentOutputRoot']}/{variant}_{spec['inputs']['baselineProfile']}_R1/artifacts/production.exr"
            speed_uri = f"{spec['inputs']['parentOutputRoot']}/{variant}_{profile}_R1/artifacts/production.exr"
            for repeat in (1, 2):
                cell_id = f"{variant}_{profile}_C{repeat}"
                cell_uri = f"{spec['outputRoot']}/cells/{cell_id}"
                output_uri = f"{cell_uri}/vector-blur.exr"
                report_uri = f"{cell_uri}/report.json"
                with tempfile.TemporaryDirectory(prefix=f"bfs-b52-d4-{cell_id.lower()}-") as temporary:
                    temporary_path = Path(temporary)
                    environment = dict(base_environment)
                    environment.update({"TMPDIR": str(temporary_path / "tmp"), "BLENDER_USER_CONFIG": str(temporary_path / "config"), "BLENDER_USER_SCRIPTS": str(temporary_path / "scripts")})
                    for key in ("TMPDIR", "BLENDER_USER_CONFIG", "BLENDER_USER_SCRIPTS"):
                        Path(environment[key]).mkdir(parents=True, exist_ok=True)
                    command = [
                        str(blender_path), *spec["runtime"]["launchFlags"], "--python", worker_uri, "--",
                        "--spec", spec_uri, "--baseline-exr", baseline_uri, "--speed-exr", speed_uri,
                        "--expected-baseline-sha", source_identity_by_uri[baseline_uri], "--expected-speed-sha", source_identity_by_uri[speed_uri],
                        "--output-exr", output_uri, "--report", report_uri, "--cell-id", cell_id, "--variant", variant, "--profile", profile, "--repeat", str(repeat),
                    ]
                    launched = launch(command, root, environment, 120.0)
                cell_path = root / cell_uri
                cell_path.mkdir(parents=True, exist_ok=True)
                (cell_path / "stdout.log").write_text(launched["stdout"], encoding="utf-8")
                (cell_path / "stderr.log").write_text(launched["stderr"], encoding="utf-8")
                report_path = root / report_uri
                report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else None
                record = {"cellId": cell_id, "profileId": profile, "variantId": variant, "repeat": repeat, "pid": launched["pid"], "exitCode": launched["exitCode"], "timedOut": launched["timedOut"], "elapsedSeconds": launched["elapsedSeconds"], "argv": normalized_argv(command, root), "stdoutUri": f"{cell_uri}/stdout.log", "stderrUri": f"{cell_uri}/stderr.log", "reportUri": report_uri, "report": report}
                runs.append(record)
                if launched["exitCode"] != 0 or launched["timedOut"] or report is None:
                    failure = {"schemaVersion": "bfs.adaptiveVectorBlurRunFailure.v0.1", "experimentId": spec["experimentId"], "failedCell": record, "completedRuns": runs}
                    (output_root / "run.failure.json").write_text(json.dumps(failure, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                    raise RuntimeError(f"B52-D4 cell failed: {cell_id}")

    source_post = []
    for item in source_pre:
        source_post.append(observation(root, item["runId"], item["uri"], item["expectedSha256"], item["expectedBytes"]))
    receipt = {
        "schemaVersion": "bfs.adaptiveVectorBlurSemanticsDerivationReceipt.v0.1", "experimentId": spec["experimentId"],
        "preregistration": {"commit": PREREGISTRATION_COMMIT, "specUri": "specs/adaptive-vector-blur-semantics-derivation.v0.1.json", "specSha256": SPEC_SHA256},
        "toolFreezeCommit": args.tool_freeze_commit, "tools": tools, "specObservation": spec_observation, "parentObservations": parent_observations, "parentArtifactObservations": parent_artifacts,
        "runtimeObservations": {"blender": blender_observation, "ocio": ocio_observation}, "diskAdmission": disk_admission,
        "sourcePreObservations": source_pre, "sourcePostObservations": source_post, "sourceIdentityByUri": source_identity_by_uri, "runs": runs, "operationPlan": spec["operationBoundary"],
    }
    receipt_path = output_root / "run.receipt.json"
    result_path = output_root / "results.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    analyze = [sys.executable, TOOL_URIS["analyzer"], "--spec", spec_uri, "--receipt", str(receipt_path.relative_to(root)), "--output", str(result_path.relative_to(root))]
    process = subprocess.run(analyze, cwd=root, capture_output=True, text=True, check=False)
    (output_root / "analysis.stdout.log").write_text(process.stdout, encoding="utf-8")
    (output_root / "analysis.stderr.log").write_text(process.stderr, encoding="utf-8")
    if process.returncode:
        failure = {"schemaVersion": "bfs.adaptiveVectorBlurAnalysisFailure.v0.1", "exitCode": process.returncode, "argv": normalized_argv(analyze, root), "stdout": process.stdout, "stderr": process.stderr}
        (output_root / "analysis.failure.json").write_text(json.dumps(failure, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        raise SystemExit(process.returncode)
    print(process.stdout.strip())
    print(f"BFS_B52_D4_RUN_OK receipt={sha256_file(receipt_path)} result={sha256_file(result_path)}", flush=True)


if __name__ == "__main__":
    main()
