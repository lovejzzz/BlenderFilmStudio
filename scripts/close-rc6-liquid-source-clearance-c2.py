#!/usr/bin/env python3
"""Close retained attempt-23 without launching Blender or recomputing physics."""

import hashlib
import json
import shutil
import subprocess
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
RETAINED_WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-01-source-clearance-c1-attempt-23")
RETAINED_EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-01-source-clearance-c1-attempt-23"
CLOSURE_EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-01-source-clearance-c2-closure-attempt-24"
SPEC = RESEARCH / "specs/ai-native-studio-rc6-liquid-source-clearance-c2-closure.v0.24.json"
RUNNER = Path(__file__).resolve()
AUDITOR = RESEARCH / "scripts/audit-rc6-liquid-source-clearance-c2.py"
BINARY = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC5-2026-09-01-attempt-01/build/bin/Film Studio Engine F0.app/Contents/MacOS/Blender")
SOURCE_BLEND = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-01-feasibility-attempt-13/RC6_F1_BULLET_MANTAFLOW_CONSEQUENCE.blend")
SCENE_TOOL = RESEARCH / "scripts/run-rc6-liquid-source-clearance-scene-c1.py"
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


def expected_argv(cell_id, requested):
    return [
        str(BINARY), "--background", "--factory-startup", "--disable-autoexec", "--offline-mode",
        str(SOURCE_BLEND), "--python", str(SCENE_TOOL), "--", "--cell-id", cell_id,
        "--work-root", str(RETAINED_WORK), "--evidence-root", str(RETAINED_EVIDENCE),
        "--resolution", "96", "--frame-end", "7", "--particle-radius", "1.6",
        "--particle-number", "2", "--mesh-particle-radius", "4.5",
        "--source-bottom-clearance", str(requested),
    ]


def expected_cache_files():
    return sorted(
        [f"config/config_{frame:04d}.uni" for frame in range(1, 8)]
        + [f"data/fluid_data_{frame:04d}.vdb" for frame in range(1, 8)]
        + [f"mesh/fluid_mesh_{frame:04d}.bobj.gz" for frame in range(1, 8)]
    )


def signed_topology_passes(row, thresholds):
    for sample in row["samples"]:
        components = sample.get("components", [])
        positive = [item for item in components if item["signedVolumeCubicMeters"] > 1e-12]
        negative = [item for item in components if item["signedVolumeCubicMeters"] < -1e-12]
        if len(positive) != 1 or len(negative) > thresholds["maximumNegativeNestedShellCount"]:
            return False
        if any(item["nonManifoldEdgeCount"] for item in components):
            return False
        outer = positive[0]
        for inner in negative:
            if any(
                inner["boundsMinWorld"][axis] < outer["boundsMinWorld"][axis] - 1e-7
                or inner["boundsMaxWorld"][axis] > outer["boundsMaxWorld"][axis] + 1e-7
                for axis in range(3)
            ):
                return False
            separation = sum(
                (inner["centroidWorld"][axis] - outer["centroidWorld"][axis]) ** 2 for axis in range(3)
            ) ** 0.5
            if separation > thresholds["maximumNestedCentroidSeparationMeters"]:
                return False
    return True


def cell_passes(row, thresholds):
    metrics = row["metrics"]
    return (
        metrics["maximumNonManifoldEdgeCount"] == 0
        and metrics["maximumAbsoluteVolumeDriftFraction"] <= thresholds["maximumAbsoluteTemporalDriftFraction"]
        and metrics["maximumAbsoluteSourceVolumeErrorFraction"] <= thresholds["maximumAbsoluteSourceVolumeErrorFraction"]
        and metrics["maximumOutsideCupInteriorPlusOneVoxelFraction"] <= thresholds["maximumOutsideCupInteriorPlusOneVoxelFraction"]
        and signed_topology_passes(row, thresholds)
    )


