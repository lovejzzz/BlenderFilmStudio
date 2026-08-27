"""Run the preregistered B51-D5 native CPU data-pass sample/cost matrix."""

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
PREREGISTRATION_COMMIT = "c1cb85429b946fc8a22d540eb8186c43dbbc0023"
SPEC_URI = Path("specs/native-cpu-data-pass-sample-cost-derivation.v0.1.json")
SPEC_SHA256 = "e504b5afa816271b70db6cfb5148eb664123817c8a5cd942595ff182d18730ae"
INSPECTOR_PYTHON = Path("/Applications/Blender.app/Contents/Resources/5.2/python/bin/python3.13")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def observe(uri: str, expected: str, kind: str) -> dict:
    path = ROOT / uri
    actual = sha256_file(path) if path.is_file() else None
    return {"kind": kind, "uri": uri, "expectedSha256": expected, "observedSha256": actual, "match": actual == expected}


def git(*args: str) -> str:
    process = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
    if process.returncode:
        raise RuntimeError(process.stderr.strip() or "git failed")
    return process.stdout.strip()


def sanitize(text: str) -> str:
    return text.replace(str(ROOT), "<REPO>").replace(str(Path.home()), "<USER_HOME>")


def matrix(spec: dict) -> list[dict]:
    rows, order = [], 1
    for samples in spec["sampleLadder"]:
        for variant in spec["variants"]:
            for repeat in range(1, spec["repeatsPerVariantDose"] + 1):
                rows.append({"runId": f"{variant['id']}_S{samples:03d}_R{repeat}", "variant": variant["id"], "source": variant["source"], "samples": samples, "repeat": repeat, "order": order})
                order += 1
    return rows


