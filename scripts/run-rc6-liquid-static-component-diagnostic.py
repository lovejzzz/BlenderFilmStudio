#!/usr/bin/env python3
"""Run one zero-bake, zero-render retained-cache component diagnostic."""

import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-01-component-diagnostic-attempt-18")
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-01-component-diagnostic-attempt-18"
BINARY = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC5-2026-09-01-attempt-01/build/bin/Film Studio Engine F0.app/Contents/MacOS/Blender")
SOURCE_BLEND = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-01-feasibility-attempt-13/RC6_F1_BULLET_MANTAFLOW_CONSEQUENCE.blend")
CACHE_ROOT = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-01-static-confirmation-attempt-17/radius-1p3-res192/mantaflow-cache")
TOOL = RESEARCH / "scripts/inspect-rc6-liquid-static-components.py"
SPEC = RESEARCH / "specs/ai-native-studio-rc6-liquid-static-component-diagnostic.v0.18.json"
EXPECTED_BINARY_SHA256 = "ad08b54132b75325a12580f705fdefc205dd4444a36f2491e4d8a200e1091ef2"
EXPECTED_SOURCE_BLEND_SHA256 = "9ac79c9c3c0d13273ac20804a3af99884f9465534800c3d9ca2ae8121499e644"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def self_hash(value, field):
    body = dict(value)
    body.pop(field, None)
    return hashlib.sha256(canonical(body).encode()).hexdigest()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_exclusive(path, value):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def main():
    if WORK.exists() or EVIDENCE.exists():
        raise RuntimeError("component diagnostic roots are not fresh")
    if sha(BINARY) != EXPECTED_BINARY_SHA256 or sha(SOURCE_BLEND) != EXPECTED_SOURCE_BLEND_SHA256 or not CACHE_ROOT.is_dir():
        raise RuntimeError("component diagnostic retained input identity mismatch")
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    if spec["specHash"] != self_hash(spec, "specHash"):
        raise RuntimeError("component diagnostic spec self-hash mismatch")
    expected_tools = {str(Path(__file__).resolve().relative_to(RESEARCH)): sha(Path(__file__).resolve()), str(TOOL.relative_to(RESEARCH)): sha(TOOL)}
    if spec["status"] != "FROZEN" or spec["tools"] != expected_tools:
        raise RuntimeError("component diagnostic tool roster mismatch")
    free_before = shutil.disk_usage(WORK.parent).free
    if free_before < 100 * 1024**3:
        raise RuntimeError("component diagnostic reserve failed")
    for root in (WORK, EVIDENCE):
        root.mkdir(parents=True, exist_ok=False)
    for root in (WORK / "user/config", WORK / "user/scripts", WORK / "user/datafiles", WORK / "user/extensions", EVIDENCE / "logs", EVIDENCE / "processes"):
        root.mkdir(parents=True, exist_ok=False)
    report_path = EVIDENCE / "diagnostic.json"
    stdout_path = EVIDENCE / "logs/01-diagnostic.stdout.log"
    stderr_path = EVIDENCE / "logs/01-diagnostic.stderr.log"
    argv = [str(BINARY), "--background", "--factory-startup", "--disable-autoexec", "--offline-mode", str(SOURCE_BLEND), "--python", str(TOOL), "--", "--cache-root", str(CACHE_ROOT), "--output", str(report_path)]
    environment = dict(os.environ)
    environment.update({"BLENDER_USER_CONFIG": str(WORK / "user/config"), "BLENDER_USER_SCRIPTS": str(WORK / "user/scripts"), "BLENDER_USER_DATAFILES": str(WORK / "user/datafiles"), "BLENDER_USER_EXTENSIONS": str(WORK / "user/extensions")})
    started = time.monotonic()
    with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
        done = subprocess.run(argv, cwd=RESEARCH, env=environment, stdout=stdout, stderr=stderr, check=False)
    process = {"schemaVersion": "bfs.rc6LiquidStaticComponentDiagnosticProcess.v0.1", "argv": argv, "cwd": str(RESEARCH), "exitCode": done.returncode, "wallSeconds": round(time.monotonic() - started, 6), "stdoutSha256": sha(stdout_path), "stderrSha256": sha(stderr_path)}
    process["processHash"] = self_hash(process, "processHash")
    write_exclusive(EVIDENCE / "processes/01-diagnostic.json", process)
    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
    stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace")
    if done.returncode or stderr_text or "RC6_COMPONENT_DIAGNOSTIC=" not in stdout_text or not report_path.is_file():
        raise RuntimeError("component diagnostic process failed")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report["reportHash"] != self_hash(report, "reportHash"):
        raise RuntimeError("component diagnostic report self-hash mismatch")
    receipt = {"schemaVersion": "bfs.rc6LiquidStaticComponentDiagnosticReceipt.v0.1", "status": "PASS", "reportHash": report["reportHash"], "processHash": process["processHash"], "counts": {"blenderStarts": 1, "fluidDataBakes": 0, "fluidMeshBakes": 0, "renderCalls": 0, "networkCalls": 0, "engineRemoteWrites": 0}, "resources": {"freeBytesBefore": free_before, "freeBytesAfter": shutil.disk_usage(WORK.parent).free}}
    receipt["receiptHash"] = self_hash(receipt, "receiptHash")
    write_exclusive(EVIDENCE / "receipt.json", receipt)
    print("RC6_COMPONENT_RECEIPT=" + canonical({"status": receipt["status"], "receiptHash": receipt["receiptHash"]}), flush=True)


if __name__ == "__main__":
    main()
