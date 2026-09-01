#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""PC6 C5 audit-only correction over immutable attempt-05 product evidence."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
BASE_AUDITOR = ROOT / "scripts/audit-pc6-causal-productization.py"
C5_SPEC = ROOT / "specs/ai-native-studio-pc6-causal-contract-productization-c5-preregistration.v0.6.json"
C5_FREEZE = ROOT / "specs/ai-native-studio-pc6-causal-contract-productization-c5-tool-freeze.v0.6.json"
EVIDENCE05 = ROOT / "experiments/causal-productization/PC6-2026-09-01-attempt-05"
EVIDENCE06 = ROOT / "experiments/causal-productization/PC6-2026-09-01-attempt-06"
EXTERNAL05 = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/PC6-2026-09-01-attempt-05")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def valid_self(value, field):
    expected = value.get(field)
    body = dict(value)
    body.pop(field, None)
    return expected == hashlib.sha256(canonical(body)).hexdigest()


def write_json(path, body, field):
    value = dict(body)
    value[field] = hashlib.sha256(canonical(body)).hexdigest()
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return value


spec = json.loads(C5_SPEC.read_text(encoding="utf-8"))
freeze = json.loads(C5_FREEZE.read_text(encoding="utf-8"))
if not valid_self(spec, "specHash") or not valid_self(freeze, "freezeHash") or any(sha256_file(ROOT / row["uri"]) != row["sha256"] for row in freeze["tools"]):
    raise RuntimeError("PC6 C5 bindings differ")
retained = spec["retainedProductAttempt05"]
bindings = {
    "productReceiptSha256": sha256_file(EVIDENCE05 / "receipt.json"),
    "c4ReceiptSha256": sha256_file(EVIDENCE05 / "c4-receipt.json"),
    "buildSha256": sha256_file(EVIDENCE05 / "build.json"),
    "reopenSha256": sha256_file(EVIDENCE05 / "reopen.json"),
    "negativeControlsSha256": sha256_file(EVIDENCE05 / "negative-controls.json"),
    "auditFailureFileSha256": sha256_file(EVIDENCE05 / "audit-failure.json"),
    "binarySha256": sha256_file(EXTERNAL05 / "build/bin/Film Studio Engine F0.app/Contents/MacOS/Blender"),
}
if any(bindings[key] != retained[key] for key in bindings):
    raise RuntimeError("PC6 attempt-05 retained product evidence differs")
failure = json.loads((EVIDENCE05 / "audit-failure.json").read_text(encoding="utf-8"))
if not valid_self(failure, "failureHash") or failure["failureHash"] != retained["auditFailureHash"]:
    raise RuntimeError("PC6 attempt-05 audit failure differs")
if EVIDENCE06.exists():
    raise RuntimeError("PC6 attempt-06 audit root is not fresh")
EVIDENCE06.mkdir(parents=True)
base_source = BASE_AUDITOR.read_text(encoding="utf-8")
attempt05_source = base_source.replace("PC6-2026-09-01-attempt-01", "PC6-2026-09-01-attempt-05")
old_gate = 'gate("A17_REOPEN_EXACT", reopen["status"] == "PASS" and reopen["responseFramesExact"] and max(reopen["finalTiltDeltaDegrees"].values()) <= prereg["positiveValidation"]["reopenFinalTiltToleranceDegrees"])'
new_gate = 'gate("A17_REOPEN_EXACT", reopen["status"] == "PASS" and reopen["responseFramesExact"] and prereg["positiveValidation"]["reopenExact"] is True and all(value == 0.0 for value in reopen["finalTiltDeltaDegrees"].values()))'
old_output = '(EVIDENCE / "independent-audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\\n", encoding="utf-8")'
new_output = '(OUTPUT / "independent-audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\\n", encoding="utf-8")'
if attempt05_source.count(old_gate) != 1 or attempt05_source.count(old_output) != 1:
    raise RuntimeError("PC6 base auditor correction sites differ")
