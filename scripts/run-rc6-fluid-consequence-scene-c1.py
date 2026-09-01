#!/usr/bin/env python3
"""C1 in-memory correction: create the missing World after an empty factory reset."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-fluid-consequence-scene.py")
EXPECTED_BASE_SHA256 = "1385897455a451bbc7a012c3acf8e53a819fb121974fa8100ac9b1257bbc07d8"
digest = hashlib.sha256(BASE.read_bytes()).hexdigest()
if digest != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 C1 base scene tool identity mismatch")

source = BASE.read_text(encoding="utf-8")
before = "    scene.world.color = (0.018, 0.022, 0.035)"
after = "    scene.world = bpy.data.worlds.new(\"RC6 World\")\n    scene.world.color = (0.018, 0.022, 0.035)"
if source.count(before) != 1:
    raise RuntimeError("RC6 C1 World correction target is not unique")
corrected = source.replace(before, after)
exec(compile(corrected, str(BASE) + "#C1_WORLD", "exec"), globals(), globals())
