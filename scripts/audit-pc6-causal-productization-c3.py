#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Independent PC6 C3 audit for explicit LIBDIR with intact gitlink."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
BASE_AUDITOR = ROOT / "scripts/audit-pc6-causal-productization.py"
C3_SPEC = ROOT / "specs/ai-native-studio-pc6-causal-contract-productization-c3-preregistration.v0.4.json"
C3_FREEZE = ROOT / "specs/ai-native-studio-pc6-causal-contract-productization-c3-tool-freeze.v0.4.json"
EVIDENCE03 = ROOT / "experiments/causal-productization/PC6-2026-09-01-attempt-03"
EVIDENCE04 = ROOT / "experiments/causal-productization/PC6-2026-09-01-attempt-04"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def sha256_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def valid_self(value, field):
    expected = value.get(field)
    body = dict(value)
    body.pop(field, None)
    return expected == hashlib.sha256(canonical(body)).hexdigest()


spec = json.loads(C3_SPEC.read_text(encoding="utf-8"))
freeze = json.loads(C3_FREEZE.read_text(encoding="utf-8"))
if not valid_self(spec, "specHash") or not valid_self(freeze, "freezeHash") or any(sha256_file(ROOT / row["uri"]) != row["sha256"] for row in freeze["tools"]):
    raise RuntimeError("PC6 C3 bindings differ")
retained = spec["retainedAttempt03"]
retained_exact = sha256_file(EVIDENCE03 / "failure.json") == retained["failureFileSha256"]
base_source = BASE_AUDITOR.read_text(encoding="utf-8")
attempt04_source = base_source.replace("PC6-2026-09-01-attempt-01", "PC6-2026-09-01-attempt-04")
namespace = {"__file__": str(BASE_AUDITOR), "__name__": "pc6_base_auditor_c3"}
exec(compile(attempt04_source, str(BASE_AUDITOR), "exec"), namespace)
base_audit = json.loads((EVIDENCE04 / "independent-audit.json").read_text(encoding="utf-8"))
receipt = json.loads((EVIDENCE04 / "c3-receipt.json").read_text(encoding="utf-8"))
checks = {
    "retainedAttempt03Exact": retained_exact,
    "explicitLibdirExact": receipt["buildCmakeArgument"] == spec["onlyCorrection"]["buildCmakeArgument"],
    "gitlinkIndexExact": receipt["gitlinkIndex"] == f"160000 {retained['gitlinkCommit']} 0\tlib/macos_arm64",
    "gitlinkUnchanged": receipt["gitlinkMutations"] == 0 and receipt["dependencySymlinks"] == 0,
    "baseMachineAudit": base_audit["status"] == "PASS" and base_audit["checkPassed"] == base_audit["checkTotal"],
    "noNetworkDependencyOrRemoteWrite": receipt["dependencyNetworkCalls"] == receipt["dependencyWrites"] == receipt["engineRemoteWrites"] == 0,
}
body = {
    "schemaVersion": "bfs.pc6C3IndependentAudit.v0.4",
    "status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "checkPassed": sum(checks.values()),
    "checkTotal": len(checks),
    "baseAuditHash": base_audit["auditHash"],
    "c3ReceiptHash": receipt["c3ReceiptHash"],
    "retainedAttempt03FailureHash": retained["failureHash"],
}
audit = dict(body)
audit["c3AuditHash"] = hashlib.sha256(canonical(body)).hexdigest()
(EVIDENCE04 / "c3-independent-audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(f"PC6_C3_AUDIT {audit['status']} {audit['checkPassed']}/{audit['checkTotal']} {audit['c3AuditHash']}")
if audit["status"] != "PASS":
    raise SystemExit(1)
