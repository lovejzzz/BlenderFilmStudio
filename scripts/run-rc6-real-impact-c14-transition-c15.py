#!/usr/bin/env python3
"""Copy immutable C14 cache and run one zero-Blender transition diagnosis."""

import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-real-impact-c14-transition-c15-attempt-87")
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-c14-transition-c15-attempt-87"
SOURCE_CACHE = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-real-impact-liquid-timestep-max-c14-attempt-86/mantaflow-cache")
ATTEMPT86_ROOT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-timestep-max-c14-attempt-86"
C13_ROOT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-data-occupancy-c13-attempt-85"
ENGINE_PYTHON = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC5-2026-09-01-attempt-01/build/bin/Film Studio Engine F0.app/Contents/Resources/5.2/python/bin/python3.13")
OPENVDB_MODULE = ENGINE_PYTHON.parent.parent / "lib/python3.13/site-packages/openvdb.cpython-313-darwin.so"
OPENVDB_LIBRARY = ENGINE_PYTHON.parents[3] / "lib/libopenvdb.dylib"
ANALYZER = RESEARCH / "scripts/analyze-rc6-real-impact-c14-transition-c15.py"
AUDITOR = RESEARCH / "scripts/audit-rc6-real-impact-c14-transition-c15.py"
SPEC = RESEARCH / "specs/ai-native-studio-rc6-real-impact-c14-transition-c15.v0.98.json"


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


