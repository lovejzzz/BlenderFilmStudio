#!/usr/bin/env python3
"""F7: preserve the accepted Bullet chain and gate liquid volume/coherence."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-fluid-consequence-scene-f6.py")
EXPECTED_BASE_SHA256 = "0ec1a24e5e8be832569c4807131463a2af00d657195254363d0bdb0493d2b283"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 F7 base scene adapter identity mismatch")

source = BASE.read_text(encoding="utf-8")
raw_before = "tuple_expansion = tuple_anchor + '''"
raw_after = "tuple_expansion = tuple_anchor + r'''"
if source.count(raw_before) != 1:
    raise RuntimeError("RC6 F7 raw tuple-expansion target is not unique")
source = source.replace(raw_before, raw_after)

patches = (
    (
        "'fluid_modifier(cup, \"EFFECTOR\").effector_settings.surface_distance = 1.5'",
        "'cup_effector = fluid_modifier(cup, \"EFFECTOR\"); cup_effector.effector_settings.surface_distance = 1.5; cup_effector.effector_settings.subframes = 4'",
        "moving cup effector subframes",
    ),
    (
        "'settings.resolution_max = 128'",
        "'settings.resolution_max = 192'",
        "base liquid resolution",
    ),
    (
        "'settings.mesh_particle_radius = 1.0'",
        "'settings.mesh_particle_radius = 2.0'",
        "volume-preserving mesh radius",
    ),
    (
        "'settings.resolution_max == 128 and settings.cache_frame_end == 48'",
        "'settings.resolution_max == 192 and settings.cache_frame_end == 48 and settings.timesteps_min == 2 and settings.timesteps_max == 8 and settings.cfl_condition == 1.0 and settings.particle_number == 3 and settings.particle_radius == 1.5 and settings.use_viscosity and settings.viscosity_base == 1.0 and settings.viscosity_exponent == 6 and cup_effector.effector_settings.subframes == 4'",
        "resource and physical configuration assertion",
    ),
)
for before, after, label in patches:
    if source.count(before) != 1:
        raise RuntimeError(f"RC6 F7 {label} target is not unique")
    source = source.replace(before, after)

anchor = "    ('settings.mesh_particle_radius = 1.2', 'settings.mesh_particle_radius = 2.0', \"surface particle radius\"),"
expansion = anchor + r'''
    ('settings.timesteps_min = 1', 'settings.timesteps_min = 2', "minimum fluid substeps"),
    ('settings.timesteps_max = 4', 'settings.timesteps_max = 8', "maximum fluid substeps"),
    ('settings.cfl_condition = 2.0', 'settings.cfl_condition = 1.0', "fluid CFL"),
    ('settings.particle_number = 2', 'settings.particle_number = 3; settings.particle_radius = 1.5', "volume particles"),
    ('settings.flip_ratio = 0.95', 'settings.flip_ratio = 0.95; settings.use_viscosity = True; settings.viscosity_base = 1.0; settings.viscosity_exponent = 6', "water-scale viscosity"),
    ('import bpy\nfrom mathutils import Vector', 'import bmesh\nimport bpy\nfrom mathutils import Vector', "bmesh metrics import"),
    (
        'def evaluated_fluid(domain, cup):',
        """def fluid_quality(domain):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = domain.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        vertex_count = len(mesh.vertices)
        if not vertex_count:
            return {"connectedComponentCount": 0, "largestComponentFraction": 0.0, "meshVolumeCubicMeters": 0.0, "meshSurfaceAreaSquareMeters": 0.0, "surfaceAreaToVolume": 0.0}
        parent = list(range(vertex_count))
        sizes = [1] * vertex_count
        def find(index):
            while parent[index] != index:
                parent[index] = parent[parent[index]]
                index = parent[index]
            return index
        def union(a, b):
            root_a, root_b = find(a), find(b)
            if root_a == root_b:
                return
            if sizes[root_a] < sizes[root_b]:
                root_a, root_b = root_b, root_a
            parent[root_b] = root_a
            sizes[root_a] += sizes[root_b]
        for edge in mesh.edges:
            union(edge.vertices[0], edge.vertices[1])
        components = {}
        for index in range(vertex_count):
            root = find(index)
            components[root] = components.get(root, 0) + 1
        bm = bmesh.new()
        bm.from_mesh(mesh)
        volume = abs(bm.calc_volume(signed=True))
        bm.free()
        area = sum(polygon.area for polygon in mesh.polygons)
        return {
            "connectedComponentCount": len(components),
            "largestComponentFraction": round(max(components.values()) / vertex_count, 8),
            "meshVolumeCubicMeters": round(volume, 10),
            "meshSurfaceAreaSquareMeters": round(area, 10),
            "surfaceAreaToVolume": round(area / volume, 8) if volume > 1e-12 else 0.0,
        }
    finally:
        evaluated.to_mesh_clear()


