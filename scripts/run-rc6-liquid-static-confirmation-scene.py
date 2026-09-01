#!/usr/bin/env python3
"""High-resolution static confirmation using the measured radius-1.3 candidate."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-liquid-static-calibration-scene.py")
EXPECTED_BASE_SHA256 = "4ee27ef3e381bbc6275d18044f97194a825b3d935f0b2bc604f09232d26ced48"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("static confirmation scene base identity mismatch")

source = BASE.read_text(encoding="utf-8")
replacements = (
    ('"preContactOnly": true,', '"preContactOnly": True,', "Python boolean"),
    ('args.frame_end != 7 or args.resolution != 96 or args.particle_number != 2', 'args.frame_end != 7 or args.resolution != 192 or args.particle_number != 2', "resolution assertion"),
    ('args.particle_radius not in {1.0, 1.1, 1.2, 1.3}', 'args.particle_radius != 1.3', "radius assertion"),
)
for before, after, label in replacements:
    if source.count(before) != 1:
        raise RuntimeError(f"static confirmation scene {label} target is not exact")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#HIGH_RES_STATIC_CONFIRMATION", "exec"), globals(), globals())
