#!/usr/bin/env python3
"""Run the four-cell, single-variable liquid mesh concavity matrix."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-liquid-final-mesh-only-matrix.py")
EXPECTED_BASE_SHA256 = "62bef5b16268b1870cbf2eebde32463fd7f2295a9f8a1c8fef6f4271a7d63df6"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 liquid mesh concavity runner base identity mismatch")


source = BASE.read_text(encoding="utf-8")
replacements = (
    (
        '"""Run a four-cell mesh-only matrix from copied immutable resolution-192 data."""',
        '"""Run a fixed-radius mesh_concave_upper matrix from immutable resolution-192 data."""',
        1,
        "docstring",
    ),
    ("RC6-2026-09-01-final-mesh-only-attempt-28", "RC6-2026-09-01-mesh-concavity-attempt-31", 2, "roots"),
    ("scripts/run-rc6-liquid-final-mesh-only-scene.py", "scripts/run-rc6-liquid-mesh-concavity-scene.py", 1, "scene tool"),
    ("scripts/audit-rc6-liquid-final-mesh-only-matrix.py", "scripts/audit-rc6-liquid-mesh-concavity-matrix.py", 1, "audit tool"),
    ("specs/ai-native-studio-rc6-liquid-final-mesh-only.v0.28.json", "specs/ai-native-studio-rc6-liquid-mesh-concavity.v0.31.json", 1, "spec"),
    (
        'CELLS = (("mesh-radius-8p0", 8.0), ("mesh-radius-9p0", 9.0), ("mesh-radius-9p5", 9.5), ("mesh-radius-10p0", 10.0))',
        'CELLS = (("concavity-upper-3p50", 3.5), ("concavity-upper-2p75", 2.75), ("concavity-upper-2p00", 2.0), ("concavity-upper-1p25", 1.25))',
        1,
        "cell roster",
    ),
    (
        '''def expected_argv(cell_id, radius):
    copied_blend = WORK / cell_id / "copied-baked-state.blend"
    return [
        str(BINARY), "--background", "--factory-startup", "--disable-autoexec", "--offline-mode",
        str(copied_blend), "--python", str(SCENE_TOOL), "--", "--cell-id", cell_id,
        "--work-root", str(WORK), "--evidence-root", str(EVIDENCE),
        "--mesh-particle-radius", str(radius), "--retained-data-manifest-hash", RETAINED_DATA_HASH,
    ]''',
        '''def expected_argv(cell_id, concave_upper):
    copied_blend = WORK / cell_id / "copied-baked-state.blend"
    return [
        str(BINARY), "--background", "--factory-startup", "--disable-autoexec", "--offline-mode",
        str(copied_blend), "--python", str(SCENE_TOOL), "--", "--cell-id", cell_id,
        "--work-root", str(WORK), "--evidence-root", str(EVIDENCE),
        "--mesh-particle-radius", "9.0", "--mesh-concave-upper", str(concave_upper),
        "--retained-data-manifest-hash", RETAINED_DATA_HASH,
    ]''',
        1,
        "argv builder",
    ),
    ("for index, (cell_id, radius) in enumerate(CELLS, start=1):", "for index, (cell_id, concave_upper) in enumerate(CELLS, start=1):", 1, "loop variable"),
    ("argv = expected_argv(cell_id, radius)", "argv = expected_argv(cell_id, concave_upper)", 1, "argv call"),
    (
        'if result["configuration"]["meshParticleRadius"] != radius or result["configuration"]["retainedDataManifestHash"] != RETAINED_DATA_HASH:',
        'if result["configuration"]["meshParticleRadius"] != 9.0 or result["configuration"]["meshConcaveUpper"] != concave_upper or result["configuration"]["retainedDataManifestHash"] != RETAINED_DATA_HASH:',
        1,
        "configuration check",
    ),
    (
        'row["metrics"]["maximumAbsoluteVolumeDriftFraction"],\n        row["configuration"]["meshParticleRadius"],\n    ))',
        'row["metrics"]["maximumAbsoluteVolumeDriftFraction"],\n        row["configuration"]["meshConcaveUpper"],\n    ))',
        1,
        "ranking tie-break",
    ),
    ("bfs.rc6LiquidFinalMeshOnlyMatrix.v0.1", "bfs.rc6LiquidMeshConcavityMatrix.v0.1", 1, "matrix schema"),
    (
        '"cellId": row["cellId"], "meshParticleRadius": row["configuration"]["meshParticleRadius"],',
        '"cellId": row["cellId"], "meshParticleRadius": row["configuration"]["meshParticleRadius"], "meshConcaveUpper": row["configuration"]["meshConcaveUpper"],',
        1,
        "matrix cells",
    ),
)
for before, after, expected, label in replacements:
    if source.count(before) != expected:
        raise RuntimeError(f"RC6 liquid mesh concavity runner {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#LIQUID_MESH_CONCAVITY_RUNNER_V01", "exec"), globals(), globals())
