#!/usr/bin/env python3
"""C2: transform the fully assembled scene at its final compile boundary."""

import builtins
import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-liquid-source-clearance-scene-c1.py")
EXPECTED_BASE_SHA256 = "7e20565d326ab6691889a7fb22ff244ea8b825ddb08539cf38f1f6729cf45beb"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 source-clearance final C2 base identity mismatch")


original_compile = builtins.compile
interceptions = 0


def final_compile(source, filename, mode, *args, **kwargs):
    global interceptions
    if str(filename).endswith("#LOCAL_DOMAIN_STATIC_V02"):
        if not isinstance(source, str):
            raise RuntimeError("RC6 source-clearance final C2 expected text source")
        replacements = (
            ("args.frame_end != 7 or args.resolution != 96 or args.particle_number != 2", "args.frame_end != 7 or args.resolution != 192 or args.particle_number != 2", "resolution assertion"),
            ("LOCAL_BASE_VOXEL_METERS = 0.5 / 96.0", "LOCAL_BASE_VOXEL_METERS = 0.5 / 192.0", "base voxel"),
            ('allowed = {"clearance-20mm": 0.020, "clearance-25mm": 0.025, "clearance-30mm": 0.030, "clearance-35mm": 0.035}', 'allowed = {"clearance-35mm-res192": 0.035}', "cell roster"),
            ("bfs.rc6LiquidSourceClearanceCell.v0.2", "bfs.rc6LiquidSourceClearanceFinalCell.v0.3", "schema"),
        )
        for before, after, label in replacements:
            if source.count(before) != 1:
                raise RuntimeError(f"RC6 source-clearance final C2 {label} target mismatch")
            source = source.replace(before, after)
        interceptions += 1
        filename = str(filename) + "#SOURCE_CLEARANCE_FINAL_C2_V03"
    return original_compile(source, filename, mode, *args, **kwargs)


builtins.compile = final_compile
try:
    assembled = BASE.read_text(encoding="utf-8")
    exec(original_compile(assembled, str(BASE) + "#SOURCE_CLEARANCE_FINAL_C2_WRAPPER_V01", "exec"), globals(), globals())
finally:
    builtins.compile = original_compile
if interceptions != 1:
    raise RuntimeError(f"RC6 source-clearance final C2 interception count {interceptions}, expected 1")
