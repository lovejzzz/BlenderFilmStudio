#!/usr/bin/env python3
"""Run the frozen three-cell exact-scene Bullet impact speed screen."""

import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-real-impact-bullet-speed-screen-attempt-71")
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-bullet-speed-screen-attempt-71"
BINARY = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC5-2026-09-01-attempt-01/build/bin/Film Studio Engine F0.app/Contents/MacOS/Blender")
SOURCE = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-final-effector-mesh-c3-attempt-46/final-effector-mesh-c3/source-state.blend")
SCENE_TOOL = RESEARCH / "scripts/run-rc6-real-impact-bullet-speed-screen-scene.py"
AUDITOR = RESEARCH / "scripts/audit-rc6-real-impact-bullet-speed-screen.py"
SPEC = RESEARCH / "specs/ai-native-studio-rc6-real-impact-bullet-speed-screen.v0.82.json"
CELLS = (("I08", 8), ("I10", 10), ("I12", 12))
EXPECTED_BINARY_SHA256 = "ad08b54132b75325a12580f705fdefc205dd4444a36f2491e4d8a200e1091ef2"
EXPECTED_SOURCE_SHA256 = "9ac79c9c3c0d13273ac20804a3af99884f9465534800c3d9ca2ae8121499e644"
EXPECTED_COMMIT_PATHS = {
    "research/2026-09-02-rc6-real-impact-bullet-speed-screen-preregistration.md",
    "research/lab-journal.md",
    "scripts/audit-rc6-real-impact-bullet-speed-screen.py",
    "scripts/run-rc6-real-impact-bullet-speed-screen-scene.py",
    "scripts/run-rc6-real-impact-bullet-speed-screen.py",
    "specs/ai-native-studio-rc6-real-impact-bullet-speed-screen.v0.82.json",
}


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


def manifest(root, excluded=()):
    excluded = {Path(value) for value in excluded}
    return [
        {"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": sha256(path)}
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.relative_to(root) not in excluded
    ]