def main():
    if CLOSURE_EVIDENCE.exists():
        raise RuntimeError("C2 closure evidence root is not fresh")
    if subprocess.run(["git", "status", "--porcelain"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout:
        raise RuntimeError("research worktree must be clean before C2 closure")
    spec = read_json(SPEC)
    if spec.get("specHash") != self_hash(spec, "specHash") or spec.get("status") != "FROZEN":
        raise RuntimeError("C2 closure spec identity mismatch")
    expected_tools = {
        str(RUNNER.relative_to(RESEARCH)): sha(RUNNER),
        str(AUDITOR.relative_to(RESEARCH)): sha(AUDITOR),
    }
    if spec.get("tools") != expected_tools:
        raise RuntimeError("C2 closure tool roster mismatch")
    if str(RETAINED_WORK) != spec["roots"]["retainedWork"] or str(RETAINED_EVIDENCE) != spec["roots"]["retainedEvidence"] or str(CLOSURE_EVIDENCE) != spec["roots"]["closureEvidence"]:
        raise RuntimeError("C2 closure roots mismatch")
    if sha(BINARY) != spec["inputs"]["binarySha256"] or sha(SOURCE_BLEND) != spec["inputs"]["sourceBlendSha256"]:
        raise RuntimeError("retained binary or source identity mismatch")
    if sha(RETAINED_EVIDENCE / "failure.json") != spec["retainedAttempt"]["failureFileSha256"]:
        raise RuntimeError("retained failure file identity mismatch")
    failure = read_json(RETAINED_EVIDENCE / "failure.json")
    if failure.get("failureHash") != self_hash(failure, "failureHash") or failure.get("message") != "clearance-20mm: configuration mismatch":
        raise RuntimeError("retained fail-closed receipt mismatch")
    if any(path.is_symlink() for root in (RETAINED_WORK, RETAINED_EVIDENCE) for path in root.rglob("*")):
        raise RuntimeError("retained roots contain symlinks")
    if any(path.is_file() and path.suffix.lower() in BANNED_MEDIA for root in (RETAINED_WORK, RETAINED_EVIDENCE) for path in root.rglob("*")):
        raise RuntimeError("retained roots contain forbidden render media")

    CLOSURE_EVIDENCE.mkdir(parents=True, exist_ok=False)
    admission = {
        "schemaVersion": "bfs.rc6LiquidSourceClearanceC2ClosureAdmission.v0.1",
        "status": "PASS",
        "researchCommit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.strip(),
        "specHash": spec["specHash"],
        "retainedFailureHash": failure["failureHash"],
        "freeBytesBefore": shutil.disk_usage(RETAINED_WORK.parent).free,
        "newBlenderStarts": 0,
        "newPhysicsBakes": 0,
        "newRenderCalls": 0,
        "networkCalls": 0,
        "engineRemoteWrites": 0,
    }
    admission["admissionHash"] = self_hash(admission, "admissionHash")
    write_exclusive(CLOSURE_EVIDENCE / "admission.json", admission)

    fixed = spec["matrix"]["fixed"]
    thresholds = spec["acceptanceThresholds"]
    placement = spec["measurementBinding"]
    results = []
    cells = []
    for index, cell in enumerate(spec["matrix"]["cells"], start=1):
        cell_id = cell["cellId"]
        requested = cell["requestedClearanceMeters"]
        process_path = RETAINED_EVIDENCE / "processes" / f"{index:02d}-{cell_id}.json"
        stdout_path = RETAINED_EVIDENCE / "logs" / f"{index:02d}-{cell_id}.stdout.log"
        stderr_path = RETAINED_EVIDENCE / "logs" / f"{index:02d}-{cell_id}.stderr.log"
        result_path = RETAINED_EVIDENCE / "cells" / cell_id / "result.json"
        process = read_json(process_path)
        result = read_json(result_path)
        if process.get("processHash") != self_hash(process, "processHash") or process.get("argv") != expected_argv(cell_id, requested) or process.get("cwd") != str(RESEARCH) or process.get("exitCode") != 0:
            raise RuntimeError(f"{cell_id}: retained process mismatch")
        if sha(stdout_path) != process.get("stdoutSha256") or sha(stderr_path) != process.get("stderrSha256") or stderr_path.stat().st_size != 0:
            raise RuntimeError(f"{cell_id}: retained log mismatch")
        if result.get("resultHash") != self_hash(result, "resultHash") or result.get("status") != "MEASURED" or result.get("cellId") != cell_id:
            raise RuntimeError(f"{cell_id}: retained result mismatch")
        configuration = dict(result["configuration"])
        measured = configuration.pop("sourceBottomClearanceMeters")
        measured_voxels = configuration.pop("sourceBottomClearanceVoxels")
        if configuration != fixed:
            raise RuntimeError(f"{cell_id}: fixed configuration mismatch")
        clearance_error = abs(measured - requested)
        voxel_error = abs(measured_voxels - cell["requestedClearanceVoxels"])
        if clearance_error > placement["maximumAbsoluteClearanceErrorMeters"] or voxel_error > placement["maximumAbsoluteClearanceErrorVoxels"]:
            raise RuntimeError(f"{cell_id}: measured placement outside frozen roundoff bound")
        if [item.get("frame") for item in result.get("samples", [])] != list(range(1, 8)):
            raise RuntimeError(f"{cell_id}: sample frame roster mismatch")
        if abs(result["metrics"]["sourceMeshVolumeCubicMeters"] - spec["inputs"]["sourceMeshVolumeCubicMeters"]) > 1e-15:
            raise RuntimeError(f"{cell_id}: source volume mismatch")
        baked = result["bakedState"]
        baked_path = Path(baked["uri"])
        if not baked_path.is_file() or baked_path.stat().st_size != baked["bytes"] or sha(baked_path) != baked["sha256"]:
            raise RuntimeError(f"{cell_id}: baked-state mismatch")
        expected_cache = expected_cache_files()
        cache_root = baked_path.parent / "mantaflow-cache"
        actual_cache = sorted(str(path.relative_to(cache_root)) for path in cache_root.rglob("*") if path.is_file())
        if result.get("cacheFiles") != expected_cache or actual_cache != expected_cache:
            raise RuntimeError(f"{cell_id}: exact cache roster mismatch")
        passed = cell_passes(result, thresholds)
        cells.append({
            "cellId": cell_id,
            "requestedClearanceMeters": requested,
            "measuredClearanceMeters": measured,
            "absoluteClearanceErrorMeters": round(clearance_error, 12),
            "requestedClearanceVoxels": cell["requestedClearanceVoxels"],
            "measuredClearanceVoxels": measured_voxels,
            "absoluteClearanceErrorVoxels": round(voxel_error, 10),
            "passesStaticControl": passed,
            "resultHash": result["resultHash"],
            "processHash": process["processHash"],
            "metrics": result["metrics"],
        })
        results.append(result)

    passing = [row for row in results if cell_passes(row, thresholds)]
    ranked = sorted(results, key=lambda row: (
        not signed_topology_passes(row, thresholds),
        row["metrics"]["maximumAbsoluteSourceVolumeErrorFraction"],
        row["metrics"]["maximumAbsoluteVolumeDriftFraction"],
        row["configuration"]["sourceBottomClearanceMeters"],
    ))
    selected = (passing or ranked)[0]
    closure = {
        "schemaVersion": "bfs.rc6LiquidSourceClearanceC2Closure.v0.1",
        "status": "PASS_CLOSURE",
        "retainedExecutionStatus": failure["status"],
        "scientificVerdict": "PASS_STATIC_CONTROL" if passing else "FAIL_STATIC_CONTROL",
        "slowTipUnlocked": bool(passing),
        "selectedCellId": selected["cellId"],
        "selectedCandidateKind": "accepted" if passing else "relative-only",
        "selectionRule": spec["matrix"]["selectionRule"],
        "cells": cells,
        "counts": {
            "retainedBlenderStarts": 4, "retainedFluidDataBakes": 4, "retainedFluidMeshBakes": 4,
            "newBlenderStarts": 0, "newPhysicsBakes": 0, "newRenderCalls": 0,
            "networkCalls": 0, "engineRemoteWrites": 0,
        },
        "resources": {
            "retainedWorkBytes": tree_bytes(RETAINED_WORK),
            "retainedEvidenceBytes": tree_bytes(RETAINED_EVIDENCE),
            "freeBytesAfter": shutil.disk_usage(RETAINED_WORK.parent).free,
        },
        "claimCeiling": spec["claimCeiling"],
    }
    closure["closureHash"] = self_hash(closure, "closureHash")
    write_exclusive(CLOSURE_EVIDENCE / "closure.json", closure)
    write_exclusive(CLOSURE_EVIDENCE / "retained-work-manifest.json", manifest(RETAINED_WORK))
    write_exclusive(CLOSURE_EVIDENCE / "retained-evidence-manifest.json", manifest(RETAINED_EVIDENCE))
    write_exclusive(CLOSURE_EVIDENCE / "closure-manifest.json", manifest(CLOSURE_EVIDENCE, exclusions=("closure-manifest.json", "independent-audit.json")))
    print("RC6_SOURCE_CLEARANCE_C2_CLOSURE=" + canonical({
        "status": closure["status"], "scientificVerdict": closure["scientificVerdict"],
        "slowTipUnlocked": closure["slowTipUnlocked"], "selectedCellId": closure["selectedCellId"],
        "closureHash": closure["closureHash"],
    }))


if __name__ == "__main__":
    main()
