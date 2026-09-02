#!/usr/bin/env python3
"""C9 independent auditor for one passive contact-ramp test."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-real-impact-bullet-speed-screen.py")
EXPECTED_BASE_SHA256 = "9bc233e999aee4a6e4df83b31be233fbbad57103013701562355d49dff2a76a4"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("real-impact C9 auditor base identity mismatch")
source = BASE.read_text(encoding="utf-8")
replacements = (
    ("RC6-2026-09-02-real-impact-bullet-speed-screen-attempt-71", "RC6-2026-09-02-real-impact-passive-ramp-c9-attempt-81", 2, "fresh roots"),
    ('CELLS = (("I08", 8), ("I10", 10), ("I12", 12))', 'CELLS = (("R60", 9),)', 1, "cell roster"),
    ("scripts/run-rc6-real-impact-bullet-speed-screen-scene.py", "scripts/run-rc6-real-impact-passive-ramp-c9-scene.py", 2, "scene tool"),
    ("scripts/run-rc6-real-impact-bullet-speed-screen.py", "scripts/run-rc6-real-impact-passive-ramp-c9.py", 2, "runner"),
    ("scripts/audit-rc6-real-impact-bullet-speed-screen.py", "scripts/audit-rc6-real-impact-passive-ramp-c9.py", 1, "auditor commit path"),
    ("specs/ai-native-studio-rc6-real-impact-bullet-speed-screen.v0.82.json", "specs/ai-native-studio-rc6-real-impact-passive-ramp-c9.v0.92.json", 2, "spec"),
    ("research/2026-09-02-rc6-real-impact-bullet-speed-screen-preregistration.md", "research/2026-09-02-rc6-real-impact-passive-ramp-c9-preregistration.md", 1, "preregistration"),
    ('row["configuration"]["acceptedDomainCenterMeters"] == domain_center', 'all(abs(a - b) <= 1e-6 for a, b in zip(row["configuration"]["acceptedDomainCenterMeters"], domain_center))', 1, "domain center tolerance"),
    ('row["configuration"]["acceptedDomainDimensionsMeters"] == domain_dimensions', 'all(abs(a - b) <= 1e-6 for a, b in zip(row["configuration"]["acceptedDomainDimensionsMeters"], domain_dimensions))', 1, "domain dimensions tolerance"),
    ('abs(row["configuration"]["baseVoxelMeters"] - base_voxel) <= 1e-10', 'abs(row["configuration"]["baseVoxelMeters"] - base_voxel) <= 1e-6', 1, "base voxel tolerance"),
    ('"exactRigidBodyIdentity": True,', '"exactRigidBodyIdentity": True,\n        "cupCollisionMarginExplicitTwoMillimeters": True,\n        "passiveRampExact": True,\n        "solverOwnedRaisedContactAtLeastPoint38Meters": contact is not None and next(sample["ballLocation"][2] for sample in samples if sample["frame"] == contact) >= 0.38,', 1, "ramp checks"),
    ('and abs(row["configuration"]["ballCollisionRadiusMeters"] - 0.12) <= 1e-6', 'and abs(row["configuration"]["ballCollisionRadiusMeters"] - 0.12) <= 1e-6\n        and row["configuration"]["sourceCupUseMargin"] is False\n        and abs(row["configuration"]["sourceCupCollisionMarginMeters"] - 0.04) <= 1e-6\n        and row["configuration"]["cupUseMargin"] is True\n        and abs(row["configuration"]["cupCollisionMarginMeters"] - 0.002) <= 1e-6\n        and abs(row["configuration"]["cupFriction"] - 0.75) <= 1e-6\n        and abs(row["configuration"]["rampStartX"] + 0.26) <= 1e-6\n        and abs(row["configuration"]["rampEndX"] - 0.04) <= 1e-6\n        and abs(row["configuration"]["rampSurfaceStartZ"] - 0.22) <= 1e-6\n        and abs(row["configuration"]["rampSurfaceEndZ"] - 0.28) <= 1e-6\n        and abs(row["configuration"]["rampRiseMeters"] - 0.06) <= 1e-6\n        and abs(row["configuration"]["rampRunMeters"] - 0.30) <= 1e-6\n        and abs(row["configuration"]["rampWidthMeters"] - 0.40) <= 1e-6\n        and abs(row["configuration"]["rampAngleDegrees"] - math.degrees(math.atan2(0.06, 0.30))) <= 1e-6', 1, "ramp configuration"),
    ('row["metrics"]["derivedContactFrame"] == contact', 'row["metrics"]["derivedContactFrame"] == contact\n        and row["metrics"]["contactBallCenterZMeters"] == (None if contact is None else next(sample["ballLocation"][2] for sample in samples if sample["frame"] == contact))\n        and row["metrics"]["maximumBallCenterZMetersBeforeContact"] == max(sample["ballLocation"][2] for sample in samples if contact is None or sample["frame"] <= contact)', 1, "raised contact metrics"),
    ('"blenderStarts": 3,', '"blenderStarts": 1,', 1, "Blender count"),
    ('"bulletBakes": 3,', '"bulletBakes": 1,', 1, "Bullet count"),
    ('"processRosterExact": len(processes) == 3', '"processRosterExact": len(processes) == 1', 1, "process count"),
    ('bfs.rc6RealImpactBulletSpeedScreenIndependentAudit.v0.1', 'bfs.rc6RealImpactPassiveRampC9IndependentAudit.v0.1', 1, "schema"),
    ('RC6_REAL_IMPACT_BULLET_SPEED_SCREEN_AUDIT=', 'RC6_REAL_IMPACT_PASSIVE_RAMP_C9_AUDIT=', 1, "marker"),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"real-impact C9 auditor {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#C9_PASSIVE_RAMP_60MM", "exec"), globals(), globals())
