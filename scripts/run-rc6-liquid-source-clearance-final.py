#!/usr/bin/env python3
"""Run one bounded resolution-192 static confirmation for 35 mm clearance."""

import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-01-source-clearance-final-attempt-25")
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-01-source-clearance-final-attempt-25"
BINARY = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC5-2026-09-01-attempt-01/build/bin/Film Studio Engine F0.app/Contents/MacOS/Blender")
SOURCE_BLEND = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-01-feasibility-attempt-13/RC6_F1_BULLET_MANTAFLOW_CONSEQUENCE.blend")
SCENE_TOOL = RESEARCH / "scripts/run-rc6-liquid-source-clearance-final-scene.py"
RUNNER = Path(__file__).resolve()
AUDITOR = RESEARCH / "scripts/audit-rc6-liquid-source-clearance-final.py"
SPEC = RESEARCH / "specs/ai-native-studio-rc6-liquid-source-clearance-final.v0.25.json"
CELL_ID = "clearance-35mm-res192"
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


def argv():
    return [
        str(BINARY), "--background", "--factory-startup", "--disable-autoexec", "--offline-mode",
        str(SOURCE_BLEND), "--python", str(SCENE_TOOL), "--", "--cell-id", CELL_ID,
        "--work-root", str(WORK), "--evidence-root", str(EVIDENCE), "--resolution", "192",
        "--frame-end", "7", "--particle-radius", "1.6", "--particle-number", "2",
        "--mesh-particle-radius", "4.5", "--source-bottom-clearance", "0.035",
    ]


def expected_cache_files():
    return sorted(
        [f"config/config_{frame:04d}.uni" for frame in range(1, 8)]
        + [f"data/fluid_data_{frame:04d}.vdb" for frame in range(1, 8)]
        + [f"mesh/fluid_mesh_{frame:04d}.bobj.gz" for frame in range(1, 8)]
    )


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


