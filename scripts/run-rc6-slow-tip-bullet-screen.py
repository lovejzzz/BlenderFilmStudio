#!/usr/bin/env python3
"""Run the frozen four-cell Bullet-only slow-tip screen."""

import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-slow-tip-bullet-screen-attempt-47")
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-slow-tip-bullet-screen-attempt-47"
BINARY = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC5-2026-09-01-attempt-01/build/bin/Film Studio Engine F0.app/Contents/MacOS/Blender")
SOURCE = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-final-effector-mesh-c3-attempt-46/final-effector-mesh-c3/source-state.blend")
SCENE_TOOL = RESEARCH / "scripts/run-rc6-slow-tip-bullet-screen-scene.py"
AUDITOR = RESEARCH / "scripts/audit-rc6-slow-tip-bullet-screen.py"
SPEC = RESEARCH / "specs/ai-native-studio-rc6-slow-tip-bullet-screen.v0.55.json"
CELLS = (("D12", 12), ("D16", 16), ("D20", 20), ("D24", 24))
EXPECTED_BINARY_SHA256 = "ad08b54132b75325a12580f705fdefc205dd4444a36f2491e4d8a200e1091ef2"
EXPECTED_SOURCE_SHA256 = "9ac79c9c3c0d13273ac20804a3af99884f9465534800c3d9ca2ae8121499e644"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def self_hash(value, field):
    body = dict(value)
    body.pop(field, None)
    return hashlib.sha256(canonical(body).encode()).hexdigest()


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def tree_bytes(root):
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())


def manifest(root):
    return [
        {"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": sha256(path)}
        for path in sorted(root.rglob("*"))
        if path.is_file()
    ]


