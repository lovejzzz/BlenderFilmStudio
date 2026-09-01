#!/usr/bin/env python3
"""C1 wrapper: correct only the admitted display-device enum before execution."""

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "scripts/build-ai-native-studio-pc4.py"
BASE_SHA256 = "ee9760273f7a00e843956d7bf693e6101544b3465d1ae5967a417e5b3849fda4"
OLD = 'output_scene.display_settings.display_device = "sRGB - Display"'
NEW = 'output_scene.display_settings.display_device = "sRGB"'


payload = BASE.read_bytes()
if hashlib.sha256(payload).hexdigest() != BASE_SHA256:
    raise RuntimeError("C1_BASE_BUILDER_HASH")
source = payload.decode("utf-8")
if source.count(OLD) != 1:
    raise RuntimeError("C1_DISPLAY_PATCH_SITE")
exec(compile(source.replace(OLD, NEW), str(BASE), "exec"), {"__name__": "__main__", "__file__": str(BASE)})
