#!/usr/bin/env python3
"""Copy immutable attempt-57 Data and run one zero-Blender occupancy diagnosis."""

import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-moving-liquid-data-occupancy-attempt-58")
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-data-occupancy-attempt-58"
SOURCE_CACHE = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-moving-liquid-data-diagnostic-attempt-57/mantaflow-cache")
ATTEMPT56 = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-preview-attempt-56/result.json"
ATTEMPT57 = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-data-diagnostic-attempt-57/result.json"
ENGINE_PYTHON = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC5-2026-09-01-attempt-01/build/bin/Film Studio Engine F0.app/Contents/Resources/5.2/python/bin/python3.13")
OPENVDB_MODULE = ENGINE_PYTHON.parent.parent / "lib/python3.13/site-packages/openvdb.cpython-313-darwin.so"
OPENVDB_LIBRARY = ENGINE_PYTHON.parents[3] / "lib/libopenvdb.dylib"
ANALYZER = RESEARCH / "scripts/analyze-rc6-moving-liquid-data-occupancy.py"
AUDITOR = RESEARCH / "scripts/audit-rc6-moving-liquid-data-occupancy.py"
SPEC = RESEARCH / "specs/ai-native-studio-rc6-moving-liquid-data-occupancy.v0.69.json"


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


def manifest(root):
    rows = [
        {"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": sha(path)}
        for path in sorted(root.rglob("*"))
        if path.is_file()
    ]
    value = {"root": str(root), "files": rows}
    value["manifestHash"] = self_hash(value, "manifestHash")
    return value


def write_exclusive(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


spec = json.loads(SPEC.read_text())
if spec["specHash"] != self_hash(spec, "specHash"):
    raise RuntimeError("Data occupancy spec self hash mismatch")
tools = {row["uri"]: row["sha256"] for row in spec["tools"]}
for tool in (ANALYZER, Path(__file__).resolve(), AUDITOR):
    relative = str(tool.relative_to(RESEARCH))
    if tools.get(relative) != sha(tool):
        raise RuntimeError(f"Data occupancy tool identity mismatch: {relative}")
for path, expected in (
    (ENGINE_PYTHON, spec["runtime"]["enginePythonSha256"]),
    (OPENVDB_MODULE, spec["runtime"]["openVdbModuleSha256"]),
    (OPENVDB_LIBRARY, spec["runtime"]["openVdbLibrarySha256"]),
    (ATTEMPT56, spec["baseline"]["attempt56ResultFileSha256"]),
    (ATTEMPT57, spec["baseline"]["attempt57ResultFileSha256"]),
):
    if sha(path) != expected:
        raise RuntimeError(f"Data occupancy runtime/baseline mismatch: {path}")
if subprocess.run(["git", "status", "--porcelain"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout:
    raise RuntimeError("Data occupancy research worktree is not clean")
if WORK.exists() or EVIDENCE.exists():
    raise RuntimeError("Data occupancy roots are not fresh")
source_manifest_before = manifest(SOURCE_CACHE)
if source_manifest_before["manifestHash"] != spec["baseline"]["attempt57CacheManifestHash"]:
    raise RuntimeError("Data occupancy source cache manifest mismatch")
free = shutil.disk_usage(WORK.parent).free
if free < spec["resourceCeilings"]["minimumReserveBytes"] + spec["resourceCeilings"]["projectedWriteBytes"]:
    raise RuntimeError("Data occupancy disk admission failed")

WORK.mkdir(parents=True, exist_ok=False)
EVIDENCE.mkdir(parents=True, exist_ok=False)
(EVIDENCE / "logs").mkdir()
(EVIDENCE / "processes").mkdir()
cache_copy = WORK / "cache-copy"
shutil.copytree(SOURCE_CACHE, cache_copy)
copied_manifest = manifest(cache_copy)
normalized_copy = dict(copied_manifest)
normalized_copy["root"] = str(SOURCE_CACHE)
normalized_copy["manifestHash"] = self_hash(normalized_copy, "manifestHash")
if normalized_copy["manifestHash"] != source_manifest_before["manifestHash"]:
    raise RuntimeError("Data occupancy copied cache differs from source")
write_exclusive(
    EVIDENCE / "admission.json",
    {
        "schemaVersion": "bfs.rc6MovingLiquidDataOccupancyAdmission.v0.1",
        "status": "PASS",
        "workRootAbsentBeforeRun": True,
        "evidenceRootAbsentBeforeRun": True,
        "freeBytes": free,
        "sourceCacheManifestBefore": source_manifest_before["manifestHash"],
        "copiedCacheManifestNormalized": normalized_copy["manifestHash"],
    },
)
result_path = EVIDENCE / "result.json"
argv = [str(ENGINE_PYTHON), str(ANALYZER), "--cache-copy", str(cache_copy), "--attempt56-result", str(ATTEMPT56), "--attempt57-result", str(ATTEMPT57), "--result", str(result_path)]
started = time.monotonic()
completed = subprocess.run(argv, cwd=RESEARCH, capture_output=True, text=True)
wall_seconds = time.monotonic() - started
stdout_path = EVIDENCE / "logs/01-data-occupancy.stdout.log"
stderr_path = EVIDENCE / "logs/01-data-occupancy.stderr.log"
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
write_exclusive(EVIDENCE / "processes/01-data-occupancy.json", process)
if completed.returncode != 0 or not result_path.is_file() or "RC6_MOVING_LIQUID_DATA_OCCUPANCY=" not in completed.stdout:
    raise RuntimeError("Data occupancy analyzer stopped before explicit result")
result = json.loads(result_path.read_text())
if result["resultHash"] != self_hash(result, "resultHash") or result["status"] != "MEASURED_DATA_OCCUPANCY":
    raise RuntimeError("Data occupancy result identity/status mismatch")
source_manifest_after = manifest(SOURCE_CACHE)
if source_manifest_after["manifestHash"] != source_manifest_before["manifestHash"]:
    raise RuntimeError("Data occupancy retained source cache changed")
receipt = {
    "schemaVersion": "bfs.rc6MovingLiquidDataOccupancyReceipt.v0.1",
    "status": "PASS_DIAGNOSTIC",
    "classification": result["classification"],
    "resultHash": result["resultHash"],
    "processHash": process["processHash"],
    "sourceCacheManifestBefore": source_manifest_before["manifestHash"],
    "sourceCacheManifestAfter": source_manifest_after["manifestHash"],
    "copiedCacheManifest": copied_manifest["manifestHash"],
    "retainedSourceUnchanged": True,
    "counts": {"enginePythonStarts": 1, "blenderStarts": 0, "fluidDataBakes": 0, "fluidMeshBakes": 0, "renders": 0, "blendSaves": 0, "networkCalls": 0, "retainedRootWrites": 0},
    "resources": {"freeBytesAtAdmission": free, "processWallSeconds": round(wall_seconds, 6), "copiedCacheBytes": sum(row["bytes"] for row in copied_manifest["files"])},
    "claimCeiling": result["claimCeiling"],
}
receipt["receiptHash"] = self_hash(receipt, "receiptHash")
write_exclusive(EVIDENCE / "receipt.json", receipt)
write_exclusive(EVIDENCE / "copied-cache-manifest.json", copied_manifest)
write_exclusive(EVIDENCE / "evidence-manifest.pre-audit.json", manifest(EVIDENCE))
print("RC6_MOVING_LIQUID_DATA_OCCUPANCY_RUN=" + canonical({"status": receipt["status"], "classification": receipt["classification"], "receiptHash": receipt["receiptHash"], "resultHash": result["resultHash"]}))
