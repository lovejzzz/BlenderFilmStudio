#!/usr/bin/env python3
"""Independently audit the single-variable liquid mesh concavity matrix."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-liquid-final-mesh-only-matrix.py")
EXPECTED_BASE_SHA256 = "f8eba28d1f0c9bdc60c6f19943333cade6b6e02853400518cbe1b1d018b1068d"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 liquid mesh concavity auditor base identity mismatch")


source = BASE.read_text(encoding="utf-8")
replacements = (
    (
        '"""Independently audit the copied-data resolution-192 mesh-only matrix."""',
        '"""Independently audit the fixed-radius mesh_concave_upper matrix."""',
        1,
        "docstring",
    ),
    ("RC6-2026-09-01-final-mesh-only-attempt-28", "RC6-2026-09-01-mesh-concavity-attempt-31", 2, "roots"),
    ("scripts/run-rc6-liquid-final-mesh-only-scene.py", "scripts/run-rc6-liquid-mesh-concavity-scene.py", 1, "scene tool"),
    ("scripts/run-rc6-liquid-final-mesh-only-matrix.py", "scripts/run-rc6-liquid-mesh-concavity-matrix.py", 1, "runner"),
    ("specs/ai-native-studio-rc6-liquid-final-mesh-only.v0.28.json", "specs/ai-native-studio-rc6-liquid-mesh-concavity.v0.31.json", 1, "spec"),
    (
        'CELLS = (("mesh-radius-8p0", 8.0), ("mesh-radius-9p0", 9.0), ("mesh-radius-9p5", 9.5), ("mesh-radius-10p0", 10.0))',
        'CELLS = (("concavity-upper-3p50", 3.5), ("concavity-upper-2p75", 2.75), ("concavity-upper-2p00", 2.0), ("concavity-upper-1p25", 1.25))',
        1,
        "cell roster",
    ),
    (
        '''def expected_argv(cell_id, radius, retained_data_hash):
    return [
        str(BINARY), "--background", "--factory-startup", "--disable-autoexec", "--offline-mode",
        str(WORK / cell_id / "copied-baked-state.blend"), "--python", str(SCENE_TOOL), "--",
        "--cell-id", cell_id, "--work-root", str(WORK), "--evidence-root", str(EVIDENCE),
        "--mesh-particle-radius", str(radius), "--retained-data-manifest-hash", retained_data_hash,
    ]''',
        '''def expected_argv(cell_id, concave_upper, retained_data_hash):
    return [
        str(BINARY), "--background", "--factory-startup", "--disable-autoexec", "--offline-mode",
        str(WORK / cell_id / "copied-baked-state.blend"), "--python", str(SCENE_TOOL), "--",
        "--cell-id", cell_id, "--work-root", str(WORK), "--evidence-root", str(EVIDENCE),
        "--mesh-particle-radius", "9.0", "--mesh-concave-upper", str(concave_upper),
        "--retained-data-manifest-hash", retained_data_hash,
    ]''',
        1,
        "argv builder",
    ),
    ("for index, (cell_id, radius) in enumerate(CELLS, start=1):", "for index, (cell_id, concave_upper) in enumerate(CELLS, start=1):", 1, "loop variable"),
    ("expected_argv(cell_id, radius, retained_data[\"manifestHash\"])", "expected_argv(cell_id, concave_upper, retained_data[\"manifestHash\"])", 1, "argv call"),
    (
        '"particleNumber": 2, "particleRadius": 1.6, "meshScale": 2, "meshParticleRadius": radius,',
        '"particleNumber": 2, "particleRadius": 1.6, "meshScale": 2, "meshParticleRadius": 9.0,\n                "meshConcaveLower": 0.4, "meshConcaveUpper": concave_upper, "meshSmoothenPos": 1, "meshSmoothenNeg": 1,',
        1,
        "configuration receipt",
    ),
    (
        '{"retainedDataCopied": True, "fluidDataBakes": 0, "fluidMeshBakes": 1, "blendSaves": 1, "renderCalls": 0, "networkCalls": 0, "engineRemoteWrites": 0}',
        '{"retainedDataCopied": True, "cacheDirectoryRebound": True, "rnaFloatTolerance": 1e-6, "singleReconstructionVariable": "mesh_concave_upper", "fluidDataBakes": 0, "fluidMeshBakes": 1, "blendSaves": 1, "renderCalls": 0, "networkCalls": 0, "engineRemoteWrites": 0}',
        1,
        "authority receipt",
    ),
    (
        'row["metrics"]["maximumAbsoluteVolumeDriftFraction"],\n        row["configuration"]["meshParticleRadius"],\n    ))',
        'row["metrics"]["maximumAbsoluteVolumeDriftFraction"],\n        row["configuration"]["meshConcaveUpper"],\n    ))',
        1,
        "ranking tie-break",
    ),
    (
        '"cellId": row["cellId"], "meshParticleRadius": row["configuration"]["meshParticleRadius"],',
        '"cellId": row["cellId"], "meshParticleRadius": row["configuration"]["meshParticleRadius"], "meshConcaveUpper": row["configuration"]["meshConcaveUpper"],',
        1,
        "matrix cells",
    ),
    ("bfs.rc6LiquidFinalMeshOnlyIndependentAudit.v0.1", "bfs.rc6LiquidMeshConcavityIndependentAudit.v0.1", 1, "audit schema"),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"RC6 liquid mesh concavity auditor {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#LIQUID_MESH_CONCAVITY_AUDITOR_V01", "exec"), globals(), globals())
