#!/usr/bin/env python3
"""C1: require the exported FLIP particle system only after the Data bake."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-liquid-obstacle-voxel-screen-scene.py")
EXPECTED_BASE_SHA256 = "27f00928b1f21dfa8f1d97aaf632431d0f2594b93eff0ac646b983a4f0bdaffe"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("obstacle-voxel C1 scene base identity mismatch")


source = BASE.read_text(encoding="utf-8")
before = '''    bpy.context.view_layer.update()
    if len(domain.particle_systems) != 1:
        raise RuntimeError("FLIP particle system was not exposed before bake")
    domain.particle_systems[0].settings.display_percentage = 100

    started = time.monotonic()'''
after = '''    bpy.context.view_layer.update()

    started = time.monotonic()'''
if source.count(before) != 1:
    raise RuntimeError("obstacle-voxel C1 pre-bake assertion target mismatch")
source = source.replace(before, after)

before = '''        bpy.ops.fluid.bake_data()

    cache_files = sorted'''
after = '''        bpy.ops.fluid.bake_data()

    scene.frame_set(1)
    bpy.context.view_layer.update()
    evaluated_after_bake = domain.evaluated_get(bpy.context.evaluated_depsgraph_get())
    if len(evaluated_after_bake.particle_systems) != 1:
        raise RuntimeError("FLIP particle system was not exposed after Data bake")
    domain.particle_systems[0].settings.display_percentage = 100
    bpy.context.view_layer.update()

    cache_files = sorted'''
if source.count(before) != 1:
    raise RuntimeError("obstacle-voxel C1 post-bake assertion target mismatch")
source = source.replace(before, after)
if source.count("bfs.rc6LiquidObstacleVoxelScreenCell.v0.1") != 1:
    raise RuntimeError("obstacle-voxel C1 schema target mismatch")
source = source.replace("bfs.rc6LiquidObstacleVoxelScreenCell.v0.1", "bfs.rc6LiquidObstacleVoxelScreenCell.v0.2")
exec(compile(source, str(BASE) + "#OBSTACLE_VOXEL_SCREEN_C1_V02", "exec"), globals(), globals())