def run_process(spec: dict, cell: dict, output_root: Path) -> dict:
    source = spec["sources"][cell["source"]]
    run_root = output_root / cell["runId"]
    artifacts, work = run_root / "artifacts", run_root / "work"
    artifacts.mkdir(parents=True)
    work.mkdir(parents=True)
    argv = [
        spec["nativeBlender"]["executable"], "--background", "--disable-autoexec", "--offline-mode",
        str(ROOT / source["blendUri"]), "--python-exit-code", "1", "--python",
        str(ROOT / "blender/render_b51_native_cpu_data_sample_cost.py"), "--",
        "--spec", str(ROOT / SPEC_URI), "--variant", cell["variant"], "--samples", str(cell["samples"]),
        "--repeat", str(cell["repeat"]), "--order", str(cell["order"]), "--output-dir", str(artifacts),
    ]
    environment = {
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "OCIO": str(ROOT / spec["ocio"]["uri"]),
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
    spec_path = ROOT / SPEC_URI
    if sha256_file(spec_path) != SPEC_SHA256:
        raise RuntimeError("B51-D5 spec SHA differs")
    if subprocess.run(["git", "merge-base", "--is-ancestor", PREREGISTRATION_COMMIT, "HEAD"], cwd=ROOT).returncode:
        raise RuntimeError("B51-D5 preregistration is not an ancestor")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    output_root = ROOT / spec["outputRoot"]
    if output_root.exists() and any(output_root.iterdir()):
        raise RuntimeError("B51-D5 output root is not empty")

    parent_observations = [observe(item["uri"], item["sha256"], "PARENT") for item in spec["parents"].values()]
    source_observations = [observe(item["blendUri"], item["blendSha256"], "SOURCE") for item in spec["sources"].values()]
    source_observations += [observe(item["parentExr"]["uri"], item["parentExr"]["sha256"], "PARENT_EXR") for item in spec["variants"]]
    source_observations += [observe(spec["ocio"]["uri"], spec["ocio"]["sha256"], "OCIO"), observe(str(SPEC_URI), SPEC_SHA256, "SPEC")]
    if not all(item["match"] for item in [*parent_observations, *source_observations]):
        raise RuntimeError("B51-D5 frozen identity differs")
    blender = Path(spec["nativeBlender"]["executable"])
    blender_observation = {
        "executable": str(blender),
        "expectedSha256": spec["nativeBlender"]["sha256"],
        "observedSha256": sha256_file(blender),
        "expectedBytes": spec["nativeBlender"]["bytes"],
        "observedBytes": blender.stat().st_size,
    }
    blender_observation["match"] = blender_observation["expectedSha256"] == blender_observation["observedSha256"] and blender_observation["expectedBytes"] == blender_observation["observedBytes"]
    if not blender_observation["match"]:
        raise RuntimeError("B51-D5 Blender identity differs")
    disk = shutil.disk_usage(ROOT)
    projected, reserve = int(spec["evidenceGates"]["projectedWriteBytes"]), int(spec["evidenceGates"]["minimumDiskReserveBytes"])
    disk_admission = {"availableBytes": disk.free, "projectedWriteBytes": projected, "minimumReserveBytes": reserve, "freeAfterProjectedBytes": disk.free - projected, "status": "ACCEPTED" if disk.free - projected >= reserve else "BLOCKED"}
    if disk_admission["status"] != "ACCEPTED":
        raise RuntimeError(f"B51-D5 disk admission blocked: free={disk.free} projected={disk.free - projected}")

    output_root.mkdir(parents=True, exist_ok=True)
    schedule = matrix(spec)
    runs, runtime_operations = [], []
    for cell in schedule:
        run = run_process(spec, cell, output_root)
        runs.append(run)
        runtime_operations.append(f"NATIVE_BLENDER_PROCESS_{cell['runId']}")
        print(f"BFS_B51_D5_RUN {cell['order']:02d}/32 {cell['runId']} exit={run['exitCode']} elapsed={run['elapsedSeconds']:.3f}s", flush=True)
        if run["exitCode"] != 0 or run["timeoutTriggered"] or run["report"] is None or run["report"].get("passed") is not True:
            raise RuntimeError(f"B51-D5 render failed: {cell['runId']}")

    source_post_observations = [observe(item["blendUri"], item["blendSha256"], "SOURCE_POST") for item in spec["sources"].values()]
    source_post_observations += [observe(item["parentExr"]["uri"], item["parentExr"]["sha256"], "PARENT_EXR_POST") for item in spec["variants"]]
    if not all(item["match"] for item in source_post_observations):
        raise RuntimeError("B51-D5 source changed during run")

    tool_paths = {
        "runner": "scripts/run-b51-native-cpu-data-sample-cost.py",
        "renderer": "blender/render_b51_native_cpu_data_sample_cost.py",
        "analyzer": "scripts/analyze-b51-native-cpu-data-sample-cost.py",
        "audit": "scripts/audit-b51-native-cpu-data-sample-cost.py",
    }
    receipt = {
        "schemaVersion": "bfs.nativeCpuDataPassSampleCostRunReceipt.v0.1",
        "preregistration": {"commit": PREREGISTRATION_COMMIT, "specUri": str(SPEC_URI), "specSha256": SPEC_SHA256},
        "toolFreezeCommit": git("rev-parse", "HEAD"),
        "tools": {name: {"uri": uri, "sha256": sha256_file(ROOT / uri)} for name, uri in tool_paths.items()},
        "parentObservations": parent_observations,
        "sourceObservations": source_observations,
        "sourcePostObservations": source_post_observations,
        "blenderObservation": blender_observation,
        "diskAdmission": disk_admission,
        "schedule": schedule,
        "runtimeOperations": runtime_operations,
        "runs": runs,
    }
    receipt_path = output_root / "run.receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    analyzer = ROOT / "scripts/analyze-b51-native-cpu-data-sample-cost.py"
    analysis = subprocess.run([str(INSPECTOR_PYTHON), str(analyzer), "--spec", str(spec_path), "--receipt", str(receipt_path), "--output", str(output_root / "results.json")], cwd=ROOT, capture_output=True, text=True, check=False)
    sys.stdout.write(analysis.stdout)
    sys.stderr.write(analysis.stderr)
    if analysis.returncode:
        raise RuntimeError(f"B51-D5 analyzer failed ({analysis.returncode})")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B51_D5_RUNNER_ERROR {error}", file=sys.stderr, flush=True)
        raise SystemExit(1) from error
