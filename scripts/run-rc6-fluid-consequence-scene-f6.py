#!/usr/bin/env python3
"""F6: preserve F4 corrections and add solver-scale effector shells plus finer liquid mesh."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-fluid-consequence-scene-f4.py")
EXPECTED_BASE_SHA256 = "ff53e111ddfd8b6e94a91703ed903903895d8b840747c22ef18cd79e451ce718"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 F6 base adapter identity mismatch")

source = BASE.read_text(encoding="utf-8")
raw_before = "injected = '''f4_replacements = ("
raw_after = "injected = r'''f4_replacements = ("
if source.count(raw_before) != 1:
    raise RuntimeError("RC6 F6 raw-string target is not unique")
source = source.replace(raw_before, raw_after)
tuple_anchor = '    (\'bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=0.07, depth=0.16, location=(0.32, 0, 0.15))\', \'bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=0.055, depth=0.14, location=(0.32, 0, 0.145))\', "smaller liquid source"),'
tuple_expansion = tuple_anchor + '''
    ('fluid_modifier(cup, "EFFECTOR").effector_settings.surface_distance = 0.0015', 'fluid_modifier(cup, "EFFECTOR").effector_settings.surface_distance = 1.5', "cup effector shell"),
    ('fluid_modifier(floor, "EFFECTOR").effector_settings.surface_distance = 0.0015', 'fluid_modifier(floor, "EFFECTOR").effector_settings.surface_distance = 1.5', "floor effector shell"),
    ('settings.resolution_max = 96', 'settings.resolution_max = 128', "fluid resolution"),
    ('settings.mesh_particle_radius = 1.2', 'settings.mesh_particle_radius = 1.0', "surface particle radius"),
    ('settings.resolution_max == 96 and settings.cache_frame_end == 48', 'settings.resolution_max == 128 and settings.cache_frame_end == 48', "resource assertion"),'''
if source.count(tuple_anchor) != 1:
    raise RuntimeError("RC6 F6 tuple insertion anchor is not unique")
source = source.replace(tuple_anchor, tuple_expansion)
exec(compile(source, str(BASE) + "#F6_EFFECTOR_SHELL_AND_FINE_MESH", "exec"), globals(), globals())
