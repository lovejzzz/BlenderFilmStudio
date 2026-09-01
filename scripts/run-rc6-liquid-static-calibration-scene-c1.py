#!/usr/bin/env python3
"""C1: correct one Python boolean token after the retained attempt-15 bake."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-liquid-static-calibration-scene.py")
EXPECTED_BASE_SHA256 = "4ee27ef3e381bbc6275d18044f97194a825b3d935f0b2bc604f09232d26ced48"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("static calibration scene C1 base identity mismatch")

source = BASE.read_text(encoding="utf-8")
before = '"preContactOnly": true,'
after = '"preContactOnly": True,'
if source.count(before) != 1:
    raise RuntimeError("static calibration scene C1 boolean target is not exact")
source = source.replace(before, after)
exec(compile(source, str(BASE) + "#C1_PYTHON_BOOLEAN", "exec"), globals(), globals())
