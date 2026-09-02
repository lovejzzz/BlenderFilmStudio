#!/usr/bin/env python3
"""Audit retained R40 samples for a bounded contact-to-first-70-degree fluid window."""

import hashlib
import json
import math
import subprocess
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
RETAINED = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-passive-ramp-c10-attempt-82"
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-event-window-c11-attempt-83"
SPEC = RESEARCH / "specs/ai-native-studio-rc6-real-impact-event-window-c11.v0.94.json"
EXPECTED_COMMIT_PATHS = {
    "research/2026-09-02-rc6-real-impact-event-window-c11-preregistration.md",
    "research/lab-journal.md",
    "scripts/audit-rc6-real-impact-event-window-c11.py",
    "specs/ai-native-studio-rc6-real-impact-event-window-c11.v0.94.json",
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
        for path in sorted(root.rglob("*")) if path.is_file()
    ]


spec = json.loads(SPEC.read_text())
if spec["specHash"] != self_hash(spec, "specHash"):
    raise RuntimeError("event-window C11 spec self hash mismatch")
if sha256(Path(__file__).resolve()) != spec["tool"]["sha256"]:
    raise RuntimeError("event-window C11 tool identity mismatch")
if subprocess.run(["git", "status", "--porcelain"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout:
    raise RuntimeError("event-window C11 research worktree is not clean")
head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.strip()
parent = subprocess.run(["git", "rev-parse", "HEAD^"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.strip()
paths = set(subprocess.run(["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.splitlines())
if parent != spec["researchParentBeforePreregistration"] or paths != EXPECTED_COMMIT_PATHS:
    raise RuntimeError("event-window C11 preregistration commit binding mismatch")
if EVIDENCE.exists():
    raise RuntimeError("event-window C11 evidence root is not fresh")

before = root_manifest(RETAINED)
before_hash = hashlib.sha256(canonical(before).encode()).hexdigest()
result_path = RETAINED / "cells/R40/result.json"
audit_path = RETAINED / "independent-audit.json"
receipt_path = RETAINED / "receipt.json"
result = json.loads(result_path.read_text())
original_audit = json.loads(audit_path.read_text())
receipt = json.loads(receipt_path.read_text())
samples = result["samples"]
contact = next((row["frame"] for row in samples if row["ballCupCollisionSurfaceSeparationMeters"] <= 0.01), None)
first_70 = next((row["frame"] for row in samples if row["cupTiltDegrees"] >= 70.0), None)
event_samples = [row for row in samples if first_70 is not None and row["frame"] <= first_70]
maximum_surface = max(row["cupSurfaceDisplacementFromPriorFrameMeters"] for row in event_samples)
base_voxel = 0.009375
required_subframes = max(1, math.ceil(maximum_surface / base_voxel - 1e-10))
swept_low = [min(row["cupBoundsMin"][axis] for row in event_samples) for axis in range(3)]
swept_high = [max(row["cupBoundsMax"][axis] for row in event_samples) for axis in range(3)]
domain_center = [0.57, 0.0, 0.26]
domain_dimensions = [0.9, 0.5, 0.58]
domain_low = [domain_center[i] - domain_dimensions[i] * 0.5 for i in range(3)]
domain_high = [domain_center[i] + domain_dimensions[i] * 0.5 for i in range(3)]
contained = all(
    swept_low[i] >= domain_low[i] + base_voxel
    and swept_high[i] <= domain_high[i] - base_voxel
    for i in range(3)
)
checks = {
    "specSelfHash": spec["specHash"] == self_hash(spec, "specHash"),
    "toolIdentity": sha256(Path(__file__).resolve()) == spec["tool"]["sha256"],
    "executionCommitBound": parent == spec["researchParentBeforePreregistration"] and paths == EXPECTED_COMMIT_PATHS,
    "retainedRootManifestExact": before_hash == spec["retainedAttempt82"]["rootManifestHash"] and len(before) == spec["retainedAttempt82"]["fileCount"] and sum(row["bytes"] for row in before) == spec["retainedAttempt82"]["bytes"],
    "retainedFilesExact": sha256(result_path) == spec["retainedAttempt82"]["resultFileSha256"] and sha256(receipt_path) == spec["retainedAttempt82"]["receiptFileSha256"] and sha256(audit_path) == spec["retainedAttempt82"]["auditFileSha256"],
    "retainedSelfHashesExact": result["resultHash"] == self_hash(result, "resultHash") and receipt["receiptHash"] == self_hash(receipt, "receiptHash") and original_audit["auditHash"] == self_hash(original_audit, "auditHash"),
    "originalFullWindowFailurePreserved": result["status"] == "FAIL" and receipt["verdict"] == "FAIL_REAL_IMPACT_BULLET_TRAJECTORY" and original_audit["status"] == "PASS" and original_audit["passCount"] == 23,
    "eventFramesDerived": contact == 19 and first_70 == 36 and len(event_samples) == 36,
    "causalRaisedContactAndTipPreserved": result["metrics"]["contactBallCenterZMeters"] >= 0.38 and result["metrics"]["firstFortyFiveDegreeFrame"] >= contact and result["metrics"]["peakCupTiltDegrees"] >= 45.0,
    "eventSurfaceMotionExact": abs(maximum_surface - 0.07210387) <= 1e-8,
    "eventSubframeCeiling": required_subframes == 8,
    "sameSizeShiftedDomain": domain_dimensions == [0.9, 0.5, 0.58] and domain_center == [0.57, 0.0, 0.26],
    "eventSweepContainedWithOneVoxelMargin": contained,
    "noLiquidCompletionClaim": spec["claimCeiling"].startswith("Eligibility only"),
    "auditOnlyZeroExecution": spec["auditOnlyCeilings"] == {"blenderStarts": 0, "bulletBakes": 0, "fluidBakes": 0, "renders": 0, "saves": 0, "networkCalls": 0},
}
after = root_manifest(RETAINED)
checks["retainedRootUnchanged"] = after == before and hashlib.sha256(canonical(after).encode()).hexdigest() == before_hash
record = {
    "schemaVersion": "bfs.rc6RealImpactEventWindowC11Audit.v0.1",
    "status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "checkCount": len(checks),
    "passCount": sum(checks.values()),
    "retainedFullWindowVerdict": "FAIL_REAL_IMPACT_BULLET_TRAJECTORY",
    "eventWindow": {
        "frameStart": 1,
        "derivedContactFrame": contact,
        "derivedFirstSeventyDegreeFrame": first_70,
        "frameEnd": first_70,
        "maximumSurfaceDisplacementMeters": maximum_surface,
        "requiredPreview96EffectorSubframes": required_subframes,
        "sweptCupBoundsMin": swept_low,
        "sweptCupBoundsMax": swept_high,
        "candidateDomainCenterMeters": domain_center,
        "unchangedDomainDimensionsMeters": domain_dimensions,
        "containedWithOneVoxelMargin": contained,
    },
    "claimCeiling": spec["claimCeiling"],
    "counts": spec["auditOnlyCeilings"],
}
record["auditHash"] = self_hash(record, "auditHash")
EVIDENCE.mkdir(parents=True, exist_ok=False)
with (EVIDENCE / "event-window-audit.json").open("x", encoding="utf-8") as handle:
    json.dump(record, handle, indent=2, sort_keys=True)
    handle.write("\n")
manifest = root_manifest(EVIDENCE)
with (EVIDENCE / "evidence-manifest.json").open("x", encoding="utf-8") as handle:
    json.dump({"root": str(EVIDENCE), "files": manifest}, handle, indent=2, sort_keys=True)
    handle.write("\n")
print("RC6_REAL_IMPACT_EVENT_WINDOW_C11=" + canonical(record))
if record["status"] != "PASS":
    raise RuntimeError("event-window C11 audit failed")
