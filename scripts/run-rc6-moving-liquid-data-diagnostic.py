#!/usr/bin/env python3
"""Run one bounded Data-only FLIP-particle diagnosis on attempt-56 physics."""

import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-moving-liquid-data-diagnostic-attempt-57")
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-data-diagnostic-attempt-57"
BINARY = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC5-2026-09-01-attempt-01/build/bin/Film Studio Engine F0.app/Contents/MacOS/Blender")
SOURCE = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-final-effector-mesh-c3-attempt-46/final-effector-mesh-c3/source-state.blend")
TRAJECTORY = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-slow-tip-bullet-screen-c5-c3-attempt-55/cells/C5F96/result.json"
RETAINED56_WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-moving-liquid-preview-attempt-56")
RETAINED56_EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-preview-attempt-56"
SCENE_TOOL = RESEARCH / "scripts/run-rc6-moving-liquid-data-diagnostic-scene.py"
AUDITOR = RESEARCH / "scripts/audit-rc6-moving-liquid-data-diagnostic.py"
SPEC = RESEARCH / "specs/ai-native-studio-rc6-moving-liquid-data-diagnostic.v0.68.json"


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
    raise RuntimeError("moving-liquid Data diagnostic spec self hash mismatch")
tools = {row["uri"]: row["sha256"] for row in spec["tools"]}
for tool in (SCENE_TOOL, Path(__file__).resolve(), AUDITOR):
    relative = str(tool.relative_to(RESEARCH))
    if tools.get(relative) != sha(tool):
        raise RuntimeError(f"moving-liquid Data diagnostic tool identity mismatch: {relative}")
if subprocess.run(["git", "status", "--porcelain"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout:
    raise RuntimeError("moving-liquid Data diagnostic research worktree is not clean")
if WORK.exists() or EVIDENCE.exists():
    raise RuntimeError("moving-liquid Data diagnostic roots are not fresh")
for path, expected in (
    (BINARY, spec["baseline"]["binarySha256"]),
    (SOURCE, spec["baseline"]["sourceBlendSha256"]),
    (TRAJECTORY, spec["baseline"]["trajectoryFileSha256"]),
    (RETAINED56_EVIDENCE / "result.json", spec["retainedAttempt56"]["resultFileSha256"]),
    (RETAINED56_EVIDENCE / "failure-receipt-c1.json", spec["retainedAttempt56"]["failureReceiptFileSha256"]),
    (RETAINED56_EVIDENCE / "independent-audit-c1.json", spec["retainedAttempt56"]["failureAuditFileSha256"]),
):
    if sha(path) != expected:
        raise RuntimeError(f"moving-liquid Data diagnostic baseline mismatch: {path}")
retained_manifest_before = manifest(RETAINED56_WORK)
if retained_manifest_before["manifestHash"] != spec["retainedAttempt56"]["workManifestHash"]:
    raise RuntimeError("moving-liquid Data diagnostic retained attempt-56 work drift")
free = shutil.disk_usage(WORK.parent).free
if free < spec["resourceCeilings"]["minimumReserveBytes"] + spec["resourceCeilings"]["projectedWriteBytes"]:
    raise RuntimeError("moving-liquid Data diagnostic disk admission failed")

WORK.mkdir(parents=True, exist_ok=False)
EVIDENCE.mkdir(parents=True, exist_ok=False)
for path in (EVIDENCE / "logs", EVIDENCE / "processes"):
    path.mkdir(parents=True, exist_ok=False)
source_copy = WORK / "source-state-copy.blend"
shutil.copy2(SOURCE, source_copy)
write_exclusive(
    EVIDENCE / "admission.json",
    {
        "schemaVersion": "bfs.rc6MovingLiquidDataDiagnosticAdmission.v0.1",
        "status": "PASS",
        "workRootAbsentBeforeRun": True,
        "evidenceRootAbsentBeforeRun": True,
        "freeBytes": free,
        "projectedWriteBytes": spec["resourceCeilings"]["projectedWriteBytes"],
        "reserveBytes": spec["resourceCeilings"]["minimumReserveBytes"],
        "sourceCopySha256": sha(source_copy),
        "retainedAttempt56WorkManifestBefore": retained_manifest_before["manifestHash"],
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
stdout_path = EVIDENCE / "logs/01-moving-liquid-data-diagnostic.stdout.log"
stderr_path = EVIDENCE / "logs/01-moving-liquid-data-diagnostic.stderr.log"
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
write_exclusive(EVIDENCE / "processes/01-moving-liquid-data-diagnostic.json", process)
result_path = EVIDENCE / "result.json"
marker = "RC6_MOVING_LIQUID_DATA_DIAGNOSTIC="
if not result_path.is_file() or marker not in completed.stdout:
    failure = {
        "schemaVersion": "bfs.rc6MovingLiquidDataDiagnosticFailure.v0.1",
        "status": "FAIL_EXECUTION",
        "message": "Data diagnostic process stopped before explicit self-hashed result",
        "processHash": process["processHash"],
        "counts": {"blenderStarts": 1, "bulletBakes": 1, "fluidDataBakes": 1, "fluidMeshBakes": 0, "renders": 0, "blendSaves": 0, "networkCalls": 0, "engineRemoteWrites": 0},
    }
    failure["failureHash"] = self_hash(failure, "failureHash")
    write_exclusive(EVIDENCE / "failure.json", failure)
    raise RuntimeError("moving-liquid Data diagnostic stopped before result")
result = json.loads(result_path.read_text())
if result["resultHash"] != self_hash(result, "resultHash") or result["status"] != "MEASURED_DATA_ONLY":
    raise RuntimeError("moving-liquid Data diagnostic result identity/status mismatch")
if completed.returncode != 0:
    raise RuntimeError("moving-liquid Data diagnostic Blender process nonzero")
retained_manifest_after = manifest(RETAINED56_WORK)
retained_exact = retained_manifest_after["manifestHash"] == retained_manifest_before["manifestHash"]
receipt = {
    "schemaVersion": "bfs.rc6MovingLiquidDataDiagnosticReceipt.v0.1",
    "status": "PASS_DIAGNOSTIC",
    "classification": result["classification"],
    "resultHash": result["resultHash"],
    "processHash": process["processHash"],
    "retainedAttempt56WorkManifestBefore": retained_manifest_before["manifestHash"],
    "retainedAttempt56WorkManifestAfter": retained_manifest_after["manifestHash"],
    "retainedAttempt56Unchanged": retained_exact,
    "counts": result["counts"],
    "resources": {
        "freeBytesAtAdmission": free,
        "processWallSeconds": round(wall_seconds, 6),
        "workBytesBeforeManifest": tree_bytes(WORK),
        "evidenceBytesBeforeReceipt": tree_bytes(EVIDENCE),
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
    raise RuntimeError("moving-liquid Data diagnostic independent audit failed")
write_exclusive(EVIDENCE / "evidence-manifest.json", manifest(EVIDENCE))
print("RC6_MOVING_LIQUID_DATA_DIAGNOSTIC_RUN=" + canonical({"status": receipt["status"], "classification": receipt["classification"], "receiptHash": receipt["receiptHash"], "resultHash": result["resultHash"]}))
