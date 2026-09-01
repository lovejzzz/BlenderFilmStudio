#!/usr/bin/env python3
"""C1: apply final-resolution changes after C1 assembles the scene source."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-liquid-source-clearance-scene-c1.py")
EXPECTED_BASE_SHA256 = "7e20565d326ab6691889a7fb22ff244ea8b825ddb08539cf38f1f6729cf45beb"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 source-clearance final C1 base identity mismatch")


source = BASE.read_text(encoding="utf-8")
anchor = 'exec(compile(source, str(BASE) + "#SOURCE_CLEARANCE_C1_V02", "exec"), globals(), globals())'
if source.count(anchor) != 1:
    raise RuntimeError("RC6 source-clearance final C1 execution anchor mismatch")
injection = r'''
runtime_replacements = (
    ("args.frame_end != 7 or args.resolution != 96 or args.particle_number != 2", "args.frame_end != 7 or args.resolution != 192 or args.particle_number != 2", "resolution assertion"),
    ("LOCAL_BASE_VOXEL_METERS = 0.5 / 96.0", "LOCAL_BASE_VOXEL_METERS = 0.5 / 192.0", "base voxel"),
    ('allowed = {"clearance-20mm": 0.020, "clearance-25mm": 0.025, "clearance-30mm": 0.030, "clearance-35mm": 0.035}', 'allowed = {"clearance-35mm-res192": 0.035}', "cell roster"),
    ("bfs.rc6LiquidSourceClearanceCell.v0.2", "bfs.rc6LiquidSourceClearanceFinalCell.v0.2", "schema"),
)
for before, after, label in runtime_replacements:
    if source.count(before) != 1:
        raise RuntimeError(f"RC6 source-clearance final C1 runtime {label} target mismatch")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#SOURCE_CLEARANCE_FINAL_C1_V02", "exec"), globals(), globals())
'''
source = source.replace(anchor, injection)
exec(compile(source, str(BASE) + "#SOURCE_CLEARANCE_FINAL_C1_WRAPPER_V01", "exec"), globals(), globals())
