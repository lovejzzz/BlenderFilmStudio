#!/usr/bin/env python3
"""Independently audit the attempt-70 particle-band-width test."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-moving-liquid-effector-distance.py")
EXPECTED_BASE_SHA256 = "d97cbf62a45517fe8e1e3c90a1abad6f87d09bae1445d42db716118b83a2200f"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("moving-liquid particle-band-width auditor base identity mismatch")
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
    baseline_before = 'sha(ATTEMPT58_AUDIT) == spec["baseline"]["attempt58AuditFileSha256"]'
    baseline_after = baseline_before + ' and sha(ATTEMPT68_RESULT) == spec["baseline"]["attempt68ResultFileSha256"] and sha(ATTEMPT68_AUDIT) == spec["baseline"]["attempt68AuditFileSha256"] and sha(ATTEMPT69_AUDIT) == spec["baseline"]["attempt69AuditFileSha256"] and sha(SOURCE_RNA) == spec["implementation"]["rnaFluidSha256"] and sha(SOURCE_DNA) == spec["implementation"]["dnaFluidTypesSha256"] and sha(SOURCE_LIQUID_SCRIPT) == spec["implementation"]["liquidScriptSha256"]'
    config_before = 'abs(result["configuration"]["particleRadius"] - 1.6) <= 1e-6 and abs(result["configuration"]["meshParticleRadius"] - 2.5) <= 1e-6 and abs(result["configuration"]["cupEffectorSurfaceDistanceCells"] - 2.0) <= 1e-6 and result["configuration"]["cupEffectorSubframes"] == 1'
    config_after = 'abs(result["configuration"]["particleRadius"] - 1.8) <= 1e-6 and result["configuration"]["particleNumber"] == 2 and result["configuration"]["particleMinimum"] == 8 and result["configuration"]["particleMaximum"] == 16 and abs(result["configuration"]["particleBandWidth"] - 4.0) <= 1e-6 and abs(result["configuration"]["fractionsThreshold"] - 0.05) <= 1e-6 and abs(result["configuration"]["fractionsDistance"] - 0.25) <= 1e-6 and abs(result["configuration"]["meshParticleRadius"] - 2.5) <= 1e-6 and abs(result["configuration"]["cupEffectorSurfaceDistanceCells"] - 2.0) <= 1e-6 and result["configuration"]["cupEffectorSubframes"] == 1 and result["configuration"]["timestepsMin"] == 2 and result["configuration"]["timestepsMax"] == 4 and abs(result["configuration"]["cflCondition"] - 2.0) <= 1e-6'
    replacements = [
        ('"""Independently audit the attempt-59 2.0-cell moving-liquid test."""', '"""Independently audit the attempt-70 particle-band-width test."""', "docstring"),
        ("RC6-2026-09-02-moving-liquid-effector-distance-attempt-59", "RC6-2026-09-02-moving-liquid-particle-band-width-attempt-70", "fresh roots"),
        (constants_before, constants_after, "new baseline constants"),
        ('"scripts/run-rc6-moving-liquid-effector-distance-scene.py"', '"scripts/run-rc6-moving-liquid-particle-band-width-scene.py"', "scene tool"),
        ('"scripts/run-rc6-moving-liquid-effector-distance.py"', '"scripts/run-rc6-moving-liquid-particle-band-width.py"', "runner"),
        ('"specs/ai-native-studio-rc6-moving-liquid-effector-distance.v0.70.json"', '"specs/ai-native-studio-rc6-moving-liquid-particle-band-width.v0.81.json"', "spec"),
        (config_before, config_after, "configuration check"),
        (baseline_before, baseline_after, "new baseline checks"),
        ('"logs/01-effector-distance.stdout.log"', '"logs/01-particle-band-width.stdout.log"', "stdout log"),
        ('"logs/01-effector-distance.stderr.log"', '"logs/01-particle-band-width.stderr.log"', "stderr log"),
        ('"processes/01-effector-distance.json"', '"processes/01-particle-band-width.json"', "process receipt"),
        ('"bfs.rc6MovingLiquidEffectorDistanceIndependentAudit.v0.1"', '"bfs.rc6MovingLiquidParticleBandWidthIndependentAudit.v0.1"', "audit schema"),
        ('"RC6_MOVING_LIQUID_EFFECTOR_DISTANCE_AUDIT="', '"RC6_MOVING_LIQUID_PARTICLE_BAND_WIDTH_AUDIT="', "audit marker"),
    ]
    for before, after, label in replacements:
        expected = 2 if label == "fresh roots" else 1
        if source.count(before) != expected:
            raise RuntimeError(f"moving-liquid particle-band-width auditor {label} target mismatch")
        source = source.replace(before, after)
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#MOVING_LIQUID_PARTICLE_BAND_WIDTH_V01", "exec"), globals(), globals())