def main():
    if WORK.exists() or EVIDENCE.exists():
        raise RuntimeError("final static roots are not fresh")
    if subprocess.run(["git", "status", "--porcelain"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout:
        raise RuntimeError("research worktree must be clean before final static confirmation")
    spec = read_json(SPEC)
    if spec.get("specHash") != self_hash(spec, "specHash") or spec.get("status") != "FROZEN":
        raise RuntimeError("final static spec identity mismatch")
    expected_tools = {
        str(SCENE_TOOL.relative_to(RESEARCH)): sha(SCENE_TOOL),
        str(RUNNER.relative_to(RESEARCH)): sha(RUNNER),
        str(AUDITOR.relative_to(RESEARCH)): sha(AUDITOR),
    }
    if spec.get("tools") != expected_tools:
        raise RuntimeError("final static tool roster mismatch")
    if sha(BINARY) != spec["inputs"]["binarySha256"] or sha(SOURCE_BLEND) != spec["inputs"]["sourceBlendSha256"]:
        raise RuntimeError("final static input identity mismatch")
    ceilings = spec["resourceCeilings"]
    free_before = shutil.disk_usage(WORK.parent).free
    if free_before < ceilings["minimumFreeBytesBefore"] or free_before < ceilings["minimumFreeBytesAfter"] + ceilings["projectedWriteBytes"]:
        raise RuntimeError("final static resource admission failed")
    for root in (WORK, EVIDENCE):
        root.mkdir(parents=True, exist_ok=False)
    for root in (WORK / "user/config", WORK / "user/scripts", WORK / "user/datafiles", WORK / "user/extensions", EVIDENCE / "logs", EVIDENCE / "processes", EVIDENCE / "cells"):
        root.mkdir(parents=True, exist_ok=False)
    admission = {
        "schemaVersion": "bfs.rc6LiquidSourceClearanceFinalAdmission.v0.1", "status": "PASS",
        "researchCommit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.strip(),
        "freeBytesBefore": free_before, "binarySha256": sha(BINARY), "sourceBlendSha256": sha(SOURCE_BLEND),
        "specHash": spec["specHash"],
    }
    admission["admissionHash"] = self_hash(admission, "admissionHash")
    write_exclusive(EVIDENCE / "admission.json", admission)
    stdout_path = EVIDENCE / "logs/01-final-static.stdout.log"
    stderr_path = EVIDENCE / "logs/01-final-static.stderr.log"
    environment = dict(os.environ)
    environment.update({
        "BLENDER_USER_CONFIG": str(WORK / "user/config"), "BLENDER_USER_SCRIPTS": str(WORK / "user/scripts"),
        "BLENDER_USER_DATAFILES": str(WORK / "user/datafiles"), "BLENDER_USER_EXTENSIONS": str(WORK / "user/extensions"),
    })
    started = time.monotonic()
    with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
        done = subprocess.run(argv(), cwd=RESEARCH, env=environment, stdout=stdout, stderr=stderr, check=False)
    process = {
        "schemaVersion": "bfs.rc6LiquidSourceClearanceFinalProcess.v0.1", "index": 1, "cellId": CELL_ID,
        "argv": argv(), "cwd": str(RESEARCH), "exitCode": done.returncode,
        "wallSeconds": round(time.monotonic() - started, 6), "stdoutSha256": sha(stdout_path), "stderrSha256": sha(stderr_path),
    }
    process["processHash"] = self_hash(process, "processHash")
    write_exclusive(EVIDENCE / "processes/01-final-static.json", process)
    result_path = EVIDENCE / "cells" / CELL_ID / "result.json"
    if done.returncode != 0 or stderr_path.stat().st_size != 0 or "RC6_STATIC_CALIBRATION=" not in stdout_path.read_text(encoding="utf-8", errors="replace") or not result_path.is_file():
        raise RuntimeError("final static Blender process failed")
    result = read_json(result_path)
    if result.get("resultHash") != self_hash(result, "resultHash") or result.get("status") != "MEASURED" or result.get("cellId") != CELL_ID:
        raise RuntimeError("final static result identity mismatch")
    configuration = dict(result["configuration"])
    measured_clearance = configuration.pop("sourceBottomClearanceMeters")
    measured_voxels = configuration.pop("sourceBottomClearanceVoxels")
    if configuration != spec["configuration"]:
        raise RuntimeError("final static fixed configuration mismatch")
    binding = spec["measurementBinding"]
    if abs(measured_clearance - binding["requestedClearanceMeters"]) > binding["maximumAbsoluteClearanceErrorMeters"] or abs(measured_voxels - binding["requestedClearanceVoxels"]) > binding["maximumAbsoluteClearanceErrorVoxels"]:
        raise RuntimeError("final static placement measurement mismatch")
    if [item.get("frame") for item in result.get("samples", [])] != list(range(1, 8)):
        raise RuntimeError("final static sample roster mismatch")
    baked = result["bakedState"]
    baked_path = Path(baked["uri"])
    if not baked_path.is_file() or baked_path.stat().st_size != baked["bytes"] or sha(baked_path) != baked["sha256"]:
        raise RuntimeError("final static baked-state mismatch")
    cache_root = baked_path.parent / "mantaflow-cache"
    actual_cache = sorted(str(path.relative_to(cache_root)) for path in cache_root.rglob("*") if path.is_file())
    if result.get("cacheFiles") != expected_cache_files() or actual_cache != expected_cache_files():
        raise RuntimeError("final static exact cache roster mismatch")
    thresholds = spec["acceptanceThresholds"]
    metrics = result["metrics"]
    checks = {
        "sourceVolumeWithinFivePercent": metrics["maximumAbsoluteSourceVolumeErrorFraction"] <= thresholds["maximumAbsoluteSourceVolumeErrorFraction"],
        "temporalDriftWithinFivePercent": metrics["maximumAbsoluteVolumeDriftFraction"] <= thresholds["maximumAbsoluteTemporalDriftFraction"],
        "containedWithinOnePercent": metrics["maximumOutsideCupInteriorPlusOneVoxelFraction"] <= thresholds["maximumOutsideCupInteriorPlusOneVoxelFraction"],
        "manifold": metrics["maximumNonManifoldEdgeCount"] == thresholds["maximumNonManifoldEdgeCount"],
        "signedTopology": signed_topology_passes(result, thresholds),
        "zeroRender": result["authority"]["renderCalls"] == 0,
        "zeroNetwork": result["authority"]["networkCalls"] == 0,
    }
    work_bytes = tree_bytes(WORK)
    evidence_bytes = tree_bytes(EVIDENCE)
    checks["resourceCeilings"] = work_bytes <= ceilings["workBytes"] and evidence_bytes <= ceilings["evidenceBytes"] and shutil.disk_usage(WORK.parent).free >= ceilings["minimumFreeBytesAfter"]
    checks["zeroRenderMedia"] = not any(path.is_file() and path.suffix.lower() in BANNED_MEDIA for root in (WORK, EVIDENCE) for path in root.rglob("*"))
    receipt = {
        "schemaVersion": "bfs.rc6LiquidSourceClearanceFinalReceipt.v0.1",
        "status": "PASS_FINAL_STATIC" if all(checks.values()) else "FAIL_FINAL_STATIC",
        "slowTipUnlocked": all(checks.values()), "selectedGeometry": "clearance-35mm",
        "requestedClearanceMeters": binding["requestedClearanceMeters"], "measuredClearanceMeters": measured_clearance,
        "absoluteClearanceErrorMeters": round(abs(measured_clearance - binding["requestedClearanceMeters"]), 12),
        "checks": checks, "metrics": metrics, "resultHash": result["resultHash"], "processHash": process["processHash"],
        "counts": {"blenderStarts": 1, "fluidDataBakes": 1, "fluidMeshBakes": 1, "blendSaves": 1, "renderCalls": 0, "networkCalls": 0, "engineRemoteWrites": 0},
        "resources": {"freeBytesBefore": free_before, "freeBytesAfter": shutil.disk_usage(WORK.parent).free, "workBytes": work_bytes, "evidenceBytesBeforeReceipt": evidence_bytes},
        "claimCeiling": spec["claimCeiling"],
    }
    receipt["receiptHash"] = self_hash(receipt, "receiptHash")
    write_exclusive(EVIDENCE / "receipt.json", receipt)
    write_exclusive(EVIDENCE / "work-manifest.json", manifest(WORK))
    write_exclusive(EVIDENCE / "evidence-manifest.json", manifest(EVIDENCE, exclusions=("evidence-manifest.json", "independent-audit.json")))
    print("RC6_SOURCE_CLEARANCE_FINAL=" + canonical({"status": receipt["status"], "slowTipUnlocked": receipt["slowTipUnlocked"], "receiptHash": receipt["receiptHash"], "wallSeconds": process["wallSeconds"]}))


if __name__ == "__main__":
    main()
