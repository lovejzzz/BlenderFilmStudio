#!/usr/bin/env python3
"""Run one 24-frame moving-liquid test with only particle band width at 4.0."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-moving-liquid-effector-distance.py")
EXPECTED_BASE_SHA256 = "5237861edf167e647e3543bb1c3176be5d70dc52eb850497835a584348782d5e"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("moving-liquid particle-band-width runner base identity mismatch")
    source = BASE.read_text(encoding="utf-8")
    constants_before = 'ATTEMPT58_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-data-occupancy-attempt-58/independent-audit.json"\n'
    constants_after = constants_before + (
        'ATTEMPT68_RESULT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-fractions-distance-attempt-68/result.json"\n'
        'ATTEMPT68_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-fractions-distance-attempt-68/independent-audit.json"\n'
        'ATTEMPT69_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-moving-liquid-fractions-distance-data-comparison-attempt-69/independent-audit.json"\n'
        'SOURCE_RNA = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PhaseB-workspace/PB.1-2026-08-30-mac-m2max-attempt-01/source/source/blender/makesrna/intern/rna_fluid.cc")\n'
        'SOURCE_DNA = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PhaseB-workspace/PB.1-2026-08-30-mac-m2max-attempt-01/source/source/blender/makesdna/DNA_fluid_types.h")\n'
        'SOURCE_LIQUID_SCRIPT = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PhaseB-workspace/PB.1-2026-08-30-mac-m2max-attempt-01/source/intern/mantaflow/intern/strings/liquid_script.h")\n'
    )
    baseline_before = '    (ATTEMPT58_AUDIT, spec["baseline"]["attempt58AuditFileSha256"]),\n'
    baseline_after = baseline_before + (
        '    (ATTEMPT68_RESULT, spec["baseline"]["attempt68ResultFileSha256"]),\n'
        '    (ATTEMPT68_AUDIT, spec["baseline"]["attempt68AuditFileSha256"]),\n'
        '    (ATTEMPT69_AUDIT, spec["baseline"]["attempt69AuditFileSha256"]),\n'
        '    (SOURCE_RNA, spec["implementation"]["rnaFluidSha256"]),\n'
        '    (SOURCE_DNA, spec["implementation"]["dnaFluidTypesSha256"]),\n'
        '    (SOURCE_LIQUID_SCRIPT, spec["implementation"]["liquidScriptSha256"]),\n'
    )
    replacements = [
        ('"""Run one 24-frame moving-liquid test with only effector distance at 2.0."""', '"""Run one 24-frame moving-liquid test with only particle band width at 4.0."""', "docstring"),
        ("RC6-2026-09-02-moving-liquid-effector-distance-attempt-59", "RC6-2026-09-02-moving-liquid-particle-band-width-attempt-70", "fresh roots"),
        (constants_before, constants_after, "new baseline constants"),
        ('"scripts/run-rc6-moving-liquid-effector-distance-scene.py"', '"scripts/run-rc6-moving-liquid-particle-band-width-scene.py"', "scene tool"),
        ('"scripts/audit-rc6-moving-liquid-effector-distance.py"', '"scripts/audit-rc6-moving-liquid-particle-band-width.py"', "auditor"),
        ('"specs/ai-native-studio-rc6-moving-liquid-effector-distance.v0.70.json"', '"specs/ai-native-studio-rc6-moving-liquid-particle-band-width.v0.81.json"', "spec"),
        (baseline_before, baseline_after, "new baseline checks"),
        ('"RC6_MOVING_LIQUID_EFFECTOR_DISTANCE="', '"RC6_MOVING_LIQUID_PARTICLE_BAND_WIDTH="', "process marker"),
        ('"RC6_MOVING_LIQUID_EFFECTOR_DISTANCE_RUN="', '"RC6_MOVING_LIQUID_PARTICLE_BAND_WIDTH_RUN="', "runner marker"),
        ('"bfs.rc6MovingLiquidEffectorDistanceAdmission.v0.1"', '"bfs.rc6MovingLiquidParticleBandWidthAdmission.v0.1"', "admission schema"),
        ('"bfs.rc6MovingLiquidEffectorDistanceFailure.v0.1"', '"bfs.rc6MovingLiquidParticleBandWidthFailure.v0.1"', "failure schema"),
        ('"bfs.rc6MovingLiquidEffectorDistanceReceipt.v0.1"', '"bfs.rc6MovingLiquidParticleBandWidthReceipt.v0.1"', "receipt schema"),
        ('"PASS_MOVING_LIQUID_EFFECTOR_DISTANCE"', '"PASS_MOVING_LIQUID_PARTICLE_BAND_WIDTH"', "pass verdict"),
        ('"FAIL_MOVING_LIQUID_EFFECTOR_DISTANCE"', '"FAIL_MOVING_LIQUID_PARTICLE_BAND_WIDTH"', "fail verdict"),
        ('"logs/01-effector-distance.stdout.log"', '"logs/01-particle-band-width.stdout.log"', "stdout log"),
        ('"logs/01-effector-distance.stderr.log"', '"logs/01-particle-band-width.stderr.log"', "stderr log"),
        ('"processes/01-effector-distance.json"', '"processes/01-particle-band-width.json"', "process receipt"),
    ]
    for before, after, label in replacements:
        expected = 2 if label == "fresh roots" else 1
        if source.count(before) != expected:
            raise RuntimeError(f"moving-liquid particle-band-width runner {label} target mismatch")
        source = source.replace(before, after)
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#MOVING_LIQUID_PARTICLE_BAND_WIDTH_V01", "exec"), globals(), globals())
