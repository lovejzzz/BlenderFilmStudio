#!/usr/bin/env python3
"""Run the frozen four-cell RC6 local-domain static Mantaflow control."""

import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-01-local-static-attempt-19")
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-01-local-static-attempt-19"
BINARY = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC5-2026-09-01-attempt-01/build/bin/Film Studio Engine F0.app/Contents/MacOS/Blender")
SOURCE_BLEND = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-01-feasibility-attempt-13/RC6_F1_BULLET_MANTAFLOW_CONSEQUENCE.blend")
SCENE_TOOL = RESEARCH / "scripts/run-rc6-liquid-local-static-scene.py"
AUDIT_TOOL = RESEARCH / "scripts/audit-rc6-liquid-local-static-matrix.py"
SPEC = RESEARCH / "specs/ai-native-studio-rc6-liquid-local-static.v0.19.json"
CELLS = (("radius-1p0", 1.0), ("radius-1p1", 1.1), ("radius-1p2", 1.2), ("radius-1p3", 1.3))
BANNED_MEDIA = {".exr", ".png", ".jpg", ".jpeg", ".mov", ".mp4"}


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


def manifest(root, exclusions=()):
    excluded = {str(value) for value in exclusions}
    files = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        relative = str(path.relative_to(root))
        if relative in excluded:
            continue
        files.append({"path": relative, "bytes": path.stat().st_size, "sha256": sha(path)})
    value = {"schemaVersion": "bfs.rootManifest.v0.1", "root": str(root), "files": files}
    value["manifestHash"] = self_hash(value, "manifestHash")
    return value


def expected_argv(cell_id, radius):
    return [
        str(BINARY), "--background", "--factory-startup", "--disable-autoexec", "--offline-mode",
        str(SOURCE_BLEND), "--python", str(SCENE_TOOL), "--",
        "--cell-id", cell_id, "--work-root", str(WORK), "--evidence-root", str(EVIDENCE),
        "--resolution", "96", "--frame-end", "7", "--particle-radius", str(radius), "--particle-number", "2",
    ]


def run_cell(index, cell_id, radius):
    stdout_path = EVIDENCE / "logs" / f"{index:02d}-{cell_id}.stdout.log"
    stderr_path = EVIDENCE / "logs" / f"{index:02d}-{cell_id}.stderr.log"
    argv = expected_argv(cell_id, radius)
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
        "schemaVersion": "bfs.rc6LiquidLocalStaticProcess.v0.1",
        "index": index,
        "cellId": cell_id,
        "argv": argv,
        "cwd": str(RESEARCH),
        "exitCode": done.returncode,
        "wallSeconds": round(time.monotonic() - started, 6),
        "stdoutSha256": sha(stdout_path),
        "stderrSha256": sha(stderr_path),
    }
    process["processHash"] = self_hash(process, "processHash")
    write_exclusive(EVIDENCE / "processes" / f"{index:02d}-{cell_id}.json", process)
    result_path = EVIDENCE / "cells" / cell_id / "result.json"
    error = None
    stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace")
    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
    if done.returncode != 0:
        error = f"process exit {done.returncode}"
    elif "Traceback (most recent call last)" in stdout_text + stderr_text:
        error = "Blender traceback"
    elif "RC6_STATIC_CALIBRATION=" not in stdout_text or not result_path.is_file():
        error = "missing measured result"
    if error:
        return process, None, error
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if result.get("resultHash") != self_hash(result, "resultHash") or result.get("status") != "MEASURED":
        return process, result, "cell result self-audit failed"
    return process, result, None


def cell_passes(row, thresholds):
    metrics = row["metrics"]
    return (
        metrics["maximumNonManifoldEdgeCount"] == 0
        and metrics["maximumConnectedComponentCount"] <= thresholds["maximumConnectedComponentCount"]
        and metrics["minimumLargestComponentFraction"] >= thresholds["minimumLargestComponentFraction"]
        and metrics["maximumAbsoluteVolumeDriftFraction"] <= thresholds["maximumAbsoluteTemporalDriftFraction"]
        and metrics["maximumAbsoluteSourceVolumeErrorFraction"] <= thresholds["maximumAbsoluteSourceVolumeErrorFraction"]
        and metrics["maximumOutsideCupInteriorPlusOneVoxelFraction"] <= thresholds["maximumOutsideCupInteriorPlusOneVoxelFraction"]
    )


