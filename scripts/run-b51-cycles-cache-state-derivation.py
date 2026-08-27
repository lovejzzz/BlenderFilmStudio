"""Run B51-D2 with an atomic, reversible Cycles cache intervention."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREREGISTRATION_COMMIT = "90d73be7b73cb15e6f9a15f7fc5f3d72b6af2595"
SPEC_URI = Path("specs/native-cycles-cache-state-derivation.v0.1.json")
SPEC_SHA256 = "3c0523e7d74a723e7326cfa39fb142f06386ae7806fd4e98ed2835d8c5ae0341"
INSPECTOR_PYTHON = Path("/Applications/Blender.app/Contents/Resources/5.2/python/bin/python3.13")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def tree_manifest(root: Path) -> dict:
    if not root.is_dir() or root.is_symlink():
        raise RuntimeError(f"unsafe cache tree root: {root}")
    records = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode):
            raise RuntimeError(f"cache symlink rejected: {relative}")
        if stat.S_ISREG(info.st_mode):
            records.append({"relativePath": relative, "mode": stat.S_IMODE(info.st_mode), "bytes": info.st_size, "sha256": sha256_file(path)})
    return {"root": str(root), "fileCount": len(records), "bytes": sum(item["bytes"] for item in records), "treeSha256": canonical_hash(records), "records": records}


def observe(uri: str, expected: str) -> dict:
    path = ROOT / uri
    actual = sha256_file(path) if path.is_file() else None
    return {"uri": uri, "expectedSha256": expected, "observedSha256": actual, "match": actual == expected}


def git(*args: str) -> str:
    process = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
    if process.returncode:
        raise RuntimeError(process.stderr.strip() or "git failed")
    return process.stdout.strip()


def run_cell(spec: dict, cell: dict, output_root: Path, cache_path: Path) -> dict:
    run_root = output_root / cell["runId"]
    artifacts = run_root / "artifacts"
    work = run_root / "work"
    artifacts.mkdir(parents=True)
    work.mkdir(parents=True)
    cache_before = {"exists": cache_path.exists(), "manifest": tree_manifest(cache_path) if cache_path.exists() else None}
    argv = [str(Path(spec["nativeBlender"]["executable"])), "--background", "--disable-autoexec", "--offline-mode", str(ROOT / spec["shot"]["blendUri"]), "--python-exit-code", "1", "--python", str(ROOT / "blender/render_b51_cycles_cache_state.py"), "--", "--spec", str(ROOT / SPEC_URI), "--run-id", cell["runId"], "--output-dir", str(artifacts)]
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
    cache_after = {"exists": cache_path.exists(), "manifest": tree_manifest(cache_path) if cache_path.exists() else None}
    return {"runId": cell["runId"], "cacheState": cell["cacheState"], "order": cell["order"], "argv": argv, "pid": process.pid, "exitCode": process.returncode, "elapsedSeconds": round(elapsed, 6), "timeoutTriggered": timeout_triggered, "termSent": term_sent, "killSent": kill_sent, "cacheBefore": cache_before, "cacheAfter": cache_after, "report": report}


def main() -> None:
    spec_path = ROOT / SPEC_URI
    if sha256_file(spec_path) != SPEC_SHA256:
        raise RuntimeError("B51-D2 spec SHA differs")
    if subprocess.run(["git", "merge-base", "--is-ancestor", PREREGISTRATION_COMMIT, "HEAD"], cwd=ROOT).returncode:
        raise RuntimeError("B51-D2 preregistration is not an ancestor")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    output_root = ROOT / spec["outputRoot"]
    if output_root.exists() and any(output_root.iterdir()):
        raise RuntimeError("B51-D2 output root is not empty")

    parents = [observe(item["uri"], item["sha256"]) for item in spec["parents"].values()]
    sources = [observe(spec["shot"]["blendUri"], spec["shot"]["blendSha256"]), observe(spec["ocio"]["uri"], spec["ocio"]["sha256"]), observe(str(SPEC_URI), SPEC_SHA256)]
    if not all(item["match"] for item in [*parents, *sources]):
        raise RuntimeError("B51-D2 frozen identity differs")
    blender = Path(spec["nativeBlender"]["executable"])
    blender_observation = {"executable": str(blender), "expectedSha256": spec["nativeBlender"]["sha256"], "observedSha256": sha256_file(blender), "expectedBytes": spec["nativeBlender"]["bytes"], "observedBytes": blender.stat().st_size}
    blender_observation["match"] = blender_observation["expectedSha256"] == blender_observation["observedSha256"] and blender_observation["expectedBytes"] == blender_observation["observedBytes"]
    if not blender_observation["match"]:
        raise RuntimeError("B51-D2 Blender identity differs")
    disk = shutil.disk_usage(ROOT)
    free_after = disk.free - int(spec["evidenceGates"]["projectedWriteBytes"])
    disk_admission = {"availableBytes": disk.free, "projectedWriteBytes": int(spec["evidenceGates"]["projectedWriteBytes"]), "minimumReserveBytes": int(spec["evidenceGates"]["minimumDiskReserveBytes"]), "freeAfterProjectedBytes": free_after, "status": "ACCEPTED" if free_after >= int(spec["evidenceGates"]["minimumDiskReserveBytes"]) else "BLOCKED"}
    if disk_admission["status"] != "ACCEPTED":
        raise RuntimeError("B51-D2 disk admission blocked")

    cache = Path(spec["cacheContract"]["originalPath"])
    quarantine = Path(spec["cacheContract"]["quarantinePath"])
    retained = ROOT / spec["cacheContract"]["generatedRetentionPath"]
    if not cache.is_dir() or cache.is_symlink() or quarantine.exists() or retained.exists():
        raise RuntimeError("B51-D2 cache preflight rejected")
    if cache.parent.stat().st_dev != output_root.parent.stat().st_dev:
        raise RuntimeError("B51-D2 paths are not on one filesystem")
    preflight_manifest = tree_manifest(cache)
    cache_preflight = {"status": "ACCEPTED", "original": preflight_manifest, "quarantineAbsent": True, "generatedRetentionAbsent": True, "sameFilesystem": True}
    output_root.mkdir(parents=True)
    runs = []
    cache_events = []
    runtime_operations = []
    execution_error = None
    restored_manifest = None
    restore_status = "NOT_ATTEMPTED"
    try:
        os.rename(cache, quarantine)
        runtime_operations.append("ATOMIC_RENAME_ORIGINAL_TO_QUARANTINE")
        quarantine_manifest = tree_manifest(quarantine)
        cache_events.append({"event": "SEQUESTER_ORIGINAL", "sourceAbsent": not cache.exists(), "quarantineManifest": quarantine_manifest, "matchesPreflight": quarantine_manifest["treeSha256"] == preflight_manifest["treeSha256"]})
        for cell in sorted(spec["cells"], key=lambda item: item["order"]):
            run = run_cell(spec, cell, output_root, cache)
            runs.append(run)
            runtime_operations.append(f"NATIVE_BLENDER_PROCESS_{cell['runId']}")
            print(f"BFS_B51_D2_RUN {cell['runId']} exit={run['exitCode']} elapsed={run['elapsedSeconds']:.3f}s", flush=True)
            if run["exitCode"] != 0 or run["timeoutTriggered"] or run["report"] is None or run["report"].get("passed") is not True:
                raise RuntimeError(f"B51-D2 run failed: {cell['runId']}")
    except Exception as error:
        execution_error = f"{type(error).__name__}: {error}"
    finally:
        try:
            if quarantine.exists():
                if cache.exists():
                    retained.parent.mkdir(parents=True, exist_ok=True)
                    if retained.exists():
                        raise RuntimeError("generated retention path became occupied")
                    os.rename(cache, retained)
                    runtime_operations.append("ATOMIC_RENAME_GENERATED_TO_RETENTION")
                    cache_events.append({"event": "RETAIN_GENERATED", "retainedManifest": tree_manifest(retained)})
                os.rename(quarantine, cache)
                runtime_operations.append("ATOMIC_RENAME_QUARANTINE_TO_ORIGINAL")
            restored_manifest = tree_manifest(cache)
            restore_status = "PASS" if restored_manifest["treeSha256"] == preflight_manifest["treeSha256"] and not quarantine.exists() else "FAIL"
        except Exception as restore_error:
            restore_status = "FAIL"
            execution_error = f"{execution_error + '; ' if execution_error else ''}RESTORE_{type(restore_error).__name__}: {restore_error}"
    cache_restore = {"status": restore_status, "originalExists": cache.is_dir(), "originalIsSymlink": cache.is_symlink(), "quarantineExists": quarantine.exists(), "generatedRetentionExists": retained.exists(), "restoredManifest": restored_manifest, "matchesPreflight": bool(restored_manifest and restored_manifest["treeSha256"] == preflight_manifest["treeSha256"])}

    tool_paths = {"runner": "scripts/run-b51-cycles-cache-state-derivation.py", "renderer": "blender/render_b51_cycles_cache_state.py", "analyzer": "scripts/analyze-b51-cycles-cache-state-derivation.py", "audit": "scripts/audit-b51-cycles-cache-state-derivation.py"}
    receipt = {"schemaVersion": "bfs.cyclesCacheStateRunReceipt.v0.1", "preregistration": {"commit": PREREGISTRATION_COMMIT, "specUri": str(SPEC_URI), "specSha256": SPEC_SHA256}, "toolFreezeCommit": git("rev-parse", "HEAD"), "tools": {name: {"uri": uri, "sha256": sha256_file(ROOT / uri)} for name, uri in tool_paths.items()}, "parents": spec["parents"], "parentObservations": parents, "sourceObservations": sources, "blenderObservation": blender_observation, "diskAdmission": disk_admission, "cachePreflight": cache_preflight, "cacheEvents": cache_events, "cacheRestore": cache_restore, "runtimeOperations": runtime_operations, "runs": runs, "executionError": execution_error}
    receipt_path = output_root / "run.receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if execution_error or restore_status != "PASS":
        raise RuntimeError(execution_error or "B51-D2 restore failed")
    analyzer = subprocess.run([str(INSPECTOR_PYTHON), str(ROOT / tool_paths["analyzer"]), "--spec", str(spec_path), "--receipt", str(receipt_path), "--output", str(output_root / "results.json")], cwd=ROOT, capture_output=True, text=True, check=False)
    sys.stdout.write(analyzer.stdout)
    sys.stderr.write(analyzer.stderr)
    if analyzer.returncode:
        raise RuntimeError(f"B51-D2 analyzer failed ({analyzer.returncode})")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B51_D2_RUNNER_ERROR {error}", file=sys.stderr, flush=True)
        raise SystemExit(1) from error
