#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Independent PC6 C4 audit for the accepted post-build bundle rename."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
BASE_AUDITOR = ROOT / "scripts/audit-pc6-causal-productization.py"
C4_SPEC = ROOT / "specs/ai-native-studio-pc6-causal-contract-productization-c4-preregistration.v0.5.json"
C4_FREEZE = ROOT / "specs/ai-native-studio-pc6-causal-contract-productization-c4-tool-freeze.v0.5.json"
ATTEMPT04 = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/PC6-2026-09-01-attempt-04")
ATTEMPT05 = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/PC6-2026-09-01-attempt-05")
EVIDENCE04 = ROOT / "experiments/causal-productization/PC6-2026-09-01-attempt-04"
EVIDENCE05 = ROOT / "experiments/causal-productization/PC6-2026-09-01-attempt-05"


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


spec = json.loads(C4_SPEC.read_text(encoding="utf-8"))
freeze = json.loads(C4_FREEZE.read_text(encoding="utf-8"))
if not valid_self(spec, "specHash") or not valid_self(freeze, "freezeHash") or any(sha256_file(ROOT / row["uri"]) != row["sha256"] for row in freeze["tools"]):
    raise RuntimeError("PC6 C4 bindings differ")
retained = spec["retainedAttempt04"]
retained_binary = ATTEMPT04 / "build/bin/Blender.app/Contents/MacOS/Blender"
retained_exact = (
    sha256_file(EVIDENCE04 / "failure.json") == retained["failureFileSha256"]
    and sha256_file(EVIDENCE04 / "logs/build.stdout.log") == retained["buildStdoutSha256"]
    and sha256_file(EVIDENCE04 / "logs/build.stderr.log") == retained["buildStderrSha256"]
    and sha256_file(retained_binary) == retained["builtBinarySha256"]
)
base_source = BASE_AUDITOR.read_text(encoding="utf-8")
attempt05_source = base_source.replace("PC6-2026-09-01-attempt-01", "PC6-2026-09-01-attempt-05")
namespace = {"__file__": str(BASE_AUDITOR), "__name__": "pc6_base_auditor_c4"}
exec(compile(attempt05_source, str(BASE_AUDITOR), "exec"), namespace)
base_audit = json.loads((EVIDENCE05 / "independent-audit.json").read_text(encoding="utf-8"))
receipt = json.loads((EVIDENCE05 / "c4-receipt.json").read_text(encoding="utf-8"))
bundle = receipt["bundle"]
checks = {
    "retainedAttempt04Exact": retained_exact,
    "explicitLibdirExact": receipt["buildCmakeArgument"] == spec["buildInput"]["argument"],
    "gitlinkIndexExact": receipt["gitlinkIndex"] == f"160000 {spec['buildInput']['gitlinkCommit']} 0\tlib/macos_arm64",
    "gitlinkUnchanged": receipt["gitlinkMutations"] == 0 and receipt["dependencySymlinks"] == 0,
    "singleBundleRename": bundle["operationCount"] == 1 and bundle["sourceAbsentAfterRename"] and bundle["productPresentAfterRename"],
    "bundleIdentityExact": bundle["cfBundleName"] == bundle["cfBundleDisplayName"] == "Film Studio Engine F0" and bundle["cfBundleIdentifier"] == "studio.ainativefilm.f0",
    "baseMachineAudit": base_audit["status"] == "PASS" and base_audit["checkPassed"] == base_audit["checkTotal"],
    "dependencyRetainedClean": receipt["dependencyHeadAfterBuild"] == spec["buildInput"]["gitlinkCommit"] and receipt["dependencyCleanAfterBuild"],
    "noNetworkDependencyOrRemoteWrite": receipt["dependencyNetworkCalls"] == receipt["dependencyWrites"] == receipt["engineRemoteWrites"] == 0,
    "productBinaryExists": (ATTEMPT05 / spec["onlyCorrection"]["productBundle"] / "Contents/MacOS/Blender").is_file(),
}
body = {
    "schemaVersion": "bfs.pc6C4IndependentAudit.v0.5",
    "status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "checkPassed": sum(checks.values()),
    "checkTotal": len(checks),
    "baseAuditHash": base_audit["auditHash"],
    "c4ReceiptHash": receipt["c4ReceiptHash"],
    "retainedAttempt04FailureHash": retained["failureHash"],
}
audit = dict(body)
audit["c4AuditHash"] = hashlib.sha256(canonical(body)).hexdigest()
(EVIDENCE05 / "c4-independent-audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(f"PC6_C4_AUDIT {audit['status']} {audit['checkPassed']}/{audit['checkTotal']} {audit['c4AuditHash']}")
if audit["status"] != "PASS":
    raise SystemExit(1)
