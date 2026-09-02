#!/usr/bin/env python3
"""C1 audit: bind measured float32 cup geometry and the frozen effector distance."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-liquid-containment-axis-diagnostic.py")
EXPECTED_BASE_SHA256 = "4ba9db968898102e99bf7726ca9576d924b41ac4572d07056db067697733ffcd"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 containment-axis C1 auditor base identity mismatch")


source = BASE.read_text(encoding="utf-8")
replacements = (
    (
        'SPEC = RESEARCH / "specs/ai-native-studio-rc6-liquid-containment-axis.v0.32.json"',
        'SPEC = RESEARCH / "specs/ai-native-studio-rc6-liquid-containment-axis-audit-c1.v0.33.json"',
        "correction spec",
    ),
    (
        'audit_path = EVIDENCE / "independent-audit.json"',
        'audit_path = EVIDENCE / "independent-audit-c1.json"',
        "fresh C1 audit path",
    ),
    (
        '''        "cupRawMeshRadialZHistogram": {
            "0.00000000@-0.22000000": 1, "0.00000000@-0.16000000": 1,
            "0.09000000@-0.16000000": 64, "0.09000000@0.22000000": 64,
            "0.15000000@-0.22000000": 64, "0.15000000@0.22000000": 64,
        },
        "cupEffectorSurfaceDistance": 0.0015,''',
        '''        "cupRawMeshRadialZHistogram": {
            "0.00000000@-0.16000000": 1, "0.00000000@-0.22000000": 1,
            "0.09000000@-0.16000000": 64, "0.09000000@0.22000000": 64,
            "0.14999999@-0.22000000": 8, "0.14999999@0.22000000": 8,
            "0.15000000@-0.22000000": 52, "0.15000000@0.22000000": 52,
            "0.15000001@-0.22000000": 4, "0.15000001@0.22000000": 4,
        },
        "cupEffectorSurfaceDistance": 1.5,''',
        "measured configuration",
    ),
    (
        '"bfs.rc6LiquidContainmentAxisIndependentAudit.v0.1"',
        '"bfs.rc6LiquidContainmentAxisIndependentAudit.v0.2"',
        "schema",
    ),
    (
        '    commit = admission["researchCommit"]',
        '    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.strip()',
        "correction commit source",
    ),
    (
        '    check("committedToolAndSpecBytesExact", committed_exact, checks)',
        '''    check("committedToolAndSpecBytesExact", committed_exact, checks)
    correction_parent = subprocess.run(["git", "rev-parse", "HEAD^"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.strip()
    base_audit = read_json(EVIDENCE / "independent-audit.json")
    check("auditCorrectionParentExact", correction_parent == spec["auditCorrection"]["parentCommit"], checks)
    check("retainedBaseAuditFailure", sha(EVIDENCE / "independent-audit.json") == spec["auditCorrection"]["baseAuditFileSha256"] and base_audit.get("auditHash") == spec["auditCorrection"]["baseAuditHash"] and base_audit.get("status") == "FAIL" and base_audit.get("checksPassed") == 23 and base_audit.get("checksTotal") == 24 and base_audit.get("checks", {}).get("configurationExact") is False, checks)''',
        "correction cross-binding",
    ),
)
for before, after, label in replacements:
    if source.count(before) != 1:
        raise RuntimeError(f"RC6 containment-axis C1 auditor {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#CONTAINMENT_AXIS_AUDIT_C1_V02", "exec"), globals(), globals())
