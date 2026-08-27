"""Run the preregistered B51-H1 canary and native CPU / Metal holdout."""

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
PREREGISTRATION_COMMIT = "b2c053c0f2c4c498fd8123de628dd83ba76e9ebe"
SPEC_URI = Path("specs/native-metal-production-holdout.v0.1.json")
SPEC_SHA256 = "06178fde2f81e5ce8746f6e851010443c62408c0414e157647c0e7ded5b52232"
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


def run_process(spec: dict, run_id: str, source_id: str, output_root: Path) -> dict:
    source = spec["sources"][source_id]
    run_root = output_root / run_id
    artifacts = run_root / "artifacts"
    work = run_root / "work"
    artifacts.mkdir(parents=True)
    work.mkdir(parents=True)
    argv = [
        spec["nativeBlender"]["executable"], "--background", "--disable-autoexec", "--offline-mode",
        str(ROOT / source["blendUri"]), "--python-exit-code", "1", "--python",
        str(ROOT / "blender/render_b51_native_metal_holdout.py"), "--", "--spec", str(ROOT / SPEC_URI),
        "--run-id", run_id, "--output-dir", str(artifacts),
    ]
    environment = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "OCIO": str(ROOT / spec["ocio"]["uri"]), "TMPDIR": str(work), "BLENDER_USER_CONFIG": str(work / "blender-config"), "BLENDER_USER_SCRIPTS": str(work / "blender-scripts")}
    started = time.perf_counter()
    process = subprocess.Popen(argv, cwd=ROOT, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    timeout_triggered = False
    term_sent = False
    kill_sent = False
    try:
        stdout, stderr = process.communicate(timeout=spec["evidenceGates"]["perProcessWallTimeSeconds"])
    except subprocess.TimeoutExpired:
        timeout_triggered = True
        process.terminate()
        term_sent = True
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            kill_sent = True
            stdout, stderr = process.communicate()
    elapsed = time.perf_counter() - started
    (run_root / "stdout.log").write_text(stdout, encoding="utf-8")
    (run_root / "stderr.log").write_text(stderr, encoding="utf-8")
    report_path = artifacts / "render.report.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else None
    return {"runId": run_id, "sourceId": source_id, "argv": argv, "pid": process.pid, "exitCode": process.returncode, "elapsedSeconds": round(elapsed, 6), "timeoutTriggered": timeout_triggered, "termSent": term_sent, "killSent": kill_sent, "report": report}


def main() -> None:
    spec_path = ROOT / SPEC_URI
    if sha256_file(spec_path) != SPEC_SHA256:
        raise RuntimeError("B51-H1 spec SHA differs")
    if subprocess.run(["git", "merge-base", "--is-ancestor", PREREGISTRATION_COMMIT, "HEAD"], cwd=ROOT).returncode:
        raise RuntimeError("B51-H1 preregistration is not an ancestor")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    output_root = ROOT / spec["outputRoot"]
    if output_root.exists() and any(output_root.iterdir()):
        raise RuntimeError("B51-H1 output root is not empty")

    parents = [observe(item["uri"], item["sha256"], "PARENT") for item in spec["parents"].values()]
    sources = [observe(item["blendUri"], item["blendSha256"], "SOURCE") for item in spec["sources"].values()]
    sources += [observe(spec["ocio"]["uri"], spec["ocio"]["sha256"], "OCIO"), observe(str(SPEC_URI), SPEC_SHA256, "SPEC")]
    if not all(item["match"] for item in [*parents, *sources]):
        raise RuntimeError("B51-H1 frozen identity differs")
    blender = Path(spec["nativeBlender"]["executable"])
    blender_observation = {"executable": str(blender), "expectedSha256": spec["nativeBlender"]["sha256"], "observedSha256": sha256_file(blender), "expectedBytes": spec["nativeBlender"]["bytes"], "observedBytes": blender.stat().st_size}
    blender_observation["match"] = blender_observation["expectedSha256"] == blender_observation["observedSha256"] and blender_observation["expectedBytes"] == blender_observation["observedBytes"]
    if not blender_observation["match"]:
        raise RuntimeError("B51-H1 Blender identity differs")
    disk = shutil.disk_usage(ROOT)
    free_after = disk.free - int(spec["evidenceGates"]["projectedWriteBytes"])
    disk_admission = {"availableBytes": disk.free, "projectedWriteBytes": int(spec["evidenceGates"]["projectedWriteBytes"]), "minimumReserveBytes": int(spec["evidenceGates"]["minimumDiskReserveBytes"]), "freeAfterProjectedBytes": free_after, "status": "ACCEPTED" if free_after >= int(spec["evidenceGates"]["minimumDiskReserveBytes"]) else "BLOCKED"}
    if disk_admission["status"] != "ACCEPTED":
        raise RuntimeError(f"B51-H1 disk admission blocked: free={disk.free} projected={free_after}")

    output_root.mkdir(parents=True)
    runtime_operations = []
    canary = run_process(spec, spec["canary"]["runId"], spec["canary"]["source"], output_root)
    runtime_operations.append(f"NATIVE_BLENDER_PROCESS_{spec['canary']['runId']}")
    print(f"BFS_B51_H1_RUN {canary['runId']} exit={canary['exitCode']} elapsed={canary['elapsedSeconds']:.3f}s", flush=True)
    if canary["exitCode"] != 0 or canary["timeoutTriggered"] or canary["report"] is None or canary["report"].get("passed") is not True:
        raise RuntimeError("B51-H1 canary render failed")
    canary_decision_path = output_root / "canary.decision.json"
    analyzer = ROOT / "scripts/analyze-b51-native-metal-production-holdout.py"
    check = subprocess.run([str(INSPECTOR_PYTHON), str(analyzer), "--check-canary", "--spec", str(spec_path), "--run-root", str(output_root / canary["runId"]), "--output", str(canary_decision_path), "--wall-seconds", str(canary["elapsedSeconds"])], cwd=ROOT, capture_output=True, text=True, check=False)
    sys.stdout.write(check.stdout)
    sys.stderr.write(check.stderr)
    canary_decision = json.loads(canary_decision_path.read_text(encoding="utf-8")) if canary_decision_path.is_file() else None
    if check.returncode or canary_decision is None or canary_decision.get("status") != "PASS":
        raise RuntimeError("B51-H1 canary readiness failed closed")

    runs = []
    variants = {item["id"]: item for item in spec["variants"]}
    for cell in sorted(spec["cells"], key=lambda item: item["order"]):
        source_id = variants[cell["variant"]]["source"]
        run = run_process(spec, cell["runId"], source_id, output_root)
        runs.append(run)
        runtime_operations.append(f"NATIVE_BLENDER_PROCESS_{cell['runId']}")
        print(f"BFS_B51_H1_RUN {cell['runId']} exit={run['exitCode']} elapsed={run['elapsedSeconds']:.3f}s", flush=True)
        if run["exitCode"] != 0 or run["timeoutTriggered"] or run["report"] is None or run["report"].get("passed") is not True:
            raise RuntimeError(f"B51-H1 holdout render failed: {cell['runId']}")

    source_post_observations = [observe(item["blendUri"], item["blendSha256"], "SOURCE_POST") for item in spec["sources"].values()]
    if not all(item["match"] for item in source_post_observations):
        raise RuntimeError("B51-H1 source file changed during holdout")

    tool_paths = {"runner": "scripts/run-b51-native-metal-production-holdout.py", "renderer": "blender/render_b51_native_metal_holdout.py", "analyzer": "scripts/analyze-b51-native-metal-production-holdout.py", "audit": "scripts/audit-b51-native-metal-production-holdout.py"}
    receipt = {"schemaVersion": "bfs.nativeMetalProductionHoldoutRunReceipt.v0.1", "preregistration": {"commit": PREREGISTRATION_COMMIT, "specUri": str(SPEC_URI), "specSha256": SPEC_SHA256}, "toolFreezeCommit": git("rev-parse", "HEAD"), "tools": {name: {"uri": uri, "sha256": sha256_file(ROOT / uri)} for name, uri in tool_paths.items()}, "parents": spec["parents"], "parentObservations": parents, "sourceObservations": sources, "sourcePostObservations": source_post_observations, "blenderObservation": blender_observation, "diskAdmission": disk_admission, "canary": canary, "canaryDecision": canary_decision, "runtimeOperations": runtime_operations, "runs": runs}
    receipt_path = output_root / "run.receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    analysis = subprocess.run([str(INSPECTOR_PYTHON), str(analyzer), "--spec", str(spec_path), "--receipt", str(receipt_path), "--output", str(output_root / "results.json")], cwd=ROOT, capture_output=True, text=True, check=False)
    sys.stdout.write(analysis.stdout)
    sys.stderr.write(analysis.stderr)
    if analysis.returncode:
        raise RuntimeError(f"B51-H1 analyzer failed ({analysis.returncode})")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B51_H1_RUNNER_ERROR {error}", file=sys.stderr, flush=True)
        raise SystemExit(1) from error