def main():
    if WORK.exists() or EVIDENCE.exists():
        raise RuntimeError("RC6 local static roots are not fresh")
    if subprocess.run(["git", "status", "--porcelain"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout:
        raise RuntimeError("research worktree must be clean before formal execution")
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    if spec.get("specHash") != self_hash(spec, "specHash") or spec.get("status") != "FROZEN":
        raise RuntimeError("RC6 local static spec identity mismatch")
    expected_tools = {
        str(SCENE_TOOL.relative_to(RESEARCH)): sha(SCENE_TOOL),
        str(Path(__file__).resolve().relative_to(RESEARCH)): sha(Path(__file__).resolve()),
        str(AUDIT_TOOL.relative_to(RESEARCH)): sha(AUDIT_TOOL),
    }
    if spec["tools"] != expected_tools:
        raise RuntimeError("RC6 local static tool roster mismatch")
    if sha(BINARY) != spec["inputs"]["binarySha256"] or sha(SOURCE_BLEND) != spec["inputs"]["sourceBlendSha256"]:
        raise RuntimeError("RC6 local static binary or source blend mismatch")
    free_before = shutil.disk_usage(WORK.parent).free
    ceilings = spec["resourceCeilings"]
    if free_before < ceilings["minimumFreeBytesBefore"] or free_before < ceilings["minimumFreeBytesAfter"] + ceilings["projectedWriteBytes"]:
        raise RuntimeError("RC6 local static resource admission failed")
    for root in (WORK, EVIDENCE):
        root.mkdir(parents=True, exist_ok=False)
    for root in (
        WORK / "user/config", WORK / "user/scripts", WORK / "user/datafiles", WORK / "user/extensions",
        EVIDENCE / "logs", EVIDENCE / "processes", EVIDENCE / "cells",
    ):
        root.mkdir(parents=True, exist_ok=False)
    admission = {
        "schemaVersion": "bfs.rc6LiquidLocalStaticAdmission.v0.1",
        "status": "PASS",
        "researchCommit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.strip(),
        "freeBytesBefore": free_before,
        "binarySha256": sha(BINARY),
        "sourceBlendSha256": sha(SOURCE_BLEND),
        "specHash": spec["specHash"],
    }
    admission["admissionHash"] = self_hash(admission, "admissionHash")
    write_exclusive(EVIDENCE / "admission.json", admission)

    processes = []
    results = []
    try:
        for index, (cell_id, radius) in enumerate(CELLS, start=1):
            process, result, error = run_cell(index, cell_id, radius)
            processes.append(process)
            if error:
                raise RuntimeError(f"{cell_id}: {error}")
            results.append(result)
        fixed = spec["matrix"]["fixed"]
        for result, (cell_id, radius) in zip(results, CELLS):
            expected_configuration = dict(fixed)
            expected_configuration["particleRadius"] = radius
            if result["cellId"] != cell_id or result["configuration"] != expected_configuration:
                raise RuntimeError(f"{cell_id}: configuration mismatch")
            baked = result["bakedState"]
            baked_path = Path(baked["uri"])
            if not baked_path.is_file() or baked_path.stat().st_size != baked["bytes"] or sha(baked_path) != baked["sha256"]:
                raise RuntimeError(f"{cell_id}: baked-state identity mismatch")
        thresholds = spec["acceptanceThresholds"]
        passing = [row for row in results if cell_passes(row, thresholds)]
        ranked = sorted(results, key=lambda row: (
            row["metrics"]["maximumNonManifoldEdgeCount"] > 0,
            row["metrics"]["maximumAbsoluteSourceVolumeErrorFraction"],
            row["metrics"]["maximumAbsoluteVolumeDriftFraction"],
            row["metrics"]["maximumConnectedComponentCount"],
            -row["metrics"]["minimumLargestComponentFraction"],
            row["configuration"]["particleRadius"],
        ))
        work_bytes = tree_bytes(WORK)
        evidence_bytes_before = tree_bytes(EVIDENCE)
        forbidden_media = sorted(str(path) for root in (WORK, EVIDENCE) for path in root.rglob("*") if path.is_file() and path.suffix.lower() in BANNED_MEDIA)
        execution_pass = (
            len(processes) == 4 and all(row["exitCode"] == 0 for row in processes)
            and work_bytes <= ceilings["workBytes"] and evidence_bytes_before <= ceilings["evidenceBytes"]
            and shutil.disk_usage(WORK.parent).free >= ceilings["minimumFreeBytesAfter"] and not forbidden_media
        )
        matrix = {
            "schemaVersion": "bfs.rc6LiquidLocalStaticMatrix.v0.1",
            "status": "PASS_EXECUTION" if execution_pass else "FAIL_EXECUTION",
            "scientificVerdict": "PASS_STATIC_CONTROL" if passing else "FAIL_STATIC_CONTROL",
            "slowTipUnlocked": bool(execution_pass and passing),
            "selectionRule": spec["matrix"]["selectionRule"],
            "selectedCellId": (passing or ranked)[0]["cellId"],
            "selectedCandidateKind": "accepted" if passing else "relative-only",
            "cells": [{
                "cellId": row["cellId"], "particleRadius": row["configuration"]["particleRadius"],
                "passesStaticControl": cell_passes(row, thresholds), "resultHash": row["resultHash"], "metrics": row["metrics"],
            } for row in results],
            "counts": {"blenderStarts": 4, "fluidDataBakes": 4, "fluidMeshBakes": 4, "blendSaves": 4, "renderCalls": 0, "networkCalls": 0, "engineRemoteWrites": 0},
            "resources": {"freeBytesBefore": free_before, "freeBytesAfter": shutil.disk_usage(WORK.parent).free, "workBytes": work_bytes, "evidenceBytesBeforeMatrix": evidence_bytes_before},
            "forbiddenMedia": forbidden_media,
            "claimCeiling": spec["claimCeiling"],
        }
        matrix["matrixHash"] = self_hash(matrix, "matrixHash")
        write_exclusive(EVIDENCE / "matrix.json", matrix)
        write_exclusive(EVIDENCE / "work-manifest.json", manifest(WORK))
        write_exclusive(EVIDENCE / "evidence-manifest.json", manifest(EVIDENCE, exclusions=("evidence-manifest.json", "independent-audit.json")))
        print("RC6_LOCAL_STATIC_MATRIX=" + canonical({"status": matrix["status"], "scientificVerdict": matrix["scientificVerdict"], "selectedCellId": matrix["selectedCellId"], "matrixHash": matrix["matrixHash"]}), flush=True)
        if not execution_pass:
            raise RuntimeError("RC6 local static execution or resource audit failed")
    except Exception as error:
        failure_path = EVIDENCE / "failure.json"
        if not failure_path.exists():
            failure = {
                "schemaVersion": "bfs.rc6LiquidLocalStaticFailure.v0.1", "status": "FAIL_EXECUTION",
                "errorType": type(error).__name__, "message": str(error),
                "processes": [{"cellId": row["cellId"], "processHash": row["processHash"], "exitCode": row["exitCode"]} for row in processes],
                "counts": {"blenderStarts": len(processes), "renderCalls": 0, "networkCalls": 0, "engineRemoteWrites": 0},
                "resources": {"freeBytesBefore": free_before, "freeBytesAfter": shutil.disk_usage(WORK.parent).free, "workBytes": tree_bytes(WORK), "evidenceBytes": tree_bytes(EVIDENCE)},
            }
            failure["failureHash"] = self_hash(failure, "failureHash")
            write_exclusive(failure_path, failure)
        raise


if __name__ == "__main__":
    main()
