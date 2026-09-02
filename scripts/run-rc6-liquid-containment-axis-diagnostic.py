#!/usr/bin/env python3
"""Copy one accepted-input liquid surface and run one zero-bake axis diagnosis."""

import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
SOURCE_WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-01-mesh-concavity-attempt-31")
SOURCE_EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-01-mesh-concavity-attempt-31"
SOURCE_CANDIDATE = SOURCE_WORK / "concavity-upper-3p50"
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-01-containment-axis-attempt-32")
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-01-containment-axis-attempt-32"
BINARY = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC5-2026-09-01-attempt-01/build/bin/Film Studio Engine F0.app/Contents/MacOS/Blender")
SCENE_TOOL = RESEARCH / "scripts/inspect-rc6-liquid-containment-axis-scene.py"
RUNNER = Path(__file__).resolve()
AUDITOR = RESEARCH / "scripts/audit-rc6-liquid-containment-axis-diagnostic.py"
SPEC = RESEARCH / "specs/ai-native-studio-rc6-liquid-containment-axis.v0.32.json"
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
        for path in sorted(root.rglob("*")) if path.is_file() and not path.is_symlink()
    ]


def manifest(root, exclusions=()):
    excluded = set(exclusions)
    files = [entry for entry in file_entries(root) if entry["path"] not in excluded]
    value = {"schemaVersion": "bfs.rootManifest.v0.1", "root": str(root), "files": files}
    value["manifestHash"] = self_hash(value, "manifestHash")
    return value


def tree_bytes(root):
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file() and not path.is_symlink())


def expected_argv(candidate_manifest_hash):
    return [
        str(BINARY), "--background", "--factory-startup", "--disable-autoexec", "--offline-mode",
        str(WORK / "axis-control/mesh-reconstructed-state.blend"), "--python", str(SCENE_TOOL), "--",
        "--work-root", str(WORK), "--evidence-root", str(EVIDENCE),
        "--retained-candidate-manifest-hash", candidate_manifest_hash,
    ]


