#!/usr/bin/env python3
"""Run a three-cell Preview/Review obstacle level-set screen."""

import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-obstacle-voxel-screen-attempt-39")
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-obstacle-voxel-screen-attempt-39"
BINARY = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC5-2026-09-01-attempt-01/build/bin/Film Studio Engine F0.app/Contents/MacOS/Blender")
SOURCE_BLEND = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-01-feasibility-attempt-13/RC6_F1_BULLET_MANTAFLOW_CONSEQUENCE.blend")
SCENE_TOOL = RESEARCH / "scripts/run-rc6-liquid-obstacle-voxel-screen-scene.py"
RUNNER = Path(__file__).resolve()
AUDITOR = RESEARCH / "scripts/audit-rc6-liquid-obstacle-voxel-screen.py"
SPEC = RESEARCH / "specs/ai-native-studio-rc6-liquid-obstacle-voxel-screen.v0.41.json"
CELLS = (
    ("preview-baseline", 96, 1.5),
    ("preview-effector-plus1", 96, 2.5),
    ("review-baseline", 128, 1.5),
)
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


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_exclusive(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def file_entries(root):
    return [
        {"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": sha(path)}
        for path in sorted(root.rglob("*"))
        if path.is_file() and not path.is_symlink()
    ]


def manifest(root, exclusions=()):
    excluded = set(exclusions)
    files = [entry for entry in file_entries(root) if entry["path"] not in excluded]
    value = {"schemaVersion": "bfs.rootManifest.v0.1", "root": str(root), "files": files}
    value["manifestHash"] = self_hash(value, "manifestHash")
    return value


def tree_bytes(root):
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file() and not path.is_symlink())


def argv(cell_id, resolution, surface_distance):
    return [
        str(BINARY), "--background", "--factory-startup", "--disable-autoexec", "--offline-mode",
        str(SOURCE_BLEND), "--python", str(SCENE_TOOL), "--",
        "--cell-id", cell_id, "--work-root", str(WORK), "--evidence-root", str(EVIDENCE),
        "--resolution", str(resolution), "--effector-surface-distance", str(surface_distance),
    ]


