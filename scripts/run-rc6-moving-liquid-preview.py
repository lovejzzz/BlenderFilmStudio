#!/usr/bin/env python3
"""Run one bounded RC6 moving-liquid Preview gate on C5F96."""

import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-moving-liquid-preview-attempt-56")
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-preview-attempt-56"
BINARY = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC5-2026-09-01-attempt-01/build/bin/Film Studio Engine F0.app/Contents/MacOS/Blender")
SOURCE = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-final-effector-mesh-c3-attempt-46/final-effector-mesh-c3/source-state.blend")
RETAINED_CACHE = SOURCE.parent / "mantaflow-cache"
TRAJECTORY = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-slow-tip-bullet-screen-c5-c3-attempt-55/cells/C5F96/result.json"
SCENE_TOOL = RESEARCH / "scripts/run-rc6-moving-liquid-preview-scene.py"
AUDITOR = RESEARCH / "scripts/audit-rc6-moving-liquid-preview.py"
SPEC = RESEARCH / "specs/ai-native-studio-rc6-moving-liquid-preview.v0.66.json"
EXPECTED_BINARY_SHA256 = "ad08b54132b75325a12580f705fdefc205dd4444a36f2491e4d8a200e1091ef2"
EXPECTED_SOURCE_SHA256 = "9ac79c9c3c0d13273ac20804a3af99884f9465534800c3d9ca2ae8121499e644"
EXPECTED_TRAJECTORY_SHA256 = "00193b1a1258814f5a0a5b7a2308686f9f7daa0826f554af62c55e7de38fb261"
EXPECTED_RETAINED_CACHE_MANIFEST = "53bc19e1532b64ea8c37b0cc5fa52347c72c73023728d3705d45c063d5b7c265"


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
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())


def manifest(root):
    rows = [
        {"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": sha(path)}
        for path in sorted(root.rglob("*"))
        if path.is_file()
    ]
    value = {"root": str(root), "files": rows}
    value["manifestHash"] = self_hash(value, "manifestHash")
    return value


def retained_cache_manifest():
    rows = [
        {"path": str(path.relative_to(RETAINED_CACHE)), "bytes": path.stat().st_size, "sha256": sha(path)}
        for path in sorted(RETAINED_CACHE.rglob("*"))
        if path.is_file()
    ]
    value = {"root": str(RETAINED_CACHE), "files": rows}
    return self_hash(value, "manifestHash"), len(rows), sum(row["bytes"] for row in rows)


spec = json.loads(SPEC.read_text()) if SPEC.is_file() else None
if spec is None or spec.get("specHash") != self_hash(spec, "specHash"):
    raise RuntimeError("moving-liquid Preview spec self hash mismatch")
expected_tools = {row["uri"]: row["sha256"] for row in spec["tools"]}
for tool in (SCENE_TOOL, Path(__file__).resolve(), AUDITOR):
    relative = str(tool.relative_to(RESEARCH))
    if expected_tools.get(relative) != sha(tool):
        raise RuntimeError(f"moving-liquid Preview tool identity mismatch: {relative}")