def main():
    if WORK.exists() or EVIDENCE.exists():
        raise RuntimeError("containment-axis roots are not fresh")
    if subprocess.run(["git", "status", "--porcelain"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout:
        raise RuntimeError("research worktree must be clean before containment-axis diagnostic")
    spec = read_json(SPEC)
    if spec.get("status") != "FROZEN" or spec.get("specHash") != self_hash(spec, "specHash"):
        raise RuntimeError("containment-axis spec identity mismatch")
    expected_tools = {
        str(SCENE_TOOL.relative_to(RESEARCH)): sha(SCENE_TOOL),
        str(RUNNER.relative_to(RESEARCH)): sha(RUNNER),
        str(AUDITOR.relative_to(RESEARCH)): sha(AUDITOR),
    }
    if spec.get("tools") != expected_tools:
        raise RuntimeError("containment-axis tool roster mismatch")
    if sha(BINARY) != spec["inputs"]["binarySha256"]:
        raise RuntimeError("containment-axis binary identity mismatch")
    source_work_manifest = read_json(SOURCE_EVIDENCE / "work-manifest.json")
    if source_work_manifest != manifest(SOURCE_WORK) or sha(SOURCE_EVIDENCE / "work-manifest.json") != spec["inputs"]["sourceWorkManifestFileSha256"]:
        raise RuntimeError("containment-axis source work manifest mismatch")
    source_candidate_manifest = manifest(SOURCE_CANDIDATE)
    if source_candidate_manifest["manifestHash"] != spec["inputs"]["sourceCandidateManifestHash"]:
        raise RuntimeError("containment-axis source candidate manifest mismatch")
    if any(path.is_symlink() for path in SOURCE_WORK.rglob("*")):
        raise RuntimeError("containment-axis source work contains symlinks")

    ceilings = spec["resourceCeilings"]
    free_before = shutil.disk_usage(WORK.parent).free
    if free_before < ceilings["minimumFreeBytesBefore"] or free_before < ceilings["minimumFreeBytesAfter"] + ceilings["projectedWriteBytes"]:
        raise RuntimeError("containment-axis resource admission failed")
    WORK.mkdir(parents=True, exist_ok=False)
    EVIDENCE.mkdir(parents=True, exist_ok=False)
    for root in (WORK / "user/config", WORK / "user/scripts", WORK / "user/datafiles", WORK / "user/extensions", EVIDENCE / "logs", EVIDENCE / "processes", EVIDENCE / "cells"):
        root.mkdir(parents=True, exist_ok=False)
    copied_candidate = WORK / "axis-control"
    shutil.copytree(SOURCE_CANDIDATE, copied_candidate, symlinks=False)
    if file_entries(copied_candidate) != source_candidate_manifest["files"]:
        raise RuntimeError("containment-axis copied candidate mismatch")
    write_exclusive(EVIDENCE / "retained-candidate-manifest.json", source_candidate_manifest)
    admission = {
        "schemaVersion": "bfs.rc6LiquidContainmentAxisAdmission.v0.1",
        "status": "PASS",
        "researchCommit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.strip(),
        "freeBytesBefore": free_before,
        "binarySha256": sha(BINARY),
        "sourceWorkManifestHash": source_work_manifest["manifestHash"],
        "sourceCandidateManifestHash": source_candidate_manifest["manifestHash"],
        "specHash": spec["specHash"],
    }
    admission["admissionHash"] = self_hash(admission, "admissionHash")
    write_exclusive(EVIDENCE / "admission.json", admission)

    stdout_path = EVIDENCE / "logs/01-axis-control.stdout.log"
    stderr_path = EVIDENCE / "logs/01-axis-control.stderr.log"
    argv = expected_argv(source_candidate_manifest["manifestHash"])
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
        "schemaVersion": "bfs.rc6LiquidContainmentAxisProcess.v0.1",
        "index": 1,
        "cellId": "axis-control",
        "argv": argv,
        "cwd": str(RESEARCH),
        "exitCode": done.returncode,
        "wallSeconds": round(time.monotonic() - started, 6),
        "stdoutSha256": sha(stdout_path),
        "stderrSha256": sha(stderr_path),
    }
    process["processHash"] = self_hash(process, "processHash")
    write_exclusive(EVIDENCE / "processes/01-axis-control.json", process)
    result_path = EVIDENCE / "cells/axis-control/result.json"
    if done.returncode != 0 or stderr_path.stat().st_size != 0 or "RC6_CONTAINMENT_AXIS=" not in stdout_path.read_text(encoding="utf-8", errors="replace") or not result_path.is_file():
        raise RuntimeError("containment-axis Blender process failed")
    result = read_json(result_path)
    if result.get("status") != "MEASURED_READ_ONLY" or result.get("resultHash") != self_hash(result, "resultHash"):
        raise RuntimeError("containment-axis result identity mismatch")
    if result.get("retainedCandidateManifestHash") != source_candidate_manifest["manifestHash"] or [row.get("frame") for row in result.get("samples", [])] != list(range(1, 8)):
        raise RuntimeError("containment-axis result binding mismatch")
    if file_entries(copied_candidate) != source_candidate_manifest["files"] or manifest(SOURCE_WORK) != source_work_manifest:
        raise RuntimeError("containment-axis read-only invariants changed")

    peak_sample = max(result["samples"], key=lambda row: row["aggregate"]["outsideUnionFraction"])
    peak_aggregate = peak_sample["aggregate"]
    axis_counts = {
        "radial": peak_aggregate["radialCount"],
        "belowFloor": peak_aggregate["belowFloorCount"],
        "aboveRim": peak_aggregate["aboveRimCount"],
    }
    dominant_axis = max(axis_counts, key=axis_counts.get)
    dominant_share = axis_counts[dominant_axis] / peak_aggregate["outsideUnionCount"] if peak_aggregate["outsideUnionCount"] else 0.0

    work_bytes = tree_bytes(WORK)
    evidence_bytes = tree_bytes(EVIDENCE)
    forbidden_media = sorted(str(path) for root in (WORK, EVIDENCE) for path in root.rglob("*") if path.is_file() and path.suffix.lower() in BANNED_MEDIA)
    free_after = shutil.disk_usage(WORK.parent).free
    execution_pass = (
        work_bytes <= ceilings["workBytes"] and evidence_bytes <= ceilings["evidenceBytes"]
        and free_after >= ceilings["minimumFreeBytesAfter"] and not forbidden_media
    )
    receipt = {
        "schemaVersion": "bfs.rc6LiquidContainmentAxisReceipt.v0.1",
        "status": "PASS_EXECUTION" if execution_pass else "FAIL_EXECUTION",
        "diagnosticVerdict": "MEASURED_AXIS_CAUSE" if execution_pass else "UNINTERPRETABLE",
        "resultHash": result["resultHash"],
        "peakOutsideFrame": peak_sample["frame"],
        "peakOutsideUnionFraction": peak_aggregate["outsideUnionFraction"],
        "peakAxisCounts": axis_counts,
        "dominantAxis": dominant_axis,
        "dominantAxisShareOfOutsideUnion": round(dominant_share, 8),
        "counts": {"blenderStarts": 1, "fluidDataBakes": 0, "fluidMeshBakes": 0, "blendSaves": 0, "renderCalls": 0, "networkCalls": 0, "engineRemoteWrites": 0},
        "resources": {"freeBytesBefore": free_before, "freeBytesAfter": free_after, "workBytes": work_bytes, "evidenceBytesBeforeReceipt": evidence_bytes},
        "forbiddenMedia": forbidden_media,
        "claimCeiling": spec["claimCeiling"],
    }
    receipt["receiptHash"] = self_hash(receipt, "receiptHash")
    write_exclusive(EVIDENCE / "receipt.json", receipt)
    write_exclusive(EVIDENCE / "work-manifest.json", manifest(WORK))
    write_exclusive(EVIDENCE / "evidence-manifest.json", manifest(EVIDENCE, exclusions=("evidence-manifest.json", "independent-audit.json")))
    print("RC6_CONTAINMENT_AXIS_RECEIPT=" + canonical({"status": receipt["status"], "receiptHash": receipt["receiptHash"], "resultHash": receipt["resultHash"]}), flush=True)
    if not execution_pass:
        raise RuntimeError("containment-axis execution failed")


if __name__ == "__main__":
    main()
