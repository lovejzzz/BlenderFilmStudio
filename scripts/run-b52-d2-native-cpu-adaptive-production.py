#!/usr/bin/env python3
"""Run the preregistered B52-D2 native CPU adaptive-production holdout."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREREGISTRATION_COMMIT = "5467a234c98d4e632705f32ad1209b1703105266"
SPEC_URI = Path("specs/native-cpu-adaptive-production-holdout.v0.1.json")
SPEC_SHA256 = "41288927f5f12c2488b9e9396ff943a152b736157264d156bfea26806eb5273e"
INSPECTOR_PYTHON = Path("/Applications/Blender.app/Contents/Resources/5.2/python/bin/python3.13")
TOOL_PATHS = {
    "runner": "scripts/run-b52-d2-native-cpu-adaptive-production.py",
    "renderer": "blender/render_b52_d2_native_cpu_adaptive_production.py",
    "analyzer": "scripts/analyze-b52-d2-native-cpu-adaptive-production.py",
    "audit": "scripts/audit-b52-d2-native-cpu-adaptive-production.py",
    "rendererLibrary": "blender/render_b52_native_cpu_adaptive_quality_cost.py",
    "analysisLibrary": "scripts/analyze-b52-native-cpu-adaptive-quality-cost.py",
    "analysisContractTest": "tests/test_b52_d2_analysis_contract.py",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def observe(uri: str, expected: str, kind: str, expected_bytes: int | None = None) -> dict:
    path = ROOT / uri
    actual = sha256_file(path) if path.is_file() else None
    actual_bytes = path.stat().st_size if path.is_file() else None
    match = actual == expected and (expected_bytes is None or actual_bytes == expected_bytes)
    return {
        "kind": kind,
        "uri": uri,
        "expectedSha256": expected,
        "observedSha256": actual,
        "expectedBytes": expected_bytes,
        "observedBytes": actual_bytes,
        "match": match,
    }


def git(*args: str) -> str:
    process = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
    if process.returncode:
        raise RuntimeError(process.stderr.strip() or "git failed")
    return process.stdout.strip()


def git_blob_sha(commit: str, uri: str) -> str | None:
    process = subprocess.run(["git", "show", f"{commit}:{uri}"], cwd=ROOT, capture_output=True, check=False)
    return hashlib.sha256(process.stdout).hexdigest() if process.returncode == 0 else None


def sanitize(text: str) -> str:
    return text.replace(str(ROOT), "<REPO>").replace(str(Path.home()), "<USER_HOME>")


def matrix(spec: dict, d5_spec: dict) -> list[dict]:
    rows: list[dict] = []
    order = 1
    variants = {item["id"]: item for item in d5_spec["variants"]}
    for profile in spec["profiles"]:
        for variant_id, variant in variants.items():
            for repeat in range(1, spec["repeatsPerProfileVariant"] + 1):
                rows.append({
                    "runId": f"{variant_id}_{profile['id']}_R{repeat}",
                    "variant": variant_id,
                    "source": variant["source"],
                    "profile": profile["id"],
                    "role": profile["role"],
                    "repeat": repeat,
                    "order": order,
                })
                order += 1
    return rows


def run_process(spec: dict, d5_spec: dict, cell: dict, output_root: Path) -> dict:
    source = d5_spec["sources"][cell["source"]]
    run_root = output_root / cell["runId"]
    artifacts, work = run_root / "artifacts", run_root / "work"
    artifacts.mkdir(parents=True)
    work.mkdir(parents=True)
    argv = [
        spec["nativeBlender"]["executable"], "--background", "--disable-autoexec", "--offline-mode",
        str(ROOT / source["blendUri"]), "--python-exit-code", "1", "--python",
        str(ROOT / "blender/render_b52_d2_native_cpu_adaptive_production.py"), "--",
        "--spec", str(ROOT / SPEC_URI), "--variant", cell["variant"], "--profile", cell["profile"],
        "--repeat", str(cell["repeat"]), "--order", str(cell["order"]), "--output-dir", str(artifacts),
    ]
    environment = {
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "OCIO": str(ROOT / d5_spec["ocio"]["uri"]),
        "TMPDIR": str(work),
        "BLENDER_USER_CONFIG": str(work / "blender-config"),
        "BLENDER_USER_SCRIPTS": str(work / "blender-scripts"),
    }
    started = time.perf_counter()
    process = subprocess.Popen(argv, cwd=ROOT, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    timeout_triggered = term_sent = kill_sent = False
    try:
        stdout, stderr = process.communicate(timeout=spec["evidenceGates"]["perProcessWallTimeSeconds"])
    except subprocess.TimeoutExpired:
        timeout_triggered = term_sent = True
        process.terminate()
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            kill_sent = True
            process.kill()
            stdout, stderr = process.communicate()
    elapsed = time.perf_counter() - started
    (run_root / "stdout.log").write_text(sanitize(stdout), encoding="utf-8")
    (run_root / "stderr.log").write_text(sanitize(stderr), encoding="utf-8")
    report_path = artifacts / "render.report.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else None
    return {
        **cell,
        "argv": [sanitize(item) for item in argv],
        "pid": process.pid,
        "exitCode": process.returncode,
        "elapsedSeconds": round(elapsed, 6),
        "timeoutTriggered": timeout_triggered,
        "termSent": term_sent,
        "killSent": kill_sent,
        "report": report,
    }


def main() -> None:
    if sys.argv[1:] not in ([], ["--preflight-only"]):
        raise RuntimeError("usage: run-b52-d2-native-cpu-adaptive-production.py [--preflight-only]")
    preflight_only = sys.argv[1:] == ["--preflight-only"]
    spec_path = ROOT / SPEC_URI
    if sha256_file(spec_path) != SPEC_SHA256:
        raise RuntimeError("B52-D2 spec SHA differs")
    if subprocess.run(["git", "merge-base", "--is-ancestor", PREREGISTRATION_COMMIT, "HEAD"], cwd=ROOT).returncode:
        raise RuntimeError("B52-D2 preregistration is not an ancestor")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    d5_path = ROOT / spec["parents"]["d5Spec"]["uri"]
    d5_spec = json.loads(d5_path.read_text(encoding="utf-8"))
    output_root = ROOT / spec["outputRoot"]
    if output_root.exists() and any(output_root.iterdir()):
        raise RuntimeError("B52-D2 output root is not empty")

    parent_observations = [observe(item["uri"], item["sha256"], f"PARENT_{name}") for name, item in spec["parents"].items()]
    source_observations = [observe(item["blendUri"], item["blendSha256"], "SOURCE", item["blendBytes"]) for item in d5_spec["sources"].values()]
    source_observations += [observe(d5_spec["ocio"]["uri"], d5_spec["ocio"]["sha256"], "OCIO")]
    reference_observations = [
        observe(reference["uri"], reference["sha256"], f"REFERENCE_{variant['id']}_{reference['id']}", reference["bytes"])
        for variant in spec["variants"] for reference in variant["references"]
    ]
    spec_observation = observe(str(SPEC_URI), SPEC_SHA256, "SPEC")
    if not all(item["match"] for item in [*parent_observations, *source_observations, *reference_observations, spec_observation]):
        raise RuntimeError("B52-D2 frozen identity differs")

    blender = Path(spec["nativeBlender"]["executable"])
    blender_observation = {
        "executable": str(blender),
        "expectedSha256": spec["nativeBlender"]["sha256"],
        "observedSha256": sha256_file(blender),
        "expectedBytes": spec["nativeBlender"]["bytes"],
        "observedBytes": blender.stat().st_size,
    }
    blender_observation["match"] = (
        blender_observation["expectedSha256"] == blender_observation["observedSha256"]
        and blender_observation["expectedBytes"] == blender_observation["observedBytes"]
    )
    if not blender_observation["match"]:
        raise RuntimeError("B52-D2 Blender identity differs")

    tool_freeze_commit = git("rev-parse", "HEAD")
    tool_observations = {
        name: {
            "uri": uri,
            "sha256": sha256_file(ROOT / uri),
            "gitBlobSha256": git_blob_sha(tool_freeze_commit, uri),
        }
        for name, uri in TOOL_PATHS.items()
    }
    for binding in tool_observations.values():
        binding["match"] = binding["sha256"] == binding["gitBlobSha256"]
    if not all(item["match"] for item in tool_observations.values()):
        raise RuntimeError("B52-D2 tools are not frozen in HEAD")

    disk = shutil.disk_usage(ROOT)
    projected = int(spec["evidenceGates"]["projectedWriteBytes"])
    reserve = int(spec["evidenceGates"]["minimumDiskReserveBytes"])
    disk_admission = {
        "availableBytes": disk.free,
        "projectedWriteBytes": projected,
        "minimumReserveBytes": reserve,
        "freeAfterProjectedBytes": disk.free - projected,
        "status": "ACCEPTED" if disk.free - projected >= reserve else "BLOCKED",
    }
    if disk_admission["status"] != "ACCEPTED":
        raise RuntimeError(f"B52-D2 disk admission blocked: free={disk.free} projectedFree={disk.free - projected}")

    schedule = matrix(spec, d5_spec)
    if len(schedule) != spec["matrix"]["nativeBlenderProcesses"]:
        raise RuntimeError("B52-D2 matrix count differs")
    if preflight_only:
        print(json.dumps({
            "schemaVersion": "bfs.nativeCpuAdaptiveProductionPreflight.v0.1",
            "status": "PASS",
            "preregistrationCommit": PREREGISTRATION_COMMIT,
            "specSha256": SPEC_SHA256,
            "matrixCells": len(schedule),
            "parentIdentities": len(parent_observations),
            "sourceIdentities": len(source_observations),
            "referenceIdentities": len(reference_observations),
            "frozenTools": len(tool_observations),
            "blenderIdentity": blender_observation["match"],
            "diskAdmission": disk_admission,
            "renders": 0,
        }, indent=2, sort_keys=True))
        return

    output_root.mkdir(parents=True, exist_ok=True)
    runs: list[dict] = []
    runtime_operations: list[str] = []
    for cell in schedule:
        run = run_process(spec, d5_spec, cell, output_root)
        runs.append(run)
        runtime_operations.append(f"NATIVE_BLENDER_PROCESS_{cell['runId']}")
        print(f"BFS_B52_D2_RUN {cell['order']:02d}/54 {cell['runId']} exit={run['exitCode']} elapsed={run['elapsedSeconds']:.3f}s", flush=True)
        if run["exitCode"] != 0 or run["timeoutTriggered"] or run["report"] is None or run["report"].get("passed") is not True:
            raise RuntimeError(f"B52-D2 render failed: {cell['runId']}")

    source_post_observations = [observe(item["blendUri"], item["blendSha256"], "SOURCE_POST", item["blendBytes"]) for item in d5_spec["sources"].values()]
    source_post_observations += [observe(d5_spec["ocio"]["uri"], d5_spec["ocio"]["sha256"], "OCIO_POST")]
    reference_post_observations = [
        observe(reference["uri"], reference["sha256"], f"REFERENCE_POST_{variant['id']}_{reference['id']}", reference["bytes"])
        for variant in spec["variants"] for reference in variant["references"]
    ]
    if not all(item["match"] for item in [*source_post_observations, *reference_post_observations]):
        raise RuntimeError("B52-D2 source or reference changed during run")

    receipt = {
        "schemaVersion": "bfs.nativeCpuAdaptiveProductionRunReceipt.v0.1",
        "preregistration": {"commit": PREREGISTRATION_COMMIT, "specUri": str(SPEC_URI), "specSha256": SPEC_SHA256},
        "toolFreezeCommit": tool_freeze_commit,
        "tools": {name: {"uri": item["uri"], "sha256": item["sha256"]} for name, item in tool_observations.items()},
        "parentObservations": parent_observations,
        "sourceObservations": source_observations,
        "sourcePostObservations": source_post_observations,
        "referenceObservations": reference_observations,
        "referencePostObservations": reference_post_observations,
        "specObservation": spec_observation,
        "blenderObservation": blender_observation,
        "diskAdmission": disk_admission,
        "schedule": schedule,
        "runtimeOperations": runtime_operations,
        "runs": runs,
    }
    receipt_path = output_root / "run.receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    analysis = subprocess.run([
        str(INSPECTOR_PYTHON), str(ROOT / TOOL_PATHS["analyzer"]), "--spec", str(spec_path),
        "--receipt", str(receipt_path), "--output", str(output_root / "results.json"),
    ], cwd=ROOT, capture_output=True, text=True, check=False)
    sys.stdout.write(analysis.stdout)
    sys.stderr.write(analysis.stderr)
    if analysis.returncode:
        raise RuntimeError(f"B52-D2 analyzer failed ({analysis.returncode})")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B52_D2_RUNNER_ERROR {error}", file=sys.stderr, flush=True)
        raise SystemExit(1) from error
