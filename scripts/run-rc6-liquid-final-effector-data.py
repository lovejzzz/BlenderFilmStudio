#!/usr/bin/env python3
"""Run one Final-tier +1-cell effector Data bake against the retained baseline."""

import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-final-effector-data-attempt-42")
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-final-effector-data-attempt-42"
BINARY = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC5-2026-09-01-attempt-01/build/bin/Film Studio Engine F0.app/Contents/MacOS/Blender")
SOURCE_BLEND = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-01-feasibility-attempt-13/RC6_F1_BULLET_MANTAFLOW_CONSEQUENCE.blend")
BASELINE_RESULT = RESEARCH / "experiments/physical-richness/RC6-2026-09-01-flip-particle-detail-attempt-37/cells/axis-control/result.json"
BASELINE_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-01-flip-particle-detail-audit-c1-attempt-38/independent-audit-c1.json"
LOWER_TIER_RECEIPT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-obstacle-voxel-screen-c2-attempt-41/receipt.json"
LOWER_TIER_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-obstacle-voxel-screen-c2-attempt-41/independent-audit.json"
SCENE_TOOL = RESEARCH / "scripts/run-rc6-liquid-final-effector-data-scene.py"
RUNNER = Path(__file__).resolve()
AUDITOR = RESEARCH / "scripts/audit-rc6-liquid-final-effector-data.py"
SPEC = RESEARCH / "specs/ai-native-studio-rc6-liquid-final-effector-data.v0.44.json"
CELL_ID = "final-effector-plus1"
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
    return [{"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": sha(path)} for path in sorted(root.rglob("*")) if path.is_file() and not path.is_symlink()]


def manifest(root, exclusions=()):
    excluded = set(exclusions)
    files = [entry for entry in file_entries(root) if entry["path"] not in excluded]
    value = {"schemaVersion": "bfs.rootManifest.v0.1", "root": str(root), "files": files}
    value["manifestHash"] = self_hash(value, "manifestHash")
    return value


def tree_bytes(root):
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file() and not path.is_symlink())


def argv():
    return [
        str(BINARY), "--background", "--factory-startup", "--disable-autoexec", "--offline-mode",
        str(SOURCE_BLEND), "--python", str(SCENE_TOOL), "--",
        "--cell-id", CELL_ID, "--work-root", str(WORK), "--evidence-root", str(EVIDENCE),
        "--resolution", "192", "--effector-surface-distance", "2.5",
    ]


