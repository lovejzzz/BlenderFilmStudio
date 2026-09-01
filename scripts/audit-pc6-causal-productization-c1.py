#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Independent PC6 C1 audit binding the retained failure and one correction."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
BASE_AUDITOR = ROOT / "scripts/audit-pc6-causal-productization.py"
C1_SPEC = ROOT / "specs/ai-native-studio-pc6-causal-contract-productization-c1-preregistration.v0.2.json"
C1_FREEZE = ROOT / "specs/ai-native-studio-pc6-causal-contract-productization-c1-tool-freeze.v0.2.json"
EVIDENCE01 = ROOT / "experiments/causal-productization/PC6-2026-09-01-attempt-01"
EVIDENCE02 = ROOT / "experiments/causal-productization/PC6-2026-09-01-attempt-02"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def sha256_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def valid_self(value, field):
    expected = value.get(field)
    body = dict(value)
    body.pop(field, None)
    return expected == hashlib.sha256(canonical(body)).hexdigest()


spec = json.loads(C1_SPEC.read_text(encoding="utf-8"))
freeze = json.loads(C1_FREEZE.read_text(encoding="utf-8"))
if not valid_self(spec, "specHash") or not valid_self(freeze, "freezeHash"):
    raise RuntimeError("PC6 C1 spec/tool freeze invalid")
if any(sha256_file(ROOT / row["uri"]) != row["sha256"] for row in freeze["tools"]):
    raise RuntimeError("PC6 C1 tool binding differs")
retained = spec["retainedAttempt01"]
retained_exact = (
    sha256_file(EVIDENCE01 / "failure.json") == retained["failureFileSha256"]
    and sha256_file(EVIDENCE01 / "logs/build.stdout.log") == retained["buildStdoutSha256"]
    and sha256_file(EVIDENCE01 / "logs/build.stderr.log") == retained["buildStderrSha256"]
)
base_source = BASE_AUDITOR.read_text(encoding="utf-8")
attempt02_source = base_source.replace("PC6-2026-09-01-attempt-01", "PC6-2026-09-01-attempt-02")
namespace = {"__file__": str(BASE_AUDITOR), "__name__": "pc6_base_auditor_c1"}
exec(compile(attempt02_source, str(BASE_AUDITOR), "exec"), namespace)
base_audit = json.loads((EVIDENCE02 / "independent-audit.json").read_text(encoding="utf-8"))
c1_receipt = json.loads((EVIDENCE02 / "c1-receipt.json").read_text(encoding="utf-8"))
checks = {
    "retainedAttempt01Exact": retained_exact,
    "oneCorrection": c1_receipt["correction"] == "ONE_LOCAL_PRECOMPILED_DEPENDENCY_DIRECTORY_SYMLINK",
    "dependencyTargetSymlink": c1_receipt["dependencyTargetIsSymlink"] is True,
    "representativeObjectExact": c1_receipt["representativeObjectSha256"] == spec["onlyCorrection"]["representativeObjectSha256"],
    "baseMachineAudit": base_audit["status"] == "PASS" and base_audit["checkPassed"] == base_audit["checkTotal"],
    "noNetworkOrDependencyWrite": c1_receipt["networkDependencyAcquisition"] == c1_receipt["dependencyWrites"] == c1_receipt["engineRemoteWrites"] == 0,
}
body = {
    "schemaVersion": "bfs.pc6C1IndependentAudit.v0.2",
    "status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "checkPassed": sum(checks.values()),
    "checkTotal": len(checks),
    "baseAuditHash": base_audit["auditHash"],
    "c1ReceiptHash": c1_receipt["c1ReceiptHash"],
    "retainedAttempt01FailureHash": retained["failureHash"],
}
audit = dict(body)
audit["c1AuditHash"] = hashlib.sha256(canonical(body)).hexdigest()
(EVIDENCE02 / "c1-independent-audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(f"PC6_C1_AUDIT {audit['status']} {audit['checkPassed']}/{audit['checkTotal']} {audit['c1AuditHash']}")
if audit["status"] != "PASS":
    raise SystemExit(1)
