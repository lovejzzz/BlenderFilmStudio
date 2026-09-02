#!/usr/bin/env python3
"""Audit-only closure for the immutable C18 attempt-90 claim wording mismatch."""

import hashlib
import json
import os
from pathlib import Path
import subprocess


RESEARCH = Path(__file__).resolve().parents[1]
SPEC_PATH = RESEARCH / "specs/ai-native-studio-rc6-real-impact-liquid-fractions-threshold-c18-audit-c1.v1.02.json"
RETAINED_EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-fractions-threshold-c18-attempt-90"
RETAINED_WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-real-impact-liquid-fractions-threshold-c18-attempt-90")
FRESH_EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-fractions-threshold-c18-audit-c1-attempt-91"
BASE_SPEC = RESEARCH / "specs/ai-native-studio-rc6-real-impact-liquid-fractions-threshold-c18.v1.01.json"
BASE_AUDITOR = RESEARCH / "scripts/audit-rc6-real-impact-liquid-fractions-threshold-c18.py"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def self_hash(value, field):
    return hashlib.sha256(canonical({key: item for key, item in value.items() if key != field})).hexdigest()


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_exclusive(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")


def root_manifest(root, label):
    entries = []
    symlinks = []
    for directory, directory_names, file_names in os.walk(root, followlinks=False):
        directory_path = Path(directory)
        for name in list(directory_names):
            path = directory_path / name
            if path.is_symlink():
                symlinks.append(path.relative_to(root).as_posix())
        for name in file_names:
            path = directory_path / name
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                symlinks.append(relative)
                continue
            entries.append({"path": relative, "bytes": path.stat().st_size, "sha256": sha(path)})
    entries.sort(key=lambda row: row["path"])
    manifest = {
        "schemaVersion": "bfs.immutableRootManifest.v0.1",
        "root": label,
        "files": len(entries),
        "bytes": sum(row["bytes"] for row in entries),
        "symlinks": sorted(symlinks),
        "entries": entries,
    }
    manifest["manifestHash"] = self_hash(manifest, "manifestHash")
    return manifest


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def check(name, value, checks):
    checks[name] = bool(value)


if not SPEC_PATH.is_file() or not RETAINED_EVIDENCE.is_dir() or not RETAINED_WORK.is_dir():
    raise RuntimeError("C18 C1 frozen input missing")
if FRESH_EVIDENCE.exists():
    raise RuntimeError("C18 C1 fresh evidence root already exists")

spec = read(SPEC_PATH)
retained_evidence_before = root_manifest(RETAINED_EVIDENCE, spec["retainedAttempt90"]["evidenceRoot"])
retained_work_before = root_manifest(RETAINED_WORK, spec["retainedAttempt90"]["workRoot"])
base_spec = read(BASE_SPEC)
result = read(RETAINED_EVIDENCE / "result.json")
receipt = read(RETAINED_EVIDENCE / "receipt.json")
original_audit = read(RETAINED_EVIDENCE / "independent-audit.json")
process = read(RETAINED_EVIDENCE / "processes/01-real-impact-fractions-threshold.json")
checks = {}

spec_without_hash = {key: value for key, value in spec.items() if key != "specHash"}
check("specSelfHash", hashlib.sha256(canonical(spec_without_hash)).hexdigest() == spec["specHash"], checks)
check("toolIdentity", sha(Path(__file__).resolve()) == spec["tool"]["sha256"], checks)
check("baseFilesExact", sha(BASE_SPEC) == spec["baseFreeze"]["specFileSha256"] and sha(BASE_AUDITOR) == spec["baseFreeze"]["auditorFileSha256"], checks)

head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.strip()
parent = subprocess.run(["git", "rev-parse", "HEAD^"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.strip()
changed = set(subprocess.run(["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.splitlines())
check("freezeCommitBound", parent == spec["researchParentBeforePreregistration"] and changed == set(spec["freezePaths"]), checks)

retained = spec["retainedAttempt90"]
check("retainedEvidenceExact", retained_evidence_before["manifestHash"] == retained["evidenceManifestHash"] and retained_evidence_before["files"] == retained["evidenceFiles"] and retained_evidence_before["bytes"] == retained["evidenceBytes"] and not retained_evidence_before["symlinks"], checks)
check("retainedWorkExact", retained_work_before["manifestHash"] == retained["workManifestHash"] and retained_work_before["files"] == retained["workFiles"] and retained_work_before["bytes"] == retained["workBytes"] and not retained_work_before["symlinks"], checks)
check("retainedCoreFilesExact", sha(RETAINED_EVIDENCE / "result.json") == retained["resultFileSha256"] and sha(RETAINED_EVIDENCE / "receipt.json") == retained["receiptFileSha256"] and sha(RETAINED_EVIDENCE / "independent-audit.json") == retained["auditFileSha256"], checks)
check("retainedSelfHashes", result["resultHash"] == self_hash(result, "resultHash") == retained["resultHash"] and receipt["receiptHash"] == self_hash(receipt, "receiptHash") == retained["receiptHash"] and original_audit["auditHash"] == self_hash(original_audit, "auditHash") == retained["auditHash"], checks)

false_checks = sorted(name for name, value in original_audit["checks"].items() if not value)
check("originalAuditDefectIsolated", original_audit["status"] == "FAIL" and original_audit["passCount"] == 19 and original_audit["checkCount"] == 20 and false_checks == ["claimCeilingExact"], checks)
check("physicalResultStillFail", result["status"] == "FAIL" and receipt["status"] == "FAIL" and original_audit["physicalStatus"] == "FAIL" and original_audit["physicalPassCount"] == 23 and original_audit["physicalCheckCount"] == 27 and original_audit["recomputedPhysicalChecks"] == result["checks"], checks)
check("fourPhysicalFailuresExact", sorted(name for name, value in result["checks"].items() if not value) == spec["physicalResult"]["failedChecks"], checks)
check("physicalMetricsExact", all(abs(result["metrics"][name] - value) <= 1e-8 for name, value in spec["physicalResult"]["exactMetrics"].items()), checks)

check("producerClaimExact", result["claimCeiling"] == receipt["claimCeiling"] == spec["correction"]["producerExactClaim"], checks)
check("preregisteredClaimExact", base_spec["claimCeiling"] == spec["correction"]["preregisteredExactClaim"], checks)
producer_normalized = result["claimCeiling"].replace("fractional-obstacle threshold", "fractions_threshold").replace("on the retained C14 CFL2/timesteps2/8 baseline", "on exact C14 CFL2/timesteps2/8")
check("claimDifferenceOnlyNaming", producer_normalized == base_spec["claimCeiling"], checks)

check("processAndLogsExact", process["processHash"] == self_hash(process, "processHash") and sha(RETAINED_EVIDENCE / "logs/01-real-impact-fractions-threshold.stdout.log") == process["stdoutSha256"] and sha(RETAINED_EVIDENCE / "logs/01-real-impact-fractions-threshold.stderr.log") == process["stderrSha256"] and process["exitCode"] == 0, checks)
check("boundedOperationsExact", receipt["counts"] == spec["physicalResult"]["operationCounts"] and receipt["resources"]["workBytesBeforeManifest"] <= 2147483648 and receipt["resources"]["evidenceBytesBeforeReceipt"] <= 67108864, checks)
check("noRenderMedia", not any(path.suffix.lower() in {".exr", ".png", ".jpg", ".jpeg", ".mov", ".mp4"} for path in RETAINED_WORK.rglob("*") if path.is_file()), checks)

retained_evidence_after = root_manifest(RETAINED_EVIDENCE, spec["retainedAttempt90"]["evidenceRoot"])
retained_work_after = root_manifest(RETAINED_WORK, spec["retainedAttempt90"]["workRoot"])
check("retainedRootsUnchanged", retained_evidence_after == retained_evidence_before and retained_work_after == retained_work_before, checks)

FRESH_EVIDENCE.mkdir(parents=True, exist_ok=False)
write_exclusive(FRESH_EVIDENCE / "retained-evidence-manifest.json", retained_evidence_before)
write_exclusive(FRESH_EVIDENCE / "retained-work-manifest.json", retained_work_before)
status = "PASS_AUDIT_ONLY_PHYSICAL_FAIL_RETAINED" if all(checks.values()) else "FAIL_AUDIT_ONLY"
audit = {
    "schemaVersion": "bfs.rc6RealImpactLiquidFractionsThresholdC18AuditC1.v0.1",
    "status": status,
    "researchCommit": head,
    "checks": checks,
    "passCount": sum(checks.values()),
    "checkCount": len(checks),
    "retainedPhysicalStatus": result["status"],
    "retainedPhysicalPassCount": original_audit["physicalPassCount"],
    "retainedPhysicalCheckCount": original_audit["physicalCheckCount"],
    "retainedResultHash": result["resultHash"],
    "retainedReceiptHash": receipt["receiptHash"],
    "retainedOriginalAuditHash": original_audit["auditHash"],
    "retainedEvidenceManifestHashBefore": retained_evidence_before["manifestHash"],
    "retainedEvidenceManifestHashAfter": retained_evidence_after["manifestHash"],
    "retainedWorkManifestHashBefore": retained_work_before["manifestHash"],
    "retainedWorkManifestHashAfter": retained_work_after["manifestHash"],
    "claimFinding": "The producer and preregistered claim ceilings differ only by exact parameter/baseline naming; scope and prohibited claims are identical.",
    "nextGate": spec["nextGate"],
    "claimCeiling": spec["claimCeiling"],
}
audit["auditHash"] = self_hash(audit, "auditHash")
write_exclusive(FRESH_EVIDENCE / "audit.json", audit)
fresh_manifest = root_manifest(FRESH_EVIDENCE, spec["freshEvidenceRoot"])
if fresh_manifest["bytes"] > spec["resourceCeilingBytes"] or fresh_manifest["symlinks"]:
    raise RuntimeError("C18 C1 fresh evidence root exceeds ceiling or contains symlinks")
write_exclusive(FRESH_EVIDENCE / "evidence-manifest.json", fresh_manifest)
print("RC6_REAL_IMPACT_LIQUID_FRACTIONS_THRESHOLD_C18_AUDIT_C1=" + json.dumps({"status": status, "passCount": audit["passCount"], "checkCount": audit["checkCount"], "auditHash": audit["auditHash"]}, sort_keys=True, separators=(",", ":")))
if status != "PASS_AUDIT_ONLY_PHYSICAL_FAIL_RETAINED":
    raise RuntimeError("C18 C1 audit-only closure failed")
