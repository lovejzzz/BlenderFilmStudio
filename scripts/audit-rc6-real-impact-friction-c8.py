#!/usr/bin/env python3
"""C8 independent auditor for the one-value cup-friction test."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-real-impact-bullet-speed-screen.py")
EXPECTED_BASE_SHA256 = "9bc233e999aee4a6e4df83b31be233fbbad57103013701562355d49dff2a76a4"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("real-impact C8 auditor base identity mismatch")
source = BASE.read_text(encoding="utf-8")
replacements = (
    ("RC6-2026-09-02-real-impact-bullet-speed-screen-attempt-71", "RC6-2026-09-02-real-impact-friction-c8-attempt-80", 2, "fresh roots"),
    ('CELLS = (("I08", 8), ("I10", 10), ("I12", 12))', 'CELLS = (("F80", 9),)', 1, "cell roster"),
    ("scripts/run-rc6-real-impact-bullet-speed-screen-scene.py", "scripts/run-rc6-real-impact-friction-c8-scene.py", 2, "scene tool"),
    ("scripts/run-rc6-real-impact-bullet-speed-screen.py", "scripts/run-rc6-real-impact-friction-c8.py", 2, "runner"),
    ("scripts/audit-rc6-real-impact-bullet-speed-screen.py", "scripts/audit-rc6-real-impact-friction-c8.py", 1, "auditor commit path"),
    ("specs/ai-native-studio-rc6-real-impact-bullet-speed-screen.v0.82.json", "specs/ai-native-studio-rc6-real-impact-friction-c8.v0.91.json", 2, "spec"),
    ("research/2026-09-02-rc6-real-impact-bullet-speed-screen-preregistration.md", "research/2026-09-02-rc6-real-impact-friction-c8-preregistration.md", 1, "preregistration"),
    ('row["configuration"]["acceptedDomainCenterMeters"] == domain_center', 'all(abs(a - b) <= 1e-6 for a, b in zip(row["configuration"]["acceptedDomainCenterMeters"], domain_center))', 1, "domain center tolerance"),
    ('row["configuration"]["acceptedDomainDimensionsMeters"] == domain_dimensions', 'all(abs(a - b) <= 1e-6 for a, b in zip(row["configuration"]["acceptedDomainDimensionsMeters"], domain_dimensions))', 1, "domain dimensions tolerance"),
    ('abs(row["configuration"]["baseVoxelMeters"] - base_voxel) <= 1e-10', 'abs(row["configuration"]["baseVoxelMeters"] - base_voxel) <= 1e-6', 1, "base voxel tolerance"),
    ('"exactRigidBodyIdentity": True,', '"exactRigidBodyIdentity": True,\n        "cupCollisionMarginExplicitTwoMillimeters": True,\n        "cupFrictionExplicitPointEight": True,', 1, "physical checks"),
    ('and abs(row["configuration"]["ballCollisionRadiusMeters"] - 0.12) <= 1e-6', 'and abs(row["configuration"]["ballCollisionRadiusMeters"] - 0.12) <= 1e-6\n        and row["configuration"]["sourceCupUseMargin"] is False\n        and abs(row["configuration"]["sourceCupCollisionMarginMeters"] - 0.04) <= 1e-6\n        and row["configuration"]["cupUseMargin"] is True\n        and abs(row["configuration"]["cupCollisionMarginMeters"] - 0.002) <= 1e-6\n        and abs(row["configuration"]["sourceCupFriction"] - 0.75) <= 1e-6\n        and abs(row["configuration"]["cupFriction"] - 0.80) <= 1e-6\n        and abs(row["configuration"]["floorFriction"] - 0.58) <= 1e-6\n        and abs(row["configuration"]["combinedFloorFriction"] - 0.464) <= 1e-6', 1, "physical configuration"),
    ('"blenderStarts": 3,', '"blenderStarts": 1,', 1, "Blender count"),
    ('"bulletBakes": 3,', '"bulletBakes": 1,', 1, "Bullet count"),
    ('"processRosterExact": len(processes) == 3', '"processRosterExact": len(processes) == 1', 1, "process count"),
    ('bfs.rc6RealImpactBulletSpeedScreenIndependentAudit.v0.1', 'bfs.rc6RealImpactFrictionC8IndependentAudit.v0.1', 1, "schema"),
    ('RC6_REAL_IMPACT_BULLET_SPEED_SCREEN_AUDIT=', 'RC6_REAL_IMPACT_FRICTION_C8_AUDIT=', 1, "marker"),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"real-impact C8 auditor {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#C8_FRICTION_080", "exec"), globals(), globals())