def evaluated_fluid(domain, cup):""",
        "liquid topology and volume metrics",
    ),
    ('        sample = evaluated_fluid(domain, cup)\n        sample["frame"] = frame', '        sample = evaluated_fluid(domain, cup)\n        sample.update(fluid_quality(domain))\n        sample["frame"] = frame', "per-frame liquid quality"),
    ('    initial_fluid = fluid_samples[0]\n    precontact_maximum_outside = max(row["outsideCupFraction"] for row in fluid_samples if row["frame"] < contact_frame) if contact_frame > 1 else initial_fluid["outsideCupFraction"]', '    initial_fluid = fluid_samples[0]\n    impact_window_liquid = [row for row in fluid_samples if contact_frame <= row["frame"] <= min(48, contact_frame + 8)]\n    initial_volume = initial_fluid["meshVolumeCubicMeters"]\n    impact_window_minimum_volume_retention = min(row["meshVolumeCubicMeters"] / initial_volume for row in impact_window_liquid) if initial_volume > 1e-12 else 0.0\n    impact_window_minimum_largest_component = min(row["largestComponentFraction"] for row in impact_window_liquid)\n    precontact_maximum_outside = max(row["outsideCupFraction"] for row in fluid_samples if row["frame"] < contact_frame) if contact_frame > 1 else initial_fluid["outsideCupFraction"]', "impact-window quality metrics"),
    ('        "liquidMeshExists": max(row["vertexCount"] for row in fluid_samples) >= 100,', '        "liquidMeshExists": max(row["vertexCount"] for row in fluid_samples) >= 100,\n        "impactWindowVolumeRetention": impact_window_minimum_volume_retention >= 0.40,\n        "impactWindowLiquidCoherence": impact_window_minimum_largest_component >= 0.50,', "liquid quality gates"),
    ('                "initialVertexCount": initial_fluid["vertexCount"],\n                "preContactMaximumOutsideCupFraction": round(precontact_maximum_outside, 8),', '                "initialVertexCount": initial_fluid["vertexCount"],\n                "initialMeshVolumeCubicMeters": initial_volume,\n                "impactWindowMinimumVolumeRetentionFraction": round(impact_window_minimum_volume_retention, 8),\n                "impactWindowMinimumLargestComponentFraction": round(impact_window_minimum_largest_component, 8),\n                "preContactMaximumOutsideCupFraction": round(precontact_maximum_outside, 8),', "liquid quality receipts"),
    ('    actual_fluid = evaluated_fluid(domain, cup)\n    expected_fluid = expected["physics"]["liquid"]["samples"][effect_frame - 1]', '    actual_fluid = evaluated_fluid(domain, cup)\n    actual_fluid.update(fluid_quality(domain))\n    expected_fluid = expected["physics"]["liquid"]["samples"][effect_frame - 1]', "reopen quality sample"),
    ('        "fluidBoundsExact": actual_fluid["boundsMin"] == expected_fluid["boundsMin"] and actual_fluid["boundsMax"] == expected_fluid["boundsMax"],', '        "fluidBoundsExact": actual_fluid["boundsMin"] == expected_fluid["boundsMin"] and actual_fluid["boundsMax"] == expected_fluid["boundsMax"],\n        "fluidQualityExact": actual_fluid["connectedComponentCount"] == expected_fluid["connectedComponentCount"] and actual_fluid["largestComponentFraction"] == expected_fluid["largestComponentFraction"] and actual_fluid["meshVolumeCubicMeters"] == expected_fluid["meshVolumeCubicMeters"],', "reopen liquid quality gate"),
'''
if source.count(anchor) != 1:
    raise RuntimeError("RC6 F7 tuple insertion anchor is not unique")
source = source.replace(anchor, expansion)
exec(compile(source, str(BASE) + "#F7_VOLUME_COHERENCE", "exec"), globals(), globals())
