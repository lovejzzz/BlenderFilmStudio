#!/usr/bin/env python3
"""Run one Mesh-only confirmation from copied accepted Final effector Data."""

import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
RETAINED_WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-final-effector-data-attempt-42")
RETAINED_EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-final-effector-data-attempt-42"
RETAINED_CACHE = RETAINED_WORK / "final-effector-plus1/mantaflow-cache"
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-final-effector-mesh-attempt-44")
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-final-effector-mesh-attempt-44"
BINARY = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC5-2026-09-01-attempt-01/build/bin/Film Studio Engine F0.app/Contents/MacOS/Blender")
SOURCE_BLEND = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-01-feasibility-attempt-13/RC6_F1_BULLET_MANTAFLOW_CONSEQUENCE.blend")
SCENE_TOOL = RESEARCH / "scripts/run-rc6-liquid-final-effector-mesh-scene.py"
RUNNER = Path(__file__).resolve()
AUDITOR = RESEARCH / "scripts/audit-rc6-liquid-final-effector-mesh.py"
SPEC = RESEARCH / "specs/ai-native-studio-rc6-liquid-final-effector-mesh-tool-freeze.v0.48.json"
CELL_ID = "final-effector-mesh"
BANNED_MEDIA = {".exr", ".png", ".jpg", ".jpeg", ".mov", ".mp4"}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def self_hash(value, field):
    body = dict(value); body.pop(field, None)
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
        json.dump(value, handle, indent=2, sort_keys=True); handle.write("\n")


def manifest(root, exclusions=()):
    excluded = set(exclusions)
    files = [{"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": sha(path)} for path in sorted(root.rglob("*")) if path.is_file() and not path.is_symlink() and str(path.relative_to(root)) not in excluded]
    value = {"schemaVersion": "bfs.rootManifest.v0.1", "root": str(root), "files": files}
    value["manifestHash"] = self_hash(value, "manifestHash")
    return value


def expected_data_files():
    return sorted([f"config/config_{frame:04d}.uni" for frame in range(1, 8)] + [f"data/fluid_data_{frame:04d}.vdb" for frame in range(1, 8)])


def expected_all_files():
    return sorted(expected_data_files() + [f"mesh/fluid_mesh_{frame:04d}.bobj.gz" for frame in range(1, 8)])


def cache_roster(root):
    return sorted(str(path.relative_to(root)) for path in root.rglob("*") if path.is_file())


def data_manifest(root):
    files = []
    for relative in expected_data_files():
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"Final effector Mesh Data file missing or symlinked: {relative}")
        files.append({"path": relative, "bytes": path.stat().st_size, "sha256": sha(path)})
    value = {"schemaVersion": "bfs.rc6LiquidDataManifest.v0.1", "files": files}
    value["manifestHash"] = self_hash(value, "manifestHash")
    return value


def tree_bytes(root):
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file() and not path.is_symlink())


def expected_argv():
    return [str(BINARY), "--background", "--factory-startup", "--disable-autoexec", "--offline-mode", str(WORK / CELL_ID / "source-state.blend"), "--python", str(SCENE_TOOL), "--", "--cell-id", CELL_ID, "--work-root", str(WORK), "--evidence-root", str(EVIDENCE), "--mesh-particle-radius", "9.0", "--retained-data-manifest-hash", RETAINED_DATA_HASH]


def signed_topology_passes(result, thresholds):
    for sample in result["samples"]:
        positive = [item for item in sample["components"] if item["signedVolumeCubicMeters"] > 1e-12]
        negative = [item for item in sample["components"] if item["signedVolumeCubicMeters"] < -1e-12]
        if len(positive) != thresholds["requiredPositiveWaterBodiesPerFrame"] or len(negative) > thresholds["maximumNegativeNestedShellCount"] or any(item["nonManifoldEdgeCount"] for item in sample["components"]):
            return False
        outer = positive[0]
        for inner in negative:
            if any(inner["boundsMinWorld"][axis] < outer["boundsMinWorld"][axis] - 1e-7 or inner["boundsMaxWorld"][axis] > outer["boundsMaxWorld"][axis] + 1e-7 for axis in range(3)):
                return False
            separation = sum((inner["centroidWorld"][axis] - outer["centroidWorld"][axis]) ** 2 for axis in range(3)) ** 0.5
            if separation > thresholds["maximumNestedCentroidSeparationMeters"]:
                return False
    return True


def scientific_passes(result, thresholds):
    metrics = result["metrics"]
    return metrics["maximumAbsoluteSourceVolumeErrorFraction"] <= thresholds["maximumAbsoluteSourceVolumeErrorFraction"] and metrics["maximumAbsoluteVolumeDriftFraction"] <= thresholds["maximumAbsoluteTemporalDriftFraction"] and metrics["maximumOutsideCupInteriorPlusOneVoxelFraction"] <= thresholds["maximumOutsideCupInteriorPlusOneVoxelFraction"] and metrics["maximumNonManifoldEdgeCount"] == thresholds["maximumNonManifoldEdgeCount"] and signed_topology_passes(result, thresholds)


