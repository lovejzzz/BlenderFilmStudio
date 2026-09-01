#!/usr/bin/env python3
"""C1: validate frozen volume before translating the unchanged source mesh."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-liquid-source-clearance-scene.py")
EXPECTED_BASE_SHA256 = "8dff215bcbbc5a1507f4de93689378159e00526d1f822d85b90a9f2f5f3babc1"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 source-clearance C1 base identity mismatch")


source = BASE.read_text(encoding="utf-8")
old_block = r'''source = replace_unique(
    source,
    '    scene.frame_set(1)\\n    bpy.context.view_layer.update()\\n    source_volume = closed_object_mesh_volume(source)',
    (
        '    scene.frame_set(1)\\n'
        '    bpy.context.view_layer.update()\\n'
        '    inner_floor_world_z = (cup.matrix_world @ Vector((0.0, 0.0, CUP_INTERIOR_BOTTOM_LOCAL_Z))).z\\n'
        '    source.location.z = inner_floor_world_z + source.dimensions.z * 0.5 + args.source_bottom_clearance\\n'
        '    bpy.context.view_layer.update()\\n'
        '    actual_source_bottom_clearance = source.matrix_world.translation.z - source.dimensions.z * 0.5 - inner_floor_world_z\\n'
        '    if abs(actual_source_bottom_clearance - args.source_bottom_clearance) > 1e-8:\\n'
        '        raise RuntimeError("source-bottom clearance placement mismatch")\\n'
        '    source_volume = closed_object_mesh_volume(source)'
    ),
    "derived source placement",
)'''
new_block = r'''source = replace_unique(
    source,
    '    if abs(source_volume - EXPECTED_SOURCE_MESH_VOLUME) > 1e-10 or any(abs(source_dimensions[index] - EXPECTED_SOURCE_DIMENSIONS[index]) > 1e-8 for index in range(3)):\\n        raise RuntimeError("frozen source geometry identity mismatch")\\n    bpy.ops.object.select_all(action="DESELECT")',
    (
        '    if abs(source_volume - EXPECTED_SOURCE_MESH_VOLUME) > 1e-10 or any(abs(source_dimensions[index] - EXPECTED_SOURCE_DIMENSIONS[index]) > 1e-8 for index in range(3)):\\n'
        '        raise RuntimeError("frozen source geometry identity mismatch")\\n'
        '    inner_floor_world_z = (cup.matrix_world @ Vector((0.0, 0.0, CUP_INTERIOR_BOTTOM_LOCAL_Z))).z\\n'
        '    source.location.z = inner_floor_world_z + source.dimensions.z * 0.5 + args.source_bottom_clearance\\n'
        '    bpy.context.view_layer.update()\\n'
        '    actual_source_bottom_clearance = source.matrix_world.translation.z - source.dimensions.z * 0.5 - inner_floor_world_z\\n'
        '    if abs(actual_source_bottom_clearance - args.source_bottom_clearance) > 1e-8:\\n'
        '        raise RuntimeError("source-bottom clearance placement mismatch")\\n'
        '    bpy.ops.object.select_all(action="DESELECT")'
    ),
    "identity-before-placement order",
)'''
if source.count(old_block) != 1:
    raise RuntimeError("RC6 source-clearance C1 measurement-order target mismatch")
source = source.replace(old_block, new_block)
if source.count("bfs.rc6LiquidSourceClearanceCell.v0.1") != 1:
    raise RuntimeError("RC6 source-clearance C1 schema target mismatch")
source = source.replace("bfs.rc6LiquidSourceClearanceCell.v0.1", "bfs.rc6LiquidSourceClearanceCell.v0.2")
exec(compile(source, str(BASE) + "#SOURCE_CLEARANCE_C1_V02", "exec"), globals(), globals())
