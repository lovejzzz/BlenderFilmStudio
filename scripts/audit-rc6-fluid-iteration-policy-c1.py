#!/usr/bin/env python3
"""C1 audit-only correction for the retained attempt-35 cleanliness check."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-fluid-iteration-policy.py")
EXPECTED_BASE_SHA256 = "e50a23e403cacccf0c01a6a3d8a1e4c8f061af28424c87700e19bfdc7721eb16"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 fluid-policy C1 auditor base identity mismatch")


source = BASE.read_text(encoding="utf-8")
replacements = (
    (
        'EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-01-fluid-policy-attempt-35"',
        'RETAINED_EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-01-fluid-policy-attempt-35"\nEVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-01-fluid-policy-audit-c1-attempt-36"',
        1,
        "roots",
    ),
    (
        'SPEC = RESEARCH / "specs/ai-native-studio-rc6-fluid-iteration-policy-tool-freeze.v0.37.json"',
        'SPEC = RESEARCH / "specs/ai-native-studio-rc6-fluid-iteration-policy-audit-c1.v0.38.json"',
        1,
        "spec",
    ),
    (
        '''    audit_path = EVIDENCE / "independent-audit.json"
    if audit_path.exists():
        raise RuntimeError("fluid-policy audit path is not fresh")
    spec = read_json(SPEC)
    receipt = read_json(EVIDENCE / "receipt.json")
    checks = {}''',
        '''    audit_path = EVIDENCE / "independent-audit.json"
    if EVIDENCE.exists():
        raise RuntimeError("fluid-policy C1 audit root is not fresh")
    research_status_before = git("status", "--porcelain", cwd=RESEARCH).strip()
    source_status_before = git("status", "--porcelain", cwd=SOURCE).strip()
    spec = read_json(SPEC)
    receipt = read_json(RETAINED_EVIDENCE / "receipt.json")
    retained_audit = read_json(RETAINED_EVIDENCE / "independent-audit.json")
    EVIDENCE.mkdir(parents=True, exist_ok=False)
    checks = {}''',
        1,
        "audit admission",
    ),
    (
        '    check("sourceTreesClean", not git("status", "--porcelain", cwd=RESEARCH).strip() and not git("status", "--porcelain", cwd=SOURCE).strip(), checks)',
        '    check("sourceTreesCleanAtC1Admission", not research_status_before and not source_status_before, checks)',
        1,
        "cleanliness timing",
    ),
    (
        '    research_commit = receipt.get("researchCommit")',
        '    research_commit = git("rev-parse", "HEAD", cwd=RESEARCH).strip()',
        1,
        "correction commit",
    ),
    (
        '    check("receiptSelfHash", receipt.get("status") == "PASS" and receipt.get("receiptHash") == self_hash(receipt, "receiptHash"), checks)',
        '''    check("receiptSelfHash", receipt.get("status") == "PASS" and receipt.get("receiptHash") == self_hash(receipt, "receiptHash"), checks)
    check("retainedAttempt35FailureExact", sha(RETAINED_EVIDENCE / "receipt.json") == spec["retainedAttempt35"]["receiptFileSha256"] and receipt.get("receiptHash") == spec["retainedAttempt35"]["receiptHash"] and sha(RETAINED_EVIDENCE / "independent-audit.json") == spec["retainedAttempt35"]["auditFileSha256"] and retained_audit.get("auditHash") == spec["retainedAttempt35"]["auditHash"] and retained_audit.get("status") == "FAIL" and retained_audit.get("checksPassed") == 14 and retained_audit.get("checksTotal") == 15 and retained_audit.get("checks", {}).get("sourceTreesClean") is False and sum(value is False for value in retained_audit.get("checks", {}).values()) == 1, checks)''',
        1,
        "retained failure binding",
    ),
    ("bfs.rc6FluidIterationPolicyIndependentAudit.v0.1", "bfs.rc6FluidIterationPolicyIndependentAudit.v0.2", 1, "schema"),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"RC6 fluid-policy C1 auditor {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#FLUID_POLICY_AUDIT_C1_V02", "exec"), globals(), globals())
