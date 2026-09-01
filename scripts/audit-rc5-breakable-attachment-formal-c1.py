#!/usr/bin/env python3
"""C1 correction audit for the retained RC5 formal base-auditor scope error."""

import hashlib
import json
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
EVIDENCE = RESEARCH / "experiments/physical-richness/RC5-2026-09-01-attempt-01"
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC5-2026-09-01-attempt-01")
BASE_AUDIT_HASH = "5c65ef1d6adaf6a6eab02d269f5ca8ff471a053fe83a2f6e0bde17f262b98f61"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def self_hash(value, field):
    body = dict(value)
    body.pop(field, None)
    return hashlib.sha256(canonical(body).encode()).hexdigest()


def tree_bytes(root):
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file() and not path.is_symlink())


def main():
    destination = EVIDENCE / "formal-audit-c1.json"
    if destination.exists():
        raise RuntimeError("C1 audit already exists")
    base = load(EVIDENCE / "formal-audit.json")
    receipt = load(EVIDENCE / "receipt.json")
    visual = load(EVIDENCE / "formal-visual-review.json")
    false_checks = [name for name, passed in base["checks"].items() if not passed]
    source_media = [path for path in (WORK / "source").rglob("*") if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".exr", ".mov", ".mp4"}]
    runtime_media = [path for path in (WORK / "runtime").rglob("*") if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".exr", ".mov", ".mp4"}]
    checks = {
        "retainedBaseAuditExact": base["status"] == "FAIL" and base["auditHash"] == BASE_AUDIT_HASH and base["checkCount"] == 27 and base["passCount"] == 26,
        "singleKnownFailure": false_checks == ["workMediaAndResources"],
        "baseOtherChecksRemainPass": all(passed for name, passed in base["checks"].items() if name != "workMediaAndResources"),
        "scopeCauseConfirmed": len(source_media) > 0 and any("tests/files" in str(path.relative_to(WORK / "source")) for path in source_media),
        "runtimeRenderLeakageZero": runtime_media == [],
        "workCeiling": tree_bytes(WORK) <= 64 * 1024**3,
        "evidenceCeiling": tree_bytes(EVIDENCE) <= 1024 * 1024**2,
        "reserveCeiling": receipt["resources"]["freeBytesAfter"] >= 100 * 1024**3,
        "machineAndVisualRemainPass": receipt["status"] == "PASS_PENDING_FRESH_DIRECT_VISUAL_REVIEW_AND_INDEPENDENT_AUDIT" and all(receipt["checks"].values()) and visual["status"] == "PASS" and visual["yesCount"] == 10,
        "combinedAuditAcceptance": base["passCount"] == 26 and runtime_media == [] and tree_bytes(WORK) <= 64 * 1024**3 and tree_bytes(EVIDENCE) <= 1024 * 1024**2 and receipt["resources"]["freeBytesAfter"] >= 100 * 1024**3,
    }
    output = {
        "schemaVersion": "bfs.rc5BreakableAttachmentFormalAuditC1.v0.1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "checkCount": len(checks),
        "passCount": sum(checks.values()),
        "retainedBaseAuditHash": base["auditHash"],
        "baseEvidenceManifestSha256": sha(EVIDENCE / "formal-evidence-manifest.json"),
        "baseWorkManifestSha256": sha(EVIDENCE / "formal-work-manifest.json"),
        "formalReceiptHash": receipt["receiptHash"],
        "formalVisualReviewHash": visual["reviewHash"],
        "sourceMediaCountExcludedFromRuntimeLeakageCheck": len(source_media),
        "runtimeMediaCount": len(runtime_media),
        "workBytes": tree_bytes(WORK),
        "evidenceBytesBeforeC1Audit": tree_bytes(EVIDENCE),
        "claim": "C1 corrects only the audit scope from the whole build/source workspace to the formal scene runtime; it does not change or rerun source, build, physics, render, visual review, thresholds or resources."
    }
    output["auditHash"] = self_hash(output, "auditHash")
    destination.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(canonical(output))
    if output["status"] != "PASS":
        raise RuntimeError("RC5 formal C1 audit failed")


if __name__ == "__main__":
    main()
