#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Independent PC6 C2 audit for the empty-directory-only correction."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
BASE_AUDITOR = ROOT / "scripts/audit-pc6-causal-productization.py"
C2_SPEC = ROOT / "specs/ai-native-studio-pc6-causal-contract-productization-c2-preregistration.v0.3.json"
C2_FREEZE = ROOT / "specs/ai-native-studio-pc6-causal-contract-productization-c2-tool-freeze.v0.3.json"
EVIDENCE02 = ROOT / "experiments/causal-productization/PC6-2026-09-01-attempt-02"
EVIDENCE03 = ROOT / "experiments/causal-productization/PC6-2026-09-01-attempt-03"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def sha256_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def valid_self(value, field):
    expected = value.get(field)
    body = dict(value)
    body.pop(field, None)
    return expected == hashlib.sha256(canonical(body)).hexdigest()


spec = json.loads(C2_SPEC.read_text(encoding="utf-8"))
freeze = json.loads(C2_FREEZE.read_text(encoding="utf-8"))
if not valid_self(spec, "specHash") or not valid_self(freeze, "freezeHash") or any(sha256_file(ROOT / row["uri"]) != row["sha256"] for row in freeze["tools"]):
    raise RuntimeError("PC6 C2 bindings differ")
retained = spec["retainedAttempt02"]
retained_exact = sha256_file(EVIDENCE02 / "failure.json") == retained["failureFileSha256"]
base_source = BASE_AUDITOR.read_text(encoding="utf-8")
attempt03_source = base_source.replace("PC6-2026-09-01-attempt-01", "PC6-2026-09-01-attempt-03")
namespace = {"__file__": str(BASE_AUDITOR), "__name__": "pc6_base_auditor_c2"}
exec(compile(attempt03_source, str(BASE_AUDITOR), "exec"), namespace)
base_audit = json.loads((EVIDENCE03 / "independent-audit.json").read_text(encoding="utf-8"))
receipt = json.loads((EVIDENCE03 / "c2-receipt.json").read_text(encoding="utf-8"))
checks = {
    "retainedAttempt02Exact": retained_exact,
    "oneEmptyDirectoryRemoved": receipt["removedEmptyDirectories"] == 1,
    "oneDependencySymlink": receipt["dependencySymlinks"] == 1,
    "baseMachineAudit": base_audit["status"] == "PASS" and base_audit["checkPassed"] == base_audit["checkTotal"],
    "noThresholdChange": freeze["correction"]["thresholdChanges"] == 0,
    "noNetworkDependencyOrRemoteWrite": receipt["networkCalls"] == receipt["dependencyWrites"] == receipt["engineRemoteWrites"] == 0,
}
body = {
    "schemaVersion": "bfs.pc6C2IndependentAudit.v0.3",
    "status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "checkPassed": sum(checks.values()),
    "checkTotal": len(checks),
    "baseAuditHash": base_audit["auditHash"],
    "c2ReceiptHash": receipt["c2ReceiptHash"],
    "retainedAttempt02FailureHash": retained["failureHash"],
}
audit = dict(body)
audit["c2AuditHash"] = hashlib.sha256(canonical(body)).hexdigest()
(EVIDENCE03 / "c2-independent-audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(f"PC6_C2_AUDIT {audit['status']} {audit['checkPassed']}/{audit['checkTotal']} {audit['c2AuditHash']}")
if audit["status"] != "PASS":
    raise SystemExit(1)
