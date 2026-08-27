"""Run the preregistered B51-D1 native CPU / Metal matrix."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PREREGISTRATION_COMMIT = "57ae67254c0c269c283acd7e280654a74316442e"
SPEC_URI = Path("specs/native-cycles-backend-derivation.v0.1.json")
SPEC_SHA256 = "91457a34f654423ccd14eee25ea0b147d7a66ddce6c107fb9f1e20f694ca931b"
INSPECTOR_PYTHON = Path("/Applications/Blender.app/Contents/Resources/5.2/python/bin/python3.13")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def observe(uri: str, expected: str) -> dict:
    path = REPOSITORY_ROOT / uri
    actual = sha256_file(path) if path.is_file() else None
    return {"uri": uri, "expectedSha256": expected, "observedSha256": actual, "match": actual == expected}


def git(*arguments: str) -> str:
    process = subprocess.run(["git", *arguments], cwd=REPOSITORY_ROOT, text=True, capture_output=True, check=False)
    if process.returncode:
        raise RuntimeError(process.stderr.strip() or "git command failed")
    return process.stdout.strip()


def main() -> None:
    spec_path = REPOSITORY_ROOT / SPEC_URI
    if sha256_file(spec_path) != SPEC_SHA256:
        raise RuntimeError("B51-D1 spec SHA differs")
    if subprocess.run(["git", "merge-base", "--is-ancestor", PREREGISTRATION_COMMIT, "HEAD"], cwd=REPOSITORY_ROOT).returncode:
        raise RuntimeError("B51-D1 preregistration is not an ancestor")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    output_root = REPOSITORY_ROOT / spec["outputRoot"]
    if output_root.exists() and any(output_root.iterdir()):
        raise RuntimeError("B51-D1 output root is not empty")

    parent_observations = [observe(item["uri"], item["sha256"]) for item in spec["parents"].values()]
    source_observations = [observe(item["blendUri"], item["blendSha256"]) for item in spec["shots"]]
    source_observations.append(observe(spec["ocio"]["uri"], spec["ocio"]["sha256"]))
    source_observations.append(observe(str(SPEC_URI), SPEC_SHA256))
    if not all(item["match"] for item in [*parent_observations, *source_observations]):
        raise RuntimeError("B51-D1 frozen parent or source identity differs")

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
        raise RuntimeError("B51-D1 Blender executable identity differs")

    disk = shutil.disk_usage(REPOSITORY_ROOT)
    free_after = disk.free - int(spec["evidenceGates"]["projectedWriteBytes"])
    disk_admission = {
        "availableBytes": disk.free,
        "projectedWriteBytes": int(spec["evidenceGates"]["projectedWriteBytes"]),
        "minimumReserveBytes": int(spec["evidenceGates"]["minimumDiskReserveBytes"]),
        "freeAfterProjectedBytes": free_after,
        "status": "ACCEPTED" if free_after >= int(spec["evidenceGates"]["minimumDiskReserveBytes"]) else "BLOCKED",
    }
    if disk_admission["status"] != "ACCEPTED":
        raise RuntimeError(f"B51-D1 disk reserve rejected: {disk.free}")

    output_root.mkdir(parents=True, exist_ok=True)
    runs = []
    runtime_operations = []
    for cell in sorted(spec["cells"], key=lambda item: item["order"]):
        shot = next(item for item in spec["shots"] if item["id"] == cell["shot"])
        run_root = output_root / cell["runId"]
        artifact_root = run_root / "artifacts"
        work_root = run_root / "work"
        artifact_root.mkdir(parents=True)
        work_root.mkdir(parents=True)
        argv = [
            str(blender), "--background", "--disable-autoexec", "--offline-mode",
            str(REPOSITORY_ROOT / shot["blendUri"]), "--python-exit-code", "1", "--python",
            str(REPOSITORY_ROOT / "blender/render_b51_native_cycles_backend.py"), "--",
            "--spec", str(spec_path), "--run-id", cell["runId"], "--output-dir", str(artifact_root),
        ]
        environment = {
            "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "OCIO": str(REPOSITORY_ROOT / spec["ocio"]["uri"]),
            "TMPDIR": str(work_root),
            "BLENDER_USER_CONFIG": str(work_root / "blender-config"),
            "BLENDER_USER_SCRIPTS": str(work_root / "blender-scripts"),
        }
        started = time.perf_counter()
        process = subprocess.Popen(argv, cwd=REPOSITORY_ROOT, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        timeout_triggered = False
        terminated = False
        killed = False
        try:
            stdout, stderr = process.communicate(timeout=spec["evidenceGates"]["perProcessWallTimeSeconds"])
        except subprocess.TimeoutExpired:
            timeout_triggered = True
            process.terminate()
            terminated = True
            try:
                stdout, stderr = process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                killed = True
                stdout, stderr = process.communicate()
        elapsed = time.perf_counter() - started
        (run_root / "stdout.log").write_text(stdout, encoding="utf-8")
        (run_root / "stderr.log").write_text(stderr, encoding="utf-8")
        report_path = artifact_root / "render.report.json"
        report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else None
        run = {
            "runId": cell["runId"], "shotId": cell["shot"], "device": cell["device"], "repeat": cell["repeat"],
            "order": cell["order"], "argv": argv, "pid": process.pid, "exitCode": process.returncode,
            "elapsedSeconds": round(elapsed, 6), "timeoutTriggered": timeout_triggered,
            "termSent": terminated, "killSent": killed, "report": report,
        }
        runs.append(run)
        runtime_operations.append(f"NATIVE_BLENDER_PROCESS_{cell['runId']}")
        print(f"BFS_B51_D1_RUN {cell['runId']} exit={process.returncode} elapsed={elapsed:.3f}s", flush=True)
        if process.returncode != 0 or timeout_triggered or report is None or report.get("passed") is not True:
            raise RuntimeError(f"B51-D1 run failed: {cell['runId']}")

    tool_paths = {
        "runner": "scripts/run-b51-native-cycles-backend-derivation.py",
        "renderer": "blender/render_b51_native_cycles_backend.py",
        "analyzer": "scripts/analyze-b51-native-cycles-backend-derivation.py",
        "audit": "scripts/audit-b51-native-cycles-backend-derivation.py",
    }
    receipt = {
        "schemaVersion": "bfs.nativeCyclesBackendRunReceipt.v0.1",
        "preregistration": {"commit": PREREGISTRATION_COMMIT, "specUri": str(SPEC_URI), "specSha256": SPEC_SHA256},
        "toolFreezeCommit": git("rev-parse", "HEAD"),
        "tools": {name: {"uri": uri, "sha256": sha256_file(REPOSITORY_ROOT / uri)} for name, uri in tool_paths.items()},
        "parents": spec["parents"],
        "parentObservations": parent_observations,
        "sourceObservations": source_observations,
        "blenderObservation": blender_observation,
        "diskAdmission": disk_admission,
        "operationBoundary": spec["operationBoundary"],
        "runtimeOperations": runtime_operations,
        "runs": runs,
    }
    receipt_path = output_root / "run.receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    analyzer = REPOSITORY_ROOT / "scripts/analyze-b51-native-cycles-backend-derivation.py"
    analysis = subprocess.run(
        [str(INSPECTOR_PYTHON), str(analyzer), "--spec", str(spec_path), "--receipt", str(receipt_path), "--output", str(output_root / "results.json")],
        cwd=REPOSITORY_ROOT, text=True, capture_output=True, check=False,
    )
    sys.stdout.write(analysis.stdout)
    sys.stderr.write(analysis.stderr)
    if analysis.returncode:
        raise RuntimeError(f"B51-D1 analyzer failed ({analysis.returncode})")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B51_D1_RUNNER_ERROR {error}", file=sys.stderr, flush=True)
        raise SystemExit(1) from error