def write_exclusive(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


spec = json.loads(SPEC.read_text()) if SPEC.is_file() else None
if spec is None or spec.get("specHash") != self_hash(spec, "specHash"):
    raise RuntimeError("slow-tip frozen spec self hash mismatch")
expected_tools = {row["uri"]: row["sha256"] for row in spec["tools"]}
for tool in (SCENE_TOOL, Path(__file__).resolve(), AUDITOR):
    relative = str(tool.relative_to(RESEARCH))
    if expected_tools.get(relative) != sha256(tool):
        raise RuntimeError(f"slow-tip frozen tool identity mismatch: {relative}")
status = subprocess.run(
    ["git", "status", "--porcelain"], cwd=RESEARCH, capture_output=True, text=True, check=True
).stdout
if status:
    raise RuntimeError("slow-tip research worktree is not clean")
if WORK.exists() or EVIDENCE.exists():
    raise RuntimeError("slow-tip attempt roots are not fresh")
if sha256(BINARY) != EXPECTED_BINARY_SHA256 or sha256(SOURCE) != EXPECTED_SOURCE_SHA256:
    raise RuntimeError("slow-tip binary or source identity mismatch")
if not SPEC.is_file() or not AUDITOR.is_file() or not SCENE_TOOL.is_file():
    raise RuntimeError("slow-tip frozen input missing")
free = shutil.disk_usage(WORK.parent).free
projected = 268435456
reserve = 107374182400
if free < projected + reserve:
    raise RuntimeError("slow-tip disk admission failed")

WORK.mkdir(parents=True, exist_ok=False)
EVIDENCE.mkdir(parents=True, exist_ok=False)
for path in (WORK / "cells", EVIDENCE / "cells", EVIDENCE / "logs", EVIDENCE / "processes"):
    path.mkdir(parents=True, exist_ok=False)
write_exclusive(
    EVIDENCE / "admission.json",
    {
        "schemaVersion": "bfs.rc6SlowTipBulletScreenAdmission.v0.1",
        "status": "PASS",
        "workRootAbsentBeforeRun": True,
        "evidenceRootAbsentBeforeRun": True,
        "freeBytes": free,
        "projectedWriteBytes": projected,
        "reserveBytes": reserve,
        "binarySha256": EXPECTED_BINARY_SHA256,
        "sourceSha256": EXPECTED_SOURCE_SHA256,
    },
)

process_hashes = []
results = []
for index, (cell_id, drive_end) in enumerate(CELLS, 1):
    argv = [
        str(BINARY),
        "--background",
        str(SOURCE),
        "--python",
        str(SCENE_TOOL),
        "--",
        "--cell-id",
        cell_id,
        "--drive-end-frame",
        str(drive_end),
        "--source-blend",
        str(SOURCE),
        "--work-root",
        str(WORK),
        "--evidence-root",
        str(EVIDENCE),
    ]
    started = time.monotonic()
    completed = subprocess.run(argv, cwd=RESEARCH, capture_output=True, text=True)
    wall = time.monotonic() - started
    stdout_path = EVIDENCE / "logs" / f"{index:02d}-{cell_id}.stdout.log"
    stderr_path = EVIDENCE / "logs" / f"{index:02d}-{cell_id}.stderr.log"
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")
    process = {
        "schemaVersion": "bfs.processReceipt.v0.1",
        "index": index,
        "cellId": cell_id,
        "argv": argv,
        "cwd": str(RESEARCH),
        "exitCode": completed.returncode,
        "wallSeconds": round(wall, 6),
        "stdoutSha256": sha256(stdout_path),
        "stderrSha256": sha256(stderr_path),
    }
    process["processHash"] = self_hash(process, "processHash")
    write_exclusive(EVIDENCE / "processes" / f"{index:02d}-{cell_id}.json", process)
    process_hashes.append(process["processHash"])
    marker = f'RC6_SLOW_TIP_BULLET_SCREEN={{"cellId":"{cell_id}"'
    result_path = EVIDENCE / "cells" / cell_id / "result.json"
    if completed.returncode != 0 or "Traceback (most recent call last)" in completed.stderr or marker not in completed.stdout or not result_path.is_file():
        raise RuntimeError(f"slow-tip cell failed: {cell_id}")
    result = json.loads(result_path.read_text())
    if result["resultHash"] != self_hash(result, "resultHash"):
        raise RuntimeError(f"slow-tip cell self hash failed: {cell_id}")
    results.append(result)

passing = [row for row in results if row["status"] == "PASS"]
selected = max(passing, key=lambda row: row["configuration"]["driveEndFrame"]) if passing else None
receipt = {
    "schemaVersion": "bfs.rc6SlowTipBulletScreenReceipt.v0.1",
    "status": "PASS" if selected else "FAIL",
    "verdict": "PASS_BULLET_SCREEN" if selected else "FAIL_BULLET_SCREEN",
    "selectedCellId": selected["cellId"] if selected else None,
    "selectedDriveEndFrame": selected["configuration"]["driveEndFrame"] if selected else None,
    "selectedRequiredEffectorSubframes": selected["metrics"]["requiredEffectorSubframes"] if selected else None,
    "cellResultHashes": [row["resultHash"] for row in results],
    "processHashes": process_hashes,
    "counts": {
        "blenderStarts": len(CELLS),
        "bulletBakes": len(CELLS),
        "fluidDataBakes": 0,
        "fluidMeshBakes": 0,
        "renders": 0,
        "blendSaves": 0,
        "networkCalls": 0,
        "engineRemoteWrites": 0,
    },
    "resources": {
        "freeBytesAtAdmission": free,
        "workBytesBeforeManifest": tree_bytes(WORK),
        "evidenceBytesBeforeReceipt": tree_bytes(EVIDENCE),
    },
    "claimCeiling": "The slowest passing Bullet-only cause among four frozen candidates and a measured moving-effector subframe requirement; no fluid or film-quality claim.",
}
receipt["receiptHash"] = self_hash(receipt, "receiptHash")
write_exclusive(EVIDENCE / "receipt.json", receipt)
write_exclusive(WORK / "work-manifest.json", {"root": str(WORK), "files": manifest(WORK)})
write_exclusive(EVIDENCE / "evidence-manifest.pre-audit.json", {"root": str(EVIDENCE), "files": manifest(EVIDENCE)})

audit = subprocess.run(["/usr/bin/python3", str(AUDITOR)], cwd=RESEARCH, capture_output=True, text=True)
(EVIDENCE / "logs" / "audit.stdout.log").write_text(audit.stdout, encoding="utf-8")
(EVIDENCE / "logs" / "audit.stderr.log").write_text(audit.stderr, encoding="utf-8")
if audit.returncode != 0:
    raise RuntimeError("slow-tip independent audit failed")
write_exclusive(EVIDENCE / "evidence-manifest.json", {"root": str(EVIDENCE), "files": manifest(EVIDENCE)})
print("RC6_SLOW_TIP_BULLET_SCREEN_RUN=" + canonical({"status": receipt["status"], "selectedCellId": receipt["selectedCellId"], "receiptHash": receipt["receiptHash"]}))
