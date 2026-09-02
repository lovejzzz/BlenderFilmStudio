#!/usr/bin/env python3
"""C10 independent auditor adapter for the 40 mm passive ramp."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-real-impact-passive-ramp-c9.py")
EXPECTED_BASE_SHA256 = "8c7b63ccefda83bbde9c68f6b3741aec2148a90bc213e45da6b928aadf4407aa"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("real-impact C10 auditor base identity mismatch")
source = BASE.read_text(encoding="utf-8")
replacements = (
    ("RC6-2026-09-02-real-impact-passive-ramp-c9-attempt-81", "RC6-2026-09-02-real-impact-passive-ramp-c10-attempt-82", 1, "fresh roots"),
    ('CELLS = (("R60", 9),)', 'CELLS = (("R40", 9),)', 1, "cell roster"),
    ("scripts/run-rc6-real-impact-passive-ramp-c9-scene.py", "scripts/run-rc6-real-impact-passive-ramp-c10-scene.py", 1, "scene tool"),
    ("scripts/run-rc6-real-impact-passive-ramp-c9.py", "scripts/run-rc6-real-impact-passive-ramp-c10.py", 1, "runner"),
    ("scripts/audit-rc6-real-impact-passive-ramp-c9.py", "scripts/audit-rc6-real-impact-passive-ramp-c10.py", 1, "auditor"),
    ("specs/ai-native-studio-rc6-real-impact-passive-ramp-c9.v0.92.json", "specs/ai-native-studio-rc6-real-impact-passive-ramp-c10.v0.93.json", 1, "spec"),
    ("research/2026-09-02-rc6-real-impact-passive-ramp-c9-preregistration.md", "research/2026-09-02-rc6-real-impact-passive-ramp-c10-preregistration.md", 1, "preregistration"),
    ('rampSurfaceEndZ"] - 0.28', 'rampSurfaceEndZ"] - 0.26', 1, "surface end"),
    ('rampRiseMeters"] - 0.06', 'rampRiseMeters"] - 0.04', 1, "rise"),
    ("math.atan2(0.06, 0.30)", "math.atan2(0.04, 0.30)", 1, "angle"),
    ("#C9_PASSIVE_RAMP_60MM", "#C10_PASSIVE_RAMP_40MM", 1, "compile identity"),
    ("bfs.rc6RealImpactPassiveRampC9IndependentAudit.v0.1", "bfs.rc6RealImpactPassiveRampC10IndependentAudit.v0.1", 1, "schema"),
    ("RC6_REAL_IMPACT_PASSIVE_RAMP_C9_AUDIT=", "RC6_REAL_IMPACT_PASSIVE_RAMP_C10_AUDIT=", 1, "marker"),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"real-impact C10 auditor {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#C10_PASSIVE_RAMP_40MM", "exec"), globals(), globals())
