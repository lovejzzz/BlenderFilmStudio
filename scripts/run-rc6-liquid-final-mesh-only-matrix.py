#!/usr/bin/env python3
"""Run a four-cell mesh-only matrix from copied immutable resolution-192 data."""

import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
RETAINED_WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-01-source-clearance-final-c2-attempt-27")
RETAINED_EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-01-source-clearance-final-c2-attempt-27"
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-01-final-mesh-only-attempt-28")
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-01-final-mesh-only-attempt-28"
BINARY = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC5-2026-09-01-attempt-01/build/bin/Film Studio Engine F0.app/Contents/MacOS/Blender")
SCENE_TOOL = RESEARCH / "scripts/run-rc6-liquid-final-mesh-only-scene.py"
RUNNER = Path(__file__).resolve()
AUDITOR = RESEARCH / "scripts/audit-rc6-liquid-final-mesh-only-matrix.py"
SPEC = RESEARCH / "specs/ai-native-studio-rc6-liquid-final-mesh-only.v0.28.json"
RETAINED_CELL = RETAINED_WORK / "clearance-35mm-res192"
RETAINED_BLEND = RETAINED_CELL / "baked-state.blend"
RETAINED_CACHE = RETAINED_CELL / "mantaflow-cache"
CELLS = (("mesh-radius-8p0", 8.0), ("mesh-radius-9p0", 9.0), ("mesh-radius-9p5", 9.5), ("mesh-radius-10p0", 10.0))
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


def tree_bytes(root):
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file() and not path.is_symlink())


def manifest(root, exclusions=()):
    excluded = set(exclusions)
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


def data_manifest(cache_root):
    files = []
    for relative in expected_data_files():
        path = cache_root / relative
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"data manifest file missing or symlinked: {relative}")
        files.append({"path": relative, "bytes": path.stat().st_size, "sha256": sha(path)})
    value = {"schemaVersion": "bfs.rc6LiquidDataManifest.v0.1", "files": files}
    value["manifestHash"] = self_hash(value, "manifestHash")
    return value


def expected_data_files():
    return sorted(
        [f"config/config_{frame:04d}.uni" for frame in range(1, 8)]
        + [f"data/fluid_data_{frame:04d}.vdb" for frame in range(1, 8)]
    )


def expected_all_files():
    return sorted(expected_data_files() + [f"mesh/fluid_mesh_{frame:04d}.bobj.gz" for frame in range(1, 8)])


def cache_roster(cache_root):
    return sorted(str(path.relative_to(cache_root)) for path in cache_root.rglob("*") if path.is_file())


def expected_argv(cell_id, radius):
    copied_blend = WORK / cell_id / "copied-baked-state.blend"
    return [
        str(BINARY), "--background", "--factory-startup", "--disable-autoexec", "--offline-mode",
        str(copied_blend), "--python", str(SCENE_TOOL), "--", "--cell-id", cell_id,
        "--work-root", str(WORK), "--evidence-root", str(EVIDENCE),
        "--mesh-particle-radius", str(radius), "--retained-data-manifest-hash", RETAINED_DATA_HASH,
    ]


def signed_topology_passes(result, thresholds):
    for sample in result["samples"]:
        components = sample.get("components", [])
        positive = [item for item in components if item["signedVolumeCubicMeters"] > 1e-12]
        negative = [item for item in components if item["signedVolumeCubicMeters"] < -1e-12]
        if len(positive) != 1 or len(negative) > thresholds["maximumNegativeNestedShellCount"]:
            return False
        if any(item["nonManifoldEdgeCount"] for item in components):
            return False
        outer = positive[0]
        for inner in negative:
            if any(inner["boundsMinWorld"][axis] < outer["boundsMinWorld"][axis] - 1e-7 or inner["boundsMaxWorld"][axis] > outer["boundsMaxWorld"][axis] + 1e-7 for axis in range(3)):
                return False
            separation = sum((inner["centroidWorld"][axis] - outer["centroidWorld"][axis]) ** 2 for axis in range(3)) ** 0.5
            if separation > thresholds["maximumNestedCentroidSeparationMeters"]:
                return False
    return True


