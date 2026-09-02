#!/usr/bin/env python3
"""Independently audit active FLIP-particle detail localization."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-liquid-containment-axis-diagnostic.py")
EXPECTED_BASE_SHA256 = "4ba9db968898102e99bf7726ca9576d924b41ac4572d07056db067697733ffcd"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 FLIP-particle detail auditor base identity mismatch")


source = BASE.read_text(encoding="utf-8")
replacements = (
    ("RC6-2026-09-01-containment-axis-attempt-32", "RC6-2026-09-01-flip-particle-detail-attempt-37", 2, "roots"),
    ("scripts/inspect-rc6-liquid-containment-axis-scene.py", "scripts/inspect-rc6-liquid-flip-particle-detail-scene.py", 1, "scene tool"),
    ("scripts/run-rc6-liquid-containment-axis-diagnostic.py", "scripts/run-rc6-liquid-flip-particle-detail.py", 1, "runner"),
    ("specs/ai-native-studio-rc6-liquid-containment-axis.v0.32.json", "specs/ai-native-studio-rc6-liquid-flip-particle-detail.v0.39.json", 1, "spec"),
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
        "initialUseFlipParticles": True, "initialParticleSystemCount": 1,
        "exposureAction": "REUSED_EXISTING_ENABLED_SYSTEM", "finalUseFlipParticles": True,
        "finalParticleSystemCount": 1, "displayPercentage": 100,
        "cupOuterRadiusMeters": 0.15, "cupOuterBottomLocalZMeters": -0.22,
        "particleAliveSourceRule": "Blender filters PARTICLE_TYPE_DELETE then marks exposed Mantaflow FLIP particles PARS_ALIVE",
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
    detail_exact = True
    for sample in result.get("samples", []):
        details = sample.get("outliersOneVoxel", [])
        aggregate = sample.get("aggregate", {})
        strict = sample.get("strictInterior", {})
        detail_exact = detail_exact and len(details) == aggregate.get("outsideUnionCount")
        detail_exact = detail_exact and aggregate.get("marginMeters") == 0.0026041667 and strict.get("marginMeters") == 0.0
        detail_exact = detail_exact and strict.get("outsideUnionCount", -1) >= aggregate.get("outsideUnionCount", -1)
        for detail in details:
            local = detail.get("locationCupLocal", [])
            if len(local) != 3:
                detail_exact = False
                continue
            radial = (local[0] * local[0] + local[1] * local[1]) ** 0.5
            radial_out = radial > 0.0926041667
            below_out = local[2] < -0.1626041667
            above_out = local[2] > 0.2226041667
            expected_region = "INSIDE_CUP_SOLID_FLOOR" if radial <= 0.15 and -0.22 <= local[2] < -0.16 else ("BELOW_CUP_OUTER_BOTTOM" if local[2] < -0.22 else ("INSIDE_CUP_SOLID_WALL" if 0.09 < radial <= 0.15 and -0.22 <= local[2] <= 0.22 else "OUTSIDE_MODELED_CUP_SOLID"))
            detail_exact = detail_exact and detail.get("detailHash") == self_hash(detail, "detailHash")
            detail_exact = detail_exact and detail.get("aliveState") == "ALIVE" and detail.get("physicalRegion") == expected_region
            detail_exact = detail_exact and detail.get("radialOutsideOneVoxel") == radial_out and detail.get("belowFloorOneVoxel") == below_out and detail.get("aboveRimOneVoxel") == above_out and (radial_out or below_out or above_out)
            detail_exact = detail_exact and detail.get("interiorFloorPenetrationMeters") == round(max(0.0, -0.16 - local[2]), 8)
            detail_exact = detail_exact and detail.get("oneVoxelEnvelopePenetrationMeters") == round(max(0.0, -0.16260416666666666 - local[2]), 8)
    check("activeOutlierDetailsRecomputed", detail_exact, checks)
    prior_result = read_json(RESEARCH / spec["priorParticleAxis"]["resultPath"])
    prior_audit = read_json(RESEARCH / spec["priorParticleAxis"]["auditPath"])
    projected = lambda sample: {key: sample.get(key) for key in ("frame", "aggregate", "strictInterior", "components", "boundsMinCupLocal", "boundsMaxCupLocal")}
    check("priorParticleAxisExact", sha(RESEARCH / spec["priorParticleAxis"]["resultPath"]) == spec["priorParticleAxis"]["resultFileSha256"] and sha(RESEARCH / spec["priorParticleAxis"]["auditPath"]) == spec["priorParticleAxis"]["auditFileSha256"] and prior_audit.get("auditHash") == spec["priorParticleAxis"]["auditHash"] and [projected(sample) for sample in result.get("samples", [])] == [projected(sample) for sample in prior_result.get("samples", [])], checks)
    source_code = Path(spec["sourceCodeBinding"]["path"])
    check("activeParticleSourceCodeExact", sha(source_code) == spec["sourceCodeBinding"]["fileSha256"] and spec["sourceCodeBinding"]["commit"] == "8e18c82548f8716c415e6e1b69fdbbdeef1f1900", checks)''',
        1,
        "detail and prior bindings",
    ),
    ("bfs.rc6LiquidContainmentAxisIndependentAudit.v0.1", "bfs.rc6LiquidFlipParticleDetailIndependentAudit.v0.1", 1, "audit schema"),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"RC6 FLIP-particle detail auditor {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#FLIP_PARTICLE_DETAIL_AUDITOR_V01", "exec"), globals(), globals())
