#!/usr/bin/env python3
"""C2: preserve the coherent true/one FLIP roster instead of toggling it off."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-liquid-obstacle-voxel-screen-scene.py")
EXPECTED_BASE_SHA256 = "27f00928b1f21dfa8f1d97aaf632431d0f2594b93eff0ac646b983a4f0bdaffe"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("obstacle-voxel C2 scene base identity mismatch")


source = BASE.read_text(encoding="utf-8")
before = '''    settings.use_mesh = False
    settings.use_flip_particles = True
    settings.use_fractions = True'''
after = '''    settings.use_mesh = False
    if not initial_use_flip_particles or initial_particle_system_count != 1:
        raise RuntimeError("source FLIP roster is not the frozen coherent true/one state")
    settings.use_fractions = True'''
if source.count(before) != 1:
    raise RuntimeError("obstacle-voxel C2 FLIP assignment target mismatch")
source = source.replace(before, after)
if source.count("bfs.rc6LiquidObstacleVoxelScreenCell.v0.1") != 1:
    raise RuntimeError("obstacle-voxel C2 schema target mismatch")
source = source.replace("bfs.rc6LiquidObstacleVoxelScreenCell.v0.1", "bfs.rc6LiquidObstacleVoxelScreenCell.v0.3")
exec(compile(source, str(BASE) + "#OBSTACLE_VOXEL_SCREEN_C2_V03", "exec"), globals(), globals())