def cell_passes(result, thresholds):
    metrics = result["metrics"]
    return (
        metrics["maximumAbsoluteSourceVolumeErrorFraction"] <= thresholds["maximumAbsoluteSourceVolumeErrorFraction"]
        and metrics["maximumAbsoluteVolumeDriftFraction"] <= thresholds["maximumAbsoluteTemporalDriftFraction"]
        and metrics["maximumOutsideCupInteriorPlusOneVoxelFraction"] <= thresholds["maximumOutsideCupInteriorPlusOneVoxelFraction"]
        and metrics["maximumNonManifoldEdgeCount"] == thresholds["maximumNonManifoldEdgeCount"]
        and signed_topology_passes(result, thresholds)
    )


RETAINED_DATA_HASH = data_manifest(RETAINED_CACHE)["manifestHash"] if RETAINED_CACHE.is_dir() else ""


def main():
    if WORK.exists() or EVIDENCE.exists():
        raise RuntimeError("mesh-only matrix roots are not fresh")
    if subprocess.run(["git", "status", "--porcelain"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout:
        raise RuntimeError("research worktree must be clean before mesh-only matrix")
    spec = read_json(SPEC)
    if spec.get("specHash") != self_hash(spec, "specHash") or spec.get("status") != "FROZEN":
        raise RuntimeError("mesh-only matrix spec identity mismatch")
    expected_tools = {
        str(SCENE_TOOL.relative_to(RESEARCH)): sha(SCENE_TOOL),
        str(RUNNER.relative_to(RESEARCH)): sha(RUNNER),
        str(AUDITOR.relative_to(RESEARCH)): sha(AUDITOR),
    }
    if spec.get("tools") != expected_tools:
        raise RuntimeError("mesh-only matrix tool roster mismatch")
    if sha(BINARY) != spec["inputs"]["binarySha256"] or sha(RETAINED_BLEND) != spec["inputs"]["retainedBakedStateSha256"]:
        raise RuntimeError("mesh-only retained input identity mismatch")
    retained_manifest = read_json(RETAINED_EVIDENCE / "work-manifest.json")
    if retained_manifest != manifest(RETAINED_WORK) or sha(RETAINED_EVIDENCE / "work-manifest.json") != spec["inputs"]["retainedWorkManifestFileSha256"]:
        raise RuntimeError("mesh-only retained work manifest mismatch")
    retained_data = data_manifest(RETAINED_CACHE)
    if retained_data["manifestHash"] != RETAINED_DATA_HASH or RETAINED_DATA_HASH != spec["inputs"]["retainedDataManifestHash"]:
        raise RuntimeError("mesh-only retained data manifest mismatch")
    if cache_roster(RETAINED_CACHE) != expected_all_files():
        raise RuntimeError("mesh-only retained cache roster mismatch")
    if any(path.is_symlink() for path in RETAINED_WORK.rglob("*")):
        raise RuntimeError("mesh-only retained work contains symlinks")

    ceilings = spec["resourceCeilings"]
    free_before = shutil.disk_usage(WORK.parent).free
    if free_before < ceilings["minimumFreeBytesBefore"] or free_before < ceilings["minimumFreeBytesAfter"] + ceilings["projectedWriteBytes"]:
        raise RuntimeError("mesh-only resource admission failed")
    WORK.mkdir(parents=True, exist_ok=False)
    EVIDENCE.mkdir(parents=True, exist_ok=False)
    for root in (WORK / "user/config", WORK / "user/scripts", WORK / "user/datafiles", WORK / "user/extensions", EVIDENCE / "logs", EVIDENCE / "processes", EVIDENCE / "cells"):
        root.mkdir(parents=True, exist_ok=False)
    write_exclusive(EVIDENCE / "retained-data-manifest.json", retained_data)
    admission = {
        "schemaVersion": "bfs.rc6LiquidFinalMeshOnlyAdmission.v0.1", "status": "PASS",
        "researchCommit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.strip(),
        "freeBytesBefore": free_before, "binarySha256": sha(BINARY), "retainedBakedStateSha256": sha(RETAINED_BLEND),
        "retainedWorkManifestHash": retained_manifest["manifestHash"], "retainedDataManifestHash": RETAINED_DATA_HASH,
        "specHash": spec["specHash"],
    }
    admission["admissionHash"] = self_hash(admission, "admissionHash")
    write_exclusive(EVIDENCE / "admission.json", admission)

    processes = []
    results = []
    for index, (cell_id, radius) in enumerate(CELLS, start=1):
        candidate_root = WORK / cell_id
        candidate_root.mkdir(parents=True, exist_ok=False)
        copied_blend = candidate_root / "copied-baked-state.blend"
        shutil.copy2(RETAINED_BLEND, copied_blend)
        shutil.copytree(RETAINED_CACHE, candidate_root / "mantaflow-cache", symlinks=False)
        if sha(copied_blend) != sha(RETAINED_BLEND) or cache_roster(candidate_root / "mantaflow-cache") != expected_all_files() or data_manifest(candidate_root / "mantaflow-cache") != retained_data:
            raise RuntimeError(f"{cell_id}: copied input identity mismatch")
        stdout_path = EVIDENCE / "logs" / f"{index:02d}-{cell_id}.stdout.log"
        stderr_path = EVIDENCE / "logs" / f"{index:02d}-{cell_id}.stderr.log"
        argv = expected_argv(cell_id, radius)
        environment = dict(os.environ)
        environment.update({
            "BLENDER_USER_CONFIG": str(WORK / "user/config"), "BLENDER_USER_SCRIPTS": str(WORK / "user/scripts"),
            "BLENDER_USER_DATAFILES": str(WORK / "user/datafiles"), "BLENDER_USER_EXTENSIONS": str(WORK / "user/extensions"),
        })
        started = time.monotonic()
        with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
            done = subprocess.run(argv, cwd=RESEARCH, env=environment, stdout=stdout, stderr=stderr, check=False)
        process = {
            "schemaVersion": "bfs.rc6LiquidFinalMeshOnlyProcess.v0.1", "index": index, "cellId": cell_id,
            "argv": argv, "cwd": str(RESEARCH), "exitCode": done.returncode,
            "wallSeconds": round(time.monotonic() - started, 6), "stdoutSha256": sha(stdout_path), "stderrSha256": sha(stderr_path),
        }
        process["processHash"] = self_hash(process, "processHash")
        write_exclusive(EVIDENCE / "processes" / f"{index:02d}-{cell_id}.json", process)
        processes.append(process)
        result_path = EVIDENCE / "cells" / cell_id / "result.json"
        if done.returncode != 0 or stderr_path.stat().st_size != 0 or "RC6_FINAL_MESH_ONLY=" not in stdout_path.read_text(encoding="utf-8", errors="replace") or not result_path.is_file():
            raise RuntimeError(f"{cell_id}: mesh-only Blender process failed")
        result = read_json(result_path)
        if result.get("resultHash") != self_hash(result, "resultHash") or result.get("status") != "MEASURED" or result.get("cellId") != cell_id:
            raise RuntimeError(f"{cell_id}: mesh-only result identity mismatch")
        if result["configuration"]["meshParticleRadius"] != radius or result["configuration"]["retainedDataManifestHash"] != RETAINED_DATA_HASH:
            raise RuntimeError(f"{cell_id}: mesh-only configuration mismatch")
        candidate_cache = candidate_root / "mantaflow-cache"
        if data_manifest(candidate_cache) != retained_data or cache_roster(candidate_cache) != expected_all_files():
            raise RuntimeError(f"{cell_id}: mesh-only data changed or cache roster mismatch")
        baked = result["bakedState"]
        baked_path = Path(baked["uri"])
        if not baked_path.is_file() or baked_path.stat().st_size != baked["bytes"] or sha(baked_path) != baked["sha256"]:
            raise RuntimeError(f"{cell_id}: mesh-only baked-state mismatch")
        results.append(result)

    if manifest(RETAINED_WORK) != retained_manifest or data_manifest(RETAINED_CACHE) != retained_data:
        raise RuntimeError("mesh-only retained attempt changed")
    thresholds = spec["acceptanceThresholds"]
    passing = [row for row in results if cell_passes(row, thresholds)]
    ranked = sorted(results, key=lambda row: (
        not signed_topology_passes(row, thresholds),
        row["metrics"]["maximumAbsoluteSourceVolumeErrorFraction"],
        row["metrics"]["maximumAbsoluteVolumeDriftFraction"],
        row["configuration"]["meshParticleRadius"],
    ))
    selected = (passing or ranked)[0]
    work_bytes = tree_bytes(WORK)
    evidence_bytes = tree_bytes(EVIDENCE)
    forbidden_media = sorted(str(path) for root in (WORK, EVIDENCE) for path in root.rglob("*") if path.is_file() and path.suffix.lower() in BANNED_MEDIA)
    execution_pass = (
        len(processes) == 4 and all(row["exitCode"] == 0 for row in processes)
        and work_bytes <= ceilings["workBytes"] and evidence_bytes <= ceilings["evidenceBytes"]
        and shutil.disk_usage(WORK.parent).free >= ceilings["minimumFreeBytesAfter"] and not forbidden_media
    )
    matrix = {
        "schemaVersion": "bfs.rc6LiquidFinalMeshOnlyMatrix.v0.1",
        "status": "PASS_EXECUTION" if execution_pass else "FAIL_EXECUTION",
        "scientificVerdict": "PASS_FINAL_STATIC" if passing else "FAIL_FINAL_STATIC",
        "slowTipUnlocked": bool(execution_pass and passing),
        "selectedCellId": selected["cellId"], "selectedCandidateKind": "accepted" if passing else "relative-only",
        "selectionRule": spec["selectionRule"],
        "cells": [{
            "cellId": row["cellId"], "meshParticleRadius": row["configuration"]["meshParticleRadius"],
            "passesFinalStatic": cell_passes(row, thresholds), "resultHash": row["resultHash"], "metrics": row["metrics"],
        } for row in results],
        "counts": {"blenderStarts": 4, "fluidDataBakes": 0, "fluidMeshBakes": 4, "blendSaves": 4, "renderCalls": 0, "networkCalls": 0, "engineRemoteWrites": 0},
        "resources": {"freeBytesBefore": free_before, "freeBytesAfter": shutil.disk_usage(WORK.parent).free, "workBytes": work_bytes, "evidenceBytesBeforeMatrix": evidence_bytes},
        "forbiddenMedia": forbidden_media, "retainedDataManifestHash": RETAINED_DATA_HASH,
        "claimCeiling": spec["claimCeiling"],
    }
    matrix["matrixHash"] = self_hash(matrix, "matrixHash")
    write_exclusive(EVIDENCE / "matrix.json", matrix)
    write_exclusive(EVIDENCE / "work-manifest.json", manifest(WORK))
    write_exclusive(EVIDENCE / "evidence-manifest.json", manifest(EVIDENCE, exclusions=("evidence-manifest.json", "independent-audit.json")))
    print("RC6_FINAL_MESH_ONLY_MATRIX=" + canonical({"status": matrix["status"], "scientificVerdict": matrix["scientificVerdict"], "slowTipUnlocked": matrix["slowTipUnlocked"], "selectedCellId": matrix["selectedCellId"], "matrixHash": matrix["matrixHash"]}), flush=True)
    if not execution_pass:
        raise RuntimeError("mesh-only matrix execution failed")


if __name__ == "__main__":
    main()
