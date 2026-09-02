#!/usr/bin/env python3
"""C4 independent-auditor adapter for single I09 and float32 tolerance."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-real-impact-bullet-speed-screen.py")
EXPECTED_BASE_SHA256 = "9bc233e999aee4a6e4df83b31be233fbbad57103013701562355d49dff2a76a4"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("real-impact C4 auditor base identity mismatch")
source = BASE.read_text(encoding="utf-8")
replacements = (
    ("RC6-2026-09-02-real-impact-bullet-speed-screen-attempt-71", "RC6-2026-09-02-real-impact-bullet-midpoint-c4-attempt-75", 2, "fresh roots"),
    ('CELLS = (("I08", 8), ("I10", 10), ("I12", 12))', 'CELLS = (("I09", 9),)', 1, "cell roster"),
    ("scripts/run-rc6-real-impact-bullet-speed-screen-scene.py", "scripts/run-rc6-real-impact-bullet-midpoint-c4-scene.py", 2, "scene tool"),
    ("scripts/run-rc6-real-impact-bullet-speed-screen.py", "scripts/run-rc6-real-impact-bullet-midpoint-c4.py", 2, "runner"),
    ("scripts/audit-rc6-real-impact-bullet-speed-screen.py", "scripts/audit-rc6-real-impact-bullet-midpoint-c4.py", 1, "auditor commit path"),
    ("specs/ai-native-studio-rc6-real-impact-bullet-speed-screen.v0.82.json", "specs/ai-native-studio-rc6-real-impact-bullet-midpoint-c4.v0.86.json", 2, "spec"),
    ("research/2026-09-02-rc6-real-impact-bullet-speed-screen-preregistration.md", "research/2026-09-02-rc6-real-impact-bullet-midpoint-c4-preregistration.md", 1, "preregistration"),
    ('row["configuration"]["acceptedDomainCenterMeters"] == domain_center', 'all(abs(a - b) <= 1e-6 for a, b in zip(row["configuration"]["acceptedDomainCenterMeters"], domain_center))', 1, "domain center tolerance"),
    ('row["configuration"]["acceptedDomainDimensionsMeters"] == domain_dimensions', 'all(abs(a - b) <= 1e-6 for a, b in zip(row["configuration"]["acceptedDomainDimensionsMeters"], domain_dimensions))', 1, "domain dimensions tolerance"),
    ('"blenderStarts": 3,', '"blenderStarts": 1,', 1, "Blender count"),
    ('"bulletBakes": 3,', '"bulletBakes": 1,', 1, "Bullet count"),
    ('"processRosterExact": len(processes) == 3', '"processRosterExact": len(processes) == 1', 1, "process count"),
    ('bfs.rc6RealImpactBulletSpeedScreenIndependentAudit.v0.1', 'bfs.rc6RealImpactBulletMidpointC4IndependentAudit.v0.1', 1, "schema"),
    ('RC6_REAL_IMPACT_BULLET_SPEED_SCREEN_AUDIT=', 'RC6_REAL_IMPACT_BULLET_MIDPOINT_C4_AUDIT=', 1, "marker"),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"real-impact C4 auditor {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#C4_I09_MIDPOINT", "exec"), globals(), globals())
