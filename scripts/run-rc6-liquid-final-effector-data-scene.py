#!/usr/bin/env python3
"""Run one Final-tier Data-only cell with the cup effector expanded by one cell."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-liquid-obstacle-voxel-screen-scene.py")
EXPECTED_BASE_SHA256 = "27f00928b1f21dfa8f1d97aaf632431d0f2594b93eff0ac646b983a4f0bdaffe"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("final-effector Data scene base identity mismatch")


source = BASE.read_text(encoding="utf-8")
before = '''CELLS = {
    "preview-baseline": (96, 1.5),
    "preview-effector-plus1": (96, 2.5),
    "review-baseline": (128, 1.5),
}'''
after = '''CELLS = {
    "final-effector-plus1": (192, 2.5),
}'''
if source.count(before) != 1:
    raise RuntimeError("final-effector Data cell-roster target mismatch")
source = source.replace(before, after)

before = '''    settings.use_mesh = False
    settings.use_flip_particles = True
    settings.use_fractions = True'''
after = '''    settings.use_mesh = False
    if not initial_use_flip_particles or initial_particle_system_count != 1:
        raise RuntimeError("source FLIP roster is not the frozen coherent true/one state")
    settings.use_fractions = True'''
if source.count(before) != 1:
    raise RuntimeError("final-effector Data FLIP-roster target mismatch")
source = source.replace(before, after)
if source.count("bfs.rc6LiquidObstacleVoxelScreenCell.v0.1") != 1:
    raise RuntimeError("final-effector Data schema target mismatch")
source = source.replace("bfs.rc6LiquidObstacleVoxelScreenCell.v0.1", "bfs.rc6LiquidFinalEffectorDataCell.v0.1")
source = source.replace("RC6_OBSTACLE_VOXEL_SCREEN=", "RC6_FINAL_EFFECTOR_DATA=")
exec(compile(source, str(BASE) + "#FINAL_EFFECTOR_DATA_V01", "exec"), globals(), globals())
