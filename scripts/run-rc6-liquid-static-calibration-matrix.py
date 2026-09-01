#!/usr/bin/env python3
"""Run the frozen zero-render RC6 static-container radius matrix."""

import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-01-static-calibration-attempt-14")
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-01-static-calibration-attempt-14"
BINARY = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC5-2026-09-01-attempt-01/build/bin/Film Studio Engine F0.app/Contents/MacOS/Blender")
SOURCE_BLEND = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-01-feasibility-attempt-13/RC6_F1_BULLET_MANTAFLOW_CONSEQUENCE.blend")
SCENE_TOOL = RESEARCH / "scripts/run-rc6-liquid-static-calibration-scene.py"
SPEC = RESEARCH / "specs/ai-native-studio-rc6-liquid-static-calibration.v0.14.json"
EXPECTED_BINARY_SHA256 = "ad08b54132b75325a12580f705fdefc205dd4444a36f2491e4d8a200e1091ef2"
EXPECTED_SOURCE_BLEND_SHA256 = "9ac79c9c3c0d13273ac20804a3af99884f9465534800c3d9ca2ae8121499e644"
MINIMUM_FREE = 120 * 1024**3
MINIMUM_RESERVE = 100 * 1024**3
PROJECTED_WRITES = 2 * 1024**3
WORK_LIMIT = 2 * 1024**3
EVIDENCE_LIMIT = 64 * 1024**2
CELLS = (
    ("radius-1p0", 1.0),
    ("radius-1p1", 1.1),
    ("radius-1p2", 1.2),
    ("radius-1p3", 1.3),
)


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


