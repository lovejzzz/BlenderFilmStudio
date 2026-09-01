#!/usr/bin/env python3
"""Run one bounded high-resolution static liquid confirmation."""

import hashlib
import json
import math
import os
import shutil
import subprocess
import time
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-01-static-confirmation-attempt-17")
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-01-static-confirmation-attempt-17"
BINARY = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC5-2026-09-01-attempt-01/build/bin/Film Studio Engine F0.app/Contents/MacOS/Blender")
SOURCE_BLEND = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-01-feasibility-attempt-13/RC6_F1_BULLET_MANTAFLOW_CONSEQUENCE.blend")
SCENE_TOOL = RESEARCH / "scripts/run-rc6-liquid-static-confirmation-scene.py"
SPEC = RESEARCH / "specs/ai-native-studio-rc6-liquid-static-confirmation.v0.17.json"
EXPECTED_BINARY_SHA256 = "ad08b54132b75325a12580f705fdefc205dd4444a36f2491e4d8a200e1091ef2"
EXPECTED_SOURCE_BLEND_SHA256 = "9ac79c9c3c0d13273ac20804a3af99884f9465534800c3d9ca2ae8121499e644"
MINIMUM_FREE = 120 * 1024**3
MINIMUM_RESERVE = 100 * 1024**3
PROJECTED_WRITES = 2 * 1024**3
WORK_LIMIT = 2 * 1024**3
EVIDENCE_LIMIT = 64 * 1024**2


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def self_hash(value, field):
    body = dict(value)
    body.pop(field, None)
    return hashlib.sha256(canonical(body).encode()).hexdigest()


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def write_exclusive(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def tree_bytes(root):
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file() and not path.is_symlink())


