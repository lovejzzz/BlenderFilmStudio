#!/usr/bin/env python3
"""Copy immutable attempt-61 cache and compare two-subframe Data with attempt-60."""

import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-moving-liquid-subframes-data-comparison-attempt-62")
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-subframes-data-comparison-attempt-62"
SOURCE_CACHE = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-moving-liquid-effector-subframes-attempt-61/mantaflow-cache")
CURRENT_RESULT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-effector-subframes-attempt-61/result.json"
CURRENT_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-effector-subframes-attempt-61/independent-audit.json"
BASELINE_RESULT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-effector-distance-data-occupancy-attempt-60/result.json"
BASELINE_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-effector-distance-data-occupancy-attempt-60/independent-audit.json"
ENGINE_PYTHON = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC5-2026-09-01-attempt-01/build/bin/Film Studio Engine F0.app/Contents/Resources/5.2/python/bin/python3.13")
OPENVDB_MODULE = ENGINE_PYTHON.parent.parent / "lib/python3.13/site-packages/openvdb.cpython-313-darwin.so"
OPENVDB_LIBRARY = ENGINE_PYTHON.parents[3] / "lib/libopenvdb.dylib"
ANALYZER = RESEARCH / "scripts/analyze-rc6-moving-liquid-data-comparison.py"
AUDITOR = RESEARCH / "scripts/audit-rc6-moving-liquid-subframes-data-comparison.py"
SPEC = RESEARCH / "specs/ai-native-studio-rc6-moving-liquid-subframes-data-comparison.v0.73.json"


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
    raise RuntimeError("attempt-62 spec self hash mismatch")
tools = {row["uri"]: row["sha256"] for row in spec["tools"]}
for tool in (ANALYZER, Path(__file__).resolve(), AUDITOR):
    relative = str(tool.relative_to(RESEARCH))
    if tools.get(relative) != sha(tool):
        raise RuntimeError(f"attempt-62 tool identity mismatch: {relative}")
for path, expected in (
    (ENGINE_PYTHON, spec["runtime"]["enginePythonSha256"]),
    (OPENVDB_MODULE, spec["runtime"]["openVdbModuleSha256"]),
    (OPENVDB_LIBRARY, spec["runtime"]["openVdbLibrarySha256"]),
    (CURRENT_RESULT, spec["baseline"]["attempt61ResultFileSha256"]),
    (CURRENT_AUDIT, spec["baseline"]["attempt61AuditFileSha256"]),
    (BASELINE_RESULT, spec["baseline"]["attempt60ResultFileSha256"]),
    (BASELINE_AUDIT, spec["baseline"]["attempt60AuditFileSha256"]),
):
    if sha(path) != expected:
        raise RuntimeError(f"attempt-62 runtime/baseline mismatch: {path}")