def run_cell(index, cell_id, radius):
    log_root = EVIDENCE / "logs"
    process_root = EVIDENCE / "processes"
    stdout_path = log_root / f"{index:02d}-{cell_id}.stdout.log"
    stderr_path = log_root / f"{index:02d}-{cell_id}.stderr.log"
    argv = [
        str(BINARY), "--background", "--factory-startup", "--disable-autoexec", "--offline-mode",
        str(SOURCE_BLEND), "--python", str(SCENE_TOOL), "--",
        "--cell-id", cell_id,
        "--work-root", str(WORK),
        "--evidence-root", str(EVIDENCE),
        "--resolution", "96",
        "--frame-end", "7",
        "--particle-radius", str(radius),
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
    row = {
        "schemaVersion": "bfs.rc6LiquidStaticCalibrationProcess.v0.1",
        "index": index,
        "cellId": cell_id,
        "argv": argv,
        "cwd": str(RESEARCH),
        "exitCode": done.returncode,
        "wallSeconds": round(time.monotonic() - started, 6),
        "stdoutSha256": sha(stdout_path),
        "stderrSha256": sha(stderr_path),
    }
    row["processHash"] = self_hash(row, "processHash")
    write_exclusive(process_root / f"{index:02d}-{cell_id}.json", row)
    stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace")
    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
    result_path = EVIDENCE / "cells" / cell_id / "result.json"
    if done.returncode or "Traceback (most recent call last)" in stderr_text or "RC6_STATIC_CALIBRATION=" not in stdout_text or not result_path.is_file():
        raise RuntimeError(f"static calibration cell failed: {cell_id}")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if result["resultHash"] != self_hash(result, "resultHash") or result["status"] != "MEASURED":
        raise RuntimeError(f"static calibration cell self-audit failed: {cell_id}")
    return row, result


def main():
    if WORK.exists() or EVIDENCE.exists():
        raise RuntimeError("static calibration roots are not fresh")
    if sha(BINARY) != EXPECTED_BINARY_SHA256 or sha(SOURCE_BLEND) != EXPECTED_SOURCE_BLEND_SHA256:
        raise RuntimeError("static calibration binary or source blend identity mismatch")
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    if spec["specHash"] != self_hash(spec, "specHash"):
        raise RuntimeError("static calibration spec self-hash mismatch")
    expected_tools = {
        str(SCENE_TOOL.relative_to(RESEARCH)): sha(SCENE_TOOL),
        str(Path(__file__).resolve().relative_to(RESEARCH)): sha(Path(__file__).resolve()),
    }
    if spec["status"] != "FROZEN" or spec["tools"] != expected_tools:
        raise RuntimeError("static calibration tool roster mismatch")
    free_before = shutil.disk_usage(WORK.parent).free
    if free_before < MINIMUM_FREE or free_before < MINIMUM_RESERVE + PROJECTED_WRITES:
        raise RuntimeError("static calibration resource admission failed")
    for root in (WORK, EVIDENCE):
        root.mkdir(parents=True, exist_ok=False)
    for root in (WORK / "user/config", WORK / "user/scripts", WORK / "user/datafiles", WORK / "user/extensions", EVIDENCE / "logs", EVIDENCE / "processes", EVIDENCE / "cells"):
        root.mkdir(parents=True, exist_ok=False)
    admission = {
        "schemaVersion": "bfs.rc6LiquidStaticCalibrationAdmission.v0.1",
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

    completed = []
    try:
        results = []
        for index, (cell_id, radius) in enumerate(CELLS, start=1):
            process, result = run_cell(index, cell_id, radius)
            completed.append(process)
            results.append(result)
        ranked = sorted(results, key=lambda row: (
            row["metrics"]["maximumNonManifoldEdgeCount"] > 0,
            row["metrics"]["maximumAbsoluteVolumeDriftFraction"],
            row["metrics"]["maximumConnectedComponentCount"],
            -row["metrics"]["minimumLargestComponentFraction"],
            row["configuration"]["particleRadius"],
        ))
        work_bytes = tree_bytes(WORK)
        evidence_bytes = tree_bytes(EVIDENCE)
        matrix = {
            "schemaVersion": "bfs.rc6LiquidStaticCalibrationMatrix.v0.1",
            "status": "PASS" if work_bytes <= WORK_LIMIT and evidence_bytes <= EVIDENCE_LIMIT else "FAIL",
            "selectionRule": "closed mesh, then minimum absolute volume drift, then minimum component count, then maximum largest-component fraction, then lower particle radius",
            "selectedCellId": ranked[0]["cellId"],
            "selectedParticleRadius": ranked[0]["configuration"]["particleRadius"],
            "cells": [{
                "cellId": row["cellId"],
                "particleRadius": row["configuration"]["particleRadius"],
                "resultHash": row["resultHash"],
                "metrics": row["metrics"],
            } for row in results],
            "counts": {"blenderStarts": 4, "fluidDataBakes": 4, "fluidMeshBakes": 4, "renderCalls": 0, "networkCalls": 0, "engineRemoteWrites": 0},
            "resources": {"freeBytesBefore": free_before, "freeBytesAfter": shutil.disk_usage(WORK.parent).free, "workBytes": work_bytes, "evidenceBytes": evidence_bytes},
            "claimCeiling": "Relative pre-contact static-container calibration at resolution 96 through frame 7. It selects a particle-radius candidate only; it does not prove slow-tip, impact, full-resolution or visual fluid quality."
        }
        matrix["matrixHash"] = self_hash(matrix, "matrixHash")
        write_exclusive(EVIDENCE / "matrix.json", matrix)
        print("RC6_STATIC_MATRIX=" + canonical({"status": matrix["status"], "selectedCellId": matrix["selectedCellId"], "matrixHash": matrix["matrixHash"]}), flush=True)
        if matrix["status"] != "PASS":
            raise RuntimeError("static calibration matrix resource audit failed")
    except Exception as error:
        failure = {
            "schemaVersion": "bfs.rc6LiquidStaticCalibrationFailure.v0.1",
            "status": "FAIL",
            "errorType": type(error).__name__,
            "message": str(error),
            "completedProcesses": [{"index": row["index"], "cellId": row["cellId"], "processHash": row["processHash"]} for row in completed],
            "counts": {"blenderStartsCompleted": len(completed), "renderCalls": 0, "networkCalls": 0, "engineRemoteWrites": 0},
            "resources": {"freeBytesBefore": free_before, "freeBytesAfter": shutil.disk_usage(WORK.parent).free, "workBytes": tree_bytes(WORK), "evidenceBytes": tree_bytes(EVIDENCE)},
        }
        failure["failureHash"] = self_hash(failure, "failureHash")
        write_exclusive(EVIDENCE / "failure.json", failure)
        raise


if __name__ == "__main__":
    main()
