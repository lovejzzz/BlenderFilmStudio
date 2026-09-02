#!/usr/bin/env python3
"""C5 audit-only adapter for the immutable I09 attempt-75 root."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-real-impact-bullet-speed-screen-c3.py")
EXPECTED_BASE_SHA256 = "b430e9e922b191b39907375c385ce221c69b79319341620593e2c019432c1201"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("real-impact C5 auditor base identity mismatch")
source = BASE.read_text(encoding="utf-8")
old_physical = '''expected_physical = {
    "I08": {"contact": 17, "peak": 90.14820695, "surface": 0.09684497, "subframes": 11},
    "I10": {"contact": 21, "peak": 9.97081942, "surface": 0.042258, "subframes": 5},
    "I12": {"contact": 25, "peak": 10.14016409, "surface": 0.03722252, "subframes": 4},
}'''
new_physical = '''expected_physical = {
    "I09": {"contact": 19, "peak": 90.0007237, "surface": 0.09684143, "subframes": 11},
}'''
replacements = (
    ("RC6-2026-09-02-real-impact-bullet-speed-screen-c2-attempt-73", "RC6-2026-09-02-real-impact-bullet-midpoint-c4-attempt-75", 1, "retained root"),
    ("RC6-2026-09-02-real-impact-bullet-speed-screen-audit-c3-attempt-74", "RC6-2026-09-02-real-impact-bullet-midpoint-audit-c5-attempt-76", 1, "fresh root"),
    ("specs/ai-native-studio-rc6-real-impact-bullet-speed-screen-audit-c3.v0.85.json", "specs/ai-native-studio-rc6-real-impact-bullet-midpoint-audit-c5.v0.87.json", 2, "spec"),
    ('CELLS = (("I08", 8), ("I10", 10), ("I12", 12))', 'CELLS = (("I09", 9),)', 1, "cells"),
    ("research/2026-09-02-rc6-real-impact-bullet-speed-screen-audit-c3-preregistration.md", "research/2026-09-02-rc6-real-impact-bullet-midpoint-audit-c5-preregistration.md", 1, "preregistration"),
    ("scripts/audit-rc6-real-impact-bullet-speed-screen-c3.py", "scripts/audit-rc6-real-impact-bullet-midpoint-c5.py", 1, "tool path"),
    ("retainedAttempt73", "retainedAttempt75", 7, "retained spec key"),
    (old_physical, new_physical, 1, "physical metrics"),
    ("driveEndFrame 9 only", "inspect cup collision margin and visible/collision congruence", 1, "next question"),
    ("bfs.rc6RealImpactBulletSpeedScreenAuditC3.v0.1", "bfs.rc6RealImpactBulletMidpointAuditC5.v0.1", 1, "schema"),
    ("RC6_REAL_IMPACT_BULLET_SPEED_SCREEN_AUDIT_C3=", "RC6_REAL_IMPACT_BULLET_MIDPOINT_AUDIT_C5=", 1, "marker"),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"real-impact C5 auditor {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#C5_I09_AUDIT", "exec"), globals(), globals())
