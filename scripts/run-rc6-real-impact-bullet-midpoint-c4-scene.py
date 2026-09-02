#!/usr/bin/env python3
"""C4 single-midpoint adapter for the unchanged real-impact scene tool."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-real-impact-bullet-speed-screen-scene.py")
EXPECTED_BASE_SHA256 = "2e3f7814c9fc80cc27cba3dd3f3e7390eebffe8ccbe2b99dc742ae86e2f1994a"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("real-impact C4 scene base identity mismatch")
source = BASE.read_text(encoding="utf-8")
before = 'DRIVE_ENDS = {"I08": 8, "I10": 10, "I12": 12}'
after = 'DRIVE_ENDS = {"I09": 9}'
if source.count(before) != 1:
    raise RuntimeError("real-impact C4 cell roster target mismatch")
source = source.replace(before, after)
exec(compile(source, str(BASE) + "#C4_I09_MIDPOINT", "exec"), globals(), globals())
