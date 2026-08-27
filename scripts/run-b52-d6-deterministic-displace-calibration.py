#!/usr/bin/env python3
"""Run the preregistered B52-D6 deterministic Displace calibration."""

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


PREREGISTRATION_COMMIT = "65ea41cdb0235630f781776fed8324a9f94ec4ad"
SPEC_SHA256 = "28d3c0b292b89d5d056d5521aececbfb6d88b70971d2b500fbff69d2498703be"
TOOL_URIS = {
    "reference": "scripts/b52_d6_reference.py",
    "worker": "blender/render_b52_d6_displace_cell.py",
    "analyzer": "scripts/analyze-b52-d6-deterministic-displace-calibration.py",
    "audit": "scripts/audit-b52-d6-deterministic-displace-calibration.py",
    "runner": "scripts/run-b52-d6-deterministic-displace-calibration.py",
    "contractTests": "tests/test_b52_d6_deterministic_displace_contract.py",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def git_blob_hash(root: Path, commit: str, uri: str) -> str | None:
    process = subprocess.run(["git", "show", f"{commit}:{uri}"], cwd=root, capture_output=True, check=False)
    return hashlib.sha256(process.stdout).hexdigest() if process.returncode == 0 else None


def observe(root: Path, uri: str, expected_sha: str, expected_bytes: int | None = None) -> dict:
    path = root / uri
    observed_sha = sha256_file(path) if path.is_file() else None
    observed_bytes = path.stat().st_size if path.is_file() else None
    return {
        "uri": uri,
        "expectedSha256": expected_sha,
        "observedSha256": observed_sha,
        "expectedBytes": expected_bytes,
        "observedBytes": observed_bytes,
        "match": observed_sha == expected_sha and (expected_bytes is None or observed_bytes == expected_bytes),
    }


def isolated_environment(root: Path, ocio_uri: str, temporary: Path) -> dict[str, str]:
    environment = {key: value for key, value in os.environ.items() if key == "PATH"}
    environment.update({
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "OCIO": str((root / ocio_uri).resolve()),
        "TMPDIR": str(temporary / "tmp"),
        "BLENDER_USER_CONFIG": str(temporary / "config"),
        "BLENDER_USER_SCRIPTS": str(temporary / "scripts"),
    })
    for key in ("TMPDIR", "BLENDER_USER_CONFIG", "BLENDER_USER_SCRIPTS"):
        Path(environment[key]).mkdir(parents=True, exist_ok=True)
    return environment


def launch(command: list[str], root: Path, environment: dict[str, str], timeout: float) -> dict:
    started = time.monotonic()
    process = subprocess.Popen(command, cwd=root, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.terminate()
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
    return {"pid": process.pid, "exitCode": process.returncode, "timedOut": timed_out, "elapsedSeconds": round(time.monotonic() - started, 6), "stdout": stdout, "stderr": stderr}


def normalized_argv(command: list[str], root: Path) -> list[str]:
    prefix = str(root.resolve())
    return [item.replace(prefix, "<REPO>") for item in command]


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
    expected_output_root = (root / spec["formalOutputRoot"]).resolve()
    if sha256_file(args.spec) != SPEC_SHA256:
        raise RuntimeError("B52-D6 spec differs from preregistration")
    if output_root != expected_output_root:
        raise RuntimeError("formal output root differs from preregistration")
    if output_root.exists():
        raise RuntimeError("formal output root already exists")
    if args.preflight_only != (args.preflight_output is not None):
        raise RuntimeError("preflight arguments must be supplied together")
    if subprocess.run(["git", "merge-base", "--is-ancestor", args.tool_freeze_commit, "HEAD"], cwd=root, check=False).returncode:
        raise RuntimeError("tool freeze commit is not an ancestor of HEAD")

    tools = {}
    for name, uri in TOOL_URIS.items():
        current = sha256_file(root / uri) if (root / uri).is_file() else None
        frozen = git_blob_hash(root, args.tool_freeze_commit, uri)
        if current is None or current != frozen:
            raise RuntimeError(f"tool absent or differs from freeze commit: {uri}")
        tools[name] = {"uri": uri, "sha256": current, "freezeCommit": args.tool_freeze_commit}
    parent_observations = [observe(root, binding["uri"], binding["sha256"]) for binding in spec["parents"].values()]
    blender = Path(spec["runtime"]["blenderExecutable"])
    blender_observation = {
        "uri": str(blender),
        "expectedSha256": spec["runtime"]["blenderExecutableSha256"],
        "observedSha256": sha256_file(blender),
        "expectedBytes": spec["runtime"]["blenderExecutableBytes"],
        "observedBytes": blender.stat().st_size,
    }
    blender_observation["match"] = blender_observation["expectedSha256"] == blender_observation["observedSha256"] and blender_observation["expectedBytes"] == blender_observation["observedBytes"]
    ocio = observe(root, spec["runtime"]["ocio"]["uri"], spec["runtime"]["ocio"]["sha256"])
    checks = {
        "parentIdentity": all(item["match"] for item in parent_observations),
        "runtimeBinaryIdentity": blender_observation["match"],
        "ocioIdentity": ocio["match"],
    }
    if not all(checks.values()):
        raise RuntimeError(f"B52-D6 input identity preflight failed: {checks}")
    available = shutil.disk_usage(root).free
    projected = spec["projectedWriteBytes"]
    reserve = spec["diskReserveBytes"]
    disk = {"availableBytes": available, "projectedWriteBytes": projected, "projectedFreeAfterBytes": available - projected, "reserveBytes": reserve, "status": "ACCEPTED" if available - projected >= reserve else "BLOCKED"}
    if disk["status"] != "ACCEPTED":
        raise RuntimeError(f"B52-D6 disk admission blocked: {disk}")
    preregistration = {"commit": PREREGISTRATION_COMMIT, "specUri": "specs/deterministic-displace-calibration.v0.1.json", "specSha256": SPEC_SHA256}

    if args.preflight_only:
        preflight_output = args.preflight_output.resolve()
        if preflight_output.exists() or root not in preflight_output.parents:
            raise RuntimeError("invalid or existing preflight output")
        with tempfile.TemporaryDirectory(prefix="bfs-b52-d6-preflight-") as temporary_string:
            temporary = Path(temporary_string)
            environment = isolated_environment(root, spec["runtime"]["ocio"]["uri"], temporary)
            report_path = temporary / "probe-report.json"
            command = [str(blender), *spec["runtime"]["launchFlags"], "--python", TOOL_URIS["worker"], "--", "--spec", str(args.spec.resolve().relative_to(root)), "--fixture", "ZERO_NEAREST_CLIP", "--repeat", "1", "--probe-only", "--report", str(report_path)]
            launched = launch(command, root, environment, 30.0)
            report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else None
        if launched["exitCode"] != 0 or launched["timedOut"] or not report or report["operationCounts"]["renderCalls"] != 0:
            raise RuntimeError(f"B52-D6 zero-render worker preflight failed: {launched}")
        body = {
            "schemaVersion": "bfs.deterministicDisplaceFrozenToolPreflight.v0.1",
            "experimentId": spec["experimentId"],
            "classification": "ZERO_FORMAL_OUTPUT_IDENTITY_AND_RNA_PREFLIGHT",
            "preregistration": preregistration,
            "toolFreezeCommit": args.tool_freeze_commit,
            "tools": tools,
            "parentObservations": parent_observations,
            "runtimeObservations": {"blender": blender_observation, "ocio": ocio},
            "checks": checks,
            "diskAdmission": disk,
            "formalOutputRoot": {"uri": spec["formalOutputRoot"], "absent": not output_root.exists()},
            "probe": {"pid": launched["pid"], "exitCode": launched["exitCode"], "timedOut": launched["timedOut"], "report": report},
            "formalOperationCounts": {"blenderProcesses": 0, "renderCalls": 0, "formalMeasurements": 0},
        }
        preflight = {**body, "preflightHash": canonical_hash(body)}
        preflight_output.parent.mkdir(parents=True, exist_ok=True)
        preflight_output.write_text(json.dumps(preflight, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
        print(f"BFS_B52_D6_PREFLIGHT_OK tools={len(tools)} parents={len(parent_observations)} outputAbsent={not output_root.exists()} sha256={sha256_file(preflight_output)}", flush=True)
        return

    output_root.mkdir(parents=True)
    runs = []
    spec_uri = str(args.spec.resolve().relative_to(root))
    for fixture in spec["fixtures"]:
        for repeat in (1, 2):
            cell_id = f"{fixture['id']}_R{repeat}"
            cell_uri = f"{spec['formalOutputRoot']}/cells/{cell_id}"
            output_uri = f"{cell_uri}/displace.exr"
            report_uri = f"{cell_uri}/report.json"
            with tempfile.TemporaryDirectory(prefix=f"bfs-b52-d6-{cell_id.lower()}-") as temporary_string:
                environment = isolated_environment(root, spec["runtime"]["ocio"]["uri"], Path(temporary_string))
                command = [str(blender), *spec["runtime"]["launchFlags"], "--python", TOOL_URIS["worker"], "--", "--spec", spec_uri, "--fixture", fixture["id"], "--repeat", str(repeat), "--output-exr", output_uri, "--report", report_uri]
                launched = launch(command, root, environment, 30.0)
            cell_path = root / cell_uri
            cell_path.mkdir(parents=True, exist_ok=True)
            (cell_path / "stdout.log").write_text(launched["stdout"], encoding="utf-8")
            (cell_path / "stderr.log").write_text(launched["stderr"], encoding="utf-8")
            report_path = root / report_uri
            report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else None
            run = {"cellId": cell_id, "fixtureId": fixture["id"], "repeat": repeat, "pid": launched["pid"], "exitCode": launched["exitCode"], "timedOut": launched["timedOut"], "elapsedSeconds": launched["elapsedSeconds"], "argv": normalized_argv(command, root), "reportUri": report_uri, "stdoutUri": f"{cell_uri}/stdout.log", "stderrUri": f"{cell_uri}/stderr.log", "report": report}
            runs.append(run)
            if launched["exitCode"] != 0 or launched["timedOut"] or report is None:
                (output_root / "run.failure.json").write_text(json.dumps({"schemaVersion": "bfs.deterministicDisplaceRunFailure.v0.1", "failedCell": run, "runs": runs}, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
                raise RuntimeError(f"B52-D6 cell failed: {cell_id}")
    receipt_body = {
        "schemaVersion": "bfs.deterministicDisplaceCalibrationReceipt.v0.1",
        "experimentId": spec["experimentId"],
        "preregistration": preregistration,
        "toolFreezeCommit": args.tool_freeze_commit,
        "tools": tools,
        "parentObservations": parent_observations,
        "runtimeObservations": {"blender": blender_observation, "ocio": ocio},
        "checks": checks,
        "diskAdmission": disk,
        "runs": runs,
    }
    receipt = {**receipt_body, "receiptHash": canonical_hash(receipt_body)}
    receipt_path = output_root / "run.receipt.json"
    result_path = output_root / "results.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    command = [sys.executable, TOOL_URIS["analyzer"], "--spec", spec_uri, "--receipt", str(receipt_path.relative_to(root)), "--output", str(result_path.relative_to(root))]
    process = subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)
    (output_root / "analysis.stdout.log").write_text(process.stdout, encoding="utf-8")
    (output_root / "analysis.stderr.log").write_text(process.stderr, encoding="utf-8")
    if process.returncode:
        (output_root / "analysis.failure.json").write_text(json.dumps({"schemaVersion": "bfs.deterministicDisplaceAnalysisFailure.v0.1", "exitCode": process.returncode, "argv": normalized_argv(command, root), "stdout": process.stdout, "stderr": process.stderr}, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
        raise SystemExit(process.returncode)
    print(process.stdout.strip())
    print(f"BFS_B52_D6_RUN_OK receipt={sha256_file(receipt_path)} result={sha256_file(result_path)}", flush=True)


if __name__ == "__main__":
    main()
