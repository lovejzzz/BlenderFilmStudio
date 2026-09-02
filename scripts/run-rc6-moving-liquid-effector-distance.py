#!/usr/bin/env python3
"""Run one 24-frame moving-liquid test with only effector distance at 2.0."""

import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-moving-liquid-effector-distance-attempt-59")
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-effector-distance-attempt-59"
BINARY = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC5-2026-09-01-attempt-01/build/bin/Film Studio Engine F0.app/Contents/MacOS/Blender")
SOURCE = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-final-effector-mesh-c3-attempt-46/final-effector-mesh-c3/source-state.blend")
STATIC_CACHE = SOURCE.parent / "mantaflow-cache"
TRAJECTORY = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-slow-tip-bullet-screen-c5-c3-attempt-55/cells/C5F96/result.json"
ATTEMPT56 = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-preview-attempt-56/result.json"
ATTEMPT57_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-data-diagnostic-attempt-57/independent-audit.json"
ATTEMPT58_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-data-occupancy-attempt-58/independent-audit.json"
SCENE_TOOL = RESEARCH / "scripts/run-rc6-moving-liquid-effector-distance-scene.py"
AUDITOR = RESEARCH / "scripts/audit-rc6-moving-liquid-effector-distance.py"
SPEC = RESEARCH / "specs/ai-native-studio-rc6-moving-liquid-effector-distance.v0.70.json"


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


def manifest(root):
    rows = [
        {"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": sha(path)}
        for path in sorted(root.rglob("*"))
        if path.is_file()
    ]
    value = {"root": str(root), "files": rows}
    value["manifestHash"] = self_hash(value, "manifestHash")
    return value


def tree_bytes(root):
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())


spec = json.loads(SPEC.read_text())
if spec["specHash"] != self_hash(spec, "specHash"):
    raise RuntimeError("moving-liquid effector-distance spec self hash mismatch")
tools = {row["uri"]: row["sha256"] for row in spec["tools"]}
for tool in (SCENE_TOOL, Path(__file__).resolve(), AUDITOR):
    relative = str(tool.relative_to(RESEARCH))
    if tools.get(relative) != sha(tool):
        raise RuntimeError(f"moving-liquid effector-distance tool mismatch: {relative}")