def main():
    if WORK.exists() or EVIDENCE.exists():
        raise RuntimeError("obstacle-voxel roots are not fresh")
    if subprocess.run(["git", "status", "--porcelain"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout:
        raise RuntimeError("research worktree must be clean before obstacle-voxel screen")
    spec = read_json(SPEC)
    if spec.get("status") != "FROZEN" or spec.get("specHash") != self_hash(spec, "specHash"):
        raise RuntimeError("obstacle-voxel spec identity mismatch")
    expected_tools = {
        str(SCENE_TOOL.relative_to(RESEARCH)): sha(SCENE_TOOL),
        str(RUNNER.relative_to(RESEARCH)): sha(RUNNER),
        str(AUDITOR.relative_to(RESEARCH)): sha(AUDITOR),
    }
    if spec.get("tools") != expected_tools:
        raise RuntimeError("obstacle-voxel tool roster mismatch")
    if sha(BINARY) != spec["inputs"]["binarySha256"] or sha(SOURCE_BLEND) != spec["inputs"]["sourceBlendSha256"]:
        raise RuntimeError("obstacle-voxel input identity mismatch")
    expected_cells = [
        {"cellId": cell_id, "resolutionMax": resolution, "cupEffectorSurfaceDistanceCells": distance}
        for cell_id, resolution, distance in CELLS
    ]
    if spec.get("cells") != expected_cells:
        raise RuntimeError("obstacle-voxel cell roster mismatch")

    ceilings = spec["resourceCeilings"]
    free_before = shutil.disk_usage(WORK.parent).free
    if free_before < ceilings["minimumFreeBytesBefore"] or free_before < ceilings["minimumFreeBytesAfter"] + ceilings["projectedWriteBytes"]:
        raise RuntimeError("obstacle-voxel resource admission failed")
    for root in (WORK, EVIDENCE):
        root.mkdir(parents=True, exist_ok=False)
    for root in (
        WORK / "user/config", WORK / "user/scripts", WORK / "user/datafiles", WORK / "user/extensions",
        EVIDENCE / "logs", EVIDENCE / "processes", EVIDENCE / "cells",
    ):
        root.mkdir(parents=True, exist_ok=False)
    admission = {
        "schemaVersion": "bfs.rc6LiquidObstacleVoxelScreenAdmission.v0.1",
        "status": "PASS",
        "researchCommit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.strip(),
        "freeBytesBefore": free_before,
        "binarySha256": sha(BINARY),
        "sourceBlendSha256": sha(SOURCE_BLEND),
        "specHash": spec["specHash"],
    }
    admission["admissionHash"] = self_hash(admission, "admissionHash")
    write_exclusive(EVIDENCE / "admission.json", admission)

    environment = dict(os.environ)
    environment.update({
        "BLENDER_USER_CONFIG": str(WORK / "user/config"),
        "BLENDER_USER_SCRIPTS": str(WORK / "user/scripts"),
        "BLENDER_USER_DATAFILES": str(WORK / "user/datafiles"),
        "BLENDER_USER_EXTENSIONS": str(WORK / "user/extensions"),
    })
    processes = []
    results = []
    for index, (cell_id, resolution, distance) in enumerate(CELLS, start=1):
        stdout_path = EVIDENCE / f"logs/{index:02d}-{cell_id}.stdout.log"
        stderr_path = EVIDENCE / f"logs/{index:02d}-{cell_id}.stderr.log"
        command = argv(cell_id, resolution, distance)
        started = time.monotonic()
        with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
            done = subprocess.run(command, cwd=RESEARCH, env=environment, stdout=stdout, stderr=stderr, check=False)
        process = {
            "schemaVersion": "bfs.rc6LiquidObstacleVoxelScreenProcess.v0.1",
            "index": index,
            "cellId": cell_id,
            "argv": command,
            "cwd": str(RESEARCH),
            "exitCode": done.returncode,
            "wallSeconds": round(time.monotonic() - started, 6),
            "stdoutSha256": sha(stdout_path),
            "stderrSha256": sha(stderr_path),
        }
        process["processHash"] = self_hash(process, "processHash")
        write_exclusive(EVIDENCE / f"processes/{index:02d}-{cell_id}.json", process)
        processes.append(process)
        result_path = EVIDENCE / f"cells/{cell_id}/result.json"
        if done.returncode != 0 or stderr_path.stat().st_size != 0 or "RC6_OBSTACLE_VOXEL_SCREEN=" not in stdout_path.read_text(encoding="utf-8", errors="replace") or not result_path.is_file():
            raise RuntimeError(f"{cell_id}: Blender process failed")
        result = read_json(result_path)
        if result.get("status") != "MEASURED_DATA_ONLY" or result.get("cellId") != cell_id or result.get("resultHash") != self_hash(result, "resultHash"):
            raise RuntimeError(f"{cell_id}: result identity mismatch")
        if result.get("authority") != {
            "fluidDataBakes": 1, "fluidMeshBakes": 0, "blendSaves": 0,
            "renderCalls": 0, "networkCalls": 0, "engineRemoteWrites": 0,
        }:
            raise RuntimeError(f"{cell_id}: authority mismatch")
        results.append(result)

    by_id = {result["cellId"]: result for result in results}
    preview_base = by_id["preview-baseline"]["metrics"]["maximumOneVoxelOutlierCount"]
    preview_plus = by_id["preview-effector-plus1"]["metrics"]["maximumOneVoxelOutlierCount"]
    review_base = by_id["review-baseline"]["metrics"]["maximumOneVoxelOutlierCount"]
    surface_signal = preview_base > 0 and preview_plus == 0
    resolution_signal = preview_base != review_base
    if surface_signal:
        verdict = "PASS_SURFACE_DISTANCE_SIGNAL"
        next_cell = "review-effector-plus1"
    elif resolution_signal:
        verdict = "PASS_RESOLUTION_SIGNAL"
        next_cell = "review-effector-plus1" if review_base > 0 else "final-resolution-baseline-reproduction"
    elif preview_base == 0 and preview_plus == 0 and review_base == 0:
        verdict = "INCONCLUSIVE_LOWER_TIERS_CONTAINED"
        next_cell = "final-resolution-effector-paired-screen"
    else:
        verdict = "FAIL_OBSTACLE_VOXEL_SCREEN_NO_CORRECTION"
        next_cell = "cup-topology-and-transform-audit"

    work_bytes = tree_bytes(WORK)
    evidence_bytes = tree_bytes(EVIDENCE)
    free_after = shutil.disk_usage(WORK.parent).free
    counts = {
        "blenderStarts": 3, "fluidDataBakes": 3, "fluidMeshBakes": 0, "blendSaves": 0,
        "renderCalls": 0, "networkCalls": 0, "engineRemoteWrites": 0,
    }
    if work_bytes > ceilings["workBytes"] or evidence_bytes > ceilings["evidenceBytes"] or free_after < ceilings["minimumFreeBytesAfter"]:
        verdict = "FAIL_RESOURCE_CEILING"
    if any(path.is_symlink() for root in (WORK, EVIDENCE) for path in root.rglob("*")):
        verdict = "FAIL_SYMLINK"
    if any(path.is_file() and path.suffix.lower() in BANNED_MEDIA for root in (WORK, EVIDENCE) for path in root.rglob("*")):
        verdict = "FAIL_RENDER_MEDIA"

    receipt = {
        "schemaVersion": "bfs.rc6LiquidObstacleVoxelScreenReceipt.v0.1",
        "status": verdict,
        "surfaceDistanceSignal": surface_signal,
        "resolutionSignal": resolution_signal,
        "nextCell": next_cell,
        "cells": [
            {
                "cellId": result["cellId"],
                "resolutionMax": result["configuration"]["resolutionMax"],
                "cupEffectorSurfaceDistanceCells": result["configuration"]["cupEffectorSurfaceDistanceCells"],
                "maximumOneVoxelOutlierCount": result["metrics"]["maximumOneVoxelOutlierCount"],
                "maximumOneVoxelOutlierFraction": result["metrics"]["maximumOneVoxelOutlierFraction"],
                "framesWithOneVoxelOutliers": result["metrics"]["framesWithOneVoxelOutliers"],
                "maximumInteriorFloorPenetrationMeters": result["metrics"]["maximumInteriorFloorPenetrationMeters"],
                "outlierPhysicalRegions": result["metrics"]["outlierPhysicalRegions"],
                "wallSeconds": result["metrics"]["wallSeconds"],
                "resultHash": result["resultHash"],
            }
            for result in results
        ],
        "processHashes": [process["processHash"] for process in processes],
        "counts": counts,
        "resources": {
            "freeBytesBefore": free_before,
            "freeBytesAfter": free_after,
            "workBytes": work_bytes,
            "evidenceBytesBeforeReceipt": evidence_bytes,
        },
        "claimCeiling": spec["claimCeiling"],
    }
    receipt["receiptHash"] = self_hash(receipt, "receiptHash")
    write_exclusive(EVIDENCE / "receipt.json", receipt)
    write_exclusive(EVIDENCE / "work-manifest.json", manifest(WORK))
    write_exclusive(EVIDENCE / "evidence-manifest.json", manifest(EVIDENCE, exclusions=("evidence-manifest.json", "independent-audit.json")))
    print("RC6_OBSTACLE_VOXEL_SCREEN_RECEIPT=" + canonical({"status": verdict, "nextCell": next_cell, "receiptHash": receipt["receiptHash"]}))


if __name__ == "__main__":
    main()
