#!/usr/bin/env python3
"""Independently audit attempt-33 cached FLIP-particle containment evidence."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-liquid-containment-axis-diagnostic.py")
EXPECTED_BASE_SHA256 = "4ba9db968898102e99bf7726ca9576d924b41ac4572d07056db067697733ffcd"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 FLIP-particle axis auditor base identity mismatch")


source = BASE.read_text(encoding="utf-8")
replacements = (
    ("RC6-2026-09-01-containment-axis-attempt-32", "RC6-2026-09-01-flip-particle-axis-attempt-33", 2, "roots"),
    ("scripts/inspect-rc6-liquid-containment-axis-scene.py", "scripts/inspect-rc6-liquid-flip-particle-axis-scene.py", 1, "scene tool"),
    ("scripts/run-rc6-liquid-containment-axis-diagnostic.py", "scripts/run-rc6-liquid-flip-particle-axis-diagnostic.py", 1, "runner"),
    ("specs/ai-native-studio-rc6-liquid-containment-axis.v0.32.json", "specs/ai-native-studio-rc6-liquid-flip-particle-axis.v0.34.json", 1, "spec"),
    ("RC6_CONTAINMENT_AXIS=", "RC6_FLIP_PARTICLE_AXIS=", 1, "scene marker"),
    (
        '''    check("configurationExact", result.get("configuration") == {
        "frameStart": 1, "frameEnd": 7, "resolutionMax": 192, "baseVoxelMeters": 0.0026041667,
        "radialLimitCupLocalMeters": 0.0926041667, "bottomLimitCupLocalMeters": -0.1626041667, "topLimitCupLocalMeters": 0.2226041667,
        "particleRadius": 1.6, "meshParticleRadius": 9.0, "meshConcaveLower": 0.4, "meshConcaveUpper": 3.5,
        "meshSmoothenPos": 1, "meshSmoothenNeg": 1,
        "cupRawMeshRadialZHistogram": {
            "0.00000000@-0.22000000": 1, "0.00000000@-0.16000000": 1,
            "0.09000000@-0.16000000": 64, "0.09000000@0.22000000": 64,
            "0.15000000@-0.22000000": 64, "0.15000000@0.22000000": 64,
        },
        "cupEffectorSurfaceDistance": 0.0015,
    }, checks)''',
        '''    check("configurationExact", result.get("configuration") == {
        "frameStart": 1, "frameEnd": 7, "resolutionMax": 192, "baseVoxelMeters": 0.0026041667,
        "particleRadius": 1.6, "particleNumber": 2, "meshParticleRadius": 9.0,
        "cupInnerRadiusMeters": 0.09, "cupInteriorBottomLocalZMeters": -0.16,
        "cupInteriorTopLocalZMeters": 0.22, "cupEffectorSurfaceDistance": 1.5,
        "flipParticleSystemInitiallyAbsent": True, "flipParticleSystemExposedInMemory": True,
        "displayPercentage": 100,
        "particleCoordinateConvention": "Blender Particle.location world-space converted by cup.matrix_world.inverted",
    }, checks)''',
        1,
        "configuration",
    ),
    (
        '''    check("authorityExact", result.get("authority") == {
        "copiedCandidateReadOnly": True, "fluidDataBakes": 0, "fluidMeshBakes": 0, "blendSaves": 0,
        "renderCalls": 0, "networkCalls": 0, "engineRemoteWrites": 0,
    }, checks)''',
        '''    check("authorityExact", result.get("authority") == {
        "copiedCandidateInMemoryFlipExposure": True, "fluidDataBakes": 0, "fluidMeshBakes": 0, "blendSaves": 0,
        "renderCalls": 0, "networkCalls": 0, "engineRemoteWrites": 0,
    }, checks)''',
        1,
        "authority",
    ),
    (
        '    check("axisArithmeticExact", arithmetic_exact, checks)',
        '''    check("axisArithmeticExact", arithmetic_exact, checks)
    strict_coherent = True
    for sample in result.get("samples", []):
        aggregate = sample.get("aggregate", {})
        strict = sample.get("strictInterior", {})
        strict_coherent = strict_coherent and aggregate.get("marginMeters") == 0.0026041667 and strict.get("marginMeters") == 0.0
        strict_coherent = strict_coherent and aggregate.get("particleCount") == strict.get("particleCount") == aggregate.get("vertexCount") == strict.get("vertexCount")
        strict_coherent = strict_coherent and strict.get("outsideUnionCount", -1) >= aggregate.get("outsideUnionCount", -1)
        strict_coherent = strict_coherent and all(strict.get(key, -1) >= aggregate.get(key, -1) for key in ("radialCount", "belowFloorCount", "aboveRimCount"))
    check("strictAndOneVoxelClassificationsCoherent", strict_coherent, checks)
    prior_axis = read_json(RESEARCH / spec["priorAxisDiagnosis"]["path"])
    check("priorSurfaceAxisDiagnosisExact", sha(RESEARCH / spec["priorAxisDiagnosis"]["path"]) == spec["priorAxisDiagnosis"]["fileSha256"] and prior_axis.get("auditHash") == spec["priorAxisDiagnosis"]["auditHash"] and prior_axis.get("status") == "PASS" and prior_axis.get("checksPassed") == 26 and prior_axis.get("checksTotal") == 26, checks)''',
        1,
        "particle coherence checks",
    ),
    ("bfs.rc6LiquidContainmentAxisIndependentAudit.v0.1", "bfs.rc6LiquidFlipParticleAxisIndependentAudit.v0.1", 1, "audit schema"),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"RC6 FLIP-particle axis auditor {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#FLIP_PARTICLE_AXIS_AUDITOR_V01", "exec"), globals(), globals())
