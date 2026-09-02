#!/usr/bin/env python3
"""Reopen a persisted adopted Data state and perform exactly one Mesh bake."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-liquid-final-mesh-only-scene.py")
EXPECTED_BASE_SHA256 = "2e68cb021c860066a1ec24d301fc3684fdee7c94b13077744b68bf6f6bdd4a0c"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256: raise RuntimeError("Final effector Mesh C1 base identity mismatch")
source = BASE.read_text(encoding="utf-8")
replacements = (
    ('"""Rebuild only a copied Mantaflow liquid mesh and measure signed topology."""', '"""Reopen adopted Final effector Data and measure one Mesh reconstruction."""', "docstring"),
    ('''ALLOWED = {
    "mesh-radius-8p0": 8.0,
    "mesh-radius-9p0": 9.0,
    "mesh-radius-9p5": 9.5,
    "mesh-radius-10p0": 10.0,
}''', '''ALLOWED = {
    "final-effector-mesh-c1": 9.0,
}''', "cell roster"),
    ('''def expected_all_files():
    return sorted(expected_data_files() + [f"mesh/fluid_mesh_{frame:04d}.bobj.gz" for frame in range(1, 8)])''', '''def expected_all_files():
    return sorted(expected_data_files() + [f"mesh/fluid_mesh_{frame:04d}.bobj.gz" for frame in range(1, 8)])


def data_manifest_hash(cache_root):
    files = []
    for relative in expected_data_files():
        path = cache_root / relative
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"Final effector Mesh C1 Data file missing or symlinked: {relative}")
        files.append({"path": relative, "bytes": path.stat().st_size, "sha256": sha(path)})
    value = {"schemaVersion": "bfs.rc6LiquidDataManifest.v0.1", "files": files}
    value["manifestHash"] = self_hash(value, "manifestHash")
    return value["manifestHash"]''', "manifest helper"),
    ('    expected_blend = candidate_root / "copied-baked-state.blend"', '    expected_blend = candidate_root / "data-adopted-state.blend"', "input blend"),
    ('''    if cache_files(cache_root) != expected_all_files():
        raise RuntimeError("mesh-only initial cache roster mismatch")''', '''    if cache_files(cache_root) != expected_data_files():
        raise RuntimeError("Final effector Mesh C1 initial Data roster mismatch")
    initial_data_manifest_hash = data_manifest_hash(cache_root)
    if initial_data_manifest_hash != args.retained_data_manifest_hash:
        raise RuntimeError("Final effector Mesh C1 initial Data manifest mismatch")''', "initial Data"),
    ('''    domain_modifier = next((item for item in domain.modifiers if item.type == "FLUID" and item.fluid_type == "DOMAIN"), None)
    if domain_modifier is None:
        raise RuntimeError("mesh-only domain modifier missing")
    settings = domain_modifier.domain_settings
    resolved_cache = Path(bpy.path.abspath(settings.cache_directory)).resolve()
    if resolved_cache != cache_root:
        raise RuntimeError("mesh-only relative cache resolution mismatch")
    if settings.cache_type != "MODULAR" or not settings.has_cache_baked_data or not settings.has_cache_baked_mesh:
        raise RuntimeError("mesh-only initial baked flags mismatch")
    if settings.resolution_max != 192 or settings.cache_frame_start != 1 or settings.cache_frame_end != 7:
        raise RuntimeError("mesh-only frozen resolution or frame range mismatch")
    if abs(settings.particle_radius - 1.6) > 1e-12 or settings.particle_number != 2:
        raise RuntimeError("mesh-only frozen simulation setting mismatch")
    if any(abs(source.dimensions[index] - EXPECTED_SOURCE_DIMENSIONS[index]) > 1e-8 for index in range(3)):
        raise RuntimeError("mesh-only source dimensions mismatch")''', '''    domain_modifier = next((item for item in domain.modifiers if item.type == "FLUID" and item.fluid_type == "DOMAIN"), None)
    cup_modifier = next((item for item in cup.modifiers if item.type == "FLUID" and item.fluid_type == "EFFECTOR"), None)
    if domain_modifier is None or cup_modifier is None:
        raise RuntimeError("Final effector Mesh C1 modifier identity incomplete")
    settings = domain_modifier.domain_settings
    effector = cup_modifier.effector_settings
    settings.cache_directory = str(cache_root)
    resolved_cache = Path(bpy.path.abspath(settings.cache_directory)).resolve()
    if resolved_cache != cache_root:
        raise RuntimeError("Final effector Mesh C1 explicit cache rebind mismatch")
    if settings.cache_type != "MODULAR" or not settings.has_cache_baked_data or settings.has_cache_baked_mesh:
        raise RuntimeError("Final effector Mesh C1 persisted baked flags mismatch")
    if settings.resolution_max != 192 or settings.cache_frame_start != 1 or settings.cache_frame_end != 7:
        raise RuntimeError("Final effector Mesh C1 frozen resolution or frame range mismatch")
    if abs(settings.particle_radius - 1.6) > 1e-6 or settings.particle_number != 2 or abs(effector.surface_distance - 2.5) > 1e-6:
        raise RuntimeError("Final effector Mesh C1 physical setting mismatch")
    if any(abs(source.dimensions[index] - EXPECTED_SOURCE_DIMENSIONS[index]) > 1e-8 for index in range(3)):
        raise RuntimeError("Final effector Mesh C1 source dimensions mismatch")
    if data_manifest_hash(cache_root) != initial_data_manifest_hash:
        raise RuntimeError("Final effector Mesh C1 reopen changed Data")''', "reopen verification"),
    ('''    with bpy.context.temp_override(**context):
        if "FINISHED" not in bpy.ops.fluid.free_mesh():
            raise RuntimeError("mesh-only free_mesh did not finish")
    if not settings.has_cache_baked_data or settings.has_cache_baked_mesh:
        raise RuntimeError("mesh-only flags after free mismatch")
    if cache_files(cache_root) != expected_data_files():
        raise RuntimeError("mesh-only free changed data roster or retained mesh")
    settings.mesh_particle_radius = args.mesh_particle_radius
    with bpy.context.temp_override(**context):''', '''    settings.use_mesh = True
    settings.mesh_particle_radius = args.mesh_particle_radius
    settings.mesh_concave_lower = 0.4
    settings.mesh_concave_upper = 3.5
    settings.mesh_smoothen_pos = 1
    settings.mesh_smoothen_neg = 1
    if not settings.has_cache_baked_data or settings.has_cache_baked_mesh or data_manifest_hash(cache_root) != initial_data_manifest_hash:
        raise RuntimeError("Final effector Mesh C1 enabling Mesh invalidated Data")
    with bpy.context.temp_override(**context):''', "single Mesh stage"),
    ('''    if not settings.has_cache_baked_data or not settings.has_cache_baked_mesh:
        raise RuntimeError("mesh-only flags after bake mismatch")
    final_cache_files = cache_files(cache_root)''', '''    if not settings.has_cache_baked_data or not settings.has_cache_baked_mesh:
        raise RuntimeError("Final effector Mesh C1 flags after bake mismatch")
    if data_manifest_hash(cache_root) != initial_data_manifest_hash:
        raise RuntimeError("Final effector Mesh C1 bake changed Data")
    final_cache_files = cache_files(cache_root)''', "post-bake Data"),
    ('''            "meshParticleRadius": args.mesh_particle_radius,
            "sourceBottomClearanceMeters": 0.0350000039,''', '''            "meshParticleRadius": args.mesh_particle_radius,
            "meshConcaveLower": 0.4,
            "meshConcaveUpper": 3.5,
            "meshSmoothenPos": 1,
            "meshSmoothenNeg": 1,
            "cupEffectorSurfaceDistanceCells": 2.5,
            "sourceBottomClearanceMeters": 0.0350000039,''', "configuration"),
    ('''            "retainedDataCopied": True,
            "fluidDataBakes": 0,''', '''            "retainedDataCopied": True,
            "persistedDataStateReopened": True,
            "cacheDirectoryRebound": True,
            "fluidDataBakes": 0,''', "authority"),
    ("bfs.rc6LiquidFinalMeshOnlyCell.v0.1", "bfs.rc6LiquidFinalEffectorMeshC1Cell.v0.1", "schema"),
    ("RC6_FINAL_MESH_ONLY=", "RC6_FINAL_EFFECTOR_MESH_C1=", "marker"),
)
for before, after, label in replacements:
    if source.count(before) != 1: raise RuntimeError(f"Final effector Mesh C1 {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#FINAL_EFFECTOR_MESH_C1_V01", "exec"), globals(), globals())