def manifest(root, exclude=()):
    excluded = set(exclude)
    rows = [
        {"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": sha(path)}
        for path in sorted(root.rglob("*"))
        if path.is_file() and str(path.relative_to(root)) not in excluded
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
    raise RuntimeError("C15 spec self hash mismatch")
tool_hashes = {row["uri"]: row["sha256"] for row in spec["tools"]}
for tool in (ANALYZER, Path(__file__).resolve(), AUDITOR):
    relative = str(tool.relative_to(RESEARCH))
    if tool_hashes.get(relative) != sha(tool):
        raise RuntimeError(f"C15 tool identity mismatch: {relative}")
    committed = subprocess.run(["git", "show", f"HEAD:{relative}"], cwd=RESEARCH, capture_output=True, check=True).stdout
    if hashlib.sha256(committed).hexdigest() != sha(tool):
        raise RuntimeError(f"C15 tool is not execution-commit exact: {relative}")
spec_relative = str(SPEC.relative_to(RESEARCH))
if hashlib.sha256(subprocess.run(["git", "show", f"HEAD:{spec_relative}"], cwd=RESEARCH, capture_output=True, check=True).stdout).hexdigest() != sha(SPEC):
    raise RuntimeError("C15 spec is not execution-commit exact")
paths = {
    ENGINE_PYTHON: spec["runtime"]["enginePythonSha256"],
    OPENVDB_MODULE: spec["runtime"]["openVdbModuleSha256"],
    OPENVDB_LIBRARY: spec["runtime"]["openVdbLibrarySha256"],
    ATTEMPT86_ROOT / "result.json": spec["baseline"]["attempt86ResultFileSha256"],
    ATTEMPT86_ROOT / "receipt.json": spec["baseline"]["attempt86ReceiptFileSha256"],
    ATTEMPT86_ROOT / "independent-audit.json": spec["baseline"]["attempt86AuditFileSha256"],
    C13_ROOT / "result.json": spec["baseline"]["c13ResultFileSha256"],
    C13_ROOT / "receipt.json": spec["baseline"]["c13ReceiptFileSha256"],
    C13_ROOT / "independent-audit.json": spec["baseline"]["c13AuditFileSha256"],
}
for path, expected in paths.items():
    if sha(path) != expected:
        raise RuntimeError(f"C15 runtime/baseline mismatch: {path}")
if subprocess.run(["git", "status", "--porcelain"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout:
    raise RuntimeError("C15 research worktree is not clean")
if WORK.exists() or EVIDENCE.exists():
    raise RuntimeError("C15 roots are not fresh")
source_manifest_before = manifest(SOURCE_CACHE)
if source_manifest_before["manifestHash"] != spec["baseline"]["attempt86CacheManifestHash"] or len(source_manifest_before["files"]) != spec["baseline"]["attempt86CacheFiles"]:
    raise RuntimeError("C15 source cache manifest mismatch")
if any(path.is_symlink() for path in SOURCE_CACHE.rglob("*")):
    raise RuntimeError("C15 source cache contains a symlink")
free = shutil.disk_usage(WORK.parent).free
ceilings = spec["resourceCeilings"]
if free < ceilings["minimumReserveBytes"] + ceilings["projectedWriteBytes"]:
    raise RuntimeError("C15 disk admission failed")

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
    raise RuntimeError("C15 copied cache differs from source")
write_exclusive(EVIDENCE / "admission.json", {
    "schemaVersion": "bfs.rc6RealImpactC14TransitionC15Admission.v0.1",
    "status": "PASS",
    "workRootAbsentBeforeRun": True,
    "evidenceRootAbsentBeforeRun": True,
    "freeBytes": free,
    "sourceCacheManifestBefore": source_manifest_before["manifestHash"],
    "copiedCacheManifestNormalized": normalized_copy["manifestHash"],
})
write_exclusive(EVIDENCE / "copied-cache-manifest.json", copied_manifest)

result_path = EVIDENCE / "result.json"
argv = [
    str(ENGINE_PYTHON), str(ANALYZER),
    "--cache-copy", str(cache_copy),
    "--attempt86-result", str(ATTEMPT86_ROOT / "result.json"),
    "--c13-result", str(C13_ROOT / "result.json"),
    "--spec", str(SPEC),
    "--result", str(result_path),
]
started = time.monotonic()
completed = subprocess.run(argv, cwd=RESEARCH, capture_output=True, text=True)
wall_seconds = time.monotonic() - started
stdout_path = EVIDENCE / "logs/01-transition.stdout.log"
stderr_path = EVIDENCE / "logs/01-transition.stderr.log"
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
write_exclusive(EVIDENCE / "processes/01-transition.json", process)
if completed.returncode != 0 or not result_path.is_file() or "RC6_REAL_IMPACT_C14_TRANSITION_C15=" not in completed.stdout:
    raise RuntimeError("C15 analyzer stopped before explicit result")
result = json.loads(result_path.read_text())
if result["resultHash"] != self_hash(result, "resultHash") or result["status"] != "MEASURED_TRANSITION_ORDER":
    raise RuntimeError("C15 result identity/status mismatch")
source_manifest_after = manifest(SOURCE_CACHE)
if source_manifest_after["manifestHash"] != source_manifest_before["manifestHash"]:
    raise RuntimeError("C15 retained source cache changed")
receipt = {
    "schemaVersion": "bfs.rc6RealImpactC14TransitionC15Receipt.v0.1",
    "status": "PASS_DIAGNOSTIC",
    "classification": result["classification"],
    "resultHash": result["resultHash"],
    "processHash": process["processHash"],
    "researchExecutionCommit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.strip(),
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
work_manifest = manifest(WORK)
if sum(row["bytes"] for row in work_manifest["files"]) > ceilings["maximumWorkspaceBytes"]:
    raise RuntimeError("C15 workspace ceiling exceeded")
write_exclusive(EVIDENCE / "work-manifest.json", work_manifest)
evidence_manifest = manifest(EVIDENCE, exclude={"evidence-manifest.pre-audit.json"})
if sum(row["bytes"] for row in evidence_manifest["files"]) > ceilings["maximumEvidenceBytes"]:
    raise RuntimeError("C15 evidence ceiling exceeded")
write_exclusive(EVIDENCE / "evidence-manifest.pre-audit.json", evidence_manifest)
print("RC6_REAL_IMPACT_C14_TRANSITION_C15_RUN=" + canonical({"status": receipt["status"], "classification": receipt["classification"], "receiptHash": receipt["receiptHash"], "resultHash": result["resultHash"]}))
