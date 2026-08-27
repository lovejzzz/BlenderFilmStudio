#!/usr/bin/env python3
"""Run the preregistered B52-D5 controlled-motion calibration matrix."""

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


PREREGISTRATION_COMMIT = "0e127a66d19f16dec7bf88bafb5158d608e574cf"
SPEC_SHA256 = "5c2e6564650d6ab6d98f6bb7d91da4304c1cfeece4601871ed74fe5fd5521e01"
TOOL_URIS = {
    "sourceWorker": "blender/render_b52_d5_controlled_motion_source.py",
    "compositorWorker": "blender/render_b52_d5_vector_blur_cell.py",
    "analyzer": "scripts/analyze-b52-d5-controlled-motion-calibration.py",
    "audit": "scripts/audit-b52-d5-controlled-motion-calibration.py",
    "runner": "scripts/run-b52-d5-controlled-motion-calibration.py",
    "analysisContractTest": "tests/test_b52_d5_analysis_contract.py",
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
    return {
        "kind": kind, "uri": uri, "expectedSha256": expected_sha, "observedSha256": observed_sha,
        "expectedBytes": expected_bytes, "observedBytes": observed_bytes,
        "match": observed_sha == expected_sha and (expected_bytes is None or observed_bytes == expected_bytes),
    }


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


def isolated_environment(root: Path, ocio_uri: str, temporary: Path) -> dict[str, str]:
    environment = {key: value for key, value in os.environ.items() if key == "PATH"}
    environment.update({
        "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "OCIO": str((root / ocio_uri).resolve()),
        "TMPDIR": str(temporary / "tmp"), "BLENDER_USER_CONFIG": str(temporary / "config"), "BLENDER_USER_SCRIPTS": str(temporary / "scripts"),
    })
    for key in ("TMPDIR", "BLENDER_USER_CONFIG", "BLENDER_USER_SCRIPTS"):
        Path(environment[key]).mkdir(parents=True, exist_ok=True)
    return environment


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
        raise RuntimeError("B52-D5 spec hash differs from preregistration")
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
        current_sha = sha256_file(root / uri) if (root / uri).is_file() else None
        frozen_sha = git_blob_hash(root, args.tool_freeze_commit, uri)
        if current_sha is None or current_sha != frozen_sha:
            raise RuntimeError(f"tool absent or differs from freeze commit: {uri}")
        tools[name] = {"uri": uri, "sha256": current_sha, "freezeCommit": args.tool_freeze_commit}

    spec_observation = observation(root, "D5_SPEC", "specs/controlled-motion-vector-blur-calibration.v0.1.json", SPEC_SHA256)
    parent_observations = [observation(root, name, binding["uri"], binding["sha256"]) for name, binding in spec["parents"].items()]
    if not spec_observation["match"] or not all(item["match"] for item in parent_observations):
        raise RuntimeError("B52-D5 parent identity preflight failed")
    blender_path = Path(spec["runtime"]["blenderExecutable"])
    blender_observation = {
        "uri": str(blender_path), "expectedSha256": spec["runtime"]["blenderExecutableSha256"], "observedSha256": sha256_file(blender_path),
        "expectedBytes": spec["runtime"]["blenderExecutableBytes"], "observedBytes": blender_path.stat().st_size,
    }
    blender_observation["match"] = blender_observation["observedSha256"] == blender_observation["expectedSha256"] and blender_observation["observedBytes"] == blender_observation["expectedBytes"]
    ocio_binding = spec["runtime"]["ocio"]
    ocio_observation = observation(root, "OCIO", ocio_binding["uri"], ocio_binding["sha256"])
    if not blender_observation["match"] or not ocio_observation["match"]:
        raise RuntimeError("B52-D5 Blender or OCIO identity preflight failed")
    free_bytes = shutil.disk_usage(root).free
    reserve = int(spec["evidenceGates"]["minimumDiskReserveBytes"])
    projected = int(spec["evidenceGates"]["projectedWriteBytes"])
    disk_admission = {"availableBytes": free_bytes, "minimumReserveBytes": reserve, "projectedWriteBytes": projected, "projectedFreeAfterBytes": free_bytes - projected, "status": "ACCEPTED" if free_bytes - projected >= reserve else "BLOCKED"}
    if disk_admission["status"] != "ACCEPTED":
        raise RuntimeError(f"B52-D5 disk admission blocked: {disk_admission}")

    preregistration = {"commit": PREREGISTRATION_COMMIT, "specUri": "specs/controlled-motion-vector-blur-calibration.v0.1.json", "specSha256": SPEC_SHA256}
    if args.preflight_only:
        preflight_path = args.preflight_output.resolve()
        if preflight_path.exists() or root not in preflight_path.parents:
            raise RuntimeError("invalid or existing B52-D5 preflight path")
        preflight = {
            "schemaVersion": "bfs.controlledMotionVectorBlurFrozenToolPreflight.v0.1", "experimentId": spec["experimentId"],
            "classification": "ZERO_FORMAL_OUTPUT_IDENTITY_PREFLIGHT", "preregistration": preregistration,
            "toolFreezeCommit": args.tool_freeze_commit, "tools": tools, "specObservation": spec_observation,
            "parentObservations": parent_observations, "runtimeObservations": {"blender": blender_observation, "ocio": ocio_observation},
            "diskAdmission": disk_admission, "formalOutputRoot": {"uri": spec["outputRoot"], "absent": not output_root.exists()},
            "matrix": {"sourceProcesses": 6, "compositorProcesses": 24, "totalProcesses": 30},
            "operationCounts": {"blenderProcesses": 0, "blenderRenderCalls": 0, "cyclesRayRenders": 0, "formalMeasurements": 0},
        }
        preflight_path.parent.mkdir(parents=True, exist_ok=True)
        preflight_path.write_text(json.dumps(preflight, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
        print(f"BFS_B52_D5_PREFLIGHT_OK tools={len(tools)} parents={len(parent_observations)} formalOutputAbsent={not output_root.exists()} sha256={sha256_file(preflight_path)}", flush=True)
        return

    output_root.mkdir(parents=True)
    spec_uri = str(args.spec.resolve().relative_to(root))
    source_runs = []
    source_identity_by_key: dict[tuple[str, int], dict] = {}
    for fixture in [item["id"] for item in spec["fixtures"]]:
        for repeat in (1, 2):
            cell_id = f"{fixture}_SOURCE_R{repeat}"
            cell_uri = f"{spec['outputRoot']}/sources/{cell_id}"
            output_uri = f"{cell_uri}/source.exr"
            report_uri = f"{cell_uri}/report.json"
            with tempfile.TemporaryDirectory(prefix=f"bfs-b52-d5-{cell_id.lower()}-") as temporary:
                environment = isolated_environment(root, ocio_binding["uri"], Path(temporary))
                command = [str(blender_path), *spec["runtime"]["launchFlags"], "--python", TOOL_URIS["sourceWorker"], "--", "--spec", spec_uri, "--fixture", fixture, "--repeat", str(repeat), "--output-exr", output_uri, "--report", report_uri]
                launched = launch(command, root, environment, 120.0)
            cell_path = root / cell_uri
            cell_path.mkdir(parents=True, exist_ok=True)
            (cell_path / "stdout.log").write_text(launched["stdout"], encoding="utf-8")
            (cell_path / "stderr.log").write_text(launched["stderr"], encoding="utf-8")
            report_path = root / report_uri
            report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else None
            record = {"cellId": cell_id, "fixtureId": fixture, "repeat": repeat, "pid": launched["pid"], "exitCode": launched["exitCode"], "timedOut": launched["timedOut"], "elapsedSeconds": launched["elapsedSeconds"], "argv": normalized_argv(command, root), "stdoutUri": f"{cell_uri}/stdout.log", "stderrUri": f"{cell_uri}/stderr.log", "reportUri": report_uri, "report": report}
            source_runs.append(record)
            if launched["exitCode"] != 0 or launched["timedOut"] or report is None:
                (output_root / "run.failure.json").write_text(json.dumps({"schemaVersion": "bfs.controlledMotionVectorBlurRunFailure.v0.1", "stage": "SOURCE", "failedCell": record, "sourceRuns": source_runs}, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
                raise RuntimeError(f"B52-D5 source failed: {cell_id}")
            source_identity_by_key[(fixture, repeat)] = {"uri": report["output"]["uri"], "sha256": report["output"]["sha256"], "bytes": report["output"]["bytes"]}

    source_pre_observations = [observation(root, f"{fixture}_R{repeat}", binding["uri"], binding["sha256"], binding["bytes"]) for (fixture, repeat), binding in source_identity_by_key.items()]
    if not all(item["match"] for item in source_pre_observations):
        raise RuntimeError("B52-D5 source pre-observation failed")

    compositor_runs = []
    for fixture in [item["id"] for item in spec["fixtures"]]:
        for shutter in spec["compositor"]["shutters"]:
            shutter_id = str(shutter).replace(".", "p")
            for repeat in (1, 2):
                cell_id = f"{fixture}_SHUTTER_{shutter_id}_R{repeat}"
                cell_uri = f"{spec['outputRoot']}/compositor/{cell_id}"
                output_uri = f"{cell_uri}/vector-blur.exr"
                report_uri = f"{cell_uri}/report.json"
                source = source_identity_by_key[(fixture, repeat)]
                with tempfile.TemporaryDirectory(prefix=f"bfs-b52-d5-{cell_id.lower()}-") as temporary:
                    environment = isolated_environment(root, ocio_binding["uri"], Path(temporary))
                    command = [str(blender_path), *spec["runtime"]["launchFlags"], "--python", TOOL_URIS["compositorWorker"], "--", "--spec", spec_uri, "--source-exr", source["uri"], "--expected-source-sha", source["sha256"], "--fixture", fixture, "--shutter", str(shutter), "--repeat", str(repeat), "--output-exr", output_uri, "--report", report_uri]
                    launched = launch(command, root, environment, 120.0)
                cell_path = root / cell_uri
                cell_path.mkdir(parents=True, exist_ok=True)
                (cell_path / "stdout.log").write_text(launched["stdout"], encoding="utf-8")
                (cell_path / "stderr.log").write_text(launched["stderr"], encoding="utf-8")
                report_path = root / report_uri
                report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else None
                record = {"cellId": cell_id, "fixtureId": fixture, "shutter": float(shutter), "repeat": repeat, "pid": launched["pid"], "exitCode": launched["exitCode"], "timedOut": launched["timedOut"], "elapsedSeconds": launched["elapsedSeconds"], "argv": normalized_argv(command, root), "stdoutUri": f"{cell_uri}/stdout.log", "stderrUri": f"{cell_uri}/stderr.log", "reportUri": report_uri, "report": report}
                compositor_runs.append(record)
                if launched["exitCode"] != 0 or launched["timedOut"] or report is None:
                    (output_root / "run.failure.json").write_text(json.dumps({"schemaVersion": "bfs.controlledMotionVectorBlurRunFailure.v0.1", "stage": "COMPOSITOR", "failedCell": record, "sourceRuns": source_runs, "compositorRuns": compositor_runs}, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
                    raise RuntimeError(f"B52-D5 compositor failed: {cell_id}")

    source_post_observations = [observation(root, f"{fixture}_R{repeat}", binding["uri"], binding["sha256"], binding["bytes"]) for (fixture, repeat), binding in source_identity_by_key.items()]
    receipt = {
        "schemaVersion": "bfs.controlledMotionVectorBlurCalibrationReceipt.v0.1", "experimentId": spec["experimentId"],
        "preregistration": preregistration, "toolFreezeCommit": args.tool_freeze_commit, "tools": tools,
        "specObservation": spec_observation, "parentObservations": parent_observations,
        "runtimeObservations": {"blender": blender_observation, "ocio": ocio_observation}, "diskAdmission": disk_admission,
        "sourceRuns": source_runs, "sourcePreObservations": source_pre_observations, "sourcePostObservations": source_post_observations,
        "compositorRuns": compositor_runs, "operationPlan": spec["operationBoundary"],
    }
    receipt_path = output_root / "run.receipt.json"
    result_path = output_root / "results.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    analyze = [sys.executable, TOOL_URIS["analyzer"], "--spec", spec_uri, "--receipt", str(receipt_path.relative_to(root)), "--output", str(result_path.relative_to(root))]
    process = subprocess.run(analyze, cwd=root, capture_output=True, text=True, check=False)
    (output_root / "analysis.stdout.log").write_text(process.stdout, encoding="utf-8")
    (output_root / "analysis.stderr.log").write_text(process.stderr, encoding="utf-8")
    if process.returncode:
        (output_root / "analysis.failure.json").write_text(json.dumps({"schemaVersion": "bfs.controlledMotionVectorBlurAnalysisFailure.v0.1", "exitCode": process.returncode, "argv": normalized_argv(analyze, root), "stdout": process.stdout, "stderr": process.stderr}, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
        raise SystemExit(process.returncode)
    print(process.stdout.strip())
    print(f"BFS_B52_D5_RUN_OK receipt={sha256_file(receipt_path)} result={sha256_file(result_path)}", flush=True)


if __name__ == "__main__":
    main()