def write_exclusive(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


spec = json.loads(SPEC.read_text()) if SPEC.is_file() else None
if spec is None or spec.get("specHash") != self_hash(spec, "specHash"):
    raise RuntimeError("real-impact frozen spec self hash mismatch")
expected_tools = {row["uri"]: row["sha256"] for row in spec["tools"]}
for tool in (SCENE_TOOL, Path(__file__).resolve(), AUDITOR):
    relative = str(tool.relative_to(RESEARCH))
    if expected_tools.get(relative) != sha256(tool):
        raise RuntimeError(f"real-impact frozen tool identity mismatch: {relative}")
status = subprocess.run(
    ["git", "status", "--porcelain"], cwd=RESEARCH, capture_output=True, text=True, check=True
).stdout
if status:
    raise RuntimeError("real-impact research worktree is not clean")
head = subprocess.run(
    ["git", "rev-parse", "HEAD"], cwd=RESEARCH, capture_output=True, text=True, check=True
).stdout.strip()
parent = subprocess.run(
    ["git", "rev-parse", "HEAD^"], cwd=RESEARCH, capture_output=True, text=True, check=True
).stdout.strip()
commit_paths = set(
    subprocess.run(
        ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"],
        cwd=RESEARCH,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
)
if parent != spec["researchParentBeforePreregistration"] or commit_paths != EXPECTED_COMMIT_PATHS:
    raise RuntimeError("real-impact preregistration commit binding mismatch")
if WORK.exists() or EVIDENCE.exists():
    raise RuntimeError("real-impact attempt roots are not fresh")
if sha256(BINARY) != EXPECTED_BINARY_SHA256 or sha256(SOURCE) != EXPECTED_SOURCE_SHA256:
    raise RuntimeError("real-impact binary or source identity mismatch")
baseline_paths = {row["uri"]: row["sha256"] for row in spec["baselineEvidenceFiles"]}
for relative, expected_hash in baseline_paths.items():
    if sha256(RESEARCH / relative) != expected_hash:
        raise RuntimeError(f"real-impact baseline evidence mismatch: {relative}")
free = shutil.disk_usage(WORK.parent).free
projected = spec["resourceCeilings"]["projectedWriteBytes"]
reserve = spec["resourceCeilings"]["minimumReserveBytes"]
if free < projected + reserve:
    raise RuntimeError("real-impact disk admission failed")

WORK.mkdir(parents=True, exist_ok=False)
EVIDENCE.mkdir(parents=True, exist_ok=False)
for path in (WORK / "user", EVIDENCE / "cells", EVIDENCE / "logs", EVIDENCE / "processes"):
    path.mkdir(parents=True, exist_ok=False)
write_exclusive(
    EVIDENCE / "admission.json",
    {
        "schemaVersion": "bfs.rc6RealImpactBulletSpeedScreenAdmission.v0.1",
        "status": "PASS",
        "workRootAbsentBeforeRun": True,
        "evidenceRootAbsentBeforeRun": True,
        "freeBytes": free,
        "projectedWriteBytes": projected,
        "reserveBytes": reserve,
        "binarySha256": EXPECTED_BINARY_SHA256,
        "sourceSha256": EXPECTED_SOURCE_SHA256,
        "researchHead": head,
    },
)

process_hashes = []
results = []
for index, (cell_id, drive_end) in enumerate(CELLS, 1):
    user_root = WORK / "user" / cell_id
    user_paths = {
        "HOME": user_root / "home",
        "BLENDER_USER_CONFIG": user_root / "config",
        "BLENDER_USER_SCRIPTS": user_root / "scripts",
        "BLENDER_USER_DATAFILES": user_root / "datafiles",
        "BLENDER_USER_AUTOSAVE": user_root / "autosave",
    }
    for path in user_paths.values():
        path.mkdir(parents=True, exist_ok=False)
    process_env = dict(os.environ)
    process_env.update({key: str(value) for key, value in user_paths.items()})
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
    completed = subprocess.run(argv, cwd=RESEARCH, env=process_env, capture_output=True, text=True)
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
        "isolatedUserPaths": {key: str(value) for key, value in user_paths.items()},
        "exitCode": completed.returncode,
        "wallSeconds": round(wall, 6),
        "stdoutSha256": sha256(stdout_path),
        "stderrSha256": sha256(stderr_path),
    }
    process["processHash"] = self_hash(process, "processHash")
    write_exclusive(EVIDENCE / "processes" / f"{index:02d}-{cell_id}.json", process)
    process_hashes.append(process["processHash"])
    marker = f'RC6_REAL_IMPACT_BULLET_SPEED_SCREEN={{"cellId":"{cell_id}"'
    result_path = EVIDENCE / "cells" / cell_id / "result.json"
    if (
        completed.returncode != 0
        or "Traceback (most recent call last)" in completed.stderr
        or marker not in completed.stdout
        or not result_path.is_file()
    ):
        raise RuntimeError(f"real-impact cell execution failed: {cell_id}")
    result = json.loads(result_path.read_text())
    if result["resultHash"] != self_hash(result, "resultHash"):
        raise RuntimeError(f"real-impact cell self hash failed: {cell_id}")
    results.append(result)

passing = [row for row in results if row["status"] == "PASS"]
selected = max(passing, key=lambda row: row["configuration"]["driveEndFrame"]) if passing else None
receipt = {
    "schemaVersion": "bfs.rc6RealImpactBulletSpeedScreenReceipt.v0.1",
    "status": "PASS" if selected else "FAIL",
    "verdict": "PASS_REAL_IMPACT_BULLET_TRAJECTORY" if selected else "FAIL_REAL_IMPACT_BULLET_TRAJECTORY",
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
        "nativeBuilds": 0,
        "networkCalls": 0,
        "engineRemoteWrites": 0,
    },
    "resources": {
        "freeBytesAtAdmission": free,
        "workBytesBeforeManifest": tree_bytes(WORK),
        "evidenceBytesBeforeReceipt": tree_bytes(EVIDENCE),
    },
    "claimCeiling": "The slowest passing exact-scene Bullet basketball impact among three frozen striker speeds and its derived Preview-96 effector-subframe requirement; no liquid or film-quality claim.",
}
receipt["receiptHash"] = self_hash(receipt, "receiptHash")
write_exclusive(EVIDENCE / "receipt.json", receipt)
write_exclusive(
    WORK / "work-manifest.json",
    {"root": str(WORK), "files": manifest(WORK, excluded=(Path("work-manifest.json"),))},
)
write_exclusive(
    EVIDENCE / "evidence-manifest.pre-audit.json",
    {
        "root": str(EVIDENCE),
        "files": manifest(EVIDENCE, excluded=(Path("evidence-manifest.pre-audit.json"),)),
    },
)

audit = subprocess.run(["/usr/bin/python3", str(AUDITOR)], cwd=RESEARCH, capture_output=True, text=True)
(EVIDENCE / "logs" / "audit.stdout.log").write_text(audit.stdout, encoding="utf-8")
(EVIDENCE / "logs" / "audit.stderr.log").write_text(audit.stderr, encoding="utf-8")
if audit.returncode != 0:
    raise RuntimeError("real-impact independent audit failed")
write_exclusive(
    EVIDENCE / "evidence-manifest.json",
    {"root": str(EVIDENCE), "files": manifest(EVIDENCE, excluded=(Path("evidence-manifest.json"),))},
)
print(
    "RC6_REAL_IMPACT_BULLET_SPEED_SCREEN_RUN="
    + canonical(
        {
            "status": receipt["status"],
            "selectedCellId": receipt["selectedCellId"],
            "receiptHash": receipt["receiptHash"],
        }
    )
)
