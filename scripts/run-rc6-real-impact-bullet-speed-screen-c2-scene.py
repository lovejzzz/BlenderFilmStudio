#!/usr/bin/env python3
"""C2 versioned adapter for the unchanged real-impact scene measurement."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-real-impact-bullet-speed-screen-scene.py")
EXPECTED_BASE_SHA256 = "2e3f7814c9fc80cc27cba3dd3f3e7390eebffe8ccbe2b99dc742ae86e2f1994a"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("real-impact C2 scene base identity mismatch")
exec(compile(BASE.read_text(encoding="utf-8"), str(BASE) + "#C2_PARENT_OID", "exec"), globals(), globals())