RETAINED_DATA_HASH = data_manifest(RETAINED_CACHE)["manifestHash"] if RETAINED_CACHE.is_dir() else ""


def main():
    if WORK.exists() or EVIDENCE.exists():
        raise RuntimeError("Final effector Mesh roots are not fresh")
    if subprocess.run(["git", "status", "--porcelain"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout:
        raise RuntimeError("research worktree must be clean before Final effector Mesh")
    spec = read_json(SPEC)
    if spec.get("status") != "FROZEN" or spec.get("specHash") != self_hash(spec, "specHash"):
        raise RuntimeError("Final effector Mesh spec identity mismatch")
    if spec.get("tools") != {str(SCENE_TOOL.relative_to(RESEARCH)): sha(SCENE_TOOL), str(RUNNER.relative_to(RESEARCH)): sha(RUNNER), str(AUDITOR.relative_to(RESEARCH)): sha(AUDITOR)}:
        raise RuntimeError("Final effector Mesh tool roster mismatch")
    if sha(BINARY) != spec["inputs"]["binarySha256"] or sha(SOURCE_BLEND) != spec["inputs"]["sourceBlendSha256"]:
        raise RuntimeError("Final effector Mesh input identity mismatch")
    retained_work_manifest = read_json(RETAINED_EVIDENCE / "work-manifest.json")
    retained_receipt = read_json(RETAINED_EVIDENCE / "receipt.json")
    retained_audit = read_json(RETAINED_EVIDENCE / "independent-audit.json")
    if manifest(RETAINED_WORK) != retained_work_manifest or sha(RETAINED_EVIDENCE / "work-manifest.json") != spec["inputs"]["retainedWorkManifestFileSha256"] or retained_work_manifest.get("manifestHash") != spec["inputs"]["retainedWorkManifestHash"]:
        raise RuntimeError("Final effector Mesh retained work mismatch")
    if sha(RETAINED_EVIDENCE / "receipt.json") != spec["inputs"]["retainedReceiptFileSha256"] or retained_receipt.get("receiptHash") != spec["inputs"]["retainedReceiptHash"] or sha(RETAINED_EVIDENCE / "independent-audit.json") != spec["inputs"]["retainedAuditFileSha256"] or retained_audit.get("auditHash") != spec["inputs"]["retainedAuditHash"] or retained_audit.get("status") != "PASS":
        raise RuntimeError("Final effector Mesh retained evidence mismatch")
    retained_data = data_manifest(RETAINED_CACHE)
    if retained_data["manifestHash"] != RETAINED_DATA_HASH or RETAINED_DATA_HASH != spec["inputs"]["retainedDataManifestHash"] or cache_roster(RETAINED_CACHE) != expected_data_files():
        raise RuntimeError("Final effector Mesh retained Data mismatch")
    ceilings = spec["resourceCeilings"]
    free_before = shutil.disk_usage(WORK.parent).free
    if free_before < ceilings["minimumFreeBytesBefore"] or free_before < ceilings["minimumFreeBytesAfter"] + ceilings["projectedWriteBytes"]:
        raise RuntimeError("Final effector Mesh resource admission failed")
    for root in (WORK, EVIDENCE):
        root.mkdir(parents=True, exist_ok=False)
    for root in (WORK / "user/config", WORK / "user/scripts", WORK / "user/datafiles", WORK / "user/extensions", EVIDENCE / "logs", EVIDENCE / "processes", EVIDENCE / "cells"):
        root.mkdir(parents=True, exist_ok=False)
    cell_root = WORK / CELL_ID
    cell_root.mkdir(parents=True, exist_ok=False)
    shutil.copy2(SOURCE_BLEND, cell_root / "source-state.blend")
    shutil.copytree(RETAINED_CACHE, cell_root / "mantaflow-cache", symlinks=False)
    if sha(cell_root / "source-state.blend") != sha(SOURCE_BLEND) or data_manifest(cell_root / "mantaflow-cache") != retained_data:
        raise RuntimeError("Final effector Mesh copy identity mismatch")
    write_exclusive(EVIDENCE / "retained-data-manifest.json", retained_data)
    admission = {"schemaVersion": "bfs.rc6LiquidFinalEffectorMeshAdmission.v0.1", "status": "PASS", "researchCommit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.strip(), "freeBytesBefore": free_before, "binarySha256": sha(BINARY), "sourceBlendSha256": sha(SOURCE_BLEND), "retainedWorkManifestHash": retained_work_manifest["manifestHash"], "retainedReceiptHash": retained_receipt["receiptHash"], "retainedAuditHash": retained_audit["auditHash"], "retainedDataManifestHash": RETAINED_DATA_HASH, "specHash": spec["specHash"]}
    admission["admissionHash"] = self_hash(admission, "admissionHash")
    write_exclusive(EVIDENCE / "admission.json", admission)
    environment = dict(os.environ)
    environment.update({"BLENDER_USER_CONFIG": str(WORK / "user/config"), "BLENDER_USER_SCRIPTS": str(WORK / "user/scripts"), "BLENDER_USER_DATAFILES": str(WORK / "user/datafiles"), "BLENDER_USER_EXTENSIONS": str(WORK / "user/extensions")})
    stdout_path = EVIDENCE / "logs/01-final-effector-mesh.stdout.log"
    stderr_path = EVIDENCE / "logs/01-final-effector-mesh.stderr.log"
    started = time.monotonic()
    with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
        done = subprocess.run(expected_argv(), cwd=RESEARCH, env=environment, stdout=stdout, stderr=stderr, check=False)
    process = {"schemaVersion": "bfs.rc6LiquidFinalEffectorMeshProcess.v0.1", "index": 1, "cellId": CELL_ID, "argv": expected_argv(), "cwd": str(RESEARCH), "exitCode": done.returncode, "wallSeconds": round(time.monotonic() - started, 6), "stdoutSha256": sha(stdout_path), "stderrSha256": sha(stderr_path)}
    process["processHash"] = self_hash(process, "processHash")
    write_exclusive(EVIDENCE / "processes/01-final-effector-mesh.json", process)
    result_path = EVIDENCE / f"cells/{CELL_ID}/result.json"
    if done.returncode != 0 or stderr_path.stat().st_size != 0 or "RC6_FINAL_EFFECTOR_MESH=" not in stdout_path.read_text(encoding="utf-8", errors="replace") or not result_path.is_file():
        raise RuntimeError("Final effector Mesh Blender process failed")
    result = read_json(result_path)
    if result.get("schemaVersion") != "bfs.rc6LiquidFinalEffectorMeshCell.v0.1" or result.get("status") != "MEASURED" or result.get("cellId") != CELL_ID or result.get("resultHash") != self_hash(result, "resultHash"):
        raise RuntimeError("Final effector Mesh result identity mismatch")
    copied_cache = cell_root / "mantaflow-cache"
    if data_manifest(copied_cache) != retained_data or cache_roster(copied_cache) != expected_all_files():
        raise RuntimeError("Final effector Mesh changed Data or cache roster")
    thresholds = spec["acceptanceThresholds"]
    status = "PASS_FINAL_EFFECTOR_MESH_STATIC" if scientific_passes(result, thresholds) else "FAIL_FINAL_EFFECTOR_MESH_STATIC"
    work_bytes = tree_bytes(WORK); evidence_bytes = tree_bytes(EVIDENCE); free_after = shutil.disk_usage(WORK.parent).free
    if work_bytes > ceilings["workBytes"] or evidence_bytes > ceilings["evidenceBytes"] or free_after < ceilings["minimumFreeBytesAfter"]:
        status = "FAIL_RESOURCE_CEILING"
    if any(path.is_symlink() for root in (WORK, EVIDENCE) for path in root.rglob("*")):
        status = "FAIL_SYMLINK"
    if any(path.is_file() and path.suffix.lower() in BANNED_MEDIA for root in (WORK, EVIDENCE) for path in root.rglob("*")):
        status = "FAIL_RENDER_MEDIA"
    receipt = {"schemaVersion": "bfs.rc6LiquidFinalEffectorMeshReceipt.v0.1", "status": status, "slowTipUnlocked": status == "PASS_FINAL_EFFECTOR_MESH_STATIC", "resultHash": result["resultHash"], "metrics": result["metrics"], "signedTopologyPass": signed_topology_passes(result, thresholds), "counts": {"blenderStarts": 1, "fluidDataBakes": 0, "fluidMeshBakes": 1, "blendSaves": 1, "renderCalls": 0, "networkCalls": 0, "engineRemoteWrites": 0}, "processHash": process["processHash"], "retainedDataManifestHash": RETAINED_DATA_HASH, "resources": {"freeBytesBefore": free_before, "freeBytesAfter": free_after, "workBytes": work_bytes, "evidenceBytesBeforeReceipt": evidence_bytes}, "nextGate": "slow solver-owned tip" if status == "PASS_FINAL_EFFECTOR_MESH_STATIC" else "surface/obstacle interaction diagnosis", "claimCeiling": spec["claimCeiling"]}
    receipt["receiptHash"] = self_hash(receipt, "receiptHash")
    write_exclusive(EVIDENCE / "receipt.json", receipt)
    write_exclusive(EVIDENCE / "work-manifest.json", manifest(WORK))
    write_exclusive(EVIDENCE / "evidence-manifest.json", manifest(EVIDENCE, exclusions=("evidence-manifest.json", "independent-audit.json")))
    print("RC6_FINAL_EFFECTOR_MESH_RECEIPT=" + canonical({"status": status, "slowTipUnlocked": receipt["slowTipUnlocked"], "receiptHash": receipt["receiptHash"], "metrics": result["metrics"]}))


if __name__ == "__main__":
    main()