if subprocess.run(["git", "status", "--porcelain"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout:
    raise RuntimeError("moving-liquid Preview research worktree is not clean")
if WORK.exists() or EVIDENCE.exists():
    raise RuntimeError("moving-liquid Preview roots are not fresh")
if sha(BINARY) != EXPECTED_BINARY_SHA256 or sha(SOURCE) != EXPECTED_SOURCE_SHA256 or sha(TRAJECTORY) != EXPECTED_TRAJECTORY_SHA256:
    raise RuntimeError("moving-liquid Preview binary, source or trajectory identity mismatch")
retained_before, retained_files, retained_bytes = retained_cache_manifest()
if retained_before != EXPECTED_RETAINED_CACHE_MANIFEST or retained_files != 21 or retained_bytes != 31537894:
    raise RuntimeError("moving-liquid Preview retained static cache identity mismatch")
free = shutil.disk_usage(WORK.parent).free
projected = 2147483648
reserve = 107374182400
if free < projected + reserve:
    raise RuntimeError("moving-liquid Preview disk admission failed")

WORK.mkdir(parents=True, exist_ok=False)
EVIDENCE.mkdir(parents=True, exist_ok=False)
for path in (EVIDENCE / "logs", EVIDENCE / "processes"):
    path.mkdir(parents=True, exist_ok=False)
source_copy = WORK / "source-state-copy.blend"
shutil.copy2(SOURCE, source_copy)
if sha(source_copy) != EXPECTED_SOURCE_SHA256:
    raise RuntimeError("moving-liquid Preview source copy mismatch")
write_exclusive(
    EVIDENCE / "admission.json",
    {
        "schemaVersion": "bfs.rc6MovingLiquidPreviewAdmission.v0.1",
        "status": "PASS",
        "workRootAbsentBeforeRun": True,
        "evidenceRootAbsentBeforeRun": True,
        "freeBytes": free,
        "projectedWriteBytes": projected,
        "reserveBytes": reserve,
        "binarySha256": EXPECTED_BINARY_SHA256,
        "sourceSha256": EXPECTED_SOURCE_SHA256,
        "trajectorySha256": EXPECTED_TRAJECTORY_SHA256,
        "retainedCacheManifestBefore": retained_before,
    },
)

argv = [
    str(BINARY),
    "--background",
    str(source_copy),
    "--python",
    str(SCENE_TOOL),
    "--",
    "--work-root",
    str(WORK),
    "--evidence-root",
    str(EVIDENCE),
    "--trajectory-json",
    str(TRAJECTORY),
    "--source-copy",
    str(source_copy),
]
started = time.monotonic()
completed = subprocess.run(argv, cwd=RESEARCH, capture_output=True, text=True)
wall_seconds = time.monotonic() - started
stdout_path = EVIDENCE / "logs/01-moving-liquid-preview.stdout.log"
stderr_path = EVIDENCE / "logs/01-moving-liquid-preview.stderr.log"
stdout_path.write_text(completed.stdout, encoding="utf-8")
stderr_path.write_text(completed.stderr, encoding="utf-8")
process = {
    "schemaVersion": "bfs.processReceipt.v0.1",
    "index": 1,
    "argv": argv,
    "cwd": str(RESEARCH),
    "exitCode": completed.returncode,
    "wallSeconds": round(wall_seconds, 6),
    "stdoutSha256": sha(stdout_path),
    "stderrSha256": sha(stderr_path),
}
process["processHash"] = self_hash(process, "processHash")
write_exclusive(EVIDENCE / "processes/01-moving-liquid-preview.json", process)
result_path = EVIDENCE / "result.json"
marker = "RC6_MOVING_LIQUID_PREVIEW="
if not result_path.is_file() or marker not in completed.stdout:
    failure = {
        "schemaVersion": "bfs.rc6MovingLiquidPreviewFailure.v0.1",
        "status": "FAIL_EXECUTION",
        "message": "moving-liquid Preview process stopped before a self-hashed physical result",
        "processHash": process["processHash"],
        "counts": {"blenderStarts": 1, "renders": 0, "blendSaves": 0, "networkCalls": 0, "engineRemoteWrites": 0},
    }
    failure["failureHash"] = self_hash(failure, "failureHash")
    write_exclusive(EVIDENCE / "failure.json", failure)
    raise RuntimeError("moving-liquid Preview process failed before result")
result = json.loads(result_path.read_text())
if result["resultHash"] != self_hash(result, "resultHash"):
    raise RuntimeError("moving-liquid Preview result self hash mismatch")
expected_exit = 0 if result["status"] == "PASS" else 1
if completed.returncode != expected_exit:
    raise RuntimeError("moving-liquid Preview result/process status mismatch")
retained_after, retained_after_files, retained_after_bytes = retained_cache_manifest()
retained_exact = (retained_after, retained_after_files, retained_after_bytes) == (retained_before, retained_files, retained_bytes)
overall_pass = result["status"] == "PASS" and retained_exact
receipt = {
    "schemaVersion": "bfs.rc6MovingLiquidPreviewReceipt.v0.1",
    "status": "PASS" if overall_pass else "FAIL",
    "verdict": "PASS_MOVING_LIQUID_PREVIEW" if overall_pass else "FAIL_MOVING_LIQUID_PREVIEW",
    "resultHash": result["resultHash"],
    "processHash": process["processHash"],
    "retainedStaticCacheManifestBefore": retained_before,
    "retainedStaticCacheManifestAfter": retained_after,
    "retainedStaticCacheUnchanged": retained_exact,
    "counts": result["counts"],
    "resources": {
        "freeBytesAtAdmission": free,
        "workBytesBeforeManifest": tree_bytes(WORK),
        "evidenceBytesBeforeReceipt": tree_bytes(EVIDENCE),
        "processWallSeconds": round(wall_seconds, 6),
    },
    "claimCeiling": result["claimCeiling"],
}
receipt["receiptHash"] = self_hash(receipt, "receiptHash")
write_exclusive(EVIDENCE / "receipt.json", receipt)
write_exclusive(WORK / "work-manifest.json", manifest(WORK))
write_exclusive(EVIDENCE / "evidence-manifest.pre-audit.json", manifest(EVIDENCE))
audit = subprocess.run(["/usr/bin/python3", str(AUDITOR)], cwd=RESEARCH, capture_output=True, text=True)
(EVIDENCE / "logs/audit.stdout.log").write_text(audit.stdout, encoding="utf-8")
(EVIDENCE / "logs/audit.stderr.log").write_text(audit.stderr, encoding="utf-8")
if audit.returncode != 0:
    raise RuntimeError("moving-liquid Preview independent audit failed")
write_exclusive(EVIDENCE / "evidence-manifest.json", manifest(EVIDENCE))
print("RC6_MOVING_LIQUID_PREVIEW_RUN=" + canonical({"status": receipt["status"], "receiptHash": receipt["receiptHash"], "resultHash": result["resultHash"]}))
if receipt["status"] != "PASS":
    raise RuntimeError("moving-liquid Preview physical gate failed")