if subprocess.run(["git", "status", "--porcelain"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout:
    raise RuntimeError("attempt-62 research worktree is not clean")
if WORK.exists() or EVIDENCE.exists():
    raise RuntimeError("attempt-62 roots are not fresh")
source_manifest_before = manifest(SOURCE_CACHE)
if source_manifest_before["manifestHash"] != spec["baseline"]["attempt61CacheManifestHash"]:
    raise RuntimeError("attempt-62 source cache manifest mismatch")
free = shutil.disk_usage(WORK.parent).free
if free < spec["resourceCeilings"]["minimumReserveBytes"] + spec["resourceCeilings"]["projectedWriteBytes"]:
    raise RuntimeError("attempt-62 disk admission failed")

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
    raise RuntimeError("attempt-62 copied cache differs from source")
write_exclusive(
    EVIDENCE / "admission.json",
    {
        "schemaVersion": "bfs.rc6MovingLiquidSubframesDataComparisonAdmission.v0.1",
        "status": "PASS",
        "workRootAbsentBeforeRun": True,
        "evidenceRootAbsentBeforeRun": True,
        "freeBytes": free,
        "sourceCacheManifestBefore": source_manifest_before["manifestHash"],
        "copiedCacheManifestNormalized": normalized_copy["manifestHash"],
    },
)
result_path = EVIDENCE / "result.json"
argv = [
    str(ENGINE_PYTHON), str(ANALYZER),
    "--cache-copy", str(cache_copy),
    "--current-result", str(CURRENT_RESULT),
    "--baseline-occupancy-result", str(BASELINE_RESULT),
    "--expected-current-result-hash", spec["baseline"]["attempt61ResultHash"],
    "--expected-baseline-result-hash", spec["baseline"]["attempt60ResultHash"],
    "--expected-surface-distance", "2.0",
    "--expected-subframes", "2",
    "--current-label", "subframes-2",
    "--baseline-label", "subframes-1",
    "--result", str(result_path),
]
started = time.monotonic()
completed = subprocess.run(argv, cwd=RESEARCH, capture_output=True, text=True)
wall_seconds = time.monotonic() - started
stdout_path = EVIDENCE / "logs/01-data-comparison.stdout.log"
stderr_path = EVIDENCE / "logs/01-data-comparison.stderr.log"
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
write_exclusive(EVIDENCE / "processes/01-data-comparison.json", process)
if completed.returncode != 0 or not result_path.is_file() or "RC6_MOVING_LIQUID_DATA_COMPARISON=" not in completed.stdout:
    raise RuntimeError("attempt-62 analyzer stopped before explicit result")
result = json.loads(result_path.read_text())
if result["resultHash"] != self_hash(result, "resultHash") or result["status"] != "MEASURED_DATA_COMPARISON":
    raise RuntimeError("attempt-62 result identity/status mismatch")
source_manifest_after = manifest(SOURCE_CACHE)
if source_manifest_after["manifestHash"] != source_manifest_before["manifestHash"]:
    raise RuntimeError("attempt-62 retained source cache changed")
receipt = {
    "schemaVersion": "bfs.rc6MovingLiquidSubframesDataComparisonReceipt.v0.1",
    "status": "PASS_DIAGNOSTIC",
    "classification": result["classification"],
    "resultHash": result["resultHash"],
    "processHash": process["processHash"],
    "sourceCacheManifestBefore": source_manifest_before["manifestHash"],
    "sourceCacheManifestAfter": source_manifest_after["manifestHash"],
    "copiedCacheManifest": copied_manifest["manifestHash"],
    "retainedSourceUnchanged": True,
    "counts": result["counts"],
    "resources": {"freeBytesAtAdmission": free, "processWallSeconds": round(wall_seconds, 6), "copiedCacheBytes": sum(row["bytes"] for row in copied_manifest["files"])},
    "claimCeiling": result["claimCeiling"],
}
receipt["receiptHash"] = self_hash(receipt, "receiptHash")
write_exclusive(EVIDENCE / "receipt.json", receipt)
write_exclusive(EVIDENCE / "copied-cache-manifest.json", copied_manifest)
write_exclusive(EVIDENCE / "evidence-manifest.pre-audit.json", manifest(EVIDENCE))
audit_completed = subprocess.run([str(ENGINE_PYTHON), str(AUDITOR)], cwd=RESEARCH, capture_output=True, text=True)
audit_stdout = EVIDENCE / "logs/audit.stdout.log"
audit_stderr = EVIDENCE / "logs/audit.stderr.log"
audit_stdout.write_text(audit_completed.stdout, encoding="utf-8")
audit_stderr.write_text(audit_completed.stderr, encoding="utf-8")
audit_path = EVIDENCE / "independent-audit.json"
if audit_completed.returncode != 0 or not audit_path.is_file() or "RC6_MOVING_LIQUID_SUBFRAMES_DATA_COMPARISON_AUDIT=" not in audit_completed.stdout:
    raise RuntimeError("attempt-62 independent audit failed")
audit = json.loads(audit_path.read_text())
if audit["auditHash"] != self_hash(audit, "auditHash") or audit["status"] != "PASS":
    raise RuntimeError("attempt-62 independent audit identity/status mismatch")
write_exclusive(EVIDENCE / "evidence-manifest.json", manifest(EVIDENCE))
print("RC6_MOVING_LIQUID_SUBFRAMES_DATA_COMPARISON_RUN=" + canonical({"status": receipt["status"], "classification": receipt["classification"], "receiptHash": receipt["receiptHash"], "resultHash": result["resultHash"], "auditHash": audit["auditHash"]}))