corrected_source = attempt05_source.replace(old_gate, new_gate).replace(old_output, new_output)
namespace = {"__file__": str(BASE_AUDITOR), "__name__": "pc6_base_auditor_c5", "OUTPUT": EVIDENCE06}
exec(compile(corrected_source, str(BASE_AUDITOR), "exec"), namespace)
base_audit = json.loads((EVIDENCE06 / "independent-audit.json").read_text(encoding="utf-8"))
product = json.loads((EVIDENCE05 / "receipt.json").read_text(encoding="utf-8"))
c4 = json.loads((EVIDENCE05 / "c4-receipt.json").read_text(encoding="utf-8"))
build = json.loads((EVIDENCE05 / "build.json").read_text(encoding="utf-8"))
reopen = json.loads((EVIDENCE05 / "reopen.json").read_text(encoding="utf-8"))
checks = {
    "retainedProductBindingsExact": all(bindings[key] == retained[key] for key in bindings),
    "retainedAuditFailureExact": failure["failureHash"] == retained["auditFailureHash"],
    "correctedBaseAudit": base_audit["status"] == "PASS" and base_audit["checkPassed"] == base_audit["checkTotal"] == spec["requiredOutcome"]["correctedBaseAuditChecks"],
    "productReceiptPass": valid_self(product, "receiptHash") and product["status"] == "PASS" and all(product["checks"].values()),
    "c4ReceiptPass": valid_self(c4, "c4ReceiptHash") and c4["status"] == "PASS",
    "realBulletProvenance": build["provenance"]["finalPoseSource"] == spec["requiredOutcome"]["finalPoseSource"],
    "noFinalPoseAuthoring": build["provenance"]["targetPoseKeyframes"] == spec["requiredOutcome"]["targetPoseKeyframes"] and build["provenance"]["postReleaseActorPoseKeyframes"] == spec["requiredOutcome"]["postReleaseActorPoseKeyframes"],
    "exactReopen": reopen["status"] == "PASS" and reopen["responseFramesExact"] and all(value == 0.0 for value in reopen["finalTiltDeltaDegrees"].values()),
    "threeReviewImages": len(build["review"]) == spec["requiredOutcome"]["reviewImages"] and all((EVIDENCE05 / row["uri"]).is_file() and sha256_file(EVIDENCE05 / row["uri"]) == row["sha256"] for row in build["review"]),
    "noAdditionalProductExecution": spec["onlyCorrection"]["nativeBuilds"] == spec["onlyCorrection"]["productStarts"] == spec["onlyCorrection"]["sceneMutatingExecutions"] == spec["onlyCorrection"]["renders"] == 0,
    "noForbiddenWrites": spec["onlyCorrection"]["productEvidenceWrites"] == spec["onlyCorrection"]["networkCalls"] == spec["onlyCorrection"]["engineRemoteWrites"] == 0,
}
body = {
    "schemaVersion": "bfs.pc6C5IndependentAudit.v0.6",
    "status": "PASS" if all(checks.values()) else "FAIL",
    "machineVerdict": "PASS" if all(checks.values()) else "FAIL",
    "visualVerdict": "PENDING_DIRECT_SCREENSHOT_REVIEW",
    "overallVerdict": "PENDING_DIRECT_SCREENSHOT_REVIEW",
    "checks": checks,
    "checkPassed": sum(checks.values()),
    "checkTotal": len(checks),
    "correctedBaseAuditHash": base_audit["auditHash"],
    "productReceiptHash": product["receiptHash"],
    "c4ReceiptHash": c4["c4ReceiptHash"],
    "retainedAuditFailureHash": failure["failureHash"],
    "additionalProductStarts": 0,
}
audit = write_json(EVIDENCE06 / "c5-independent-audit.json", body, "c5AuditHash")
print(f"PC6_C5_AUDIT {audit['status']} {audit['checkPassed']}/{audit['checkTotal']} {audit['c5AuditHash']}")
if audit["status"] != "PASS":
    raise SystemExit(1)
