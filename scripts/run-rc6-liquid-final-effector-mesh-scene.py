#!/usr/bin/env python3
"""Reconstruct the accepted Final effector Data cache without rebaking Data."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-liquid-final-mesh-only-scene.py")
EXPECTED_BASE_SHA256 = "2e68cb021c860066a1ec24d301fc3684fdee7c94b13077744b68bf6f6bdd4a0c"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("Final effector Mesh scene base identity mismatch")


source = BASE.read_text(encoding="utf-8")
replacements = (
    (
        '"""Rebuild only a copied Mantaflow liquid mesh and measure signed topology."""',
        '"""Reconstruct one copied Final effector Data cache and measure signed topology."""',
        "docstring",
    ),
    (
        "import bmesh\nimport bpy",
        "import bmesh\nimport bpy\nfrom mathutils import Vector",
        "vector import",
    ),
    (
        '''ALLOWED = {
    "mesh-radius-8p0": 8.0,
    "mesh-radius-9p0": 9.0,
    "mesh-radius-9p5": 9.5,
    "mesh-radius-10p0": 10.0,
}''',
        '''ALLOWED = {
    "final-effector-mesh": 9.0,
}''',
        "cell roster",
    ),
    (
        '''def expected_all_files():
    return sorted(expected_data_files() + [f"mesh/fluid_mesh_{frame:04d}.bobj.gz" for frame in range(1, 8)])''',
        '''def expected_all_files():
    return sorted(expected_data_files() + [f"mesh/fluid_mesh_{frame:04d}.bobj.gz" for frame in range(1, 8)])


def data_manifest_hash(cache_root):
    files = []
    for relative in expected_data_files():
        path = cache_root / relative
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"Final effector Mesh Data file missing or symlinked: {relative}")
        files.append({"path": relative, "bytes": path.stat().st_size, "sha256": sha(path)})
    value = {"schemaVersion": "bfs.rc6LiquidDataManifest.v0.1", "files": files}
    value["manifestHash"] = self_hash(value, "manifestHash")
    return value["manifestHash"]''',
        "data manifest helper",
    ),
    (
        '    expected_blend = candidate_root / "copied-baked-state.blend"',
        '    expected_blend = candidate_root / "source-state.blend"',
        "source blend path",
    ),
    (
        '''    if cache_files(cache_root) != expected_all_files():
        raise RuntimeError("mesh-only initial cache roster mismatch")''',
        '''    if cache_files(cache_root) != expected_data_files():
        raise RuntimeError("Final effector Mesh initial Data roster mismatch")
    initial_data_manifest_hash = data_manifest_hash(cache_root)
    if initial_data_manifest_hash != args.retained_data_manifest_hash:
        raise RuntimeError("Final effector Mesh initial Data manifest mismatch")''',
        "initial Data roster",
    ),
    (
        '''    domain_modifier = next((item for item in domain.modifiers if item.type == "FLUID" and item.fluid_type == "DOMAIN"), None)
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
        raise RuntimeError("mesh-only source dimensions mismatch")''',
        '''    domain_modifier = next((item for item in domain.modifiers if item.type == "FLUID" and item.fluid_type == "DOMAIN"), None)
    cup_modifier = next((item for item in cup.modifiers if item.type == "FLUID" and item.fluid_type == "EFFECTOR"), None)
    flow_modifier = next((item for item in source.modifiers if item.type == "FLUID" and item.fluid_type == "FLOW"), None)
    if domain_modifier is None or cup_modifier is None or flow_modifier is None:
        raise RuntimeError("Final effector Mesh fluid modifier identity incomplete")
    settings = domain_modifier.domain_settings
    flow_settings = flow_modifier.flow_settings
    effector_settings = cup_modifier.effector_settings
    if settings.domain_type != "LIQUID" or settings.simulation_method != "APIC" or flow_settings.flow_behavior != "GEOMETRY":
        raise RuntimeError("Final effector Mesh semantic identity mismatch")
    domain.location = (0.32, 0.0, 0.25)
    domain.dimensions = (0.36, 0.36, 0.5)
    bpy.ops.object.select_all(action="DESELECT")
    domain.select_set(True)
    bpy.context.view_layer.objects.active = domain
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    scene.frame_start = 1
    scene.frame_end = 7
    scene.frame_set(1)
    bpy.context.view_layer.update()
    if any(abs(source.dimensions[index] - EXPECTED_SOURCE_DIMENSIONS[index]) > 1e-8 for index in range(3)):
        raise RuntimeError("Final effector Mesh source dimensions mismatch")
    inner_floor_world_z = (cup.matrix_world @ Vector((0.0, 0.0, CUP_INTERIOR_BOTTOM_LOCAL_Z))).z
    source.location.z = inner_floor_world_z + source.dimensions.z * 0.5 + 0.035
    bpy.context.view_layer.update()
    measured_clearance = source.matrix_world.translation.z - source.dimensions.z * 0.5 - inner_floor_world_z
    if abs(measured_clearance - 0.035) > 1e-8:
        raise RuntimeError("Final effector Mesh source clearance mismatch")
    initial_use_flip_particles = bool(settings.use_flip_particles)
    initial_particle_system_count = len(domain.particle_systems)
    if not initial_use_flip_particles or initial_particle_system_count != 1:
        raise RuntimeError("Final effector Mesh source FLIP roster mismatch")
    settings.cache_type = "MODULAR"
    settings.cache_frame_start = 1
    settings.cache_frame_end = 7
    settings.resolution_max = 192
    settings.use_adaptive_timesteps = True
    settings.timesteps_min = 1
    settings.timesteps_max = 4
    settings.cfl_condition = 2.0
    settings.particle_number = 2
    settings.particle_radius = 1.6
    settings.use_mesh = True
    settings.use_fractions = True
    settings.delete_in_obstacle = False
    settings.use_viscosity = True
    settings.viscosity_base = 1.0
    settings.viscosity_exponent = 6
    flow_settings.surface_distance = 0.0
    effector_settings.surface_distance = 2.5
    effector_settings.use_plane_init = False
    effector_settings.use_effector = True
    effector_settings.subframes = 0
    settings.mesh_particle_radius = 9.0
    settings.mesh_concave_lower = 0.4
    settings.mesh_concave_upper = 3.5
    settings.mesh_smoothen_pos = 1
    settings.mesh_smoothen_neg = 1
    settings.cache_directory = str(cache_root)
    bpy.context.view_layer.update()
    resolved_cache = Path(bpy.path.abspath(settings.cache_directory)).resolve()
    if resolved_cache != cache_root:
        raise RuntimeError("Final effector Mesh absolute cache rebind mismatch")
    if settings.cache_type != "MODULAR" or not settings.has_cache_baked_data or settings.has_cache_baked_mesh:
        raise RuntimeError("Final effector Mesh initial baked flags mismatch")
    if settings.resolution_max != 192 or settings.cache_frame_start != 1 or settings.cache_frame_end != 7:
        raise RuntimeError("Final effector Mesh frozen resolution or frame range mismatch")
    if abs(settings.particle_radius - 1.6) > 1e-6 or settings.particle_number != 2:
        raise RuntimeError("Final effector Mesh frozen simulation setting mismatch")
    if abs(settings.mesh_particle_radius - 9.0) > 1e-6 or abs(settings.mesh_concave_lower - 0.4) > 1e-6 or abs(settings.mesh_concave_upper - 3.5) > 1e-6 or settings.mesh_smoothen_pos != 1 or settings.mesh_smoothen_neg != 1:
        raise RuntimeError("Final effector Mesh reconstruction setting mismatch")
    if cache_files(cache_root) != expected_data_files() or data_manifest_hash(cache_root) != initial_data_manifest_hash:
        raise RuntimeError("Final effector Mesh scene reconstruction changed Data")''',
        "scene-state reconstruction",
    ),
    (
        '''    with bpy.context.temp_override(**context):
        if "FINISHED" not in bpy.ops.fluid.free_mesh():
            raise RuntimeError("mesh-only free_mesh did not finish")
    if not settings.has_cache_baked_data or settings.has_cache_baked_mesh:
        raise RuntimeError("mesh-only flags after free mismatch")
    if cache_files(cache_root) != expected_data_files():
        raise RuntimeError("mesh-only free changed data roster or retained mesh")
    settings.mesh_particle_radius = args.mesh_particle_radius
    with bpy.context.temp_override(**context):''',
        '''    settings.mesh_particle_radius = args.mesh_particle_radius
    with bpy.context.temp_override(**context):''',
        "remove free Mesh stage",
    ),
    (
        '''    if not settings.has_cache_baked_data or not settings.has_cache_baked_mesh:
        raise RuntimeError("mesh-only flags after bake mismatch")
    final_cache_files = cache_files(cache_root)''',
        '''    if not settings.has_cache_baked_data or not settings.has_cache_baked_mesh:
        raise RuntimeError("Final effector Mesh flags after bake mismatch")
    if data_manifest_hash(cache_root) != initial_data_manifest_hash:
        raise RuntimeError("Final effector Mesh bake changed copied Data bytes")
    final_cache_files = cache_files(cache_root)''',
        "post-bake Data identity",
    ),
    (
        '''            "meshParticleRadius": args.mesh_particle_radius,
            "sourceBottomClearanceMeters": 0.0350000039,''',
        '''            "meshParticleRadius": args.mesh_particle_radius,
            "meshConcaveLower": 0.4,
            "meshConcaveUpper": 3.5,
            "meshSmoothenPos": 1,
            "meshSmoothenNeg": 1,
            "cupEffectorSurfaceDistanceCells": 2.5,
            "sourceBottomClearanceMeters": round(measured_clearance, 10),''',
        "configuration receipt",
    ),
    (
        '''            "retainedDataCopied": True,
            "fluidDataBakes": 0,''',
        '''            "retainedDataCopied": True,
            "sceneStateReconstructed": True,
            "cacheDirectoryRebound": True,
            "initialUseFlipParticles": initial_use_flip_particles,
            "initialParticleSystemCount": initial_particle_system_count,
            "fluidDataBakes": 0,''',
        "authority receipt",
    ),
    ("bfs.rc6LiquidFinalMeshOnlyCell.v0.1", "bfs.rc6LiquidFinalEffectorMeshCell.v0.1", "schema"),
    ("RC6_FINAL_MESH_ONLY=", "RC6_FINAL_EFFECTOR_MESH=", "marker"),
)
for before, after, label in replacements:
    if source.count(before) != 1:
        raise RuntimeError(f"Final effector Mesh scene {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#FINAL_EFFECTOR_MESH_V01", "exec"), globals(), globals())