def main():
    if WORK.exists() or EVIDENCE.exists():
        raise RuntimeError("static confirmation roots are not fresh")
    if sha(BINARY) != EXPECTED_BINARY_SHA256 or sha(SOURCE_BLEND) != EXPECTED_SOURCE_BLEND_SHA256:
        raise RuntimeError("static confirmation binary or source blend identity mismatch")
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    if spec["specHash"] != self_hash(spec, "specHash"):
        raise RuntimeError("static confirmation spec self-hash mismatch")
    expected_tools = {
        str(Path(__file__).resolve().relative_to(RESEARCH)): sha(Path(__file__).resolve()),
        str(SCENE_TOOL.relative_to(RESEARCH)): sha(SCENE_TOOL),
    }
    if spec["status"] != "FROZEN" or spec["tools"] != expected_tools:
        raise RuntimeError("static confirmation tool roster mismatch")
    free_before = shutil.disk_usage(WORK.parent).free
    if free_before < MINIMUM_FREE or free_before < MINIMUM_RESERVE + PROJECTED_WRITES:
        raise RuntimeError("static confirmation resource admission failed")
    for root in (WORK, EVIDENCE):
        root.mkdir(parents=True, exist_ok=False)
    for root in (WORK / "user/config", WORK / "user/scripts", WORK / "user/datafiles", WORK / "user/extensions", EVIDENCE / "logs", EVIDENCE / "processes", EVIDENCE / "cells"):
        root.mkdir(parents=True, exist_ok=False)
    admission = {
        "schemaVersion": "bfs.rc6LiquidStaticConfirmationAdmission.v0.1",
        "status": "PASS",
        "freeBytesBefore": free_before,
        "minimumFreeBytes": MINIMUM_FREE,
        "minimumReserveBytes": MINIMUM_RESERVE,
        "projectedWriteBytes": PROJECTED_WRITES,
        "binarySha256": sha(BINARY),
        "sourceBlendSha256": sha(SOURCE_BLEND),
        "specHash": spec["specHash"],
    }
    admission["admissionHash"] = self_hash(admission, "admissionHash")
    write_exclusive(EVIDENCE / "admission.json", admission)

    cell_id = "radius-1p3-res192"
    stdout_path = EVIDENCE / "logs/01-static-confirmation.stdout.log"
    stderr_path = EVIDENCE / "logs/01-static-confirmation.stderr.log"
    argv = [
        str(BINARY), "--background", "--factory-startup", "--disable-autoexec", "--offline-mode",
        str(SOURCE_BLEND), "--python", str(SCENE_TOOL), "--",
        "--cell-id", cell_id,
        "--work-root", str(WORK),
        "--evidence-root", str(EVIDENCE),
        "--resolution", "192",
        "--frame-end", "7",
        "--particle-radius", "1.3",
        "--particle-number", "2",
    ]
    environment = dict(os.environ)
    environment.update({
        "BLENDER_USER_CONFIG": str(WORK / "user/config"),
        "BLENDER_USER_SCRIPTS": str(WORK / "user/scripts"),
        "BLENDER_USER_DATAFILES": str(WORK / "user/datafiles"),
        "BLENDER_USER_EXTENSIONS": str(WORK / "user/extensions"),
    })
    started = time.monotonic()
    with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
        done = subprocess.run(argv, cwd=RESEARCH, env=environment, stdout=stdout, stderr=stderr, check=False)
    process = {
        "schemaVersion": "bfs.rc6LiquidStaticConfirmationProcess.v0.1",
        "index": 1,
        "cellId": cell_id,
        "argv": argv,
        "cwd": str(RESEARCH),
        "exitCode": done.returncode,
        "wallSeconds": round(time.monotonic() - started, 6),
        "stdoutSha256": sha(stdout_path),
        "stderrSha256": sha(stderr_path),
    }
    process["processHash"] = self_hash(process, "processHash")
    write_exclusive(EVIDENCE / "processes/01-static-confirmation.json", process)
    stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace")
    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
    result_path = EVIDENCE / "cells" / cell_id / "result.json"
    if done.returncode or "Traceback (most recent call last)" in stderr_text or "RC6_STATIC_CALIBRATION=" not in stdout_text or not result_path.is_file():
        raise RuntimeError("high-resolution static confirmation process failed")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if result["resultHash"] != self_hash(result, "resultHash"):
        raise RuntimeError("high-resolution static confirmation result self-hash failed")

    analytical_volume = math.pi * 0.057**2 * 0.105
    analytical_errors = [row["meshVolumeCubicMeters"] / analytical_volume - 1.0 for row in result["samples"]]
    work_bytes = tree_bytes(WORK)
    evidence_bytes = tree_bytes(EVIDENCE)
    checks = {
        "configurationExact": result["configuration"]["resolutionMax"] == 192 and result["configuration"]["particleRadius"] == 1.3 and result["configuration"]["frameEnd"] == 7,
        "closedMeshes": result["metrics"]["maximumNonManifoldEdgeCount"] == 0,
        "coherentMeshes": result["metrics"]["maximumConnectedComponentCount"] <= 2 and result["metrics"]["minimumLargestComponentFraction"] >= 0.9,
        "temporalDriftWithinFivePercent": result["metrics"]["maximumAbsoluteVolumeDriftFraction"] <= 0.05,
        "analyticalErrorWithinFivePercent": max(abs(value) for value in analytical_errors) <= 0.05,
        "resourceCeilings": work_bytes <= WORK_LIMIT and evidence_bytes <= EVIDENCE_LIMIT and shutil.disk_usage(WORK.parent).free >= MINIMUM_RESERVE,
        "zeroRender": result["authority"]["renderCalls"] == 0,
        "zeroNetwork": result["authority"]["networkCalls"] == 0,
    }
    receipt = {
        "schemaVersion": "bfs.rc6LiquidStaticConfirmationReceipt.v0.1",
        "status": "PASS_STATIC_CONTROL" if all(checks.values()) else "FAIL_STATIC_CONTROL",
        "checks": checks,
        "resultHash": result["resultHash"],
        "processHash": process["processHash"],
        "analyticalInitialCylinderVolumeCubicMeters": round(analytical_volume, 10),
        "maximumAbsoluteAnalyticalErrorFraction": round(max(abs(value) for value in analytical_errors), 8),
        "analyticalErrorsByFrame": [{"frame": row["frame"], "errorFraction": round(error, 8)} for row, error in zip(result["samples"], analytical_errors)],
        "counts": {"blenderStarts": 1, "fluidDataBakes": 1, "fluidMeshBakes": 1, "renderCalls": 0, "networkCalls": 0, "engineRemoteWrites": 0},
        "resources": {"freeBytesBefore": free_before, "freeBytesAfter": shutil.disk_usage(WORK.parent).free, "workBytes": work_bytes, "evidenceBytes": evidence_bytes},
        "claimCeiling": "One pre-contact high-resolution static confirmation. PASS_STATIC_CONTROL is required but not sufficient for slow-tip, impact or visual fluid quality."
    }
    receipt["receiptHash"] = self_hash(receipt, "receiptHash")
    write_exclusive(EVIDENCE / "receipt.json", receipt)
    print("RC6_STATIC_CONFIRMATION=" + canonical({"status": receipt["status"], "receiptHash": receipt["receiptHash"], "checks": checks}), flush=True)


if __name__ == "__main__":
    main()
