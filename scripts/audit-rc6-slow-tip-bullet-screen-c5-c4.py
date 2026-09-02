#!/usr/bin/env python3
"""C5-C4 audit-only float32 representation correction for attempt-55."""

import hashlib
import json
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-slow-tip-bullet-screen-c5.py")
EXPECTED_BASE_SHA256 = "36dda7c8d45f23d1b46ca001b19471640463007998faa02c37bc89d55402ae2c"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("slow-tip C5-C4 auditor base identity mismatch")

source = BASE.read_text(encoding="utf-8")
replacements = (
    ("RC6-2026-09-02-slow-tip-bullet-screen-c5-attempt-52", "RC6-2026-09-02-slow-tip-bullet-screen-c5-c3-attempt-55", 1, "retained roots"),
    ("scripts/run-rc6-slow-tip-bullet-screen-c5-scene.py", "scripts/run-rc6-slow-tip-bullet-screen-c5-c1-scene.py", 1, "scene tool"),
    ("scripts/run-rc6-slow-tip-bullet-screen-c5.py", "scripts/run-rc6-slow-tip-bullet-screen-c5-c3.py", 1, "runner"),
    ("specs/ai-native-studio-rc6-slow-tip-bullet-screen-c5.v0.60.json", "specs/ai-native-studio-rc6-slow-tip-bullet-screen-c5-c4-audit-only.v0.65.json", 1, "spec"),
    ("bfs.rc6SlowTipBulletScreenC5IndependentAudit.v0.1", "bfs.rc6SlowTipBulletScreenC5C4IndependentAudit.v0.1", 1, "schema"),
    (
        'and row["configuration"]["candidateDomainDimensionsMeters"] == [0.9, 0.5, 0.58]',
        'and all(abs(actual - expected) <= 1e-6 for actual, expected in zip(row["configuration"]["candidateDomainDimensionsMeters"], [0.9, 0.5, 0.58]))',
        1,
        "float32 domain representation tolerance",
    ),
    (
        "    ('RC6_SLOW_TIP_BULLET_SCREEN_AUDIT=', 'RC6_SLOW_TIP_BULLET_SCREEN_C5_AUDIT=', 1, \"marker\"),",
        "    ('RC6_SLOW_TIP_BULLET_SCREEN_AUDIT=', 'RC6_SLOW_TIP_BULLET_SCREEN_C5_C4_AUDIT=', 1, \"marker\"),\n    ('EVIDENCE / \"independent-audit.json\"', 'EVIDENCE / \"independent-audit-c1.json\"', 1, \"append-only audit output\"),",
        1,
        "marker and append-only output",
    ),
    ("#C5_ATTEMPT52", "#C5_C4_AUDIT_ATTEMPT55", 1, "compile tag"),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"slow-tip C5-C4 auditor {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#C5_C4_AUDIT_ATTEMPT55", "exec"), globals(), globals())

manifest_path = EVIDENCE / "evidence-manifest.json"
if manifest_path.exists():
    raise RuntimeError("slow-tip C5-C4 final manifest already exists")
rows = [
    {"path": str(path.relative_to(EVIDENCE)), "bytes": path.stat().st_size, "sha256": sha256(path)}
    for path in sorted(EVIDENCE.rglob("*"))
    if path.is_file()
]
manifest_value = {"root": str(EVIDENCE), "files": rows}
manifest_value["manifestHash"] = self_hash(manifest_value, "manifestHash")
with manifest_path.open("x", encoding="utf-8") as handle:
    json.dump(manifest_value, handle, indent=2, sort_keys=True)
    handle.write("\n")
