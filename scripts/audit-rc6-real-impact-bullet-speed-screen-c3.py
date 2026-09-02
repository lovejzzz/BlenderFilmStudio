#!/usr/bin/env python3
"""Audit-only C3 closure for the immutable attempt-73 float32 mismatch."""

import hashlib
import json
import subprocess
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
RETAINED = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-bullet-speed-screen-c2-attempt-73"
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-bullet-speed-screen-audit-c3-attempt-74"
SPEC = RESEARCH / "specs/ai-native-studio-rc6-real-impact-bullet-speed-screen-audit-c3.v0.85.json"
CELLS = (("I08", 8), ("I10", 10), ("I12", 12))
EXPECTED_COMMIT_PATHS = {
    "research/2026-09-02-rc6-real-impact-bullet-speed-screen-audit-c3-preregistration.md",
    "research/lab-journal.md",
    "scripts/audit-rc6-real-impact-bullet-speed-screen-c3.py",
    "specs/ai-native-studio-rc6-real-impact-bullet-speed-screen-audit-c3.v0.85.json",
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def self_hash(value, field):
    body = dict(value)
    body.pop(field, None)
    return hashlib.sha256(canonical(body).encode()).hexdigest()


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def root_manifest(root):
    return [
        {"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": sha256(path)}
        for path in sorted(root.rglob("*"))
        if path.is_file()
    ]


def manifest_hash(rows):
    return hashlib.sha256(canonical(rows).encode()).hexdigest()


def within_vector(actual, expected, tolerance):
    return len(actual) == len(expected) and all(abs(a - b) <= tolerance for a, b in zip(actual, expected))


spec = json.loads(SPEC.read_text())
if spec["specHash"] != self_hash(spec, "specHash"):
    raise RuntimeError("real-impact C3 spec self hash mismatch")
if sha256(Path(__file__).resolve()) != spec["tool"]["sha256"]:
    raise RuntimeError("real-impact C3 tool identity mismatch")
if subprocess.run(
    ["git", "status", "--porcelain"], cwd=RESEARCH, capture_output=True, text=True, check=True
).stdout:
    raise RuntimeError("real-impact C3 research worktree is not clean")
head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.strip()
parent = subprocess.run(["git", "rev-parse", "HEAD^"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.strip()
paths = set(
    subprocess.run(
        ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"],
        cwd=RESEARCH,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
)
if parent != spec["researchParentBeforePreregistration"] or paths != EXPECTED_COMMIT_PATHS:
    raise RuntimeError("real-impact C3 preregistration commit binding mismatch")
if EVIDENCE.exists():
    raise RuntimeError("real-impact C3 evidence root is not fresh")

retained_before = root_manifest(RETAINED)
retained_hash_before = manifest_hash(retained_before)
original_audit = json.loads((RETAINED / "independent-audit.json").read_text())
receipt = json.loads((RETAINED / "receipt.json").read_text())
results = [json.loads((RETAINED / "cells" / cell / "result.json").read_text()) for cell, _ in CELLS]
tolerance = spec["representationTolerance"]

configuration_corrected = True
for row, (cell_id, drive_end) in zip(results, CELLS):
    config = row["configuration"]
    configuration_corrected &= (
        row["cellId"] == cell_id
        and config["driveEndFrame"] == drive_end
        and config["frameStart"] == 1
        and config["frameEnd"] == 48
        and config["fps"] == 24
        and config["bulletSubstepsPerFrame"] == 20
        and config["bulletSolverIterations"] == 80
        and config["previewResolution"] == 96
        and within_vector(config["acceptedDomainCenterMeters"], [0.45, 0.0, 0.26], tolerance)
        and within_vector(config["acceptedDomainDimensionsMeters"], [0.9, 0.5, 0.58], tolerance)
        and abs(config["baseVoxelMeters"] - 0.009375) <= tolerance
        and abs(config["cupCollisionRadiusMeters"] - 0.15) <= tolerance
        and abs(config["cupCollisionHalfHeightMeters"] - 0.22) <= tolerance
        and abs(config["ballCollisionRadiusMeters"] - 0.12) <= tolerance
    )

expected_physical = {
    "I08": {"contact": 17, "peak": 90.14820695, "surface": 0.09684497, "subframes": 11},
    "I10": {"contact": 21, "peak": 9.97081942, "surface": 0.042258, "subframes": 5},
    "I12": {"contact": 25, "peak": 10.14016409, "surface": 0.03722252, "subframes": 4},
}
physical_exact = all(
    row["status"] == "FAIL"
    and row["metrics"]["derivedContactFrame"] == expected_physical[row["cellId"]]["contact"]
    and abs(row["metrics"]["peakCupTiltDegrees"] - expected_physical[row["cellId"]]["peak"]) <= 1e-8
    and abs(row["metrics"]["maximumCupSurfaceDisplacementPerFrameMeters"] - expected_physical[row["cellId"]]["surface"]) <= 1e-8
    and row["metrics"]["requiredEffectorSubframes"] == expected_physical[row["cellId"]]["subframes"]
    for row in results
)
checks = {
    "specSelfHash": spec["specHash"] == self_hash(spec, "specHash"),
    "toolIdentity": sha256(Path(__file__).resolve()) == spec["tool"]["sha256"],
    "executionCommitBound": head
    == subprocess.run(["git", "rev-parse", "HEAD"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.strip()
    and parent == spec["researchParentBeforePreregistration"]
    and paths == EXPECTED_COMMIT_PATHS,
    "retainedRootManifestExact": retained_hash_before == spec["retainedAttempt73"]["rootManifestHash"]
    and len(retained_before) == spec["retainedAttempt73"]["fileCount"]
    and sum(row["bytes"] for row in retained_before) == spec["retainedAttempt73"]["bytes"],
    "retainedReceiptExact": sha256(RETAINED / "receipt.json") == spec["retainedAttempt73"]["receiptFileSha256"]
    and receipt["receiptHash"] == spec["retainedAttempt73"]["receiptHash"]
    and receipt["receiptHash"] == self_hash(receipt, "receiptHash"),
    "retainedAuditExact": sha256(RETAINED / "independent-audit.json")
    == spec["retainedAttempt73"]["auditFileSha256"]
    and original_audit["auditHash"] == spec["retainedAttempt73"]["auditHash"]
    and original_audit["auditHash"] == self_hash(original_audit, "auditHash"),
    "soleOriginalAuditFailureIdentified": original_audit["status"] == "FAIL"
    and original_audit["passCount"] == 22
    and original_audit["checkCount"] == 23
    and [key for key, value in original_audit["checks"].items() if not value]
    == ["cellRosterAndConfigurationExact"],
    "allOtherOriginalChecksPass": all(
        value for key, value in original_audit["checks"].items() if key != "cellRosterAndConfigurationExact"
    ),
    "cellResultSelfHashesExact": all(row["resultHash"] == self_hash(row, "resultHash") for row in results),
    "float32ConfigurationCorrectedWithinOneEminusSix": configuration_corrected,
    "physicalFailureRemainsExact": physical_exact
    and receipt["status"] == "FAIL"
    and receipt["verdict"] == "FAIL_REAL_IMPACT_BULLET_TRAJECTORY"
    and receipt["selectedCellId"] is None,
    "auditOnlyZeroExecution": spec["auditOnlyCeilings"]
    == {"blenderStarts": 0, "bulletBakes": 0, "fluidBakes": 0, "renders": 0, "saves": 0, "networkCalls": 0},
}
retained_after = root_manifest(RETAINED)
checks["retainedRootUnchanged"] = retained_after == retained_before and manifest_hash(retained_after) == retained_hash_before
audit = {
    "schemaVersion": "bfs.rc6RealImpactBulletSpeedScreenAuditC3.v0.1",
    "status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "checkCount": len(checks),
    "passCount": sum(checks.values()),
    "physicalVerdict": "FAIL_REAL_IMPACT_BULLET_TRAJECTORY",
    "retainedRootManifestHashBefore": retained_hash_before,
    "retainedRootManifestHashAfter": manifest_hash(retained_after),
    "representationTolerance": tolerance,
    "nextPhysicalQuestion": "driveEndFrame 9 only",
    "counts": spec["auditOnlyCeilings"],
}
audit["auditHash"] = self_hash(audit, "auditHash")
EVIDENCE.mkdir(parents=True, exist_ok=False)
with (EVIDENCE / "corrected-independent-audit.json").open("x", encoding="utf-8") as handle:
    json.dump(audit, handle, indent=2, sort_keys=True)
    handle.write("\n")
evidence_manifest = root_manifest(EVIDENCE)
with (EVIDENCE / "evidence-manifest.json").open("x", encoding="utf-8") as handle:
    json.dump({"root": str(EVIDENCE), "files": evidence_manifest}, handle, indent=2, sort_keys=True)
    handle.write("\n")
print("RC6_REAL_IMPACT_BULLET_SPEED_SCREEN_AUDIT_C3=" + canonical(audit))
if audit["status"] != "PASS":
    raise RuntimeError("real-impact C3 audit-only correction failed")