if subprocess.run(["git", "status", "--porcelain"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout:
    raise RuntimeError("moving-liquid effector-distance research worktree is not clean")
if WORK.exists() or EVIDENCE.exists():
    raise RuntimeError("moving-liquid effector-distance roots are not fresh")
for path, expected in (
    (BINARY, spec["baseline"]["binarySha256"]),
    (SOURCE, spec["baseline"]["sourceBlendSha256"]),
    (TRAJECTORY, spec["baseline"]["trajectoryFileSha256"]),
    (ATTEMPT56, spec["baseline"]["attempt56ResultFileSha256"]),
    (ATTEMPT57_AUDIT, spec["baseline"]["attempt57AuditFileSha256"]),
    (ATTEMPT58_AUDIT, spec["baseline"]["attempt58AuditFileSha256"]),
):
    if sha(path) != expected:
        raise RuntimeError(f"moving-liquid effector-distance baseline mismatch: {path}")
static_before = manifest(STATIC_CACHE)
if static_before["manifestHash"] != spec["baseline"]["retainedStaticCacheManifestHash"]:
    raise RuntimeError("moving-liquid effector-distance static cache drift")
free = shutil.disk_usage(WORK.parent).free
if free < spec["resourceCeilings"]["minimumReserveBytes"] + spec["resourceCeilings"]["projectedWriteBytes"]:
    raise RuntimeError("moving-liquid effector-distance disk admission failed")

WORK.mkdir(parents=True, exist_ok=False)
EVIDENCE.mkdir(parents=True, exist_ok=False)
for path in (EVIDENCE / "logs", EVIDENCE / "processes"):
    path.mkdir(parents=True, exist_ok=False)
source_copy = WORK / "source-state-copy.blend"
shutil.copy2(SOURCE, source_copy)
write_exclusive(EVIDENCE / "admission.json", {"schemaVersion": "bfs.rc6MovingLiquidEffectorDistanceAdmission.v0.1", "status": "PASS", "workRootAbsentBeforeRun": True, "evidenceRootAbsentBeforeRun": True, "freeBytes": free, "sourceCopySha256": sha(source_copy), "retainedStaticCacheManifestBefore": static_before["manifestHash"]})
argv = [str(BINARY), "--background", str(source_copy), "--python", str(SCENE_TOOL), "--", "--work-root", str(WORK), "--evidence-root", str(EVIDENCE), "--trajectory-json", str(TRAJECTORY), "--source-copy", str(source_copy)]
started = time.monotonic()
completed = subprocess.run(argv, cwd=RESEARCH, capture_output=True, text=True)
wall_seconds = time.monotonic() - started
stdout_path = EVIDENCE / "logs/01-effector-distance.stdout.log"
stderr_path = EVIDENCE / "logs/01-effector-distance.stderr.log"
stdout_path.write_text(completed.stdout, encoding="utf-8")
stderr_path.write_text(completed.stderr, encoding="utf-8")
process = {"schemaVersion": "bfs.processReceipt.v0.1", "index": 1, "argv": argv, "cwd": str(RESEARCH), "exitCode": completed.returncode, "wallSeconds": round(wall_seconds, 6), "stdoutSha256": sha(stdout_path), "stderrSha256": sha(stderr_path)}
process["processHash"] = self_hash(process, "processHash")
write_exclusive(EVIDENCE / "processes/01-effector-distance.json", process)
result_path = EVIDENCE / "result.json"
if not result_path.is_file() or "RC6_MOVING_LIQUID_EFFECTOR_DISTANCE=" not in completed.stdout:
    failure = {"schemaVersion": "bfs.rc6MovingLiquidEffectorDistanceFailure.v0.1", "status": "FAIL_EXECUTION", "message": "process stopped before explicit physical result", "processHash": process["processHash"], "counts": {"blenderStarts": 1, "bulletBakes": 1, "fluidDataBakes": 1, "fluidMeshBakes": 1, "renders": 0, "blendSaves": 0, "networkCalls": 0, "engineRemoteWrites": 0}}
    failure["failureHash"] = self_hash(failure, "failureHash")
    write_exclusive(EVIDENCE / "failure.json", failure)
    raise RuntimeError("moving-liquid effector-distance process stopped before result")
result = json.loads(result_path.read_text())
if result["resultHash"] != self_hash(result, "resultHash") or result["status"] not in {"PASS", "FAIL"} or completed.returncode != 0:
    raise RuntimeError("moving-liquid effector-distance result/process identity mismatch")
static_after = manifest(STATIC_CACHE)
static_exact = static_after["manifestHash"] == static_before["manifestHash"]
overall_pass = result["status"] == "PASS" and static_exact
receipt = {
    "schemaVersion": "bfs.rc6MovingLiquidEffectorDistanceReceipt.v0.1",
    "status": "PASS" if overall_pass else "FAIL",
    "verdict": "PASS_MOVING_LIQUID_EFFECTOR_DISTANCE" if overall_pass else "FAIL_MOVING_LIQUID_EFFECTOR_DISTANCE",
    "resultHash": result["resultHash"],
    "processHash": process["processHash"],
    "blenderExitCode": completed.returncode,
    "blenderThresholdExceptionObserved": "moving-liquid Preview thresholds failed" in completed.stderr,
    "retainedStaticCacheManifestBefore": static_before["manifestHash"],
    "retainedStaticCacheManifestAfter": static_after["manifestHash"],
    "retainedStaticCacheUnchanged": static_exact,
    "counts": result["counts"],
    "resources": {"freeBytesAtAdmission": free, "processWallSeconds": round(wall_seconds, 6), "workBytesBeforeManifest": tree_bytes(WORK), "evidenceBytesBeforeReceipt": tree_bytes(EVIDENCE)},
    "claimCeiling": result["claimCeiling"],
}
receipt["receiptHash"] = self_hash(receipt, "receiptHash")
write_exclusive(EVIDENCE / "receipt.json", receipt)
write_exclusive(EVIDENCE / "work-manifest.json", manifest(WORK))
write_exclusive(EVIDENCE / "evidence-manifest.pre-audit.json", manifest(EVIDENCE))
audit = subprocess.run(["/usr/bin/python3", str(AUDITOR)], cwd=RESEARCH, capture_output=True, text=True)
(EVIDENCE / "logs/audit.stdout.log").write_text(audit.stdout, encoding="utf-8")
(EVIDENCE / "logs/audit.stderr.log").write_text(audit.stderr, encoding="utf-8")
if audit.returncode != 0:
    raise RuntimeError("moving-liquid effector-distance independent audit failed")
write_exclusive(EVIDENCE / "evidence-manifest.json", manifest(EVIDENCE))
print("RC6_MOVING_LIQUID_EFFECTOR_DISTANCE_RUN=" + canonical({"status": receipt["status"], "receiptHash": receipt["receiptHash"], "resultHash": result["resultHash"]}))
if receipt["status"] != "PASS":
    raise RuntimeError("moving-liquid effector-distance physical gate failed")
