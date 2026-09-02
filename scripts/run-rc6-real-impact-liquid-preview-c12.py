#!/usr/bin/env python3
"""Run one bounded R40 Bullet plus APIC Preview impact-liquid experiment."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-moving-liquid-effector-distance.py")
EXPECTED_BASE_SHA256 = "5237861edf167e647e3543bb1c3176be5d70dc52eb850497835a584348782d5e"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("real-impact liquid C12 runner base identity mismatch")
    source = BASE.read_text(encoding="utf-8")

    constants_before = (
        'TRAJECTORY = RESEARCH / "experiments/physical-richness/'
        'RC6-2026-09-02-slow-tip-bullet-screen-c5-c3-attempt-55/cells/C5F96/result.json"\n'
    )
    constants_after = (
        'TRAJECTORY = RESEARCH / "experiments/physical-richness/'
        'RC6-2026-09-02-real-impact-passive-ramp-c10-attempt-82/cells/R40/result.json"\n'
    )
    lineage_before = (
        'ATTEMPT58_AUDIT = RESEARCH / "experiments/physical-richness/'
        'RC6-2026-09-02-moving-liquid-data-occupancy-attempt-58/independent-audit.json"\n'
    )
    lineage_after = lineage_before + (
        'ATTEMPT70_RESULT = RESEARCH / "experiments/physical-richness/'
        'RC6-2026-09-02-moving-liquid-particle-band-width-attempt-70/result.json"\n'
        'ATTEMPT70_AUDIT = RESEARCH / "experiments/physical-richness/'
        'RC6-2026-09-02-moving-liquid-particle-band-width-attempt-70/independent-audit.json"\n'
        'C11_AUDIT = RESEARCH / "experiments/physical-richness/'
        'RC6-2026-09-02-real-impact-event-window-c11-attempt-83/event-window-audit.json"\n'
    )
    baseline_before = '    (ATTEMPT58_AUDIT, spec["baseline"]["attempt58AuditFileSha256"]),\n'
    baseline_after = baseline_before + (
        '    (ATTEMPT70_RESULT, spec["baseline"]["attempt70ResultFileSha256"]),\n'
        '    (ATTEMPT70_AUDIT, spec["baseline"]["attempt70AuditFileSha256"]),\n'
        '    (C11_AUDIT, spec["baseline"]["c11AuditFileSha256"]),\n'
    )
    replacements = (
        (
            '"""Run one 24-frame moving-liquid test with only effector distance at 2.0."""',
            '"""Run one bounded R40 Bullet plus APIC Preview impact-liquid experiment."""',
            "docstring",
            1,
        ),
        (
            "RC6-2026-09-02-moving-liquid-effector-distance-attempt-59",
            "RC6-2026-09-02-real-impact-liquid-preview-c12-attempt-84",
            "fresh roots",
            2,
        ),
        (constants_before, constants_after, "R40 trajectory", 1),
        (lineage_before, lineage_after, "accepted lineage constants", 1),
        (
            '"scripts/run-rc6-moving-liquid-effector-distance-scene.py"',
            '"scripts/run-rc6-real-impact-liquid-preview-c12-scene.py"',
            "scene tool",
            1,
        ),
        (
            '"scripts/audit-rc6-moving-liquid-effector-distance.py"',
            '"scripts/audit-rc6-real-impact-liquid-preview-c12.py"',
            "auditor",
            1,
        ),
        (
            '"specs/ai-native-studio-rc6-moving-liquid-effector-distance.v0.70.json"',
            '"specs/ai-native-studio-rc6-real-impact-liquid-preview-c12.v0.95.json"',
            "spec",
            1,
        ),
        (baseline_before, baseline_after, "accepted lineage checks", 1),
        (
            '"RC6_MOVING_LIQUID_EFFECTOR_DISTANCE="',
            '"RC6_REAL_IMPACT_LIQUID_PREVIEW="',
            "scene marker",
            1,
        ),
        (
            '"bfs.rc6MovingLiquidEffectorDistanceAdmission.v0.1"',
            '"bfs.rc6RealImpactLiquidPreviewC12Admission.v0.1"',
            "admission schema",
            1,
        ),
        (
            '"bfs.rc6MovingLiquidEffectorDistanceFailure.v0.1"',
            '"bfs.rc6RealImpactLiquidPreviewC12Failure.v0.1"',
            "failure schema",
            1,
        ),
        (
            '"bfs.rc6MovingLiquidEffectorDistanceReceipt.v0.1"',
            '"bfs.rc6RealImpactLiquidPreviewC12Receipt.v0.1"',
            "receipt schema",
            1,
        ),
        (
            '"PASS_MOVING_LIQUID_EFFECTOR_DISTANCE"',
            '"PASS_REAL_IMPACT_LIQUID_PREVIEW"',
            "pass verdict",
            1,
        ),
        (
            '"FAIL_MOVING_LIQUID_EFFECTOR_DISTANCE"',
            '"FAIL_REAL_IMPACT_LIQUID_PREVIEW"',
            "fail verdict",
            1,
        ),
        (
            '"logs/01-effector-distance.stdout.log"',
            '"logs/01-real-impact-liquid.stdout.log"',
            "stdout log",
            1,
        ),
        (
            '"logs/01-effector-distance.stderr.log"',
            '"logs/01-real-impact-liquid.stderr.log"',
            "stderr log",
            1,
        ),
        (
            '"processes/01-effector-distance.json"',
            '"processes/01-real-impact-liquid.json"',
            "process receipt",
            1,
        ),
        (
            '"moving-liquid Preview thresholds failed"',
            '"real-impact liquid C12 thresholds failed"',
            "threshold marker",
            1,
        ),
        (
            '"RC6_MOVING_LIQUID_EFFECTOR_DISTANCE_RUN="',
            '"RC6_REAL_IMPACT_LIQUID_PREVIEW_C12_RUN="',
            "runner marker",
            1,
        ),
    )
    for before, after, label, expected in replacements:
        if source.count(before) != expected:
            raise RuntimeError(f"real-impact liquid C12 runner {label} target mismatch")
        source = source.replace(before, after)

    source = source.replace("moving-liquid effector-distance", "real-impact liquid C12")
    receipt_anchor = '    "schemaVersion": "bfs.rc6RealImpactLiquidPreviewC12Receipt.v0.1",'
    receipt_bound = receipt_anchor + '\n    "researchExecutionCommit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.strip(),'
    if source.count(receipt_anchor) != 1:
        raise RuntimeError("real-impact liquid C12 receipt commit anchor mismatch")
    source = source.replace(receipt_anchor, receipt_bound)
    failure_counts = '"counts": {"blenderStarts": 1, "bulletBakes": 1, "fluidDataBakes": 1, "fluidMeshBakes": 1, "renders": 0, "blendSaves": 0, "networkCalls": 0, "engineRemoteWrites": 0}'
    corrected_failure_counts = '"counts": {"blenderStarts": 1, "bulletBakes": 1, "fluidDataBakes": 1, "fluidMeshBakes": 1, "renders": 0, "blendSaves": 0, "nativeBuilds": 0, "networkCalls": 0, "engineSourceEdits": 0, "engineRemoteWrites": 0}'
    if source.count(failure_counts) != 1:
        raise RuntimeError("real-impact liquid C12 failure-count anchor mismatch")
    source = source.replace(failure_counts, corrected_failure_counts)
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#RC6_REAL_IMPACT_LIQUID_PREVIEW_C12", "exec"), globals(), globals())
