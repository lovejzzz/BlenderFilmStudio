#!/usr/bin/env python3
"""C2 wrapper: bind both admitted color-management enum names before execution."""

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "scripts/build-ai-native-studio-pc4.py"
BASE_SHA256 = "ee9760273f7a00e843956d7bf693e6101544b3465d1ae5967a417e5b3849fda4"
PATCHES = (
    ('output_scene.display_settings.display_device = "sRGB - Display"', 'output_scene.display_settings.display_device = "sRGB"'),
    ('output_scene.view_settings.view_transform = "ACES 2.0 - SDR 100 nits (Rec.709)"', 'output_scene.view_settings.view_transform = "ACES 2.0"'),
)


payload = BASE.read_bytes()
if hashlib.sha256(payload).hexdigest() != BASE_SHA256:
    raise RuntimeError("C2_BASE_BUILDER_HASH")
source = payload.decode("utf-8")
for old, new in PATCHES:
    if source.count(old) != 1:
        raise RuntimeError("C2_COLOR_PATCH_SITE")
    source = source.replace(old, new)
exec(compile(source, str(BASE), "exec"), {"__name__": "__main__", "__file__": str(BASE)})
