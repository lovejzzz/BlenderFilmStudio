#!/usr/bin/env python3
"""Close only C21's transcribed C19 receipt self hash in a fresh audit root."""

import hashlib
import json
import subprocess
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
SPEC = RESEARCH / "specs/ai-native-studio-rc6-real-impact-particle-radius-data-comparison-c21-c1.v1.11.json"
ORIGINAL_SPEC = RESEARCH / "specs/ai-native-studio-rc6-real-impact-particle-radius-data-comparison-c21.v1.10.json"
RETAINED = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-particle-radius-data-comparison-c21-attempt-99"
C19 = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-fractions-threshold-data-comparison-c19-attempt-92"
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-particle-radius-data-comparison-c21-c1-audit-attempt-100"


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


def main():
    spec = json.loads(SPEC.read_text())
    original_spec = json.loads(ORIGINAL_SPEC.read_text())
    result = json.loads((RETAINED / "result.json").read_text())
    receipt = json.loads((RETAINED / "receipt.json").read_text())
    original_audit = json.loads((RETAINED / "independent-audit.json").read_text())
    failure = json.loads((RETAINED / "failure.json").read_text())
    c19_result = json.loads((C19 / "result.json").read_text())
    c19_receipt = json.loads((C19 / "receipt.json").read_text())
    c19_audit = json.loads((C19 / "independent-audit.json").read_text())

    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.strip()
    parent = subprocess.run(["git", "rev-parse", "HEAD^"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.strip()
    freeze_paths = set(subprocess.run(["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.splitlines())
    false_checks = sorted(key for key, value in original_audit["checks"].items() if not value)
    retained_before = manifest(RETAINED)
    corrected_view = json.loads(ORIGINAL_SPEC.read_text())
    corrected_view["baseline"]["c19ReceiptHash"] = spec["correctedC19ReceiptHash"]

    checks = {
        "specSelfHash": spec["specHash"] == self_hash(spec, "specHash"),
        "toolIdentity": sha(Path(__file__).resolve()) == spec["toolSha256"],
        "freezeCommitExact": parent == spec["researchParentBeforePreregistration"] and freeze_paths == set(spec["freezePaths"]),
        "worktreeClean": subprocess.run(["git", "status", "--porcelain"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout == "",
        "freshRootAbsent": not EVIDENCE.exists(),
        "retainedRootExact": retained_before["manifestHash"] == spec["retainedAttempt99ManifestHash"] and len(retained_before["files"]) == spec["retainedAttempt99FileCount"],
        "retainedFilesExact": sha(RETAINED / "result.json") == spec["retainedResultFileSha256"] and sha(RETAINED / "receipt.json") == spec["retainedReceiptFileSha256"] and sha(RETAINED / "independent-audit.json") == spec["retainedAuditFileSha256"] and sha(RETAINED / "failure.json") == spec["retainedFailureFileSha256"],
        "retainedSelfHashesExact": result["resultHash"] == self_hash(result, "resultHash") == spec["retainedResultHash"] and receipt["receiptHash"] == self_hash(receipt, "receiptHash") == spec["retainedReceiptHash"] and original_audit["auditHash"] == self_hash(original_audit, "auditHash") == spec["retainedAuditHash"],
        "originalSoleFailureExact": original_audit["status"] == "FAIL" and original_audit["passCount"] == 22 and original_audit["checkCount"] == 23 and false_checks == ["c19EvidenceExact"],
        "scientificResultExact": result["status"] == "MEASURED_PARTICLE_RADIUS_DATA_MESH_COMPARISON" and result["classification"] == receipt["classification"] == original_audit["classification"] == "C20_SAME_ONSET_MORE_SEVERE_THAN_C18",
        "failureRecordExact": failure["status"] == "FAIL_INDEPENDENT_AUDIT_BASELINE_RECEIPT_HASH_TRANSCRIPTION" and failure["cause"]["field"] == "baseline.c19ReceiptHash",
        "originalSpecExact": sha(ORIGINAL_SPEC) == spec["originalSpecFileSha256"] and original_spec["specHash"] == spec["originalSpecHash"],
        "wrongLeafExact": original_spec["baseline"]["c19ReceiptHash"] == spec["transcribedC19ReceiptHash"] and spec["transcribedC19ReceiptHash"] != spec["correctedC19ReceiptHash"],
        "correctedViewSingleLeaf": corrected_view["baseline"]["c19ReceiptHash"] == spec["correctedC19ReceiptHash"] and {k: v for k, v in corrected_view.items() if k != "baseline"} == {k: v for k, v in original_spec.items() if k != "baseline"} and {k: v for k, v in corrected_view["baseline"].items() if k != "c19ReceiptHash"} == {k: v for k, v in original_spec["baseline"].items() if k != "c19ReceiptHash"},
        "c19ResultExact": sha(C19 / "result.json") == original_spec["baseline"]["c19ResultFileSha256"] and c19_result["resultHash"] == original_spec["baseline"]["c19ResultHash"],
        "c19ReceiptCorrected": sha(C19 / "receipt.json") == original_spec["baseline"]["c19ReceiptFileSha256"] and c19_receipt["receiptHash"] == self_hash(c19_receipt, "receiptHash") == spec["correctedC19ReceiptHash"],
        "c19AuditExact": sha(C19 / "independent-audit.json") == original_spec["baseline"]["c19AuditFileSha256"] and c19_audit["auditHash"] == self_hash(c19_audit, "auditHash") == original_spec["baseline"]["c19AuditHash"] and c19_audit["status"] == "PASS",
        "zeroExecutionAuthority": spec["counts"] == {"systemPythonStarts": 1, "analyzerStarts": 0, "cacheCopies": 0, "blenderStarts": 0, "fluidDataBakes": 0, "fluidMeshBakes": 0, "renders": 0, "blendSaves": 0, "networkCalls": 0, "retainedRootWrites": 0},
    }
    if not all(checks.values()):
        raise RuntimeError("C21 C1 admission failed: " + canonical(checks))

    EVIDENCE.mkdir(parents=True, exist_ok=False)
    audit = {
        "schemaVersion": "bfs.rc6RealImpactParticleRadiusDataComparisonC21C1AuditOnly.v0.1",
        "status": "PASS",
        "checks": checks,
        "checkCount": len(checks),
        "passCount": sum(checks.values()),
        "executionCommit": head,
        "retainedResultHash": result["resultHash"],
        "retainedReceiptHash": receipt["receiptHash"],
        "retainedOriginalAuditHash": original_audit["auditHash"],
        "correctedC19ReceiptHash": c19_receipt["receiptHash"],
        "classification": result["classification"],
        "counts": spec["counts"],
        "claimCeiling": spec["claimCeiling"],
    }
    audit["auditHash"] = self_hash(audit, "auditHash")
    write_exclusive(EVIDENCE / "audit.json", audit)
    retained_after = manifest(RETAINED)
    receipt_out = {
        "schemaVersion": "bfs.rc6RealImpactParticleRadiusDataComparisonC21C1Receipt.v0.1",
        "status": "PASS_AUDIT_ONLY",
        "executionCommit": head,
        "auditHash": audit["auditHash"],
        "retainedAttempt99ManifestBefore": retained_before["manifestHash"],
        "retainedAttempt99ManifestAfter": retained_after["manifestHash"],
        "counts": spec["counts"],
        "claimCeiling": spec["claimCeiling"],
    }
    receipt_out["receiptHash"] = self_hash(receipt_out, "receiptHash")
    write_exclusive(EVIDENCE / "receipt.json", receipt_out)
    write_exclusive(EVIDENCE / "evidence-manifest.json", manifest(EVIDENCE))
    print("RC6_REAL_IMPACT_PARTICLE_RADIUS_DATA_COMPARISON_C21_C1=" + canonical({"status": receipt_out["status"], "classification": audit["classification"], "auditHash": audit["auditHash"], "receiptHash": receipt_out["receiptHash"]}), flush=True)


if __name__ == "__main__":
    main()