def main():
    if WORK.exists() or EVIDENCE.exists():
        raise RuntimeError("final-effector Data roots are not fresh")
    if subprocess.run(["git", "status", "--porcelain"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout:
        raise RuntimeError("research worktree must be clean before final-effector Data bake")
    spec = read_json(SPEC)
    if spec.get("status") != "FROZEN" or spec.get("specHash") != self_hash(spec, "specHash"):
        raise RuntimeError("final-effector Data spec identity mismatch")
    expected_tools = {
        str(SCENE_TOOL.relative_to(RESEARCH)): sha(SCENE_TOOL),
        str(RUNNER.relative_to(RESEARCH)): sha(RUNNER),
        str(AUDITOR.relative_to(RESEARCH)): sha(AUDITOR),
    }
    if spec.get("tools") != expected_tools:
        raise RuntimeError("final-effector Data tool roster mismatch")
    if sha(BINARY) != spec["inputs"]["binarySha256"] or sha(SOURCE_BLEND) != spec["inputs"]["sourceBlendSha256"]:
        raise RuntimeError("final-effector Data input identity mismatch")
    baseline = read_json(BASELINE_RESULT)
    baseline_audit = read_json(BASELINE_AUDIT)
    lower_tier_receipt = read_json(LOWER_TIER_RECEIPT)
    lower_tier_audit = read_json(LOWER_TIER_AUDIT)
    if sha(BASELINE_RESULT) != spec["retainedBaseline"]["resultFileSha256"] or baseline.get("resultHash") != spec["retainedBaseline"]["resultHash"]:
        raise RuntimeError("final-effector retained baseline result mismatch")
    if sha(BASELINE_AUDIT) != spec["retainedBaseline"]["auditFileSha256"] or baseline_audit.get("auditHash") != spec["retainedBaseline"]["auditHash"]:
        raise RuntimeError("final-effector retained baseline audit mismatch")
    if sha(LOWER_TIER_RECEIPT) != spec["lowerTierScreen"]["receiptFileSha256"] or lower_tier_receipt.get("receiptHash") != spec["lowerTierScreen"]["receiptHash"]:
        raise RuntimeError("final-effector lower-tier receipt mismatch")
    if sha(LOWER_TIER_AUDIT) != spec["lowerTierScreen"]["auditFileSha256"] or lower_tier_audit.get("auditHash") != spec["lowerTierScreen"]["auditHash"]:
        raise RuntimeError("final-effector lower-tier audit mismatch")
    if lower_tier_receipt.get("status") != spec["lowerTierScreen"]["status"] or lower_tier_audit.get("status") != "PASS" or lower_tier_audit.get("screenVerdict") != spec["lowerTierScreen"]["status"]:
        raise RuntimeError("final-effector lower-tier interpretation mismatch")

    ceilings = spec["resourceCeilings"]
    free_before = shutil.disk_usage(WORK.parent).free
    if free_before < ceilings["minimumFreeBytesBefore"] or free_before < ceilings["minimumFreeBytesAfter"] + ceilings["projectedWriteBytes"]:
        raise RuntimeError("final-effector Data resource admission failed")
    for root in (WORK, EVIDENCE):
        root.mkdir(parents=True, exist_ok=False)
    for root in (WORK / "user/config", WORK / "user/scripts", WORK / "user/datafiles", WORK / "user/extensions", EVIDENCE / "logs", EVIDENCE / "processes", EVIDENCE / "cells"):
        root.mkdir(parents=True, exist_ok=False)
    admission = {
        "schemaVersion": "bfs.rc6LiquidFinalEffectorDataAdmission.v0.1",
        "status": "PASS",
        "researchCommit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.strip(),
        "freeBytesBefore": free_before,
        "binarySha256": sha(BINARY),
        "sourceBlendSha256": sha(SOURCE_BLEND),
        "retainedBaselineResultHash": baseline["resultHash"],
        "retainedBaselineAuditHash": baseline_audit["auditHash"],
        "lowerTierReceiptHash": lower_tier_receipt["receiptHash"],
        "lowerTierAuditHash": lower_tier_audit["auditHash"],
        "specHash": spec["specHash"],
    }
    admission["admissionHash"] = self_hash(admission, "admissionHash")
    write_exclusive(EVIDENCE / "admission.json", admission)

    environment = dict(os.environ)
    environment.update({
        "BLENDER_USER_CONFIG": str(WORK / "user/config"), "BLENDER_USER_SCRIPTS": str(WORK / "user/scripts"),
        "BLENDER_USER_DATAFILES": str(WORK / "user/datafiles"), "BLENDER_USER_EXTENSIONS": str(WORK / "user/extensions"),
    })
    stdout_path = EVIDENCE / "logs/01-final-effector-plus1.stdout.log"
    stderr_path = EVIDENCE / "logs/01-final-effector-plus1.stderr.log"
    started = time.monotonic()
    with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
        done = subprocess.run(argv(), cwd=RESEARCH, env=environment, stdout=stdout, stderr=stderr, check=False)
    process = {
        "schemaVersion": "bfs.rc6LiquidFinalEffectorDataProcess.v0.1", "index": 1, "cellId": CELL_ID,
        "argv": argv(), "cwd": str(RESEARCH), "exitCode": done.returncode,
        "wallSeconds": round(time.monotonic() - started, 6), "stdoutSha256": sha(stdout_path), "stderrSha256": sha(stderr_path),
    }
    process["processHash"] = self_hash(process, "processHash")
    write_exclusive(EVIDENCE / "processes/01-final-effector-plus1.json", process)
    result_path = EVIDENCE / f"cells/{CELL_ID}/result.json"
    if done.returncode != 0 or stderr_path.stat().st_size != 0 or "RC6_FINAL_EFFECTOR_DATA=" not in stdout_path.read_text(encoding="utf-8", errors="replace") or not result_path.is_file():
        raise RuntimeError("final-effector Data Blender process failed")
    result = read_json(result_path)
    if result.get("status") != "MEASURED_DATA_ONLY" or result.get("cellId") != CELL_ID or result.get("resultHash") != self_hash(result, "resultHash"):
        raise RuntimeError("final-effector Data result identity mismatch")

    baseline_max = max(sample["aggregate"]["outsideUnionCount"] for sample in baseline["samples"])
    candidate_max = result["metrics"]["maximumOneVoxelOutlierCount"]
    status = "PASS_FINAL_SURFACE_DISTANCE_DATA_SIGNAL" if baseline_max == 9 and candidate_max == 0 else "FAIL_FINAL_SURFACE_DISTANCE_NO_CORRECTION"
    work_bytes = tree_bytes(WORK)
    evidence_bytes = tree_bytes(EVIDENCE)
    free_after = shutil.disk_usage(WORK.parent).free
    if work_bytes > ceilings["workBytes"] or evidence_bytes > ceilings["evidenceBytes"] or free_after < ceilings["minimumFreeBytesAfter"]:
        status = "FAIL_RESOURCE_CEILING"
    if any(path.is_symlink() for root in (WORK, EVIDENCE) for path in root.rglob("*")):
        status = "FAIL_SYMLINK"
    if any(path.is_file() and path.suffix.lower() in BANNED_MEDIA for root in (WORK, EVIDENCE) for path in root.rglob("*")):
        status = "FAIL_RENDER_MEDIA"
    receipt = {
        "schemaVersion": "bfs.rc6LiquidFinalEffectorDataReceipt.v0.1",
        "status": status,
        "retainedBaseline": {"resolutionMax": 192, "cupEffectorSurfaceDistanceCells": 1.5, "maximumOneVoxelOutlierCount": baseline_max, "resultHash": baseline["resultHash"], "auditHash": baseline_audit["auditHash"]},
        "candidate": {"resolutionMax": 192, "cupEffectorSurfaceDistanceCells": 2.5, "maximumOneVoxelOutlierCount": candidate_max, "maximumOneVoxelOutlierFraction": result["metrics"]["maximumOneVoxelOutlierFraction"], "framesWithOneVoxelOutliers": result["metrics"]["framesWithOneVoxelOutliers"], "maximumInteriorFloorPenetrationMeters": result["metrics"]["maximumInteriorFloorPenetrationMeters"], "resultHash": result["resultHash"]},
        "counts": {"blenderStarts": 1, "fluidDataBakes": 1, "fluidMeshBakes": 0, "blendSaves": 0, "renderCalls": 0, "networkCalls": 0, "engineRemoteWrites": 0},
        "processHash": process["processHash"],
        "resources": {"freeBytesBefore": free_before, "freeBytesAfter": free_after, "workBytes": work_bytes, "evidenceBytesBeforeReceipt": evidence_bytes},
        "nextGate": "mesh-only reconstruction confirmation" if status == "PASS_FINAL_SURFACE_DISTANCE_DATA_SIGNAL" else "cup topology, normals and transform audit",
        "claimCeiling": spec["claimCeiling"],
    }
    receipt["receiptHash"] = self_hash(receipt, "receiptHash")
    write_exclusive(EVIDENCE / "receipt.json", receipt)
    write_exclusive(EVIDENCE / "work-manifest.json", manifest(WORK))
    write_exclusive(EVIDENCE / "evidence-manifest.json", manifest(EVIDENCE, exclusions=("evidence-manifest.json", "independent-audit.json")))
    print("RC6_FINAL_EFFECTOR_DATA_RECEIPT=" + canonical({"status": status, "receiptHash": receipt["receiptHash"], "candidateOutliers": candidate_max}))


if __name__ == "__main__":
    main()
